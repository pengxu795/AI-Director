"""CLI for Module 14 remediation authorization scope contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.adapters import build_fcpxml_remediation_authorization_from_file, write_fcpxml_remediation_authorization


def main() -> None:
    parser = argparse.ArgumentParser(description="Authorize implementation scope for one selected remediation.")
    parser.add_argument("remediation_selection_json", help="Path to Module 13 remediation selection JSON.")
    parser.add_argument("output_json", help="Output authorization contract JSON path.")
    parser.add_argument("--authorized-by", required=True, help="Human reviewer authorizing the scope.")
    parser.add_argument("--authorized-at", required=True, help="Authorization timestamp.")
    parser.add_argument("--authorization-rationale", required=True, help="Rationale for this scope authorization.")
    parser.add_argument("--allowed-file", action="append", default=[], help="Future implementation file path allowed by this contract.")
    parser.add_argument("--prohibited-file", action="append", default=[], help="File path or pattern prohibited by this contract.")
    parser.add_argument("--verification-command", action="append", default=[], help="Verification command required after future implementation.")
    parser.add_argument("--rollback-step", action="append", default=[], help="Rollback step required if future implementation fails.")
    args = parser.parse_args()

    request = {
        "authorized_by": args.authorized_by,
        "authorized_at": args.authorized_at,
        "authorization_rationale": args.authorization_rationale,
        "allowed_files": args.allowed_file,
        "prohibited_files": args.prohibited_file,
        "verification_commands": args.verification_command,
        "rollback_steps": args.rollback_step,
    }
    authorization = build_fcpxml_remediation_authorization_from_file(args.remediation_selection_json, request)
    if authorization.get("status") != "authorization_ready":
        print(json.dumps(authorization, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    result = write_fcpxml_remediation_authorization(authorization, args.output_json)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
