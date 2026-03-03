---
name: "whisper-cpp"
description: "Local offline ASR/transcription for audio & video using whisper.cpp on macOS. Use when user asks to transcribe speech, generate subtitles (txt/srt/vtt/lrc), process Chinese/English audio, translate to English, or run batch transcription for files/directories/globs. Supports CPU/GPU control, custom output path, and structured JSON error reporting."
---

# Whisper CPP Speech Recognition Skill

This skill uses `whisper.cpp` to perform automatic speech recognition (ASR) on audio and video files locally on macOS. It supports Apple Silicon (Metal) acceleration.

## Trigger Phrases

Use this skill when user intent includes:

- Chinese: "转文字", "语音识别", "视频转字幕", "生成SRT/VTT", "批量转写", "会议录音整理"
- English: "transcribe", "speech to text", "generate subtitles", "SRT/VTT", "batch transcription", "offline ASR"
- Format/path intent: custom output filename/path, directory/glob input, local/private transcription

## When NOT To Use

Use other skills instead in these cases:

- `subtitle-translator`: user already has subtitle files (`.srt/.vtt/.txt`) and only needs translation.
- `subtitle-embedder`: user wants to mux/burn subtitles into video (soft/hard subtitles), not ASR transcription.
- `yt-dlp`: user first needs to download media/subtitles from online platforms before transcription.
- Non-local/cloud ASR requirement: user explicitly requires cloud APIs or managed SaaS transcription providers.

## Capabilities

- Transcribe audio files (mp3, wav, m4a, etc.)
- Transcribe video files (mp4, mov, mkv, etc.)
- Offline processing (privacy-focused)
- GPU acceleration on macOS

## Prerequisites

The underlying script requires the following tools to be installed on your macOS system:

- `ffmpeg` (for audio conversion)
- `git`
- `make` or `cmake`
- `c++` compiler (Xcode Command Line Tools)

You can install missing dependencies via Homebrew:

```bash
brew install ffmpeg git cmake
```

## Usage

The skill provides a helper Python script `transcribe.py` that handles the installation, building, audio conversion, and transcription process automatically.

### Basic Transcription

To transcribe a file:

```python
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/your/audio_or_video.mp4"
```

### Select Model Size

You can specify the model size (`tiny`, `base`, `small`, `medium`, `large`). Default is `base`. Larger models are more accurate but slower.

```python
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/file.mp3" --model small
```

### Generate Subtitles (Timestamps)

You can specify the output format to generate subtitles with timestamps. Supported formats: `txt`, `vtt`, `srt`, `lrc`. Default is `txt`.

```python
# Generate SRT subtitles
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/video.mp4" --format srt

# Generate VTT subtitles
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/video.mp4" --format vtt
```

### Language / Translation

```python
# Auto detect source language
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/file.mp3" --language auto

# Force Chinese transcription
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/file.mp3" --language zh

# Translate to English
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/file.mp3" --translate
```

### CPU/GPU Control

```python
# Force CPU mode
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/file.mp3" --force-cpu

# Force GPU mode (no auto fallback)
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/file.mp3" --force-gpu
```

### Custom Output Directory

```python
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/file.mp3" --output-dir "/path/to/output"
```

### Exact Output File (Single Input)

```python
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/file.mp3" --output-file "/path/to/output/my_transcript"
```

### Batch Transcription (Directory/Glob)

```python
# Multiple files
python3 .trae/skills/whisper-cpp/transcribe.py "/path/a.mp3" "/path/b.mp4" --format srt

# Directory batch
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/media_dir" --format txt

# Recursive directory batch
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/media_dir" --recursive --format srt

# Glob batch
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/media/*.mp3" --format txt
```

### Optional: Print transcript content

By default the script does not print full transcript text (to reduce noisy output).  
Use `--print-transcript` when needed:

```python
python3 .trae/skills/whisper-cpp/transcribe.py "/path/to/video.mp4" --format srt --print-transcript
```

## How it works

1. **Setup**: On first run, it clones `whisper.cpp` and compiles it.
   - Build priority: `make`; fallback to `cmake` when `make` fails.
2. **Model**: It downloads the specified Whisper model (GGML format) if missing.
3. **Convert**: It uses `ffmpeg` to convert the input file to the required 16kHz 16-bit Mono WAV format.
4. **Transcribe**: It runs the inference using `whisper.cpp`.
5. **Output**: Transcript files are saved beside the temporary WAV file.
6. **Agent Summary**: Script prints a JSON summary at the end (`status`, `output_file`, `model`, `format`, etc.).
   - Failures now include structured fields (`error_code`, `returncode`, `stderr_tail`) for easier debugging.
   - In batch mode, summary includes `total`, `succeeded`, `failed`, and per-file `results`.

## Troubleshooting

- If build fails, ensure Xcode Command Line Tools are installed (`xcode-select --install`).
- If `ffmpeg` is missing, install it via Homebrew.
- If GPU/Metal initialization fails on macOS, script auto-falls back to CPU unless `--force-gpu` is set.
