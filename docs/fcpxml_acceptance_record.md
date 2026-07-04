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
- import result
- media validation result
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

`status`, `import_result`, `media_validation_result`, and `compatibility_result` may be:

- `passed`
- `failed`
- `blocked`

Result levels are intentionally separate:

- `import_result`: whether Final Cut Pro accepted the `.fcpxml`.
- `media_validation_result`: whether expected media was online and could be manually checked.
- `compatibility_result`: full compatibility. It may be `passed` only when top-level `status`, import, and media validation all pass, and `imported == true`.

A `passed` record requires:

- `imported == true`
- top-level `status == "passed"`
- `import_result == "passed"`
- `media_validation_result == "passed"`
- `compatibility_result == "passed"`
- every expected asset has exactly one result
- every expected asset `import_state == "online"`
- every checklist item is `passed`
- no blocker `import_errors`
- artifact relationship was manually confirmed
- required environment and evidence fields are present

Failed or blocked records may include offline, missing, or unverified assets; `import_errors`; and failed checklist items. They are still valid records when they are traceable and evidence-backed.

When the `.fcpxml` imports but media is offline, use `import_result: "passed"` with `media_validation_result: "blocked"` or `failed`, and keep `compatibility_result` non-passing. This records that XML import was checked without claiming the edit chain is usable.

## Boundary

Module 11 does not:

- Launch or control Final Cut Pro.
- Perform automatic import.
- Read, probe, relink, transcode, cut, render, or export media.
- Mark results without manual evidence.
- Modify the generated `.fcpxml` or source design.
