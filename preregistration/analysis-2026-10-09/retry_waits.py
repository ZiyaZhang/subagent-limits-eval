#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seconds a run spent waiting between a failed model request and its automatic retry (the llm retry policy that the
phase-2 batches run with: up to 12 retries, 2-60 s apart; protocol change log 2026-10-08).

Per run, from every session log: the number of llm/retry events and the sum of their delayMs, for the root session
and for all sessions together. The root's waits add to the time the user waits one for one (the root's timeline is
serial); waits of subagents overlap each other, so their sum is an upper bound on what they add.

Usage: retry_waits.py results/runs/<batch> --out results/analysis-<batch>-retry.json [--jobs 16]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import glob
import json
import os
import subprocess


def one(run_dir: str) -> dict:
    res = json.load(open(os.path.join(run_dir, "result.json")))
    out = {"id": res.get("id") or os.path.basename(run_dir), "retries": 0, "retries_root": 0, "retry_wait_all_s": 0.0, "retry_wait_root_s": 0.0,
           "max_delay_s": 0.0, "sessions": 0}
    for sp in glob.glob(os.path.join(run_dir, "home", "sessions", "**", "session.v4.jsonl*"), recursive=True):
        raw = subprocess.run(["zstd", "-dc", sp], capture_output=True, check=False).stdout if sp.endswith(".zstd") else open(sp, "rb").read()
        root, n, wait, big = None, 0, 0.0, 0.0
        for line in raw.splitlines():
            if b'"session"' not in line and b"llm/retry" not in line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            t, d = e.get("type"), e.get("data") or {}
            if t == "session" and root is None:  # the header's fields are on the event itself (run_metrics.read_log)
                root = not (e.get("parentSession") or d.get("parentSession"))
            elif t == "llm/retry":
                n += 1
                s = float(d.get("delayMs") or 0) / 1000
                wait += s
                big = max(big, s)
        out["sessions"] += 1
        out["retries"] += n
        out["retry_wait_all_s"] += wait
        out["max_delay_s"] = max(out["max_delay_s"], big)
        if root:
            out["retries_root"] += n
            out["retry_wait_root_s"] += wait
    for k in ("retry_wait_all_s", "retry_wait_root_s", "max_delay_s"):
        out[k] = round(out[k], 1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch")
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    runs = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(a.batch, "*", "result.json")))
    with cf.ProcessPoolExecutor(max_workers=a.jobs) as ex:
        rows = list(ex.map(one, runs, chunksize=4))
    json.dump(rows, open(a.out, "w"), ensure_ascii=False, indent=1)
    w = sorted(r["retry_wait_all_s"] for r in rows)
    wr = sorted(r["retry_wait_root_s"] for r in rows)
    q = lambda v, p: v[int(p * (len(v) - 1))] if v else 0  # noqa: E731
    print(f"{len(rows)} runs; retries {sum(r['retries'] for r in rows)} (root {sum(r['retries_root'] for r in rows)}); wait of all sessions per run: "
          f"median {q(w, .5):.0f} s, p90 {q(w, .9):.0f} s, max {w[-1] if w else 0:.0f} s; root only: median {q(wr, .5):.0f} s, p90 {q(wr, .9):.0f} s, max {wr[-1] if wr else 0:.0f} s; "
          f"runs with no retry {sum(r['retries'] == 0 for r in rows)}")


if __name__ == "__main__":
    main()
