import json

from modules.editing import build_edit_timeline


def video_range(block_id, start, end, priority=1, reuse_policy="primary"):
    return {
        "start": start,
        "end": end,
        "source_story_block_id": block_id,
        "priority": priority,
        "reuse_policy": reuse_policy,
    }


def timeline_item(item_id, ranges, text="解说文本", status="matched", reuse_policy="primary", confidence=0.7):
    return {
        "id": item_id,
        "narration_segment_id": item_id.replace("t", "n"),
        "segment_type": "development",
        "text": text,
        "video_ranges": ranges,
        "selection_reason": "test",
        "reuse_policy": reuse_policy,
        "confidence": confidence,
        "status": status,
    }


def base_timeline(items=None):
    return {
        "schema_version": "1.0",
        "source_script_schema_version": "1.0",
        "timeline": items
        if items is not None
        else [
            timeline_item("t001", [video_range("b001", "00:00:01.000", "00:00:03.000")]),
            timeline_item("t002", [video_range("b002", "00:00:05.000", "00:00:06.500")]),
        ],
        "unresolved_segments": [],
        "metadata": {},
    }


def test_build_edit_timeline_outputs_stable_schema_and_tracks():
    edit_timeline = build_edit_timeline(base_timeline())

    assert edit_timeline["schema_version"] == "1.0"
    assert edit_timeline["source_timeline_schema_version"] == "1.0"
    assert edit_timeline["sequence"] == {
        "id": "seq001",
        "start": "00:00:00.000",
        "end": "00:00:03.500",
        "duration_ms": 3500,
    }
    assert len(edit_timeline["edit_segments"]) == 2
    assert len(edit_timeline["tracks"]["video"]) == 2
    assert len(edit_timeline["tracks"]["narration"]) == 2
    assert edit_timeline["metadata"]["video_editing_performed"] is False


def test_video_clips_are_laid_out_sequentially_from_source_ranges():
    edit_timeline = build_edit_timeline(base_timeline())

    clips = edit_timeline["tracks"]["video"]
    assert clips[0]["source_start"] == "00:00:01.000"
    assert clips[0]["source_end"] == "00:00:03.000"
    assert clips[0]["timeline_start"] == "00:00:00.000"
    assert clips[0]["timeline_end"] == "00:00:02.000"
    assert clips[0]["duration_ms"] == 2000
    assert clips[1]["timeline_start"] == "00:00:02.000"
    assert clips[1]["timeline_end"] == "00:00:03.500"
    assert clips[1]["duration_ms"] == 1500


def test_multiple_ranges_in_one_item_create_one_segment_with_multiple_clips():
    timeline = base_timeline(
        [
            timeline_item(
                "t001",
                [
                    video_range("b001", "00:00:01.000", "00:00:02.000", 1, "primary"),
                    video_range("b002", "00:00:03.000", "00:00:04.500", 2, "duplicate"),
                ],
                reuse_policy="mixed",
            )
        ]
    )

    edit_timeline = build_edit_timeline(timeline)

    assert edit_timeline["edit_segments"][0]["clip_ids"] == ["v001", "v002"]
    assert edit_timeline["edit_segments"][0]["reuse_policy"] == "mixed"
    assert [clip["reuse_policy"] for clip in edit_timeline["tracks"]["video"]] == ["primary", "duplicate"]
    assert edit_timeline["tracks"]["narration"][0]["clip_ids"] == ["v001", "v002"]


def test_unresolved_timeline_item_does_not_create_clips_or_narration():
    timeline = base_timeline([timeline_item("t001", [], status="unresolved", reuse_policy="unresolved")])

    edit_timeline = build_edit_timeline(timeline)

    assert edit_timeline["edit_segments"] == []
    assert edit_timeline["tracks"]["video"] == []
    assert edit_timeline["tracks"]["narration"] == []
    assert edit_timeline["unresolved_items"] == [
        {
            "source_timeline_item_id": "t001",
            "narration_segment_id": "n001",
            "segment_type": "development",
            "reason": "no_valid_clip_ranges",
        }
    ]


def test_invalid_or_zero_duration_ranges_are_unresolved_not_fabricated():
    timeline = base_timeline(
        [
            timeline_item("t001", [video_range("b001", "00:00:03.000", "00:00:03.000")]),
            timeline_item("t002", [video_range("b002", "00:00:05.000", "00:00:04.000")]),
            timeline_item("t003", [video_range("b003", "bad", "00:00:06.000")]),
        ]
    )

    edit_timeline = build_edit_timeline(timeline)

    assert edit_timeline["tracks"]["video"] == []
    assert [item["source_timeline_item_id"] for item in edit_timeline["unresolved_items"]] == ["t001", "t002", "t003"]


def test_reuse_policy_and_traceability_fields_are_preserved():
    timeline = base_timeline(
        [
            timeline_item(
                "t001",
                [video_range("b001", "00:00:01.000", "00:00:02.000", 1, "callback")],
                status="matched",
                reuse_policy="callback",
                confidence=0.8,
            )
        ]
    )

    edit_timeline = build_edit_timeline(timeline)
    clip = edit_timeline["tracks"]["video"][0]
    segment = edit_timeline["edit_segments"][0]

    assert clip["source_timeline_item_id"] == "t001"
    assert clip["narration_segment_id"] == "n001"
    assert clip["source_story_block_id"] == "b001"
    assert clip["reuse_policy"] == "callback"
    assert segment["source_timeline_item_id"] == "t001"
    assert segment["confidence"] == 0.8


def test_empty_text_timeline_item_is_skipped():
    edit_timeline = build_edit_timeline(
        base_timeline([timeline_item("t001", [video_range("b001", "00:00:01.000", "00:00:02.000")], text="")])
    )

    assert edit_timeline["edit_segments"] == []
    assert edit_timeline["tracks"]["video"] == []
    assert edit_timeline["unresolved_items"] == []


def test_edit_timeline_is_json_serializable():
    encoded = json.dumps(build_edit_timeline(base_timeline()), ensure_ascii=False)
    decoded = json.loads(encoded)

    assert decoded["schema_version"] == "1.0"
