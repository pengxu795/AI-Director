"""FCPXML compatibility findings review for Module 12.

This module turns a Module 11 manual acceptance record into a findings and
remediation plan. It does not modify the serializer, launch Final Cut Pro,
automate import, read media, transcode, render, or export video.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FCPXML_COMPATIBILITY_REVIEW_SCHEMA_VERSION = "1.0"


def build_fcpxml_compatibility_review(acceptance_record: dict[str, Any]) -> dict[str, Any]:
    """Build a compatibility review and remediation plan from a Module 11 record."""
    validation_result = validate_fcpxml_compatibility_review_input(acceptance_record)
    findings = _findings_from_record(acceptance_record) if validation_result["valid"] else []
    remediation_plan = _remediation_plan(findings)

    return {
        "schema_version": FCPXML_COMPATIBILITY_REVIEW_SCHEMA_VERSION,
        "module": "Module 12",
        "name": "FCPXML Compatibility Findings Review / Remediation Plan",
        "status": "review_ready" if validation_result["valid"] else "blocked",
        "source_record": {
            "schema_version": str(acceptance_record.get("schema_version", "")),
            "status": str(acceptance_record.get("status", "")),
            "fcpxml_path": str(_safe_dict(acceptance_record.get("source_protocol")).get("fcpxml_path", "")),
            "fcpxml_sha256": str(_safe_dict(acceptance_record.get("source_protocol")).get("fcpxml_sha256", "")),
            "source_design_sha256": str(_safe_dict(acceptance_record.get("source_protocol")).get("source_design_sha256", "")),
            "git_commit": str(_safe_dict(acceptance_record.get("source_protocol")).get("git_commit", "")),
            "serializer_commit": str(_safe_dict(acceptance_record.get("source_protocol")).get("serializer_commit", "")),
        },
        "environment": _safe_dict(acceptance_record.get("environment")),
        "result_summary": _safe_dict(acceptance_record.get("result")),
        "findings": findings,
        "remediation_plan": remediation_plan,
        "regression_samples": _safe_list(acceptance_record.get("regression_samples")),
        "validation_result": validation_result,
        "metadata": {
            "review_generated": True,
            "serializer_modified": False,
            "media_files_read": False,
            "editor_launched": False,
            "automatic_import_performed": False,
            "video_export_performed": False,
        },
    }


def validate_fcpxml_compatibility_review_input(acceptance_record: dict[str, Any]) -> dict[str, Any]:
    """Validate a Module 11 record before generating compatibility findings."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if acceptance_record.get("schema_version") != "1.0":
        errors.append(_issue("invalid_acceptance_record_schema", "acceptance_record.schema_version", "Module 12 expects a Module 11 record."))
    if acceptance_record.get("status") != "recorded":
        errors.append(_issue("acceptance_record_not_recorded", "acceptance_record.status", "Compatibility review requires a recorded acceptance result."))
    validation = _safe_dict(acceptance_record.get("validation_result"))
    if validation.get("valid") is not True:
        errors.append(_issue("acceptance_record_invalid", "acceptance_record.validation_result.valid", "Compatibility review requires a valid acceptance record."))

    source_protocol = _safe_dict(acceptance_record.get("source_protocol"))
    for field in ("fcpxml_path", "fcpxml_sha256", "source_design_sha256", "git_commit", "serializer_commit"):
        if not source_protocol.get(field):
            errors.append(_issue("missing_source_record_artifact", f"acceptance_record.source_protocol.{field}", "Compatibility review requires traceable source artifacts."))

    metadata = _safe_dict(acceptance_record.get("metadata"))
    for field in ("media_files_read", "editor_launched", "automatic_import_performed", "video_export_performed"):
        if metadata.get(field) is not False:
            errors.append(_issue("boundary_violation", f"acceptance_record.metadata.{field}", "Module 12 must not depend on automated editor or media processing."))

    if not _safe_list(acceptance_record.get("evidence")):
        warnings.append(_issue("missing_review_evidence", "acceptance_record.evidence", "No evidence entries were attached to this record."))

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def write_fcpxml_compatibility_review(review: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Write a compatibility review JSON without applying remediation."""
    if review.get("status") != "review_ready":
        raise ValueError(f"Invalid Module 12 compatibility review: {review.get('validation_result', {})}")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "schema_version": FCPXML_COMPATIBILITY_REVIEW_SCHEMA_VERSION,
        "status": "written",
        "output_path": str(output),
        "bytes_written": output.stat().st_size,
        "review_file_written": True,
        "serializer_modified": False,
        "media_files_read": False,
        "editor_launched": False,
        "automatic_import_performed": False,
        "video_export_performed": False,
    }


def _findings_from_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    for asset in _safe_list(record.get("asset_results")):
        if asset.get("import_state") != "online":
            findings.append(
                _finding(
                    "media_not_online",
                    "blocker",
                    "media",
                    f"Asset {asset.get('asset_id', '')} was {asset.get('import_state', '')}.",
                    str(asset.get("notes", "")),
                    [str(asset.get("asset_id", ""))],
                )
            )
    for check in _safe_list(record.get("check_results")):
        if check.get("status") != "passed":
            findings.append(
                _finding(
                    "manual_check_not_passed",
                    _severity_for_check(check),
                    "manual_check",
                    f"Checklist item {check.get('id', '')} was {check.get('status', '')}.",
                    str(check.get("actual_result", "")),
                    [str(check.get("id", ""))],
                )
            )
    for error in _safe_list(record.get("import_errors")):
        findings.append(
            _finding(
                str(error.get("code", "import_error")),
                str(error.get("severity", "warning")),
                "import_error",
                str(error.get("message", "")),
                str(error.get("message", "")),
                [],
            )
        )
    for warning in _safe_list(_safe_dict(record.get("validation_result")).get("warnings")):
        findings.append(
            _finding(
                str(warning.get("code", "validation_warning")),
                "warning",
                "record_warning",
                str(warning.get("message", "")),
                str(warning.get("field", "")),
                [],
            )
        )
    if not findings and _safe_dict(record.get("result")).get("compatibility_result") == "passed":
        findings.append(
            _finding(
                "manual_acceptance_passed",
                "info",
                "compatibility",
                "Manual acceptance record passed with no findings.",
                "No remediation required.",
                [],
            )
        )
    return [_with_id(index, finding) for index, finding in enumerate(findings, start=1)]


def _remediation_plan(findings: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for index, finding in enumerate(findings, start=1):
        if finding["code"] == "manual_acceptance_passed":
            continue
        action = _recommended_action(finding)
        items.append(
            {
                "id": f"r{index:03d}",
                "finding_id": finding["id"],
                "priority": _priority_for_severity(finding["severity"]),
                "action": action,
                "owner": "human_review",
                "serializer_change_allowed": False,
                "requires_review_before_implementation": True,
                "status": "proposed",
            }
        )
    return {
        "status": "no_action_needed" if not items else "proposed",
        "items": items,
        "serializer_changes_applied": False,
        "next_gate": "Review findings before changing serializer or adding editor automation.",
    }


def _finding(code: str, severity: str, category: str, summary: str, reproduction: str, evidence_refs: list[str]) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "category": category,
        "summary": summary,
        "reproduction": reproduction,
        "evidence_refs": evidence_refs,
        "status": "open" if severity != "info" else "informational",
    }


def _with_id(index: int, finding: dict[str, Any]) -> dict[str, Any]:
    return {"id": f"f{index:03d}", **finding}


def _severity_for_check(check: dict[str, Any]) -> str:
    return "blocker" if check.get("status") == "blocked" else "major"


def _priority_for_severity(severity: str) -> str:
    return {
        "blocker": "P0",
        "major": "P1",
        "warning": "P2",
        "minor": "P2",
    }.get(severity, "P3")


def _recommended_action(finding: dict[str, Any]) -> str:
    if finding["category"] == "media":
        return "Repeat manual import with bound online media before assessing source ranges or edit usability."
    if finding["category"] == "manual_check":
        return "Inspect the failed checklist evidence and decide whether a serializer fix, protocol update, or sample correction is needed."
    if finding["category"] == "import_error":
        return "Triage the importer error against the exact FCPXML/design fingerprints before changing serializer output."
    return "Review this finding and decide whether remediation is needed."


def _issue(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message}


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
