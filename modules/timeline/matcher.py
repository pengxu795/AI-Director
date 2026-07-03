"""Shot matcher and timeline planner for Module 4."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


TIMELINE_SCHEMA_VERSION = "1.0"
TIMECODE_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$")


def load_story_analysis_json(path: str | Path) -> dict[str, Any]:
    """Load Module 2 story analysis JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Story analysis JSON must be an object.")
    return data


def load_script_json(path: str | Path) -> dict[str, Any]:
    """Load Module 3 script JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Script JSON must be an object.")
    return data


def load_subtitles_json(path: str | Path) -> list[dict[str, Any]]:
    """Load subtitle segments JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Subtitle JSON must be a list.")
    return [item for item in data if isinstance(item, dict)]


def write_timeline_json(timeline: dict[str, Any], output_path: str | Path) -> None:
    """Write generated timeline JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_file_to_json(
    story_path: str | Path,
    script_path: str | Path,
    subtitles_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    """Generate timeline JSON from story, script, and subtitle JSON files."""
    timeline = generate_timeline(
        load_story_analysis_json(story_path),
        load_script_json(script_path),
        load_subtitles_json(subtitles_path),
    )
    write_timeline_json(timeline, output_path)
    return timeline


def generate_timeline(
    story_analysis: dict[str, Any],
    script: dict[str, Any],
    subtitles: list[dict[str, Any]],
) -> dict[str, Any]:
    """Map script narration segments to traceable video ranges without editing video."""
    story_blocks = _safe_list(story_analysis.get("story_blocks"))
    blocks_by_id = {
        str(block.get("id")): block
        for block in story_blocks
        if block.get("id") is not None and str(block.get("id"))
    }
    source_bounds = _valid_subtitle_bounds(subtitles)
    used_block_ids: set[str] = set()
    timeline_items: list[dict[str, Any]] = []
    unresolved_segments: list[dict[str, str]] = []

    for segment in _script_timeline_segments(script):
        if not str(segment.get("text", "")).strip():
            continue

        item, reason = _timeline_item_for_segment(
            len(timeline_items) + 1,
            segment,
            blocks_by_id,
            source_bounds,
            used_block_ids,
        )
        timeline_items.append(item)
        if item["status"] == "unresolved":
            unresolved_segments.append(
                {
                    "narration_segment_id": item["narration_segment_id"],
                    "segment_type": item["segment_type"],
                    "reason": reason,
                }
            )
        if item["status"] in {"matched", "partial"}:
            used_block_ids.update(range_item["source_story_block_id"] for range_item in item["video_ranges"])

    return {
        "schema_version": TIMELINE_SCHEMA_VERSION,
        "source_script_schema_version": str(script.get("schema_version", "")),
        "timeline": timeline_items,
        "unresolved_segments": unresolved_segments,
        "metadata": {
            "planner": "rule_based",
            "timeline_item_count": len(timeline_items),
            "unresolved_count": len(unresolved_segments),
            "source_story_block_count": len(story_blocks),
            "source_subtitle_range": _range_dict_from_bounds(source_bounds),
            "video_editing_performed": False,
        },
    }


def _timeline_item_for_segment(
    index: int,
    segment: dict[str, Any],
    blocks_by_id: dict[str, dict[str, Any]],
    source_bounds: tuple[int, int] | None,
    used_block_ids: set[str],
) -> tuple[dict[str, Any], str]:
    segment_id = str(segment.get("id", ""))
    segment_type = str(segment.get("type", "development"))
    text = str(segment.get("text", ""))
    source_ids = _unique_block_ids(segment.get("source_story_block_ids"))

    if not source_ids:
        return _unresolved_item(index, segment_id, segment_type, text, "missing_source_story_block_ids"), (
            "missing_source_story_block_ids"
        )

    missing_ids = [block_id for block_id in source_ids if block_id not in blocks_by_id]
    if missing_ids:
        return _unresolved_item(index, segment_id, segment_type, text, "source_story_block_id_not_found"), (
            "source_story_block_id_not_found"
        )

    ranges: list[dict[str, Any]] = []
    invalid_ids: list[str] = []
    for block_id in source_ids:
        block_range = _valid_block_range(blocks_by_id[block_id], source_bounds)
        if not block_range:
            invalid_ids.append(block_id)
            continue
        ranges.append(
            {
                "start": block_range["start"],
                "end": block_range["end"],
                "source_story_block_id": block_id,
                "_start_ms": block_range["start_ms"],
            }
        )

    if not ranges:
        return _unresolved_item(index, segment_id, segment_type, text, "no_valid_video_range"), "no_valid_video_range"

    ranges.sort(key=lambda item: (item["_start_ms"], item["source_story_block_id"]))
    video_ranges = [
        {
            "start": range_item["start"],
            "end": range_item["end"],
            "source_story_block_id": range_item["source_story_block_id"],
            "priority": priority,
        }
        for priority, range_item in enumerate(ranges, start=1)
    ]
    matched_ids = {range_item["source_story_block_id"] for range_item in video_ranges}
    status = "partial" if invalid_ids or len(matched_ids) < len(set(source_ids)) else "matched"
    reuse_policy = _reuse_policy_for_segment(segment, matched_ids, used_block_ids)
    confidence = _confidence_for_segment(segment, [blocks_by_id[block_id] for block_id in matched_ids], status)

    return (
        {
            "id": f"t{index:03d}",
            "narration_segment_id": segment_id,
            "segment_type": segment_type,
            "text": text,
            "video_ranges": video_ranges,
            "selection_reason": "matched_by_story_block_source_range",
            "reuse_policy": reuse_policy,
            "confidence": confidence,
            "status": status,
        },
        "matched_by_story_block_source_range",
    )


def _unresolved_item(index: int, segment_id: str, segment_type: str, text: str, reason: str) -> dict[str, Any]:
    return {
        "id": f"t{index:03d}",
        "narration_segment_id": segment_id,
        "segment_type": segment_type,
        "text": text,
        "video_ranges": [],
        "selection_reason": reason,
        "reuse_policy": "unresolved",
        "confidence": 0.0,
        "status": "unresolved",
    }


def _script_timeline_segments(script: dict[str, Any]) -> list[dict[str, Any]]:
    segments = _safe_list(script.get("narration_segments"))
    ending_hook = script.get("ending_hook")
    if isinstance(ending_hook, dict):
        segments.append(ending_hook)
    return segments


def _valid_block_range(block: dict[str, Any], source_bounds: tuple[int, int] | None) -> dict[str, Any] | None:
    source_range = block.get("source_range")
    if not isinstance(source_range, dict):
        return None
    start = str(source_range.get("start", ""))
    end = str(source_range.get("end", ""))
    start_ms = _timecode_to_ms(start)
    end_ms = _timecode_to_ms(end)
    if start_ms is None or end_ms is None or start_ms > end_ms:
        return None
    if source_bounds and (start_ms < source_bounds[0] or end_ms > source_bounds[1]):
        return None
    if source_bounds is None:
        return None
    return {"start": start, "end": end, "start_ms": start_ms, "end_ms": end_ms}


def _valid_subtitle_bounds(subtitles: list[dict[str, Any]]) -> tuple[int, int] | None:
    valid_ranges = []
    for subtitle in subtitles:
        start_ms = _timecode_to_ms(str(subtitle.get("start", "")))
        end_ms = _timecode_to_ms(str(subtitle.get("end", "")))
        if start_ms is None or end_ms is None or start_ms > end_ms:
            continue
        valid_ranges.append((start_ms, end_ms))
    if not valid_ranges:
        return None
    return min(start for start, _ in valid_ranges), max(end for _, end in valid_ranges)


def _range_dict_from_bounds(bounds: tuple[int, int] | None) -> dict[str, str]:
    if not bounds:
        return {"start": "", "end": ""}
    return {"start": _ms_to_timecode(bounds[0]), "end": _ms_to_timecode(bounds[1])}


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


def _reuse_policy_for_segment(
    segment: dict[str, Any],
    matched_ids: set[str],
    used_block_ids: set[str],
) -> str:
    if str(segment.get("type", "")) == "ending_hook" and matched_ids & used_block_ids:
        return "callback"
    if matched_ids & used_block_ids:
        return "duplicate"
    return "primary"


def _confidence_for_segment(segment: dict[str, Any], blocks: list[dict[str, Any]], status: str) -> float:
    if not blocks:
        return 0.0
    block_confidences = [_safe_float(block.get("confidence")) for block in blocks]
    source_confidence = _safe_float(segment.get("confidence"))
    confidence = min(source_confidence, sum(block_confidences) / len(block_confidences))
    if status == "partial":
        confidence = min(confidence, 0.5)
    return round(max(confidence, 0.0), 2)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _safe_scalar_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    return value


def _unique_block_ids(value: Any) -> list[str]:
    block_ids = []
    seen = set()
    for block_id in _safe_scalar_list(value):
        normalized = str(block_id)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        block_ids.append(normalized)
    return block_ids
