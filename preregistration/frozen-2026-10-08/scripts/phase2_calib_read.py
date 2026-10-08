#!/usr/bin/env python3
"""Read the sentence-calibration batch (protocol v5.1 section 五): did the sentences do what they should?

Targets, fixed before the batch:
  Pb3  (split into 3, delegate)   subagents started per run close to 3 (2-4 on most runs)
  Pb8  (split into 8, delegate)   subagents started per run close to 8 (6-10 on most runs); with K=8 no cap rejection needed
  Pgs  (split into 8, do it yourself, no delegation tools)  no subagents (D0); the report exists
  Pgm  (at least 150 searches / 250 pages, single agent)    search requests 0.8-1.4 x the phase-1 default (214 per run)
The judgement is per group over its runs: median and range of spawn_started (accepted delegation calls), rejected_cap,
search_requests, n_web_fetch, t_answer_s, and whether the deliverable exists. Reads the run table written by
run_table.py (results/master/raw/<batch>.csv) and prints one block per group.

Usage (dev box): python judge-env/scripts/phase2_calib_read.py results/master/raw/phase2-calib.csv [--default-search 214]
"""
from __future__ import annotations

import argparse
import csv
import statistics as st
from collections import defaultdict

TARGET = {"Pb3": ("spawn_started", 2, 4), "Pb8": ("spawn_started", 6, 10), "Pgs": ("spawn_started", 0, 0), "Pgm": ("search_ratio", 0.8, 1.4)}


def tag_of(group: str) -> str:
    for part in group.split("-"):
        if part.startswith("P") and part[1:].isalnum() and part not in ("P",):
            return part
    return ""


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("table")
    ap.add_argument("--default-search", type=float, default=214.0, help="phase-1 default-cell search requests per run")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.table, encoding="utf-8")))
    by = defaultdict(list)
    for r in rows:
        by[r["group"]].append(r)
    verdicts = {}
    for g, rs in sorted(by.items()):
        tag = tag_of(g)
        cols = {"spawn_started": [num(r.get("spawn_started")) for r in rs], "rejected_cap": [num(r.get("rejected_cap")) for r in rs],
                "search_requests": [num(r.get("search_requests")) for r in rs], "n_web_fetch": [num(r.get("n_web_fetch")) for r in rs],
                "t_answer_min": [num(r.get("t_answer_s")) / 60 if num(r.get("t_answer_s")) is not None else None for r in rs],
                "kids_d1": [num(r.get("kids_d1")) for r in rs]}
        print(f"== {g} ({len(rs)} runs; tasks {sorted({r['task'] for r in rs})})")
        for k, v in cols.items():
            vv = [x for x in v if x is not None]
            if vv:
                print(f"   {k:16s} median {st.median(vv):7.1f}  min {min(vv):7.1f}  max {max(vv):7.1f}  (n={len(vv)})")
            else:
                print(f"   {k:16s} (no values)")
        exits = defaultdict(int)
        for r in rs:
            exits[(r.get("exit"), r.get("timeout"), r.get("crash5063"))] += 1
        print(f"   exit/timeout/crash: {dict(exits)}")
        if tag in TARGET:
            what, lo, hi = TARGET[tag]
            if what == "search_ratio":
                vals = [x / a.default_search for x in cols["search_requests"] if x is not None]
            else:
                vals = [x for x in cols[what] if x is not None]
            inside = sum(1 for x in vals if lo <= x <= hi)
            med = st.median(vals) if vals else None
            verdicts[g] = (what, med, inside, len(vals))
            print(f"   target {what} in [{lo}, {hi}]: median {med}, {inside}/{len(vals)} runs inside")
    print("\nSummary (median of the target quantity per sentence group):")
    for g, (what, med, inside, n) in verdicts.items():
        print(f"  {g}: {what} median {med}; {inside}/{n} inside the target range")


if __name__ == "__main__":
    main()
