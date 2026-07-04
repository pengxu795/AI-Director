"""CLI for Module 11 FCPXML manual import result capture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.adapters import build_fcpxml_acceptance_record, write_fcpxml_acceptance_record


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a manual FCPXML import acceptance result.")
    parser.add_argument("protocol_json", help="Path to Module 10 acceptance protocol JSON.")
    parser.add_argument("manual_result_json", help="Path to manually filled result JSON.")
    parser.add_argument("output_json", help="Output acceptance record JSON path.")
    args = parser.parse_args()

    protocol = json.loads(Path(args.protocol_json).read_text(encoding="utf-8"))
    manual_result = json.loads(Path(args.manual_result_json).read_text(encoding="utf-8"))
    record = build_fcpxml_acceptance_record(protocol, manual_result)
    result = write_fcpxml_acceptance_record(record, args.output_json)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
