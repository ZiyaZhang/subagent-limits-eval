#!/usr/bin/env python3
"""Hierarchical models for the phase-2 pre-registered analysis (phase2-experiment-protocol-2026-10-08.md, section 七).

One model per outcome, fitted with statsmodels MixedLM (REML):
    y = grand mean + task random intercept + cell fixed effect [+ batch fixed effect] + residual
with a task x cell random effect (variance component) added only when some cell has >= 2 runs per task,
detected from the data. Quality (q) is modelled in points; cost and time are modelled on the log scale and
reported as ratios (exp of the log contrast). Every contrast is a cell against the reference cell (the default,
D=1 K=8 unless --default says otherwise) with a 95% interval; contrasts between two non-default cells can be
added with --contrasts A/B. Batch is a nuisance: when the selected rows span more than one batch it enters as a
fixed effect (stage-1 data: the default cell has one run per task in each of three batches, the other cells
one run per task in one batch). The same contrasts are also computed as plain paired differences within task
(mean of the cell's runs minus mean of the reference's runs, per task; per (batch, task) block first when the
family spans batches, then averaged within task), with a t interval over tasks, and printed side by side.

Judgement words (quality only, protocol 七): 优效 when the interval's lower bound > 0; 显著更差 when the upper
bound < 0; otherwise 没测出 with the sentence "排除了 L 以上的损失，排除了 U 以上的提高". Cost and time get
ratios and intervals, no word. Holm correction over the confirmatory family given by --family-contrasts
(mixed-model p-values); everything else is exploratory.

Rows used: the family's rows, minus recognized=1 (leaks; --include-recognized keeps them for the sensitivity
version), minus runs whose status is not ok or whose complete flag is 0 (--all-runs keeps them), minus rows
with no value of the outcome (unjudged q, missing cost or time; listed per outcome). Cells not listed in
--cells are dropped and listed. The intervals of the mixed model are the z intervals statsmodels reports; the
paired intervals use t with (tasks - 1) degrees of freedom.

Cell names: D=0 -> D0; D=1 -> K{K}; D>=2 -> D{D}K{K}. Cells can be given as "D,K" (K empty when D=0) or by name.

Usage (dev box, after `source haienv py312-202505` and setting PYTHONPATH to the pylib with statsmodels 0.15):
  python phase2_models.py --runs runs.csv --family drb2 --default 1,8 --cells "0,;1,1;1,4;2,8" \
      --family-contrasts "D0:q;K4:q;D2K8:q" --out results/analysis-phase2-proto
  python phase2_models.py --simulate --n-sim 200 --out results/analysis-phase2-proto/sim
Outputs: contrasts.csv, model_summary.txt (and in --simulate mode simulation.csv, simulation_summary.txt).
"""
from __future__ import annotations

import argparse
import hashlib
import math
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_OUTCOMES = "q:diff,total_yuan:ratio,t_answer_s:ratio"
FIT_METHODS = ["lbfgs", "bfgs", "cg", "powell", "nm"]
CONF = 0.95
VERDICT_SUPERIOR = "优效"
VERDICT_WORSE = "显著更差"
VERDICT_NONE = "没测出"

# Planned phase-2 layout of module A (protocol 四): runs per task of each cell.
SIM_LAYOUT = {"K8": 2, "D2K8": 2, "D0": 1, "K1": 1, "K2": 1, "K3": 1, "K4": 1, "D2K16": 1, "D3K8": 1}
# True quality effects of the simulation (points against the default), chosen near the stage-1 estimates.
SIM_EFFECTS = {"K8": 0.0, "D2K8": 0.6, "D0": -3.5, "K1": -1.0, "K2": -0.5, "K3": 0.0, "K4": 0.0,
               "D2K16": 0.5, "D3K8": 0.0}
SIM_GRAND_MEAN = 57.0


# ----------------------------------------------------------------------------------------------- cells
def cell_label(d, k) -> str:
    d = int(d)
    if d == 0:
        return "D0"
    k = int(k)
    return f"K{k}" if d == 1 else f"D{d}K{k}"


def parse_cell(tok: str) -> str:
    """'0,' / '1,8' / '2,8' or a label such as D0 / K8 / D2K8 -> label."""
    tok = tok.strip()
    if "," in tok:
        d, k = tok.split(",", 1)
        d = int(d.strip())
        if d == 0:
            return "D0"
        if not k.strip():
            raise SystemExit(f"cell {tok!r}: K is needed when D > 0")
        return cell_label(d, int(k.strip()))
    if tok == "D0":
        return tok
    if tok.startswith("K") and tok[1:].isdigit():
        return tok
    if tok.startswith("D") and "K" in tok:
        d, k = tok[1:].split("K", 1)
        if d.isdigit() and k.isdigit():
            return cell_label(int(d), int(k))
    raise SystemExit(f"cannot read cell {tok!r} (use D,K or a name like D0 / K4 / D2K8)")


def parse_pair(tok: str, default: str) -> tuple[str, str]:
    """'A' -> (A, default); 'A/B' -> (A, B)."""
    if "/" in tok:
        a, b = tok.split("/", 1)
        return parse_cell(a), parse_cell(b)
    return parse_cell(tok), default


def parse_family(spec: str | None, default: str) -> list[tuple[str, str, str]]:
    """'D0:q;K4:q;D3K8/D2K8:q' -> [(cell, ref, outcome), ...]."""
    out = []
    for item in (spec or "").split(";"):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise SystemExit(f"family contrast {item!r}: write <cell>[/<ref>]:<outcome>")
        pair, outcome = item.rsplit(":", 1)
        a, b = parse_pair(pair, default)
        out.append((a, b, outcome.strip()))
    return out


def parse_outcomes(spec: str) -> list[tuple[str, str]]:
    out = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        col, _, scale = item.partition(":")
        scale = scale or ("diff" if col == "q" else "ratio")
        if scale not in ("diff", "ratio"):
            raise SystemExit(f"outcome {item!r}: scale must be diff or ratio")
        out.append((col, scale))
    return out


# ----------------------------------------------------------------------------------------------- data
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rows(args, log) -> tuple[pd.DataFrame, list[str]]:
    """Family rows with task, batch, cell and the outcome columns; returns the frame and the cells present."""
    df = pd.read_csv(args.runs)
    fam = df[df["family"] == args.family].copy()
    log(f"input: {args.runs} (sha256 {sha256(Path(args.runs))[:16]}...), {len(df)} rows, family {args.family}: {len(fam)} rows")
    if fam.empty:
        raise SystemExit(f"no rows of family {args.family!r}; families present: {sorted(df['family'].dropna().unique())}")
    if args.batches:
        keep = [b.strip() for b in args.batches.split(",") if b.strip()]
        before = len(fam)
        fam = fam[fam["batch"].isin(keep)]
        log(f"batches restricted to {keep}: {before} -> {len(fam)} rows")
    if "hint" in fam.columns:
        if args.hint is not None:
            before = len(fam)
            fam = fam[fam["hint"].fillna("none") == args.hint]
            log(f"hint == {args.hint!r}: {before} -> {len(fam)} rows")
        else:
            hints = sorted(fam["hint"].fillna("none").unique())
            if len(hints) > 1:
                log(f"WARNING: several task-prompt hints in the selected rows {hints}; cells are identified by D and K "
                    f"only. Use --hint to pick one.")
    fam["cell"] = [cell_label(d, k) for d, k in zip(fam["D"], fam["K"])]
    # exclusions, each counted
    n0 = len(fam)
    if "recognized" in fam.columns and not args.include_recognized:
        leaks = fam["recognized"].fillna(0).astype(int) == 1
        log(f"dropped recognized=1 (leaks): {int(leaks.sum())} rows "
            f"({', '.join(sorted(set(fam.loc[leaks, 'cell'] + '@' + fam.loc[leaks, 'task'].astype(str)))) or '-'})")
        fam = fam[~leaks]
    elif args.include_recognized:
        log("recognized=1 rows KEPT (--include-recognized; sensitivity version with leaks)")
    if not args.all_runs:
        bad = pd.Series(False, index=fam.index)
        if "status" in fam.columns:
            bad |= fam["status"].fillna("") != "ok"
        if "complete" in fam.columns:
            bad |= fam["complete"].fillna(1).astype(float) == 0
        log(f"dropped status != ok or complete == 0: {int(bad.sum())} rows"
            + (f" ({fam.loc[bad, 'status'].value_counts().to_dict()})" if bad.any() else ""))
        fam = fam[~bad]
    else:
        log("all exit statuses KEPT (--all-runs; sensitivity version)")
    present = sorted(fam["cell"].unique(), key=lambda c: (c != args.default_label, c))
    log(f"cells present after exclusions: " + ", ".join(f"{c}={int((fam['cell'] == c).sum())}" for c in present))
    wanted = [args.default_label] + [c for c in args.cell_labels if c != args.default_label]
    missing = [c for c in wanted if c not in present]
    if missing:
        raise SystemExit(f"cells {missing} have no rows; present: {present}")
    extra = [c for c in present if c not in wanted]
    if extra:
        log(f"cells not listed, dropped: " + ", ".join(f"{c}={int((fam['cell'] == c).sum())}" for c in extra))
        fam = fam[fam["cell"].isin(wanted)]
    fam = fam.copy()
    fam["cell"] = pd.Categorical(fam["cell"], categories=wanted)
    fam["task"] = fam["task"].astype(str)
    fam["batch"] = fam["batch"].astype(str)
    log(f"rows used: {len(fam)} of {n0}; tasks: {fam['task'].nunique()}; batches: {sorted(fam['batch'].unique())}")
    return fam, wanted


def replication(df: pd.DataFrame) -> dict[str, float]:
    """Median number of runs per task of each cell (over the whole selection, batches pooled)."""
    counts = df.groupby(["cell", "task"], observed=True).size()
    return {c: float(counts.xs(c, level="cell").median()) for c in df["cell"].cat.categories}


# ----------------------------------------------------------------------------------------------- models
def fit_mixed(df: pd.DataFrame, y: str, use_batch: bool, use_tc: bool) -> tuple[object, dict]:
    """REML fit; tries the optimisers in FIT_METHODS until one converges. Returns (result, info)."""
    import statsmodels.formula.api as smf

    formula = f"{y} ~ cell" + (" + batch" if use_batch else "")
    vc = {"task_x_cell": "0 + C(cell)"} if use_tc else None
    info = {"formula": formula, "vc": vc, "method": None, "converged": False, "warnings": [], "errors": []}
    res = None
    for method in FIT_METHODS:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                md = smf.mixedlm(formula, df, groups=df["task"], re_formula="1", vc_formula=vc)
                r = md.fit(reml=True, method=method, maxiter=2000)
            except Exception as e:  # singular matrix, line-search failure, ...
                info["errors"].append(f"{method}: {type(e).__name__}: {e}")
                continue
        msgs = sorted({str(w.message).strip().splitlines()[0][:160] for w in caught})
        if r.converged:
            res, info["method"], info["converged"], info["warnings"] = r, method, True, msgs
            break
        info["warnings"].extend(f"{method}: {m}" for m in msgs)
        res = r
    if res is None:
        raise RuntimeError("MixedLM could not be fitted: " + "; ".join(info["errors"]))
    # variance components: cov_re (task), vcomp (task x cell), scale (residual); params holds them / scale
    info["task_sd"] = float(np.sqrt(max(float(np.asarray(res.cov_re).ravel()[0]), 0.0)))
    info["tc_sd"] = float(np.sqrt(max(float(res.vcomp[0]), 0.0))) if use_tc else None
    info["resid_sd"] = float(np.sqrt(res.scale))
    info["boundary"] = bool(use_tc and res.vcomp[0] < 1e-6 * res.scale)
    info["llf"] = float(res.llf)
    info["n"] = int(res.nobs)
    info["groups"] = int(len(res.model.group_labels))
    return res, info


def mixed_contrast(res, a: str, b: str, default: str) -> dict:
    """Fixed-effect contrast a - b (b = default or another cell) from the fitted model, on the model scale."""
    names = list(res.model.exog_names)
    L = np.zeros(len(names))
    for cell, sign in ((a, 1.0), (b, -1.0)):
        if cell != default:
            L[names.index(f"cell[T.{cell}]")] += sign
    tt = res.t_test(L.reshape(1, -1))
    lo, hi = np.asarray(tt.conf_int(alpha=1 - CONF)).ravel()
    return {"estimate": float(np.asarray(tt.effect).ravel()[0]), "se": float(np.asarray(tt.sd).ravel()[0]),
            "lower": float(lo), "upper": float(hi), "p": float(np.asarray(tt.pvalue).ravel()[0])}


def paired_contrast(df: pd.DataFrame, y: str, a: str, b: str, pair_cols: list[str]) -> dict:
    """Mean of a's runs minus mean of b's runs inside each pairing block, averaged within task; t interval over tasks."""
    from scipy import stats

    sub = df[df["cell"].isin([a, b])]
    means = sub.groupby(pair_cols + ["cell"], observed=True)[y].mean().unstack("cell")
    if a not in means.columns or b not in means.columns:
        return {"estimate": np.nan, "se": np.nan, "lower": np.nan, "upper": np.nan, "p": np.nan, "n_pairs": 0}
    d = (means[a] - means[b]).dropna()
    d = d.groupby(level="task").mean()
    n = int(len(d))
    if n < 2:
        return {"estimate": float(d.mean()) if n else np.nan, "se": np.nan, "lower": np.nan, "upper": np.nan,
                "p": np.nan, "n_pairs": n}
    est = float(d.mean())
    se = float(d.std(ddof=1) / math.sqrt(n))
    tq = stats.t.ppf(0.5 + CONF / 2, n - 1)
    p = float(2 * stats.t.sf(abs(est / se), n - 1)) if se > 0 else 0.0
    return {"estimate": est, "se": se, "lower": est - tq * se, "upper": est + tq * se, "p": p, "n_pairs": n}


def n_pairs_mixed(df: pd.DataFrame, a: str, b: str) -> int:
    """Tasks that have at least one run of each of the two cells (what the fixed-effect contrast is paired on)."""
    ct = pd.crosstab(df["task"], df["cell"].astype(str))
    if a not in ct.columns or b not in ct.columns:
        return 0
    return int(((ct[a] > 0) & (ct[b] > 0)).sum())


def verdict(lower: float, upper: float) -> str:
    if lower > 0:
        return f"{VERDICT_SUPERIOR}：区间下限 {lower:+.1f} > 0"
    if upper < 0:
        return f"{VERDICT_WORSE}：区间上限 {upper:+.1f} < 0"
    return f"{VERDICT_NONE}：区间含 0；排除了 {-lower:.1f} 分以上的损失，排除了 {upper:.1f} 分以上的提高"


def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * pvals[idx])
        adj[idx] = min(1.0, running)
    return list(adj)


# ----------------------------------------------------------------------------------------------- analysis
def analyse(df: pd.DataFrame, outcomes: list[tuple[str, str]], pairs: list[tuple[str, str]], default: str,
            log, summary: list[str]) -> pd.DataFrame:
    """Fit the models and both kinds of contrasts for every outcome; returns the long contrasts table."""
    batches = sorted(df["batch"].unique())
    use_batch = len(batches) > 1
    rep = replication(df)
    use_tc = any(v >= 2 for v in rep.values())
    pair_cols = ["batch", "task"] if use_batch else ["task"]
    log("replicates per task (median) by cell: " + ", ".join(f"{c} {v:g}" for c, v in rep.items()))
    log(f"task x cell random effect: {'yes' if use_tc else 'no'} "
        f"({'some cell has >= 2 runs per task' if use_tc else 'no cell has >= 2 runs per task'})")
    log(f"batch: {len(batches)} batch(es) {batches} -> "
        + ("batch entered as a fixed effect (nuisance); paired differences formed within (batch, task) blocks, "
           "then averaged within task" if use_batch else "no batch term; paired differences formed within task"))
    summary.append(f"rows {len(df)}, tasks {df['task'].nunique()}, batches {batches}")
    summary.append("replicates per task (median) by cell: " + ", ".join(f"{c} {v:g}" for c, v in rep.items()))
    summary.append(f"fixed effects: cell (reference {default})" + (" + batch (nuisance, family spans batches)" if use_batch else ""))
    summary.append("random effects: task intercept" + (" + task x cell (variance component)" if use_tc else "")
                   + "; residual")
    rows = []
    for col, scale in outcomes:
        y = col if scale == "diff" else f"log_{col}"
        sub = df.copy()
        vals = pd.to_numeric(sub[col], errors="coerce")
        ok = vals.notna() & ((vals > 0) if scale == "ratio" else True)
        dropped = int((~ok).sum())
        sub = sub[ok].copy()
        sub[y] = np.log(vals[ok]) if scale == "ratio" else vals[ok]
        log(f"\n-- outcome {col} ({'points' if scale == 'diff' else 'log scale, reported as ratios'}): "
            f"{len(sub)} rows ({dropped} rows without a usable value dropped), {sub['task'].nunique()} tasks")
        # rank check of the fixed-effect design (cells confounded with batches would make the contrast unestimable)
        X = pd.get_dummies(sub[["cell"] + (["batch"] if use_batch else [])], drop_first=True, dtype=float)
        X.insert(0, "Intercept", 1.0)
        if np.linalg.matrix_rank(X.to_numpy()) < X.shape[1]:
            raise SystemExit(f"outcome {col}: fixed-effect design is rank deficient; cells by batch: "
                             f"{sub.groupby('batch')['cell'].agg(lambda s: sorted(set(s.astype(str)))).to_dict()}")
        t0 = time.time()
        res, info = fit_mixed(sub, y, use_batch, use_tc)
        tc_txt = f"{info['tc_sd']:.2f}" if use_tc else "not fitted"
        log(f"   MixedLM REML {info['formula']} | vc {list(info['vc']) if info['vc'] else '-'} | optimiser {info['method']} "
            f"| converged {info['converged']} | {time.time() - t0:.1f}s")
        log(f"   task SD {info['task_sd']:.2f}  task x cell SD {tc_txt}  residual SD {info['resid_sd']:.2f}"
            + ("  [task x cell variance at the boundary (~0); its SEs equal the model without it]" if info["boundary"] else ""))
        for w in info["warnings"]:
            log(f"   warning: {w}")
        for e in info["errors"]:
            log(f"   optimiser failure: {e}")
        if not info["converged"]:
            log("   WARNING: no optimiser converged; the last fit is reported, read its numbers with care")
        summary.append(f"\n[{col}] {y} = grand mean + task + cell" + (" + batch" if use_batch else "")
                       + (" + task x cell" if use_tc else "") + " + residual; REML; "
                       f"n={info['n']}, tasks={info['groups']}, optimiser={info['method']}, converged={info['converged']}")
        summary.append(f"  task SD = {info['task_sd']:.3f}; task x cell SD = {tc_txt}; residual SD = {info['resid_sd']:.3f}"
                       + ("  (task x cell at the boundary)" if info["boundary"] else "")
                       + f"; REML log-likelihood = {info['llf']:.2f}")
        if use_batch:
            bnames = [n for n in res.model.exog_names if n.startswith("batch[")]
            summary.append("  batch effects (nuisance, model scale): "
                           + ", ".join(f"{n[len('batch[T.'):-1]} {float(res.params[n]):+.3f} (se {float(res.bse[n]):.3f})" for n in bnames))
        for w in info["warnings"]:
            summary.append(f"  warning: {w}")
        for e in info["errors"]:
            summary.append(f"  optimiser failure: {e}")
        summary.append("  " + "\n  ".join(str(res.summary()).splitlines()))
        for a, b in pairs:
            m = mixed_contrast(res, a, b, default)
            p = paired_contrast(sub, y, a, b, pair_cols)
            for method, c in (("mixed", m), ("paired-t", p)):
                row = {"cell": a, "ref": b, "outcome": col, "scale": scale, "method": method,
                       "estimate": c["estimate"], "lower": c["lower"], "upper": c["upper"], "se": c["se"], "p": c["p"],
                       "n_pairs": n_pairs_mixed(sub, a, b) if method == "mixed" else c["n_pairs"],
                       "n_rows_cell": int((sub["cell"] == a).sum()), "n_rows_ref": int((sub["cell"] == b).sum())}
                if scale == "ratio":
                    row["log_estimate"], row["log_lower"], row["log_upper"] = row["estimate"], row["lower"], row["upper"]
                    row["estimate"], row["lower"], row["upper"] = (math.exp(row[k]) if pd.notna(row[k]) else np.nan
                                                                   for k in ("estimate", "lower", "upper"))
                else:
                    row["log_estimate"] = row["log_lower"] = row["log_upper"] = np.nan
                row["verdict"] = (verdict(row["lower"], row["upper"]) if scale == "diff" and col == "q"
                                  and pd.notna(row["lower"]) else "")
                rows.append(row)
    return pd.DataFrame(rows)


def fmt(row: pd.Series) -> str:
    if row["scale"] == "ratio":
        return f"x{row['estimate']:.3f} [{row['lower']:.3f}, {row['upper']:.3f}]"
    return f"{row['estimate']:+.2f} [{row['lower']:+.2f}, {row['upper']:+.2f}]"


def print_tables(tab: pd.DataFrame, log) -> None:
    log("\n== contrasts (cell minus reference; ratios for cost and time), mixed model and paired differences side by side ==")
    log(f"{'cell':<12}{'ref':<8}{'outcome':<12}{'mixed':<30}{'paired-t':<30}{'n':<8}{'est diff':<10}{'SE ratio':<10}verdict (mixed)")
    for (a, b, col), g in tab.groupby(["cell", "ref", "outcome"], sort=False):
        m = g[g["method"] == "mixed"].iloc[0]
        p = g[g["method"] == "paired-t"].iloc[0]
        if m["scale"] == "ratio":
            diff = f"{m['log_estimate'] - p['log_estimate']:+.4f}" if pd.notna(p["log_estimate"]) else "-"
        else:
            diff = f"{m['estimate'] - p['estimate']:+.3f}" if pd.notna(p["estimate"]) else "-"
        ratio = f"{m['se'] / p['se']:.3f}" if pd.notna(p["se"]) and p["se"] > 0 else "-"
        log(f"{a:<12}{b:<8}{col:<12}{fmt(m):<30}{fmt(p):<30}{str(m['n_pairs']) + '/' + str(p['n_pairs']):<8}{diff:<10}{ratio:<10}{m['verdict']}")
    log("   (est diff = mixed minus paired estimate, on the model scale; SE ratio = mixed SE / paired SE; n = tasks paired, mixed/paired)")


def apply_holm(tab: pd.DataFrame, family: list[tuple[str, str, str]], log, summary: list[str]) -> pd.DataFrame:
    tab = tab.copy()
    tab["family"] = "exploratory"
    tab["p_holm"] = np.nan
    if not family:
        log("\n== Holm: no --family-contrasts given; every contrast is exploratory ==")
        return tab
    idx, labels = [], []
    for a, b, col in family:
        hit = tab.index[(tab["cell"] == a) & (tab["ref"] == b) & (tab["outcome"] == col) & (tab["method"] == "mixed")]
        if len(hit) != 1:
            raise SystemExit(f"family contrast {a}/{b}:{col} is not among the computed contrasts")
        idx.append(hit[0])
        labels.append(f"{a} vs {b}, {col}")
    adj = holm([float(tab.loc[i, "p"]) for i in idx])
    for i, a in zip(idx, adj):
        tab.loc[i, "p_holm"] = a
        tab.loc[i, "family"] = "confirmatory"
        # the paired row of the same contrast is marked too (its p stays unadjusted; the family uses the model)
        j = tab.index[(tab["cell"] == tab.loc[i, "cell"]) & (tab["ref"] == tab.loc[i, "ref"])
                      & (tab["outcome"] == tab.loc[i, "outcome"]) & (tab["method"] == "paired-t")]
        tab.loc[j, "family"] = "confirmatory"
    log(f"\n== Holm over the confirmatory family ({len(idx)} contrasts, mixed-model p-values) ==")
    log(f"{'contrast':<28}{'estimate [95%]':<30}{'p':<12}{'p_holm':<12}at 0.05")
    summary.append(f"\nHolm family ({len(idx)} contrasts, mixed-model Wald p-values):")
    for lab, i in zip(labels, idx):
        r = tab.loc[i]
        line = f"{lab:<28}{fmt(r):<30}{r['p']:<12.4g}{r['p_holm']:<12.4g}{'yes' if r['p_holm'] < 0.05 else 'no'}"
        log(line)
        summary.append("  " + line)
    return tab


# ----------------------------------------------------------------------------------------------- simulation
def simulate_dataset(rng: np.random.Generator, n_tasks: int, task_sd: float, tc_sd: float, res_sd: float,
                     layout: dict[str, int], effects: dict[str, float]) -> pd.DataFrame:
    task_eff = rng.normal(0.0, task_sd, n_tasks)
    rows = []
    for i in range(n_tasks):
        for cell, n in layout.items():
            tc = rng.normal(0.0, tc_sd) if tc_sd > 0 else 0.0
            for r in range(n):
                rows.append({"task": f"t{i:03d}", "batch": "sim", "cell": cell, "rep": r + 1,
                             "q": SIM_GRAND_MEAN + task_eff[i] + effects[cell] + tc + rng.normal(0.0, res_sd)})
    df = pd.DataFrame(rows)
    df["cell"] = pd.Categorical(df["cell"], categories=list(layout))
    return df


def run_simulation(args, log) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    default = "K8"
    cells = [c for c in SIM_LAYOUT if c != default]
    pairs = [(c, default) for c in cells]
    rng = np.random.default_rng(args.seed)
    log(f"== simulation: {args.n_sim} datasets, {args.sim_tasks} tasks, layout {SIM_LAYOUT}")
    log(f"   task SD {args.sim_task_sd}, task x cell SD {args.sim_tc_sd}, residual SD {args.sim_res_sd}, "
        f"true effects vs {default}: { {c: SIM_EFFECTS[c] for c in cells} }")
    records, varcomps, failures = [], [], 0
    t0 = time.time()
    quiet: list[str] = []
    for s in range(args.n_sim):
        df = simulate_dataset(rng, args.sim_tasks, args.sim_task_sd, args.sim_tc_sd, args.sim_res_sd, SIM_LAYOUT, SIM_EFFECTS)
        use_tc = any(v >= 2 for v in replication(df).values())
        try:
            res, info = fit_mixed(df, "q", use_batch=False, use_tc=use_tc)
        except RuntimeError as e:
            failures += 1
            log(f"   dataset {s}: fit failed: {e}")
            continue
        varcomps.append({"sim": s, "task_sd": info["task_sd"], "tc_sd": info["tc_sd"], "resid_sd": info["resid_sd"],
                         "converged": info["converged"], "method": info["method"], "boundary": info["boundary"],
                         "warnings": " | ".join(info["warnings"])})
        for a, b in pairs:
            true = SIM_EFFECTS[a] - SIM_EFFECTS[b]
            for method, c in (("mixed", mixed_contrast(res, a, b, default)), ("paired-t", paired_contrast(df, "q", a, b, ["task"]))):
                records.append({"sim": s, "cell": a, "method": method, "true": true, "estimate": c["estimate"], "se": c["se"],
                                "lower": c["lower"], "upper": c["upper"], "covered": int(c["lower"] <= true <= c["upper"]),
                                "converged": info["converged"]})
        if (s + 1) % 20 == 0:
            log(f"   {s + 1}/{args.n_sim} datasets done ({time.time() - t0:.0f}s)")
    rec = pd.DataFrame(records)
    vc = pd.DataFrame(varcomps)
    rec.to_csv(out / "simulation.csv", index=False)
    vc.to_csv(out / "simulation_varcomps.csv", index=False)
    lines = [f"simulation: {args.n_sim} datasets, {args.sim_tasks} tasks, seed {args.seed}; layout {SIM_LAYOUT}",
             f"true: task SD {args.sim_task_sd}, task x cell SD {args.sim_tc_sd}, residual SD {args.sim_res_sd}; "
             f"effects vs {default}: { {c: SIM_EFFECTS[c] for c in cells} }",
             f"fits: {len(vc)} ok, {failures} failed, {int((~vc['converged']).sum())} not converged, "
             f"{int(vc['boundary'].sum())} with task x cell variance at the boundary; "
             f"optimisers used: {vc['method'].value_counts().to_dict()}",
             f"variance components, mean (SD) over datasets: task SD {vc['task_sd'].mean():.2f} ({vc['task_sd'].std():.2f}); "
             f"task x cell SD {vc['tc_sd'].mean():.2f} ({vc['tc_sd'].std():.2f}); residual SD {vc['resid_sd'].mean():.2f} ({vc['resid_sd'].std():.2f})",
             "", f"{'cell':<8}{'method':<10}{'true':>7}{'mean est':>10}{'bias':>8}{'SD est':>8}{'mean SE':>9}{'coverage':>10}{'half-width':>12}"]
    ok_all = True
    for a in cells:
        for method in ("mixed", "paired-t"):
            g = rec[(rec["cell"] == a) & (rec["method"] == method)]
            bias = g["estimate"].mean() - g["true"].iloc[0]
            cov = g["covered"].mean()
            hw = ((g["upper"] - g["lower"]) / 2).mean()
            lines.append(f"{a:<8}{method:<10}{g['true'].iloc[0]:>7.2f}{g['estimate'].mean():>10.3f}{bias:>8.3f}"
                         f"{g['estimate'].std():>8.3f}{g['se'].mean():>9.3f}{cov:>10.3f}{hw:>12.3f}")
            if method == "mixed" and (abs(bias) > 0.5 or not (0.92 <= cov <= 0.98)):
                ok_all = False
    n = len(rec[rec["method"] == "mixed"]["sim"].unique())
    mc = 1.96 * math.sqrt(0.95 * 0.05 / max(n, 1))
    lines.append(f"\n(Monte-Carlo half-width of a coverage estimate at 0.95 with {n} datasets: about {mc:.3f})")
    lines.append("CHECK " + ("PASS" if ok_all else "FAIL") + ": mixed-model |bias| <= 0.5 points and coverage within [0.92, 0.98] for every cell")
    text = "\n".join(lines)
    (out / "simulation_summary.txt").write_text(text + "\n", encoding="utf-8")
    log("\n" + text)
    log(f"\nwritten: {out / 'simulation.csv'}, {out / 'simulation_varcomps.csv'}, {out / 'simulation_summary.txt'}")


# ----------------------------------------------------------------------------------------------- main
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", help="run-level master table (results/master/runs.csv)")
    ap.add_argument("--family", help="task family, e.g. drb2")
    ap.add_argument("--default", default="1,8", help="reference cell as D,K (default 1,8)")
    ap.add_argument("--cells", default="", help="cells to contrast against the reference, ';'-separated D,K or names, or 'all'")
    ap.add_argument("--contrasts", default="", help="extra contrasts between two cells, ';'-separated A/B (e.g. D3K8/D2K8)")
    ap.add_argument("--family-contrasts", default="", help="confirmatory family for Holm: ';'-separated <cell>[/<ref>]:<outcome>")
    ap.add_argument("--outcomes", default=DEFAULT_OUTCOMES, help=f"outcome columns with scale (default {DEFAULT_OUTCOMES})")
    ap.add_argument("--batches", default="", help="restrict to these batches (comma list)")
    ap.add_argument("--hint", default=None, help="keep only rows with this task-prompt hint (e.g. none)")
    ap.add_argument("--include-recognized", action="store_true", help="keep recognized=1 rows (sensitivity version with leaks)")
    ap.add_argument("--all-runs", action="store_true", help="keep runs whose status is not ok / complete == 0 (sensitivity)")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--simulate", action="store_true", help="simulate the planned phase-2 layout instead of reading --runs")
    ap.add_argument("--n-sim", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261008)
    ap.add_argument("--sim-tasks", type=int, default=64)
    ap.add_argument("--sim-task-sd", type=float, default=18.0)
    ap.add_argument("--sim-tc-sd", type=float, default=4.0, help="task x cell SD of the simulation (0 = none)")
    ap.add_argument("--sim-res-sd", type=float, default=5.0, help="replicate (residual) SD of the simulation")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log_lines: list[str] = []

    def log(msg: str = "") -> None:
        print(msg, flush=True)
        log_lines.append(msg)

    try:
        if args.simulate:
            run_simulation(args, log)
            return
        if not args.runs or not args.family:
            ap.error("--runs and --family are required (or --simulate)")
        args.default_label = parse_cell(args.default)
        if args.cells.strip() == "all":
            probe = pd.read_csv(args.runs, usecols=["family", "batch", "D", "K"])
            probe = probe[probe["family"] == args.family]
            if args.batches:
                probe = probe[probe["batch"].isin([b.strip() for b in args.batches.split(",") if b.strip()])]
            args.cell_labels = sorted({cell_label(d, k) for d, k in zip(probe["D"], probe["K"])} - {args.default_label})
        else:
            args.cell_labels = [parse_cell(t) for t in args.cells.split(";") if t.strip()]
        if not args.cell_labels:
            ap.error("--cells is empty")
        outcomes = parse_outcomes(args.outcomes)
        extra_pairs = [parse_pair(t, args.default_label) for t in args.contrasts.split(";") if t.strip()]
        family = parse_family(args.family_contrasts, args.default_label)
        for a, b, col in family:
            if col not in [c for c, _ in outcomes]:
                raise SystemExit(f"family contrast outcome {col!r} is not among --outcomes")
        pairs = [(c, args.default_label) for c in args.cell_labels if c != args.default_label]
        for a, b in extra_pairs + [(a, b) for a, b, _ in family]:
            if (a, b) not in pairs:
                pairs.append((a, b))
        log(f"== phase2_models: family {args.family}, reference {args.default_label}, cells {args.cell_labels}, "
            f"contrasts {[f'{a}/{b}' for a, b in pairs]} ==")
        summary = [f"phase2_models.py {' '.join(sys.argv[1:])}", f"input sha256 {sha256(Path(args.runs))}", ""]
        df, wanted = load_rows(args, log)
        needed = {c for pr in pairs for c in pr}
        missing = needed - set(wanted)
        if missing:
            raise SystemExit(f"contrast cells {sorted(missing)} are not among the selected cells; add them to --cells")
        tab = analyse(df, outcomes, pairs, args.default_label, log, summary)
        print_tables(tab, log)
        tab = apply_holm(tab, family, log, summary)
        cols = ["cell", "ref", "outcome", "scale", "method", "estimate", "lower", "upper", "se", "p", "n_pairs",
                "n_rows_cell", "n_rows_ref", "family", "p_holm", "verdict", "log_estimate", "log_lower", "log_upper"]
        tab[cols].to_csv(out / "contrasts.csv", index=False, float_format="%.6g")
        (out / "model_summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
        log(f"\nwritten: {out / 'contrasts.csv'}, {out / 'model_summary.txt'}")
        log("notes: estimate/lower/upper are points for q and ratios for cost and time (se and p on the log scale for ratios); "
            "mixed intervals are z intervals (statsmodels), paired intervals are t intervals over tasks.")
    finally:
        (out / "run.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
