#!/usr/bin/env python3
"""
outline_generator.py — Deep Research v2
生成结构化调研大纲（outline.yaml），管理断点续传状态
用法: python3 outline_generator.py "储能行业出口" ./results
"""
import json, os, sys, hashlib
from pathlib import Path
from datetime import datetime
import requests

NVIDIA_KEY = os.environ.get("NVIDIA_API_KEY", "")
ENDPOINT = "https://inference-api.nvidia.com/v1/search/perplexity-search"

def ps(query, max_r=6, days=90, country="CN"):
    payload = {"query": query, "max_r": max_r}
    if days:
        payload["recency_days"] = days
    r = requests.post(ENDPOINT,
        headers={"Authorization": f"Bearer {NVIDIA_KEY}", "Content-Type": "application/json"},
        json=payload, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])

def generate_outline(topic: str, output_dir: str = "./results"):
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 核心调研维度（对应投资研报需要的信息）
    sub_questions = [
        {"name": "市场规模与增速", "description": f"{topic}的市场规模、主要厂商、市场份额、近3年复合增速，带具体数字和来源"},
        {"name": "政策环境", "description": f"{topic}相关的国家/地方政策、补贴机制、136号文等重大政策影响"},
        {"name": "竞争格局", "description": f"{topic}的竞争格局、龙头公司（A股代码）、护城河分析、市场集中度变化"},
        {"name": "投资逻辑", "description": f"{topic}的受益方向、具体A股标的（代码+名称+逻辑+当前状态）、ETF推荐"},
        {"name": "主要风险", "description": f"{topic}的主要风险：估值风险、政策风险、竞争风险、供应链风险，附触发条件和可能跌幅"},
        {"name": "出口与海外市场", "description": f"{topic}的出口情况、欧洲/东南亚/中东市场差异、关税影响、 海外运营商合作"},
        {"name": "未来趋势", "description": f"{topic}的3年预测、量价数据、技术路线变化、机构预期差"},
    ]

    # 字段定义（每项都要填这些）
    fields = [
        {"name": "核心观点", "type": "text", "required": True,
         "description": "用3句话总结最重要判断"},
        {"name": "关键数字", "type": "text", "required": True,
         "description": "列出最重要3个数字，并注明来源和日期"},
        {"name": "反直觉发现", "type": "text", "required": True,
         "description": "相比市场共识的最大亮点或反直觉发现"},
        {"name": "受益标的", "type": "text", "required": False,
         "description": "高确定性A股（代码+名称+逻辑+当前状态强势/整理）"},
        {"name": "ETF推荐", "type": "text", "required": False,
         "description": "ETF代码+适合策略（定投/均线回归/支撑位）"},
        {"name": "回避标的", "type": "text", "required": False,
         "description": "不宜买入的标的+理由"},
        {"name": "最大风险", "type": "text", "required": True,
         "description": "逻辑崩塌的前提假设，触发条件，可能跌幅"},
        {"name": "跟踪指标", "type": "text", "required": False,
         "description": "可量化验证的跟踪指标（政策/价格/出货量）"},
        {"name": "时间轴", "type": "text", "required": True,
         "description": "关键时间节点表（2024-2027），区分已发生/预期/不确定"},
        {"name": "不确定字段", "type": "array", "required": False,
         "description": "列出所有[不确定]字段名，方便后续补充调研"},
    ]

    outline = {
        "topic": topic,
        "generated_at": datetime.now().isoformat(),
        "sub_questions": sub_questions,
        "fields": fields,
        "execution": {
            "batch_size": 3,
            "items_per_agent": 2,
            "checkpoint_file": str(out_dir / "checkpoint.json"),
        }
    }

    outline_path = out_dir / "outline.yaml"
    # 注意：用JSON存(outline_yaml太随意)，实际存json但叫yaml方便理解
    outline_json = out_dir / "outline.json"
    outline_json.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    fields_path = out_dir / "fields.json"
    fields_path.write_text(json.dumps(fields, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"📋 大纲生成完成: {outline_json}", flush=True)
    print(f"   子问题数: {len(sub_questions)}", flush=True)
    print(f"   字段定义: {len(fields)}个（必填{len([f for f in fields if f.get('required',True)])}个）", flush=True)
    return str(outline_json), str(fields_path), str(out_dir)

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "储能行业出口"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "./results"
    outline_path, fields_path, out_dir = generate_outline(topic, out_dir)
    print("\n===== OUTLINE_PATH =====", flush=True)
    print(outline_path, flush=True)
    print("===== FIELDS_PATH =====", flush=True)
    print(fields_path, flush=True)
    print("===== OUTPUT_DIR =====", flush=True)
    print(out_dir, flush=True)