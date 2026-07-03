#!/usr/bin/env python3
"""CLI entry point for Module 3 script generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.script import generate_file_to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate narration script JSON from story analysis JSON.")
    parser.add_argument("input", help="Path to input story analysis .json file")
    parser.add_argument("output", help="Path to output script .json file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    script = generate_file_to_json(args.input, args.output)
    print(
        json.dumps(
            {
                "segment_count": len(script["narration_segments"]),
                "output": args.output,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

