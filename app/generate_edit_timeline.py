#!/usr/bin/env python3
"""CLI entry point for Module 5 edit timeline generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.editing import generate_file_to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate edit timeline JSON from Module 4 timeline JSON.")
    parser.add_argument("input", help="Path to Module 4 timeline .json file")
    parser.add_argument("output", help="Path to output edit timeline .json file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    edit_timeline = generate_file_to_json(args.input, args.output)
    print(
        json.dumps(
            {
                "edit_segment_count": len(edit_timeline["edit_segments"]),
                "video_clip_count": len(edit_timeline["tracks"]["video"]),
                "unresolved_count": len(edit_timeline["unresolved_items"]),
                "output": args.output,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
