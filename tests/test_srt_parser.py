from modules.subtitle import parse_srt, parse_srt_file


def test_parse_srt_keeps_time_text_and_order():
    content = """1
00:02:15,200 --> 00:02:18,800
你不是我的亲生女儿

2
00:02:19,100 --> 00:02:22,400
女主愣住了
她终于明白自己被隐瞒多年
"""

    subtitles = parse_srt(content)

    assert subtitles == [
        {
            "start": "00:02:15.200",
            "end": "00:02:18.800",
            "text": "你不是我的亲生女儿",
        },
        {
            "start": "00:02:19.100",
            "end": "00:02:22.400",
            "text": "女主愣住了 她终于明白自己被隐瞒多年",
        },
    ]


def test_parse_sample_file():
    subtitles = parse_srt_file("data/examples/sample.srt")

    assert len(subtitles) == 3
    assert subtitles[0]["start"] == "00:02:15.200"
    assert subtitles[0]["text"] == "你不是我的亲生女儿"
