#!/usr/bin/env python3
"""
Enhanced DIFF40 Strategy v2 — Asymmetric (Add-Only) + Graduated Sizing

Key design:
  - NEVER reduce below 100% baseline dividend allocation
  - Graduated add: -6% → +20%, -8% → +40%, -10% → +60%, -15% → +100%
  - Exit extra position when DIFF40 crosses above +2% (not -6% anymore)
  - Volume confirmation: amplify add when dividend vol is LOW relative to market
  
"""

import pandas as pd
import numpy as np
import json
import os
import warnings
warnings.filterwarnings('ignore')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

_font_path = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
if os.path.exists(_font_path):
    plt.rcParams['font.family'] = 'WenQuanYi Micro Hei'

CACHE_DIR = os.path.expanduser('~/.openclaw/workspace/data/cache')

# ============================================================
# 1. Load Data
# ============================================================
def load_index(symbol):
    path = os.path.join(CACHE_DIR, f'{symbol}.csv')
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['日期'])
    df = df.sort_values('date').reset_index(drop=True)
    df = df[['date', '收盘', '成交量', '成交金额']].copy()
    df.columns = ['date', 'close', 'volume', 'amount']
    df = df.groupby('date').agg({'close': 'last', 'volume': 'sum', 'amount': 'sum'}).reset_index()
    return df

d1 = load_index('H00922')  # 中证红利全收益
d2 = load_index('000985')   # 中证全指

df = pd.merge(d1, d2, on='date', suffixes=('_div', '_all'), how='inner').dropna()

# ============================================================
# 2. Compute DIFF40 and Volume
# ============================================================
df['ret40_div'] = df['close_div'].pct_change(40)
df['ret40_all'] = df['close_all'].pct_change(40)
df['diff40'] = df['ret40_div'] - df['ret40_all']
df['ma242'] = df['diff40'].rolling(242, min_periods=120).mean()

# Volume ratio (dividend volume / all-share volume)
df['vol_ratio'] = df['volume_div'] / df['volume_all']
df['vol_ratio_ma60'] = df['vol_ratio'].rolling(60).mean()
df['vol_ratio_std60'] = df['vol_ratio'].rolling(60).std()
df['vol_zscore'] = (df['vol_ratio'] - df['vol_ratio_ma60']) / df['vol_ratio_std60']

# ============================================================
# 3. Position Sizing — Asymmetric Add-Only
# ============================================================
def position_extra(diff40, vol_zscore, in_position=False):
    """
    Compute EXTRA position above baseline (0 = baseline, 1.0 = 2x baseline).
    NEVER returns negative (never underweight).
    
    Graduated curve:
      DIFF40 = 0%     → extra = 0%
      DIFF40 = -3%    → extra = 5%
      DIFF40 = -5%    → extra = 15%
      DIFF40 = -6%    → extra = 25%
      DIFF40 = -8%    → extra = 45%
      DIFF40 = -10%   → extra = 65%
      DIFF40 = -15%   → extra = 100%
    
    Exit: return to 0% extra when DIFF40 > +1% (if in_position)
    """
    if pd.isna(diff40):
        return 0.0
    
    # Exit logic: if in position and diff40 recovered to +1%, exit
    if in_position and diff40 > 0.01:
        return 0.0
    
    # Only add when diff40 is negative
    if diff40 >= 0:
        return 0.0
    
    # Graduated curve: smooth interpolation
    # Use log-sigmoid type smooth curve
    abs_d = abs(diff40)
    
    if abs_d <= 0.03:
        extra = abs_d / 0.03 * 0.05
    elif abs_d <= 0.05:
        extra = 0.05 + (abs_d - 0.03) / 0.02 * 0.10
    elif abs_d <= 0.06:
        extra = 0.15 + (abs_d - 0.05) / 0.01 * 0.10
    elif abs_d <= 0.08:
        extra = 0.25 + (abs_d - 0.06) / 0.02 * 0.20
    elif abs_d <= 0.10:
        extra = 0.45 + (abs_d - 0.08) / 0.02 * 0.20
    elif abs_d <= 0.15:
        extra = 0.65 + (abs_d - 0.10) / 0.05 * 0.35
    else:
        extra = 1.00
    
    # Volume confirmation: amplify when dividend volume is LOW
    if not pd.isna(vol_zscore) and diff40 < -0.02:
        if vol_zscore < -1.0:
            extra = min(extra * 1.3, 1.0)  # strong contrarian signal
        elif vol_zscore < -0.5:
            extra = min(extra * 1.15, 1.0)
        elif vol_zscore > 1.0:
            extra = extra * 0.8  # high vol dampens (not as contrarian)
        elif vol_zscore > 0.5:
            extra = extra * 0.9
    
    return extra

# ============================================================
# 4. Backtest
# ============================================================
def run_backtest(df, start_idx, mode, exit_threshold=0.01):
    """mode: 'graduated' | 'binary' | 'hold'"""
    records = []
    in_position = False
    exit_at = exit_threshold
    
    for i in range(start_idx, len(df)):
        date = df['date'].iloc[i]
        diff40 = df['diff40'].iloc[i]
        vol_z = df['vol_zscore'].iloc[i]
        
        if mode == 'graduated':
            extra = position_extra(diff40, vol_z, in_position)
        elif mode == 'binary':
            if diff40 <= -0.06 and not in_position:
                extra = 0.50
                in_position = True
            elif diff40 >= exit_at and in_position:
                extra = 0.0
                in_position = False
            else:
                extra = 0.50 if in_position else 0.0
        else:  # hold
            extra = 0.0
        
        # Update in_position flag for graduated mode
        if mode == 'graduated':
            in_position = extra > 0.01
        
        effective_weight = 1.0 + extra
        
        div_return = df['close_div'].iloc[i] / df['close_div'].iloc[i-1] - 1
        daily_return = effective_weight * div_return
        
        records.append({
            'date': date,
            'diff40': diff40,
            'extra': extra,
            'weight': effective_weight,
            'daily_return': daily_return,
            'div_return': div_return,
        })
    
    r = pd.DataFrame(records)
    r['cum_return'] = (1 + r['daily_return']).cumprod()
    r['year'] = r['date'].dt.year
    return r

# ============================================================
# 5. Run & Compare
# ============================================================
start_idx = 242
r_grad = run_backtest(df, start_idx, 'graduated')
r_bin6 = run_backtest(df, start_idx, 'binary', exit_threshold=0.02)
r_hold = run_backtest(df, start_idx, 'hold')

def print_stats(r, name):
    final = r['cum_return'].iloc[-1]
    n_days = len(r)
    annual = (final ** (252/n_days) - 1) * 100
    daily_std = r['daily_return'].std()
    annual_std = daily_std * np.sqrt(252) * 100
    sharpe = (annual - 2) / annual_std if annual_std > 0 else 0
    max_dd = (r['cum_return'] / r['cum_return'].cummax() - 1).min() * 100
    avg_weight = r['weight'].mean() * 100
    
    # Add times
    add_count = (r['extra'] > 0.01).astype(int)
    add_starts = (add_count.diff() == 1).sum()
    
    yr = r.groupby('year').apply(lambda g: (1+g['daily_return']).prod() - 1) * 100
    
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"  Annual Return:   {annual:6.2f}%")
    print(f"  Annual Vol:      {annual_std:6.2f}%")
    print(f"  Sharpe:          {sharpe:6.2f}")
    print(f"  Max Drawdown:    {max_dd:6.2f}%")
    print(f"  Avg Weight:      {avg_weight:6.1f}%")
    print(f"  Add Signals:     {add_starts:4d}")
    print(f"  Final Multiple:  {final:6.2f}x")
    print(f"\n  Yearly:")
    for yr_v, ret in yr.items():
        print(f"    {yr_v}: {ret:+.2f}%")
    
    return {'annual': annual, 'sharpe': sharpe, 'max_dd': max_dd, 'final': final,
            'adds': add_starts, 'yearly': yr.to_dict()}

s_grad = print_stats(r_grad, 'GRADUATED ADD-ONLY (smooth curve)')
s_bin6 = print_stats(r_bin6, 'BINARY (±6% enter, +2% exit)')
s_hold = print_stats(r_hold, 'BUY & HOLD (100% Dividend)')

# ============================================================
# 6. Weight Distribution
# ============================================================
print(f"\n{'='*60}")
print(f"  Weight Distribution (Graduated)")
print(f"{'='*60}")
bins = [(-100, -10, '< -10%'), (-10, -5, '-10~-5%'), (-5, -3, '-5~-3%'),
        (-3, 0, '-3~0%'), (0, 5, '0~+5%'), (5, 100, '> +5%')]
for lo, hi, label in bins:
    mask = (r_grad['diff40'] * 100 >= lo) & (r_grad['diff40'] * 100 < hi)
    if mask.sum() > 0:
        avg_w = r_grad.loc[mask, 'weight'].mean() * 100
        n = mask.sum()
        pct = n / len(r_grad) * 100
        print(f"  {label:12s}: avg weight {avg_w:5.1f}%  ({n:4d} days, {pct:5.1f}%)")

# ============================================================
# 7. Volume Signal Analysis
# ============================================================
print(f"\n{'='*60}")
print(f"  Volume: Mean Reversion After DIFF40 < -5%")
print(f"{'='*60}")
for horizon in [10, 20, 40]:
    mask_neg = df['diff40'] < -0.05
    mask_low_vol = mask_neg & (df['vol_zscore'] < -0.5)
    mask_norm_vol = mask_neg & (df['vol_zscore'].abs() < 0.5) & df['vol_zscore'].notna()
    
    fwd = df['diff40'].shift(-horizon) - df['diff40']
    
    for label, m in [('Low Vol', mask_low_vol), ('Normal Vol', mask_norm_vol)]:
        f = fwd[m].dropna()
        if len(f) > 0:
            mean = f.mean() * 100
            win = (f > 0).mean() * 100
            print(f"  {horizon:2d}d | {label:10s}: mean rev {mean:+.2f}pp | win {win:.0f}% | n={len(f)}")

# ============================================================
# 8. Generate Chart
# ============================================================
chart_path = os.path.expanduser('~/.openclaw/workspace/output/enhanced_strategy.png')

fig, axes = plt.subplots(3, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2, 1, 1]})

# Recent 2 years for readability
recent = df[df['date'] >= '2024-01-01'].copy()
recent_ret = r_grad[r_grad['date'] >= '2024-01-01'].copy()

# Panel 1: Cumulative returns comparison
ax1 = axes[0]
ax1.plot(recent_ret['date'], r_hold[r_hold['date'] >= '2024-01-01']['cum_return'].values / r_hold[r_hold['date'] >= '2024-01-01']['cum_return'].iloc[0] - 1,
         color='gray', linewidth=1.5, label='Buy & Hold 红利', alpha=0.7)
ax1.plot(recent_ret['date'], recent_ret['cum_return'].values / recent_ret['cum_return'].iloc[0] - 1,
         color='#d62728', linewidth=2, label='Graduated Add-Only', alpha=0.9)
ax1.fill_between(recent_ret['date'], 0, 
                 recent_ret['cum_return'].values / recent_ret['cum_return'].iloc[0] - 1,
                 where=(recent_ret['cum_return'].values / recent_ret['cum_return'].iloc[0] - 1) >= 
                       (r_hold[r_hold['date'] >= '2024-01-01']['cum_return'].values / r_hold[r_hold['date'] >= '2024-01-01']['cum_return'].iloc[0] - 1),
                 color='#d62728', alpha=0.15)
ax1.set_ylabel('Cumulative Return', fontsize=11)
ax1.set_title('Enhanced DIFF40 Strategy — Graduated Add-Only vs Buy & Hold', fontsize=13, fontweight='bold')
ax1.legend(loc='upper left', fontsize=9)
ax1.grid(True, alpha=0.2)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax1.axhline(y=0, color='black', linewidth=0.5)

# Panel 2: DIFF40 + position overlay
ax2 = axes[1]
ax2.plot(recent['date'], recent['diff40'] * 100, color='#1f77b4', linewidth=1.2, label='DIFF40')
ax2.plot(recent['date'], recent['ma242'] * 100, color='orange', linewidth=1, linestyle='--', label='MA242', alpha=0.7)
ax2.fill_between(recent['date'], 0, recent['diff40'] * 100,
                 where=recent['diff40'] < 0, color='green', alpha=0.1)
ax2.fill_between(recent['date'], 0, recent['diff40'] * 100,
                 where=recent['diff40'] > 0, color='red', alpha=0.1)
ax2.axhline(y=-6, color='green', linewidth=0.8, linestyle=':', alpha=0.6)
ax2.axhline(y=-3, color='green', linewidth=0.5, linestyle=':', alpha=0.3)
ax2.axhline(y=2, color='red', linewidth=0.8, linestyle=':', alpha=0.6, label='Exit +2%')
ax2.axhline(y=0, color='black', linewidth=0.5)
ax2.set_ylabel('DIFF40 (%)', fontsize=11)
ax2.legend(loc='upper left', fontsize=8, ncol=4)
ax2.grid(True, alpha=0.2)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

# Panel 3: Position weight
ax3 = axes[2]
ax3.fill_between(recent_ret['date'], 100, recent_ret['weight'] * 100, 
                 color='green', alpha=0.3, step='post')
ax3.plot(recent_ret['date'], recent_ret['weight'] * 100, color='darkgreen', linewidth=1.5, drawstyle='steps-post')
ax3.axhline(y=100, color='black', linewidth=0.5)
ax3.set_ylabel('Position Weight (%)', fontsize=11)
ax3.set_xlabel('Date', fontsize=11)
ax3.set_ylim(95, max(recent_ret['weight'].max() * 100 + 10, 165))
ax3.grid(True, alpha=0.2)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

plt.tight_layout()
plt.savefig(chart_path, dpi=150, bbox_inches='tight')
plt.close()
print(f"\nChart saved: {chart_path}")

# ============================================================
# 9. Current Signal
# ============================================================
latest = df.iloc[-1]
current_diff40 = latest['diff40'] * 100
current_vol_z = latest['vol_zscore']
current_extra = position_extra(latest['diff40'], latest['vol_zscore'], in_position=False)
current_weight = 100 * (1 + current_extra)

# Build weight table
print(f"\n{'='*60}")
print(f"  POSITION SIZING TABLE")
print(f"{'='*60}")
for d in [-0.15, -0.10, -0.08, -0.06, -0.05, -0.04, -0.03, -0.02, 0.0]:
    e = position_extra(d, 0, False)
    print(f"  DIFF40 {d*100:+.0f}%  →  Extra {e*100:+5.0f}%  →  Weight {(1+e)*100:5.0f}%")

print(f"\n{'='*60}")
print(f"  CURRENT SIGNAL ({latest['date'].date()})")
print(f"{'='*60}")
print(f"  DIFF40:          {current_diff40:+.2f}%")
print(f"  MA242:           {latest['ma242']*100:+.2f}%")
print(f"  Volume Z-Score:  {current_vol_z:+.2f}")
print(f"  Extra Position:  {current_extra*100:+.1f}%")
print(f"  Dividend Weight: {current_weight:.0f}%")

signal = 'HOLD'
if current_extra >= 0.5:
    signal = 'STRONG BUY — 大幅加仓'
elif current_extra >= 0.25:
    signal = 'BUY — 适度加仓'
elif current_extra >= 0.15:
    signal = 'LIGHT BUY — 小幅加仓'
elif current_extra > 0.01:
    signal = 'LIGHT BUY — 试探加仓'
print(f"  Signal:          {signal}")