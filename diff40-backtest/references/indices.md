# CSI Index Codes Reference

## Core Indices

| Code | Name | Description | Type |
|------|------|-------------|------|
| 000922 | CSI Dividend | 中证红利价格指数 | Price |
| H00922 | CSI Dividend TR | 中证红利全收益 | Total Return |
| 000510 | CSI A500 | 中证A500价格指数 | Price |
| 000985 | CSI All Share | 中证全指 | Price |
| 000300 | CSI 300 | 沪深300 | Price |
| 000905 | CSI 500 | 中证500 | Price |
| 000852 | CSI 1000 | 中证1000 | Price |
| 399006 | ChiNext | 创业板指 | Price |
| H11052 | CSI Dividend Quality | 中证红利质量 | Price |

## Data Source

All indices fetched via `akshare.stock_zh_index_hist_csindex(symbol, start_date, end_date)`.
Returns DataFrame with columns: 日期, 指数代码, 开盘, 最高, 最低, 收盘, 涨跌, 涨跌幅, etc.

Note: Total return indices (H prefix) typically only have 收盘 populated; OHLC are NaN.

## Common Pairs for DIFF40 Analysis

| Pair | Logic |
|------|-------|
| H00922 vs 000985 | Dividend TR vs All Share (classic EarlETF pair) |
| 000922 vs 000510 | Dividend vs A500 (ETF rotation pair) |
| 000922 vs 399006 | Dividend vs ChiNext (value vs growth) |
| 000922 vs 000300 | Dividend vs CSI 300 |

## Important

For rotation/rebalancing with ETFs, use price indices (not TR) since ETF NAV tracks price.
For total return comparison, use TR indices with H prefix.