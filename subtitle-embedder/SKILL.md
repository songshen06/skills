---
name: "subtitle-embedder"
description: "Embeds subtitles into video files using FFmpeg. Supports both Soft Subtitles (muxing, fast) and Hard Subtitles (burning, compatible). Invoke when user wants to merge subtitles with video."
---

# Subtitle Embedder Skill

This skill allows you to embed SRT or VTT subtitles into a video file using `ffmpeg`.

## Features

- **Soft Subtitles (Default)**: Muxes subtitles into the video container as a separate stream.
  - Very fast (no re-encoding).
  - Toggle on/off in player.
  - Supports MP4 (`mov_text`) and MKV (`srt`).
- **Hard Subtitles**: Burns text permanently into the video frames.
  - Compatible with all players.
  - Requires re-encoding (slower).

## Prerequisites

- **FFmpeg**: Must be installed on the system.
  ```bash
  brew install ffmpeg
  ```
- **Python 3**: To run the wrapper script.
- **Optional for bilingual hard-burn merge**: `pysrt`
  ```bash
  pip install pysrt
  ```

## Usage

Run the `embed_subs.py` script.

### Basic Usage (Soft Subs)

Embeds subtitles as a stream (fastest).

```bash
python3 .trae/skills/subtitle-embedder/embed_subs.py "video.mp4" "subs.srt"
```

### Hard Subtitles (Burn-in)

Burns the subtitles into the video.

```bash
python3 .trae/skills/subtitle-embedder/embed_subs.py "video.mp4" "subs.srt" --hard
```

### Bilingual Support

You can provide a second subtitle file to create bilingual subtitles.

**Soft Subs**: Adds two separate subtitle streams (e.g., one for Chinese, one for English).

```bash
python3 .trae/skills/subtitle-embedder/embed_subs.py "video.mp4" "chinese.srt" "english.srt"
```

**Hard Subs**: Merges both subtitles into one (Dual-line display) and burns them into the video.

```bash
python3 .trae/skills/subtitle-embedder/embed_subs.py "video.mp4" "chinese.srt" "english.srt" --hard
```

### Specify Output Filename

```bash
python3 .trae/skills/subtitle-embedder/embed_subs.py "video.mp4" "subs.srt" -o "final_video.mp4"
```

### Specify Language (Soft Subs only)

Set the language metadata for the subtitle stream (default: `chi`).

```bash
python3 .trae/skills/subtitle-embedder/embed_subs.py "video.mp4" "subs.srt" --lang eng
```

## Agent Output

Script exits with non-zero code on failure and prints a JSON summary:

```json
{
  "status": "success|failed",
  "mode": "soft|hard",
  "video": "input video path",
  "subtitle": "primary subtitle path",
  "secondary_subtitle": "optional second subtitle path",
  "output": "output video path",
  "error": "only when failed"
}
```
