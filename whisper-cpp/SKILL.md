---
name: "whisper-cpp"
description: "Transcribes audio and video files to text using whisper.cpp (High-performance OpenAI Whisper port). Optimized for macOS (Apple Silicon/Intel). Invoke when user wants to convert speech to text, transcribe meetings/videos, or extract subtitles."
---

# Whisper CPP Speech Recognition Skill

This skill uses `whisper.cpp` to perform automatic speech recognition (ASR) on audio and video files locally on macOS. It supports Apple Silicon (Metal) acceleration.

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

## Troubleshooting

- If build fails, ensure Xcode Command Line Tools are installed (`xcode-select --install`).
- If `ffmpeg` is missing, install it via Homebrew.
