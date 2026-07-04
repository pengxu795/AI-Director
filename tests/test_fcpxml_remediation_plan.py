import ast
import hashlib
import json
from pathlib import Path

import pytest

from modules.adapters import (
    build_fcpxml_remediation_plan,
    build_fcpxml_remediation_plan_from_file,
    validate_fcpxml_remediation_plan_input,
    write_fcpxml_remediation_plan,
)


def load_authorization(name="sample_fcpxml_remediation_authorization.json"):
    return json.loads(Path("output", name).read_text(encoding="utf-8"))


def plan_request():
    return {
        "planned_by": "module15-planner",
        "planned_at": "2026-07-04T03:15:00+00:00",
        "planning_rationale": "Convert the authorized human-review remediation into a reviewable implementation plan.",
        "source_authorization_artifact": "output/sample_fcpxml_remediation_authorization.json",
        "source_authorization_sha256": hashlib.sha256(Path("output/sample_fcpxml_remediation_authorization.json").read_bytes()).hexdigest(),
        "planned_file_changes": [
            {
                "path": "docs/fcpxml_acceptance_record.md",
                "action": "update_manual_review_guidance",
                "summary": "Document the follow-up import with bound online media and required evidence fields.",
            },
            {
                "path": "output/sample_fcpxml_acceptance_record_offline_blocked.json",
                "action": "add_manual_follow_up_placeholder",
                "summary": "Reserve a blocked follow-up sample until a human reviewer records online media evidence.",
            },
        ],
        "acceptance_criteria": [
            "Plan references the same authorization SHA-256 used by Module 14.",
            "All planned files are within Module 14 allowed_files.",
            "No serializer, FCPXML generation, editor automation, or media processing is planned.",
        ],
        "review_checklist": [
            "Confirm the implementation plan still requires a later approval module.",
            "Confirm rollback checkpoints are explicit before any future implementation.",
        ],
        "rollback_checkpoints": [
            "Stop before implementation if the authorized remediation no longer matches the manual evidence.",
            "Discard only future changes made under the implementation module if Review fails.",
        ],
    }


def plan_request_without_fingerprint():
    request = plan_request()
    request.pop("source_authorization_artifact", None)
    request.pop("source_authorization_sha256", None)
    return request


def write_authorization(tmp_path, authorization):
    path = tmp_path / "authorization.json"
    path.write_text(json.dumps(authorization, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_plan_records_authorized_scope_without_execution():
    plan = build_fcpxml_remediation_plan_from_file("output/sample_fcpxml_remediation_authorization.json", plan_request())

    assert plan["status"] == "plan_ready"
    assert plan["plan_id"] == "plan_r001"
    assert plan["implementation_execution_allowed"] is False
    assert plan["serializer_change_execution_allowed"] is False
    assert plan["requires_module_16_approval"] is True
    assert plan["metadata"]["code_changes_applied"] is False
    assert plan["metadata"]["serializer_modified"] is False
    assert plan["metadata"]["fcpxml_generated"] is False
    assert plan["source_authorization"]["source_authorization_sha256"] == hashlib.sha256(Path("output/sample_fcpxml_remediation_authorization.json").read_bytes()).hexdigest()
    assert plan["immutable_plan_snapshot"]["authorization"]["authorization_id"] == "auth_r001"


def test_plan_requires_authorization_ready():
    authorization = load_authorization()
    authorization["status"] = "blocked"

    validation = validate_fcpxml_remediation_plan_input(authorization, plan_request())

    assert validation["valid"] is False
    assert any(error["code"] == "authorization_not_ready" for error in validation["errors"])


def test_direct_builder_cannot_create_plan_ready():
    plan = build_fcpxml_remediation_plan(load_authorization(), plan_request())

    assert plan["status"] == "blocked"
    assert any(error["code"] == "source_authorization_artifact_not_verified" for error in plan["validation_result"]["errors"])


def test_plan_from_file_blocks_missing_authorization_file():
    plan = build_fcpxml_remediation_plan_from_file("output/missing_authorization.json", plan_request())

    assert plan["status"] == "blocked"
    assert any(error["code"] == "fcpxml_remediation_authorization_file_not_found" for error in plan["validation_result"]["errors"])


def test_plan_from_file_blocks_forged_authorization_sha():
    request = plan_request()
    request["source_authorization_sha256"] = "not-real"

    plan = build_fcpxml_remediation_plan_from_file("output/sample_fcpxml_remediation_authorization.json", request)

    assert plan["status"] == "blocked"
    assert any(error["code"] == "source_authorization_fingerprint_mismatch" for error in plan["validation_result"]["errors"])


def test_plan_from_file_blocks_forged_authorization_path():
    request = plan_request()
    request["source_authorization_artifact"] = "output/other_authorization.json"

    plan = build_fcpxml_remediation_plan_from_file("output/sample_fcpxml_remediation_authorization.json", request)

    assert plan["status"] == "blocked"
    assert any(error["code"] == "source_authorization_fingerprint_mismatch" for error in plan["validation_result"]["errors"])


def test_plan_from_file_sha_changes_when_authorization_file_changes(tmp_path):
    authorization = load_authorization()
    first_path = write_authorization(tmp_path, authorization)
    first = build_fcpxml_remediation_plan_from_file(first_path, plan_request_without_fingerprint())

    authorization["authorization_rationale"] = "Changed authorization content."
    second_path = write_authorization(tmp_path, authorization)
    second = build_fcpxml_remediation_plan_from_file(second_path, plan_request_without_fingerprint())

    assert first["status"] == "plan_ready"
    assert second["status"] == "plan_ready"
    assert first["source_authorization"]["source_authorization_sha256"] != second["source_authorization"]["source_authorization_sha256"]


@pytest.mark.parametrize(
    ("mutate", "field"),
    [
        (lambda authorization: authorization.update({"selected_remediation_id": "r999"}), "authorization.selected_remediation_id"),
        (lambda authorization: authorization.update({"selected_finding_id": "f999"}), "authorization.selected_finding_id"),
        (lambda authorization: authorization.update({"evidence_refs": ["ev_other"]}), "authorization.evidence_refs"),
        (lambda authorization: authorization.update({"related_entities": {"asset_ids": ["asset_999"], "check_ids": [], "error_codes": []}}), "authorization.related_entities"),
        (lambda authorization: authorization["source_selection"].update({"source_review_sha256": "different-review-sha"}), "authorization.source_selection.source_review_sha256"),
    ],
)
def test_plan_from_file_blocks_authorization_snapshot_identity_mismatch(tmp_path, mutate, field):
    authorization = load_authorization()
    mutate(authorization)
    authorization_path = write_authorization(tmp_path, authorization)

    plan = build_fcpxml_remediation_plan_from_file(authorization_path, plan_request_without_fingerprint())

    assert plan["status"] == "blocked"
    assert any(
        error["code"] == "authorization_snapshot_integrity_mismatch" and error["field"] == field
        for error in plan["validation_result"]["errors"]
    )


def test_plan_from_file_blocks_expanded_allowed_files_in_authorization_top_level(tmp_path):
    authorization = load_authorization()
    authorization["implementation_scope"]["allowed_files"].append("docs/unapproved_followup.md")
    authorization_path = write_authorization(tmp_path, authorization)

    plan = build_fcpxml_remediation_plan_from_file(authorization_path, plan_request_without_fingerprint())

    assert plan["status"] == "blocked"
    assert any(
        error["code"] == "authorization_snapshot_integrity_mismatch" and error["field"] == "authorization.implementation_scope.allowed_files"
        for error in plan["validation_result"]["errors"]
    )


def test_plan_from_file_blocks_deleted_prohibited_files_in_authorization_top_level(tmp_path):
    authorization = load_authorization()
    authorization["implementation_scope"]["prohibited_files"] = []
    authorization_path = write_authorization(tmp_path, authorization)

    plan = build_fcpxml_remediation_plan_from_file(authorization_path, plan_request_without_fingerprint())

    assert plan["status"] == "blocked"
    assert any(
        error["code"] == "authorization_snapshot_integrity_mismatch" and error["field"] == "authorization.implementation_scope.prohibited_files"
        for error in plan["validation_result"]["errors"]
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("verification_plan", {"commands": ["python -m pytest tests/test_other.py"], "required_results": ["changed"]}),
        ("rollback_plan", {"steps": ["Changed rollback step."], "requires_review_if_rollback_needed": False}),
    ],
)
def test_plan_from_file_blocks_changed_verification_or_rollback_plan(tmp_path, field, value):
    authorization = load_authorization()
    authorization[field] = value
    authorization_path = write_authorization(tmp_path, authorization)

    plan = build_fcpxml_remediation_plan_from_file(authorization_path, plan_request_without_fingerprint())

    assert plan["status"] == "blocked"
    assert any(
        error["code"] == "authorization_snapshot_integrity_mismatch" and error["field"] == f"authorization.{field}"
        for error in plan["validation_result"]["errors"]
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("implementation_execution_allowed", True),
        ("serializer_change_execution_allowed", True),
    ],
)
def test_plan_from_file_blocks_execution_flag_mismatch(tmp_path, field, value):
    authorization = load_authorization()
    authorization[field] = value
    authorization_path = write_authorization(tmp_path, authorization)

    plan = build_fcpxml_remediation_plan_from_file(authorization_path, plan_request_without_fingerprint())

    assert plan["status"] == "blocked"
    assert any(
        error["code"] == "authorization_snapshot_integrity_mismatch" and error["field"] == f"authorization.{field}"
        for error in plan["validation_result"]["errors"]
    )


def test_plan_payload_uses_verified_authorization_identity():
    plan = build_fcpxml_remediation_plan_from_file("output/sample_fcpxml_remediation_authorization.json", plan_request())

    snapshot = plan["immutable_plan_snapshot"]
    assert plan["status"] == "plan_ready"
    assert plan["plan_id"] == "plan_r001"
    assert plan["selected_remediation_id"] == "r001"
    assert plan["selected_finding_id"] == "f001"
    assert snapshot["authorization_snapshot_verified"] is True
    assert snapshot["verified_authorization_identity"]["selected_remediation_id"] == "r001"
    assert snapshot["selected_remediation_id"] == "r001"
    assert snapshot["selected_finding_id"] == "f001"
    assert snapshot["allowed_files"] == plan["allowed_files"]
    assert snapshot["prohibited_files"] == plan["prohibited_files"]
    assert plan["verification_plan"] == snapshot["verified_verification_plan"]
    assert plan["rollback_plan"] == snapshot["verified_rollback_plan"]
    assert snapshot["verified_verification_plan"]["commands"] == snapshot["authorization"]["immutable_authorization_snapshot"]["verification_commands"]
    assert snapshot["verified_rollback_plan"]["steps"] == snapshot["authorization"]["immutable_authorization_snapshot"]["rollback_steps"]


def test_plan_rejects_file_outside_authorized_scope():
    request = plan_request()
    request["planned_file_changes"].append(
        {
            "path": "docs/unapproved_followup.md",
            "action": "update_docs",
            "summary": "Attempt to plan an unapproved file.",
        }
    )

    plan = build_fcpxml_remediation_plan_from_file("output/sample_fcpxml_remediation_authorization.json", request)

    assert plan["status"] == "blocked"
    assert any(error["code"] == "planned_file_not_authorized" for error in plan["validation_result"]["errors"])


def test_plan_rejects_prohibited_file_even_if_requested():
    request = plan_request()
    request["planned_file_changes"].append(
        {
            "path": "output/sample_minimal.fcpxml",
            "action": "rewrite_output",
            "summary": "Attempt to rewrite FCPXML.",
        }
    )

    plan = build_fcpxml_remediation_plan_from_file("output/sample_fcpxml_remediation_authorization.json", request)

    assert plan["status"] == "blocked"
    assert any(error["code"] == "planned_file_not_authorized" for error in plan["validation_result"]["errors"])
    assert any(error["code"] == "planned_file_prohibited" for error in plan["validation_result"]["errors"])


def test_plan_requires_concrete_file_changes_and_review_controls():
    request = plan_request()
    request["planned_file_changes"] = []
    request["acceptance_criteria"] = []
    request["review_checklist"] = []
    request["rollback_checkpoints"] = []

    plan = build_fcpxml_remediation_plan_from_file("output/sample_fcpxml_remediation_authorization.json", request)

    assert plan["status"] == "blocked"
    assert any(error["code"] == "missing_planned_file_changes" for error in plan["validation_result"]["errors"])
    assert any(error["code"] == "missing_acceptance_criteria" for error in plan["validation_result"]["errors"])
    assert any(error["code"] == "missing_review_checklist" for error in plan["validation_result"]["errors"])
    assert any(error["code"] == "missing_rollback_checkpoints" for error in plan["validation_result"]["errors"])


def test_plan_blocks_media_or_editor_runtime_requirements():
    request = plan_request()
    request["acceptance_criteria"].append("Run ffmpeg before approval.")

    plan = build_fcpxml_remediation_plan_from_file("output/sample_fcpxml_remediation_authorization.json", request)

    assert plan["status"] == "blocked"
    assert any(error["code"] == "forbidden_plan_runtime_dependency" for error in plan["validation_result"]["errors"])


def test_plan_snapshot_is_immutable_after_authorization_changes(tmp_path):
    authorization = load_authorization()
    authorization_path = write_authorization(tmp_path, authorization)
    plan = build_fcpxml_remediation_plan_from_file(authorization_path, plan_request_without_fingerprint())

    authorization["selected_remediation_id"] = "changed"
    authorization["implementation_scope"]["allowed_files"].append("docs/new_file.md")

    assert plan["immutable_plan_snapshot"]["authorization"]["selected_remediation_id"] == "r001"
    assert "docs/new_file.md" not in plan["immutable_plan_snapshot"]["authorization"]["implementation_scope"]["allowed_files"]


def test_plan_write_outputs_json_only(tmp_path):
    plan = build_fcpxml_remediation_plan_from_file("output/sample_fcpxml_remediation_authorization.json", plan_request())
    output = tmp_path / "plan.json"

    result = write_fcpxml_remediation_plan(plan, output)

    assert output.exists()
    assert result["status"] == "written"
    assert result["plan_file_written"] is True
    assert result["code_changes_applied"] is False
    assert result["serializer_modified"] is False
    assert result["fcpxml_generated"] is False
    assert result["media_files_read"] is False
    assert result["editor_launched"] is False
    assert result["automatic_import_performed"] is False
    assert result["video_export_performed"] is False


def test_plan_module_does_not_import_editor_or_media_automation_libraries():
    forbidden = {"ffmpeg", "cv2", "moviepy", "subprocess", "pyautogui", "AppKit", "Quartz"}
    for path in (
        Path("modules/adapters/fcpxml_remediation_plan.py"),
        Path("app/plan_fcpxml_remediation.py"),
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not (imports & forbidden)
