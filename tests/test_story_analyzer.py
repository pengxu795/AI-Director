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
    assert analysis["story_blocks"] == [
        {
            "id": "b001",
            "type": "opening",
            "summary": "你不是我的亲生女儿",
            "start": "00:02:15.200",
            "end": "00:02:18.800",
            "purpose": "建立开场信息",
        },
        {
            "id": "b002",
            "type": "conflict",
            "summary": "你不是我的亲生女儿",
            "start": "00:02:15.200",
            "end": "00:02:18.800",
            "purpose": "抛出核心矛盾",
        },
        {
            "id": "b003",
            "type": "climax",
            "summary": "可门外的孩子，却喊了她一声妈妈",
            "start": "00:02:23.000",
            "end": "00:02:26.500",
            "purpose": "推到剧情高潮",
        },
    ]
    assert analysis["scenes"][0]["type"] == "conflict"
    assert analysis["scenes"][0]["subtitle_count"] == 2
    assert analysis["scenes"][1]["type"] == "twist"
    assert analysis["conflicts"][0]["text"] == "你不是我的亲生女儿"
    assert analysis["satisfying_points"][0]["reason"] == "终于"
    assert analysis["twists"][0]["text"] == "可门外的孩子，却喊了她一声妈妈"
    assert analysis["climax"]["text"] == "可门外的孩子，却喊了她一声妈妈"
    assert analysis["spoiler_warnings"][0]["reason"] == "亲生"
    assert "核心矛盾" in analysis["main_plot"]


def test_analyze_story_handles_empty_subtitles():
    analysis = analyze_story([])

    assert analysis["schema_version"] == "0.1"
    assert analysis["summary"] == {
        "subtitle_count": 0,
        "scene_count": 0,
        "story_block_count": 0,
        "start": "",
        "end": "",
    }
    assert analysis["characters"] == []
    assert analysis["relationships"] == []
    assert analysis["main_plot"] == ""
    assert analysis["story_blocks"] == []
    assert analysis["scenes"] == []
    assert analysis["climax"] == {"text": "", "start": "", "end": "", "reason": ""}


def test_load_subtitles_json_reads_sample_output():
    subtitles = load_subtitles_json("output/sample_subtitles.json")

    assert len(subtitles) == 3
    assert subtitles[0]["text"] == "你不是我的亲生女儿"


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
