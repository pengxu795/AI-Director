"""CLI for Module 15 authorized remediation implementation plans."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.adapters import build_fcpxml_remediation_plan_from_file, write_fcpxml_remediation_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan implementation steps for one authorized remediation.")
    parser.add_argument("remediation_authorization_json", help="Path to Module 14 authorization JSON.")
    parser.add_argument("output_json", help="Output Module 15 remediation plan JSON path.")
    parser.add_argument("--planned-by", required=True, help="Human reviewer/planner creating the plan.")
    parser.add_argument("--planned-at", required=True, help="Planning timestamp.")
    parser.add_argument("--planning-rationale", required=True, help="Rationale for the implementation plan.")
    parser.add_argument("--planned-file-change", action="append", default=[], help="JSON object with path, action, and summary.")
    parser.add_argument("--acceptance-criterion", action="append", default=[], help="Acceptance criterion required before implementation can be approved.")
    parser.add_argument("--review-checklist-item", action="append", default=[], help="Review checklist item for the future implementation.")
    parser.add_argument("--rollback-checkpoint", action="append", default=[], help="Rollback checkpoint for the future implementation.")
    args = parser.parse_args()

    planned_file_changes = []
    for raw_change in args.planned_file_change:
        planned_file_changes.append(json.loads(raw_change))

    request = {
        "planned_by": args.planned_by,
        "planned_at": args.planned_at,
        "planning_rationale": args.planning_rationale,
        "planned_file_changes": planned_file_changes,
        "acceptance_criteria": args.acceptance_criterion,
        "review_checklist": args.review_checklist_item,
        "rollback_checkpoints": args.rollback_checkpoint,
    }
    plan = build_fcpxml_remediation_plan_from_file(args.remediation_authorization_json, request)
    if plan.get("status") != "plan_ready":
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    result = write_fcpxml_remediation_plan(plan, args.output_json)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
