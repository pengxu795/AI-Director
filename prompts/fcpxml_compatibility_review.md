# FCPXML Compatibility Review Prompt

Module 12 reviews Module 11 manual acceptance records.

- Require a valid Module 11 `recorded` acceptance record.
- Preserve source `.fcpxml`, source design, git commit, and serializer commit fingerprints.
- Extract findings from non-online media, failed or blocked checklist items, import errors, and validation warnings.
- Keep successful acceptance as informational with no remediation items.
- Propose remediation only; do not apply fixes.
- Keep `serializer_change_allowed: false` for every remediation item.
- Require review before any serializer change, sample update, media rebinding, or editor automation.
- Do not launch or control Final Cut Pro.
- Do not automate import.
- Do not read, probe, relink, transcode, cut, render, or export media.
- Do not enter compatibility remediation before Module 12 Review passes.
