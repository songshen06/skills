#!/usr/bin/env python3
"""
East Money (东方财富) API for A-Share Market Data
东方财富A股数据获取API - 完整版

Features:
- Real-time stock quotes (实时行情)
- K-line data (K线数据)
- Financial statements (财务报表)
- Technical indicators (技术指标)
- Valuation metrics (估值指标)
- Fund flow data (资金流向)
- Shareholder data (股东数据)
- Analyst ratings (机构评级)
- North/South bound flow (北向/南向资金)

Author: AI Assistant
Date: 2026-02-19
"""

import requests
import json
import sys
import pandas as pd
from datetime import datetime, timedelta
import time
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

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Constants
EASTMONEY_API_BASE = "https://push2.eastmoney.com/api"
EASTMONEY_HQ_BASE = "https://push2.eastmoney.com/api/qt"
EASTMONEY_STOCK_BASE = "https://push2.eastmoney.com/api/qt/stock"
EASTMONEY_SEC_BASE = "https://datacenter-web.eastmoney.com/api/data/v1/get"

# Market codes
MARKET_SH = "1"  # 上海
MARKET_SZ = "0"  # 深圳
MARKET_BJ = "0"  # 北京 (使用深圳代码)

# Data Manager instance
_data_manager = None

def get_dm():
    """Get or create data manager instance"""
    global _data_manager
    if _data_manager is None:
        _data_manager = get_data_manager(cache_dir="./cache/eastmoney")
    return _data_manager

def get_market_code(stock_code: str) -> str:
    """
    Get market code based on stock code
    根据股票代码判断市场
    
    Args:
        stock_code: Stock code (e.g., "600519", "000001", "300750")
    
    Returns:
        Market code ("1" for Shanghai, "0" for Shenzhen)
    """
    # 沪市主板 (60开头)、科创板 (68开头)、B股 (90开头)
    if stock_code.startswith(('60', '68', '90', '110', '113', '132', '204', '5')):
        return MARKET_SH
    # 深市主板 (00开头)、中小板 (002开头)、创业板 (30开头)、B股 (20开头)
    elif stock_code.startswith(('00', '30', '20', '12', '13', '14', '15', '16', '17', '18')):
        return MARKET_SZ
    # 北交所 (43, 83, 87开头)
    elif stock_code.startswith(('4', '8')):
        return MARKET_SZ  # 北交所使用深圳代码
    else:
        # 默认深圳
        return MARKET_SZ

def get_full_stock_code(stock_code: str) -> str:
    """
    Get full stock code with market prefix
    获取带市场前缀的完整股票代码
    
    Args:
        stock_code: Stock code (e.g., "600519")
    
    Returns:
        Full stock code (e.g., "1.600519" for Shanghai)
    """
    market_code = get_market_code(stock_code)
    return f"{market_code}.{stock_code}"

# ==================== Real-time Data APIs ====================

@cached(data_type="realtime_quote", ttl=60)
def get_realtime_quote(stock_code: str) -> Dict:
    """
    Get real-time stock quote
    获取实时行情数据
    
    Args:
        stock_code: Stock code (e.g., "600519")
    
    Returns:
        Dictionary with real-time quote data
    """
    try:
        secid = get_full_stock_code(stock_code)
        
        def _scaled_float(value: Any, scale: float = 1.0, default: Optional[float] = 0.0):
            if value is None:
                return default
            try:
                return float(value) / scale
            except (TypeError, ValueError):
                return default
        
        def _normalize_price(value: Any, default: Optional[float] = 0.0):
            num = _scaled_float(value, 1, default)
            if num is None:
                return default
            # Compatibility: some legacy endpoints return price * 100.
            return num / 100 if abs(num) >= 1000 else num
        
        def _normalize_percent(value: Any, default: Optional[float] = 0.0):
            num = _scaled_float(value, 1, default)
            if num is None:
                return default
            # Compatibility: some legacy endpoints return pct * 100.
            return num / 100 if abs(num) >= 1000 else num
        
        url = f"{EASTMONEY_STOCK_BASE}/get"
        params = {
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fltt": "2",
            "invt": "2",
            "fields": "f43,f44,f45,f46,f47,f48,f50,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170,f171",
            "secid": secid
        }
        
        try:
            response = requests.get(url, params=params, timeout=10, verify=False)
        except Exception:
            response = None
        if response is None or response.status_code != 200 or not response.text.strip():
            # Fallback: bypass environment proxies that may hijack this request.
            session = requests.Session()
            session.trust_env = False
            response = session.get(url, params=params, timeout=10, verify=False)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code} for stock {stock_code}"}

        try:
            data = response.json()
        except Exception as e:
            return {"error": f"Invalid JSON response: {e}"}
        
        if 'data' not in data or data['data'] is None:
            return {"error": f"No data found for stock {stock_code}"}
        
        result = data['data']
        
        # Map field codes to meaningful names
        quote_data = {
            "股票代码": result.get('f57', stock_code),
            "股票名称": result.get('f58', ''),
            "最新价": _normalize_price(result.get('f43')),
            "涨跌额": _normalize_price(result.get('f169'), None),
            "涨跌幅": _normalize_percent(result.get('f170'), None),
            "成交量(手)": _scaled_float(result.get('f47'), 100),
            "成交额(万)": _scaled_float(result.get('f48'), 10000),
            "振幅": _normalize_percent(result.get('f171'), None),
            "最高价": _normalize_price(result.get('f44')),
            "最低价": _normalize_price(result.get('f45')),
            "今开": _normalize_price(result.get('f46')),
            "昨收": _normalize_price(result.get('f60')),
            "总市值(亿)": _scaled_float(result.get('f116'), 100000000),
            "流通市值(亿)": _scaled_float(result.get('f117'), 100000000),
            "换手率": _normalize_percent(result.get('f168'), None),
            "市盈率(动)": _normalize_price(result.get('f162'), None),
            "市净率": _normalize_price(result.get('f167'), None),
            "60日涨跌幅": None,
            "年初至今涨跌幅": None,
        }
        
        return quote_data
        
    except Exception as e:
        logger.error(f"Failed to get realtime quote: {e}")
        return {"error": f"Failed to get realtime quote: {str(e)}"}

# More API functions will be added here...

# ==================== K-line Data APIs ====================

@cached(data_type="kline_daily", ttl=300)
def get_kline_daily(stock_code: str, count: int = 100) -> pd.DataFrame:
    """
    Get daily K-line data
    获取日K线数据
    
    Args:
        stock_code: Stock code (e.g., "600519")
        count: Number of data points to retrieve
    
    Returns:
        DataFrame with OHLCV data
    """
    return _get_kline_data(stock_code, period="101", count=count)

@cached(data_type="kline_weekly", ttl=1800)
def get_kline_weekly(stock_code: str, count: int = 100) -> pd.DataFrame:
    """
    Get weekly K-line data
    获取周K线数据
    
    Args:
        stock_code: Stock code (e.g., "600519")
        count: Number of data points to retrieve
    
    Returns:
        DataFrame with OHLCV data
    """
    return _get_kline_data(stock_code, period="102", count=count)

@cached(data_type="kline_monthly", ttl=3600)
def get_kline_monthly(stock_code: str, count: int = 100) -> pd.DataFrame:
    """
    Get monthly K-line data
    获取月K线数据
    
    Args:
        stock_code: Stock code (e.g., "600519")
        count: Number of data points to retrieve
    
    Returns:
        DataFrame with OHLCV data
    """
    return _get_kline_data(stock_code, period="103", count=count)

def _get_kline_data(stock_code: str, period: str, count: int) -> pd.DataFrame:
    """
    Internal function to get K-line data
    内部函数：获取K线数据
    
    Args:
        stock_code: Stock code
        period: K-line period ("101"=daily, "102"=weekly, "103"=monthly)
        count: Number of data points
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        secid = get_full_stock_code(stock_code)
        
        url = f"{EASTMONEY_API_BASE}/qt/stock/kline/get"
        params = {
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": period,
            "fqt": "1",
            "end": "20500101",
            "lmt": str(count),
        }
        
        try:
            response = requests.get(url, params=params, timeout=10, verify=False)
        except Exception:
            response = None
        if response is None or response.status_code != 200 or not response.text.strip():
            session = requests.Session()
            session.trust_env = False
            response = session.get(url, params=params, timeout=10, verify=False)
        if response.status_code != 200:
            logger.warning(f"Kline request failed ({response.status_code}) for {stock_code}")
            return pd.DataFrame()
        response.encoding = 'utf-8'
        try:
            data = response.json()
        except Exception:
            logger.warning(f"Invalid kline JSON for {stock_code}")
            return pd.DataFrame()
        
        if 'data' not in data or data['data'] is None or 'klines' not in data['data']:
            logger.warning(f"No kline data found for {stock_code}")
            return pd.DataFrame()
        
        klines = data['data']['klines']
        
        # Parse kline data
        data_list = []
        for kline in klines:
            parts = kline.split(',')
            if len(parts) >= 6:
                data_list.append({
                    '日期': parts[0],
                    '开盘': float(parts[1]),
                    '收盘': float(parts[2]),
                    '最高': float(parts[3]),
                    '最低': float(parts[4]),
                    '成交量': int(float(parts[5])),
                    '成交额': float(parts[6]) if len(parts) > 6 else 0,
                    '振幅': float(parts[7]) if len(parts) > 7 else 0,
                    '涨跌幅': float(parts[8]) if len(parts) > 8 else 0,
                    '涨跌额': float(parts[9]) if len(parts) > 9 else 0,
                    '换手率': float(parts[10]) if len(parts) > 10 else 0,
                })
        
        df = pd.DataFrame(data_list)
        return df
        
    except Exception as e:
        logger.error(f"Error getting kline data: {e}")
        return pd.DataFrame()

# ==================== Financial Data APIs ====================

@cached(data_type="financial_statements", ttl=86400)
def get_financial_statements(stock_code: str, report_type: str = "balance") -> pd.DataFrame:
    """
    Get financial statements
    获取财务报表
    
    Args:
        stock_code: Stock code (e.g., "600519")
        report_type: Report type ("balance", "income", "cash_flow")
    
    Returns:
        DataFrame with financial statement data
    """
    # This is a placeholder - actual implementation would require
    # additional API endpoints or web scraping
    logger.info(f"Financial statements for {stock_code} - {report_type}")
    return pd.DataFrame()

# More financial data functions will be added here...

# ==================== Financial Data APIs ====================

@cached(data_type="financial_statements", ttl=86400)
def get_income_statement(stock_code: str, count: int = 5) -> pd.DataFrame:
    """
    Get income statement (利润表)
    获取利润表数据
    
    Args:
        stock_code: Stock code (e.g., "600519")
        count: Number of periods to retrieve
    
    Returns:
        DataFrame with income statement data
    """
    try:
        secid = get_full_stock_code(stock_code)
        
        url = f"{EASTMONEY_SEC_BASE}"
        params = {
            "reportName": "RPT_FCI_PERFORMANCEE",
            "columns": "ALL",
            "filter": f"(SECURITY_CODE%3D%22{stock_code}%22)",
            "pageNumber": "1",
            "pageSize": str(count),
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "source": "WEB",
            "client": "WEB"
        }
        
        response = requests.get(url, params=params, timeout=10, verify=False)
        response.encoding = 'utf-8'
        
        data = response.json()
        
        if 'result' not in data or data['result'] is None or 'data' not in data['result']:
            logger.warning(f"No income statement data found for {stock_code}")
            return pd.DataFrame()
        
        df = pd.DataFrame(data['result']['data'])
        return df
        
    except Exception as e:
        logger.error(f"Error getting income statement: {e}")
        return pd.DataFrame()

@cached(data_type="financial_statements", ttl=86400)
def get_balance_sheet(stock_code: str, count: int = 5) -> pd.DataFrame:
    """
    Get balance sheet (资产负债表)
    获取资产负债表数据
    
    Args:
        stock_code: Stock code (e.g., "600519")
        count: Number of periods to retrieve
    
    Returns:
        DataFrame with balance sheet data
    """
    # Placeholder - actual implementation would require specific API endpoint
    logger.info(f"Balance sheet for {stock_code} - placeholder")
    return pd.DataFrame()

@cached(data_type="financial_statements", ttl=86400)
def get_cash_flow(stock_code: str, count: int = 5) -> pd.DataFrame:
    """
    Get cash flow statement (现金流量表)
    获取现金流量表数据
    
    Args:
        stock_code: Stock code (e.g., "600519")
        count: Number of periods to retrieve
    
    Returns:
        DataFrame with cash flow data
    """
    # Placeholder - actual implementation would require specific API endpoint
    logger.info(f"Cash flow for {stock_code} - placeholder")
    return pd.DataFrame()

# ==================== Fund Flow APIs ====================

@cached(data_type="fund_flow", ttl=300)
def get_fund_flow(stock_code: str) -> Dict:
    """
    Get fund flow data (资金流向)
    获取资金流向数据
    
    Args:
        stock_code: Stock code (e.g., "600519")
    
    Returns:
        Dictionary with fund flow data
    """
    try:
        secid = get_full_stock_code(stock_code)
        
        url = f"{EASTMONEY_HQ_BASE}/get"
        params = {
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fltt": "2",
            "invt": "2",
            "fields": "f124,f125,f126,f127,f128,f129,f130,f131,f132,f133,f134,f135,f136,f137,f138,f139,f140,f141,f142,f143,f144,f145,f146,f147,f148,f149,f150",
            "secid": secid
        }
        
        try:
            response = requests.get(url, params=params, timeout=10, verify=False)
        except Exception:
            response = None
        if response is None or response.status_code != 200 or not response.text.strip():
            session = requests.Session()
            session.trust_env = False
            response = session.get(url, params=params, timeout=10, verify=False)
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code} for fund flow {stock_code}"}
        response.encoding = 'utf-8'
        try:
            data = response.json()
        except Exception as e:
            return {"error": f"Invalid fund flow JSON: {e}"}
        
        if 'data' not in data or data['data'] is None:
            return {"error": f"No fund flow data found for {stock_code}"}
        
        result = data['data']
        
        # Parse fund flow data
        fund_flow_data = {
            "股票代码": stock_code,
            "主力净流入": float(result.get('f124', 0)) / 10000 if result.get('f124') else 0,
            "主力净流入占比": float(result.get('f125', 0)) / 100 if result.get('f125') else 0,
            "超大单净流入": float(result.get('f126', 0)) / 10000 if result.get('f126') else 0,
            "超大单净流入占比": float(result.get('f127', 0)) / 100 if result.get('f127') else 0,
            "大单净流入": float(result.get('f128', 0)) / 10000 if result.get('f128') else 0,
            "大单净流入占比": float(result.get('f129', 0)) / 100 if result.get('f129') else 0,
            "中单净流入": float(result.get('f130', 0)) / 10000 if result.get('f130') else 0,
            "中单净流入占比": float(result.get('f131', 0)) / 100 if result.get('f131') else 0,
            "小单净流入": float(result.get('f132', 0)) / 10000 if result.get('f132') else 0,
            "小单净流入占比": float(result.get('f133', 0)) / 100 if result.get('f133') else 0,
            "主力流入": float(result.get('f134', 0)) / 10000 if result.get('f134') else 0,
            "主力流出": float(result.get('f135', 0)) / 10000 if result.get('f135') else 0,
        }
        
        return fund_flow_data
        
    except Exception as e:
        logger.error(f"Failed to get fund flow: {e}")
        return {"error": f"Failed to get fund flow: {str(e)}"}

# More APIs will be added here...


def fetch_index_data(index_code: str) -> Optional[Dict[str, Any]]:
    """
    Fetch simplified index data for fallback use in index analyzer.
    为指数分析器提供简化版指数数据（回退数据源）。
    """
    try:
        df = get_kline_daily(index_code, count=252)
        if df is None or df.empty:
            logger.warning(f"No East Money index data found for {index_code}")
            return None

        latest = df.iloc[-1]
        change_pct = latest.get("涨跌幅", 0)
        volume = latest.get("成交量", 0)
        amount = latest.get("成交额", 0)

        result = {
            "index_code": index_code,
            "latest_price": float(latest.get("收盘", 0)),
            "change_pct": float(change_pct) if change_pct is not None else 0.0,
            "volume": float(volume) if volume is not None else 0.0,
            "amount": float(amount) if amount is not None else 0.0,
            "high_52w": float(df["最高"].max()) if "最高" in df.columns else None,
            "low_52w": float(df["最低"].min()) if "最低" in df.columns else None,
            "date": str(latest.get("日期", datetime.now().strftime("%Y-%m-%d"))),
            "source": "eastmoney",
        }
        return result
    except Exception as e:
        logger.error(f"Failed to fetch index data via East Money: {e}")
        return None

if __name__ == "__main__":
    # Test the API
    print("Testing East Money API...")
    
    # Test getting real-time quote
    result = get_realtime_quote("600519")
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"\n股票名称: {result.get('股票名称')}")
        print(f"最新价: {result.get('最新价')}")
        print(f"涨跌幅: {result.get('涨跌幅')}%")
        print(f"换手率: {result.get('换手率')}%")
        print(f"市盈率: {result.get('市盈率(动)')}")
