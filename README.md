# Skills Repository

该仓库包含两个可由 AI agent 编排调用的技能（skill）：

- `a-stock-analysis`
- `analyzing-financial-statements`

## 1) a-stock-analysis

用途：
- A 股个股 / 指数 / 行业分析
- 生成 Markdown 与 HTML 报告
- 支持 rule / agent / hybrid 点评模式

入口（agent 内部执行）：
- `a-stock-analysis/scripts/quick_report.py`

示例：

```bash
python a-stock-analysis/scripts/quick_report.py stock 600941 "中国移动" \
  --narrative-mode hybrid \
  --output a-stock-analysis/test_output/中国移动_分析报告.md
```

测试开关（建议仅测试环境启用）：
- `--use-local-fin-fixture`：启用本地财报夹具回退
- `--force-live-on-empty-cache`：财报缓存为空/无效时，单次强制实时重取

## 2) analyzing-financial-statements

用途：
- 基于三大报表计算关键财务比率
- 作为 `a-stock-analysis` 的增强模块被自动加载

关键文件：
- `analyzing-financial-statements/calculate_ratios.py`
- `analyzing-financial-statements/interpret_ratios.py`
- `analyzing-financial-statements/SKILL.md`

## Agent 调用建议

- 以 agent 编排为主，不面向终端用户直接调用脚本。
- `a-stock-analysis` 负责数据抓取、报告结构和渲染。
- `analyzing-financial-statements` 负责财务指标计算与解释增强。
- 生产默认关闭测试开关；仅在排障或回归测试时开启。

## 目录结构

```text
.
├── a-stock-analysis/
└── analyzing-financial-statements/
```
