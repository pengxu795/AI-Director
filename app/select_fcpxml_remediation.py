"""CLI for Module 13 evidence-backed remediation selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.adapters import build_fcpxml_remediation_selection_from_file, write_fcpxml_remediation_selection


def main() -> None:
    parser = argparse.ArgumentParser(description="Select one evidence-backed Module 12 remediation item.")
    parser.add_argument("compatibility_review_json", help="Path to Module 12 compatibility review JSON.")
    parser.add_argument("output_json", help="Output remediation selection JSON path.")
    parser.add_argument("--remediation-id", required=True, help="Remediation item id to select.")
    parser.add_argument("--selected-by", required=True, help="Human reviewer selecting the remediation.")
    parser.add_argument("--selected-at", required=True, help="Selection timestamp.")
    parser.add_argument("--selection-rationale", required=True, help="Rationale for selecting this remediation.")
    parser.add_argument("--source-review-git-commit", default="", help="Optional git commit for the source review artifact.")
    parser.add_argument("--priority-override", default="", help="Optional selected priority override.")
    parser.add_argument("--priority-override-reason", default="", help="Reason for a priority override.")
    args = parser.parse_args()

    request = {
        "remediation_id": args.remediation_id,
        "selected_by": args.selected_by,
        "selected_at": args.selected_at,
        "selection_rationale": args.selection_rationale,
        "source_review_git_commit": args.source_review_git_commit,
        "priority_override": args.priority_override,
        "priority_override_reason": args.priority_override_reason,
    }
    selection = build_fcpxml_remediation_selection_from_file(args.compatibility_review_json, request)
    if selection.get("status") != "selected":
        print(json.dumps(selection, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    result = write_fcpxml_remediation_selection(selection, args.output_json)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
