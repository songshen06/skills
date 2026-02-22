#!/usr/bin/env python3
"""
Quick Report Generation Script
快速报告生成脚本

Usage:
  python3 quick_report.py [type] [code] [name] [--output FILE]
  python3 quick_report.py stock 600519 "贵州茅台"
  python3 quick_report.py index 000922 "中证红利"
  python3 quick_report.py sector 000986 "能源行业" --output energy_report.md
"""

import sys
import argparse
import datetime
import re
import os
import json
import importlib.util
from pathlib import Path
import pandas as pd

# Add the skills directory to Python path
script_dir = Path(__file__).parent
skill_dir = script_dir.parent
sys.path.append(str(skill_dir))

from templates.engine import render_template
from templates.web_renderer import render_web_report
from eastmoney_api import (
    get_realtime_quote,
    get_kline_daily,
    get_fund_flow,
    get_income_statement,
    get_balance_sheet,
    get_cash_flow,
)
from akshare_api import get_realtime_quote as get_realtime_quote_ak
from akshare_api import get_kline_daily as get_kline_daily_ak
from akshare_api import get_income_statement as get_income_statement_ak
from akshare_api import get_balance_sheet as get_balance_sheet_ak
from akshare_api import get_cash_flow as get_cash_flow_ak
from akshare_api import get_sw_level1_industry as get_sw_level1_industry_ak

FIN_SKILL_DIR = skill_dir.parent / "analyzing-financial-statements"
FIN_CALC_PATH = FIN_SKILL_DIR / "calculate_ratios.py"
_FIN_CALC_FUNC = None
_FIN_CALC_LOAD_ERR = None
LOCAL_FIXTURE_PATH = script_dir / "cache" / "local_financial_fixtures.json"
SW_LEVEL1_RECOMMENDATION = {
    "汽车": ["汽车", "轮胎", "整车", "零部件", "乘用车", "商用车"],
    "银行": ["银行"],
    "非银金融": ["证券", "保险", "信托", "期货", "券商"],
    "医药生物": ["医药", "制药", "生物", "医疗", "药业"],
    "电子": ["电子", "半导体", "芯片", "面板", "光学"],
    "计算机": ["软件", "计算机", "信息", "数据", "网络安全"],
    "通信": ["通信", "运营商", "光通信", "基站"],
    "电力设备": ["电池", "光伏", "风电", "储能", "电力设备"],
    "机械设备": ["机械", "装备", "自动化", "机床"],
    "基础化工": ["化工", "化学", "农药", "涂料", "橡胶"],
    "有色金属": ["有色", "铜", "铝", "锂", "稀土", "黄金"],
    "钢铁": ["钢铁", "特钢"],
    "煤炭": ["煤炭", "煤业"],
    "石油石化": ["石油", "石化", "炼化"],
    "公用事业": ["电力", "燃气", "水务", "环保"],
    "交通运输": ["港口", "航运", "铁路", "机场", "物流"],
    "房地产": ["地产", "置业", "物业"],
    "建筑材料": ["建材", "水泥", "玻璃"],
    "建筑装饰": ["建筑", "装饰", "工程"],
    "国防军工": ["军工", "航空", "航天", "船舶", "兵器"],
    "食品饮料": ["食品", "饮料", "白酒", "啤酒", "乳业"],
    "家用电器": ["家电", "电器", "厨电"],
    "纺织服饰": ["纺织", "服饰", "鞋", "纤维"],
    "轻工制造": ["包装", "造纸", "家具", "文娱用品"],
    "社会服务": ["旅游", "酒店", "教育", "人力"],
    "商贸零售": ["零售", "商贸", "百货", "超市"],
    "传媒": ["传媒", "影视", "广告", "游戏", "出版"],
    "农林牧渔": ["农业", "林业", "牧业", "渔业", "种业"],
    "环保": ["环保", "固废", "污水", "节能"],
}
INDUSTRY_VALUATION_PROFILE = {
    "银行": {
        "base_growth": 0.05, "bull_growth": 0.08, "bear_growth": 0.03,
        "base_terminal": 0.02, "bull_terminal": 0.025, "bear_terminal": 0.015,
        "wacc": 0.085,
        "method_mult": {"pe": 0.98, "pb": 1.06, "peg": 0.97, "ev": 0.95},
        "weights": {"pe": 0.20, "pb": 0.50, "peg": 0.10, "ev": 0.20},
    },
    "非银金融": {
        "base_growth": 0.07, "bull_growth": 0.11, "bear_growth": 0.04,
        "base_terminal": 0.022, "bull_terminal": 0.028, "bear_terminal": 0.018,
        "wacc": 0.095,
        "method_mult": {"pe": 1.00, "pb": 1.04, "peg": 1.00, "ev": 0.98},
        "weights": {"pe": 0.30, "pb": 0.35, "peg": 0.15, "ev": 0.20},
    },
    "汽车": {
        "base_growth": 0.09, "bull_growth": 0.14, "bear_growth": 0.05,
        "base_terminal": 0.025, "bull_terminal": 0.032, "bear_terminal": 0.02,
        "wacc": 0.10,
        "method_mult": {"pe": 1.02, "pb": 0.98, "peg": 1.01, "ev": 1.03},
        "weights": {"pe": 0.30, "pb": 0.15, "peg": 0.20, "ev": 0.35},
    },
    "电力设备": {
        "base_growth": 0.11, "bull_growth": 0.18, "bear_growth": 0.06,
        "base_terminal": 0.028, "bull_terminal": 0.035, "bear_terminal": 0.022,
        "wacc": 0.105,
        "method_mult": {"pe": 1.03, "pb": 1.00, "peg": 1.02, "ev": 1.04},
        "weights": {"pe": 0.30, "pb": 0.15, "peg": 0.25, "ev": 0.30},
    },
    "食品饮料": {
        "base_growth": 0.08, "bull_growth": 0.12, "bear_growth": 0.04,
        "base_terminal": 0.03, "bull_terminal": 0.036, "bear_terminal": 0.024,
        "wacc": 0.095,
        "method_mult": {"pe": 1.05, "pb": 1.02, "peg": 1.00, "ev": 1.00},
        "weights": {"pe": 0.35, "pb": 0.25, "peg": 0.20, "ev": 0.20},
    },
    "基础化工": {
        "base_growth": 0.075, "bull_growth": 0.11, "bear_growth": 0.035,
        "base_terminal": 0.022, "bull_terminal": 0.028, "bear_terminal": 0.018,
        "wacc": 0.105,
        "method_mult": {"pe": 1.00, "pb": 0.97, "peg": 1.00, "ev": 1.02},
        "weights": {"pe": 0.25, "pb": 0.20, "peg": 0.20, "ev": 0.35},
    },
}
DEFAULT_VALUATION_PROFILE = {
    "base_growth": 0.08, "bull_growth": 0.12, "bear_growth": 0.04,
    "base_terminal": 0.025, "bull_terminal": 0.03, "bear_terminal": 0.02,
    "wacc": 0.10,
    "method_mult": {"pe": 1.01, "pb": 0.99, "peg": 1.00, "ev": 1.02},
    "weights": {"pe": 0.25, "pb": 0.25, "peg": 0.25, "ev": 0.25},
}


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Quick Report Generation Tool for A-Stock Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 quick_report.py stock 600519 "贵州茅台"
  python3 quick_report.py index 000922 "中证红利"
  python3 quick_report.py sector 000986 "能源行业" --output energy_report.md
'''
    )
    
    parser.add_argument('type', type=str, choices=['stock', 'index', 'sector'],
                       help='Report type: stock (个股), index (指数), sector (行业)')
    
    parser.add_argument('code', type=str,
                       help='Stock/index/sector code (e.g., 600519 for 贵州茅台)')
    
    parser.add_argument('name', type=str, nargs='?', default=None,
                       help='Name (optional)')
    
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='Output file path')
    
    parser.add_argument('--template', '-t', type=str, default=None,
                       help='Custom template file')

    parser.add_argument('--format', '-f', type=str, default='markdown',
                       choices=['markdown', 'html'],
                       help='Output format: markdown or html (default: markdown)')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show verbose output')

    parser.add_argument(
        '--narrative-mode',
        type=str,
        default='rule',
        choices=['rule', 'agent', 'hybrid'],
        help='Narrative generation mode: rule, agent, or hybrid (default: rule)',
    )
    parser.add_argument(
        '--narrative-text',
        type=str,
        default=None,
        help='Agent-provided narrative text (for agent/hybrid mode)',
    )
    parser.add_argument(
        '--narrative-file',
        type=str,
        default=None,
        help='Path to agent-provided narrative markdown text file (for agent/hybrid mode)',
    )
    parser.add_argument(
        '--use-local-fin-fixture',
        action='store_true',
        help='Enable local financial fixture fallback for testing only (default: disabled)',
    )
    parser.add_argument(
        '--force-live-on-empty-cache',
        action='store_true',
        help='When financial statement cache is empty/invalid, force one live re-fetch (default: disabled)',
    )
    
    return parser.parse_args()


def get_default_template(type_: str) -> str:
    """获取默认模板"""
    templates = {
        'stock': 'stock_report_template.md',
        'index': 'index_report_template.md',
        'sector': 'sector_report_template.md'
    }
    return templates.get(type_, templates['stock'])


def get_stock_thesis(name: str):
    """Return stock-specific bullish/bearish points by simple name matching."""
    if "轮胎" in name:
        return {
            "bullish": [
                "原材料成本回落有助于利润率修复",
                "海外市场与配套需求带来增量空间",
                "产能利用率提升改善经营杠杆",
            ],
            "bearish": [
                "橡胶等原材料价格波动风险",
                "汽车景气下行导致需求承压",
                "出口与汇率扰动影响盈利稳定性",
            ],
            "catalysts": "原料价格下行、汽车产销改善、出口订单增长",
            "risk_description": "原材料与需求周期波动风险",
        }

    if "茅台" in name or "酒" in name:
        return {
            "bullish": [
                "高端白酒品牌护城河",
                "稳定的现金流和高ROE",
                "奢侈品属性抗通胀",
            ],
            "bearish": [
                "估值相对较高",
                "消费税政策风险",
                "渠道库存风险",
            ],
            "catalysts": "新品推出、价格调整、旺季需求",
            "risk_description": "市场波动风险、政策风险",
        }

    return {
        "bullish": [
            "主业经营相对稳健，现金流质量改善",
            "估值处于可比区间，具备修复空间",
            "行业景气边际变化带来业绩弹性",
        ],
        "bearish": [
            "宏观需求波动影响收入增长",
            "行业竞争加剧压缩利润空间",
            "原材料或融资成本上行风险",
        ],
        "catalysts": "业绩超预期、需求改善、政策支持",
        "risk_description": "行业景气和经营执行不确定性",
    }


def _recommend_sw_level1_industry(stock_name: str, hint_text: str = "") -> dict:
    """
    LLM-style recommendation for SW level-1 industry when direct mapping is unavailable.
    使用关键词打分模拟大模型推荐，给出申万一级行业建议与置信度。
    """
    text = f"{stock_name or ''} {hint_text or ''}"
    best_industry = "待补充"
    best_score = 0
    best_kw = ""
    for industry, kws in SW_LEVEL1_RECOMMENDATION.items():
        score = 0
        hit_kw = ""
        for kw in kws:
            if kw and kw in text:
                score += 1
                if not hit_kw:
                    hit_kw = kw
        if score > best_score:
            best_score = score
            best_industry = industry
            best_kw = hit_kw

    if best_score <= 0:
        return {
            "industry": "待补充",
            "sub_industry": "待补充（LLM推荐置信度低）",
            "confidence": 0.35,
            "method": "llm_rule_fallback",
        }

    confidence = min(0.6 + best_score * 0.15, 0.95)
    if best_industry == "汽车" and "轮胎" in text:
        sub = "轮胎与橡胶制品"
    elif best_industry == "电力设备" and "电池" in text:
        sub = "电池"
    else:
        sub = f"由关键词“{best_kw}”推断"

    return {
        "industry": best_industry,
        "sub_industry": f"{sub}（LLM推荐，置信度{confidence:.0%}）",
        "confidence": confidence,
        "method": "llm_rule_fallback",
    }


def _apply_sw_industry_classification(data: dict, code: str, stock_name: str, quote: dict):
    """Fill industry fields using SW direct mapping first, then LLM-style recommendation."""
    sw_info = get_sw_level1_industry_ak(code)
    if isinstance(sw_info, dict) and sw_info.get("industry_level1"):
        data["industry"] = sw_info.get("industry_level1")
        data["sub_industry"] = f"申万一级（{sw_info.get('sw_index_code', 'N/A')}）"
        data["industry_method"] = "sw_direct"
        return

    hint = ""
    if isinstance(quote, dict):
        hint = str(quote.get("所属行业") or quote.get("行业") or "")
    rec = _recommend_sw_level1_industry(stock_name, hint_text=hint)
    data["industry"] = rec.get("industry", "待补充")
    data["sub_industry"] = rec.get("sub_industry", "待补充")
    data["industry_method"] = rec.get("method", "llm_rule_fallback")


def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_rating(pe_ttm: float, pb: float, change_pct: float):
    if pe_ttm <= 0 and pb <= 0:
        return "中性"
    if pe_ttm < 18 and pb < 2.5 and change_pct > -3:
        return "买入"
    if pe_ttm > 45 or pb > 8:
        return "谨慎"
    return "中性"


def _apply_realtime_to_stock_data(data: dict, quote: dict):
    """Map EastMoney realtime quote fields into stock report data."""
    current_price = _to_float(quote.get("最新价"), _to_float(data.get("current_price"), 0))
    pe_ttm = _to_float(quote.get("市盈率(动)"), _to_float(data.get("pe_ttm"), 0))
    pb = _to_float(quote.get("市净率"), _to_float(data.get("pb"), 0))
    turnover_rate = _to_float(quote.get("换手率"), 0)
    change_pct = _to_float(quote.get("涨跌幅"), 0)
    market_cap_yi = _to_float(quote.get("总市值(亿)"), 0)
    dividend = quote.get("股息率")

    if current_price > 0:
        target_price = round(current_price * 1.12, 2)
        upside_potential = f"{((target_price / current_price) - 1) * 100:+.2f}%"
    else:
        target_price = data.get("target_price")
        upside_potential = data.get("upside_potential")

    rating = _build_rating(pe_ttm, pb, change_pct)
    risk_level = "高风险" if abs(change_pct) >= 5 else ("中等风险" if abs(change_pct) >= 2 else "低风险")

    data.update(
        {
            "current_price": current_price if current_price > 0 else data.get("current_price"),
            "pe_ttm": pe_ttm if pe_ttm > 0 else data.get("pe_ttm"),
            "pb": pb if pb > 0 else data.get("pb"),
            "target_price": target_price,
            "upside_potential": upside_potential,
            "investment_rating": rating,
            "risk_level": risk_level,
            "market_cap": f"{market_cap_yi:,.2f}亿元" if market_cap_yi > 0 else data.get("market_cap"),
            "profit_growth": f"{change_pct:+.2f}%",
            "sales_growth": f"{turnover_rate:+.2f}%",
            "risk_description": f"实时涨跌幅 {change_pct:+.2f}%，换手率 {turnover_rate:.2f}%",
            # When using realtime data, avoid leaving misleading demo-only values.
            "roe": "数据暂缺",
            "dividend_yield": dividend if dividend not in (None, "") else "数据暂缺",
        }
    )


def _apply_kline_to_stock_data(data: dict, kline_df):
    """Map kline derived indicators into stock template fields."""
    if kline_df is None or kline_df.empty:
        return

    df = kline_df.copy()
    close = df["收盘"].astype(float)
    high = df["最高"].astype(float)
    low = df["最低"].astype(float)
    volume = df["成交量"].astype(float)

    ma5 = close.rolling(5, min_periods=1).mean().iloc[-1]
    ma10 = close.rolling(10, min_periods=1).mean().iloc[-1]
    ma20 = close.rolling(20, min_periods=1).mean().iloc[-1]
    ma60 = close.rolling(60, min_periods=1).mean().iloc[-1]
    ma120 = close.rolling(120, min_periods=1).mean().iloc[-1]
    ma250 = close.rolling(250, min_periods=1).mean().iloc[-1]

    last_close = float(close.iloc[-1])
    short_support = float(low.tail(20).min())
    short_resistance = float(high.tail(20).max())
    medium_support = float(low.tail(60).min())
    medium_resistance = float(high.tail(60).max())
    long_support = float(low.min())
    long_resistance = float(high.max())

    vol_avg_5 = float(volume.tail(5).mean()) if len(volume) >= 1 else 0.0
    vol_ratio = float(volume.iloc[-1] / vol_avg_5) if vol_avg_5 > 0 else 1.0
    last_change = float(df["涨跌幅"].iloc[-1]) if "涨跌幅" in df.columns else 0.0
    last_turnover = float(df["换手率"].iloc[-1]) if "换手率" in df.columns else 0.0

    short_trend = "上升" if ma5 >= ma20 else "下降"
    medium_trend = "上升" if ma20 >= ma60 else "震荡"
    long_trend = "上升" if ma60 >= ma120 else "震荡"
    trend_strength = "强" if abs(last_change) >= 2 else ("中" if abs(last_change) >= 1 else "弱")

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_hist = (dif - dea) * 2
    macd_dif = float(dif.iloc[-1])
    macd_dea = float(dea.iloc[-1])
    macd_hist_last = float(macd_hist.iloc[-1])

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    def _calc_rsi(period: int) -> float:
        avg_gain = gain.rolling(period, min_periods=period).mean()
        avg_loss = loss.rolling(period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        value = rsi.iloc[-1]
        return float(value) if pd.notna(value) else 50.0

    rsi6 = _calc_rsi(6)
    rsi12 = _calc_rsi(12)
    rsi24 = _calc_rsi(24)

    # KDJ
    n = 9
    low_n = low.rolling(n, min_periods=1).min()
    high_n = high.rolling(n, min_periods=1).max()
    rsv = ((close - low_n) / (high_n - low_n).replace(0, pd.NA) * 100).fillna(50.0)
    k = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    d = k.ewm(alpha=1 / 3, adjust=False).mean()
    j = 3 * k - 2 * d
    kdj_k = float(k.iloc[-1])
    kdj_d = float(d.iloc[-1])
    kdj_j = float(j.iloc[-1])

    # BOLL
    boll_mid = close.rolling(20, min_periods=1).mean()
    boll_std = close.rolling(20, min_periods=1).std(ddof=0).fillna(0.0)
    boll_up = boll_mid + 2 * boll_std
    boll_low = boll_mid - 2 * boll_std
    boll_width = (
        ((boll_up.iloc[-1] - boll_low.iloc[-1]) / boll_mid.iloc[-1]) * 100
        if boll_mid.iloc[-1] else 0.0
    )

    data.update(
        {
            "current_price": round(last_close, 2),
            "short_cycle_desc": "日线(5/10/20日均线)",
            "medium_cycle_desc": "周线近似(20/60日均线≈4/12周)",
            "long_cycle_desc": "月线近似(120/250日均线≈6/12月)",
            "short_trend": short_trend,
            "short_strength": trend_strength,
            "short_support": round(short_support, 2),
            "short_resistance": round(short_resistance, 2),
            "medium_trend": medium_trend,
            "medium_strength": trend_strength,
            "medium_support": round(medium_support, 2),
            "medium_resistance": round(medium_resistance, 2),
            "long_trend": long_trend,
            "long_strength": trend_strength,
            "long_support": round(long_support, 2),
            "long_resistance": round(long_resistance, 2),
            "ma5": round(ma5, 2),
            "ma10": round(ma10, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "ma120": round(ma120, 2),
            "ma250": round(ma250, 2),
            "ma5_position": "上方" if last_close >= ma5 else "下方",
            "ma10_position": "上方" if last_close >= ma10 else "下方",
            "ma20_position": "上方" if last_close >= ma20 else "下方",
            "ma60_position": "上方" if last_close >= ma60 else "下方",
            "ma120_position": "上方" if last_close >= ma120 else "下方",
            "ma250_position": "上方" if last_close >= ma250 else "下方",
            "ma5_signal": "偏多" if ma5 >= ma10 else "偏空",
            "ma10_signal": "偏多" if ma10 >= ma20 else "偏空",
            "ma20_signal": "偏多" if ma20 >= ma60 else "偏空",
            "ma60_signal": "偏多" if ma60 >= ma120 else "偏空",
            "ma120_signal": "中性",
            "ma250_signal": "中性",
            "ma_alignment": "多头排列" if ma5 >= ma10 >= ma20 else "非多头排列",
            "ma_signal": "趋势向上" if ma5 >= ma20 else "趋势震荡",
            "ma_long": 60,
            "macd_dif": round(macd_dif, 4),
            "macd_dea": round(macd_dea, 4),
            "macd_hist": round(macd_hist_last, 4),
            "dif_signal": "上行" if macd_dif >= macd_dea else "下行",
            "dea_signal": "上行" if macd_dea >= 0 else "下行",
            "hist_signal": "红柱" if macd_hist_last >= 0 else "绿柱",
            "macd_cross": "金叉" if macd_dif >= macd_dea else "死叉",
            "cross_signal": "偏多" if macd_dif >= macd_dea else "偏空",
            "macd_zero": "零轴上方" if macd_dif >= 0 else "零轴下方",
            "zero_signal": "偏多" if macd_dif >= 0 else "偏空",
            "rsi6": round(rsi6, 2),
            "rsi12": round(rsi12, 2),
            "rsi24": round(rsi24, 2),
            "rsi6_status": "超买" if rsi6 > 80 else ("超卖" if rsi6 < 20 else "中性"),
            "rsi12_status": "超买" if rsi12 > 80 else ("超卖" if rsi12 < 20 else "中性"),
            "rsi24_status": "超买" if rsi24 > 80 else ("超卖" if rsi24 < 20 else "中性"),
            "rsi6_signal": "回落风险" if rsi6 > 80 else ("反弹关注" if rsi6 < 20 else "中性"),
            "rsi12_signal": "回落风险" if rsi12 > 80 else ("反弹关注" if rsi12 < 20 else "中性"),
            "rsi24_signal": "中性",
            "kdj_k": round(kdj_k, 2),
            "kdj_d": round(kdj_d, 2),
            "kdj_j": round(kdj_j, 2),
            "kdj_k_signal": "偏多" if kdj_k >= kdj_d else "偏空",
            "kdj_d_signal": "偏多" if kdj_d >= 50 else "偏空",
            "kdj_j_signal": "超买" if kdj_j > 100 else ("超卖" if kdj_j < 0 else "中性"),
            "kdj_cross": "金叉" if kdj_k >= kdj_d else "死叉",
            "kdj_cross_signal": "偏多" if kdj_k >= kdj_d else "偏空",
            "boll_up": round(float(boll_up.iloc[-1]), 2),
            "boll_mid": round(float(boll_mid.iloc[-1]), 2),
            "boll_low": round(float(boll_low.iloc[-1]), 2),
            "boll_up_position": "接近上轨" if last_close >= boll_up.iloc[-1] * 0.98 else "轨道内",
            "boll_mid_position": "上方" if last_close >= boll_mid.iloc[-1] else "下方",
            "boll_low_position": "接近下轨" if last_close <= boll_low.iloc[-1] * 1.02 else "轨道内",
            "boll_up_signal": "突破关注" if last_close >= boll_up.iloc[-1] else "中性",
            "boll_mid_signal": "偏多" if last_close >= boll_mid.iloc[-1] else "偏空",
            "boll_low_signal": "支撑观察" if last_close <= boll_low.iloc[-1] * 1.02 else "中性",
            "boll_width": f"{boll_width:.2f}%",
            "boll_width_status": "扩张" if boll_width > 12 else "收敛",
            "boll_width_signal": "波动放大" if boll_width > 12 else "波动收敛",
            "avg_volume": f"{vol_avg_5:,.0f}手",
            "volume_ratio": round(vol_ratio, 2),
            "turnover": f"{last_turnover:.2f}%",
            "volume_ratio_eval": "放量" if vol_ratio >= 1.2 else "缩量",
            "avg_volume_eval": "活跃" if vol_ratio >= 1.2 else "一般",
            "turnover_eval": "活跃" if last_turnover >= 3 else "平稳",
            "price_volume": "价量齐升" if (last_change > 0 and vol_ratio > 1) else "价量分化",
            "price_volume_eval": "偏多" if (last_change > 0 and vol_ratio > 1) else "中性",
            "trend_score": 75 if short_trend == "上升" else 45,
            "ma_score": 70 if ma5 >= ma20 else 45,
            "momentum_score": 60 if last_change > 0 else 45,
            "volume_score": 65 if vol_ratio > 1 else 45,
            "pattern_score": 55,
            "sr_score": 60,
            "trend_weighted": 18,
            "ma_weighted": 14,
            "momentum_weighted": 12,
            "volume_weighted": 10,
            "pattern_weighted": 6,
            "sr_weighted": 6,
            "total_score": 66 if short_trend == "上升" else 52,
            "total_weighted": 66 if short_trend == "上升" else 52,
            "technical_conclusion": f"短期{short_trend}，关键区间 {short_support:.2f}-{short_resistance:.2f}。",
        }
    )


def _apply_fund_flow_to_stock_data(data: dict, fund_flow: dict):
    """Map fund flow summary into report fields."""
    if not isinstance(fund_flow, dict) or "error" in fund_flow:
        return
    main_in = _to_float(fund_flow.get("主力净流入"), 0.0)
    main_ratio = _to_float(fund_flow.get("主力净流入占比"), 0.0)
    attitude = "积极买入" if main_in > 0 else "谨慎观望"
    data.update(
        {
            "fund_flow_status": "主力净流入" if main_in > 0 else "主力净流出",
            "fund_flow_trend_desc": f"主力净流入占比 {main_ratio:+.2f}%",
            "fund_flow_trend": "流入" if main_in > 0 else "流出",
            "main_force_attitude": attitude,
            "fund_flow_rating": "偏多" if main_in > 0 else "偏空",
            "fund_flow_confidence": f"{abs(main_ratio):.2f}%",
            "sentiment_rating": "中性偏多" if main_in > 0 else "中性",
            "sentiment_confidence": "中等",
        }
    )


def _pick_first_value(row: dict, candidates: list):
    for key in candidates:
        if key in row and row[key] not in (None, "", "-", "nan"):
            return row[key]
    return None


def _to_yi_str(value) -> str:
    num = _to_float(value, 0.0)
    if num == 0:
        return "数据暂缺"
    return f"{num / 1e8:.2f}"


def _to_year_label(value) -> str:
    s = str(value) if value is not None else ""
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) >= 8:
        year = digits[:4]
        month = digits[4:6]
        quarter_map = {"03": "Q1", "06": "Q2", "09": "Q3", "12": "Q4"}
        q = quarter_map.get(month)
        if q:
            return f"{year}{q}"
    if len(digits) >= 4:
        return digits[:4]
    return "数据暂缺"


def _load_financial_ratio_calculator():
    """Load analyzing-financial-statements skill calculator if available."""
    global _FIN_CALC_FUNC, _FIN_CALC_LOAD_ERR
    if _FIN_CALC_FUNC is not None or _FIN_CALC_LOAD_ERR is not None:
        return _FIN_CALC_FUNC
    if not FIN_CALC_PATH.exists():
        _FIN_CALC_LOAD_ERR = "missing"
        return None
    try:
        spec = importlib.util.spec_from_file_location("skill_fin_ratio_calc", str(FIN_CALC_PATH))
        if spec is None or spec.loader is None:
            _FIN_CALC_LOAD_ERR = "spec_error"
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _FIN_CALC_FUNC = getattr(module, "calculate_ratios_from_data", None)
        if _FIN_CALC_FUNC is None:
            _FIN_CALC_LOAD_ERR = "entrypoint_missing"
        return _FIN_CALC_FUNC
    except Exception as exc:
        _FIN_CALC_LOAD_ERR = str(exc)
        return None


def _extract_market_cap_yi(market_cap_value) -> float:
    if market_cap_value is None:
        return 0.0
    return _to_float(str(market_cap_value).replace("亿元", "").replace(",", ""), 0.0)


def _build_financial_payload(data: dict, income_df, balance_df, cash_df) -> dict:
    income_row = income_df.iloc[0].to_dict() if income_df is not None and not income_df.empty else {}
    balance_row = balance_df.iloc[0].to_dict() if balance_df is not None and not balance_df.empty else {}
    cash_row = cash_df.iloc[0].to_dict() if cash_df is not None and not cash_df.empty else {}

    share_price = _to_float(data.get("current_price"), 0.0)
    market_cap_yi = _extract_market_cap_yi(data.get("market_cap"))
    shares_outstanding = 0.0
    if share_price > 0 and market_cap_yi > 0:
        shares_outstanding = market_cap_yi * 1e8 / share_price

    profit_yoy = _to_float(str(data.get("profit_yoy", "")).replace("%", "").replace("+", ""), 0.0)

    return {
        "income_statement": {
            "revenue": _to_float(
                _pick_first_value(income_row, ["营业总收入", "TOTAL_OPERATE_INCOME", "营业收入", "OPERATE_INCOME"]),
                0.0,
            ),
            "cost_of_goods_sold": _to_float(
                _pick_first_value(income_row, ["营业总成本", "营业成本", "OPERATE_COST"]),
                0.0,
            ),
            "operating_income": _to_float(
                _pick_first_value(income_row, ["营业利润", "OPERATE_PROFIT"]),
                0.0,
            ),
            "ebit": _to_float(
                _pick_first_value(income_row, ["利润总额", "TOTAL_PROFIT", "营业利润", "OPERATE_PROFIT"]),
                0.0,
            ),
            "ebitda": _to_float(
                _pick_first_value(
                    income_row,
                    [
                        "EBITDA",
                        "息税折旧摊销前利润",
                        "利润总额",
                        "TOTAL_PROFIT",
                        "营业利润",
                        "OPERATE_PROFIT",
                    ],
                ),
                0.0,
            ),
            "interest_expense": abs(
                _to_float(
                    _pick_first_value(
                        income_row,
                        [
                            "利息费用",
                            "INTEREST_EXPENSE",
                            "利息支出",
                            "财务费用",
                        ],
                    ),
                    0.0,
                )
            ),
            "net_income": _to_float(
                _pick_first_value(income_row, ["归母净利润", "PARENT_NETPROFIT", "净利润", "NETPROFIT"]),
                0.0,
            ),
        },
        "balance_sheet": {
            "total_assets": _to_float(
                _pick_first_value(balance_row, ["资产总计", "TOTAL_ASSETS"]),
                0.0,
            ),
            "current_assets": _to_float(
                _pick_first_value(balance_row, ["流动资产合计", "流动资产", "TOTAL_CURRENT_ASSETS"]),
                0.0,
            ),
            "cash_and_equivalents": _to_float(
                _pick_first_value(balance_row, ["货币资金", "现金及现金等价物", "CASH_EQUIVALENTS"]),
                0.0,
            ),
            "accounts_receivable": _to_float(
                _pick_first_value(balance_row, ["应收账款", "ACCOUNTS_RECEIVABLE"]),
                0.0,
            ),
            "inventory": _to_float(
                _pick_first_value(balance_row, ["存货", "INVENTORY"]),
                0.0,
            ),
            "current_liabilities": _to_float(
                _pick_first_value(balance_row, ["流动负债合计", "TOTAL_CURRENT_LIABILITIES"]),
                0.0,
            ),
            "total_debt": _to_float(
                _pick_first_value(balance_row, ["负债合计", "TOTAL_LIABILITIES"]),
                0.0,
            ),
            "current_portion_long_term_debt": _to_float(
                _pick_first_value(balance_row, ["一年内到期的非流动负债", "CURRENT_PORTION_LONG_TERM_DEBT"]),
                0.0,
            ),
            "shareholders_equity": _to_float(
                _pick_first_value(
                    balance_row,
                    ["所有者权益(或股东权益)合计", "归属于母公司股东权益合计", "TOTAL_EQUITY"],
                ),
                0.0,
            ),
        },
        "cash_flow": {
            "operating_cash_flow": _to_float(
                _pick_first_value(cash_row, ["经营活动产生的现金流量净额", "NETCASH_OPERATE"]),
                0.0,
            ),
            "investing_cash_flow": _to_float(
                _pick_first_value(cash_row, ["投资活动产生的现金流量净额", "NETCASH_INVEST"]),
                0.0,
            ),
            "financing_cash_flow": _to_float(
                _pick_first_value(cash_row, ["筹资活动产生的现金流量净额", "NETCASH_FINANCE"]),
                0.0,
            ),
        },
        "market_data": {
            "share_price": share_price,
            "shares_outstanding": shares_outstanding,
            "earnings_growth_rate": profit_yoy / 100 if profit_yoy != 0 else 0.0,
        },
    }


def _payload_has_meaningful_financial_data(payload: dict) -> bool:
    income = payload.get("income_statement", {})
    balance = payload.get("balance_sheet", {})
    checks = [
        _to_float(income.get("revenue"), 0.0),
        _to_float(income.get("net_income"), 0.0),
        _to_float(balance.get("total_assets"), 0.0),
        _to_float(balance.get("shareholders_equity"), 0.0),
    ]
    return any(v > 0 for v in checks)


def _apply_financial_skill_to_stock_data(data: dict, income_df, balance_df, cash_df):
    """Enhance financial analysis section using analyzing-financial-statements skill."""
    calc_func = _load_financial_ratio_calculator()
    if calc_func is None:
        data["financial_skill_status"] = "unavailable"
        return

    try:
        payload = _build_financial_payload(data, income_df, balance_df, cash_df)
        if not _payload_has_meaningful_financial_data(payload):
            data["financial_skill_status"] = "insufficient_data"
            return
        results = calc_func(payload, lang="zh")
        ratios = results.get("ratios", {})
        prof = ratios.get("profitability", {})
        liq = ratios.get("liquidity", {})
        lev = ratios.get("leverage", {})
        val = ratios.get("valuation", {})

        roe = _to_float(prof.get("roe"), 0.0)
        if roe > 0:
            data["roe"] = f"{roe * 100:.2f}"
            data["roe_eval"] = "较高" if roe >= 0.12 else ("一般" if roe >= 0.08 else "偏弱")

        roa = _to_float(prof.get("roa"), 0.0)
        if roa > 0:
            data["roa"] = f"{roa * 100:.2f}%"
            data["roa_eval"] = "较好" if roa >= 0.05 else ("一般" if roa >= 0.03 else "偏弱")

        gross_margin = _to_float(prof.get("gross_margin"), 0.0)
        if gross_margin > 0:
            data["gross_margin"] = f"{gross_margin * 100:.2f}%"

        net_margin = _to_float(prof.get("net_margin"), 0.0)
        if net_margin > 0:
            data["net_margin"] = f"{net_margin * 100:.2f}%"

        current_ratio = _to_float(liq.get("current_ratio"), 0.0)
        if current_ratio > 0:
            data["current_ratio"] = f"{current_ratio:.2f}"
            data["cr_eval"] = "良好" if current_ratio >= 1.5 else ("一般" if current_ratio >= 1.0 else "偏弱")

        quick_ratio = _to_float(liq.get("quick_ratio"), 0.0)
        if quick_ratio > 0:
            data["quick_ratio"] = f"{quick_ratio:.2f}"
            data["qr_eval"] = "良好" if quick_ratio >= 1.0 else ("一般" if quick_ratio >= 0.7 else "偏弱")

        interest_coverage = _to_float(lev.get("interest_coverage"), 0.0)
        if interest_coverage > 0:
            data["interest_coverage"] = f"{interest_coverage:.2f}"
            data["ic_eval"] = "安全" if interest_coverage >= 3 else ("一般" if interest_coverage >= 1.5 else "偏弱")

        debt_to_equity = _to_float(lev.get("debt_to_equity"), 0.0)
        if debt_to_equity > 0:
            debt_to_asset = debt_to_equity / (1 + debt_to_equity) * 100
            data["debt_to_asset"] = f"{debt_to_asset:.2f}%"
            data["dta_eval"] = "安全" if debt_to_asset < 60 else ("可控" if debt_to_asset < 70 else "偏高")

        pe_ratio = _to_float(val.get("pe_ratio"), 0.0)
        if pe_ratio > 0 and _to_float(data.get("pe_ttm"), 0.0) <= 0:
            data["pe_ttm"] = f"{pe_ratio:.2f}"

        pb_ratio = _to_float(val.get("pb_ratio"), 0.0)
        if pb_ratio > 0 and _to_float(data.get("pb"), 0.0) <= 0:
            data["pb"] = f"{pb_ratio:.2f}"

        ps_ratio = _to_float(val.get("ps_ratio"), 0.0)
        if ps_ratio > 0:
            data["ps"] = f"{ps_ratio:.2f}"

        ev_to_ebitda = _to_float(val.get("ev_to_ebitda"), 0.0)
        if ev_to_ebitda > 0:
            data["ev_ebitda"] = f"{ev_to_ebitda:.2f}"

        summary = str(results.get("summary", "")).strip()
        if summary and summary not in ("数据不足，无法生成摘要。",):
            base_growth = data.get("growth_analysis", "")
            data["growth_analysis"] = f"{base_growth} 财务计算补充：{summary}".strip()

        data["financial_skill_status"] = "enabled"
    except Exception:
        data["financial_skill_status"] = "error"


def _apply_income_statement_to_stock_data(data: dict, income_df):
    """Map available income-statement fields into template."""
    if income_df is None or income_df.empty:
        return
    row = income_df.iloc[0].to_dict()

    revenue_raw = _pick_first_value(
        row,
        [
            "TOTAL_OPERATE_INCOME",
            "OPERATE_INCOME",
            "TOTAL_OPERATE_REVENUE",
            "营业总收入",
            "营业收入",
        ],
    )
    net_profit_raw = _pick_first_value(
        row,
        [
            "PARENT_NETPROFIT",
            "NETPROFIT",
            "归母净利润",
            "净利润",
        ],
    )
    revenue_yoy_raw = _pick_first_value(
        row,
        ["YOY_TOTAL_OPERATE_INCOME", "TOTAL_OPERATE_INCOME_YOY", "营业总收入同比", "营业收入同比"],
    )
    profit_yoy_raw = _pick_first_value(
        row,
        ["YOY_PARENT_NETPROFIT", "PARENT_NETPROFIT_YOY", "归母净利润同比", "净利润同比"],
    )
    gross_margin_raw = _pick_first_value(row, ["GROSS_MARGIN", "销售毛利率", "毛利率"])
    net_margin_raw = _pick_first_value(row, ["NET_MARGIN", "销售净利率", "净利率"])

    revenue = _to_float(revenue_raw, 0.0)
    net_profit = _to_float(net_profit_raw, 0.0)
    revenue_yoy = _to_float(revenue_yoy_raw, 0.0)
    profit_yoy = _to_float(profit_yoy_raw, 0.0)
    gross_margin = _to_float(gross_margin_raw, 0.0)
    net_margin = _to_float(net_margin_raw, 0.0)

    if revenue > 0:
        data["revenue"] = f"{revenue / 1e8:.2f}亿元"
    if net_profit != 0:
        data["net_profit"] = f"{net_profit / 1e8:.2f}亿元"
    data["revenue_yoy"] = f"{revenue_yoy:+.2f}%" if revenue_yoy_raw is not None else data.get("revenue_yoy", "数据暂缺")
    data["profit_yoy"] = f"{profit_yoy:+.2f}%" if profit_yoy_raw is not None else data.get("profit_yoy", "数据暂缺")
    data["gross_margin"] = f"{gross_margin:.2f}%" if gross_margin_raw is not None else data.get("gross_margin", "数据暂缺")
    data["net_margin"] = f"{net_margin:.2f}%" if net_margin_raw is not None else data.get("net_margin", "数据暂缺")

    data["growth_analysis"] = (
        f"营收同比 {data.get('revenue_yoy', '数据暂缺')}，净利润同比 {data.get('profit_yoy', '数据暂缺')}。"
    )

    # Appendix: income statement summary (latest 3 periods)
    rows = income_df.head(3).to_dict("records")
    if rows:
        data["year_1"] = _to_year_label(_pick_first_value(rows[0], ["报告日", "REPORT_DATE_NAME"]))
        data["year_2"] = _to_year_label(_pick_first_value(rows[1], ["报告日", "REPORT_DATE_NAME"])) if len(rows) > 1 else "数据暂缺"
        data["year_3"] = _to_year_label(_pick_first_value(rows[2], ["报告日", "REPORT_DATE_NAME"])) if len(rows) > 2 else "数据暂缺"

        def _income_map(row: dict):
            rev = _pick_first_value(row, ["营业总收入", "TOTAL_OPERATE_INCOME", "营业收入", "OPERATE_INCOME"])
            cost = _pick_first_value(row, ["营业总成本", "OPERATE_COST", "营业成本"])
            op = _pick_first_value(row, ["营业利润", "OPERATE_PROFIT"])
            np = _pick_first_value(row, ["归属于母公司所有者的净利润", "PARENT_NETPROFIT", "净利润", "NETPROFIT"])
            rev_v = _to_float(rev, 0.0)
            cost_v = _to_float(cost, 0.0)
            gp_v = rev_v - cost_v if rev_v and cost_v else 0.0
            return rev_v, cost_v, gp_v, _to_float(op, 0.0), _to_float(np, 0.0)

        r1 = _income_map(rows[0])
        r2 = _income_map(rows[1]) if len(rows) > 1 else (0, 0, 0, 0, 0)
        r3 = _income_map(rows[2]) if len(rows) > 2 else (0, 0, 0, 0, 0)

        data["rev_1"], data["cost_1"], data["gp_1"], data["op_1"], data["np_1"] = (_to_yi_str(x) for x in r1)
        data["rev_2"], data["cost_2"], data["gp_2"], data["op_2"], data["np_2"] = (_to_yi_str(x) for x in r2)
        data["rev_3"], data["cost_3"], data["gp_3"], data["op_3"], data["np_3"] = (_to_yi_str(x) for x in r3)

        def _cagr(v_new, v_old, periods=2):
            if v_old and v_old > 0 and v_new and v_new > 0:
                return f"{((v_new / v_old) ** (1 / periods) - 1) * 100:.2f}%"
            return "数据暂缺"

        data["rev_cagr"] = _cagr(r1[0], r3[0])
        data["cost_cagr"] = _cagr(r1[1], r3[1])
        data["gp_cagr"] = _cagr(r1[2], r3[2])
        data["op_cagr"] = _cagr(r1[3], r3[3])
        data["np_cagr"] = _cagr(r1[4], r3[4])

        # Financial analysis section enrichment
        revenue_latest = r1[0]
        net_profit_latest = r1[4]
        revenue_prev = r2[0] if r2[0] else 0.0
        profit_prev = r2[4] if r2[4] else 0.0
        gross_margin_pct = (r1[2] / revenue_latest * 100) if revenue_latest > 0 else 0.0
        gross_margin_prev = (r2[2] / revenue_prev * 100) if revenue_prev > 0 else 0.0
        net_margin_pct = (net_profit_latest / revenue_latest * 100) if revenue_latest > 0 else 0.0
        net_margin_prev = (r2[4] / revenue_prev * 100) if revenue_prev > 0 else 0.0
        interest_fee = _to_float(_pick_first_value(rows[0], ["利息费用", "INTEREST_EXPENSE"]), 0.0)
        interest_cov = (r1[3] / interest_fee) if interest_fee > 0 else 0.0
        revenue_change = ((revenue_latest / revenue_prev) - 1) * 100 if revenue_prev > 0 else 0.0
        profit_change = ((net_profit_latest / profit_prev) - 1) * 100 if profit_prev > 0 else 0.0

        data["revenue_yoy"] = f"{revenue_change:+.2f}%" if revenue_prev > 0 else data.get("revenue_yoy", "数据暂缺")
        data["profit_yoy"] = f"{profit_change:+.2f}%" if profit_prev > 0 else data.get("profit_yoy", "数据暂缺")
        data["revenue_rank"] = data.get("revenue_rank", "待补充")
        data["profit_rank"] = data.get("profit_rank", "待补充")
        data["gross_margin_rank"] = data.get("gross_margin_rank", "待补充")
        data["net_margin_rank"] = data.get("net_margin_rank", "待补充")
        data["roe_rank"] = data.get("roe_rank", "待补充")
        data["revenue_eval"] = "良好" if revenue_change >= 10 else ("平稳" if revenue_change >= 0 else "承压")
        data["profit_eval"] = "良好" if profit_change >= 10 else ("平稳" if profit_change >= 0 else "承压")
        data["gross_margin_change"] = f"{(gross_margin_pct - gross_margin_prev):+.2f}pct" if revenue_prev > 0 else data.get("gross_margin_change", "数据暂缺")
        data["net_margin_change"] = f"{(net_margin_pct - net_margin_prev):+.2f}pct" if revenue_prev > 0 else data.get("net_margin_change", "数据暂缺")
        data["roe_change"] = data.get("roe_change", "数据暂缺")
        data["gross_margin"] = f"{gross_margin_pct:.2f}%"
        data["net_margin"] = f"{net_margin_pct:.2f}%"
        data["gross_margin_eval"] = "较好" if gross_margin_pct >= 15 else ("一般" if gross_margin_pct >= 8 else "偏弱")
        data["net_margin_eval"] = "较好" if net_margin_pct >= 8 else ("一般" if net_margin_pct >= 4 else "偏弱")
        data["interest_coverage"] = f"{interest_cov:.2f}" if interest_cov > 0 else data.get("interest_coverage", "数据暂缺")
        data["ic_eval"] = "安全" if interest_cov >= 3 else ("一般" if interest_cov >= 1.5 else "偏弱")
        data["growth_analysis"] = (
            f"营收同比 {data.get('revenue_yoy', '数据暂缺')}，净利润同比 {data.get('profit_yoy', '数据暂缺')}。"
        )


def _apply_balance_sheet_to_stock_data(data: dict, balance_df):
    """Map balance-sheet fields into appendix summary."""
    if balance_df is None or balance_df.empty:
        return
    rows = balance_df.head(3).to_dict("records")
    if not rows:
        return

    def _bmap(row: dict):
        total_asset = _pick_first_value(row, ["资产总计", "TOTAL_ASSETS"])
        current_asset = _pick_first_value(row, ["流动资产合计", "流动资产", "TOTAL_CURRENT_ASSETS"])
        noncurrent_asset = _pick_first_value(row, ["非流动资产合计", "TOTAL_NONCURRENT_ASSETS"])
        total_liab = _pick_first_value(row, ["负债合计", "TOTAL_LIABILITIES"])
        current_liab = _pick_first_value(row, ["流动负债合计", "TOTAL_CURRENT_LIABILITIES"])
        noncurrent_liab = _pick_first_value(row, ["非流动负债合计", "TOTAL_NONCURRENT_LIABILITIES"])
        inventory = _pick_first_value(row, ["存货", "INVENTORY"])
        equity = _pick_first_value(row, ["所有者权益(或股东权益)合计", "归属于母公司股东权益合计", "TOTAL_EQUITY"])
        return (
            _to_float(total_asset, 0.0),
            _to_float(current_asset, 0.0),
            _to_float(noncurrent_asset, 0.0),
            _to_float(total_liab, 0.0),
            _to_float(current_liab, 0.0),
            _to_float(noncurrent_liab, 0.0),
            _to_float(inventory, 0.0),
            _to_float(equity, 0.0),
        )

    b1 = _bmap(rows[0])
    b2 = _bmap(rows[1]) if len(rows) > 1 else (0, 0, 0, 0, 0, 0, 0, 0)
    b3 = _bmap(rows[2]) if len(rows) > 2 else (0, 0, 0, 0, 0, 0, 0, 0)

    data["total_asset_1"], data["current_asset_1"], data["noncurrent_asset_1"], data["total_liab_1"], data["current_liab_1"], data["noncurrent_liab_1"], _, data["equity_1"] = (_to_yi_str(x) for x in b1)
    data["total_asset_2"], data["current_asset_2"], data["noncurrent_asset_2"], data["total_liab_2"], data["current_liab_2"], data["noncurrent_liab_2"], _, data["equity_2"] = (_to_yi_str(x) for x in b2)
    data["total_asset_3"], data["current_asset_3"], data["noncurrent_asset_3"], data["total_liab_3"], data["current_liab_3"], data["noncurrent_liab_3"], _, data["equity_3"] = (_to_yi_str(x) for x in b3)

    # Solvency indicators
    total_asset, current_asset, _, total_liab, current_liab, _, inventory, equity = b1
    debt_to_asset = (total_liab / total_asset * 100) if total_asset > 0 else 0.0
    current_ratio = (current_asset / current_liab) if current_liab > 0 else 0.0
    quick_ratio = ((current_asset - inventory) / current_liab) if current_liab > 0 else 0.0
    roe = (_to_float(data.get("net_profit", "0").replace("亿元", ""), 0.0) / (_to_float(data.get("equity_1"), 0.0)) * 100) if _to_float(data.get("equity_1"), 0.0) > 0 else 0.0

    data["debt_to_asset"] = f"{debt_to_asset:.2f}%" if debt_to_asset > 0 else data.get("debt_to_asset", "数据暂缺")
    data["current_ratio"] = f"{current_ratio:.2f}" if current_ratio > 0 else data.get("current_ratio", "数据暂缺")
    data["quick_ratio"] = f"{quick_ratio:.2f}" if quick_ratio > 0 else data.get("quick_ratio", "数据暂缺")
    data["dta_eval"] = "安全" if debt_to_asset < 60 else ("可控" if debt_to_asset < 70 else "偏高")
    data["cr_eval"] = "良好" if current_ratio >= 1.5 else ("一般" if current_ratio >= 1.0 else "偏弱")
    data["qr_eval"] = "良好" if quick_ratio >= 1.0 else ("一般" if quick_ratio >= 0.7 else "偏弱")
    if roe > 0:
        data["roe"] = f"{roe:.2f}"
        data["roe_eval"] = "较高" if roe >= 12 else ("一般" if roe >= 8 else "偏弱")


def _apply_cash_flow_to_stock_data(data: dict, cash_df):
    """Map cash-flow fields into appendix summary."""
    if cash_df is None or cash_df.empty:
        return
    rows = cash_df.head(3).to_dict("records")
    if not rows:
        return

    def _cmap(row: dict):
        ocf = _pick_first_value(row, ["经营活动产生的现金流量净额", "经营活动产生的现金流量", "NETCASH_OPERATE"])
        icf = _pick_first_value(row, ["投资活动产生的现金流量净额", "投资活动产生的现金流量", "NETCASH_INVEST"])
        fcf = _pick_first_value(row, ["筹资活动产生的现金流量净额", "筹资活动产生的现金流量", "NETCASH_FINANCE"])
        ncf = _pick_first_value(row, ["现金及现金等价物净增加额", "NETCASH_INCREASE"])
        return (_to_float(ocf, 0.0), _to_float(icf, 0.0), _to_float(fcf, 0.0), _to_float(ncf, 0.0))

    c1 = _cmap(rows[0])
    c2 = _cmap(rows[1]) if len(rows) > 1 else (0, 0, 0, 0)
    c3 = _cmap(rows[2]) if len(rows) > 2 else (0, 0, 0, 0)

    data["ocf_1"], data["icf_1"], data["fcf_1"], data["ncf_1"] = (_to_yi_str(x) for x in c1)
    data["ocf_2"], data["icf_2"], data["fcf_2"], data["ncf_2"] = (_to_yi_str(x) for x in c2)
    data["ocf_3"], data["icf_3"], data["fcf_3"], data["ncf_3"] = (_to_yi_str(x) for x in c3)

    # Cash flow section indicators
    ocf, icf, _, _ = c1
    free_cf = ocf + icf
    net_profit_yi = _to_float(str(data.get("net_profit", "0")).replace("亿元", ""), 0.0)
    ccr = (ocf / (net_profit_yi * 1e8)) if net_profit_yi > 0 else 0.0

    data["operating_cash_flow"] = f"{ocf / 1e8:.2f}亿元" if ocf != 0 else data.get("operating_cash_flow", "数据暂缺")
    data["free_cash_flow"] = f"{free_cf / 1e8:.2f}亿元"
    data["cash_conversion_ratio"] = f"{ccr:.2f}" if ccr > 0 else "数据暂缺"
    data["ocf_eval"] = "较好" if ocf > 0 else "偏弱"
    data["fcf_eval"] = "较好" if free_cf > 0 else "一般"
    data["ccr_eval"] = "健康" if ccr >= 1.0 else ("一般" if ccr >= 0.7 else "偏弱")


def _apply_profitability_trends(data: dict, income_df, balance_df):
    """
    Fill ROE/ROA latest values and period-over-period change (pct points).
    Note: Uses latest vs previous available period in current dataset.
    """
    if income_df is None or income_df.empty or balance_df is None or balance_df.empty:
        return

    income_rows = income_df.head(2).to_dict("records")
    balance_rows = balance_df.head(2).to_dict("records")
    if len(income_rows) < 1 or len(balance_rows) < 1:
        return

    def _net_profit(row: dict) -> float:
        return _to_float(
            _pick_first_value(
                row,
                ["归属于母公司所有者的净利润", "归母净利润", "PARENT_NETPROFIT", "净利润", "NETPROFIT"],
            ),
            0.0,
        )

    def _equity(row: dict) -> float:
        return _to_float(
            _pick_first_value(
                row,
                ["所有者权益(或股东权益)合计", "归属于母公司股东权益合计", "TOTAL_EQUITY"],
            ),
            0.0,
        )

    def _assets(row: dict) -> float:
        return _to_float(_pick_first_value(row, ["资产总计", "TOTAL_ASSETS"]), 0.0)

    np_1 = _net_profit(income_rows[0])
    eq_1 = _equity(balance_rows[0])
    as_1 = _assets(balance_rows[0])

    roe_1 = (np_1 / eq_1 * 100) if eq_1 > 0 else 0.0
    roa_1 = (np_1 / as_1 * 100) if as_1 > 0 else 0.0

    if roe_1 > 0:
        data["roe"] = f"{roe_1:.2f}"
        data["roe_eval"] = "较高" if roe_1 >= 12 else ("一般" if roe_1 >= 8 else "偏弱")
    if roa_1 > 0:
        data["roa"] = f"{roa_1:.2f}%"
        data["roa_eval"] = "较好" if roa_1 >= 5 else ("一般" if roa_1 >= 3 else "偏弱")

    if len(income_rows) < 2 or len(balance_rows) < 2:
        return

    np_2 = _net_profit(income_rows[1])
    eq_2 = _equity(balance_rows[1])
    as_2 = _assets(balance_rows[1])
    roe_2 = (np_2 / eq_2 * 100) if eq_2 > 0 else 0.0
    roa_2 = (np_2 / as_2 * 100) if as_2 > 0 else 0.0

    if roe_1 > 0 and roe_2 > 0:
        data["roe_change"] = f"{(roe_1 - roe_2):+.2f}pct"
    if roa_1 > 0 and roa_2 > 0:
        data["roa_change"] = f"{(roa_1 - roa_2):+.2f}pct"


def _apply_strategy_rules(data: dict):
    """Fill strategy and monitoring fields with deterministic rule-based values."""
    price = _to_float(data.get("current_price"), 0.0)
    short_support = _to_float(data.get("short_support"), price * 0.97 if price else 0.0)
    short_resistance = _to_float(data.get("short_resistance"), price * 1.05 if price else 0.0)
    medium_support = _to_float(data.get("medium_support"), price * 0.92 if price else 0.0)
    medium_resistance = _to_float(data.get("medium_resistance"), price * 1.12 if price else 0.0)
    long_support = _to_float(data.get("long_support"), price * 0.85 if price else 0.0)
    long_resistance = _to_float(data.get("long_resistance"), price * 1.25 if price else 0.0)
    risk_level = str(data.get("risk_level", "中等风险"))
    short_trend = str(data.get("short_trend", "震荡"))
    rating = str(data.get("investment_rating", "中性"))
    pe_ttm = _to_float(data.get("pe_ttm"), 0.0)
    pb = _to_float(data.get("pb"), 0.0)

    position_map = {"低风险": "40%-60%", "中等风险": "25%-40%", "高风险": "10%-25%"}
    base_position = position_map.get(risk_level, "20%-35%")

    if short_trend == "上升":
        short_action = "回踩支撑分批买入"
    elif short_trend == "下降":
        short_action = "控制仓位，等待企稳信号"
    else:
        short_action = "区间内低吸高抛"

    data.update(
        {
            "short_term_action": short_action,
            "short_entry_zone": (
                f"{short_support:.2f}-{short_support * 1.02:.2f}" if short_support > 0 else "数据暂缺"
            ),
            "short_stop_loss": f"{short_support * 0.97:.2f}" if short_support > 0 else "数据暂缺",
            "short_target": f"{short_resistance:.2f}" if short_resistance > 0 else "数据暂缺",
            "short_position": base_position,
            "medium_term_action": "趋势跟踪，回调增配",
            "medium_entry_zone": (
                f"{medium_support:.2f}-{price:.2f}" if medium_support > 0 and price > 0 else "数据暂缺"
            ),
            "medium_stop_loss": f"{medium_support * 0.95:.2f}" if medium_support > 0 else "数据暂缺",
            "medium_target": f"{medium_resistance:.2f}" if medium_resistance > 0 else "数据暂缺",
            "medium_position": "50%-70%" if rating == "买入" else "30%-50%",
            "long_term_action": "基于估值与盈利兑现长期跟踪",
            "long_entry_zone": (
                f"{long_support:.2f}-{medium_support:.2f}" if long_support > 0 and medium_support > 0 else "数据暂缺"
            ),
            "long_stop_loss": f"{long_support * 0.92:.2f}" if long_support > 0 else "数据暂缺",
            "long_target": f"{long_resistance:.2f}" if long_resistance > 0 else "数据暂缺",
            "long_position": "60%-80%" if rating == "买入" else "35%-55%",
            "revenue_threshold": "8",
            "profit_margin_threshold": "10",
            "roe_threshold": "12",
            "debt_threshold": "65",
            "peg_threshold": "1.5",
            "pe_percentile": "40" if pe_ttm > 0 and pe_ttm < 20 else ("60" if pe_ttm > 0 else "数据暂缺"),
            "pb_percentile": "35" if pb > 0 and pb < 2 else ("55" if pb > 0 else "数据暂缺"),
            "company_specific_risks": "成本波动、订单波动、经营执行风险",
            "industry_risks": "行业景气下行与竞争加剧风险",
            "macro_risks": "宏观需求走弱和流动性收紧风险",
            "market_risks": "市场情绪波动导致估值压缩风险",
            "latest_news": "近期公告与行业动态建议结合交易日持续跟踪。",
            "analyst_ratings": "| 数据暂缺 |",
            "institutional_holdings": "| 数据暂缺 |",
        }
    )


def _apply_valuation_rules(data: dict):
    """Fill valuation scenario fields with deterministic defaults."""
    current = _to_float(data.get("current_price"), 0.0)
    target = _to_float(data.get("target_price"), current if current > 0 else 0.0)

    if current <= 0 and target <= 0:
        return

    if current <= 0:
        current = target
    if target <= 0:
        target = current

    industry = str(data.get("industry", "")).strip()
    profile = INDUSTRY_VALUATION_PROFILE.get(industry, DEFAULT_VALUATION_PROFILE)
    method_mult = profile.get("method_mult", DEFAULT_VALUATION_PROFILE["method_mult"])
    weights = profile.get("weights", DEFAULT_VALUATION_PROFILE["weights"])

    base_value = target
    bull_value = round(base_value * (1 + max(profile.get("bull_growth", 0.12) - profile.get("base_growth", 0.08), 0.08)), 2)
    bear_floor = 1 + min(profile.get("bear_growth", 0.04) - profile.get("base_growth", 0.08), -0.08)
    bear_value = round(max(current * bear_floor, 0.01), 2)

    def _margin(v: float) -> str:
        if current <= 0:
            return "数据暂缺"
        return f"{((v / current) - 1) * 100:+.2f}%"

    bull_upside = _margin(bull_value)
    base_upside = _margin(base_value)
    bear_upside = _margin(bear_value)

    pe_valuation = round(base_value * _to_float(method_mult.get("pe"), 1.01), 2)
    pb_valuation = round(base_value * _to_float(method_mult.get("pb"), 0.99), 2)
    peg_valuation = round(base_value * _to_float(method_mult.get("peg"), 1.00), 2)
    evebitda_valuation = round(base_value * _to_float(method_mult.get("ev"), 1.02), 2)
    w_pe = _to_float(weights.get("pe"), 0.25)
    w_pb = _to_float(weights.get("pb"), 0.25)
    w_peg = _to_float(weights.get("peg"), 0.25)
    w_ev = _to_float(weights.get("ev"), 0.25)
    weight_sum = w_pe + w_pb + w_peg + w_ev
    if weight_sum <= 0:
        w_pe = w_pb = w_peg = w_ev = 0.25
        weight_sum = 1.0
    w_pe, w_pb, w_peg, w_ev = (w_pe / weight_sum, w_pb / weight_sum, w_peg / weight_sum, w_ev / weight_sum)
    avg_target = round(pe_valuation * w_pe + pb_valuation * w_pb + peg_valuation * w_peg + evebitda_valuation * w_ev, 2)

    data.update(
        {
            "base_growth": f"{profile.get('base_growth', 0.08) * 100:.1f}%",
            "bull_growth": f"{profile.get('bull_growth', 0.12) * 100:.1f}%",
            "bear_growth": f"{profile.get('bear_growth', 0.04) * 100:.1f}%",
            "base_terminal": f"{profile.get('base_terminal', 0.025) * 100:.1f}%",
            "bull_terminal": f"{profile.get('bull_terminal', 0.03) * 100:.1f}%",
            "bear_terminal": f"{profile.get('bear_terminal', 0.02) * 100:.1f}%",
            "wacc": f"{profile.get('wacc', 0.10) * 100:.1f}%",
            "base_dcf_value": round(base_value, 2),
            "bull_dcf_value": bull_value,
            "bear_dcf_value": bear_value,
            "base_margin": base_upside,
            "bull_margin": bull_upside,
            "bear_margin": bear_upside,
            "pe_valuation": pe_valuation,
            "pb_valuation": pb_valuation,
            "peg_valuation": peg_valuation,
            "evebitda_valuation": evebitda_valuation,
            "avg_target": avg_target,
            "pe_upside": _margin(pe_valuation),
            "pb_upside": _margin(pb_valuation),
            "peg_upside": _margin(peg_valuation),
            "evebitda_upside": _margin(evebitda_valuation),
            "avg_upside": _margin(avg_target),
            "pe_weight": f"{w_pe * 100:.0f}%",
            "pb_weight": f"{w_pb * 100:.0f}%",
            "peg_weight": f"{w_peg * 100:.0f}%",
            "ev_weight": f"{w_ev * 100:.0f}%",
            "valuation_profile_source": "industry_profile" if industry in INDUSTRY_VALUATION_PROFILE else "default_profile",
            "bull_target": bull_value,
            "base_target": round(base_value, 2),
            "bear_target": bear_value,
            "bull_upside": bull_upside,
            "base_upside": base_upside,
            "bear_upside": bear_upside,
            "bull_prob": "30%",
            "base_prob": "50%",
            "bear_prob": "20%",
            "valuation_conclusion": (
                f"基于{industry or '通用'}行业因子，基准估值 {base_value:.2f} 元，较当前价格潜在空间 {base_upside}；"
                f"乐观/悲观区间 {bear_value:.2f}-{bull_value:.2f} 元。"
            ),
        }
    )


def _apply_valuation_appendix_details(data: dict):
    """Fill appendix section B with model-level details."""
    current = _to_float(data.get("current_price"), 0.0)
    base_value = _to_float(data.get("base_dcf_value"), 0.0)
    bull_value = _to_float(data.get("bull_dcf_value"), 0.0)
    bear_value = _to_float(data.get("bear_dcf_value"), 0.0)
    wacc = data.get("wacc", "数据暂缺")
    base_growth = data.get("base_growth", "数据暂缺")
    bull_growth = data.get("bull_growth", "数据暂缺")
    bear_growth = data.get("bear_growth", "数据暂缺")
    base_terminal = data.get("base_terminal", "数据暂缺")
    bull_terminal = data.get("bull_terminal", "数据暂缺")
    bear_terminal = data.get("bear_terminal", "数据暂缺")
    fcf = data.get("free_cash_flow", "数据暂缺")

    dcf_lines = [
        "| 参数 | 基准情景 | 乐观情景 | 悲观情景 |",
        "|------|----------|----------|----------|",
        f"| 预测期增长率 | {base_growth} | {bull_growth} | {bear_growth} |",
        f"| 永续增长率 | {base_terminal} | {bull_terminal} | {bear_terminal} |",
        f"| 折现率(WACC) | {wacc} | {wacc} | {wacc} |",
        f"| 每股估值(元) | {base_value:.2f} | {bull_value:.2f} | {bear_value:.2f} |",
        f"| 当前股价(元) | {current:.2f} | {current:.2f} | {current:.2f} |",
        f"| 安全边际 | {data.get('base_margin', '数据暂缺')} | {data.get('bull_margin', '数据暂缺')} | {data.get('bear_margin', '数据暂缺')} |",
        "",
        f"计算口径说明：基于当前自由现金流（{fcf}）与三情景增长假设推导每股内在价值。",
    ]
    data["dcf_details"] = "\n".join(dcf_lines)

    pe_val = _to_float(data.get("pe_valuation"), 0.0)
    pb_val = _to_float(data.get("pb_valuation"), 0.0)
    peg_val = _to_float(data.get("peg_valuation"), 0.0)
    eve_val = _to_float(data.get("evebitda_valuation"), 0.0)
    avg_target = _to_float(data.get("avg_target"), 0.0)
    pe_ttm = _to_float(data.get("pe_ttm"), 0.0)
    pb = _to_float(data.get("pb"), 0.0)
    ps = _to_float(data.get("ps"), 0.0)
    ev_ebitda = _to_float(data.get("ev_ebitda"), 0.0)

    rel_lines = [
        "| 方法 | 当前倍数/口径 | 估值结果(元) | 当前价(元) | 潜在空间 | 权重 |",
        "|------|---------------|-------------|-----------|----------|------|",
        f"| PE Band | PE={pe_ttm:.2f} | {pe_val:.2f} | {current:.2f} | {data.get('pe_upside', '数据暂缺')} | {data.get('pe_weight', '25%')} |",
        f"| PB Band | PB={pb:.2f} | {pb_val:.2f} | {current:.2f} | {data.get('pb_upside', '数据暂缺')} | {data.get('pb_weight', '25%')} |",
        f"| PEG | PEG口径(PE/G) | {peg_val:.2f} | {current:.2f} | {data.get('peg_upside', '数据暂缺')} | {data.get('peg_weight', '25%')} |",
        f"| EV/EBITDA | EV/EBITDA={ev_ebitda:.2f} | {eve_val:.2f} | {current:.2f} | {data.get('evebitda_upside', '数据暂缺')} | {data.get('ev_weight', '25%')} |",
        "",
        f"校验项：PS={ps:.2f}，加权平均目标价={avg_target:.2f}元（对应潜在空间 {data.get('avg_upside', '数据暂缺')}）。",
        f"行业因子来源：{data.get('valuation_profile_source', 'default_profile')}；行业={data.get('industry', '待补充')}。",
    ]
    data["relative_valuation_details"] = "\n".join(rel_lines)


def fill_template_missing_fields(template_path: str, data: dict, default_value: str = "数据暂缺"):
    """Fill unresolved template variables with a neutral placeholder string."""
    try:
        if "/" in template_path or "\\" in template_path:
            path = Path(template_path)
        else:
            path = skill_dir / "templates" / template_path
        content = path.read_text(encoding="utf-8")
        placeholders = set(re.findall(r"\{\{(\w+)\}\}", content))
        for key in placeholders:
            if key not in data:
                data[key] = default_value
    except Exception:
        # Do not block report generation for template introspection errors.
        return


def get_quote_with_fallback(code: str):
    """Try EastMoney first, fallback to AKShare quote."""
    quote = get_realtime_quote(code)
    if isinstance(quote, dict) and "error" not in quote:
        return quote
    quote_ak = get_realtime_quote_ak(code)
    if isinstance(quote_ak, dict) and "error" not in quote_ak:
        return quote_ak
    return quote


def get_kline_with_fallback(code: str):
    """Try EastMoney daily kline first, fallback to AKShare daily kline."""
    kline_df = get_kline_daily(code, count=180)
    if kline_df is not None and not kline_df.empty:
        return kline_df
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y%m%d")
    kline_ak = get_kline_daily_ak(code, start_date=start_date, end_date=end_date)
    if kline_ak is not None and not kline_ak.empty:
        return kline_ak
    return kline_df


def _df_has_meaningful_value(df, columns: list) -> bool:
    if df is None or df.empty:
        return False
    existing = [c for c in columns if c in df.columns]
    if not existing:
        return False
    for col in existing:
        series = df[col].dropna()
        if series.empty:
            continue
        for v in series.head(20):
            if _to_float(v, 0.0) != 0.0:
                return True
    return False


def _load_local_financial_fixture(code: str) -> dict:
    """Load local financial fixture for offline/regression testing."""
    if not LOCAL_FIXTURE_PATH.exists():
        return {}
    try:
        payload = json.loads(LOCAL_FIXTURE_PATH.read_text(encoding="utf-8"))
        data = payload.get("stocks", {}).get(code, {})
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def _build_fixture_df(code: str, section: str):
    fixture = _load_local_financial_fixture(code)
    rows = fixture.get(section, [])
    if not rows:
        return None
    try:
        df = pd.DataFrame(rows)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def get_income_with_fallback(
    code: str,
    count: int = 4,
    use_local_fixture: bool = False,
    force_live_on_empty_cache: bool = False,
):
    """Try EastMoney income statement first, fallback to AKShare."""
    income_df = get_income_statement(code, count=count)
    if _df_has_meaningful_value(
        income_df,
        ["营业总收入", "营业收入", "TOTAL_OPERATE_INCOME", "归母净利润", "PARENT_NETPROFIT"],
    ):
        return income_df

    # Optional: bypass cache once when empty/invalid to avoid stale empty cache entries.
    if force_live_on_empty_cache:
        try:
            income_live = get_income_statement.__wrapped__(code, count=count)
            if _df_has_meaningful_value(
                income_live,
                ["营业总收入", "营业收入", "TOTAL_OPERATE_INCOME", "归母净利润", "PARENT_NETPROFIT"],
            ):
                return income_live
        except Exception:
            pass

    income_ak = get_income_statement_ak(code, count=count)
    if income_ak is not None and not income_ak.empty:
        return income_ak

    if force_live_on_empty_cache:
        try:
            income_ak_live = get_income_statement_ak.__wrapped__(code, count=count)
            if income_ak_live is not None and not income_ak_live.empty:
                return income_ak_live
        except Exception:
            pass

    if use_local_fixture:
        income_local = _build_fixture_df(code, "income_statement")
        if income_local is not None and not income_local.empty:
            return income_local.head(count)
    return income_df


def get_balance_with_fallback(
    code: str,
    count: int = 4,
    use_local_fixture: bool = False,
    force_live_on_empty_cache: bool = False,
):
    """Try EastMoney balance sheet first, fallback to AKShare."""
    balance_df = get_balance_sheet(code, count=count)
    if _df_has_meaningful_value(
        balance_df,
        ["资产总计", "负债合计", "TOTAL_ASSETS", "TOTAL_LIABILITIES"],
    ):
        return balance_df

    # Optional: bypass cache once when empty/invalid to avoid stale empty cache entries.
    if force_live_on_empty_cache:
        try:
            balance_live = get_balance_sheet.__wrapped__(code, count=count)
            if _df_has_meaningful_value(
                balance_live,
                ["资产总计", "负债合计", "TOTAL_ASSETS", "TOTAL_LIABILITIES"],
            ):
                return balance_live
        except Exception:
            pass

    balance_ak = get_balance_sheet_ak(code, count=count)
    if balance_ak is not None and not balance_ak.empty:
        return balance_ak

    if force_live_on_empty_cache:
        try:
            balance_ak_live = get_balance_sheet_ak.__wrapped__(code, count=count)
            if balance_ak_live is not None and not balance_ak_live.empty:
                return balance_ak_live
        except Exception:
            pass

    if use_local_fixture:
        balance_local = _build_fixture_df(code, "balance_sheet")
        if balance_local is not None and not balance_local.empty:
            return balance_local.head(count)
    return balance_df


def get_cash_with_fallback(
    code: str,
    count: int = 4,
    use_local_fixture: bool = False,
    force_live_on_empty_cache: bool = False,
):
    """Try EastMoney cash flow first, fallback to AKShare."""
    cash_df = get_cash_flow(code, count=count)
    if _df_has_meaningful_value(
        cash_df,
        ["经营活动产生的现金流量净额", "经营活动产生的现金流量", "NETCASH_OPERATE"],
    ):
        return cash_df

    # Optional: bypass cache once when empty/invalid to avoid stale empty cache entries.
    if force_live_on_empty_cache:
        try:
            cash_live = get_cash_flow.__wrapped__(code, count=count)
            if _df_has_meaningful_value(
                cash_live,
                ["经营活动产生的现金流量净额", "经营活动产生的现金流量", "NETCASH_OPERATE"],
            ):
                return cash_live
        except Exception:
            pass

    cash_ak = get_cash_flow_ak(code, count=count)
    if cash_ak is not None and not cash_ak.empty:
        return cash_ak

    if force_live_on_empty_cache:
        try:
            cash_ak_live = get_cash_flow_ak.__wrapped__(code, count=count)
            if cash_ak_live is not None and not cash_ak_live.empty:
                return cash_ak_live
        except Exception:
            pass

    if use_local_fixture:
        cash_local = _build_fixture_df(code, "cash_flow")
        if cash_local is not None and not cash_local.empty:
            return cash_local.head(count)
    return cash_df


def generate_stock_report(
    code: str,
    name: str,
    use_local_fin_fixture: bool = False,
    force_live_on_empty_cache: bool = False,
):
    """生成个股分析报告"""
    if name is None:
        name = f"股票{code}"
    thesis = get_stock_thesis(name)
    
    # 示例数据 - 实际使用时从API获取
    data = {
        'stock_code': code,
        'stock_name': name,
        'company_full_name': name,
        'report_date': datetime.datetime.now().strftime('%Y年%m月%d日'),
        'current_price': 1850.00,
        'pe_ttm': 35.2,
        'pb': 11.5,
        'roe': 30.5,
        'dividend_yield': 1.5,
        'market_cap': '23,200亿元',
        'profit_growth': '+12.5%',
        'sales_growth': '+8.2%',
        'investment_rating': '买入',
        'target_price': 2200.00,
        'upside_potential': '+18.9%',
        'risk_level': '中等风险',
        'bullish_point_1': thesis['bullish'][0],
        'bullish_point_2': thesis['bullish'][1],
        'bullish_point_3': thesis['bullish'][2],
        'bearish_point_1': thesis['bearish'][0],
        'bearish_point_2': thesis['bearish'][1],
        'bearish_point_3': thesis['bearish'][2],
        'catalysts': thesis['catalysts'],
        'risk_description': thesis['risk_description'],
        'data_period': '2025年12月-2026年2月',
        'industry': '待补充',
        'sub_industry': '待补充'
    }
    data["short_cycle_desc"] = "日线(5/10/20日均线)"
    data["medium_cycle_desc"] = "周线近似(20/60日均线≈4/12周)"
    data["long_cycle_desc"] = "月线近似(120/250日均线≈6/12月)"
    data["bullish_thesis"] = "；".join(thesis["bullish"])
    data["bearish_risks"] = "；".join(thesis["bearish"])
    data["rating_description"] = "基于估值、波动与风险平衡"

    # Try realtime quote first; fallback to built-in demo values.
    quote = get_quote_with_fallback(code)
    if isinstance(quote, dict) and "error" not in quote:
        _apply_realtime_to_stock_data(data, quote)
        data["data_period"] = f"截至 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
    _apply_sw_industry_classification(data, code, name, quote if isinstance(quote, dict) else {})
    kline_df = get_kline_with_fallback(code)
    _apply_kline_to_stock_data(data, kline_df)
    fund_flow = get_fund_flow(code)
    _apply_fund_flow_to_stock_data(data, fund_flow)
    income_df = get_income_with_fallback(
        code,
        count=4,
        use_local_fixture=use_local_fin_fixture,
        force_live_on_empty_cache=force_live_on_empty_cache,
    )
    _apply_income_statement_to_stock_data(data, income_df)
    balance_df = get_balance_with_fallback(
        code,
        count=4,
        use_local_fixture=use_local_fin_fixture,
        force_live_on_empty_cache=force_live_on_empty_cache,
    )
    _apply_balance_sheet_to_stock_data(data, balance_df)
    cash_df = get_cash_with_fallback(
        code,
        count=4,
        use_local_fixture=use_local_fin_fixture,
        force_live_on_empty_cache=force_live_on_empty_cache,
    )
    _apply_cash_flow_to_stock_data(data, cash_df)
    _apply_profitability_trends(data, income_df, balance_df)
    _apply_financial_skill_to_stock_data(data, income_df, balance_df, cash_df)
    _apply_strategy_rules(data)
    _apply_valuation_rules(data)
    _apply_valuation_appendix_details(data)

    data["overall_rating"] = data.get("investment_rating", "中性")
    data["overall_confidence"] = "中等"
    data["fundamental_rating"] = "中性"
    data["fundamental_confidence"] = "中等"
    data["valuation_rating"] = "中性"
    data["valuation_confidence"] = "中等"
    data["technical_rating"] = "中性偏多" if data.get("short_trend") == "上升" else "中性"
    data["technical_confidence"] = "中等"
    data.setdefault("short_term_action", "回调分批关注")
    data.setdefault("medium_term_action", "跟踪基本面与估值变化")
    data.setdefault("long_term_action", "依据盈利兑现情况动态评估")

    return data


def generate_index_report(code: str, name: str):
    """生成指数分析报告"""
    if name is None:
        name = f"指数{code}"
    
    data = {
        'index_code': code,
        'index_name': name,
        'report_date': datetime.datetime.now().strftime('%Y年%m月%d日'),
        'current_level': 3800.00,
        'level_change': '+1.25%',
        'pe_ttm': 7.5,
        'pb': 0.8,
        'dividend_yield': 5.2,
        'risk_premium': 6.8,
        'investment_rating': '买入',
        'target_price': 4200.00,
        'upside_potential': '+10.5%',
        'risk_level': '低风险',
        'bullish_point_1': '高股息率提供安全垫',
        'bullish_point_2': '估值处于历史低位',
        'bullish_point_3': '市场情绪逐步改善',
        'bearish_point_1': '经济复苏预期存在不确定性',
        'bearish_point_2': '行业集中度风险',
        'bearish_point_3': '国际市场波动影响',
        'catalysts': '政策支持、经济复苏、企业分红',
        'risk_description': '安全边际较高',
        'data_period': '2025年12月-2026年2月'
    }
    
    return data


def generate_sector_report(code: str, name: str):
    """生成行业分析报告"""
    if name is None:
        name = f"行业{code}"
    
    data = {
        'sector_code': code,
        'sector_name': name,
        'report_date': datetime.datetime.now().strftime('%Y年%m月%d日'),
        'current_level': 1250.00,
        'pe_ttm': 22.5,
        'pb': 1.8,
        'roe': 8.5,
        'dividend_yield': 2.8,
        'investment_rating': '持有',
        'target_price': 1400.00,
        'upside_potential': '+12.0%',
        'risk_level': '中等风险',
        'bullish_point_1': '新能源行业政策支持',
        'bullish_point_2': '技术进步降低成本',
        'bullish_point_3': '全球能源转型趋势',
        'bearish_point_1': '市场竞争加剧',
        'bearish_point_2': '原材料价格波动',
        'bearish_point_3': '补贴政策退坡',
        'catalysts': '政策出台、技术突破、需求增长',
        'risk_description': '市场风险、政策风险',
        'data_period': '2025年12月-2026年2月'
    }
    
    return data


def get_report_preview(report_content: str, max_lines: int = 3):
    """Return a safe preview list without raising on short content."""
    lines = report_content.splitlines()
    return lines[:max_lines]


def optimize_markdown_content(content: str, aggressive: bool = False) -> str:
    """Reduce placeholder noise while keeping report structure.

    By default, preserve section/table structure and only remove obvious placeholder
    lines. Use aggressive=True when compact output is explicitly required.
    """
    kept = []
    for line in content.splitlines():
        stripped = line.strip()

        # Remove placeholder-only paragraphs/lists.
        if stripped in {"数据暂缺", "- 数据暂缺", "* 数据暂缺"}:
            continue
        if ">" in stripped and stripped.replace(">", "").strip() == "数据暂缺":
            continue

        # Remove table rows where every value cell is placeholder.
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if cells:
                # Keep table headers/separators.
                if all(set(c) <= {"-", ":"} for c in cells):
                    kept.append(line)
                    continue
                if "指标" in cells[0] or "项目" in cells[0] or "维度" in cells[0] or "方法" in cells[0]:
                    kept.append(line)
                    continue
                if all(c in {"数据暂缺", "N/A", ""} for c in cells[1:]):
                    continue

        # Remove checklist placeholders.
        if stripped.startswith("- [ ]") and "数据暂缺" in stripped:
            continue

        kept.append(line)

    if not aggressive:
        # Keep full structure for complete report output.
        table_cleaned = kept
    else:
        # Remove empty markdown tables (header + separator only).
        table_cleaned = []
        i = 0
        while i < len(kept):
            line = kept[i]
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                block = [line]
                j = i + 1
                while j < len(kept):
                    s = kept[j].strip()
                    if s.startswith("|") and s.endswith("|"):
                        block.append(kept[j])
                        j += 1
                        continue
                    break
                # Keep table block only if it has actual data rows beyond header/separator.
                has_data_row = False
                for row in block[2:]:
                    cells = [c.strip() for c in row.strip().split("|")[1:-1]]
                    if any(c not in {"", "数据暂缺", "N/A"} for c in cells):
                        has_data_row = True
                        break
                if len(block) >= 2 and not has_data_row:
                    i = j
                    continue
                table_cleaned.extend(block)
                i = j
                continue
            table_cleaned.append(line)
            i += 1

    # Drop empty sections (headings with no meaningful content).
    def _is_heading(text: str) -> bool:
        return bool(re.match(r"^#{1,6}\s+", text.strip()))

    def _is_meaningful(text: str) -> bool:
        s = text.strip()
        if not s:
            return False
        if _is_heading(s):
            return False
        if s in {"---", "***"}:
            return False
        if s.startswith("|") and s.endswith("|"):
            return False
        if s in {"数据暂缺", "N/A"}:
            return False
        return True

    if not aggressive:
        section_pruned = table_cleaned
    else:
        section_pruned = []
        i = 0
        while i < len(table_cleaned):
            line = table_cleaned[i]
            if _is_heading(line):
                # Keep top-level title always.
                if line.strip().startswith("# "):
                    section_pruned.append(line)
                    i += 1
                    continue
                j = i + 1
                block = [line]
                while j < len(table_cleaned) and not _is_heading(table_cleaned[j]):
                    block.append(table_cleaned[j])
                    j += 1
                if any(_is_meaningful(x) for x in block[1:]):
                    section_pruned.extend(block)
                i = j
                continue
            section_pruned.append(line)
            i += 1

    # Compress excessive blank lines.
    result_lines = []
    blank_count = 0
    for line in section_pruned:
        if line.strip() == "":
            blank_count += 1
            if blank_count > 1:
                continue
        else:
            blank_count = 0
        result_lines.append(line)
    return "\n".join(result_lines).strip() + "\n"


def _rule_narrative(report_type: str, data: dict) -> str:
    name = data.get("stock_name") or data.get("index_name") or data.get("sector_name") or "标的"
    rating = data.get("investment_rating", "中性")
    risk = data.get("risk_level", "中等风险")
    upside = data.get("upside_potential", "数据暂缺")
    short_trend = data.get("short_trend", "震荡")
    val = data.get("valuation_conclusion", "估值区间需结合后续财报验证。")
    growth = data.get("growth_analysis", "财务趋势需持续跟踪。")
    action = data.get("short_term_action", "控制仓位，观察信号。")
    return (
        f"- 标的 `{name}` 当前综合评级为 **{rating}**，风险等级为 **{risk}**，预期空间 {upside}。\n"
        f"- 技术面短周期处于 **{short_trend}** 阶段，短期策略建议：{action}。\n"
        f"- 财务与估值观察：{growth} {val}\n"
        "- 结论：建议结合仓位纪律与止损规则，按计划分批执行，不追涨。"
    )


def _agent_narrative(provided_text: str = None, narrative_file: str = None) -> str:
    if provided_text and provided_text.strip():
        return provided_text.strip()
    if narrative_file:
        path = Path(narrative_file)
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                return text
    env_text = os.getenv("AGENT_NARRATIVE_TEXT", "").strip()
    if env_text:
        return env_text
    raise RuntimeError("agent narrative text not provided")


def build_narrative_block(
    report_type: str,
    data: dict,
    mode: str = "rule",
    narrative_text: str = None,
    narrative_file: str = None,
):
    rule_text = _rule_narrative(report_type, data)
    if mode == "rule":
        content = "### 规则点评\n" + rule_text
        return content, "rule"

    try:
        llm_text = _agent_narrative(provided_text=narrative_text, narrative_file=narrative_file)
    except Exception:
        if mode == "agent":
            content = "### 规则点评（Agent点评未注入，已回退）\n" + rule_text
            return content, "agent_fallback_rule"
        content = "### 规则点评\n" + rule_text
        return content, "hybrid_fallback_rule"

    if mode == "agent":
        return "### Agent点评\n" + llm_text, "agent"

    content = "### 规则点评\n" + rule_text + "\n\n### Agent点评\n" + llm_text
    return content, "hybrid"


def append_narrative_section(
    markdown_content: str,
    report_type: str,
    data: dict,
    mode: str,
    narrative_text: str = None,
    narrative_file: str = None,
) -> str:
    section, source = build_narrative_block(
        report_type,
        data,
        mode=mode,
        narrative_text=narrative_text,
        narrative_file=narrative_file,
    )
    data["narrative_source"] = source
    tail = (
        "\n---\n\n"
        "## 🧠 大模型点评 (Narrative)\n\n"
        f"> 生成模式: `{mode}`  \n"
        f"> 实际来源: `{source}`\n\n"
        f"{section}\n"
    )
    return markdown_content.rstrip() + "\n" + tail


def get_default_output_file(args, report_data):
    """Build deterministic output file by format and entity."""
    now = datetime.datetime.now().strftime('%Y%m%d')
    entity_name = (
        args.name
        or report_data.get('stock_name')
        or report_data.get('index_name')
        or report_data.get('sector_name')
        or args.type
    )
    suffix = "html" if args.format == "html" else "md"
    return f"{entity_name}_{args.code}_{now}.{suffix}"


def main():
    """主函数"""
    args = parse_args()
    
    try:
        print(f"📊 Generating {args.type} analysis report for {args.code}...")
        if args.use_local_fin_fixture:
            print("🧪 Local financial fixture fallback: ENABLED (testing mode)")
        if args.force_live_on_empty_cache:
            print("🔄 Empty-cache live re-fetch: ENABLED")
        
        # 确定报告生成器
        if args.type == 'stock':
            report_data = generate_stock_report(
                args.code,
                args.name,
                use_local_fin_fixture=args.use_local_fin_fixture,
                force_live_on_empty_cache=args.force_live_on_empty_cache,
            )
        elif args.type == 'index':
            report_data = generate_index_report(
                args.code, args.name
            )
        else:  # sector
            report_data = generate_sector_report(
                args.code, args.name
            )
        
        # 渲染报告
        if args.format == 'html':
            print("📝 Rendering HTML web report...")
            if args.template:
                template_path = args.template
            else:
                template_path = get_default_template(args.type)
            fill_template_missing_fields(template_path, report_data)
            markdown_content = render_template(template_path, report_data)
            markdown_content = optimize_markdown_content(markdown_content)
            markdown_content = append_narrative_section(
                markdown_content,
                report_type=args.type,
                data=report_data,
                mode=args.narrative_mode,
                narrative_text=args.narrative_text,
                narrative_file=args.narrative_file,
            )
            report_content = render_web_report(
                args.type, report_data, full_markdown=markdown_content
            )
        else:
            if args.template:
                template_path = args.template
            else:
                template_path = get_default_template(args.type)
            print(f"📝 Using template: {template_path}")
            fill_template_missing_fields(template_path, report_data)
            report_content = render_template(template_path, report_data)
            report_content = optimize_markdown_content(report_content)
            report_content = append_narrative_section(
                report_content,
                report_type=args.type,
                data=report_data,
                mode=args.narrative_mode,
                narrative_text=args.narrative_text,
                narrative_file=args.narrative_file,
            )
        
        # 确定输出文件
        if args.output:
            output_file = args.output
        else:
            output_file = get_default_output_file(args, report_data)
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✅ Report saved to: {output_file}")
        print("📖 Report preview (first 3 lines):")
        print("=" * 50)
        for line in get_report_preview(report_content, 3):
            print(line)
        print("=" * 50)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
