# FCPXML Remediation Implementation Plan Prompt

Module 15 creates a non-executable implementation plan from one Module 14 authorization.

- Require an existing Module 14 authorization JSON file.
- Freeze `source_authorization_sha256`.
- Generate formal writable plans only from `build_fcpxml_remediation_plan_from_file(...)`.
- Block direct in-memory planning with `source_authorization_artifact_not_verified`.
- Block caller-provided path or SHA mismatches with `source_authorization_fingerprint_mismatch`.
- Require authorization status `authorization_ready`.
- Require `implementation_execution_allowed: false`, `serializer_change_execution_allowed: false`, and `requires_module_15_implementation_review: true`.
- Require Module 14 `selection_snapshot_verified: true`.
- Require human `planned_by`, `planned_at`, and `planning_rationale`.
- Require non-empty `planned_file_changes`, `acceptance_criteria`, `review_checklist`, and `rollback_checkpoints`.
- Every planned file must be inside Module 14 `allowed_files`.
- No planned file may match Module 14 `prohibited_files`.
- Each planned file change must include `path`, `action`, and `summary`.
- Reject acceptance or checklist items that invoke editor automation or media tooling.
- Define future implementation plan only; do not implement the remediation.
- Keep `implementation_execution_allowed: false`.
- Keep `serializer_change_execution_allowed: false`.
- Keep `code_changes_applied: false`.
- Keep `fcpxml_generated: false`.
- Do not launch or control Final Cut Pro.
- Do not automate import.
- Do not read, probe, relink, transcode, cut, render, or export media.
