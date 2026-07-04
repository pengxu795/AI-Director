import ast
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from modules.adapters import (
    build_canonical_adapter_input,
    build_fcpxml_minimal_design,
    default_target_profiles,
    plan_adapter_export,
    serialize_fcpxml,
    validate_fcpxml_serialization_input,
    write_fcpxml_file,
)


def fcpxml_design():
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
                "source_start": "00:00:05.000",
                "source_end": "00:00:06.480",
                "timeline_start": "00:00:00.000",
                "timeline_end": "00:00:01.480",
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
                "fps": 25.0,
                "audio_available": True,
                "status": "bound",
                "validation_errors": [],
            }
        ],
        default_target_profiles()["fcpxml"],
    )
    plan = plan_adapter_export(adapter_input)
    plan["target_profile"] = {"target_id": "fcpxml", "sequence_fps": 25.0}
    return build_fcpxml_minimal_design(plan)


def test_validate_serializer_accepts_designed_input():
    result = validate_fcpxml_serialization_input(fcpxml_design())

    assert result["valid"] is True
    assert result["errors"] == []


def test_serialize_minimal_fcpxml_structure():
    xml_text = serialize_fcpxml(fcpxml_design())

    assert xml_text.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<!DOCTYPE fcpxml>" in xml_text
    root = ET.fromstring(xml_text.split("<!DOCTYPE fcpxml>\n", 1)[1])
    assert root.tag == "fcpxml"
    assert root.attrib["version"] == "1.10"
    assert root.find("./resources/format").attrib["frameDuration"] == "1/25s"
    asset = root.find("./resources/asset")
    assert asset.attrib["src"] == "file:///media/drama_episode_01.mp4"
    clip = root.find("./library/event/project/sequence/spine/asset-clip")
    assert clip.attrib == {
        "name": "drama_episode_01.mp4",
        "ref": "asset_001",
        "offset": "0s",
        "start": "5s",
        "duration": "37/25s",
    }
    marker = root.find("./library/event/project/sequence/spine/asset-clip/marker")
    assert marker.attrib["value"] == "她终于发现真相"


def test_blocked_design_does_not_serialize():
    design = fcpxml_design()
    design["status"] = "blocked"

    result = validate_fcpxml_serialization_input(design)
    assert result["valid"] is False
    assert any(error["code"] == "design_not_ready" for error in result["errors"])
    with pytest.raises(ValueError):
        serialize_fcpxml(design)


def test_unknown_clip_asset_ref_blocks_serialization():
    design = fcpxml_design()
    design["sequence_design"]["spine"][0]["ref"] = "asset_missing"
    result = validate_fcpxml_serialization_input(design)

    assert result["valid"] is False
    assert any(error["code"] == "unknown_clip_asset_ref" for error in result["errors"])


def test_write_fcpxml_file_outputs_only_fcpxml(tmp_path):
    output = tmp_path / "minimal.fcpxml"
    result = write_fcpxml_file(fcpxml_design(), output)

    assert output.exists()
    assert result["status"] == "written"
    assert result["fcpxml_file_written"] is True
    assert result["media_files_read"] is False
    assert result["editor_launched"] is False
    assert result["video_export_performed"] is False
    assert "<fcpxml version=\"1.10\">" in output.read_text(encoding="utf-8")


def test_write_requires_fcpxml_suffix(tmp_path):
    with pytest.raises(ValueError):
        write_fcpxml_file(fcpxml_design(), tmp_path / "minimal.xml")
    assert not (tmp_path / "minimal.xml").exists()


def test_serializer_module_does_not_import_media_processing_libraries():
    forbidden = {"ffmpeg", "cv2", "moviepy", "subprocess"}
    path = Path("modules/adapters/fcpxml_serializer.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert not (imports & forbidden)
