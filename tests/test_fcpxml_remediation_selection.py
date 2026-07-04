import ast
import hashlib
import json
from pathlib import Path

import pytest

from modules.adapters import (
    build_fcpxml_remediation_selection,
    build_fcpxml_remediation_selection_from_file,
    validate_fcpxml_remediation_selection_input,
    write_fcpxml_remediation_selection,
)


def load_review(name="sample_fcpxml_compatibility_review.json"):
    return json.loads(Path("output", name).read_text(encoding="utf-8"))


def selection_request(remediation_id="r001"):
    return {
        "remediation_id": remediation_id,
        "selected_by": "module13-reviewer",
        "selected_at": "2026-07-04T02:10:00+00:00",
        "selection_rationale": "Select the highest-priority evidence-backed remediation for the next reviewed implementation module.",
        "source_review_artifact": "output/sample_fcpxml_compatibility_review.json",
        "source_review_sha256": hashlib.sha256(Path("output/sample_fcpxml_compatibility_review.json").read_bytes()).hexdigest(),
    }


def test_remediation_selection_records_one_linked_evidence_task_contract():
    selection = build_fcpxml_remediation_selection(load_review(), selection_request("r001"))

    assert selection["status"] == "selected"
    assert selection["selection_id"] == "sel_r001"
    assert selection["selected_remediation_id"] == "r001"
    assert selection["selected_finding_id"] == "f001"
    assert selection["evidence_refs"]
    assert selection["execution_allowed"] is False
    assert selection["requires_module_14_approval"] is True
    assert selection["source_review_sha256"] == selection_request("r001")["source_review_sha256"]
    assert selection["immutable_selection_snapshot"]["remediation"]["id"] == "r001"
    assert selection["task_contract"]["status"] == "task_contract_ready"
    assert selection["task_contract"]["implementation_allowed"] is False
    assert selection["task_contract"]["serializer_change_allowed"] is False
    assert selection["task_contract"]["requires_linked_evidence"] is True
    assert selection["metadata"]["serializer_modified"] is False


def test_remediation_selection_requires_review_ready_input():
    review = load_review()
    review["status"] = "evidence_incomplete"

    validation = validate_fcpxml_remediation_selection_input(review, selection_request("r001"))

    assert validation["valid"] is False
    assert any(error["code"] == "review_not_ready" for error in validation["errors"])


def test_remediation_selection_rejects_missing_remediation_id():
    request = selection_request("")
    selection = build_fcpxml_remediation_selection(load_review(), request)

    assert selection["status"] == "blocked"
    assert any(error["code"] == "selection_requires_explicit_remediation_id" for error in selection["validation_result"]["errors"])
    with pytest.raises(ValueError):
        write_fcpxml_remediation_selection(selection, Path("output/should_not_write_selection.json"))


def test_remediation_selection_rejects_multiple_remediation_ids():
    request = selection_request("")
    request["remediation_ids"] = ["r001", "r002"]

    selection = build_fcpxml_remediation_selection(load_review(), request)

    assert selection["status"] == "blocked"
    assert any(error["code"] == "multiple_remediations_not_allowed" for error in selection["validation_result"]["errors"])


def test_remediation_selection_rejects_unknown_remediation_id():
    selection = build_fcpxml_remediation_selection(load_review(), selection_request("missing"))

    assert selection["status"] == "blocked"
    assert any(error["code"] == "remediation_not_found" for error in selection["validation_result"]["errors"])


def test_remediation_selection_rejects_finding_without_linked_evidence():
    review = load_review()
    finding = next(item for item in review["findings"] if item["id"] == "f001")
    finding["evidence_refs"] = []
    finding["evidence_status"] = "missing"

    selection = build_fcpxml_remediation_selection(review, selection_request("r001"))

    assert selection["status"] == "blocked"
    assert any(error["code"] == "selected_finding_without_linked_evidence" for error in selection["validation_result"]["errors"])


def test_remediation_selection_rejects_warning_findings():
    review = load_review()
    finding = next(item for item in review["findings"] if item["id"] == "f001")
    finding["severity"] = "warning"

    selection = build_fcpxml_remediation_selection(review, selection_request("r001"))

    assert selection["status"] == "blocked"
    assert any(error["code"] == "selected_finding_not_actionable" for error in selection["validation_result"]["errors"])


def test_remediation_selection_rejects_items_requiring_more_evidence():
    review = load_review()
    remediation = next(item for item in review["remediation_plan"]["items"] if item["id"] == "r001")
    remediation["requires_evidence_before_implementation"] = True

    selection = build_fcpxml_remediation_selection(review, selection_request("r001"))

    assert selection["status"] == "blocked"
    assert any(error["code"] == "remediation_requires_more_evidence" for error in selection["validation_result"]["errors"])


def test_remediation_selection_rejects_serializer_change_allowed_items():
    review = load_review()
    remediation = next(item for item in review["remediation_plan"]["items"] if item["id"] == "r001")
    remediation["serializer_change_allowed"] = True

    selection = build_fcpxml_remediation_selection(review, selection_request("r001"))

    assert selection["status"] == "blocked"
    assert any(error["code"] == "remediation_allows_serializer_change" for error in selection["validation_result"]["errors"])


def test_remediation_selection_rejects_boundary_violating_review():
    review = load_review()
    review["metadata"]["serializer_modified"] = True

    selection = build_fcpxml_remediation_selection(review, selection_request("r001"))

    assert selection["status"] == "blocked"
    assert any(error["code"] == "boundary_violation" for error in selection["validation_result"]["errors"])


def test_remediation_selection_from_file_records_stable_review_sha256():
    path = Path("output/sample_fcpxml_compatibility_review.json")
    selection = build_fcpxml_remediation_selection_from_file(path, selection_request("r001"))

    assert selection["status"] == "selected"
    assert selection["source_review_artifact"] == str(path)
    assert selection["source_review_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_remediation_selection_from_file_blocks_missing_review_file():
    selection = build_fcpxml_remediation_selection_from_file("output/missing_review.json", selection_request("r001"))

    assert selection["status"] == "blocked"
    assert any(error["code"] == "fcpxml_compatibility_review_file_not_found" for error in selection["validation_result"]["errors"])


def test_remediation_selection_snapshot_is_immutable_after_review_changes():
    review = load_review()
    selection = build_fcpxml_remediation_selection(review, selection_request("r001"))

    review["findings"][0]["summary"] = "Changed after selection"
    review["remediation_plan"]["items"][0]["action"] = "Changed after selection"

    assert selection["immutable_selection_snapshot"]["finding"]["summary"] == "Asset asset_001 was offline."
    assert selection["immutable_selection_snapshot"]["remediation"]["action"] == "Repeat manual import with bound online media before assessing source ranges or edit usability."


def test_remediation_selection_write_outputs_json_only(tmp_path):
    selection = build_fcpxml_remediation_selection(load_review(), selection_request("r001"))
    output = tmp_path / "remediation_selection.json"

    result = write_fcpxml_remediation_selection(selection, output)

    assert output.exists()
    assert result["status"] == "written"
    assert result["selection_file_written"] is True
    assert result["serializer_modified"] is False
    assert result["media_files_read"] is False
    assert result["editor_launched"] is False
    assert result["automatic_import_performed"] is False
    assert result["video_export_performed"] is False


def test_remediation_selection_module_does_not_import_editor_or_media_automation_libraries():
    forbidden = {"ffmpeg", "cv2", "moviepy", "subprocess", "pyautogui", "AppKit", "Quartz"}
    for path in (
        Path("modules/adapters/fcpxml_remediation_selection.py"),
        Path("app/select_fcpxml_remediation.py"),
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not (imports & forbidden)
