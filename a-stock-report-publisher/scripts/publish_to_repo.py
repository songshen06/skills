#!/usr/bin/env python3
import argparse
import shlex
import subprocess
from pathlib import Path


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(shlex.quote(x) for x in cmd)}\n{p.stderr.strip()}")
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser(description="Publish one A-stock html report to GitHub Pages repo")
    ap.add_argument("--source-html", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--symbol", default="")
    ap.add_argument("--notes", default="")
    ap.add_argument("--repo-path", default="/Users/shens/Downloads/skills/__a_stock_reports_repo")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    src = Path(args.source_html).expanduser().resolve()
    repo = Path(args.repo_path).expanduser().resolve()

    if not src.exists() or src.suffix.lower() != ".html":
        raise SystemExit(f"invalid source html: {src}")
    if not (repo / ".git").exists():
        raise SystemExit(f"invalid git repo path: {repo}")
    pub_tool = repo / "tools" / "publish_report.py"
    if not pub_tool.exists():
        raise SystemExit(f"missing publish tool: {pub_tool}")

    run([
        "python3", str(pub_tool),
        "--source", str(src),
        "--title", args.title,
        "--symbol", args.symbol,
        "--notes", args.notes,
    ], cwd=str(repo))

    run(["git", "add", "reports", "index.html", "reports/index.json"], cwd=str(repo))

    status = run(["git", "status", "--porcelain"], cwd=str(repo))
    if not status.strip():
        print("No changes to commit.")
        return

    msg = f"docs(reports): add {args.title}"
    run(["git", "commit", "-m", msg], cwd=str(repo))
    commit_id = run(["git", "rev-parse", "--short", "HEAD"], cwd=str(repo))

    if not args.no_push:
        run(["git", "push", "origin", "main"], cwd=str(repo))

    print(f"Published report: {src}")
    print(f"Repo: {repo}")
    print(f"Commit: {commit_id}")
    print(f"Pushed: {not args.no_push}")


if __name__ == "__main__":
    main()
