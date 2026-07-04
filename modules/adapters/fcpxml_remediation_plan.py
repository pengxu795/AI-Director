"""Authorized remediation implementation plan contract for Module 15.

This module turns a Module 14 authorization into a reviewed implementation
plan. It does not implement the remediation, modify serializers, generate
FCPXML, launch Final Cut Pro, automate import, read media, transcode, render,
or export video.
"""

from __future__ import annotations

import copy
import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any


FCPXML_REMEDIATION_PLAN_SCHEMA_VERSION = "1.0"


def build_fcpxml_remediation_plan_from_file(authorization_path: str | Path, plan_request: dict[str, Any]) -> dict[str, Any]:
    """Build a Module 15 implementation plan from a Module 14 authorization file."""
    path = Path(authorization_path)
    if not path.exists():
        return _blocked_plan(
            plan_request,
            [_issue("fcpxml_remediation_authorization_file_not_found", "authorization_json", "Module 15 requires an existing Module 14 authorization file.")],
        )
    authorization_bytes = path.read_bytes()
    source_authorization_artifact = str(path)
    source_authorization_sha256 = hashlib.sha256(authorization_bytes).hexdigest()
    requested_artifact = plan_request.get("source_authorization_artifact")
    requested_sha256 = plan_request.get("source_authorization_sha256")
    if (requested_artifact and str(requested_artifact) != source_authorization_artifact) or (requested_sha256 and str(requested_sha256) != source_authorization_sha256):
        return _blocked_plan(
            plan_request,
            [_issue("source_authorization_fingerprint_mismatch", "plan_request.source_authorization_sha256", "Caller-provided authorization path or SHA-256 does not match the file read by Module 15.")],
        )
    request = {
        **plan_request,
        "source_authorization_artifact": source_authorization_artifact,
        "source_authorization_sha256": source_authorization_sha256,
        "_source_authorization_verified": True,
    }
    return build_fcpxml_remediation_plan(json.loads(authorization_bytes.decode("utf-8")), request)


def build_fcpxml_remediation_plan(authorization: dict[str, Any], plan_request: dict[str, Any]) -> dict[str, Any]:
    """Build a non-executable remediation implementation plan."""
    validation_result = validate_fcpxml_remediation_plan_input(authorization, plan_request)
    payload = _plan_payload(authorization, plan_request) if validation_result["valid"] else {}

    return {
        "schema_version": FCPXML_REMEDIATION_PLAN_SCHEMA_VERSION,
        "module": "Module 15",
        "name": "Authorized Remediation Implementation Plan",
        "plan_id": payload.get("plan_id", ""),
        "status": "plan_ready" if validation_result["valid"] else "blocked",
        **payload,
        "validation_result": validation_result,
        "metadata": {
            "plan_recorded": validation_result["valid"],
            "code_changes_applied": False,
            "serializer_modified": False,
            "fcpxml_generated": False,
            "media_files_read": False,
            "editor_launched": False,
            "automatic_import_performed": False,
            "video_export_performed": False,
        },
    }


def validate_fcpxml_remediation_plan_input(authorization: dict[str, Any], plan_request: dict[str, Any]) -> dict[str, Any]:
    """Validate that an authorization can become a reviewed implementation plan."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if authorization.get("schema_version") != "1.0":
        errors.append(_issue("invalid_authorization_schema", "authorization.schema_version", "Module 15 expects a Module 14 authorization."))
    if authorization.get("status") != "authorization_ready":
        errors.append(_issue("authorization_not_ready", "authorization.status", "Module 15 requires an authorization_ready Module 14 contract."))
    validation_result = _safe_dict(authorization.get("validation_result"))
    if validation_result.get("valid") is not True:
        errors.append(_issue("authorization_validation_not_valid", "authorization.validation_result.valid", "Module 15 requires a valid Module 14 authorization."))
    if authorization.get("implementation_execution_allowed") is not False:
        errors.append(_issue("authorization_execution_flag_invalid", "authorization.implementation_execution_allowed", "Module 15 cannot plan from an already executable authorization."))
    if authorization.get("serializer_change_execution_allowed") is not False:
        errors.append(_issue("authorization_serializer_flag_invalid", "authorization.serializer_change_execution_allowed", "Module 15 cannot plan from an already executable serializer authorization."))
    if authorization.get("requires_module_15_implementation_review") is not True:
        errors.append(_issue("authorization_missing_module_15_gate", "authorization.requires_module_15_implementation_review", "Authorization must require Module 15 review before implementation."))

    snapshot = _safe_dict(authorization.get("immutable_authorization_snapshot"))
    if not snapshot:
        errors.append(_issue("missing_immutable_authorization_snapshot", "authorization.immutable_authorization_snapshot", "Module 15 requires the immutable Module 14 authorization snapshot."))
    if snapshot and snapshot.get("selection_snapshot_verified") is not True:
        errors.append(_issue("authorization_selection_snapshot_not_verified", "authorization.immutable_authorization_snapshot.selection_snapshot_verified", "Module 15 requires a verified selection snapshot identity."))

    metadata = _safe_dict(authorization.get("metadata"))
    for field in ("code_changes_applied", "serializer_modified", "fcpxml_generated", "media_files_read", "editor_launched", "automatic_import_performed", "video_export_performed"):
        if metadata.get(field) is not False:
            errors.append(_issue("boundary_violation", f"authorization.metadata.{field}", "Module 15 cannot plan from a boundary-violating authorization."))

    for field in ("planned_by", "planned_at", "planning_rationale"):
        if not plan_request.get(field):
            errors.append(_issue("missing_plan_metadata", f"plan_request.{field}", "Module 15 plan requires planner, timestamp, and rationale."))
    if not plan_request.get("source_authorization_artifact") or not plan_request.get("source_authorization_sha256"):
        errors.append(_issue("missing_source_authorization_fingerprint", "plan_request.source_authorization_sha256", "Module 15 must freeze the source authorization artifact path and SHA-256."))
    if plan_request.get("_source_authorization_verified") is not True:
        errors.append(_issue("source_authorization_artifact_not_verified", "plan_request.source_authorization_artifact", "Writable Module 15 plans must be generated from a verified authorization file."))

    planned_file_changes = _safe_plan_changes(plan_request.get("planned_file_changes"))
    acceptance_criteria = _safe_string_list(plan_request.get("acceptance_criteria"))
    review_checklist = _safe_string_list(plan_request.get("review_checklist"))
    rollback_checkpoints = _safe_string_list(plan_request.get("rollback_checkpoints"))
    if not planned_file_changes:
        errors.append(_issue("missing_planned_file_changes", "plan_request.planned_file_changes", "Module 15 must list concrete future file changes."))
    if not acceptance_criteria:
        errors.append(_issue("missing_acceptance_criteria", "plan_request.acceptance_criteria", "Module 15 must define acceptance criteria."))
    if not review_checklist:
        errors.append(_issue("missing_review_checklist", "plan_request.review_checklist", "Module 15 must define review checklist items."))
    if not rollback_checkpoints:
        errors.append(_issue("missing_rollback_checkpoints", "plan_request.rollback_checkpoints", "Module 15 must define rollback checkpoints."))

    allowed_files = _safe_string_list(_safe_dict(authorization.get("implementation_scope")).get("allowed_files"))
    prohibited_files = _safe_string_list(_safe_dict(authorization.get("implementation_scope")).get("prohibited_files"))
    for index, change in enumerate(planned_file_changes):
        path = str(change.get("path", ""))
        if not path:
            errors.append(_issue("missing_planned_file_path", f"plan_request.planned_file_changes[{index}].path", "Every planned change needs a path."))
            continue
        if not _path_allowed(path, allowed_files):
            errors.append(_issue("planned_file_not_authorized", f"plan_request.planned_file_changes[{index}].path", f"Planned file is outside Module 14 allowed_files: {path}."))
        if _path_prohibited(path, prohibited_files):
            errors.append(_issue("planned_file_prohibited", f"plan_request.planned_file_changes[{index}].path", f"Planned file is prohibited by Module 14 authorization: {path}."))
        if not change.get("summary") or not change.get("action"):
            errors.append(_issue("incomplete_planned_file_change", f"plan_request.planned_file_changes[{index}]", "Every planned change needs action and summary."))

    forbidden_runtime_terms = ("ffmpeg", "moviepy", "opencv", "cv2", "Final Cut Pro", "osascript")
    for index, item in enumerate(acceptance_criteria + review_checklist):
        if any(term.lower() in item.lower() for term in forbidden_runtime_terms):
            errors.append(_issue("forbidden_plan_runtime_dependency", f"plan_request.review_or_acceptance[{index}]", "Module 15 cannot require editor automation or media tooling."))

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def write_fcpxml_remediation_plan(plan: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Write a Module 15 plan without applying any remediation."""
    if plan.get("status") != "plan_ready":
        raise ValueError(f"Invalid Module 15 remediation plan: {plan.get('validation_result', {})}")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "schema_version": FCPXML_REMEDIATION_PLAN_SCHEMA_VERSION,
        "status": "written",
        "output_path": str(output),
        "bytes_written": output.stat().st_size,
        "plan_file_written": True,
        "code_changes_applied": False,
        "serializer_modified": False,
        "fcpxml_generated": False,
        "media_files_read": False,
        "editor_launched": False,
        "automatic_import_performed": False,
        "video_export_performed": False,
    }


def _plan_payload(authorization: dict[str, Any], plan_request: dict[str, Any]) -> dict[str, Any]:
    selected_remediation_id = str(authorization.get("selected_remediation_id", ""))
    plan_id = f"plan_{selected_remediation_id or 'unknown'}"
    planned_file_changes = _safe_plan_changes(plan_request.get("planned_file_changes"))
    acceptance_criteria = _safe_string_list(plan_request.get("acceptance_criteria"))
    review_checklist = _safe_string_list(plan_request.get("review_checklist"))
    rollback_checkpoints = _safe_string_list(plan_request.get("rollback_checkpoints"))
    implementation_scope = _safe_dict(authorization.get("implementation_scope"))
    return {
        "plan_id": plan_id,
        "source_authorization": {
            "authorization_id": str(authorization.get("authorization_id", "")),
            "selected_remediation_id": selected_remediation_id,
            "selected_finding_id": str(authorization.get("selected_finding_id", "")),
            "source_authorization_artifact": str(plan_request.get("source_authorization_artifact", "")),
            "source_authorization_sha256": str(plan_request.get("source_authorization_sha256", "")),
            "source_selection_sha256": str(_safe_dict(authorization.get("source_selection")).get("source_selection_sha256", "")),
            "source_review_sha256": str(_safe_dict(authorization.get("source_selection")).get("source_review_sha256", "")),
        },
        "planned_by": str(plan_request.get("planned_by", "")),
        "planned_at": str(plan_request.get("planned_at", "")),
        "planning_rationale": str(plan_request.get("planning_rationale", "")),
        "selected_remediation_id": selected_remediation_id,
        "selected_finding_id": str(authorization.get("selected_finding_id", "")),
        "evidence_refs": _safe_string_list(authorization.get("evidence_refs")),
        "related_entities": copy.deepcopy(_safe_dict(authorization.get("related_entities"))),
        "planned_file_changes": copy.deepcopy(planned_file_changes),
        "allowed_files": copy.deepcopy(_safe_string_list(implementation_scope.get("allowed_files"))),
        "prohibited_files": copy.deepcopy(_safe_string_list(implementation_scope.get("prohibited_files"))),
        "verification_plan": copy.deepcopy(_safe_dict(authorization.get("verification_plan"))),
        "rollback_plan": copy.deepcopy(_safe_dict(authorization.get("rollback_plan"))),
        "acceptance_criteria": acceptance_criteria,
        "review_checklist": review_checklist,
        "rollback_checkpoints": rollback_checkpoints,
        "implementation_execution_allowed": False,
        "serializer_change_execution_allowed": False,
        "requires_module_16_approval": True,
        "immutable_plan_snapshot": {
            "authorization": copy.deepcopy(authorization),
            "source_authorization_sha256": str(plan_request.get("source_authorization_sha256", "")),
            "selected_remediation_id": selected_remediation_id,
            "selected_finding_id": str(authorization.get("selected_finding_id", "")),
            "planned_file_changes": copy.deepcopy(planned_file_changes),
            "acceptance_criteria": copy.deepcopy(acceptance_criteria),
            "review_checklist": copy.deepcopy(review_checklist),
            "rollback_checkpoints": copy.deepcopy(rollback_checkpoints),
            "planning_rationale": str(plan_request.get("planning_rationale", "")),
        },
    }


def _blocked_plan(plan_request: dict[str, Any], errors: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema_version": FCPXML_REMEDIATION_PLAN_SCHEMA_VERSION,
        "module": "Module 15",
        "name": "Authorized Remediation Implementation Plan",
        "plan_id": "",
        "status": "blocked",
        "planned_by": str(plan_request.get("planned_by", "")),
        "planned_at": str(plan_request.get("planned_at", "")),
        "planning_rationale": str(plan_request.get("planning_rationale", "")),
        "implementation_execution_allowed": False,
        "serializer_change_execution_allowed": False,
        "requires_module_16_approval": True,
        "immutable_plan_snapshot": {},
        "validation_result": {"valid": False, "errors": errors, "warnings": []},
        "metadata": {
            "plan_recorded": False,
            "code_changes_applied": False,
            "serializer_modified": False,
            "fcpxml_generated": False,
            "media_files_read": False,
            "editor_launched": False,
            "automatic_import_performed": False,
            "video_export_performed": False,
        },
    }


def _issue(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message}


def _path_allowed(path: str, allowed_files: list[str]) -> bool:
    return any(path == allowed or fnmatch.fnmatch(path, allowed) for allowed in allowed_files)


def _path_prohibited(path: str, prohibited_files: list[str]) -> bool:
    for prohibited in prohibited_files:
        if fnmatch.fnmatch(path, prohibited):
            return True
        if prohibited.endswith("/") and path.startswith(prohibited):
            return True
        if path == prohibited:
            return True
    return False


def _safe_plan_changes(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [copy.deepcopy(item) for item in value if isinstance(item, dict)]


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]
