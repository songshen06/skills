---
name: a-stock-analysis
description: Comprehensive A-share (Chinese stock) analysis including fundamental analysis (financial metrics, business quality, valuation), technical analysis (indicators, chart patterns, support/resistance), stock comparisons, and investment report generation. Use when user requests analysis of A-share tickers (e.g., "analyze 茅台", "compare 比亚迪 vs 宁德时代", "give me a report on 中国平安"), evaluation of financial metrics, technical chart analysis, or investment recommendations for Chinese stocks. When `analyzing-financial-statements` skill exists locally, call it to enhance ratio calculation and interpretation.
---

# A-Stock Analysis (A股分析)

> 调用模型（最高优先级）  
> 本 skill 由 AI agent 编排触发；`scripts/*.py` 仅作为 agent 内部执行与回归测试工具，不是面向终端用户的独立入口。

当前版本以“可执行、可回退、可落盘、可网页展示”为优先，覆盖：
- 个股分析（stock）
- 指数分析（index）
- 行业分析（sector）
- 模板化 Markdown 报告生成
- 网页版 HTML 报告（含图表与完整正文渲染）
- 报告尾部可配置的主观点评（rule / agent / hybrid）

## Repository Layout

- `scripts/quick_report.py`: 快速生成三类报告（推荐入口）
- `scripts/index_analyzer.py`: 指数分析主入口（含缓存与数据源回退）
- `scripts/eastmoney_api.py`: 东方财富数据接口（含实时行情与指数回退函数）
- `scripts/akshare_api.py`: AKShare 数据接口与能力补充（含三大财报）
- `scripts/templates/engine.py`: 报告模板渲染引擎
- `scripts/templates/web_renderer.py`: 网页报告渲染器（卡片+图表+Markdown正文）
- `templates/*.md`: 报告模板（个股/指数/行业）
- `references/report-template.md`: 报告结构参考

## Maintenance Setup (仅维护/调试)

在仓库根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

模板渲染自测：

```bash
python3 scripts/test_templates.py
python3 scripts/test_regressions.py
```

## Agent Internal Execution Examples (仅 agent 内部执行)

### 1) 快速报告（推荐）

```bash
python3 scripts/quick_report.py stock 600519 "贵州茅台"
python3 scripts/quick_report.py index 000922 "中证红利"
python3 scripts/quick_report.py sector 000986 "能源行业"
python3 scripts/quick_report.py stock 000589 "贵州轮胎" --output "贵州轮胎_报告.md"
python3 scripts/quick_report.py index 000922 --template templates/index_report_template.md
python3 scripts/quick_report.py stock 000589 "贵州轮胎" --format html --output "贵州轮胎_报告.html"
# 仅联调/回归测试使用：启用本地财报测试夹具
python3 scripts/quick_report.py stock 000589 "贵州轮胎" --use-local-fin-fixture
# 当财报缓存为空/无效时，允许单次强制实时重取（默认关闭）
python3 scripts/quick_report.py stock 600941 "中国移动" --force-live-on-empty-cache
# 混合点评 + HTML（低token推荐）
python3 scripts/quick_report.py stock 000589 "贵州轮胎" \
  --format html \
  --narrative-mode hybrid \
  --narrative-file /path/to/agent_narrative.md
```

点评模式（主观文案）：

```bash
# 规则文案（默认）
python3 scripts/quick_report.py stock 000589 "贵州轮胎" --narrative-mode rule

# Agent注入文案（推荐给 Codex/OpenClaw 技能场景）
python3 scripts/quick_report.py stock 000589 "贵州轮胎" \
  --narrative-mode agent \
  --narrative-file /path/to/agent_narrative.md

# 混合模式（规则 + Agent）
python3 scripts/quick_report.py stock 000589 "贵州轮胎" \
  --narrative-mode hybrid \
  --narrative-text "- 核心判断 ... "
```

### 2) 指数分析器

```bash
python3 scripts/index_analyzer.py 000922 --name "中证红利"
python3 scripts/index_analyzer.py 000300 --template templates/index_report_template.md --output "沪深300_分析.md"
```

### 3) 数据接口冒烟测试

```bash
python3 scripts/eastmoney_api.py
python3 scripts/akshare_api.py
```

说明：`eastmoney_api.py` / `akshare_api.py` 当前入口是测试模式，不是“传代码直接落 JSON 文件”的 CLI。

## Data Source Strategy

指数数据优先级（`index_analyzer.py`）：
1. 本地缓存
2. AKShare
3. EastMoney 回退（`fetch_index_data`）

个股财务数据优先级（`quick_report.py`）：
1. EastMoney（利润表/资产负债表/现金流）
2. 有效性校验（占位空表会判定为无效）
3. AKShare 回退（优先 `stock_financial_report_sina`，空数据再回退到 EM 报表接口）
4. 全空自动重取：若三大财报均为空/无效，自动触发一次 live 重取（仅一次）
5. 可选空缓存重取：显式传入 `--force-live-on-empty-cache` 时，对单表空缓存直接启用单次绕过缓存重取

个股行业分类优先级（`quick_report.py`）：
1. 申万一级直连：`akshare_api.get_sw_level1_industry(stock_code)`（按申万一级指数成分股匹配）
2. 大模型推荐回退：基于股票名/行业提示词进行申万一级推荐（仅在直连失败时触发）

估值行业因子（`quick_report.py`）：
1. 基于申万一级行业选择估值参数档位（增长率/WACC/相对估值权重）
2. 若行业未命中配置，回退到通用参数档位
3. 在附录 B 中输出“行业因子来源”和权重明细，保证可追溯

执行原则：
- 优先返回成功源，不阻塞在单一数据源失败。
- 明确记录错误并继续降级。
- 输出里标明关键字段是否缺失（例如估值字段暂不可得时为 `N/A`）。

## Cross-Skill Integration (财务计算联动)

当目录中存在 `../analyzing-financial-statements/calculate_ratios.py` 时，个股分析需要自动启用财务计算增强：
1. 先走本技能原有数据拉取与缓存链路（实时行情/K线/三大财报）。
2. 组装标准财务载荷（income_statement / balance_sheet / cash_flow / market_data）。
3. 调用 `calculate_ratios_from_data(..., lang="zh")`。
4. 用结果回填关键字段：`ROE/ROA/流动比率/速动比率/利息保障倍数/EV-EBITDA/PS` 等。
5. 在附录 `B. 估值模型详细计算` 中补齐 `DCF模型参数与结果` 与 `相对估值法详细计算` 的可追溯明细。
6. 若财务数据不足（核心字段全空或全零），跳过增强并保留原始回退逻辑，不输出误导性结论。

调用保障策略（必须遵守）：
- 优先“可用即调用”：先探测本地文件是否存在，再动态加载函数。
- 失败不阻塞主流程：联动失败只降级，不应导致报告生成失败。
- 缓存优先：默认走缓存；当三表全空时自动单次 live 重取，或显式启用 `--force-live-on-empty-cache` 时对单表启用单次重取。
- 本地夹具显式开关：仅当传入 `--use-local-fin-fixture` 时才允许读取 `scripts/cache/local_financial_fixtures.json`。
- 行业口径统一：报告中的“所属行业”优先展示申万一级，必要时标注 LLM 推荐。

## Template Engine Reality (当前实现边界)

`templates/engine.py` 已实现：
- `{{variable}}` 变量替换
- 未渲染变量回填 `N/A`
- 保留 Markdown 空行结构

当前未实现（不要在分析中假设可用）：
- 条件渲染（`if`）
- 自动表格对齐
- 图表渲染
- 模板继承

## Analysis Workflow (Agent-Orchestrated)

### A. 用户要“快速报告”
1. Agent 识别请求类型（stock/index/sector）并选择对应执行路径。
2. Agent 组装参数（模板、格式、点评模式、是否测试夹具）并调用内部脚本层。
3. Agent 校验输出完整性（关键字段、降级标记、来源标记）。
4. 若需要网页展示，Agent 选择 HTML 渲染路径。
5. 若需要主观点评，Agent 以 `rule/agent/hybrid` 方式注入点评文本。

### B. 用户要“指数深度分析”
1. Agent 调用指数分析链路获取基础信息与成分股。
2. Agent 识别输出状态：`success` / `partial` / `failed`。
3. 仅在用户需要报告时进行模板渲染与落盘。

### C. 用户要“数据真实性校验”
1. Agent 通过行情接口能力进行字段核验（必要时走内部冒烟脚本）。
2. 关键字段建议至少核对：`最新价`、`涨跌幅`、`换手率`、`市盈率(动)`、`总市值(亿)`、`流通市值(亿)`。

## Output Standard

生成报告时保持以下最小结构：
- 标的与代码
- 报告日期
- 关键行情（价格、涨跌、成交、换手）
- 估值与结论（可得则给值，不可得写 `N/A` 并说明）
- 风险点与催化因素
- 免责声明

增强输出（当前已实现）：
- 技术分析：趋势、均线、MACD、RSI、KDJ、BOLL、量价、技术评分
- 策略区：短/中/长周期动作、入场/止损/目标、仓位建议
- 估值区：DCF 三情景 + 相对估值 + 目标情景概率
- 财务摘要：利润表/资产负债表/现金流三表（近三期，按 `YYYYQx`）
- 盈利能力核心四项：`营收同比/净利同比/ROE/ROA`（含 ROE/ROA 期间变化 `pct`）
- 网页版：核心指标卡 + 决策雷达 + 目标达成视图 + 完整报告渲染
- 网页版新增：`行业因子估值设置` 卡片（行业、档位来源、增长率、WACC、PE/PB/PEG/EV 权重）
- 报告尾部：`大模型点评 (Narrative)`，并标注实际来源（rule / agent / fallback）

### 大模型点评低Token约束（Agent调用）

仅向大模型传“压缩特征包”，不要传整份报告正文。建议字段不超过 25 个：
- 基础：`stock_code` `stock_name` `current_price` `report_date`
- 行业与估值：`industry` `valuation_profile_source` `wacc` `base_growth` `base_dcf_value` `bull_dcf_value` `bear_dcf_value` `avg_target` `avg_upside`
- 财务核心：`revenue_yoy` `profit_yoy` `roe` `roa` `current_ratio` `quick_ratio` `debt_to_asset` `interest_coverage` `free_cash_flow`
- 市场技术：`change_pct` `turnover_rate` `short_trend` `technical_score` `short_support` `short_resistance`
- 风险结论：`risk_level` `top_risks(<=3)` `top_catalysts(<=3)` `investment_rating`

输出格式建议（固定4句）：
1. 核心判断（评级+一句话）
2. 看多逻辑（1句）
3. 主要风险（1句）
4. 执行建议（1句，含仓位或止损）

推荐使用 `--narrative-mode hybrid`：
- `rule` 负责结构化兜底
- `agent` 只补判断句，控制 token 消耗

## Troubleshooting

- 模板文件找不到：优先用 `templates/*.md` 的相对路径。
- EastMoney 接口异常：先重试，再走 AKShare 或缓存。
- 输出内容过短：检查模板变量名是否与数据字典一致。
- 指数分析失败：查看 `errors` 列表，确认是否为单源故障。
- `agent` 模式无点评：确认传入 `--narrative-file` / `--narrative-text` 或环境变量 `AGENT_NARRATIVE_TEXT`。
- shell 传多行失败：优先用 `--narrative-file`，避免 `\n` 转义问题。

## Example Queries

- “分析一下贵州轮胎 000589，给我简版报告”
- “对比宁德时代 300750 和 比亚迪 002594 的估值”
- “生成中证红利 000922 的指数报告，输出到本地文件”
- “看一下银行板块的风险和催化因素”
- “出一个网页版，包含完整报告和点评”
- “点评用规则还是 agent 注入，我要可切换”

## Notes

- 本技能用于研究和信息整理，不构成投资建议。
- 遇到实时数据口径冲突时，以当次接口返回为准并在结论里注明时间戳。
- 本技能面向 agent 编排：脚本不内置外部 LLM 请求，主观文案由上层 agent 注入。
- 调用约束：此技能由 AI agent 编排触发，`scripts/*.py` 仅作为 agent 内部执行工具，不作为面向终端用户的独立产品入口。
