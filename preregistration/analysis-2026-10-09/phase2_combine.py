#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Appendix, exploratory (protocol v5.1 section 七, "合并"): the contrasts both phases have, each phase's own estimate and
a random-effects combination of the two.

Phase 1 ran DeepResearch Bench II on 30 tasks in three batches, each with its own default cell: drb2-h1 (no subagents
against the default), drb2-kd (K=1 and depth 2 with K=8 against the default), drb2-k4 (K=4 against the default). Its
reports are re-judged by the phase-2 judge (results/drb2-score-gpt/<batch>/), so both phases are on one scale.
  phase 1  paired difference within task and batch, t interval over tasks; a pair with a flagged run (the batch's
           sources.json) is left out
  phase 2  the paired difference of phase2_report.py (contrasts.csv, version confirmatory, method paired-t)
  combined DerSimonian-Laird random effects over the two estimates. With two studies the between-phase variance is
           barely estimable; the phases also share 30 tasks. The combination is a summary for the appendix, not a test.
Nothing here enters the confirmatory analysis.

Usage: phase2_combine.py --phase1 results --judge results/drb2-score-gpt --contrasts results/analysis-phase2/contrasts.csv --out results/analysis-phase2/combined.md
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics as st
from pathlib import Path

# (label, phase-1 batch, phase-1 group, phase-1 reference group, phase-2 cell, phase-2 reference)
PAIRS = [("默认对不开", "drb2-h1", "W-D1-K8", "D0", "K8", "D0"), ("K=4 对默认", "drb2-k4", "W-D1-K4", "W-D1-K8", "K4", "K8"),
         ("K=1 对默认", "drb2-kd", "W-D1-K1", "W-D1-K8", "K1", "K8"), ("深度 2 配 K=8 对默认", "drb2-kd", "W-D2-K8", "W-D1-K8", "D2K8", "K8")]
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 12: 2.179, 15: 2.131, 20: 2.086,
        25: 2.060, 28: 2.048, 29: 2.045, 30: 2.042, 40: 2.021, 60: 2.000, 120: 1.980}


def tq(df: int) -> float:
    try:
        from scipy import stats
        return float(stats.t.ppf(0.975, df))
    except Exception:  # noqa: BLE001
        return T975[min(T975, key=lambda k: abs(k - df))]


def phase1(base: Path, judge: Path, batch: str, a: str, b: str) -> dict:
    rows = list(csv.DictReader(open(base / f"analysis-{batch}" / "rows-all.csv", encoding="utf-8")))
    src = base / f"analysis-{batch}" / "sources.json"
    flagged = {x["id"] for x in json.loads(src.read_text(encoding="utf-8")) if (x.get("n_hits") or 0) > 0} if src.exists() else set()
    score, missing = {}, 0
    for r in rows:
        f = judge / batch / f"{r['id']}.r1.json"
        if not f.exists():
            missing += 1
            continue
        t = json.loads(f.read_text(encoding="utf-8")).get("total")
        if t is not None and r["id"] not in flagged and r.get("incomplete") != "1":
            score[(r["task"], r["group"])] = float(t)
    d = [score[(t, a)] - score[(t, b)] for (t, g) in score if g == a and (t, b) in score]
    if len(d) < 3:
        return {"n": len(d), "missing": missing}
    est, se = st.mean(d), st.stdev(d) / math.sqrt(len(d))
    q = tq(len(d) - 1)
    return {"n": len(d), "est": est, "se": se, "lo": est - q * se, "hi": est + q * se, "missing": missing, "flagged": len(flagged)}


def phase2(path: Path, a: str, b: str) -> dict:
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if (r["version"], r["family"], r["cell"], r["ref"], r["outcome"], r["method"]) == ("confirmatory", "A", a, b, "q", "paired-t") and r["estimate"]:
            return {"n": int(float(r["n_pairs"])), "est": float(r["estimate"]), "se": float(r["se"]), "lo": float(r["lower"]), "hi": float(r["upper"])}
    return {}


def pool(parts: list) -> dict:
    w = [1 / p["se"] ** 2 for p in parts]
    fixed = sum(wi * p["est"] for wi, p in zip(w, parts)) / sum(w)
    q = sum(wi * (p["est"] - fixed) ** 2 for wi, p in zip(w, parts))
    c = sum(w) - sum(wi ** 2 for wi in w) / sum(w)
    tau2 = max(0.0, (q - (len(parts) - 1)) / c) if c > 0 else 0.0
    ws = [1 / (p["se"] ** 2 + tau2) for p in parts]
    est = sum(wi * p["est"] for wi, p in zip(ws, parts)) / sum(ws)
    se = math.sqrt(1 / sum(ws))
    return {"est": est, "se": se, "lo": est - 1.96 * se, "hi": est + 1.96 * se, "tau": math.sqrt(tau2)}


def f(x: dict) -> str:
    return f"{x['est']:+.1f} [{x['lo']:+.1f}, {x['hi']:+.1f}]" if "est" in x else "没算出"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase1", type=Path, required=True, help="directory holding analysis-<batch>/rows-all.csv and sources.json of phase 1")
    ap.add_argument("--judge", type=Path, required=True, help="judge directory with <batch>/<id>.r1.json for the phase-1 batches")
    ap.add_argument("--contrasts", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    lines = ["# 两阶段都有的对比（探索，进附录）", "",
             "第一阶段的 150 份评测集报告用第二阶段的判分模型重判过，两阶段在同一把尺子上。合并用随机效应；只有两个阶段，且共用 30 道题，合并值只是摘要，不作检验。", "",
             "| 对比 | 第一阶段（题数） | 第二阶段（题数） | 合并 | 阶段间标准差 |", "|---|---|---|---|---|"]
    for label, batch, g, ref, c2, r2 in PAIRS:
        p1, p2 = phase1(a.phase1, a.judge, batch, g, ref), phase2(a.contrasts, c2, r2)
        both = [p for p in (p1, p2) if "est" in p]
        pl = pool(both) if len(both) == 2 else {}
        lines.append(f"| {label} | {f(p1)}（{p1.get('n', 0)}） | {f(p2)}（{p2.get('n', 0)}） | {f(pl)} | {pl['tau']:.1f} |" if pl
                     else f"| {label} | {f(p1)}（{p1.get('n', 0)}） | {f(p2)}（{p2.get('n', 0)}） | 没算出 | |")
        print(label, "| phase 1:", f(p1), "n", p1.get("n"), "missing judge files", p1.get("missing"), "| phase 2:", f(p2), "| pooled:", f(pl))
    a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("written:", a.out)


if __name__ == "__main__":
    main()
