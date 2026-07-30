---
name: diff40-backtest
description: Backtest and monitor 40-day return differential (DIFF40) strategies for CSI index pairs. Run rotation or rebalancing backtests, set up daily DIFF40 monitoring, and generate charts. Use when the user asks to backtest DIFF40, 40日收益差, CSI Dividend timing, A500 vs Dividend rotation/rebalancing, or when setting up daily DIFF40 alerts.
---

# DIFF40 Backtest & Monitor

Backtest rotation and rebalancing strategies based on the 40-day return differential (DIFF40) between any two CSI indices. Also supports daily monitoring with state persistence.

## Quick Start

### Rotation Backtest (switching allocation based on DIFF40 thresholds)

```bash
python3 scripts/backtest.py \
  --symbol1 H00922 --symbol2 000985 \
  --label1 "CSI Dividend TR" --label2 "CSI All Share" \
  --mode rotation --entry -0.10 --exit 0.10 \
  --output output/diff40_rotation.png
```

### Rebalancing Backtest (50/50 with DIFF40 trigger to rebalance)

```bash
python3 scripts/backtest.py \
  --symbol1 000922 --symbol2 000510 \
  --label1 "CSI Dividend" --label2 "CSI A500" \
  --mode rebalance --entry -0.10 \
  --output output/diff40_rebalance.png
```

### Daily Check

```bash
python3 scripts/daily_check.py \
  --symbol1 H00922 --symbol2 000985 \
  --label1 "CSI Dividend TR" --label2 "CSI All Share" \
  --state-file data/diff40_state.json
```

## Parameters

### backtest.py

| Param | Default | Description |
|-------|---------|-------------|
| --symbol1 | 000922 | First index code |
| --symbol2 | 000510 | Second index code |
| --label1/2 | Asset 1/2 | Display labels |
| --mode | rotation | rotation, rebalance, or both |
| --entry | -0.10 | Entry threshold for rotation; absolute threshold for rebalance |
| --exit | 0.10 | Exit threshold (rotation only) |
| --start | 20050101 | Start date |
| --end | 20501231 | End date |
| --output | /tmp/... | Chart output path |
| --no-chart | false | Skip chart generation |
| --cache-dir | none | Directory for CSV cache (e.g. data/cache) |
| --refresh | false | Force re-download, ignore cache |

### Data Caching

Use `--cache-dir` to persist downloaded data as CSV. Second run is ~75x faster.

```bash
# First run: downloads & caches (~2 min)
python3 scripts/backtest.py --symbol1 000922 --symbol2 000510 \
  --cache-dir data/cache --mode rebalance --entry -0.10

# Subsequent runs: reads from cache (~1.6 sec)
python3 scripts/backtest.py --symbol1 000922 --symbol2 000510 \
  --cache-dir data/cache --mode rebalance --entry -0.10

# Force refresh when index composition changes
python3 scripts/backtest.py --symbol1 000922 --symbol2 000510 \
  --cache-dir data/cache --mode rebalance --refresh
```

Cache files: `data/cache/{symbol}.csv` (~650KB each)

### daily_check.py

| Param | Default | Description |
|-------|---------|-------------|
| --symbol1/2 | H00922/000985 | Index codes |
| --label1/2 | Asset 1/2 | Display labels |
| --state-file | /tmp/... | JSON state file for persistence |
| --output | text | text, json, or both |

## Strategy Logic

### Rotation Mode
- DIFF40 <= entry threshold → switch to asset 1 (e.g., dividend)
- DIFF40 >= exit threshold → switch to asset 2 (e.g., broad market)
- Hold position until reverse signal

### Rebalance Mode
- Start 50/50 allocation
- When |DIFF40| >= threshold → rebalance back to 50/50
- Compare vs: never rebalance, quarterly, annual

## Index Codes

See `references/indices.md` for common CSI index codes.

Key pairs:
- H00922 vs 000985: Dividend TR vs All Share (classic EarlETF pair)
- 000922 vs 000510: Dividend vs A500 (ETF rotation)
- For ETF strategies, use price indices (000922, 000510)
- For total return analysis, use TR indices (H00922)

## Setting Up Daily Alerts

To set up daily DIFF40 alerts via heartbeat:

1. Add to HEARTBEAT.md:
```
### DIFF40_DAILY
触发条件：每天北京时间17:00（UTC 09:00），仅交易日
执行内容：
1. 运行 python3 scripts/daily_check.py --symbol1 <code1> --symbol2 <code2> --label1 "..." --label2 "..." --state-file data/diff40_state.json
2. 将输出通过 message 工具发送给用户
3. 如果当天日期与状态文件中 last_date 相同则跳过
```

2. Run once manually to seed the state file
3. Heartbeat will handle the rest