---
name: analyzing-financial-statements
description: This skill calculates key financial ratios and metrics from financial statement data for investment analysis. Use directly for ratio analysis tasks, and auto-invoke from `a-stock-analysis` when financial statements are available to enhance A-share report quality.
---

# Financial Ratio Calculator Skill

> Invocation model (highest priority)  
> This skill is designed to be called by AI agents. Standalone script execution is only for agent-internal testing/debug.

This skill provides comprehensive financial ratio analysis for evaluating company performance, profitability, liquidity, and valuation.

## Capabilities

Calculate and interpret:
- **Profitability Ratios**: ROE, ROA, Gross Margin, Operating Margin, Net Margin
- **Liquidity Ratios**: Current Ratio, Quick Ratio, Cash Ratio
- **Leverage Ratios**: Debt-to-Equity, Interest Coverage, Debt Service Coverage
- **Efficiency Ratios**: Asset Turnover, Inventory Turnover, Receivables Turnover
- **Valuation Ratios**: P/E, P/B, P/S, EV/EBITDA, PEG
- **Per-Share Metrics**: EPS, Book Value per Share, Dividend per Share

## How to Use

1. **Input Data**: Provide financial statement data (income statement, balance sheet, cash flow)
2. **Select Ratios**: Specify which ratios to calculate or use "all" for comprehensive analysis
3. **Interpretation**: The skill will calculate ratios and provide industry-standard interpretations

### Called by a-stock-analysis (推荐联动模式)

When invoked by `a-stock-analysis`, use this minimal payload contract:

```json
{
  "income_statement": {},
  "balance_sheet": {},
  "cash_flow": {},
  "market_data": {}
}
```

Required core fields (at least one non-zero from each side for meaningful output):
- `income_statement`: `revenue` / `net_income`
- `balance_sheet`: `total_assets` / `shareholders_equity`

If core fields are missing or zero, return neutral output and let caller fallback to its rule-based logic.

Test-mode note:
- `a-stock-analysis` may pass data from a local fixture only when user explicitly enables `--use-local-fin-fixture`.
- Treat fixture data as regression-test input, not production market data.

## Input Format

Financial data can be provided as:
- CSV with financial line items
- JSON with structured financial statements
- Text description of key financial figures
- Excel files with financial statements

## Output Format

Results include:
- Calculated ratios with values
- Industry benchmark comparisons (when available)
- Trend analysis (if multiple periods provided)
- Interpretation and insights
- Excel report with formatted results

## Example Usage

"Calculate key financial ratios for this company based on the attached financial statements"

"What's the P/E ratio if the stock price is $50 and annual earnings are $2.50 per share?"

"Analyze the liquidity position using the balance sheet data"

## Scripts

- `calculate_ratios.py`: Main calculation engine for all financial ratios
- `interpret_ratios.py`: Provides interpretation and benchmarking

## Best Practices

1. Always validate data completeness before calculations
2. Handle missing values appropriately (use industry averages or exclude)
3. Consider industry context when interpreting ratios
4. Include period comparisons for trend analysis
5. Flag unusual or concerning ratios

## Limitations

- Requires accurate financial data
- Industry benchmarks are general guidelines
- Some ratios may not apply to all industries
- Historical data doesn't guarantee future performance
