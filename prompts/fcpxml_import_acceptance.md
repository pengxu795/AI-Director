# FCPXML Import Acceptance Prompt

Module 10 creates a manual Final Cut Pro import acceptance protocol.

- Treat Module 9 `.fcpxml` output as the file under review.
- Generate checklist JSON only.
- Preserve expected media assets, clip source ranges, timeline offsets, marker positions, and traceability ids.
- Keep every checklist item in `not_run` status.
- Require manual evidence for resource paths, clip in/out, timeline offsets, marker positions, and importer error behavior.
- Do not infer PASS/FAIL from generated files.
- Do not launch or control Final Cut Pro.
- Do not automate import.
- Do not read, probe, relink, transcode, cut, render, or export media.
- Do not enter editor automation or compatibility remediation before Module 10 Review passes.
