# Report Templates Documentation (A-Stock Analysis Skill)

## 📊 Overview

We have created dedicated report templates for different analysis scenarios in the `templates/` directory:

| Template File | Purpose | Use Case |
|--------------|---------|----------|
| `stock_report_template.md` | **Stock Analysis Report** | In-depth analysis of individual listed companies |
| `index_report_template.md` | **Index Analysis Report** | Market index and ETF analysis |
| `sector_report_template.md` | **Sector Analysis Report** | Industry-wide and sub-industry analysis |

## 🚀 Quick Start

### 1. Using the Template Engine Directly

```python
# Import the template engine
from templates.engine import render_template

# Data for your analysis
data = {
    'stock_code': '600519',
    'stock_name': '贵州茅台',
    'current_price': 1850.00,
    'pe_ttm': 35.2,
    'pb': 11.5,
    'dividend_yield': 1.5,
    'target_price': 2200.00,
    'upside_potential': '+18.9%',
    'risk_level': '中等风险',
    'bullish_point_1': '高端白酒品牌护城河',
    'bullish_point_2': '稳定的现金流和高ROE',
    'bullish_point_3': '奢侈品属性抗通胀',
    'bearish_point_1': '估值相对较高',
    'bearish_point_2': '消费税政策风险',
    'bearish_point_3': '渠道库存风险',
    'catalysts': '新品推出、价格调整、旺季需求'
}

# Render and save the report
report_content = render_template('stock_report_template.md', data)

with open('贵州茅台_分析报告.md', 'w', encoding='utf-8') as f:
    f.write(report_content)

print("✅ Report generated successfully!")
```

### 2. Using the Quick Report Tool

#### Command-line Usage

```bash
# Generate stock analysis report
python3 quick_report.py stock 600519 "贵州茅台"

# Generate index analysis report with custom template and output
python3 quick_report.py index 000922 "中证红利" --template index_report_template.md --output "中证红利_指数分析报告.md"

# Generate sector analysis report with verbose output
python3 quick_report.py sector 000986 "能源行业" -v
```

#### Output Examples

```
📊 Generating stock analysis report for 600519...
📝 Using template: stock_report_template.md
✅ Report saved to: 贵州茅台_600519_20260220.md
📖 Report preview (first 3 lines):
==================================================
# 贵州茅台 (600519) 投资分析报告
> **报告日期**: 2026年02月20日
==================================================
```

### 3. Integration with Analyzers

#### Using with Index Analyzer

```bash
# Use the index analyzer with custom template
python3 index_analyzer.py 000922 --name "中证红利" --template index_report_template.md --output "中证红利_分析报告.md"
```

#### Using with Stock Analyzer

```python
from a_stock_analyzer import analyze_stock
from templates.engine import render_template

# Analyze the stock and get data
analysis_result = analyze_stock('600519')

# Render report
report_content = render_template('stock_report_template.md', analysis_result)
```

## 🎯 Template Variables

### Common Variables (All Templates)

| Variable | Description | Example |
|----------|-------------|---------|
| `report_date` | 报告日期 | 2026年02月20日 |
| `data_date` | 数据截止日期 | 2026年02月20日 |
| `next_update_date` | 下次更新日期 | 2026年02月27日 |
| `author` | 分析师/来源 | AI Investment Analyst |
| `data_source` | 数据来源 | AKShare + East Money |
| `risk_level` | 风险等级 | 低风险/中等风险/高风险 |
| `risk_description` | 风险描述 | 安全边际较高 |

### Stock Analysis Variables

```python
{
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
    'catalysts': '新品推出、价格调整、旺季需求'
}
```

### Index Analysis Variables

```python
{
    'index_code': '000922',
    'index_name': '中证红利',
    'report_date': '2026年02月20日',
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
    'catalysts': '政策支持、经济复苏、企业分红'
}
```

### Sector Analysis Variables

```python
{
    'sector_code': '000986',
    'sector_name': '能源行业',
    'industry_name': '能源',
    'total_market_cap': '1.2万亿元',
    'stock_count': 35,
    'report_date': '2026年02月20日',
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
    'catalysts': '政策出台、技术突破、需求增长'
}
```

## 🛠️ Template Engine Features

### Variable Replacement

The engine supports simple variable replacement:

```markdown
# {{stock_name}} ({{stock_code}}) 投资分析报告

> **报告日期**: {{report_date}}
> **当前价格**: {{current_price}} 元
> **市盈率**: {{pe_ttm}}
> **市净率**: {{pb}}
> **股息率**: {{dividend_yield}}%

{{bullish_point_1}}
{{bullish_point_2}}
{{bullish_point_3}}
```

### Conditional Logic (Coming Soon)

```markdown
{{#if target_price}}
## 投资建议

**目标价**: {{target_price}} 元
**上涨空间**: {{upside_potential}}

{{#if upside_potential > 20}}
⚠️ 巨大上涨空间，但需注意风险
{{/if}}
{{/if}}
```

### Table Formatting

The engine automatically formats tables:

```markdown
| 指标 | 值 | 趋势 |
|-----|----|------|
| {{indicator1}} | {{value1}} | {{trend1}} |
| {{indicator2}} | {{value2}} | {{trend2}} |
```

### Chart Rendering (Coming Soon)

```markdown
## 价格走势

{{price_chart}}

## 成交量分析

{{volume_chart}}
```

## 📊 Advanced Usage

### 1. Custom Templates

You can create your own custom templates:

```python
# Create a simple custom template
template_content = """
# {{name}} Analysis Report
Date: {{report_date}}
Current Price: {{current_price}}

## Analysis
{{analysis_text}}
"""

with open('custom_report.md', 'w', encoding='utf-8') as f:
    f.write(template_content)

# Use the custom template
report_content = render_template('custom_report.md', {
    'name': 'My Stock',
    'report_date': '2026年02月20日',
    'current_price': 150.00,
    'analysis_text': 'Stock analysis content here'
})
```

### 2. Batch Processing

Generate multiple reports at once:

```python
import os
import json
from templates.engine import render_template

# Load stock list from JSON file
with open('stock_list.json', 'r', encoding='utf-8') as f:
    stock_list = json.load(f)

# Create output directory
output_dir = 'reports'
os.makedirs(output_dir, exist_ok=True)

# Generate reports
for stock in stock_list:
    report_content = render_template('stock_report_template.md', stock)
    filename = f"{stock['name']}_{stock['code']}_分析报告.md"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ Generated: {filepath}")
```

### 3. Web Integration

```python
# Web interface example with Flask
from flask import Flask, render_template_string, request
from templates.engine import render_template

app = Flask(__name__)

@app.route('/report', methods=['POST'])
def generate_report():
    data = request.get_json()
    report_type = data.get('type', 'stock')
    report_data = data.get('data', {})
    
    template_name = f'{report_type}_report_template.md'
    report_content = render_template(template_name, report_data)
    
    return {'success': True, 'report': report_content}

if __name__ == '__main__':
    app.run(debug=True)
```

## 🔧 Troubleshooting

### Common Issues

1. **Template Not Found**
   - Check the template file exists in `templates/` directory
   - Ensure the template name is correct (case-sensitive)
   - Verify the skills directory structure

2. **Variables Not Rendered**
   - Check variable name matches in template and data dict
   - Ensure the variable exists in your data dict
   - Use `{{variable_name}}` syntax correctly

3. **Encoding Issues**
   - Ensure files are read/written with 'utf-8' encoding
   - Use proper encoding when dealing with Chinese characters

### Error Handling

```python
try:
    report_content = render_template('stock_report_template.md', data)
    
    with open('output.md', 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print("✅ Report generated successfully")
    
except FileNotFoundError:
    print("❌ Template file not found")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
```

## 📈 Performance Tips

### Caching Templates

The template engine automatically caches templates for performance:

```python
from templates.engine import StockReportTemplateEngine

# Create engine instance (templates are cached)
engine = StockReportTemplateEngine()

# Render 10 reports with the same template
for i in range(10):
    report_content = engine.render('stock_report_template.md', data)
    # Process the report
```

### Efficient Data Loading

```python
import concurrent.futures
import time
from templates.engine import render_template

def generate_report_task(stock_data):
    try:
        return render_template('stock_report_template.md', stock_data)
    except Exception as e:
        return None

# Parallel report generation
stocks = [{'stock_code': f'6000{i:02d}', 'stock_name': f'股票{i}'} for i in range(1, 11)]

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(generate_report_task, stock) for stock in stocks]
    
    for future in concurrent.futures.as_completed(futures):
        report_content = future.result()
        if report_content:
            print("✅ Report generated")
```

## 🎯 Best Practices

### 1. Use Appropriate Template for Analysis Type

```python
# Use stock template for individual stocks
if analysis_type == 'stock':
    template_name = 'stock_report_template.md'

# Use index template for indices
elif analysis_type == 'index':
    template_name = 'index_report_template.md'

# Use sector template for industry analysis
elif analysis_type == 'sector':
    template_name = 'sector_report_template.md'
```

### 2. Validate Data Before Rendering

```python
def validate_report_data(data: dict) -> dict:
    """Validate and clean report data"""
    # Ensure required fields are present
    required_fields = ['stock_code', 'stock_name', 'current_price']
    for field in required_fields:
        if field not in data:
            data[field] = 'N/A'
    
    # Clean numeric fields
    numeric_fields = ['current_price', 'pe_ttm', 'pb']
    for field in numeric_fields:
        if field in data:
            try:
                data[field] = float(data[field])
            except (ValueError, TypeError):
                data[field] = 0
    
    return data

# Usage
clean_data = validate_report_data(original_data)
report_content = render_template('stock_report_template.md', clean_data)
```

### 3. Add Comments and Documentation

```python
# Stock Analysis Report - 贵州茅台
data = {
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
    'catalysts': '新品推出、价格调整、旺季需求'
}

# Render with comments
report_content = render_template('stock_report_template.md', data)
```

## 📚 Resources

### Documentation Links

- [Main SKILL.md](/root/.openclaw/workspace/skills/a-stock-analysis/SKILL.md) - Skill documentation
- [CHANGELOG.md](/root/.openclaw/workspace/skills/a-stock-analysis/CHANGELOG.md) - Version history
- [REPORT_TEMPLATES.md](/root/.openclaw/workspace/skills/a-stock-analysis/TEMPLATES.md) - Template documentation

### Source Code

- `templates/engine.py` - Template engine implementation
- `scripts/test_templates.py` - Template testing script
- `scripts/quick_report.py` - Quick report generation tool

### Examples

- `test_templates.py` - Template rendering examples
- `quick_report.py` - Command-line usage examples
- `templates/stock_report_template.md` - Stock analysis template
- `templates/index_report_template.md` - Index analysis template
- `templates/sector_report_template.md` - Sector analysis template

---

**Updated**: 2026年02月20日  
**Version**: v2.1  
**Author**: AI Investment Analyst  
**Contributors**: OpenClaw Team
