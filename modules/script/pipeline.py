"""Script pipeline for Module 3."""

from __future__ import annotations

from .generator import generate_script


def run_script_pipeline(story_analysis: dict) -> dict:
    """Run Module 3 script generation pipeline."""
    return generate_script(story_analysis)

