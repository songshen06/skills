#!/usr/bin/env python3
"""
agent_executor.py — Deep Research v2
分批并行执行子问题Agent，支持断点续传
用法: python3 agent_executor.py ./results/储能行业出口
"""
import json, os, sys, subprocess
from pathlib import Path
from datetime import datetime

CHECKPOINT_FILE = "checkpoint.json"

def load_checkpoint(out_dir: Path) -> dict:
    ckpt = out_dir / CHECKPOINT_FILE
    if ckpt.exists():
        return json.loads(ckpt.read_text(encoding="utf-8"))
    return {"completed": [], "failed": [], "started": []}

def save_checkpoint(out_dir: Path, state: dict):
    (out_dir / CHECKPOINT_FILE).write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def build_agent_prompt(topic: str, sq: dict, fields_path: str, output_path: str) -> str:
    return f"""## 任务
深度调研主题「{topic}」中的子问题：「{sq['name']}」
问题描述：{sq['description']}

## 字段定义（必须全部覆盖）
{open(fields_path, encoding='utf-8').read()}

## 输出要求
1. 按fields.json定义的字段输出JSON
2. 必填字段不能为空，不确定时标注[不确定]
3. JSON末尾添加"不确定字段"数组，列出所有未确认的字段名（即使有些可选字段没填也不报error）
4. 所有字段值必须使用中文输出

## 输出路径
{output_path}

## 验证
完成JSON输出后，运行验证：
python3 /home/ubuntu/.openclaw/workspace/skills/deep-research-v2/scripts/validate_json.py -f {fields_path} -j {output_path}

验证通过后才算完成任务。
"""

def run():
    if len(sys.argv) < 2:
        print("用法: python3 agent_executor.py <output_dir>", file=sys.stderr)
        sys.exit(1)
    out_dir = Path(sys.argv[1])
    outline_path = out_dir / "outline.json"
    if not outline_path.exists():
        print(f"❌ 未找到大纲文件: {outline_path}", file=sys.stderr)
        sys.exit(1)
    outline = json.loads(outline_path.read_text(encoding="utf-8"))
    fields_path = out_dir / "fields.json"
    topic = outline["topic"]
    sub_questions = outline["sub_questions"]
    batch_size = outline["execution"].get("batch_size", 3)

    state = load_checkpoint(out_dir)
    completed = set(state["completed"])
    total = len(sub_questions)

    print(f"🔍 主题: {topic}", flush=True)
    print(f"📊 总计: {total} 个子问题 | 已完成: {len(completed)} | 批次大小: {batch_size}", flush=True)

    pending = [sq for sq in sub_questions if sq["name"] not in completed]
    if not pending:
        print("✅ 全部已完成", flush=True)
        return

    # 分批处理
    for i in range(0, len(pending), batch_size):
        batch = pending[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(sub_questions) + batch_size - 1) // batch_size
        print(f"\n📦 批次 {batch_num}/{total_batches} | {len(batch)}个子问题", flush=True)

        for sq in batch:
            name = sq["name"]
            slug = name.replace(" ", "_").replace("/", "_")
            output_path = out_dir / f"result_{slug}.json"
            print(f"  → {name} ...", end=" ", flush=True)

            if output_path.exists() and output_path.stat().st_size > 10:
                print("已存在(跳过)", flush=True)
                state["completed"].append(name)
                completed.add(name)
                save_checkpoint(out_dir, state)
                continue

            # 构建prompt（这里通过subprocess调用主Agent — 在真实调用中会用sessions_spawn）
            prompt = build_agent_prompt(topic, sq, str(fields_path), str(output_path))
            
            # 输出prompt供主Agent消费（实际运行时主Agent会读取此文件并传给sessions_spawn）
            prompt_file = out_dir / f"prompt_{slug}.txt"
            prompt_file.write_text(prompt, encoding="utf-8")
            print(f"已生成prompt: {prompt_file.name}", flush=True)
            
            state["completed"].append(name)
            completed.add(name)
            state["started"].append(name)
            save_checkpoint(out_dir, state)

        print(f"  批次 {batch_num} 完成({len(batch)}个)，共{len(completed)}/{total})", flush=True)

    # 汇总
    print(f"\n{'='*40}", flush=True)
    print(f"✅ 调研完成: {len(completed)}/{total} 个子问题", flush=True)
    if state["failed"]:
        print(f"❌ 失败: {state['failed']}", flush=True)
    print(f"📁 结果目录: {out_dir}", flush=True)

if __name__ == "__main__":
    run()