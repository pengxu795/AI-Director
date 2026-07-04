# Module 14: Remediation Authorization / Implementation Scope Contract

## Goal

Module 14 converts one Module 13 remediation selection into an auditable implementation scope contract.

This module defines future allowed files, prohibited files, verification commands, and rollback steps. It does not apply the remediation.

## Inputs

- Module 13 remediation selection JSON
- Human authorization request:
  - `authorized_by`
  - `authorized_at`
  - `authorization_rationale`
  - `allowed_files`
  - `prohibited_files`
  - `verification_commands`
  - `rollback_steps`

The selection file must exist so Module 14 can compute and freeze `source_selection_sha256`.

Formal authorization contracts that can be written to disk or used by a later module must be generated through `build_fcpxml_remediation_authorization_from_file(...)`. Direct in-memory authorization calls are treated as unverified and blocked with `source_selection_artifact_not_verified`.

If the caller supplies `source_selection_artifact` or `source_selection_sha256`, Module 14 verifies those values against the actual file read from disk. Mismatches are blocked with `source_selection_fingerprint_mismatch`.

The verified selection file must also be internally consistent. Top-level `selected_remediation_id`, `selected_finding_id`, `evidence_refs`, `related_entities`, `source_review_sha256`, and `source_review_git_commit` must match the immutable selection snapshot. Any mismatch is blocked with `selection_snapshot_integrity_mismatch`.

## Validation Rules

Authorization requires:

- selection status is `selected`
- selection keeps `execution_allowed: false`
- selection keeps `serializer_change_allowed: false`
- selection keeps `requires_module_14_approval: true`
- immutable Module 13 selection snapshot exists
- top-level selection identity matches the immutable selection snapshot
- source selection path and SHA-256 are present
- source selection path and SHA-256 were verified from the file read by Module 14
- allowed files are listed
- prohibited files are listed
- allowed and prohibited paths do not overlap
- verification commands are listed
- rollback steps are listed

Verification commands must not invoke editor automation or media tools such as FFmpeg, OpenCV, moviepy, Final Cut Pro, or `osascript`.

Authorization scope must match the selected remediation:

- If `selected remediation.serializer_change_allowed == false`, `allowed_files` must not include serializer files, serializer tests, serializer docs, FCPXML export helper files, FCPXML export CLI files, or `.fcpxml` outputs.
- This check uses semantic path patterns such as `*serializer*`, `*fcpxml*export*`, `app/*export_fcpxml*.py`, and `output/*.fcpxml`; renaming the file must not bypass the rule.
- FCPXML implementation, generation, writing, builder, project, or app files are also blocked when `serializer_change_allowed == false`. This includes semantic patterns such as `modules/adapters/*fcpxml*.py`, `tests/*fcpxml*.py`, `docs/*fcpxml*.md`, `app/*fcpxml*.py`, and `app/*final_cut*.py`.
- If `selected remediation.owner == "human_review"`, `allowed_files` must pass a positive whitelist for review, protocol, record, manual follow-up, or documentation artifacts.
- Human-review scope is not authorized just because a path is absent from `prohibited_files`; each `allowed_files` entry must pass the whitelist.
- Human-review remediations set `manual_follow_up_required: true`.
- Serializer or FCPXML generation files can be authorized only when the selected remediation itself allows serializer changes.

## Output

The authorization JSON contains:

- `source_selection`
- `authorization_id`
- `authorized_by`
- `authorized_at`
- `authorization_rationale`
- `selected_remediation_id`
- `selected_finding_id`
- `evidence_refs`
- `related_entities`
- `implementation_scope`
- `verification_plan`
- `rollback_plan`
- `implementation_execution_allowed`
- `serializer_change_execution_allowed`
- `manual_follow_up_required`
- `requires_module_15_implementation_review`
- `immutable_authorization_snapshot`
- `validation_result`
- `metadata`

`allowed_files` defines the maximum future implementation scope. It does not modify those files in Module 14.

`immutable_authorization_snapshot` records `verified_selection_identity`, `selected_remediation_id`, `selected_finding_id`, `source_review_sha256`, and `selection_snapshot_verified: true` so a later implementation module cannot mix top-level selection fields with a different snapshot remediation.

`implementation_execution_allowed` and `serializer_change_execution_allowed` are fixed to `false` in Module 14. A later reviewed module must explicitly implement any authorized fix.

## Boundary

Module 14 does not:

- Modify serializer code.
- Modify samples or media bindings.
- Create code patches.
- Generate or rewrite FCPXML.
- Launch or control Final Cut Pro.
- Perform automatic import.
- Read, probe, relink, transcode, cut, render, or export media.
- Implement the selected remediation.
