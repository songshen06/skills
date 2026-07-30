#!/usr/bin/env python3
"""
Daily DIFF40 Check & Report

Usage:
  python3 daily_check.py --symbol1 H00922 --symbol2 000985 \
    --label1 "CSI Dividend TR" --label2 "CSI All Share" \
    --state-file /path/to/state.json --output text
"""

import akshare as ak
import pandas as pd
import numpy as np
import json
import os
import argparse
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Chinese font support
_font_path = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
if os.path.exists(_font_path):
    from matplotlib.font_manager import FontProperties
    _cn_font = FontProperties(fname=_font_path)
    plt.rcParams['font.family'] = 'WenQuanYi Micro Hei'
else:
    _cn_font = None

parser = argparse.ArgumentParser(description='Daily DIFF40 Check')
parser.add_argument('--symbol1', default='H00922')
parser.add_argument('--symbol2', default='000985')
parser.add_argument('--label1', default='Asset 1')
parser.add_argument('--label2', default='Asset 2')
parser.add_argument('--state-file', default='/tmp/diff40_state.json')
parser.add_argument('--output', default='text', choices=['text', 'json', 'both'])
parser.add_argument('--chart', default=None, help='Output path for trend chart (optional)')
parser.add_argument('--cache-dir', default=None, help='Cache directory for index data')
parser.add_argument('--refresh', action='store_true', help='Force re-download')
args = parser.parse_args()

S1, S2 = args.symbol1, args.symbol2
L1, L2 = args.label1, args.label2

# ============================================================
# 1. Fetch Data (with optional caching)
# ============================================================
def fetch_or_cache(symbol, label, cache_dir, refresh):
    if cache_dir:
        cache_file = os.path.join(cache_dir, f'{symbol}.csv')
        if os.path.exists(cache_file) and not refresh:
            df = pd.read_csv(cache_file, parse_dates=['日期'])
            # Only the latest rows matter; we fetch from 2020, filter to >= 2020
            df = df[df['日期'] >= '2020-01-01'].copy()
            print(f"  {label} ({symbol}) from cache: {len(df)} rows")
            return df

    print(f"  Fetching {label} ({symbol})...")
    df = ak.stock_zh_index_hist_csindex(symbol=symbol, start_date='20200101', end_date='20501231')
    
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        # Merge with existing cache to keep full history
        if os.path.exists(cache_file):
            old = pd.read_csv(cache_file)
            old['日期'] = pd.to_datetime(old['日期']).dt.strftime('%Y-%m-%d')
            df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
            df = pd.concat([old, df]).drop_duplicates(subset='日期', keep='last')
        df.to_csv(cache_file, index=False)
        print(f"  Cached ({len(df)} rows)")
    
    return df

df1 = fetch_or_cache(S1, L1, args.cache_dir, args.refresh)
df2 = fetch_or_cache(S2, L2, args.cache_dir, args.refresh)

df1 = df1[['日期', '收盘']].copy(); df1.columns = ['date', 'close1']
df2 = df2[['日期', '收盘']].copy(); df2.columns = ['date', 'close2']
df1['date'] = pd.to_datetime(df1['date'])
df2['date'] = pd.to_datetime(df2['date'])

df = pd.merge(df1, df2, on='date', how='inner').sort_values('date').reset_index(drop=True)
df = df.drop_duplicates(subset='date', keep='last').reset_index(drop=True)

# ============================================================
# 2. Calculate DIFF40 and DIFF20
# ============================================================
df['ret40_1'] = df['close1'].pct_change(40)
df['ret40_2'] = df['close2'].pct_change(40)
df['diff40'] = df['ret40_1'] - df['ret40_2']
df['ma242'] = df['diff40'].rolling(242, min_periods=120).mean()

# DIFF20 for higher-frequency trading signals
df['ret20_1'] = df['close1'].pct_change(20)
df['ret20_2'] = df['close2'].pct_change(20)
df['diff20'] = df['ret20_1'] - df['ret20_2']
df['ma20_242'] = df['diff20'].rolling(242, min_periods=120).mean()

valid = df.dropna(subset=['diff40', 'ma242'])
L = valid.iloc[-1]
latest_date = L['date'].strftime('%Y-%m-%d')
diff40_val = L['diff40']
ma242_val = L['ma242']
diff20_val = L['diff20']
ma20_242_val = L['ma20_242']

# ============================================================
# 3. State Management
# ============================================================
os.makedirs(os.path.dirname(args.state_file) or '.', exist_ok=True)
state = {}
if os.path.exists(args.state_file):
    with open(args.state_file) as f:
        state = json.load(f)

prev_date = state.get('last_date', 'N/A')
prev_diff40 = state.get('diff40', None)
direction = ''
if prev_diff40 is not None and prev_date != latest_date:
    if diff40_val > prev_diff40: direction = 'rising'
    elif diff40_val < prev_diff40: direction = 'falling'
    else: direction = 'flat'

state['last_date'] = latest_date
state['diff40'] = round(diff40_val, 6)
state['ma242'] = round(ma242_val, 6)
state['diff20'] = round(diff20_val, 6)
state['last_update_utc'] = datetime.utcnow().isoformat()
state['close1'] = round(float(L['close1']), 2)
state['close2'] = round(float(L['close2']), 2)
state['symbol1'] = S1
state['symbol2'] = S2

# Track DIFF20 position state
in_pos = state.get('in_diiff20_position', False)
if diff20_val <= -0.03:
    state['in_diiff20_position'] = True
elif diff20_val >= 0.03:
    state['in_diiff20_position'] = False
# else: keep previous state

if 'history' not in state: state['history'] = []
entry = {'date': latest_date, 'diff40': round(diff40_val, 6),
         'ma242': round(ma242_val, 6), 'close1': state['close1'], 'close2': state['close2']}
state['history'].append(entry)
seen = set(); uniq = []
for h in reversed(state['history']):
    if h['date'] not in seen: uniq.append(h); seen.add(h['date'])
state['history'] = list(reversed(uniq))[-60:]

with open(args.state_file, 'w') as f:
    json.dump(state, f, indent=2, ensure_ascii=False)

# ============================================================
# 4. Signal Zones (DIFF40 for long-term context, DIFF20 for trading)
# ============================================================
d40 = diff40_val * 100
d20 = diff20_val * 100

# DIFF20 strategy: -3% enter, +3% exit, 70% extra position
if d20 <= -3:
    trade_signal = '🟢 BUY'
    trade_extra = 70
    trade_action = f'加仓至 {170}%'
elif d20 >= 3:
    trade_signal = '🔴 EXIT'
    trade_extra = 0
    trade_action = '回到基线 100%'
else:
    # Check if currently in position (based on daily state tracking)
    in_position = state.get('in_diiff20_position', False)
    if in_position:
        trade_signal = '🟡 HOLD (in position)'
        trade_extra = 70
        trade_action = f'维持 {170}%'
    else:
        trade_signal = '⚪ WAIT'
        trade_extra = 0
        trade_action = '保持基线 100%'

# DIFF40 for context / regime awareness
if d40 <= -15:    zone40 = '🟢 DEEP VALUE'
elif d40 <= -10:  zone40 = '🟢 VALUE'
elif d40 <= -5:   zone40 = '🟡 NEAR VALUE'
elif d40 <= 0:    zone40 = '⚪ NEUTRAL'
elif d40 <= 10:   zone40 = '⚪ NEUTRAL'
elif d40 <= 15:   zone40 = '🟠 OVERVALUED'
else:             zone40 = '🔴 EXTREME'

# ============================================================
# 5. Output
# ============================================================
if args.output in ('text', 'both'):
    print(f"""
DIFF40 Daily Report
====================
Date:     {latest_date}
{L1}: {state['close1']:.2f}
{L2}: {state['close2']:.2f}

DIFF40 (long-term):  {d40:+.2f}% ({direction})  {zone40}
MA242:               {ma242_val*100:+.2f}%

DIFF20 (trading):    {d20:+.2f}%  →  {trade_signal}  {trade_action}
Strategy:            DIFF20 -3% enter / +3% exit / 70% extra

State:    {args.state_file}
""")

if args.output in ('json', 'both'):
    report = {
        'date': latest_date,
        'symbols': [S1, S2],
        'labels': [L1, L2],
        'diff40': round(diff40_val, 6),
        'diff40_pct': round(d40, 2),
        'diff20_pct': round(d20, 2),
        'ma242': round(ma242_val, 6),
        'ma242_pct': round(ma242_val*100, 2),
        'zone40': zone40,
        'trade_signal': trade_signal,
        'trade_extra': trade_extra,
        'trade_action': trade_action,
        'in_position': state.get('in_diiff20_position', False),
        'direction': direction,
        'close1': state['close1'],
        'close2': state['close2'],
        'updated': state['last_update_utc']
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

# ============================================================
# 6. Chart (optional)
# ============================================================
if args.chart:
    # Use last ~500 trading days
    plot_df = valid.tail(500).copy()
    
    fig, axes = plt.subplots(3, 1, figsize=(16, 10), gridspec_kw={'height_ratios': [1.5, 1.5, 1]})
    fig.suptitle(f'{L1} vs {L2} — DIFF20 Trading + DIFF40 Context', fontsize=14, fontweight='bold', y=0.97)

    # Panel 1: DIFF20 (trading signal)
    ax1 = axes[0]
    ax1.plot(plot_df['date'], plot_df['diff20']*100, color='#2ca02c', linewidth=1.5, label='DIFF20 (Trading)')
    ax1.axhline(y=-3, color='green', ls='--', lw=1, alpha=0.6, label='Enter -3%')
    ax1.axhline(y=3, color='red', ls='--', lw=1, alpha=0.6, label='Exit +3%')
    ax1.axhline(y=0, color='black', ls='-', lw=0.5, alpha=0.2)
    ax1.fill_between(plot_df['date'], 0, plot_df['diff20']*100,
                     where=plot_df['diff20'] < -0.03, color='green', alpha=0.1, label='Buy Zone')
    ax1.fill_between(plot_df['date'], 0, plot_df['diff20']*100,
                     where=plot_df['diff20'] > 0.03, color='red', alpha=0.1, label='Sell Zone')
    ax1.scatter(plot_df['date'].iloc[-1], d20, color='#2ca02c', s=80, zorder=5, edgecolors='white', linewidth=1.5)
    ax1.annotate(f'  {d20:+.1f}%', (plot_df['date'].iloc[-1], d20),
                 fontsize=10, fontweight='bold', color='#2ca02c', va='center')
    ax1.set_ylabel('DIFF20 (%)', fontsize=11)
    ax1.legend(loc='upper left', ncol=3, fontsize=8)
    ax1.grid(True, alpha=0.2)

    # Panel 2: DIFF40 + MA242 (context)
    ax2 = axes[1]
    ax2.plot(plot_df['date'], plot_df['diff40']*100, color='#d62728', linewidth=1.2, label='DIFF40')
    ax2.plot(plot_df['date'], plot_df['ma242']*100, color='#1f77b4', linewidth=1.5, label='MA242')
    ax2.axhline(y=10, color='orange', ls='--', lw=0.8, alpha=0.4, label='±10%')
    ax2.axhline(y=0, color='black', ls='-', lw=0.5, alpha=0.2)
    ax2.axhline(y=-10, color='green', ls='--', lw=0.8, alpha=0.4)
    ax2.scatter(plot_df['date'].iloc[-1], d40, color='#d62728', s=80, zorder=5, edgecolors='white', linewidth=1.5)
    ax2.annotate(f'  {d40:+.1f}%', (plot_df['date'].iloc[-1], d40),
                 fontsize=10, fontweight='bold', color='#d62728', va='center')
    ax2.set_ylabel('DIFF40 (%)', fontsize=11)
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.2)

    # Panel 3: Ratio
    plot_df['ratio'] = plot_df['close1'] / plot_df['close2']
    ax3 = axes[2]
    ax3.plot(plot_df['date'], plot_df['ratio'], color='black', linewidth=1.3)
    ax3.fill_between(plot_df['date'], plot_df['ratio'].min(), plot_df['ratio'], alpha=0.1, color='black')
    ax3.set_ylabel(f'{L1} / {L2} Ratio', fontsize=11)
    ax3.grid(True, alpha=0.2)

    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    fig.autofmt_xdate()

    # Signal annotation (chart-safe text labels, emoji skipped to avoid font warnings)
    _chart_signal_map = {'🟢 BUY': 'BUY', '🔴 EXIT': 'EXIT', '🟡 HOLD (in position)': 'HOLD', '⚪ WAIT': 'WAIT'}
    _chart_signal = _chart_signal_map.get(trade_signal, 'WAIT')
    colors = {'🟢 BUY': '#2ca02c', '🔴 EXIT': '#d62728', '🟡 HOLD (in position)': '#bcbd22', '⚪ WAIT': '#7f7f7f'}
    clr = colors.get(trade_signal, '#7f7f7f')
    
    ax1.text(0.99, 0.95, f'DIFF20 Signal: [{_chart_signal}] {trade_action}', 
             transform=ax1.transAxes, fontsize=12, fontweight='bold', color=clr, ha='right', va='top',
             bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.8, edgecolor=clr))

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(args.chart, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Chart saved: {args.chart}")