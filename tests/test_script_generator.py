import json

from modules.script import generate_script, load_story_analysis_json


def story_block(block_id, block_type, summary, start="00:00:01.000", end="00:00:02.000", confidence=0.7):
    source_range = {"start": start, "end": end} if start and end else {"start": "", "end": ""}
    return {
        "id": block_id,
        "type": block_type,
        "summary": summary,
        "evidence": summary,
        "start": source_range["start"],
        "end": source_range["end"],
        "source_range": source_range,
        "purpose": "test",
        "confidence": confidence,
    }


def base_story_analysis():
    blocks = [
        story_block("b001", "conflict", "你不是我的亲生女儿"),
        story_block("b002", "satisfying_point", "女主终于明白自己被隐瞒多年", "00:00:03.000", "00:00:04.000"),
        story_block("b003", "climax", "可门外的孩子却喊了她一声妈妈", "00:00:05.000", "00:00:06.000", 0.8),
    ]
    return {
        "schema_version": "0.1",
        "characters": [
            {"id": "c001", "name": "女主", "aliases": ["女主"], "role": "protagonist", "mentions": 1},
            {"id": "c002", "name": "孩子", "aliases": ["孩子"], "role": "supporting", "mentions": 1},
        ],
        "relationships": [
            {
                "type": "亲子关系被否定",
                "evidence": "你不是我的亲生女儿",
                "source_range": {"start": "00:00:01.000", "end": "00:00:02.000"},
                "confidence": 0.7,
            }
        ],
        "main_plot": "剧情从“你不是我的亲生女儿”开始，并通过“可门外的孩子却喊了她一声妈妈”推进反转。",
        "story_blocks": blocks,
        "conflicts": [
            {
                "type": "conflict",
                "text": "你不是我的亲生女儿",
                "source_range": {"start": "00:00:01.000", "end": "00:00:02.000"},
                "confidence": 0.7,
            }
        ],
        "twists": [
            {
                "type": "twist",
                "text": "可门外的孩子却喊了她一声妈妈",
                "source_range": {"start": "00:00:05.000", "end": "00:00:06.000"},
                "confidence": 0.8,
            }
        ],
        "climax": {
            "text": "可门外的孩子却喊了她一声妈妈",
            "source_range": {"start": "00:00:05.000", "end": "00:00:06.000"},
            "confidence": 0.8,
        },
    }


def test_generate_script_outputs_stable_schema():
    script = generate_script(base_story_analysis())

    assert script["schema_version"] == "1.0"
    assert script["source_story_schema_version"] == "0.1"
    assert isinstance(script["title_hooks"], list)
    assert isinstance(script["narration_segments"], list)
    assert script["ending_hook"]["type"] == "ending_hook"
    assert script["metadata"]["generator"] == "rule_based"

    for segment in script["narration_segments"]:
        assert set(segment) == {
            "id",
            "type",
            "text",
            "source_story_block_ids",
            "source_ranges",
            "confidence",
            "reuse_policy",
        }


def test_generate_script_handles_empty_story_blocks():
    script = generate_script({"schema_version": "0.1", "story_blocks": []})

    assert script["narration_segments"] == []
    assert script["ending_hook"] == {
        "id": "n-ending",
        "type": "ending_hook",
        "text": "",
        "source_story_block_ids": [],
        "source_ranges": [],
        "confidence": 0.0,
        "reuse_policy": "callback",
    }
    assert script["metadata"]["source_story_block_count"] == 0


def test_generate_script_handles_conflict_without_twist():
    story = base_story_analysis()
    story["twists"] = []
    story["story_blocks"] = [story_block("b001", "conflict", "女主被赶出家门")]
    story["conflicts"] = [
        {
            "type": "conflict",
            "text": "女主被赶出家门",
            "source_range": {"start": "00:00:01.000", "end": "00:00:02.000"},
            "confidence": 0.7,
        }
    ]
    story["climax"] = {}

    script = generate_script(story)

    assert any(segment["type"] == "conflict" for segment in script["narration_segments"])
    assert script["ending_hook"]["source_story_block_ids"] == ["b001"]


def test_generate_script_handles_twist_without_conflict():
    story = base_story_analysis()
    story["conflicts"] = []
    story["story_blocks"] = [story_block("b001", "twist", "可孩子突然喊她妈妈")]

    script = generate_script(story)

    assert script["narration_segments"][0]["type"] == "hook"
    assert any(segment["type"] == "twist" for segment in script["narration_segments"])


def test_generate_script_handles_blocks_without_valid_time_range():
    story = base_story_analysis()
    story["story_blocks"] = [story_block("b001", "conflict", "女主发现真相", "", "", 0.2)]
    story["conflicts"] = []
    story["twists"] = []
    story["climax"] = {}

    script = generate_script(story)

    assert script["narration_segments"][0]["source_ranges"] == []
    assert script["narration_segments"][0]["confidence"] == 0.2
    assert script["metadata"]["has_valid_source_ranges"] is False


def test_every_narration_segment_traces_to_story_blocks():
    story = base_story_analysis()
    script = generate_script(story)
    valid_ids = {block["id"] for block in story["story_blocks"]}

    for segment in script["narration_segments"]:
        assert segment["source_story_block_ids"]
        assert set(segment["source_story_block_ids"]) <= valid_ids


def test_all_non_empty_script_outputs_trace_to_story_blocks():
    story = base_story_analysis()
    script = generate_script(story)
    blocks_by_id = {block["id"]: block for block in story["story_blocks"]}

    outputs = script["title_hooks"] + script["narration_segments"] + [script["ending_hook"]]
    for item in outputs:
        if not item["text"]:
            continue
        assert item["source_story_block_ids"]
        assert set(item["source_story_block_ids"]) <= set(blocks_by_id)
        expected_ranges = [
            blocks_by_id[block_id]["source_range"]
            for block_id in item["source_story_block_ids"]
            if blocks_by_id[block_id]["source_range"]["start"]
        ]
        assert item["source_ranges"] == expected_ranges


def test_generate_script_output_is_json_serializable():
    encoded = json.dumps(generate_script(base_story_analysis()), ensure_ascii=False)
    decoded = json.loads(encoded)

    assert decoded["schema_version"] == "1.0"


def test_ending_hook_does_not_repeat_climax_as_full_ending():
    script = generate_script(base_story_analysis())
    climax_text = base_story_analysis()["climax"]["text"]

    assert script["ending_hook"]["text"] != climax_text
    assert "秘密" in script["ending_hook"]["text"] or "答案" in script["ending_hook"]["text"]


def test_unmapped_twist_does_not_generate_confident_hooks():
    story = base_story_analysis()
    story["story_blocks"] = [story_block("b001", "development", "女主回到家")]
    story["twists"] = [
        {
            "type": "twist",
            "text": "这是无法映射的反转",
            "source_range": {"start": "00:09:01.000", "end": "00:09:02.000"},
            "confidence": 0.9,
        }
    ]
    story["conflicts"] = []
    story["climax"] = {}

    script = generate_script(story)

    assert all("无法映射" not in hook["text"] for hook in script["title_hooks"])
    assert script["ending_hook"] == {
        "id": "n-ending",
        "type": "ending_hook",
        "text": "",
        "source_story_block_ids": [],
        "source_ranges": [],
        "confidence": 0.0,
        "reuse_policy": "callback",
    }


def test_source_range_match_maps_external_moment_to_story_block():
    story = base_story_analysis()
    story["story_blocks"] = [
        story_block("b009", "twist", "孩子叫出了那个称呼", "00:00:09.000", "00:00:10.000", 0.6)
    ]
    story["twists"] = [
        {
            "type": "twist",
            "text": "外部文案和 block 不一样",
            "source_range": {"start": "00:00:09.000", "end": "00:00:10.000"},
            "confidence": 0.95,
        }
    ]
    story["conflicts"] = []
    story["climax"] = {}

    script = generate_script(story)

    assert script["title_hooks"][0]["source_story_block_ids"] == ["b009"]
    assert script["title_hooks"][0]["source_ranges"] == [
        {"start": "00:00:09.000", "end": "00:00:10.000"}
    ]
    assert script["title_hooks"][0]["confidence"] == 0.6


def test_ending_hook_reuses_climax_as_callback():
    script = generate_script(base_story_analysis())

    assert script["ending_hook"]["source_story_block_ids"] == ["b003"]
    assert script["ending_hook"]["reuse_policy"] == "callback"


def test_load_story_analysis_json_reads_sample_output():
    story = load_story_analysis_json("output/sample_story_analysis.json")

    assert story["schema_version"] == "0.1"
