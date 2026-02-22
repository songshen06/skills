---
name: "subtitle-translator"
description: "Translates SRT, VTT, and TXT subtitle files to any language using AI while preserving timestamps. Invoke when user wants to translate subtitles or caption files."
---

# Subtitle Translator Skill

This skill allows you to translate subtitle files (`.srt`, `.vtt`, `.txt`) into any language using high-quality AI models (via OpenAI-compatible APIs like NVIDIA or OpenAI). It strictly preserves the original timestamps and formatting.

## Features

- **Multi-format Support**: Handles SRT, VTT, and TXT files.
- **Timestamp Preservation**: Ensures translated subtitles match the video timing perfectly.
- **Batch Processing**: Can process single files or entire directories.
- **AI-Powered**: Uses advanced LLMs for context-aware translation.

## Prerequisites

1.  **Python Environment**: Ensure you have Python installed.
2.  **Dependencies**: Install required packages:
    ```bash
    pip install -r .trae/skills/subtitle-translator/requirements.txt
    ```
3.  **API Key**: You need an API Key (e.g., NVIDIA API Key or OpenAI API Key).
    - Create a `.env` file in your project root:
      ```env
      NVIDIA_API_KEY=your_key_here
      # OR
      OPENAI_API_KEY=your_key_here
      ```

## Usage

Run the `translate_subs.py` script from your project root.

### Basic Usage

Translate a single file to Chinese using NVIDIA API (default):

```bash
python3 .trae/skills/subtitle-translator/translate_subs.py "path/to/movie.srt" --target-lang "Chinese"
```

### Local Ollama Usage

Translate using a local Ollama model (default: `translategemma:4b`):

```bash
python3 .trae/skills/subtitle-translator/translate_subs.py "path/to/movie.srt" --target-lang "Chinese" --service ollama
```

You can also specify a different local model:

```bash
python3 .trae/skills/subtitle-translator/translate_subs.py "path/to/movie.srt" --target-lang "Chinese" --service ollama --model "llama3"
```

### Batch Processing

Translate all subtitle files in a directory to Spanish:

```bash
python3 .trae/skills/subtitle-translator/translate_subs.py "path/to/subtitle_folder" --target-lang "Spanish"
```

### Advanced Options

- `--model`: Specify a custom model (default: `nvidia/qwen/qwen3-next-80b-a3b-instruct`).
- `--output-dir`: Save translated files to a specific directory.
- `--batch-size`: Number of lines to translate in one API call (default: 10).
- `--concurrency`: Number of concurrent API calls (default: 5).

Example with custom model and high concurrency:

```bash
python3 .trae/skills/subtitle-translator/translate_subs.py "movie.vtt" -t "French" --model "gpt-4o" --batch-size 30 --concurrency 20
```

## Output

The translated file will be saved with the language code appended, e.g., `movie.Chinese.srt`.
For safety, language suffix is sanitized for filesystem usage.

At the end of execution, the script prints a JSON summary for agent parsing:

```json
{
  "status": "success|partial|failed",
  "results": [
    {
      "file": "input path",
      "output": "output path",
      "status": "success|partial|failed",
      "total_lines": 120,
      "line_fallback_failures": 3,
      "batch_error_count": 1,
      "service": "llm|google|ollama",
      "model": "model name",
      "target_lang": "Chinese"
    }
  ]
}
```

`partial` / `failed` indicates fallback happened for some or all subtitle lines.
