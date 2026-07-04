"""CLI for Module 9 minimal FCPXML serialization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.adapters import write_fcpxml_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Serialize a Module 8 FCPXML design JSON to a minimal .fcpxml file.")
    parser.add_argument("design_json", help="Path to Module 8 FCPXML design JSON.")
    parser.add_argument("output_fcpxml", help="Output .fcpxml path.")
    args = parser.parse_args()

    design = json.loads(Path(args.design_json).read_text(encoding="utf-8"))
    result = write_fcpxml_file(design, args.output_fcpxml)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
