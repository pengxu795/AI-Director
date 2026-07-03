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
    _normalize_record,
    _pick_climax,
)


SCHEMA_VERSION = "0.1"

ROLE_ALIASES = {
    "女主": ("女主", "妈妈"),
    "男主": ("男主", "爸爸", "总裁"),
    "妈妈": ("妈妈", "母亲"),
    "爸爸": ("爸爸", "父亲"),
    "孩子": ("孩子", "女儿", "儿子"),
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

    scenes = split_scenes(cleaned)
    characters = extract_characters(cleaned)
    relationships = _extract_relationships(cleaned)
    conflicts = _extract_moments(cleaned, CONFLICT_KEYWORDS, "conflict")
    satisfying_points = _extract_moments(cleaned, SATISFYING_KEYWORDS, "satisfying_point")
    twists = _extract_moments(cleaned, TWIST_KEYWORDS, "twist")
    climax = _pick_climax(cleaned)
    spoiler_warnings = _extract_moments(cleaned, SPOILER_KEYWORDS, "spoiler_warning")
    story_blocks = build_story_blocks(cleaned, conflicts, twists, climax)
    episodes = build_episodes(cleaned, scenes, story_blocks)

    return {
        "schema_version": SCHEMA_VERSION,
        "summary": {
            "subtitle_count": len(cleaned),
            "scene_count": len(scenes),
            "story_block_count": len(story_blocks),
            "episode_count": len(episodes),
            "start": cleaned[0]["start"] if cleaned else "",
            "end": cleaned[-1]["end"] if cleaned else "",
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
    twists: list[dict[str, Any]],
    climax: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build compact story blocks that Module 3 can turn into narration."""
    blocks: list[dict[str, Any]] = []
    if not subtitles:
        return blocks

    blocks.append(_story_block(1, "opening", subtitles[0], "建立开场信息"))

    if conflicts:
        blocks.append(_story_block(len(blocks) + 1, "conflict", conflicts[0], "抛出核心矛盾"))

    if twists:
        blocks.append(_story_block(len(blocks) + 1, "twist", twists[-1], "制造剧情反转"))

    if climax.get("text"):
        block_type = "climax"
        if blocks and blocks[-1]["summary"] == climax["text"]:
            blocks[-1]["type"] = block_type
            blocks[-1]["purpose"] = "推到剧情高潮"
        else:
            blocks.append(_story_block(len(blocks) + 1, block_type, climax, "推到剧情高潮"))

    return blocks


def build_episodes(
    subtitles: list[dict[str, str]],
    scenes: list[dict[str, Any]],
    story_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build episode containers for future multi-episode workflows."""
    if not subtitles:
        return []

    return [
        {
            "id": "e001",
            "title": "Episode 1",
            "start": subtitles[0]["start"],
            "end": subtitles[-1]["end"],
            "source_range": {
                "start": subtitles[0]["start"],
                "end": subtitles[-1]["end"],
            },
            "scene_ids": [scene["id"] for scene in scenes],
            "story_block_ids": [block["id"] for block in story_blocks],
            "confidence": 0.5,
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
    return {
        "id": f"s{scene_id:03d}",
        "type": scene_type,
        "start": records[0]["start"],
        "end": records[-1]["end"],
        "source_range": {
            "start": records[0]["start"],
            "end": records[-1]["end"],
        },
        "summary": " ".join(record["text"] for record in records),
        "subtitle_count": len(records),
        "confidence": 0.55,
    }


def _story_block(
    block_id: int,
    block_type: str,
    record: dict[str, str],
    purpose: str,
) -> dict[str, Any]:
    return {
        "id": f"b{block_id:03d}",
        "type": block_type,
        "summary": record["text"],
        "evidence": record.get("evidence", record["text"]),
        "start": record["start"],
        "end": record["end"],
        "source_range": record.get(
            "source_range",
            {
                "start": record["start"],
                "end": record["end"],
            },
        ),
        "purpose": purpose,
        "confidence": record.get("confidence", 0.5),
    }
