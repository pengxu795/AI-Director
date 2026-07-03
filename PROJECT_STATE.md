# Project State

## Current Status

- Current phase: Module 4 Review
- Latest completed work: Module 4 shot matching and timeline planning phase 1
- Next module: Module 5 Video Editing / Export Planning
- Gate: Do not start Module 5 until Module 4 Review passes

## Completed

- Module 1: Subtitle parsing
- Module 2: Rule-based story analysis MVP
- Module 2.5: Schema stabilization, prompt layer, story blocks, scene split
- Module 2 Review hardening: time range validation, low-confidence fallback, JSON serialization test
- Module 2 Review fix: ordered story blocks, input-container episodes, safe character aliases
- Module 2 Review fix: reject out-of-range minute and second values in timecodes
- Module 2 Review fix: canonical parent aliases and time-ordered `main_plot`
- Module 3 phase 1: rule-based script generation schema and traceability
- Module 3 Review fix: title hooks, narration segments, and ending hook must trace to `story_blocks`
- Module 4 phase 1: rule-based shot matching and timeline planning
- Module 4 Review fix: callback reuse policy, partial matching coverage, and duplicate block-id cleanup

## Pending Review

- Review Module 4 timeline schema.
- Confirm every matched video range traces back to Module 2 story blocks.
- Confirm unresolved segments never output guessed video ranges.
- Confirm Module 4 should proceed before Module 5 video editing/export work.

## Development Rule

After each module:

1. Update `PROJECT_STATE.md`.
2. Update `CHANGELOG.md`.
3. Run tests.
4. Commit.
5. Push to GitHub.
6. Stop and wait for Review.
