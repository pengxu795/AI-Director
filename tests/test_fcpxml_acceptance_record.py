import ast
import json
from pathlib import Path

import pytest

from modules.adapters import (
    build_fcpxml_acceptance_record,
    build_fcpxml_import_acceptance_protocol,
    validate_fcpxml_acceptance_record_input,
    write_fcpxml_acceptance_record,
)


def sample_design():
    return json.loads(Path("output/sample_fcpxml_design.json").read_text(encoding="utf-8"))


def acceptance_ready_protocol(tmp_path):
    design_path = tmp_path / "design.json"
    design_path.write_text(json.dumps(sample_design(), ensure_ascii=False), encoding="utf-8")
    return build_fcpxml_import_acceptance_protocol(
        sample_design(),
        "output/sample_minimal.fcpxml",
        source_design_path=design_path,
        git_commit="abc123",
        serializer_commit="def456",
        generated_at="2026-07-04T00:00:00+00:00",
    )


def manual_result(protocol, status="passed", asset_state="online", blocker_error=False):
    artifacts = protocol["source_artifacts"]
    checks = [
        {
            "id": item["id"],
            "status": "passed" if status == "passed" else ("failed" if item["id"] == "marker_positions" else "passed"),
            "actual_result": "Manual observation recorded.",
            "evidence_path": "evidence/fcpxml_import_screen.png",
            "notes": "",
        }
        for item in protocol["checklist"]
    ]
    return {
        "status": status,
        "artifact_identifiers": {
            "fcpxml_path": artifacts["fcpxml_path"],
            "fcpxml_sha256": artifacts["fcpxml_sha256"],
            "source_design_path": artifacts["source_design_path"],
            "source_design_sha256": artifacts["source_design_sha256"],
            "git_commit": artifacts["git_commit"],
            "serializer_commit": artifacts["serializer_commit"],
        },
        "artifact_relationship_confirmation": {
            "relationship_verified": True,
            "confirmed_by": "manual-reviewer",
            "confirmed_at": "2026-07-04T01:00:00+00:00",
            "notes": "Design JSON, FCPXML, and serializer commit were checked before import.",
        },
        "tester": "manual-reviewer",
        "run_at": "2026-07-04T01:05:00+00:00",
        "final_cut_pro_version": "10.8.1",
        "macos_version": "15.5",
        "library_name": "AI-Director Acceptance",
        "project_name": "Module 11 Sample",
        "import_result": "passed" if status in {"passed", "failed", "blocked"} else status,
        "media_validation_result": "passed" if status == "passed" else status,
        "imported": status == "passed",
        "compatibility_result": status,
        "summary": "Manual FCPXML import result captured.",
        "asset_results": [
            {
                "asset_id": asset["asset_id"],
                "source_file": asset["source_file"],
                "import_state": asset_state,
                "notes": f"Source media manually recorded as {asset_state}.",
            }
            for asset in protocol["expected_assets"]
        ],
        "checks": checks,
        "import_errors": []
        if status == "passed" and not blocker_error
        else [
            {
                "code": "manual_import_blocker",
                "message": "A blocker was observed during manual import review.",
                "severity": "blocker",
            }
        ],
        "evidence": [
            {
                "evidence_id": "ev001",
                "evidence_type": "screenshot",
                "path_or_reference": "evidence/fcpxml_import_screen.png",
                "description": "Manual import evidence screenshot.",
                "related_asset_ids": [asset["asset_id"] for asset in protocol["expected_assets"]],
                "related_check_ids": [item["id"] for item in protocol["checklist"]],
                "related_error_codes": ["manual_import_blocker"] if status != "passed" or blocker_error else [],
            }
        ],
        "regression_samples": [
            {
                "name": "module11_sample_fcpxml",
                "fcpxml_path": artifacts["fcpxml_path"],
                "fcpxml_sha256": artifacts["fcpxml_sha256"],
                "result": status,
            }
        ],
        "media_files_read_by_code": False,
        "editor_launched_by_code": False,
        "automatic_import_performed": False,
        "video_export_performed": False,
    }


def test_acceptance_record_captures_passing_manual_result(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    result = manual_result(protocol)

    record = build_fcpxml_acceptance_record(protocol, result)

    assert record["status"] == "recorded"
    assert record["validation_result"]["valid"] is True
    assert record["source_protocol"]["acceptance_ready"] is True
    assert record["recorded_artifacts"]["fcpxml_sha256"] == protocol["source_artifacts"]["fcpxml_sha256"]
    assert record["artifact_relationship_confirmation"]["relationship_verified"] is True
    assert record["environment"]["final_cut_pro_version"] == "10.8.1"
    assert record["result"]["compatibility_result"] == "passed"
    assert record["result"]["import_result"] == "passed"
    assert record["result"]["media_validation_result"] == "passed"
    assert all(check["status"] == "passed" for check in record["check_results"])
    assert all(asset["import_state"] == "online" for asset in record["asset_results"])
    assert record["metadata"]["editor_launched"] is False
    assert record["metadata"]["automatic_import_performed"] is False


def test_acceptance_record_captures_failed_result_with_error_details(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    result = manual_result(protocol, status="failed")

    record = build_fcpxml_acceptance_record(protocol, result)

    assert record["status"] == "recorded"
    assert record["validation_result"]["valid"] is True
    assert record["result"]["compatibility_result"] == "failed"
    assert record["import_errors"][0]["code"] == "manual_import_blocker"
    assert any(check["status"] == "failed" for check in record["check_results"])


@pytest.mark.parametrize("asset_state", ["offline", "missing", "unverified"])
def test_acceptance_record_does_not_allow_pass_when_media_is_not_online(tmp_path, asset_state):
    protocol = acceptance_ready_protocol(tmp_path)
    result = manual_result(protocol, asset_state=asset_state)

    validation = validate_fcpxml_acceptance_record_input(protocol, result)

    assert validation["valid"] is False
    assert any(error["code"] == "media_assets_not_online" for error in validation["errors"])
    assert any(error["code"] == "passed_result_requires_online_assets" for error in validation["errors"])


def test_acceptance_record_can_capture_import_passed_but_offline_media_as_blocked(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    result = manual_result(protocol, status="blocked", asset_state="offline")
    result["imported"] = True
    result["import_result"] = "passed"
    result["media_validation_result"] = "blocked"
    result["compatibility_result"] = "blocked"
    result["summary"] = "Only FCPXML import was verified; offline media prevents edit validation."

    record = build_fcpxml_acceptance_record(protocol, result)

    assert record["status"] == "recorded"
    assert record["validation_result"]["valid"] is True
    assert any(warning["code"] == "media_assets_not_online" for warning in record["validation_result"]["warnings"])
    assert record["result"]["import_result"] == "passed"
    assert record["result"]["media_validation_result"] == "blocked"
    assert record["result"]["compatibility_result"] == "blocked"


def test_acceptance_record_does_not_allow_pass_with_blocker_import_error(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    result = manual_result(protocol, blocker_error=True)

    validation = validate_fcpxml_acceptance_record_input(protocol, result)

    assert validation["valid"] is False
    assert any(error["code"] == "passed_result_has_blocker_import_error" for error in validation["errors"])


def test_acceptance_record_does_not_allow_blocked_status_with_passed_compatibility(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    result = manual_result(protocol)
    result["status"] = "blocked"
    result["imported"] = False
    result["import_result"] = "passed"
    result["media_validation_result"] = "passed"
    result["compatibility_result"] = "passed"

    validation = validate_fcpxml_acceptance_record_input(protocol, result)

    assert validation["valid"] is False
    assert any(error["code"] == "compatibility_pass_requires_pass_status" for error in validation["errors"])
    assert any(error["code"] == "compatibility_pass_requires_import" for error in validation["errors"])


def test_acceptance_record_requires_asset_validation_for_every_expected_asset(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    result = manual_result(protocol)
    result["asset_results"] = result["asset_results"][:-1]

    validation = validate_fcpxml_acceptance_record_input(protocol, result)

    assert validation["valid"] is False
    assert any(error["code"] == "missing_asset_validation" for error in validation["errors"])


def test_acceptance_record_blocks_protocol_without_acceptance_ready():
    protocol = build_fcpxml_import_acceptance_protocol(sample_design(), "output/sample_minimal.fcpxml")
    result = manual_result(protocol)

    record = build_fcpxml_acceptance_record(protocol, result)

    assert record["status"] == "blocked"
    assert any(error["code"] == "protocol_not_acceptance_ready" for error in record["validation_result"]["errors"])


def test_acceptance_record_blocks_artifact_identifier_mismatch(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    result = manual_result(protocol)
    result["artifact_identifiers"]["fcpxml_sha256"] = "bad"

    validation = validate_fcpxml_acceptance_record_input(protocol, result)

    assert validation["valid"] is False
    assert any(error["code"] == "artifact_identifier_mismatch" for error in validation["errors"])


def test_acceptance_record_requires_manual_relationship_confirmation(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    result = manual_result(protocol)
    result["artifact_relationship_confirmation"]["relationship_verified"] = False

    validation = validate_fcpxml_acceptance_record_input(protocol, result)

    assert validation["valid"] is False
    assert any(error["code"] == "artifact_relationship_not_confirmed" for error in validation["errors"])


def test_acceptance_record_requires_evidence(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    result = manual_result(protocol)
    result["evidence"] = []

    validation = validate_fcpxml_acceptance_record_input(protocol, result)

    assert validation["valid"] is False
    assert any(error["code"] == "missing_manual_evidence" for error in validation["errors"])


def test_acceptance_record_write_outputs_json_only(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    record = build_fcpxml_acceptance_record(protocol, manual_result(protocol))
    output = tmp_path / "acceptance_record.json"

    result = write_fcpxml_acceptance_record(record, output)

    assert output.exists()
    assert result["status"] == "written"
    assert result["record_file_written"] is True
    assert result["media_files_read"] is False
    assert result["editor_launched"] is False
    assert result["automatic_import_performed"] is False
    assert result["video_export_performed"] is False


def test_acceptance_record_rejects_boundary_violations(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    result = manual_result(protocol)
    result["editor_launched_by_code"] = True

    validation = validate_fcpxml_acceptance_record_input(protocol, result)

    assert validation["valid"] is False
    assert any(error["code"] == "boundary_violation" for error in validation["errors"])


def test_acceptance_record_module_does_not_import_editor_or_media_automation_libraries():
    forbidden = {"ffmpeg", "cv2", "moviepy", "subprocess", "pyautogui", "AppKit", "Quartz"}
    for path in (
        Path("modules/adapters/fcpxml_acceptance_record.py"),
        Path("app/record_fcpxml_acceptance_result.py"),
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not (imports & forbidden)


def test_invalid_acceptance_record_is_not_written(tmp_path):
    protocol = acceptance_ready_protocol(tmp_path)
    record = build_fcpxml_acceptance_record(protocol, manual_result(protocol))
    record["status"] = "blocked"

    with pytest.raises(ValueError):
        write_fcpxml_acceptance_record(record, tmp_path / "invalid.json")
    assert not (tmp_path / "invalid.json").exists()
