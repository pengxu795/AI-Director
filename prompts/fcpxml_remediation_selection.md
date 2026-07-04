# FCPXML Remediation Selection Prompt

Module 13 records one human-selected remediation from a Module 12 review.

- Require a Module 12 review with `status: review_ready`.
- Require a human `remediation_id`, `selected_by`, `selected_at`, and `selection_reason`.
- Select only remediation items that resolve to findings with `evidence_status: linked`.
- Require selected findings to have non-empty `evidence_refs`.
- Reject findings that require more evidence before implementation.
- Reject `evidence_incomplete`, blocked, or boundary-violating reviews.
- Preserve source review artifact fingerprints and selected finding context.
- Generate a task contract only; do not implement the remediation.
- Keep `implementation_allowed: false`.
- Keep `serializer_change_allowed: false`.
- Require Module 13 Review before any serializer, sample, media binding, or automation change.
- Do not launch or control Final Cut Pro.
- Do not automate import.
- Do not read, probe, relink, transcode, cut, render, or export media.
