#!/usr/bin/env python3
"""Numbers added to the report after the review of 2026-10-07: which facts delegation adds, what the main agent loses
when it sums up, the design coverage, how small a difference each comparison could show, how much the estimated search
price matters, and the checks on model speed. Read from the analysis files; nothing typed.

Usage: clean_extra.py            prints every section (for checking)
"""
from __future__ import annotations

import collections
import json
import math
import statistics as st
import sys
from pathlib import Path

sys.dont_write_bytecode = True
EXP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXP / "scripts"))
import clean_data as cd  # noqa: E402

J, R, num = cd.J, cd.R, cd.num
TASKS = ("o1-singapore-trip", "o2-server-cpu-report")
FACT_BATCHES = {"first": ("results/analysis-facts/fact-rows.csv", "results/judge-facts/main-office"),
                "confirm": ("results/analysis-facts-confirm/fact-rows.csv", "results/judge-facts/office-confirm"),
                "floor": ("results/analysis-facts-floor/fact-rows.csv", "results/judge-facts/office-floor")}
# how often a run WITHOUT subagents states the fact correctly: (name, above, up to and including)
STRATA = (("几乎写不到（10% 以下）", -1.0, 0.10), ("偶尔写到（10%–50%）", 0.10, 0.50), ("多数写到（50%–90%）", 0.50, 0.90), ("几乎都写到（90% 以上）", 0.90, 1.0))


# ------------------------------------------------------------------------------------- which facts delegation adds
def _hits() -> tuple:
    """(legacy flag per (task, fact), hits[batch][group][(task, fact)] = list of 0/1 over the judged reports)."""
    legacy = {}
    for short, task in (("o1", TASKS[0]), ("o2", TASKS[1])):
        for f in J(f"rubrics/facts/{short}-facts.json"):
            legacy[(task, f["id"])] = bool(f.get("legacy"))
    hits = {}
    for b, (rows_f, jd) in FACT_BATCHES.items():
        hb = hits.setdefault(b, {})
        for r in R(rows_f):
            j = J(f"{jd}/{r['id']}.f1.json")
            assert j["group"] == r["group"] and j["task"] == r["task"]
            hg = hb.setdefault(r["group"], {})
            for f in j["facts"]:
                hg.setdefault((r["task"], f["id"]), []).append(1 if f["status"] == "对" else 0)
    return legacy, hits


def fact_strata() -> dict:
    """Facts grouped by how often a run without subagents states them, and where the default's gain falls.

    The grouping and the gain use different batches: grouped by the no-subagent runs of two batches, the gain measured
    in the third. (Grouping and measuring in the same runs would show a gain for every fact that just happened to be
    missed there.) Two directions: measured in the confirmation batch (the batch of the report's main contrast) and,
    as a check, measured in the batch of the search-more sentence.
    Each row: items per task, of which fixed beforehand; facts right per report without subagents and with the
    default (tasks weighted equally); the gain and its share of the whole gain.
    union2: what two independent no-subagent reports would cover together if nothing were lost in merging,
    1 - (1 - p)^2 summed over the facts, next to the default's count (same measuring batch)."""
    legacy, hits = _hits()
    rate = lambda b, g, k: st.mean(hits[b][g][k])  # noqa: E731

    def one(strata_from: tuple, meas: str, hi: str = "D1-K8", lo: str = "D0") -> dict:
        rows, tot = [], {}
        base = {k: st.mean([x for sb in strata_from for x in hits[sb]["D0"][k]]) for k in legacy}
        for name, a, z in STRATA:
            per_task = []
            for t in TASKS:
                ks = [k for k in legacy if k[0] == t and a < base[k] <= z]
                per_task.append((len(ks), sum(1 for k in ks if legacy[k]), sum(rate(meas, lo, k) for k in ks), sum(rate(meas, hi, k) for k in ks)))
            n, leg, lo_n, hi_n = (st.mean(v[i] for v in per_task) for i in range(4))
            rows.append({"name": name, "items": n, "legacy": leg, "low": lo_n, "high": hi_n, "gain": hi_n - lo_n,
                         "low_rate": lo_n / n if n else None, "high_rate": hi_n / n if n else None})
        total = sum(r["gain"] for r in rows)
        for r in rows:
            r["share"] = r["gain"] / total
        tot["gain"] = total
        tot["low"], tot["high"] = sum(r["low"] for r in rows), sum(r["high"] for r in rows)
        tot["union2"] = st.mean(sum(1 - (1 - rate(meas, lo, k)) ** 2 for k in legacy if k[0] == t) for t in TASKS)
        tot["union4"] = st.mean(sum(1 - (1 - rate(meas, lo, k)) ** 4 for k in legacy if k[0] == t) for t in TASKS)
        tot["runs"] = {g: {t: len(hits[meas][g][next(k for k in legacy if k[0] == t)]) for t in TASKS} for g in (lo, hi)}
        tot["strata_runs"] = {t: sum(len(hits[sb]["D0"][next(k for k in legacy if k[0] == t)]) for sb in strata_from) for t in TASKS}
        return {"rows": rows, "total": tot, "measured_in": meas, "strata_from": list(strata_from)}

    return {"confirm": one(("floor", "first"), "confirm"), "floor": one(("confirm", "first"), "floor"),
            "depth2": one(("floor", "first"), "confirm", hi="D2-K8", lo="D1-K8"), "items": len(legacy), "legacy": sum(legacy.values())}


def strata_merged() -> dict:
    """The strata of fact_strata() with the merged no-subagent reports next to the default: facts right per report in
    each stratum, measured in the batch whose no-subagent reports were merged (strata from the other two batches)."""
    legacy, hits = _hits()
    mh = {}
    for batch, f, jd in (("confirm", "results/analysis-office-merge/merge-stats.json", "results/judge-facts/office-merge"),
                         ("floor", "results/analysis-office-merge-b/merge-stats.json", "results/judge-facts/office-merge-b")):
        for r in J(f)["rows"]:
            j = J(f"{jd}/{r['run']}.f1.json")
            d = mh.setdefault((batch, r["kind"]), {})
            for x in j["facts"]:
                d.setdefault((r["base_task"], x["id"]), []).append(1 if x["status"] == "对" else 0)
    out = {}
    for strata_from, meas in ((("floor", "first"), "confirm"), (("confirm", "first"), "floor")):
        base = {k: st.mean([x for sb in strata_from for x in hits[sb]["D0"][k]]) for k in legacy}
        rows = []
        for name, a, z in STRATA:
            vals = []
            for t in TASKS:
                ks = [k for k in legacy if k[0] == t and a < base[k] <= z]
                vals.append((len(ks), sum(st.mean(hits[meas]["D0"][k]) for k in ks), sum(st.mean(hits[meas]["D1-K8"][k]) for k in ks),
                             sum(st.mean(mh[(meas, "M2")][k]) for k in ks), sum(st.mean(mh[(meas, "M4")][k]) for k in ks)))
            n, d0, df, m2, m4 = (st.mean(v[i] for v in vals) for i in range(5))
            rows.append({"name": name, "items": n, "none": d0, "default": df, "m2": m2, "m4": m4})
        out[meas] = {"rows": rows, "merges": {kind: {t: len(mh[(meas, kind)][next(k for k in legacy if k[0] == t)]) for t in TASKS} for kind in ("M2", "M4")}}
    return out


def list_origin() -> dict:
    """The gain from subagents on the 63 items fixed before any run and on the 132 items added later, and how much of
    the difference is the mix of easy and hard items. Items in three groups by how often a run without subagents states
    them (up to 50%, 50-90%, above 90%; grouped in two batches, measured in the third, as in fact_strata). "mix": the
    gain the added items would show if, group by group, they gained what the fixed items gain; explained = the part
    of the difference between the two lists that this accounts for."""
    legacy, hits = _hits()
    rate = lambda b, g, k: st.mean(hits[b][g][k])  # noqa: E731
    edges = ((-1.0, 0.5), (0.5, 0.9), (0.9, 1.0))
    out = {}
    for name, strata_from, meas in (("confirm", ("floor", "first"), "confirm"), ("floor", ("confirm", "first"), "floor")):
        base = {k: st.mean([x for sb in strata_from for x in hits[sb]["D0"][k]]) for k in legacy}
        gain = lambda ks: st.mean(rate(meas, "D1-K8", k) - rate(meas, "D0", k) for k in ks)  # noqa: E731
        fixed, added = [k for k in legacy if legacy[k]], [k for k in legacy if not legacy[k]]
        mix, mix_rev, groups = 0.0, 0.0, []
        for a, z in edges:
            fx = [k for k in fixed if a < base[k] <= z]
            ad = [k for k in added if a < base[k] <= z]
            assert len(fx) >= 10 and len(ad) >= 10, (name, a, z, len(fx), len(ad))
            mix += gain(fx) * len(ad) / len(added)
            mix_rev += gain(ad) * len(fx) / len(fixed)  # the other way round: the fixed items' mix with the added items' gains
            groups.append({"fixed_n": len(fx), "added_n": len(ad), "fixed_gain": 100 * gain(fx), "added_gain": 100 * gain(ad)})
        g_fixed, g_added = 100 * gain(fixed), 100 * gain(added)
        by_task = {}
        for t_ in TASKS:  # the same decomposition inside one task (bands may hold few items there)
            fx_t, ad_t = [k for k in fixed if k[0] == t_], [k for k in added if k[0] == t_]
            mix_t = 0.0
            for a, z in edges:
                fb, ab = [k for k in fx_t if a < base[k] <= z], [k for k in ad_t if a < base[k] <= z]
                mix_t += (gain(fb) if fb else gain(ab)) * len(ab) / len(ad_t)
            gf, ga = 100 * gain(fx_t), 100 * gain(ad_t)
            by_task[t_] = {"fixed_gain": gf, "added_gain": ga, "explained": (100 * mix_t - gf) / (ga - gf)}
        out[name] = {"by_task": by_task, "fixed_none": 100 * st.mean(rate(meas, "D0", k) for k in fixed), "added_none": 100 * st.mean(rate(meas, "D0", k) for k in added),
                     "fixed_gain": g_fixed, "added_gain": g_added, "mix": 100 * mix, "explained": (100 * mix - g_fixed) / (g_added - g_fixed),
                     "explained_rev": (g_added - 100 * mix_rev) / (g_added - g_fixed), "groups": groups}
    return out


# --------------------------------------------------------------------- what the main agent loses when it sums up
def relay() -> dict:
    """Facts stated correctly in what the subagents handed back to the main agent, and how many of them are missing
    from the final report (results/analysis-relay/relay-loss.json: 90 runs of five groups, judged with the same lists)."""
    d = J("results/analysis-relay/relay-loss.json")
    label = {"office-confirm/D1-K8": "默认", "office-confirm/D2-K8": "深度 2", "office-floor/D1-K8": "默认（和下一组同批）",
             "office-floor/N-D1-K8": "默认 + 都写进去提示", "office-highk/W-D2-K64": "深度 2、K=64"}
    rows = [{"key": k, "label": label[k], "runs": g["runs"], "handed": g["relay_right_n"], "final": g["final_right_n"], "lost": g["lost_n"],
             "lost_share": g["lost_share"], "own": g["own_n"]} for k, g in d["groups"].items()]
    # the two paired contrasts with the method of every other contrast of the report (cd.contrast: pairs are (task, repeat),
    # the task effect removed, the two tasks weighted equally); the file's own contrasts are plain paired t intervals
    per = [dict(r, rep=str(r["rep"])) for r in d["rows"]]
    con = lambda batch, a, b, col: cd.contrast([r for r in per if r["batch"] == batch], a, b, lambda r: float(r[col]))  # noqa: E731
    return {"rows": rows, "runs": sum(r["runs"] for r in rows), "skipped": len(d["skipped"]),
            "share_range": [min(r["lost_share"] for r in rows), max(r["lost_share"] for r in rows)],
            "lost_range": [min(r["lost"] for r in rows), max(r["lost"] for r in rows)],
            "depth": con("office-confirm", "D2-K8", "D1-K8", "lost_n"), "keep": con("office-floor", "N-D1-K8", "D1-K8", "lost_n"),
            "keep_own": con("office-floor", "N-D1-K8", "D1-K8", "own_n")}


def merge_union() -> dict:
    """Merged reports: facts right in the merged report, next to what the merged reports' own inputs cover together
    (the union of the facts right in the 2 or 4 reports that were merged; merge-stats.json: union_n) and the mean of
    one input. Per kind (M2, M4), the two batches together, tasks weighted equally."""
    out = {}
    for kind in ("M2", "M4"):
        rows = [r for f in ("results/analysis-office-merge/merge-stats.json", "results/analysis-office-merge-b/merge-stats.json") for r in J(f)["rows"] if r["kind"] == kind]
        te = lambda get: st.mean(st.mean(get(r) for r in rows if r["base_task"] == t) for t in TASKS)  # noqa: E731
        out[kind] = {"n": len(rows), "merged": te(lambda r: r["merged_right_n"]), "union": te(lambda r: r["union_n"]),
                     "one": te(lambda r: st.mean(r["input_right_n"])), "retention": te(lambda r: r["retention"]), "new": te(lambda r: r["new_n"])}
    return out


def pages() -> dict:
    """Pages opened in the batch of the search-more sentence, with the pages a run's own scripts saved to disk counted
    in (pages_saved.py; the count used before saw only web_fetch and the URLs written out in shell commands).
    Per group, tasks weighted equally: distinct pages by web_fetch, URLs seen, pages saved, and the total as a lower
    bound, max(URLs seen, web_fetch pages + saved pages); the same total as an upper bound (URLs seen + saved)."""
    sv = {r["id"]: r for r in R("results/analysis-pages-saved/saved.csv")}
    ov = {r["id"]: r for r in R("results/analysis-office-floor/search-overlap.csv")}
    rows = [r for r in R("results/analysis-office-floor/rows-all.csv") if cd.complete(r) and r["id"] in ov and r["id"] in sv]
    A = lambda r: num(ov[r["id"]]["fetches_distinct"])  # noqa: E731
    P = lambda r: num(ov[r["id"]]["pages_distinct"])  # noqa: E731
    S = lambda r: num(sv[r["id"]]["saved_pages"])  # noqa: E731
    out = {}
    for g in ("D0", "E-D0", "D1-K8"):
        x = [r for r in rows if r["group"] == g]
        te = lambda f: st.mean(st.mean(f(r) for r in x if r["task"] == t) for t in TASKS)  # noqa: E731
        out[g] = {"n": len(x), "fetch": te(A), "urls": te(P), "saved": te(S), "low": te(lambda r: max(P(r), A(r) + S(r))), "high": te(lambda r: P(r) + S(r)),
                  "saved50": sum(1 for r in x if S(r) >= 50)}
    out["more_over_default"] = {"fetch": out["E-D0"]["fetch"] / out["D1-K8"]["fetch"], "low": out["E-D0"]["low"] / out["D1-K8"]["low"], "high": out["E-D0"]["high"] / out["D1-K8"]["high"],
                                "widest": [out["E-D0"]["low"] / out["D1-K8"]["high"], out["E-D0"]["high"] / out["D1-K8"]["low"]]}
    if (EXP / DOSE_ROWS).exists():  # the two-dose batch: its rows carry the three counts
        dr = [r for r in R(DOSE_ROWS) if cd.complete(r)]
        out["dose"] = {}
        for g in ("D0", "E-D0", "N-D0", "D1-K8"):
            x = [r for r in dr if r["group"] == g]
            te = lambda f: st.mean(st.mean(f(r) for r in x if r["task"] == t) for t in TASKS)  # noqa: E731
            F, U, V = (lambda r: num(r["fetches_distinct"]) or 0), (lambda r: num(r["pages_distinct"]) or 0), (lambda r: num(r["pages_saved"]) or 0)
            out["dose"][g] = {"n": len(x), "fetch": te(F), "urls": te(U), "saved": te(V), "low": te(lambda r: max(U(r), F(r) + V(r))), "high": te(lambda r: U(r) + V(r)),
                              "saved50": sum(1 for r in x if V(r) >= 50), "saved_median": st.median(V(r) for r in x), "no_search": sum(1 for r in x if (num(r["search_aux"]) or 0) == 0)}
    return out


# ------------------------------------------------------------------------------------------------ design coverage
COVER_ROWS = (("office", "办公报告题（2 道）"), ("ws", "评测集填表题（24 道）"), ("drb2", "评测集报告题（30 道）"), ("code", "读代码题（2 道）"), ("p4", "小编程题"),
              ("wide", "限时 24 题"), ("chain", "16 步串行题"), ("free", "不限时 24 题"), ("xl", "大型编码题"))
COVER_COLS = (("none", "不开"),) + tuple((f"1-{k}", str(k)) for k in (1, 2, 4, 8, 16, 64)) + tuple((f"2-{k}", str(k)) for k in (1, 2, 4, 8, 16, 64)) \
    + tuple((f"3-{k}", str(k)) for k in (1, 2, 4, 8, 64))
EVERY = {"results/analysis-v2/rows.csv": None, "results/analysis-ctl/rows.csv": None, "results/analysis-wait/rows.csv": None, "results/analysis-ctl-dk/rows.csv": None,
         "results/analysis-ctl-free-all/rows.csv": None, "results/analysis-xl-main/rows-all.csv": None, "results/analysis-xl-depth/rows-all.csv": None,
         "results/analysis-office-confirm/rows-all.csv": None, "results/analysis-office-highk/rows-all.csv": None, "results/analysis-office-floor/rows-all.csv": None,
         "results/analysis-office-keep-depth/rows-all.csv": None, "results/analysis-ws-screen/rows-all.csv": "screen", "results/analysis-ws-h1/rows-all.csv": "ws",
         "results/analysis-drb2-h1/rows-all.csv": "drb2", "results/analysis-drb2-kd/rows-all.csv": "drb2"}
TASK_ROW = {"o1-singapore-trip": "office", "o2-server-cpu-report": "office", "c1-subagent-limits": "code", "w1-memory-plugin": "code", "p4-python": "p4",
            "pw-exercises": "wide", "pw-exercises-120": "wide120", "n1-chain16": "chain", "pw-exercises-free": "free", "toolkit-xl": "xl"}


def setting(group: str) -> tuple:
    """(column key, prompt variant) of a group name: W- (the process waits) is dropped; E- / N- mark an added sentence."""
    g = group[2:] if group.startswith("W-") else group
    variant = "plain"
    if g.startswith("T-"):  # the limit written into the tool description (the told-limit batch)
        g, variant = g[2:], "T"
    if g.startswith("E-"):
        g, variant = g[2:], "E"
    if g.startswith("N-"):
        g, variant = g[2:], "N"
    if g == "D0":
        return "none", variant
    d, k = g.split("-")
    return f"{d[1:]}-{k[1:]}", variant


DOSE_ROWS = "results/analysis-office-dose/rows-all.csv"
PUBK_READY = lambda: (EXP / "results/analysis-ws-k4/stats.json").exists() and (EXP / "results/analysis-drb2-k4/stats.json").exists()  # noqa: E731
DOSE_STATS = "results/analysis-facts-dose/stats.json"
TOLD_ROWS = "results/analysis-office-told/rows-all.csv"
TOLD_STATS = "results/analysis-facts-told/stats.json"
TOLD_READY = lambda: (EXP / TOLD_STATS).exists()  # noqa: E731  (the told-limit batch, once its analysis exists)


def every_rows() -> dict:
    """The rows files behind the report's run count; the two-dose batch joins once it has been analysed."""
    out = dict(EVERY)
    if (EXP / DOSE_STATS).exists():
        out[DOSE_ROWS] = None
    if PUBK_READY():
        out["results/analysis-ws-k4/rows-all.csv"] = "ws"
        out["results/analysis-drb2-k4/rows-all.csv"] = "drb2"
    if TOLD_READY():
        out[TOLD_ROWS] = None
    return out


def coverage() -> dict:
    """Runs per task and setting over every batch of the report (prompt variants together), and what is outside the grid."""
    cells, variants, extra, total = collections.Counter(), collections.defaultdict(set), collections.Counter(), 0
    for f, fixed in every_rows().items():
        for r in R(f):
            total += 1
            row = fixed or TASK_ROW[r["task"]]
            if row in ("screen", "wide120"):
                extra[row] += 1
                continue
            col, var = setting(r["group"])
            cells[(row, col)] += 1
            variants[(row, col)].add(var)
    assert all(c in dict(COVER_COLS) for (_, c) in cells), sorted({c for (_, c) in cells} - set(dict(COVER_COLS)))
    return {"cells": {f"{r}|{c}": n for (r, c), n in cells.items()}, "variants": {f"{r}|{c}": sorted(v) for (r, c), v in variants.items()},
            "extra": dict(extra), "total": total, "in_grid": sum(cells.values())}


# ------------------------------------------------------------------------------------------- the search price
def price() -> dict:
    """The probe behind the search price (40 requests) and how far the cost ratios move when the price moves by its
    95% interval. total = model fee + price x search requests, so a ratio moves only as far as the two groups'
    search share differs."""
    probe = J("results/search-cost-probe-main-office.json")
    c = [x["cost_cny_peak"] for x in probe["sample"]]
    se = st.stdev(c) / math.sqrt(len(c))
    from scipy import stats as sps
    half = sps.t.ppf(0.975, len(c) - 1) * se
    rel = half / st.mean(c)
    p0 = probe["per_request_cny_peak"]
    assert abs(st.mean(c) - p0) < 1e-9
    spec = {"none_default": ("results/analysis-office-confirm/rows-all.csv", "D0", "D1-K8"), "k1_default": ("results/analysis-office-confirm/rows-all.csv", "D1-K1", "D1-K8"),
            "d2_default": ("results/analysis-office-confirm/rows-all.csv", "D2-K8", "D1-K8"), "old_default": ("results/analysis-office-highk/rows-all.csv", "W-D3-K64", "W-D1-K8"),
            "more_default": ("results/analysis-office-floor/rows-all.csv", "E-D0", "D1-K8")}
    if (EXP / DOSE_ROWS).exists():  # the two search-more sentences of the two-dose batch
        spec.update({"dose150_default": (DOSE_ROWS, "E-D0", "D1-K8"), "dose250_default": (DOSE_ROWS, "N-D0", "D1-K8")})
    out = {"n": len(c), "mean": p0, "sd": st.stdev(c), "half": half, "rel": rel, "median": st.median(c), "min": min(c), "max": max(c), "ratios": {}, "search_share": {}}
    for key, (f, a, b) in spec.items():
        rows = [r for r in R(f) if cd.complete(r)]
        tot = lambda r, p: num(r["model_cost_peak"]) + p * num(r["search_aux"])  # noqa: E731
        for g in (a, b):  # the search fee's share of the group's cost (mean of the fee over mean of the cost, tasks weighted equally)
            te = lambda get, g=g: st.mean(st.mean(get(r) for r in rows if r["group"] == g and r["task"] == t_) for t_ in TASKS)  # noqa: E731
            out["search_share"][f"{key}:{g}"] = te(lambda r: p0 * num(r["search_aux"])) / te(lambda r: tot(r, p0))
        assert all(abs(tot(r, p0) - num(r["total_cost_peak"])) < 0.02 for r in rows if r["group"] in (a, b)), key
        out["ratios"][key] = {tag: cd.contrast(rows, a, b, (lambda r, p=p: tot(r, p)), "ratio")["est"] for tag, p in (("mid", p0), ("low", p0 * (1 - rel)), ("high", p0 * (1 + rel)))}
    drows = [r for r in R("results/analysis-office-confirm/rows-all.csv") if cd.complete(r) and r["group"] == "D1-K8"]
    sfee = st.mean(st.mean(p0 * num(r["search_aux"]) for r in drows if r["task"] == t) for t in TASKS)
    out["default_search_fee"], out["default_fee_half"] = sfee, sfee * rel
    out["max_shift"] = max(abs(v[k] / v["mid"] - 1) for v in out["ratios"].values() for k in ("low", "high"))
    out["shift"] = {key: max(abs(v[k] / v["mid"] - 1) for k in ("low", "high")) for key, v in out["ratios"].items()}
    out["share_more"] = out["search_share"]["more_default:E-D0"]
    more_keys = ("more_default:E-D0", "dose150_default:E-D0", "dose250_default:N-D0")  # the groups told to search more
    out["share_more_all"] = sorted(v for k, v in out["search_share"].items() if k in more_keys)
    out["shift_more"] = sorted(v for k, v in out["shift"].items() if k in ("more_default", "dose150_default", "dose250_default"))
    out["shift_rest"] = max(v for k, v in out["shift"].items() if k not in ("more_default", "dose150_default", "dose250_default"))
    others = [v for k, v in out["search_share"].items() if k not in more_keys]
    out["share_others"] = [min(others), max(others)]
    return out


# ----------------------------------------------------------------------------------------------- model speed
def speed() -> dict:
    """Was any group served by a slower model endpoint? Output tokens per second of each model request stream
    (request_timing.py), by group, for the two batches of the 24 exercises (the batches whose time result was in
    doubt), and the time contrasts of the office task recomputed with every request at one fixed speed."""
    out = {"batches": {}}
    for name, f in (("b1", "results/analysis-ctl-free-timing/request-timing-ctl-free.json"), ("b2", "results/analysis-ctl-free-timing/request-timing-ctl-free-b2.json")):
        by = collections.defaultdict(list)
        for r in J(f):
            if r.get("tps_med"):
                by[r["group"]].append(r["tps_med"])
        m = {g: st.mean(v) for g, v in by.items()}
        sub = [v for g, v in m.items() if g != "D0"]
        out["batches"][name] = {"groups": m, "none": m["D0"], "sub_min": min(sub), "sub_max": max(sub), "runs": sum(len(v) for v in by.values())}
    allv = [v for b in out["batches"].values() for v in b["groups"].values()]
    out["min"], out["max"] = min(allv), max(allv)
    out["sub_min"], out["sub_max"] = min(b["sub_min"] for b in out["batches"].values()), max(b["sub_max"] for b in out["batches"].values())
    out["none_min"], out["none_max"] = min(b["none"] for b in out["batches"].values()), max(b["none"] for b in out["batches"].values())
    # office: the same time contrasts on the raw duration and on the duration recomputed at a fixed model speed
    rows = [r for r in R("results/analysis-office-confirm/rows-all.csv") if cd.complete(r)]
    pairs = {}
    for key, a in (("none", "D0"), ("k1", "D1-K1"), ("k4", "D1-K4"), ("d2", "D2-K8")):
        raw = cd.contrast(rows, a, "D1-K8", lambda r: num(r["seconds"]), "ratio")
        std = cd.contrast(rows, a, "D1-K8", lambda r: num(r["std_seconds"]), "ratio")
        pairs[key] = {"raw": raw["est"], "std": std["est"], "gap": abs(std["est"] - raw["est"])}
    out["office"] = pairs
    out["office_max_gap"] = max(v["gap"] for v in pairs.values())
    return out


# ------------------------------------------------------------------ the primary comparisons written down beforehand
# (experiment, statistics file, metric, margin of "no difference", unit, [(label in the file, what is compared)])
SCORECARD = (
    ("办公报告题第一批（按评分表打总分）", "results/analysis-v2/stats-office.json", "score", 5, "分", (
        ("H1", "默认对不开 subagent"), ("H2a", "K=1 对 K=8"), ("H2b", "K=2 对 K=8"), ("H2c", "K=4 对 K=8"), ("H3a", "深度 2 对深度 1"), ("H3b", "深度 3 对深度 1"),
        ("H4", "K 的作用在深度 3 和深度 1 下差多少"))),
    ("读代码题和小编程题第一批（三道题合在一起）", "results/analysis-v2/stats-code.json", "score", 5, "分", (
        ("C1", "默认对不开 subagent"), ("C2", "并行提示对默认"), ("C3a", "K=1 对 K=8（加并行提示）"), ("C3b", "K=2 对 K=8（加并行提示）"), ("C3c", "K=4 对 K=8（加并行提示）"),
        ("C4a", "深度 2 对深度 1（加并行提示）"), ("C4b", "深度 3 对深度 1（加并行提示）"), ("C5", "K 的作用在深度 3 和深度 1 下差多少"))),
    ("办公报告题：让进程等 subagent 结束再退出（按评分表打总分）", "results/analysis-wait/stats-wait.json", "score", 5, "分", (
        ("S1", "等对不等（深度 2）"), ("S2", "等对不等（深度 3）"), ("S3", "深度 2 对深度 1（都等）"), ("S4", "深度 3 对深度 1（都等）"))),
    ("限时 24 题：开不开", "results/analysis-ctl/stats-pw-exercises.json", "score", 5, "分", (("PC", "并行提示对不开 subagent"),)),
    ("16 步串行题：开不开", "results/analysis-ctl/stats-n1-chain16.json", "score", 5, "分", (("PC", "并行提示对不开 subagent"),)),
    ("限时 24 题换 K 和深度（限时 3 分钟）", "results/analysis-ctl-dk/stats-pw-exercises.json", "score", 5, "分", (
        ("K1", "K=1 对 K=8"), ("K2", "K=2 对 K=8"), ("K4", "K=4 对 K=8"), ("K16", "K=16 对 K=8"), ("FD", "深度 2 对深度 1（五个 K 合起来）"))),
    ("限时 24 题换 K 和深度（限时 2 分钟，只作参考）", "results/analysis-ctl-dk/stats-pw-exercises-120.json", "score", 5, "分", (
        ("K1", "K=1 对 K=8"), ("K2", "K=2 对 K=8"), ("K4", "K=4 对 K=8"), ("K16", "K=16 对 K=8"), ("FD", "深度 2 对深度 1（五个 K 合起来）"))),
    ("不限时 24 题：到最终回答的时间", "results/analysis-ctl-free-all/stats-pw-exercises-free.json", "answer_s", None, "", (
        ("K1", "K=1 对 K=8"), ("K2", "K=2 对 K=8"), ("K4", "K=4 对 K=8"), ("K16", "K=16 对 K=8"), ("K64", "K=64 对 K=8"), ("FD", "深度 2 对深度 1（K=4、8、16 合起来）"))),
    ("不限时 24 题：K 到多少时间不再缩短", "results/analysis-ctl-free-all/stats-plateau.json", "answer_s", None, "", (
        ("P4", "K=4 对 K=64"), ("P8", "K=8 对 K=64"), ("P16", "K=16 对 K=64"))),
    ("办公报告题 K=64 和放开深度（按评分表打总分）", "results/analysis-office-highk/stats-office-highk.json", "score", 5, "分", (
        ("H1", "K=64 对 K=8（深度 1）"), ("H2", "深度 2、K=64 对默认"), ("H3", "深度 3、K=64 对默认"))),
    ("办公报告题 K=64 和放开深度：费用", "results/analysis-office-highk/stats-office-highk.json", "total_cost_peak", None, "", (
        ("H1", "K=64 对 K=8（深度 1）"), ("H2", "深度 2、K=64 对默认"), ("H3", "深度 3、K=64 对默认"))),
    ("大型编码题（加不复核提示）：到最终回答的时间", "results/analysis-xl-main/stats.json", "answer_s", None, "", (
        ("K1", "K=1 对 K=8"), ("K2", "K=2 对 K=8"), ("K4", "K=4 对 K=8"), ("K16", "K=16 对 K=8"))),
    ("办公报告题第一批的报告，改按事实清单判分", "results/analysis-facts/stats-facts.json", "right_pct", 8, "个百分点", (
        ("H1", "默认对不开 subagent"), ("H2a", "K=1 对 K=8"), ("H2b", "K=2 对 K=8"), ("H2c", "K=4 对 K=8"), ("H3a", "深度 2 对深度 1"), ("H3b", "深度 3 对深度 1"))),
    ("办公报告题：重做来确认的一批（按事实清单判分）", "results/analysis-facts-confirm/stats.json", "right_pct", 8, "个百分点", (("K1", "K=1 对 K=8"), ("K2", "K=2 对 K=8"), ("K4", "K=4 对 K=8"))),
    ("办公报告题 K=64 和放开深度（改按事实清单判分）", "results/analysis-facts-highk/stats.json", "right_pct", 8, "个百分点", (
        ("H1", "K=64 对 K=8（深度 1）"), ("H2", "深度 2、K=64 对默认"), ("H3", "深度 3、K=64 对默认"))),
    ("办公报告题：让进程等 subagent 结束再退出（改按事实清单判分）", "results/analysis-facts-wait2/stats.json", "right_pct", 8, "个百分点", (("WD2", "深度 2 对深度 1"), ("WD3", "深度 3 对深度 1"))),
    ("评测集填表题：开不开", "results/analysis-ws-h1/stats.json", "f1_item", 5, "分", (("H1n", "默认对不开 subagent"), ("H1e", "并行提示对不开 subagent"))),
    ("办公报告题：不开 subagent 加多查 100/100", "results/analysis-facts-floor/stats.json", "right_pct", 8, "个百分点", (("PRIM", "多查 100/100 对默认"),)),
    ("大型编码题：K=16、64 时的深度 2", "results/analysis-xl-depth/stats.json", "answer_s", None, "", (("DE16", "深度 2 对深度 1（K=16）"), ("DE64", "深度 2 对深度 1（K=64）"))),
    ("办公报告题：加都写进去提示时的深度 2", "results/analysis-facts-keepdepth/stats.json", "right_pct", 8, "个百分点", (("DK", "深度 2 对深度 1（都加都写进去提示）"),)),
    ("评测集报告题：开不开", "results/analysis-drb2-h1/stats.json", "total", 5, "分", (("H1", "默认对不开 subagent"),)),
    ("评测集报告题：换 K 和深度", "results/analysis-drb2-kd/stats.json", "total", 5, "分", (("K1", "K=1 对 K=8"), ("D2", "深度 2 对深度 1"))),
)


def primary_word(r: dict, metric: str, margin, ratio: bool) -> str:
    """The word of the report for a primary comparison: corrected within its family when the family has more than one
    member; "no difference" when the whole interval lies inside the margin (scores and shares only)."""
    many = r["family_size"] > 1
    weak = many and not (r["holm"] is not None and r["holm"] < 0.05)
    if ratio:
        if r["lo"] <= 1 <= r["hi"]:
            return "没测出差别"
        if weak:
            return "校正后不显著"
        slow = metric in ("answer_s", "seconds")
        return ("显著更慢" if slow else "显著更贵") if r["est"] > 1 else ("显著更快" if slow else "显著更省")
    if r["lo"] > 0 or r["hi"] < 0:
        return "校正后不显著" if weak else ("显著变好" if r["lo"] > 0 else "显著变差")
    return "没有差别" if abs(r["lo"]) <= margin and abs(r["hi"]) <= margin else "没测出差别"


def scorecard() -> list:
    """Every comparison the plan declared as primary before the runs, with its result as the batch's own statistics
    file holds it (estimate, 95% interval, Holm-corrected p within the family, pairs)."""
    out = []
    spec = SCORECARD
    if (EXP / DOSE_STATS).exists():
        spec = spec + (("办公报告题：不开 subagent 加多查 150/250、多查 250/500", DOSE_STATS, "right_pct", 8, "个百分点", (("P150", "多查 150/250 对默认"), ("P250", "多查 250/500 对默认"))),)
    if TOLD_READY():  # quality on the 63 items fixed beforehand, as the plan of this batch wrote
        spec = spec + (("办公报告题：把同时存活上限写进工具说明", TOLD_STATS, "right_legacy_pct", 8, "个百分点", (("P1", "K=2：告知对不告知"), ("P2", "K=8：告知对不告知"))),)
    for title, f, metric, margin, unit, items in spec:
        m = J(f)["metrics"][metric]
        ratio = m.get("kind") == "ratio"
        g = math.exp if ratio else (lambda v: v)
        rows = []
        for key, label in items:
            c = m["comparisons"][key]
            assert c.get("family", "primary") == "primary", (f, metric, key, c.get("family"))
            r = {"key": key, "label": label, "est": g(c["est"]), "lo": g(c["lo"]), "hi": g(c["hi"]), "n": c["n"], "holm": c.get("p_holm"), "ratio": ratio, "family_size": len(items)}
            r["word"] = primary_word(r, metric, margin, ratio)
            rows.append(r)
        out.append({"title": title, "metric": metric, "margin": margin, "unit": unit, "ratio": ratio, "rows": rows})
    if PUBK_READY():  # one family over two files: K = 4 against K = 8 on each public benchmark's main score
        pub = cd.public()
        rows = []
        for key, label, c in (("wsk", "评测集填表题：K=4 对 K=8", pub["wsk"]["cmp"]["K4"]["f1_item"]), ("drbk", "评测集报告题：K=4 对 K=8", pub["drbk"]["cmp"]["K4"]["total"])):
            r = {"key": key, "label": label, "est": c["est"], "lo": c["lo"], "hi": c["hi"], "n": c["n"], "holm": c["holm"], "ratio": False, "family_size": 2}
            r["word"] = primary_word(r, "score", 5, False)
            rows.append(r)
        out.append({"title": "两个公开评测集补测 K=4", "metric": "score", "margin": 5, "unit": "分", "ratio": False, "rows": rows})
    return out


def stat(f: str, metric: str, key: str) -> dict:
    """One comparison of a batch's statistics file (ratio metrics as ratios)."""
    m = J(f)["metrics"][metric]
    c = m["comparisons"][key]
    ratio = m.get("kind") == "ratio"
    g = math.exp if ratio else (lambda v: v)
    return {"est": g(c["est"]), "lo": g(c["lo"]), "hi": g(c["hi"]), "n": c["n"], "holm": c.get("p_holm"), "ratio": ratio,
            "mdd": (g(c["mdd"]) if c.get("mdd") is not None else None), "family": c.get("family")}


def expectations() -> dict:
    """Numbers set against the results the plan expected beforehand (the appendix table of expectations)."""
    out = {}
    # the search-more sentence: the runs that reached 200 search requests, against their paired default
    rows = [r for r in R("results/analysis-office-floor/rows-all.csv") if cd.complete(r)]
    ff = {r["id"]: r for r in R("results/analysis-facts-floor/fact-rows.csv")}
    by = {(r["task"], r["rep"], r["group"]): r for r in rows if r["id"] in ff}
    d = [num(ff[r["id"]]["right_pct"]) - num(ff[by[(t, q, "D1-K8")]["id"]]["right_pct"]) for (t, q, g), r in by.items()
         if g == "E-D0" and num(r["search_aux"]) >= 200 and (t, q, "D1-K8") in by]
    out["more200"] = {"n": len(d), "diff": st.mean(d)}
    # merged reports, each batch: % right of the merged report (tasks weighted equally)
    out["merged"] = {}
    for kind in ("M2", "M4"):
        out["merged"][kind] = []
        for f in ("results/analysis-office-merge/merge-stats.json", "results/analysis-office-merge-b/merge-stats.json"):
            rs = [r for r in J(f)["rows"] if r["kind"] == kind]
            out["merged"][kind].append(st.mean(st.mean(r["merged_right_pct"] for r in rs if r["base_task"] == t) for t in TASKS))
    w, h, kd_, xd = "results/analysis-wait/stats-wait.json", "results/analysis-office-highk/stats-office-highk.json", "results/analysis-facts-keepdepth/stats.json", "results/analysis-xl-depth/stats.json"
    out["wait"] = {k: {m: stat(w, m, k) for m in ("total_cost_peak", "seconds")} for k in ("S1", "S2")}
    out["highk_cost"] = {k: stat(h, "total_cost_peak", k) for k in ("H1", "H2", "H3")}
    out["highk_score"] = {k: stat(h, "score", k) for k in ("H1", "H2", "H3")}
    out["keep_depth"] = {m: stat(kd_, m, "DK") for m in ("right_pct", "total_cost_peak")}
    out["xl_depth"] = {k: {m: stat(xd, m, k) for m in ("answer_s", "model_cost_peak")} for k in ("DE16", "DE64")}
    # the first batch's rubric score with the rule added after the scores were seen (runs without a complete report left out)
    out["first_complete"] = {k: stat("results/analysis-complete/stats-office.json", "score", k) for k in ("H3a", "H3b", "H4")}
    # the search-more runs that reached 200 requests against their paired default, the report's usual way
    sub = [dict(r, m=num(ff[r["id"]]["right_pct"])) for (t, q, g), r in by.items()
           if (g == "E-D0" and num(r["search_aux"]) >= 200) or (g == "D1-K8" and (t, q, "E-D0") in by and num(by[(t, q, "E-D0")]["search_aux"]) >= 200)]
    out["more200"]["contrast"] = cd.contrast(sub, "E-D0", "D1-K8", lambda r: r["m"])
    out["dk"] = {"k16_2min": stat("results/analysis-ctl-dk/stats-pw-exercises-120.json", "score", "K16"), "k1_none": stat("results/analysis-ctl-dk/stats-pw-exercises.json", "score", "Z1")}
    out["facts_line"] = {"k64": stat("results/analysis-facts-highk/stats.json", "right_pct", "H1"), "d2k64": stat("results/analysis-facts-highk/stats.json", "right_pct", "H2"),
                         "d3k64": stat("results/analysis-facts-highk/stats.json", "right_pct", "H3"), "wd2": stat("results/analysis-facts-wait2/stats.json", "right_pct", "WD2"),
                         "wd3": stat("results/analysis-facts-wait2/stats.json", "right_pct", "WD3")}
    return out


# ------------------------------------------------------------------------------ how small a difference could show
def half(c: dict) -> float:
    """Half the width of a 95% interval: for a difference in its unit; for a ratio as a factor (x or / this much)."""
    if c.get("ratio"):
        return math.exp((math.log(c["hi"]) - math.log(c["lo"])) / 2)
    return (c["hi"] - c["lo"]) / 2


def dose() -> dict | None:
    """The two-dose batch (plan: 追加实验：单 agent 多查两档), when its analysis exists: the paired contrasts of the batch's
    statistics file and what dose_extra.py wrote (volumes reached, the single agent's curve, context, prices)."""
    if not (EXP / DOSE_STATS).exists():
        return None
    s = J(DOSE_STATS)
    cmp_ = {}
    for metric, m in s["metrics"].items():
        for key in m["comparisons"]:
            cmp_.setdefault(key, {})[metric] = stat(DOSE_STATS, metric, key)
    by_task = {}
    for t in TASKS:
        st_ = J(f"results/analysis-facts-dose/stats-{t}.json")
        by_task[t] = {key: stat(f"results/analysis-facts-dose/stats-{t}.json", "right_pct", key) for key in st_["metrics"]["right_pct"]["comparisons"]}
    rows = [r for r in R(DOSE_ROWS)]
    facts = {r["id"]: r for r in R("results/analysis-facts-dose/fact-rows.csv")}
    done = [r for r in rows if cd.complete(r) and r["id"] in facts]
    means = {}
    for g in ("D0", "E-D0", "N-D0", "D1-K8"):  # complete, judged runs; the tasks weighted equally (like the other office tables)
        x = [r for r in done if r["group"] == g]
        te = lambda f: st.mean(st.mean(f(r) for r in x if r["task"] == t) for t in TASKS)  # noqa: E731
        fx = lambda col: te(lambda r: num(facts[r["id"]][col]))  # noqa: E731
        rx = lambda col: te(lambda r: num(r[col]) or 0)  # noqa: E731
        peaks = sorted(num(r["root_peak"]) for r in x if num(r.get("root_peak")) is not None)
        means[g] = {"n": len(x), "runs": sum(1 for r in rows if r["group"] == g), "right_pct": fx("right_pct"), "right_legacy_pct": fx("right_legacy_pct"), "right_n": fx("right_n"),
                    "wrong": fx("wrong_firm_n"), "search": rx("search_aux"), "calls": rx("web_search_calls"), "cost": rx("total_cost_peak"), "model_cost": rx("model_cost_peak"),
                    "minutes": te(lambda r: cd.answer_s(r) / 60), "chars": rx("deliv_chars"), "kids": rx("children"),
                    "peak_median": st.median(peaks), "peak_max": peaks[-1], "pruned": sum(1 for r in x if (num(r.get("root_compact")) or 0) > 0)}
    # search requests against the default by task (pairs = repeats), and the contrast against no subagents with every run counted
    sr = lambda r: num(r["search_aux"]) or None  # noqa: E731  (a run without any search request cannot enter a ratio)
    search_task = {t: {g: cd.contrast([r for r in done if r["task"] == t and sr(r)], g, "D1-K8", sr, "ratio") for g in ("E-D0", "N-D0")} for t in TASKS}
    allv = lambda r: num(facts[r["id"]]["right_pct"]) if r["id"] in facts else 0.0  # noqa: E731
    every = {"Z150": cd.contrast(rows, "E-D0", "D0", allv), "Z250": cd.contrast(rows, "N-D0", "D0", allv)}
    return {"cmp": cmp_, "extra": J("results/analysis-facts-dose/extra.json"), "by_task": by_task, "runs": len(rows), "means": means, "search_task": search_task, "every": every,
            "timeouts": sum(1 for r in rows if str(r.get("timeout")) == "True"),
            "second": J("results/analysis-facts-dose/second-pass.json") if (EXP / "results/analysis-facts-dose/second-pass.json").exists() else None}


def told() -> dict | None:
    """The told-limit batch (plan: 追加实验：把同时存活上限写进工具说明), when its analysis exists: the paired contrasts of
    the batch's statistics file (P1, P2 primary; S1, S2 listed in advance), the same with every run counted, by task,
    the group means, and what told_extra.py wrote (rejections told / not told, the interaction, the second pass)."""
    if not TOLD_READY():
        return None
    keys = ("P1", "P2", "S1", "S2")

    def contrasts(f: str) -> dict:
        s = J(f)
        return {k: {m: stat(f, m, k) for m, mm in s["metrics"].items() if k in mm["comparisons"]} for k in keys}
    cmp_ = contrasts(TOLD_STATS)
    every = contrasts("results/analysis-facts-told/stats-every-run.json")
    by_task = {t: contrasts(f"results/analysis-facts-told/stats-{t}.json") for t in TASKS}
    rows = R(TOLD_ROWS)
    facts = {r["id"]: r for r in R("results/analysis-facts-told/fact-rows.csv")}
    done = [r for r in rows if cd.complete(r) and r["id"] in facts]
    means = {}
    for g in ("D1-K2", "T-D1-K2", "D1-K8", "T-D1-K8"):
        x = [r for r in done if r["group"] == g]
        allg = [r for r in rows if r["group"] == g]
        te = lambda f_, src=x: st.mean(st.mean(f_(r) for r in src if r["task"] == t) for t in TASKS)  # noqa: E731  (the tasks weighted equally)
        fx = lambda col: te(lambda r: num(facts[r["id"]][col]))  # noqa: E731
        rx = lambda col, src=x: te(lambda r: num(r[col]) or 0, src)  # noqa: E731
        cap = [int(num(r.get("capacity_rejects")) or 0) for r in allg]
        means[g] = {"n": len(x), "runs": len(allg), "incomplete": sum(1 for r in allg if not cd.complete(r)),
                    "right_legacy_pct": fx("right_legacy_pct"), "right_pct": fx("right_pct"), "right_n": fx("right_n"), "wrong": fx("wrong_firm_n"),
                    "cost": rx("total_cost_peak"), "model_cost": rx("model_cost_peak"), "minutes": te(lambda r: cd.answer_s(r) / 60), "search": rx("search_aux"),
                    "chars": rx("deliv_chars"), "kids": rx("children", allg), "slot_peak": rx("slot_peak", allg), "depth_rejects": rx("depth_rejects", allg),
                    "cap_rejects": st.mean(cap), "cap_reject_runs": sum(1 for v in cap if v), "early": sum(1 for r in allg if r.get("early_finish") == "1"),
                    "crash": sum(1 for r in allg if r.get("crash5063") == "True")}
    second = "results/analysis-facts-told/second-pass.json"
    return {"cmp": cmp_, "every": every, "by_task": by_task, "means": means, "extra": J("results/analysis-facts-told/extra.json"), "runs": len(rows),
            "second": J(second) if (EXP / second).exists() else None}


# ------------------------------------------------------- every tested value of the two limits against the default
def strong(c: dict, corrected: bool = False) -> bool:
    """A contrast counts as detected: its interval leaves out 0 (1 for a ratio) and, where it belongs to a family
    that was corrected together, it survives the correction. The rule of the report's bracketed numbers."""
    ref = 1 if c.get("ratio") else 0
    if c["lo"] <= ref <= c["hi"]:
        return False
    holm = c.get("holm", c.get("p_holm"))
    return not corrected or (holm is not None and holm < 0.05)


def _triple(d: dict, pre: str, ratio: bool, n=None) -> dict:
    return {"est": d[f"{pre}est" if not ratio else f"{pre}ratio"], "lo": d[f"{pre}lo"], "hi": d[f"{pre}hi"], "ratio": ratio, "n": n, "holm": None}


def office_k_pooled() -> dict:
    """K = 1, 2, 4 against K = 8 on the office task, the first batch and the main batch together (the estimate the plan
    of 2026-10-04 11:53Z asks for): pairs are (task, repeat) inside a batch, deviations taken inside each (batch, task).
    legacy / full: difference in facts stated correctly on the 63 items fixed beforehand / on the whole list
    (percentage points); cost, time: ratios (cost with search fees; time to the root's final answer)."""
    r1 = R("results/analysis-v2/rows-office.csv")
    r2 = [r for r in R("results/analysis-office-confirm/rows-all.csv") if cd.complete(r)]
    f1 = {r["id"]: r for r in R("results/analysis-facts/fact-rows.csv")}
    f2 = {r["id"]: r for r in R("results/analysis-facts-confirm/fact-rows.csv")}
    judged = ((r1, f1), (r2, f2))

    def together(a: str, col, kind: str) -> dict:
        strata = {}
        for name, (rows, fx) in zip(("first", "main"), judged):
            conv = [{"task": r["task"], "group": r["group"], "rep": r["rep"], "m": col(r, fx)} for r in rows if r["group"] in (a, "D1-K8") and r["id"] in fx and cd.complete(r)]
            dbt, _, _ = cd.ps.paired(cd.ps.index_rows([q for q in conv if q["m"] is not None]), a, "D1-K8", "m", kind)
            for t, dv in dbt.items():
                strata[(name, t)] = list(dv.values()) if isinstance(dv, dict) else list(dv)
        return dict(cd.pooled(strata, kind == "ratio"), a=a, b="D1-K8")
    out = {}
    for v in (1, 2, 4):
        g = f"D1-K{v}"
        out[v] = {"legacy": together(g, lambda r, fx: num(fx[r["id"]]["right_legacy_pct"]), "diff"), "full": together(g, lambda r, fx: num(fx[r["id"]]["right_pct"]), "diff"),
                  "cost": together(g, lambda r, fx: num(r["total_cost_peak"]), "ratio"), "time": together(g, lambda r, fx: cd.answer_s(r), "ratio")}
    return out


def limits(D: dict) -> dict:
    """One row per kind of task, one cell per tested value of K (depth 1) and of the depth limit (K = 8): the
    difference in quality and the ratios of cost and time against the default-like group run with it. The same
    contrasts as the tables of the K and depth sections (those tables are written from this), so the two overview
    figures of the conclusions and the tables cannot disagree.

    cell: q / c / t = contrast dicts (None: not measured), corr = (q, c, t) corrected together with a family,
    star = a primary comparison written down beforehand, legacy = the same contrast on the 63 items fixed beforehand,
    nd = decimals of the quality difference. base: the reference group's own level (quality, yuan, minutes)."""
    o, c, k, b, p, gr = D["office"], D["code"], D["ctl"], D["build"], D["pub"], D["grid"]
    cmp_, pooled, lg = o["cmp"], o["depth_pooled"], o["legacy"]
    leg = {g: cmp_[g]["right_legacy_pct"] for g in cmp_}
    free, xl, ws, drb, kd = b["free"], b["xl"], p["ws"], p["drb2"], p["drb2kd"]
    wd, ch, g3 = k["wide"], k["chain"], gr["m3"]["cmp"]
    fk, xk, cc = free["cmp"], xl["cmp"], c["cmp"]
    p4s = J("results/analysis-v2/stats-code-p4-python.json")
    p4 = {q: {m_: cd.comp(p4s, m_, q) for m_ in ("score", "model_cost_peak", "seconds")} for q in ("C1", "N2", "N3")}
    dk = [r for r in R("results/analysis-ctl-dk/rows.csv") if r["task"] == "pw-exercises"]
    dkc = lambda a, b_: cd.contrast(dk, a, b_, lambda r: num(r["model_cost_peak"]), "ratio")  # noqa: E731
    dk_mean = lambda g, col: st.mean(num(r[col]) for r in dk if r["group"] == g)  # noqa: E731

    def cell(q=None, c_=None, t=None, corr=(False, False, False), star=False, legacy=None, nd=1, flip=False, note=""):
        """The quality contrast is a difference, cost and time are ratios (some files do not carry the flag)."""
        f = (lambda v: cd.flip(v) if v is not None else None) if flip else (lambda v: v)
        tag = lambda v, ratio: None if v is None else dict({"a": None, "b": None}, **dict(v, ratio=ratio))  # noqa: E731
        assert all(v is None or v.get("ratio", r_) == r_ for v, r_ in ((q, False), (c_, True), (t, True), (legacy, False)))
        return {"q": f(tag(q, False)), "c": f(tag(c_, True)), "t": f(tag(t, True)), "corr": corr, "star": star, "legacy": f(tag(legacy, False)), "nd": nd, "note": note}

    def three(v: dict, tm: str = "seconds", **kw):
        return cell(v["score"], v["model_cost_peak"], v[tm], **kw)

    p2, p3 = pooled["2_k8"], pooled["3_k8"]
    pool_cell = lambda v: cell(_triple(v, "", False, v["pairs"]), _triple(v, "cost_", True, v["pairs"]), _triple(v, "time_", True, v["pairs"]),  # noqa: E731
                               legacy=_triple(v, "legacy_", False, v["pairs"]))
    om, wp, dp = o["means"]["D1-K8"], ws["pair"]["W-D1-K8"], drb["pair"]["W-D1-K8"]
    T = (True, True, True)
    k_rows = [
        {"key": "office", "name": "办公报告题", "sub": "", "margin": 8, "unit": "个百分点", "base": {"q": om["right_pct"], "c": om["cost"], "t": om["minutes"], "qu": "%"},
         "cells": {1: cell(cmp_["D1-K1"]["right_pct"], cmp_["D1-K1"]["total_cost_peak"], cmp_["D1-K1"]["seconds"], (True, True, False), True, leg["D1-K1"]),
                   2: cell(cmp_["D1-K2"]["right_pct"], cmp_["D1-K2"]["total_cost_peak"], cmp_["D1-K2"]["seconds"], (True, True, False), True, leg["D1-K2"]),
                   4: cell(cmp_["D1-K4"]["right_pct"], cmp_["D1-K4"]["total_cost_peak"], cmp_["D1-K4"]["seconds"], (True, True, False), True, leg["D1-K4"]),
                   64: cell(o["k64"]["right_pct"], o["k64"]["total_cost_peak"], o["k64"]["answer_s"], (True, True, False), True, lg["k64"])}},
        {"key": "drb2", "name": "评测集报告题", "sub": "", "margin": 5, "unit": "分",
         "base": {"q": kd["base"]["total"], "c": kd["base"]["cost"], "t": kd["base"]["answer_minutes"], "qu": "分"},  # the default of the batch that changed K
         "cells": {1: cell(kd["cmp"]["K1"]["total"], kd["cmp"]["K1"]["total_cost_peak"], kd["time"]["K1"], (False, True, False), True)}},
        {"key": "code", "name": "读代码题", "sub": "题面加并行提示", "margin": 5, "unit": "分",
         "base": {"q": c["means"]["E-D1-K8"]["score"], "c": c["means"]["E-D1-K8"]["cost"], "t": c["means"]["E-D1-K8"]["minutes"], "qu": "分"},
         "cells": {1: three(cc["C3a"], corr=T), 2: three(cc["C3b"], corr=T), 4: three(cc["C3c"], corr=T)}},
        {"key": "wide", "name": "限时 24 题", "sub": "题面加并行提示", "margin": 5, "unit": "分", "limited": True,
         "base": {"q": gr["m3"]["means"]["W-E-D1-K8"], "c": dk_mean("W-E-D1-K8", "model_cost_peak"), "t": None, "qu": "分"},
         "cells": {q: cell(g3[f"K{q}"], dkc(f"W-E-D1-K{q}", "W-E-D1-K8"), None, (True, False, False), True) for q in (1, 2, 4, 16)}},
        {"key": "free", "name": "不限时 24 题", "sub": "题面加并行提示", "margin": 5, "unit": "分",
         "base": {"q": free["means"]["W-E-D1-K8"]["score"], "c": free["means"]["W-E-D1-K8"]["cost"], "t": free["means"]["W-E-D1-K8"]["answer"], "qu": "分"},
         "cells": {q: three(fk[f"K{q}"], "answer_s", corr=T, star=True) for q in (1, 2, 4, 16, 64)}},
        {"key": "xl", "name": "大型编码题", "sub": "原题面", "margin": 5, "unit": "分", "tests": True,
         "base": {"q": xl["means"]["W-D1-K8"]["score"], "c": xl["means"]["W-D1-K8"]["cost"], "t": xl["means"]["W-D1-K8"]["answer"], "qu": "分"},
         "cells": {4: three(xk["NK4"], "answer_s", nd=2), 16: three(xk["NK16"], "answer_s", nd=2)}},
        {"key": "xln", "name": "大型编码题", "sub": "题面加不复核提示", "margin": 5, "unit": "分", "tests": True,
         "base": {"q": xl["means"]["W-N-D1-K8"]["score"], "c": xl["means"]["W-N-D1-K8"]["cost"], "t": xl["means"]["W-N-D1-K8"]["answer"], "qu": "分"},
         "cells": {q: three(xk[f"K{q}"], "answer_s", corr=T, star=True, nd=2) for q in (1, 2, 4, 16)}},
    ]
    cm, pm = c["means"]["D1-K8"], c["p4"]["means"]["D1-K8"]
    wm, chm, fm, xm, xn = wd["means"]["W-D1-K8"], ch["means"]["W-D1-K8"], free["means"]["W-D1-K8"], xl["means"]["W-D1-K8"], xl["means"]["W-N-D1-K8"]
    wt, dtm = ws["time"]["H1n"], drb["time"]["H1"]
    d_rows = [
        {"key": "office", "name": "办公报告题", "sub": "", "margin": 8, "unit": "个百分点", "base": {"q": om["right_pct"], "c": om["cost"], "t": om["minutes"], "qu": "%"},
         "cells": {0: cell(cmp_["D0"]["right_pct"], cmp_["D0"]["total_cost_peak"], cmp_["D0"]["seconds"], legacy=leg["D0"]), 2: pool_cell(p2), 3: pool_cell(p3)},
         "k64": {2: cell(o["k64_d2"]["right_pct"], o["k64_d2"]["total_cost_peak"], o["k64_d2"]["answer_s"], legacy=lg["d2k64"]),
                 3: cell(o["k64_d3"]["right_pct"], o["k64_d3"]["total_cost_peak"], o["k64_d3"]["answer_s"], star=True, legacy=lg["old"])}},
        {"key": "ws", "name": "评测集填表题", "sub": "", "margin": 5, "unit": "分", "base": {"q": wp["f1_item"], "c": wp["cost"], "t": wp["answer_minutes"], "qu": "分"},
         "cells": {0: cell(ws["cmp"]["H1n"]["f1_item"], ws["cmp"]["H1n"]["total_cost_peak"], wt, (True, True, False), True, flip=True)}},
        {"key": "drb2", "name": "评测集报告题", "sub": "", "margin": 5, "unit": "分", "base": {"q": dp["total"], "c": dp["cost"], "t": dp["answer_minutes"], "qu": "分"},
         "cells": {0: cell(drb["cmp"]["H1"]["total"], drb["cmp"]["H1"]["total_cost_peak"], dtm, star=True, flip=True),
                   2: cell(kd["cmp"]["D2"]["total"], kd["cmp"]["D2"]["total_cost_peak"], kd["time"]["D2"], (False, True, False), True)}},
        {"key": "code", "name": "读代码题", "sub": "", "margin": 5, "unit": "分", "base": {"q": cm["score"], "c": cm["cost"], "t": cm["minutes"], "qu": "分"},
         "cells": {0: three(cc["C1"], corr=T, flip=True), 2: three(cc["N2"]), 3: three(cc["N3"])}},
        {"key": "p4", "name": "小编程题", "sub": "", "margin": 5, "unit": "分", "base": {"q": pm["score"], "c": pm["cost"], "t": pm["minutes"], "qu": "分"},
         "cells": {0: three(p4["C1"], corr=T, flip=True), 2: three(p4["N2"]), 3: three(p4["N3"])}},
        {"key": "wide", "name": "限时 24 题", "sub": "深度 2：题面加并行提示", "margin": 5, "unit": "分", "limited": True, "base": {"q": wm["score"], "c": wm["cost"], "t": None, "qu": "分"},
         "cells": {0: cell(wd["cmp"]["NC"]["score"], wd["cmp"]["NC"]["model_cost_peak"], None, flip=True),
                   2: cell(g3["FD"], dkc("+".join(f"W-E-D2-K{q}" for q in (1, 2, 4, 8, 16)), "+".join(f"W-E-D1-K{q}" for q in (1, 2, 4, 8, 16))), None, star=True, note="五个 K 合起来")}},
        {"key": "chain", "name": "16 步串行题", "sub": "", "margin": 5, "unit": "分", "base": {"q": chm["score"], "c": chm["cost"], "t": chm["minutes"], "qu": "分"},
         "cells": {0: three(ch["cmp"]["NC"], flip=True)}},
        {"key": "free", "name": "不限时 24 题", "sub": "深度 2：题面加并行提示", "margin": 5, "unit": "分", "base": {"q": fm["score"], "c": fm["cost"], "t": fm["answer"], "qu": "分"},
         "cells": {0: three(fk["NC"], "answer_s", flip=True), 2: three(fk["FD"], "answer_s", corr=T, star=True, note="K=4、8、16 合起来")}},
        {"key": "xl", "name": "大型编码题", "sub": "原题面", "margin": 5, "unit": "分", "tests": True, "base": {"q": xm["score"], "c": xm["cost"], "t": xm["answer"], "qu": "分"},
         "cells": {0: three(xk["NC"], "answer_s", nd=2, flip=True), 2: three(xk["DN"], "answer_s", nd=2)}},
        {"key": "xln", "name": "大型编码题", "sub": "题面加不复核提示", "margin": 5, "unit": "分", "tests": True, "base": {"q": xn["score"], "c": xn["cost"], "t": xn["answer"], "qu": "分"},
         "cells": {0: three(xk["U"], "answer_s", nd=2, flip=True), 2: three(xk["DE"], "answer_s", nd=2)}},
    ]
    wsk, drbk = p.get("wsk"), p.get("drbk")
    if wsk and drbk:  # K = 4 on the two public benchmarks; K = 1 and depth 2 on the table-collection tasks
        wq = lambda x: cell(wsk["cmp"][x]["f1_item"], wsk["cmp"][x]["total_cost_peak"], wsk["time"][x], (x == "K4", False, False), x == "K4")  # noqa: E731
        k_rows.insert(1, {"key": "ws", "name": "评测集填表题", "sub": "", "margin": 5, "unit": "分",
                          "base": {"q": wsk["base"]["q"], "c": wsk["base"]["cost"], "t": wsk["base"]["answer_minutes"], "qu": "分"}, "cells": {1: wq("K1"), 4: wq("K4")}})
        next(r for r in k_rows if r["key"] == "drb2")["cells"][4] = cell(drbk["cmp"]["K4"]["total"], drbk["cmp"]["K4"]["total_cost_peak"], drbk["time"]["K4"], (True, False, False), True)
        next(r for r in d_rows if r["key"] == "ws")["cells"][2] = wq("D2")
    # The uniform rule of the main text for the K table (2026-10-08): on the office task the values that were run in
    # two batches (K = 1, 2, 4) are read from both batches together; the reading tasks are read the way the plan wrote
    # beforehand, the three code tasks together. These cells stand next to the ones above (key "rule"), which the
    # appendix still words; the figures, the overview table and the full table of the main text use "rule" where it exists.
    kp = office_k_pooled()
    orow = next(r for r in k_rows if r["key"] == "office")
    orow["rule"] = {v: cell(kp[v]["full"], kp[v]["cost"], kp[v]["time"], legacy=kp[v]["legacy"]) for v in (1, 2, 4)}
    orow["rule_what"] = "两批合起来"
    crow = next(r for r in k_rows if r["key"] == "code")
    crow["rule"] = {v: three(c["three"][q], corr=T, star=True) for v, q in ((1, "C3a"), (2, "C3b"), (4, "C3c"))}
    crow["rule_name"], crow["rule_sub"] = "读代码题和小编程题", "三题合起来，题面加并行提示"
    return {"k": k_rows, "depth": d_rows}


def rule_cells(r: dict) -> dict:
    """The cells of a row of limits() as the main text reads them: the cells of the uniform rule where they exist."""
    out = dict(r["cells"])
    out.update(r.get("rule", {}))
    return out


# ---------------------------------------------------------------------------------- delivery by task and setting
def reliability() -> dict:
    """How the runs ended, by task, setting, prompt variant and whether the process waited for the subagents, over every
    rows file behind the run count.
      runs        all runs of the cell
      incomplete  no deliverable or one under 5,000 characters (the three research tasks; None where it is not recorded)
      early       the root's turn ended while subagents were still open, so their work was lost (groups whose process
                  does not wait; None for the waiting groups, where the root simply goes on when they report)
      crash       the process failed on exit while a subagent's message arrived (#5063)
      other_exit  another non-zero exit that is not the time limit
      timeout     the run hit its time limit (the time-limited task is left out: there the limit is the design)
      wait_cap    waiting groups: subagents still alive after 20 minutes of waiting
      oom         a process was killed for memory (recorded for the large coding task only)"""
    agg = {}
    for f, fixed in every_rows().items():
        rows = R(f)
        cols = set(rows[0])
        for r in rows:
            row = fixed or TASK_ROW[r["task"]]
            if row in ("screen", "wide120"):
                continue
            col, var = setting(r["group"])
            waits = r["group"].startswith("W-")
            a = agg.setdefault((row, col, var, waits), collections.Counter())
            a["runs"] += 1
            if "incomplete" in cols:
                a["inc_known"] += 1
                a["incomplete"] += str(r["incomplete"]) == "1"
            elif row == "office":
                n = num(r.get("deliv_chars"))
                a["inc_known"] += 1
                a["incomplete"] += n is None or n < 5000
            a["crash"] += r.get("crash5063") == "True"
            a["other_exit"] += r.get("exit") not in ("0", "124") and r.get("crash5063") != "True"
            a["timeout"] += r.get("timeout") == "True" and row != "wide"
            if "early_finish" in cols and not waits:
                a["early_known"] += 1
                a["early"] += r["early_finish"] == "1"
            a["wait_cap"] += r.get("wait_cap") == "1"
            if "oom_kill" in cols:
                a["oom_known"] += 1
                a["oom"] += (num(r["oom_kill"]) or 0) > 0
    out = []
    for (row, col, var, waits), a in agg.items():
        out.append({"task": row, "col": col, "variant": var, "waits": waits, "runs": a["runs"],
                    "incomplete": a["incomplete"] if a["inc_known"] == a["runs"] else None,
                    "early": a["early"] if a["early_known"] == a["runs"] and not waits else None,
                    "crash": a["crash"], "other_exit": a["other_exit"], "timeout": a["timeout"], "wait_cap": a["wait_cap"] if waits else None,
                    "oom": a["oom"] if a["oom_known"] == a["runs"] else None})
    return {"cells": out}


def reliability_sum(cells: list, task: str, pick) -> dict:
    """The cells of one task that pick(cell) selects, added up (None where a count is not recorded for all of them)."""
    sel = [c for c in cells if c["task"] == task and pick(c)]
    out = {"runs": sum(c["runs"] for c in sel), "cells": len(sel)}
    for k in ("incomplete", "early", "crash", "other_exit", "timeout", "wait_cap", "oom"):
        out[k] = None if not sel or any(c[k] is None for c in sel) else sum(c[k] for c in sel)
    return out


def xl_by_group() -> dict:
    """The large coding task, per group of its two batches: subagents opened, the largest number alive at once, calls
    rejected by K, review subagents, runs with a process killed for memory, the memory peak, minutes until every file
    was written and until the final answer (arithmetic mean, as in the other tables; the geometric mean beside it), the
    model fee. dead = runs that ended at once without writing a file (one run: 27 seconds, no subagent, score 0); they
    are left out of the two times and counted separately."""
    out = {}
    for f, batch in (("results/analysis-xl-main/rows-all.csv", "main"), ("results/analysis-xl-depth/rows-all.csv", "depth")):
        rows = R(f)
        for g in sorted({r["group"] for r in rows}):
            x = [r for r in rows if r["group"] == g]
            live = [r for r in x if num(r.get("all_written_s")) is not None]  # the runs that wrote the files
            mean = lambda k, x=x: st.mean(num(r[k]) for r in x if num(r[k]) is not None)  # noqa: E731
            out[f"{batch}:{g}"] = {
                "batch": batch, "group": g, "n": len(x), "dead": len(x) - len(live), "full_runs": sum(1 for r in x if (num(r["slot_peak"]) or 0) >= int(g.split("K")[-1])) if "K" in g else 0,
                "kids": mean("children"), "slot_peak": mean("slot_peak"), "slot_max": max(num(r["slot_peak"]) or 0 for r in x),
                "cap_rejects": mean("capacity_rejects"), "review_kids": mean("review_kids"), "oom_runs": sum(1 for r in x if (num(r["oom_kill"]) or 0) > 0),
                "mem_peak": mean("mem_peak_gb"), "mem_full_runs": sum(1 for r in x if (num(r["mem_peak_gb"]) or 0) >= 15.9),
                "written_min": mean("all_written_s", live) / 60, "answer_geo_min": math.exp(st.mean(math.log(num(r["answer_s"])) for r in live if num(r["answer_s"]))) / 60,
                "answer_min": mean("answer_s", live) / 60, "after_written_min": st.mean((num(r["answer_s"]) - num(r["all_written_s"])) / 60 for r in live), "cost": mean("model_cost_peak")}
    return out


# ----------------------------------------------------------------- web work repeated between the agents of a run
OVERLAP = (("results/analysis-office-confirm/search-overlap-pages.csv", (("D1-K1", "K=1"), ("D1-K2", "K=2"), ("D1-K4", "K=4"), ("D1-K8", "默认（K=8）"), ("D2-K8", "深度 2（K=8）"))),
           ("results/analysis-office-highk/search-overlap-pages.csv", (("W-D2-K64", "深度 2、K=64"), ("W-D3-K64", "深度 3、K=64"))))


def overlap() -> list:
    """The office task, per setting: agents with web calls, distinct search queries and distinct pages opened with
    web_fetch in one run, and how many of them two or more agents asked for (scripts/search_overlap.py: a query is
    compared lower-cased with whitespace collapsed, a page by its URL without scheme, www., fragment and trailing
    slash). Pages fetched inside shell commands are not in these counts."""
    out = []
    for f, groups in OVERLAP:
        rows = R(f)
        for g, label in groups:
            x = [r for r in rows if r["group"] == g]
            mean = lambda k, x=x: st.mean(num(r[k]) for r in x)  # noqa: E731
            share = lambda a, b, x=x: st.mean(num(r[a]) / num(r[b]) for r in x if num(r[b]))  # noqa: E731
            out.append({"group": g, "label": label, "n": len(x), "agents": mean("agents_web"), "queries": mean("searches_distinct"), "query_cross": mean("search_cross"),
                        "query_cross_share": share("search_cross", "searches_distinct"), "pages": mean("fetches_distinct"), "page_cross": mean("fetch_cross"),
                        "page_cross_share": share("fetch_cross", "fetches_distinct")})
    return out


MECH = "results/analysis-mechanism"
MECH_BATCHES = ("main-office", "main-code", "main-code-B", "ctl-main", "wait-office-2", "ctl-dk", "ctl-free", "ctl-free-b2", "xl-main", "xl-depth", "office-confirm", "office-highk",
                "office-floor", "office-keep-depth", "ws-screen", "ws-h1", "drb2-h1", "drb2-kd", "office-dose", "ws-k4", "drb2-k4")  # every batch of the report


def mechanism() -> dict:
    """What the session logs say about the delegation calls (scripts/mechanism_extra.py, run on the dev box by
    scripts/mech-run.sh; files in results/analysis-mechanism):
    rejects   per batch and group, per run: delegation calls rejected by the depth limit and by K; the yuan of the
              output tokens that wrote the arguments of the rejected calls; the requests whose every call was rejected
              and their yuan (input, cache hits and output; the two amounts overlap in the output of such a request)
    tools     over every run of the report: calls of `subagent` and of `subagent_fork`, subagents started
    senders   the 90 runs whose handed-back messages were judged: a fact judged right is assigned to the subagent whose
              message holds its quote; "also elsewhere" when the quote or the fact's value is in another subagent's messages
    trees     two runs of the travel task from the main office batch (default, depth 2; the run whose number of
              subagents is the group's median): every agent with its parent"""
    rej, tools, per = {}, collections.Counter(), {}
    batches = MECH_BATCHES + (("office-told",) if TOLD_READY() and (EXP / f"{MECH}/rejects-office-told.json").exists() else ())  # the told-limit batch, together with the rest of its analysis
    for b in batches:
        rej[b] = J(f"{MECH}/rejects-{b}.json")["groups"]
        per[b] = J(f"{MECH}/tools-{b}.json")[b]
        for v in per[b].values():
            tools.update(v)
    total = {k: sum(v[k] * v["runs"] for g in rej.values() for v in g.values()) for k in ("depth", "cap", "args_yuan", "dead_step_yuan", "dead_steps", "model_yuan")}
    total["runs"] = sum(v["runs"] for g in rej.values() for v in g.values())
    senders = {}
    for b in ("office-confirm", "office-floor", "office-highk"):
        for g, v in J(f"{MECH}/relay-senders-{b}.json")["groups"].items():
            senders[f"{b}/{g}"] = v
    trees = {g: J(f"{MECH}/tree-{g}.json") for g in ("D1-K8", "D2-K8")}
    return {"rejects": rej, "tools": dict(tools), "tools_by_batch": per, "rejected": total, "senders": senders, "trees": trees}


def second_all() -> list:
    """Agreement of the two judging passes on the fact lists, slot by slot, in every batch that has a second pass."""
    out = []
    for f in sorted(EXP.glob("results/analysis-facts*/second-pass.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        out.append({"batch": f.parent.name, "n": j["n"], "same": j["same"], "share": j["same"] / j["n"], "reports": j["reports"]})
    return out


def load() -> dict:
    return {"dose": dose(), "second_all": second_all(), "strata": fact_strata(), "strata_merged": strata_merged(), "origin": list_origin(), "relay": relay(), "merge_union": merge_union(), "pages": pages(), "coverage": coverage(), "price": price(), "speed": speed(), "scorecard": scorecard(), "expect": expectations(), "reliability": reliability(), "xl_groups": xl_by_group(), "overlap": overlap(), "mechanism": mechanism(), "told": told()}


if __name__ == "__main__":
    D = load()
    s = D["strata"]
    for key in ("confirm", "floor", "depth2"):
        print("== facts by how often a run without subagents states them; measured in", s[key]["measured_in"], "strata from", s[key]["strata_from"], s[key]["total"]["runs"], s[key]["total"]["strata_runs"])
        for r in s[key]["rows"]:
            print(f"  {r['name']:24s} items {r['items']:5.1f} (fixed beforehand {r['legacy']:4.1f})  {r['low']:5.1f} ({100 * r['low_rate']:3.0f}%) -> {r['high']:5.1f} ({100 * r['high_rate']:3.0f}%)  gain {r['gain']:+5.1f} = {100 * r['share']:3.0f}%")
        t = s[key]["total"]
        print(f"  total: {t['low']:.1f} -> {t['high']:.1f}, gain {t['gain']:+.1f}; two independent runs together {t['union2']:.1f}, four {t['union4']:.1f}")
    print("== relay")
    for r in D["relay"]["rows"]:
        print("  ", r["label"], r["runs"], round(r["handed"], 1), round(r["final"], 1), round(r["lost"], 1), f"{100 * r['lost_share']:.1f}%", round(r["own"], 1))
    print("  ", {k: (v if not isinstance(v, dict) else {q: round(w, 2) for q, w in v.items() if isinstance(w, float)}) for k, v in D["relay"].items() if k != "rows"})
    cv = D["coverage"]
    print("== coverage: total", cv["total"], "in grid", cv["in_grid"], "outside", cv["extra"])
    for rk, rn in COVER_ROWS:
        print(f"  {rn:16s}", " ".join(f"{cv['cells'].get(f'{rk}|{ck}', 0) or '·':>4}" for ck, _ in COVER_COLS))
    p = D["price"]
    print("== price", {k: (round(v, 5) if isinstance(v, float) else v) for k, v in p.items() if k != "ratios"})
    for k, v in p["ratios"].items():
        print("  ", k, {q: round(w, 3) for q, w in v.items()})
    sp = D["speed"]
    print("== speed", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in sp.items() if k not in ("batches", "office")})
    for b, v in sp["batches"].items():
        print("  ", b, v["runs"], {g: round(x, 1) for g, x in sorted(v["groups"].items())})
    print("  office", {k: {q: round(w, 3) for q, w in v.items()} for k, v in sp["office"].items()})
