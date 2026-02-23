#!/usr/bin/env python3
"""
AKShare API for A-Share Market Data
AKShare A股数据获取API

Features:
- Real-time stock quotes (实时行情)
- K-line data (K线数据)
- Financial statements (财务报表)
- Technical indicators (技术指标)
- Valuation metrics (估值指标)
- Fund flow data (资金流向)
- North bound flow (北向资金)
- Industry/Sector data (行业板块)

Author: AI Assistant
Date: 2026-02-19
"""

import json
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
import logging

# Import data manager
from data_manager import get_data_manager, cached

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("AKShare imported successfully")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("AKShare not available. Please install: pip install akshare")

# Data Manager instance
_data_manager = None

def get_dm():
    """Get or create data manager instance"""
    global _data_manager
    if _data_manager is None:
        _data_manager = get_data_manager(cache_dir="./cache/akshare")
    return _data_manager

def check_akshare():
    """Check if AKShare is available"""
    if not AKSHARE_AVAILABLE:
        return {
            "error": "AKShare not available. Please install: pip install akshare",
            "status": "unavailable"
        }
    return {"status": "available"}

# ==================== Real-time Data APIs ====================

@cached(data_type="realtime_quote", ttl=60)
def get_realtime_quote(stock_code: str) -> Dict:
    """
    Get real-time stock quote using AKShare
    获取实时行情数据
    
    Args:
        stock_code: Stock code (e.g., "600519")
    
    Returns:
        Dictionary with real-time quote data
    """
    if not AKSHARE_AVAILABLE:
        return {"error": "AKShare not available"}
    
    try:
        # Use AKShare to get real-time quote
        # Determine market
        if stock_code.startswith(('60', '68', '90')):
            # Shanghai
            df = ak.stock_sh_a_spot_em()
            prefix = "sh"
        elif stock_code.startswith(('00', '30', '20')):
            # Shenzhen
            df = ak.stock_sz_a_spot_em()
            prefix = "sz"
        else:
            # Try both
            try:
                df = ak.stock_sh_a_spot_em()
                prefix = "sh"
            except:
                df = ak.stock_sz_a_spot_em()
                prefix = "sz"
        
        # Find the stock
        stock_row = df[df['代码'] == stock_code]
        
        if stock_row.empty:
            return {"error": f"Stock {stock_code} not found"}
        
        # Extract data
        row = stock_row.iloc[0]
        
        quote_data = {
            "股票代码": stock_code,
            "股票名称": row.get('名称', ''),
            "最新价": float(row.get('最新价', 0)),
            "涨跌额": float(row.get('涨跌额', 0)),
            "涨跌幅": float(row.get('涨跌幅', 0)),
            "成交量(手)": float(row.get('成交量', 0)),
            "成交额(万)": float(row.get('成交额', 0)) / 10000,
            "振幅": float(row.get('振幅', 0)),
            "最高价": float(row.get('最高', 0)),
            "最低价": float(row.get('最低', 0)),
            "今开": float(row.get('今开', 0)),
            "昨收": float(row.get('昨收', 0)),
            "总市值(亿)": float(row.get('总市值', 0)) / 100000000,
            "流通市值(亿)": float(row.get('流通市值', 0)) / 100000000,
            "换手率": float(row.get('换手率', 0)),
            "市盈率(动)": float(row.get('市盈率-动态', 0)) if row.get('市盈率-动态') else None,
            "市净率": float(row.get('市净率', 0)) if row.get('市净率') else None,
            "60日涨跌幅": float(row.get('60日涨跌幅', 0)) if row.get('60日涨跌幅') else None,
            "年初至今涨跌幅": float(row.get('年初至今涨跌幅', 0)) if row.get('年初至今涨跌幅') else None,
        }
        
        return quote_data
        
    except Exception as e:
        logger.error(f"Failed to get realtime quote: {e}")
        return {"error": f"Failed to get realtime quote: {str(e)}"}

# ==================== K-line Data APIs ====================

@cached(data_type="kline_daily", ttl=300)
def get_kline_daily(stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Get daily K-line data using AKShare
    获取日K线数据
    
    Args:
        stock_code: Stock code (e.g., "600519")
        start_date: Start date (YYYYMMDD), default is 1 year ago
        end_date: End date (YYYYMMDD), default is today
    
    Returns:
        DataFrame with OHLCV data
    """
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    
    try:
        # Set default dates
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
        # Use AKShare to get K-line data
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        
        # Rename columns to match our format
        df = df.rename(columns={
            '日期': '日期',
            '开盘': '开盘',
            '收盘': '收盘',
            '最高': '最高',
            '最低': '最低',
            '成交量': '成交量',
            '成交额': '成交额',
            '振幅': '振幅',
            '涨跌幅': '涨跌幅',
            '涨跌额': '涨跌额',
            '换手率': '换手率'
        })
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to get kline data: {e}")
        return pd.DataFrame()

@cached(data_type="kline_weekly", ttl=1800)
def get_kline_weekly(stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """Get weekly K-line data"""
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    
    try:
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=730)).strftime('%Y%m%d')
        
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="weekly",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to get weekly kline: {e}")
        return pd.DataFrame()

@cached(data_type="kline_monthly", ttl=3600)
def get_kline_monthly(stock_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """Get monthly K-line data"""
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    
    try:
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=1825)).strftime('%Y%m%d')
        
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="monthly",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to get monthly kline: {e}")
        return pd.DataFrame()

# ==================== North Bound Flow APIs ====================

@cached(data_type="north_bound_flow", ttl=300)
def get_north_bound_flow() -> pd.DataFrame:
    """
    Get north bound capital flow (北向资金流向)
    获取北向资金流向
    
    Returns:
        DataFrame with north bound flow data
    """
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    
    try:
        # Use AKShare to get north bound flow
        df = ak.stock_hsgt_hist_em(symbol="北上资金")
        return df
    except Exception as e:
        logger.error(f"Failed to get north bound flow: {e}")
        return pd.DataFrame()

@cached(data_type="north_bound_top10", ttl=300)
def get_north_bound_top10() -> pd.DataFrame:
    """
    Get top 10 stocks by north bound capital
    获取北向资金持仓Top10
    
    Returns:
        DataFrame with top 10 stocks
    """
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    
    try:
        # Use AKShare to get top 10
        df = ak.stock_hsgt_hold_stock_em()
        return df.head(10)
    except Exception as e:
        logger.error(f"Failed to get north bound top10: {e}")
        return pd.DataFrame()


@cached(data_type="dragon_tiger", ttl=1800)
def get_dragon_tiger_dates(stock_code: str) -> pd.DataFrame:
    """Get historical dragon-tiger list dates for a stock."""
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    try:
        df = ak.stock_lhb_stock_detail_date_em(symbol=str(stock_code))
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        logger.error(f"Failed to get dragon tiger dates: {e}")
        return pd.DataFrame()


@cached(data_type="block_trade", ttl=1800)
def get_block_trade_records(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Get block trade records for a stock within date range."""
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    try:
        # AKShare returns full-market records; filter by stock code afterwards.
        df = ak.stock_dzjy_mrmx(symbol="A股", start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            return pd.DataFrame()
        code = str(stock_code).zfill(6)
        if "证券代码" not in df.columns:
            return pd.DataFrame()
        out = df[df["证券代码"].astype(str).str.zfill(6) == code].copy()
        if out.empty:
            return pd.DataFrame()
        return out.reset_index(drop=True)
    except Exception as e:
        logger.error(f"Failed to get block trade records: {e}")
        return pd.DataFrame()


@cached(data_type="research_reports", ttl=1800)
def get_research_reports(stock_code: str) -> pd.DataFrame:
    """Get research reports for a stock."""
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    try:
        df = ak.stock_research_report_em(symbol=str(stock_code))
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        logger.error(f"Failed to get research reports: {e}")
        return pd.DataFrame()


@cached(data_type="institute_hold", ttl=21600)
def get_institute_hold_by_period(period: str) -> pd.DataFrame:
    """Get institutional holding table by report period, e.g. 20253."""
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    try:
        df = ak.stock_institute_hold(symbol=str(period))
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        logger.error(f"Failed to get institute hold by period: {e}")
        return pd.DataFrame()


@cached(data_type="notice_report", ttl=1800)
def get_notice_report_by_date(date: str) -> pd.DataFrame:
    """Get notice report table by date, format YYYYMMDD."""
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    try:
        df = ak.stock_notice_report(symbol="全部", date=str(date))
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        # Some dates may return schema-incompatible payloads; treat as empty.
        logger.debug(f"Notice report unavailable for {date}: {e}")
        return pd.DataFrame()


@cached(data_type="dividend_detail", ttl=86400)
def get_dividend_detail(stock_code: str) -> pd.DataFrame:
    """Get historical dividend detail for a stock."""
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    try:
        df = ak.stock_history_dividend_detail(symbol=str(stock_code), indicator="分红")
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        logger.debug(f"Dividend detail unavailable for {stock_code}: {e}")
        return pd.DataFrame()

# ==================== Industry/Sector APIs ====================

# ==================== Financial Statement APIs ====================

def _to_sina_symbol(stock_code: str) -> str:
    """Convert 6-digit code to sina symbol format, e.g. 600519 -> sh600519."""
    code = str(stock_code).strip()
    if code.startswith(("5", "6", "9", "11")):
        return f"sh{code}"
    return f"sz{code}"


def _to_em_symbol(stock_code: str) -> str:
    """Convert 6-digit code to EastMoney symbol format, e.g. 600519 -> SH600519."""
    code = str(stock_code).strip()
    if code.startswith(("5", "6", "9", "11")):
        return f"SH{code}"
    return f"SZ{code}"


@cached(data_type="financial_statements", ttl=86400)
def get_income_statement(stock_code: str, count: int = 5) -> pd.DataFrame:
    """Get income statement (利润表) via AKShare/Sina."""
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    try:
        # Source A: Sina financial report
        df = ak.stock_financial_report_sina(
            stock=_to_sina_symbol(stock_code), symbol="利润表"
        )
        if df is not None and not df.empty:
            if "报告日" in df.columns:
                df = df.sort_values("报告日", ascending=False)
            return df.head(count).reset_index(drop=True)

        # Source B: EastMoney report API via AKShare
        # This source is usually available for large-cap symbols such as 600941.
        df_em = ak.stock_profit_sheet_by_report_em(symbol=_to_em_symbol(stock_code))
        if df_em is not None and not df_em.empty:
            if "REPORT_DATE" in df_em.columns:
                df_em = df_em.sort_values("REPORT_DATE", ascending=False)
            return df_em.head(count).reset_index(drop=True)

        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Failed to get income statement via AKShare: {e}")
        return pd.DataFrame()


@cached(data_type="financial_statements", ttl=86400)
def get_balance_sheet(stock_code: str, count: int = 5) -> pd.DataFrame:
    """Get balance sheet (资产负债表) via AKShare with Sina + EastMoney fallback."""
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    try:
        # Source A: Sina financial report
        df = ak.stock_financial_report_sina(
            stock=_to_sina_symbol(stock_code), symbol="资产负债表"
        )
        if df is not None and not df.empty:
            if "报告日" in df.columns:
                df = df.sort_values("报告日", ascending=False)
            return df.head(count).reset_index(drop=True)

        # Source B: EastMoney report API via AKShare
        df_em = ak.stock_balance_sheet_by_report_em(symbol=_to_em_symbol(stock_code))
        if df_em is not None and not df_em.empty:
            if "REPORT_DATE" in df_em.columns:
                df_em = df_em.sort_values("REPORT_DATE", ascending=False)
            return df_em.head(count).reset_index(drop=True)

        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Failed to get balance sheet via AKShare: {e}")
        return pd.DataFrame()


@cached(data_type="financial_statements", ttl=86400)
def get_cash_flow(stock_code: str, count: int = 5) -> pd.DataFrame:
    """Get cash flow statement (现金流量表) via AKShare with Sina + EastMoney fallback."""
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    try:
        # Source A: Sina financial report
        df = ak.stock_financial_report_sina(
            stock=_to_sina_symbol(stock_code), symbol="现金流量表"
        )
        if df is not None and not df.empty:
            if "报告日" in df.columns:
                df = df.sort_values("报告日", ascending=False)
            return df.head(count).reset_index(drop=True)

        # Source B: EastMoney report API via AKShare
        df_em = ak.stock_cash_flow_sheet_by_report_em(symbol=_to_em_symbol(stock_code))
        if df_em is not None and not df_em.empty:
            if "REPORT_DATE" in df_em.columns:
                df_em = df_em.sort_values("REPORT_DATE", ascending=False)
            return df_em.head(count).reset_index(drop=True)

        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Failed to get cash flow via AKShare: {e}")
        return pd.DataFrame()

@cached(data_type="industry_list", ttl=3600)
def get_industry_list() -> pd.DataFrame:
    """
    Get industry sector list
    获取行业板块列表
    
    Returns:
        DataFrame with industry list
    """
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    
    try:
        df = ak.stock_board_industry_name_em()
        return df
    except Exception as e:
        logger.error(f"Failed to get industry list: {e}")
        return pd.DataFrame()

@cached(data_type="industry_stocks", ttl=1800)
def get_industry_stocks(industry_name: str) -> pd.DataFrame:
    """
    Get stocks in an industry sector
    获取行业板块成分股
    
    Args:
        industry_name: Industry name (e.g., "银行")
    
    Returns:
        DataFrame with stocks in the industry
    """
    if not AKSHARE_AVAILABLE:
        return pd.DataFrame()
    
    try:
        df = ak.stock_board_industry_cons_em(symbol=industry_name)
        return df
    except Exception as e:
        logger.error(f"Failed to get industry stocks: {e}")
        return pd.DataFrame()


@cached(data_type="search_data", ttl=86400, identifier_param="stock_code")
def get_sw_level1_industry(stock_code: str) -> Dict:
    """
    Get Shenwan level-1 industry for a stock code.
    获取股票对应的申万一级行业

    Notes:
    - Implementation scans level-1 SW index constituents and finds the stock.
    - Result is cached to reduce repeated remote calls.
    """
    if not AKSHARE_AVAILABLE:
        return {}

    try:
        first_df = ak.sw_index_first_info()
        if first_df is None or first_df.empty:
            return {}

        code_str = str(stock_code).zfill(6)
        for _, row in first_df.iterrows():
            idx_code = str(row.get("行业代码", "")).split(".")[0]
            if not idx_code:
                continue
            try:
                cons_df = ak.index_component_sw(symbol=idx_code)
            except Exception:
                continue
            if cons_df is None or cons_df.empty or "证券代码" not in cons_df.columns:
                continue
            match = cons_df[cons_df["证券代码"].astype(str).str.zfill(6) == code_str]
            if match.empty:
                continue

            stock_name = ""
            if "证券名称" in match.columns:
                stock_name = str(match.iloc[0].get("证券名称", "")).strip()
            return {
                "stock_code": code_str,
                "stock_name": stock_name,
                "industry_level1": str(row.get("行业名称", "")).strip(),
                "sw_index_code": idx_code,
                "source": "sw_index_first_info+index_component_sw",
            }

        return {}
    except Exception as e:
        logger.error(f"Failed to get SW level-1 industry for {stock_code}: {e}")
        return {}

# ==================== Main Test Function ====================

if __name__ == "__main__":
    # Test the API
    print("="*60)
    print("AKShare API Test")
    print("="*60)
    
    # Check AKShare availability
    check = check_akshare()
    if check['status'] != 'available':
        print(f"\n❌ {check['error']}")
        print("\nPlease install AKShare:")
        print("  pip install akshare -i https://pypi.org/simple/")
        sys.exit(1)
    
    print("\n✅ AKShare is available!")
    
    # Test with PetroChina (中国石油)
    stock_code = "601857"
    print(f"\n{'='*60}")
    print(f"Testing with: {stock_code} (中国石油)")
    print(f"{'='*60}\n")
    
    # Test 1: Real-time quote
    print("1. Real-time Quote:")
    print("-" * 40)
    quote = get_realtime_quote(stock_code)
    if 'error' in quote:
        print(f"   ❌ Error: {quote['error']}")
    else:
        print(f"   股票名称: {quote.get('股票名称', 'N/A')}")
        print(f"   最新价: ¥{quote.get('最新价', 0):.2f}")
        print(f"   涨跌幅: {quote.get('涨跌幅', 0):.2f}%")
        print(f"   成交量: {quote.get('成交量(手)', 0):,.0f}手")
        print(f"   成交额: ¥{quote.get('成交额(万)', 0):,.2f}万")
        print(f"   换手率: {quote.get('换手率', 0):.2f}%")
        print(f"   市盈率: {quote.get('市盈率(动)', 'N/A')}")
        print(f"   总市值: ¥{quote.get('总市值(亿)', 0):,.2f}亿")
    
    # Test 2: K-line data
    print(f"\n2. Daily K-line (last 5 days):")
    print("-" * 40)
    kline = get_kline_daily(stock_code)
    if kline.empty:
        print("   ❌ No data")
    else:
        for idx, row in kline.iterrows():
            print(f"   {row['日期']}: 收¥{row['收盘']:.2f} 涨{row['涨跌幅']:.2f}%")
    
    # Test 3: North bound flow
    print(f"\n3. North Bound Capital Flow (Top 5):")
    print("-" * 40)
    north_bound = get_north_bound_top10()
    if north_bound.empty:
        print("   ❌ No data")
    else:
        for idx, row in north_bound.head(5).iterrows():
            print(f"   {row.get('股票代码', 'N/A')} - {row.get('股票名称', 'N/A')}")
    
    # Test 4: Industry list
    print(f"\n4. Industry Sectors (Top 5):")
    print("-" * 40)
    industries = get_industry_list()
    if industries.empty:
        print("   ❌ No data")
    else:
        for idx, row in industries.head(5).iterrows():
            print(f"   {row.get('板块名称', 'N/A')}")
    
    print(f"\n{'='*60}")
    print("Test Completed!")
    print(f"{'='*60}\n")
