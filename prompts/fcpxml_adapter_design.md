# FCPXML Adapter Design Prompt

Module 8 is FCPXML discovery and minimal export design only.

- Consume a validated Module 7 abstract adapter plan.
- Use `register_media_asset` operations to design FCPXML asset resources.
- Use `place_clip.source_in` / `place_clip.source_out` as the actual clip source range.
- Preserve `source_story_block_id`, `source_timeline_item_id`, and `reuse_policy` as design metadata.
- Convert internal `HH:MM:SS.mmm` timecodes to rational seconds.
- Require explicit sequence fps from target profile or project settings.
- Keep sequence format separate from asset metadata.
- Reject mixed fps in Module 8 MVP.
- Reject non-millisecond frame rates such as 30, 30000/1001, 60000/1001, 29.97, and 59.94.
- Reject any source or timeline edit point that is not exactly frame aligned.
- Never round edit points to frames.
- Represent narration text as marker or note design only.
- Do not infer width, height, codec, audio layout, or drop-frame settings from media files.
- Do not generate XML, FCPXML, EDL, AAF, project files, editor projects, or media files.
- Do not read, probe, transcode, render, cut, or export video.
