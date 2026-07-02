"""SRT subtitle parser for Module 1."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


TIMECODE_PATTERN = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})"
)


def normalize_timecode(value: str) -> str:
    """Normalize SRT timecode separator from comma to dot."""
    return value.strip().replace(",", ".")


def parse_srt(content: str) -> list[dict[str, str]]:
    """Parse SRT content into ordered subtitle JSON records.

    The returned records keep only the stable MVP fields:
    start, end, and text.
    """
    blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n").replace("\r", "\n").strip())
    subtitles: list[dict[str, str]] = []

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        time_line_index = None
        match = None
        for index, line in enumerate(lines):
            match = TIMECODE_PATTERN.search(line)
            if match:
                time_line_index = index
                break

        if match is None or time_line_index is None:
            continue

        text_lines = lines[time_line_index + 1 :]
        text = " ".join(text_lines).strip()
        if not text:
            continue

        subtitles.append(
            {
                "start": normalize_timecode(match.group("start")),
                "end": normalize_timecode(match.group("end")),
                "text": text,
            }
        )

    return subtitles


def parse_srt_file(path: str | Path) -> list[dict[str, str]]:
    """Read and parse an SRT file."""
    srt_path = Path(path)
    return parse_srt(srt_path.read_text(encoding="utf-8-sig"))


def write_subtitles_json(subtitles: list[dict[str, str]], output_path: str | Path) -> None:
    """Write parsed subtitles to a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(subtitles, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_file_to_json(input_path: str | Path, output_path: str | Path) -> list[dict[str, Any]]:
    """Parse SRT file and write JSON output."""
    subtitles = parse_srt_file(input_path)
    write_subtitles_json(subtitles, output_path)
    return subtitles

