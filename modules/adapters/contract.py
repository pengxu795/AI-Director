"""Export adapter contract for Module 7.

The adapter contract defines validation and abstract planning only. It does not
write editor projects, read media, transcode, render, or export video.
"""

from __future__ import annotations

from typing import Any


ADAPTER_CONTRACT_SCHEMA_VERSION = "1.0"

MEDIA_BINDING_REQUIRED_FIELDS = (
    "media_asset_id",
    "source_file",
    "source_in",
    "source_out",
    "duration",
    "fps",
    "audio_available",
    "status",
    "validation_errors",
)


def default_target_profiles() -> dict[str, dict[str, Any]]:
    """Return built-in abstract target profiles."""
    return {
        "fcpxml": {
            "target_id": "fcpxml",
            "target_version": "1.11",
            "supports_video_track": True,
            "supports_narration_track": True,
            "supports_markers": True,
            "supports_reuse_policy_metadata": True,
            "requires_media_asset_binding": True,
            "supports_round_trip": True,
            "output_kind": "abstract_fcpxml_plan",
            "known_limitations": ["Effects and editor-specific transitions are outside Module 7."],
        },
        "premiere_xml": {
            "target_id": "premiere_xml",
            "target_version": "fcp7_xml_interchange",
            "supports_video_track": True,
            "supports_narration_track": True,
            "supports_markers": True,
            "supports_reuse_policy_metadata": False,
            "requires_media_asset_binding": True,
            "supports_round_trip": False,
            "output_kind": "abstract_premiere_xml_plan",
            "known_limitations": ["Some metadata must be downgraded to comments or markers."],
        },
        "davinci_resolve": {
            "target_id": "davinci_resolve",
            "target_version": "fcpxml_or_edl",
            "supports_video_track": True,
            "supports_narration_track": True,
            "supports_markers": True,
            "supports_reuse_policy_metadata": False,
            "requires_media_asset_binding": True,
            "supports_round_trip": True,
            "output_kind": "abstract_resolve_plan",
            "known_limitations": ["Round-trip behavior depends on chosen interchange format."],
        },
        "jianying": {
            "target_id": "jianying",
            "target_version": "research_only",
            "supports_video_track": False,
            "supports_narration_track": False,
            "supports_markers": False,
            "supports_reuse_policy_metadata": False,
            "requires_media_asset_binding": True,
            "supports_round_trip": False,
            "output_kind": "research_only_no_project_output",
            "known_limitations": ["No stable public project interchange contract is assumed."],
        },
    }


def build_canonical_adapter_input(
    export_package_manifest: dict[str, Any],
    edit_timeline: dict[str, Any],
    narration_script: dict[str, Any],
    shot_list: list[dict[str, Any]],
    unresolved_items: list[dict[str, Any]],
    media_asset_bindings: list[dict[str, Any]],
    target_profile: dict[str, Any],
) -> dict[str, Any]:
    """Build the canonical adapter input object."""
    return {
        "schema_version": ADAPTER_CONTRACT_SCHEMA_VERSION,
        "export_package_manifest": export_package_manifest,
        "edit_timeline": edit_timeline,
        "narration_script": narration_script,
        "shot_list": shot_list,
        "unresolved_items": unresolved_items,
        "media_asset_bindings": media_asset_bindings,
        "target_profile": target_profile,
    }


def validate_adapter_input(adapter_input: dict[str, Any]) -> dict[str, Any]:
    """Validate canonical adapter input without producing editor files."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    unresolved_items = list(_safe_list(adapter_input.get("unresolved_items")))
    required_missing_fields: list[dict[str, str]] = []

    target_profile = _safe_dict(adapter_input.get("target_profile"))
    shot_list = _safe_list(adapter_input.get("shot_list"))
    narration_segments = _safe_list(_safe_dict(adapter_input.get("narration_script")).get("segments"))
    bindings = _safe_list(adapter_input.get("media_asset_bindings"))

    _validate_top_level(adapter_input, errors, required_missing_fields)
    _validate_target_profile(target_profile, errors, required_missing_fields)
    _validate_target_compatibility(target_profile, shot_list, narration_segments, errors, warnings)

    binding_index = _validate_media_asset_bindings(bindings, errors, required_missing_fields)
    if target_profile.get("requires_media_asset_binding") and not bindings:
        errors.append(_issue("missing_media_asset_bindings", "media_asset_bindings", "Target requires media bindings."))

    for shot in shot_list:
        binding = _matching_binding(shot, binding_index)
        if not binding:
            unresolved_items.append(
                {
                    "source_timeline_item_id": str(shot.get("source_timeline_item_id", "")),
                    "narration_segment_id": str(shot.get("narration_segment_id", "")),
                    "source_story_block_id": str(shot.get("source_story_block_id", "")),
                    "reason": "missing_media_asset_binding",
                }
            )

    target_compatibility = {
        "target_id": str(target_profile.get("target_id", "")),
        "output_kind": str(target_profile.get("output_kind", "")),
        "supports_video_track": bool(target_profile.get("supports_video_track")),
        "supports_narration_track": bool(target_profile.get("supports_narration_track")),
        "supports_reuse_policy_metadata": bool(target_profile.get("supports_reuse_policy_metadata")),
        "requires_media_asset_binding": bool(target_profile.get("requires_media_asset_binding")),
    }

    return {
        "valid": not errors and not unresolved_items,
        "errors": errors,
        "warnings": warnings,
        "unresolved_items": unresolved_items,
        "required_missing_fields": required_missing_fields,
        "target_compatibility": target_compatibility,
    }


def plan_adapter_export(adapter_input: dict[str, Any]) -> dict[str, Any]:
    """Return an abstract adapter plan without writing project or media files."""
    validation_result = validate_adapter_input(adapter_input)
    target_profile = _safe_dict(adapter_input.get("target_profile"))
    if not validation_result["valid"]:
        return {
            "schema_version": ADAPTER_CONTRACT_SCHEMA_VERSION,
            "target_id": str(target_profile.get("target_id", "")),
            "output_kind": str(target_profile.get("output_kind", "")),
            "status": "blocked",
            "operations": [],
            "validation_result": validation_result,
            "editor_project_generated": False,
            "media_files_read": False,
        }

    binding_index = _binding_index(_safe_list(adapter_input.get("media_asset_bindings")))
    operations = [
        {
            "type": "create_sequence",
            "sequence": _safe_dict(adapter_input.get("edit_timeline")).get("sequence", {}),
        }
    ]
    for binding in _safe_list(adapter_input.get("media_asset_bindings")):
        operations.append(
            {
                "type": "register_media_asset",
                "media_asset_id": str(binding.get("media_asset_id", "")),
                "source_file": str(binding.get("source_file", "")),
                "fps": binding.get("fps"),
                "duration": str(binding.get("duration", "")),
            }
        )

    for shot in _safe_list(adapter_input.get("shot_list")):
        binding = _matching_binding(shot, binding_index)
        operations.append(
            {
                "type": "place_clip",
                "media_asset_id": str(binding.get("media_asset_id", "")),
                "source_story_block_id": str(shot.get("source_story_block_id", "")),
                "source_timeline_item_id": str(shot.get("source_timeline_item_id", "")),
                "timeline_start": str(shot.get("timeline_start", "")),
                "timeline_end": str(shot.get("timeline_end", "")),
                "source_in": str(binding.get("source_in", "")),
                "source_out": str(binding.get("source_out", "")),
                "reuse_policy": str(shot.get("reuse_policy", "")),
            }
        )

    if target_profile.get("supports_narration_track"):
        for segment in _safe_list(_safe_dict(adapter_input.get("narration_script")).get("segments")):
            operations.append(
                {
                    "type": "add_narration_cue",
                    "narration_segment_id": str(segment.get("id", "")),
                    "text": str(segment.get("text", "")),
                }
            )

    return {
        "schema_version": ADAPTER_CONTRACT_SCHEMA_VERSION,
        "target_id": str(target_profile.get("target_id", "")),
        "output_kind": str(target_profile.get("output_kind", "")),
        "status": "planned",
        "operations": operations,
        "validation_result": validation_result,
        "editor_project_generated": False,
        "media_files_read": False,
    }


def export_adapter_project(*_args: Any, **_kwargs: Any) -> None:
    """Define the future export interface without implementing real export."""
    raise NotImplementedError("Module 7 defines the adapter export contract only; real editor export is gated.")


def _validate_top_level(
    adapter_input: dict[str, Any],
    errors: list[dict[str, str]],
    required_missing_fields: list[dict[str, str]],
) -> None:
    for field in (
        "export_package_manifest",
        "edit_timeline",
        "narration_script",
        "shot_list",
        "unresolved_items",
        "media_asset_bindings",
        "target_profile",
    ):
        if field not in adapter_input:
            issue = _issue("missing_required_field", field, f"Missing required top-level field: {field}.")
            errors.append(issue)
            required_missing_fields.append(issue)


def _validate_target_profile(
    target_profile: dict[str, Any],
    errors: list[dict[str, str]],
    required_missing_fields: list[dict[str, str]],
) -> None:
    for field in (
        "target_id",
        "target_version",
        "supports_video_track",
        "supports_narration_track",
        "supports_markers",
        "supports_reuse_policy_metadata",
        "requires_media_asset_binding",
        "supports_round_trip",
        "output_kind",
        "known_limitations",
    ):
        if field not in target_profile:
            issue = _issue("missing_required_field", f"target_profile.{field}", f"Missing target field: {field}.")
            errors.append(issue)
            required_missing_fields.append(issue)


def _validate_target_compatibility(
    target_profile: dict[str, Any],
    shot_list: list[dict[str, Any]],
    narration_segments: list[dict[str, Any]],
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> None:
    if shot_list and not target_profile.get("supports_video_track"):
        errors.append(_issue("unsupported_video_track", "target_profile.supports_video_track", "Target cannot place video clips."))
    if narration_segments and not target_profile.get("supports_narration_track"):
        warnings.append(
            _issue(
                "unsupported_narration_track",
                "target_profile.supports_narration_track",
                "Target cannot preserve narration as a track.",
            )
        )
    has_reuse_metadata = any(shot.get("reuse_policy") for shot in shot_list)
    if has_reuse_metadata and not target_profile.get("supports_reuse_policy_metadata"):
        warnings.append(
            _issue(
                "reuse_policy_metadata_not_supported",
                "target_profile.supports_reuse_policy_metadata",
                "Reuse policy metadata may need markers or sidecar files.",
            )
        )


def _validate_media_asset_bindings(
    bindings: list[dict[str, Any]],
    errors: list[dict[str, str]],
    required_missing_fields: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    for index, binding in enumerate(bindings):
        prefix = f"media_asset_bindings[{index}]"
        if not (binding.get("source_story_block_id") or binding.get("source_timeline_item_id")):
            issue = _issue(
                "missing_binding_source_reference",
                prefix,
                "Binding must reference source_story_block_id or source_timeline_item_id.",
            )
            errors.append(issue)
            required_missing_fields.append(issue)
        for field in MEDIA_BINDING_REQUIRED_FIELDS:
            if field not in binding or binding.get(field) in ("", None):
                issue = _issue("missing_required_field", f"{prefix}.{field}", f"Missing binding field: {field}.")
                errors.append(issue)
                required_missing_fields.append(issue)
        if "validation_errors" in binding and not isinstance(binding.get("validation_errors"), list):
            errors.append(_issue("invalid_field_type", f"{prefix}.validation_errors", "validation_errors must be a list."))
        if binding.get("status") not in ("bound", "unresolved", "invalid", "pending"):
            errors.append(_issue("invalid_binding_status", f"{prefix}.status", "Unsupported binding status."))
    return _binding_index(bindings)


def _binding_index(bindings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index = {}
    for binding in bindings:
        story_id = str(binding.get("source_story_block_id", ""))
        timeline_id = str(binding.get("source_timeline_item_id", ""))
        if story_id:
            index[f"story:{story_id}"] = binding
        if timeline_id:
            index[f"timeline:{timeline_id}"] = binding
    return index


def _matching_binding(shot: dict[str, Any], binding_index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    story_id = str(shot.get("source_story_block_id", ""))
    timeline_id = str(shot.get("source_timeline_item_id", ""))
    return binding_index.get(f"story:{story_id}") or binding_index.get(f"timeline:{timeline_id}")


def _issue(code: str, field: str, message: str) -> dict[str, str]:
    return {"code": code, "field": field, "message": message}


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
