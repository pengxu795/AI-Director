"""Story pipeline for Module 2 and Module 2.5."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .analyzer import (
    CLIMAX_KEYWORDS,
    CONFLICT_KEYWORDS,
    CHARACTER_KEYWORDS,
    SATISFYING_KEYWORDS,
    SPOILER_KEYWORDS,
    TWIST_KEYWORDS,
    _build_main_plot,
    _extract_moments,
    _extract_relationships,
    _has_valid_source_range,
    _normalize_record,
    _pick_climax,
    _source_range,
    _timecode_to_ms,
)


SCHEMA_VERSION = "0.1"

ROLE_ALIASES = {
    "女主": ("女主",),
    "男主": ("男主",),
    "妈妈": ("妈妈", "母亲"),
    "爸爸": ("爸爸", "父亲"),
    "孩子": ("孩子",),
    "女儿": ("女儿",),
    "儿子": ("儿子",),
    "总裁": ("总裁",),
}

ROLE_TYPES = {
    "女主": "protagonist",
    "男主": "protagonist",
    "妈妈": "supporting",
    "爸爸": "supporting",
    "孩子": "supporting",
}


def run_story_pipeline(subtitles: list[dict[str, str]]) -> dict[str, Any]:
    """Run the story pipeline and return stable story JSON."""
    cleaned = [_normalize_record(record) for record in subtitles]
    cleaned = [record for record in cleaned if record["text"]]
    story_ordered = _sort_records_for_story_order(cleaned)

    scenes = split_scenes(story_ordered)
    characters = extract_characters(story_ordered)
    relationships = _extract_relationships(story_ordered)
    conflicts = _extract_moments(story_ordered, CONFLICT_KEYWORDS, "conflict")
    satisfying_points = _extract_moments(story_ordered, SATISFYING_KEYWORDS, "satisfying_point")
    twists = _extract_moments(story_ordered, TWIST_KEYWORDS, "twist")
    climax = _pick_climax(story_ordered)
    spoiler_warnings = _extract_moments(story_ordered, SPOILER_KEYWORDS, "spoiler_warning")
    story_blocks = build_story_blocks(story_ordered, conflicts, satisfying_points, twists, climax)
    episodes = build_episodes(story_ordered, scenes, story_blocks)
    source_range = _records_source_range(cleaned)

    return {
        "schema_version": SCHEMA_VERSION,
        "summary": {
            "subtitle_count": len(cleaned),
            "scene_count": len(scenes),
            "story_block_count": len(story_blocks),
            "episode_count": len(episodes),
            "start": source_range["start"],
            "end": source_range["end"],
        },
        "characters": characters,
        "relationships": relationships,
        "main_plot": _build_main_plot(cleaned, conflicts, twists),
        "episodes": episodes,
        "story_blocks": story_blocks,
        "scenes": scenes,
        "conflicts": conflicts,
        "satisfying_points": satisfying_points,
        "twists": twists,
        "climax": climax,
        "spoiler_warnings": spoiler_warnings,
    }


def extract_characters(subtitles: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Extract MVP character records with stable ids and aliases."""
    counts: Counter[str] = Counter()
    for record in subtitles:
        text = record["text"]
        for keyword in CHARACTER_KEYWORDS:
            if keyword in text:
                counts[keyword] += text.count(keyword)

    priority = {name: index for index, name in enumerate(CHARACTER_KEYWORDS)}
    ordered = sorted(
        counts.items(),
        key=lambda item: (-item[1], priority.get(item[0], len(priority))),
    )

    characters = []
    for index, (name, mentions) in enumerate(ordered, start=1):
        aliases = list(ROLE_ALIASES.get(name, (name,)))
        if name not in aliases:
            aliases.insert(0, name)
        characters.append(
            {
                "id": f"c{index:03d}",
                "name": name,
                "aliases": aliases,
                "role": ROLE_TYPES.get(name, "unknown"),
                "mentions": mentions,
            }
        )
    return characters


def split_scenes(subtitles: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Split subtitles into coarse story scenes for downstream modules."""
    if not subtitles:
        return []

    scenes: list[dict[str, Any]] = []
    current_records: list[dict[str, str]] = []
    current_type = "opening"

    for index, record in enumerate(subtitles):
        detected_type = _detect_scene_type(record["text"], index)
        if current_records and detected_type != current_type:
            scenes.append(_build_scene(len(scenes) + 1, current_type, current_records))
            current_records = []
        current_type = detected_type
        current_records.append(record)

    if current_records:
        scenes.append(_build_scene(len(scenes) + 1, current_type, current_records))
    return scenes


def build_story_blocks(
    subtitles: list[dict[str, str]],
    conflicts: list[dict[str, Any]],
    satisfying_points: list[dict[str, Any]],
    twists: list[dict[str, Any]],
    climax: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build ordered story blocks that Module 3 can turn into narration."""
    blocks: list[dict[str, Any]] = []
    if not subtitles:
        return blocks

    moments_by_text = _build_moment_lookup(conflicts, satisfying_points, twists, climax)
    climax_text = climax.get("text", "") if climax.get("reason") == "keyword_intensity" else ""
    used_text_types: set[tuple[str, str]] = set()

    for index, record in enumerate(subtitles):
        record_text = record["text"]
        block_type = _block_type_for_record(index, record, moments_by_text, climax_text)
        key = (record_text, block_type)
        if key in used_text_types:
            continue
        used_text_types.add(key)

        source_record = moments_by_text.get(record_text, {}).get(block_type, record)
        blocks.append(
            _story_block(
                len(blocks) + 1,
                block_type,
                source_record,
                _purpose_for_block_type(block_type),
            )
        )

    return blocks


def build_episodes(
    subtitles: list[dict[str, str]],
    scenes: list[dict[str, Any]],
    story_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build episode containers for future multi-episode workflows."""
    if not subtitles:
        return []

    source_range = _records_source_range(subtitles)
    return [
        {
            "id": "e001",
            "title": "Input 1",
            "kind": "input_container",
            "start": source_range["start"],
            "end": source_range["end"],
            "source_range": source_range,
            "scene_ids": [scene["id"] for scene in scenes],
            "story_block_ids": [block["id"] for block in story_blocks],
            "confidence": 0.5 if source_range["start"] else 0.2,
        }
    ]


def _detect_scene_type(text: str, index: int) -> str:
    if any(keyword in text for keyword in TWIST_KEYWORDS):
        return "twist"
    if any(keyword in text for keyword in CONFLICT_KEYWORDS):
        return "conflict"
    if any(keyword in text for keyword in SATISFYING_KEYWORDS):
        return "satisfying_point"
    if index == 0:
        return "opening"
    return "development"


def _build_scene(scene_id: int, scene_type: str, records: list[dict[str, str]]) -> dict[str, Any]:
    source_range = _records_source_range(records)
    return {
        "id": f"s{scene_id:03d}",
        "type": scene_type,
        "start": source_range["start"],
        "end": source_range["end"],
        "source_range": source_range,
        "summary": " ".join(record["text"] for record in records),
        "subtitle_count": len(records),
        "confidence": 0.55 if source_range["start"] else 0.25,
    }


def _story_block(
    block_id: int,
    block_type: str,
    record: dict[str, str],
    purpose: str,
) -> dict[str, Any]:
    source_range = record.get("source_range", _source_range(record))
    return {
        "id": f"b{block_id:03d}",
        "type": block_type,
        "summary": record["text"],
        "evidence": record.get("evidence", record["text"]),
        "start": source_range["start"],
        "end": source_range["end"],
        "source_range": source_range,
        "purpose": purpose,
        "confidence": record.get(
            "confidence",
            0.5 if _has_valid_source_range(record) else 0.2,
        ),
    }


def _build_moment_lookup(
    conflicts: list[dict[str, Any]],
    satisfying_points: list[dict[str, Any]],
    twists: list[dict[str, Any]],
    climax: dict[str, Any],
) -> dict[str, dict[str, dict[str, Any]]]:
    lookup: dict[str, dict[str, dict[str, Any]]] = {}
    for block_type, moments in (
        ("conflict", conflicts),
        ("satisfying_point", satisfying_points),
        ("twist", twists),
    ):
        for moment in moments:
            lookup.setdefault(moment["text"], {})[block_type] = moment
    if climax.get("text") and climax.get("reason") == "keyword_intensity":
        lookup.setdefault(climax["text"], {})["climax"] = climax
    return lookup


def _block_type_for_record(
    index: int,
    record: dict[str, str],
    moments_by_text: dict[str, dict[str, dict[str, Any]]],
    climax_text: str,
) -> str:
    moment_types = moments_by_text.get(record["text"], {})
    if record["text"] == climax_text and "climax" in moment_types:
        return "climax"
    if "twist" in moment_types:
        return "twist"
    if "satisfying_point" in moment_types:
        return "satisfying_point"
    if "conflict" in moment_types:
        return "conflict"
    if index == 0:
        return "opening"
    return "development"


def _purpose_for_block_type(block_type: str) -> str:
    purposes = {
        "opening": "建立开场信息",
        "development": "补充剧情发展",
        "conflict": "推进冲突升级",
        "satisfying_point": "呈现爽点",
        "twist": "制造剧情反转",
        "climax": "推到剧情高潮",
    }
    return purposes.get(block_type, "补充剧情信息")


def _records_source_range(records: list[dict[str, str]]) -> dict[str, str]:
    timed_records = []
    for record in records:
        start = _timecode_to_ms(record.get("start", ""))
        end = _timecode_to_ms(record.get("end", ""))
        if start is not None and end is not None and start <= end:
            timed_records.append((start, end, record))

    if not timed_records:
        return {"start": "", "end": ""}

    start_record = min(timed_records, key=lambda item: item[0])[2]
    end_record = max(timed_records, key=lambda item: item[1])[2]
    return {"start": start_record["start"], "end": end_record["end"]}


def _sort_records_for_story_order(records: list[dict[str, str]]) -> list[dict[str, str]]:
    def sort_key(item: tuple[int, dict[str, str]]) -> tuple[int, int, int]:
        index, record = item
        start = _timecode_to_ms(record.get("start", ""))
        end = _timecode_to_ms(record.get("end", ""))
        if start is None or end is None or start > end:
            return (1, index, index)
        return (0, start, index)

    return [record for _, record in sorted(enumerate(records), key=sort_key)]
