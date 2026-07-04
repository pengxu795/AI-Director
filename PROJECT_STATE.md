# Project State

## Current Status

- Current phase: Module 8 Review
- Latest completed work: Module 8 FCPXML adapter discovery, minimal export design, millisecond-fps contract, and frame alignment validation
- Next module: real FCPXML adapter implementation
- Gate: Module 8 Review passes before generating real FCPXML, XML, or editor project files

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
- Module 4 Review fix: range-level reuse policy for mixed primary, duplicate, and callback ranges
- Module 5 phase 1: editor-agnostic edit timeline generation
- Module 5 Review fix: range-level unresolved records for rejected video ranges
- Module 6 phase 1: JSON/TXT export package generation
- Module 7: export target research, media asset binding schema, and adapter contract
- Module 8: FCPXML adapter discovery, source mapping design, time conversion, and minimal outline

## Pending Review

- Review Module 8 FCPXML discovery and minimal export design.
- Confirm FCPXML version baseline, field mapping, resource IDs, and rational time conversion are clear.
- Confirm sequence fps is explicit and mixed fps is blocked for MVP.
- Confirm non-millisecond frame rates are blocked until Module 8 gains rational or frame-index edit fields.
- Confirm non-frame-aligned source or timeline times are blocked without rounding.
- Confirm `place_clip` design uses shot-level source ranges.
- Confirm narration remains marker or note design only, with no generated audio asset.
- Confirm no editor project, XML, FCPXML, EDL, AAF, media read, render, or video export was introduced.

## Development Rule

After each module:

1. Update `PROJECT_STATE.md`.
2. Update `CHANGELOG.md`.
3. Run tests.
4. Commit.
5. Push to GitHub.
6. Stop and wait for Review.
