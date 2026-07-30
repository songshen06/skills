#!/usr/bin/env python3
"""
DIFF40 Backtest — Rotation & Rebalancing Strategies

Usage:
  python3 backtest.py \
    --symbol1 H00922 --symbol2 000985 \
    --label1 "CSI Dividend TR" --label2 "CSI All Share" \
    --mode rotation \
    --entry -0.10 --exit 0.10

Modes:
  rotation  — Switch allocation based on DIFF40 thresholds
  rebalance — Start 50/50, rebalance to 50/50 when |DIFF40| >= threshold
"""

import akshare as ak
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import argparse
import os
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CLI
# ============================================================
parser = argparse.ArgumentParser(description='DIFF40 Strategy Backtest')
parser.add_argument('--symbol1', default='000922', help='Index code for asset 1')
parser.add_argument('--symbol2', default='000510', help='Index code for asset 2')
parser.add_argument('--label1', default='Asset 1', help='Label for asset 1')
parser.add_argument('--label2', default='Asset 2', help='Label for asset 2')
parser.add_argument('--mode', default='rotation', choices=['rotation', 'rebalance', 'both'],
                    help='Strategy mode')
parser.add_argument('--entry', type=float, default=-0.10,
                    help='Entry/buy threshold for rotation, absolute threshold for rebalance')
parser.add_argument('--exit', type=float, default=0.10,
                    help='Exit/sell threshold for rotation')
parser.add_argument('--start', default='20050101', help='Start date YYYYMMDD')
parser.add_argument('--end', default='20501231', help='End date YYYYMMDD')
parser.add_argument('--output', default='/tmp/diff40_backtest.png', help='Chart output path')
parser.add_argument('--no-chart', action='store_true', help='Skip chart generation')
parser.add_argument('--cache-dir', default=None, help='Cache directory for downloaded data (e.g. data/cache)')
parser.add_argument('--refresh', action='store_true', help='Force re-download, ignore cache')
args = parser.parse_args()

S1, S2 = args.symbol1, args.symbol2
L1, L2 = args.label1, args.label2

# ============================================================
# 1. Fetch Data (with optional caching)
# ============================================================
def fetch_index(symbol, label, cache_dir, refresh):
    """Fetch index data, using cache if available."""
    if cache_dir:
        cache_file = os.path.join(cache_dir, f'{symbol}.csv')
        if os.path.exists(cache_file) and not refresh:
            df = pd.read_csv(cache_file, parse_dates=['日期'])
            print(f"Loaded {label} ({symbol}) from cache: {len(df)} rows")
            return df
    
    print(f"Fetching {label} ({symbol})...")
    df = ak.stock_zh_index_hist_csindex(symbol=symbol, start_date=args.start, end_date=args.end)
    print(f"  {len(df)} rows")
    
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        df.to_csv(cache_file, index=False)
        print(f"  Cached to {cache_file}")
    
    return df

if args.cache_dir:
    print(f"Cache dir: {args.cache_dir}")

df1 = fetch_index(S1, L1, args.cache_dir, args.refresh)
df2 = fetch_index(S2, L2, args.cache_dir, args.refresh)

df1 = df1[['日期', '收盘']].copy(); df1.columns = ['date', 'close1']
df2 = df2[['日期', '收盘']].copy(); df2.columns = ['date', 'close2']
df1['date'] = pd.to_datetime(df1['date'])
df2['date'] = pd.to_datetime(df2['date'])

df = pd.merge(df1, df2, on='date', how='inner').sort_values('date').reset_index(drop=True)
df = df.drop_duplicates(subset='date', keep='last').reset_index(drop=True)
print(f"Merged: {len(df)} rows, {df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()}")

# ============================================================
# 2. Calculate Indicators
# ============================================================
df['ret40_1'] = df['close1'].pct_change(40)
df['ret40_2'] = df['close2'].pct_change(40)
df['diff40'] = df['ret40_1'] - df['ret40_2']
df['ma242'] = df['diff40'].rolling(242, min_periods=120).mean()
df['ret1'] = df['close1'].pct_change()
df['ret2'] = df['close2'].pct_change()
df = df.dropna(subset=['diff40', 'ma242']).reset_index(drop=True)
print(f"Valid: {len(df)} rows, {df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()}")

# ============================================================
# 3. Stats Function
# ============================================================
def calc_stats(returns, name, rf=0.03):
    rets = returns.dropna()
    n = len(rets)
    total_r = (1 + rets).prod() - 1
    yrs = n / 242
    ann_r = (1 + total_r) ** (1 / yrs) - 1
    ann_v = rets.std() * np.sqrt(242)
    sharpe = (ann_r - rf) / ann_v if ann_v > 0 else 0
    cum = (1 + rets).cumprod()
    max_dd = (cum / cum.cummax() - 1).min()
    wr = (rets > 0).sum() / n
    print(f"  {name:30s} | Total: {total_r*100:>8.2f}% | Ann: {ann_r*100:>6.2f}% | Sharpe: {sharpe:>5.2f} | MaxDD: {max_dd*100:>6.2f}%")
    return dict(name=name, total_return=total_r, ann_return=ann_r, sharpe=sharpe, max_dd=max_dd, win_rate=wr, years=yrs)

# ============================================================
# 4a. Rotation Strategy
# ============================================================
if args.mode in ('rotation', 'both'):
    print(f"\n{'='*70}")
    print(f"  ROTATION Strategy: {L1} vs {L2}")
    print(f"  Entry: {args.entry:.0%}  Exit: {args.exit:.0%}")
    print(f"{'='*70}")

    df['signal'] = 0
    df.loc[df['diff40'] <= args.entry, 'signal'] = 1
    df.loc[df['diff40'] >= args.exit, 'signal'] = -1

    df['position'] = 0
    pos = 0
    for i in range(len(df)):
        if df.loc[i, 'signal'] == 1: pos = 1
        elif df.loc[i, 'signal'] == -1: pos = 0
        df.loc[i, 'position'] = pos

    df['ret_rotation'] = df['position'] * df['ret1'] + (1 - df['position']) * df['ret2']
    df['cum_rotation'] = (1 + df['ret_rotation']).cumprod()

    s1  = calc_stats(df['ret1'], f'100% {L1}')
    s2  = calc_stats(df['ret2'], f'100% {L2}')
    s_rot = calc_stats(df['ret_rotation'], f'DIFF40 Rotation')
    
    print(f"\n  Rotation vs {L2}: {(s_rot['total_return']-s2['total_return'])*100:+.2f}% excess")
    print(f"  Rotation vs {L1}: {(s_rot['total_return']-s1['total_return'])*100:+.2f}% excess")
    print(f"  Days in {L1}: {(df['position']==1).sum()}/{len(df)} ({(df['position']==1).sum()/len(df)*100:.1f}%)")
    print(f"  Days in {L2}: {(df['position']==0).sum()}/{len(df)} ({(df['position']==0).sum()/len(df)*100:.1f}%)")
    
    # Annual breakdown
    print(f"\n  {'Year':<6} {L1[:8]:>9} {L2[:8]:>9} {'Rotation':>9} {'Excess':>9} {'Pos%':>6}")
    print(f"  {'-'*55}")
    df['year'] = df['date'].dt.year
    for yr, g in df.groupby('year'):
        if len(g) < 50: continue
        r1 = (1+g['ret1'].dropna()).prod()-1
        r2 = (1+g['ret2'].dropna()).prod()-1
        rr = (1+g['ret_rotation'].dropna()).prod()-1
        ex = rr - r2
        pp = g['position'].mean()*100
        print(f"  {int(yr):<6} {r1*100:>8.2f}% {r2*100:>8.2f}% {rr*100:>8.2f}% {ex*100:>8.2f}% {pp:>5.1f}%")

# ============================================================
# 4b. Rebalancing Strategy
# ============================================================
if args.mode in ('rebalance', 'both'):
    print(f"\n{'='*70}")
    print(f"  REBALANCE Strategy: 50/50 {L1} + {L2}")
    print(f"  Trigger: |DIFF40| >= {args.entry:.0%}")
    print(f"{'='*70}")
    
    REBAL_THRESHOLD = abs(args.entry)

    # Never rebalance
    nav_noreb = [1.0]
    w_noreb = [0.5]
    for i in range(1, len(df)):
        r1, r2v = df.loc[i, 'ret1'], df.loc[i, 'ret2']
        w = w_noreb[-1]
        w_new = w*(1+r1)/(w*(1+r1)+(1-w)*(1+r2v))
        nav = nav_noreb[-1]*(w*(1+r1)+(1-w)*(1+r2v))
        nav_noreb.append(nav); w_noreb.append(w_new)

    # DIFF40 rebalance
    nav_diff40 = [1.0]
    w_diff40 = [0.5]
    rebal_dates = []
    for i in range(1, len(df)):
        r1, r2v = df.loc[i, 'ret1'], df.loc[i, 'ret2']
        w = w_diff40[-1]
        if abs(df.loc[i, 'diff40']) >= REBAL_THRESHOLD:
            w = 0.5
            rebal_dates.append(df.loc[i, 'date'])
        w_new = w*(1+r1)/(w*(1+r1)+(1-w)*(1+r2v))
        nav = nav_diff40[-1]*(w*(1+r1)+(1-w)*(1+r2v))
        nav_diff40.append(nav); w_diff40.append(w_new)

    # Quarterly rebalance
    nav_q = [1.0]
    w_q = [0.5]
    for i in range(1, len(df)):
        r1, r2v = df.loc[i, 'ret1'], df.loc[i, 'ret2']
        w = w_q[-1]
        d = df.loc[i, 'date']
        if d.month in [3, 6, 9, 12]:
            next_idx = i + 1
            if next_idx < len(df) and df.loc[next_idx, 'date'].month != d.month:
                w = 0.5
        w_new = w*(1+r1)/(w*(1+r1)+(1-w)*(1+r2v))
        nav = nav_q[-1]*(w*(1+r1)+(1-w)*(1+r2v))
        nav_q.append(nav); w_q.append(w_new)

    # Annual rebalance
    nav_y = [1.0]
    for i in range(1, len(df)):
        r1, r2v = df.loc[i, 'ret1'], df.loc[i, 'ret2']
        w = (nav_y[-1]*0.5*(1+r1))/nav_y[-1] if i==1 else w_y[-1]*(1+r1)/(w_y[-1]*(1+r1)+(1-w_y[-1])*(1+r2v))
        if i == 1: w = 0.5
        else: w = w_y[-1]*(1+r1)/(w_y[-1]*(1+r1)+(1-w_y[-1])*(1+r2v))
        
        d = df.loc[i, 'date']
        if d.month == 12:
            next_idx = i+1
            if next_idx < len(df) and df.loc[next_idx, 'date'].month != 12:
                w = 0.5
        w_new = w*(1+r1)/(w*(1+r1)+(1-w)*(1+r2v))
        if i == 1:
            nav = nav_y[-1]*(0.5*(1+r1)+0.5*(1+r2v))
        else:
            nav = nav_y[-1]* (w_y[-1]*(1+r1)+(1-w_y[-1])*(1+r2v))
        nav_y.append(nav)
        if i == 1:
            w_y = [0.5, w_new]
        else:
            w_y.append(w_new)

    # Fix annual rebalance simulation
    nav_y = [1.0]
    w_y_list = [0.5]
    for i in range(1, len(df)):
        r1, r2v = df.loc[i, 'ret1'], df.loc[i, 'ret2']
        w = w_y_list[-1]
        d = df.loc[i, 'date']
        if d.month == 12:
            next_idx = i+1
            if next_idx < len(df) and df.loc[next_idx, 'date'].month != 12:
                w = 0.5
        w_new = w*(1+r1)/(w*(1+r1)+(1-w)*(1+r2v))
        nav = nav_y[-1]*(w*(1+r1)+(1-w)*(1+r2v))
        nav_y.append(nav); w_y_list.append(w_new)

    df['nav_noreb'] = nav_noreb
    df['ret_noreb'] = pd.Series(nav_noreb).pct_change()
    df['ret_diff40'] = pd.Series(nav_diff40).pct_change()
    df['ret_q'] = pd.Series(nav_q).pct_change()
    df['ret_y'] = pd.Series(nav_y).pct_change()

    ns = calc_stats(df['ret_noreb'], 'Never Rebalance')
    ds = calc_stats(df['ret_diff40'], f'DIFF40 Rebalance (+-{REBAL_THRESHOLD:.0%})')
    qs = calc_stats(df['ret_q'], 'Quarterly Rebalance')
    ys = calc_stats(df['ret_y'], 'Annual Rebalance')

    bonus_d = ds['total_return'] - ns['total_return']
    bonus_q = qs['total_return'] - ns['total_return']
    bonus_y = ys['total_return'] - ns['total_return']
    print(f"\n  Rebalancing Bonus (vs Never):")
    print(f"    DIFF40:    {'+' if bonus_d>0 else ''}{bonus_d*100:.2f}%  ({len(rebal_dates)} trades)")
    print(f"    Quarterly: {'+' if bonus_q>0 else ''}{bonus_q*100:.2f}%")
    print(f"    Annual:    {'+' if bonus_y>0 else ''}{bonus_y*100:.2f}%")

    print(f"\n  Weight Drift (Never Rebalance):")
    w_arr = np.array(w_noreb)
    print(f"    {L1}: min={w_arr.min()*100:.1f}%  max={w_arr.max()*100:.1f}%  mean={w_arr.mean()*100:.1f}%  latest={w_arr[-1]*100:.1f}%")

# ============================================================
# 5. Latest Signal
# ============================================================
L = df.iloc[-1]
print(f"\n{'='*70}")
print(f"  Latest: {L['date'].strftime('%Y-%m-%d')}")
print(f"  DIFF40 = {L['diff40']*100:+.2f}%  |  MA242 = {L['ma242']*100:+.2f}%")
print(f"{'='*70}")

# ============================================================
# 6. Charts
# ============================================================
if not args.no_chart:
    print(f"\nGenerating chart...")
    fig, axes = plt.subplots(2, 1, figsize=(18, 10), gridspec_kw={'height_ratios': [2, 1]})
    title_parts = [f'{L1} vs {L2}']

    if args.mode in ('rotation', 'both'):
        title_parts.append('Rotation')
        ax1 = axes[0]
        ax1.plot(df['date'], (1+df['ret1']).cumprod(), label=f'{L1}', color='#d62728', lw=1.2)
        ax1.plot(df['date'], (1+df['ret2']).cumprod(), label=f'{L2}', color='#7f7f7f', lw=1.2)
        ax1.plot(df['date'], df['cum_rotation'], label=f'DIFF40 Rotation', color='#1f77b4', lw=1.8)
        ax1.fill_between(df['date'], 0, 1, where=(df['position']==1),
                          transform=ax1.get_xaxis_transform(), color='#d62728', alpha=0.06)
        ax1.legend(loc='upper left', fontsize=9); ax1.grid(True, alpha=0.25)
        ax1.set_title(f'NAV — Rotation Strategy (shaded = holding {L1})', fontsize=12, fontweight='bold')
    elif args.mode == 'rebalance':
        title_parts.append('Rebalance')
        ax1 = axes[0]
        ax1.plot(df['date'], nav_noreb, label='Never Rebalance', color='#7f7f7f', lw=1, alpha=0.6)
        ax1.plot(df['date'], nav_y, label='Annual', color='#ff7f0e', lw=1.2, alpha=0.7)
        ax1.plot(df['date'], nav_q, label='Quarterly', color='#2ca02c', lw=1.2, alpha=0.7)
        ax1.plot(df['date'], nav_diff40, label=f'DIFF40 (+-{REBAL_THRESHOLD:.0%})', color='#1f77b4', lw=1.8)
        for d in rebal_dates:
            ax1.axvline(x=d, color='#d62728', alpha=0.1, lw=0.5)
        ax1.legend(loc='upper left', fontsize=9); ax1.grid(True, alpha=0.25)
        ax1.set_title(f'NAV — Rebalancing Strategies', fontsize=12, fontweight='bold')
    ax1.set_ylabel('NAV')
    ax1.xaxis.set_major_locator(mdates.YearLocator(2))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    ax2 = axes[1]
    ax2.plot(df['date'], df['diff40']*100, label='DIFF40', color='#d62728', lw=1)
    ax2.plot(df['date'], df['ma242']*100, label='MA242', color='#1f77b4', lw=1.2)
    ax2.axhline(y=args.exit*100, color='orange', ls='--', lw=0.8, alpha=0.5)
    ax2.axhline(y=0, color='black', ls='-', lw=0.5, alpha=0.2)
    ax2.axhline(y=args.entry*100, color='green', ls='--', lw=0.8, alpha=0.5)
    ax2.set_title('DIFF40 Signal', fontsize=12, fontweight='bold')
    ax2.set_ylabel('%'); ax2.legend(loc='upper left', fontsize=9); ax2.grid(True, alpha=0.25)
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    fig.suptitle(' — '.join(title_parts) + ' Backtest', fontsize=15, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(args.output, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Chart saved: {args.output}")

print(f"\nDone!")