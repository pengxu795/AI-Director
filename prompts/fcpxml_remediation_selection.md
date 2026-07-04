# FCPXML Remediation Selection Prompt

Module 13 records one human-selected remediation from a Module 12 review.

- Require a Module 12 review with `status: review_ready`.
- Require a human `remediation_id`, `selected_by`, `selected_at`, and `selection_rationale`.
- Require exactly one explicit remediation id; reject missing ids with `selection_requires_explicit_remediation_id` and multiple ids with `multiple_remediations_not_allowed`.
- Require an existing source review JSON file and freeze `source_review_sha256`.
- Select only remediation items that resolve to findings with `evidence_status: linked`.
- Require selected findings to have non-empty `evidence_refs`.
- Select only blocker or major findings.
- Reject findings that require more evidence before implementation.
- Reject `evidence_incomplete`, blocked, or boundary-violating reviews.
- Preserve source review artifact fingerprints, selected finding context, selected remediation context, and an immutable selection snapshot.
- Generate a task contract only; do not implement the remediation.
- Keep `execution_allowed: false`.
- Keep `serializer_change_allowed: false`.
- Keep `requires_module_14_approval: true`.
- Require Module 13 Review before Module 14 authorization or any serializer, sample, media binding, or automation change.
- Do not launch or control Final Cut Pro.
- Do not automate import.
- Do not read, probe, relink, transcode, cut, render, or export media.
