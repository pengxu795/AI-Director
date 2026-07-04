# FCPXML Adapter Design Prompt

Module 8 is FCPXML discovery and minimal export design only.

- Consume a validated Module 7 abstract adapter plan.
- Use `register_media_asset` operations to design FCPXML asset resources.
- Use `place_clip.source_in` / `place_clip.source_out` as the actual clip source range.
- Preserve `source_story_block_id`, `source_timeline_item_id`, and `reuse_policy` as design metadata.
- Convert internal `HH:MM:SS.mmm` timecodes to rational seconds.
- Represent narration text as marker or note design only.
- Do not infer width, height, codec, audio layout, or drop-frame settings from media files.
- Do not generate XML, FCPXML, EDL, AAF, project files, editor projects, or media files.
- Do not read, probe, transcode, render, cut, or export video.
