# Project State

## Current Status

- Current phase: Module 2 stabilization
- Latest completed work: Module 2.5 Story Pipeline foundations
- Next module: Module 3 Script Generation
- Gate: Do not start Module 3 until Module 2 Review passes

## Completed

- Module 1: Subtitle parsing
- Module 2: Rule-based story analysis MVP
- Module 2.5: Schema stabilization, prompt layer, story blocks, scene split

## Pending Review

- Verify Module 2 schema is stable enough for Module 3.
- Confirm `story_blocks` can drive script generation.
- Confirm `episodes`, `source_range`, `evidence`, and `confidence` are sufficient for later matcher work.

## Development Rule

After each module:

1. Update `PROJECT_STATE.md`.
2. Update `CHANGELOG.md`.
3. Run tests.
4. Commit.
5. Push to GitHub.
6. Stop and wait for Review.
