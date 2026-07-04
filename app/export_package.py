#!/usr/bin/env python3
"""CLI entry point for Module 6 export package generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.exporter import export_file_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate JSON/text export package from pipeline outputs.")
    parser.add_argument("edit_timeline", help="Path to Module 5 edit timeline .json file")
    parser.add_argument("script", help="Path to Module 3 script .json file")
    parser.add_argument("timeline", help="Path to Module 4 timeline .json file")
    parser.add_argument("output_dir", help="Directory for export package files")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    package = export_file_package(args.edit_timeline, args.script, args.timeline, args.output_dir)
    print(
        json.dumps(
            {
                "output_dir": args.output_dir,
                "file_count": len(package["manifest"]["files"]),
                "shot_count": package["manifest"]["metadata"]["shot_count"],
                "unresolved_count": package["manifest"]["metadata"]["unresolved_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
