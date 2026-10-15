#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Census of failed tool calls in a batch, to find odd behaviour of the harness or of the model that nobody was looking
for (her instruction of 2026-10-09: when something strange shows up, track it down and write it down).

For every tool call whose result is an error: the tool, the message with ids / numbers / addresses / paths replaced by
placeholders, the depth of the agent, and what the same agent did next (the next tool call: the same call again, the
same tool with other arguments, another tool, or nothing more). Aggregated over the batch: how often, in how many runs,
at which depths, what came next, and three places to read (run, agent session, seconds from the run's start).

Web tools (web_search, web_fetch) fail for outside reasons most of the time and are summarised in one line each unless
--web is given. Names no outcome of the experiment; the group of a run is kept only for the per-group counts.

Usage: tool_error_census.py results/runs/<batch> --out results/analysis-<batch>-toolcensus [--jobs 16] [--web]
Writes census.json (every pattern), census.md (the table), examples.jsonl (up to 5 per pattern).
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
UUID = re.compile(r"(?:session-)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
URL = re.compile(r"https?://[^\s\"'<>)\]]+")
PATH = re.compile(r"(?:/[\w.@%+~-]+){2,}")
NUM = re.compile(r"\b\d[\d,.]*\b")
QUOTED = re.compile(r"\"[^\"]{24,}\"|'[^']{24,}'")
WEB = {"web_search", "web_fetch"}


def norm(text: str) -> str:
    t = " ".join((text or "").split())[:400]
    t = UUID.sub("<id>", t)
    t = URL.sub("<url>", t)
    t = PATH.sub("<path>", t)
    t = QUOTED.sub("\"…\"", t)
    t = NUM.sub("N", t)
    return t[:150]


def one(run_dir: str) -> list:
    import run_metrics as rm
    d = Path(run_dir)
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    try:
        _, sessions = rm.load_sessions(d)
    except Exception:  # noqa: BLE001
        return []
    firsts = [s["first_time"] for s in sessions if s["first_time"] is not None]
    t0 = min(firsts) if firsts else 0
    out = []
    for s in sessions:
        order = s["call_order"]
        for pos, cid in enumerate(order):
            c = s["calls"][cid]
            r = s["results"].get(cid)
            if r is None:
                continue
            text = r["text"] or ""
            if not (r["is_error"] or text.lstrip().startswith("Error")):
                continue
            nxt = "nothing more"
            if pos + 1 < len(order):
                n = s["calls"][order[pos + 1]]
                same_args = json.dumps(n["args"], sort_keys=True, ensure_ascii=False) == json.dumps(c["args"], sort_keys=True, ensure_ascii=False)
                nxt = "same call again" if (n["name"] == c["name"] and same_args) else ("same tool, other arguments" if n["name"] == c["name"] else "then " + str(n["name"]))
            out.append({"run": res.get("id") or d.name, "group": res.get("group"), "task": res.get("task"), "tool": c["name"], "msg": norm(text),
                        "depth": s["depth"], "next": nxt, "sid": str(s["id"])[:8], "t": round(((c["time"] or t0) - t0) / 1000, 1),
                        "args": " ".join(json.dumps(c["args"], ensure_ascii=False).split())[:240] if c["args"] is not None else "", "raw": " ".join(text.split())[:300]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--web", action="store_true")
    a = ap.parse_args()
    runs = sorted(str(p.parent) for p in a.batch.glob("*/result.json"))
    with cf.ProcessPoolExecutor(max_workers=a.jobs) as ex:
        rows = [x for part in ex.map(one, runs, chunksize=4) for x in part]
    a.out.mkdir(parents=True, exist_ok=True)
    pat = collections.defaultdict(lambda: {"n": 0, "runs": set(), "depth": collections.Counter(), "next": collections.Counter(), "groups": collections.Counter(), "ex": []})
    web = collections.Counter()
    for x in rows:
        if x["tool"] in WEB and not a.web:
            web[x["tool"]] += 1
            continue
        p = pat[(x["tool"], x["msg"])]
        p["n"] += 1
        p["runs"].add(x["run"])
        p["depth"][min(x["depth"], 2)] += 1
        p["next"][x["next"]] += 1
        p["groups"][x["group"]] += 1
        if len(p["ex"]) < 5 and x["run"] not in {e["run"] for e in p["ex"]}:
            p["ex"].append({k: x[k] for k in ("run", "group", "task", "sid", "t", "depth", "args", "raw", "next")})
    items = sorted(pat.items(), key=lambda kv: -kv[1]["n"])
    census = [{"tool": k[0], "message": k[1], "calls": v["n"], "runs": len(v["runs"]), "depth": dict(v["depth"]), "next": dict(v["next"].most_common(6)),
               "groups": dict(v["groups"].most_common(8)), "examples": v["ex"]} for k, v in items]
    (a.out / "census.json").write_text(json.dumps(census, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(a.out / "examples.jsonl", "w", encoding="utf-8") as fh:
        for c in census:
            for e in c["examples"]:
                fh.write(json.dumps({"tool": c["tool"], "message": c["message"], **e}, ensure_ascii=False) + "\n")
    md = [f"# 失败的工具调用普查：{a.batch.name}（{len(runs)} 次运行）", "",
          f"网页工具另计：" + "，".join(f"{k} 失败 {v} 次" for k, v in web.items()) + "。" if web else "", "",
          "| 工具 | 错误消息（编号、数字、地址已换成占位符） | 次数 | 运行数 | 主 agent / 第 1 层 / 更深 | 之后最常见的动作 |", "|---|---|---|---|---|---|"]
    for c in census[:80]:
        nx = "；".join(f"{k} {v}" for k, v in list(c["next"].items())[:3])
        md.append(f"| {c['tool']} | {c['message'].replace('|', '/')} | {c['calls']} | {c['runs']} | {c['depth'].get(0, 0)} / {c['depth'].get(1, 0)} / {c['depth'].get(2, 0)} | {nx} |")
    (a.out / "census.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    by_tool = collections.Counter()
    for c in census:
        by_tool[c["tool"]] += c["calls"]
    print(f"{len(runs)} runs; failed calls {len(rows)} (web: {dict(web)}); other tools: {dict(by_tool.most_common(14))}; patterns {len(census)}")
    for c in census[:40]:
        print(f"  {c['calls']:5d} calls {c['runs']:4d} runs  {c['tool']:14s} {c['message'][:110]}  | next: " + "; ".join(f"{k} {v}" for k, v in list(c['next'].items())[:2]))


if __name__ == "__main__":
    main()
