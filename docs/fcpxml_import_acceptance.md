# Module 10: FCPXML Import Validation / Manual Acceptance Protocol

## Goal

Module 10 defines a repeatable manual acceptance protocol for importing the generated `.fcpxml` into Final Cut Pro and recording compatibility results.

This module does not automate Final Cut Pro, validate import by code, read media, probe files, transcode, render, or export finished video.

## Inputs

- Module 8 FCPXML design JSON
- Module 9 generated `.fcpxml` path

The `.fcpxml` path is recorded for the tester, but Module 10 does not open the file in Final Cut Pro.

## Output

The protocol JSON contains:

- `schema_version`
- `target_editor`
- `source_design`
- `expected_assets`
- `expected_clips`
- `expected_markers`
- `checklist`
- `manual_result_template`
- `validation_result`
- `metadata`

All checklist items start with `status: "not_run"`. Module 10 must not pre-fill pass/fail results.

## Manual Acceptance Scope

The tester manually imports the `.fcpxml` into Final Cut Pro and records:

- Final Cut Pro version
- macOS version
- library and project names
- whether media asset paths resolve or appear offline
- clip count and order
- clip source in/out
- timeline offsets and durations
- marker text, parent clip, and clip-relative position
- negative import behavior for malformed or rejected files

## Expected Observations

`expected_assets` records source file paths and expected import state.

`expected_clips` records:

- clip id
- asset ref
- timeline offset
- source start
- duration
- source story block id
- source timeline item id
- reuse policy

`expected_markers` records:

- marker id
- narration segment id
- source timeline item id
- marker text
- timeline start
- expected parent clip id
- clip-relative start

## Boundary

Module 10 does not:

- Launch or control Final Cut Pro.
- Perform automatic import.
- Verify editor import by code.
- Read, probe, relink, transcode, cut, render, or export media.
- Mark compatibility as passed without manual evidence.

The protocol can be used to collect evidence, but PASS/FAIL remains a human review decision until a later gated module defines any editor automation.
