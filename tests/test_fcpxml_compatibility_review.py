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
