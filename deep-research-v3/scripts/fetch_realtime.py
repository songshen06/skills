#!/usr/bin/env python3
"""
fetch_realtime.py - 批量查询A股/ETF实时行情
用法: python3 fetch_realtime.py 300274 159566 600089
输出: 格式化行情快照表格
"""
import sys
import urllib.request
import json
import re
import statistics
from datetime import datetime, timedelta

def secid(code):
    """判断市场代码：沪=1.xxxx，深=0.xxxx"""
    code = code.strip()
    if code.startswith(('6', '9', '5')):
        return f"1.{code}"
    return f"0.{code}"

def fetch_current(secid_str, name="Unknown"):
    """获取实时快照"""
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid_str}&fields=f43,f44,f45,f46,f47,f48,f57,f58,f60,f170"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read().decode('utf-8'))
            data = d.get("data", {})
            if not data:
                return None
            return {
                "name": data.get("f58", name),
                "price": data.get("f43", 0) / 100 if data.get("f43") else 0,
                "change": data.get("f44", 0) / 100 if data.get("f44") else 0,
                "pct": data.get("f170", 0) / 100 if data.get("f170") else 0,
                "open": data.get("f46", 0) / 100 if data.get("f46") else 0,
                "high": data.get("f44", 0) / 100 if data.get("f44") else 0,  # will fix
                "low": data.get("f45", 0) / 100 if data.get("f45") else 0,
                "prev_close": data.get("f60", 0) / 100 if data.get("f60") else 0,
                "volume": data.get("f47", 0),
                "amount": data.get("f48", 0),
            }
    except Exception as e:
        return None

def fetch_klines(secid_str, days=30):
    """获取近N日K线数据用于计算RSI和动量"""
    url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
           f"?secid={secid_str}&fields1=f1,f2,f3,f4,f5,f6"
           f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
           f"&klt=101&fqt=1&lmt={days}&end=20260427")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read().decode('utf-8'))
            rows = d.get("data", {}).get("klines", [])
            result = []
            for row in rows:
                parts = row.split(",")
                if len(parts) >= 6:
                    result.append({
                        "date": parts[0],
                        "open": float(parts[1]) if parts[1] else 0,
                        "close": float(parts[2]) if parts[2] else 0,
                        "high": float(parts[3]) if parts[3] else 0,
                        "low": float(parts[4]) if parts[4] else 0,
                        "vol": float(parts[5]) if parts[5] else 0,
                    })
            return result
    except:
        return []

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

def calc_momentum(closes, n=5):
    if len(closes) < n + 1:
        return None
    return (closes[-1] / closes[-n-1] - 1) * 100

def calc_volatility(closes, n=10):
    if len(closes) < n:
        return None
    recent = closes[-n:]
    mean = statistics.mean(recent)
    std = statistics.stdev(recent)
    return (std / mean) * 100

def support_resistance(klines):
    if len(klines) < 5:
        return None, None
    lows = [k["low"] for k in klines[-20:]]
    highs = [k["high"] for k in klines[-20:]]
    return round(min(lows), 3), round(max(highs), 3)

def main():
    codes = [c.strip() for c in sys.argv[1:] if c.strip()]
    if not codes:
        print("用法: python3 fetch_realtime.py 300274 159566 600089")
        sys.exit(1)
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n## 实时行情快照（查询时间: {now}）")
    print(f"\n| 代码 | 名称 | 现价 | 涨跌幅 | RSI14 | 5日动量 | 波动率(10日) | 近20日支撑 | 近20日压力 |")
    print(f"|------|------|------|--------|-------|---------|------------|----------|----------|")
    
    for code in codes:
        s = secid(code)
        # Get current snapshot
        curr = fetch_current(s, name=code)
        
        # Get klines for indicators
        klines = fetch_klines(s, days=30)
        
        if not klines:
            name = curr["name"] if curr else code
            print(f"| {code} | {name} | 暂无法获取 | - | - | - | - | - | - |")
            continue
        
        closes = [k["close"] for k in klines]
        name = curr["name"] if curr else (klines[-1].get("name", code) if klines else code)
        price = curr["price"] if curr else closes[-1]
        pct = curr["pct"] if curr else 0.0
        vol = curr["volume"] if curr else 0
        prev = curr["prev_close"] if curr else (closes[-2] if len(closes) > 1 else closes[-1])
        
        # Indicators
        rsi = calc_rsi(closes, 14)
        mom5 = calc_momentum(closes, 5)
        vol10 = calc_volatility(closes, 10)
        sup, res = support_resistance(klines)
        
        # Format
        pct_str = f"{pct:+.2f}%" if pct else "N/A"
        rsi_str = f"{rsi:.1f}" if rsi else "N/A"
        mom_str = f"{mom5:+.2f}%" if mom5 else "N/A"
        vol_str = f"{vol10:.2f}%" if vol10 else "N/A"
        sup_str = f"{sup:.3f}" if sup else "N/A"
        res_str = f"{res:.3f}" if res else "N/A"
        price_str = f"{price:.3f}" if price else "N/A"
        
        # Vol 格式化
        vol_str_fmt = f"{vol:,.0f}" if vol else "N/A"
        
        print(f"| {code} | {name} | {price_str} | {pct_str} | {rsi_str} | {mom_str} | {vol_str} | {sup_str} | {res_str} |")
    
    print()

if __name__ == "__main__":
    main()