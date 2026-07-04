# FCPXML Compatibility Review Prompt

Module 12 reviews Module 11 manual acceptance records.

- Require a valid Module 11 `recorded` acceptance record.
- Preserve source `.fcpxml`, source design, git commit, and serializer commit fingerprints.
- Extract findings from non-online media, failed or blocked checklist items, import errors, and validation warnings.
- Put only real Module 11 `evidence_id` values in `finding.evidence_refs`.
- Put affected asset ids, checklist ids, and error codes in `related_entities`, not in `evidence_refs`.
- Match media findings by `related_asset_ids`, checklist findings by `related_check_ids`, and import-error findings by `related_error_codes`.
- If blocker or major findings lack matching evidence, mark `evidence_status: missing`, downgrade them to warning, set review status to `evidence_incomplete`, and require evidence before implementation.
- Keep successful acceptance as informational with no remediation items.
- Propose remediation only; do not apply fixes.
- Keep `serializer_change_allowed: false` for every remediation item.
- Keep `requires_evidence_before_implementation: true` for remediation derived from findings without linked evidence.
- Require review before any serializer change, sample update, media rebinding, or editor automation.
- Do not launch or control Final Cut Pro.
- Do not automate import.
- Do not read, probe, relink, transcode, cut, render, or export media.
- Do not enter compatibility remediation before Module 12 Review passes.
