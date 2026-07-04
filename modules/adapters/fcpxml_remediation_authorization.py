"""Remediation authorization and implementation scope contract for Module 14.

This module turns a Module 13 remediation selection into an auditable
authorization contract. It does not apply fixes, modify serializers, launch
Final Cut Pro, automate import, read media, transcode, render, or export video.
"""

from __future__ import annotations

import copy
import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any


FCPXML_REMEDIATION_AUTHORIZATION_SCHEMA_VERSION = "1.0"

SERIALIZER_SCOPE_PATTERNS = (
    "modules/adapters/*serializer*.py",
    "modules/adapters/*fcpxml*export*.py",
    "tests/*serializer*.py",
    "tests/*fcpxml*export*.py",
    "docs/*serializer*.md",
    "docs/*fcpxml*export*.md",
    "app/*export_fcpxml*.py",
    "output/*.fcpxml",
)

FCPXML_IMPLEMENTATION_SCOPE_PATTERNS = (
    "modules/adapters/*fcpxml*.py",
    "tests/*fcpxml*.py",
    "docs/*fcpxml*.md",
    "app/*fcpxml*.py",
    "app/*final_cut*.py",
    "output/*.fcpxml",
)

HUMAN_REVIEW_ALLOWED_PATTERNS = (
    "docs/fcpxml_acceptance_*.md",
    "docs/fcpxml_compatibility_*.md",
    "output/*acceptance*.json",
    "output/*compatibility_review*.json",
    "output/*manual_follow_up*.json",
    "CHANGELOG.md",
    "PROJECT_STATE.md",
    "prompts/*human_review*.md",
)


def build_fcpxml_remediation_authorization_from_file(selection_path: str | Path, authorization_request: dict[str, Any]) -> dict[str, Any]:
    """Build an authorization contract from a selected remediation JSON file."""
    path = Path(selection_path)
    if not path.exists():
        return _blocked_authorization(
            authorization_request,
            [_issue("remediation_selection_file_not_found", "remediation_selection_json", "Module 14 requires an existing Module 13 selection file.")],
        )
    selection_text = path.read_text(encoding="utf-8")
    request = {
        **authorization_request,
        "source_selection_artifact": str(path),
        "source_selection_sha256": hashlib.sha256(selection_text.encode("utf-8")).hexdigest(),
    }
    return build_fcpxml_remediation_authorization(json.loads(selection_text), request)


def build_fcpxml_remediation_authorization(selection: dict[str, Any], authorization_request: dict[str, Any]) -> dict[str, Any]:
    """Build a controlled implementation-scope authorization contract."""
    validation_result = validate_fcpxml_remediation_authorization_input(selection, authorization_request)
    payload = _authorization_payload(selection, authorization_request) if validation_result["valid"] else {}

    return {
        "schema_version": FCPXML_REMEDIATION_AUTHORIZATION_SCHEMA_VERSION,
        "module": "Module 14",
        "name": "Remediation Authorization / Implementation Scope Contract",
        "authorization_id": payload.get("authorization_id", ""),
        "status": "authorization_ready" if validation_result["valid"] else "blocked",
        **payload,
        "validation_result": validation_result,
        "metadata": {
            "authorization_recorded": validation_result["valid"],
            "code_changes_applied": False,
            "serializer_modified": False,
            "fcpxml_generated": False,
            "media_files_read": False,
            "editor_launched": False,
            "automatic_import_performed": False,
            "video_export_performed": False,
        },
    }


def validate_fcpxml_remediation_authorization_input(selection: dict[str, Any], authorization_request: dict[str, Any]) -> dict[str, Any]:
    """Validate that a Module 13 selection can be scoped for a later fix."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if selection.get("schema_version") != "1.0":
        errors.append(_issue("invalid_selection_schema", "selection.schema_version", "Module 14 expects a Module 13 remediation selection."))
    if selection.get("status") != "selected":
        errors.append(_issue("selection_not_selected", "selection.status", "Module 14 requires a selected Module 13 remediation."))
    if selection.get("execution_allowed") is not False:
        errors.append(_issue("selection_execution_flag_invalid", "selection.execution_allowed", "Module 13 selection must not already allow execution."))
    if selection.get("serializer_change_allowed") is not False:
        errors.append(_issue("selection_serializer_flag_invalid", "selection.serializer_change_allowed", "Module 13 selection must not already allow serializer changes."))
    if selection.get("requires_module_14_approval") is not True:
        errors.append(_issue("selection_missing_module_14_gate", "selection.requires_module_14_approval", "Selection must require Module 14 approval."))
    if not _safe_dict(selection.get("immutable_selection_snapshot")):
        errors.append(_issue("missing_immutable_selection_snapshot", "selection.immutable_selection_snapshot", "Authorization requires the immutable Module 13 selection snapshot."))

    metadata = _safe_dict(selection.get("metadata"))
    for field in ("serializer_modified", "media_files_read", "editor_launched", "automatic_import_performed", "video_export_performed"):
        if metadata.get(field) is not False:
            errors.append(_issue("boundary_violation", f"selection.metadata.{field}", "Module 14 cannot authorize from a boundary-violating selection."))

    for field in ("authorized_by", "authorized_at", "authorization_rationale"):
        if not authorization_request.get(field):
            errors.append(_issue("missing_authorization_metadata", f"authorization_request.{field}", "Authorization requires approver, timestamp, and rationale."))
    if not authorization_request.get("source_selection_artifact") or not authorization_request.get("source_selection_sha256"):
        errors.append(_issue("missing_source_selection_fingerprint", "authorization_request.source_selection_sha256", "Authorization must freeze the source selection artifact path and SHA-256."))

    allowed_files = _safe_string_list(authorization_request.get("allowed_files"))
    prohibited_files = _safe_string_list(authorization_request.get("prohibited_files"))
    verification_commands = _safe_string_list(authorization_request.get("verification_commands"))
    rollback_steps = _safe_string_list(authorization_request.get("rollback_steps"))
    selected_remediation = _selected_remediation(selection)
    owner = str(selected_remediation.get("owner", ""))
    serializer_change_allowed = selected_remediation.get("serializer_change_allowed") is True
    if not allowed_files:
        errors.append(_issue("missing_allowed_files", "authorization_request.allowed_files", "Authorization must list future allowed file paths."))
    if not prohibited_files:
        errors.append(_issue("missing_prohibited_files", "authorization_request.prohibited_files", "Authorization must list prohibited paths."))
    if set(allowed_files) & set(prohibited_files):
        errors.append(_issue("allowed_file_also_prohibited", "authorization_request.allowed_files", "Allowed and prohibited paths must not overlap."))
    if not serializer_change_allowed:
        for path in allowed_files:
            if _matches_any(path, SERIALIZER_SCOPE_PATTERNS):
                errors.append(
                    _issue(
                        "serializer_scope_not_authorized_for_selected_remediation",
                        "authorization_request.allowed_files",
                        f"Selected remediation does not authorize serializer or FCPXML generation scope: {path}.",
                    )
                )
            if _matches_any(path, FCPXML_IMPLEMENTATION_SCOPE_PATTERNS) and not _is_human_review_allowed_path(path):
                errors.append(
                    _issue(
                        "fcpxml_implementation_scope_not_authorized",
                        "authorization_request.allowed_files",
                        f"Selected remediation does not authorize FCPXML implementation, generation, or writing scope: {path}.",
                    )
                )
    if owner == "human_review":
        for path in allowed_files:
            if not _matches_any(path, HUMAN_REVIEW_ALLOWED_PATTERNS):
                errors.append(
                    _issue(
                        "human_review_scope_path_not_allowed",
                        "authorization_request.allowed_files",
                        f"Human-review remediation can authorize only review, protocol, record, manual follow-up, or documentation paths: {path}.",
                    )
                )
    if not verification_commands:
        errors.append(_issue("missing_verification_commands", "authorization_request.verification_commands", "Authorization must define verification commands."))
    if not rollback_steps:
        errors.append(_issue("missing_rollback_steps", "authorization_request.rollback_steps", "Authorization must define rollback steps."))

    forbidden_runtime_terms = ("ffmpeg", "moviepy", "opencv", "cv2", "Final Cut Pro", "osascript")
    for index, command in enumerate(verification_commands):
        if any(term.lower() in command.lower() for term in forbidden_runtime_terms):
            errors.append(_issue("forbidden_verification_command", f"authorization_request.verification_commands[{index}]", "Module 14 verification cannot invoke editor automation or media tooling."))

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def write_fcpxml_remediation_authorization(authorization: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Write a remediation authorization contract without applying any fix."""
    if authorization.get("status") != "authorization_ready":
        raise ValueError(f"Invalid Module 14 remediation authorization: {authorization.get('validation_result', {})}")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(authorization, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "schema_version": FCPXML_REMEDIATION_AUTHORIZATION_SCHEMA_VERSION,
        "status": "written",
        "output_path": str(output),
        "bytes_written": output.stat().st_size,
        "authorization_file_written": True,
        "code_changes_applied": False,
        "serializer_modified": False,
        "fcpxml_generated": False,
        "media_files_read": False,
        "editor_launched": False,
        "automatic_import_performed": False,
        "video_export_performed": False,
    }


def _authorization_payload(selection: dict[str, Any], authorization_request: dict[str, Any]) -> dict[str, Any]:
    authorization_id = f"auth_{selection.get('selected_remediation_id', 'unknown')}"
    allowed_files = _safe_string_list(authorization_request.get("allowed_files"))
    prohibited_files = _safe_string_list(authorization_request.get("prohibited_files"))
    verification_commands = _safe_string_list(authorization_request.get("verification_commands"))
    rollback_steps = _safe_string_list(authorization_request.get("rollback_steps"))
    selected_remediation = _selected_remediation(selection)
    manual_follow_up_required = str(selected_remediation.get("owner", "")) == "human_review"
    return {
        "source_selection": {
            "selection_id": str(selection.get("selection_id", "")),
            "selected_remediation_id": str(selection.get("selected_remediation_id", "")),
            "selected_finding_id": str(selection.get("selected_finding_id", "")),
            "source_selection_artifact": str(authorization_request.get("source_selection_artifact", "")),
            "source_selection_sha256": str(authorization_request.get("source_selection_sha256", "")),
            "source_review_sha256": str(selection.get("source_review_sha256", "")),
            "source_review_git_commit": str(selection.get("source_review_git_commit", "")),
        },
        "authorization_id": authorization_id,
        "authorized_by": str(authorization_request.get("authorized_by", "")),
        "authorized_at": str(authorization_request.get("authorized_at", "")),
        "authorization_rationale": str(authorization_request.get("authorization_rationale", "")),
        "selected_remediation_id": str(selection.get("selected_remediation_id", "")),
        "selected_finding_id": str(selection.get("selected_finding_id", "")),
        "evidence_refs": _safe_string_list(selection.get("evidence_refs")),
        "related_entities": _safe_dict(selection.get("related_entities")),
        "implementation_scope": {
            "allowed_files": allowed_files,
            "prohibited_files": prohibited_files,
            "manual_follow_up_required": manual_follow_up_required,
            "allowed_operations": ["edit_existing_files_within_scope", "add_tests_within_scope", "update_docs_within_scope"],
            "prohibited_operations": [
                "modify_files_outside_allowed_scope",
                "launch_editor",
                "automatic_import",
                "read_or_probe_media",
                "transcode_render_or_export_video",
            ],
        },
        "verification_plan": {
            "commands": verification_commands,
            "required_results": ["all_commands_pass", "git_diff_limited_to_allowed_files", "no_boundary_violations"],
        },
        "rollback_plan": {
            "steps": rollback_steps,
            "requires_review_if_rollback_needed": True,
        },
        "implementation_execution_allowed": False,
        "serializer_change_execution_allowed": False,
        "manual_follow_up_required": manual_follow_up_required,
        "requires_module_15_implementation_review": True,
        "immutable_authorization_snapshot": {
            "selection": copy.deepcopy(selection),
            "allowed_files": copy.deepcopy(allowed_files),
            "prohibited_files": copy.deepcopy(prohibited_files),
            "verification_commands": copy.deepcopy(verification_commands),
            "rollback_steps": copy.deepcopy(rollback_steps),
            "authorization_rationale": str(authorization_request.get("authorization_rationale", "")),
            "source_selection_sha256": str(authorization_request.get("source_selection_sha256", "")),
        },
}


def _blocked_authorization(authorization_request: dict[str, Any], errors: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema_version": FCPXML_REMEDIATION_AUTHORIZATION_SCHEMA_VERSION,
        "module": "Module 14",
        "name": "Remediation Authorization / Implementation Scope Contract",
        "authorization_id": "",
        "status": "blocked",
        "authorized_by": str(authorization_request.get("authorized_by", "")),
        "authorized_at": str(authorization_request.get("authorized_at", "")),
        "authorization_rationale": str(authorization_request.get("authorization_rationale", "")),
        "implementation_execution_allowed": False,
        "serializer_change_execution_allowed": False,
        "requires_module_15_implementation_review": True,
        "immutable_authorization_snapshot": {},
        "validation_result": {"valid": False, "errors": errors, "warnings": []},
        "metadata": {
            "authorization_recorded": False,
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


def _selected_remediation(selection: dict[str, Any]) -> dict[str, Any]:
    snapshot = _safe_dict(selection.get("immutable_selection_snapshot"))
    return _safe_dict(snapshot.get("remediation"))


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _is_human_review_allowed_path(path: str) -> bool:
    return _matches_any(path, HUMAN_REVIEW_ALLOWED_PATTERNS)


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]
