# Module 7: Export Target Research / Adapter Contract

## Goal

Module 7 defines the adapter contract for future editor-specific exports. It does not generate editor project files, XML, FCPXML, EDL, AAF, media files, or rendered video.

The stable Module 1-6 JSON pipeline remains the source of truth. Editor-specific adapters must consume a canonical adapter input and produce only an abstract plan until a later reviewed module selects one concrete target.

## Canonical Adapter Input

```json
{
  "schema_version": "1.0",
  "export_package_manifest": {},
  "edit_timeline": {},
  "narration_script": {},
  "shot_list": [],
  "unresolved_items": [],
  "media_asset_bindings": [],
  "target_profile": {}
}
```

## Media Asset Bindings

`media_asset_bindings` is an external binding layer. Module 1-6 must not know or guess local video paths.

Each binding must include:

- `media_asset_id`
- `source_story_block_id` or `source_timeline_item_id`
- `source_file`
- `source_in`
- `source_out`
- `duration`
- `fps`
- `audio_available`
- `status`
- `validation_errors`

Rules:

- Bindings are injected after the JSON export package is created.
- Missing bindings block real editor export validation.
- Missing `source_file`, `fps`, or `duration` is a validation error.
- Only `status: "bound"` with `validation_errors: []` is usable for adapter planning.
- `pending`, `unresolved`, `invalid`, or non-empty `validation_errors` must block planning and keep matching shots unresolved.
- No adapter may infer filenames from subtitle text, story blocks, or narration.
- Unbound shots remain unresolved; they must not become fake clips.

## Target Profile

Each target declares:

- `target_id`
- `target_version`
- `supports_video_track`
- `supports_narration_track`
- `supports_markers`
- `supports_reuse_policy_metadata`
- `requires_media_asset_binding`
- `supports_round_trip`
- `output_kind`
- `known_limitations`

## Adapter Contract

- `validate(input) -> validation_result`
- `plan(input) -> adapter_plan`
- `export(...)` is intentionally not implemented in Module 7.

`adapter_plan` contains abstract operations such as `create_sequence`, `register_media_asset`, `place_clip`, and `add_narration_cue`. It must not write XML, FCPXML, EDL, AAF, project files, or media files.

## Validation Result

```json
{
  "valid": false,
  "errors": [],
  "warnings": [],
  "unresolved_items": [],
  "required_missing_fields": [],
  "target_compatibility": {}
}
```

## Export Target Matrix

| Target | Public interchange format | Video clips / timeline | Narration / audio | Markers / metadata | Round trip | MVP priority | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FCPXML / Final Cut Pro | Yes. Apple documents FCPXML as an XML format for exchanging media, projects, and metadata with Final Cut Pro: https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference | Strong fit | Likely fit through audio clips, but must test narration track mapping | Stronger than most options; custom metadata still needs validation | Good | Highest | Low-Medium |
| Premiere Pro XML | Partially. Adobe documents exporting Final Cut Pro XML and importing converted XML; FCPX XML may require conversion for Premiere: https://helpx.adobe.com/premiere/desktop/render-and-export/export-files/export-a-project-as-final-cut-pro-xml-file.html and https://helpx.adobe.com/premiere/desktop/organize-media/import-files/migrate-from-final-cut-pro-x.html | Good fit for basic sequence data | Good, but translation limits exist | Limited; reuse metadata may need markers or sidecars | Limited | High | Medium |
| DaVinci Resolve | Yes for multiple interchange families. Blackmagic documents XML/AAF/FCPXML/EDL timeline import workflows in Resolve materials, including FCP XML support notes: https://documents.blackmagicdesign.com/SupportNotes/DaVinci_Resolve_18.6_New_Features_Guide.pdf | Good fit | Good, but target format choice matters | Moderate; depends on XML/AAF/EDL route | Good | High | Medium |
| 剪映 / Jianying | No stable public contract assumed in this project. Public web results are mostly tutorials or user reports rather than official, versioned interchange documentation. | Unknown | Unknown | Unknown | Unknown | Low for first implementation | High |

## Recommendation

The first real export adapter should target FCPXML or a Premiere-compatible XML route before attempting Jianying.

Reasons:

- FCPXML has the clearest public, versioned documentation from Apple.
- Premiere-compatible XML is broadly understood but has translation limits and may require FCP7-style XML or conversion tooling.
- DaVinci Resolve is a strong second candidate, especially through FCPXML or EDL, but should be chosen after the exact interchange path is tested.
- Jianying should remain research-only until a stable, public, versioned import/export contract is confirmed.

## Current Unknowns

- Exact mapping for narration text to target-native audio or marker structures.
- How each target preserves custom metadata such as `reuse_policy`.
- Whether each target can reliably relink media from absolute paths across machines.
- Timebase and frame-rate rounding behavior for non-integer frame rates.
- Whether editor import dialogs alter timeline start, clip naming, or marker metadata.

## Module 7 Boundary

Module 7 does not:

- Generate XML, FCPXML, EDL, AAF, or project files.
- Read, inspect, transcode, cut, render, or export video.
- Control Final Cut Pro, Premiere, DaVinci Resolve, Jianying, or any other editor.
- Modify Module 1-6 schema field meanings.
