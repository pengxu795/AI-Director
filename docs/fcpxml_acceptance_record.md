# Module 11: Manual Import Result Capture / Acceptance Record

## Goal

Module 11 records the human result of importing a generated `.fcpxml` into Final Cut Pro.

It captures PASS/FAIL evidence, Final Cut Pro version, macOS version, media online/offline state, importer errors, and regression sample references.

Module 11 does not automate Final Cut Pro, import files by code, read media, transcode, render, or export finished video.

## Inputs

- Module 10 acceptance protocol JSON
- Manually filled result JSON

The Module 10 protocol must be `acceptance_ready`. This means the `.fcpxml`, source design, git commit, and serializer commit are all fingerprinted before manual PASS/FAIL can be recorded.

## Output

The acceptance record JSON contains:

- `source_protocol`
- `recorded_artifacts`
- `artifact_relationship_confirmation`
- `environment`
- `result`
- `asset_results`
- `check_results`
- `import_errors`
- `evidence`
- `regression_samples`
- `validation_result`
- `metadata`

## Required Manual Data

The manual result must record:

- tester
- run timestamp
- Final Cut Pro version
- macOS version
- library name
- project name
- imported state
- compatibility result
- every checklist result from the Module 10 protocol
- every expected asset import state
- evidence entries
- artifact relationship confirmation

## Artifact Safety

The manual result artifact identifiers must match the Module 10 protocol:

- `fcpxml_path`
- `fcpxml_sha256`
- `source_design_path`
- `source_design_sha256`
- `git_commit`
- `serializer_commit`

If any identifier differs, Module 11 blocks the record with `artifact_identifier_mismatch`.

## Result Rules

`status` and `compatibility_result` may be:

- `passed`
- `failed`
- `blocked`

A `passed` record requires:

- `imported == true`
- every checklist item is `passed`
- artifact relationship was manually confirmed
- required environment and evidence fields are present

Failed or blocked records may include `import_errors` and failed checklist items. They are still valid records when they are traceable and evidence-backed.

## Boundary

Module 11 does not:

- Launch or control Final Cut Pro.
- Perform automatic import.
- Read, probe, relink, transcode, cut, render, or export media.
- Mark results without manual evidence.
- Modify the generated `.fcpxml` or source design.
