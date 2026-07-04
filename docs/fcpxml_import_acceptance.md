# Module 10: FCPXML Import Validation / Manual Acceptance Protocol

## Goal

Module 10 defines a repeatable manual acceptance protocol for importing the generated `.fcpxml` into Final Cut Pro and recording compatibility results.

This module does not automate Final Cut Pro, validate import by code, read media, probe files, transcode, render, or export finished video.

## Inputs

- Module 8 FCPXML design JSON
- Module 9 generated `.fcpxml` path

The `.fcpxml` path and SHA-256 fingerprint are recorded for the tester. Module 10 may read the generated `.fcpxml` text file to calculate this fingerprint, but it does not open the file in Final Cut Pro and does not read any media files.

## Output

The protocol JSON contains:

- `schema_version`
- `target_editor`
- `source_artifacts`
- `artifact_relationship`
- `source_design`
- `expected_assets`
- `expected_clips`
- `expected_markers`
- `checklist`
- `manual_result_template`
- `validation_result`
- `metadata`

All checklist items start with `status: "not_run"`. Module 10 must not pre-fill pass/fail results.

## Artifact Traceability

`source_artifacts` records:

- `fcpxml_path`
- `fcpxml_sha256`
- `source_design_path`
- `source_design_sha256`
- `git_commit`
- `serializer_module_version`
- `serializer_commit`
- `protocol_generated_at`
- `fully_traceable`
- `acceptance_ready`

Formal manual acceptance requires `fcpxml_path`, `fcpxml_sha256`, `source_design_path`, `source_design_sha256`, `git_commit`, and `serializer_commit`.

Default protocol generation allows `source_design_path`, `git_commit`, and `serializer_commit` to be empty, but it emits `missing_source_design_artifact` or `missing_artifact_revision_metadata` and keeps `fully_traceable` / `acceptance_ready` false.

If `source_design_path` is provided but the file is missing, the protocol emits `source_design_file_not_found` and keeps `fully_traceable` / `acceptance_ready` false.

If the `.fcpxml` path does not exist, protocol generation returns `status: "blocked"` with `fcpxml_file_not_found`.

`artifact_relationship` records both fingerprints and the serializer commit, but `relationship_verified` remains `false`. Module 10 does not parse FCPXML to prove design-to-file consistency; the preflight checklist requires a human to confirm both artifacts came from the same serializer output chain.

## Manual Acceptance Scope

The tester manually imports the `.fcpxml` into Final Cut Pro and records:

- Final Cut Pro version
- macOS version
- library and project names
- whether media asset paths resolve or appear offline
- whether the imported `.fcpxml` file SHA-256 matches the protocol
- whether the source design SHA-256 matches the design file used to generate the `.fcpxml`
- whether the design file, `.fcpxml` file, and serializer commit belong to the same output chain
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

It may read the generated `.fcpxml` text to calculate `fcpxml_sha256`. That fingerprinting step is explicitly separate from media reading or editor import.

The protocol can be used to collect evidence, but PASS/FAIL remains a human review decision until a later gated module defines any editor automation.
