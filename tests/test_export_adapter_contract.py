import ast
from pathlib import Path

import pytest

from modules.adapters import (
    build_canonical_adapter_input,
    default_target_profiles,
    export_adapter_project,
    plan_adapter_export,
    validate_adapter_input,
)


def manifest():
    return {
        "schema_version": "1.0",
        "metadata": {"video_export_performed": False, "editor_project_exported": False},
    }


def edit_timeline():
    return {
        "schema_version": "1.0",
        "sequence": {"id": "seq001", "start": "00:00:00.000", "end": "00:00:01.000", "duration_ms": 1000},
    }


def narration_script():
    return {
        "schema_version": "1.0",
        "segments": [{"id": "n001", "type": "hook", "text": "开场"}],
    }


def shot(**overrides):
    item = {
        "id": "v001",
        "edit_segment_id": "e001",
        "source_timeline_item_id": "t001",
        "narration_segment_id": "n001",
        "source_story_block_id": "b001",
        "source_start": "00:00:05.000",
        "source_end": "00:00:06.000",
        "timeline_start": "00:00:00.000",
        "timeline_end": "00:00:01.000",
        "duration_ms": 1000,
        "priority": 1,
        "reuse_policy": "primary",
    }
    item.update(overrides)
    return item


def shot_list():
    return [shot()]


def media_binding(**overrides):
    binding = {
        "media_asset_id": "m001",
        "source_story_block_id": "b001",
        "source_timeline_item_id": "t001",
        "source_file": "/media/drama_episode_01.mp4",
        "source_in": "00:00:05.000",
        "source_out": "00:00:06.000",
        "duration": "00:00:01.000",
        "fps": 25.0,
        "audio_available": True,
        "status": "bound",
        "validation_errors": [],
    }
    binding.update(overrides)
    return binding


def adapter_input(bindings=None, target_id="fcpxml", unresolved=None, shots=None):
    profiles = default_target_profiles()
    return build_canonical_adapter_input(
        manifest(),
        edit_timeline(),
        narration_script(),
        shots if shots is not None else shot_list(),
        unresolved if unresolved is not None else [],
        bindings if bindings is not None else [media_binding()],
        profiles[target_id],
    )


def test_valid_adapter_input_passes_validation():
    result = validate_adapter_input(adapter_input())

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["unresolved_items"] == []
    assert result["target_compatibility"]["target_id"] == "fcpxml"


def test_missing_media_asset_bindings_blocks_real_export_validation():
    result = validate_adapter_input(adapter_input(bindings=[]))

    assert result["valid"] is False
    assert any(error["code"] == "missing_media_asset_bindings" for error in result["errors"])
    assert result["unresolved_items"][0]["reason"] == "missing_media_asset_binding"


def test_missing_source_file_fps_and_duration_report_explicit_errors():
    result = validate_adapter_input(adapter_input(bindings=[media_binding(source_file="", fps=None, duration="")]))

    missing_fields = {item["field"] for item in result["required_missing_fields"]}
    assert "media_asset_bindings[0].source_file" in missing_fields
    assert "media_asset_bindings[0].fps" in missing_fields
    assert "media_asset_bindings[0].duration" in missing_fields
    assert result["valid"] is False


@pytest.mark.parametrize("status", ["pending", "unresolved", "invalid"])
def test_non_bound_media_asset_binding_blocks_planning(status):
    result = validate_adapter_input(adapter_input(bindings=[media_binding(status=status)]))
    plan = plan_adapter_export(adapter_input(bindings=[media_binding(status=status)]))

    assert result["valid"] is False
    assert any(error["code"] == "binding_not_bound" for error in result["errors"])
    assert result["unresolved_items"] == [
        {
            "source_timeline_item_id": "t001",
            "narration_segment_id": "n001",
            "source_story_block_id": "b001",
            "reason": "binding_not_bound",
        }
    ]
    assert plan["status"] == "blocked"
    assert not any(operation.get("type") == "place_clip" for operation in plan["operations"])


def test_media_asset_binding_with_validation_errors_blocks_planning():
    binding = media_binding(validation_errors=["source file does not exist"])
    result = validate_adapter_input(adapter_input(bindings=[binding]))
    plan = plan_adapter_export(adapter_input(bindings=[binding]))

    assert result["valid"] is False
    assert any(error["code"] == "binding_has_validation_errors" for error in result["errors"])
    assert result["unresolved_items"][0]["reason"] == "binding_has_validation_errors"
    assert plan["status"] == "blocked"
    assert not any(operation.get("type") == "place_clip" for operation in plan["operations"])


def test_mixed_bound_and_pending_bindings_only_unresolve_pending_shot():
    shots = [
        shot(id="v001", source_story_block_id="b001", source_timeline_item_id="t001"),
        shot(id="v002", source_story_block_id="b002", source_timeline_item_id="t002", narration_segment_id="n002"),
    ]
    bindings = [
        media_binding(media_asset_id="m001", source_story_block_id="b001", source_timeline_item_id="t001"),
        media_binding(media_asset_id="m002", source_story_block_id="b002", source_timeline_item_id="t002", status="pending"),
    ]
    result = validate_adapter_input(adapter_input(bindings=bindings, shots=shots))
    plan = plan_adapter_export(adapter_input(bindings=bindings, shots=shots))

    assert result["valid"] is False
    assert result["unresolved_items"] == [
        {
            "source_timeline_item_id": "t002",
            "narration_segment_id": "n002",
            "source_story_block_id": "b002",
            "reason": "binding_not_bound",
        }
    ]
    assert plan["status"] == "blocked"
    assert plan["operations"] == []


def test_existing_unresolved_items_never_become_fake_clip_operations():
    unresolved = [{"source_timeline_item_id": "t404", "reason": "missing_media_asset_binding"}]
    result = validate_adapter_input(adapter_input(unresolved=unresolved))
    plan = plan_adapter_export(adapter_input(unresolved=unresolved))

    assert result["valid"] is False
    assert result["unresolved_items"] == unresolved
    assert plan["status"] == "blocked"
    assert plan["operations"] == []


def test_target_unsupported_capabilities_are_reported():
    result = validate_adapter_input(adapter_input(target_id="jianying"))

    assert result["valid"] is False
    assert any(error["code"] == "unsupported_video_track" for error in result["errors"])
    assert any(warning["code"] == "unsupported_narration_track" for warning in result["warnings"])


def test_reuse_policy_metadata_warning_when_target_cannot_preserve_it():
    result = validate_adapter_input(adapter_input(target_id="premiere_xml"))

    assert result["valid"] is True
    assert any(warning["code"] == "reuse_policy_metadata_not_supported" for warning in result["warnings"])


def test_plan_is_abstract_and_does_not_write_project_files():
    plan = plan_adapter_export(adapter_input())

    assert plan["status"] == "planned"
    assert plan["editor_project_generated"] is False
    assert plan["media_files_read"] is False
    assert [operation["type"] for operation in plan["operations"]] == [
        "create_sequence",
        "register_media_asset",
        "place_clip",
        "add_narration_cue",
    ]
    assert "xml" not in plan
    assert "project_file" not in plan


def test_place_clip_uses_shot_source_range_not_binding_range():
    shots = [
        shot(id="v001", source_story_block_id="b001", source_timeline_item_id="t001", source_start="00:00:05.000", source_end="00:00:06.000"),
        shot(id="v002", source_story_block_id="b001", source_timeline_item_id="t002", source_start="00:00:07.000", source_end="00:00:08.000"),
    ]
    binding = media_binding(source_story_block_id="b001", source_timeline_item_id="", source_in="00:00:05.000", source_out="00:00:08.000")
    plan = plan_adapter_export(adapter_input(bindings=[binding], shots=shots))

    place_clips = [operation for operation in plan["operations"] if operation["type"] == "place_clip"]
    assert plan["status"] == "planned"
    assert [(clip["source_in"], clip["source_out"]) for clip in place_clips] == [
        ("00:00:05.000", "00:00:06.000"),
        ("00:00:07.000", "00:00:08.000"),
    ]
    assert all(clip["binding_source_in"] == "00:00:05.000" for clip in place_clips)
    assert all(clip["binding_source_out"] == "00:00:08.000" for clip in place_clips)


def test_shot_source_range_outside_binding_blocks_plan():
    bad_shot = shot(source_start="00:00:05.500", source_end="00:00:06.500")
    binding = media_binding(source_in="00:00:05.000", source_out="00:00:06.000")
    result = validate_adapter_input(adapter_input(bindings=[binding], shots=[bad_shot]))
    plan = plan_adapter_export(adapter_input(bindings=[binding], shots=[bad_shot]))

    assert result["valid"] is False
    assert any(error["code"] == "shot_source_range_outside_binding" for error in result["errors"])
    assert result["unresolved_items"][0]["reason"] == "shot_source_range_outside_binding"
    assert plan["status"] == "blocked"
    assert not any(operation.get("type") == "place_clip" for operation in plan["operations"])


@pytest.mark.parametrize(
    ("source_start", "source_end"),
    [
        ("00:00:06.000", "00:00:05.000"),
        ("00:00:05.000", "00:00:05.000"),
    ],
)
def test_invalid_shot_source_range_blocks_plan(source_start, source_end):
    bad_shot = shot(source_start=source_start, source_end=source_end)
    result = validate_adapter_input(adapter_input(shots=[bad_shot]))
    plan = plan_adapter_export(adapter_input(shots=[bad_shot]))

    assert result["valid"] is False
    assert any(error["code"] == "invalid_shot_source_range" for error in result["errors"])
    assert result["unresolved_items"][0]["reason"] == "invalid_shot_source_range"
    assert plan["status"] == "blocked"


def test_duplicate_story_binding_with_different_media_is_ambiguous():
    bindings = [
        media_binding(media_asset_id="m001", source_story_block_id="b001", source_timeline_item_id=""),
        media_binding(media_asset_id="m002", source_story_block_id="b001", source_timeline_item_id="", source_file="/media/other.mp4"),
    ]
    result = validate_adapter_input(adapter_input(bindings=bindings))
    plan = plan_adapter_export(adapter_input(bindings=bindings))

    assert result["valid"] is False
    assert any(error["code"] == "ambiguous_media_asset_binding" for error in result["errors"])
    assert result["unresolved_items"][0]["reason"] == "ambiguous_media_asset_binding"
    assert plan["status"] == "blocked"
    assert plan["operations"] == []


def test_story_and_timeline_binding_conflict_is_ambiguous():
    bindings = [
        media_binding(media_asset_id="m001", source_story_block_id="b001", source_timeline_item_id=""),
        media_binding(media_asset_id="m002", source_story_block_id="", source_timeline_item_id="t001", source_file="/media/other.mp4"),
    ]
    result = validate_adapter_input(adapter_input(bindings=bindings))

    assert result["valid"] is False
    assert any(error["code"] == "ambiguous_media_asset_binding" for error in result["errors"])
    assert result["unresolved_items"][0]["reason"] == "ambiguous_media_asset_binding"


def test_exact_duplicate_binding_is_deduped():
    binding = media_binding()
    plan = plan_adapter_export(adapter_input(bindings=[binding, dict(binding)]))

    assert plan["status"] == "planned"
    assert [operation["type"] for operation in plan["operations"]].count("register_media_asset") == 1
    assert [operation["type"] for operation in plan["operations"]].count("place_clip") == 1


def test_export_interface_is_defined_but_not_implemented():
    with pytest.raises(NotImplementedError):
        export_adapter_project(adapter_input())


def test_media_asset_binding_can_match_by_timeline_item_id():
    binding = media_binding(source_story_block_id="")
    result = validate_adapter_input(adapter_input(bindings=[binding]))

    assert result["valid"] is True


def test_adapter_module_does_not_import_media_processing_libraries():
    forbidden = {"ffmpeg", "cv2", "moviepy", "subprocess"}
    for path in Path("modules/adapters").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not (imports & forbidden)
