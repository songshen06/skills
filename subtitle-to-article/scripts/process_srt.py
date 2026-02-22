import sys
import re
import os
import json
import argparse


TIMESTAMP_RE = re.compile(r"^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}[,\.]\d{3}")


def parse_blocks(content: str):
    raw_blocks = re.split(r"\n\s*\n", content.strip())
    text_blocks = []
    for block in raw_blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        cleaned = []
        for ln in lines:
            if ln.isdigit():
                continue
            if TIMESTAMP_RE.match(ln):
                continue
            cleaned.append(ln)
        if cleaned:
            text_blocks.append(" ".join(cleaned))
    return text_blocks


def build_paragraphs(text_blocks, max_chars=380):
    paragraphs = []
    cur = []
    cur_len = 0
    for block in text_blocks:
        b = block.strip()
        if not b:
            continue
        cur.append(b)
        cur_len += len(b) + 1
        should_break = False
        if cur_len >= max_chars:
            should_break = True
        if b.endswith(("。", "！", "？", ".", "!", "?", "；", ";")) and cur_len >= int(max_chars * 0.5):
            should_break = True
        if should_break:
            paragraphs.append(" ".join(cur).strip())
            cur = []
            cur_len = 0
    if cur:
        paragraphs.append(" ".join(cur).strip())
    return paragraphs

def clean_srt(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)

    text_blocks = parse_blocks(content)
    paragraphs = build_paragraphs(text_blocks)
    return paragraphs


def main():
    parser = argparse.ArgumentParser(description="Extract clean article-ready text from SRT.")
    parser.add_argument("file_path", help="Path to input .srt file")
    parser.add_argument("--output", "-o", help="Write extracted text to file")
    parser.add_argument(
        "--join",
        choices=["paragraphs", "single-line"],
        default="paragraphs",
        help="Output style: paragraphs (default) or single-line",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Print a JSON summary line after content",
    )
    args = parser.parse_args()

    paragraphs = clean_srt(args.file_path)
    if args.join == "single-line":
        text = " ".join(paragraphs).strip()
    else:
        text = "\n\n".join(paragraphs).strip()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + ("\n" if text else ""))

    print(text)

    if args.json_summary:
        print(
            json.dumps(
                {
                    "status": "success",
                    "input": args.file_path,
                    "output": args.output,
                    "paragraphs": len(paragraphs),
                    "chars": len(text),
                    "join": args.join,
                },
                ensure_ascii=False,
            )
        )

if __name__ == "__main__":
    main()
