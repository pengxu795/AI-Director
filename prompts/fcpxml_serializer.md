# FCPXML Serializer Prompt

Module 9 serializes a validated Module 8 abstract FCPXML design to `.fcpxml`.

- Only accept `status: "designed"` FCPXML design objects.
- Never serialize blocked or unresolved designs.
- Preserve resources, asset refs, clip offsets, clip starts, clip durations, and narration marker text.
- Use existing rational seconds from the design.
- Do not round times.
- Do not read, probe, transcode, cut, render, or export video.
- Do not launch Final Cut Pro or any editor.
- Do not check whether media files exist.
- Do not support fps values rejected by Module 8.
