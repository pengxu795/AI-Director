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
- Module 3：解说稿生成（第一阶段）
- Module 4：镜头匹配与时间线规划（第一阶段）
- Module 5：编辑时间线生成（第一阶段）
- Module 6：导出包生成（第一阶段）
- Module 7：导出适配器合同研究

待开发：

- 第一个真实 editor-specific adapter

## 项目结构

```text
AI-Director/
├── README.md
├── PRD.md
├── CHANGELOG.md
├── PROJECT_STATE.md
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
├── prompts/
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
- `episodes`
- `story_blocks`
- `scenes`
- `conflicts`
- `satisfying_points`
- `twists`
- `climax`
- `spoiler_warnings`

关键约束：

- 顶层必须包含 `schema_version`
- 剧情节点必须保留 `evidence`
- 剧情节点必须保留 `source_range`
- 规则引擎判断必须保留 `confidence`
- 无效或缺失时间戳不编造时间，返回空 `source_range` 并降低 `confidence`
- 单条证据时间无效时，`confidence` 不高于 `0.2`
- 聚合时间范围使用有效字幕中的最早 `start` 和最晚 `end`
- 剧情顺序优先按有效时间码排序；无效时间码不会参与聚合时间范围
- `episodes` 在当前阶段表示单文件输入容器，`kind` 为 `input_container`，不是自动分集
- 人物 `aliases` 只保存明确同义称呼，不自动把“女主”和“妈妈”等身份称呼合并
- `story_blocks` 是 Module 3 解说生成的主要输入

运行示例：

```bash
.venv/bin/python app/analyze_story.py output/sample_subtitles.json output/sample_story_analysis.json
```

## Prompt Layer

Prompt 模板统一放在 `prompts/`，避免写死在 Python 代码里：

- `prompts/story_analysis.md`
- `prompts/script_generation.md`
- `prompts/matcher.md`
- `prompts/timeline_matching.md`
- `prompts/edit_timeline.md`
- `prompts/export_package.md`
- `prompts/export_adapter_contract.md`

## Module 3：解说稿生成

将 Module 2 的剧情分析 JSON 转换为可追溯的解说稿结构 JSON。第一阶段使用规则引擎，不调用模型 API。

当前 schema：

- `schema_version`
- `source_story_schema_version`
- `title_hooks`
- `narration_segments`
- `ending_hook`
- `metadata`

关键约束：

- `story_blocks` 是主要输入桥
- 每个 `narration_segments` 必须保留 `source_story_block_ids`
- 每个 `narration_segments` 必须保留 `source_ranges`
- 每个 `narration_segments` 和 `ending_hook` 必须保留 `reuse_policy`
- 非空 `title_hooks`、`narration_segments`、`ending_hook` 必须可追溯到输入 `story_blocks`
- `source_ranges` 必须来自对应 `story_blocks`
- 无可靠来源时返回空段或低 `confidence`，不编造剧情
- 当前不做镜头匹配，不生成时间线

运行示例：

```bash
python app/generate_script.py output/sample_story_analysis.json output/sample_script.json
```

## Module 4：镜头匹配与时间线规划

将 Module 3 的解说稿 JSON 映射为可供后续剪辑执行的 timeline JSON。第一阶段只做规划层，不读取、剪辑、渲染或导出视频文件。

当前 schema：

- `schema_version`
- `source_script_schema_version`
- `timeline`
- `unresolved_segments`
- `metadata`

每个 `timeline` item 保留：

- `id`
- `narration_segment_id`
- `segment_type`
- `text`
- `video_ranges`
- `selection_reason`
- `reuse_policy`
- `confidence`
- `status`

每个 `video_ranges` item 保留：

- `start`
- `end`
- `source_story_block_id`
- `priority`
- `reuse_policy`

关键约束：

- 只从 Module 2 `story_blocks` 的合法 `source_range` 生成 `video_ranges`
- 每个 `video_ranges` 必须保留 `source_story_block_id`
- 无 block id、block 不存在、时间无效或超出原始字幕有效范围时，返回 `unresolved`
- `unresolved` 不得输出视频范围，`confidence` 必须为 `0.0`
- 每个 `video_ranges` 独立标记 `reuse_policy`：首次使用为 `primary`，普通复用为 `duplicate`，ending hook 复用为 `callback`
- `timeline` item 的 `reuse_policy` 可为 `primary`、`duplicate`、`callback`、`mixed` 或 `unresolved`
- 空文本解说段不生成 timeline item
- 当前不做真实视频剪辑、渲染或导出

运行示例：

```bash
python app/generate_timeline.py output/sample_story_analysis.json output/sample_script.json output/sample_subtitles.json output/sample_timeline.json
```

## Module 5：编辑时间线生成

将 Module 4 的 timeline JSON 转换为编辑执行层可消费的统一 edit timeline JSON。第一阶段只生成编辑决策数据，不读取、剪辑、渲染或导出视频文件。

当前 schema：

- `schema_version`
- `source_timeline_schema_version`
- `sequence`
- `edit_segments`
- `tracks`
- `unresolved_items`
- `metadata`

关键约束：

- 只消费 Module 4 timeline JSON
- 只把合法且正时长的 `video_ranges` 转换为视频 clip
- `unresolved`、非法时间、倒置时间、零时长范围不得生成 clip
- 每个被拒绝的 `video_ranges` 必须进入 `unresolved_items`，并保留来源时间与原因
- 每个 clip 必须保留 `source_timeline_item_id`、`narration_segment_id`、`source_story_block_id` 和 `reuse_policy`
- 生成顺序化 `tracks.video` 和 `tracks.narration`，供后续导出器转换
- 当前不做真实视频剪辑、渲染或导出

运行示例：

```bash
python app/generate_edit_timeline.py output/sample_timeline.json output/sample_edit_timeline.json
```

## Module 6：导出包生成

将已完成的 edit timeline、解说稿和镜头匹配结果导出为可交付的 JSON/TXT 文件包。第一阶段只导出通用文件，不生成剪映、Premiere、DaVinci 工程，不读取、剪辑、渲染或导出视频文件。

导出文件：

- `manifest.json`
- `timeline.json`
- `narration_script.json`
- `narration_script.txt`
- `shot_list.json`
- `unresolved_items.json`

关键约束：

- `shot_list.json` 必须保留 clip 到 edit timeline、解说段和 story block 的追溯字段
- `narration_script` 必须跳过空文本段
- `unresolved_items` 必须合并编辑时间线和镜头匹配阶段的 unresolved 信息
- `manifest.json` 必须声明 `video_export_performed` 和 `editor_project_exported` 为 `false`
- 当前不生成真实视频、不生成编辑器工程文件

运行示例：

```bash
python app/export_package.py output/sample_edit_timeline.json output/sample_script.json output/sample_timeline.json output/export_package
```

## Module 7：导出适配器合同研究

定义未来剪辑软件导出的统一适配层合同。当前阶段只做 schema、校验、抽象计划和目标能力矩阵，不生成剪映、Premiere、DaVinci、FCPXML、XML、EDL、AAF 或工程文件。

关键合同：

- Canonical Adapter Input
- Media Asset Bindings
- Target Profile
- `validate(input) -> validation_result`
- `plan(input) -> adapter_plan`

Media Asset Binding 是外部注入层，用于把抽象 `source_story_block_id` / `source_timeline_item_id` 绑定到真实媒体资产。Module 1-6 不负责知道本地视频路径，也不得猜测 `source_file`。

只有 `status: "bound"` 且 `validation_errors: []` 的 binding 可以参与 adapter plan；`pending`、`unresolved`、`invalid` 或带校验错误的 binding 会阻断计划，并让对应 shot 保持 unresolved。

`binding.source_in/source_out` 表示媒体绑定允许使用的范围；`shot.source_start/source_end` 表示实际要放进剪辑时间线的镜头范围。Adapter plan 的 `place_clip` 必须使用 shot 级范围，并在 binding 范围冲突或多个 binding 歧义时阻断。

文档：

```text
docs/export_target_research.md
```
