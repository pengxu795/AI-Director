# Module 15: Authorized Remediation Implementation Plan

## Goal

Module 15 converts one Module 14 authorization into a concrete implementation plan for a later review module.

This module does not implement the remediation. It only records the files that a future module may change, the planned change summaries, acceptance criteria, review checklist, and rollback checkpoints.

## Inputs

- Module 14 authorization JSON
- Planning request:
  - `planned_by`
  - `planned_at`
  - `planning_rationale`
  - `planned_file_changes`
  - `acceptance_criteria`
  - `review_checklist`
  - `rollback_checkpoints`

The authorization file must exist so Module 15 can compute and freeze `source_authorization_sha256`.

Formal plans that can be written to disk or used by a later module must be generated through `build_fcpxml_remediation_plan_from_file(...)`. Direct in-memory plan calls are treated as unverified and blocked with `source_authorization_artifact_not_verified`.

If the caller supplies `source_authorization_artifact` or `source_authorization_sha256`, Module 15 verifies those values against the actual file read from disk. Mismatches are blocked with `source_authorization_fingerprint_mismatch`.

## Validation Rules

Planning requires:

- authorization status is `authorization_ready`
- authorization validation result is valid
- authorization keeps `implementation_execution_allowed: false`
- authorization keeps `serializer_change_execution_allowed: false`
- authorization keeps `requires_module_15_implementation_review: true`
- immutable Module 14 authorization snapshot exists
- selection snapshot identity was verified by Module 14
- source authorization path and SHA-256 are present
- source authorization path and SHA-256 were verified from the file read by Module 15
- planned file changes are listed
- every planned file is included in Module 14 `allowed_files`
- no planned file matches Module 14 `prohibited_files`
- each planned change has `path`, `action`, and `summary`
- acceptance criteria are listed
- review checklist items are listed
- rollback checkpoints are listed

Acceptance criteria and review checklist items must not require editor automation or media tools such as FFmpeg, OpenCV, moviepy, Final Cut Pro, or `osascript`.

## Output

The plan JSON contains:

- `source_authorization`
- `plan_id`
- `planned_by`
- `planned_at`
- `planning_rationale`
- `selected_remediation_id`
- `selected_finding_id`
- `evidence_refs`
- `related_entities`
- `planned_file_changes`
- `allowed_files`
- `prohibited_files`
- `verification_plan`
- `rollback_plan`
- `acceptance_criteria`
- `review_checklist`
- `rollback_checkpoints`
- `implementation_execution_allowed`
- `serializer_change_execution_allowed`
- `requires_module_16_approval`
- `immutable_plan_snapshot`
- `validation_result`
- `metadata`

`planned_file_changes` defines the future implementation intent. It does not modify those files in Module 15.

`immutable_plan_snapshot` freezes the source authorization, authorization SHA-256, planned changes, acceptance criteria, review checklist, rollback checkpoints, and planning rationale.

`implementation_execution_allowed` and `serializer_change_execution_allowed` are fixed to `false` in Module 15. A later reviewed module must explicitly implement the approved plan.

## Boundary

Module 15 does not:

- Modify serializer code.
- Modify FCPXML output.
- Modify the authorized files.
- Create code patches.
- Generate or rewrite FCPXML.
- Launch or control Final Cut Pro.
- Perform automatic import.
- Read, probe, relink, transcode, cut, render, or export media.
- Implement the selected remediation.
