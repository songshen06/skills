---
name: subtitle-to-article
description: Converts SRT subtitle files into detailed, well-structured Markdown articles. Use this skill when the user wants to turn a video transcript or subtitle file into a readable document.
---

# Subtitle to Article Converter

## Overview

This skill converts SRT subtitle files into comprehensive Markdown articles. It handles the parsing of the subtitle file to extract clean text and then uses LLM capabilities to structure that text into a coherent, readable article.

## Usage

When a user provides an SRT file and asks for an article:

1.  **Extract Text**: Run the provided Python script to parse the SRT file and get the raw text.
    ```bash
    python3 .trae/skills/subtitle-to-article/scripts/process_srt.py <path_to_srt_file>
    ```
    Recommended for agent pipeline:
    ```bash
    python3 .trae/skills/subtitle-to-article/scripts/process_srt.py <path_to_srt_file> \
      --output <clean_text.txt> \
      --json-summary
    ```

2.  **Generate Article**: using the extracted text, generate a detailed article following these guidelines:
    -   **Goal**: Create a "Deep Dive" or "Comprehensive Guide" document. The output should NOT be a brief summary. It must retain the depth and nuance of the original transcript while enhancing readability.
    -   **Title**: Create a relevant, professional title based on the content.
    -   **Introduction**: Provide a solid context, summarizing the main topic, target audience, and speaker(s).
    -   **Structure & Depth**:
        -   Organize content into logical sections with descriptive H2/H3 headings.
        -   **Retain Detail**: Do not over-simplify technical explanations. If the speaker goes into depth about a mechanism, the article must reflect that depth.
        -   **Q&A**: If the transcript includes a Q&A session, include a dedicated "Common Questions" or "Q&A" section.
    -   **Visual Enhancement (Mandatory)**:
        -   **Mermaid Diagrams**: You MUST identify at least 1-2 opportunities to insert Mermaid diagrams. Use `graph TD` for flows, hierarchies, or relationships. Use `sequenceDiagram` for interactions.
        -   **Tables**: You MUST look for opportunities to use Markdown tables. Use them for:
            -   Comparisons (e.g., Method A vs. Method B).
            -   Lists of parameters or properties.
            -   Timelines or schedules.
            -   Pros/Cons analysis.
    -   **Formatting**: Use bold text for key terms. Use code blocks for code snippets, commands, or file structures.
    -   **Cleanup**: Fix speech disfluencies but preserve the speaker's tone and technical accuracy.

3.  **Save Output**: Write the generated article to a new Markdown file (e.g., `Article_<OriginalFilename>.md`) in the same directory as the source file.

## Agent I/O Contract (Recommended)

- Input:
  - `srt_path` (required)
  - `output_text_path` (optional)
  - `join` = `paragraphs|single-line` (optional, default `paragraphs`)
- Output:
  - Cleaned transcript text (stdout or `--output`)
  - Optional JSON summary when `--json-summary` is enabled:
    - `status`, `input`, `output`, `paragraphs`, `chars`, `join`

## Resources

### Scripts
- `scripts/process_srt.py`: Python script to parse SRT files and extract clean text.
