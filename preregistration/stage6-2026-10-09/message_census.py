#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Every message one agent sends to another (send_message) in a batch: who to whom, was the target still working, did
it arrive, and what the sender did when it did not (her instruction of 2026-10-09 on odd behaviour: an agent that
cannot reach a finished subagent and opens a new one instead).

Per call: the sender's depth; what the target is to the sender (its child, its parent, a sibling, a deeper descendant,
itself, or an id that is no session of the run); whether the target's log had already ended when the message was sent
(a finished background subagent is resumed by a message: the harness calls this a cold resume, and it needs a free
slot of the K limit); the outcome (delivered, or the error with ids replaced). After a failed message: the sender's
next six tool calls, and whether one of them starts a new subagent (a replacement for the one it could not reach).

Usage: message_census.py results/runs/<batch> --out results/analysis-<batch>-messages.json [--jobs 16]
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
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
SPAWN = {"subagent", "subagent_fork"}


def one(run_dir: str) -> list:
    import run_metrics as rm
    d = Path(run_dir)
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    try:
        _, sessions = rm.load_sessions(d)
    except Exception:  # noqa: BLE001
        return []
    by = {s["id"]: s for s in sessions}
    firsts = [s["first_time"] for s in sessions if s["first_time"] is not None]
    t0 = min(firsts) if firsts else 0
    out = []
    for s in sessions:
        order = s["call_order"]
        for pos, cid in enumerate(order):
            c = s["calls"][cid]
            if c["name"] != "send_message":
                continue
            a = c["args"] if isinstance(c["args"], dict) else {}
            raw_id = str(a.get("agent_id") or a.get("to") or a.get("target") or "")
            m = UUID.search(raw_id)
            tid = rm.norm_id(m.group(0)) if m else None
            exact = bool(m) and raw_id.replace("session-", "") == m.group(0)
            t = by.get(tid)
            if tid is None:
                rel = "no id in the argument"
            elif t is None:
                rel = "id of no session in this run"
            elif tid == s["id"]:
                rel = "itself"
            elif t["parent"] == s["id"]:
                rel = "its child"
            elif s["parent"] == tid:
                rel = "its parent"
            elif t["parent"] == s["parent"]:
                rel = "a sibling"
            else:
                anc, cur = False, t
                while cur is not None and cur["parent"] in by:
                    cur = by[cur["parent"]]
                    if cur["id"] == s["id"]:
                        anc = True
                        break
                rel = "a deeper descendant" if anc else "another agent of the tree"
            state = ""
            if t is not None and c["time"] is not None:
                ends = [e[0] for e in t["turn_ends"] if e[0] is not None and e[0] <= c["time"]]
                open_turn = any(a_ <= c["time"] <= b_ for a_, b_, _ in t["turns"]) if t["turns"] else False
                state = "working" if open_turn else ("finished a turn earlier" if ends else "not started")
            r = s["results"].get(cid)
            text = (r["text"] if r else "") or ""
            err = bool(r) and (r["is_error"] or text.lstrip().startswith("Error"))
            outcome = "no result" if r is None else ("delivered" if not err else UUID.sub("<id>", " ".join(text.split()))[:110])
            follow, replaced = [], False
            if err:
                for nid in order[pos + 1:pos + 7]:
                    n = s["calls"][nid]
                    follow.append(n["name"])
                    nr = s["results"].get(nid)
                    if n["name"] in SPAWN:
                        replaced = True
            out.append({"run": res.get("id") or d.name, "group": res.get("group"), "task": res.get("task"), "depth": s["depth"], "sid": str(s["id"])[:8],
                        "t": round(((c["time"] or t0) - t0) / 1000, 1), "target": rel, "exact_id": exact, "target_state": state, "outcome": outcome,
                        "follow": follow, "replaced": replaced, "raw_id": raw_id[:60], "message": " ".join(str(a.get("message") or a.get("content") or "").split())[:200]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    runs = sorted(str(p.parent) for p in a.batch.glob("*/result.json"))
    with cf.ProcessPoolExecutor(max_workers=a.jobs) as ex:
        rows = [x for part in ex.map(one, runs, chunksize=4) for x in part]
    a.out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    n = len(rows)
    print(f"{len(runs)} runs; send_message calls {n} in {len({r['run'] for r in rows})} runs; delivered {sum(r['outcome'] == 'delivered' for r in rows)}, failed {sum(r['outcome'] not in ('delivered', 'no result') for r in rows)}")
    print("who to whom (sender depth 0 = root):")
    c = collections.Counter(("root" if r["depth"] == 0 else "subagent", r["target"], r["target_state"], "ok" if r["outcome"] == "delivered" else "FAILED") for r in rows)
    for k, v in c.most_common(30):
        print(f"  {v:5d}  {k[0]:8s} -> {k[1]:28s} target {k[2] or '-':24s} {k[3]}")
    fails = [r for r in rows if r["outcome"] not in ("delivered", "no result")]
    print(f"\nfailed messages: {len(fails)} in {len({r['run'] for r in fails})} runs; the sender then started a new subagent within six calls: {sum(r['replaced'] for r in fails)}")
    e = collections.Counter((r["outcome"][:70], r["target"], r["target_state"]) for r in fails)
    for k, v in e.most_common(14):
        print(f"  {v:4d}  {k[0]:72s} | target: {k[1]}, {k[2] or '-'}")
    nx = collections.Counter(tuple(r["follow"][:2]) for r in fails)
    print("  next two calls after a failed message:", nx.most_common(8))


if __name__ == "__main__":
    main()
