"""Edit timeline builder for Module 5.

This module creates an editor-agnostic JSON timeline from Module 4 planning data.
It does not read, cut, render, or export video files.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


EDIT_TIMELINE_SCHEMA_VERSION = "1.0"
TIMECODE_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$")


def load_timeline_json(path: str | Path) -> dict[str, Any]:
    """Load Module 4 timeline JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Timeline JSON must be an object.")
    return data


def write_edit_timeline_json(edit_timeline: dict[str, Any], output_path: str | Path) -> None:
    """Write generated edit timeline JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(edit_timeline, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_file_to_json(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Generate edit timeline JSON from Module 4 timeline JSON and write output."""
    edit_timeline = build_edit_timeline(load_timeline_json(input_path))
    write_edit_timeline_json(edit_timeline, output_path)
    return edit_timeline


def build_edit_timeline(timeline_plan: dict[str, Any]) -> dict[str, Any]:
    """Build a sequential edit decision timeline from matched video ranges."""
    source_items = _safe_list(timeline_plan.get("timeline"))
    cursor_ms = 0
    edit_segments: list[dict[str, Any]] = []
    video_track: list[dict[str, Any]] = []
    narration_track: list[dict[str, Any]] = []
    unresolved_items: list[dict[str, Any]] = []

    for item in source_items:
        if not str(item.get("text", "")).strip():
            continue

        clips, rejected_ranges, cursor_ms = _clips_for_item(item, len(video_track), cursor_ms)
        unresolved_items.extend(rejected_ranges)
        if not clips:
            continue

        segment_id = f"e{len(edit_segments) + 1:03d}"
        clip_ids = []
        for clip in clips:
            clip["edit_segment_id"] = segment_id
            video_track.append(clip)
            clip_ids.append(clip["id"])

        narration_cue = _narration_cue_for_item(item, segment_id, clip_ids, clips)
        narration_track.append(narration_cue)
        edit_segments.append(
            {
                "id": segment_id,
                "source_timeline_item_id": str(item.get("id", "")),
                "narration_segment_id": str(item.get("narration_segment_id", "")),
                "segment_type": str(item.get("segment_type", "")),
                "text": str(item.get("text", "")),
                "clip_ids": clip_ids,
                "narration_cue_id": narration_cue["id"],
                "timeline_start": clips[0]["timeline_start"],
                "timeline_end": clips[-1]["timeline_end"],
                "duration_ms": sum(clip["duration_ms"] for clip in clips),
                "reuse_policy": str(item.get("reuse_policy", "")),
                "source_status": str(item.get("status", "")),
                "confidence": _safe_float(item.get("confidence")),
            }
        )

    return {
        "schema_version": EDIT_TIMELINE_SCHEMA_VERSION,
        "source_timeline_schema_version": str(timeline_plan.get("schema_version", "")),
        "sequence": {
            "id": "seq001",
            "start": _ms_to_timecode(0),
            "end": _ms_to_timecode(cursor_ms),
            "duration_ms": cursor_ms,
        },
        "edit_segments": edit_segments,
        "tracks": {
            "video": video_track,
            "narration": narration_track,
        },
        "unresolved_items": unresolved_items,
        "metadata": {
            "builder": "rule_based",
            "source_timeline_item_count": len(source_items),
            "edit_segment_count": len(edit_segments),
            "video_clip_count": len(video_track),
            "narration_cue_count": len(narration_track),
            "unresolved_count": len(unresolved_items),
            "video_editing_performed": False,
        },
    }


def _clips_for_item(
    item: dict[str, Any],
    existing_clip_count: int,
    cursor_ms: int,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    if str(item.get("status", "")) == "unresolved":
        return [], [_unresolved_item(item, None, "item_marked_unresolved")], cursor_ms

    clips = []
    rejected_ranges = []
    for source_range in _safe_list(item.get("video_ranges")):
        start = str(source_range.get("start", ""))
        end = str(source_range.get("end", ""))
        start_ms = _timecode_to_ms(start)
        end_ms = _timecode_to_ms(end)
        if start_ms is None or end_ms is None:
            rejected_ranges.append(_unresolved_item(item, source_range, "invalid_timecode"))
            continue
        if start_ms >= end_ms:
            rejected_ranges.append(_unresolved_item(item, source_range, "non_positive_duration"))
            continue

        duration_ms = end_ms - start_ms
        timeline_start_ms = cursor_ms
        timeline_end_ms = cursor_ms + duration_ms
        clips.append(
            {
                "id": f"v{existing_clip_count + len(clips) + 1:03d}",
                "source_timeline_item_id": str(item.get("id", "")),
                "narration_segment_id": str(item.get("narration_segment_id", "")),
                "source_story_block_id": str(source_range.get("source_story_block_id", "")),
                "source_start": start,
                "source_end": end,
                "timeline_start": _ms_to_timecode(timeline_start_ms),
                "timeline_end": _ms_to_timecode(timeline_end_ms),
                "duration_ms": duration_ms,
                "priority": _safe_int(source_range.get("priority"), len(clips) + 1),
                "reuse_policy": str(source_range.get("reuse_policy", "")),
            }
        )
        cursor_ms = timeline_end_ms

    if not clips and not rejected_ranges:
        rejected_ranges.append(_unresolved_item(item, None, "missing_or_invalid_range"))

    return clips, rejected_ranges, cursor_ms


def _narration_cue_for_item(
    item: dict[str, Any],
    edit_segment_id: str,
    clip_ids: list[str],
    clips: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": f"a{int(edit_segment_id[1:]):03d}",
        "edit_segment_id": edit_segment_id,
        "source_timeline_item_id": str(item.get("id", "")),
        "narration_segment_id": str(item.get("narration_segment_id", "")),
        "text": str(item.get("text", "")),
        "timeline_start": clips[0]["timeline_start"],
        "timeline_end": clips[-1]["timeline_end"],
        "duration_ms": sum(clip["duration_ms"] for clip in clips),
        "clip_ids": clip_ids,
        "confidence": _safe_float(item.get("confidence")),
    }


def _unresolved_item(item: dict[str, Any], source_range: dict[str, Any] | None, reason: str) -> dict[str, str]:
    source_range = source_range if isinstance(source_range, dict) else {}
    return {
        "source_timeline_item_id": str(item.get("id", "")),
        "narration_segment_id": str(item.get("narration_segment_id", "")),
        "segment_type": str(item.get("segment_type", "")),
        "source_story_block_id": str(source_range.get("source_story_block_id", "")),
        "source_start": str(source_range.get("start", "")),
        "source_end": str(source_range.get("end", "")),
        "reason": reason,
    }


def _timecode_to_ms(value: str) -> int | None:
    match = TIMECODE_PATTERN.match(value)
    if not match:
        return None
    hours, minutes, seconds, milliseconds = (int(part) for part in match.groups())
    if minutes > 59 or seconds > 59:
        return None
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds


def _ms_to_timecode(value: int) -> str:
    hours, remainder = divmod(value, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


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
