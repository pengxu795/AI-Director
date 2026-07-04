# FCPXML Serializer Prompt

Module 9 serializes a validated Module 8 abstract FCPXML design to `.fcpxml`.

- Only accept `status: "designed"` FCPXML design objects.
- Never serialize blocked or unresolved designs.
- Preserve resources, asset refs, clip offsets, clip starts, clip durations, and narration marker text.
- Require each narration marker to carry a real timeline position.
- Never infer marker time from `source_timeline_item_id` or clip offset.
- Attach each marker to the clip covering its timeline position.
- Convert marker timeline position to clip-relative marker start.
- Require marker timeline position and clip-relative marker start to align to sequence `frameDuration`.
- Block markers in gaps, outside sequence duration, or overlapping multiple clips.
- Use existing rational seconds from the design.
- Do not round times.
- Do not read, probe, transcode, cut, render, or export video.
- Do not launch Final Cut Pro or any editor.
- Do not check whether media files exist.
- Do not support fps values rejected by Module 8.
