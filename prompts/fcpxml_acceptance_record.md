# FCPXML Acceptance Record Prompt

Module 11 records manually observed Final Cut Pro import results.

- Require a Module 10 protocol with `acceptance_ready: true`.
- Require manual artifact identifiers to match the protocol exactly.
- Require human confirmation that source design, FCPXML, and serializer commit belong to the same output chain.
- Capture tester, run time, Final Cut Pro version, macOS version, library name, and project name.
- Split `import_result`, `media_validation_result`, and `compatibility_result`.
- Require `status: passed` and `imported: true` before allowing `compatibility_result: passed`.
- Require every expected asset to be online before allowing `status: passed` or `compatibility_result: passed`.
- Block PASS when any asset is offline, missing, or unverified.
- Block PASS when any import error has `severity: blocker`.
- Capture every checklist result from the Module 10 protocol.
- Capture every expected asset's online/offline/missing/unverified state.
- Capture importer errors, evidence paths, notes, and regression sample references.
- Allow valid failed or blocked records when they are traceable and evidence-backed.
- Do not infer PASS from generated files.
- Do not launch or control Final Cut Pro.
- Do not automate import.
- Do not read, probe, relink, transcode, cut, render, or export media.
- Do not enter compatibility remediation before Module 11 Review passes.
