import ast
import hashlib
import json
from pathlib import Path

import pytest

from modules.adapters import (
    build_fcpxml_remediation_authorization,
    build_fcpxml_remediation_authorization_from_file,
    validate_fcpxml_remediation_authorization_input,
    write_fcpxml_remediation_authorization,
)


def load_selection(name="sample_fcpxml_remediation_selection.json"):
    return json.loads(Path("output", name).read_text(encoding="utf-8"))


def authorization_request():
    return {
        "authorized_by": "module14-reviewer",
        "authorized_at": "2026-07-04T02:40:00+00:00",
        "authorization_rationale": "Authorize a narrow future implementation scope for the selected evidence-backed remediation.",
        "source_selection_artifact": "output/sample_fcpxml_remediation_selection.json",
        "source_selection_sha256": hashlib.sha256(Path("output/sample_fcpxml_remediation_selection.json").read_bytes()).hexdigest(),
        "allowed_files": [
            "docs/fcpxml_acceptance_record.md",
            "docs/fcpxml_compatibility_review.md",
            "output/sample_fcpxml_acceptance_record_offline_blocked.json",
            "output/sample_fcpxml_compatibility_review.json",
            "CHANGELOG.md",
            "PROJECT_STATE.md",
        ],
        "prohibited_files": [
            "modules/story/",
            "modules/script/",
            "modules/timeline/",
            "data/",
            "media/",
        ],
        "verification_commands": [
            "python -m pytest -q",
            "python -m compileall modules app tests",
            "git diff --check",
        ],
        "rollback_steps": [
            "Stop implementation immediately.",
            "Revert only files changed by the future implementation module.",
            "Record the failed verification result before requesting Review.",
        ],
    }


def authorization_request_without_fingerprint():
    request = authorization_request()
    request.pop("source_selection_artifact", None)
    request.pop("source_selection_sha256", None)
    return request


def write_selection(tmp_path, selection):
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_authorization_records_scope_contract_without_execution():
    authorization = build_fcpxml_remediation_authorization_from_file("output/sample_fcpxml_remediation_selection.json", authorization_request())

    assert authorization["status"] == "authorization_ready"
    assert authorization["authorization_id"] == "auth_r001"
    assert authorization["implementation_execution_allowed"] is False
    assert authorization["serializer_change_execution_allowed"] is False
    assert authorization["manual_follow_up_required"] is True
    assert authorization["metadata"]["code_changes_applied"] is False
    assert authorization["metadata"]["serializer_modified"] is False
    assert "docs/fcpxml_acceptance_record.md" in authorization["implementation_scope"]["allowed_files"]
    assert authorization["immutable_authorization_snapshot"]["selection"]["selection_id"] == "sel_r001"


def test_authorization_requires_selected_input():
    selection = load_selection()
    selection["status"] = "blocked"

    validation = validate_fcpxml_remediation_authorization_input(selection, authorization_request())

    assert validation["valid"] is False
    assert any(error["code"] == "selection_not_selected" for error in validation["errors"])


def test_authorization_requires_selection_fingerprint():
    request = authorization_request()
    request["source_selection_sha256"] = ""

    authorization = build_fcpxml_remediation_authorization(load_selection(), request)

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "missing_source_selection_fingerprint" for error in authorization["validation_result"]["errors"])


def test_authorization_from_file_records_selection_sha256():
    path = Path("output/sample_fcpxml_remediation_selection.json")
    authorization = build_fcpxml_remediation_authorization_from_file(path, authorization_request())

    assert authorization["status"] == "authorization_ready"
    assert authorization["source_selection"]["source_selection_artifact"] == str(path)
    assert authorization["source_selection"]["source_selection_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_authorization_from_file_blocks_forged_selection_sha256():
    request = authorization_request()
    request["source_selection_sha256"] = "not-the-real-sha"

    authorization = build_fcpxml_remediation_authorization_from_file("output/sample_fcpxml_remediation_selection.json", request)

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "source_selection_fingerprint_mismatch" for error in authorization["validation_result"]["errors"])


def test_authorization_from_file_blocks_forged_selection_path():
    request = authorization_request()
    request["source_selection_artifact"] = "output/other_selection.json"

    authorization = build_fcpxml_remediation_authorization_from_file("output/sample_fcpxml_remediation_selection.json", request)

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "source_selection_fingerprint_mismatch" for error in authorization["validation_result"]["errors"])


def test_direct_builder_cannot_create_authorization_ready():
    authorization = build_fcpxml_remediation_authorization(load_selection(), authorization_request())

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "source_selection_artifact_not_verified" for error in authorization["validation_result"]["errors"])


def test_authorization_from_file_sha_changes_when_selection_file_changes(tmp_path):
    selection = load_selection()
    first_path = write_selection(tmp_path, selection)
    first = build_fcpxml_remediation_authorization_from_file(first_path, authorization_request_without_fingerprint())

    selection["selection_rationale"] = "Changed selection content."
    second_path = write_selection(tmp_path, selection)
    second = build_fcpxml_remediation_authorization_from_file(second_path, authorization_request_without_fingerprint())

    assert first["status"] == "authorization_ready"
    assert second["status"] == "authorization_ready"
    assert first["source_selection"]["source_selection_sha256"] != second["source_selection"]["source_selection_sha256"]


def test_authorization_from_file_blocks_missing_selection_file():
    authorization = build_fcpxml_remediation_authorization_from_file("output/missing_selection.json", authorization_request())

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "remediation_selection_file_not_found" for error in authorization["validation_result"]["errors"])


def test_authorization_rejects_overlapping_allowed_and_prohibited_files():
    request = authorization_request()
    request["prohibited_files"].append("docs/fcpxml_acceptance_record.md")

    authorization = build_fcpxml_remediation_authorization(load_selection(), request)

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "allowed_file_also_prohibited" for error in authorization["validation_result"]["errors"])


def test_human_review_remediation_rejects_serializer_allowed_file():
    request = authorization_request()
    request["allowed_files"].append("modules/adapters/fcpxml_serializer.py")

    authorization = build_fcpxml_remediation_authorization(load_selection(), request)

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "serializer_scope_not_authorized_for_selected_remediation" for error in authorization["validation_result"]["errors"])
    assert any(error["code"] == "human_review_scope_path_not_allowed" for error in authorization["validation_result"]["errors"])


def test_serializer_change_false_rejects_serializer_test_and_fcpxml_output_scope():
    request = authorization_request()
    request["allowed_files"].extend(["tests/test_fcpxml_serializer.py", "output/sample_minimal.fcpxml"])

    authorization = build_fcpxml_remediation_authorization(load_selection(), request)

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "serializer_scope_not_authorized_for_selected_remediation" for error in authorization["validation_result"]["errors"])


@pytest.mark.parametrize(
    "path",
    [
        "tests/test_fcpxml_serializer_regression.py",
        "docs/fcpxml_serializer_followup.md",
        "app/export_fcpxml_v2.py",
        "modules/adapters/fcpxml_export_helper.py",
    ],
)
def test_human_review_scope_rejects_semantic_serializer_or_export_paths(path):
    request = authorization_request()
    request["allowed_files"].append(path)

    authorization = build_fcpxml_remediation_authorization(load_selection(), request)

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "human_review_scope_path_not_allowed" for error in authorization["validation_result"]["errors"])


def test_serializer_change_false_rejects_adapter_export_helper_path():
    request = authorization_request()
    request["allowed_files"].append("modules/adapters/fcpxml_export_helper.py")

    authorization = build_fcpxml_remediation_authorization(load_selection(), request)

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "serializer_scope_not_authorized_for_selected_remediation" for error in authorization["validation_result"]["errors"])


@pytest.mark.parametrize(
    "path",
    [
        "modules/adapters/fcpxml_writer.py",
        "modules/adapters/fcpxml_generator.py",
        "modules/adapters/fcpxml_project_builder.py",
        "tests/test_fcpxml_writer.py",
        "docs/fcpxml_writer.md",
        "app/generate_fcpxml.py",
    ],
)
def test_serializer_change_false_rejects_fcpxml_implementation_paths(path):
    request = authorization_request()
    request["allowed_files"].append(path)

    authorization = build_fcpxml_remediation_authorization(load_selection(), request)

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "fcpxml_implementation_scope_not_authorized" for error in authorization["validation_result"]["errors"])


def test_human_review_remediation_allows_record_and_documentation_only_scope():
    authorization = build_fcpxml_remediation_authorization_from_file("output/sample_fcpxml_remediation_selection.json", authorization_request())

    assert authorization["status"] == "authorization_ready"
    assert authorization["implementation_scope"]["manual_follow_up_required"] is True
    assert all("fcpxml_serializer.py" not in path for path in authorization["implementation_scope"]["allowed_files"])


def test_serializer_remediation_can_authorize_serializer_files_only_when_selected_remediation_allows_it(tmp_path):
    selection = load_selection()
    selection["immutable_selection_snapshot"]["remediation"]["owner"] = "engineering"
    selection["immutable_selection_snapshot"]["remediation"]["serializer_change_allowed"] = True
    selection_path = write_selection(tmp_path, selection)
    request = authorization_request_without_fingerprint()
    request["allowed_files"] = [
        "modules/adapters/fcpxml_serializer.py",
        "modules/adapters/fcpxml_export_helper.py",
        "modules/adapters/fcpxml_writer.py",
        "modules/adapters/fcpxml_generator.py",
        "modules/adapters/fcpxml_project_builder.py",
        "tests/test_fcpxml_serializer_regression.py",
        "tests/test_fcpxml_writer.py",
        "docs/fcpxml_serializer_followup.md",
        "docs/fcpxml_writer.md",
        "app/export_fcpxml_v2.py",
        "app/generate_fcpxml.py",
        "CHANGELOG.md",
        "PROJECT_STATE.md",
    ]

    authorization = build_fcpxml_remediation_authorization_from_file(selection_path, request)

    assert authorization["status"] == "authorization_ready"
    assert authorization["manual_follow_up_required"] is False
    assert "modules/adapters/fcpxml_serializer.py" in authorization["implementation_scope"]["allowed_files"]


def test_authorization_requires_verification_and_rollback_plan():
    request = authorization_request()
    request["verification_commands"] = []
    request["rollback_steps"] = []

    authorization = build_fcpxml_remediation_authorization(load_selection(), request)

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "missing_verification_commands" for error in authorization["validation_result"]["errors"])
    assert any(error["code"] == "missing_rollback_steps" for error in authorization["validation_result"]["errors"])


def test_authorization_blocks_media_or_editor_verification_commands():
    request = authorization_request()
    request["verification_commands"].append("ffmpeg -i sample.mp4")

    authorization = build_fcpxml_remediation_authorization(load_selection(), request)

    assert authorization["status"] == "blocked"
    assert any(error["code"] == "forbidden_verification_command" for error in authorization["validation_result"]["errors"])


def test_authorization_snapshot_is_immutable_after_selection_changes(tmp_path):
    selection = load_selection()
    selection_path = write_selection(tmp_path, selection)
    authorization = build_fcpxml_remediation_authorization_from_file(selection_path, authorization_request_without_fingerprint())

    selection["selected_remediation_id"] = "changed"
    selection["immutable_selection_snapshot"]["remediation"]["action"] = "changed"

    assert authorization["immutable_authorization_snapshot"]["selection"]["selected_remediation_id"] == "r001"
    assert authorization["immutable_authorization_snapshot"]["selection"]["immutable_selection_snapshot"]["remediation"]["action"] == "Repeat manual import with bound online media before assessing source ranges or edit usability."


def test_authorization_write_outputs_json_only(tmp_path):
    authorization = build_fcpxml_remediation_authorization_from_file("output/sample_fcpxml_remediation_selection.json", authorization_request())
    output = tmp_path / "authorization.json"

    result = write_fcpxml_remediation_authorization(authorization, output)

    assert output.exists()
    assert result["status"] == "written"
    assert result["authorization_file_written"] is True
    assert result["code_changes_applied"] is False
    assert result["serializer_modified"] is False
    assert result["fcpxml_generated"] is False
    assert result["media_files_read"] is False
    assert result["editor_launched"] is False
    assert result["automatic_import_performed"] is False
    assert result["video_export_performed"] is False


def test_authorization_module_does_not_import_editor_or_media_automation_libraries():
    forbidden = {"ffmpeg", "cv2", "moviepy", "subprocess", "pyautogui", "AppKit", "Quartz"}
    for path in (
        Path("modules/adapters/fcpxml_remediation_authorization.py"),
        Path("app/authorize_fcpxml_remediation.py"),
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not (imports & forbidden)
