#!/usr/bin/env python3
"""Per-request model timing from DSH session logs, to check whether some groups got a slower interface.

For every run under a batch directory (run_matrix_v2 layout), read every persisted session log
(home/sessions/**/session.v4.jsonl.zstd: the root session and each subagent) and, for each model request:
  start    = the step/start event time
  first    = the first streamed chunk time (assistant/message data.stream[0])
  end      = the assistant/message event time
  ttft     = first - start, gen = end - first, out_tps = outputTokens / gen.
Also counts events whose type mentions retry / error / rate, and "429" / "rate limit" text anywhere in the logs.

Usage: request_timing.py <batch_dir> [--json out.json]
Prints one row per group (task x group): requests, median TTFT, median output tokens/s, retry-ish events.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import statistics as st
import subprocess
import sys


def read_session(path: str):
    """The session's own events. A forked agent's log (header isSeeded) starts with a copy of its parent's history,
    closed by session/end-seed: the copy is skipped (see run_metrics.read_log)."""
    raw = subprocess.run(["zstd", "-dc", path], capture_output=True, check=False).stdout
    copy = False
    for line in raw.splitlines():
        try:
            e = json.loads(line)
        except Exception:  # noqa: BLE001 - tolerate a torn last line
            continue
        if not isinstance(e, dict):
            continue
        if e.get("type") == "session":
            copy = bool(e.get("isSeeded") or (e.get("data") or {}).get("isSeeded"))
        elif copy:
            if e.get("type") != "session/end-seed":
                continue
            copy = False
        yield e


def first_stream_time(stream) -> int | None:
    if not isinstance(stream, list):
        return None
    for item in stream:
        t = item.get("time", item.get("time0")) if isinstance(item, dict) else None
        if isinstance(t, (int, float)):
            return int(t)
    return None


def session_requests(path: str):
    starts: dict[str, int] = {}
    reqs, flagged, header = [], collections.Counter(), {}
    for e in read_session(path):
        t, d, tm = e.get("type", ""), e.get("data") or {}, e.get("time")
        if t == "session":
            header = d
        low = t.lower()
        if "retry" in low or "error" in low or "rate" in low:
            flagged[t] += 1
        if t == "step/start" and isinstance(tm, (int, float)):
            starts[f"{d.get('turn')}:{d.get('step')}"] = int(tm)
        elif t == "assistant/message" and isinstance(tm, (int, float)):
            key = f"{d.get('turn')}:{d.get('step')}"
            s, f = starts.get(key), first_stream_time(d.get("stream"))
            u = d.get("usage") or {}
            out = u.get("outputTokens") or 0
            r = {"start": s, "first": f, "end": int(tm), "out": out,
                 "in_miss": u.get("inputTokens") or 0, "in_hit": u.get("cacheReadTokens") or 0}
            if s is not None and f is not None and f >= s:
                r["ttft_ms"] = f - s
                gen = int(tm) - f
                r["gen_ms"] = gen
                if gen >= 500 and out >= 50:
                    r["out_tps"] = out / (gen / 1000)
            reqs.append(r)
    return reqs, flagged, header


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch", help="batch directory, e.g. results/runs/office-v2")
    ap.add_argument("--json", help="write per-run details here")
    args = ap.parse_args()
    runs = []
    for rp in sorted(glob.glob(os.path.join(args.batch, "*", "result.json"))):
        res = json.load(open(rp))
        rdir = os.path.dirname(rp)
        sessions = glob.glob(os.path.join(rdir, "home", "sessions", "**", "session.v4.jsonl.zstd"), recursive=True)
        reqs, flagged = [], collections.Counter()
        for sp in sessions:
            r, fl, _ = session_requests(sp)
            reqs += r
            flagged.update(fl)
        text_hits = 0
        for name in ("events.jsonl", "stderr.log"):
            p = os.path.join(rdir, name)
            if os.path.exists(p):
                s = open(p, errors="replace").read().lower()
                text_hits += s.count(" 429") + s.count("rate limit") + s.count("too many requests")
        ttft = [r["ttft_ms"] for r in reqs if "ttft_ms" in r]
        tps = [r["out_tps"] for r in reqs if "out_tps" in r]
        runs.append({"id": res.get("id") or res.get("run_id"), "task": res["task"], "group": res["group"],
                     "rep": res["rep"], "order": res.get("order"), "started_utc": res.get("started_utc"),
                     "seconds": res.get("seconds"), "sessions": len(sessions), "requests": len(reqs),
                     "ttft_med_ms": st.median(ttft) if ttft else None, "ttft_p90_ms": sorted(ttft)[int(0.9 * (len(ttft) - 1))] if ttft else None,
                     "tps_med": st.median(tps) if tps else None, "flagged": dict(flagged), "text_429ish": text_hits,
                     "_ttft": ttft, "_tps": tps})
    by = collections.defaultdict(list)
    for r in runs:
        by[(r["task"][:2], r["group"])].append(r)
    print(f"{'task':4} {'group':7} {'runs':>4} {'reqs':>6} {'TTFT med s':>10} {'TTFT p90 s':>10} {'out tok/s med':>13} {'retry/err ev':>12} {'429-ish':>7}")
    for k in sorted(by):
        rs = by[k]
        tt = [x for r in rs for x in r["_ttft"]]
        tp = [x for r in rs for x in r["_tps"]]
        fl = sum(sum(r["flagged"].values()) for r in rs)
        print(f"{k[0]:4} {k[1]:7} {len(rs):>4} {sum(r['requests'] for r in rs):>6} "
              f"{(st.median(tt) / 1000 if tt else float('nan')):>10.2f} {(sorted(tt)[int(0.9 * (len(tt) - 1))] / 1000 if tt else float('nan')):>10.2f} "
              f"{(st.median(tp) if tp else float('nan')):>13.1f} {fl:>12} {sum(r['text_429ish'] for r in rs):>7}")
    flagged_types = collections.Counter()
    for r in runs:
        flagged_types.update(r["flagged"])
    print("flagged event types:", dict(flagged_types) or "none")
    if args.json:
        with open(args.json, "w") as fh:
            json.dump([{k: v for k, v in r.items() if not k.startswith("_")} for r in runs], fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
