"""Evidence-backed remediation selection for Module 13.

This module records a human-selected remediation item from a Module 12
compatibility review. It does not modify serializers, launch Final Cut Pro,
automate import, read media, transcode, render, or export video.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


FCPXML_REMEDIATION_SELECTION_SCHEMA_VERSION = "1.0"


def build_fcpxml_remediation_selection(review: dict[str, Any], selection_request: dict[str, Any]) -> dict[str, Any]:
    """Build a controlled remediation task contract from one selected item."""
    validation_result = validate_fcpxml_remediation_selection_input(review, selection_request)
    selected = _selected_payload(review, selection_request) if validation_result["valid"] else {}

    return {
        "schema_version": FCPXML_REMEDIATION_SELECTION_SCHEMA_VERSION,
        "module": "Module 13",
        "name": "Evidence-Backed Remediation Selection",
        "selection_id": selected.get("selection_id", ""),
        "status": "selected" if validation_result["valid"] else "blocked",
        **selected,
        "task_contract": _task_contract(selected) if selected else {},
        "validation_result": validation_result,
        "metadata": {
            "selection_recorded": validation_result["valid"],
            "serializer_modified": False,
            "media_files_read": False,
            "editor_launched": False,
            "automatic_import_performed": False,
            "video_export_performed": False,
        },
    }


def build_fcpxml_remediation_selection_from_file(review_path: str | Path, selection_request: dict[str, Any]) -> dict[str, Any]:
    """Build a remediation selection from a review JSON file and freeze its SHA-256."""
    path = Path(review_path)
    if not path.exists():
        return _blocked_selection(
            selection_request,
            [_issue("fcpxml_compatibility_review_file_not_found", "compatibility_review_json", "Module 13 requires an existing Module 12 review file.")],
        )
    review_text = path.read_text(encoding="utf-8")
    request = {
        **selection_request,
        "source_review_artifact": str(path),
        "source_review_sha256": hashlib.sha256(review_text.encode("utf-8")).hexdigest(),
    }
    return build_fcpxml_remediation_selection(json.loads(review_text), request)


def validate_fcpxml_remediation_selection_input(review: dict[str, Any], selection_request: dict[str, Any]) -> dict[str, Any]:
    """Validate that a remediation can be selected without implementing it."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if review.get("schema_version") != "1.0":
        errors.append(_issue("invalid_review_schema", "review.schema_version", "Module 13 expects a Module 12 review."))
    if review.get("status") != "review_ready":
        errors.append(_issue("review_not_ready", "review.status", "Only review_ready Module 12 findings can be selected for remediation."))

    metadata = _safe_dict(review.get("metadata"))
    for field in ("serializer_modified", "media_files_read", "editor_launched", "automatic_import_performed", "video_export_performed"):
        if metadata.get(field) is not False:
            errors.append(_issue("boundary_violation", f"review.metadata.{field}", "Module 13 cannot select remediation from a boundary-violating review."))

    remediation_ids = selection_request.get("remediation_ids")
    if isinstance(remediation_ids, list):
        if len(remediation_ids) > 1:
            errors.append(_issue("multiple_remediations_not_allowed", "selection_request.remediation_ids", "Module 13 can select exactly one remediation."))
        elif len(remediation_ids) == 1 and not selection_request.get("remediation_id"):
            selection_request = {**selection_request, "remediation_id": remediation_ids[0]}
    selection_id = str(selection_request.get("remediation_id", ""))
    if not selection_id:
        errors.append(_issue("selection_requires_explicit_remediation_id", "selection_request.remediation_id", "A remediation id must be explicitly selected."))
    if not selection_request.get("selected_by") or not selection_request.get("selected_at") or not selection_request.get("selection_rationale"):
        errors.append(_issue("missing_selection_metadata", "selection_request", "Selection requires reviewer, timestamp, and rationale."))
    if not selection_request.get("source_review_artifact") or not selection_request.get("source_review_sha256"):
        errors.append(_issue("missing_source_review_fingerprint", "selection_request.source_review_sha256", "Selection must freeze the source review artifact path and SHA-256."))

    remediation = _remediation_by_id(review, selection_id)
    if selection_id and not remediation:
        errors.append(_issue("remediation_not_found", "selection_request.remediation_id", "Selected remediation id does not exist."))
        return {"valid": False, "errors": errors, "warnings": warnings}

    if remediation:
        finding = _finding_by_id(review, str(remediation.get("finding_id", "")))
        if not finding:
            errors.append(_issue("remediation_finding_not_found", "review.remediation_plan", "Selected remediation does not resolve to a finding."))
        else:
            if finding.get("evidence_status") != "linked" or not _safe_list_values(finding.get("evidence_refs")):
                errors.append(_issue("selected_finding_without_linked_evidence", "review.findings", "Selected remediation must be backed by linked evidence."))
            if finding.get("severity") not in {"blocker", "major"}:
                errors.append(_issue("selected_finding_not_actionable", "review.findings", "Only blocker or major findings may be selected for remediation."))
        if remediation.get("serializer_change_allowed") is not False:
            errors.append(_issue("remediation_allows_serializer_change", "review.remediation_plan", "Module 13 may not select an item that already allows serializer changes."))
        if remediation.get("requires_evidence_before_implementation") is True:
            errors.append(_issue("remediation_requires_more_evidence", "review.remediation_plan", "Attach evidence before selecting this remediation for implementation planning."))
        if remediation.get("status") != "proposed":
            errors.append(_issue("remediation_not_proposed", "review.remediation_plan", "Only proposed remediation items can be selected."))

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def write_fcpxml_remediation_selection(selection: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Write a remediation selection contract without applying the remediation."""
    if selection.get("status") != "selected":
        raise ValueError(f"Invalid Module 13 remediation selection: {selection.get('validation_result', {})}")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "schema_version": FCPXML_REMEDIATION_SELECTION_SCHEMA_VERSION,
        "status": "written",
        "output_path": str(output),
        "bytes_written": output.stat().st_size,
        "selection_file_written": True,
        "serializer_modified": False,
        "media_files_read": False,
        "editor_launched": False,
        "automatic_import_performed": False,
        "video_export_performed": False,
    }


def _selected_payload(review: dict[str, Any], selection_request: dict[str, Any]) -> dict[str, Any]:
    remediation = _remediation_by_id(review, str(selection_request.get("remediation_id", "")))
    finding = _finding_by_id(review, str(remediation.get("finding_id", ""))) if remediation else {}
    source_record = _safe_dict(review.get("source_record"))
    selection_id = f"sel_{str(remediation.get('id', 'unknown'))}"
    evidence_refs = _safe_list_values(finding.get("evidence_refs"))
    related_entities = _safe_dict(finding.get("related_entities"))
    priority = str(selection_request.get("priority_override") or remediation.get("priority", ""))
    rationale = str(selection_request.get("selection_rationale", ""))
    source_review_git_commit = str(selection_request.get("source_review_git_commit") or source_record.get("git_commit", ""))
    return {
        "source_review": {
            "schema_version": str(review.get("schema_version", "")),
            "status": str(review.get("status", "")),
            "source_record": source_record,
        },
        "selection": {
            "selection_id": selection_id,
            "status": "selected",
            "selected_remediation_id": str(remediation.get("id", "")),
            "selected_finding_id": str(finding.get("id", "")),
            "selected_by": str(selection_request.get("selected_by", "")),
            "selected_at": str(selection_request.get("selected_at", "")),
            "selection_rationale": rationale,
            "priority": priority,
            "priority_override_reason": str(selection_request.get("priority_override_reason", "")),
            "evidence_refs": evidence_refs,
            "related_entities": related_entities,
            "source_review_artifact": str(selection_request.get("source_review_artifact", "")),
            "source_review_sha256": str(selection_request.get("source_review_sha256", "")),
            "source_review_git_commit": source_review_git_commit,
            "execution_allowed": False,
            "serializer_change_allowed": False,
            "requires_module_14_approval": True,
        },
        "selection_id": selection_id,
        "selected_remediation_id": str(remediation.get("id", "")),
        "selected_finding_id": str(finding.get("id", "")),
        "selected_by": str(selection_request.get("selected_by", "")),
        "selected_at": str(selection_request.get("selected_at", "")),
        "selection_rationale": rationale,
        "priority": priority,
        "evidence_refs": evidence_refs,
        "related_entities": related_entities,
        "source_review_artifact": str(selection_request.get("source_review_artifact", "")),
        "source_review_sha256": str(selection_request.get("source_review_sha256", "")),
        "source_review_git_commit": source_review_git_commit,
        "execution_allowed": False,
        "serializer_change_allowed": False,
        "requires_module_14_approval": True,
        "immutable_selection_snapshot": {
            "finding": copy.deepcopy(finding),
            "remediation": copy.deepcopy(remediation),
            "evidence_refs": copy.deepcopy(evidence_refs),
            "related_entities": copy.deepcopy(related_entities),
            "review_status": str(review.get("status", "")),
            "review_sha256": str(selection_request.get("source_review_sha256", "")),
            "review_git_commit": source_review_git_commit,
            "selected_priority": priority,
            "selection_rationale": rationale,
        },
    }


def _task_contract(selection: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "task_contract_ready",
        "implementation_allowed": False,
        "serializer_change_allowed": False,
        "requires_module_14_approval": True,
        "requires_linked_evidence": True,
        "selected_remediation_id": selection.get("selected_remediation_id", ""),
        "selected_finding_id": selection.get("selected_finding_id", ""),
        "evidence_refs": _safe_list_values(selection.get("evidence_refs")),
        "scope_boundary": {
            "may_define_future_fix_scope": True,
            "may_modify_serializer": False,
            "may_create_code_patch": False,
            "may_modify_samples": False,
            "may_launch_editor": False,
            "may_read_media": False,
            "may_render_or_export_video": False,
        },
        "next_gate": "Module 13 Review must pass before remediation implementation begins.",
    }


def _blocked_selection(selection_request: dict[str, Any], errors: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema_version": FCPXML_REMEDIATION_SELECTION_SCHEMA_VERSION,
        "module": "Module 13",
        "name": "Evidence-Backed Remediation Selection",
        "selection_id": "",
        "status": "blocked",
        "selected_remediation_id": str(selection_request.get("remediation_id", "")),
        "selected_finding_id": "",
        "selected_by": str(selection_request.get("selected_by", "")),
        "selected_at": str(selection_request.get("selected_at", "")),
        "selection_rationale": str(selection_request.get("selection_rationale", "")),
        "priority": "",
        "evidence_refs": [],
        "related_entities": {},
        "source_review_artifact": str(selection_request.get("source_review_artifact", "")),
        "source_review_sha256": "",
        "source_review_git_commit": "",
        "execution_allowed": False,
        "serializer_change_allowed": False,
        "requires_module_14_approval": True,
        "immutable_selection_snapshot": {},
        "task_contract": {},
        "validation_result": {"valid": False, "errors": errors, "warnings": []},
        "metadata": {
            "selection_recorded": False,
            "serializer_modified": False,
            "media_files_read": False,
            "editor_launched": False,
            "automatic_import_performed": False,
            "video_export_performed": False,
        },
    }


def _remediation_by_id(review: dict[str, Any], remediation_id: str) -> dict[str, Any]:
    for item in _safe_list(_safe_dict(review.get("remediation_plan")).get("items")):
        if str(item.get("id", "")) == remediation_id:
            return item
    return {}


def _finding_by_id(review: dict[str, Any], finding_id: str) -> dict[str, Any]:
    for item in _safe_list(review.get("findings")):
        if str(item.get("id", "")) == finding_id:
            return item
    return {}


def _issue(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message}


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _safe_list_values(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
