# Skills Repository

该仓库收录一组遵循通用 Skill 架构的能力模块，可由不同 AI Agent 编排调用（例如 `Trae`、`Codex` 等）。

核心目标：
- 每个 skill 独立目录，包含 `SKILL.md` 作为行为与调用约定
- 优先面向 agent orchestration（而非终端用户直接交互）
- 在多 agent 运行时保持一致输入/输出契约与可回退策略

## Skill Architecture (跨 Agent 兼容约定)

- 每个 skill 至少包含：
  - `SKILL.md`（能力描述、触发条件、参数、输出约定）
  - 必要脚本（如 `scripts/*.py` 或入口 `*.py`）
- 设计原则：
  - 明确输入参数（可映射为 agent 字段）
  - 明确输出结构（优先结构化文本 / JSON）
  - 失败可观测（非零退出码 + 可读错误摘要）
- 兼容性：
  - 不绑定单一 agent 实现细节
  - 可被 Trae、Codex 或其它支持技能编排的 Agent 复用

## Included Skills

- `a-stock-analysis`
- `analyzing-financial-statements`
- `subtitle-embedder`
- `subtitle-to-article`
- `subtitle-translator`
- `whisper-cpp`
- `yt-dlp`

## 1) a-stock-analysis

用途：
- A 股个股 / 指数 / 行业分析
- 生成 Markdown 与 HTML 报告
- 支持 rule / agent / hybrid 点评模式

入口（agent 内部执行）：
- `a-stock-analysis/scripts/quick_report.py`

示例：

```bash
python a-stock-analysis/scripts/quick_report.py stock 600941 "中国移动" \
  --narrative-mode hybrid \
  --output a-stock-analysis/test_output/中国移动_分析报告.md
```

测试开关（建议仅测试环境启用）：
- `--use-local-fin-fixture`：启用本地财报夹具回退
- `--force-live-on-empty-cache`：财报缓存为空/无效时，单次强制实时重取

## 2) analyzing-financial-statements

用途：
- 基于三大报表计算关键财务比率
- 作为 `a-stock-analysis` 的增强模块被自动加载

关键文件：
- `analyzing-financial-statements/calculate_ratios.py`
- `analyzing-financial-statements/interpret_ratios.py`
- `analyzing-financial-statements/SKILL.md`

## 3) subtitle-embedder

用途：
- 将字幕嵌入视频（软字幕/硬字幕）
- 支持双语字幕流与双语硬烧

关键文件：
- `subtitle-embedder/embed_subs.py`
- `subtitle-embedder/SKILL.md`

## 4) subtitle-to-article

用途：
- 从 SRT 提取文本并生成文章化输入材料
- 支持段落化输出与 JSON 摘要（供 agent 后续加工）

关键文件：
- `subtitle-to-article/scripts/process_srt.py`
- `subtitle-to-article/SKILL.md`

## 5) subtitle-translator

用途：
- 翻译 SRT/VTT/TXT 字幕
- 支持 LLM / Google / Ollama 路径
- 输出文件级状态（success/partial/failed）与 JSON 汇总

关键文件：
- `subtitle-translator/translate_subs.py`
- `subtitle-translator/merge_subs.py`
- `subtitle-translator/SKILL.md`

## 6) whisper-cpp

用途：
- 本地音视频转写（whisper.cpp）
- 支持 `make -> cmake` 构建回退
- 输出结构化 JSON 结果

关键文件：
- `whisper-cpp/transcribe.py`
- `whisper-cpp/SKILL.md`

## 7) yt-dlp

用途：
- 视频下载、音频提取、格式查询、元数据获取、字幕下载
- 通过统一 wrapper 入口提供稳定 agent 调用契约

关键文件：
- `yt-dlp/run_yt_dlp.py`
- `yt-dlp/SKILL.md`

## Agent 调用建议

- 以 agent 编排为主，不面向终端用户直接调用脚本。
- `a-stock-analysis` 负责数据抓取、报告结构和渲染。
- `analyzing-financial-statements` 负责财务指标计算与解释增强。
- 媒体相关 skill（`whisper-cpp` / `subtitle-*` / `yt-dlp`）建议统一采用结构化输出链路，便于上层 agent 串联。
- 生产默认关闭测试开关；仅在排障或回归测试时开启。

## 目录结构

```text
.
├── a-stock-analysis/
├── analyzing-financial-statements/
├── reports/
├── tools/
├── subtitle-embedder/
├── subtitle-to-article/
├── subtitle-translator/
├── whisper-cpp/
└── yt-dlp/
```

## GitHub Pages 报告主页

该仓库已支持一个简单的 HTML 报告索引主页：

- 首页：`index.html`
- 报告目录：`reports/`
- 发布脚本：`tools/publish_report.py`

### 首次启用

1. GitHub 仓库设置中打开 `Pages`
2. `Source` 选择 `Deploy from a branch`
3. 分支选择 `main`，目录选择 `/ (root)`

保存后访问：

- `https://songshen06.github.io/skills/`

### 每次新增一份报告

在仓库根目录执行：

```bash
python tools/publish_report.py \
  --source /绝对路径/你的报告.html \
  --title \"报告标题\" \
  --symbol \"股票代码\" \
  --notes \"可选备注\"
```

然后提交并推送：

```bash
git add reports index.html reports/index.json
git commit -m \"docs(reports): add new html report\"
git push
```
