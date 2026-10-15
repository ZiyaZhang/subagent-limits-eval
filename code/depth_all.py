#!/usr/bin/env python3
"""Depth 2 (and 3) against depth 1 on the two office tasks, every batch that has the contrast inside it, side by side
and pooled (post hoc, descriptive; plan: 深度对比的汇总). Reads files only.

Per batch the contrast is the one that was written down before that batch ran; pairs are (task, repeat) of the same
batch, and the row is computed like that batch's own statistics (paired_stats.py): the two tasks weighted equally,
t interval from the deviations inside each task (df = pairs - tasks). The pooled rows put all pairs together: mean of
the pair differences, t interval with the pairs' deviations taken from their own (batch, task) mean (df = pairs -
strata), and the same for the cost ratio on the log scale. Besides the row over all batches there are: the three
batches that came after the first two (the first two suggested about +4, so the later three are a check of that), the
four batches at K = 8 (for the cost), and depth 3 against depth 2 directly inside the batches that have both.

  batch      depth-1 group   deeper groups                 how it was run
  formal     D1-K8           D2-K8, D3-K8                  10 repeats, process does not wait
  confirm    D1-K8           D2-K8                         20 repeats, process does not wait
  wait2      W-D1-K8         W-D2-K8, W-D3-K8              10 repeats, process waits for the subagents
  highk      W-D1-K8         W-D2-K64, W-D3-K64            10 repeats, waits, 64 slots for the deeper groups
  keep       W-N-D1-K8       W-N-D2-K8                     10 repeats, waits, the keep-everything sentence

Usage: depth_all.py --out results/analysis-depth-all
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics as st
from pathlib import Path

from scipy import stats

EXP = Path(__file__).resolve().parent.parent
SETS = [  # name, label, fact rows, run rows, depth-1 group, {depth: group}
    ("formal", "正式实验（K=8）", "results/analysis-facts/fact-rows.csv", "results/analysis-v2/rows-office.csv", "D1-K8", {2: "D2-K8", 3: "D3-K8"}),
    ("confirm", "确认实验（K=8）", "results/analysis-facts-confirm/fact-rows.csv", "results/analysis-office-confirm/rows-all.csv", "D1-K8", {2: "D2-K8"}),
    ("wait2", "进程等subagent回来（K=8）", "results/analysis-facts-wait2/fact-rows.csv", "results/analysis-wait/rows.csv", "W-D1-K8", {2: "W-D2-K8", 3: "W-D3-K8"}),
    ("highk", "名额放到 64（进程等subagent回来）", "results/analysis-facts-highk/fact-rows.csv", "results/analysis-office-highk/rows-all.csv", "W-D1-K8", {2: "W-D2-K64", 3: "W-D3-K64"}),
    ("keep", "要求“都写进去”（进程等subagent回来，K=8）", "results/analysis-facts-keepdepth/fact-rows.csv", "results/analysis-office-keep-depth/rows-all.csv", "W-N-D1-K8", {2: "W-N-D2-K8"}),
]


def tci(diffs: dict, equal: bool = False) -> dict:
    """diffs: stratum -> list of pair differences; residual sd within strata, df = pairs - strata.
    equal = False: mean over all pairs. equal = True: the strata (the tasks of one batch) weighted equally."""
    diffs = {k: v for k, v in diffs.items() if v}
    allv = [x for v in diffs.values() for x in v]
    n, k = len(allv), len(diffs)
    ss = sum(sum((x - st.mean(v)) ** 2 for x in v) for v in diffs.values())
    sd = math.sqrt(ss / (n - k))
    if equal:
        m = st.mean(st.mean(v) for v in diffs.values())
        se = sd * math.sqrt(sum((1 / k) ** 2 / len(v) for v in diffs.values()))
    else:
        m = st.mean(allv)
        se = sd / math.sqrt(n)
    h = stats.t.ppf(0.975, n - k) * se
    p = 2 * (1 - stats.t.cdf(abs(m) / se, n - k))
    return {"n": n, "est": m, "lo": m - h, "hi": m + h, "p": p}


_MASTER = {}


def answer_seconds(r: dict) -> float:
    """Time to the root's final answer. Batches without that column take it from the run-level table
    (results/master/runs.csv, read from the session logs); the process duration is never used in its place."""
    v = r.get("answer_s")
    if v not in (None, "") and float(v) > 0:
        return float(v)
    if not _MASTER:
        _MASTER.update({x["id"]: x for x in csv.DictReader(open(EXP / "results/master/runs.csv", encoding="utf-8"))})
    m = _MASTER[r["id"]]
    assert m["t_answer_s"] != "", r["id"]
    return float(m["t_answer_s"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    res = {"rows": [], "pooled": {}}
    pool = {2: ({}, {}), 3: ({}, {})}
    pool_t, pool_l = {2: {}, 3: {}}, {2: {}, 3: {}}  # time to the answer (log ratio), share on the 63 pre-set items
    d32, c32, l32 = {}, {}, {}
    for name, label, fp, rp, base, deeper in SETS:
        if not (EXP / fp).exists() or not (EXP / rp).exists():
            continue
        facts = {r["id"]: r for r in csv.DictReader(open(EXP / fp, encoding="utf-8"))}
        runs = [r for r in csv.DictReader(open(EXP / rp, encoding="utf-8")) if r["task"].startswith("o") and r["id"] in facts and str(r.get("incomplete", "0")) != "1"]
        by = {(r["task"], int(r["rep"]), r["group"]): r for r in runs}
        for depth, g in deeper.items():
            d, c, tm, lg = {}, {}, {}, {}
            for (t, rep, gg), r in by.items():
                if gg != g or (t, rep, base) not in by:
                    continue
                b = by[(t, rep, base)]
                d.setdefault((name, t), []).append(float(facts[r["id"]]["right_pct"]) - float(facts[b["id"]]["right_pct"]))
                c.setdefault((name, t), []).append(math.log(float(r["total_cost_peak"]) / float(b["total_cost_peak"])))
                tm.setdefault((name, t), []).append(math.log(answer_seconds(r) / answer_seconds(b)))
                lg.setdefault((name, t), []).append(float(facts[r["id"]]["right_legacy_pct"]) - float(facts[b["id"]]["right_legacy_pct"]))
            x, y = tci(d, equal=True), tci(c, equal=True)
            z, w = tci(tm, equal=True), tci(lg, equal=True)
            pool_t[depth].update(tm)
            pool_l[depth].update(lg)
            res["rows"].append({"batch": name, "label": label, "depth": depth, "group": g, "base": base, "pairs": x["n"], "est": round(x["est"], 3), "lo": round(x["lo"], 3),
                                "hi": round(x["hi"], 3), "p": round(x["p"], 4), "cost_ratio": round(math.exp(y["est"]), 3), "cost_lo": round(math.exp(y["lo"]), 3),
                                "cost_hi": round(math.exp(y["hi"]), 3),
                                "time_ratio": round(math.exp(z["est"]), 3), "time_lo": round(math.exp(z["lo"]), 3), "time_hi": round(math.exp(z["hi"]), 3),
                                "time_source": "answer" if any(r.get("answer_s") not in (None, "") for r in runs) else "answer (run-level table)",
                                "legacy_est": round(w["est"], 3), "legacy_lo": round(w["lo"], 3), "legacy_hi": round(w["hi"], 3),
                                "by_task": {k[1][:2]: round(st.mean(v), 2) for k, v in d.items()}})
            pool[depth][0].update(d)
            pool[depth][1].update(c)
        if 2 in deeper and 3 in deeper:  # depth 3 against depth 2 directly, inside the batch
            for (t, rep, gg), r in by.items():
                if gg == deeper[3] and (t, rep, deeper[2]) in by:
                    b2 = by[(t, rep, deeper[2])]
                    d32.setdefault((name, t), []).append(float(facts[r["id"]]["right_pct"]) - float(facts[b2["id"]]["right_pct"]))
                    c32.setdefault((name, t), []).append(math.log(float(r["total_cost_peak"]) / float(b2["total_cost_peak"])))
                    l32.setdefault((name, t), []).append(float(facts[r["id"]]["right_legacy_pct"]) - float(facts[b2["id"]]["right_legacy_pct"]))
    for depth in (2, 3):
        d, c = pool[depth]
        if not d:
            continue
        x, y = tci(d), tci(c)
        res["pooled"][str(depth)] = {"pairs": x["n"], "batches": len({k[0] for k in d}), "est": round(x["est"], 3), "lo": round(x["lo"], 3), "hi": round(x["hi"], 3), "p": round(x["p"], 5),
                                     "cost_ratio": round(math.exp(y["est"]), 3), "cost_lo": round(math.exp(y["lo"]), 3), "cost_hi": round(math.exp(y["hi"]), 3),
                                     "positive_batches": sum(1 for r in res["rows"] if r["depth"] == depth and r["est"] > 0)}

    def pooled(d: dict, c: dict) -> dict:
        x, y = tci(d), tci(c)
        return {"pairs": x["n"], "batches": len({k[0] for k in d}), "est": round(x["est"], 3), "lo": round(x["lo"], 3), "hi": round(x["hi"], 3), "p": round(x["p"], 5),
                "cost_ratio": round(math.exp(y["est"]), 3), "cost_lo": round(math.exp(y["lo"]), 3), "cost_hi": round(math.exp(y["hi"]), 3)}
    d2, c2 = pool[2]
    later = ("wait2", "highk", "keep")
    res["pooled"]["2_later_three"] = pooled({k: v for k, v in d2.items() if k[0] in later}, {k: v for k, v in c2.items() if k[0] in later})
    res["pooled"]["2_first_two"] = pooled({k: v for k, v in d2.items() if k[0] not in later}, {k: v for k, v in c2.items() if k[0] not in later})
    res["pooled"]["2_k8"] = pooled({k: v for k, v in d2.items() if k[0] != "highk"}, {k: v for k, v in c2.items() if k[0] != "highk"})
    if d32:
        res["pooled"]["3_vs_2"] = pooled(d32, c32)
        res["pooled"]["3_vs_2_k8"] = pooled({k: v for k, v in d32.items() if k[0] != "highk"}, {k: v for k, v in c32.items() if k[0] != "highk"})
        for key_, keep_ in (("3_vs_2", lambda b: True), ("3_vs_2_k8", lambda b: b != "highk")):  # the same contrast on the 63 items fixed beforehand
            w_ = tci({k: v for k, v in l32.items() if keep_(k[0])})
            res["pooled"][key_].update({"legacy_est": round(w_["est"], 3), "legacy_lo": round(w_["lo"], 3), "legacy_hi": round(w_["hi"], 3), "legacy_p": round(w_["p"], 5)})
    d3, c3 = pool[3]
    if d3:  # depth 3 against depth 1 with K = 8 on both sides (the batch that also raises K to 64 left out)
        res["pooled"]["3_k8"] = pooled({k: v for k, v in d3.items() if k[0] != "highk"}, {k: v for k, v in c3.items() if k[0] != "highk"})

    def extra(key: str, keep) -> None:
        """Time and pre-set-item share pooled the same way, added to an existing pooled entry."""
        depth = int(key[0])
        z = tci({k: v for k, v in pool_t[depth].items() if keep(k[0])})
        w = tci({k: v for k, v in pool_l[depth].items() if keep(k[0])})
        res["pooled"][key].update({"time_ratio": round(math.exp(z["est"]), 3), "time_lo": round(math.exp(z["lo"]), 3), "time_hi": round(math.exp(z["hi"]), 3),
                                   "legacy_est": round(w["est"], 3), "legacy_lo": round(w["lo"], 3), "legacy_hi": round(w["hi"], 3), "legacy_p": round(w["p"], 5)})
    extra("2", lambda b: True)
    extra("3", lambda b: True)
    extra("2_later_three", lambda b: b in later)
    extra("2_first_two", lambda b: b not in later)
    extra("2_k8", lambda b: b != "highk")
    if "3_k8" in res["pooled"]:
        extra("3_k8", lambda b: b != "highk")
    (a.out / "depth-all.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in res["rows"]:
        print(f"depth {r['depth']} | {r['batch']:8s} {r['group']:10s} vs {r['base']:10s} | pairs {r['pairs']:3d} | {r['est']:+.1f} [{r['lo']:+.1f}, {r['hi']:+.1f}] p={r['p']:.3f} | cost x{r['cost_ratio']:.2f}")
    for r in res["rows"]:
        print("   by task:", r["batch"], r["depth"], r["by_task"])
    for k, v in res["pooled"].items():
        print(f"pooled {k} ({v['batches']} batches): pairs {v['pairs']} | {v['est']:+.2f} [{v['lo']:+.2f}, {v['hi']:+.2f}] p={v['p']:.5f} | cost x{v['cost_ratio']:.2f} [{v['cost_lo']:.2f}, {v['cost_hi']:.2f}]"
              + (f" | time x{v['time_ratio']:.2f} [{v['time_lo']:.2f}, {v['time_hi']:.2f}] | pre-set items {v['legacy_est']:+.2f} [{v['legacy_lo']:+.2f}, {v['legacy_hi']:+.2f}]" if "time_ratio" in v else ""))
    for r in res["rows"]:
        print(f"   time ({r['time_source']}): {r['batch']:8s} depth {r['depth']} x{r['time_ratio']:.2f} [{r['time_lo']:.2f}, {r['time_hi']:.2f}] | pre-set items {r['legacy_est']:+.1f} [{r['legacy_lo']:+.1f}, {r['legacy_hi']:+.1f}]")


if __name__ == "__main__":
    main()
