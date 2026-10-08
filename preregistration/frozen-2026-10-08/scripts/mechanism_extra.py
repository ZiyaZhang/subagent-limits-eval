#!/usr/bin/env python3
"""Mechanism analyses that need the session logs (review of 2026-10-07, step 2 item 8). Reads files only.

  rejects BATCH [--groups G1,G2]   what the rejected delegation calls cost. For every assistant message with at least
        one delegation call rejected by the depth limit or by K: the yuan of that message's output tokens, split
        between its tool calls in proportion to the length of their arguments (the model wrote those arguments for a
        subagent that never started); and, when every call of the message was rejected, the whole request (input,
        cache read, output) as a step that produced nothing. Prices: uncached input 2, cache hit 0.04, output 8 yuan
        per million tokens. Per group: rejected calls per run by kind, yuan per run both ways, share of the model fee.
  tools BATCH [BATCH ...]          delegation calls by tool (`subagent`, `subagent_fork`), foreground calls, per batch
        and group.
  tree RUN_DIR                     the delegation tree of one run: every session with its parent, depth, label, the
        tool that started it, minutes, search requests, tool calls, rejected calls, output tokens.
  relay BATCH --judge DIR          which subagent handed back which fact: for the runs whose handed-back messages were
        judged (results/judge-facts/relay-<batch>/<id>.f1.json), every fact judged right is assigned to the sender
        of the message that holds its quote; then, for each fact, whether its value also appears in another
        sender's messages.

Usage (experiment directory; on the dev box with judge-env/scripts on the path):
  python scripts/mechanism_extra.py rejects results/runs/office-confirm --out results/analysis-mechanism/rejects-office-confirm.json
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_metrics as rm  # noqa: E402

PRICE = {"miss": 2.0, "hit": 0.04, "out": 8.0}  # yuan per million tokens, peak
SPAWN = ("subagent", "subagent_fork")
from delegation_stats import CAPACITY_REJECT as CAP, DEPTH_REJECT as DEPTH  # noqa: E402  (the rule of the run metrics)


def yuan(usage: dict, parts=("miss", "hit", "out")) -> float:
    u = {"miss": usage.get("inputTokens") or 0, "hit": usage.get("cacheReadTokens") or 0, "out": usage.get("outputTokens") or 0}
    return sum(u[k] * PRICE[k] for k in parts) / 1e6


def sessions_of(run_dir: Path):
    _, sessions = rm.load_sessions(run_dir)
    by_id = {s["id"]: s for s in sessions}
    roots = [s for s in sessions if not s["parent"] or s["parent"] not in by_id]
    root = min(roots, key=lambda s: s["depth"]) if roots else (sessions[0] if sessions else None)
    return sessions, root


def reject_kind(s: dict, cid: str):
    c, res = s["calls"][cid], s["results"].get(cid)
    if c["name"] not in SPAWN or not res or not (res["is_error"] or res["text"].lstrip().startswith("Error")):
        return None
    return "depth" if DEPTH.search(res["text"]) else "cap" if CAP.search(res["text"]) else None


def run_rejects(run_dir: Path) -> dict:
    sessions, root = sessions_of(run_dir)
    out = {"depth": 0, "cap": 0, "args_yuan": 0.0, "dead_step_yuan": 0.0, "dead_steps": 0, "model_yuan": sum(yuan(m["usage"]) for s in sessions for m in s["messages"]),
           "args_chars": 0}
    for s in sessions:
        by_key = collections.defaultdict(list)
        for cid, c in s["calls"].items():
            by_key[c["key"]].append(cid)
        for m in s["messages"]:
            cids = by_key.get(m["key"], [])
            kinds = {cid: reject_kind(s, cid) for cid in cids}
            rej = [cid for cid in cids if kinds[cid]]
            if not rej:
                continue
            size = {cid: len(json.dumps(s["calls"][cid]["args"], ensure_ascii=False)) for cid in cids}
            for cid in rej:
                out[kinds[cid]] += 1
                out["args_chars"] += size[cid]
            out["args_yuan"] += yuan(m["usage"], ("out",)) * sum(size[cid] for cid in rej) / max(1, sum(size.values()))
            if len(rej) == len(cids):
                out["dead_steps"] += 1
                out["dead_step_yuan"] += yuan(m["usage"])
    return out


def cmd_rejects(a) -> None:
    runs, _ = rm.discover(Path(a.batch))
    want = set(a.groups.split(",")) if a.groups else None
    per = collections.defaultdict(list)
    for run in runs:
        g = run["result"].get("group")
        if want and g not in want:
            continue
        per[g].append(dict(run_rejects(run["dir"]), id=run["key"], task=run["result"].get("task")))
    res = {"batch": Path(a.batch).name, "price": PRICE, "groups": {}}
    for g, rows in sorted(per.items()):
        mean = lambda k, rows=rows: st.mean(r[k] for r in rows)  # noqa: E731
        res["groups"][g] = {"runs": len(rows), "depth": mean("depth"), "cap": mean("cap"), "args_yuan": mean("args_yuan"), "dead_steps": mean("dead_steps"),
                            "dead_step_yuan": mean("dead_step_yuan"), "model_yuan": mean("model_yuan"), "args_chars": mean("args_chars"),
                            "args_share": sum(r["args_yuan"] for r in rows) / sum(r["model_yuan"] for r in rows),
                            "dead_share": sum(r["dead_step_yuan"] for r in rows) / sum(r["model_yuan"] for r in rows)}
        v = res["groups"][g]
        print(f"{g:12s} runs {v['runs']:3d} | rejected by depth {v['depth']:.2f} by K {v['cap']:.2f} per run | arguments {v['args_yuan']:.3f} yuan ({100 * v['args_share']:.1f}% of the model fee {v['model_yuan']:.2f}) | "
              f"steps with every call rejected {v['dead_steps']:.2f}, {v['dead_step_yuan']:.3f} yuan ({100 * v['dead_share']:.1f}%)")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_tools(a) -> None:
    res = {}
    for b in a.batches:
        runs, _ = rm.discover(Path(b))
        per = collections.defaultdict(lambda: collections.Counter())
        for run in runs:
            sessions, root = sessions_of(run["dir"])
            g = run["result"].get("group")
            per[g]["runs"] += 1
            for s in sessions:
                for c in s["calls"].values():
                    if c["name"] in SPAWN:
                        per[g][c["name"]] += 1
                        per[g]["foreground"] += (c["args"] or {}).get("run_in_background") is False
                        per[g]["from_root"] += s is root
            per[g]["children"] += len(sessions) - 1
        res[Path(b).name] = {g: dict(v) for g, v in sorted(per.items())}
        tot = collections.Counter()
        for v in per.values():
            tot.update(v)
        print(Path(b).name, dict(tot))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_tree(a) -> None:
    run_dir = Path(a.run)
    sessions, root = sessions_of(run_dir)
    by_id = {s["id"]: s for s in sessions}
    started_by = {}
    for s in sessions:  # the call that started each child: the parent's delegation calls in time order against the children in time order
        kids = sorted((c for c in sessions if c["parent"] == s["id"]), key=lambda c: c["first_time"] or 0)
        calls = sorted((c for cid, c in s["calls"].items() if c["name"] in SPAWN and not reject_kind(s, cid)), key=lambda c: c["time"] or 0)
        for kid, call in zip(kids, calls):
            started_by[kid["id"]] = call
    nodes = []
    for s in sessions:
        call = started_by.get(s["id"]) or {}
        nodes.append({"id": s["id"][:12], "parent": (s["parent"] or "")[:12] if s["parent"] in by_id else None, "depth": s["depth"], "label": s["label"] or (call.get("args") or {}).get("description"),
                      "tool": call.get("name"), "minutes": None if s["first_time"] is None else round((s["last_time"] - s["first_time"]) / 60000, 1),
                      "start_min": None if s["first_time"] is None or root["first_time"] is None else round((s["first_time"] - root["first_time"]) / 60000, 1),
                      "search_requests": s["search_aux"], "tool_calls": len(s["calls"]), "rejected_depth": sum(1 for cid in s["calls"] if reject_kind(s, cid) == "depth"),
                      "rejected_cap": sum(1 for cid in s["calls"] if reject_kind(s, cid) == "cap"), "output_tokens": s["usage"].get("outputTokens", 0), "yuan": round(sum(yuan(m["usage"]) for m in s["messages"]), 3)})
    res = {"run": run_dir.name, "result": {k: json.loads((run_dir / "result.json").read_text(encoding="utf-8")).get(k) for k in ("task", "group", "rep")}, "nodes": nodes}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for n in sorted(nodes, key=lambda n: (n["depth"], n["start_min"] or 0)):
        print("  " * n["depth"] + f"{n['label'] or 'root'} | {n['tool']} | start {n['start_min']} min, {n['minutes']} min | searches {n['search_requests']} | calls {n['tool_calls']} | rejected depth {n['rejected_depth']} K {n['rejected_cap']} | {n['yuan']} yuan")


def squeeze(text: str) -> str:
    return re.sub(r"[\s*`_>#|\-]+", "", text or "")


def cmd_relay(a) -> None:
    runs, _ = rm.discover(Path(a.batch))
    judge = Path(a.judge)
    res, rows = {"batch": Path(a.batch).name, "runs": []}, []
    for run in runs:
        jf = judge / f"{run['key']}.f1.json"
        if not jf.exists():
            continue
        facts = [f for f in json.loads(jf.read_text(encoding="utf-8"))["facts"] if f.get("status") == "对"]
        sessions, root = sessions_of(run["dir"])
        msgs = []  # (sender session id, squeezed text) of every message a subagent handed to the root
        for box in root["inbox"]:
            for m in box["messages"]:
                src = m.get("source") or {}
                if src.get("kind") in ("agent-message", "subagent-settled"):
                    text = "".join(b.get("text", "") for b in (m.get("content") or []) if isinstance(b, dict) and b.get("type") == "text")
                    if text.strip():
                        msgs.append((rm.norm_id(src.get("senderSessionId") or src.get("sessionId")) or "?", squeeze(text)))
        senders = sorted({s for s, _ in msgs})
        by_sender = {s: "".join(t for q, t in msgs if q == s) for s in senders}
        owner, also, lost = collections.Counter(), 0, 0
        also_quote = also_value_short = also6 = 0  # how a fact came to count as "also elsewhere": the quote itself in two senders; only its value, and that value under 6 characters; the count with values of 6 or more only
        for f in facts:
            q = squeeze(f.get("quote"))
            hit = [s for s in senders if q and q in by_sender[s]]
            if not hit and len(q) > 16:  # the judge may have shortened the quote: its first and last 12 characters
                hit = [s for s in senders if q[:12] in by_sender[s] and q[-12:] in by_sender[s]]
            if not hit:
                lost += 1
                continue
            owner[hit[0]] += 1
            v = squeeze(f.get("value"))
            by_value = len(v) >= 4 and any(v in by_sender[s] for s in senders if s != hit[0])
            also += len(hit) > 1 or by_value
            also_quote += len(hit) > 1
            also_value_short += len(hit) == 1 and by_value and len(v) < 6
            also6 += len(hit) > 1 or (by_value and len(v) >= 6)
        placed = sum(owner.values())
        counts = sorted(owner.values(), reverse=True)
        rows.append({"id": run["key"], "task": run["result"].get("task"), "group": run["result"].get("group"), "senders": len(senders), "facts_right": len(facts), "placed": placed, "not_placed": lost,
                     "top_sender_share": counts[0] / placed if placed else None, "also_elsewhere": also, "only_one_sender": placed - also, "per_sender": counts,
                     "also_quote": also_quote, "also_value_short": also_value_short, "also6": also6, "senders_with_facts": len(counts), "messages": len(msgs)})
    res["runs"] = rows
    by_group = collections.defaultdict(list)
    for r in rows:
        by_group[r["group"]].append(r)
    res["groups"] = {}
    for g, rs in sorted(by_group.items()):
        ok = [r for r in rs if r["placed"]]
        res["groups"][g] = {"runs": len(rs), "senders": st.mean(r["senders"] for r in rs), "facts_right": st.mean(r["facts_right"] for r in rs), "placed_share": sum(r["placed"] for r in rs) / max(1, sum(r["facts_right"] for r in rs)),
                            "only_one_sender": st.mean(r["only_one_sender"] for r in ok), "also_elsewhere": st.mean(r["also_elsewhere"] for r in ok),
                            "only_one_share": sum(r["only_one_sender"] for r in ok) / max(1, sum(r["placed"] for r in ok)), "top_sender_share": st.mean(r["top_sender_share"] for r in ok),
                            "also_quote": st.mean(r["also_quote"] for r in ok), "also_value_short": st.mean(r["also_value_short"] for r in ok), "also_value_short_total": sum(r["also_value_short"] for r in ok),
                            "also_total": sum(r["also_elsewhere"] for r in ok), "also_quote_total": sum(r["also_quote"] for r in ok),
                            "only_one_share6": 1 - sum(r["also6"] for r in ok) / max(1, sum(r["placed"] for r in ok)), "only_one_share_quote": 1 - sum(r["also_quote"] for r in ok) / max(1, sum(r["placed"] for r in ok)),
                            "senders_with_facts": st.mean(r["senders_with_facts"] for r in rs), "messages": sum(r["messages"] for r in rs)}
        v = res["groups"][g]
        print(f"{g:12s} runs {v['runs']} | senders {v['senders']:.1f} | facts right {v['facts_right']:.1f}, placed {100 * v['placed_share']:.0f}% | found with one sender only {v['only_one_sender']:.1f} ({100 * v['only_one_share']:.0f}%) | top sender {100 * v['top_sender_share']:.0f}%")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("rejects"); p.add_argument("batch"); p.add_argument("--groups", default=""); p.add_argument("--out", required=True); p.set_defaults(fn=cmd_rejects)
    p = sub.add_parser("tools"); p.add_argument("batches", nargs="+"); p.add_argument("--out", required=True); p.set_defaults(fn=cmd_tools)
    p = sub.add_parser("tree"); p.add_argument("run"); p.add_argument("--out", required=True); p.set_defaults(fn=cmd_tree)
    p = sub.add_parser("relay"); p.add_argument("batch"); p.add_argument("--judge", required=True); p.add_argument("--out", required=True); p.set_defaults(fn=cmd_relay)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
