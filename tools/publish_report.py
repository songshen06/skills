#!/usr/bin/env python3
import argparse
import datetime as dt
import html
import json
import re
import shutil
from pathlib import Path


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-_.\u4e00-\u9fff]", "", text)
    return text[:80] or "report"


def load_index(path: Path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_index(path: Path, items):
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def render_home(repo_root: Path, items):
    rows = []
    for item in items:
        title = html.escape(str(item.get("title", "Untitled")))
        date = html.escape(str(item.get("date", "")))
        symbol = html.escape(str(item.get("symbol", "")))
        notes = html.escape(str(item.get("notes", "")))
        href = html.escape(str(item.get("path", "")))
        rows.append(
            f"<tr><td>{date}</td><td>{title}</td><td>{symbol}</td><td>{notes}</td>"
            f"<td><a href=\"{href}\" target=\"_blank\">打开报告</a></td></tr>"
        )

    table_rows = "\n".join(rows) if rows else (
        '<tr><td colspan="5">暂无报告，先运行 publish_report.py 添加一份。</td></tr>'
    )

    content = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>A-Stock Reports</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif; margin: 24px; color: #1f2937; }}
    h1 {{ margin: 0 0 8px; }}
    .hint {{ color: #6b7280; margin-bottom: 18px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f9fafb; }}
    a {{ color: #2563eb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: #f3f4f6; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>A-Stock Report Index</h1>
  <p class=\"hint\">每次新增 HTML 报告后，运行 <code>python tools/publish_report.py --source /path/to/report.html --title 标题</code> 自动更新本页索引。</p>
  <table>
    <thead>
      <tr><th>日期</th><th>标题</th><th>代码</th><th>备注</th><th>链接</th></tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
</body>
</html>
"""
    (repo_root / "index.html").write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Add an HTML report and update GitHub Pages index.")
    parser.add_argument("--source", required=True, help="Source HTML report path")
    parser.add_argument("--title", required=True, help="Display title in index")
    parser.add_argument("--symbol", default="", help="Ticker/symbol")
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="Display date (YYYY-MM-DD)")
    parser.add_argument("--notes", default="", help="Optional note")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    reports_dir = repo_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    src = Path(args.source).expanduser().resolve()
    if not src.exists() or src.suffix.lower() != ".html":
        raise SystemExit(f"Invalid source html: {src}")

    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = slugify(src.stem)
    dst_name = f"{ts}-{stem}.html"
    dst = reports_dir / dst_name
    shutil.copy2(src, dst)

    index_path = reports_dir / "index.json"
    items = load_index(index_path)
    items.insert(0, {
        "date": args.date,
        "title": args.title,
        "symbol": args.symbol,
        "notes": args.notes,
        "path": f"reports/{dst_name}",
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
    })

    save_index(index_path, items)
    render_home(repo_root, items)
    print(f"Added: reports/{dst_name}")
    print("Updated: reports/index.json")
    print("Updated: index.html")


if __name__ == "__main__":
    main()
