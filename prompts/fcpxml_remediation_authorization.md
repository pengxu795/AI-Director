# FCPXML Remediation Authorization Prompt

Module 14 creates an implementation scope contract from one Module 13 selection.

- Require an existing Module 13 selection JSON file.
- Freeze `source_selection_sha256`.
- Require selection status `selected`.
- Require `execution_allowed: false`, `serializer_change_allowed: false`, and `requires_module_14_approval: true`.
- Require an immutable selection snapshot.
- Require human `authorized_by`, `authorized_at`, and `authorization_rationale`.
- Require non-empty `allowed_files`, `prohibited_files`, `verification_commands`, and `rollback_steps`.
- Reject overlap between allowed and prohibited paths.
- Reject verification commands that invoke editor automation or media tooling.
- Define future implementation scope only; do not implement the remediation.
- Keep `implementation_execution_allowed: false`.
- Keep `serializer_change_execution_allowed: false`.
- Keep `code_changes_applied: false`.
- Keep `fcpxml_generated: false`.
- Do not launch or control Final Cut Pro.
- Do not automate import.
- Do not read, probe, relink, transcode, cut, render, or export media.
