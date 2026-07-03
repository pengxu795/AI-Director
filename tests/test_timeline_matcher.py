import json

from modules.timeline import generate_timeline


def story_block(block_id, start="00:00:01.000", end="00:00:02.000", confidence=0.7):
    return {
        "id": block_id,
        "type": "development",
        "summary": f"block {block_id}",
        "evidence": f"block {block_id}",
        "start": start,
        "end": end,
        "source_range": {"start": start, "end": end},
        "purpose": "test",
        "confidence": confidence,
    }


def narration_segment(segment_id, block_ids, text="解说文本", segment_type="development", confidence=0.8):
    return {
        "id": segment_id,
        "type": segment_type,
        "text": text,
        "source_story_block_ids": block_ids,
        "source_ranges": [],
        "confidence": confidence,
        "reuse_policy": "primary",
    }


def base_story(blocks=None):
    return {
        "schema_version": "0.1",
        "story_blocks": blocks
        if blocks is not None
        else [
            story_block("b001", "00:00:01.000", "00:00:02.000", 0.7),
            story_block("b002", "00:00:03.000", "00:00:04.000", 0.8),
        ],
    }


def base_script(segments=None, ending_hook=None):
    return {
        "schema_version": "1.0",
        "source_story_schema_version": "0.1",
        "title_hooks": [],
        "narration_segments": segments if segments is not None else [narration_segment("n001", ["b001"])],
        "ending_hook": ending_hook
        if ending_hook is not None
        else {
            "id": "n-ending",
            "type": "ending_hook",
            "text": "",
            "source_story_block_ids": [],
            "source_ranges": [],
            "confidence": 0.0,
            "reuse_policy": "callback",
        },
        "metadata": {},
    }


def subtitles():
    return [
        {"start": "00:00:03.000", "end": "00:00:04.000", "text": "second"},
        {"start": "00:00:01.000", "end": "00:00:02.000", "text": "first"},
        {"start": "", "end": "", "text": "missing"},
        {"start": "00:99:00.000", "end": "00:99:01.000", "text": "invalid"},
    ]


def test_normal_segment_maps_one_story_block():
    timeline = generate_timeline(base_story(), base_script(), subtitles())

    item = timeline["timeline"][0]
    assert item["status"] == "matched"
    assert item["reuse_policy"] == "primary"
    assert item["video_ranges"] == [
        {
            "start": "00:00:01.000",
            "end": "00:00:02.000",
            "source_story_block_id": "b001",
            "priority": 1,
        }
    ]


def test_one_segment_maps_multiple_valid_ranges_sorted_by_time():
    script = base_script([narration_segment("n001", ["b002", "b001"])])

    timeline = generate_timeline(base_story(), script, subtitles())

    assert timeline["timeline"][0]["status"] == "matched"
    assert [item["source_story_block_id"] for item in timeline["timeline"][0]["video_ranges"]] == ["b001", "b002"]
    assert [item["priority"] for item in timeline["timeline"][0]["video_ranges"]] == [1, 2]


def test_segment_without_source_story_block_ids_is_unresolved():
    script = base_script([narration_segment("n001", [])])

    timeline = generate_timeline(base_story(), script, subtitles())

    item = timeline["timeline"][0]
    assert item["status"] == "unresolved"
    assert item["reuse_policy"] == "unresolved"
    assert item["confidence"] == 0.0
    assert item["video_ranges"] == []
    assert timeline["unresolved_segments"][0]["reason"] == "missing_source_story_block_ids"


def test_missing_source_story_block_id_is_unresolved():
    script = base_script([narration_segment("n001", ["b404"])])

    timeline = generate_timeline(base_story(), script, subtitles())

    assert timeline["timeline"][0]["status"] == "unresolved"
    assert timeline["timeline"][0]["video_ranges"] == []
    assert timeline["unresolved_segments"][0]["reason"] == "source_story_block_id_not_found"


def test_invalid_story_block_time_is_unresolved():
    story = base_story([story_block("b001", "00:00:09.000", "00:00:08.000", 0.2)])

    timeline = generate_timeline(story, base_script(), subtitles())

    item = timeline["timeline"][0]
    assert item["status"] == "unresolved"
    assert item["reuse_policy"] == "unresolved"
    assert item["confidence"] == 0.0
    assert item["video_ranges"] == []


def test_hook_climax_and_ending_hook_reuse_same_block_with_stable_policy():
    script = base_script(
        [
            narration_segment("n001", ["b001"], "钩子", "hook"),
            narration_segment("n002", ["b001"], "高潮", "climax"),
        ],
        {
            "id": "n-ending",
            "type": "ending_hook",
            "text": "悬念",
            "source_story_block_ids": ["b001"],
            "source_ranges": [],
            "confidence": 0.7,
            "reuse_policy": "callback",
        },
    )

    timeline = generate_timeline(base_story(), script, subtitles())

    assert [item["reuse_policy"] for item in timeline["timeline"]] == ["primary", "duplicate", "callback"]
    assert [item["status"] for item in timeline["timeline"]] == ["matched", "matched", "matched"]


def test_out_of_order_ranges_are_sorted_in_output():
    story = base_story(
        [
            story_block("b001", "00:00:05.000", "00:00:06.000", 0.7),
            story_block("b002", "00:00:01.000", "00:00:02.000", 0.7),
        ]
    )
    script = base_script([narration_segment("n001", ["b001", "b002"])])
    source_subtitles = [
        {"start": "00:00:05.000", "end": "00:00:06.000", "text": "later"},
        {"start": "00:00:01.000", "end": "00:00:02.000", "text": "earlier"},
    ]

    timeline = generate_timeline(story, script, source_subtitles)

    assert [item["source_story_block_id"] for item in timeline["timeline"][0]["video_ranges"]] == ["b002", "b001"]


def test_all_matched_video_ranges_have_valid_start_end_order():
    timeline = generate_timeline(base_story(), base_script([narration_segment("n001", ["b001", "b002"])]), subtitles())

    for item in timeline["timeline"]:
        if item["status"] not in {"matched", "partial"}:
            continue
        for video_range in item["video_ranges"]:
            assert video_range["start"] <= video_range["end"]


def test_unresolved_segments_never_output_video_ranges():
    script = base_script(
        [
            narration_segment("n001", ["missing"]),
            narration_segment("n002", [], "没有来源"),
        ]
    )

    timeline = generate_timeline(base_story(), script, subtitles())

    assert timeline["unresolved_segments"]
    assert all(item["video_ranges"] == [] for item in timeline["timeline"] if item["status"] == "unresolved")


def test_empty_text_narration_segment_is_skipped():
    script = base_script(
        [
            narration_segment("n001", ["b001"], ""),
            narration_segment("n002", ["b001"], "有效文本"),
        ]
    )

    timeline = generate_timeline(base_story(), script, subtitles())

    assert [item["narration_segment_id"] for item in timeline["timeline"]] == ["n002"]


def test_timeline_output_is_json_serializable():
    encoded = json.dumps(generate_timeline(base_story(), base_script(), subtitles()), ensure_ascii=False)
    decoded = json.loads(encoded)

    assert decoded["schema_version"] == "1.0"
