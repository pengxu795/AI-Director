"""Manual FCPXML import acceptance protocol for Module 10.

This module defines a repeatable manual validation protocol for importing a
generated .fcpxml file into Final Cut Pro. It does not launch Final Cut Pro,
control editors, read media files, transcode, render, or export video.
"""

from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

from .fcpxml_serializer import validate_fcpxml_serialization_input


FCPXML_ACCEPTANCE_SCHEMA_VERSION = "1.0"

CHECKLIST_DEFINITIONS = [
    (
        "preflight_fcpxml_file",
        "preflight",
        "Confirm the generated .fcpxml file fingerprint matches the protocol before import.",
        "File path, SHA-256, design fingerprint, commit hash, and serializer metadata are recorded before import.",
    ),
    (
        "preflight_environment",
        "preflight",
        "Record Final Cut Pro version, macOS version, test machine, and library/project names.",
        "Environment details are recorded in the manual result.",
    ),
    (
        "resource_paths",
        "resources",
        "Import the .fcpxml and inspect whether declared media asset paths resolve or appear offline as expected.",
        "Every asset path is recorded with online/offline state; missing media is not guessed or relinked silently.",
    ),
    (
        "clip_count_and_order",
        "timeline",
        "Verify imported clips appear in the same order as the generated spine.",
        "Clip count and order match expected clip ids.",
    ),
    (
        "clip_source_ranges",
        "timeline",
        "Verify each clip source in/out matches the expected FCPXML start and duration.",
        "Each imported clip uses the expected source start and duration.",
    ),
    (
        "clip_timeline_offsets",
        "timeline",
        "Verify each clip appears at the expected timeline offset and duration.",
        "Timeline offsets and durations match the expected rational seconds.",
    ),
    (
        "marker_positions",
        "markers",
        "Verify narration markers are attached to the correct clip and clip-relative position.",
        "Marker text, parent clip, timeline_start, and clip_relative_start match expectations.",
    ),
    (
        "invalid_file_behavior",
        "error_behavior",
        "Record how Final Cut Pro reports malformed or rejected FCPXML files in a separate negative run.",
        "Importer errors are recorded without editing the generated FCPXML by hand.",
    ),
]


def build_fcpxml_import_acceptance_protocol(
    fcpxml_design: dict[str, Any],
    fcpxml_path: str | Path,
    source_design_path: str | Path = "",
    git_commit: str = "",
    serializer_module_version: str = FCPXML_ACCEPTANCE_SCHEMA_VERSION,
    serializer_commit: str = "",
    generated_at: str = "",
) -> dict[str, Any]:
    """Build a manual acceptance protocol from a Module 8/9 FCPXML design."""
    path = str(fcpxml_path)
    design_path = str(source_design_path)
    serialization_validation = validate_fcpxml_serialization_input(fcpxml_design)
    protocol_errors: list[dict[str, str]] = []
    protocol_warnings: list[dict[str, str]] = []
    fcpxml_sha256 = ""
    source_design_sha256 = ""
    if not path:
        protocol_errors.append(_issue("missing_fcpxml_path", "fcpxml_path", "A generated .fcpxml path is required."))
    elif not path.endswith(".fcpxml"):
        protocol_errors.append(_issue("invalid_fcpxml_suffix", "fcpxml_path", "Acceptance protocol must point at a .fcpxml file."))
    elif not Path(path).is_file():
        protocol_errors.append(_issue("fcpxml_file_not_found", "fcpxml_path", "The .fcpxml file under review was not found."))
    else:
        fcpxml_sha256 = _sha256_file(Path(path))

    if design_path and Path(design_path).is_file():
        source_design_sha256 = _sha256_file(Path(design_path))
    if not git_commit or not serializer_commit:
        protocol_warnings.append(
            _issue(
                "missing_artifact_revision_metadata",
                "source_artifacts",
                "git_commit and serializer_commit should be supplied before manual acceptance.",
            )
        )

    resources = _safe_dict(fcpxml_design.get("resources"))
    sequence_design = _safe_dict(fcpxml_design.get("sequence_design"))
    clips = _safe_list(sequence_design.get("spine"))
    markers = _safe_list(sequence_design.get("markers"))
    assets = _safe_list(resources.get("assets"))

    validation_result = {
        "valid": serialization_validation["valid"] and not protocol_errors,
        "errors": protocol_errors + list(serialization_validation["errors"]),
        "warnings": protocol_warnings + list(serialization_validation["warnings"]),
    }
    fully_traceable = bool(fcpxml_sha256 and git_commit and serializer_commit)

    return {
        "schema_version": FCPXML_ACCEPTANCE_SCHEMA_VERSION,
        "module": "Module 10",
        "name": "FCPXML Import Validation / Manual Acceptance Protocol",
        "status": "protocol_ready" if validation_result["valid"] else "blocked",
        "fcpxml_path": path,
        "source_artifacts": {
            "fcpxml_path": path,
            "fcpxml_sha256": fcpxml_sha256,
            "source_design_path": design_path,
            "source_design_sha256": source_design_sha256,
            "git_commit": git_commit,
            "serializer_module_version": serializer_module_version,
            "serializer_commit": serializer_commit,
            "protocol_generated_at": generated_at or _utc_now(),
            "fully_traceable": fully_traceable,
            "acceptance_ready": validation_result["valid"] and fully_traceable,
        },
        "target_editor": {
            "name": "Final Cut Pro",
            "validation_mode": "manual_import_only",
            "editor_launched_by_code": False,
            "automatic_import_performed": False,
        },
        "source_design": {
            "schema_version": str(fcpxml_design.get("schema_version", "")),
            "target_version": str(_safe_dict(fcpxml_design.get("target_profile")).get("target_version", "")),
            "sequence_frame_duration": str(_safe_dict(resources.get("sequence_format")).get("frameDuration", "")),
        },
        "expected_assets": _expected_assets(assets),
        "expected_clips": _expected_clips(clips),
        "expected_markers": _expected_markers(markers, clips),
        "checklist": _checklist(),
        "manual_result_template": _manual_result_template(
            path,
            fcpxml_sha256,
            design_path,
            source_design_sha256,
            git_commit,
            serializer_module_version,
            serializer_commit,
        ),
        "validation_result": validation_result,
        "metadata": {
            "protocol_generated": True,
            "import_validation_performed": False,
            "manual_review_required": True,
            "media_files_read": False,
            "editor_launched": False,
            "video_export_performed": False,
            "fcpxml_file_read_for_sha256": bool(fcpxml_sha256),
        },
    }


def validate_fcpxml_import_acceptance_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    """Validate the manual protocol object itself without running editor import."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if protocol.get("schema_version") != FCPXML_ACCEPTANCE_SCHEMA_VERSION:
        errors.append(_issue("invalid_schema_version", "schema_version", "Unexpected Module 10 schema version."))
    if protocol.get("status") not in {"protocol_ready", "blocked"}:
        errors.append(_issue("invalid_protocol_status", "status", "Protocol status must be protocol_ready or blocked."))
    if not str(protocol.get("fcpxml_path", "")).endswith(".fcpxml"):
        errors.append(_issue("invalid_fcpxml_suffix", "fcpxml_path", "Protocol must reference a .fcpxml file."))
    source_artifacts = _safe_dict(protocol.get("source_artifacts"))
    if source_artifacts.get("fcpxml_path") != protocol.get("fcpxml_path"):
        errors.append(_issue("artifact_path_mismatch", "source_artifacts.fcpxml_path", "Artifact path must match top-level fcpxml_path."))
    if protocol.get("status") == "protocol_ready" and not source_artifacts.get("fcpxml_sha256"):
        errors.append(_issue("missing_fcpxml_sha256", "source_artifacts.fcpxml_sha256", "Protocol-ready runs must fingerprint the .fcpxml file."))
    if source_artifacts.get("acceptance_ready") and not source_artifacts.get("fully_traceable"):
        errors.append(_issue("acceptance_ready_requires_traceability", "source_artifacts.acceptance_ready", "Acceptance readiness requires full traceability."))

    metadata = _safe_dict(protocol.get("metadata"))
    for field in ("media_files_read", "editor_launched", "video_export_performed", "import_validation_performed"):
        if metadata.get(field) is not False:
            errors.append(_issue("boundary_violation", f"metadata.{field}", "Module 10 protocol generation must not perform this action."))

    target_editor = _safe_dict(protocol.get("target_editor"))
    if target_editor.get("automatic_import_performed") is not False:
        errors.append(_issue("automatic_import_not_allowed", "target_editor.automatic_import_performed", "Import must remain manual."))
    if target_editor.get("editor_launched_by_code") is not False:
        errors.append(_issue("editor_launch_not_allowed", "target_editor.editor_launched_by_code", "Code must not launch Final Cut Pro."))

    checklist = _safe_list(protocol.get("checklist"))
    checklist_ids = [str(item.get("id", "")) for item in checklist]
    if len(checklist_ids) != len(set(checklist_ids)):
        errors.append(_issue("duplicate_checklist_id", "checklist", "Checklist ids must be unique."))
    required_categories = {"preflight", "resources", "timeline", "markers", "error_behavior"}
    present_categories = {str(item.get("category", "")) for item in checklist}
    missing_categories = sorted(required_categories - present_categories)
    for category in missing_categories:
        errors.append(_issue("missing_checklist_category", "checklist", f"Missing checklist category: {category}."))
    for index, item in enumerate(checklist):
        prefix = f"checklist[{index}]"
        for field in ("id", "category", "instruction", "expected_result", "status"):
            if not item.get(field):
                errors.append(_issue("missing_checklist_field", f"{prefix}.{field}", "Checklist item is incomplete."))
        if item.get("status") != "not_run":
            errors.append(_issue("checklist_must_start_not_run", f"{prefix}.status", "Protocol must not pre-fill manual results."))

    if not _safe_list(protocol.get("expected_clips")):
        errors.append(_issue("missing_expected_clips", "expected_clips", "Protocol needs expected clip observations."))
    if not _safe_list(protocol.get("expected_assets")):
        errors.append(_issue("missing_expected_assets", "expected_assets", "Protocol needs expected asset observations."))

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def write_fcpxml_import_acceptance_protocol(protocol: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Write the manual acceptance protocol JSON without touching editor or media."""
    validation_result = validate_fcpxml_import_acceptance_protocol(protocol)
    if not validation_result["valid"]:
        raise ValueError(f"Invalid Module 10 acceptance protocol: {validation_result['errors']}")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "schema_version": FCPXML_ACCEPTANCE_SCHEMA_VERSION,
        "status": "written",
        "output_path": str(output),
        "bytes_written": output.stat().st_size,
        "protocol_file_written": True,
        "media_files_read": False,
        "editor_launched": False,
        "import_validation_performed": False,
        "video_export_performed": False,
    }


def _expected_assets(assets: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "asset_id": str(asset.get("id", "")),
            "media_asset_id": str(asset.get("media_asset_id", "")),
            "source_file": str(asset.get("src", "")),
            "duration": str(asset.get("duration", "")),
            "frame_duration": str(asset.get("frameDuration", "")),
            "expected_import_state": "online_or_offline_reported_explicitly",
        }
        for asset in assets
    ]


def _expected_clips(clips: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "clip_id": str(clip.get("id", "")),
            "asset_ref": str(clip.get("ref", "")),
            "name": str(clip.get("name", "")),
            "timeline_offset": str(clip.get("offset", "")),
            "source_start": str(clip.get("start", "")),
            "duration": str(clip.get("duration", "")),
            "source_story_block_id": str(clip.get("source_story_block_id", "")),
            "source_timeline_item_id": str(clip.get("source_timeline_item_id", "")),
            "reuse_policy": str(clip.get("reuse_policy", "")),
        }
        for clip in clips
    ]


def _expected_markers(markers: list[dict[str, Any]], clips: list[dict[str, Any]]) -> list[dict[str, str]]:
    expected = []
    for marker in markers:
        timeline_start = str(marker.get("timeline_start", ""))
        matched_clip = _clip_for_marker(timeline_start, clips)
        clip_relative_start = ""
        if matched_clip:
            clip_relative_start = _fraction_to_time(
                _rational_time_to_fraction(timeline_start) - _rational_time_to_fraction(str(matched_clip.get("offset", "0s")))
            )
        expected.append(
            {
                "marker_id": str(marker.get("id", "")),
                "narration_segment_id": str(marker.get("narration_segment_id", "")),
                "source_timeline_item_id": str(marker.get("source_timeline_item_id", "")),
                "value": str(marker.get("value", "")),
                "timeline_start": timeline_start,
                "expected_clip_id": str(matched_clip.get("id", "")) if matched_clip else "",
                "clip_relative_start": clip_relative_start,
            }
        )
    return expected


def _checklist() -> list[dict[str, Any]]:
    return [
        {
            "id": item_id,
            "category": category,
            "instruction": instruction,
            "expected_result": expected_result,
            "evidence_required": ["manual_note", "screenshot_or_screen_recording"],
            "status": "not_run",
            "actual_result": "",
        }
        for item_id, category, instruction, expected_result in CHECKLIST_DEFINITIONS
    ]


def _manual_result_template(
    fcpxml_path: str,
    fcpxml_sha256: str,
    source_design_path: str,
    source_design_sha256: str,
    git_commit: str,
    serializer_module_version: str,
    serializer_commit: str,
) -> dict[str, Any]:
    return {
        "status": "not_run",
        "artifact_identifiers": {
            "fcpxml_path": fcpxml_path,
            "fcpxml_sha256": fcpxml_sha256,
            "source_design_path": source_design_path,
            "source_design_sha256": source_design_sha256,
            "git_commit": git_commit,
            "serializer_module_version": serializer_module_version,
            "serializer_commit": serializer_commit,
        },
        "tester": "",
        "run_at": "",
        "final_cut_pro_version": "",
        "macos_version": "",
        "library_name": "",
        "project_name": "",
        "imported": None,
        "compatibility_result": "unknown",
        "checks": [
            {
                "id": item_id,
                "status": "not_run",
                "actual_result": "",
                "evidence_path": "",
                "notes": "",
            }
            for item_id, *_rest in CHECKLIST_DEFINITIONS
        ],
        "blockers": [],
        "follow_up_actions": [],
    }


def _clip_for_marker(timeline_start: str, clips: list[dict[str, Any]]) -> dict[str, Any]:
    if not timeline_start:
        return {}
    marker_time = _rational_time_to_fraction(timeline_start)
    matches = []
    for clip in clips:
        offset = _rational_time_to_fraction(str(clip.get("offset", "0s")))
        duration = _rational_time_to_fraction(str(clip.get("duration", "0s")))
        if offset <= marker_time < offset + duration:
            matches.append(clip)
    return matches[0] if len(matches) == 1 else {}


def _rational_time_to_fraction(value: str) -> Fraction:
    raw = value[:-1] if value.endswith("s") else value
    if "/" in raw:
        numerator, denominator = raw.split("/", 1)
        return Fraction(int(numerator), int(denominator))
    return Fraction(int(raw or 0), 1)


def _fraction_to_time(value: Fraction) -> str:
    value = value.limit_denominator()
    if value.denominator == 1:
        return f"{value.numerator}s"
    return f"{value.numerator}/{value.denominator}s"


def _issue(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
