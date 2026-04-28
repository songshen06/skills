import json, os, sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

NVIDIA_KEY = os.environ.get("NVIDIA_API_KEY", "")
ENDPOINT = "https://inference-api.nvidia.com/v1/search/perplexity-search"

def ps(query, max_r=8, days=90, country="CN"):
    payload = {"query": query, "max_results": max_r}
    if days:
        payload["recency_days"] = days
    if country:
        payload["country"] = country
    r = requests.post(ENDPOINT,
        headers={"Authorization": f"Bearer {NVIDIA_KEY}", "Content-Type": "application/json"},
        json=payload, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])

def search_all(queries):
    def go(q):
        try:
            res = ps(q["query"], max_r=q.get("max_r", 8), days=q.get("days", 90), country=q.get("country","CN"))
            for r in res:
                r["_query"] = q["query"]
            return res
        except:
            return []
    out = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(go, q) for q in queries]
        for f in as_completed(futs):
            out.extend(f.result())
    seen = set()
    d = []
    for r in out:
        u = r.get("url","")
        if u and u not in seen:
            seen.add(u)
            d.append(r)
    return d

def decompose(topic):
    return [
        topic + " definition, market size and core data",
        topic + " policy environment and support framework",
        topic + " competitive landscape and leading companies (with stock codes and business descriptions)",
        topic + " investment logic and beneficiary direction (specific A-share stocks, ETFs and investment strategies)",
        topic + " main risks and constraints (including valuation risks)",
        topic + " export situation and overseas market (Europe, Southeast Asia, Middle East)",
        topic + " future trends and 3-year forecast (with volume and price data)",
    ]

def format_evidence(results, max_chars=10000):
    if not results:
        return "(No search results)"
    parts = []
    for i, r in enumerate(results[:20], 1):
        parts.append(f"[{i}] {r.get('title','Untitled')}\n  Date:{r.get('date','n/a')} URL:{r.get('url','N/A')}\n  Summary:{r.get('snippet','')[:350]}")
    text = "\n\n".join(parts)
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n(Total {len(results)} sources, truncated)"
    return text

def run(topic, mode="deep"):
    print(f"DeepResearch v2 | Topic: {topic}")
    sub_questions = decompose(topic)
    print(f"{len(sub_questions)} sub-questions generated")
    
    queries = []
    for sq in sub_questions:
        queries.append({"query": sq, "max_r": 8, "days": 90, "country": "CN"})
        queries.append({"query": sq + " news", "max_r": 5, "days": 30})
    
    all_results = search_all(queries)
    print(f"Collected {len(all_results)} unique results")
    
    # Quick categorization
    sq_map = {sq: [] for sq in sub_questions}
    for r in all_results:
        rq = r.get("_query","")
        for sq in sub_questions:
            if sq.split(",")[0].lower() in rq.lower() or rq.lower() in sq.lower():
                sq_map[sq].append(r)
                break
    
    for sq in sub_questions:
        if not sq_map[sq]:
            sq_map[sq] = all_results[:10]
    
    # Print evidence summary for each sub-question
    for sq, results in sq_map.items():
        print(f"\n  {sq[:40]}: {len(results)} results")
        for r in results[:2]:
            print(f"    - {r.get('title','')[:60]}")
    
    return {
        "topic": topic,
        "sources": len(all_results),
        "sub_questions": sub_questions,
        "all_evidence": format_evidence(all_results, 8000),
        "sq_evidence": {sq: format_evidence(results, 3000) for sq, results in sq_map.items()},
    }

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "光伏行业出口2026"
    result = run(topic)
    print(f"\nAll evidence ready for agent analysis")
