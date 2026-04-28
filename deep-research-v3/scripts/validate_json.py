#!/usr/bin/env python3
"""
validate_json.py — 校验调研结果JSON是否覆盖所有fields.yaml定义的字段
用法: python validate_json.py -f fields.yaml -j result.json
"""
import json, sys, argparse
from pathlib import Path

def validate(fields_path: str, json_path: str) -> dict:
    with open(fields_path, encoding="utf-8") as f:
        fields = json.load(f)
    with open(json_path, encoding="utf-8") as f:
        result = json.load(f)

    required = [f["name"] for f in fields if f.get("required", True)]
    optional = [f["name"] for f in fields if not f.get("required", True)]
    all_fields = required + optional

    missing = []
    uncertain = result.get("uncertain", [])
    filled = {}

    for fname in all_fields:
        if fname in result and result[fname] not in (None, "", []):
            filled[fname] = result[fname]
        elif fname in uncertain:
            filled[fname] = "[不确定]"
        else:
            missing.append(fname)

    status = "PASS" if not missing else "FAIL"
    print(f"[{status}] 必填字段{len(required)}个，已填{len([f for f in required if f in filled])}个", flush=True)
    if missing:
        print(f"  ⚠️ 缺失字段: {missing}", flush=True)
    print(f"  ✅ 已填字段: {len(filled)}/{len(all_fields)}", flush=True)
    return {"status": status, "missing": missing, "filled": len(filled), "total": len(all_fields)}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--fields", required=True)
    ap.add_argument("-j", "--json", required=True)
    args = ap.parse_args()
    result = validate(args.fields, args.json)
    sys.exit(0 if result["status"] == "PASS" else 1)