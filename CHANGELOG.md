# Changelog

## 2026-07-03

- Hardened Module 2 story contract during Review.
- Added validation for invalid, missing, reversed, and out-of-order time ranges.
- Ensured invalid evidence ranges return empty `source_range` and low `confidence` instead of fabricated timecodes.
- Added JSON serialization, single-subtitle, missing-timecode, reversed-timecode, and out-of-order-timecode tests.
- Added Module 2.5 Story Pipeline foundations.
- Added `schema_version` to story analysis output.
- Added `episodes`, `story_blocks`, and `scenes` to stabilize downstream inputs.
- Added `evidence`, `source_range`, and `confidence` to story moments.
- Added prompt templates under `prompts/`.
- Added tests for empty subtitles, ordinary subtitles, and twist keyword subtitles.

## 2026-07-02

- Initialized project structure.
- Completed Module 1 subtitle parser.
- Completed initial Module 2 rule-based story analysis MVP.
