import ast
import json
from pathlib import Path

import pytest

from modules.adapters import (
    build_fcpxml_import_acceptance_protocol,
    validate_fcpxml_import_acceptance_protocol,
    write_fcpxml_import_acceptance_protocol,
)


def sample_design():
    return json.loads(Path("output/sample_fcpxml_design.json").read_text(encoding="utf-8"))


def test_acceptance_protocol_builds_manual_checklist_from_design():
    protocol = build_fcpxml_import_acceptance_protocol(sample_design(), "output/sample_minimal.fcpxml")

    assert protocol["schema_version"] == "1.0"
    assert protocol["status"] == "protocol_ready"
    assert protocol["target_editor"]["name"] == "Final Cut Pro"
    assert protocol["target_editor"]["validation_mode"] == "manual_import_only"
    assert protocol["target_editor"]["automatic_import_performed"] is False
    assert protocol["metadata"]["import_validation_performed"] is False
    assert protocol["metadata"]["media_files_read"] is False
    assert protocol["metadata"]["editor_launched"] is False
    assert protocol["metadata"]["video_export_performed"] is False
    assert {item["category"] for item in protocol["checklist"]} >= {
        "preflight",
        "resources",
        "timeline",
        "markers",
        "error_behavior",
    }
    assert all(item["status"] == "not_run" for item in protocol["checklist"])


def test_acceptance_protocol_preserves_expected_clip_and_marker_observations():
    protocol = build_fcpxml_import_acceptance_protocol(sample_design(), "output/sample_minimal.fcpxml")

    assert protocol["expected_clips"] == [
        {
            "clip_id": "clip_001",
            "asset_ref": "asset_001",
            "name": "drama_episode_01.mp4",
            "timeline_offset": "0s",
            "source_start": "5s",
            "duration": "37/25s",
            "source_story_block_id": "b001",
            "source_timeline_item_id": "t001",
            "reuse_policy": "primary",
        },
        {
            "clip_id": "clip_002",
            "asset_ref": "asset_002",
            "name": "drama_episode_01.mp4",
            "timeline_offset": "37/25s",
            "source_start": "7s",
            "duration": "37/25s",
            "source_story_block_id": "b002",
            "source_timeline_item_id": "t002",
            "reuse_policy": "primary",
        },
    ]
    assert protocol["expected_markers"] == [
        {
            "marker_id": "marker_001",
            "narration_segment_id": "n001",
            "source_timeline_item_id": "t001",
            "value": "她终于发现真相",
            "timeline_start": "0s",
            "expected_clip_id": "clip_001",
            "clip_relative_start": "0s",
        },
        {
            "marker_id": "marker_002",
            "narration_segment_id": "n002",
            "source_timeline_item_id": "t002",
            "value": "她开始反击",
            "timeline_start": "38/25s",
            "expected_clip_id": "clip_002",
            "clip_relative_start": "1/25s",
        },
    ]


def test_acceptance_protocol_validation_rejects_non_fcpxml_path():
    protocol = build_fcpxml_import_acceptance_protocol(sample_design(), "output/sample_minimal.xml")
    result = validate_fcpxml_import_acceptance_protocol(protocol)

    assert protocol["status"] == "blocked"
    assert result["valid"] is False
    assert any(error["code"] == "invalid_fcpxml_suffix" for error in result["errors"])


def test_acceptance_protocol_validation_rejects_prefilled_manual_results():
    protocol = build_fcpxml_import_acceptance_protocol(sample_design(), "output/sample_minimal.fcpxml")
    protocol["checklist"][0]["status"] = "passed"

    result = validate_fcpxml_import_acceptance_protocol(protocol)

    assert result["valid"] is False
    assert any(error["code"] == "checklist_must_start_not_run" for error in result["errors"])


def test_acceptance_protocol_validation_rejects_boundary_violations():
    protocol = build_fcpxml_import_acceptance_protocol(sample_design(), "output/sample_minimal.fcpxml")
    protocol["metadata"]["editor_launched"] = True

    result = validate_fcpxml_import_acceptance_protocol(protocol)

    assert result["valid"] is False
    assert any(error["code"] == "boundary_violation" for error in result["errors"])


def test_write_acceptance_protocol_writes_json_only(tmp_path):
    protocol = build_fcpxml_import_acceptance_protocol(sample_design(), "output/sample_minimal.fcpxml")
    output = tmp_path / "acceptance_protocol.json"

    result = write_fcpxml_import_acceptance_protocol(protocol, output)

    assert output.exists()
    assert result["status"] == "written"
    assert result["protocol_file_written"] is True
    assert result["media_files_read"] is False
    assert result["editor_launched"] is False
    assert result["import_validation_performed"] is False
    assert result["video_export_performed"] is False
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["manual_result_template"]["status"] == "not_run"


def test_acceptance_module_does_not_import_editor_or_media_automation_libraries():
    forbidden = {"ffmpeg", "cv2", "moviepy", "subprocess", "pyautogui", "AppKit", "Quartz"}
    for path in (
        Path("modules/adapters/fcpxml_acceptance.py"),
        Path("app/generate_fcpxml_acceptance_protocol.py"),
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not (imports & forbidden)


def test_invalid_protocol_is_not_written(tmp_path):
    protocol = build_fcpxml_import_acceptance_protocol(sample_design(), "output/sample_minimal.fcpxml")
    protocol["metadata"]["import_validation_performed"] = True

    with pytest.raises(ValueError):
        write_fcpxml_import_acceptance_protocol(protocol, tmp_path / "invalid.json")
    assert not (tmp_path / "invalid.json").exists()
