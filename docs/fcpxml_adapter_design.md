# Module 8: FCPXML Adapter Discovery / Minimal Export Design

## Goal

Module 8 selects FCPXML as the first concrete export target for design research. It defines the minimum mapping needed for a later real adapter, but it does not generate FCPXML, XML, editor project files, or media files.

## References

- Apple FCPXML Reference: https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference
- Apple Document Type Definition: https://developer.apple.com/documentation/professional-video-applications/document-type-definition
- Apple legacy DTD notes for time values: https://developer.apple.com/library/archive/documentation/Miscellaneous/Conceptual/LegacyDTDsFinalCutPro/FCPXMLDTDv1.7/FCPXMLDTDv1.7.html

## Selected Version

- Selected baseline: FCPXML `1.10`
- Reason: Apple's public DTD documentation currently identifies the FCPXML DTD baseline as the design reference.
- Constraint: A later gated module must verify import behavior inside Final Cut Pro before real export is considered complete.

## Time Model

Internal AI-Director timecodes use:

```text
HH:MM:SS.mmm
```

FCPXML time attributes use rational seconds, for example:

```text
5s
3/2s
1001/30000s
```

Module 8 conversion policy:

- Convert internal milliseconds to reduced rational seconds.
- Derive `frameDuration` from fps as seconds per frame.
- Do not model drop-frame behavior yet.
- Do not infer frame rate from media files.

## Resource ID Strategy

Resource IDs are deterministic within the adapter plan order:

- format: `fmt001`
- assets: `asset_001`, `asset_002`, ...
- clips: `clip_001`, `clip_002`, ...
- narration markers: `marker_001`, `marker_002`, ...

These IDs are design IDs only. A later real adapter may revise them if Final Cut Pro import behavior requires stricter naming.

## Field Mapping

| Adapter Plan Field | FCPXML Design Field |
| --- | --- |
| `register_media_asset.media_asset_id` | `resources.asset.id` |
| `register_media_asset.source_file` | `resources.asset.src` |
| `register_media_asset.duration` | `resources.asset.duration` |
| `register_media_asset.fps` | `resources.format.frameDuration` |
| `place_clip.media_asset_id` | `spine.asset-clip.ref` |
| `place_clip.timeline_start` | `spine.asset-clip.offset` |
| `place_clip.source_in` | `spine.asset-clip.start` |
| `place_clip.source_out - source_in` | `spine.asset-clip.duration` |
| `add_narration_cue.text` | marker or note design value |

## Minimal Outline

The design-only outline is:

```text
fcpxml
  resources
    format
    asset*
  library
    event
      project
        sequence
          spine
            asset-clip*
          marker*
```

This is an abstract outline, not XML text.

## Known Gaps

- Width and height require media probing and are intentionally unknown.
- Audio channel layout is not modeled.
- Narration is represented as marker or note design only; no generated audio asset exists.
- Drop-frame and non-integer frame-rate import behavior must be verified later.
- Final Cut Pro import testing is outside Module 8.

## Boundary

Module 8 does not:

- Generate `.fcpxml`, `.xml`, `.edl`, `.aaf`, or editor project files.
- Read, inspect, transcode, cut, render, or export video.
- Control Final Cut Pro or any other editor.
- Change Module 1-7 schema meanings.
