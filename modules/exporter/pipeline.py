"""Export pipeline for Module 6."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .package import build_export_package, export_package_files


def run_export_pipeline(
    edit_timeline: dict[str, Any],
    script: dict[str, Any],
    timeline_plan: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    """Run Module 6 export package generation."""
    package = build_export_package(edit_timeline, script, timeline_plan)
    export_package_files(package, output_dir)
    return package
