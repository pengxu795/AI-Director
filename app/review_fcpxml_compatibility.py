"""CLI for Module 12 FCPXML compatibility findings review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.adapters import build_fcpxml_compatibility_review, write_fcpxml_compatibility_review


def main() -> None:
    parser = argparse.ArgumentParser(description="Review a Module 11 FCPXML acceptance record and propose remediation.")
    parser.add_argument("acceptance_record_json", help="Path to Module 11 acceptance record JSON.")
    parser.add_argument("output_json", help="Output compatibility review JSON path.")
    args = parser.parse_args()

    record = json.loads(Path(args.acceptance_record_json).read_text(encoding="utf-8"))
    review = build_fcpxml_compatibility_review(record)
    result = write_fcpxml_compatibility_review(review, args.output_json)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
