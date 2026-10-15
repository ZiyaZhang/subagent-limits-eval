#!/usr/bin/env python3
"""Step 3 of the follow-up plan (plan: 补强计划 第 3 步): merged single-agent reports against one delegated report.

For every merge task (M2 = two D0 reports of the confirmation batch merged by one more D0 run, M4 = four):
  merged right % / wrong count        from the fact-list judgment of the merged report
  union of its inputs                 slots at least one input report had right (the ceiling of a lossless merge)
  retention                           slots right in the merged report that were right in an input / union
  new                                 slots right in the merged report that no input had right
  total cost                          the inputs' estimated total cost + the merge run's
  total time                          the longest input + the merge run (inputs run side by side); also the sum
Block = (task, pair number). Comparator in a block = the mean of the confirmation batch's D1-K8 (and D2-K8) reports of
the same task and the same repeats. Paired differences over blocks: mean, t interval, sign-flip p.

Usage: merge_stats.py --out results/analysis-office-merge/merge-stats.json
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import statistics as st
from pathlib import Path

from scipy import stats

EXP = Path(__file__).resolve().parent.parent


def right_set(path: Path):
    d = json.loads(path.read_text(encoding="utf-8"))
    facts = d.get("facts", [])
    return ({x["id"] for x in facts if x["status"] == "对"}, sum(1 for x in facts if x["status"] == "错" and not x.get("hedged")), d.get("slots") or len(facts))


def paired(diffs: list) -> dict:
    n = len(diffs)
    if n < 2:
        return {"n": n}
    m, sd = st.mean(diffs), st.stdev(diffs)
    h = stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n)
    if n <= 20:
        tot = cnt = 0
        for signs in itertools.product((1, -1), repeat=n):
            tot += 1
            cnt += abs(sum(s * d for s, d in zip(signs, diffs)) / n) >= abs(m) - 1e-12
        p = cnt / tot
    else:
        p = float(stats.ttest_1samp(diffs, 0).pvalue)
    return {"n": n, "est": round(m, 3), "lo": round(m - h, 3), "hi": round(m + h, 3), "sd": round(sd, 3), "p": round(p, 5)}


def ratio(pairs: list) -> dict:
    logs = [math.log(a / b) for a, b in pairs if a and b and a > 0 and b > 0]
    r = paired(logs)
    return {"n": r["n"], "est": round(math.exp(r["est"]), 3), "lo": round(math.exp(r["lo"]), 3), "hi": round(math.exp(r["hi"]), 3)} if r.get("est") is not None else r


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", default="office-merge")
    ap.add_argument("--index", default="tasks/merge-index.json")
    ap.add_argument("--source-batch", default="office-confirm", help="batch of the input reports and of the comparator groups")
    ap.add_argument("--source-facts", default="results/analysis-facts-confirm/fact-rows.csv")
    ap.add_argument("--source-judge", default="results/judge-facts/office-confirm")
    ap.add_argument("--same-place-judge", default="results/judge-facts/office-confirm-hgcheck",
                    help="judgments of the comparator reports made where the merged reports were judged (the dev box)")
    ap.add_argument("--finished-only", action="store_true",
                    help="comparator runs that ended while subagents were still running are left out (plan: 第 4 步的执行记录（五）)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    idx = json.loads((EXP / a.index).read_text(encoding="utf-8"))
    mrows = {r["task"]: r for r in csv.DictReader(open(EXP / f"results/analysis-{a.batch}/rows-all.csv", encoding="utf-8"))}
    crows = list(csv.DictReader(open(EXP / f"results/analysis-{a.source_batch}/rows-all.csv", encoding="utf-8")))
    cby = {(r["task"], r["group"], int(r["rep"])): r for r in crows}
    cid = {r["id"]: r for r in crows}
    cfacts = {r["id"]: r for r in csv.DictReader(open(EXP / a.source_facts, encoding="utf-8"))}
    JM, JC = EXP / f"results/judge-facts/{a.batch}", EXP / a.source_judge
    JH = EXP / a.same_place_judge
    out, skipped = [], []
    for tid, m in sorted(idx.items()):
        r = mrows.get(tid)
        if r is None or str(r.get("incomplete")) == "1" or not (JM / f"{r['id']}.f1.json").exists():
            skipped.append(tid)
            continue
        got, wrong, slots = right_set(JM / f"{r['id']}.f1.json")
        ins = [right_set(JC / f"{i}.f1.json")[0] for i in m["inputs"]]
        union = set().union(*ins)
        row = {"task": tid, "base_task": m["base_task"], "kind": m["kind"], "block": m["n"], "run": r["id"], "slots": slots,
               "merged_right_n": len(got), "merged_right_pct": round(100 * len(got) / slots, 3), "merged_wrong_firm_n": wrong,
               "input_right_n": [len(s) for s in ins], "input_mean_right_pct": round(100 * st.mean(len(s) for s in ins) / slots, 3),
               "union_n": len(union), "union_pct": round(100 * len(union) / slots, 3),
               "retention": round(len(got & union) / len(union), 4), "new_n": len(got - union),
               "merge_chars": float(r["deliv_chars"]), "merge_search": float(r["search_aux"]), "merge_cost": float(r["total_cost_peak"]),
               "merge_seconds": float(r["seconds"]),
               "input_cost": sum(float(cid[i]["total_cost_peak"]) for i in m["inputs"]),
               "input_seconds_max": max(float(cid[i]["seconds"]) for i in m["inputs"]),
               "input_seconds_sum": sum(float(cid[i]["seconds"]) for i in m["inputs"])}
        row["total_cost"] = round(row["input_cost"] + row["merge_cost"], 4)
        row["total_seconds_parallel"] = round(row["input_seconds_max"] + row["merge_seconds"], 1)
        row["total_seconds_serial"] = round(row["input_seconds_sum"] + row["merge_seconds"], 1)
        row["researched_again"] = int(row["merge_search"] > 30)  # plan: more than 30 search requests in the merge run itself
        for g in ("D1-K8", "N-D1-K8", "D2-K8", "D0", "E-D0"):
            comp = [cby.get((m["base_task"], g, rep)) for rep in m["reps"]]
            comp = [c for c in comp if c and c["id"] in cfacts and not (a.finished_only and float(c.get("open_children_at_end") or 0) > 0)]
            row[f"{g}_n"] = len(comp)
            if comp:
                row[f"{g}_right_pct"] = round(st.mean(float(cfacts[c["id"]]["right_pct"]) for c in comp), 3)
                row[f"{g}_wrong_firm_n"] = round(st.mean(float(cfacts[c["id"]]["wrong_firm_n"]) for c in comp), 3)
                row[f"{g}_cost"] = round(st.mean(float(c["total_cost_peak"]) for c in comp), 4)
                row[f"{g}_seconds"] = round(st.mean(float(c["seconds"]) for c in comp), 1)
                hg = [JH / f"{c['id']}.f1.json" for c in comp]
                if all(f.exists() for f in hg):  # the same reports judged on the dev box, like the merged ones
                    sets = [right_set(f) for f in hg]
                    row[f"{g}_right_pct_hg"] = round(st.mean(100 * len(x[0]) / x[2] for x in sets), 3)
                    row[f"{g}_wrong_firm_n_hg"] = round(st.mean(x[1] for x in sets), 3)
        out.append(row)
    res = {"batch": a.batch, "skipped": skipped, "rows": out, "contrasts": {}, "means": {},
           "note": "contrasts against the confirmation batch's D1-K8 / D2-K8 are descriptive when the merge runs are from a later day "
                   "(plan: 审查后的修订, 第 3 步 1); *_same_place uses the comparator reports as judged on the dev box"}
    for kind in ("M2", "M4"):
        rs = [r for r in out if r["kind"] == kind]
        if not rs:
            continue
        mean = lambda k: round(st.mean(r[k] for r in rs), 3)  # noqa: E731
        res["means"][kind] = {k: mean(k) for k in ("merged_right_pct", "merged_right_n", "merged_wrong_firm_n", "input_mean_right_pct", "union_pct", "union_n",
                                                    "retention", "new_n", "merge_chars", "merge_search", "merge_cost", "merge_seconds", "total_cost",
                                                    "total_seconds_parallel", "total_seconds_serial")}
        res["means"][kind]["tasks"] = len(rs)
        res["means"][kind]["researched_again"] = sum(r["researched_again"] for r in rs)
        for g in ("D1-K8", "N-D1-K8", "D2-K8", "E-D0"):
            ok = [r for r in rs if r.get(f"{g}_n")]
            if not ok:
                continue
            hg = [r for r in ok if f"{g}_right_pct_hg" in r]
            res["contrasts"][f"{kind}_vs_{g}"] = {
                "right_pct_same_place": paired([r["merged_right_pct"] - r[f"{g}_right_pct_hg"] for r in hg]) if hg else None,
                "right_pct_same_place_merge_only": paired([r["merged_right_pct"] - r[f"{g}_right_pct_hg"] for r in hg if not r["researched_again"]]) if hg else None,
                "wrong_firm_n_same_place": paired([r["merged_wrong_firm_n"] - r[f"{g}_wrong_firm_n_hg"] for r in hg]) if hg else None,
                "right_pct": paired([r["merged_right_pct"] - r[f"{g}_right_pct"] for r in ok]),
                "wrong_firm_n": paired([r["merged_wrong_firm_n"] - r[f"{g}_wrong_firm_n"] for r in ok]),
                "total_cost_ratio": ratio([(r["total_cost"], r[f"{g}_cost"]) for r in ok]),
                "seconds_parallel_ratio": ratio([(r["total_seconds_parallel"], r[f"{g}_seconds"]) for r in ok]),
                "seconds_serial_ratio": ratio([(r["total_seconds_serial"], r[f"{g}_seconds"]) for r in ok]),
                "comparator_right_pct": round(st.mean(r[f"{g}_right_pct"] for r in ok), 3), "comparator_cost": round(st.mean(r[f"{g}_cost"] for r in ok), 3)}
        res["contrasts"][f"{kind}_vs_union"] = {"right_pct": paired([r["merged_right_pct"] - r["union_pct"] for r in rs])}
        res["contrasts"][f"{kind}_vs_one_input"] = {"right_pct": paired([r["merged_right_pct"] - r["input_mean_right_pct"] for r in rs])}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("skipped:", skipped)
    for kind, mm in res["means"].items():
        print(kind, mm)
    for k, c in res["contrasts"].items():
        print(k, json.dumps(c, ensure_ascii=False))


if __name__ == "__main__":
    main()
