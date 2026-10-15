#!/usr/bin/env python3
"""Estimate the per-task cost of web search, which DSH session logs leave out.

The DeepSeek search provider makes one full Messages call per web_search (model deepseek-v4-flash,
server tool web_search_20250305, max_uses 5). The session log records each request body as a
`web/deepseek-search-llm-request` event but never the response usage. This script resends a random
sample of the logged request bodies, unchanged, to the same endpoint, reads `usage` from each
response, and scales the mean cost per request by each run's request count.

Usage: search_cost_probe.py RUNS_DIR [--sample 40] [--out results/search-cost-probe.json]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from delegation_stats import PRICES_CNY_PER_M, read_lines  # noqa: E402


def keychain(service: str) -> str:
    """JUDGE_USER_SK when set (HG dev box runs), else the macOS keychain."""
    if service == "dsllm-usersk" and os.environ.get("JUDGE_USER_SK"):
        return os.environ["JUDGE_USER_SK"].strip()
    return subprocess.run(["security", "find-generic-password", "-a", "zhangziya", "-s", service, "-w"],
                          check=True, capture_output=True, text=True).stdout.strip()


def collect(runs_dir: Path) -> dict:
    """run_id -> list of (endpoint, apiVersion, body) for every logged search request."""
    reqs = defaultdict(list)
    for f in sorted(runs_dir.rglob("session*.jsonl.zstd")):
        run_id = f.relative_to(runs_dir).parts[0]
        if run_id.startswith("_"):  # _failed/: discarded infrastructure attempts are not part of the batch
            continue
        for line in read_lines(f):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") == "web/deepseek-search-llm-request":
                d = e.get("data") or {}
                reqs[run_id].append((d["endpoint"], d.get("apiVersion", "2023-06-01"), d["body"]))
    return reqs


def send(endpoint: str, api_version: str, body: dict, key: str) -> dict:
    # In-process (httpx, proxies ignored) so the key never appears on a command line.
    import httpx
    try:
        r = httpx.post(endpoint, timeout=180, trust_env=False, content=json.dumps(body),
                       headers={"x-api-key": key, "authorization": f"Bearer {key}", "anthropic-version": api_version,
                                "content-type": "application/json"})
        text = r.text
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}"}
    try:
        out = json.loads(text)
    except ValueError:
        return {"error": text[:300].replace(key, "<key>")}
    if "usage" not in out:
        return {"error": json.dumps(out)[:300].replace(key, "<key>")}
    blocks = out.get("content") or []
    return {"usage": out["usage"], "results": sum(1 for b in blocks if b.get("type") == "web_search_tool_result")}


def cost(u: dict) -> float:
    price = PRICES_CNY_PER_M["peak"]
    cached = u.get("cache_read_input_tokens") or 0
    return ((u.get("input_tokens") or 0) * price["inputTokens"] + cached * price["cacheReadTokens"]
            + (u.get("output_tokens") or 0) * price["outputTokens"]) / 1e6


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs_dir", type=Path)
    ap.add_argument("--sample", type=int, default=40)
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "search-cost-probe.json")
    args = ap.parse_args()
    reqs = collect(args.runs_dir)
    pool = [(run, r) for run, rs in reqs.items() for r in rs]
    picked = random.Random(20261001).sample(pool, min(args.sample, len(pool)))
    key = keychain("dsllm-usersk")
    with cf.ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda pr: {"run": pr[0], "query": pr[1][2]["messages"][0]["content"][0]["text"][-120:],
                                      **send(pr[1][0], pr[1][1], pr[1][2], key)}, picked))
    ok = [r for r in res if "usage" in r]
    for r in ok:
        r["cost_cny_peak"] = cost(r["usage"])
    mean = lambda f: sum(f(r) for r in ok) / len(ok)
    per_req = mean(lambda r: r["cost_cny_peak"])
    print(f"sent {len(res)}, usable {len(ok)}, errors {[r['error'][:120] for r in res if 'error' in r][:3]}")
    print(f"per request: input {mean(lambda r: r['usage'].get('input_tokens') or 0):,.0f} "
          f"(cache read {mean(lambda r: r['usage'].get('cache_read_input_tokens') or 0):,.0f}), "
          f"output {mean(lambda r: r['usage'].get('output_tokens') or 0):,.0f} tokens, "
          f"web searches {mean(lambda r: ((r['usage'].get('server_tool_use') or {}).get('web_search_requests') or 0)):.1f}; "
          f"cost {per_req:.4f} yuan at peak price (min {min(r['cost_cny_peak'] for r in ok):.4f}, max {max(r['cost_cny_peak'] for r in ok):.4f})")
    per_run = {run: {"requests": len(rs), "search_cost_cny_peak": round(len(rs) * per_req, 3)} for run, rs in reqs.items()}
    args.out.write_text(json.dumps({"per_request_cny_peak": per_req, "sample": res, "per_run": per_run}, ensure_ascii=False, indent=1))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
