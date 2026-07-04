import ast
import hashlib
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
    assert protocol["metadata"]["fcpxml_file_read_for_sha256"] is True
    assert protocol["source_artifacts"]["fcpxml_path"] == "output/sample_minimal.fcpxml"
    assert len(protocol["source_artifacts"]["fcpxml_sha256"]) == 64
    assert protocol["source_artifacts"]["git_commit"] == ""
    assert protocol["source_artifacts"]["fully_traceable"] is False
    assert protocol["source_artifacts"]["acceptance_ready"] is False
    assert protocol["artifact_relationship"]["relationship_status"] == "insufficient_artifacts"
    assert protocol["artifact_relationship"]["relationship_verified"] is False
    assert any(error["code"] == "missing_artifact_revision_metadata" for error in protocol["validation_result"]["warnings"])
    assert any(error["code"] == "missing_source_design_artifact" for error in protocol["validation_result"]["warnings"])
    assert {item["category"] for item in protocol["checklist"]} >= {
        "preflight",
        "resources",
        "timeline",
        "markers",
        "error_behavior",
    }
    assert all(item["status"] == "not_run" for item in protocol["checklist"])
    assert "SHA-256" in protocol["checklist"][0]["expected_result"]


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


def test_acceptance_protocol_records_stable_fcpxml_sha256(tmp_path):
    fcpxml = tmp_path / "sample.fcpxml"
    fcpxml.write_text("<fcpxml version=\"1.10\" />\n", encoding="utf-8")
    protocol = build_fcpxml_import_acceptance_protocol(sample_design(), fcpxml, git_commit="abc123", serializer_commit="abc123")

    expected = hashlib.sha256(fcpxml.read_bytes()).hexdigest()

    assert protocol["status"] == "protocol_ready"
    assert protocol["source_artifacts"]["fcpxml_sha256"] == expected
    assert protocol["source_artifacts"]["fully_traceable"] is False
    assert protocol["source_artifacts"]["acceptance_ready"] is False
    assert any(error["code"] == "missing_source_design_artifact" for error in protocol["validation_result"]["warnings"])


def test_acceptance_protocol_sha256_changes_when_fcpxml_changes(tmp_path):
    fcpxml = tmp_path / "sample.fcpxml"
    fcpxml.write_text("first", encoding="utf-8")
    first = build_fcpxml_import_acceptance_protocol(sample_design(), fcpxml, git_commit="abc123", serializer_commit="abc123")
    fcpxml.write_text("second", encoding="utf-8")
    second = build_fcpxml_import_acceptance_protocol(sample_design(), fcpxml, git_commit="abc123", serializer_commit="abc123")

    assert first["source_artifacts"]["fcpxml_sha256"] != second["source_artifacts"]["fcpxml_sha256"]


def test_acceptance_protocol_blocks_missing_fcpxml_file(tmp_path):
    missing = tmp_path / "missing.fcpxml"
    protocol = build_fcpxml_import_acceptance_protocol(sample_design(), missing, git_commit="abc123", serializer_commit="abc123")

    assert protocol["status"] == "blocked"
    assert protocol["source_artifacts"]["fcpxml_sha256"] == ""
    assert protocol["source_artifacts"]["acceptance_ready"] is False
    assert any(error["code"] == "fcpxml_file_not_found" for error in protocol["validation_result"]["errors"])


def test_acceptance_protocol_warns_when_source_design_path_is_missing_despite_revision_metadata(tmp_path):
    fcpxml = tmp_path / "sample.fcpxml"
    fcpxml.write_text("<fcpxml version=\"1.10\" />\n", encoding="utf-8")

    protocol = build_fcpxml_import_acceptance_protocol(sample_design(), fcpxml, git_commit="abc123", serializer_commit="def456")

    assert protocol["status"] == "protocol_ready"
    assert protocol["source_artifacts"]["fcpxml_sha256"]
    assert protocol["source_artifacts"]["source_design_path"] == ""
    assert protocol["source_artifacts"]["source_design_sha256"] == ""
    assert protocol["source_artifacts"]["fully_traceable"] is False
    assert protocol["source_artifacts"]["acceptance_ready"] is False
    assert any(error["code"] == "missing_source_design_artifact" for error in protocol["validation_result"]["warnings"])


def test_acceptance_protocol_warns_when_source_design_file_is_missing(tmp_path):
    fcpxml = tmp_path / "sample.fcpxml"
    fcpxml.write_text("<fcpxml version=\"1.10\" />\n", encoding="utf-8")
    missing_design = tmp_path / "missing_design.json"

    protocol = build_fcpxml_import_acceptance_protocol(
        sample_design(),
        fcpxml,
        source_design_path=missing_design,
        git_commit="abc123",
        serializer_commit="def456",
    )

    assert protocol["status"] == "protocol_ready"
    assert protocol["source_artifacts"]["source_design_path"] == str(missing_design)
    assert protocol["source_artifacts"]["source_design_sha256"] == ""
    assert protocol["source_artifacts"]["fully_traceable"] is False
    assert protocol["source_artifacts"]["acceptance_ready"] is False
    assert any(error["code"] == "source_design_file_not_found" for error in protocol["validation_result"]["warnings"])


def test_acceptance_protocol_records_source_design_fingerprint_and_revision_metadata(tmp_path):
    design_path = tmp_path / "design.json"
    design_path.write_text(json.dumps(sample_design(), ensure_ascii=False), encoding="utf-8")
    protocol = build_fcpxml_import_acceptance_protocol(
        sample_design(),
        "output/sample_minimal.fcpxml",
        source_design_path=design_path,
        git_commit="abc123",
        serializer_module_version="1.0",
        serializer_commit="def456",
        generated_at="2026-07-04T00:00:00+00:00",
    )

    assert protocol["source_artifacts"]["source_design_path"] == str(design_path)
    assert protocol["source_artifacts"]["source_design_sha256"] == hashlib.sha256(design_path.read_bytes()).hexdigest()
    assert protocol["source_artifacts"]["git_commit"] == "abc123"
    assert protocol["source_artifacts"]["serializer_module_version"] == "1.0"
    assert protocol["source_artifacts"]["serializer_commit"] == "def456"
    assert protocol["source_artifacts"]["protocol_generated_at"] == "2026-07-04T00:00:00+00:00"
    assert protocol["source_artifacts"]["fully_traceable"] is True
    assert protocol["source_artifacts"]["acceptance_ready"] is True
    assert protocol["artifact_relationship"] == {
        "source_design_sha256": hashlib.sha256(design_path.read_bytes()).hexdigest(),
        "fcpxml_sha256": hashlib.sha256(Path("output/sample_minimal.fcpxml").read_bytes()).hexdigest(),
        "serializer_commit": "def456",
        "relationship_status": "fingerprinted_unverified",
        "relationship_verified": False,
        "manual_confirmation_required": True,
    }
    assert protocol["validation_result"]["warnings"] == [
        {
            "code": "markers_design_only",
            "field": "sequence_design.markers",
            "message": "Markers preserve narration text only; no audio is generated.",
        }
    ]


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
    assert saved["manual_result_template"]["artifact_identifiers"]["fcpxml_sha256"]
    assert "git_commit" in saved["manual_result_template"]["artifact_identifiers"]
    assert saved["manual_result_template"]["artifact_relationship"]["relationship_verified"] is False
    assert "artifact_relationship" in saved["checklist"][0]


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
