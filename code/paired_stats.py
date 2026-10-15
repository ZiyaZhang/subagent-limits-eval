#!/usr/bin/env python3
"""Paired comparisons between experiment groups (code-stage-plan-draft.md section 6.6 and appendix C).

Input: per-run rows, one per (task, group, rep), as CSV, a JSON array or JSONL, with metric columns such as
score, model_cost, total_cost and seconds. Several files are merged on (task, group, rep), later files
filling in or overriding columns, so summary.json (summarize_runs.py), scores.csv (judge_code.py) and
index.jsonl (grade_tests.py) can be given together. A row that carries only a run id (id, run or run_id)
gets task, group and rep from --manifest (run_matrix_v2's manifest.jsonl). Duplicate rows within one file
are an error. Aliases, each reported when used: score <- main_score (grade_tests.py); model_cost <-
cost_cny_peak (summarize_runs.py, run_metrics.py); search_aux <- search_aux_requests; total_cost <- model_cost
when the row made no search calls (search_aux 0, or no search_aux column and web_tools / web false: the code
tasks with web tools off), and model_cost + search_aux x --search-cost for rows with search calls (office).
A row with search calls and no --search-cost, or with no column that tells, gets no total_cost (listed).

For each comparison A - B and metric (pairing unit = (task, rep)):
  d         score: A - B in points; ratio metrics (cost, time): ln(A / B), reported as exp(.) = the
            geometric mean ratio. Cells where a group has no run or no value are listed, never dropped
            silently.
  estimate  mean over tasks of the per-task mean d (equal task weights; the plain mean when balanced)
  95% CI    paired t interval with task effects removed: s^2 from d minus its task mean, df = pairs - tasks,
            Var = s^2 / T^2 * sum(1 / n_t)  (balanced: s^2 / pairs)
  p         sign-flip randomization test of the same statistic, two-sided: all 2^n sign vectors when
            n <= 20 (exact, counted by meet-in-the-middle), otherwise 100000 random flips with seed 20261002,
            p = (1 + hits) / (1 + 100000)
  Holm      within each metric, over the primary comparisons that could be evaluated
  up/down/flat  score: |d| < 1 point is flat; ratio metrics: |ratio - 1| < 1% is flat
  bootstrap 95% percentile interval, pairs resampled within each task (10000 resamples, seed 20261002);
            an appended column, not the main result (narrow with 5 pairs per task)
  MDD       minimum detectable difference at 80% power: (t[1-a/2, df] + t[0.8, df]) * SE, with a = 0.05 and
            with a = 0.05 / m (Holm's first step, m comparisons in the family)

Proportions (--binary NAME=COND, e.g. spawned=children>0): per group x/n with Clopper-Pearson 95% intervals
(pooled and per task); per comparison the discordant pairs and the exact McNemar p (= sign flip on +-1).
Extrapolation (--extrapolate LABEL=SOURCE:COND, e.g. "E-D2-K4=E-D2-K8:slot_peak>4"): f = share of SOURCE runs
where COND holds, Clopper-Pearson 95% interval; an unrun configuration's group mean differs by at most
f x (score range); the bound uses the interval's upper end, per task (range from score_min / score_max when
present, else 0-100; w1 can be negative) and pooled (largest range of the tasks; equal to the task-weighted
bound when every task has the same number of runs). Only scores are bounded; for cost and time report f.
Best K (--series G1,G2,..., listed in K order): the group with the highest mean score, then each group's
paired difference to it; the best K is the first listed group whose interval contains 0 (plan H2).
Covariate (--covariate COL, e.g. units_original for w1): Pearson r between score and COL within task, and the
difference adjusted for the paired difference in COL (within-task regression, df = pairs - tasks - 1).
Filters for sensitivity analyses: --tasks t1,t2  --where COND  --exclude COND (repeatable).
COND: col>x, col>=x, col<x, col<=x, col==x, col!=x or col (truthy); alternatives joined with '|'.

Usage:
  paired_stats.py ROWS [ROWS ...] [--manifest manifest.jsonl ...] [--preset code|office|office-d1k]
                  [--compare LABEL=A,B ...] [--secondary LABEL=A,B ...] [--metrics score:diff,seconds:ratio,...]
                  [--binary NAME=COND ...] [--extrapolate LABEL=SOURCE:COND ...] [--series G1,G2,...]
                  [--covariate COL] [--tasks t1,t2] [--where COND] [--exclude COND] [--search-cost CNY]
                  [--json OUT]
  paired_stats.py --self-test      (simulated data with known answers; exit 1 on any failure)
Presets: code = C1 D1-K8-D0, C2 E-D1-K8-D1-K8, C3 E-D2-K8-E-D1-K8, C4 E-D2-K2-E-D2-K8, C7 E-D1-K2-E-D1-K8,
C8 E-D2-K2-E-D1-K2, C5 D2-K8-D1-K8, C6 E-D2-K4-E-D2-K8 (C5, C6 only when run), secondary S1 E-D1-K8-D0;
office = H1 D1-K8-D0, H2a/b/c D2-K1/K2/K4 minus D2-K8, H3 D2-K8-D1-K8; office-d1k = H2d/e/f D1-K1/K2/K4 minus
D1-K8 (the second office batch). --compare replaces the preset's primary list.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import sys
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

import numpy as np
from scipy import stats as sps

SEED = 20261002
EXACT_MAX = 20
N_MC = 100_000
N_BOOT = 10_000
CONF = 0.95
POWER = 0.80
GROUP_ORDER = ["D0"] + [f"{e}D{d}-K{k}" for e in ("", "E-") for d in (1, 2, 3) for k in (1, 2, 4, 8)]
# An interaction contrast compares two differences: group names joined by MINUS (U+2212; group names use the
# ASCII hyphen) form a composite "A−B" whose value per (task, rep) is A - B on the comparison scale (ln for ratio
# metrics), so (label, "A−B", "C−D") estimates (A - B) - (C - D). --compare LABEL=A,B,C,D builds one.
# Names joined by PLUS form the mean of those groups on the comparison scale within the (task, rep) block (the
# geometric mean for ratio metrics): ("FK1", "D1-K1+D2-K1+D3-K1", "D1-K8+D2-K8+D3-K8") is the K1 - K8 main effect
# averaged over the three depths, one value per block.
MINUS = "\u2212"
PLUS = "+"


def avg(*groups: str) -> str:
    return PLUS.join(groups)


def ia(label: str, a: str, b: str, c: str, d: str) -> tuple:
    return (label, a + MINUS + b, c + MINUS + d)


# experiment-plan-dsec-v2.md section 9 (analysis details fixed 10/3, before any main-batch result was read).
# Primary = one factor changed from the factory default D1-K8, plus the delegation tool and one D x K interaction;
# Holm over these within each metric. Everything else is descriptive.
V2_OFFICE_SECONDARY = (
    [(f"K{d}{k}", f"D{d}-K{k}", f"D{d}-K8") for d in (2, 3) for k in (1, 2, 4)]
    + [(f"D{d}{k}", f"D{d}-K{k}", f"D1-K{k}") for k in (1, 2, 4) for d in (2, 3)]
    + [ia("I2", "D2-K8", "D2-K1", "D1-K8", "D1-K1")]
    + [(f"Z{d}{k}", f"D{d}-K{k}", "D0") for d in (1, 2, 3) for k in (1, 2, 4, 8) if (d, k) != (1, 8)])
V2_CODE_SECONDARY = (
    [("N2", "D2-K8", "D1-K8"), ("N3", "D3-K8", "D1-K8"), ("E2", "E-D2-K8", "D2-K8"), ("E3", "E-D3-K8", "D3-K8")]
    + [(f"K{d}{k}", f"E-D{d}-K{k}", f"E-D{d}-K8") for d in (2, 3) for k in (1, 2, 4)]
    + [(f"D{d}{k}", f"E-D{d}-K{k}", f"E-D1-K{k}") for k in (1, 2, 4) for d in (2, 3)]
    + [ia("I2", "E-D2-K8", "E-D2-K1", "E-D1-K8", "E-D1-K1")]
    + [(f"Z{d}{k}", f"E-D{d}-K{k}", "D0") for d in (1, 2, 3) for k in (1, 2, 4, 8)])
PRESETS = {
    "code": {"primary": [("C1", "D1-K8", "D0"), ("C2", "E-D1-K8", "D1-K8"), ("C3", "E-D2-K8", "E-D1-K8"),
                         ("C4", "E-D2-K2", "E-D2-K8"), ("C7", "E-D1-K2", "E-D1-K8"), ("C8", "E-D2-K2", "E-D1-K2"),
                         ("C5", "D2-K8", "D1-K8"), ("C6", "E-D2-K4", "E-D2-K8")],
             "secondary": [("S1", "E-D1-K8", "D0")]},
    "office": {"primary": [("H1", "D1-K8", "D0"), ("H2a", "D2-K1", "D2-K8"), ("H2b", "D2-K2", "D2-K8"),
                           ("H2c", "D2-K4", "D2-K8"), ("H3", "D2-K8", "D1-K8")],
               "secondary": []},
    # The second office batch (adr-034): K at depth 1, against this batch's own D1-K8.
    "office-d1k": {"primary": [("H2d", "D1-K1", "D1-K8"), ("H2e", "D1-K2", "D1-K8"), ("H2f", "D1-K4", "D1-K8")],
                   "secondary": []},
    "v2-office": {"primary": [("H1", "D1-K8", "D0"), ("H2a", "D1-K1", "D1-K8"), ("H2b", "D1-K2", "D1-K8"),
                              ("H2c", "D1-K4", "D1-K8"), ("H3a", "D2-K8", "D1-K8"), ("H3b", "D3-K8", "D1-K8"),
                              ia("H4", "D3-K8", "D3-K1", "D1-K8", "D1-K1")],
                  "secondary": V2_OFFICE_SECONDARY},
    # Post hoc (not in the preregistration): main effects with the other factor averaged out inside each block.
    "v2-office-factorial": {"primary": [
        ("FK1", avg("D1-K1", "D2-K1", "D3-K1"), avg("D1-K8", "D2-K8", "D3-K8")),
        ("FK2", avg("D1-K2", "D2-K2", "D3-K2"), avg("D1-K8", "D2-K8", "D3-K8")),
        ("FK4", avg("D1-K4", "D2-K4", "D3-K4"), avg("D1-K8", "D2-K8", "D3-K8")),
        ("FD2", avg("D2-K1", "D2-K2", "D2-K4", "D2-K8"), avg("D1-K1", "D1-K2", "D1-K4", "D1-K8")),
        ("FD3", avg("D3-K1", "D3-K2", "D3-K4", "D3-K8"), avg("D1-K1", "D1-K2", "D1-K4", "D1-K8"))],
        "secondary": [("FX", avg("D2-K1", "D2-K2", "D2-K4", "D3-K1", "D3-K2", "D3-K4"), avg("D2-K8", "D3-K8")),
                      ("FA", avg(*[f"D{d}-K{k}" for d in (1, 2, 3) for k in (1, 2, 4, 8)]), "D0")]},
    "v2-code-factorial": {"primary": [
        ("FK1", avg("E-D1-K1", "E-D2-K1", "E-D3-K1"), avg("E-D1-K8", "E-D2-K8", "E-D3-K8")),
        ("FK2", avg("E-D1-K2", "E-D2-K2", "E-D3-K2"), avg("E-D1-K8", "E-D2-K8", "E-D3-K8")),
        ("FK4", avg("E-D1-K4", "E-D2-K4", "E-D3-K4"), avg("E-D1-K8", "E-D2-K8", "E-D3-K8")),
        ("FD2", avg("E-D2-K1", "E-D2-K2", "E-D2-K4", "E-D2-K8"), avg("E-D1-K1", "E-D1-K2", "E-D1-K4", "E-D1-K8")),
        ("FD3", avg("E-D3-K1", "E-D3-K2", "E-D3-K4", "E-D3-K8"), avg("E-D1-K1", "E-D1-K2", "E-D1-K4", "E-D1-K8"))],
        "secondary": [("FX", avg("E-D2-K1", "E-D2-K2", "E-D2-K4", "E-D3-K1", "E-D3-K2", "E-D3-K4"), avg("E-D2-K8", "E-D3-K8")),
                      ("FE", avg(*[f"E-D{d}-K8" for d in (1, 2, 3)]), avg("D1-K8", "D2-K8", "D3-K8"))]},
    "v2-code": {"primary": [("C1", "D1-K8", "D0"), ("C2", "E-D1-K8", "D1-K8"), ("C3a", "E-D1-K1", "E-D1-K8"),
                            ("C3b", "E-D1-K2", "E-D1-K8"), ("C3c", "E-D1-K4", "E-D1-K8"), ("C4a", "E-D2-K8", "E-D1-K8"),
                            ("C4b", "E-D3-K8", "E-D1-K8"), ia("C5", "E-D3-K8", "E-D3-K1", "E-D1-K8", "E-D1-K1")],
                "secondary": V2_CODE_SECONDARY},
}


def parts(g: str) -> list:
    """The plain group names a (possibly composite) name is built from."""
    return [a for side in g.split(MINUS) for a in side.split(PLUS)]


def show(g: str) -> str:
    """A group name for the tables; a composite reads (A − B), a mean reads 均值(A, B, C)."""
    sides = [f"均值({', '.join(x.split(PLUS))})" if PLUS in x else x for x in g.split(MINUS)]
    return f"({' − '.join(sides)})" if MINUS in g else sides[0]
DEFAULT_METRICS = "score:diff,model_cost:ratio,total_cost:ratio,seconds:ratio"
METRIC_ZH = {"score": "得分", "model_cost": "模型费（元/次）", "total_cost": "估算总费用（元/次）", "seconds": "时长（秒）"}
FLAT = {"diff": 1.0, "ratio": math.log(1.01)}


class InputError(Exception):
    pass


# ---------------------------------------------------------------- input

def _convert(v):
    if v is None or isinstance(v, (bool, list, dict)):
        return v
    if isinstance(v, (int, float)):
        return None if isinstance(v, float) and math.isnan(v) else v
    s = str(v).strip()
    if s == "" or s.lower() in ("none", "null", "nan", "na", "n/a", "—"):
        return None
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    if re.fullmatch(r"[+-]?\d+", s):
        return int(s)
    try:
        return float(s)
    except ValueError:
        return s


def read_table(path) -> list:
    """Rows of a CSV, JSON array, {"rows": [...]} or JSONL file (lines split on \\n only)."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    head = text.lstrip()[:1]
    if path.suffix.lower() == ".csv" or head not in ("[", "{"):
        rows = list(csv.DictReader(io.StringIO(text)))
    elif head == "[":
        rows = json.loads(text)
    else:
        try:
            data = json.loads(text)
            rows = data["rows"] if isinstance(data, dict) and isinstance(data.get("rows"), list) else [data]
        except json.JSONDecodeError:
            rows = [json.loads(line) for line in text.split("\n") if line.strip()]
    return [{str(k): (_text(v) if str(k) in KEEP_TEXT else _convert(v)) for k, v in r.items()}
            for r in rows if isinstance(r, dict)]


KEEP_TEXT = {"id", "run", "run_id", "task", "group"}  # a random run id such as 1234e56789 must not become a float


def _text(v):
    return None if v is None or (isinstance(v, str) and not v.strip()) else str(v).strip()


def norm_rep(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str):
        m = re.fullmatch(r"r?(\d+)", v.strip())
        return int(m.group(1)) if m else None
    return None


def load_rows(paths: list, manifests: list = (), notes: list | None = None, search_cost: float | None = None) -> list:
    notes = notes if notes is not None else []
    by_id = {}
    for m in manifests:
        for r in read_table(m):
            rid = r.get("id") or r.get("run_id")
            if rid is not None:
                by_id[str(rid)] = r
    merged = {}
    for path in paths:
        seen = set()
        for r in read_table(path):
            task, group, rep = r.get("task"), r.get("group"), norm_rep(r.get("rep"))
            if task is None or group is None or rep is None:
                rid = r.get("id") or r.get("run") or r.get("run_id")
                m = by_id.get(str(rid)) if rid is not None else None
                if m:
                    task = task if task is not None else m.get("task")
                    group = group if group is not None else m.get("group")
                    rep = rep if rep is not None else norm_rep(m.get("rep"))
            if task is None or group is None or rep is None:
                raise InputError(f"{path}: a row has no task/group/rep and its id is not in any manifest: "
                                 f"{dict(list(r.items())[:4])}")
            key = (str(task), str(group), rep)
            if key in seen:
                raise InputError(f"{path}: two rows for task={key[0]} group={key[1]} rep={key[2]}")
            seen.add(key)
            row = merged.setdefault(key, {"task": key[0], "group": key[1], "rep": rep})
            for k, v in r.items():
                if v is not None and k not in ("task", "group", "rep"):
                    row[k] = v
    used, unpriced, unknown = Counter(), 0, 0
    for row in merged.values():
        if row.get("score") is None and isinstance(row.get("main_score"), (int, float)):
            row["score"] = row["main_score"]
            used["score <- main_score"] += 1
        if row.get("model_cost") is None and isinstance(row.get("cost_cny_peak"), (int, float)):
            row["model_cost"] = row["cost_cny_peak"]
            used["model_cost <- cost_cny_peak"] += 1
        if row.get("search_aux") is None and isinstance(row.get("search_aux_requests"), (int, float)):
            row["search_aux"] = row["search_aux_requests"]
        if row.get("total_cost") is None and isinstance(row.get("model_cost"), (int, float)):
            searches = row.get("search_aux")
            if isinstance(searches, (int, float)) and not isinstance(searches, bool):
                if searches == 0:
                    row["total_cost"] = row["model_cost"]
                    used["total_cost <- model_cost (no search calls)"] += 1
                elif search_cost is not None:
                    row["total_cost"] = row["model_cost"] + searches * search_cost
                    used[f"total_cost <- model_cost + search_aux x {search_cost:g}"] += 1
                else:
                    unpriced += 1
            elif row.get("web_tools") is False or row.get("web") is False:
                row["total_cost"] = row["model_cost"]
                used["total_cost <- model_cost (web tools off)"] += 1
            else:
                unknown += 1
    notes += [f"{k}: {v} rows" for k, v in sorted(used.items())]
    if unpriced:
        notes.append(f"total_cost 没算：{unpriced} 行有搜索调用（search_aux > 0），需用 --search-cost 给出每次搜索的费用")
    if unknown:
        notes.append(f"total_cost 没算：{unknown} 行既没有 search_aux（或 search_aux_requests）列，也没有 web_tools / web 列，"
                     "无法判断有没有搜索费")
    # judge_code.py statuses other than ok / zero_deliverable need a person before the numbers are final
    open_ = sorted(f"{r['task']} {r['group']} r{r['rep']}（{r['status']}）" for r in merged.values()
                   if isinstance(r.get("status"), str) and r["status"] not in ("ok", "zero_deliverable"))
    if open_:
        notes.append(f"评分没有结清的运行 {len(open_)} 次（有分数的照常计入，没分数的按缺值列出），需人工处理："
                     f"{'；'.join(open_)}")
    return sorted(merged.values(), key=lambda r: (r["task"], group_key(r["group"]), r["rep"]))


def group_key(g: str):
    return (GROUP_ORDER.index(g), g) if g in GROUP_ORDER else (len(GROUP_ORDER), g)


# ---------------------------------------------------------------- conditions

COND_RE = re.compile(r"^\s*([A-Za-z_][\w.\-]*)\s*(>=|<=|==|!=|>|<)\s*(.+?)\s*$")


def parse_cond(text: str) -> list:
    alts = []
    for part in text.split("|"):
        m = COND_RE.match(part)
        if m:
            alts.append((m.group(1), m.group(2), _convert(m.group(3))))
        elif re.fullmatch(r"\s*[A-Za-z_][\w.\-]*\s*", part):
            alts.append((part.strip(), None, None))
        else:
            raise InputError(f"cannot read condition {part!r}")
    return alts


def _num(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return float(v)
    return None


def eval_cond(alts: list, row: dict):
    """True if any alternative holds; None if none holds and some column was missing; else False."""
    missing = False
    for col, op, val in alts:
        v = row.get(col)
        if v is None:
            missing = True
            continue
        if op is None:
            ok = bool(v)
        else:
            a, b = _num(v), _num(val)
            if a is not None and b is not None:
                ok = {">": a > b, ">=": a >= b, "<": a < b, "<=": a <= b, "==": a == b, "!=": a != b}[op]
            elif op in ("==", "!="):
                ok = (str(v) == str(val)) == (op == "==")
            else:
                raise InputError(f"cannot compare {col}={v!r} {op} {val!r}")
        if ok:
            return True
    return None if missing else False


def filter_rows(rows: list, tasks=None, where=(), exclude=()) -> list:
    out = []
    for r in rows:
        if tasks and r["task"] not in tasks:
            continue
        if any(eval_cond(c, r) is not True for c in where):
            continue
        if any(eval_cond(c, r) is True for c in exclude):
            continue
        out.append(r)
    return out


# ---------------------------------------------------------------- statistics

def clopper_pearson(x: int, n: int, conf: float = CONF) -> tuple:
    if n == 0:
        return (None, None)
    a = 1 - conf
    lo = 0.0 if x == 0 else float(sps.beta.ppf(a / 2, x, n - x + 1))
    hi = 1.0 if x == n else float(sps.beta.ppf(1 - a / 2, x + 1, n - x))
    return lo, hi


def holm(pvals: dict) -> dict:
    items = sorted(((k, p) for k, p in pvals.items() if p is not None), key=lambda kv: kv[1])
    m, running, out = len(items), 0.0, {}
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def _weights(dbt: dict) -> tuple:
    """(flattened d, per-pair weights 1/(T n_t)) for tasks with at least one pair."""
    tasks = [t for t in dbt if dbt[t]]
    vals, w = [], []
    for t in tasks:
        vals += list(dbt[t])
        w += [1.0 / (len(tasks) * len(dbt[t]))] * len(dbt[t])
    return np.array(vals, dtype=float), np.array(w, dtype=float)


def t_interval(dbt: dict, conf: float = CONF) -> dict:
    """Equal-task-weight mean with the within-task (task effects removed) t interval."""
    tasks = [t for t in dbt if dbt[t]]
    n = sum(len(dbt[t]) for t in tasks)
    T = len(tasks)
    if n == 0:
        return {"n": 0, "tasks": 0, "est": None, "se": None, "df": 0, "lo": None, "hi": None}
    means = {t: float(np.mean(dbt[t])) for t in tasks}
    est = float(np.mean(list(means.values())))
    df = n - T
    out = {"n": n, "tasks": T, "est": est, "se": None, "df": df, "lo": None, "hi": None, "sd": None}
    if df < 1:
        return out
    ss = sum((x - means[t]) ** 2 for t in tasks for x in dbt[t])
    s2 = ss / df
    se = math.sqrt(s2 / T ** 2 * sum(1.0 / len(dbt[t]) for t in tasks))
    q = float(sps.t.ppf(0.5 + conf / 2, df))
    out.update({"se": se, "sd": math.sqrt(s2), "lo": est - q * se, "hi": est + q * se})
    return out


def _signed_sums(c: np.ndarray) -> np.ndarray:
    sums = np.zeros(1)
    for v in c:
        sums = np.concatenate([sums + v, sums - v])
    return sums


def sign_flip_p(dbt: dict, exact_max: int = EXACT_MAX, n_mc: int = N_MC, seed: int = SEED) -> tuple:
    """(two-sided p, method, n) for the weighted mean statistic under random sign flips."""
    d, w = _weights(dbt)
    n = len(d)
    if n == 0:
        return None, "none", 0
    c = d * w
    obs = abs(float(c.sum()))
    eps = 1e-9 * (1.0 + float(np.abs(c).sum()))
    if obs <= eps:
        return 1.0, ("exact" if n <= exact_max else "mc"), n
    if n <= exact_max:
        h = n // 2
        s1 = _signed_sums(c[:h])
        s2 = np.sort(_signed_sums(c[h:]))
        hi = len(s2) - np.searchsorted(s2, obs - eps - s1, side="left")
        lo = np.searchsorted(s2, -obs + eps - s1, side="right")
        return float((hi.sum() + lo.sum()) / 2 ** n), "exact", n
    rng = np.random.default_rng(seed)
    hits, done = 0, 0
    while done < n_mc:
        m = min(20_000, n_mc - done)
        signs = rng.integers(0, 2, size=(m, n)).astype(float) * 2 - 1
        hits += int(np.count_nonzero(np.abs((signs * c).sum(axis=1)) >= obs - eps))  # no BLAS: no spurious FP flags
        done += m
    return (1 + hits) / (1 + n_mc), "mc", n


def bootstrap_ci(dbt: dict, n_boot: int = N_BOOT, seed: int = SEED, conf: float = CONF) -> tuple:
    tasks = [t for t in dbt if dbt[t]]
    if not tasks:
        return (None, None)
    rng = np.random.default_rng(seed)
    means = np.zeros((n_boot, len(tasks)))
    for j, t in enumerate(tasks):
        x = np.asarray(dbt[t], dtype=float)
        idx = rng.integers(0, len(x), size=(n_boot, len(x)))
        means[:, j] = x[idx].mean(axis=1)
    est = means.mean(axis=1)
    a = (1 - conf) / 2
    return float(np.quantile(est, a)), float(np.quantile(est, 1 - a))


def mdd(se, df, alpha: float = 0.05, power: float = POWER):
    if se is None or df is None or df < 1:
        return None
    return (float(sps.t.ppf(1 - alpha / 2, df)) + float(sps.t.ppf(power, df))) * se


def up_down_flat(values: list, flat: float) -> tuple:
    up = sum(1 for v in values if v >= flat)
    down = sum(1 for v in values if v <= -flat)
    return up, down, len(values) - up - down


# ---------------------------------------------------------------- pairing

def index_rows(rows: list) -> dict:
    return {(r["task"], r["group"], r["rep"]): r for r in rows}


def value_of(row: dict, metric: str):
    v = row.get(metric)
    if isinstance(v, bool):
        return float(v)
    return float(v) if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)) else None


def cells_of(idx: dict, g: str) -> set:
    """The (task, rep) cells group g has; a composite needs every part."""
    return set.intersection(*({(t, r) for (t, gg, r) in idx if gg == p} for p in parts(g)))


def scaled(idx: dict, t, r, g: str, metric: str, kind: str) -> tuple:
    """(value of g at (t, r) on the comparison scale, problem): the metric (diff) or its ln (ratio); a composite is
    the difference of its parts on that scale."""
    sides = []
    for side in g.split(MINUS):
        vals = []
        for p in side.split(PLUS):
            v = value_of(idx[(t, p, r)], metric)
            if v is None:
                return None, f"{p} 缺 {metric}"
            if kind == "ratio":
                if v <= 0:
                    return None, f"{p} 的 {metric} 不是正数（{v}），不能取对数比"
                v = math.log(v)
            vals.append(v)
        sides.append(sum(vals) / len(vals))
    return (sides[0] - sides[1] if len(sides) == 2 else sides[0]), None


def paired(idx: dict, a: str, b: str, metric: str, kind: str) -> tuple:
    """({task: [d, ...]}, {task: [rep, ...]}, problems) over the (task, rep) cells either group has."""
    cells_a, cells_b = cells_of(idx, a), cells_of(idx, b)
    dbt, reps, problems = defaultdict(list), defaultdict(list), []
    for t, r in sorted(cells_a | cells_b):
        if (t, r) not in cells_a or (t, r) not in cells_b:
            problems.append(f"{t} r{r}: {show(a) if (t, r) not in cells_a else show(b)} 没有这次运行")
            continue
        (va, pa), (vb, pb) = scaled(idx, t, r, a, metric, kind), scaled(idx, t, r, b, metric, kind)
        if va is None or vb is None:
            problems.append(f"{t} r{r}: {'；'.join(x for x in (pa, pb) if x)}")
            continue
        dbt[t].append(va - vb)
        reps[t].append(r)
    return dict(dbt), dict(reps), problems


def compare(idx: dict, label: str, a: str, b: str, metric: str, kind: str, flat: float | None = None) -> dict:
    dbt, reps, problems = paired(idx, a, b, metric, kind)
    res = {"label": label, "a": a, "b": b, "metric": metric, "kind": kind, "problems": problems}
    ti = t_interval(dbt)
    res.update(ti)
    if ti["n"] == 0:
        return res
    p, method, _ = sign_flip_p(dbt)
    flat = FLAT[kind] if flat is None else flat
    allv = [x for t in dbt for x in dbt[t]]
    res.update({"p": p, "p_method": method, "flat_threshold": flat})
    res["up"], res["down"], res["flat"] = up_down_flat(allv, flat)
    res["boot_lo"], res["boot_hi"] = bootstrap_ci(dbt)
    res["mdd"] = mdd(ti["se"], ti["df"])
    res["per_task"] = {t: {"n": len(v), "mean": float(np.mean(v)), "min": float(min(v)), "max": float(max(v)),
                           "reps": reps[t]} for t, v in dbt.items()}
    return res


def group_summary(rows: list, group: str, metric: str, kind: str) -> dict:
    """Group mean over tasks (equal weights) with the within-task t interval; ratio metrics on ln, so est,
    lo and hi come back as the geometric mean and its interval."""
    vbt, missing = defaultdict(list), []
    for r in rows:
        if r["group"] != group:
            continue
        v = value_of(r, metric)
        if v is None or (kind == "ratio" and v <= 0):
            missing.append(f"{r['task']} r{r['rep']}")
            continue
        vbt[r["task"]].append(math.log(v) if kind == "ratio" else v)
    ti = t_interval(dict(vbt))
    if kind == "ratio" and ti["est"] is not None:
        for k in ("est", "lo", "hi"):
            ti[k] = math.exp(ti[k]) if ti[k] is not None else None
    ti["missing"] = missing
    ti["per_task"] = {t: (math.exp(float(np.mean(v))) if kind == "ratio" else float(np.mean(v))) for t, v in vbt.items()}
    return ti


def proportion_table(rows: list, name: str, cond: list, groups: list) -> dict:
    out = {}
    for g in groups:
        per_task, x_all, n_all, missing = defaultdict(lambda: [0, 0]), 0, 0, []
        for r in rows:
            if r["group"] != g:
                continue
            v = eval_cond(cond, r)
            if v is None:
                missing.append(f"{r['task']} r{r['rep']}")
                continue
            per_task[r["task"]][0] += int(v)
            per_task[r["task"]][1] += 1
            x_all += int(v)
            n_all += 1
        lo, hi = clopper_pearson(x_all, n_all)
        out[g] = {"x": x_all, "n": n_all, "p": x_all / n_all if n_all else None, "lo": lo, "hi": hi,
                  "missing": missing,
                  "per_task": {t: {"x": x, "n": n, "lo": clopper_pearson(x, n)[0], "hi": clopper_pearson(x, n)[1]}
                               for t, (x, n) in sorted(per_task.items())}}
    return out


def mcnemar_compare(idx: dict, a: str, b: str, cond: list) -> dict:
    cells = sorted({(t, r) for (t, g, r) in idx if g == a} & {(t, r) for (t, g, r) in idx if g == b})
    b_, c_, both, neither, missing = 0, 0, 0, 0, []
    for t, r in cells:
        va, vb = eval_cond(cond, idx[(t, a, r)]), eval_cond(cond, idx[(t, b, r)])
        if va is None or vb is None:
            missing.append(f"{t} r{r}")
            continue
        if va and not vb:
            b_ += 1
        elif vb and not va:
            c_ += 1
        elif va and vb:
            both += 1
        else:
            neither += 1
    n = b_ + c_ + both + neither
    return {"a_only": b_, "b_only": c_, "both": both, "neither": neither, "pairs": n, "p": mcnemar_exact(b_, c_),
            "diff": (b_ - c_) / n if n else None, "missing": missing}


def extrapolate(rows: list, label: str, source: str, cond: list) -> dict:
    per_task, missing = defaultdict(lambda: [0, 0]), []
    ranges = defaultdict(lambda: [0.0, 100.0])
    seen_range = set()
    for r in rows:
        lo_v, hi_v = value_of(r, "score_min"), value_of(r, "score_max")
        if lo_v is not None and hi_v is not None:
            if r["task"] not in seen_range:
                ranges[r["task"]] = [lo_v, hi_v]
                seen_range.add(r["task"])
            else:
                ranges[r["task"]] = [min(ranges[r["task"]][0], lo_v), max(ranges[r["task"]][1], hi_v)]
        if r["group"] != source:
            continue
        v = eval_cond(cond, r)
        if v is None:
            missing.append(f"{r['task']} r{r['rep']}")
            continue
        per_task[r["task"]][0] += int(v)
        per_task[r["task"]][1] += 1
    tasks = {}
    for t, (x, n) in sorted(per_task.items()):
        lo, hi = clopper_pearson(x, n)
        width = ranges[t][1] - ranges[t][0]
        tasks[t] = {"x": x, "n": n, "f": x / n, "lo": lo, "hi": hi, "range": list(ranges[t]), "bound": hi * width}
    x_all = sum(v["x"] for v in tasks.values())
    n_all = sum(v["n"] for v in tasks.values())
    lo, hi = clopper_pearson(x_all, n_all)
    width = max((ranges[t][1] - ranges[t][0] for t in tasks), default=100.0)
    balanced = len({v["n"] for v in tasks.values()}) <= 1
    return {"label": label, "source": source, "x": x_all, "n": n_all, "f": x_all / n_all if n_all else None,
            "lo": lo, "hi": hi, "range_width": width, "bound": hi * width if hi is not None else None,
            "balanced": balanced, "per_task": tasks, "missing": missing}


def best_k(idx: dict, rows: list, series: list) -> dict:
    present = [g for g in series if any(r["group"] == g for r in rows)]
    means = {g: group_summary(rows, g, "score", "diff")["est"] for g in present}
    means = {g: m for g, m in means.items() if m is not None}
    if not means:
        return {"series": series, "top": None, "best": None, "steps": []}
    top = max(means, key=means.get)
    steps, best = [], None
    for g in present:
        if g == top:
            steps.append({"group": g, "diff": 0.0, "lo": None, "hi": None, "contains0": True})
            best = best or g
            break
        c = compare(idx, f"{g}-{top}", g, top, "score", "diff")
        has0 = c["lo"] is not None and c["lo"] <= 0 <= c["hi"]
        steps.append({"group": g, "diff": c["est"], "lo": c["lo"], "hi": c["hi"], "n": c["n"], "contains0": has0})
        if has0:
            best = g
            break
    return {"series": series, "means": means, "top": top, "best": best, "steps": steps}


def covariate_adjusted(idx: dict, rows: list, a: str, b: str, col: str) -> dict:
    """Score difference A - B adjusted for the paired difference in col (within-task regression)."""
    data = defaultdict(list)
    for (t, g, r), row in idx.items():
        if g != a or (t, b, r) not in idx:
            continue
        ya, yb = value_of(row, "score"), value_of(idx[(t, b, r)], "score")
        xa, xb = value_of(row, col), value_of(idx[(t, b, r)], col)
        if None in (ya, yb, xa, xb):
            continue
        data[t].append((ya - yb, xa - xb))
    tasks = [t for t in data if data[t]]
    n, T = sum(len(data[t]) for t in tasks), len(tasks)
    out = {"a": a, "b": b, "covariate": col, "n": n, "tasks": T}
    dc, xc, dbar, xbar, inv_n = [], [], [], [], 0.0
    for t in tasks:
        d = np.array([p[0] for p in data[t]])
        x = np.array([p[1] for p in data[t]])
        dc += list(d - d.mean())
        xc += list(x - x.mean())
        dbar.append(d.mean())
        xbar.append(x.mean())
        inv_n += 1.0 / len(d)
    dc, xc = np.array(dc), np.array(xc)
    sxx = float((xc ** 2).sum())
    df = n - T - 1
    if n == 0 or sxx == 0 or df < 1:
        out.update({"est": None, "note": "样本不够或协变量没有变化"})
        return out
    beta = float((dc * xc).sum() / sxx)
    resid = dc - beta * xc
    s2 = float((resid ** 2).sum()) / df
    theta = float(np.mean(np.array(dbar) - beta * np.array(xbar)))
    se = math.sqrt(s2 * (inv_n / T ** 2 + float(np.mean(xbar)) ** 2 / sxx))
    q = float(sps.t.ppf(0.5 + CONF / 2, df))
    out.update({"est": theta, "se": se, "df": df, "lo": theta - q * se, "hi": theta + q * se, "slope": beta,
                "unadjusted": float(np.mean(dbar))})
    return out


def correlation(rows: list, col: str) -> dict:
    """Pearson r between score and col: per task, and pooled after centring both within task."""
    by = defaultdict(list)
    for r in rows:
        y, x = value_of(r, "score"), value_of(r, col)
        if y is not None and x is not None:
            by[r["task"]].append((y, x))
    out, yc, xc = {}, [], []
    for t, pts in sorted(by.items()):
        y = np.array([p[0] for p in pts])
        x = np.array([p[1] for p in pts])
        out[t] = {"n": len(pts), "r": float(np.corrcoef(y, x)[0, 1]) if len(pts) > 2 and y.std() and x.std() else None}
        yc += list(y - y.mean())
        xc += list(x - x.mean())
    yc, xc = np.array(yc), np.array(xc)
    pooled = float((yc * xc).sum() / math.sqrt((yc ** 2).sum() * (xc ** 2).sum())) if len(yc) > 2 and yc.any() and xc.any() else None
    return {"per_task": out, "pooled_within_task": pooled}


# ---------------------------------------------------------------- report

def fmt_d(kind: str, v, signed: bool = True) -> str:
    if v is None:
        return "—"
    if kind == "ratio":
        return f"×{math.exp(v):.2f}"
    return f"{v:+.1f}" if signed else f"{v:.1f}"


def fmt_ci(kind: str, lo, hi) -> str:
    if lo is None or hi is None:
        return "—"
    return f"[{fmt_d(kind, lo)}, {fmt_d(kind, hi)}]"


def fmt_p(p, method="", n=0) -> str:
    if p is None:
        return "—"
    s = f"{p:.4f}" if p >= 0.0001 else f"{p:.1e}"
    tag = {"exact": f"精确 2^{n}", "mc": f"随机 {N_MC} 次"}.get(method)
    return f"{s}（{tag}）" if tag else s


def fmt_mdd(kind: str, v) -> str:
    if v is None:
        return "—"
    return f"×{math.exp(v):.2f}" if kind == "ratio" else f"{v:.1f}"


def parse_pairs(items: list, what: str) -> list:
    out = []
    for s in items:
        label, sep, rest = s.partition("=")
        parts = rest.split(",")
        if not sep or len(parts) not in (2, 4) or not label.strip():
            raise InputError(f"{what} {s!r}: use LABEL=A,B (meaning A - B) or LABEL=A,B,C,D ((A - B) - (C - D))")
        parts = [x.strip() for x in parts]
        out.append((label.strip(), parts[0], parts[1]) if len(parts) == 2 else ia(label.strip(), *parts))
    return out


def run(args) -> dict:
    notes = []
    rows = load_rows(args.rows, args.manifest or [], notes, getattr(args, "search_cost", None))
    rows = filter_rows(rows, set(args.tasks.split(",")) if args.tasks else None,
                       [parse_cond(c) for c in args.where or []], [parse_cond(c) for c in args.exclude or []])
    if not rows:
        raise InputError("no rows left after loading and filtering")
    idx = index_rows(rows)
    groups = sorted({r["group"] for r in rows}, key=group_key)
    tasks = sorted({r["task"] for r in rows})
    preset = PRESETS[args.preset]
    primary = parse_pairs(args.compare, "--compare") if args.compare else preset["primary"]
    secondary = parse_pairs(args.secondary, "--secondary") if args.secondary is not None else preset["secondary"]
    skipped = [(l, a, b) for l, a, b in primary + secondary if any(g not in groups for g in parts(a) + parts(b))]
    primary = [c for c in primary if c not in skipped]
    secondary = [c for c in secondary if c not in skipped]
    metrics = []
    for m in (args.metrics or DEFAULT_METRICS).split(","):
        name, _, kind = m.partition(":")
        kind = kind or "diff"
        if kind not in ("diff", "ratio"):
            raise InputError(f"metric {m!r}: kind must be diff or ratio")
        metrics.append((name.strip(), kind))
    out = {"inputs": [str(p) for p in args.rows], "rows": len(rows), "groups": groups, "tasks": tasks,
           "flat": {"score_points": args.flat_score, "ratio_share": args.flat_ratio},
           "notes": notes, "filters": {"tasks": args.tasks, "where": args.where, "exclude": args.exclude},
           "skipped_comparisons": [f"{l}: {show(a)} - {show(b)}" for l, a, b in skipped], "metrics": {}}
    m_family = len(primary)
    for name, kind in metrics:
        flat = args.flat_score if (kind == "diff" and name == "score") else (
            math.log(1 + args.flat_ratio) if kind == "ratio" else FLAT["diff"])
        res = {}
        for label, a, b in primary + secondary:
            c = compare(idx, label, a, b, name, kind, flat)
            c["family"] = "primary" if (label, a, b) in primary else "secondary"
            c["mdd_holm"] = mdd(c.get("se"), c.get("df"), alpha=0.05 / max(1, m_family)) if c["family"] == "primary" else None
            res[label] = c
        adj = holm({l: res[l].get("p") for l, _, _ in primary if res[l].get("p") is not None})
        for l in adj:
            res[l]["p_holm"] = adj[l]
        out["metrics"][name] = {"kind": kind, "comparisons": res,
                                "groups": {g: group_summary(rows, g, name, kind) for g in groups}}
    binaries = list(args.binary or [])
    if not binaries and any(r.get("children") is not None for r in rows):
        binaries = ["spawned=children>0"]
        notes.append("--binary not given: using spawned=children>0")
    out["binary"] = {}
    for spec in binaries:
        bname, sep, cond_s = spec.partition("=")
        if not sep:
            raise InputError(f"--binary {spec!r}: use NAME=COND")
        cond = parse_cond(cond_s)
        out["binary"][bname] = {"cond": cond_s, "groups": proportion_table(rows, bname, cond, groups),
                                "comparisons": {l: {"a": a, "b": b, **mcnemar_compare(idx, a, b, cond)}
                                                for l, a, b in primary + secondary if MINUS not in a + b and PLUS not in a + b}}
    out["extrapolation"] = []
    for spec in args.extrapolate or []:
        label, sep, rest = spec.partition("=")
        source, sep2, cond_s = rest.partition(":")
        if not sep or not sep2:
            raise InputError(f"--extrapolate {spec!r}: use LABEL=SOURCE:COND")
        if source not in groups:
            raise InputError(f"--extrapolate {spec!r}: no rows for group {source}")
        out["extrapolation"].append({**extrapolate(rows, label, source, parse_cond(cond_s)), "cond": cond_s})
    out["best_k"] = best_k(idx, rows, args.series.split(",")) if args.series else None
    if args.covariate:
        out["covariate"] = {"correlation": correlation(rows, args.covariate),
                            "adjusted": {l: covariate_adjusted(idx, rows, a, b, args.covariate)
                                         for l, a, b in primary + secondary if MINUS not in a + b and PLUS not in a + b}}
    return out


def print_report(out: dict) -> None:
    p = print
    p("# 配对比较（paired_stats.py）\n")
    p(f"- 输入：{', '.join(out['inputs'])}；{out['rows']} 次运行；题：{', '.join(out['tasks'])}；组：{', '.join(out['groups'])}")
    p("- 配对单位：（题，轮）。估计 = 各题配对差均值再按题平均；95% 区间 = 扣除题目效应的配对 t 区间（df = 对数 − 题数）；"
      "p = 符号翻转随机化检验（双侧）；Holm 在每个指标内部、对能算的主要对比校正。")
    p(f"- 升/降/平：得分差绝对值 < {out['flat']['score_points']:g} 分算平；费用、时长比值在 ±{100 * out['flat']['ratio_share']:g}% "
      "以内算平。bootstrap 区间为题内重抽样的附列，不作主结果。最小可测差按 80% 功效，前一个 α = 0.05，后一个为 Holm 第一步 α/m。")
    for n in out["notes"]:
        p(f"- 说明：{n}")
    if any(out["filters"].values()):
        p(f"- 筛选：{out['filters']}")
    if out["skipped_comparisons"]:
        p(f"- 没有数据、未计算的对比：{'; '.join(out['skipped_comparisons'])}")
    for name, m in out["metrics"].items():
        kind = m["kind"]
        p(f"\n## {METRIC_ZH.get(name, name)}（{'百分点差' if kind == 'diff' else '几何均值之比'}）\n")
        p("| 对比 | 对数 | 题数 | 估计 | 95% 区间（t，扣题目效应） | df | p（符号翻转） | Holm p | 升/降/平 | bootstrap 95%（附列） | 最小可测差（α / α÷m） |")
        p("|---|---|---|---|---|---|---|---|---|---|---|")
        problems = []
        for label, c in m["comparisons"].items():
            tag = "" if c["family"] == "primary" else "（描述）"
            if not c.get("n"):
                p(f"| {label}{tag} {show(c['a'])} − {show(c['b'])} | 0 | 0 | — | — | — | — | — | — | — | — |")
            else:
                hp = fmt_p(c.get("p_holm")) if c.get("p_holm") is not None else "—"
                p(f"| {label}{tag} {show(c['a'])} − {show(c['b'])} | {c['n']} | {c['tasks']} | {fmt_d(kind, c['est'])} | "
                  f"{fmt_ci(kind, c['lo'], c['hi'])} | {c['df']} | {fmt_p(c['p'], c['p_method'], c['n'])} | {hp} | "
                  f"{c['up']}/{c['down']}/{c['flat']} | {fmt_ci(kind, c['boot_lo'], c['boot_hi'])} | "
                  f"{fmt_mdd(kind, c['mdd'])} / {fmt_mdd(kind, c.get('mdd_holm'))} |")
            problems += [f"{label}: {x}" for x in c["problems"]]
        p("\n单题结果（只作描述）：\n")
        p("| 对比 | 题 | 对数 | 均值 | 最小 | 最大 |")
        p("|---|---|---|---|---|---|")
        for label, c in m["comparisons"].items():
            for t, v in (c.get("per_task") or {}).items():
                p(f"| {label} | {t} | {v['n']} | {fmt_d(kind, v['mean'])} | {fmt_d(kind, v['min'])} | {fmt_d(kind, v['max'])} |")
        p("\n各组（按题等权平均，区间同上）：\n")
        p("| 组 | 次数 | 估计 | 95% 区间 | 缺值 |")
        p("|---|---|---|---|---|")
        nd = 0 if name == "seconds" else 3 if kind == "ratio" else 1
        for g, s in m["groups"].items():
            est = "—" if s["est"] is None else f"{s['est']:.{nd}f}"
            ci = "—" if s["lo"] is None else f"[{s['lo']:.{nd}f}, {s['hi']:.{nd}f}]"
            p(f"| {g} | {s['n']} | {est} | {ci} | {len(s['missing'])} |")
        if problems:
            p("\n没进配对的格子（不是悄悄丢掉）：")
            for x in problems:
                p(f"- {x}")
    for bname, b in out["binary"].items():
        p(f"\n## 比例：{bname}（{b['cond']}）\n")
        p("| 组 | x/n | 比例 | Clopper–Pearson 95% | 缺值 |")
        p("|---|---|---|---|---|")
        for g, s in b["groups"].items():
            ci = "—" if s["lo"] is None else f"[{s['lo']:.2f}, {s['hi']:.2f}]"
            prop = "—" if s["p"] is None else f"{s['p']:.2f}"
            p(f"| {g} | {s['x']}/{s['n']} | {prop} | {ci} | {len(s['missing'])} |")
        p("\n| 对比 | 配对数 | 只有 A | 只有 B | 都有 | 都没有 | 精确 McNemar p |")
        p("|---|---|---|---|---|---|---|")
        for label, c in b["comparisons"].items():
            p(f"| {label} {c['a']} − {c['b']} | {c['pairs']} | {c['a_only']} | {c['b_only']} | {c['both']} | "
              f"{c['neither']} | {fmt_p(c['p'])} |")
    if out["extrapolation"]:
        p("\n## 推算上界（没跑的配置）\n")
        p("| 配置 | 推算用的组 | 条件 | 受影响 x/n | f | Clopper–Pearson 95% | 得分差上界（分） | 单题上界 |")
        p("|---|---|---|---|---|---|---|---|")
        for e in out["extrapolation"]:
            per = "；".join(f"{t} {v['x']}/{v['n']} → {v['bound']:.1f}" for t, v in e["per_task"].items())
            f_ = "—" if e["f"] is None else f"{e['f']:.2f}"
            ci = "—" if e["lo"] is None else f"[{e['lo']:.2f}, {e['hi']:.2f}]"
            bound = "—" if e["bound"] is None else f"{e['bound']:.1f}（{e['hi']:.3f} × {e['range_width']:.1f}）"
            p(f"| {e['label']} | {e['source']} | {e['cond']} | {e['x']}/{e['n']} | {f_} | {ci} | {bound} | {per} |")
            if e["missing"]:
                p(f"\n{e['label']}：{len(e['missing'])} 次运行缺条件里的列，没计入分母：{', '.join(e['missing'])}")
            if not e["balanced"]:
                p(f"\n{e['label']}：各题次数不同，合并上界按最宽的得分范围乘合并比例，只是近似。")
    if out.get("best_k"):
        bk = out["best_k"]
        p(f"\n## 最好的 K（{' → '.join(bk['series'])}）\n")
        p(f"最高组：{bk['top']}；最好的 K：{bk['best']}（按列出顺序，第一个与最高组得分差的区间含 0 的组）\n")
        p("| 组 | 与最高组的差 | 95% 区间 | 含 0 |")
        p("|---|---|---|---|")
        for s in bk["steps"]:
            p(f"| {s['group']} | {fmt_d('diff', s['diff'])} | {fmt_ci('diff', s['lo'], s['hi'])} | {'是' if s['contains0'] else '否'} |")
    if out.get("covariate"):
        cv = out["covariate"]
        col = next(iter(cv["adjusted"].values()))["covariate"] if cv["adjusted"] else ""
        p(f"\n## 协变量：{col}\n")
        p(f"得分与 {col} 的相关（题内）：" + "；".join(
            f"{t} r={v['r']:.2f}（n={v['n']}）" if v["r"] is not None else f"{t} r=—（n={v['n']}）"
            for t, v in cv["correlation"]["per_task"].items())
          + (f"；合并（各题内中心化）r={cv['correlation']['pooled_within_task']:.2f}"
             if cv["correlation"]["pooled_within_task"] is not None else ""))
        p("\n| 对比 | 对数 | 未调整 | 调整后 | 95% 区间 | df | 斜率（分/单位） |")
        p("|---|---|---|---|---|---|---|")
        for label, c in cv["adjusted"].items():
            if c.get("est") is None:
                p(f"| {label} {c['a']} − {c['b']} | {c['n']} | — | — | — | — | {c.get('note', '')} |")
            else:
                p(f"| {label} {c['a']} − {c['b']} | {c['n']} | {c['unadjusted']:+.1f} | {c['est']:+.1f} | "
                  f"[{c['lo']:+.1f}, {c['hi']:+.1f}] | {c['df']} | {c['slope']:.4f} |")


# ---------------------------------------------------------------- self-test

def self_test() -> list:
    """Checks against answers known in closed form or by brute force; returns [(name, ok, detail)]."""
    import itertools
    from scipy import optimize
    res = []

    def check(name, ok, detail=""):
        res.append((name, bool(ok), detail))

    lo, hi = clopper_pearson(0, 15)
    check("CP x=0 upper = 1-0.025^(1/15)", abs(hi - (1 - 0.025 ** (1 / 15))) < 1e-9 and lo == 0, f"{hi:.6f}")
    lo, hi = clopper_pearson(15, 15)
    check("CP x=n lower = 0.025^(1/15)", abs(lo - 0.025 ** (1 / 15)) < 1e-9 and hi == 1, f"{lo:.6f}")
    lo, hi = clopper_pearson(3, 15)
    root_hi = optimize.brentq(lambda q: sps.binom.cdf(3, 15, q) - 0.025, 1e-9, 1 - 1e-9)
    root_lo = optimize.brentq(lambda q: sps.binom.sf(2, 15, q) - 0.025, 1e-9, 1 - 1e-9)
    check("CP 3/15 equals binomial tail inversion", abs(hi - root_hi) < 1e-7 and abs(lo - root_lo) < 1e-7,
          f"[{lo:.4f}, {hi:.4f}]")
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.005})
    check("Holm example", all(abs(adj[k] - v) < 1e-12 for k, v in {"a": 0.03, "b": 0.06, "c": 0.06, "d": 0.02}.items()),
          str(adj))
    check("McNemar b=0 c=6 -> 2/64", abs(mcnemar_exact(0, 6) - 2 / 64) < 1e-12)
    check("McNemar b=c -> 1", mcnemar_exact(3, 3) == 1.0)

    rng = np.random.default_rng(1)
    dbt = {"t1": list(rng.normal(1, 2, 4)), "t2": list(rng.normal(0, 3, 3)), "t3": list(rng.normal(2, 1, 3))}
    d, w = _weights(dbt)
    c = d * w
    obs = abs(c.sum())
    brute = sum(1 for s in itertools.product((-1, 1), repeat=len(c)) if abs(np.dot(s, c)) >= obs - 1e-12) / 2 ** len(c)
    p, method, _ = sign_flip_p(dbt)
    check("sign flip exact = brute force (unbalanced, n=10)", abs(p - brute) < 1e-12 and method == "exact",
          f"{p:.6f} vs {brute:.6f}")
    p, _, n = sign_flip_p({"t1": [1, 2, 3, 4, 5], "t2": [1, 1, 2, 2, 3], "t3": [5, 4, 3, 2, 1]})
    check("sign flip all positive n=15 -> 2/2^15", abs(p - 2 / 2 ** 15) < 1e-15, f"{p}")
    p, method, _ = sign_flip_p({"t": [1.0] * 25})
    check("sign flip MC n=25 all positive -> 1/(1+B)", method == "mc" and abs(p - 1 / (1 + N_MC)) < 1e-15, f"{p}")

    # t interval = OLS with task fixed effects (estimate = mean of task coefficients).
    y = rng.normal(0, 5, 15) + np.repeat([8.0, -3.0, 1.0], 5)
    dbt = {"a": list(y[:5]), "b": list(y[5:10]), "c": list(y[10:])}
    X = np.kron(np.eye(3), np.ones((5, 1)))
    beta, rss, *_ = np.linalg.lstsq(X, y, rcond=None)
    s2 = float(rss[0]) / (15 - 3)
    se_ols = math.sqrt(s2 * np.ones(3) @ np.linalg.inv(X.T @ X) @ np.ones(3) / 9)
    ti = t_interval(dbt)
    check("t interval = fixed-effects OLS", abs(ti["est"] - beta.mean()) < 1e-10 and abs(ti["se"] - se_ols) < 1e-10
          and ti["df"] == 12, f"est {ti['est']:.4f} se {ti['se']:.4f}")

    # Coverage of the 95% interval when task effects differ (true mean difference = mean of task effects).
    effects, sims, cover = np.array([10.0, -2.0, 4.0]), 4000, 0
    for _ in range(sims):
        dd = rng.normal(0, 6, (3, 5)) + effects[:, None]
        ti = t_interval({str(i): list(dd[i]) for i in range(3)})
        cover += ti["lo"] <= effects.mean() <= ti["hi"]
    check("t interval coverage ~95% (4000 sims)", 0.935 <= cover / sims <= 0.965, f"{cover / sims:.3f}")

    # Type I error of the sign-flip test under a symmetric null.
    rej, sims = 0, 1000
    for _ in range(sims):
        dd = rng.normal(0, 6, (3, 5))
        p, _, _ = sign_flip_p({str(i): list(dd[i]) for i in range(3)})
        rej += p <= 0.05
    check("sign flip type I error ~5% (1000 sims)", 0.03 <= rej / sims <= 0.07, f"{rej / sims:.3f}")

    # Ratio metric: A costs exactly twice B in every pair.
    rows = [{"task": t, "group": g, "rep": r, "cost": (2.0 if g == "A" else 1.0) * (1 + r + 3 * k)}
            for k, t in enumerate(("x", "y", "z")) for g in ("A", "B") for r in range(1, 6)]
    cmp_ = compare(index_rows(rows), "A/B", "A", "B", "cost", "ratio")
    check("ratio exactly 2 -> geometric mean ratio 2, zero-width interval",
          abs(math.exp(cmp_["est"]) - 2) < 1e-12 and abs(math.exp(cmp_["lo"]) - 2) < 1e-9
          and abs(math.exp(cmp_["hi"]) - 2) < 1e-9 and cmp_["up"] == 15, f"{math.exp(cmp_['est'])}")

    # Known shift in points, with flat pairs.
    rows = []
    for k, t in enumerate(("x", "y", "z")):
        for r in range(1, 6):
            base = 50 + 10 * k + r
            rows += [{"task": t, "group": "B", "rep": r, "score": base},
                     {"task": t, "group": "A", "rep": r, "score": base + (5 if r <= 3 else 0.5)}]
    cmp_ = compare(index_rows(rows), "A-B", "A", "B", "score", "diff")
    check("up/down/flat with |d|<1 flat", (cmp_["up"], cmp_["down"], cmp_["flat"]) == (9, 0, 6)
          and abs(cmp_["est"] - (3 * 5 + 2 * 0.5) / 5) < 1e-12, f"{cmp_['up']}/{cmp_['down']}/{cmp_['flat']}")

    # Extrapolation bound from 3 of 15 affected runs, 0-100 score.
    rows = [{"task": t, "group": "S", "rep": r, "peak": 3 if (t == "x" and r <= 3) else 1}
            for t in ("x", "y", "z") for r in range(1, 6)]
    e = extrapolate(rows, "K2", "S", parse_cond("peak>2"))
    check("extrapolation bound = CP upper(3/15) x 100", e["x"] == 3 and e["n"] == 15
          and abs(e["bound"] - 100 * root_hi) < 1e-6, f"{e['bound']:.2f}")
    b = bootstrap_ci({"x": [2.0] * 5, "y": [2.0] * 5})
    check("bootstrap of a constant is that constant", b == (2.0, 2.0), str(b))
    return res


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rows", nargs="*", type=Path)
    ap.add_argument("--manifest", action="append", type=Path, help="run_matrix_v2 manifest.jsonl (repeatable)")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="code")
    ap.add_argument("--compare", action="append", help="LABEL=A,B (A - B); replaces the preset's primary list")
    ap.add_argument("--secondary", action="append", help="LABEL=A,B; descriptive, outside Holm")
    ap.add_argument("--metrics", help=f"name:diff|ratio,... (default {DEFAULT_METRICS})")
    ap.add_argument("--binary", action="append", help="NAME=COND, e.g. spawned=children>0")
    ap.add_argument("--extrapolate", action="append", help="LABEL=SOURCE:COND, e.g. E-D2-K4=E-D2-K8:slot_peak>4")
    ap.add_argument("--series", help="groups in K order for the best-K rule, e.g. E-D2-K2,E-D2-K4,E-D2-K8")
    ap.add_argument("--covariate")
    ap.add_argument("--tasks")
    ap.add_argument("--where", action="append")
    ap.add_argument("--exclude", action="append")
    ap.add_argument("--flat-score", type=float, default=FLAT["diff"])
    ap.add_argument("--flat-ratio", type=float, default=0.01)
    ap.add_argument("--search-cost", type=float,
                    help="CNY per search auxiliary request, same price period as model_cost: total_cost <- "
                         "model_cost + search_aux x this for rows with search calls (plan 5: 0.0231 at peak)")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        results = self_test()
        for name, ok, detail in results:
            print(f"{'ok  ' if ok else 'FAIL'} {name} {detail}")
        sys.exit(0 if all(ok for _, ok, _ in results) else 1)
    if not args.rows:
        ap.error("give at least one ROWS file (or --self-test)")
    try:
        out = run(args)
    except InputError as e:
        sys.exit(f"paired_stats: {e}")
    print_report(out)
    if args.json:
        args.json.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
