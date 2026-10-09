#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Balance check of a phase-2 batch (protocol v5.1 section 七, "平衡性检查"): did every cell get the same interface speed?

Reads request_timing.py's per-run JSON (median time to first chunk and median output tokens per second of each run's
model requests) and the batch's run table (tokens read from cache and not). Per cell, and per repetition for the cells
that have several: runs, the median over runs of the output speed and of the time to first chunk, the share of input
tokens read from cache, and the run start times (first, median, last). Output speed is the comparison that does not
depend on what the cell does (time to first chunk grows with the prompt, the cache share with how contexts are built);
a cell or repetition whose output speed differs from the reference cell's first repetition by more than 5% is marked.
When cells are marked, the time multiples are given next to the standardized ones (std_time.py) in the write-up.

The script shows interface speed and timing only, no outcome of the experiment.

Usage: phase2_balance.py --timing results/analysis-<batch>-reqtiming.json --raw results/master/raw/<batch>.csv --out results/analysis-<batch>-balance.md [--ref W-D1-K8]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import statistics as st
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timing", type=Path, required=True)
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ref", default="W-D1-K8")
    a = ap.parse_args()
    timing = {r["id"]: r for r in json.loads(a.timing.read_text(encoding="utf-8"))}
    rows = list(csv.DictReader(open(a.raw, encoding="utf-8")))
    by = collections.defaultdict(list)
    for r in rows:
        t = timing.get(r["id"])
        if not t or t.get("tps_med") is None:
            continue
        hit, miss = float(r["tok_hit"] or 0), float(r["tok_miss"] or 0)
        rec = {"tps": t["tps_med"], "ttft": (t["ttft_med_ms"] or 0) / 1000, "hit": hit, "miss": miss, "start": r["started_utc"]}
        by[(r["group"], "all")].append(rec)
        by[(r["group"], f"rep {r['rep']}")].append(rec)
    ref = by.get((a.ref, "rep 1")) or by.get((a.ref, "all"))
    if not ref:
        raise SystemExit(f"no run of the reference cell {a.ref} with request timing")
    ref_tps = st.median(x["tps"] for x in ref)
    multi = {g for (g, k) in by if k == "rep 2"}
    lines = [f"# 平衡性检查：各格拿到的接口速度（{a.raw.name}，{len(rows)} 次运行，其中 {sum(len(v) for (g, k), v in by.items() if k == 'all')} 次有请求计时）", "",
             f"参照：{a.ref} 的第一次重复，输出速度中位数 {ref_tps:.1f} token/秒。输出速度和参照差超过 5% 的行打了标记。", "",
             "| 格 | 重复 | 运行 | 输出速度中位数（token/秒） | 相对参照 | 首字时间中位数（秒） | 输入读缓存的比例 | 开始时刻（最早 / 中位 / 最晚，UTC） | 标记 |", "|---|---|---|---|---|---|---|---|---|"]
    flagged = []
    for (g, k) in sorted(by, key=lambda x: (x[0], x[1])):
        if k != "all" and g not in multi:
            continue
        v = by[(g, k)]
        tps = st.median(x["tps"] for x in v)
        ratio = tps / ref_tps
        starts = sorted(x["start"] for x in v if x["start"])
        mark = "差超过 5%" if abs(ratio - 1) > 0.05 else ""
        if mark:
            flagged.append(f"{g} {k}")
        hit, miss = sum(x["hit"] for x in v), sum(x["miss"] for x in v)
        lines.append(f"| {g} | {'全部' if k == 'all' else '第 ' + k[4:] + ' 次'} | {len(v)} | {tps:.1f} | ×{ratio:.3f} | {st.median(x['ttft'] for x in v):.2f} | "
                     f"{100 * hit / (hit + miss) if hit + miss else 0:.1f}% | {starts[0][5:16] if starts else '-'} / {starts[len(starts) // 2][5:16] if starts else '-'} / {starts[-1][5:16] if starts else '-'} | {mark} |")
    lines += ["", ("打了标记的行：" + "、".join(flagged) + "。这些格的时间倍数要和标准化时长并排报。") if flagged else "没有一行的输出速度和参照差超过 5%。"]
    a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:4]))
    print(f"{len(flagged)} rows marked: {flagged[:12]}")
    print(f"written: {a.out}")


if __name__ == "__main__":
    main()
