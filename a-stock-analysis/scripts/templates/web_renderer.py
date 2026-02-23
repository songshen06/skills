#!/usr/bin/env python3
"""Web report renderer for A-share analysis."""

import json
from typing import Any, Dict, List, Tuple


def _numeric(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("%", "").replace(",", "").replace("+", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return default
    return default


def _fmt_num(value: Any, digits: int = 2) -> str:
    if value is None or value == "N/A":
        return "N/A"
    num = _numeric(value, None)
    if num is None:
        return str(value)
    return f"{num:,.{digits}f}"


def _name_by_type(report_type: str, data: Dict[str, Any]) -> str:
    if report_type == "stock":
        return data.get("stock_name", "未知标的")
    if report_type == "index":
        return data.get("index_name", "未知指数")
    return data.get("sector_name", "未知行业")


def _code_by_type(report_type: str, data: Dict[str, Any]) -> str:
    if report_type == "stock":
        return data.get("stock_code", "N/A")
    if report_type == "index":
        return data.get("index_code", "N/A")
    return data.get("sector_code", "N/A")


def _primary_price(report_type: str, data: Dict[str, Any]) -> float:
    if report_type == "stock":
        return _numeric(data.get("current_price"))
    return _numeric(data.get("current_level"))


def _target_price(data: Dict[str, Any], current: float) -> float:
    target = _numeric(data.get("target_price"), 0.0)
    if target > 0:
        return target
    return current


def _risk_score(risk_level: str) -> float:
    mapping = {
        "低风险": 82,
        "中等风险": 62,
        "高风险": 38,
    }
    return float(mapping.get(risk_level, 55))


def _clamp_score(x: float) -> float:
    return float(max(0, min(100, round(x, 1))))


def _score_pack(report_type: str, data: Dict[str, Any]) -> List[float]:
    pe = _numeric(data.get("pe_ttm"), 18)
    pb = _numeric(data.get("pb"), 2)
    roe = _numeric(data.get("roe"), 10)
    dy = _numeric(data.get("dividend_yield"), 2)
    momentum = _numeric(data.get("level_change"), _numeric(data.get("upside_potential"), 0))

    valuation = _clamp_score(65 - (pe - 15) * 1.2 - (pb - 1.5) * 8)
    quality = _clamp_score(roe * 4 + dy * 6)
    trend = _clamp_score(50 + momentum * 8)
    risk = _risk_score(str(data.get("risk_level", "中等风险")))

    if report_type == "index":
        rp = _numeric(data.get("risk_premium"), 5)
        quality = _clamp_score(50 + rp * 6)

    return [valuation, quality, trend, risk]


def _metric_rows(report_type: str, data: Dict[str, Any]) -> List[Tuple[str, str]]:
    if report_type == "stock":
        return [
            ("当前价格", _fmt_num(data.get("current_price"))),
            ("目标价格", _fmt_num(data.get("target_price"))),
            ("市盈率(PE)", _fmt_num(data.get("pe_ttm"))),
            ("市净率(PB)", _fmt_num(data.get("pb"))),
            ("ROE", f"{_fmt_num(data.get('roe'))}%"),
            ("股息率", f"{_fmt_num(data.get('dividend_yield'))}%"),
        ]
    if report_type == "index":
        return [
            ("当前点位", _fmt_num(data.get("current_level"))),
            ("目标点位", _fmt_num(data.get("target_price"))),
            ("涨跌幅", str(data.get("level_change", "N/A"))),
            ("市盈率(PE)", _fmt_num(data.get("pe_ttm"))),
            ("市净率(PB)", _fmt_num(data.get("pb"))),
            ("风险溢价", _fmt_num(data.get("risk_premium"))),
        ]
    return [
        ("当前点位", _fmt_num(data.get("current_level"))),
        ("目标点位", _fmt_num(data.get("target_price"))),
        ("市盈率(PE)", _fmt_num(data.get("pe_ttm"))),
        ("市净率(PB)", _fmt_num(data.get("pb"))),
        ("ROE", f"{_fmt_num(data.get('roe'))}%"),
        ("股息率", f"{_fmt_num(data.get('dividend_yield'))}%"),
    ]


def _split_points(text: Any) -> List[str]:
    raw = str(text or "").strip()
    if not raw or raw == "N/A":
        return []
    parts = [p.strip(" -") for p in raw.replace("\n", "；").split("；")]
    return [p for p in parts if p]


def _core_point_lists(data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    bullish = _split_points(data.get("bullish_thesis"))
    bearish = _split_points(data.get("bearish_risks"))
    if not bullish:
        bullish = [
            str(data.get("bullish_point_1", "N/A")),
            str(data.get("bullish_point_2", "N/A")),
            str(data.get("bullish_point_3", "N/A")),
        ]
    if not bearish:
        bearish = [
            str(data.get("bearish_point_1", "N/A")),
            str(data.get("bearish_point_2", "N/A")),
            str(data.get("bearish_point_3", "N/A")),
        ]
    return bullish[:3], bearish[:3]


def render_web_report(
    report_type: str, data: Dict[str, Any], full_markdown: str = ""
) -> str:
    """Render a standalone HTML report with modern, report-first layout."""
    name = _name_by_type(report_type, data)
    code = _code_by_type(report_type, data)
    report_date = data.get("report_date", "N/A")
    rating = data.get("investment_rating", "中性")
    risk_level = data.get("risk_level", "中等风险")
    upside = data.get("upside_potential", "N/A")
    catalysts = data.get("catalysts", "N/A")
    risk_description = data.get("risk_description", "N/A")

    rows = _metric_rows(report_type, data)
    row_html = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)

    bullish, bearish = _core_point_lists(data)
    bullish_html = "".join(f"<li>{item}</li>" for item in bullish)
    bearish_html = "".join(f"<li>{item}</li>" for item in bearish)

    current = _primary_price(report_type, data)
    target = _target_price(data, current)
    diff_abs = target - current
    diff_pct = (diff_abs / current * 100) if current > 0 else 0.0
    current_idx = 100.0
    target_idx_raw = (target / current * 100) if current > 0 else 100.0
    target_idx = max(0.0, min(200.0, target_idx_raw))
    score_labels = ["估值性价比", "经营质量", "趋势结构", "风险控制"]
    score_values = _score_pack(report_type, data)
    industry = str(data.get("industry", "待补充"))
    sub_industry = str(data.get("sub_industry", "待补充"))
    profile_src = str(data.get("valuation_profile_source", "default_profile"))
    base_growth = str(data.get("base_growth", "N/A"))
    bull_growth = str(data.get("bull_growth", "N/A"))
    bear_growth = str(data.get("bear_growth", "N/A"))
    wacc = str(data.get("wacc", "N/A"))
    pe_weight = str(data.get("pe_weight", "25%"))
    pb_weight = str(data.get("pb_weight", "25%"))
    peg_weight = str(data.get("peg_weight", "25%"))
    ev_weight = str(data.get("ev_weight", "25%"))
    profile_badge = "行业档位" if profile_src == "industry_profile" else "通用档位"

    hero_value_label = "当前价格" if report_type == "stock" else "当前点位"
    hero_value = _fmt_num(current)
    risk_company = str(data.get("company_specific_risks", "暂无")).split("；")[0]
    risk_industry = str(data.get("industry_risks", "暂无")).split("；")[0]
    risk_macro = str(data.get("macro_risks", "暂无")).split("；")[0]
    risk_market = str(data.get("market_risks", "暂无")).split("；")[0]

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{name} ({code}) 分析报告</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    :root {{
      --bg: #f7f9f6;
      --panel: #ffffff;
      --ink: #15221f;
      --sub: #576a63;
      --brand: #0e6b63;
      --brand-2: #0b4f49;
      --good: #1b8e5f;
      --risk: #bf4b36;
      --line: #d7e1db;
      --accent: #d98a2f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Manrope", "PingFang SC", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(1000px 380px at -10% -5%, #d8efe7 0%, transparent 60%),
        radial-gradient(900px 320px at 120% 0%, #f4e4cf 0%, transparent 58%),
        var(--bg);
    }}
    .wrap {{ max-width: 1160px; margin: 0 auto; padding: 24px; }}
    .hero {{
      border: 1px solid var(--line);
      border-radius: 20px;
      background: linear-gradient(140deg, #0d5f57 0%, #0f6f66 48%, #227a67 100%);
      color: #f8fffd;
      padding: 24px;
      box-shadow: 0 18px 30px rgba(14, 58, 53, 0.2);
    }}
    .hero h1 {{ margin: 0; font-size: 34px; letter-spacing: 0.2px; }}
    .meta {{ margin-top: 8px; opacity: 0.95; }}
    .hero-grid {{ margin-top: 16px; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
    .hero-card {{ background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.28); border-radius: 12px; padding: 10px 12px; }}
    .hero-label {{ font-size: 12px; opacity: 0.9; }}
    .hero-value {{ margin-top: 3px; font-size: 20px; font-weight: 700; }}

    .grid {{ margin-top: 16px; display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 16px; }}
    .p-4 {{ grid-column: span 4; }}
    .p-5 {{ grid-column: span 5; }}
    .p-6 {{ grid-column: span 6; }}
    .p-7 {{ grid-column: span 7; }}
    .p-12 {{ grid-column: span 12; }}
    .panel h3 {{ margin: 0 0 12px 0; font-size: 18px; letter-spacing: -0.01em; }}
    .equal-card {{ min-height: 340px; display: flex; flex-direction: column; }}
    .chart-wrap {{ position: relative; height: 220px; }}
    .table-wrap {{ flex: 1; }}

    .metric-table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    .metric-table th, .metric-table td {{ border-bottom: 1px solid #e7edf3; padding: 9px 8px; font-size: 14px; }}
    .metric-table th {{ text-align: left; color: var(--sub); font-weight: 600; width: 42%; }}
    .metric-table td {{ text-align: right; font-weight: 600; width: 58%; }}

    .list {{ margin: 0; padding-left: 18px; }}
    .list li {{ margin-bottom: 8px; line-height: 1.5; }}
    .bull li::marker {{ color: var(--good); }}
    .bear li::marker {{ color: var(--risk); }}

    .risk-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }}
    .risk-cell {{
      border: 1px solid #e2e8e4;
      border-radius: 10px;
      padding: 10px;
      background: #fbfdfc;
    }}
    .risk-cell strong {{ color: #29453e; font-size: 13px; }}
    .risk-cell p {{ margin: 6px 0 0; font-size: 13px; color: var(--sub); line-height: 1.5; }}

    .tip-line {{ margin: 0 0 8px 0; }}
    .tip-good {{ color: var(--good); }}
    .tip-risk {{ color: var(--risk); }}
    .prose {{
      line-height: 1.72;
      color: #233444;
      font-size: 15px;
    }}
    .prose h1, .prose h2, .prose h3 {{ color: #17324a; margin-top: 1.1em; }}
    .prose {{ overflow-x: auto; }}
    .prose table {{
      border-collapse: collapse;
      width: max-content;
      min-width: 100%;
      table-layout: auto;
      margin: 0.6em 0 0.9em 0;
      background: #fff;
    }}
    .prose th, .prose td {{
      border: 1px solid #e1e8ef;
      padding: 8px 10px;
      vertical-align: top;
      text-align: left;
      line-height: 1.5;
      white-space: normal;
      word-break: break-word;
    }}
    .prose th {{
      background: #f6f9fc;
      color: #2f475d;
      font-weight: 600;
    }}
    .prose blockquote {{
      margin: 0.8em 0;
      padding: 0.4em 0.9em;
      border-left: 4px solid #bdd5ea;
      background: #f7fbff;
      color: #36516a;
    }}
    .prose code {{
      background: #edf3f8;
      border-radius: 4px;
      padding: 2px 6px;
      font-size: 0.92em;
    }}
    .prose pre {{
      background: #0f1720;
      color: #e6edf3;
      border-radius: 10px;
      padding: 12px;
      overflow-x: auto;
    }}

    @media (max-width: 760px) {{
      .hero-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .p-4, .p-5, .p-6, .p-7 {{ grid-column: span 12; }}
      .hero h1 {{ font-size: 28px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>{name} ({code})</h1>
      <div class="meta">报告日期：{report_date}</div>
      <div class="hero-grid">
        <div class="hero-card">
          <div class="hero-label">{hero_value_label}</div>
          <div class="hero-value">{hero_value}</div>
        </div>
        <div class="hero-card">
          <div class="hero-label">投资评级</div>
          <div class="hero-value">{rating}</div>
        </div>
        <div class="hero-card">
          <div class="hero-label">风险等级</div>
          <div class="hero-value">{risk_level}</div>
        </div>
        <div class="hero-card">
          <div class="hero-label">预期空间</div>
          <div class="hero-value">{upside}</div>
        </div>
      </div>
    </section>

    <section class="grid">
      <div class="panel p-4 equal-card">
        <h3>核心指标</h3>
        <div class="table-wrap">
          <table class="metric-table">{row_html}</table>
        </div>
      </div>

      <div class="panel p-4 equal-card">
        <h3>决策评分雷达</h3>
        <div class="chart-wrap">
          <canvas id="scoreRadar"></canvas>
        </div>
      </div>

      <div class="panel p-4 equal-card">
        <h3>目标空间（当前 vs 目标）</h3>
        <div class="chart-wrap">
          <canvas id="targetBullet"></canvas>
        </div>
        <div style="margin-top:10px;border-top:1px solid #e7edf3;padding-top:10px;">
          <p class="tip-line"><strong>图表量程：</strong>固定 0-200（当前=100）</p>
          <p class="tip-line"><strong>当前值：</strong>{_fmt_num(current)}</p>
          <p class="tip-line"><strong>目标值：</strong>{_fmt_num(target)}</p>
          <p class="tip-line"><strong>绝对差：</strong>{_fmt_num(diff_abs)} </p>
          <p class="tip-line"><strong>百分比差：</strong>{diff_pct:+.2f}%</p>
        </div>
      </div>

      <div class="panel p-6">
        <h3>看多逻辑</h3>
        <ul class="list bull">{bullish_html}</ul>
      </div>

      <div class="panel p-6">
        <h3>风险与反方逻辑</h3>
        <ul class="list bear">{bearish_html}</ul>
      </div>

      <div class="panel p-12">
        <h3>催化与风险说明</h3>
        <p class="tip-line tip-good"><strong>催化因素：</strong>{catalysts}</p>
        <p class="tip-line tip-risk"><strong>风险说明：</strong>{risk_description}</p>
      </div>

      <div class="panel p-12">
        <h3>风险矩阵（定性）</h3>
        <div class="risk-grid">
          <div class="risk-cell"><strong>公司层面</strong><p>{risk_company}</p></div>
          <div class="risk-cell"><strong>行业层面</strong><p>{risk_industry}</p></div>
          <div class="risk-cell"><strong>宏观层面</strong><p>{risk_macro}</p></div>
          <div class="risk-cell"><strong>市场层面</strong><p>{risk_market}</p></div>
        </div>
      </div>

      <div class="panel p-12">
        <h3>行业因子估值设置</h3>
        <table class="metric-table">
          <tr><th>行业分类</th><td>{industry} / {sub_industry}</td></tr>
          <tr><th>参数档位</th><td>{profile_badge}（{profile_src}）</td></tr>
          <tr><th>增长率(基准/乐观/悲观)</th><td>{base_growth} / {bull_growth} / {bear_growth}</td></tr>
          <tr><th>WACC</th><td>{wacc}</td></tr>
          <tr><th>相对估值权重(PE/PB/PEG/EV)</th><td>{pe_weight} / {pb_weight} / {peg_weight} / {ev_weight}</td></tr>
        </table>
      </div>

      <div class="panel p-12">
        <h3>完整报告</h3>
        <div id="fullReport" class="prose"></div>
      </div>
    </section>
  </div>

  <script>
    const scoreLabels = {json.dumps(score_labels, ensure_ascii=False)};
    const scoreValues = {json.dumps(score_values, ensure_ascii=False)};

    new Chart(document.getElementById('scoreRadar'), {{
      type: 'radar',
      data: {{
        labels: scoreLabels,
        datasets: [{{
          label: '评分',
          data: scoreValues,
          backgroundColor: 'rgba(19,111,159,0.18)',
          borderColor: '#136f9f',
          pointBackgroundColor: '#0f4c81',
          pointRadius: 3
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          r: {{
            min: 0,
            max: 100,
            ticks: {{ stepSize: 20, backdropColor: 'transparent' }},
            grid: {{ color: '#dfe7ef' }},
            angleLines: {{ color: '#dfe7ef' }}
          }}
        }}
      }}
    }});

    new Chart(document.getElementById('targetBullet'), {{
      type: 'bar',
      data: {{
        labels: ['当前值', '目标值'],
        datasets: [{{
          data: [{current_idx}, {target_idx}],
          backgroundColor: ['#4d7ea8', '#0f8b5f'],
          borderRadius: 8,
          maxBarThickness: 24
        }}]
      }},
      options: {{
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        normalized: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{
            beginAtZero: true,
            min: 0,
            max: 200,
            grid: {{ color: '#e8eef4' }},
            ticks: {{
              stepSize: 50,
              callback: (v) => v + ' idx'
            }}
          }},
          y: {{ grid: {{ display: false }} }}
        }}
      }}
    }});

    const markdownSource = {json.dumps(full_markdown, ensure_ascii=False)};
    const fullReportEl = document.getElementById('fullReport');
    if (markdownSource && markdownSource.trim()) {{
      fullReportEl.innerHTML = marked.parse(markdownSource);
    }} else {{
      fullReportEl.innerHTML = '<p>暂无完整正文，可通过 --template 指定报告模板。</p>';
    }}
  </script>
</body>
</html>
"""
