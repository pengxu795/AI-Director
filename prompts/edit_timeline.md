# Edit Timeline Prompt

Module 5 currently uses a rule-based edit timeline builder. When an AI planner is introduced later, it must keep the same contract:

- Consume Module 4 timeline JSON only.
- Preserve `source_timeline_item_id`, `narration_segment_id`, `source_story_block_id`, and `reuse_policy`.
- Convert valid source ranges into sequential editor-agnostic clip decisions.
- Keep unresolved items explicit instead of inventing clips.
- Return JSON only; do not read, cut, render, or export video files.
