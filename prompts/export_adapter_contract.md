# Export Adapter Contract Prompt

Module 7 defines adapter validation and abstract planning only.

- Require external `media_asset_bindings` before any real editor export.
- Never infer local video paths from story blocks, subtitles, or narration text.
- Return `validation_result` when bindings or target capabilities are missing.
- Return `adapter_plan` as abstract operations only.
- Do not generate XML, FCPXML, EDL, AAF, project files, editor projects, or media files.
- Do not read, cut, render, transcode, or export video.
