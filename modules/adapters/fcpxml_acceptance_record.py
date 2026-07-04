"""Manual FCPXML import result capture for Module 11.

This module records human Final Cut Pro import results against a Module 10
acceptance protocol. It does not launch Final Cut Pro, automate import, read
media files, transcode, render, or export video.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FCPXML_ACCEPTANCE_RECORD_SCHEMA_VERSION = "1.0"

RESULT_STATUSES = {"passed", "failed", "blocked"}
CHECK_STATUSES = {"passed", "failed", "blocked"}
ASSET_IMPORT_STATES = {"online", "offline", "missing", "unverified"}


def build_fcpxml_acceptance_record(protocol: dict[str, Any], manual_result: dict[str, Any]) -> dict[str, Any]:
    """Build a structured manual acceptance record from protocol and result data."""
    validation_result = validate_fcpxml_acceptance_record_input(protocol, manual_result)
    protocol_artifacts = _safe_dict(protocol.get("source_artifacts"))
    result_artifacts = _safe_dict(manual_result.get("artifact_identifiers"))

    return {
        "schema_version": FCPXML_ACCEPTANCE_RECORD_SCHEMA_VERSION,
        "module": "Module 11",
        "name": "FCPXML Manual Import Result Capture / Acceptance Record",
        "status": "recorded" if validation_result["valid"] else "blocked",
        "source_protocol": {
            "schema_version": str(protocol.get("schema_version", "")),
            "fcpxml_path": str(protocol_artifacts.get("fcpxml_path", "")),
            "fcpxml_sha256": str(protocol_artifacts.get("fcpxml_sha256", "")),
            "source_design_path": str(protocol_artifacts.get("source_design_path", "")),
            "source_design_sha256": str(protocol_artifacts.get("source_design_sha256", "")),
            "git_commit": str(protocol_artifacts.get("git_commit", "")),
            "serializer_commit": str(protocol_artifacts.get("serializer_commit", "")),
            "acceptance_ready": bool(protocol_artifacts.get("acceptance_ready")),
        },
        "recorded_artifacts": {
            "fcpxml_path": str(result_artifacts.get("fcpxml_path", "")),
            "fcpxml_sha256": str(result_artifacts.get("fcpxml_sha256", "")),
            "source_design_path": str(result_artifacts.get("source_design_path", "")),
            "source_design_sha256": str(result_artifacts.get("source_design_sha256", "")),
            "git_commit": str(result_artifacts.get("git_commit", "")),
            "serializer_commit": str(result_artifacts.get("serializer_commit", "")),
        },
        "artifact_relationship_confirmation": _safe_dict(manual_result.get("artifact_relationship_confirmation")),
        "environment": {
            "tester": str(manual_result.get("tester", "")),
            "run_at": str(manual_result.get("run_at", "")),
            "final_cut_pro_version": str(manual_result.get("final_cut_pro_version", "")),
            "macos_version": str(manual_result.get("macos_version", "")),
            "library_name": str(manual_result.get("library_name", "")),
            "project_name": str(manual_result.get("project_name", "")),
        },
        "result": {
            "status": str(manual_result.get("status", "")),
            "import_result": str(manual_result.get("import_result", "")),
            "media_validation_result": str(manual_result.get("media_validation_result", "")),
            "imported": manual_result.get("imported"),
            "compatibility_result": str(manual_result.get("compatibility_result", "")),
            "summary": str(manual_result.get("summary", "")),
        },
        "asset_results": _safe_list(manual_result.get("asset_results")),
        "check_results": _safe_list(manual_result.get("checks")),
        "import_errors": _safe_list(manual_result.get("import_errors")),
        "evidence": _safe_list(manual_result.get("evidence")),
        "regression_samples": _safe_list(manual_result.get("regression_samples")),
        "validation_result": validation_result,
        "metadata": {
            "record_generated": True,
            "manual_result_capture_only": True,
            "media_files_read": False,
            "editor_launched": False,
            "automatic_import_performed": False,
            "video_export_performed": False,
        },
    }


def validate_fcpxml_acceptance_record_input(protocol: dict[str, Any], manual_result: dict[str, Any]) -> dict[str, Any]:
    """Validate manual result data without touching editor or media files."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    protocol_artifacts = _safe_dict(protocol.get("source_artifacts"))
    if protocol.get("schema_version") != "1.0":
        errors.append(_issue("invalid_protocol_schema", "protocol.schema_version", "Module 11 expects a Module 10 protocol."))
    if protocol.get("status") != "protocol_ready":
        errors.append(_issue("protocol_not_ready", "protocol.status", "Manual result capture requires a protocol_ready input."))
    if protocol_artifacts.get("acceptance_ready") is not True:
        errors.append(
            _issue(
                "protocol_not_acceptance_ready",
                "protocol.source_artifacts.acceptance_ready",
                "Manual PASS/FAIL capture requires a fully traceable Module 10 protocol.",
            )
        )

    _validate_artifact_identifiers(protocol_artifacts, _safe_dict(manual_result.get("artifact_identifiers")), errors)
    _validate_relationship_confirmation(manual_result, errors)
    _validate_environment(manual_result, errors)
    _validate_result_status(manual_result, errors)
    _validate_check_results(protocol, manual_result, errors)
    _validate_asset_results(protocol, manual_result, errors, warnings)
    _validate_evidence(manual_result, errors)
    _validate_boundary_flags(manual_result, errors)

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def write_fcpxml_acceptance_record(record: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Write a manual acceptance record JSON without touching editor or media."""
    if record.get("status") != "recorded":
        raise ValueError(f"Invalid Module 11 acceptance record: {record.get('validation_result', {})}")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "schema_version": FCPXML_ACCEPTANCE_RECORD_SCHEMA_VERSION,
        "status": "written",
        "output_path": str(output),
        "bytes_written": output.stat().st_size,
        "record_file_written": True,
        "media_files_read": False,
        "editor_launched": False,
        "automatic_import_performed": False,
        "video_export_performed": False,
    }


def _validate_artifact_identifiers(
    protocol_artifacts: dict[str, Any],
    result_artifacts: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    for field in ("fcpxml_path", "fcpxml_sha256", "source_design_path", "source_design_sha256", "git_commit", "serializer_commit"):
        if not result_artifacts.get(field):
            errors.append(_issue("missing_result_artifact_identifier", f"manual_result.artifact_identifiers.{field}", "Manual result is missing an artifact identifier."))
        elif str(result_artifacts.get(field)) != str(protocol_artifacts.get(field)):
            errors.append(_issue("artifact_identifier_mismatch", f"manual_result.artifact_identifiers.{field}", "Manual result artifact does not match the protocol."))


def _validate_relationship_confirmation(manual_result: dict[str, Any], errors: list[dict[str, str]]) -> None:
    confirmation = _safe_dict(manual_result.get("artifact_relationship_confirmation"))
    if confirmation.get("relationship_verified") is not True:
        errors.append(
            _issue(
                "artifact_relationship_not_confirmed",
                "manual_result.artifact_relationship_confirmation.relationship_verified",
                "Human review must confirm design, FCPXML, and serializer revision belong to the same output chain.",
            )
        )
    if not confirmation.get("confirmed_by") or not confirmation.get("confirmed_at"):
        errors.append(_issue("missing_relationship_confirmation_evidence", "manual_result.artifact_relationship_confirmation", "Relationship confirmation needs reviewer and timestamp."))


def _validate_environment(manual_result: dict[str, Any], errors: list[dict[str, str]]) -> None:
    for field in ("tester", "run_at", "final_cut_pro_version", "macos_version", "library_name", "project_name"):
        if not manual_result.get(field):
            errors.append(_issue("missing_environment_field", f"manual_result.{field}", "Manual result must record the test environment."))


def _validate_result_status(manual_result: dict[str, Any], errors: list[dict[str, str]]) -> None:
    status = str(manual_result.get("status", ""))
    import_result = str(manual_result.get("import_result", ""))
    media_validation_result = str(manual_result.get("media_validation_result", ""))
    compatibility_result = str(manual_result.get("compatibility_result", ""))
    if status not in RESULT_STATUSES:
        errors.append(_issue("invalid_result_status", "manual_result.status", "Manual result status must be passed, failed, or blocked."))
    if import_result not in RESULT_STATUSES:
        errors.append(_issue("invalid_import_result", "manual_result.import_result", "Import result must be passed, failed, or blocked."))
    if media_validation_result not in RESULT_STATUSES:
        errors.append(_issue("invalid_media_validation_result", "manual_result.media_validation_result", "Media validation result must be passed, failed, or blocked."))
    if compatibility_result not in RESULT_STATUSES:
        errors.append(_issue("invalid_compatibility_result", "manual_result.compatibility_result", "Compatibility result must be passed, failed, or blocked."))
    if compatibility_result == "passed" and (import_result != "passed" or media_validation_result != "passed"):
        errors.append(
            _issue(
                "compatibility_requires_import_and_media_pass",
                "manual_result.compatibility_result",
                "Compatibility can pass only when import_result and media_validation_result both pass.",
            )
        )
    if compatibility_result == "passed" and status != "passed":
        errors.append(
            _issue(
                "compatibility_pass_requires_pass_status",
                "manual_result.status",
                "Compatibility can pass only when the top-level status is passed.",
            )
        )
    if compatibility_result == "passed" and manual_result.get("imported") is not True:
        errors.append(
            _issue(
                "compatibility_pass_requires_import",
                "manual_result.imported",
                "Compatibility can pass only when imported=true.",
            )
        )
    if status == "passed" and compatibility_result != "passed":
        errors.append(_issue("pass_status_mismatch", "manual_result.compatibility_result", "A passed record must have compatibility_result passed."))
    if status == "passed" and (import_result != "passed" or media_validation_result != "passed"):
        errors.append(_issue("passed_result_requires_import_and_media_pass", "manual_result.status", "A passed record requires import and media validation to pass."))
    if status == "passed" and manual_result.get("imported") is not True:
        errors.append(_issue("passed_result_requires_import", "manual_result.imported", "A passed record requires imported=true."))
    if (status == "passed" or compatibility_result == "passed") and _has_blocker_import_error(manual_result):
        errors.append(_issue("passed_result_has_blocker_import_error", "manual_result.import_errors", "Passed compatibility cannot include blocker import errors."))


def _validate_check_results(protocol: dict[str, Any], manual_result: dict[str, Any], errors: list[dict[str, str]]) -> None:
    expected_ids = [str(item.get("id", "")) for item in _safe_list(protocol.get("checklist"))]
    checks = _safe_list(manual_result.get("checks"))
    check_ids = [str(item.get("id", "")) for item in checks]
    if sorted(check_ids) != sorted(expected_ids):
        errors.append(_issue("checklist_result_mismatch", "manual_result.checks", "Manual checks must match the protocol checklist ids."))
    if len(check_ids) != len(set(check_ids)):
        errors.append(_issue("duplicate_check_result", "manual_result.checks", "Manual check ids must be unique."))
    for index, check in enumerate(checks):
        prefix = f"manual_result.checks[{index}]"
        if check.get("status") not in CHECK_STATUSES:
            errors.append(_issue("invalid_check_status", f"{prefix}.status", "Check status must be passed, failed, or blocked."))
        if not check.get("actual_result"):
            errors.append(_issue("missing_check_actual_result", f"{prefix}.actual_result", "Each manual check needs an actual result."))
    if manual_result.get("status") == "passed" and any(check.get("status") != "passed" for check in checks):
        errors.append(_issue("passed_result_requires_passed_checks", "manual_result.checks", "A passed record requires every check to pass."))


def _validate_asset_results(
    protocol: dict[str, Any],
    manual_result: dict[str, Any],
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> None:
    expected_asset_ids = [str(item.get("asset_id", "")) for item in _safe_list(protocol.get("expected_assets"))]
    asset_results = _safe_list(manual_result.get("asset_results"))
    result_asset_ids = [str(item.get("asset_id", "")) for item in asset_results]
    if len(result_asset_ids) != len(set(result_asset_ids)):
        errors.append(_issue("duplicate_asset_validation", "manual_result.asset_results", "Each expected asset can have only one manual result."))
    if sorted(result_asset_ids) != sorted(expected_asset_ids):
        errors.append(_issue("asset_result_mismatch", "manual_result.asset_results", "Manual asset results must cover every expected asset."))
    missing_asset_ids = sorted(set(expected_asset_ids) - set(result_asset_ids))
    if missing_asset_ids:
        errors.append(_issue("missing_asset_validation", "manual_result.asset_results", f"Missing manual asset validation for: {', '.join(missing_asset_ids)}."))
    non_online_assets = []
    for index, asset in enumerate(asset_results):
        prefix = f"manual_result.asset_results[{index}]"
        if asset.get("import_state") not in ASSET_IMPORT_STATES:
            errors.append(_issue("invalid_asset_import_state", f"{prefix}.import_state", "Asset import state must be online, offline, missing, or unverified."))
        elif asset.get("import_state") != "online":
            non_online_assets.append(str(asset.get("asset_id", "")))
        if asset.get("import_state") == "unverified":
            warnings.append(_issue("asset_import_state_unverified", f"{prefix}.import_state", "Asset import state remains unverified."))
    if non_online_assets:
        if manual_result.get("status") == "passed" or manual_result.get("compatibility_result") == "passed":
            errors.append(_issue("media_assets_not_online", "manual_result.asset_results", f"Media assets are not online: {', '.join(non_online_assets)}."))
            errors.append(_issue("passed_result_requires_online_assets", "manual_result.asset_results", "A passed record requires every expected asset to be online."))
        else:
            warnings.append(_issue("media_assets_not_online", "manual_result.asset_results", f"Media assets are not online: {', '.join(non_online_assets)}."))


def _validate_evidence(manual_result: dict[str, Any], errors: list[dict[str, str]]) -> None:
    evidence = _safe_list(manual_result.get("evidence"))
    if not evidence:
        errors.append(_issue("missing_manual_evidence", "manual_result.evidence", "Manual result must include evidence entries."))
    for index, item in enumerate(evidence):
        prefix = f"manual_result.evidence[{index}]"
        for field in ("evidence_id", "evidence_type", "description", "path_or_reference"):
            if not item.get(field):
                errors.append(_issue("incomplete_evidence_entry", f"{prefix}.{field}", "Evidence entries require stable id, type, description, and path/reference."))
        for field in ("related_asset_ids", "related_check_ids", "related_error_codes"):
            if not isinstance(item.get(field), list):
                errors.append(_issue("incomplete_evidence_entry", f"{prefix}.{field}", "Evidence relation fields must be lists."))
    evidence_ids = [str(item.get("evidence_id", "")) for item in evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        errors.append(_issue("duplicate_evidence_id", "manual_result.evidence", "Evidence ids must be unique."))


def _validate_boundary_flags(manual_result: dict[str, Any], errors: list[dict[str, str]]) -> None:
    for field in ("media_files_read_by_code", "editor_launched_by_code", "automatic_import_performed", "video_export_performed"):
        if manual_result.get(field) is not False:
            errors.append(_issue("boundary_violation", f"manual_result.{field}", "Module 11 must not perform this action by code."))


def _has_blocker_import_error(manual_result: dict[str, Any]) -> bool:
    return any(str(error.get("severity", "")) == "blocker" for error in _safe_list(manual_result.get("import_errors")))


def _issue(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message}


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
