#!/usr/bin/env python3
"""Numbers for the reorganised report (build_clean.py, plot_clean.py): read from the analysis files, nothing typed.

One function per kind of task. Each returns plain numbers; the contrasts are the ones the analysis scripts wrote
(paired_stats.py: pairs are (task, repeat) of one batch, the tasks weighted equally, t interval with the task
effect removed; ratio metrics on the log scale, shown here as ratios). Group means are arithmetic means with the
tasks weighted equally, as in the tables of the wiki page.

Usage: clean_data.py            prints every section (for checking)
"""
from __future__ import annotations

import csv
import json
import math
import re
import statistics as st
import sys
from pathlib import Path

sys.dont_write_bytecode = True
EXP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXP / "scripts"))
import depth_all as dal  # noqa: E402  (tci: pooled interval over (batch, task) strata)
import paired_stats as ps  # noqa: E402  (paired, t_interval: the method every batch's own statistics use)
SLOTS = 97.5  # mean length of the two fact lists (o1 96, o2 99): 1 percentage point is about 1 fact


def J(p: str):
    return json.loads((EXP / p).read_text(encoding="utf-8"))


def R(p: str) -> list:
    return list(csv.DictReader(open(EXP / p, encoding="utf-8")))


def num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def comp(stats: dict, metric: str, label: str) -> dict:
    """One contrast of a paired_stats output; ratio metrics come back as ratios (the file holds logs)."""
    m = stats["metrics"][metric]
    c = m["comparisons"][label]
    ratio = m["kind"] == "ratio"
    f = math.exp if ratio else (lambda v: v)
    return {"est": f(c["est"]), "lo": f(c["lo"]), "hi": f(c["hi"]), "n": c["n"], "p": c.get("p"), "holm": c.get("p_holm"), "ratio": ratio,
            "a": c.get("a"), "b": c.get("b"), "mdd": (f(c["mdd"]) if c.get("mdd") is not None else None), "family": c.get("family")}


def flip(c: dict) -> dict:
    """The same contrast the other way round (B - A, or B / A)."""
    if c["ratio"]:
        return dict(c, est=1 / c["est"], lo=1 / c["hi"], hi=1 / c["lo"], a=c["b"], b=c["a"])
    return dict(c, est=-c["est"], lo=-c["hi"], hi=-c["lo"], a=c["b"], b=c["a"])


def means(rows: list, group: str, col, ok=lambda r: True) -> float | None:
    """Arithmetic mean of a column over the group's runs, the tasks weighted equally."""
    get = col if callable(col) else (lambda r: num(r.get(col)))
    by = {}
    for r in rows:
        if r["group"] == group and ok(r):
            v = get(r)
            if v is not None:
                by.setdefault(r["task"], []).append(v)
    return st.mean(st.mean(v) for v in by.values()) if by else None


def count(rows: list, group: str, ok=lambda r: True) -> int:
    return sum(1 for r in rows if r["group"] == group and ok(r))


def complete(r: dict) -> bool:
    return str(r.get("incomplete", "0")) != "1"


_FACT_LISTS = {}


def fact_shares(path, task: str) -> tuple:
    """(% right on the whole fact list, % right on the items fixed before any report was read) of one judged report."""
    short = {"o1-singapore-trip": "o1", "o2-server-cpu-report": "o2"}[task]
    if short not in _FACT_LISTS:
        _FACT_LISTS[short] = json.loads((EXP / f"rubrics/facts/{short}-facts.json").read_text(encoding="utf-8"))
    slots = _FACT_LISTS[short]
    got = {x["id"]: x["status"] for x in json.loads(Path(path).read_text(encoding="utf-8"))["facts"]}
    assert len(got) == len(slots), (str(path), len(got), len(slots))
    legacy = [x["id"] for x in slots if x.get("legacy")]
    return 100 * sum(1 for x in slots if got[x["id"]] == "对") / len(slots), 100 * sum(1 for i in legacy if got[i] == "对") / len(legacy)


_MASTER = None


def master() -> dict:
    """The run-level table (scripts/run_table.py on the dev box, then scripts/master_table.py): run id -> row. It has
    the same columns for every batch, read from the raw logs with one definition each."""
    global _MASTER
    if _MASTER is None:
        _MASTER = {r["id"]: r for r in R("results/master/runs.csv")}
    return _MASTER


def answer_s(r: dict):
    """Seconds from the start to the root's final answer (what the user waits for). The batches whose own table did
    not record it take it from the run-level table. The process duration is never used in its place: a process that
    waits for its subagents stays up after the answer, in some runs for the whole 20-minute cap."""
    v = num(r.get("answer_s"))
    if v and v > 0:
        return v
    m = master().get(r["id"])
    assert m is not None and m["t_answer_s"] != "", ("no time to the final answer for run", r.get("id"))
    return float(m["t_answer_s"])


def contrast(rows: list, a: str, b: str, get, kind: str = "diff", ok=lambda r: True) -> dict:
    """A against B computed from run rows with the method of paired_stats.py (pairs are (task, rep), the tasks
    weighted equally, t interval with the task effect removed). a or b may be "G1+G2": the mean of the groups."""
    parts = set(a.split("+")) | set(b.split("+"))
    conv = [{"task": r["task"], "group": r["group"], "rep": r["rep"], "m": get(r)} for r in rows if r["group"] in parts and ok(r)]
    dbt, _, _ = ps.paired(ps.index_rows([c for c in conv if c["m"] is not None]), a, b, "m", "ratio" if kind == "ratio" else "diff")
    ti = ps.t_interval(dbt)
    f = math.exp if kind == "ratio" else (lambda v: v)
    return {"est": f(ti["est"]), "lo": f(ti["lo"]), "hi": f(ti["hi"]), "n": ti["n"], "p": None, "holm": None, "ratio": kind == "ratio", "a": a, "b": b}


def contrast_tasks(rows: list, a: str, b: str, get, kind: str = "diff") -> dict:
    """A against B with the task as the pair (one run per task and group; the interval of ws_stats.py: paired t, df = pairs - 1)."""
    from scipy import stats as sps
    by = {(r["task"], r["group"]): get(r) for r in rows if r["group"] in (a, b) and get(r) is not None}
    d = [(math.log(by[(t, a)] / by[(t, b)]) if kind == "ratio" else by[(t, a)] - by[(t, b)]) for (t, g) in sorted(by) if g == a and (t, b) in by]
    m, half = st.mean(d), sps.t.ppf(0.975, len(d) - 1) * st.stdev(d) / math.sqrt(len(d))
    f = math.exp if kind == "ratio" else (lambda v: v)
    return {"est": f(m), "lo": f(m - half), "hi": f(m + half), "n": len(d), "p": None, "holm": None, "ratio": kind == "ratio", "a": a, "b": b}


def pooled(strata: dict, ratio: bool = False) -> dict:
    """Pairs of several batches together: mean of the pair differences, deviations taken inside each (batch, task)."""
    x = dal.tci(strata)
    f = math.exp if ratio else (lambda v: v)
    return {"est": f(x["est"]), "lo": f(x["lo"]), "hi": f(x["hi"]), "n": x["n"], "p": x["p"], "holm": None, "ratio": ratio}


def opens(rows: list, group: str, task: str | None = None) -> dict:
    """How many runs of the group delegated at all, and how many subagents were alive at once at most."""
    v = [r for r in rows if r["group"] == group and (task is None or r["task"] == task)]
    peak = [num(r.get("slot_peak")) or 0 for r in v]
    cap = [num(r.get("capacity_rejects")) or 0 for r in v]
    dep = [num(r.get("depth_rejects")) or 0 for r in v]
    return {"runs": len(v), "open": sum(1 for r in v if (num(r.get("children")) or 0) > 0), "over4": sum(1 for q in peak if q > 4),
            "peak_max": max(peak) if peak else 0, "at_most4": sum(1 for q in peak if q <= 4), "peaks": sorted(peak),
            "cap_runs": sum(1 for q in cap if q > 0), "cap_total": int(sum(cap)), "depth_runs": sum(1 for q in dep if q > 0), "depth_total": int(sum(dep))}


def paired_means(rows: list, a: str, b: str, col: str, block=lambda r: (r["task"], r["rep"]), ok=lambda r: True) -> dict:
    """Means of a column over the blocks that have both groups, and their ratio (the 'ratio of the two means')."""
    by = {(block(r), r["group"]): num(r.get(col)) for r in rows if ok(r) and num(r.get(col)) is not None}
    bl = sorted(k[0] for k in by if k[1] == a and (k[0], b) in by)
    xa, xb = [by[(k, a)] for k in bl], [by[(k, b)] for k in bl]
    return {"a": st.mean(xa), "b": st.mean(xb), "ratio": st.mean(xa) / st.mean(xb), "n": len(bl)}


# ---------------------------------------------------------------------------------------------- office research
def office() -> dict:
    A = "results/analysis-facts-confirm"
    cs = J(f"{A}/stats.json")
    gm = {r["group"]: r for r in R(f"{A}/group-means.csv")}
    groups = ["D0", "D1-K1", "D1-K2", "D1-K4", "D1-K8", "D2-K8"]
    out = {"groups": groups, "runs": sum(int(gm[g]["n_runs"]) for g in groups), "judged": sum(int(gm[g]["n_judged"]) for g in groups)}
    out["means"] = {g: {"right_pct": num(gm[g]["right_pct"]), "right_n": num(gm[g]["right_n"]), "wrong": num(gm[g]["wrong_firm_n"]),
                        "cost": num(gm[g]["total_cost_peak"]), "minutes": num(gm[g]["seconds"]) / 60, "kids": num(gm[g]["children"]),
                        "search": num(gm[g]["search_aux"]), "chars": num(gm[g]["deliv_chars"]), "n": int(gm[g]["n_judged"])} for g in groups}
    rows = [r for r in R("results/analysis-office-confirm/rows-all.csv") if complete(r)]
    for g in groups:
        out["means"][g]["model_cost"] = means(rows, g, "model_cost_peak")
        out["means"][g]["minutes"] = means(rows, g, lambda r: answer_s(r) / 60)  # to the final answer, like every other time in the report
    lab = {"D0": "H1", "D1-K1": "K1", "D1-K2": "K2", "D1-K4": "K4", "D2-K8": "DN"}
    out["cmp"] = {}
    for g, k in lab.items():
        d = {m: comp(cs, m, k) for m in ("right_pct", "right_n", "right_legacy_pct", "total_cost_peak", "seconds", "wrong_firm_n", "deliv_chars", "search_aux")}
        if g == "D0":  # the file holds default - none; the table wants every column against the default
            d = {m: flip(c) for m, c in d.items()}
        out["cmp"][g] = d
    out["h1"] = {m: comp(cs, m, "H1") for m in ("right_pct", "right_n", "right_legacy_pct", "total_cost_peak", "seconds", "deliv_chars", "search_aux")}
    # time to the final answer (the batch's own statistics hold the process duration, about 2 seconds longer)
    for g in lab:
        out["cmp"][g]["seconds"] = contrast(rows, g, "D1-K8", answer_s, "ratio")
    out["h1"]["seconds"] = contrast(rows, "D1-K8", "D0", answer_s, "ratio")
    # the two tasks separately (descriptive in the analysis files)
    out["by_task"] = {}
    for t, f in (("o1", "stats-o1-singapore-trip.json"), ("o2", "stats-o2-server-cpu-report.json")):
        s = J(f"{A}/{f}")
        out["by_task"][t] = {k: comp(s, "right_pct", k) for k in ("H1", "K1", "K2", "K4", "DN")}
    # the same contrast in the other batches that have it
    fs = J("results/analysis-facts/stats-facts.json")
    fl = J("results/analysis-facts-floor/stats.json")
    out["h1_reps"] = [dict(comp(fs, "right_pct", "H1"), name="formal"), dict(comp(cs, "right_pct", "H1"), name="confirm"), dict(comp(fl, "right_pct", "H1"), name="floor")]
    out["h1_legacy"] = [dict(comp(fs, "right_legacy_pct", "H1"), name="formal"), dict(comp(cs, "right_legacy_pct", "H1"), name="confirm")]
    DOSE = "results/analysis-facts-dose"
    dose_s = J(f"{DOSE}/stats.json") if (EXP / DOSE / "stats.json").exists() else None
    if dose_s:  # the two-dose batch has the same contrast (default against no subagents) once more
        out["h1_reps"].append(dict(comp(dose_s, "right_pct", "H1"), name="dose"))
        out["h1_legacy"].append(dict(comp(dose_s, "right_legacy_pct", "H1"), name="dose"))
    out["k1_reps"] = [dict(comp(fs, "right_pct", "H2a"), name="formal"), dict(comp(cs, "right_pct", "K1"), name="confirm")]
    out["h1_cost"] = {"formal": paired_means([r for r in R("results/analysis-v2/rows-office.csv") if complete(r)], "D1-K8", "D0", "total_cost_peak"),
                      "confirm": paired_means(rows, "D1-K8", "D0", "total_cost_peak"),
                      "floor": paired_means([r for r in R("results/analysis-office-floor/rows-all.csv") if complete(r)], "D1-K8", "D0", "total_cost_peak")}
    out["h1_cost_geo"] = {"confirm": comp(cs, "total_cost_peak", "H1"), "floor": comp(fl, "total_cost_peak", "H1")}
    # by task in the three batches (delegation)
    out["h1_by_task"] = {}
    for name, f1, f2 in (("formal", "results/analysis-facts/stats-facts-o1-singapore-trip.json", "results/analysis-facts/stats-facts-o2-server-cpu-report.json"),
                         ("confirm", f"{A}/stats-o1-singapore-trip.json", f"{A}/stats-o2-server-cpu-report.json"),
                         ("floor", "results/analysis-facts-floor/stats-o1-singapore-trip.json", "results/analysis-facts-floor/stats-o2-server-cpu-report.json")):
        out["h1_by_task"][name] = {"o1": comp(J(f1), "right_pct", "H1"), "o2": comp(J(f2), "right_pct", "H1")}
    if dose_s:
        out["h1_by_task"]["dose"] = {"o1": comp(J(f"{DOSE}/stats-o1-singapore-trip.json"), "right_pct", "H1"), "o2": comp(J(f"{DOSE}/stats-o2-server-cpu-report.json"), "right_pct", "H1")}
    # the same contrast on the 63 items fixed beforehand, task by task (from the run rows, the method of paired_stats.py)
    out["h1_legacy_by_task"] = {}
    for name, rp, fp in (("formal", "results/analysis-v2/rows-office.csv", "results/analysis-facts/fact-rows.csv"), ("confirm", "results/analysis-office-confirm/rows-all.csv", f"{A}/fact-rows.csv"),
                         ("floor", "results/analysis-office-floor/rows-all.csv", "results/analysis-facts-floor/fact-rows.csv"), ("dose", "results/analysis-office-dose/rows-all.csv", f"{DOSE}/fact-rows.csv")):
        if not (EXP / fp).exists():
            continue
        fx = {r["id"]: r for r in R(fp)}
        rr = [r for r in R(rp) if r["id"] in fx and complete(r) and r["task"].startswith("o")]
        out["h1_legacy_by_task"][name] = {t_[:2]: contrast([r for r in rr if r["task"] == t_], "D1-K8", "D0", lambda r: num(fx[r["id"]]["right_legacy_pct"])) for t_ in sorted({r["task"] for r in rr})}
        both = contrast(rr, "D1-K8", "D0", lambda r: num(fx[r["id"]]["right_pct"]))
        assert abs(both["est"] - next(q for q in out["h1_reps"] if q["name"] == name)["est"]) < 1e-6, name  # the same pairs as the batch's own statistics
    # marginal price of one more fact stated correctly (yuan per fact), between neighbouring settings of the confirmation batch
    m = out["means"]
    step = lambda a, b: (m[b]["cost"] - m[a]["cost"]) / (m[b]["right_n"] - m[a]["right_n"])  # noqa: E731
    out["per_fact"] = {"none_default": step("D0", "D1-K8"), "k1_default": step("D1-K1", "D1-K8"), "default_d2": step("D1-K8", "D2-K8"),
                       "none_k1": step("D0", "D1-K1"), "k1_k2": step("D1-K1", "D1-K2"), "k2_k4": step("D1-K2", "D1-K4")}
    # the price of depth 2 if the gain were as large as the upper end of the pooled interval
    da = J("results/analysis-depth-all/depth-all.json")
    out["depth_rows"] = da["rows"]
    out["depth_pooled"] = da["pooled"]
    extra = m["D2-K8"]["cost"] - m["D1-K8"]["cost"]
    out["per_fact"]["default_d2_at_upper"] = extra / (da["pooled"]["2"]["hi"] * SLOTS / 100)
    out["per_fact"]["default_d2_at_pooled"] = extra / (da["pooled"]["2"]["est"] * SLOTS / 100)
    # K = 64 at depth 1 (20 pairs)
    hk = J("results/analysis-facts-highk/stats.json")
    out["k64"] = {m_: comp(hk, m_, "H1") for m_ in ("right_pct", "total_cost_peak", "children", "search_aux", "seconds")}
    out["k64_d2"] = {m_: comp(hk, m_, "H2") for m_ in ("right_pct", "total_cost_peak", "children", "search_aux", "answer_s", "seconds")}
    out["k64_d3"] = {m_: comp(hk, m_, "H3") for m_ in ("right_pct", "total_cost_peak", "children", "search_aux", "answer_s", "seconds")}
    w2 = J("results/analysis-facts-wait2/stats.json")
    out["wait"] = {k: {m_: comp(w2, m_, k) for m_ in ("right_pct", "total_cost_peak")} for k in ("WD2", "WD3", "N2", "N3")}
    fn = J("results/analysis-facts-floor/stats-noopen.json")  # the same batch without the runs that ended while subagents were still working
    out["keep_done"] = {m_: comp(fn, m_, "KA") for m_ in ("right_pct", "total_cost_peak", "seconds", "deliv_chars", "search_aux")}
    # single agent told to search more; merged single-agent reports (the batch of 160 runs)
    out["floor"] = {k: {m_: comp(fl, m_, k) for m_ in ("right_pct", "total_cost_peak", "seconds", "search_aux", "deliv_chars", "wrong_firm_n")} for k in ("PRIM", "EF", "H1", "KA")}
    frows = [r for r in R("results/analysis-office-floor/rows-all.csv")]
    ff = {r["id"]: r for r in R("results/analysis-facts-floor/fact-rows.csv")}
    ov = {r["id"]: r for r in R("results/analysis-office-floor/search-overlap.csv")}
    fgroups = ["D0", "E-D0", "D1-K8", "N-D1-K8"]
    judged = [dict(r, **{k: ff[r["id"]][k] for k in ("right_pct", "right_n", "wrong_firm_n")}, pages=ov.get(r["id"], {}).get("pages_distinct")) for r in frows if r["id"] in ff and complete(r)]
    out["floor_means"] = {g: {"right_pct": means(judged, g, "right_pct"), "right_n": means(judged, g, "right_n"), "cost": means(judged, g, "total_cost_peak"),
                              "minutes": means(judged, g, lambda r: num(r["seconds"]) / 60), "search": means(judged, g, "search_aux"), "pages": means(judged, g, "pages"),
                              "chars": means(judged, g, "deliv_chars"), "kids": means(judged, g, "children"), "n": count(judged, g), "runs": count(frows, g)} for g in fgroups}
    ms = J("results/analysis-office-merge-b/merge-stats.json")
    out["merge_raw"] = ms
    idx = J("tasks/merge-b-index.json")
    src = {r["id"]: r for r in frows}
    tot = {}
    for r in ms["rows"]:
        tot.setdefault(r["kind"], []).append(sum(num(src[i]["search_aux"]) for i in idx[r["task"]]["inputs"]) + r["merge_search"])
    out["merge_search"] = {k_: st.mean(v) for k_, v in tot.items()}
    # depth 3 with 64 slots: the limit on the number alive was never reached, so this group is the old default
    hrows = [r for r in R("results/analysis-office-highk/rows-all.csv") if complete(r)]
    wrows = [r for r in R("results/analysis-wait/rows.csv") if complete(r)]
    g3 = [r for r in hrows if r["group"] == "W-D3-K64"]
    l3 = [num(r.get("children_d3")) or 0 for r in g3]
    out["old_default"] = {"facts": comp(hk, "right_pct", "H3"), "cost": comp(hk, "total_cost_peak", "H3"), "time": comp(hk, "answer_s", "H3"),
                          "seconds": comp(hk, "seconds", "H3"), "l3_runs": sum(1 for q in l3 if q > 0), "l3_mean": st.mean(l3), "runs": len(g3),
                          "kids": means(hrows, "W-D3-K64", "children"), "kids_default": means(hrows, "W-D1-K8", "children"),
                          "kids_max": max(num(r["children"]) for r in g3), "cap_rejects": sum(num(r.get("capacity_rejects")) or 0 for r in g3),
                          "levels": [means(hrows, "W-D3-K64", c) for c in ("children_d1", "children_d2", "children_d3")],
                          "yuan": means(hrows, "W-D3-K64", "total_cost_peak"), "yuan_default": means(hrows, "W-D1-K8", "total_cost_peak")}
    out["k64"]["answer_s"] = comp(hk, "answer_s", "H1")
    out["wait"]["WD3"]["seconds"] = comp(w2, "seconds", "WD3")
    out["other_kids"] = {"k64": means(hrows, "W-D1-K64", "children"), "d2k64": means(hrows, "W-D2-K64", "children"), "d3k64": means(hrows, "W-D3-K64", "children"),
                         "d3": means(wrows, "W-D3-K8", "children")}
    out["k64_caps"] = sum(num(r.get("capacity_rejects")) or 0 for r in hrows if r["group"] in ("W-D1-K8", "W-D1-K64"))
    # the batch with K = 64 has two depth-1 groups that behave alike (the limit of 8 is never reached at depth 1): the
    # contrasts written down beforehand use the K = 8 one; here also against the mean of the two
    hf = {r["id"]: r for r in R("results/analysis-facts-highk/fact-rows.csv")}
    hj = [r for r in hrows if r["id"] in hf]
    share = lambda r: num(hf[r["id"]]["right_pct"])  # noqa: E731
    out["both_base"] = {g: {"facts": contrast(hj, g, "W-D1-K8+W-D1-K64", share), "facts_k64": contrast(hj, g, "W-D1-K64", share),
                            "cost": contrast(hj, g, "W-D1-K8+W-D1-K64", lambda r: num(r["total_cost_peak"]), "ratio")} for g in ("W-D2-K64", "W-D3-K64")}
    assert abs(contrast(hj, "W-D3-K64", "W-D1-K8", share)["est"] - out["old_default"]["facts"]["est"]) < 1e-6  # same method as the batch's own statistics
    out["old_default"]["answer"] = comp(hk, "answer_s", "H3")
    out["old_default"]["stuck"] = {g: sum(1 for r in hrows if r["group"] == g and (num(r["seconds"]) - num(r["answer_s"])) > 60) for g in ("W-D2-K64", "W-D3-K64")}
    # merged reports: the two batches of the same design, each against the default of its own blocks, pooled
    mp = {}
    for batch, path, index, mbatch, src_rows, same_place, src_judge in (
            ("a", "results/analysis-office-merge/merge-stats.json", "tasks/merge-index.json", "office-merge", "results/analysis-office-confirm/rows-all.csv",
             "results/judge-facts/office-confirm-hgcheck", "results/judge-facts/office-confirm"),
            ("b", "results/analysis-office-merge-b/merge-stats.json", "tasks/merge-b-index.json", "office-merge-b", "results/analysis-office-floor/rows-all.csv",
             "results/judge-facts/office-floor", "results/judge-facts/office-floor")):
        mix = J(index)
        by_place = {(r["task"], r["group"], int(r["rep"])): r for r in R(src_rows)}
        for r in J(path)["rows"]:
            if r.get("D1-K8_right_pct") is None:
                continue
            e = mp.setdefault(r["kind"], {"facts": {}, "legacy": {}, "cost": {}, "time": {}})
            key = (batch, r["base_task"])
            ref = r.get("D1-K8_right_pct_hg", r["D1-K8_right_pct"])  # comparator as judged in the same place
            e["facts"].setdefault(key, []).append(r["merged_right_pct"] - ref)
            e["cost"].setdefault(key, []).append(math.log(r["total_cost"] / r["D1-K8_cost"]))
            e["time"].setdefault(key, []).append(math.log(r["total_seconds_parallel"] / r["D1-K8_seconds"]))
            # the same difference on the items fixed beforehand: this merged report and the same comparator reports, from the judge files
            mi = mix[r["task"]]
            runs = [by_place[(mi["base_task"], "D1-K8", q)] for q in mi["reps"] if (mi["base_task"], "D1-K8", q) in by_place]
            files = [EXP / same_place / f"{q['id']}.f1.json" for q in runs]
            if not all(q.exists() for q in files):
                files = [EXP / src_judge / f"{q['id']}.f1.json" for q in runs]
            theirs = [fact_shares(q, mi["base_task"]) for q in files if q.exists()]
            mine = fact_shares(EXP / f"results/judge-facts/{mbatch}/{r['run']}.f1.json", mi["base_task"])
            assert abs(mine[0] - r["merged_right_pct"]) < 0.01 and abs(st.mean(q[0] for q in theirs) - ref) < 0.02, (batch, r["task"])
            e["legacy"].setdefault(key, []).append(mine[1] - st.mean(q[1] for q in theirs))
    out["merge_pooled"] = {k_: {"facts": pooled(v["facts"]), "legacy": pooled(v["legacy"]), "cost": pooled(v["cost"], True), "time": pooled(v["time"], True),
                                "by_batch": {b_: st.mean(st.mean(x) for kk, x in v["facts"].items() if kk[0] == b_) for b_ in ("a", "b")},
                                "batch": {b_: pooled({kk: x for kk, x in v["facts"].items() if kk[0] == b_}) for b_ in ("a", "b")},
                                "batch_legacy": {b_: pooled({kk: x for kk, x in v["legacy"].items() if kk[0] == b_}) for b_ in ("a", "b")}} for k_, v in mp.items()}
    strata = {}
    for r in J("results/analysis-office-merge-b/merge-stats.json")["rows"]:
        if r["kind"] == "M2" and r.get("N-D1-K8_right_pct") is not None:
            strata.setdefault(("b", r["base_task"]), []).append(r["merged_right_pct"] - r.get("N-D1-K8_right_pct_hg", r["N-D1-K8_right_pct"]))
    out["m2_vs_keep"] = pooled(strata)
    strata4 = {}
    for r in J("results/analysis-office-merge-b/merge-stats.json")["rows"]:
        if r["kind"] == "M4" and r.get("N-D1-K8_right_pct") is not None:
            strata4.setdefault(("b", r["base_task"]), []).append(r["merged_right_pct"] - r.get("N-D1-K8_right_pct_hg", r["N-D1-K8_right_pct"]))
    out["m4_vs_keep"] = pooled(strata4)
    # contrasts on the items fixed beforehand that the batches' own statistics do not carry, from the run rows with the same method
    leg_f = lambda r: num(ff[r["id"]]["right_legacy_pct"])  # noqa: E731
    all_f = lambda r: num(ff[r["id"]]["right_pct"])  # noqa: E731
    leg_h = lambda r: num(hf[r["id"]]["right_legacy_pct"])  # noqa: E731
    col = lambda name: (lambda r: num(r[name]))  # noqa: E731
    done = lambda r: (num(r.get("open_children_at_end")) or 0) == 0  # noqa: E731  (the run did not end while subagents were still working)
    out["floor_none"] = {"right_pct": contrast(judged, "D0", "D1-K8", all_f), "legacy": contrast(judged, "D0", "D1-K8", leg_f),
                         "search_aux": contrast(judged, "D0", "D1-K8", col("search_aux"), "ratio"), "total_cost_peak": contrast(judged, "D0", "D1-K8", col("total_cost_peak"), "ratio"),
                         "seconds": contrast(judged, "D0", "D1-K8", answer_s, "ratio")}
    out["keep_done"]["seconds"] = contrast(judged, "N-D1-K8", "D1-K8", answer_s, "ratio", ok=done)  # to the final answer, like every other time of the report
    out["legacy"] = {"more": contrast(judged, "E-D0", "D1-K8", leg_f), "more_vs_none": contrast(judged, "E-D0", "D0", leg_f),
                     "keep_done": contrast(judged, "N-D1-K8", "D1-K8", leg_f, ok=done),
                     "k64": contrast(hj, "W-D1-K64", "W-D1-K8", leg_h), "old": contrast(hj, "W-D3-K64", "W-D1-K8", leg_h),
                     "d2k64": contrast(hj, "W-D2-K64", "W-D1-K8", leg_h)}
    wf = {r["id"]: r for r in R("results/analysis-facts-wait2/fact-rows.csv")}
    wj = [r for r in wrows if r["id"] in wf]
    out["legacy"]["d3k8"] = contrast(wj, "W-D3-K8", "W-D1-K8", lambda r: num(wf[r["id"]]["right_legacy_pct"]))
    assert abs(contrast(wj, "W-D3-K8", "W-D1-K8", lambda r: num(wf[r["id"]]["right_pct"]))["est"] - out["wait"]["WD3"]["right_pct"]["est"]) < 1e-6
    assert abs(out["floor_none"]["right_pct"]["est"] + out["floor"]["H1"]["right_pct"]["est"]) < 1e-6  # the same pairs as the batch's own statistics
    assert abs(contrast(judged, "E-D0", "D1-K8", all_f)["est"] - out["floor"]["PRIM"]["right_pct"]["est"]) < 1e-6
    assert abs(contrast(judged, "N-D1-K8", "D1-K8", all_f, ok=done)["est"] - out["keep_done"]["right_pct"]["est"]) < 1e-6
    # both batches of merged reports as points of the figure of search volume: (kind, batch) -> (search requests, % right)
    mpts = {}
    for batch, path, index, src_rows in (("a", "results/analysis-office-merge/merge-stats.json", "tasks/merge-index.json", "results/analysis-office-confirm/rows-all.csv"),
                                        ("b", "results/analysis-office-merge-b/merge-stats.json", "tasks/merge-b-index.json", "results/analysis-office-floor/rows-all.csv")):
        mix, by_id = J(index), {r["id"]: r for r in R(src_rows)}
        for r in J(path)["rows"]:
            mpts.setdefault((r["kind"], batch), []).append((sum(num(by_id[i]["search_aux"]) for i in mix[r["task"]]["inputs"]) + r["merge_search"], r["merged_right_pct"]))
    out["merge_points"] = [{"kind": k_[0], "batch": k_[1], "search": st.mean(q[0] for q in v), "right_pct": st.mean(q[1] for q in v), "n": len(v)} for k_, v in sorted(mpts.items())]
    out["keep_all_runs"] = dict(J("results/analysis-facts-floor/extra.json")["keep_all_every_run"])
    ctx = J("results/analysis-office-floor/ctx-peak.json")["rows"]
    out["ctx_floor"] = {g: {"max": max(r["peak"] for r in ctx if r["group"] == g), "over": sum(1 for r in ctx if r["group"] == g and r["peak"] > 500000),
                            "pruned": sum(1 for r in ctx if r["group"] == g and r.get("compact"))} for g in sorted({r["group"] for r in ctx})}
    more_runs = [r for r in judged if r["group"] == "E-D0"]
    out["floor_more"] = {"n": len(more_runs), "over200": sum(1 for r in more_runs if num(r["search_aux"]) >= 200),
                         "ctx_median": st.median(r["peak"] for r in ctx if r["group"] == "E-D0" and r["depth"] == 0)}
    out["d2_open_at_end"] = sum(1 for r in rows if r["group"] == "D2-K8" and (num(r.get("open_children_at_end")) or 0) > 0)
    # subagents per level under each setting (mean per run): how far the model goes when the limits let it
    lev = lambda rows_, g: [means(rows_, g, c_) or 0.0 for c_ in ("children_d1", "children_d2", "children_d3")]  # noqa: E731
    out["levels"] = [("深度 1、K=8（默认）", lev(rows, "D1-K8")), ("深度 1、K=64", lev(hrows, "W-D1-K64")), ("深度 2、K=8", lev(rows, "D2-K8")),
                     ("深度 2、K=64", lev(hrows, "W-D2-K64")), ("深度 3、K=8", lev(wrows, "W-D3-K8")), ("深度 3、K=64（相当于旧默认）", lev(hrows, "W-D3-K64"))]
    # search requests of the merged reports (inputs plus the merge step) relative to the default of the same batch
    ratios = {}
    for index, stats_path, src_rows, base in (
            ("tasks/merge-index.json", "results/analysis-office-merge/merge-stats.json", rows, means(rows, "D1-K8", "search_aux")),
            ("tasks/merge-b-index.json", "results/analysis-office-merge-b/merge-stats.json", frows, out["floor_means"]["D1-K8"]["search"])):
        ix = J(index)
        by_id = {r["id"]: r for r in src_rows}
        tot_ = {}
        for r in J(stats_path)["rows"]:
            tot_.setdefault(r["kind"], []).append(sum(num(by_id[i]["search_aux"]) for i in ix[r["task"]]["inputs"]) + r["merge_search"])
        for k_, v in tot_.items():
            ratios.setdefault(k_, []).append(st.mean(v) / base)
    out["merge_search_ratio"] = {k_: st.mean(v) for k_, v in ratios.items()}
    out["second"] = {"formal": J("results/analysis-facts/second-pass.json"), "confirm": J("results/analysis-facts-confirm/second-pass.json")}
    out["levels_wait_d2"] = lev(wrows, "W-D2-K8")  # depth 2, K = 8 in the batch whose processes wait for the subagents
    cf = {r["id"]: r for r in R(f"{A}/fact-rows.csv")}
    cj = [r for r in rows if r["id"] in cf]
    out["new_items"] = {"H1": contrast(cj, "D1-K8", "D0", lambda r: num(cf[r["id"]]["right_new_pct"])), "K1": contrast(cj, "D1-K1", "D1-K8", lambda r: num(cf[r["id"]]["right_new_pct"]))}
    assert abs(contrast(cj, "D1-K8", "D0", lambda r: num(cf[r["id"]]["right_pct"]))["est"] - out["h1"]["right_pct"]["est"]) < 1e-6
    sample = [r for r in R("results/analysis-facts/fact-rows.csv") if str(r.get("sample")).lower() in ("1", "true")]
    out["samples"] = {"n": len(sample), "none": sum(1 for r in sample if r["group"] == "D0"), "tasks": len({r["task"] for r in sample})}

    def counts(g, col):
        v = [num(r.get(col)) or 0 for r in rows if r["group"] == g]
        return {"runs": len(v), "hit": sum(1 for q in v if q > 0), "total": int(sum(v))}
    out["behavior"] = {g: {"cap": counts(g, "capacity_rejects"), "depth": counts(g, "depth_rejects")} for g in groups}
    out["opens"] = {g: opens(rows, g) for g in groups}
    # the level of the default group in every batch that has it (same prompt): how much one group moves between batches
    out["default_levels"] = {"formal": fs["metrics"]["right_pct"]["groups"]["D1-K8"]["est"], "confirm": m["D1-K8"]["right_pct"], "floor": out["floor_means"]["D1-K8"]["right_pct"],
                             "highk": hk["metrics"]["right_pct"]["groups"]["W-D1-K8"]["est"], "wait2": w2["metrics"]["right_pct"]["groups"]["W-D1-K8"]["est"]}
    if dose_s:
        out["default_levels"]["dose"] = dose_s["metrics"]["right_pct"]["groups"]["D1-K8"]["est"]
    return out


# ------------------------------------------------------------------------------------------------ rubric scores
def rubric() -> dict:
    """The original rubric score of the office reports (first batch): total and the four categories."""
    s = J("results/analysis-complete/stats-office.json")
    out = {"h1": comp(s, "score", "H1"), "groups": {g: v["est"] for g, v in s["metrics"]["score"]["groups"].items()}}
    for k in ("H2a", "H2b", "H2c", "H3a", "H3b"):
        if k in s["metrics"]["score"]["comparisons"]:
            out[k] = comp(s, "score", k)
    return out


# ------------------------------------------------------------------------------------------- code reading, p4
def code_read() -> dict:
    s = J("results/analysis-v2/stats-code-c1w1.json")
    fa = J("results/analysis-v2/stats-code-factorial-c1w1.json")
    rows = R("results/analysis-v2/rows-code-c1w1.csv")
    groups = ["D0", "D1-K8", "D2-K8", "D3-K8", "E-D1-K1", "E-D1-K2", "E-D1-K4", "E-D1-K8", "E-D2-K8", "E-D3-K8"]
    out = {"groups": groups, "runs": len(rows), "opens": opens(rows, "D1-K8"),
           "opens_task": {t: opens(rows, "D1-K8", t) for t in ("c1-subagent-limits", "w1-memory-plugin")}}
    out["means"] = {g: {"score": means(rows, g, "score"), "cost": means(rows, g, "model_cost_peak"), "minutes": means(rows, g, lambda r: num(r["seconds"]) / 60),
                        "kids": means(rows, g, "children"), "n": count(rows, g)} for g in groups}
    out["cmp"] = {k: {m: comp(s, m, k) for m in ("score", "model_cost_peak", "seconds")} for k in ("C1", "C2", "C3a", "C3b", "C3c", "C4a", "C4b", "N2", "N3")}
    s3 = J("results/analysis-v2/stats-code.json")  # c1, w1 and p4 together: the contrasts written down before the runs
    out["three"] = {k: {m: comp(s3, m, k) for m in ("score", "model_cost_peak", "seconds")} for k in ("C1", "C2", "C3a", "C3b", "C3c", "C4a", "C4b")}
    out["fact"] = {k: {m: comp(fa, m, k) for m in ("score", "model_cost_peak", "seconds")} for k in ("FK1", "FK2", "FK4", "FD2", "FD3", "FE")}
    # per task: who delegates without being told
    for t in ("c1-subagent-limits", "w1-memory-plugin"):
        tr = [r for r in rows if r["task"] == t]
        out[t[:2]] = {"kids_default": means(tr, "D1-K8", "children"), "spawn_runs": sum(1 for r in tr if r["group"] == "D1-K8" and (num(r.get("children")) or 0) > 0),
                      "runs_default": count(tr, "D1-K8")}
    p = J("results/analysis-v2/stats-code-p4-python.json")
    prow = [r for r in R("results/analysis-v2/rows-code.csv") if r["task"] == "p4-python"]
    out["p4"] = {"c1": {m: comp(p, m, "C1") for m in ("score", "model_cost_peak", "seconds")}, "c2": {m: comp(p, m, "C2") for m in ("score", "model_cost_peak", "seconds")},
                 "means": {g: {"score": means(prow, g, "score"), "cost": means(prow, g, "model_cost_peak"), "minutes": means(prow, g, lambda r: num(r["seconds"]) / 60),
                               "kids": means(prow, g, "children")} for g in ("D0", "D1-K8", "E-D1-K8")},
                 "lo": min(v["est"] for v in p["metrics"]["score"]["groups"].values()), "runs": len(prow), "opens": opens(prow, "D1-K8")}
    return out


# ---------------------------------------------------------------------------------------------- control tasks
def controls() -> dict:
    out = {}
    rows = R("results/analysis-ctl/rows.csv")
    for key, f, task in (("wide", "stats-pw-exercises.json", "pw-exercises"), ("chain", "stats-n1-chain16.json", "n1-chain16")):
        s = J(f"results/analysis-ctl/{f}")
        tr = [r for r in rows if r["task"] == task]
        solved = lambda r: (lambda m_: float(m_.group(1)) if m_ else None)(re.search(r"all_pass=(\d+)", r.get("score_detail") or ""))  # noqa: E731
        out[key] = {"solved": {g: means(tr, g, solved) for g in ("D0", "W-D1-K8", "W-E-D1-K8")}, "opens": opens(tr, "W-D1-K8"),
                    "cmp": {k: {m: comp(s, m, k) for m in ("score", "model_cost_peak", "seconds")} for k in ("NC", "PC", "EC")},
                    "means": {g: {"score": means(tr, g, "score"), "cost": means(tr, g, "model_cost_peak"), "minutes": means(tr, g, lambda r: answer_s(r) / 60),
                                  "kids": means(tr, g, "children"), "n": count(tr, g)} for g in ("D0", "W-D1-K8", "W-E-D1-K8")}}
        if key == "chain":  # time to the final answer; the batch's own statistics hold the process duration, which for the two waiting groups includes the wait at exit
            for k_, (a_, b_) in {"NC": ("W-D1-K8", "D0"), "PC": ("W-E-D1-K8", "D0"), "EC": ("W-E-D1-K8", "W-D1-K8")}.items():
                was = out[key]["cmp"][k_]["seconds"]
                now = contrast(tr, a_, b_, answer_s, "ratio")
                assert was["n"] == now["n"] and abs(math.log(was["est"] / now["est"])) < 0.12, (k_, was, now)
                out[key]["cmp"][k_]["seconds_process"] = was
                out[key]["cmp"][k_]["seconds"] = now
    return out


# ------------------------------------------------------------------------------------------- code-building tasks
def answer_min(r: dict):
    if r.get("no_answer") == "1" or r.get("final_event") == "0":
        return None
    v = num(r.get("answer_s"))
    return None if v is None else v / 60


def building() -> dict:
    fs = J("results/analysis-ctl-free-all/stats-pw-exercises-free.json")
    frows = R("results/analysis-ctl-free-all/rows.csv")
    fg = ["D0", "W-D1-K8"] + [f"W-E-D1-K{k}" for k in (1, 2, 4, 8, 16, 64)] + [f"W-E-D2-K{k}" for k in (4, 8, 16, 64)]
    free = {"groups": fg, "runs": len(frows),
            "means": {g: {"score": means(frows, g, "score"), "cost": means(frows, g, "model_cost_peak"), "answer": means(frows, g, answer_min),
                          "written": means(frows, g, lambda r: (num(r.get("all_written_s")) or 0) / 60 if num(r.get("all_written_s")) is not None else None),
                          "kids": means(frows, g, "children"), "review": means(frows, g, "children_after_all_written"), "n": count(frows, g),
                          "n_answer": sum(1 for r in frows if r["group"] == g and answer_min(r) is not None)} for g in fg},
            "cmp": {k: {m: comp(fs, m, k) for m in ("answer_s", "score", "model_cost_peak", "all_written_s")} for k in ("NC", "PC", "K1", "K2", "K4", "K16", "K64", "FD", "DK8")}}
    free["review_runs"] = {g: sum(1 for r in frows if r["group"] == g and (num(r.get("children_after_all_written")) or 0) > 0) for g in fg}
    free["opens"] = opens(frows, "W-D1-K8")
    def wave(g: str) -> dict:
        v = [r for r in frows if r["group"] == g and answer_min(r) is not None]
        late = [r for r in v if (num(r.get("children_after_all_written")) or 0) > 0]
        rest = [r for r in v if r not in late]
        d = lambda x: {"n": len(x), "answer": st.mean(answer_min(r) for r in x), "cost": st.mean(num(r["model_cost_peak"]) for r in x)} if x else {"n": 0}  # noqa: E731
        return {"late": d(late), "rest": d(rest)}
    free["wave"] = {g: wave(g) for g in ("D0", "W-D1-K8", "W-E-D1-K8")}
    xs = J("results/analysis-xl-main/stats.json")
    xrows = R("results/analysis-xl-main/rows-all.csv")
    xg = ["D0", "W-D1-K4", "W-D1-K8", "W-D1-K16", "W-D2-K8", "W-N-D1-K1", "W-N-D1-K2", "W-N-D1-K4", "W-N-D1-K8", "W-N-D1-K16", "W-N-D2-K8"]
    xl = {"groups": xg, "runs": len(xrows),
          "means": {g: {"score": means(xrows, g, "score"), "cost": means(xrows, g, "model_cost_peak"), "answer": means(xrows, g, answer_min),
                        "answer_median": st.median([v for v in (answer_min(r) for r in xrows if r["group"] == g) if v is not None]),
                        "written": means(xrows, g, lambda r: num(r.get("all_written_s")) / 60 if num(r.get("all_written_s")) is not None else None),
                        "kids": means(xrows, g, "children"), "review": means(xrows, g, "review_kids"), "n": count(xrows, g)} for g in xg},
          "cmp": {k: {m: comp(xs, m, k) for m in ("answer_s", "score", "model_cost_peak", "all_written_s")} for k in ("NC", "U", "K1", "K2", "K4", "K16", "NK4", "NK16", "DN", "DE", "S8")}}
    xl["review_runs"] = {g: sum(1 for r in xrows if r["group"] == g and (num(r.get("review_kids")) or 0) > 0) for g in xg}
    xl["opens"] = opens(xrows, "W-D1-K8")
    grade = [json.loads(ln) for ln in (EXP / "results/grade/xl-main/index.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    xl["tests"] = grade[0]["total"]
    assert all(x["total"] == xl["tests"] for x in grade)
    xl["failed"] = {g: st.mean(x["total"] - x["passed"] for x in grade if x["group"] == g) for g in xg}
    xl["all_pass_runs"] = {g: sum(1 for x in grade if x["group"] == g and x["passed"] == x["total"]) for g in xg}
    xl["failed_max"] = {g: max(x["total"] - x["passed"] for x in grade if x["group"] == g) for g in xg}
    ds = J("results/analysis-xl-depth/stats.json")
    xl["depth_hi"] = {k: {m: comp(ds, m, k) for m in ds["metrics"] if k in ds["metrics"][m]["comparisons"]} for k in ("DE16", "DE64")}
    return {"free": free, "xl": xl}


# ------------------------------------------------------------------------------------------ public benchmarks
def public() -> dict:
    out = {}
    w = J("results/analysis-ws-h1/stats.json")
    c = lambda s, m, k: dict(s["metrics"][m]["comparisons"][k])  # noqa: E731  (these files hold ratios as ratios)
    out["ws"] = {"groups": w["groups"], "cmp": {k: {m: c(w, m, k) for m in ("f1_item", "r_item", "p_item", "total_cost_peak", "minutes", "children")} for k in ("H1n", "H1e", "ENC")},
                 "flagged": len(w["inputs"]["flagged"]), "runs": w["inputs"]["n_rows"], "tasks": w["inputs"]["tasks"]}
    d = J("results/analysis-drb2-h1/stats.json")
    out["drb2"] = {"groups": d["groups"], "cmp": {"H1": {m: c(d, m, "H1") for m in ("total", "info_recall", "analysis", "presentation", "total_cost_peak", "minutes", "children")}},
                   "flagged": len(d["inputs"]["flagged"]), "runs": d["inputs"]["n_rows"], "tasks": d["inputs"]["tasks"]}
    k = J("results/analysis-drb2-kd/stats.json")
    out["drb2kd"] = {"groups": k["groups"], "cmp": {x: {m: c(k, m, x) for m in ("total", "info_recall", "total_cost_peak", "minutes", "children")} for x in ("K1", "D2")},
                     "flagged": len(k["inputs"]["flagged"]), "runs": k["inputs"]["n_rows"], "retest": J("results/analysis-drb2-kd/retest.json")}
    def pair_means(d: str, score_file: str, cols: list, flagged: list) -> dict:
        sc = {r["id"]: r for r in R(f"{d}/{score_file}")}
        rows = [dict(r, **{c_: sc[r["id"]].get(c_) for c_ in cols}) for r in R(f"{d}/rows-all.csv") if r["id"] not in set(flagged) and r["id"] in sc and num(sc[r["id"]].get(cols[0])) is not None]
        both = {t for t in {r["task"] for r in rows} if {"D0", "W-D1-K8"} <= {r["group"] for r in rows if r["task"] == t}}
        res = {"n": len(both)}
        for g in ("D0", "W-D1-K8"):
            v = [r for r in rows if r["group"] == g and r["task"] in both]
            mean = lambda f: st.mean(f(r) for r in v)  # noqa: E731
            res[g] = dict({c_: mean(lambda r, c_=c_: num(r[c_])) for c_ in cols}, cost=mean(lambda r: num(r["total_cost_peak"])), model=mean(lambda r: num(r["model_cost_peak"])),
                          minutes=mean(lambda r: num(r["seconds"]) / 60), kids=mean(lambda r: num(r["children"]) or 0), search=mean(lambda r: num(r["search_aux"]) or 0))
        return res
    out["ws"]["pair"] = pair_means("results/analysis-ws-h1", "ws-rows.csv", ["f1_item", "r_item", "p_item"], w["inputs"]["flagged"])
    out["drb2"]["pair"] = pair_means("results/analysis-drb2-h1", "drb2-rows.csv", ["total", "info_recall", "analysis", "presentation"], d["inputs"]["flagged"])
    wf, df_, kf = J("results/analysis-ws-h1/stats-with-flagged.json"), J("results/analysis-drb2-h1/stats-with-flagged.json"), J("results/analysis-drb2-kd/stats-with-flagged.json")
    out["with_flagged"] = {"ws_f1": c(wf, "f1_item", "H1n"), "ws_recall": c(wf, "r_item", "H1n"), "drb": c(df_, "total", "H1"), "kd_k1": c(kf, "total", "K1"), "kd_d2": c(kf, "total", "D2")}
    sel = J("results/analysis-ws-screen/selection.json")
    out["ws"]["screen"] = {"runs": sel["runs"], "picked": sel["n_picked"], "top": sum(1 for x in sel["tasks"] if "not below" in str(x.get("reason") or x.get("why") or "")),
                           "named": len(sel["flagged_runs"])}
    assert out["ws"]["screen"]["top"] + out["ws"]["screen"]["named"] + out["ws"]["screen"]["picked"] == out["ws"]["screen"]["runs"]
    def usable(d_: str, score_file: str, col: str, flagged: list) -> list:
        sc = {r["id"]: r for r in R(f"{d_}/{score_file}")}
        return [r for r in R(f"{d_}/rows-all.csv") if r["id"] not in set(flagged) and r["id"] in sc and num(sc[r["id"]].get(col)) is not None and complete(r)]
    am = lambda r: answer_s(r) / 60  # noqa: E731
    wu = usable("results/analysis-ws-h1", "ws-rows.csv", "f1_item", w["inputs"]["flagged"])
    du = usable("results/analysis-drb2-h1", "drb2-rows.csv", "total", d["inputs"]["flagged"])
    ku = usable("results/analysis-drb2-kd", "drb2-rows.csv", "total", k["inputs"]["flagged"])
    out["ws"]["time"] = {"H1n": contrast_tasks(wu, "W-D1-K8", "D0", am, "ratio")}
    out["drb2"]["time"] = {"H1": contrast_tasks(du, "W-D1-K8", "D0", am, "ratio")}
    out["drb2kd"]["time"] = {"K1": contrast_tasks(ku, "W-D1-K1", "W-D1-K8", am, "ratio"), "D2": contrast_tasks(ku, "W-D2-K8", "W-D1-K8", am, "ratio")}
    ksc = {r["id"]: r for r in R("results/analysis-drb2-kd/drb2-rows.csv")}
    kb = [r for r in ku if r["group"] == "W-D1-K8"]  # the default group of the batch that changed K and the depth
    out["drb2kd"]["base"] = {"total": st.mean(num(ksc[r["id"]]["total"]) for r in kb), "cost": st.mean(num(r["total_cost_peak"]) for r in kb),
                             "answer_minutes": st.mean(am(r) for r in kb), "n": len(kb)}
    for key, rows_, base in (("ws", wu, out["ws"]["pair"]), ("drb2", du, out["drb2"]["pair"])):
        both = {t for t in {r["task"] for r in rows_} if {"D0", "W-D1-K8"} <= {r["group"] for r in rows_ if r["task"] == t}}
        assert len(both) == base["n"], (key, len(both), base["n"])
        for g in ("D0", "W-D1-K8"):
            base[g]["answer_minutes"] = st.mean(am(r) for r in rows_ if r["group"] == g and r["task"] in both)
    out["ws"]["second"] = J("results/analysis-ws-h1/second-pass.json")
    out["drb2"]["second"] = J("results/analysis-drb2-h1/extra.json")["second"]
    out["ws"]["opens"] = opens(R("results/analysis-ws-h1/rows-all.csv"), "W-D1-K8")
    out["drb2"]["opens"] = opens(R("results/analysis-drb2-h1/rows-all.csv"), "W-D1-K8")
    # the two means on the scored pairs and their ratio (what the bill looks like), next to the per-pair ratio of the analysis
    def scored(path: str, flagged: list) -> list:
        return [r for r in R(path) if r["id"] not in set(flagged)]
    task_block = lambda r: r["task"]  # noqa: E731
    wr = scored("results/analysis-ws-h1/rows-all.csv", w["inputs"]["flagged"])
    out["ws"]["bill"] = {"H1n": paired_means(wr, "W-D1-K8", "D0", "total_cost_peak", task_block), "H1e": paired_means(wr, "W-E-D1-K8", "D0", "total_cost_peak", task_block)}
    dr = scored("results/analysis-drb2-h1/rows-all.csv", d["inputs"]["flagged"])
    out["drb2"]["bill"] = {"H1": paired_means(dr, "W-D1-K8", "D0", "total_cost_peak", task_block)}
    kr = scored("results/analysis-drb2-kd/rows-all.csv", k["inputs"]["flagged"])
    out["drb2kd"]["bill"] = {"K1": paired_means(kr, "W-D1-K1", "W-D1-K8", "total_cost_peak", task_block), "D2": paired_means(kr, "W-D2-K8", "W-D1-K8", "total_cost_peak", task_block)}
    # K = 4 on both benchmarks (and K = 1, depth 2 on the table-collection tasks): batches ws-k4 and drb2-k4, once analysed
    out["wsk"] = out["drbk"] = None
    if (EXP / "results/analysis-ws-k4/stats.json").exists() and (EXP / "results/analysis-drb2-k4/stats.json").exists():
        GROUP = {"K4": "W-D1-K4", "K1": "W-D1-K1", "D2": "W-D2-K8"}
        for key, d_, score_file, metric, names, cols in (
                ("wsk", "results/analysis-ws-k4", "ws-rows.csv", "f1_item", ("K4", "K1", "D2"), ("f1_item", "r_item", "p_item", "total_cost_peak", "minutes", "search_aux", "children")),
                ("drbk", "results/analysis-drb2-k4", "drb2-rows.csv", "total", ("K4",), ("total", "info_recall", "total_cost_peak", "minutes", "search_aux", "children"))):
            s_ = J(f"{d_}/stats.json")
            sf = J(f"{d_}/stats-with-flagged.json")
            u = usable(d_, score_file, metric, s_["inputs"]["flagged"])
            sc_ = {r["id"]: r for r in R(f"{d_}/{score_file}")}
            allr = R(f"{d_}/rows-all.csv")
            base = [r for r in u if r["group"] == "W-D1-K8"]
            out[key] = {"groups": s_["groups"], "cmp": {x: {m: c(s_, m, x) for m in cols} for x in names}, "flagged": len(s_["inputs"]["flagged"]), "runs": s_["inputs"]["n_rows"],
                        "tasks": s_["inputs"]["tasks"], "metric": metric,
                        "time": {x: contrast_tasks(u, GROUP[x], "W-D1-K8", am, "ratio") for x in names},
                        "base": {"q": st.mean(num(sc_[r["id"]][metric]) for r in base), "cost": st.mean(num(r["total_cost_peak"]) for r in base), "answer_minutes": st.mean(am(r) for r in base), "n": len(base)},
                        "opens": {g: opens(allr, g) for g in ["W-D1-K8"] + [GROUP[x] for x in names]},
                        "with_flagged": {x: c(sf, metric, x) for x in names},
                        "incomplete": sum(1 for r in allr if not complete(r)), "timeouts": sum(1 for r in allr if str(r.get("timeout")) == "True"),
                        "crashes": sum(1 for r in allr if str(r.get("crash5063")).lower() in ("true", "1"))}
        # one Holm family over the two primary contrasts (K = 4 against K = 8 on each benchmark's main score)
        prim = sorted((("wsk", out["wsk"]["cmp"]["K4"]["f1_item"]), ("drbk", out["drbk"]["cmp"]["K4"]["total"])), key=lambda q: q[1]["p"])
        first = min(1.0, 2 * prim[0][1]["p"])
        prim[0][1]["holm"] = first
        prim[1][1]["holm"] = max(first, min(1.0, prim[1][1]["p"]))
    return out


def grid() -> dict:
    """The 24 independent exercises under a time limit (3 and 2 minutes), K and depth varied, with the encouraging sentence."""
    out = {}
    rows = R("results/analysis-ctl-dk/rows.csv")
    for key, f, task in (("m3", "stats-pw-exercises.json", "pw-exercises"), ("m2", "stats-pw-exercises-120.json", "pw-exercises-120")):
        s = J(f"results/analysis-ctl-dk/{f}")
        tr = [r for r in rows if r["task"] == task]
        out[key] = {"cmp": {k: comp(s, "score", k) for k in ("K1", "K2", "K4", "K16", "FD", "PC", "FK1", "FK2", "FK4", "FK16")},
                    "means": {g: means(tr, g, "score") for g in sorted({r["group"] for r in tr})}}
    out["runs"] = len(rows)
    return out


def issues() -> dict:
    """Counts behind the list of framework problems."""
    tr = lambda v: str(v).lower() in ("true", "1")  # noqa: E731
    rows = R("results/analysis-v2/rows.csv")
    crashed = [r for r in rows if tr(r.get("crash5063"))]
    depth_of = lambda g: int(g.replace("E-", "")[1]) if g != "D0" else 0  # noqa: E731
    xl = R("results/analysis-xl-main/rows-all.csv")
    un = R("results/analysis-xl-main/unsettled.csv")
    office_rows = R("results/analysis-v2/rows-office.csv")
    cap = lambda g: int(sum(num(r.get("capacity_rejects")) or 0 for r in office_rows if r["group"] == g))  # noqa: E731
    share = [(num(r["total_cost_peak"]) - num(r["model_cost_peak"])) / num(r["total_cost_peak"]) for r in office_rows if num(r.get("total_cost_peak"))]
    probe = J("results/search-cost-probe-main-office.json")
    answer = [x["usage"]["output_tokens"] * 8 / 1e6 / x["cost_cny_peak"] for x in probe["sample"]]  # output price: 8 yuan per million tokens
    every = ["results/analysis-v2/rows.csv", "results/analysis-ctl/rows.csv", "results/analysis-wait/rows.csv", "results/analysis-ctl-dk/rows.csv", "results/analysis-ctl-free-all/rows.csv",
             "results/analysis-xl-main/rows-all.csv", "results/analysis-xl-depth/rows-all.csv", "results/analysis-office-confirm/rows-all.csv", "results/analysis-office-highk/rows-all.csv",
             "results/analysis-office-floor/rows-all.csv", "results/analysis-office-keep-depth/rows-all.csv", "results/analysis-ws-screen/rows-all.csv", "results/analysis-ws-h1/rows-all.csv",
             "results/analysis-drb2-h1/rows-all.csv", "results/analysis-drb2-kd/rows-all.csv"]
    if (EXP / "results/analysis-facts-dose/stats.json").exists():  # the two-dose batch, once it has been analysed
        every.append("results/analysis-office-dose/rows-all.csv")
    if (EXP / "results/analysis-ws-k4/stats.json").exists() and (EXP / "results/analysis-drb2-k4/stats.json").exists():  # K = 4 on the public benchmarks
        every += ["results/analysis-ws-k4/rows-all.csv", "results/analysis-drb2-k4/rows-all.csv"]
    if (EXP / "results/analysis-facts-told/stats.json").exists():  # the limit written into the tool description
        every.append("results/analysis-office-told/rows-all.csv")
    allc = [r for f_ in every for r in R(f_) if tr(r.get("crash5063"))]
    deep = lambda g: "D2" in g or "D3" in g  # noqa: E731
    return {"search_share": 100 * st.median(share), "answer_share": 100 * st.median(answer), "probe_n": len(probe["sample"]), "search_price": probe["per_request_cny_peak"],
            "all_runs": sum(len(R(f_)) for f_ in every), "all_crashes": len(allc), "all_crashes_shallow": sum(1 for r in allc if not deep(r["group"])),
            "all_crashes_waiting": sum(1 for r in allc if r["group"].startswith("W-")),
            "runs": len(rows), "crashes": len(crashed), "crashes_depth1": sum(1 for r in crashed if depth_of(r["group"]) <= 1),
            "crashes_by_group": {g: sum(1 for r in crashed if r["group"] == g) for g in sorted({r["group"] for r in crashed})},
            "deep_office_runs": sum(1 for r in office_rows if r["group"] in ("D2-K8", "D3-K8")),
            "deep_office_crashes": sum(1 for r in crashed if r["group"] in ("D2-K8", "D3-K8") and r["task"].startswith("o")),
            "oom_runs": sum(1 for r in xl if (num(r.get("oom_kill")) or 0) > 0), "xl_runs": len(xl),
            "interrupted_pending": int(sum(num(r.get("interrupted_with_pending_inbox")) or 0 for r in un)), "unsettled": int(sum(num(r.get("unsettled")) or 0 for r in un)),
            "cap_d1k1": cap("D1-K1"), "cap_d2k4": cap("D2-K4")}


# ------------------------------------------------------------------------------------------- what one task costs
def valid_runs(d: str, score_file: str, metric: str) -> list:
    """Runs of a public-benchmark batch that count: scored, and not flagged for having found the benchmark."""
    flagged = set(J(f"{d}/stats.json")["inputs"]["flagged"])
    sc = {r["id"]: r for r in R(f"{d}/{score_file}")}
    return [dict(r, value=num(sc[r["id"]][metric])) for r in R(f"{d}/rows-all.csv") if r["id"] not in flagged and r["id"] in sc and num(sc[r["id"]].get(metric)) is not None]


def gain_against_behaviour(d: str, score_file: str, metric: str) -> dict:
    """Per question of a public set: the default's gain over no subagents against what the default run did (subagents
    opened, most alive at once) and against the score without subagents. Looked at afterwards."""
    by = {(r["task"], r["group"]): r for r in valid_runs(d, score_file, metric)}
    tasks = sorted(t for (t, g) in by if g == "D0" and (t, "W-D1-K8") in by)
    gain = [by[(t, "W-D1-K8")]["value"] - by[(t, "D0")]["value"] for t in tasks]

    def corr(a: list, b: list) -> float:
        ma, mb = st.mean(a), st.mean(b)
        return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    def band(r: float) -> list:  # Fisher's z, 95%
        z, se = math.atanh(r), 1 / math.sqrt(len(tasks) - 3)
        return [math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)]
    r_sub = corr(gain, [num(by[(t, "W-D1-K8")].get("children")) or 0 for t in tasks])
    return {"n": len(tasks), "r_subagents": r_sub, "ci_subagents": band(r_sub),
            "r_peak": corr(gain, [num(by[(t, "W-D1-K8")].get("slot_peak")) or 0 for t in tasks]), "r_base": corr(gain, [by[(t, "D0")]["value"] for t in tasks])}


def ols(columns: list, y: list) -> dict:
    """Least squares with an intercept: coefficients (intercept first), their standard errors, R2."""
    import numpy as np
    X = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in columns])
    yv = np.asarray(y, float)
    with np.errstate(all="ignore"):  # the BLAS of this machine raises spurious floating-point flags in matmul
        b, *_ = np.linalg.lstsq(X, yv, rcond=None)
        res = yv - X @ b
        cov = float(res @ res) / (len(yv) - X.shape[1]) * np.linalg.inv(X.T @ X)
    return {"b": [float(v) for v in b], "se": [float(v) for v in np.sqrt(np.diag(cov))], "r2": 1 - float(res @ res) / float((yv - yv.mean()) @ (yv - yv.mean())), "n": len(y)}


def cost() -> dict:
    """Yuan per run at the public peak price, search fee included where the task uses the web.
    Office tasks: every setting with its own runs (mean with the tasks weighted equally, median, the value 90% of the
    runs stay under, maximum) and the mean of the default group it was run with; the default over every batch.
    What the cost depends on: least squares of the cost on the number of subagents opened (office runs with the plain
    prompt of five batches; the package and the 24 exercises by what the subagents were opened for).
    The three user sessions of the background: results/analysis-clean/user-logs-cost.json (scripts/user_logs_cost.py)."""
    paths = {"main": "results/analysis-office-confirm/rows-all.csv", "first": "results/analysis-v2/rows-office.csv", "highk": "results/analysis-office-highk/rows-all.csv",
             "wait": "results/analysis-wait/rows.csv", "floor": "results/analysis-office-floor/rows-all.csv"}
    rows = {b: [r for r in R(f) if complete(r)] for b, f in paths.items()}
    total = lambda r: num(r["total_cost_peak"])  # noqa: E731
    kids = lambda r: num(r.get("children")) or 0.0  # noqa: E731

    def summary(rs: list) -> dict:
        v = sorted(total(r) for r in rs)
        te = lambda get: st.mean(st.mean(get(r) for r in rs if r["task"] == t) for t in sorted({r["task"] for r in rs}))  # noqa: E731
        return {"n": len(v), "mean": te(total), "median": st.median(v), "p90": v[math.ceil(0.9 * len(v)) - 1], "max": v[-1], "kids": te(kids),
                "search_share": te(lambda r: 1 - num(r["model_cost_peak"]) / total(r)), "runs": v}

    spec = [("none", "不开 subagent", "main", "D0", "D1-K8"), ("k1", "K=1", "main", "D1-K1", "D1-K8"), ("k2", "K=2", "main", "D1-K2", "D1-K8"),
            ("k4", "K=4", "main", "D1-K4", "D1-K8"), ("default", "默认（深度 1、K=8）", "main", "D1-K8", None), ("k64", "K=64", "highk", "W-D1-K64", "W-D1-K8"),
            ("d2", "深度 2", "main", "D2-K8", "D1-K8"), ("d3", "深度 3", "wait", "W-D3-K8", "W-D1-K8"),
            ("d2k64", "深度 2、K=64", "highk", "W-D2-K64", "W-D1-K8"), ("old", "深度 3、K=64（相当于旧默认）", "highk", "W-D3-K64", "W-D1-K8")]
    out = {"settings": []}
    for key, label, batch, g, base in spec:
        e = dict(summary([r for r in rows[batch] if r["group"] == g]), key=key, label=label, batch=batch, group=g)
        e["base_mean"] = summary([r for r in rows[batch] if r["group"] == base])["mean"] if base else None
        out["settings"].append(e)
    out["by_key"] = {e["key"]: e for e in out["settings"]}
    out["depth_k8"] = [summary([r for r in rows["wait"] if r["group"] == g]) for g in ("W-D1-K8", "W-D2-K8", "W-D3-K8")]  # one batch, depth 1 to 3
    dflt = [r for b in ("main", "first", "floor") for r in rows[b] if r["group"] == "D1-K8"] + [r for b in ("highk", "wait") for r in rows[b] if r["group"] == "W-D1-K8"]
    out["default_all"] = dict(summary(dflt), min=min(total(r) for r in dflt), r2_kids=ols([[kids(r) for r in dflt]], [total(r) for r in dflt])["r2"])
    out["default_batches"] = sorted(summary([r for r in rows[b] if r["group"] == g])["mean"] for b, g in (("main", "D1-K8"), ("first", "D1-K8"), ("floor", "D1-K8"), ("highk", "W-D1-K8"), ("wait", "W-D1-K8")))
    out["none_all"] = summary([r for b in ("main", "first", "floor") for r in rows[b] if r["group"] == "D0"])
    # the cost against the number of subagents: runs with the plain prompt (no sentence added) of the five batches
    plain = [dict(r, batch=b) for b in paths for r in rows[b] if not r["group"].replace("W-", "").startswith(("E-", "N-"))]
    y = [total(r) for r in plain]
    line = ols([[kids(r) for r in plain]], y)
    fit = {"n": line["n"], "intercept": line["b"][0], "per_subagent": line["b"][1], "se": line["se"][1], "r2": line["r2"],
           "model_part": ols([[kids(r) for r in plain]], [num(r["model_cost_peak"]) for r in plain])["b"][1],
           "by_task": {t[:2]: ols([[kids(r) for r in plain if r["task"] == t]], [total(r) for r in plain if r["task"] == t])["b"][1] for t in sorted({r["task"] for r in plain})},
           "by_level": ols([[num(r.get(c)) or 0 for r in plain] for c in ("children_d1", "children_d2", "children_d3")], y)["b"][1:]}
    sreq = [num(r["search_aux"]) for r in plain]
    fit["search_per_subagent"] = ols([[kids(r) for r in plain]], sreq)["b"][1]
    fit["r2_search"] = ols([sreq], y)["r2"]
    fit["r2_model_kids"] = ols([[kids(r) for r in plain]], [num(r["model_cost_peak"]) for r in plain])["r2"]
    fit["r2_model_search"] = ols([sreq], [num(r["model_cost_peak"]) for r in plain])["r2"]
    mk_, ms_ = st.mean(kids(r) for r in plain), st.mean(sreq)
    fit["corr_kids_search"] = (sum((kids(r) - mk_) * (s - ms_) for r, s in zip(plain, sreq))
                               / math.sqrt(sum((kids(r) - mk_) ** 2 for r in plain) * sum((s - ms_) ** 2 for s in sreq)))
    tags = sorted({(r["batch"], r["group"]) for r in plain})
    fit["r2_with_setting"] = ols([[kids(r) for r in plain]] + [[1.0 if (r["batch"], r["group"]) == g else 0.0 for r in plain] for g in tags[1:]], y)["r2"]
    dev = []
    for g in tags:
        v = [r for r in plain if (r["batch"], r["group"]) == g]
        mk, mc = st.mean(kids(r) for r in v), st.mean(total(r) for r in v)
        if mk > 0:
            dev.append(abs(mc / (fit["intercept"] + fit["per_subagent"] * mk) - 1))
    fit["max_group_gap"], fit["groups"] = max(dev), len(dev)
    fit["points"] = [(kids(r), total(r), "none" if r["group"] == "D0" else ("deep" if ("D2" in r["group"] or "D3" in r["group"]) else "d1")) for r in plain]
    out["fit"] = fit
    # code-building tasks: a subagent that writes code against one sent after the files are written
    xl = [r for r in R("results/analysis-xl-main/rows-all.csv") if num(r.get("model_cost_peak")) is not None]
    rev = [num(r.get("review_kids")) or 0 for r in xl]
    px = ols([[kids(r) - v for r, v in zip(xl, rev)], rev], [num(r["model_cost_peak"]) for r in xl])
    fr = [r for r in R("results/analysis-ctl-free-all/rows.csv") if num(r.get("model_cost_peak")) is not None]
    late = [num(r.get("children_after_all_written")) or 0 for r in fr]
    pf = ols([[kids(r) - v for r, v in zip(fr, late)], late], [num(r["model_cost_peak"]) for r in fr])
    out["code_fit"] = {"xl": {"write": px["b"][1], "review": px["b"][2], "se_write": px["se"][1], "se_review": px["se"][2], "r2": px["r2"], "n": px["n"], "intercept": px["b"][0]},
                       "free": {"write": pf["b"][1], "review": pf["b"][2], "se_write": pf["se"][1], "se_review": pf["se"][2], "r2": pf["r2"], "n": pf["n"], "intercept": pf["b"][0]},
                       "xl_points": [(kids(r), num(r["model_cost_peak"]), "none" if r["group"] == "D0" else ("plain" if "-N-" not in r["group"] else "noreview")) for r in xl]}
    # the cost of one more subagent, task by task: slope of the cost on the number opened, over every run of the task
    def per_sub(rs: list, col: str) -> dict:
        rs = [r for r in rs if num(r.get(col)) is not None]
        f = ols([[kids(r) for r in rs]], [num(r[col]) for r in rs])
        return {"slope": f["b"][1], "se": f["se"][1], "r2": f["r2"], "n": f["n"]}

    code = R("results/analysis-v2/rows-code-c1w1.csv")
    ctl = R("results/analysis-ctl/rows.csv")
    out["per_task"] = {"office": {"slope": fit["per_subagent"], "se": fit["se"], "r2": fit["r2"], "n": fit["n"]},
                       "ws": per_sub(valid_runs("results/analysis-ws-h1", "ws-rows.csv", "f1_item"), "total_cost_peak"),
                       "drb2": per_sub(valid_runs("results/analysis-drb2-h1", "drb2-rows.csv", "total") + valid_runs("results/analysis-drb2-kd", "drb2-rows.csv", "total"), "total_cost_peak"),
                       "code": per_sub(code, "model_cost_peak"),
                       "p4": per_sub([r for r in R("results/analysis-v2/rows-code.csv") if r["task"] == "p4-python"], "model_cost_peak"),
                       "wide": per_sub([r for r in R("results/analysis-ctl-dk/rows.csv") if r["task"] == "pw-exercises"], "model_cost_peak"),
                       "chain": per_sub([r for r in ctl if r["task"] == "n1-chain16"], "model_cost_peak"),
                       "free": per_sub(fr, "model_cost_peak"), "xl": per_sub(xl, "model_cost_peak")}
    # the price of one more fact stated correctly (whole list): yuan more per run / facts more per report, by way of buying it
    def price(rs: list, facts: dict, a: str, b: str, ok=lambda r: True) -> dict:
        rs = [r for r in rs if r["id"] in facts]
        fd = contrast(rs, a, b, lambda r: num(facts[r["id"]]["right_pct"]), ok=ok)
        cdiff = contrast(rs, a, b, total, ok=ok)
        n_facts = fd["est"] * SLOTS / 100
        return {"facts": n_facts, "facts_lo": fd["lo"] * SLOTS / 100, "facts_hi": fd["hi"] * SLOTS / 100, "yuan": cdiff["est"], "price": cdiff["est"] / n_facts, "n": fd["n"]}

    fm = {r["id"]: r for r in R("results/analysis-facts-confirm/fact-rows.csv")}
    ff = {r["id"]: r for r in R("results/analysis-facts-floor/fact-rows.csv")}
    fh = {r["id"]: r for r in R("results/analysis-facts-highk/fact-rows.csv")}
    done = lambda r: (num(r.get("open_children_at_end")) or 0) == 0  # noqa: E731
    prices = {"more": price(rows["floor"], ff, "E-D0", "D0"), "k1": price(rows["main"], fm, "D1-K1", "D0"), "default": price(rows["main"], fm, "D1-K8", "D0"),
              "keep": price(rows["floor"], ff, "N-D1-K8", "D1-K8", ok=done), "d2": price(rows["main"], fm, "D2-K8", "D1-K8"),
              "old": price(rows["highk"], fh, "W-D3-K64", "W-D1-K8")}
    for kind in ("M2", "M4"):  # merged reports against the default of the same blocks, the two batches together
        mr = [r for f_ in ("results/analysis-office-merge/merge-stats.json", "results/analysis-office-merge-b/merge-stats.json") for r in J(f_)["rows"]
              if r["kind"] == kind and r.get("D1-K8_right_pct") is not None]
        nf = st.mean(r["merged_right_pct"] - r.get("D1-K8_right_pct_hg", r["D1-K8_right_pct"]) for r in mr) * SLOTS / 100
        yuan = st.mean(r["total_cost"] - r["D1-K8_cost"] for r in mr)
        prices[kind] = {"facts": nf, "yuan": yuan, "price": yuan / nf, "n": len(mr), "cost": st.mean(r["total_cost"] for r in mr)}
        n_in = {"M2": 2, "M4": 4}[kind]
        nf0 = st.mean(r["merged_right_pct"] - r["input_mean_right_pct"] for r in mr) * SLOTS / 100
        y0 = st.mean(r["total_cost"] - r["input_cost"] / n_in for r in mr)  # the whole merge (its reports and the merging step) less one report
        prices[kind + "_none"] = {"facts": nf0, "yuan": y0, "price": y0 / nf0, "n": len(mr)}
    if (EXP / "results/analysis-facts-dose/fact-rows.csv").exists():  # the two search-more sentences of the two-dose batch, each against its own D0
        dr = [r for r in R("results/analysis-office-dose/rows-all.csv") if complete(r)]
        dfacts = {r["id"]: r for r in R("results/analysis-facts-dose/fact-rows.csv")}
        prices.update({"dose150": price(dr, dfacts, "E-D0", "D0"), "dose250": price(dr, dfacts, "N-D0", "D0"), "dose_default": price(dr, dfacts, "D1-K8", "D0")})
    out["prices"] = prices
    fl_pages = lambda g: st.mean(st.mean(num(r["web_fetch_calls"]) for r in rows["floor"] if r["group"] == g and r["task"] == t) for t in sorted({r["task"] for r in rows["floor"]}))  # noqa: E731
    out["more_pages"] = {"more": fl_pages("E-D0"), "default": fl_pages("D1-K8"), "none": fl_pages("D0")}
    # how many subagents the model keeps alive at once when K does not stop it (the largest K of each task)
    peak = lambda rs, g: sorted(num(r.get("slot_peak")) or 0 for r in rs if r["group"] == g)  # noqa: E731
    xd = R("results/analysis-xl-depth/rows-all.csv")
    out["demand"] = {"xl": peak(xd, "W-N-D1-K64"), "free": peak(fr, "W-E-D1-K64"), "office": peak(rows["highk"], "W-D1-K64")}
    logs = J("results/analysis-clean/user-logs-cost.json")
    out["logs"] = logs["logs"]
    web = [v["total"] for v in logs["logs"].values() if v["search_requests"] > 0]
    out["logs_web"] = sorted(web)
    old = out["by_key"]["old"]
    out["old_over_logs"] = sum(1 for v in old["runs"] if v > min(web))
    out["gain_behaviour"] = {"ws": gain_against_behaviour("results/analysis-ws-h1", "ws-rows.csv", "f1_item"),
                             "drb2": gain_against_behaviour("results/analysis-drb2-h1", "drb2-rows.csv", "total")}
    return out


def load() -> dict:
    return {"office": office(), "rubric": rubric(), "code": code_read(), "ctl": controls(), "build": building(), "pub": public(), "grid": grid(), "issues": issues(),
            "cost": cost()}


def _show(o, pre="", depth=0):
    if isinstance(o, dict):
        if set(o) >= {"est", "lo", "hi"} and not isinstance(o["est"], dict):
            s = (f"x{o['est']:.2f} [{o['lo']:.2f}, {o['hi']:.2f}]" if o.get("ratio") or (o.get("est", 0) > 0 and "sd" in o and o.get("lo", 0) > 0 and "tasks" in o and False)
                 else f"{o['est']:+.2f} [{o['lo']:+.2f}, {o['hi']:+.2f}]")
            print(f"{pre}{s} n={o.get('n')} holm={o.get('holm', o.get('p_holm'))}")
            return
        for k, v in o.items():
            if isinstance(v, (dict, list)) and depth < 5:
                print(f"{pre}{k}:")
                _show(v, pre + "  ", depth + 1)
            else:
                print(f"{pre}{k}: {round(v, 3) if isinstance(v, float) else str(v)[:160]}")
    elif isinstance(o, list):
        for i, v in enumerate(o[:8]):
            print(f"{pre}[{i}]")
            _show(v, pre + "  ", depth + 1)


if __name__ == "__main__":
    D = load()
    for name, d in D.items():
        print("=" * 20, name)
        _show({k: v for k, v in d.items() if k not in ("merge_raw", "depth_rows")})
