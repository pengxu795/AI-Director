from modules.story import analyze_story, load_subtitles_json


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

    assert analysis["summary"]["subtitle_count"] == 3
    assert analysis["characters"] == [
        {"name": "女主", "mentions": 1},
        {"name": "妈妈", "mentions": 1},
        {"name": "孩子", "mentions": 1},
        {"name": "女儿", "mentions": 1},
    ]
    assert analysis["relationships"][0]["type"] == "亲子关系被否定"
    assert analysis["conflicts"][0]["text"] == "你不是我的亲生女儿"
    assert analysis["satisfying_points"][0]["reason"] == "终于"
    assert analysis["twists"][0]["text"] == "可门外的孩子，却喊了她一声妈妈"
    assert analysis["climax"]["text"] == "可门外的孩子，却喊了她一声妈妈"
    assert analysis["spoiler_warnings"][0]["reason"] == "亲生"
    assert "核心矛盾" in analysis["main_plot"]


def test_analyze_story_handles_empty_subtitles():
    analysis = analyze_story([])

    assert analysis["summary"] == {"subtitle_count": 0, "start": "", "end": ""}
    assert analysis["characters"] == []
    assert analysis["relationships"] == []
    assert analysis["main_plot"] == ""
    assert analysis["climax"] == {"text": "", "start": "", "end": "", "reason": ""}


def test_load_subtitles_json_reads_sample_output():
    subtitles = load_subtitles_json("output/sample_subtitles.json")

    assert len(subtitles) == 3
    assert subtitles[0]["text"] == "你不是我的亲生女儿"

