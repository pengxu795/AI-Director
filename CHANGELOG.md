# Changelog

## 2026-07-03

- Canonicalized parent character aliases so `妈妈/母亲` and `爸爸/父亲` each produce one merged character entity.
- Fixed `main_plot` to use time-ordered subtitles and avoid fabricating a conflict when none is detected.
- Rejected out-of-range subtitle timecodes where minutes or seconds exceed `59`.
- Added tests for `00:99:00.000` and `00:00:99.000` so invalid ranges cannot enter summary, scenes, episodes, or story blocks.
- Fixed failed Module 2 Review findings.
- Lowered invalid evidence confidence to `0.2` or below.
- Ordered `story_blocks` by valid source time and preserved all ordered story beats instead of only first/last moments.
- Marked `episodes` as `input_container` instead of implying automatic episode splitting.
- Removed unsafe aliases that merged uncertain roles such as `女主` and `妈妈`.
- Added tests for illegal timecodes, duplicate timecodes, story block ordering, source range invariants, and alias collisions.
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
