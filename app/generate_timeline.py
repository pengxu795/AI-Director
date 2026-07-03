#!/usr/bin/env python3
"""CLI entry point for Module 4 timeline planning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.timeline import generate_file_to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate timeline JSON from story, script, and subtitle JSON.")
    parser.add_argument("story", help="Path to Module 2 story analysis .json file")
    parser.add_argument("script", help="Path to Module 3 script .json file")
    parser.add_argument("subtitles", help="Path to original subtitle segments .json file")
    parser.add_argument("output", help="Path to output timeline .json file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    timeline = generate_file_to_json(args.story, args.script, args.subtitles, args.output)
    print(
        json.dumps(
            {
                "timeline_item_count": len(timeline["timeline"]),
                "unresolved_count": len(timeline["unresolved_segments"]),
                "output": args.output,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
