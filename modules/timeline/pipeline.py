"""Timeline pipeline for Module 4."""

from __future__ import annotations

from .matcher import generate_timeline


def run_timeline_pipeline(story_analysis: dict, script: dict, subtitles: list[dict]) -> dict:
    """Run Module 4 shot matching and timeline planning."""
    return generate_timeline(story_analysis, script, subtitles)
