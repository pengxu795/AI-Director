import ast
from pathlib import Path

import pytest

from modules.adapters import (
    build_canonical_adapter_input,
    build_fcpxml_minimal_design,
    default_target_profiles,
    ensure_no_fcpxml_file_output,
    fcpxml_target_profile,
    fcpxml_time_from_timecode,
    frame_duration_from_fps,
    plan_adapter_export,
    validate_fcpxml_design_input,
)


def adapter_plan(
    sequence_fps=25.0,
    asset_fps=25.0,
    source_start="00:00:05.000",
    source_end="00:00:06.480",
    timeline_start="00:00:00.000",
    timeline_end="00:00:01.480",
):
    adapter_input = build_canonical_adapter_input(
        {"schema_version": "1.0"},
        {"schema_version": "1.0", "sequence": {"id": "seq001"}},
        {"schema_version": "1.0", "segments": [{"id": "n001", "text": "她终于发现真相"}]},
        [
            {
                "id": "v001",
                "source_timeline_item_id": "t001",
                "narration_segment_id": "n001",
                "source_story_block_id": "b001",
                "source_start": source_start,
                "source_end": source_end,
                "timeline_start": timeline_start,
                "timeline_end": timeline_end,
                "reuse_policy": "primary",
            }
        ],
        [],
        [
            {
                "media_asset_id": "m001",
                "source_story_block_id": "b001",
                "source_timeline_item_id": "t001",
                "source_file": "/media/drama_episode_01.mp4",
                "source_in": "00:00:00.000",
                "source_out": "00:00:10.000",
                "duration": "00:00:10.000",
                "fps": asset_fps,
                "audio_available": True,
                "status": "bound",
                "validation_errors": [],
            }
        ],
        default_target_profiles()["fcpxml"],
    )
    plan = plan_adapter_export(adapter_input)
    plan["target_profile"] = {"target_id": "fcpxml", "sequence_fps": sequence_fps}
    return plan


def test_fcpxml_target_profile_is_design_only():
    profile = fcpxml_target_profile()

    assert profile["target_id"] == "fcpxml"
    assert profile["target_version"] == "1.10"
    assert profile["output_kind"] == "abstract_fcpxml_design"
    assert profile["design_only"] is True
    assert profile["xml_generated"] is False
    assert profile["project_file_written"] is False
    assert profile["media_files_read"] is False


def test_timecode_conversion_uses_rational_seconds():
    assert fcpxml_time_from_timecode("00:00:05.000") == "5s"
    assert fcpxml_time_from_timecode("00:00:01.480") == "37/25s"
    assert frame_duration_from_fps(25.0) == "1/25s"
    assert frame_duration_from_fps(30) == "1/30s"
    assert frame_duration_from_fps("30000/1001") == "1001/30000s"


def test_minimal_design_maps_resources_and_shot_ranges():
    design = build_fcpxml_minimal_design(adapter_plan())

    assert design["status"] == "designed"
    assert design["xml_generated"] is False
    assert design["project_file_written"] is False
    assert design["media_files_read"] is False
    assert design["time_model"]["sequence_fps"] == "25.0"
    assert design["time_model"]["sequence_frame_duration"] == "1/25s"
    assert design["resources"]["sequence_format"]["id"] == "fmt001"
    assert design["resources"]["sequence_format"]["fps"] == "25.0"
    assert design["resources"]["assets"][0]["id"] == "asset_001"
    assert design["resources"]["assets"][0]["src"] == "/media/drama_episode_01.mp4"
    clip = design["sequence_design"]["spine"][0]
    assert clip["ref"] == "asset_001"
    assert clip["offset"] == "0s"
    assert clip["start"] == "5s"
    assert clip["duration"] == "37/25s"
    assert clip["source_story_block_id"] == "b001"


def test_sequence_fps_must_be_explicit():
    plan = adapter_plan()
    plan.pop("target_profile")
    result = validate_fcpxml_design_input(plan)

    assert result["valid"] is False
    assert any(error["code"] == "missing_sequence_fps" for error in result["errors"])


def test_sequence_fps_can_come_from_project_settings():
    plan = adapter_plan()
    plan.pop("target_profile")
    plan["project_settings"] = {"sequence_fps": 25.0}
    result = validate_fcpxml_design_input(plan)

    assert result["valid"] is True


def test_mixed_fps_is_blocked():
    plan = adapter_plan(sequence_fps=25.0)
    operations = [dict(operation) for operation in plan["operations"]]
    operations.insert(
        2,
        {
            "type": "register_media_asset",
            "media_asset_id": "m002",
            "source_file": "/media/other.mp4",
            "fps": 30.0,
            "duration": "00:00:10.000",
        },
    )
    plan["operations"] = operations
    result = validate_fcpxml_design_input(plan)

    assert result["valid"] is False
    assert any(error["code"] == "mixed_fps_not_supported" for error in result["errors"])


def test_sequence_fps_must_match_asset_fps_for_mvp():
    result = validate_fcpxml_design_input(adapter_plan(sequence_fps=30.0, asset_fps=25.0))

    assert result["valid"] is False
    assert any(error["code"] == "sequence_fps_asset_fps_mismatch" for error in result["errors"])


def test_non_frame_aligned_time_is_blocked_without_rounding():
    result = validate_fcpxml_design_input(adapter_plan(source_end="00:00:06.500", timeline_end="00:00:01.500"))

    assert result["valid"] is False
    assert any(error["code"] == "time_not_frame_aligned" for error in result["errors"])


def test_30000_1001_fps_frame_alignment_is_exact():
    result = validate_fcpxml_design_input(
        adapter_plan(
            sequence_fps="30000/1001",
            asset_fps="30000/1001",
            source_start="00:00:05.005",
            source_end="00:00:06.006",
            timeline_start="00:00:00.000",
            timeline_end="00:00:01.001",
        )
    )

    assert result["valid"] is True


def test_design_preserves_narration_as_marker_design_only():
    design = build_fcpxml_minimal_design(adapter_plan())

    markers = design["sequence_design"]["markers"]
    assert markers == [
        {
            "id": "marker_001",
            "narration_segment_id": "n001",
            "value": "她终于发现真相",
            "mapping": "marker_or_note_design_only",
        }
    ]


def test_invalid_or_blocked_adapter_plan_blocks_design():
    blocked_plan = dict(adapter_plan())
    blocked_plan["status"] = "blocked"
    result = validate_fcpxml_design_input(blocked_plan)
    design = build_fcpxml_minimal_design(blocked_plan)

    assert result["valid"] is False
    assert any(error["code"] == "adapter_plan_not_planned" for error in result["errors"])
    assert design["status"] == "blocked"
    assert design["xml_generated"] is False


def test_unregistered_clip_media_blocks_design():
    plan = adapter_plan()
    operations = [dict(operation) for operation in plan["operations"]]
    for operation in operations:
        if operation["type"] == "place_clip":
            operation["media_asset_id"] = "missing"
    plan["operations"] = operations
    result = validate_fcpxml_design_input(plan)

    assert result["valid"] is False
    assert any(error["code"] == "unregistered_media_asset" for error in result["errors"])


def test_invalid_clip_time_blocks_design():
    plan = adapter_plan()
    operations = [dict(operation) for operation in plan["operations"]]
    for operation in operations:
        if operation["type"] == "place_clip":
            operation["source_out"] = "00:00:05.000"
    plan["operations"] = operations
    result = validate_fcpxml_design_input(plan)

    assert result["valid"] is False
    assert any(error["code"] == "invalid_source_range" for error in result["errors"])


def test_minimal_outline_is_data_not_xml_text():
    design = build_fcpxml_minimal_design(adapter_plan())

    assert isinstance(design["minimal_outline"], dict)
    assert design["minimal_outline"]["fcpxml"]["version"] == "1.10"
    assert "xml" not in design or design["xml_generated"] is False
    assert "project_file" not in design


def test_file_output_interface_is_not_implemented(tmp_path):
    with pytest.raises(NotImplementedError):
        ensure_no_fcpxml_file_output(tmp_path / "draft.fcpxml")
    assert not (tmp_path / "draft.fcpxml").exists()


def test_fcpxml_design_module_does_not_import_media_or_process_libraries():
    forbidden = {"ffmpeg", "cv2", "moviepy", "subprocess", "xml"}
    path = Path("modules/adapters/fcpxml_design.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert not (imports & forbidden)
