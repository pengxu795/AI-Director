#!/usr/bin/env python3
"""CLI entry point for Module 2 story analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.story import analyze_file_to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze subtitle JSON into story analysis JSON.")
    parser.add_argument("input", help="Path to input subtitle .json file")
    parser.add_argument("output", help="Path to output story analysis .json file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    analysis = analyze_file_to_json(args.input, args.output)
    print(
        json.dumps(
            {
                "subtitle_count": analysis["summary"]["subtitle_count"],
                "output": args.output,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

