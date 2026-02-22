#!/usr/bin/env python3
"""Regression tests for key reliability fixes."""

import unittest
from unittest.mock import patch
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

# Ensure sibling modules are importable when run from repo root.
SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from eastmoney_api import fetch_index_data, get_realtime_quote
import index_analyzer
from quick_report import (
    generate_stock_report,
    get_report_preview,
    get_default_output_file,
    optimize_markdown_content,
)
from templates.engine import StockReportTemplateEngine
from templates.web_renderer import render_web_report


class TestRegressions(unittest.TestCase):
    @patch("quick_report.get_cash_with_fallback")
    @patch("quick_report.get_balance_with_fallback")
    @patch("quick_report.get_income_with_fallback")
    @patch("quick_report.get_fund_flow")
    @patch("quick_report.get_kline_with_fallback")
    @patch("quick_report.get_quote_with_fallback")
    def test_generate_stock_report_applies_strategy_rules(
        self, mock_quote, mock_kline, mock_fund_flow, mock_income, mock_balance, mock_cash
    ):
        mock_quote.return_value = {
            "最新价": 5.0,
            "市盈率(动)": 12.5,
            "市净率": 1.1,
            "换手率": 2.2,
            "涨跌幅": 0.8,
            "总市值(亿)": 120.0,
            "股息率": "2.4%",
        }
        mock_kline.return_value = pd.DataFrame(
            [
                {
                    "收盘": 4.8,
                    "最高": 4.9,
                    "最低": 4.7,
                    "成交量": 120000,
                    "涨跌幅": 0.6,
                    "换手率": 2.0,
                },
                {
                    "收盘": 5.0,
                    "最高": 5.1,
                    "最低": 4.8,
                    "成交量": 150000,
                    "涨跌幅": 0.8,
                    "换手率": 2.2,
                },
            ]
        )
        mock_fund_flow.__wrapped__ = lambda _code: {"主力净流入": 1000000, "主力净流入占比": 3.5}
        mock_income.return_value = pd.DataFrame()
        mock_balance.return_value = pd.DataFrame()
        mock_cash.return_value = pd.DataFrame()

        data = generate_stock_report("000589", "贵州轮胎")

        self.assertNotEqual(data.get("short_entry_zone"), "数据暂缺")
        self.assertNotEqual(data.get("medium_entry_zone"), "数据暂缺")
        self.assertNotEqual(data.get("long_entry_zone"), "数据暂缺")
        self.assertIn(data.get("pe_percentile"), {"40", "60"})
        self.assertIn(data.get("pb_percentile"), {"35", "55"})
        self.assertNotEqual(data.get("base_dcf_value"), "数据暂缺")
        self.assertNotEqual(data.get("bull_dcf_value"), "数据暂缺")
        self.assertNotEqual(data.get("bear_dcf_value"), "数据暂缺")
        self.assertIn("%", str(data.get("base_margin")))
        self.assertIn("日线", str(data.get("short_cycle_desc")))
        self.assertIn("周线", str(data.get("medium_cycle_desc")))
        self.assertIn("月线", str(data.get("long_cycle_desc")))

    def test_preview_handles_short_content(self):
        self.assertEqual(get_report_preview("only one line", 3), ["only one line"])

    def test_web_renderer_outputs_html(self):
        html = render_web_report(
            "stock",
            {
                "stock_code": "000589",
                "stock_name": "贵州轮胎",
                "report_date": "2026年02月21日",
                "current_price": 5.02,
                "pe_ttm": 13.01,
                "pb": 0.88,
                "roe": 8.5,
                "dividend_yield": 2.0,
                "target_price": 5.8,
                "investment_rating": "买入",
                "risk_level": "中等风险",
                "upside_potential": "+15.0%",
            },
        )
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Chart", html)
        self.assertIn("贵州轮胎", html)

    def test_default_output_file_by_format(self):
        args = SimpleNamespace(
            name="贵州轮胎", code="000589", type="stock", format="html"
        )
        output = get_default_output_file(args, {"stock_name": "贵州轮胎"})
        self.assertTrue(output.endswith(".html"))

    def test_optimize_markdown_content_removes_placeholder_rows(self):
        raw = (
            "| 指标 | 数值 | 评价 |\n"
            "|------|------|------|\n"
            "| ROE | 数据暂缺 | 数据暂缺 |\n"
            "| PE | 13.01 | 偏低 |\n"
            "\n"
            "数据暂缺\n"
            "- [ ] PB处于历史数据暂缺%分位以下\n"
        )
        cleaned = optimize_markdown_content(raw, aggressive=True)
        self.assertIn("| PE | 13.01 | 偏低 |", cleaned)
        self.assertNotIn("| ROE | 数据暂缺 | 数据暂缺 |", cleaned)
        self.assertNotIn("- [ ] PB处于历史数据暂缺%分位以下", cleaned)

    def test_optimize_markdown_content_removes_empty_sections(self):
        raw = (
            "## 空章节\n\n"
            "| 指标 | 数值 |\n"
            "|------|------|\n"
            "\n"
            "## 有效章节\n"
            "真实内容\n"
        )
        cleaned = optimize_markdown_content(raw, aggressive=True)
        self.assertNotIn("## 空章节", cleaned)
        self.assertIn("## 有效章节", cleaned)
        self.assertIn("真实内容", cleaned)

    def test_optimize_markdown_content_preserves_structure_by_default(self):
        raw = (
            "## 空章节\n\n"
            "| 指标 | 数值 |\n"
            "|------|------|\n"
            "\n"
            "## 均线系统\n"
            "| 均线 | 数值 |\n"
            "|------|------|\n"
            "| MA5 | 数据暂缺 |\n"
        )
        cleaned = optimize_markdown_content(raw)
        self.assertIn("## 空章节", cleaned)
        self.assertIn("## 均线系统", cleaned)

    def test_cleanup_preserves_blank_lines(self):
        engine = StockReportTemplateEngine()
        content = "# Title\n\nParagraph\n\n{{missing_var}}\n"
        cleaned = engine._cleanup(content)
        self.assertIn("# Title\n\nParagraph", cleaned)
        self.assertIn("N/A", cleaned)

    @patch("eastmoney_api.get_kline_daily")
    def test_fetch_index_data_from_kline(self, mock_get_kline_daily):
        mock_get_kline_daily.return_value = pd.DataFrame(
            [
                {
                    "日期": "2026-02-20",
                    "收盘": 3750.0,
                    "涨跌幅": -0.5,
                    "成交量": 1000000,
                    "成交额": 250000000,
                    "最高": 3800.0,
                    "最低": 3600.0,
                },
                {
                    "日期": "2026-02-21",
                    "收盘": 3800.0,
                    "涨跌幅": 1.33,
                    "成交量": 1200000,
                    "成交额": 280000000,
                    "最高": 3850.0,
                    "最低": 3650.0,
                },
            ]
        )

        data = fetch_index_data("000922")

        self.assertIsNotNone(data)
        self.assertEqual(data["index_code"], "000922")
        self.assertEqual(data["latest_price"], 3800.0)
        self.assertEqual(data["high_52w"], 3850.0)
        self.assertEqual(data["low_52w"], 3600.0)
        self.assertEqual(data["source"], "eastmoney")

    @patch("index_analyzer.load_from_cache", return_value={"cached": True})
    def test_fetch_index_basic_info_prefers_cache(self, _mock_cache):
        data = index_analyzer.fetch_index_basic_info("000922")
        self.assertEqual(data, {"cached": True})

    @patch("index_analyzer.save_to_cache")
    @patch("index_analyzer.load_from_cache", return_value=None)
    @patch("index_analyzer.AKSHARE_AVAILABLE", False)
    def test_fetch_index_basic_info_fallback_to_eastmoney(
        self, _mock_load_cache, mock_save_cache
    ):
        fake_data = {
            "index_code": "000922",
            "latest_price": 3800.0,
            "source": "eastmoney",
        }
        fake_module = SimpleNamespace(fetch_index_data=lambda _code: fake_data)
        with patch.dict("sys.modules", {"eastmoney_api": fake_module}):
            data = index_analyzer.fetch_index_basic_info(
                "000922", source_priority=["eastmoney"]
            )

        self.assertEqual(data, fake_data)
        mock_save_cache.assert_called_once()

    @patch("eastmoney_api.requests.get")
    def test_get_realtime_quote_uses_market_value_fields(self, mock_get):
        class _FakeResponse:
            encoding = "utf-8"
            status_code = 200
            text = "ok"

            @staticmethod
            def json():
                return {
                    "data": {
                        "f57": "600519",
                        "f58": "贵州茅台",
                        "f43": 185000,
                        "f44": 186000,
                        "f45": 183000,
                        "f46": 184000,
                        "f47": 1000000,
                        "f48": 500000000,
                        "f60": 184500,
                        "f168": 163,
                        "f169": -0.06,
                        "f170": -1.18,
                        "f171": 1.77,
                        "f116": 2320000000000,
                        "f117": 1850000000000,
                        "f162": 3520,
                        "f167": 1150,
                    }
                }

        mock_get.return_value = _FakeResponse()
        quote = get_realtime_quote.__wrapped__("600519")

        self.assertEqual(quote["股票代码"], "600519")
        self.assertEqual(quote["股票名称"], "贵州茅台")
        self.assertEqual(quote["总市值(亿)"], 23200.0)
        self.assertEqual(quote["流通市值(亿)"], 18500.0)
        self.assertAlmostEqual(quote["市盈率(动)"], 35.2)
        self.assertAlmostEqual(quote["涨跌幅"], -1.18)
        self.assertAlmostEqual(quote["最高价"], 1860.0)

    def test_build_index_report_template_data_uses_basic_info(self):
        result = {
            "index_code": "000922",
            "index_name": "中证红利",
            "report_date": "2026-02-21 10:00:00",
            "data": {
                "basic_info": {
                    "latest_price": 3800.0,
                    "change_pct": 1.25,
                    "date": "2026-02-21",
                }
            },
        }

        report_data = index_analyzer.build_index_report_template_data(result)
        self.assertEqual(report_data["current_level"], 3800.0)
        self.assertEqual(report_data["level_change"], "+1.25%")
        self.assertEqual(report_data["investment_rating"], "买入")
        self.assertEqual(report_data["data_period"], "2026-02-21")


if __name__ == "__main__":
    unittest.main()
