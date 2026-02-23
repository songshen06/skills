---
name: a-stock-report-publisher
description: Publish newly generated A-stock HTML report to the dedicated GitHub Pages repo (songshen06/a-stock-reports), update index, commit, and push.
---

# A-Stock Report Publisher Skill

## When to use
- 用户说“把这份 HTML 报告发布/推送到仓库”
- 用户说“更新 GitHub Pages 报告主页索引”
- 用户说“新增一个报告条目到 a-stock-reports”

## Inputs
- `source_html` (required): 本地 HTML 报告绝对路径
- `title` (required): 报告显示标题
- `symbol` (optional): 股票代码
- `notes` (optional): 备注
- `repo_path` (optional): `a-stock-reports` 本地仓库路径
  - 默认: `/Users/shens/Downloads/skills/__a_stock_reports_repo`

## Behavior
1. 校验 `source_html` 存在且后缀为 `.html`
2. 在 `repo_path` 调用 `tools/publish_report.py` 复制报告并更新：
   - `reports/<timestamp>-*.html`
   - `reports/index.json`
   - `index.html`
3. 执行 `git add reports index.html reports/index.json`
4. 自动 commit（消息带报告标题）
5. push 到 `origin main`
6. 返回发布文件路径与 commit id

## Command template
```bash
python a-stock-report-publisher/scripts/publish_to_repo.py \
  --source-html "/abs/path/report.html" \
  --title "长江电力 600900 Agent分析报告" \
  --symbol "600900" \
  --notes "agent模式" \
  --repo-path "/Users/shens/Downloads/skills/__a_stock_reports_repo"
```

## Notes
- 该 skill 以 agent 调用为主。
- 支持 `--no-push` 用于本地测试，不推送远端。
