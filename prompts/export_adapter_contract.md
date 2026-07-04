# Export Adapter Contract Prompt

Module 7 defines adapter validation and abstract planning only.

- Require external `media_asset_bindings` before any real editor export.
- Treat only `status: "bound"` and `validation_errors: []` bindings as usable.
- Keep shots unresolved when their binding is pending, unresolved, invalid, or has validation errors.
- Use shot-level `source_start` / `source_end` as the actual `place_clip` source range.
- Treat binding `source_in` / `source_out` as the allowed media range, not as every clip's source range.
- Block ambiguous bindings instead of choosing one silently.
- Never infer local video paths from story blocks, subtitles, or narration text.
- Return `validation_result` when bindings or target capabilities are missing.
- Return `adapter_plan` as abstract operations only.
- Do not generate XML, FCPXML, EDL, AAF, project files, editor projects, or media files.
- Do not read, cut, render, transcode, or export video.
