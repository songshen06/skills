---
name: "yt-dlp"
description: "Agent-oriented media download skill using yt-dlp. Use for video/audio download, subtitle retrieval, and metadata extraction from supported sites."
---

# yt-dlp Skill (Agent-Orchestrated)

本 skill 面向 AI agent 调用编排，不是给终端用户手敲参数的说明书。
建议优先通过 `run_yt_dlp.py` 统一入口执行，而不是让 agent 直接拼接长命令。

## 0. Runtime Check

执行前先检查工具可用性：

```bash
yt-dlp --version
```

不可用时：
- macOS: `brew install yt-dlp`
- Python: `pip install yt-dlp`

## 1. Agent Input Contract

agent 侧建议传入以下字段：

- `url` (string, required): 目标页面或媒体地址
- `mode` (string, required): `download_video | download_audio | list_formats | metadata | subtitles | playlist | kaltura`
- `output_dir` (string, optional): 输出目录，默认当前目录
- `filename_template` (string, optional): 默认 `%(title)s.%(ext)s`
- `format_id` (string, optional): `mode=download_video` 且用户指定格式时使用
- `audio_format` (string, optional): `mp3|m4a|wav`，默认 `mp3`
- `sub_langs` (string, optional): 例如 `en,zh-Hans`
- `auto_subs` (bool, optional): 是否使用自动字幕，默认 `false`
- `cookies_from_browser` (string, optional): 如 `chrome`，仅用户明确要求时使用
- `referer` (string, optional): Kaltura 等场景使用
- `partner_id` (string, optional): `mode=kaltura` 时可传
- `entry_id` (string, optional): `mode=kaltura` 时可传
- `retry_once` (bool, optional): 失败时额外重试一次（默认 `false`）

## 2. Execution Mapping

推荐统一入口（agent 内部）：

```bash
python3 .trae/skills/yt-dlp/run_yt_dlp.py \
  --mode download_video \
  --url "URL" \
  --output-dir "." \
  --retry-once
```

### 2.1 download_video

- 默认最佳质量：

```bash
yt-dlp -o "%(title)s.%(ext)s" --restrict-filenames "URL"
```

- 指定格式：

```bash
yt-dlp -f <format_id> -o "%(title)s.%(ext)s" --restrict-filenames "URL"
```

### 2.2 list_formats

```bash
yt-dlp -F "URL"
```

### 2.3 download_audio

```bash
yt-dlp -x --audio-format mp3 -o "%(title)s.%(ext)s" --restrict-filenames "URL"
```

### 2.4 metadata

```bash
yt-dlp --dump-json "URL"
```

### 2.5 subtitles

- 列出字幕：

```bash
yt-dlp --list-subs "URL"
```

- 下载字幕（官方字幕）：

```bash
yt-dlp --write-subs --sub-langs "en,zh-Hans" --convert-subs srt "URL"
```

- 自动字幕：

```bash
yt-dlp --write-auto-subs --sub-langs "en" --convert-subs srt "URL"
```

### 2.6 playlist

```bash
yt-dlp --yes-playlist -o "%(playlist_index)s-%(title)s.%(ext)s" --restrict-filenames "URL"
```

### 2.7 kaltura (NVIDIA On-Demand 等)

当页面是 Kaltura 播放器时，优先流程：

1. 从页面源码提取 `partner_id` 和 `entry_id`
2. 构造 `kaltura:<partner_id>:<entry_id>`
3. 传入原页面 `referer`

```bash
yt-dlp -o "%(title)s.%(ext)s" --restrict-filenames --referer "https://original-page-url/" "kaltura:PARTNER_ID:ENTRY_ID"
```

## 3. Decision Flow (Agent)

1. 若用户要“先看可选清晰度”，先执行 `list_formats`。
2. 若用户要“只要音频”，执行 `download_audio`。
3. 若用户要“只要信息不下载”，执行 `metadata`。
4. 若 URL 为播放页且直下失败，尝试 `kaltura` 分支。
5. 涉及登录态时，只有在用户明确要求时才加 `cookies_from_browser`。

## 4. Output Contract (Return to Agent)

每次调用后，返回结构化摘要（文本或 JSON 均可）：

- `status`: `success | failed | partial`
- `mode`: 实际执行模式
- `url`: 输入 URL
- `command`: 实际执行命令（脱敏后）
- `output_files`: 产物路径列表
- `metadata`: 标题/时长/上传日期（可得则填）
- `stderr_summary`: 失败时的关键错误
- `next_action`: 建议下一步（如“先 list_formats 再选 format_id”）

`run_yt_dlp.py` 固定输出 JSON；失败时返回非零退出码。

## 5. Failure Handling

常见失败处理顺序：

1. 重试一次同命令
2. 若下载失败，先 `-F` 查看可用格式
3. 若站点限制，尝试补 `referer`
4. 若需要登录态，按用户指令加 `--cookies-from-browser`
5. 仍失败则返回 `failed` + `stderr_summary`

## 6. Recommended Defaults

- 文件命名：`--restrict-filenames`
- 默认模板：`%(title)s.%(ext)s`
- 非播放列表模式默认 `--no-playlist`
- 仅在用户要求时下载整个播放列表
- 对长任务优先输出进度并在结束后给出文件清单

## 7. Minimal Agent Examples

下载最佳视频：

```text
mode=download_video
url=https://example.com/video
```

对应命令：
```bash
python3 .trae/skills/yt-dlp/run_yt_dlp.py \
  --mode download_video \
  --url "https://example.com/video" \
  --retry-once
```

仅提取音频：

```text
mode=download_audio
url=https://example.com/video
audio_format=mp3
```

先列格式再下载指定码流：

```text
mode=list_formats
url=https://example.com/video
# Then:
mode=download_video
format_id=137+140
```

对应命令：
```bash
python3 .trae/skills/yt-dlp/run_yt_dlp.py \
  --mode list_formats \
  --url "https://example.com/video"
python3 .trae/skills/yt-dlp/run_yt_dlp.py \
  --mode download_video \
  --url "https://example.com/video" \
  --format-id "137+140"
```
