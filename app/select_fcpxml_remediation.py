"""CLI for Module 13 evidence-backed remediation selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.adapters import build_fcpxml_remediation_selection, write_fcpxml_remediation_selection


def main() -> None:
    parser = argparse.ArgumentParser(description="Select one evidence-backed Module 12 remediation item.")
    parser.add_argument("compatibility_review_json", help="Path to Module 12 compatibility review JSON.")
    parser.add_argument("output_json", help="Output remediation selection JSON path.")
    parser.add_argument("--remediation-id", required=True, help="Remediation item id to select.")
    parser.add_argument("--selected-by", required=True, help="Human reviewer selecting the remediation.")
    parser.add_argument("--selected-at", required=True, help="Selection timestamp.")
    parser.add_argument("--selection-reason", required=True, help="Reason for selecting this remediation.")
    args = parser.parse_args()

    review = json.loads(Path(args.compatibility_review_json).read_text(encoding="utf-8"))
    request = {
        "remediation_id": args.remediation_id,
        "selected_by": args.selected_by,
        "selected_at": args.selected_at,
        "selection_reason": args.selection_reason,
    }
    selection = build_fcpxml_remediation_selection(review, request)
    result = write_fcpxml_remediation_selection(selection, args.output_json)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
