import ast
import json
from pathlib import Path

import pytest

from modules.adapters import (
    build_fcpxml_compatibility_review,
    validate_fcpxml_compatibility_review_input,
    write_fcpxml_compatibility_review,
)


def load_record(name="sample_fcpxml_acceptance_record.json"):
    return json.loads(Path("output", name).read_text(encoding="utf-8"))


def test_compatibility_review_passed_record_has_no_remediation_items():
    review = build_fcpxml_compatibility_review(load_record())

    assert review["status"] == "review_ready"
    assert review["validation_result"]["valid"] is True
    assert review["result_summary"]["compatibility_result"] == "passed"
    assert review["findings"] == [
        {
            "id": "f001",
            "code": "manual_acceptance_passed",
            "severity": "info",
            "category": "compatibility",
            "summary": "Manual acceptance record passed with no findings.",
            "reproduction": "No remediation required.",
            "evidence_refs": [],
            "evidence_status": "linked",
            "original_severity": "info",
            "related_entities": {"asset_ids": [], "check_ids": [], "error_codes": []},
            "status": "informational",
        }
    ]
    assert review["remediation_plan"]["status"] == "no_action_needed"
    assert review["remediation_plan"]["items"] == []
    assert review["metadata"]["serializer_modified"] is False


def test_compatibility_review_extracts_offline_media_and_blocked_checks():
    review = build_fcpxml_compatibility_review(load_record("sample_fcpxml_acceptance_record_offline_blocked.json"))
    finding_codes = {finding["code"] for finding in review["findings"]}

    assert review["status"] == "review_ready"
    assert "media_not_online" in finding_codes
    assert "manual_check_not_passed" in finding_codes
    assert "media_offline" in finding_codes
    assert "media_assets_not_online" in finding_codes
    assert review["remediation_plan"]["status"] == "proposed"
    assert all(item["serializer_change_allowed"] is False for item in review["remediation_plan"]["items"])
    assert any(item["priority"] == "P0" for item in review["remediation_plan"]["items"])
    assert all(finding["evidence_refs"] for finding in review["findings"] if finding["code"] != "media_assets_not_online")
    assert any("ev_asset_001" in finding["evidence_refs"] for finding in review["findings"] if finding["code"] == "media_not_online")
    assert any("ev_check_clip_source_ranges" in finding["evidence_refs"] for finding in review["findings"] if finding["code"] == "manual_check_not_passed")
    assert any("ev_error_media_offline" in finding["evidence_refs"] for finding in review["findings"] if finding["code"] == "media_offline")


def test_compatibility_review_blocks_invalid_acceptance_record():
    record = load_record()
    record["status"] = "blocked"

    review = build_fcpxml_compatibility_review(record)

    assert review["status"] == "blocked"
    assert any(error["code"] == "acceptance_record_not_recorded" for error in review["validation_result"]["errors"])
    with pytest.raises(ValueError):
        write_fcpxml_compatibility_review(review, Path("output/should_not_write.json"))


def test_compatibility_review_requires_traceable_source_artifacts():
    record = load_record()
    record["source_protocol"]["fcpxml_sha256"] = ""

    validation = validate_fcpxml_compatibility_review_input(record)

    assert validation["valid"] is False
    assert any(error["code"] == "missing_source_record_artifact" for error in validation["errors"])


def test_compatibility_review_marks_missing_evidence_as_incomplete():
    record = load_record("sample_fcpxml_acceptance_record_offline_blocked.json")
    record["evidence"] = []

    review = build_fcpxml_compatibility_review(record)

    assert review["status"] == "evidence_incomplete"
    assert any(warning["code"] == "missing_review_evidence" for warning in review["validation_result"]["warnings"])
    assert any(warning["code"] == "missing_evidence_for_import_error" for warning in review["validation_result"]["warnings"])
    assert all(finding["severity"] != "blocker" for finding in review["findings"])
    assert all(item["priority"] != "P0" for item in review["remediation_plan"]["items"])
    assert all(item["requires_evidence_before_implementation"] is True for item in review["remediation_plan"]["items"])


def test_incomplete_asset_evidence_cannot_confirm_blocker_finding():
    record = load_record("sample_fcpxml_acceptance_record_offline_blocked.json")
    for evidence in record["evidence"]:
        if evidence["evidence_id"] in {"ev_asset_001", "ev_check_clip_source_ranges", "ev_error_media_offline"}:
            evidence["related_asset_ids"] = []
    asset_evidence = next(evidence for evidence in record["evidence"] if evidence["evidence_id"] == "ev_asset_001")
    asset_evidence["related_asset_ids"] = ["asset_001"]
    asset_evidence["path_or_reference"] = ""

    review = build_fcpxml_compatibility_review(record)
    asset_finding = next(
        finding
        for finding in review["findings"]
        if finding["code"] == "media_not_online" and "asset_001" in finding["related_entities"]["asset_ids"]
    )

    assert review["status"] == "evidence_incomplete"
    assert asset_finding["evidence_status"] == "missing"
    assert asset_finding["severity"] == "warning"
    assert "ev_asset_001" not in asset_finding["evidence_refs"]
    assert any(warning["code"] == "unusable_evidence_entry" for warning in review["validation_result"]["warnings"])


def test_incomplete_check_evidence_cannot_generate_confirmed_p0_remediation():
    record = load_record("sample_fcpxml_acceptance_record_offline_blocked.json")
    for evidence in record["evidence"]:
        evidence["related_check_ids"] = []
    check_evidence = next(evidence for evidence in record["evidence"] if evidence["evidence_id"] == "ev_check_clip_source_ranges")
    check_evidence["related_check_ids"] = ["clip_source_ranges"]
    check_evidence["description"] = ""

    review = build_fcpxml_compatibility_review(record)
    check_finding = next(finding for finding in review["findings"] if finding["code"] == "manual_check_not_passed")
    check_remediation = next(item for item in review["remediation_plan"]["items"] if item["finding_id"] == check_finding["id"])

    assert review["status"] == "evidence_incomplete"
    assert check_finding["evidence_status"] == "missing"
    assert check_finding["severity"] == "warning"
    assert check_remediation["priority"] != "P0"
    assert check_remediation["requires_evidence_before_implementation"] is True


def test_duplicate_import_error_evidence_ids_are_all_unusable():
    record = load_record("sample_fcpxml_acceptance_record_offline_blocked.json")
    error_evidence = next(evidence for evidence in record["evidence"] if evidence["evidence_id"] == "ev_error_media_offline")
    duplicate = dict(error_evidence)
    record["evidence"].append(duplicate)

    review = build_fcpxml_compatibility_review(record)
    import_finding = next(finding for finding in review["findings"] if finding["code"] == "media_offline")

    assert review["status"] == "evidence_incomplete"
    assert import_finding["evidence_status"] == "missing"
    assert import_finding["severity"] == "warning"
    assert import_finding["evidence_refs"] == []
    assert any(warning["code"] == "duplicate_evidence_id" for warning in review["validation_result"]["warnings"])


def test_complete_unique_evidence_still_confirms_blocker_findings():
    review = build_fcpxml_compatibility_review(load_record("sample_fcpxml_acceptance_record_offline_blocked.json"))

    assert review["status"] == "review_ready"
    assert any(finding["severity"] == "blocker" and finding["evidence_status"] == "linked" for finding in review["findings"])
    assert any(item["priority"] == "P0" and item["requires_evidence_before_implementation"] is False for item in review["remediation_plan"]["items"])


def test_mixed_complete_and_incomplete_evidence_uses_only_complete_entries():
    record = load_record("sample_fcpxml_acceptance_record_offline_blocked.json")
    complete = {
        "evidence_id": "ev_asset_001_complete_extra",
        "evidence_type": "manual_note",
        "path_or_reference": "evidence/asset_001_complete_extra.md",
        "description": "A complete secondary note for asset_001.",
        "related_asset_ids": ["asset_001"],
        "related_check_ids": [],
        "related_error_codes": [],
    }
    incomplete = {
        "evidence_id": "ev_asset_001_incomplete_extra",
        "evidence_type": "manual_note",
        "path_or_reference": "",
        "description": "This entry is missing its path.",
        "related_asset_ids": ["asset_001"],
        "related_check_ids": [],
        "related_error_codes": [],
    }
    record["evidence"].extend([complete, incomplete])

    review = build_fcpxml_compatibility_review(record)
    asset_finding = next(
        finding
        for finding in review["findings"]
        if finding["code"] == "media_not_online" and "asset_001" in finding["related_entities"]["asset_ids"]
    )

    assert asset_finding["evidence_status"] == "linked"
    assert "ev_asset_001_complete_extra" in asset_finding["evidence_refs"]
    assert "ev_asset_001_incomplete_extra" not in asset_finding["evidence_refs"]
    assert any(warning["code"] == "unusable_evidence_entry" for warning in review["validation_result"]["warnings"])


def test_compatibility_review_keeps_entity_refs_separate_from_evidence_refs():
    review = build_fcpxml_compatibility_review(load_record("sample_fcpxml_acceptance_record_offline_blocked.json"))
    media_finding = next(finding for finding in review["findings"] if finding["code"] == "media_not_online")
    check_finding = next(finding for finding in review["findings"] if finding["code"] == "manual_check_not_passed")

    assert "asset_001" not in media_finding["evidence_refs"]
    assert "asset_001" in media_finding["related_entities"]["asset_ids"]
    assert "clip_source_ranges" not in check_finding["evidence_refs"]
    assert "clip_source_ranges" in check_finding["related_entities"]["check_ids"]


def test_compatibility_review_write_outputs_json_only(tmp_path):
    review = build_fcpxml_compatibility_review(load_record("sample_fcpxml_acceptance_record_offline_blocked.json"))
    output = tmp_path / "compatibility_review.json"

    result = write_fcpxml_compatibility_review(review, output)

    assert output.exists()
    assert result["status"] == "written"
    assert result["review_file_written"] is True
    assert result["serializer_modified"] is False
    assert result["media_files_read"] is False
    assert result["editor_launched"] is False
    assert result["automatic_import_performed"] is False
    assert result["video_export_performed"] is False


def test_compatibility_review_module_does_not_import_editor_or_media_automation_libraries():
    forbidden = {"ffmpeg", "cv2", "moviepy", "subprocess", "pyautogui", "AppKit", "Quartz"}
    for path in (
        Path("modules/adapters/fcpxml_compatibility_review.py"),
        Path("app/review_fcpxml_compatibility.py"),
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not (imports & forbidden)
