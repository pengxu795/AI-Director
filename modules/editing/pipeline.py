"""Edit timeline pipeline for Module 5."""

from __future__ import annotations

from .builder import build_edit_timeline


def run_editing_pipeline(timeline_plan: dict) -> dict:
    """Run Module 5 edit timeline generation."""
    return build_edit_timeline(timeline_plan)
