# Timeline Matching Prompt

Module 4 currently uses a rule-based timeline planner. When an AI matcher is introduced later, it must keep the same contract:

- Only map narration to existing `story_blocks`.
- Only use valid `source_range` values from those blocks.
- Never invent video ranges when a narration segment is unresolved.
- Preserve `source_story_block_id` for every selected range.
- Mark repeated block usage with `primary`, `callback`, `duplicate`, or `unresolved`.
- Return planning JSON only; do not edit, render, or export video.
