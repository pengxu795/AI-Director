import json

from modules.story import analyze_story, load_subtitles_json, split_scenes


def test_analyze_story_outputs_module_2_sections():
    subtitles = [
        {
            "start": "00:02:15.200",
            "end": "00:02:18.800",
            "text": "你不是我的亲生女儿",
        },
        {
            "start": "00:02:19.100",
            "end": "00:02:22.400",
            "text": "女主愣住了，她终于明白自己被隐瞒多年",
        },
        {
            "start": "00:02:23.000",
            "end": "00:02:26.500",
            "text": "可门外的孩子，却喊了她一声妈妈",
        },
    ]

    analysis = analyze_story(subtitles)

    assert analysis["schema_version"] == "0.1"
    assert analysis["summary"]["subtitle_count"] == 3
    assert analysis["summary"]["scene_count"] == 2
    assert analysis["summary"]["story_block_count"] == 3
    assert analysis["summary"]["episode_count"] == 1
    assert analysis["characters"] == [
        {
            "id": "c001",
            "name": "女主",
            "aliases": ["女主", "妈妈"],
            "role": "protagonist",
            "mentions": 1,
        },
        {
            "id": "c002",
            "name": "妈妈",
            "aliases": ["妈妈", "母亲"],
            "role": "supporting",
            "mentions": 1,
        },
        {
            "id": "c003",
            "name": "孩子",
            "aliases": ["孩子", "女儿", "儿子"],
            "role": "supporting",
            "mentions": 1,
        },
        {
            "id": "c004",
            "name": "女儿",
            "aliases": ["女儿"],
            "role": "unknown",
            "mentions": 1,
        },
    ]
    assert analysis["relationships"][0]["type"] == "亲子关系被否定"
    assert analysis["relationships"][0]["evidence"] == "你不是我的亲生女儿"
    assert analysis["relationships"][0]["source_range"] == {
        "start": "00:02:15.200",
        "end": "00:02:18.800",
    }
    assert analysis["episodes"] == [
        {
            "id": "e001",
            "title": "Episode 1",
            "start": "00:02:15.200",
            "end": "00:02:26.500",
            "source_range": {
                "start": "00:02:15.200",
                "end": "00:02:26.500",
            },
            "scene_ids": ["s001", "s002"],
            "story_block_ids": ["b001", "b002", "b003"],
            "confidence": 0.5,
        }
    ]
    assert analysis["story_blocks"] == [
        {
            "id": "b001",
            "type": "opening",
            "summary": "你不是我的亲生女儿",
            "evidence": "你不是我的亲生女儿",
            "start": "00:02:15.200",
            "end": "00:02:18.800",
            "source_range": {
                "start": "00:02:15.200",
                "end": "00:02:18.800",
            },
            "purpose": "建立开场信息",
            "confidence": 0.5,
        },
        {
            "id": "b002",
            "type": "conflict",
            "summary": "你不是我的亲生女儿",
            "evidence": "你不是我的亲生女儿",
            "start": "00:02:15.200",
            "end": "00:02:18.800",
            "source_range": {
                "start": "00:02:15.200",
                "end": "00:02:18.800",
            },
            "purpose": "抛出核心矛盾",
            "confidence": 0.65,
        },
        {
            "id": "b003",
            "type": "climax",
            "summary": "可门外的孩子，却喊了她一声妈妈",
            "evidence": "可门外的孩子，却喊了她一声妈妈",
            "start": "00:02:23.000",
            "end": "00:02:26.500",
            "source_range": {
                "start": "00:02:23.000",
                "end": "00:02:26.500",
            },
            "purpose": "推到剧情高潮",
            "confidence": 0.75,
        },
    ]
    assert analysis["scenes"][0]["type"] == "conflict"
    assert analysis["scenes"][0]["subtitle_count"] == 2
    assert analysis["scenes"][0]["source_range"] == {
        "start": "00:02:15.200",
        "end": "00:02:22.400",
    }
    assert analysis["scenes"][1]["type"] == "twist"
    assert analysis["conflicts"][0]["text"] == "你不是我的亲生女儿"
    assert analysis["conflicts"][0]["evidence"] == "你不是我的亲生女儿"
    assert analysis["conflicts"][0]["source_range"] == {
        "start": "00:02:15.200",
        "end": "00:02:18.800",
    }
    assert analysis["conflicts"][0]["confidence"] == 0.65
    assert analysis["satisfying_points"][0]["reason"] == "终于"
    assert analysis["satisfying_points"][0]["evidence"] == "女主愣住了，她终于明白自己被隐瞒多年"
    assert analysis["twists"][0]["text"] == "可门外的孩子，却喊了她一声妈妈"
    assert analysis["twists"][0]["evidence"] == "可门外的孩子，却喊了她一声妈妈"
    assert analysis["climax"]["text"] == "可门外的孩子，却喊了她一声妈妈"
    assert analysis["climax"]["evidence"] == "可门外的孩子，却喊了她一声妈妈"
    assert analysis["climax"]["source_range"] == {
        "start": "00:02:23.000",
        "end": "00:02:26.500",
    }
    assert analysis["spoiler_warnings"][0]["reason"] == "亲生"
    assert "核心矛盾" in analysis["main_plot"]


def test_analyze_story_handles_empty_subtitles():
    analysis = analyze_story([])

    assert analysis["schema_version"] == "0.1"
    assert analysis["summary"] == {
        "subtitle_count": 0,
        "scene_count": 0,
        "story_block_count": 0,
        "episode_count": 0,
        "start": "",
        "end": "",
    }
    assert analysis["characters"] == []
    assert analysis["relationships"] == []
    assert analysis["main_plot"] == ""
    assert analysis["episodes"] == []
    assert analysis["story_blocks"] == []
    assert analysis["scenes"] == []
    assert analysis["climax"] == {
        "text": "",
        "evidence": "",
        "start": "",
        "end": "",
        "source_range": {"start": "", "end": ""},
        "confidence": 0.0,
        "reason": "",
    }


def test_analyze_story_handles_missing_timecodes_with_low_confidence():
    subtitles = [
        {"start": "", "end": "", "text": "女主终于发现真相"},
    ]

    analysis = analyze_story(subtitles)

    assert analysis["summary"]["subtitle_count"] == 1
    assert analysis["summary"]["start"] == ""
    assert analysis["summary"]["end"] == ""
    assert analysis["episodes"] == [
        {
            "id": "e001",
            "title": "Episode 1",
            "start": "",
            "end": "",
            "source_range": {"start": "", "end": ""},
            "scene_ids": ["s001"],
            "story_block_ids": ["b001", "b002"],
            "confidence": 0.2,
        }
    ]
    assert analysis["satisfying_points"][0]["evidence"] == "女主终于发现真相"
    assert analysis["satisfying_points"][0]["source_range"] == {"start": "", "end": ""}
    assert analysis["satisfying_points"][0]["confidence"] == 0.35
    assert analysis["climax"]["source_range"] == {"start": "", "end": ""}
    assert analysis["climax"]["confidence"] == 0.35


def test_analyze_story_handles_single_subtitle():
    subtitles = [
        {
            "start": "00:00:01.000",
            "end": "00:00:02.000",
            "text": "女主回到家",
        }
    ]

    analysis = analyze_story(subtitles)

    assert analysis["summary"]["subtitle_count"] == 1
    assert analysis["summary"]["start"] == "00:00:01.000"
    assert analysis["summary"]["end"] == "00:00:02.000"
    assert analysis["episodes"][0]["source_range"] == {
        "start": "00:00:01.000",
        "end": "00:00:02.000",
    }
    assert analysis["story_blocks"][0]["type"] == "opening"


def test_analyze_story_handles_out_of_order_timecodes_without_invalid_ranges():
    subtitles = [
        {
            "start": "00:00:10.000",
            "end": "00:00:12.000",
            "text": "可孩子突然出现",
        },
        {
            "start": "00:00:01.000",
            "end": "00:00:02.000",
            "text": "女主回到家",
        },
    ]

    analysis = analyze_story(subtitles)

    assert analysis["summary"]["start"] == "00:00:01.000"
    assert analysis["summary"]["end"] == "00:00:12.000"
    assert analysis["episodes"][0]["source_range"] == {
        "start": "00:00:01.000",
        "end": "00:00:12.000",
    }
    for scene in analysis["scenes"]:
        assert scene["source_range"]["start"] <= scene["source_range"]["end"]


def test_analyze_story_rejects_reversed_time_range_for_evidence():
    subtitles = [
        {
            "start": "00:00:05.000",
            "end": "00:00:03.000",
            "text": "没想到真相被隐瞒",
        },
    ]

    analysis = analyze_story(subtitles)

    assert analysis["summary"]["start"] == ""
    assert analysis["summary"]["end"] == ""
    assert analysis["twists"][0]["source_range"] == {"start": "", "end": ""}
    assert analysis["twists"][0]["confidence"] == 0.35


def test_load_subtitles_json_reads_sample_output():
    subtitles = load_subtitles_json("output/sample_subtitles.json")

    assert len(subtitles) == 3
    assert subtitles[0]["text"] == "你不是我的亲生女儿"


def test_analyze_story_output_is_json_serializable():
    subtitles = [
        {
            "start": "00:00:01.000",
            "end": "00:00:02.000",
            "text": "可女主终于发现真相",
        }
    ]

    encoded = json.dumps(analyze_story(subtitles), ensure_ascii=False)
    decoded = json.loads(encoded)

    assert decoded["schema_version"] == "0.1"


def test_split_scenes_groups_adjacent_subtitles_by_story_type():
    subtitles = [
        {"start": "00:00:01.000", "end": "00:00:02.000", "text": "女主回到家"},
        {"start": "00:00:02.100", "end": "00:00:03.000", "text": "她发现真相被隐瞒"},
        {"start": "00:00:03.100", "end": "00:00:04.000", "text": "不是所有人都愿意相信她"},
        {"start": "00:00:04.100", "end": "00:00:05.000", "text": "可门外的人突然出现"},
    ]

    scenes = split_scenes(subtitles)

    assert [scene["type"] for scene in scenes] == ["opening", "conflict", "twist"]
    assert scenes[1]["subtitle_count"] == 2


def test_analyze_story_detects_twist_keywords_with_evidence_and_confidence():
    subtitles = [
        {"start": "00:00:01.000", "end": "00:00:02.000", "text": "女主准备离开"},
        {"start": "00:00:02.100", "end": "00:00:03.000", "text": "没想到门外的人却是孩子"},
    ]

    analysis = analyze_story(subtitles)

    assert analysis["twists"] == [
        {
            "type": "twist",
            "text": "没想到门外的人却是孩子",
            "evidence": "没想到门外的人却是孩子",
            "start": "00:00:02.100",
            "end": "00:00:03.000",
            "source_range": {
                "start": "00:00:02.100",
                "end": "00:00:03.000",
            },
            "confidence": 0.75,
            "reason": "却、没想到",
        }
    ]
