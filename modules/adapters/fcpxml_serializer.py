"""Minimal FCPXML serialization for Module 9.

This module serializes an already validated Module 8 FCPXML design into a
minimal .fcpxml file. It does not read media, probe files, transcode, render,
or control Final Cut Pro.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any
from urllib.parse import quote
import xml.etree.ElementTree as ET


FCPXML_SERIALIZER_SCHEMA_VERSION = "1.0"
DOCTYPE = "<!DOCTYPE fcpxml>"
RATIONAL_TIME_SUFFIX = "s"


def validate_fcpxml_serialization_input(design: dict[str, Any]) -> dict[str, Any]:
    """Validate a Module 8 FCPXML design before writing XML text."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if design.get("status") != "designed":
        errors.append(_issue("design_not_ready", "status", "FCPXML serialization requires a designed input."))
    if design.get("xml_generated") is not False:
        errors.append(_issue("unexpected_prior_xml_generation", "xml_generated", "Input design must not already be serialized."))
    if design.get("project_file_written") is not False:
        errors.append(_issue("unexpected_prior_project_file", "project_file_written", "Input design must not already write files."))
    if design.get("media_files_read") is not False:
        errors.append(_issue("media_read_not_allowed", "media_files_read", "Serializer must not read media files."))

    target_profile = _safe_dict(design.get("target_profile"))
    if target_profile.get("target_id") != "fcpxml":
        errors.append(_issue("unsupported_target", "target_profile.target_id", "Module 9 only serializes FCPXML designs."))

    resources = _safe_dict(design.get("resources"))
    sequence_format = _safe_dict(resources.get("sequence_format"))
    assets = _safe_list(resources.get("assets"))
    sequence_design = _safe_dict(design.get("sequence_design"))
    clips = _safe_list(sequence_design.get("spine"))
    markers = _safe_list(sequence_design.get("markers"))

    _validate_sequence_format(sequence_format, errors)
    asset_ids = _validate_assets(assets, errors)
    _validate_clips(clips, asset_ids, errors)
    _validate_markers(markers, clips, sequence_format, warnings, errors)

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def serialize_fcpxml(design: dict[str, Any]) -> str:
    """Serialize a Module 8 design to FCPXML text."""
    validation_result = validate_fcpxml_serialization_input(design)
    if not validation_result["valid"]:
        raise ValueError(f"Invalid FCPXML design: {validation_result['errors']}")

    target_profile = _safe_dict(design.get("target_profile"))
    resources = _safe_dict(design.get("resources"))
    sequence_format = _safe_dict(resources.get("sequence_format"))
    assets = _safe_list(resources.get("assets"))
    sequence_design = _safe_dict(design.get("sequence_design"))
    clips = _safe_list(sequence_design.get("spine"))
    markers = _safe_list(sequence_design.get("markers"))

    root = ET.Element("fcpxml", {"version": str(target_profile.get("target_version", "1.10"))})
    resources_el = ET.SubElement(root, "resources")
    ET.SubElement(
        resources_el,
        "format",
        {
            "id": str(sequence_format.get("id", "")),
            "name": str(sequence_format.get("name", "")),
            "frameDuration": str(sequence_format.get("frameDuration", "")),
        },
    )
    for asset in assets:
        ET.SubElement(
            resources_el,
            "asset",
            {
                "id": str(asset.get("id", "")),
                "name": str(asset.get("name", "")),
                "src": _file_url(str(asset.get("src", ""))),
                "duration": str(asset.get("duration", "")),
                "hasVideo": "1",
                "hasAudio": str(asset.get("hasAudio", "1")),
                "format": str(asset.get("format", sequence_format.get("id", ""))),
            },
        )

    library_el = ET.SubElement(root, "library")
    event_el = ET.SubElement(library_el, "event", {"name": str(sequence_design.get("event_name", "AI-Director"))})
    project_el = ET.SubElement(event_el, "project", {"name": str(sequence_design.get("project_name", "AI-Director"))})
    sequence_el = ET.SubElement(
        project_el,
        "sequence",
        {
            "format": str(sequence_format.get("id", "")),
            "duration": _sequence_duration(clips),
            "tcStart": "0s",
            "tcFormat": "NDF",
        },
    )
    spine_el = ET.SubElement(sequence_el, "spine")
    clip_elements: list[tuple[dict[str, Any], ET.Element]] = []
    for clip in clips:
        clip_el = ET.SubElement(
            spine_el,
            "asset-clip",
            {
                "name": str(clip.get("name", "")),
                "ref": str(clip.get("ref", "")),
                "offset": str(clip.get("offset", "")),
                "start": str(clip.get("start", "")),
                "duration": str(clip.get("duration", "")),
            },
        )
        metadata = _clip_metadata(clip)
        if metadata:
            clip_el.append(ET.Comment(metadata))
        clip_elements.append((clip, clip_el))

    for marker in markers:
        clip, marker_parent = _marker_clip_target(marker, clip_elements)
        marker_start = _fraction_to_fcpxml_time(
            _rational_time_to_fraction(str(marker.get("timeline_start", "0s"))) - _rational_time_to_fraction(str(clip.get("offset", "0s")))
        )
        ET.SubElement(
            marker_parent,
            "marker",
            {
                "start": marker_start,
                "duration": _first_frame_duration(sequence_format),
                "value": str(marker.get("value", "")),
            },
        )

    ET.indent(root, space="  ")
    xml_body = ET.tostring(root, encoding="unicode", short_empty_elements=True)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{DOCTYPE}\n{xml_body}\n'


def write_fcpxml_file(design: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Write minimal FCPXML text to disk without touching media files."""
    output = Path(output_path)
    if output.suffix != ".fcpxml":
        raise ValueError("Module 9 output path must end with .fcpxml.")
    xml_text = serialize_fcpxml(design)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(xml_text, encoding="utf-8")
    return {
        "schema_version": FCPXML_SERIALIZER_SCHEMA_VERSION,
        "status": "written",
        "output_path": str(output),
        "bytes_written": len(xml_text.encode("utf-8")),
        "fcpxml_file_written": True,
        "media_files_read": False,
        "editor_launched": False,
        "video_export_performed": False,
    }


def _validate_sequence_format(sequence_format: dict[str, Any], errors: list[dict[str, str]]) -> None:
    for field in ("id", "name", "frameDuration"):
        if not sequence_format.get(field):
            errors.append(_issue("missing_sequence_format_field", f"resources.sequence_format.{field}", "Missing sequence format field."))
    if sequence_format.get("frameDuration") and not _is_rational_time(sequence_format.get("frameDuration")):
        errors.append(_issue("invalid_rational_time", "resources.sequence_format.frameDuration", "frameDuration must be rational seconds."))


def _validate_assets(assets: list[dict[str, Any]], errors: list[dict[str, str]]) -> set[str]:
    asset_ids = set()
    if not assets:
        errors.append(_issue("missing_assets", "resources.assets", "At least one asset resource is required."))
    for index, asset in enumerate(assets):
        prefix = f"resources.assets[{index}]"
        for field in ("id", "name", "src", "duration", "frameDuration", "format"):
            if not asset.get(field):
                errors.append(_issue("missing_asset_field", f"{prefix}.{field}", "Missing asset field."))
        if asset.get("id") in asset_ids:
            errors.append(_issue("duplicate_asset_id", f"{prefix}.id", "Asset ids must be unique."))
        if asset.get("id"):
            asset_ids.add(str(asset.get("id")))
        for field in ("duration", "frameDuration"):
            if asset.get(field) and not _is_rational_time(asset.get(field)):
                errors.append(_issue("invalid_rational_time", f"{prefix}.{field}", "Asset time fields must be rational seconds."))
    return asset_ids


def _validate_clips(clips: list[dict[str, Any]], asset_ids: set[str], errors: list[dict[str, str]]) -> None:
    if not clips:
        errors.append(_issue("missing_clips", "sequence_design.spine", "At least one clip is required for minimal FCPXML."))
    for index, clip in enumerate(clips):
        prefix = f"sequence_design.spine[{index}]"
        for field in ("id", "ref", "name", "offset", "start", "duration"):
            if not clip.get(field):
                errors.append(_issue("missing_clip_field", f"{prefix}.{field}", "Missing clip field."))
        if clip.get("ref") and clip.get("ref") not in asset_ids:
            errors.append(_issue("unknown_clip_asset_ref", f"{prefix}.ref", "Clip references an unknown asset."))
        for field in ("offset", "start", "duration"):
            if clip.get(field) and not _is_rational_time(clip.get(field)):
                errors.append(_issue("invalid_rational_time", f"{prefix}.{field}", "Clip time fields must be rational seconds."))


def _validate_markers(
    markers: list[dict[str, Any]],
    clips: list[dict[str, Any]],
    sequence_format: dict[str, Any],
    warnings: list[dict[str, str]],
    errors: list[dict[str, str]],
) -> None:
    if markers:
        warnings.append(_issue("markers_design_only", "sequence_design.markers", "Markers preserve narration text only; no audio is generated."))
    sequence_duration = _rational_time_to_fraction(_sequence_duration(clips))
    frame_duration = _frame_duration_fraction(sequence_format)
    for index, marker in enumerate(markers):
        field = f"sequence_design.markers[{index}]"
        if not marker.get("timeline_start"):
            errors.append(_issue("missing_marker_timeline_start", f"{field}.timeline_start", "Marker must include timeline_start."))
            continue
        if not _is_rational_time(marker.get("timeline_start")):
            errors.append(_issue("invalid_rational_time", f"{field}.timeline_start", "Marker timeline_start must be rational seconds."))
            continue
        marker_time = _rational_time_to_fraction(str(marker.get("timeline_start")))
        if marker_time < 0 or marker_time >= sequence_duration:
            errors.append(_issue("marker_outside_sequence_range", f"{field}.timeline_start", "Marker must fall inside sequence duration."))
            continue
        marker_frame_aligned = True
        if frame_duration and not _is_frame_aligned(marker_time, frame_duration):
            marker_frame_aligned = False
            errors.append(
                _issue(
                    "marker_time_not_frame_aligned",
                    f"{field}.timeline_start",
                    "Marker timeline_start must align to the sequence frame duration.",
                )
            )
        matches = _clips_covering_time(marker_time, clips)
        if not matches:
            errors.append(_issue("marker_outside_clip_range", f"{field}.timeline_start", "Marker must fall inside a clip range."))
        elif len(matches) > 1:
            errors.append(_issue("ambiguous_marker_clip_target", f"{field}.timeline_start", "Marker matches multiple clips."))
        elif frame_duration:
            clip_offset = _rational_time_to_fraction(str(matches[0].get("offset", "0s")))
            relative_start = marker_time - clip_offset
            if not _is_frame_aligned(relative_start, frame_duration) and marker_frame_aligned:
                errors.append(
                    _issue(
                        "marker_time_not_frame_aligned",
                        f"{field}.timeline_start",
                        "Clip-relative marker start must align to the sequence frame duration.",
                    )
                )


def _file_url(path: str) -> str:
    if path.startswith("file://"):
        return path
    if path.startswith("/"):
        return "file://" + quote(path)
    return "file://" + quote("/" + path)


def _sequence_duration(clips: list[dict[str, Any]]) -> str:
    max_end = Fraction(0, 1)
    for clip in clips:
        offset = _rational_time_to_fraction(str(clip.get("offset", "0s")))
        duration = _rational_time_to_fraction(str(clip.get("duration", "0s")))
        max_end = max(max_end, offset + duration)
    if max_end <= 0:
        return "0s"
    return _fraction_to_fcpxml_time(max_end)


def _clips_covering_time(marker_time: Fraction, clips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matches = []
    for clip in clips:
        offset = _rational_time_to_fraction(str(clip.get("offset", "0s")))
        duration = _rational_time_to_fraction(str(clip.get("duration", "0s")))
        if offset <= marker_time < offset + duration:
            matches.append(clip)
    return matches


def _marker_clip_target(
    marker: dict[str, Any],
    clip_elements: list[tuple[dict[str, Any], ET.Element]],
) -> tuple[dict[str, Any], ET.Element]:
    marker_time = _rational_time_to_fraction(str(marker.get("timeline_start", "0s")))
    matches = []
    for clip, element in clip_elements:
        offset = _rational_time_to_fraction(str(clip.get("offset", "0s")))
        duration = _rational_time_to_fraction(str(clip.get("duration", "0s")))
        if offset <= marker_time < offset + duration:
            matches.append((clip, element))
    if len(matches) != 1:
        raise ValueError("Marker must resolve to exactly one clip.")
    return matches[0]


def _first_frame_duration(sequence_format: dict[str, Any]) -> str:
    return str(sequence_format.get("frameDuration", "1/25s"))


def _frame_duration_fraction(sequence_format: dict[str, Any]) -> Fraction | None:
    frame_duration = sequence_format.get("frameDuration")
    if not frame_duration or not _is_rational_time(frame_duration):
        return None
    value = _rational_time_to_fraction(str(frame_duration))
    return value if value > 0 else None


def _is_frame_aligned(value: Fraction, frame_duration: Fraction) -> bool:
    if frame_duration <= 0:
        return False
    return (value / frame_duration).denominator == 1


def _clip_metadata(clip: dict[str, Any]) -> str:
    parts = []
    for key in ("source_story_block_id", "source_timeline_item_id", "reuse_policy"):
        if clip.get(key):
            parts.append(f"{key}={clip[key]}")
    return "; ".join(parts)


def _is_rational_time(value: Any) -> bool:
    text = str(value)
    if not text.endswith(RATIONAL_TIME_SUFFIX):
        return False
    raw = text[:-1]
    if "/" in raw:
        numerator, denominator = raw.split("/", 1)
        return numerator.isdigit() and denominator.isdigit() and int(denominator) > 0
    return raw.isdigit()


def _rational_time_to_fraction(value: str) -> Fraction:
    raw = value[:-1] if value.endswith("s") else value
    if "/" in raw:
        numerator, denominator = raw.split("/", 1)
        return Fraction(int(numerator), int(denominator))
    return Fraction(int(raw or 0), 1)


def _fraction_to_fcpxml_time(value: Fraction) -> str:
    value = value.limit_denominator()
    if value.denominator == 1:
        return f"{value.numerator}s"
    return f"{value.numerator}/{value.denominator}s"


def _issue(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message}


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
