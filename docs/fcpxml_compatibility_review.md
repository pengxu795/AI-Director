# Module 12: FCPXML Compatibility Findings Review / Remediation Plan

## Goal

Module 12 reviews a Module 11 acceptance record and turns manual import results into structured compatibility findings and a proposed remediation plan.

This module does not modify the serializer, launch Final Cut Pro, automate import, read media, transcode, render, or export video.

## Input

- Module 11 acceptance record JSON

The record must be `recorded`, valid, and traceable to the `.fcpxml`, source design, git commit, and serializer commit.

## Output

The compatibility review JSON contains:

- `source_record`
- `environment`
- `result_summary`
- `findings`
- `remediation_plan`
- `regression_samples`
- `validation_result`
- `metadata`

## Finding Sources

Findings are derived from:

- non-online `asset_results`
- failed or blocked checklist items
- `import_errors`
- validation warnings from the acceptance record

If the acceptance record fully passes, Module 12 emits an informational `manual_acceptance_passed` finding and no remediation items.

## Evidence Contract

Every compatibility finding must distinguish evidence from affected entities:

- `evidence_refs` contains only real `evidence_id` values from the Module 11 acceptance record.
- `related_entities.asset_ids` contains affected media assets.
- `related_entities.check_ids` contains affected checklist items.
- `related_entities.error_codes` contains affected importer or validation error codes.

Asset ids, checklist ids, and error codes must not be used as `evidence_refs`.

`evidence_id` is only an index. Module 12 may use an evidence entry to confirm a finding only when the entry is complete and uniquely identified:

- `evidence_id` is non-empty and appears exactly once in the record.
- `evidence_type` is non-empty.
- `description` is non-empty.
- `path_or_reference` is non-empty.
- `related_asset_ids`, `related_check_ids`, and `related_error_codes` are lists.

Incomplete evidence and duplicate evidence ids produce `unusable_evidence_entry` or `duplicate_evidence_id` warnings. They must not appear in `finding.evidence_refs`.

Blocker or major findings require at least one matching evidence id before they can be treated as confirmed. If matching evidence is missing, the finding is downgraded to warning severity, keeps `original_severity`, sets `evidence_status: "missing"`, and the review status becomes `evidence_incomplete`.

Import-error findings match evidence through `related_error_codes`. Missing import-error evidence produces `missing_evidence_for_import_error`.

Manual checklist findings match evidence through `related_check_ids`. A failed or blocked checklist item without matching evidence cannot produce executable P0/P1 remediation.

## Remediation Plan

The remediation plan is proposed only. Every item keeps:

- `serializer_change_allowed: false`
- `requires_evidence_before_implementation`
- `requires_review_before_implementation: true`
- `status: "proposed"`

Module 12 is for triage and prioritization. Serializer changes, sample updates, media rebinding, or editor automation require a later reviewed module.

If `requires_evidence_before_implementation` is true, the item must not be implemented until manual evidence is attached and reviewed.

## Boundary

Module 12 does not:

- Change FCPXML serializer behavior.
- Write FCPXML or editor project files.
- Launch or control Final Cut Pro.
- Perform automatic import.
- Read, probe, relink, transcode, cut, render, or export media.
- Mark compatibility as fixed.
