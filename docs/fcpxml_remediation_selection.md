# Module 13: Evidence-Backed Remediation Selection

## Goal

Module 13 records one human-selected remediation item from a Module 12 compatibility review and turns it into a controlled task contract for a later implementation module.

This module does not modify the serializer, launch Final Cut Pro, automate import, read media, transcode, render, or export video.

## Input

- Module 12 compatibility review JSON
- Human selection request containing:
  - `remediation_id`
  - `selected_by`
  - `selected_at`
  - `selection_rationale`
  - optional `priority_override_reason`

The Module 12 review must be `review_ready`.
The review must be loaded from an existing JSON file so Module 13 can compute and freeze `source_review_sha256`.

## Selection Rules

A remediation item can be selected only when:

- The source review status is `review_ready`.
- The remediation item exists.
- The remediation item is still `proposed`.
- The remediation item resolves to an existing finding.
- The finding has `evidence_status: "linked"`.
- The finding has non-empty `evidence_refs`.
- The finding severity is `blocker` or `major`.
- The remediation does not require additional evidence before implementation.
- The remediation does not already allow serializer changes.
- Exactly one `remediation_id` is provided explicitly.

`evidence_incomplete`, blocked, or boundary-violating reviews cannot be selected for implementation planning.

If the source review file path does not exist, selection is blocked with `fcpxml_compatibility_review_file_not_found`. Missing explicit remediation ids are blocked with `selection_requires_explicit_remediation_id`; multiple ids are blocked with `multiple_remediations_not_allowed`.

## Output

The remediation selection JSON contains:

- `selection_id`
- `status`
- `selected_remediation_id`
- `selected_finding_id`
- `selected_by`
- `selected_at`
- `selection_rationale`
- `priority`
- `evidence_refs`
- `related_entities`
- `source_review_artifact`
- `source_review_sha256`
- `source_review_git_commit`
- `execution_allowed`
- `serializer_change_allowed`
- `requires_module_14_approval`
- `immutable_selection_snapshot`
- `source_review`
- `selection`
- `task_contract`
- `validation_result`
- `metadata`

`immutable_selection_snapshot` freezes the selected finding, selected remediation, evidence refs, related entities, review status, review SHA-256, review git commit, selected priority, and rationale. Later edits to the source review must not change this snapshot.

`source_review_git_commit` may be passed explicitly by the caller. If omitted, Module 13 falls back to the review's embedded source record git commit.

The `task_contract` is a planning artifact only. It keeps:

- `implementation_allowed: false`
- `serializer_change_allowed: false`
- `requires_module_14_approval: true`
- `requires_linked_evidence: true`

## Boundary

Module 13 does not:

- Change FCPXML serializer behavior.
- Write FCPXML or editor project files.
- Launch or control Final Cut Pro.
- Perform automatic import.
- Read, probe, relink, transcode, cut, render, or export media.
- Implement the selected remediation.
