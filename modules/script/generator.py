"""Script generator for Module 3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCRIPT_SCHEMA_VERSION = "1.0"
SUPPORTED_STORY_SCHEMA_VERSION = "0.1"

SEGMENT_ORDER = (
    "hook",
    "setup",
    "development",
    "conflict",
    "twist",
    "climax",
)

SEGMENT_PURPOSES = {
    "hook": "开场钩子",
    "setup": "交代人物和关系",
    "development": "推进剧情",
    "conflict": "突出核心矛盾",
    "twist": "制造反转",
    "climax": "推向高潮",
    "ending_hook": "留下悬念",
}


def load_story_analysis_json(path: str | Path) -> dict[str, Any]:
    """Load Module 2 story analysis JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Story analysis JSON must be an object.")
    return data


def write_script_json(script: dict[str, Any], output_path: str | Path) -> None:
    """Write generated script JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_file_to_json(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Generate script JSON from story analysis JSON and write output."""
    script = generate_script(load_story_analysis_json(input_path))
    write_script_json(script, output_path)
    return script


def generate_script(story_analysis: dict[str, Any]) -> dict[str, Any]:
    """Generate traceable short-drama narration JSON using rules."""
    story_blocks = _safe_list(story_analysis.get("story_blocks"))
    characters = _safe_list(story_analysis.get("characters"))
    relationships = _safe_list(story_analysis.get("relationships"))
    conflicts = _safe_list(story_analysis.get("conflicts"))
    twists = _safe_list(story_analysis.get("twists"))
    climax = story_analysis.get("climax") if isinstance(story_analysis.get("climax"), dict) else {}
    source_schema_version = str(story_analysis.get("schema_version", ""))

    segments = _build_narration_segments(story_blocks, characters, relationships)
    ending_hook = _build_ending_hook(story_blocks, twists, conflicts, climax)

    return {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "source_story_schema_version": source_schema_version,
        "title_hooks": _build_title_hooks(story_blocks, conflicts, twists, climax),
        "narration_segments": segments,
        "ending_hook": ending_hook,
        "metadata": {
            "generator": "rule_based",
            "source_story_block_count": len(story_blocks),
            "narration_segment_count": len(segments),
            "has_valid_source_ranges": any(_valid_ranges_from_block(block) for block in story_blocks),
        },
    }


def _build_narration_segments(
    story_blocks: list[dict[str, Any]],
    characters: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not story_blocks:
        return []

    segments: list[dict[str, Any]] = []
    hook_block = _pick_hook_block(story_blocks)
    if hook_block:
        segments.append(_segment(len(segments) + 1, "hook", _hook_text(hook_block), [hook_block], "primary"))

    setup_text = _setup_text(characters, relationships)
    setup_blocks = _first_blocks(story_blocks, 1)
    if setup_text and setup_blocks:
        segments.append(_segment(len(segments) + 1, "setup", setup_text, setup_blocks, "primary"))

    for block in story_blocks:
        segment_type = _segment_type_for_block(block)
        if segment_type == "climax":
            text = f"直到这里，{block.get('summary', '')}"
        elif segment_type == "twist":
            text = f"可下一秒，{block.get('summary', '')}"
        elif segment_type == "conflict":
            text = f"真正的矛盾出现了：{block.get('summary', '')}"
        elif segment_type == "satisfying_point":
            text = f"观众最想看的转折来了：{block.get('summary', '')}"
        else:
            text = str(block.get("summary", ""))

        if text:
            segments.append(_segment(len(segments) + 1, segment_type, text, [block], "primary"))

    return _dedupe_segments(segments)


def _build_title_hooks(
    story_blocks: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    twists: list[dict[str, Any]],
    climax: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []
    for source in (twists, conflicts, [climax] if climax.get("text") else [], story_blocks):
        for item in source:
            block = _resolve_story_block(item, story_blocks)
            if not block:
                continue
            text = str(item.get("text") or item.get("summary") or block.get("summary") or "")
            if text:
                candidates.append(
                    {
                        "text": f"她怎么也没想到，{text}",
                        "source_story_block_ids": [str(block["id"])],
                        "source_ranges": _source_ranges_for_items([block]),
                        "confidence": _confidence_for_blocks([block]),
                        "reuse_policy": "primary",
                    }
                )
            if len(candidates) >= 3:
                return candidates
    return candidates


def _build_ending_hook(
    story_blocks: list[dict[str, Any]],
    twists: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    climax: dict[str, Any],
) -> dict[str, Any]:
    for sources in (twists, [climax] if climax.get("text") else [], conflicts):
        source = _last_non_empty(sources)
        if not source:
            continue
        block = _resolve_story_block(source, story_blocks)
        if not block:
            return _empty_ending_hook()
        return _ending_hook_from_source(source, block, climax)

    block = _last_non_empty(story_blocks)
    if not block:
        return _empty_ending_hook()
    return _ending_hook_from_source(block, block, climax)


def _ending_hook_from_source(
    source: dict[str, Any],
    block: dict[str, Any],
    climax: dict[str, Any],
) -> dict[str, Any]:
    text = str(source.get("summary") or source.get("text") or block.get("summary") or "")
    if climax.get("text") and text == climax.get("text"):
        text = f"而这声称呼背后，还藏着更大的秘密。"
    else:
        text = f"可真正的答案，还没有揭开。"

    return {
        "id": "n-ending",
        "type": "ending_hook",
        "text": text,
        "source_story_block_ids": [str(block["id"])],
        "source_ranges": _source_ranges_for_items([block]),
        "confidence": _confidence_for_blocks([block]),
        "reuse_policy": "callback",
    }


def _empty_ending_hook() -> dict[str, Any]:
    return {
        "id": "n-ending",
        "type": "ending_hook",
        "text": "",
        "source_story_block_ids": [],
        "source_ranges": [],
        "confidence": 0.0,
        "reuse_policy": "callback",
    }


def _segment(
    index: int,
    segment_type: str,
    text: str,
    blocks: list[dict[str, Any]],
    reuse_policy: str,
) -> dict[str, Any]:
    return {
        "id": f"n{index:03d}",
        "type": segment_type,
        "text": text,
        "source_story_block_ids": [str(block.get("id", "")) for block in blocks if block.get("id")],
        "source_ranges": _source_ranges_for_items(blocks),
        "confidence": _confidence_for_blocks(blocks),
        "reuse_policy": reuse_policy,
    }


def _pick_hook_block(story_blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    priority = {"twist": 0, "climax": 1, "conflict": 2, "satisfying_point": 3}
    ordered = sorted(
        story_blocks,
        key=lambda block: (priority.get(str(block.get("type", "")), 9), -float(block.get("confidence", 0.0))),
    )
    return ordered[0] if ordered else None


def _hook_text(block: dict[str, Any]) -> str:
    summary = str(block.get("summary", ""))
    if not summary:
        return ""
    return f"她以为一切已经结束，没想到{summary}"


def _setup_text(characters: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> str:
    names = [str(character.get("name", "")) for character in characters[:3] if character.get("name")]
    relationship = str(relationships[0].get("type", "")) if relationships else ""
    if names and relationship:
        return f"故事里，{'、'.join(names)}之间的关系并不简单，{relationship}。"
    if names:
        return f"故事先从{'、'.join(names)}说起。"
    return ""


def _segment_type_for_block(block: dict[str, Any]) -> str:
    block_type = str(block.get("type", "development"))
    if block_type in SEGMENT_ORDER:
        return block_type
    if block_type == "satisfying_point":
        return "development"
    return "development"


def _dedupe_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_exact: set[tuple[str, str, tuple[str, ...]]] = set()
    seen_primary_use: set[tuple[str, tuple[str, ...]]] = set()
    for segment in segments:
        source_ids = tuple(segment["source_story_block_ids"])
        exact_key = (segment["type"], segment["text"], source_ids)
        primary_key = (segment["type"], source_ids)
        if exact_key in seen_exact:
            continue
        if segment["reuse_policy"] == "primary" and primary_key in seen_primary_use:
            segment["reuse_policy"] = "duplicate"
        seen_exact.add(exact_key)
        if segment["reuse_policy"] == "primary":
            seen_primary_use.add(primary_key)
        segment["id"] = f"n{len(deduped) + 1:03d}"
        deduped.append(segment)
    return deduped


def _source_ranges_for_items(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    ranges = []
    for item in items:
        source_range = item.get("source_range")
        if isinstance(source_range, dict) and source_range.get("start") and source_range.get("end"):
            ranges.append({"start": str(source_range["start"]), "end": str(source_range["end"])})
    return ranges


def _confidence_for_blocks(blocks: list[dict[str, Any]]) -> float:
    if not blocks:
        return 0.0
    confidences = []
    for block in blocks:
        try:
            confidences.append(float(block.get("confidence", 0.0)))
        except (TypeError, ValueError):
            confidences.append(0.0)
    if not confidences:
        return 0.0
    if not all(block.get("id") for block in blocks):
        return 0.0
    if not any(_source_ranges_for_items([block]) for block in blocks):
        return min(max(confidences), 0.2)
    return round(sum(confidences) / len(confidences), 2)


def _resolve_story_block(item: dict[str, Any], story_blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    item_id = item.get("id")
    if item_id:
        for block in story_blocks:
            if item_id == block.get("id"):
                return block
    source_range = item.get("source_range")
    if isinstance(source_range, dict) and source_range.get("start") and source_range.get("end"):
        for block in story_blocks:
            if block.get("source_range") == source_range:
                return block
    text = item.get("text") or item.get("summary")
    for block in story_blocks:
        if text and text == block.get("summary"):
            return block
    return None


def _valid_ranges_from_block(block: dict[str, Any]) -> list[dict[str, str]]:
    return _source_ranges_for_items([block])


def _first_blocks(story_blocks: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    return story_blocks[:count]


def _last_non_empty(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in reversed(items):
        if item.get("summary") or item.get("text"):
            return item
    return None


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
