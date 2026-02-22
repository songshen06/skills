#!/usr/bin/env python3
"""
Template Engine Test Script
模板引擎测试脚本

测试所有报告模板是否能正常渲染
"""

import os
import sys
import datetime
from pathlib import Path

# Add the skills directory to Python path
script_dir = Path(__file__).parent
skill_dir = script_dir.parent
sys.path.append(str(skill_dir))

from templates.engine import StockReportTemplateEngine, render_template


def test_stock_template():
    """测试个股分析模板"""
    print("🔍 测试个股分析报告模板...")
    
    test_data = {
        'stock_code': '600519',
        'stock_name': '贵州茅台',
        'company_full_name': '贵州茅台酒股份有限公司',
        'industry': '白酒',
        'sub_industry': '白酒',
        'headquarters': '贵州省贵阳市',
        'employees': '16,000',
        'market_cap': '23,200亿元',
        'current_price': 1850.00,
        'pe_ttm': 35.2,
        'pb': 11.5,
        'roe': 30.5,
        'dividend_yield': 1.5,
        'profit_growth': '+12.5%',
        'sales_growth': '+8.2%',
        'investment_rating': '买入',
        'target_price': 2200.00,
        'upside_potential': '+18.9%',
        'risk_level': '中等风险',
        'bullish_point_1': '高端白酒品牌护城河',
        'bullish_point_2': '稳定的现金流和高ROE',
        'bullish_point_3': '奢侈品属性抗通胀',
        'bearish_point_1': '估值相对较高',
        'bearish_point_2': '消费税政策风险',
        'bearish_point_3': '渠道库存风险',
        'catalysts': '新品推出、价格调整、旺季需求',
        'risk_description': '市场波动风险、政策风险',
        'data_period': '2025年12月-2026年2月',
        'report_date': datetime.datetime.now().strftime('%Y年%m月%d日')
    }
    
    try:
        engine = StockReportTemplateEngine()
        report = engine.render('stock_report_template.md', test_data)
        print(f"✅ 个股分析报告渲染成功 ({len(report.split())} words)")
        return report
    except Exception as e:
        print(f"❌ 个股分析报告渲染失败: {e}")
        return None


def test_index_template():
    """测试指数分析模板"""
    print("🔍 测试指数分析报告模板...")
    
    test_data = {
        'index_code': '000922',
        'index_name': '中证红利',
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
    
    try:
        engine = StockReportTemplateEngine()
        report = engine.render('index_report_template.md', test_data)
        print(f"✅ 指数分析报告渲染成功 ({len(report.split())} words)")
        return report
    except Exception as e:
        print(f"❌ 指数分析报告渲染失败: {e}")
        return None


def test_sector_template():
    """测试行业分析模板"""
    print("🔍 测试行业分析报告模板...")
    
    test_data = {
        'sector_code': '000986',
        'sector_name': '能源行业',
        'industry_name': '能源',
        'total_market_cap': '1.2万亿元',
        'stock_count': 35,
        'report_date': datetime.datetime.now().strftime('%Y年%m月%d日'),
        'current_level': 1250.00,
        'level_change': '+0.85%',
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
    
    try:
        engine = StockReportTemplateEngine()
        report = engine.render('sector_report_template.md', test_data)
        print(f"✅ 行业分析报告渲染成功 ({len(report.split())} words)")
        return report
    except Exception as e:
        print(f"❌ 行业分析报告渲染失败: {e}")
        return None


def main():
    """主测试函数"""
    print("=" * 80)
    print("📊 A-Stock Analysis Report Templates Test")
    print("=" * 80)
    
    # 创建测试结果目录
    test_dir = Path('test_output')
    test_dir.mkdir(exist_ok=True)
    
    # 测试所有模板
    stock_report = test_stock_template()
    index_report = test_index_template()
    sector_report = test_sector_template()
    
    # 保存测试结果
    if stock_report:
        output_file = test_dir / '个股分析报告_测试.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(stock_report)
        print(f"📄 个股分析报告保存至: {output_file}")
    
    if index_report:
        output_file = test_dir / '指数分析报告_测试.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(index_report)
        print(f"📄 指数分析报告保存至: {output_file}")
    
    if sector_report:
        output_file = test_dir / '行业分析报告_测试.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(sector_report)
        print(f"📄 行业分析报告保存至: {output_file}")
    
    print("\n" + "=" * 80)
    
    # 统计结果
    tests_passed = 0
    tests_total = 3
    
    if stock_report:
        tests_passed += 1
    if index_report:
        tests_passed += 1
    if sector_report:
        tests_passed += 1
    
    print(f"✅ 测试结果: {tests_passed}/{tests_total} 个报告成功渲染")
    
    if tests_passed < tests_total:
        print("⚠️  部分报告渲染失败，请检查错误信息")
    
    return tests_passed


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result == 3 else 1)
