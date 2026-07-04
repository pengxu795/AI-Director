"""Export package generator for Module 6.

This module writes JSON and text artifacts only. It does not generate editor
project files, automate apps, render media, or export finished video.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EXPORT_PACKAGE_SCHEMA_VERSION = "1.0"


def load_json_object(path: str | Path) -> dict[str, Any]:
    """Load a JSON object from disk."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object.")
    return data


def export_file_package(
    edit_timeline_path: str | Path,
    script_path: str | Path,
    timeline_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Build and write an export package from JSON input files."""
    package = build_export_package(
        load_json_object(edit_timeline_path),
        load_json_object(script_path),
        load_json_object(timeline_path),
    )
    export_package_files(package, output_dir)
    return package


def build_export_package(
    edit_timeline: dict[str, Any],
    script: dict[str, Any],
    timeline_plan: dict[str, Any],
) -> dict[str, Any]:
    """Build export artifacts from completed pipeline JSON."""
    narration_script = _build_narration_script(script)
    shot_list = _build_shot_list(edit_timeline)
    unresolved_items = _safe_list(edit_timeline.get("unresolved_items")) + _safe_list(
        timeline_plan.get("unresolved_segments")
    )

    artifacts = {
        "timeline.json": edit_timeline,
        "narration_script.json": narration_script,
        "narration_script.txt": _script_text(narration_script),
        "shot_list.json": shot_list,
        "unresolved_items.json": unresolved_items,
    }
    manifest = _build_manifest(edit_timeline, script, timeline_plan, artifacts)

    return {
        "manifest": manifest,
        "artifacts": artifacts,
    }


def export_package_files(package: dict[str, Any], output_dir: str | Path) -> None:
    """Write export package files to a directory."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    artifacts = package.get("artifacts") if isinstance(package.get("artifacts"), dict) else {}
    for filename, content in artifacts.items():
        output_path = path / filename
        if filename.endswith(".txt"):
            output_path.write_text(str(content), encoding="utf-8")
        else:
            output_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    (path / "manifest.json").write_text(
        json.dumps(package.get("manifest", {}), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _build_manifest(
    edit_timeline: dict[str, Any],
    script: dict[str, Any],
    timeline_plan: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": EXPORT_PACKAGE_SCHEMA_VERSION,
        "source_edit_timeline_schema_version": str(edit_timeline.get("schema_version", "")),
        "source_script_schema_version": str(script.get("schema_version", "")),
        "source_timeline_schema_version": str(timeline_plan.get("schema_version", "")),
        "files": [
            {"path": filename, "kind": _file_kind(filename)}
            for filename in sorted([*artifacts.keys(), "manifest.json"])
        ],
        "metadata": {
            "exporter": "json_package",
            "edit_segment_count": len(_safe_list(edit_timeline.get("edit_segments"))),
            "video_clip_count": len(_safe_list(_safe_dict(edit_timeline.get("tracks")).get("video"))),
            "narration_cue_count": len(_safe_list(_safe_dict(edit_timeline.get("tracks")).get("narration"))),
            "shot_count": len(_build_shot_list(edit_timeline)),
            "unresolved_count": len(_safe_list(edit_timeline.get("unresolved_items")))
            + len(_safe_list(timeline_plan.get("unresolved_segments"))),
            "video_export_performed": False,
            "editor_project_exported": False,
        },
    }


def _build_narration_script(script: dict[str, Any]) -> dict[str, Any]:
    segments = []
    for segment in _safe_list(script.get("narration_segments")):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        segments.append(_script_segment(segment))

    ending_hook = script.get("ending_hook")
    if isinstance(ending_hook, dict) and str(ending_hook.get("text", "")).strip():
        segments.append(_script_segment(ending_hook))

    return {
        "schema_version": EXPORT_PACKAGE_SCHEMA_VERSION,
        "source_script_schema_version": str(script.get("schema_version", "")),
        "segments": segments,
        "metadata": {
            "segment_count": len(segments),
        },
    }


def _script_segment(segment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(segment.get("id", "")),
        "type": str(segment.get("type", "")),
        "text": str(segment.get("text", "")),
        "source_story_block_ids": [str(item) for item in segment.get("source_story_block_ids", [])],
        "source_ranges": _safe_list(segment.get("source_ranges")),
        "confidence": _safe_float(segment.get("confidence")),
        "reuse_policy": str(segment.get("reuse_policy", "")),
    }


def _script_text(narration_script: dict[str, Any]) -> str:
    lines = []
    for index, segment in enumerate(_safe_list(narration_script.get("segments")), start=1):
        segment_type = str(segment.get("type", ""))
        text = str(segment.get("text", ""))
        lines.append(f"{index:02d}. [{segment_type}] {text}")
    return "\n".join(lines) + ("\n" if lines else "")


def _build_shot_list(edit_timeline: dict[str, Any]) -> list[dict[str, Any]]:
    shots = []
    for clip in _safe_list(_safe_dict(edit_timeline.get("tracks")).get("video")):
        shots.append(
            {
                "id": str(clip.get("id", "")),
                "edit_segment_id": str(clip.get("edit_segment_id", "")),
                "source_timeline_item_id": str(clip.get("source_timeline_item_id", "")),
                "narration_segment_id": str(clip.get("narration_segment_id", "")),
                "source_story_block_id": str(clip.get("source_story_block_id", "")),
                "source_start": str(clip.get("source_start", "")),
                "source_end": str(clip.get("source_end", "")),
                "timeline_start": str(clip.get("timeline_start", "")),
                "timeline_end": str(clip.get("timeline_end", "")),
                "duration_ms": _safe_int(clip.get("duration_ms"), 0),
                "priority": _safe_int(clip.get("priority"), 0),
                "reuse_policy": str(clip.get("reuse_policy", "")),
            }
        )
    return shots


def _file_kind(filename: str) -> str:
    if filename == "manifest.json":
        return "manifest"
    if filename == "timeline.json":
        return "edit_timeline"
    if filename.startswith("narration_script"):
        return "narration_script"
    if filename == "shot_list.json":
        return "shot_list"
    if filename == "unresolved_items.json":
        return "unresolved_items"
    return "artifact"


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
