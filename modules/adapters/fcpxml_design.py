"""FCPXML adapter discovery and minimal export design for Module 8.

This module does not generate FCPXML, XML, editor projects, or media files. It
only validates a Module 7 adapter plan and returns an abstract FCPXML design.
"""

from __future__ import annotations

import re
from fractions import Fraction
from pathlib import Path
from typing import Any


FCPXML_DESIGN_SCHEMA_VERSION = "1.0"
FCPXML_SELECTED_VERSION = "1.10"
TIMECODE_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$")

ALLOWED_OPERATION_TYPES = {
    "create_sequence",
    "register_media_asset",
    "place_clip",
    "add_narration_cue",
}

DESIGN_REFERENCES = [
    {
        "name": "Apple FCPXML Reference",
        "url": "https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference",
        "usage": "Primary reference for FCPXML as media, metadata, and Final Cut Pro interchange.",
    },
    {
        "name": "Apple FCPXML Document Type Definition",
        "url": "https://developer.apple.com/documentation/professional-video-applications/document-type-definition",
        "usage": "Primary DTD reference; Module 8 uses it for design only.",
    },
    {
        "name": "Apple Legacy FCPXML DTD Notes",
        "url": "https://developer.apple.com/library/archive/documentation/Miscellaneous/Conceptual/LegacyDTDsFinalCutPro/FCPXMLDTDv1.7/FCPXMLDTDv1.7.html",
        "usage": "Confirms FCPXML time attributes are rational seconds.",
    },
]


def fcpxml_target_profile() -> dict[str, Any]:
    """Return the Module 8 FCPXML discovery profile."""
    return {
        "target_id": "fcpxml",
        "target_version": FCPXML_SELECTED_VERSION,
        "schema_version": FCPXML_DESIGN_SCHEMA_VERSION,
        "stage": "discovery_minimal_export_design",
        "output_kind": "abstract_fcpxml_design",
        "design_only": True,
        "xml_generated": False,
        "project_file_written": False,
        "media_files_read": False,
        "selected_version_reason": "Apple's current public DTD page is the baseline; import must be verified in a later gated module.",
    }


def validate_fcpxml_design_input(adapter_plan: dict[str, Any]) -> dict[str, Any]:
    """Validate that an adapter plan is safe for FCPXML design mapping."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if adapter_plan.get("status") != "planned":
        errors.append(_issue("adapter_plan_not_planned", "status", "FCPXML design requires a planned adapter plan."))
    if adapter_plan.get("editor_project_generated") is not False:
        errors.append(
            _issue(
                "editor_project_generation_not_allowed",
                "editor_project_generated",
                "Input must not already represent a generated editor project.",
            )
        )
    if adapter_plan.get("media_files_read") is not False:
        errors.append(_issue("media_read_not_allowed", "media_files_read", "Input must not read media files."))

    operations = _safe_list(adapter_plan.get("operations"))
    if not operations:
        errors.append(_issue("missing_operations", "operations", "Adapter plan must contain abstract operations."))

    media_assets = set()
    sequence_fps = _sequence_fps(adapter_plan)
    if sequence_fps is None:
        errors.append(
            _issue(
                "missing_sequence_fps",
                "target_profile.sequence_fps",
                "Module 8 requires explicit sequence fps from target_profile or project_settings.",
            )
        )
    elif not _valid_fps(sequence_fps):
        errors.append(_issue("invalid_sequence_fps", "target_profile.sequence_fps", "sequence_fps must be a positive fps value."))
    elif not _millisecond_frame_rate_supported(sequence_fps):
        errors.append(
            _issue(
                "unsupported_non_millisecond_frame_rate",
                "target_profile.sequence_fps",
                "Module 8 MVP only supports fps values whose frame duration is an integer number of milliseconds.",
            )
        )

    asset_fps_values = set()
    for index, operation in enumerate(operations):
        operation_type = str(operation.get("type", ""))
        field = f"operations[{index}]"
        if operation_type not in ALLOWED_OPERATION_TYPES:
            errors.append(_issue("unsupported_operation_type", f"{field}.type", "Operation is not part of the FCPXML minimal design."))
        if operation_type == "register_media_asset":
            _validate_register_media_asset(operation, field, errors)
            if _valid_fps(operation.get("fps")):
                asset_fps_values.add(_fps_fraction(operation.get("fps")))
            if not any(error["field"].startswith(field) for error in errors):
                media_assets.add(str(operation.get("media_asset_id", "")))
        elif operation_type == "place_clip":
            _validate_place_clip(operation, field, media_assets, sequence_fps, errors)
        elif operation_type == "add_narration_cue":
            warnings.append(
                _issue(
                    "narration_cue_design_only",
                    field,
                    "Module 8 maps narration cues as marker/text design only; no audio asset is generated.",
                )
            )

    if len(asset_fps_values) > 1:
        errors.append(_issue("mixed_fps_not_supported", "operations", "Module 8 MVP requires all bound assets to share one fps."))
    if sequence_fps is not None and asset_fps_values and _fps_fraction(sequence_fps) not in asset_fps_values:
        errors.append(
            _issue(
                "sequence_fps_asset_fps_mismatch",
                "target_profile.sequence_fps",
                "Module 8 MVP requires sequence fps to match the asset fps.",
            )
        )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def build_fcpxml_minimal_design(adapter_plan: dict[str, Any]) -> dict[str, Any]:
    """Build an abstract FCPXML design object without writing XML."""
    validation_result = validate_fcpxml_design_input(adapter_plan)
    if not validation_result["valid"]:
        return {
            "schema_version": FCPXML_DESIGN_SCHEMA_VERSION,
            "target_profile": fcpxml_target_profile(),
            "status": "blocked",
            "validation_result": validation_result,
            "xml_generated": False,
            "project_file_written": False,
            "media_files_read": False,
        }

    operations = _safe_list(adapter_plan.get("operations"))
    sequence_fps = _sequence_fps(adapter_plan)
    media_assets = _media_asset_resources(operations)
    clips = _clip_designs(operations, media_assets)
    narration_markers = _narration_marker_designs(operations)

    return {
        "schema_version": FCPXML_DESIGN_SCHEMA_VERSION,
        "target_profile": fcpxml_target_profile(),
        "status": "designed",
        "references": DESIGN_REFERENCES,
        "time_model": {
            "fcpxml_time_format": "rational_seconds",
            "internal_timecode_format": "HH:MM:SS.mmm",
            "conversion": "timecode_ms_to_reduced_rational_seconds",
            "sequence_fps": str(sequence_fps),
            "sequence_frame_duration": frame_duration_from_fps(sequence_fps),
            "frame_duration_policy": "sequence fps is explicit; asset fps must match in Module 8 MVP",
            "frame_alignment_policy": "all source and timeline edit points must align exactly to sequence fps",
            "drop_frame_policy": "not modeled in Module 8",
        },
        "resource_id_strategy": {
            "format_id": "fmt001",
            "asset_id_prefix": "asset_",
            "clip_id_prefix": "clip_",
            "marker_id_prefix": "marker_",
            "stability": "deterministic_from_adapter_plan_order",
        },
        "field_mapping": _field_mapping(),
        "resources": {
            "sequence_format": _sequence_format_resource(sequence_fps),
            "assets": list(media_assets.values()),
        },
        "sequence_design": {
            "project_name": "AI-Director Minimal FCPXML Design",
            "event_name": "AI-Director",
            "spine": clips,
            "markers": narration_markers,
        },
        "minimal_outline": _minimal_outline(media_assets, clips, narration_markers),
        "validation_result": validation_result,
        "xml_generated": False,
        "project_file_written": False,
        "media_files_read": False,
    }


def fcpxml_time_from_timecode(timecode: str) -> str:
    """Convert HH:MM:SS.mmm to reduced FCPXML rational seconds."""
    milliseconds = _timecode_to_ms(timecode)
    if milliseconds is None:
        raise ValueError("Invalid timecode.")
    return _milliseconds_to_rational_seconds(milliseconds)


def frame_duration_from_fps(fps: float | int | str) -> str:
    """Return a rational seconds-per-frame value for an fps value."""
    fps_fraction = _fps_fraction(fps)
    if fps_fraction is None or fps_fraction <= 0:
        raise ValueError("fps must be a positive number.")
    if not _millisecond_frame_rate_supported(fps):
        raise ValueError("Module 8 MVP requires an integer millisecond frame duration.")
    fraction = Fraction(1, 1) / fps_fraction
    return _fraction_to_fcpxml_time(fraction)


def ensure_no_fcpxml_file_output(output_path: str | Path) -> None:
    """Define the Module 8 export boundary by refusing file output."""
    raise NotImplementedError(f"Module 8 is design-only and will not write {output_path}.")


def _validate_register_media_asset(
    operation: dict[str, Any],
    field: str,
    errors: list[dict[str, str]],
) -> None:
    for name in ("media_asset_id", "source_file", "fps", "duration"):
        if operation.get(name) in ("", None):
            errors.append(_issue("missing_required_field", f"{field}.{name}", f"Missing media asset field: {name}."))
    if _timecode_to_ms(operation.get("duration")) is None:
        errors.append(_issue("invalid_duration_timecode", f"{field}.duration", "Media duration must use HH:MM:SS.mmm."))
    if not _valid_fps(operation.get("fps")):
        errors.append(_issue("invalid_fps", f"{field}.fps", "fps must be a positive number."))
    elif not _millisecond_frame_rate_supported(operation.get("fps")):
        errors.append(
            _issue(
                "unsupported_non_millisecond_frame_rate",
                f"{field}.fps",
                "Module 8 MVP only supports fps values whose frame duration is an integer number of milliseconds.",
            )
        )


def _validate_place_clip(
    operation: dict[str, Any],
    field: str,
    media_assets: set[str],
    sequence_fps: Any,
    errors: list[dict[str, str]],
) -> None:
    media_asset_id = str(operation.get("media_asset_id", ""))
    if not media_asset_id:
        errors.append(_issue("missing_required_field", f"{field}.media_asset_id", "Missing clip media asset id."))
    elif media_asset_id not in media_assets:
        errors.append(_issue("unregistered_media_asset", f"{field}.media_asset_id", "Clip references an unregistered media asset."))
    for name in ("source_in", "source_out", "timeline_start", "timeline_end"):
        if _timecode_to_ms(operation.get(name)) is None:
            errors.append(_issue("invalid_timecode", f"{field}.{name}", "Clip timecode must use HH:MM:SS.mmm."))
    if _valid_range_ms(operation.get("source_in"), operation.get("source_out")) is None:
        errors.append(_issue("invalid_source_range", field, "Clip source range must have positive duration."))
    if _valid_range_ms(operation.get("timeline_start"), operation.get("timeline_end")) is None:
        errors.append(_issue("invalid_timeline_range", field, "Clip timeline range must have positive duration."))
    if sequence_fps is not None and _valid_fps(sequence_fps) and _millisecond_frame_rate_supported(sequence_fps):
        for name in ("source_in", "source_out", "timeline_start", "timeline_end"):
            milliseconds = _timecode_to_ms(operation.get(name))
            if milliseconds is not None and not _time_is_frame_aligned(milliseconds, sequence_fps):
                errors.append(
                    _issue(
                        "time_not_frame_aligned",
                        f"{field}.{name}",
                        "Clip time must align exactly to the explicit sequence fps; rounding is forbidden.",
                    )
                )


def _media_asset_resources(operations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    resources = {}
    for operation in operations:
        if operation.get("type") != "register_media_asset":
            continue
        media_asset_id = str(operation.get("media_asset_id", ""))
        resources[media_asset_id] = {
            "id": f"asset_{len(resources) + 1:03d}",
            "media_asset_id": media_asset_id,
            "src": str(operation.get("source_file", "")),
            "name": Path(str(operation.get("source_file", ""))).name,
            "duration": fcpxml_time_from_timecode(str(operation.get("duration", ""))),
            "fps": operation.get("fps"),
            "frameDuration": frame_duration_from_fps(operation.get("fps")),
            "hasAudio": "1",
            "format": "fmt001",
        }
    return resources


def _clip_designs(
    operations: list[dict[str, Any]],
    media_assets: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    clips = []
    for operation in operations:
        if operation.get("type") != "place_clip":
            continue
        source_in_ms, source_out_ms = _valid_range_ms(operation.get("source_in"), operation.get("source_out")) or (0, 0)
        timeline_start_ms = _timecode_to_ms(operation.get("timeline_start")) or 0
        media_asset_id = str(operation.get("media_asset_id", ""))
        clips.append(
            {
                "id": f"clip_{len(clips) + 1:03d}",
                "element": "asset-clip",
                "ref": media_assets[media_asset_id]["id"],
                "name": media_assets[media_asset_id]["name"],
                "offset": _milliseconds_to_rational_seconds(timeline_start_ms),
                "start": _milliseconds_to_rational_seconds(source_in_ms),
                "duration": _milliseconds_to_rational_seconds(source_out_ms - source_in_ms),
                "source_story_block_id": str(operation.get("source_story_block_id", "")),
                "source_timeline_item_id": str(operation.get("source_timeline_item_id", "")),
                "reuse_policy": str(operation.get("reuse_policy", "")),
            }
        )
    return clips


def _narration_marker_designs(operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    markers = []
    for operation in operations:
        if operation.get("type") != "add_narration_cue":
            continue
        text = str(operation.get("text", ""))
        if not text:
            continue
        source_timeline_item_id = str(operation.get("source_timeline_item_id", ""))
        timeline_start = str(operation.get("timeline_start", ""))
        markers.append(
            {
                "id": f"marker_{len(markers) + 1:03d}",
                "narration_segment_id": str(operation.get("narration_segment_id", "")),
                "source_timeline_item_id": source_timeline_item_id,
                "timeline_start": _timecode_to_fcpxml_time(timeline_start),
                "value": text,
                "mapping": "marker_or_note_design_only",
            }
        )
    return markers


def _timecode_to_fcpxml_time(value: str) -> str:
    if value.endswith("s"):
        return value
    milliseconds = _timecode_to_ms(value)
    if milliseconds is None:
        return ""
    return _milliseconds_to_rational_seconds(milliseconds)


def _sequence_format_resource(sequence_fps: Any) -> dict[str, Any]:
    return {
        "id": "fmt001",
        "name": f"FFVideoFormat{sequence_fps}",
        "fps": str(sequence_fps),
        "frameDuration": frame_duration_from_fps(sequence_fps),
        "width": None,
        "height": None,
        "note": "Sequence format is explicit. Width and height require media probing and are intentionally unknown in Module 8.",
    }


def _field_mapping() -> list[dict[str, str]]:
    return [
        {"adapter_plan": "register_media_asset.media_asset_id", "fcpxml_design": "resources.asset.id"},
        {"adapter_plan": "register_media_asset.source_file", "fcpxml_design": "resources.asset.src"},
        {"adapter_plan": "register_media_asset.duration", "fcpxml_design": "resources.asset.duration"},
        {"adapter_plan": "target_profile.sequence_fps or project_settings.sequence_fps", "fcpxml_design": "resources.sequence_format.frameDuration"},
        {"adapter_plan": "register_media_asset.fps", "fcpxml_design": "resources.asset.frameDuration"},
        {"adapter_plan": "place_clip.media_asset_id", "fcpxml_design": "spine.asset-clip.ref"},
        {"adapter_plan": "place_clip.timeline_start", "fcpxml_design": "spine.asset-clip.offset"},
        {"adapter_plan": "place_clip.source_in", "fcpxml_design": "spine.asset-clip.start"},
        {"adapter_plan": "place_clip.source_out - source_in", "fcpxml_design": "spine.asset-clip.duration"},
        {"adapter_plan": "add_narration_cue.text", "fcpxml_design": "marker_or_note.value"},
    ]


def _minimal_outline(
    media_assets: dict[str, dict[str, Any]],
    clips: list[dict[str, Any]],
    markers: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "fcpxml": {
            "version": FCPXML_SELECTED_VERSION,
            "resources": {
                "format": "fmt001",
                "assets": [asset["id"] for asset in media_assets.values()],
            },
            "library": {
                "event": {
                    "project": {
                        "sequence": {
                            "format": "fmt001",
                            "spine": [clip["id"] for clip in clips],
                            "markers": [marker["id"] for marker in markers],
                        }
                    }
                }
            },
        }
    }


def _valid_range_ms(start: Any, end: Any) -> tuple[int, int] | None:
    start_ms = _timecode_to_ms(start)
    end_ms = _timecode_to_ms(end)
    if start_ms is None or end_ms is None or start_ms >= end_ms:
        return None
    return start_ms, end_ms


def _timecode_to_ms(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    match = TIMECODE_PATTERN.match(value)
    if not match:
        return None
    hours, minutes, seconds, milliseconds = (int(part) for part in match.groups())
    if minutes > 59 or seconds > 59:
        return None
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds


def _sequence_fps(adapter_plan: dict[str, Any]) -> Any:
    target_profile = adapter_plan.get("target_profile")
    if isinstance(target_profile, dict) and "sequence_fps" in target_profile:
        return target_profile.get("sequence_fps")
    project_settings = adapter_plan.get("project_settings")
    if isinstance(project_settings, dict) and "sequence_fps" in project_settings:
        return project_settings.get("sequence_fps")
    return None


def _valid_fps(value: Any) -> bool:
    fps = _fps_fraction(value)
    return fps is not None and fps > 0


def _millisecond_frame_rate_supported(value: Any) -> bool:
    fps = _fps_fraction(value)
    if fps is None or fps <= 0:
        return False
    frame_duration_ms = Fraction(1000, 1) / fps
    return frame_duration_ms.denominator == 1


def _fps_fraction(value: Any) -> Fraction | None:
    if isinstance(value, (float, int)):
        return Fraction(str(value))
    if isinstance(value, str):
        try:
            return Fraction(value)
        except ValueError:
            return None
    return None


def _time_is_frame_aligned(milliseconds: int, fps: Any) -> bool:
    fps_fraction = _fps_fraction(fps)
    if fps_fraction is None or fps_fraction <= 0:
        return False
    seconds = Fraction(milliseconds, 1000)
    return (seconds * fps_fraction).denominator == 1


def _milliseconds_to_rational_seconds(milliseconds: int) -> str:
    return _fraction_to_fcpxml_time(Fraction(milliseconds, 1000))


def _fraction_to_fcpxml_time(value: Fraction) -> str:
    value = value.limit_denominator()
    if value.denominator == 1:
        return f"{value.numerator}s"
    return f"{value.numerator}/{value.denominator}s"


def _issue(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message}


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
