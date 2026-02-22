# Repository Guidelines

## Project Structure & Module Organization
This repository is a Python-based A-share analysis skill focused on data collection and report generation.

- `scripts/`: executable analyzers and utilities (for example `a_stock_analyzer.py`, `index_analyzer.py`, `quick_report.py`).
- `scripts/templates/engine.py`: template rendering engine used by report generators.
- `templates/`: Markdown report templates (`stock_report_template.md`, `index_report_template.md`, `sector_report_template.md`).
- `references/`: reference report format and supporting docs.
- Root docs: `SKILL.md`, `TEMPLATES.md`, `使用指南.md`, `CHANGELOG.md`.

## Build, Test, and Development Commands
No packaging/build step is defined; run scripts directly.

- `python3 -m venv .venv && source .venv/bin/activate`: create and activate a local environment.
- `pip install -r requirements.txt`: install dependencies.
- `python3 scripts/test_templates.py`: validate all templates render and write outputs to `scripts/test_output/`.
- `python3 scripts/quick_report.py stock 600519 "贵州茅台"`: generate a stock report quickly.
- `python3 scripts/index_analyzer.py 000922 --name "中证红利"`: run index analysis.

## Coding Style & Naming Conventions
- Target Python 3 with PEP 8 conventions: 4-space indentation, snake_case for files/functions/variables.
- Keep script entrypoints in `if __name__ == "__main__":` blocks.
- Prefer clear, small functions over large procedural blocks.
- Use `black` and `flake8` (listed in `requirements.txt`) before submitting changes.

## Testing Guidelines
- Primary test entrypoint is `scripts/test_templates.py`.
- Add focused tests for any new template variables or render paths.
- Keep generated artifacts in `scripts/test_output/` for manual verification; do not commit transient debugging files.

## Commit & Pull Request Guidelines
Git history is not available in this workspace snapshot, so adopt a consistent standard:

- Commit format: `type(scope): short summary` (for example `feat(templates): add sector risk block`).
- Keep commits atomic and include rationale in the body for behavior changes.
- PRs should include: purpose, changed files, test commands run, and sample output/report snippets when templates change.

## Security & Configuration Tips
- Never hardcode API keys or credentials in scripts.
- Treat market/API responses as untrusted input; validate before rendering.
- Prefer local caches under `scripts/cache/` and avoid committing sensitive data dumps.
