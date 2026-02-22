#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


MODES = {
    "download_video",
    "download_audio",
    "list_formats",
    "metadata",
    "subtitles",
    "playlist",
    "kaltura",
}


def parse_args():
    p = argparse.ArgumentParser(description="Agent wrapper for yt-dlp.")
    p.add_argument("--mode", required=True, choices=sorted(MODES))
    p.add_argument("--url", required=True, help="Target URL")
    p.add_argument("--output-dir", default=".", help="Output directory")
    p.add_argument("--filename-template", default="%(title)s.%(ext)s")
    p.add_argument("--format-id", default=None)
    p.add_argument("--audio-format", default="mp3", choices=["mp3", "m4a", "wav", "flac", "opus"])
    p.add_argument("--sub-langs", default="en")
    p.add_argument("--auto-subs", action="store_true")
    p.add_argument("--cookies-from-browser", default=None)
    p.add_argument("--referer", default=None)
    p.add_argument("--partner-id", default=None)
    p.add_argument("--entry-id", default=None)
    p.add_argument("--retry-once", action="store_true", help="Retry once when command fails")
    p.add_argument("--retries", type=int, default=3, help="Pass-through to yt-dlp --retries")
    return p.parse_args()


def ensure_yt_dlp():
    if not shutil.which("yt-dlp"):
        return False, "yt-dlp not found in PATH"
    return True, None


def redact_cmd(cmd):
    redacted = []
    skip_next = False
    for i, token in enumerate(cmd):
        if skip_next:
            skip_next = False
            continue
        if token == "--cookies-from-browser":
            redacted.extend([token, "***"])
            skip_next = True
            continue
        redacted.append(token)
    return redacted


def build_command(args):
    out_dir = str(Path(args.output_dir))
    base = [
        "yt-dlp",
        "--restrict-filenames",
        "--paths",
        out_dir,
        "--retries",
        str(max(args.retries, 0)),
    ]

    if args.cookies_from_browser:
        base.extend(["--cookies-from-browser", args.cookies_from_browser])
    if args.referer:
        base.extend(["--referer", args.referer])

    cmd = list(base)
    should_collect_files = False

    if args.mode == "download_video":
        if args.format_id:
            cmd.extend(["-f", args.format_id])
        cmd.extend(["-o", args.filename_template, "--print", "after_move:filepath", "--no-playlist", args.url])
        should_collect_files = True
    elif args.mode == "download_audio":
        cmd.extend(
            [
                "-x",
                "--audio-format",
                args.audio_format,
                "-o",
                args.filename_template,
                "--print",
                "after_move:filepath",
                "--no-playlist",
                args.url,
            ]
        )
        should_collect_files = True
    elif args.mode == "list_formats":
        cmd.extend(["-F", "--no-playlist", args.url])
    elif args.mode == "metadata":
        cmd.extend(["--dump-single-json", "--no-playlist", args.url])
    elif args.mode == "subtitles":
        cmd.extend(
            [
                "--write-subs",
                "--sub-langs",
                args.sub_langs,
                "--convert-subs",
                "srt",
                "--skip-download",
                "-o",
                args.filename_template,
                "--print",
                "after_move:filepath",
                "--no-playlist",
                args.url,
            ]
        )
        if args.auto_subs:
            cmd.append("--write-auto-subs")
        should_collect_files = True
    elif args.mode == "playlist":
        cmd.extend(
            [
                "--yes-playlist",
                "-o",
                "%(playlist_index)s-%(title)s.%(ext)s",
                "--print",
                "after_move:filepath",
                args.url,
            ]
        )
        should_collect_files = True
    elif args.mode == "kaltura":
        if args.partner_id and args.entry_id:
            target = f"kaltura:{args.partner_id}:{args.entry_id}"
        else:
            target = args.url
        cmd.extend(["-o", args.filename_template, "--print", "after_move:filepath", target])
        should_collect_files = True
    else:
        raise ValueError(f"Unsupported mode: {args.mode}")

    return cmd, should_collect_files


def run_command(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def parse_output_files(stdout_text):
    files = []
    for ln in stdout_text.splitlines():
        candidate = ln.strip()
        if not candidate:
            continue
        # when using --print after_move:filepath, each printed line is a file path
        if "/" in candidate or "." in Path(candidate).name:
            p = Path(candidate)
            if p.exists():
                files.append(str(p.resolve()))
            else:
                files.append(candidate)
    # keep order, de-dup
    seen = set()
    uniq = []
    for f in files:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def summarize_error(stderr_text):
    lines = [ln.strip() for ln in stderr_text.splitlines() if ln.strip()]
    if not lines:
        return ""
    # keep tail lines with highest signal
    return " | ".join(lines[-3:])


def maybe_parse_metadata(stdout_text):
    try:
        data = json.loads(stdout_text.strip())
        return {
            "title": data.get("title"),
            "duration": data.get("duration"),
            "upload_date": data.get("upload_date"),
            "uploader": data.get("uploader"),
            "id": data.get("id"),
            "webpage_url": data.get("webpage_url"),
        }
    except Exception:
        return None


def main():
    args = parse_args()
    ok, err = ensure_yt_dlp()
    if not ok:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "mode": args.mode,
                    "url": args.url,
                    "command": [],
                    "output_files": [],
                    "metadata": None,
                    "stderr_summary": err,
                    "next_action": "Install yt-dlp and retry",
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    cmd, should_collect_files = build_command(args)
    redacted = redact_cmd(cmd)
    code, out, err_text = run_command(cmd)

    attempts = 1
    if code != 0 and args.retry_once:
        time.sleep(1.2)
        code, out, err_text = run_command(cmd)
        attempts += 1

    output_files = parse_output_files(out) if should_collect_files else []
    metadata = maybe_parse_metadata(out) if args.mode == "metadata" else None
    stderr_summary = summarize_error(err_text)

    if code == 0 and (args.mode in {"download_video", "download_audio", "playlist", "kaltura", "subtitles"}) and not output_files:
        status = "partial"
    else:
        status = "success" if code == 0 else "failed"

    next_action = ""
    if status == "failed" and args.mode in {"download_video", "download_audio"}:
        next_action = "Try mode=list_formats first, then pass --format-id"
    elif status == "failed" and args.mode == "kaltura":
        next_action = "Provide --referer and verify partner_id/entry_id"
    elif status == "failed":
        next_action = "Check stderr_summary and retry with adjusted parameters"

    result = {
        "status": status,
        "mode": args.mode,
        "url": args.url,
        "attempts": attempts,
        "command": redacted,
        "output_files": output_files,
        "metadata": metadata,
        "stderr_summary": stderr_summary,
        "next_action": next_action,
    }
    print(json.dumps(result, ensure_ascii=False))
    if status == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
