"""CLI for Module 10 FCPXML manual import acceptance protocol."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.adapters import build_fcpxml_import_acceptance_protocol, write_fcpxml_import_acceptance_protocol


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a manual FCPXML import acceptance protocol JSON.")
    parser.add_argument("design_json", help="Path to Module 8 FCPXML design JSON.")
    parser.add_argument("fcpxml_path", help="Path to generated .fcpxml file under manual review.")
    parser.add_argument("output_json", help="Output protocol JSON path.")
    args = parser.parse_args()

    design = json.loads(Path(args.design_json).read_text(encoding="utf-8"))
    protocol = build_fcpxml_import_acceptance_protocol(design, args.fcpxml_path)
    result = write_fcpxml_import_acceptance_protocol(protocol, args.output_json)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
