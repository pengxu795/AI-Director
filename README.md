# AI 短剧编导助手（MVP）

AI-Director 是一个面向短剧二创的 AI 编导助手。它不替代剪映，而是负责理解剧情、生成解说、匹配镜头和导出统一时间线；剪映继续负责字幕、配音、时间线精修和最终导出。

## MVP 流程

1. 导入短剧
2. 读取字幕
3. AI 分析剧情
4. AI 自动生成解说稿
5. 用户修改解说稿
6. AI 将解说稿逐句匹配到原字幕
7. 生成镜头时间线
8. 导出时间线

## 当前进度

已完成：

- Module 1：字幕解析
- Module 2：剧情分析

待开发：

- Module 3：解说稿生成
- Module 4：镜头匹配
- Module 5：时间线生成
- Module 6：导出

## 项目结构

```text
AI-Director/
├── README.md
├── PRD.md
├── requirements.txt
├── app/
├── modules/
│   ├── subtitle/
│   ├── story/
│   ├── script/
│   ├── matcher/
│   ├── timeline/
│   └── exporter/
├── data/
├── output/
└── tests/
```

## 安装

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Module 1：字幕解析

将 SRT 字幕解析为 JSON，保留时间码、文本和原顺序。

运行示例：

```bash
.venv/bin/python app/parse_subtitles.py data/examples/sample.srt output/sample_subtitles.json
```

运行测试：

```bash
.venv/bin/python -m pytest
```

## Module 2：剧情分析

将字幕 JSON 通过 Story Pipeline 分析为剧情结构 JSON，包含人物、人物关系、主线剧情、剧情块、场景分段、冲突、爽点、反转、高潮和不可剧透内容。

当前 schema：

- `schema_version`
- `characters`
- `relationships`
- `main_plot`
- `story_blocks`
- `scenes`
- `conflicts`
- `satisfying_points`
- `twists`
- `climax`
- `spoiler_warnings`

运行示例：

```bash
.venv/bin/python app/analyze_story.py output/sample_subtitles.json output/sample_story_analysis.json
```

## Prompt Layer

Prompt 模板统一放在 `prompts/`，避免写死在 Python 代码里：

- `prompts/story_analysis.md`
- `prompts/script_generation.md`
- `prompts/matcher.md`
