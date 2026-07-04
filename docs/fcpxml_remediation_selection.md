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
  - `selection_reason`

The Module 12 review must be `review_ready`.

## Selection Rules

A remediation item can be selected only when:

- The source review status is `review_ready`.
- The remediation item exists.
- The remediation item is still `proposed`.
- The remediation item resolves to an existing finding.
- The finding has `evidence_status: "linked"`.
- The finding has non-empty `evidence_refs`.
- The remediation does not require additional evidence before implementation.
- The remediation does not already allow serializer changes.

`evidence_incomplete`, blocked, or boundary-violating reviews cannot be selected for implementation planning.

## Output

The remediation selection JSON contains:

- `source_review`
- `selection`
- `task_contract`
- `validation_result`
- `metadata`

The `task_contract` is a planning artifact only. It keeps:

- `implementation_allowed: false`
- `serializer_change_allowed: false`
- `requires_module_review_before_implementation: true`
- `requires_linked_evidence: true`

## Boundary

Module 13 does not:

- Change FCPXML serializer behavior.
- Write FCPXML or editor project files.
- Launch or control Final Cut Pro.
- Perform automatic import.
- Read, probe, relink, transcode, cut, render, or export media.
- Implement the selected remediation.
