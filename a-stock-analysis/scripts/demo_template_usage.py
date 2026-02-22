#!/usr/bin/env python3
"""
Demo script showing how to use the report template engine in real analysis
演示脚本：展示如何在实际分析中使用报告模板引擎
"""

import os
import sys
import json
import datetime
from pathlib import Path

# Add the skills directory to Python path
script_dir = Path(__file__).parent
skill_dir = script_dir.parent
sys.path.append(str(skill_dir))

from templates.engine import render_template
from quick_report import generate_index_report, generate_stock_report


def demo_stock_analysis():
    """演示个股分析报告生成"""
    print("🚀 演示个股分析报告生成")
    print("=" * 50)
    
    try:
        # 1. 获取分析数据
        stock_data = generate_stock_report('600519', '贵州茅台')
        
        print(f"📊 获取到 {stock_data['stock_name']} 数据:")
        print(f"   代码: {stock_data['stock_code']}")
        print(f"   当前价格: {stock_data['current_price']}")
        print(f"   PE-TTM: {stock_data['pe_ttm']}")
        
        # 2. 渲染报告
        report_content = render_template('stock_report_template.md', stock_data)
        
        # 3. 保存报告
        output_file = f"{stock_data['stock_name']}_{stock_data['stock_code']}_分析报告.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        print(f"✅ 报告已保存: {output_file}")
        print(f"📖 报告长度: {len(report_content.split())} 词")
        
        return output_file
        
    except Exception as e:
        print(f"❌ 失败: {str(e)}")
        return None


def demo_index_analysis():
    """演示指数分析报告生成"""
    print("\n🚀 演示指数分析报告生成")
    print("=" * 50)
    
    try:
        # 1. 获取分析数据
        index_data = generate_index_report('000922', '中证红利')
        
        print(f"📊 获取到 {index_data['index_name']} 数据:")
        print(f"   代码: {index_data['index_code']}")
        print(f"   当前点位: {index_data['current_level']}")
        print(f"   股息率: {index_data['dividend_yield']}")
        
        # 2. 渲染报告
        report_content = render_template('index_report_template.md', index_data)
        
        # 3. 保存报告
        output_file = f"{index_data['index_name']}_{index_data['index_code']}_分析报告.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        print(f"✅ 报告已保存: {output_file}")
        print(f"📖 报告长度: {len(report_content.split())} 词")
        
        return output_file
        
    except Exception as e:
        print(f"❌ 失败: {str(e)}")
        return None


def demo_simple_template_usage():
    """演示简单模板引擎使用"""
    print("\n🚀 演示直接使用模板引擎")
    print("=" * 50)
    
    # 模拟从 API 获取的数据
    data = {
        'stock_name': '美的集团',
        'stock_code': '000333',
        'current_price': 52.80,
        'pe_ttm': 12.5,
        'pb': 2.8,
        'market_cap': '3400亿元',
        'profit_growth': '+18.5%',
        'dividend_yield': '3.2%',
        'target_price': 65.00,
        'upside_potential': '+23.1%',
        'investment_rating': '买入',
        'risk_level': '低风险',
        'bullish_point_1': '家电龙头地位巩固',
        'bullish_point_2': '智能家电布局优势',
        'bullish_point_3': '海外市场拓展加速',
        'bearish_point_1': '地产周期下行风险',
        'bearish_point_2': '原材料价格波动',
        'bearish_point_3': '行业竞争加剧',
        'report_date': datetime.datetime.now().strftime('%Y年%m月%d日')
    }
    
    try:
        report_content = render_template('stock_report_template.md', data)
        
        output_file = f"{data['stock_name']}_{data['stock_code']}_快速分析报告.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        print(f"✅ 报告已保存: {output_file}")
        print(f"📖 报告长度: {len(report_content.split())} 词")
        
        return output_file
        
    except Exception as e:
        print(f"❌ 失败: {str(e)}")
        return None


def main():
    """主函数"""
    print("📊 A-Stock Analysis Report Template Engine Demo")
    print("=" * 80)
    print()
    
    generated_files = []
    
    # 演示1：个股分析
    stock_report = demo_stock_analysis()
    if stock_report:
        generated_files.append(stock_report)
    
    # 演示2：指数分析
    index_report = demo_index_analysis()
    if index_report:
        generated_files.append(index_report)
    
    # 演示3：简单使用
    simple_report = demo_simple_template_usage()
    if simple_report:
        generated_files.append(simple_report)
    
    print()
    print("🎉 演示完成!")
    print("=" * 80)
    
    if generated_files:
        print(f"📄 生成的报告文件:")
        for file in generated_files:
            print(f"   • {file}")
        
        # 统计词数
        total_words = 0
        for file in generated_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_words += len(content.split())
            except:
                pass
                
        print(f"📊 报告总词数: {total_words} 词")
        
        # 展示报告预览
        print("\n📖 报告内容预览:")
        print("=" * 50)
        
        for file in generated_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    preview = []
                    line_count = 0
                    for line in f:
                        if line.strip() and not line.startswith('>') and not line.startswith('|'):
                            preview.append(line.strip())
                            line_count += 1
                        if line_count >= 5:
                            break
                    
                    print(f"\n📄 {file}:")
                    for line in preview:
                        print(f"   {line}")
                        
            except Exception as e:
                print(f"⚠️  无法读取 {file}: {e}")
    
    return len(generated_files)


if __name__ == "__main__":
    success_count = main()
    sys.exit(0 if success_count > 0 else 1)
