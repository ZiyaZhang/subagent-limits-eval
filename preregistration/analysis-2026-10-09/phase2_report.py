#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase-2 analysis driver: every contrast, level and curve of the pre-registered plan, from the run-level master table.

Protocol: phase2-experiment-protocol-2026-10-08.md, sections 四 (cells), 六 (metrics), 七 (analysis plan). This script
adds no analysis choice of its own; where the plan left a detail open the choice is listed under "Reading of the plan"
below and in the protocol's change log (made on 2026-10-09 before any report was judged).

What it computes
  * cells: a run's cell is its depth limit, its K and the sentence appended to the prompt (the master table's D, K, hint):
      D0 / K8 / D2K8 ...   no sentence          n3K8, n8K2 ... n8K8   "split into n parts, one subagent each" (module B)
      more, seg            single agent told to search more / to work in 8 segments (module G)
      planK8               root agent told to plan and merge only (module O)
      merge4               four independent single-agent reports merged by a fifth single-agent run (module G)
  * the 9 confirmatory contrasts (one family, Holm): each from a model with only its two cells (task random intercept,
    plus a task x cell variance component when a cell has two runs per task); contrast 8 is the linear trend of quality
    over log2 K in the four n8 cells. Paired differences within task are printed next to every model estimate.
  * every exploratory contrast needed for the tables and the curves (K curves, D curves, mechanism, other model,
    coding tasks, orchestration), from the two-cell model, the paired differences and the family's joint model.
  * levels per cell (quality, money, time, subagents wanted and opened, share of runs stuck at the cap, exit statuses,
    leak rate), the demand curves (share of runs whose peak of live subagents exceeds k), Table 1, the pre-registered
    rule for recommending a default, and two sensitivity versions of the confirmatory family.

Rows
  confirmatory set   status ok, complete != 0, not flagged as a leak (recognized != 1)
  all-runs version   failures kept and scored as they are (a run that handed in no report counts 0), leaks dropped
  with-leaks version leaks kept, failures dropped
  rep1 version       the confirmatory set restricted to the first repetition of every cell. The runner ran every first
                     repetition before any second one (dsec_matrix_v6 orders blocks by repetition), so the second runs
                     of the cells that have two (default, depth 2 with K=8, "8 parts" with K=4 and K=8) and the extra
                     "no subagents" runs came hours later than the cells they are compared with. Money and time
                     multiples are therefore given in this version too; merge4 has no rep1 version (it needs all four).
  Reference cells (the default K8 and "no subagents" D0): a flagged run is replaced by another run of the same task and
  cell when there is one (K8 has two runs; D0 has four on the 40 tasks of module G); a task whose reference cell has no
  unflagged run leaves every contrast of its batch and is listed. A cell with more than 8% flagged runs is descriptive
  only: its contrasts get no verdict word.

Reading of the plan (decided blind, 2026-10-09)
  * A verdict word (优效 / 显著更差) on a confirmatory contrast needs both the 95% interval excluding 0 and the
    Holm-adjusted p below 0.05; otherwise 没测出 with the interval. Exploratory contrasts get the interval and no word.
  * merge4 is one pipeline: money and search requests are the four input runs plus the merge run; the time the user
    waits is the slowest input plus the merge run (the four inputs can run side by side); it is flagged when any of the
    five runs is flagged, and failed when the merge run failed.
  * Module G's reference "no subagents" uses every unflagged D0 run of the task (up to four), the other families the
    first one.
  * The coding tasks (module F) are one task each: contrasts pair the runs of one repetition (they ran in one round) and
    use a t interval over the repetitions; no mixed model.

Usage (dev box: source haienv py312-202505; PYTHONPATH with statsmodels):
  python phase2_report.py --runs results/master/runs.csv --out results/analysis-phase2 [--merge-index tasks/phase2-merge-index.json]
Outputs in --out: contrasts.csv, confirmatory.md, table1.md, levels.csv, demand.csv, recommend.md, runs_used.csv, summary.md, run.log
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase2_models as pm  # noqa: E402

BATCHES = ["p2-main", "p2-merge", "p2-d", "p2-f", "p2-o"]
HINT_TAG = {"none": "", "": None, "split-3-delegate": "n3", "split-8-delegate": "n8", "search-150-250": "more", "split-8-self": "seg",
            "planner-only": "plan"}
NUM = ["D", "K", "rep", "q", "total_yuan", "model_yuan", "search_yuan", "t_answer_s", "all_written_s", "t_last_write_s", "search_requests",
       "agents", "kids_d1", "kids_d2", "kids_d3", "spawn_calls", "rejected_cap", "rejected_depth", "peak_alive", "peak_alive_d1",
       "recognized", "complete", "oom_kill", "kids_after_answer", "drb2_recall", "drb2_analysis", "drb2_presentation", "tok_miss", "tok_hit",
       "tok_out", "report_chars", "q_opus", "q_gpt_r2"]
OUT_REPORT = [("q", "diff"), ("total_yuan", "ratio"), ("model_yuan", "ratio"), ("t_answer_s", "ratio"), ("search_requests", "ratio"),
              ("drb2_recall", "diff"), ("drb2_analysis", "diff"), ("drb2_presentation", "diff")]
OUT_CODE = [("q", "diff"), ("total_yuan", "ratio"), ("t_answer_s", "ratio"), ("all_written_s", "ratio")]
LEAK_MAX = 0.08
A_CELLS = ["K8", "D0", "K1", "K2", "K3", "K4", "D2K8", "D2K16", "D3K8", "D2K2", "D2K4", "D3K2", "D3K4", "D3K16", "D3K64"]
B_CELLS = ["n8K8", "n8K2", "n8K4", "n8K6", "n3K8", "K8", "D0"]
G_CELLS = ["D0", "more", "seg", "merge4", "K8", "n3K8", "n8K8"]
D_CELLS = ["K8", "D0", "K2", "D2K8", "D3K64"]
TABLE1 = ["D0", "K1", "K2", "K3", "K4", "D2K8", "D2K16", "D3K8"]
# the pre-registered family (protocol 七): id, family, cell, reference, test, what was expected
CONFIRMATORY = [
    ("C1", "A", "K8", "D0", "优效", "+2 到 +5"),
    ("C2", "A", "K4", "K8", "显著更差检验", "没测出，排除 2.5 分以上的损失"),
    ("C3", "A", "D2K8", "K8", "优效检验", "不优效，排除 2 分以上的提高"),
    ("C4", "A", "D3K8", "D2K8", "优效检验", "不优效"),
    ("C5", "A", "D2K16", "D2K8", "优效检验", "不优效，费用更高"),
    ("C6", "B", "n8K8", "n3K8", "优效检验", "不优效，费用约两倍"),
    ("C7", "B", "n8K4", "n8K8", "显著更差检验", "没测出或小幅更差，时间更长"),
    ("C8", "B", "trend", "n8K2..n8K8", "趋势 > 0", "正"),
    ("C9", "D", "K8", "D0", "优效", "方向为正"),
]
TREND_CELLS = [("n8K2", 2), ("n8K4", 4), ("n8K6", 6), ("n8K8", 8)]
EXPLORATORY = {  # family -> [(cell, reference)]
    "A": [(c, "K8") for c in A_CELLS[1:]] + [("K1", "D0"), ("K8", "K1"), ("D2K2", "K2"), ("D3K2", "K2"), ("D3K2", "D2K2"), ("D2K4", "K4"),
                                              ("D3K4", "K4"), ("D3K4", "D2K4"), ("D3K16", "D2K16"), ("D3K64", "D3K16"), ("D3K16", "D3K8")],
    "B": [("n3K8", "K8"), ("n8K8", "K8"), ("n8K4", "K8"), ("n8K2", "n8K8"), ("n8K6", "n8K8"), ("n3K8", "D0"), ("n8K8", "D0")],
    "G": [("more", "D0"), ("seg", "D0"), ("merge4", "D0"), ("K8", "D0"), ("n3K8", "D0"), ("n8K8", "D0"), ("more", "K8"), ("seg", "K8"), ("merge4", "K8")],
    "D": [("D0", "K8"), ("K2", "K8"), ("D2K8", "K8"), ("D3K64", "K8")],
    "A@D": [("K8", "D0"), ("D0", "K8"), ("K2", "K8"), ("D2K8", "K8"), ("D3K64", "K8")],
    "O": [("planK8", "K8")],
}
TRANSFER = [("K8", "D0"), ("K2", "K8"), ("D2K8", "K8"), ("D3K64", "K8")]  # effect in v4-pro minus the same effect in flash, same tasks
JOINT = {"A": ("K8", A_CELLS), "B": ("n8K8", B_CELLS), "G": ("D0", G_CELLS), "D": ("K8", D_CELLS)}
STATUS5 = ["完成", "提前结束", "退出时崩溃", "超时", "内存被杀", "其他非零退出"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ rows and cells
def cell_of(r) -> str:
    d = int(r["D"])
    base = "D0" if d == 0 else (f"K{int(r['K'])}" if d == 1 else f"D{d}K{int(r['K'])}")
    if r["batch"] == "p2-merge":
        return "merge-step"
    tag = HINT_TAG.get(r["hint"], "?")
    if tag is None or tag == "?":
        return "UNRESOLVED"
    if tag == "":
        return base
    if tag in ("more", "seg"):
        return tag if base == "D0" else "UNRESOLVED"
    return tag + base


def status5(r) -> str:
    if r["oom_kill"] == 1:
        return "内存被杀"
    return {"ok": "完成", "no_answer": "提前结束", "crash_at_exit": "退出时崩溃", "timeout": "超时"}.get(r["status"], "其他非零退出")


def load(path: Path, merge_index: Path | None, log) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    df = raw[raw["batch"].isin(BATCHES) & (raw["module"] != "pilot")].copy()
    log(f"input: {path} (sha256 {sha256(path)[:16]}...), {len(raw)} rows, phase-2 rows: {len(df)}")
    if df.empty:
        raise SystemExit("no phase-2 rows in the master table")
    simulated = bool((df["q_metric"] == "SIMULATED").any() or df["id"].str.startswith("sim-").any())
    if simulated:
        log("\n" + "!" * 100 + "\n!! SIMULATED ROWS: this is a dry run of the code. Nothing below is a result.\n" + "!" * 100 + "\n")
    for c in NUM:
        if c not in df.columns:
            df[c] = ""
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["cell"] = [cell_of(r) for _, r in df.iterrows()]
    bad = df[df["cell"] == "UNRESOLVED"]
    if len(bad):
        raise SystemExit(f"{len(bad)} runs whose sentence could not be resolved (hint empty or unknown): {bad['id'].tolist()[:20]}")
    if df["recognized"].isna().all():
        log("WARNING: the leak column (recognized) is empty for every phase-2 row: the leak check has not been joined; no run is treated as flagged")
    else:
        miss = df[(df["family"] == "drb2") & df["recognized"].isna()]
        if len(miss):
            log(f"WARNING: {len(miss)} report runs have no leak flag (treated as not flagged): batches {miss['batch'].value_counts().to_dict()}")
    df["leak"] = (df["recognized"] == 1)
    df["status5"] = [status5(r) for _, r in df.iterrows()]
    df["failed"] = (df["status"] != "ok") | (df["complete"] == 0)
    df["opened"] = df[["kids_d1", "kids_d2", "kids_d3"]].fillna(0).sum(axis=1)
    df["wanted"] = df["opened"] + df["rejected_cap"].fillna(0) + df["rejected_depth"].fillna(0)
    df["base_task"] = df["task"].str.replace("_m4_", "_zh_", regex=False)
    df["simulated"] = simulated
    df.attrs["simulated"] = simulated
    df.attrs["merge_index"] = json.loads(merge_index.read_text(encoding="utf-8")) if merge_index and merge_index.exists() else None
    log("phase-2 rows by batch and module: " + ", ".join(f"{b}/{m}={n}" for (b, m), n in df.groupby(["batch", "module"]).size().items()))
    return df


def merge_pipeline(df: pd.DataFrame, log) -> pd.DataFrame:
    """One row per merge task: the merge run's quality, the money / requests of the four inputs plus the merge run, the wait
    of the slowest input plus the merge run. Inputs: the ids in the merge index, else the D0 runs (repeats 1-4) of the task."""
    steps = df[df["batch"] == "p2-merge"]
    if steps.empty:
        return steps.copy()
    main = df[df["batch"] == "p2-main"]
    index = df.attrs.get("merge_index") or {}
    out, src = [], {"index": 0, "repeats 1-4": 0}
    for _, m in steps.iterrows():
        ids = [x["id"] for x in index.get(m["task"], {}).get("inputs", [])]
        inp = main[main["id"].isin(ids)] if ids else main.iloc[0:0]
        if len(inp) == 4:
            src["index"] += 1
        else:
            inp = main[(main["task"] == m["base_task"]) & (main["cell"] == "D0") & (main["rep"] <= 4)]
            src["repeats 1-4"] += 1
        if len(inp) != 4:
            log(f"  merge {m['task']}: {len(inp)} input runs found instead of 4; pipeline row skipped")
            continue
        r = m.copy()
        r["cell"], r["batch"], r["task"] = "merge4", "p2-main", m["base_task"]
        for c in ("total_yuan", "model_yuan", "search_yuan", "search_requests"):
            r[c] = float(inp[c].sum()) + (0.0 if pd.isna(m[c]) else float(m[c]))
        r["t_answer_s"] = float(inp["t_answer_s"].max()) + float(m["t_answer_s"]) if pd.notna(m["t_answer_s"]) else np.nan
        r["merge_step_yuan"], r["merge_step_s"] = m["total_yuan"], m["t_answer_s"]
        r["leak"] = bool(m["leak"] or inp["leak"].any())
        r["input_ids"] = " ".join(inp["id"])
        out.append(r)
    log(f"merge pipelines: {len(out)} of {len(steps)} merge runs; inputs from " + ", ".join(f"{k} {v}" for k, v in src.items() if v))
    return pd.DataFrame(out)


def pick_d0(main: pd.DataFrame, keep_leaks: bool) -> pd.DataFrame:
    """The "no subagents" run of each task for families A, B and A@D: repeat 1, or the lowest unflagged repeat when repeat 1 is flagged."""
    d0 = main[main["cell"] == "D0"].sort_values(["task", "rep"])
    if keep_leaks:
        return d0[d0["rep"] == 1]
    first_clean = d0[~d0["leak"]].groupby("task", as_index=False).head(1)
    return first_clean


def dropped_tasks(batch_df: pd.DataFrame, refs=("K8", "D0")) -> dict:
    """Tasks whose reference cell has runs and all of them are flagged: they leave every contrast of the batch."""
    out = {}
    for ref in refs:
        g = batch_df[batch_df["cell"] == ref].groupby("task")["leak"].agg(["all", "size"])
        for t in g.index[g["all"] & (g["size"] > 0)]:
            out.setdefault(t, []).append(ref)
    return out


def build_families(df: pd.DataFrame, mode: str, log) -> tuple:
    """mode: confirmatory / all-runs / with-leaks / rep1. Returns ({family: frame}, notes)."""
    keep_leaks, keep_failed = mode == "with-leaks", mode == "all-runs"
    notes = {"dropped_tasks": {}, "mode": mode}
    work = df.copy()
    if mode == "rep1":
        work = work[(work["rep"] == 1) & (work["batch"] != "p2-merge")]
    if keep_failed:  # a run that handed in nothing satisfies nothing
        none = work["q"].isna() & (work["complete"] == 0) & (work["family"] == "drb2")
        work.loc[none, ["q", "drb2_recall", "drb2_analysis", "drb2_presentation"]] = 0.0
        notes["scored_zero"] = int(none.sum())
    main = work[work["batch"] == "p2-main"]
    pipes = merge_pipeline(work, log if mode == "confirmatory" else (lambda *_: None))
    nat = main[main["hint"].isin(["none"])]
    fam = {}
    d0 = pick_d0(main, keep_leaks)
    fam["A"] = pd.concat([nat[(nat["cell"] != "D0") & nat["cell"].isin(A_CELLS)], d0])
    b_rows = main[main["cell"].isin(["n3K8", "n8K2", "n8K4", "n8K6", "n8K8"])]
    fam["B"] = pd.concat([b_rows, nat[nat["cell"] == "K8"], d0])
    g40 = set(main.loc[main["cell"].isin(["more", "seg"]), "task"])
    g_rows = main[main["task"].isin(g40) & main["cell"].isin(["D0", "more", "seg", "K8", "n3K8", "n8K8"])]
    fam["G"] = pd.concat([g_rows, pipes]) if len(pipes) else g_rows
    dd = work[work["batch"] == "p2-d"]
    fam["D"] = dd
    d_tasks = set(dd["task"])
    fam["A@D"] = pd.concat([nat[nat["task"].isin(d_tasks) & nat["cell"].isin(["K2", "K8", "D2K8", "D3K64"])], d0[d0["task"].isin(d_tasks)]])
    fam["O"] = work[work["batch"] == "p2-o"]
    ff = work[work["batch"] == "p2-f"]
    for t in sorted(ff["task"].unique()):
        fam[f"F:{t}"] = ff[ff["task"] == t]
    # reference cells with no unflagged run: the task leaves every contrast of its batch
    drop = {}
    if not keep_leaks:
        drop["p2-main"] = dropped_tasks(main[main["hint"] == "none"])
        drop["p2-d"] = dropped_tasks(dd)
        drop["p2-o"] = dropped_tasks(fam["O"], refs=("K8",))
    notes["dropped_tasks"] = drop
    batch_of = {"A": "p2-main", "B": "p2-main", "G": "p2-main", "A@D": "p2-main", "D": "p2-d", "O": "p2-o"}
    out = {}
    for name, f in fam.items():
        f = f.copy()
        n0 = len(f)
        gone = set(drop.get(batch_of.get(name, ""), {}))
        if name == "A@D":
            gone |= set(drop.get("p2-d", {}))
        if name == "D":
            gone |= set(drop.get("p2-main", {})) & set(f["task"])  # keeps the two models on the same tasks for the transfer difference
        f = f[~f["task"].isin(gone)]
        n_task_drop = n0 - len(f)
        if not keep_leaks:
            f = f[~f["leak"]]
        n_leak = n0 - n_task_drop - len(f)
        if not keep_failed:
            f = f[~f["failed"]]
        n_fail = n0 - n_task_drop - n_leak - len(f)
        notes[name] = {"rows_in": n0, "task_dropped_rows": n_task_drop, "leak_rows": n_leak, "failed_rows": n_fail, "rows_used": len(f),
                       "tasks": int(f["task"].nunique())}
        out[name] = f
    return out, notes


# ------------------------------------------------------------------------------------------------ estimates
def as_cells(f: pd.DataFrame, cells: list) -> pd.DataFrame:
    sub = f[f["cell"].isin(cells)].copy()
    sub["cell"] = pd.Categorical(sub["cell"], categories=cells)
    sub["task"] = sub["task"].astype(str)
    sub["batch"] = "one"
    return sub


def quiet(*_a, **_k):
    return None


def two_cell(f: pd.DataFrame, a: str, b: str, outcomes: list, errors: list, tag: str) -> list:
    """Model with only the two cells (reference b) and the paired differences, for every outcome that has data."""
    rows = []
    sub = as_cells(f, [b, a])
    if sub["cell"].nunique() < 2 or (sub["cell"] == a).sum() == 0 or (sub["cell"] == b).sum() == 0:
        errors.append(f"{tag} {a}/{b}: a cell has no rows")
        return rows
    for col, scale in outcomes:
        vals = sub[col]
        if vals.notna().sum() == 0 or (scale == "ratio" and (vals.fillna(0) <= 0).all()):
            continue
        try:
            tab = pm.analyse(sub, [(col, scale)], [(a, b)], b, quiet, [])
        except (SystemExit, Exception) as e:  # noqa: BLE001  (one contrast must not stop the report)
            errors.append(f"{tag} {a}/{b} {col}: {type(e).__name__}: {str(e)[:200]}")
            continue
        tab["method"] = tab["method"].replace({"mixed": "mixed2"})
        rows += tab.to_dict("records")
    return rows


def joint(f: pd.DataFrame, ref: str, cells: list, pairs: list, outcomes: list, errors: list, tag: str, log) -> list:
    rows = []
    present = [c for c in cells if (f["cell"] == c).any()]
    if ref not in present:
        errors.append(f"{tag} joint model: reference {ref} has no rows")
        return rows
    sub = as_cells(f, [ref] + [c for c in present if c != ref])
    pairs = [(a, b) for a, b in pairs if a in present and b in present]
    for col, scale in outcomes:
        if sub[col].notna().sum() == 0:
            continue
        try:
            tab = pm.analyse(sub, [(col, scale)], pairs, ref, quiet, [])
        except (SystemExit, Exception) as e:  # noqa: BLE001
            errors.append(f"{tag} joint model {col}: {type(e).__name__}: {str(e)[:200]}")
            continue
        tab = tab[tab["method"] == "mixed"].copy()
        tab["method"] = "joint"
        rows += tab.to_dict("records")
    log(f"  joint model {tag}: reference {ref}, cells {present}, {len(sub)} rows")
    return rows


def trend(f: pd.DataFrame, errors: list) -> list:
    """Contrast 8: slope of quality per doubling of K over the four n8 cells: the linear contrast of the cell means with
    weights (x - mean x) / sum (x - mean x)^2, x = log2 K, from the model of the four cells; and the same slope per task."""
    from scipy import stats

    cells = [c for c, _ in TREND_CELLS]
    x = np.array([math.log2(k) for _, k in TREND_CELLS])
    w = (x - x.mean()) / ((x - x.mean()) ** 2).sum()
    sub = as_cells(f, [cells[-1]] + cells[:-1])  # reference n8K8
    sub = sub[sub["q"].notna()].copy()
    rows = []
    try:
        use_tc = any(v >= 2 for v in pm.replication(sub).values())
        res, info = pm.fit_mixed(sub, "q", False, use_tc)
        names = list(res.model.exog_names)
        L = np.zeros(len(names))
        for c, wk in zip(cells, w):
            if c != cells[-1]:
                L[names.index(f"cell[T.{c}]")] = wk
        tt = res.t_test(L.reshape(1, -1))
        lo, hi = np.asarray(tt.conf_int(alpha=1 - pm.CONF)).ravel()
        rows.append({"cell": "trend", "ref": "n8K2..n8K8", "outcome": "q", "scale": "diff", "method": "mixed2",
                     "estimate": float(np.asarray(tt.effect).ravel()[0]), "lower": float(lo), "upper": float(hi), "se": float(np.asarray(tt.sd).ravel()[0]),
                     "p": float(np.asarray(tt.pvalue).ravel()[0]), "n_pairs": int(sub["task"].nunique()), "n_rows_cell": int(len(sub)), "n_rows_ref": 0,
                     "note": f"slope per doubling of K; optimiser {info['method']}, converged {info['converged']}"})
    except Exception as e:  # noqa: BLE001
        errors.append(f"trend model: {type(e).__name__}: {str(e)[:200]}")
    means = sub.groupby(["task", "cell"], observed=True)["q"].mean().unstack("cell")
    means = means.dropna(subset=cells) if set(cells) <= set(means.columns) else means.iloc[0:0]
    if len(means) >= 2:
        s = means[cells].to_numpy() @ w
        est, se = float(s.mean()), float(s.std(ddof=1) / math.sqrt(len(s)))
        tq = stats.t.ppf(0.5 + pm.CONF / 2, len(s) - 1)
        rows.append({"cell": "trend", "ref": "n8K2..n8K8", "outcome": "q", "scale": "diff", "method": "paired-t", "estimate": est,
                     "lower": est - tq * se, "upper": est + tq * se, "se": se, "p": float(2 * stats.t.sf(abs(est / se), len(s) - 1)) if se > 0 else 0.0,
                     "n_pairs": int(len(s)), "n_rows_cell": int(len(sub)), "n_rows_ref": 0, "note": "per-task slope over the four cell means"})
    return rows


def by_rep(f: pd.DataFrame, a: str, b: str, outcomes: list) -> list:
    """Coding tasks: pairs are the repetitions (one round each); t interval over the repetitions."""
    from scipy import stats

    rows = []
    for col, scale in outcomes:
        pa = f[f["cell"] == a].set_index("rep")[col]
        pb = f[f["cell"] == b].set_index("rep")[col]
        both = pd.concat([pa.rename("a"), pb.rename("b")], axis=1).dropna()
        if scale == "ratio":
            both = both[(both["a"] > 0) & (both["b"] > 0)]
            d = np.log(both["a"]) - np.log(both["b"])
        else:
            d = both["a"] - both["b"]
        n = len(d)
        if n < 2:
            continue
        est, se = float(d.mean()), float(d.std(ddof=1) / math.sqrt(n))
        tq = stats.t.ppf(0.5 + pm.CONF / 2, n - 1)
        lo, hi = est - tq * se, est + tq * se
        p = float(2 * stats.t.sf(abs(est / se), n - 1)) if se > 0 else (1.0 if est == 0 else 0.0)
        row = {"cell": a, "ref": b, "outcome": col, "scale": scale, "method": "paired-rep", "se": se, "p": p, "n_pairs": n,
               "n_rows_cell": int((f["cell"] == a).sum()), "n_rows_ref": int((f["cell"] == b).sum())}
        if scale == "ratio":
            row.update(estimate=math.exp(est), lower=math.exp(lo), upper=math.exp(hi), log_estimate=est, log_lower=lo, log_upper=hi)
        else:
            row.update(estimate=est, lower=lo, upper=hi)
        rows.append(row)
    return rows


def transfer(fd: pd.DataFrame, fa: pd.DataFrame, a: str, b: str, outcomes: list) -> list:
    """(a - b in v4-pro) minus (a - b in flash), per task, t interval over the tasks that have all four cell means."""
    from scipy import stats

    rows = []
    for col, scale in outcomes:
        parts = []
        for f in (fd, fa):
            v = f[f["cell"].isin([a, b])][["task", "cell", col]].dropna()
            if scale == "ratio":
                v = v[v[col] > 0].assign(**{col: lambda z: np.log(z[col])})
            m = v.groupby(["task", "cell"])[col].mean().unstack("cell")
            parts.append((m[a] - m[b]) if a in m.columns and b in m.columns else pd.Series(dtype=float))
        d = (parts[0] - parts[1]).dropna()
        n = len(d)
        if n < 2:
            continue
        est, se = float(d.mean()), float(d.std(ddof=1) / math.sqrt(n))
        tq = stats.t.ppf(0.5 + pm.CONF / 2, n - 1)
        lo, hi = est - tq * se, est + tq * se
        row = {"cell": a, "ref": b, "outcome": col, "scale": scale, "method": "paired-t", "se": se, "n_pairs": n,
               "p": float(2 * stats.t.sf(abs(est / se), n - 1)) if se > 0 else 1.0, "n_rows_cell": 0, "n_rows_ref": 0}
        if scale == "ratio":
            row.update(estimate=math.exp(est), lower=math.exp(lo), upper=math.exp(hi), log_estimate=est, log_lower=lo, log_upper=hi)
        else:
            row.update(estimate=est, lower=lo, upper=hi)
        rows.append(row)
    return rows


# ------------------------------------------------------------------------------------------------ descriptive tables
def levels(df_all: pd.DataFrame, fams: dict, fams_all: dict) -> pd.DataFrame:
    """Per family and cell: the runs there are, how they ended, and the levels over the confirmatory rows (mean of task means)."""
    rows = []
    for name, used in fams.items():
        every = fams_all[name]
        for cell in sorted(every["cell"].unique()):
            e, u = every[every["cell"] == cell], used[used["cell"] == cell]
            k = e["K"].dropna()
            cap = float(k.iloc[0]) if len(k) else np.nan
            r = {"family": name, "cell": cell, "D": e["D"].iloc[0], "K": cap, "runs": len(e), "tasks": int(e["task"].nunique()),
                 "leaks": int(e["leak"].sum()), "leak_rate": float(e["leak"].mean()), "used": len(u), "tasks_used": int(u["task"].nunique())}
            for s in STATUS5:
                r[f"status:{s}"] = int((e["status5"] == s).sum())
            r["complete_rate"] = float(((e["status5"] == "完成") & (e["complete"] != 0)).mean())
            tm = lambda col: float(u.groupby("task")[col].mean().mean()) if u[col].notna().any() else np.nan  # noqa: E731
            for col in ("q", "drb2_recall", "drb2_analysis", "drb2_presentation", "total_yuan", "model_yuan", "search_yuan", "search_requests",
                        "t_answer_s", "all_written_s", "report_chars"):
                r[col] = tm(col)
            r["q_sd_tasks"] = float(u.groupby("task")["q"].mean().std(ddof=1)) if u["q"].notna().sum() > 2 else np.nan
            r["t_answer_median_s"] = float(u["t_answer_s"].median()) if len(u) else np.nan
            r["total_yuan_geo"] = float(np.exp(np.log(u.loc[u["total_yuan"] > 0, "total_yuan"]).mean())) if (u["total_yuan"] > 0).any() else np.nan
            # behaviour over every run of the cell (leaks and failures included: they are behaviour too)
            for col in ("wanted", "opened", "kids_d1", "kids_d2", "kids_d3", "rejected_cap", "rejected_depth", "peak_alive", "spawn_calls"):
                r[f"mean_{col}"] = float(e[col].mean()) if e[col].notna().any() else np.nan
            r["stuck_share"] = float((e["rejected_cap"].fillna(0) > 0).mean())
            r["depth_reject_share"] = float((e["rejected_depth"].fillna(0) > 0).mean())
            r["hit_cap_share"] = float((e["peak_alive"] >= cap).mean()) if pd.notna(cap) and e["peak_alive"].notna().any() else np.nan
            r["no_subagent_share"] = float((e["opened"] == 0).mean())
            r["answer_before_kids_done_share"] = float((e["kids_after_answer"].fillna(0) > 0).mean())
            if r["q"] == r["q"] and r["total_yuan"] == r["total_yuan"] and r["total_yuan"] > 0:
                r["points_per_yuan"] = r["q"] / r["total_yuan"]
            rows.append(r)
    return pd.DataFrame(rows)


def demand(fams_all: dict) -> pd.DataFrame:
    """Share of runs whose peak of live subagents exceeds k. A cell with cap K can show demand only below K; at k = K the
    share is the runs that had a call rejected by the cap; beyond K nothing is known."""
    lines = [("调研题，flash，深度 1、上限 8（默认）", "A", "K8", 1), ("调研题，flash，深度 3、上限 64", "A", "D3K64", 1),
             ("调研题，v4-pro，深度 1、上限 8（默认）", "D", "K8", 1), ("调研题，v4-pro，深度 3、上限 64", "D", "D3K64", 1),
             ("大型编码题，flash，深度 1、上限 16", "F:toolkit-xl", "K16", 1), ("24 道练习，flash，深度 1、上限 8", "F:pw-exercises-free", "K8", 1),
             ("调研题，flash，深度 2、上限 16", "A", "D2K16", 0), ("调研题，flash，指令拆 8 份、上限 8", "B", "n8K8", 0)]
    rows = []
    for label, fam, cell, main_fig in lines:
        f = fams_all.get(fam)
        if f is None:
            continue
        e = f[(f["cell"] == cell) & f["peak_alive"].notna()]
        if e.empty:
            continue
        cap = int(e["K"].iloc[0])
        for k in range(0, min(cap, 64) + 1):
            if k < cap:
                share, kind = float((e["peak_alive"] > k).mean()), "peak"
            else:
                share, kind = float((e["rejected_cap"].fillna(0) > 0).mean()), "rejected at the cap"
            rows.append({"line": label, "family": fam, "cell": cell, "cap": cap, "k": k, "share_above_k": share, "kind": kind, "runs": len(e),
                         "main_figure": main_fig})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ text
def f_diff(r) -> str:
    return f"{r['estimate']:+.1f} [{r['lower']:+.1f}, {r['upper']:+.1f}]"


def f_ratio(r) -> str:
    return f"×{r['estimate']:.2f} [{r['lower']:.2f}, {r['upper']:.2f}]"


def pick(tab: pd.DataFrame, family: str, cell: str, ref: str, outcome: str, method: str = "mixed2", version: str = "confirmatory"):
    hit = tab[(tab["family"] == family) & (tab["cell"] == cell) & (tab["ref"] == ref) & (tab["outcome"] == outcome) & (tab["method"] == method)
              & (tab["version"] == version)]
    return hit.iloc[0] if len(hit) else None


def word(lower: float, upper: float, p_holm: float | None, descriptive: bool) -> str:
    if descriptive:
        return "只作描述（该格泄漏率超过 8%）"
    sig = p_holm is None or p_holm < 0.05
    if lower > 0 and sig:
        return "优效"
    if upper < 0 and sig:
        return "显著更差"
    tail = "" if sig or not (lower > 0 or upper < 0) else "（区间不含 0，但多重校正后 p ≥ 0.05）"
    return f"没测出：排除了 {max(-lower, 0):.1f} 分以上的损失，排除了 {max(upper, 0):.1f} 分以上的提高{tail}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--merge-index", type=Path, default=Path("tasks/phase2-merge-index.json"))
    ap.add_argument("--skip-joint", action="store_true", help="skip the joint models (faster dry runs)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    def log(msg: str = "") -> None:
        print(msg, flush=True)
        lines.append(msg)

    df = load(a.runs, a.merge_index, log)
    sim = df.attrs["simulated"]
    errors: list[str] = []
    all_rows, notes_by = [], {}
    fams_by = {}
    for version in ("confirmatory", "all-runs", "with-leaks", "rep1"):
        fams, notes = build_families(df, version, log)
        fams_by[version], notes_by[version] = fams, notes
        log(f"\n== rows, version {version} ==")
        for name in fams:
            n = notes[name]
            log(f"  {name:<22} in {n['rows_in']:>5}  task dropped {n['task_dropped_rows']:>3}  leaks {n['leak_rows']:>3}  failed {n['failed_rows']:>3}  used {n['rows_used']:>5}  tasks {n['tasks']}")
        if version == "confirmatory":
            for b, d in notes["dropped_tasks"].items():
                if d:
                    log(f"  tasks out of every contrast of {b} (reference cell flagged, no replacement): " + ", ".join(f"{t} ({'/'.join(c)})" for t, c in sorted(d.items())))

        def add(rows: list, family: str, kind: str) -> None:
            for r in rows:
                r.update(family=family, kind=kind, version=version)
            all_rows.extend(rows)

        # confirmatory family, every version
        for cid, family, cell, ref, _test, _exp in CONFIRMATORY:
            if family not in fams or fams[family].empty:
                errors.append(f"{version} {cid}: family {family} has no rows")
                continue
            rows = trend(fams[family], errors) if cell == "trend" else two_cell(fams[family], cell, ref, [("q", "diff")], errors, f"{version} {cid}")
            for r in rows:
                r["contrast_id"] = cid
            add(rows, family, "confirmatory")
        if version == "rep1":  # money and time against the reference, first repetitions only
            for family in ("A", "B", "G"):
                for cell, ref in EXPLORATORY[family]:
                    if cell != "merge4" and ref != "merge4":
                        add(two_cell(fams[family], cell, ref, OUT_REPORT[:4], errors, f"rep1 {family}"), family, "exploratory")
        if version != "confirmatory":
            continue
        # exploratory contrasts: two cells, paired, and the joint model of the family
        for family, pairs in EXPLORATORY.items():
            if family not in fams or fams[family].empty:
                continue
            outcomes = OUT_REPORT
            for cell, ref in pairs:
                add(two_cell(fams[family], cell, ref, outcomes, errors, f"{family}"), family, "exploratory")
            if family in JOINT and not a.skip_joint:
                ref, cells = JOINT[family]
                add(joint(fams[family], ref, cells, [(c, r) for c, r in pairs], outcomes, errors, family, log), family, "exploratory")
        # the confirmatory contrasts' other outcomes (money, time, the three dimensions) are exploratory
        for cid, family, cell, ref, _t, _e in CONFIRMATORY:
            if cell == "trend" or family not in fams:
                continue
            if (cell, ref) not in EXPLORATORY.get(family, []):
                add(two_cell(fams[family], cell, ref, OUT_REPORT[1:], errors, cid), family, "exploratory")
        if "D" in fams and "A@D" in fams:
            for cell, ref in TRANSFER:
                add(transfer(fams["D"], fams["A@D"], cell, ref, OUT_REPORT[:4]), "transfer(D - A@D)", "exploratory")
        for name, f in fams.items():
            if not name.startswith("F:"):
                continue
            cells = sorted(f["cell"].unique())
            for ref in ("K8", "D0"):
                for cell in cells:
                    if cell != ref and ref in cells:
                        add(by_rep(f, cell, ref, OUT_CODE), name, "exploratory")

    tab = pd.DataFrame(all_rows)
    for c in ("contrast_id", "note", "log_estimate", "log_lower", "log_upper", "p_holm", "verdict"):
        if c not in tab.columns:
            tab[c] = np.nan if c.startswith(("log", "p_")) else ""
    tab["contrast_id"], tab["note"] = tab["contrast_id"].fillna(""), tab["note"].fillna("")
    tab["verdict"] = ""
    # leak rates per cell (every run of the cell) and the 8% rule
    lev = levels(df, fams_by["confirmatory"], {k: v for k, v in build_all(df).items()})
    leaky = {(r["family"], r["cell"]) for _, r in lev.iterrows() if r["leak_rate"] > LEAK_MAX}
    # Holm over the nine model p-values, per version
    for version in tab["version"].unique():
        idx = tab.index[(tab["kind"] == "confirmatory") & (tab["method"] == "mixed2") & (tab["version"] == version)]
        if len(idx):
            adj = pm.holm([float(p) for p in tab.loc[idx, "p"]])
            for i, p_adj in zip(idx, adj):
                tab.loc[i, "p_holm"] = p_adj
        if len(idx) != len(CONFIRMATORY):
            errors.append(f"{version}: {len(idx)} of {len(CONFIRMATORY)} confirmatory contrasts were estimated; Holm uses the ones present")
    for i, r in tab[tab["kind"] == "confirmatory"].iterrows():
        if r["outcome"] != "q" or pd.isna(r["lower"]):
            continue
        desc = (r["family"], r["cell"]) in leaky or (r["family"], r["ref"]) in leaky
        if r["method"] == "mixed2":
            tab.loc[i, "verdict"] = word(r["lower"], r["upper"], None if pd.isna(r["p_holm"]) else float(r["p_holm"]), desc)
    cols = ["version", "kind", "contrast_id", "family", "cell", "ref", "outcome", "scale", "method", "estimate", "lower", "upper", "se", "p", "p_holm",
            "n_pairs", "n_rows_cell", "n_rows_ref", "verdict", "log_estimate", "log_lower", "log_upper", "note"]
    tab = tab[cols]
    tab.to_csv(a.out / "contrasts.csv", index=False)
    lev.to_csv(a.out / "levels.csv", index=False)
    dem = demand(build_all(df))
    dem.to_csv(a.out / "demand.csv", index=False)
    used = pd.concat([f.assign(family_used=name)[["id", "batch", "task", "rep", "cell", "family_used", "status5", "leak", "q", "total_yuan",
                                                   "t_answer_s", "search_requests", "D", "K", "opened", "wanted", "peak_alive", "rejected_cap"]]
                      for name, f in fams_by["confirmatory"].items()])
    used.to_csv(a.out / "runs_used.csv", index=False)

    banner = "> **模拟数据，只为检查脚本，下面没有任何一个数是结果。**\n\n" if sim else ""
    # ---- confirmatory.md
    md = [banner + "# 确认性对比（9 个，一个家族，Holm 校正）", "",
          "每个对比用只含该两格的分层模型估计（题的随机截距；某格每题两次时另加题乘格的方差分量），旁边是题内配对差的 t 区间。"
          "判断词要同时满足 95% 区间不含 0 和校正后 p < 0.05。", "",
          "| 编号 | 对比 | 检验 | 事前预期 | 模型估计 [95%] | 配对差 [95%] | 题数 | p | Holm p | 判断 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for cid, family, cell, ref, test, exp in CONFIRMATORY:
        m = tab[(tab["contrast_id"] == cid) & (tab["version"] == "confirmatory") & (tab["method"] == "mixed2")]
        p = tab[(tab["contrast_id"] == cid) & (tab["version"] == "confirmatory") & (tab["method"] == "paired-t")]
        name = f"{cell} 对 {ref}（{family}）" if cell != "trend" else "质量随 K 的线性趋势，每翻一倍（B，指令 8）"
        if m.empty:
            md.append(f"| {cid} | {name} | {test} | {exp} | 没算出 | | | | | |")
            continue
        m = m.iloc[0]
        md.append(f"| {cid} | {name} | {test} | {exp} | {f_diff(m)} | {f_diff(p.iloc[0]) if len(p) else '-'} | {int(m['n_pairs'])} | {m['p']:.3g} | "
                  f"{m['p_holm']:.3g} | {m['verdict']} |")
    md += ["", "## 三套敏感性版本（模型估计 [95%]，Holm p）", "", "| 编号 | 确认性 | 全部运行（失败按实际得分） | 含泄漏标记的运行 | 只用第一次重复 |", "|---|---|---|---|---|"]
    for cid, *_ in CONFIRMATORY:
        cells_ = []
        for version in ("confirmatory", "all-runs", "with-leaks", "rep1"):
            m = tab[(tab["contrast_id"] == cid) & (tab["version"] == version) & (tab["method"] == "mixed2")]
            cells_.append(f"{f_diff(m.iloc[0])}，p {m.iloc[0]['p_holm']:.3g}" if len(m) else "没算出")
        md.append(f"| {cid} | " + " | ".join(cells_) + " |")
    (a.out / "confirmatory.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # ---- table1.md
    t1 = [banner + "# 表 1　模块 A 八格对默认（深度 1、K=8）", "",
          "| 格 | 想开的个数 | 开成的个数 | 评分项通过率之差 [95%] | 总费用倍数 [95%] | 用户等的时间倍数 [95%] | 完成率 | 被上限拒过的运行比例 | 同时活着到过上限的运行比例 | 判断 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    la = lev[lev["family"] == "A"].set_index("cell")
    conf_by = {(c[2], c[3]): c[0] for c in CONFIRMATORY}
    for cell in ["K8"] + TABLE1:
        if cell not in la.index:
            continue
        L_ = la.loc[cell]
        beh = f"{L_['mean_wanted']:.1f} | {L_['mean_opened']:.1f}"
        tailc = f"{100 * L_['complete_rate']:.0f}% | {100 * L_['stuck_share']:.0f}% | " + (f"{100 * L_['hit_cap_share']:.0f}%" if pd.notna(L_["hit_cap_share"]) else "-")
        if cell == "K8":
            t1.append(f"| 默认 K8 | {beh} | 通过率 {L_['q']:.1f} | {L_['total_yuan']:.2f} 元 | {L_['t_answer_s'] / 60:.1f} 分钟 | {tailc} | 参照 |")
            continue
        q_, c_, t_ = (pick(tab, "A", cell, "K8", o) for o in ("q", "total_yuan", "t_answer_s"))
        cid = conf_by.get((cell, "K8")) or ("C1" if cell == "D0" else None)
        if cid == "C1":
            v = tab[(tab["contrast_id"] == "C1") & (tab["version"] == "confirmatory") & (tab["method"] == "mixed2")]
            verdict = (f"默认对它：{v.iloc[0]['verdict']}（C1）" if len(v) else "")
        elif cid:
            v = tab[(tab["contrast_id"] == cid) & (tab["version"] == "confirmatory") & (tab["method"] == "mixed2")]
            verdict = f"{v.iloc[0]['verdict']}（{cid}）" if len(v) else ""
        else:
            verdict = "探索，不配判断词"
        t1.append(f"| {cell} | {beh} | {f_diff(q_) if q_ is not None else '-'} | {f_ratio(c_) if c_ is not None else '-'} | "
                  f"{f_ratio(t_) if t_ is not None else '-'} | {tailc} | {verdict} |")
    (a.out / "table1.md").write_text("\n".join(t1) + "\n", encoding="utf-8")

    # ---- recommend.md: the rule written before the run
    rec = [banner + "# 默认值的推荐规则（事前写定）", "",
           "一个备选设置替代默认，要同时满足：有一项好处（质量区间下限 > 0，或时间倍数的区间上限 < 1，或费用倍数的区间上限 < 0.85）；"
           "质量、费用、时间都没有显著更差（质量区间上限 < 0，费用或时间倍数的区间下限 > 1）；并且该格被上限拒过的运行比例大于 0。"
           "否则保留默认。这里的区间是两格模型的 95% 区间，不做多重校正。", "",
           "| 备选 | 质量差 | 费用倍数 | 时间倍数 | 被上限拒过 | 有好处 | 没有更差 | 上限起作用 | 结论 |", "|---|---|---|---|---|---|---|---|---|"]
    for cell in TABLE1:
        q_, c_, t_ = (pick(tab, "A", cell, "K8", o) for o in ("q", "total_yuan", "t_answer_s"))
        if q_ is None or c_ is None or t_ is None or cell not in la.index:
            continue
        gain = bool(q_["lower"] > 0 or t_["upper"] < 1 or c_["upper"] < 0.85)
        worse = [n for n, bad in (("质量", q_["upper"] < 0), ("费用", c_["lower"] > 1), ("时间", t_["lower"] > 1)) if bad]
        binds = bool(la.loc[cell, "stuck_share"] > 0) if cell != "D0" else True
        ok = gain and not worse and binds
        rec.append(f"| {cell} | {f_diff(q_)} | {f_ratio(c_)} | {f_ratio(t_)} | {100 * la.loc[cell, 'stuck_share']:.0f}% | {'是' if gain else '否'} | "
                   f"{'是' if not worse else '否：' + '、'.join(worse)} | {'是' if binds else '否'} | {'可替代默认' if ok else '保留默认'} |")
    (a.out / "recommend.md").write_text("\n".join(rec) + "\n", encoding="utf-8")

    # ---- summary.md
    sm = [banner + "# 第二阶段分析摘要（脚本生成）", "", f"输入：{a.runs}，sha256 {sha256(a.runs)[:16]}…；第二阶段 {len(df)} 行。", "", "## 行的取舍", "",
          "| 家族 | 版本 | 进入 | 整题去掉的行 | 泄漏 | 失败 | 用上 | 题数 |", "|---|---|---|---|---|---|---|---|"]
    for version, notes in notes_by.items():
        for name in fams_by[version]:
            n = notes[name]
            sm.append(f"| {name} | {version} | {n['rows_in']} | {n['task_dropped_rows']} | {n['leak_rows']} | {n['failed_rows']} | {n['rows_used']} | {n['tasks']} |")
    sm += ["", "## 各格泄漏率（超过 8% 的格只作描述）", "", "| 家族 | 格 | 运行 | 泄漏标记 | 比例 | 只作描述 |", "|---|---|---|---|---|---|"]
    for _, r in lev[lev["leaks"] > 0].iterrows():
        sm.append(f"| {r['family']} | {r['cell']} | {r['runs']} | {r['leaks']} | {100 * r['leak_rate']:.1f}% | {'是' if r['leak_rate'] > LEAK_MAX else ''} |")
    drop = notes_by["confirmatory"]["dropped_tasks"]
    sm += ["", "## 整题退出的题（参照格被标记且没有可顶替的运行）", ""]
    sm += [f"- {b}：" + ("、".join(f"{t}（{'/'.join(c)}）" for t, c in sorted(d.items())) if d else "无") for b, d in drop.items()]
    sm += ["", "## 退出状态（每个家族全部运行）", "", "| 家族 | 格 | 运行 | " + " | ".join(STATUS5) + " |", "|---|---|---|" + "---|" * len(STATUS5)]
    for _, r in lev.iterrows():
        sm.append(f"| {r['family']} | {r['cell']} | {r['runs']} | " + " | ".join(str(int(r[f'status:{s}'])) for s in STATUS5) + " |")
    sm += ["", "## 时间和费用倍数：全部重复对只用第一次重复", "",
           "跑批程序先跑完全部第一次重复，再跑第二次；默认格的第二次比同题其他格晚几个小时。下面把模块 A 各格对默认的倍数用两种取法并排。", "",
           "| 格 | 时间倍数，全部重复 | 时间倍数，只用第一次 | 费用倍数，全部重复 | 费用倍数，只用第一次 |", "|---|---|---|---|---|"]
    for cell in A_CELLS[1:]:
        vals = [pick(tab, "A", cell, "K8", o, version=v) for o in ("t_answer_s", "total_yuan") for v in ("confirmatory", "rep1")]
        if any(v is not None for v in vals):
            sm.append(f"| {cell} | " + " | ".join(f_ratio(v) if v is not None else "-" for v in vals) + " |")
    if errors:
        sm += ["", "## 没算出来的（要处理）", ""] + [f"- {e}" for e in errors]
    (a.out / "summary.md").write_text("\n".join(sm) + "\n", encoding="utf-8")
    log(f"\ncontrasts: {len(tab)} rows; levels: {len(lev)} rows; demand: {len(dem)} rows")
    if errors:
        log(f"\n{len(errors)} PROBLEMS:")
        for e in errors:
            log("  " + e)
    log("\n" + "\n".join(md[2:]))
    (a.out / "run.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_all(df: pd.DataFrame) -> dict:
    """Every run of every family (no exclusion at all), for behaviour, exit statuses and leak rates. D0 of A / B / A@D is repeat 1."""
    main = df[df["batch"] == "p2-main"]
    nat = main[main["hint"] == "none"]
    d0 = nat[(nat["cell"] == "D0") & (nat["rep"] == 1)]
    fam = {"A": pd.concat([nat[(nat["cell"] != "D0") & nat["cell"].isin(A_CELLS)], d0]),
           "B": pd.concat([main[main["cell"].isin(["n3K8", "n8K2", "n8K4", "n8K6", "n8K8"])], nat[nat["cell"] == "K8"], d0])}
    g40 = set(main.loc[main["cell"].isin(["more", "seg"]), "task"])
    pipes = merge_pipeline(df, quiet)
    g_rows = main[main["task"].isin(g40) & main["cell"].isin(["D0", "more", "seg", "K8", "n3K8", "n8K8"])]
    fam["G"] = pd.concat([g_rows, pipes]) if len(pipes) else g_rows
    dd = df[df["batch"] == "p2-d"]
    fam["D"] = dd
    fam["A@D"] = pd.concat([nat[nat["task"].isin(set(dd["task"])) & nat["cell"].isin(["K2", "K8", "D2K8", "D3K64"])], d0[d0["task"].isin(set(dd["task"]))]])
    fam["O"] = df[df["batch"] == "p2-o"]
    ff = df[df["batch"] == "p2-f"]
    for t in sorted(ff["task"].unique()):
        fam[f"F:{t}"] = ff[ff["task"] == t]
    return fam


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
