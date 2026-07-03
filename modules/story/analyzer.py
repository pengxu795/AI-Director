"""Story analyzer compatibility layer for Module 2."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


CHARACTER_KEYWORDS = (
    "女主",
    "男主",
    "母亲",
    "父亲",
    "妈妈",
    "爸爸",
    "孩子",
    "女儿",
    "儿子",
    "姐姐",
    "妹妹",
    "哥哥",
    "弟弟",
    "丈夫",
    "妻子",
    "总裁",
)

RELATIONSHIP_PATTERNS = (
    (re.compile(r"不是.*亲生女儿"), "亲子关系被否定"),
    (re.compile(r"不是.*亲生儿子"), "亲子关系被否定"),
    (re.compile(r"喊.*妈妈"), "亲子身份产生关联"),
    (re.compile(r"喊.*爸爸"), "亲子身份产生关联"),
    (re.compile(r"隐瞒"), "存在长期隐瞒"),
    (re.compile(r"背叛|出轨"), "亲密关系破裂"),
)

CONFLICT_KEYWORDS = ("不是", "隐瞒", "背叛", "争吵", "威胁", "报复", "误会", "赶走", "陷害")
SATISFYING_KEYWORDS = ("终于", "真相", "反击", "打脸", "揭穿", "逆袭", "报复", "救下")
TWIST_KEYWORDS = ("可", "却", "原来", "竟然", "没想到", "突然", "反而")
SPOILER_KEYWORDS = ("真相", "凶手", "幕后", "身份", "亲生", "结局")
CLIMAX_KEYWORDS = CONFLICT_KEYWORDS + SATISFYING_KEYWORDS + TWIST_KEYWORDS


def load_subtitles_json(path: str | Path) -> list[dict[str, str]]:
    """Load subtitle records from a JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Subtitle JSON must be a list of records.")
    return data


def write_story_analysis_json(analysis: dict[str, Any], output_path: str | Path) -> None:
    """Write story analysis to a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")


def analyze_file_to_json(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Analyze subtitle JSON and write story analysis output."""
    analysis = analyze_story(load_subtitles_json(input_path))
    write_story_analysis_json(analysis, output_path)
    return analysis


def analyze_story(subtitles: list[dict[str, str]]) -> dict[str, Any]:
    """Analyze ordered subtitle records into story pipeline JSON."""
    from .pipeline import run_story_pipeline

    return run_story_pipeline(subtitles)


def _normalize_record(record: dict[str, str]) -> dict[str, str]:
    return {
        "start": str(record.get("start", "")).strip(),
        "end": str(record.get("end", "")).strip(),
        "text": str(record.get("text", "")).strip(),
    }


def _extract_relationships(subtitles: list[dict[str, str]]) -> list[dict[str, str]]:
    relationships: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for record in subtitles:
        for pattern, relation_type in RELATIONSHIP_PATTERNS:
            if pattern.search(record["text"]):
                key = (relation_type, record["text"])
                if key in seen:
                    continue
                seen.add(key)
                relationships.append(
                    {
                        "type": relation_type,
                        "evidence": record["text"],
                        "start": record["start"],
                        "end": record["end"],
                    }
                )
    return relationships


def _extract_moments(
    subtitles: list[dict[str, str]],
    keywords: tuple[str, ...],
    moment_type: str,
) -> list[dict[str, str]]:
    moments: list[dict[str, str]] = []
    for record in subtitles:
        matched = [keyword for keyword in keywords if keyword in record["text"]]
        if matched:
            moments.append(
                {
                    "type": moment_type,
                    "text": record["text"],
                    "start": record["start"],
                    "end": record["end"],
                    "reason": "、".join(matched),
                }
            )
    return moments


def _pick_climax(subtitles: list[dict[str, str]]) -> dict[str, str]:
    if not subtitles:
        return {"text": "", "start": "", "end": "", "reason": ""}

    scored = []
    for index, record in enumerate(subtitles):
        keyword_score = sum(1 for keyword in CLIMAX_KEYWORDS if keyword in record["text"])
        position_score = index / max(len(subtitles) - 1, 1)
        scored.append((keyword_score * 2 + position_score, record, keyword_score))

    _, record, keyword_score = max(scored, key=lambda item: item[0])
    reason = "keyword_intensity" if keyword_score else "latest_story_beat"
    return {
        "text": record["text"],
        "start": record["start"],
        "end": record["end"],
        "reason": reason,
    }


def _build_main_plot(
    subtitles: list[dict[str, str]],
    conflicts: list[dict[str, str]],
    twists: list[dict[str, str]],
) -> str:
    if not subtitles:
        return ""

    first = subtitles[0]["text"]
    last = subtitles[-1]["text"]
    conflict_text = conflicts[0]["text"] if conflicts else first
    twist_text = twists[-1]["text"] if twists else last

    if conflict_text == twist_text:
        return f"剧情围绕“{conflict_text}”展开，并推动人物关系继续升级。"
    return f"剧情从“{first}”开始，以“{conflict_text}”制造核心矛盾，并通过“{twist_text}”推进反转。"
