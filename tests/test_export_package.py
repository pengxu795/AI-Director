import json

from modules.exporter import build_export_package, export_file_package


def edit_timeline():
    return {
        "schema_version": "1.0",
        "sequence": {"id": "seq001", "start": "00:00:00.000", "end": "00:00:01.000", "duration_ms": 1000},
        "edit_segments": [
            {
                "id": "e001",
                "source_timeline_item_id": "t001",
                "narration_segment_id": "n001",
                "segment_type": "hook",
                "text": "开场钩子",
                "clip_ids": ["v001"],
                "narration_cue_id": "a001",
                "timeline_start": "00:00:00.000",
                "timeline_end": "00:00:01.000",
                "duration_ms": 1000,
                "reuse_policy": "primary",
                "source_status": "matched",
                "confidence": 0.8,
            }
        ],
        "tracks": {
            "video": [
                {
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
            ],
            "narration": [
                {
                    "id": "a001",
                    "edit_segment_id": "e001",
                    "source_timeline_item_id": "t001",
                    "narration_segment_id": "n001",
                    "text": "开场钩子",
                    "timeline_start": "00:00:00.000",
                    "timeline_end": "00:00:01.000",
                    "duration_ms": 1000,
                    "clip_ids": ["v001"],
                    "confidence": 0.8,
                }
            ],
        },
        "unresolved_items": [
            {
                "source_timeline_item_id": "t002",
                "narration_segment_id": "n002",
                "segment_type": "development",
                "source_story_block_id": "b404",
                "source_start": "bad",
                "source_end": "00:00:08.000",
                "reason": "invalid_timecode",
            }
        ],
        "metadata": {},
    }


def script():
    return {
        "schema_version": "1.0",
        "narration_segments": [
            {
                "id": "n001",
                "type": "hook",
                "text": "开场钩子",
                "source_story_block_ids": ["b001"],
                "source_ranges": [{"start": "00:00:05.000", "end": "00:00:06.000"}],
                "confidence": 0.8,
                "reuse_policy": "primary",
            },
            {
                "id": "n-empty",
                "type": "development",
                "text": "",
                "source_story_block_ids": [],
                "source_ranges": [],
                "confidence": 0.0,
                "reuse_policy": "primary",
            },
        ],
        "ending_hook": {
            "id": "n-ending",
            "type": "ending_hook",
            "text": "留下悬念",
            "source_story_block_ids": ["b002"],
            "source_ranges": [{"start": "00:00:07.000", "end": "00:00:08.000"}],
            "confidence": 0.7,
            "reuse_policy": "callback",
        },
    }


def timeline_plan():
    return {
        "schema_version": "1.0",
        "timeline": [],
        "unresolved_segments": [
            {
                "narration_segment_id": "n003",
                "segment_type": "twist",
                "reason": "missing_source_story_block_ids",
            }
        ],
        "metadata": {},
    }


def test_build_export_package_outputs_manifest_and_artifacts():
    package = build_export_package(edit_timeline(), script(), timeline_plan())

    assert set(package) == {"manifest", "artifacts"}
    assert package["manifest"]["schema_version"] == "1.0"
    assert package["manifest"]["metadata"]["video_export_performed"] is False
    assert package["manifest"]["metadata"]["editor_project_exported"] is False
    assert {item["path"] for item in package["manifest"]["files"]} == {
        "manifest.json",
        "narration_script.json",
        "narration_script.txt",
        "shot_list.json",
        "timeline.json",
        "unresolved_items.json",
    }


def test_shot_list_preserves_traceability_and_reuse_policy():
    package = build_export_package(edit_timeline(), script(), timeline_plan())

    shot = package["artifacts"]["shot_list.json"][0]
    assert shot == {
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


def test_narration_script_exports_json_and_text_without_empty_segments():
    package = build_export_package(edit_timeline(), script(), timeline_plan())

    narration = package["artifacts"]["narration_script.json"]
    assert [segment["id"] for segment in narration["segments"]] == ["n001", "n-ending"]
    assert "01. [hook] 开场钩子" in package["artifacts"]["narration_script.txt"]
    assert "02. [ending_hook] 留下悬念" in package["artifacts"]["narration_script.txt"]
    assert "n-empty" not in package["artifacts"]["narration_script.txt"]


def test_unresolved_items_merge_edit_and_timeline_unresolved_records():
    package = build_export_package(edit_timeline(), script(), timeline_plan())

    unresolved = package["artifacts"]["unresolved_items.json"]
    assert len(unresolved) == 2
    assert unresolved[0]["source_story_block_id"] == "b404"
    assert unresolved[1]["reason"] == "missing_source_story_block_ids"
    assert package["manifest"]["metadata"]["unresolved_count"] == 2


def test_export_package_files_are_written(tmp_path):
    edit_path = tmp_path / "edit.json"
    script_path = tmp_path / "script.json"
    timeline_path = tmp_path / "timeline.json"
    output_dir = tmp_path / "export"
    edit_path.write_text(json.dumps(edit_timeline(), ensure_ascii=False), encoding="utf-8")
    script_path.write_text(json.dumps(script(), ensure_ascii=False), encoding="utf-8")
    timeline_path.write_text(json.dumps(timeline_plan(), ensure_ascii=False), encoding="utf-8")

    package = export_file_package(edit_path, script_path, timeline_path, output_dir)

    assert sorted(path.name for path in output_dir.iterdir()) == [
        "manifest.json",
        "narration_script.json",
        "narration_script.txt",
        "shot_list.json",
        "timeline.json",
        "unresolved_items.json",
    ]
    loaded_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert loaded_manifest == package["manifest"]


def test_export_package_is_json_serializable():
    encoded = json.dumps(build_export_package(edit_timeline(), script(), timeline_plan()), ensure_ascii=False)
    decoded = json.loads(encoded)

    assert decoded["manifest"]["schema_version"] == "1.0"
