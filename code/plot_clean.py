#!/usr/bin/env python3
"""New figures of the reorganised report (build_clean.py). Same drawing code, canvas width and colours as the
figures already on the wiki page (plot_brief.Svg, plot_wiki.panels_figure); numbers from clean_data.py.

  summary-by-task.svg        every kind of task on one page: what allowing subagents changes (default against no
                             delegation tools) in the result, the cost and the time
  office-cost-confirm.svg    office research tasks: cost per run by group (model + search)
  office-time-confirm.svg    office research tasks: minutes per run by group
  office-tradeoff.svg        office research tasks: every change of setting as a point, cost ratio against the change
                             in facts stated correctly (each against the default of its own batch)
  office-repeats.svg         the three office findings in every batch that has the contrast, and together
  office-levels.svg          office research tasks: subagents opened on each level under six settings of the two limits
  cost-distribution.svg      office research tasks: the cost of every run under six settings, with the two user sessions
  cost-subagents.svg         cost of a run against the number of subagents it opened (office tasks; the package)
  cost-by-k.svg              yuan per run by K, one panel per task
  cost-by-depth.svg          yuan per run by depth, one panel per task
  pub-score.svg / pub-cost.svg / pub-time.svg    the two public benchmarks: group means
  pub-paired-delegation.svg  one point per task: score without delegation tools against the default
  pub-paired-kd.svg          one point per task: default against K = 1 and against depth 2

Usage: plot_clean.py [--out results/analysis-clean]     then: bash scripts/render-brief.sh results/analysis-clean
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics as st
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean_data as cd  # noqa: E402
import plot_brief as pb  # noqa: E402
import plot_wiki as pw  # noqa: E402

EXP = cd.EXP
W = pb.W


def sgn(v: float, nd: int = 1) -> str:
    return f"{v:+.{nd}f}".replace("-", "−")


def shu(v: float, nd: int = 1) -> str:
    """Signed v with nd decimals, halves away from zero (the rounding of the report's tables)."""
    return ("−" if v < 0 else "+") + hu(abs(v), nd)


def hu(v: float, nd: int = 1) -> str:
    """v with nd decimals, exact halves away from zero (3.55 -> 3.6; the binary default gives 3.5 here and 3.7 for 3.65)."""
    from decimal import ROUND_HALF_UP, Decimal
    return str(Decimal(repr(round(float(v), 9))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


# ------------------------------------------------------------------------------------------------- summary
def summary(D: dict, out: Path) -> None:
    o, c, k, b, p = D["office"], D["code"], D["ctl"], D["build"], D["pub"]
    wsr = lambda x: {"est": x["est"], "lo": x["lo"], "hi": x["hi"]}  # noqa: E731
    rows = [  # label, subagents opened by the default, effect (diff), cost (ratio), time (ratio)
        ("办公报告题（2 道）", o["means"]["D1-K8"]["kids"], o["h1"]["right_legacy_pct"], o["h1"]["total_cost_peak"], o["h1"]["seconds"]),
        ("评测集填表题（公开，24 道）", p["ws"]["pair"]["W-D1-K8"]["kids"], wsr(p["ws"]["cmp"]["H1n"]["f1_item"]), wsr(p["ws"]["cmp"]["H1n"]["total_cost_peak"]), wsr(p["ws"]["time"]["H1n"])),
        ("评测集报告题（公开，30 道）", p["drb2"]["pair"]["W-D1-K8"]["kids"], wsr(p["drb2"]["cmp"]["H1"]["total"]), wsr(p["drb2"]["cmp"]["H1"]["total_cost_peak"]), wsr(p["drb2"]["time"]["H1"])),
        ("读代码题（2 道）", c["means"]["D1-K8"]["kids"], c["cmp"]["C1"]["score"], c["cmp"]["C1"]["model_cost_peak"], c["cmp"]["C1"]["seconds"]),
        ("小编程题（4 道练习）", c["p4"]["means"]["D1-K8"]["kids"], c["p4"]["c1"]["score"], c["p4"]["c1"]["model_cost_peak"], c["p4"]["c1"]["seconds"]),
        ("限时 24 题", k["wide"]["means"]["W-D1-K8"]["kids"], k["wide"]["cmp"]["NC"]["score"], k["wide"]["cmp"]["NC"]["model_cost_peak"], None),  # time-limited: no time
        ("16 步串行题", k["chain"]["means"]["W-D1-K8"]["kids"], k["chain"]["cmp"]["NC"]["score"], k["chain"]["cmp"]["NC"]["model_cost_peak"], k["chain"]["cmp"]["NC"]["seconds"]),
        ("不限时 24 题", b["free"]["means"]["W-D1-K8"]["kids"], b["free"]["cmp"]["NC"]["score"], b["free"]["cmp"]["NC"]["model_cost_peak"], b["free"]["cmp"]["NC"]["answer_s"]),
        ("大型编码题", b["xl"]["means"]["W-D1-K8"]["kids"], b["xl"]["cmp"]["NC"]["score"], b["xl"]["cmp"]["NC"]["model_cost_peak"], b["xl"]["cmp"]["NC"]["answer_s"]),
    ]
    heads = {0: "调研类任务", 3: "代码类任务"}
    row_h, top = 34, 64
    n_lines = len(rows) + len(heads)
    H = top + row_h * n_lines + 58
    s = pb.Svg(W, H)
    x_label, x_kids = 20, 300
    panels = [("质量之差", 352, 540, "diff", (-10.0, 22.0), (-10, 0, 10, 20), 2),
              ("费用倍数", 584, 728, "ratio", (0.6, 6.0), (1, 2, 3, 5), 3),
              ("时间倍数", 772, 896, "ratio", (0.6, 1.8), (0.75, 1, 1.5), 4)]
    bottom = top + row_h * n_lines - 10
    s.text(x_kids, 26, "默认开几个 subagent", 15, "middle", "ink", 600)
    y = top
    for i, row in enumerate(rows):
        if i in heads:
            s.text(x_label, y + 5, heads[i], 14, color="ink", weight=700)
            s.line(x_label, y + 13, W - 16, y + 13, "grid")
            y += row_h
        s.text(x_label + 12, y + 5, row[0], 14, color="ink")
        s.text(x_kids, y + 5, hu(row[1]) if row[1] >= 0.05 else "0", 14, "middle", "ink2")
        y += row_h
    for title, x0, x1, kind, (lo, hi), ticks, col in panels:
        s.text((x0 + x1) / 2, 26, title, 15, "middle", "ink", 600)
        X = (lambda v, x0=x0, x1=x1, lo=lo, hi=hi: x0 + (x1 - x0) * (v - lo) / (hi - lo)) if kind == "diff" else \
            (lambda v, x0=x0, x1=x1, lo=lo, hi=hi: x0 + (x1 - x0) * (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo)))
        ref = 0 if kind == "diff" else 1
        for t in ticks:
            s.line(X(t), top - 18, X(t), bottom, "axis" if t == ref else "grid", 1.6 if t == ref else 1)
            s.text(X(t), bottom + 20, (sgn(t, 0) if t else "0") if kind == "diff" else f"×{t:g}", 12, "middle", "muted")
        y = top
        for i, row in enumerate(rows):
            if i in heads:
                y += row_h
            c_ = row[col]
            if c_ is None:
                s.text(X(1) + 8, y + 5, "限时", 13, "start", "muted")
                y += row_h
                continue
            a, z = max(c_["lo"], lo), min(c_["hi"], hi)
            if c_["hi"] > c_["lo"]:
                s.line(X(a), y, X(z), y, "pre", 2.6)
            s.circle(X(min(max(c_["est"], lo), hi)), y, 5.2, "pre")
            if kind == "diff" and i == 0:  # office tasks: the filled dot is the 63 items fixed beforehand, the ring the whole list
                e_ = o["h1"]["right_pct"]
                s.line(X(max(e_["lo"], lo)), y + 11, X(min(e_["hi"], hi)), y + 11, "pre", 1.8)
                s.circle(X(e_["est"]), y + 11, 4.4, "pre", hollow=True)
            y += row_h
    s.text((panels[0][1] + panels[0][2]) / 2, H - 14, "默认 − 不开（分或百分点）", 13, "middle", "ink2")
    s.text((panels[1][1] + panels[1][2]) / 2, H - 14, "默认 ÷ 不开", 13, "middle", "ink2")
    s.text((panels[2][1] + panels[2][2]) / 2, H - 14, "默认 ÷ 不开", 13, "middle", "ink2")
    s.save(out / "summary-by-task.svg")


# --------------------------------------------------------------------------------- one figure per kind of task
def tci(v: list) -> tuple:
    """Mean and 95% t interval of the mean."""
    v = [x for x in v if x is not None]
    if not v:
        return None
    m = st.mean(v)
    if len(v) < 2:
        return m, m, m
    from scipy import stats as sps
    h = sps.t.ppf(0.975, len(v) - 1) * st.stdev(v) / math.sqrt(len(v))
    return m, m - h, m + h


def rows_figure(out: Path, name: str, clusters: list, rows: list, row_h: int = 176) -> None:
    """Several bar panels stacked on one set of groups: one row per measure, one bar per group.
    clusters: [(title or "", [(label, key, bold)])]; rows: [{"ylabel", "cell": key -> (mean, lo, hi) or None,
    "fmt", optional "parts": key -> [(value, colour)], optional "legend": [(text, colour)]}].
    A label may hold "|" for a line break."""
    n_bars = sum(len(c[1]) for c in clusters)
    gap_c = 26
    x0, x1 = 78, W - 16
    unit = (x1 - x0 - gap_c * (len(clusters) - 1)) / n_bars
    top0 = 58 if any(t for t, _ in clusters) else 30
    gap_r = 38
    two_lines = any("|" in b[0] for _, bs in clusters for b in bs)
    H = top0 + len(rows) * row_h + (len(rows) - 1) * gap_r + (64 if two_lines else 44)
    s = pb.Svg(W, H)
    centres, px = {}, x0
    spans = []
    for title, bars in clusters:
        w = unit * len(bars)
        spans.append((px, w, title))
        for j, (label, key, bold) in enumerate(bars):
            centres[(title, key)] = (px + unit * (j + 0.5), label, bold)
        px += w + gap_c
    for sx, w, title in spans:
        if title:
            s.text(sx + w / 2, 30, title, 16, "middle", "ink", 600)
    bw = min(46, unit * 0.58)
    for i, row in enumerate(rows):
        top = top0 + i * (row_h + gap_r)
        base = top + row_h
        cells = {ck: row["cell"](ck[1]) for ck in centres}
        peak = max([c[2] for c in cells.values() if c] + [0.0001])
        ymax, step = pw.nice_max(peak * 1.12)
        if row.get("step"):  # a coarser grid where the default one would be crowded
            step = row["step"]
            ymax = math.ceil(peak * 1.12 / step) * step
        Y = lambda v, base=base, top=top, ymax=ymax: base - (base - top) * v / ymax  # noqa: E731
        s.text(20, (top + base) / 2, row["ylabel"], 13, "middle", "ink2", rotate=True)
        for sx, w, _ in spans:
            v = 0
            while v <= ymax + 1e-9:
                s.line(sx, Y(v), sx + w, Y(v), "grid")
                if sx == spans[0][0]:
                    s.text(sx - 8, Y(v) + 4, f"{v:g}", 12, "end", "muted")
                v += step
            s.line(sx, base, sx + w, base, "axis", 1.4)
        if row.get("legend"):
            lx = x1
            for text, col in reversed(row["legend"]):
                lx -= 13 * len(text) + 30
                s.rect(lx, top - 22, 13, 13, col, rx=2)
                s.text(lx + 18, top - 11, text, 13, color="ink2")
        for ck, (cx, label, bold) in centres.items():
            c = cells[ck]
            if c is None:
                continue
            est, lo, hi = c
            if row.get("parts"):
                y = base
                for value, col in row["parts"](ck[1]):
                    h = (base - top) * value / ymax
                    s.rect(cx - bw / 2, y - h, bw, h, col)
                    y -= h
            else:
                s.rect(cx - bw / 2, Y(est), bw, base - Y(est), "bar" if not bold else "l1")
            if hi > lo:
                s.line(cx, Y(max(lo, 0)), cx, Y(hi), "ink", 1.8)
            s.text(cx, Y(hi) - 6, hu(est, int(row.get("fmt", "{:.1f}")[3])), 13, "middle", "ink", 600)
    bottom = top0 + len(rows) * row_h + (len(rows) - 1) * gap_r
    for (cx, label, bold) in centres.values():
        for li, part in enumerate(label.split("|")):
            s.text(cx, bottom + 22 + 18 * li, part, 13, "middle", "ink", 700 if bold else 400)
    s.save(out / f"{name}.svg")


def task_figures(D: dict, out: Path) -> None:
    num = cd.num
    def cell(rows, col):
        """Mean and interval of a group; the mean weights the tasks equally, like the tables (it differs from the plain
        mean only where a group has unequal numbers of runs per task: the office group with 39 complete runs)."""
        get = col if callable(col) else (lambda r: num(r.get(col)))

        def one(g):
            v = [(r["task"], get(r)) for r in rows if r["group"] == g and get(r) is not None]
            if not v:
                return None
            m, lo, hi = tci([q for _, q in v])
            by = {}
            for t, q in v:
                by.setdefault(t, []).append(q)
            te = st.mean(st.mean(q) for q in by.values())
            return te, lo + te - m, hi + te - m
        return one
    mean = lambda rows, g, col: st.mean((num(r.get(col)) or 0) for r in rows if r["group"] == g)  # noqa: E731
    minutes = lambda r: (cd.answer_s(r) / 60) if cd.answer_s(r) is not None else None  # noqa: E731  (to the final answer)

    # --- office research tasks: the six groups of the main table
    facts = {r["id"]: r for r in cd.R("results/analysis-facts-confirm/fact-rows.csv")}
    rows = [dict(r, right_pct=facts[r["id"]]["right_pct"]) for r in cd.R("results/analysis-office-confirm/rows-all.csv") if cd.complete(r) and r["id"] in facts]
    bars = [("不开|subagent", "D0", False), ("K=1", "D1-K1", False), ("K=2", "D1-K2", False), ("K=4", "D1-K4", False), ("默认|（深度 1、K=8）", "D1-K8", True), ("深度 2|（K=8）", "D2-K8", False)]
    rows_figure(out, "task-office", [("", bars)], [
        {"ylabel": "写对的事实占比（%）", "cell": cell(rows, "right_pct")},
        {"ylabel": "费用（元/次）", "cell": cell(rows, "total_cost_peak"), "fmt": "{:.1f}",
         "parts": lambda g: [(mean(rows, g, "model_cost_peak"), "bar"), (mean(rows, g, "total_cost_peak") - mean(rows, g, "model_cost_peak"), "bar2")],
         "legend": [("模型费", "bar"), ("搜索费", "bar2")]},
        {"ylabel": "时间（分钟）", "cell": cell(rows, minutes)},
        {"ylabel": "subagent 数", "cell": cell(rows, "children"),
         "parts": lambda g: [(mean(rows, g, "children_d1"), "bar"), (mean(rows, g, "children_d2"), "l2")], "legend": [("第 1 层", "bar"), ("第 2 层", "l2")]}])

    # --- the two-dose batch: one agent told to search more, next to no subagents and the default of the same batch
    if (EXP / "results/analysis-facts-dose/fact-rows.csv").exists():
        dfacts = {r["id"]: r for r in cd.R("results/analysis-facts-dose/fact-rows.csv")}
        drows = [dict(r, right_pct=dfacts[r["id"]]["right_pct"]) for r in cd.R("results/analysis-office-dose/rows-all.csv") if cd.complete(r) and r["id"] in dfacts]
        dbars = [("不开|subagent", "D0", False), ("不开 subagent|+ 多查 150/250", "E-D0", False), ("不开 subagent|+ 多查 250/500", "N-D0", False), ("默认|（开 subagent）", "D1-K8", True)]
        pages3 = lambda g: [(mean(drows, g, "fetches_distinct"), "bar"), (max(mean(drows, g, "pages_total") - mean(drows, g, "fetches_distinct") - mean(drows, g, "pages_saved"), 0), "bar2"),  # noqa: E731
                            (mean(drows, g, "pages_saved"), "l2")]
        rows_figure(out, "task-dose", [("", dbars)], [
            {"ylabel": "写对的事实占比（%）", "cell": cell(drows, "right_pct")},
            {"ylabel": "搜索请求数", "cell": cell(drows, "search_aux"), "fmt": "{:.0f}"},
            {"ylabel": "打开的网页数", "cell": cell(drows, "pages_total"), "fmt": "{:.0f}", "parts": pages3, "step": 250,
             "legend": [("web_fetch 逐个打开", "bar"), ("命令里直接抓", "bar2"), ("脚本成批下载存盘", "l2")]},
            {"ylabel": "费用（元/次）", "cell": cell(drows, "total_cost_peak"), "fmt": "{:.1f}",
             "parts": lambda g: [(mean(drows, g, "model_cost_peak"), "bar"), (mean(drows, g, "total_cost_peak") - mean(drows, g, "model_cost_peak"), "bar2")],
             "legend": [("模型费", "bar"), ("搜索费", "bar2")]},
            {"ylabel": "时间（分钟）", "cell": cell(drows, minutes)}])

    # --- code-reading tasks
    rows = cd.R("results/analysis-v2/rows-code-c1w1.csv")
    bars = [("不开|subagent", "D0", False), ("默认", "D1-K8", True), ("深度 2", "D2-K8", False), ("深度 3", "D3-K8", False), ("并行提示|K=8", "E-D1-K8", False), ("并行提示|K=4", "E-D1-K4", False),
            ("并行提示|K=2", "E-D1-K2", False), ("并行提示|K=1", "E-D1-K1", False), ("并行提示|深度 2", "E-D2-K8", False), ("并行提示|深度 3", "E-D3-K8", False)]
    rows_figure(out, "task-code", [("", bars)], [
        {"ylabel": "得分", "cell": cell(rows, "score")},
        {"ylabel": "模型费（元/次）", "cell": cell(rows, "model_cost_peak"), "fmt": "{:.2f}"},
        {"ylabel": "时间（分钟）", "cell": cell(rows, minutes)}])

    # --- the two control tasks
    rows = cd.R("results/analysis-ctl/rows.csv")
    three = lambda t: [("不开|subagent", (t, "D0"), False), ("默认", (t, "W-D1-K8"), True), ("并行提示|K=8", (t, "W-E-D1-K8"), False)]  # noqa: E731
    keyed = [dict(r, group=(r["task"], r["group"])) for r in rows]
    rows_figure(out, "task-controls", [("限时 24 题（24 道，限时 3 分钟）", three("pw-exercises")), ("16 步串行题（16 步）", three("n1-chain16"))], [
        {"ylabel": "得分", "cell": cell(keyed, "score")},
        {"ylabel": "模型费（元/次）", "cell": cell(keyed, "model_cost_peak"), "fmt": "{:.2f}"},
        {"ylabel": "时间（分钟）", "cell": cell(keyed, minutes)},
        {"ylabel": "subagent 数", "cell": cell(keyed, "children")}])

    # --- 48-module package
    rows = cd.R("results/analysis-xl-main/rows-all.csv")
    write = lambda g: mean(rows, g, "children") - mean(rows, g, "review_kids")  # noqa: E731
    clusters = [("", [("不开|subagent", "D0", False)]),
                ("原题面", [("K=4", "W-D1-K4", False), ("默认|（K=8）", "W-D1-K8", True), ("K=16", "W-D1-K16", False)]),
                ("题面加不复核提示", [(f"K={q}", f"W-N-D1-K{q}", False) for q in (1, 2, 4, 8, 16)])]
    rows_figure(out, "task-package", clusters, [
        {"ylabel": "到最终回答（分钟）", "cell": cell(rows, cd.answer_min)},
        {"ylabel": "模型费（元/次）", "cell": cell(rows, "model_cost_peak")},
        {"ylabel": "subagent 数", "cell": cell(rows, "children"), "parts": lambda g: [(write(g), "bar"), (mean(rows, g, "review_kids"), "l2")],
         "legend": [("写代码的", "bar"), ("复核的", "l2")]}])

    # --- 24 exercises without a time limit
    rows = cd.R("results/analysis-ctl-free-all/rows.csv")
    wrote = lambda g: mean(rows, g, "children") - mean(rows, g, "children_after_all_written")  # noqa: E731
    clusters = [("", [("不开|subagent", "D0", False), ("默认", "W-D1-K8", True)]),
                ("题面加并行提示", [(f"K={q}", f"W-E-D1-K{q}", False) for q in (1, 2, 4, 8, 16, 64)])]
    rows_figure(out, "task-exercises", clusters, [
        {"ylabel": "到最终回答（分钟）", "cell": cell(rows, cd.answer_min)},
        {"ylabel": "模型费（元/次）", "cell": cell(rows, "model_cost_peak")},
        {"ylabel": "subagent 数", "cell": cell(rows, "children"), "parts": lambda g: [(wrote(g), "bar"), (mean(rows, g, "children_after_all_written"), "l2")],
         "legend": [("写代码的", "bar"), ("文件都写完以后才派的", "l2")]}])

    # --- public benchmarks: the tasks scored in both groups
    pub = public_pairs()
    keyed = [dict(r, group=(b, r["group"])) for b, v in pub.items() for r in v["rows"]]
    two = lambda b: [("不开|subagent", (b, "D0"), False), ("默认", (b, "W-D1-K8"), True)]  # noqa: E731
    search_fee = lambda r: num(r["total_cost_peak"]) - num(r["model_cost_peak"])  # noqa: E731
    mk = lambda g, f: st.mean(f(r) for r in keyed if r["group"] == g)  # noqa: E731
    rows_figure(out, "task-public", [(f"评测集填表题（{pub['ws']['n']} 道）", two("ws")), (f"评测集报告题（{pub['drb2']['n']} 道）", two("drb2"))], [
        {"ylabel": "得分", "cell": cell(keyed, "value")},
        {"ylabel": "费用（元/次）", "cell": cell(keyed, "total_cost_peak"),
         "parts": lambda g: [(mk(g, lambda r: num(r["model_cost_peak"])), "bar"), (mk(g, search_fee), "bar2")], "legend": [("模型费", "bar"), ("搜索费", "bar2")]},
        {"ylabel": "时间（分钟）", "cell": cell(keyed, "minutes")}])

    # --- the time-limited grid: the existing drawing with the names used in this report
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        pb.fig_dk(cd.R("results/analysis-ctl-dk/rows.csv"), Path(tmp))
        svg = (Path(tmp) / "fig5-dk.svg").read_text(encoding="utf-8")
    svg = svg.replace("不给开 subagent 的工具", "不开 subagent").replace("不给委派工具", "不开 subagent").replace("时限 3 分钟", "限时 3 分钟").replace("时限 2 分钟", "限时 2 分钟（只作参考）").replace("同时存活上限", "同时存活上限 K")
    (out / "task-grid.svg").write_text(svg, encoding="utf-8")


def public_pairs() -> dict:
    """Rows of the two public benchmarks restricted to the tasks scored in both groups (no tools, default)."""
    out = {}
    for key, d, score_file, metric in (("ws", "results/analysis-ws-h1", "ws-rows.csv", "f1_item"), ("drb2", "results/analysis-drb2-h1", "drb2-rows.csv", "total")):
        rows = [r for r in _scored(d, score_file, metric) if r["group"] in ("D0", "W-D1-K8")]
        both = {t for t in {r["task"] for r in rows} if {r["group"] for r in rows if r["task"] == t} == {"D0", "W-D1-K8"}}
        out[key] = {"rows": [r for r in rows if r["task"] in both], "n": len(both)}
    return out


# ----------------------------------------------------------------------------------------- office bar figures
def office_bars(out: Path) -> None:
    rows = [r for r in csv.DictReader(open(EXP / "results/analysis-office-confirm/rows-all.csv", encoding="utf-8")) if cd.complete(r)]
    pw.METRIC["total_cost"] = lambda r: cd.num(r.get("total_cost_peak"))
    pw.METRIC["proc_minutes"] = lambda r: (cd.num(r.get("seconds")) or 0) / 60 if cd.num(r.get("seconds")) is not None else None
    layout = [("深度上限 1（出厂默认）", [(f"K={k}", f"D1-K{k}", k == 8) for k in (1, 2, 4, 8)]), ("深度上限 2", [("K=8", "D2-K8", False)])]
    ref = ("D0", "不给开 subagent 的工具")
    pw.panels_figure(out, "office-cost-confirm", rows, layout, "total_cost", "费用（元/次，模型费 + 搜索费）", "同时存活上限", ref, fmt="{:.1f}", widths=[4, 1.4])
    pw.panels_figure(out, "office-time-confirm", rows, layout, "proc_minutes", "时长（分钟）", "同时存活上限", ref, widths=[4, 1.4])


# -------------------------------------------------------------------------------------------- office trade-off
def office_tradeoff(D: dict, out: Path) -> None:
    o = D["office"]
    ms = o["merge_raw"]
    pooled = o["depth_pooled"]
    pts = [  # label, cost ratio, contrast, kind, label offset (dx, dy, anchor)
        ("不开 subagent", o["cmp"]["D0"]["total_cost_peak"]["est"], o["cmp"]["D0"]["right_pct"], "o", (12, 5, "start")),
        ("K=1", o["cmp"]["D1-K1"]["total_cost_peak"]["est"], o["cmp"]["D1-K1"]["right_pct"], "k", (-12, 5, "end")),
        ("K=2", o["cmp"]["D1-K2"]["total_cost_peak"]["est"], o["cmp"]["D1-K2"]["right_pct"], "k", (12, 5, "start")),
        ("K=4", o["cmp"]["D1-K4"]["total_cost_peak"]["est"], o["cmp"]["D1-K4"]["right_pct"], "k", (-12, -6, "end")),
        ("K=64", o["k64"]["total_cost_peak"]["est"], o["k64"]["right_pct"], "k", (12, 5, "start")),
        ("深度 2", o["cmp"]["D2-K8"]["total_cost_peak"]["est"], o["cmp"]["D2-K8"]["right_pct"], "d", (-10, 5, "end")),
        ("深度 3", o["wait"]["WD3"]["total_cost_peak"]["est"], o["wait"]["WD3"]["right_pct"], "d", (0, 84, "middle")),
        ("深度 2，K=64", o["k64_d2"]["total_cost_peak"]["est"], o["k64_d2"]["right_pct"], "d", (-4, -70, "middle")),
        ("深度 3，K=64|（相当于旧默认）", o["k64_d3"]["total_cost_peak"]["est"], o["k64_d3"]["right_pct"], "d", (14, 8, "start")),
        ("不开 subagent + 多查 100/100", o["floor"]["PRIM"]["total_cost_peak"]["est"], o["floor"]["PRIM"]["right_pct"], "o", (12, 22, "start")),
    ]
    for kind, name, off in (("M2", "两份不开 subagent 的报告合并", (-12, -8, "end")), ("M4", "四份合并", (12, -8, "start"))):
        c = o["merge_pooled"][kind]
        pts.append((name, c["cost"]["est"], c["facts"], "o", off))
    H = 520
    s = pb.Svg(W, H)
    x0, x1, y0, y1 = 86, W - 36, H - 70, 44
    lo, hi, ylo, yhi = math.log(0.2), math.log(5.6), -22.0, 14.0
    X = lambda v: x0 + (x1 - x0) * (math.log(v) - lo) / (hi - lo)  # noqa: E731
    Y = lambda v: y0 + (y1 - y0) * (v - ylo) / (yhi - ylo)  # noqa: E731
    for v in (-20, -15, -10, -5, 0, 5, 10):
        s.line(x0, Y(v), x1, Y(v), "axis" if v == 0 else "grid", 1.6 if v == 0 else 1)
        s.text(x0 - 10, Y(v) + 5, sgn(v, 0) if v else "0", 13, "end", "muted")
    for v in (0.25, 0.5, 1, 2, 4):
        s.line(X(v), y0, X(v), y1, "axis" if v == 1 else "grid", 1.6 if v == 1 else 1)
        s.text(X(v), y0 + 23, f"×{v:g}", 13, "middle", "muted")
    s.text((x0 + x1) / 2, H - 20, "费用是默认的几倍（对数刻度）", 14, "middle", "ink2")
    s.text(24, (y0 + y1) / 2, "写对的事实占比之差（个百分点）", 14, "middle", "ink2", rotate=True)
    col = {"k": "l1", "d": "l2", "o": "ink"}
    for label, x, c, kind, _ in pts:
        s.line(X(x), Y(max(c["lo"], ylo)), X(x), Y(min(c["hi"], yhi)), col[kind], 2.0)
    for label, x, c, kind, (dx, dy, anchor) in pts:
        s.circle(X(x), Y(c["est"]), 6, col[kind])
        for li, part in enumerate(label.split("|")):  # "|" starts a second line
            s.text(X(x) + dx, Y(c["est"]) + dy + 18 * li, part, 13, anchor, "ink")
    s.circle(X(1), Y(0), 8, "ink", hollow=True)
    s.text(X(1) - 14, Y(0) + 5, "默认", 13, "end", "ink", 700)
    lx = x0 + 8
    for kind, name in (("k", "只改 K"), ("d", "放开深度"), ("o", "不开 subagent 的做法")):
        s.circle(lx, 20, 6, col[kind])
        s.text(lx + 12, 25, name, 13, "start", "ink2")
        lx += 44 + 14 * len(name)
    s.save(out / "office-tradeoff.svg")
    print("office-tradeoff:", [(p[0], round(p[1], 2), round(p[2]["est"], 1)) for p in pts])


# --------------------------------------------------------------------------------------------- office repeats
def office_repeats(D: dict, out: Path) -> None:
    o = D["office"]
    dr = {(r["batch"], r["depth"]): r for r in o["depth_rows"]}
    p2 = o["depth_pooled"]["2_k8"]
    items = [
             (f"第一批（{dr[('formal', 2)]['pairs']} 对）", dr[("formal", 2)], False),
             (f"办公报告题主要的一批（{dr[('confirm', 2)]['pairs']} 对）", dr[("confirm", 2)], False),
             (f"等 subagent 批（{dr[('wait2', 2)]['pairs']} 对）", dr[("wait2", 2)], False),
             (f"都写进去提示的深度批（{dr[('keep', 2)]['pairs']} 对）", dr[("keep", 2)], False),
             (f"这四批合起来算（{p2['pairs']} 对）", p2, True),
             (f"另：K=64 批，深度 2、K=64 对默认（{dr[('highk', 2)]['pairs']} 对）", dr[("highk", 2)], False)]
    row_h, top = 31, 30
    H = top + row_h * len(items) + 62
    s = pb.Svg(W, H)
    x0, x1, lo, hi = 360, W - 24, -6.0, 16.0
    X = lambda v: x0 + (x1 - x0) * (v - lo) / (hi - lo)  # noqa: E731
    bottom = top + row_h * len(items) - 6
    for v in (-5, 0, 5, 10, 15):
        s.line(X(v), top - 16, X(v), bottom, "grid" if v else "axis", 1 if v else 1.6)
        s.text(X(v), bottom + 20, sgn(v, 0) if v else "0", 13, "middle", "muted")
    s.text((x0 + x1) / 2, bottom + 46, "深度 2 减去深度 1：写对的事实占比之差（个百分点）", 14, "middle", "ink2")
    y = top
    for it in items:
        if it[0] == "header":
            s.text(16, y + 5, it[1], 15, color="ink", weight=700)
            s.line(16, y + 13, W - 16, y + 13, "grid")
        else:
            label, c, total = it
            s.text(28, y + 5, label, 14, color="ink", weight=700 if total else 400)
            s.line(X(max(c["lo"], lo)), y, X(min(c["hi"], hi)), y, "pre", 3.6 if total else 2.6)
            s.circle(X(c["est"]), y, 6.5 if total else 5.2, "pre", hollow=not total)
        y += row_h
    s.save(out / "office-repeats.svg")


# -------------------------------------------------------------------------------- office: subagents per level
def office_levels(D: dict, out: Path) -> None:
    """How far the model goes when the limits let it: mean number of subagents per run on level 1, 2 and 3."""
    rows = D["office"]["levels"]
    pb.C.setdefault("white", "#ffffff")
    row_h, top, bar_h = 42, 62, 24
    H = top + row_h * len(rows) + 50
    s = pb.Svg(W, H)
    x0, x1, hi = 292, W - 70, 18.0
    X = lambda v: x0 + (x1 - x0) * v / hi  # noqa: E731
    for i, (name, col) in enumerate((("第 1 层", "l1"), ("第 2 层", "l2"), ("第 3 层", "l3"))):
        s.rect(x0 + i * 106, 12, 16, 16, col, rx=2)
        s.text(x0 + i * 106 + 23, 26, name, 15, color="ink")
    bottom = top + row_h * len(rows) - 18
    for v in (0, 4, 8, 12, 16):
        s.line(X(v), top - 22, X(v), bottom, "grid" if v else "axis", 1 if v else 1.4)
        s.text(X(v), bottom + 20, str(v), 13, "middle", "muted")
    s.text((x0 + x1) / 2, bottom + 44, "每次运行开的 subagent 数（均值）", 14, "middle", "ink2")
    y = top
    for label, lev in rows:
        s.text(20, y + 5, label, 14, color="ink", weight=700 if "默认" in label and "旧" not in label else 400)
        x = x0
        for col, v in zip(("l1", "l2", "l3"), lev):
            w = X(v) - x0
            if w <= 0:
                continue
            s.rect(x, y - bar_h / 2, w, bar_h, col)
            if w >= 34:
                s.text(x + w / 2, y + 5, hu(v), 13, "middle", "white", 600)
            x += w
        s.text(x + 9, y + 5, f"共 {hu(sum(lev))}", 14, color="ink", weight=600)
        y += row_h
    s.save(out / "office-levels.svg")


# ---------------------------------------------------------------------------------------- office: search volume
def office_search(D: dict, out: Path) -> None:
    """Facts stated correctly against search requests, one point per group (the figure of the wiki page redrawn without
    batch names): the groups of every office batch, the single agent told to search more, and the merged reports."""
    o = D["office"]
    pts = [{"key": (r["batch"], r["group"]), "x": float(r["search_aux"]), "y": float(r["right_pct"])}
           for r in csv.DictReader(open(EXP / "results/analysis-facts-step1/group-means-all.csv", encoding="utf-8"))]
    fm = o["floor_means"]
    for g in ("D0", "E-D0", "D1-K8"):
        pts.append({"key": ("floor", g), "x": fm[g]["search"], "y": fm[g]["right_pct"]})
    for q in o["merge_points"]:  # two batches of merged reports, a point each
        pts.append({"key": ("merge-" + q["batch"], q["kind"]), "x": q["search"], "y": q["right_pct"]})
    dose_f = EXP / "results/analysis-facts-dose/extra.json"
    if dose_f.exists():  # the two search-more sentences with larger numbers, with the D0 and the default of their batch
        dg = cd.J("results/analysis-facts-dose/extra.json")["groups"]
        for g in ("D0", "E-D0", "N-D0", "D1-K8"):
            pts.append({"key": ("dose", g), "x": dg[g]["search"], "y": dg[g]["right_pct"]})
    conf = [p for p in pts if p["key"][0] == "confirm"]
    lx_ = [math.log2(p["x"]) for p in conf]
    ly_ = [p["y"] for p in conf]
    mx, my = st.mean(lx_), st.mean(ly_)
    slope = sum((a - mx) * (b - my) for a, b in zip(lx_, ly_)) / sum((a - mx) ** 2 for a in lx_)
    line = lambda v: my + slope * (math.log2(v) - mx)  # noqa: E731

    def kind(key):
        batch, g = key
        if batch.startswith("merge"):
            return "merge"
        g = g.replace("W-", "")
        if g == "E-D0" or (batch == "dose" and g == "N-D0"):
            return "more"
        return "d0" if g == "D0" else ("d1" if g.startswith("D1") else "d23")

    label = {("formal", "D0"): ("不开 subagent", 14, 5, "start"), ("confirm", "D1-K1"): ("K=1", -10, -12, "end"), ("confirm", "D1-K2"): ("K=2", -10, -12, "end"),
             ("confirm", "D2-K8"): ("深度 2、3，K=8", 14, 26, "start"), ("highk", "W-D2-K64"): ("深度 2，K=64", -12, -14, "end"), ("highk", "W-D3-K64"): ("深度 3，K=64", 10, 26, "end"),
             ("formal", "D2-K1"): ("深度 2、3 配 K=1、2", 4, 26, "middle"), ("floor", "E-D0"): ("多查 100/100", 0, 26, "middle"), ("dose", "E-D0"): ("多查 150/250", 13, 5, "start"), ("dose", "N-D0"): ("多查 250/500", 13, 5, "start"),
             ("merge-b", "M2"): ("两份不开 subagent 的报告合并", -12, 6, "end"), ("merge-a", "M4"): ("四份合并", -14, 4, "end")}
    H = 500
    s = pb.Svg(W, H)
    x0, x1, y0, y1 = 86, W - 40, H - 70, 70
    lo, hi, ylo, yhi = math.log(45), math.log(900), 50.0, 85.0
    X = lambda v: x0 + (x1 - x0) * (math.log(v) - lo) / (hi - lo)  # noqa: E731
    Y = lambda v: y0 + (y1 - y0) * (v - ylo) / (yhi - ylo)  # noqa: E731
    for v in (50, 55, 60, 65, 70, 75, 80, 85):
        s.line(x0, Y(v), x1, Y(v), "grid")
        s.text(x0 - 10, Y(v) + 5, f"{v}", 13, "end", "muted")
    for v in (50, 100, 200, 400, 800):
        s.line(X(v), y0, X(v), y0 + 5, "axis")
        s.text(X(v), y0 + 23, f"{v}", 13, "middle", "muted")
    s.line(x0, y0, x1, y0, "axis")
    s.text((x0 + x1) / 2, H - 22, "每次运行的搜索请求数（对数刻度；合并的是几份原稿加合并那一步的总和）", 14, "middle", "ink2")
    s.text(24, (y0 + y1) / 2, "写对的事实占比（%）", 14, "middle", "ink2", rotate=True)
    xa, xb = min(p["x"] for p in conf), max(p["x"] for p in conf)
    s.line(X(xa), Y(line(xa)), X(xb), Y(line(xb)), "muted", 1.6)
    n = 14
    for i in range(n):  # dashed continuation beyond the fitted range
        a, b = xb * (800 / xb) ** (i / n), xb * (800 / xb) ** ((i + 0.55) / n)
        s.line(X(a), Y(min(line(a), yhi)), X(b), Y(min(line(b), yhi)), "muted", 1.6)
    col = {"d0": "muted", "d1": "l1", "d23": "l2", "more": "ink", "merge": "ink"}
    for p in pts:
        k = kind(p["key"])
        x, y = X(p["x"]), Y(p["y"])
        if k == "merge":
            s.circle(x, y, 7, "ink", hollow=True)
            s.line(x - 4, y, x + 4, y, "ink", 1.6)
            s.line(x, y - 4, x, y + 4, "ink", 1.6)
        else:
            s.circle(x, y, 7 if k == "more" else 6, col[k])
    for p in pts:
        if p["key"] in label:
            text, dx, dy, anchor = label[p["key"]]
            s.text(X(p["x"]) + dx, Y(p["y"]) + dy, text, 13, anchor, "ink2")
    lx = x0 + 6
    for k, name in (("d0", "不开 subagent"), ("d1", "深度 1"), ("d23", "深度 2、3"), ("more", "不开 subagent + 多查提示")):
        s.circle(lx, 22, 6, col[k])
        s.text(lx + 12, 27, name, 13, "start", "ink2")
        lx += 34 + 13 * len(name)
    s.circle(lx, 22, 7, "ink", hollow=True)
    s.line(lx - 4, 22, lx + 4, 22, "ink", 1.6)
    s.line(lx, 18, lx, 26, "ink", 1.6)
    s.text(lx + 12, 27, "几份报告合并", 13, "start", "ink2")
    s.text(x1, 51, "直线是拟合线，虚线是往外延长", 13, "end", "muted")
    s.save(out / "office-search.svg")
    print(f"office-search: {len(pts)} points; slope {slope:.2f} points per doubling; single agent told to search more is {fm['E-D0']['right_pct'] - line(fm['E-D0']['search']):+.1f} from the line")


# ------------------------------------------------------------------------------------------------ cost figures
def _dot(s, x: float, y: float, col: str, r: float = 3.2, op: float = 0.5) -> None:
    s.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{pb.C[col]}" opacity="{op}"/>')


def _dash(s, x1: float, y1: float, x2: float, y2: float, col: str = "ink2", width: float = 1.5) -> None:
    s.out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{pb.C[col]}" stroke-width="{width}" stroke-dasharray="7,5"/>')


def cost_distribution(D: dict, out: Path) -> None:
    """Office tasks: every run's cost (search fee included) under six settings; the tick is the median; the dashed line
    is what the two user sessions that used the web cost as whole sessions with the same costing."""
    c = D["cost"]
    groups = [("不开|subagent", "none", "muted"), ("K=1", "k1", "l1"), ("默认|（深度 1、K=8）", "default", "l1"), ("深度 2", "d2", "l2"), ("深度 3", "d3", "l2"),
              ("深度 3、K=64|（相当于旧默认）", "old", "l2")]
    H = 480
    s = pb.Svg(W, H)
    x0, x1, top, base, ymax = 66, W - 20, 56, 396, 60.0
    Y = lambda v: base - (base - top) * v / ymax  # noqa: E731
    for v in range(0, 61, 10):
        s.line(x0, Y(v), x1, Y(v), "grid")
        s.text(x0 - 9, Y(v) + 5, str(v), 13, "end", "muted")
    s.line(x0, base, x1, base, "axis", 1.4)
    s.text(22, (top + base) / 2, "一次任务的费用（元）", 14, "middle", "ink2", rotate=True)
    lx = x0 + 4
    for name, col in (("不开 subagent", "muted"), ("深度 1", "l1"), ("深度 2、3", "l2")):
        _dot(s, lx + 6, 23, col, 5.5, 0.85)
        s.text(lx + 17, 28, name, 14, color="ink")
        lx += 40 + 14 * len(name) * (0.62 if name.startswith("不开") else 1)
    s.line(lx + 6, 23, lx + 34, 23, "ink", 2.6)
    s.text(lx + 42, 28, "中位数", 14, color="ink")
    cw = (x1 - x0) / len(groups)
    for i, (label, key, col) in enumerate(groups):
        cx = x0 + (i + 0.5) * cw
        runs = c["by_key"][key]["runs"]
        for j, v in enumerate(runs):
            _dot(s, cx + ((j * 0.618034) % 1 - 0.5) * cw * 0.5, Y(min(v, ymax)), col)
        s.line(cx - cw * 0.33, Y(c["by_key"][key]["median"]), cx + cw * 0.33, Y(c["by_key"][key]["median"]), "ink", 2.6)
        for li, part in enumerate(label.split("|")):
            s.text(cx, base + 24 + 18 * li, part, 13, "middle", "ink", 700 if key == "default" else 400)
    ref = st.mean(c["logs_web"])
    _dash(s, x0, Y(ref), x1, Y(ref))
    s.text(x0 + 10, Y(ref) - 8, "两份联网的用户日志：整场约 %s 元（多轮对话）" % hu(ref, 0), 13, "start", "ink2")
    s.save(out / "cost-distribution.svg")


def cost_subagents(D: dict, out: Path) -> None:
    """One point per run: cost against the number of subagents the run opened. Left: office tasks (search fee included),
    with the least-squares line of the data layer. Right: the 48-module package (model fee), a line per prompt."""
    c = D["cost"]
    H = 440
    s = pb.Svg(W, H)
    pw_, gap, left, top, base = 372, 80, 70, 58, 372
    panels = [("办公报告题（费用含搜索费）", c["fit"]["points"], 30, 60, 5, 10, {"none": "muted", "d1": "l1", "deep": "l2"},
               [("不开 subagent", "muted"), ("深度 1", "l1"), ("深度 2、3", "l2")]),
              ("大型编码题（模型费）", c["code_fit"]["xl_points"], 30, 30, 5, 5, {"none": "muted", "noreview": "l1", "plain": "l2"},
               [("不开 subagent", "muted"), ("题面加不复核提示", "l1"), ("原题面（写完又派去复核）", "l2")])]
    for i, (title, pts, xmax, ymax, xstep, ystep, colour, legend) in enumerate(panels):
        px = left + i * (pw_ + gap)
        X = lambda v, px=px, xmax=xmax: px + pw_ * min(v, xmax) / xmax  # noqa: E731
        Y = lambda v, ymax=ymax: base - (base - top) * min(v, ymax) / ymax  # noqa: E731
        s.text(px + pw_ / 2, 26, title, 15, "middle", "ink", 600)
        for v in range(0, ymax + 1, ystep):
            s.line(px, Y(v), px + pw_, Y(v), "grid")
            s.text(px - 9, Y(v) + 5, str(v), 12, "end", "muted")
        for v in range(0, xmax + 1, xstep):
            s.text(X(v), base + 20, str(v), 12, "middle", "muted")
        s.line(px, base, px + pw_, base, "axis", 1.4)
        for k, y, tag in pts:
            _dot(s, X(k), Y(y), colour[tag], 3.0, 0.45)
        if i == 0:
            f = c["fit"]
            xa, xb = 0, max(k for k, _, _ in pts)
            s.line(X(xa), Y(f["intercept"]), X(xb), Y(f["intercept"] + f["per_subagent"] * xb), "ink", 1.8)
        else:
            for tag in ("noreview", "plain"):
                v = [(k, y) for k, y, t in pts if t in (tag, "none")]
                f = cd.ols([[k for k, _ in v]], [y for _, y in v])
                xb = max(k for k, _, t in pts if t == tag)
                s.line(X(0), Y(f["b"][0]), X(xb), Y(f["b"][0] + f["b"][1] * xb), colour[tag], 1.8)
        s.text(px + pw_ / 2, base + 44, "这次运行开的 subagent 数", 13, "middle", "ink2")
        s.text(px - 44, (top + base) / 2, "元/次", 13, "middle", "ink2", rotate=True)
        for li, (name, col) in enumerate(legend):
            _dot(s, px + 14, top + 12 + 20 * li, col, 5, 0.85)
            s.text(px + 25, top + 17 + 20 * li, name, 13, color="ink2")
    s.save(out / "cost-subagents.svg")


def bar_panels(out: Path, name: str, panels: list, cols: int = 3, plot_h: int = 150, ylabels: list | None = None) -> None:
    """Small panels of bars with their own scales: panels = [(title, [(group label, [(bar label, (mean, lo, hi), style)])])];
    style: "none" grey, "default" strong blue, "bar" blue, "alt" light blue."""
    colour = {"none": "muted", "default": "l1", "bar": "bar", "alt": "bar2"}
    left, right, gap_x, top0, gap_y, foot = 52, 12, 44, 44, 92, 58
    rows_n = math.ceil(len(panels) / cols)
    pw_ = (W - left - right - gap_x * (cols - 1)) / cols
    H = top0 + rows_n * plot_h + (rows_n - 1) * gap_y + foot
    s = pb.Svg(W, H)
    for i, (title, groups) in enumerate(panels):
        px = left + (i % cols) * (pw_ + gap_x)
        top = top0 + (i // cols) * (plot_h + gap_y)
        base = top + plot_h
        bars = [b for _, bs in groups for b in bs]
        peak = max(b[1][2] for b in bars)
        ymax, step = pw.nice_max(peak * 1.16)
        nd = 1 if peak >= 10 else 2
        Y = lambda v, base=base, top=top, ymax=ymax: base - (base - top) * v / ymax  # noqa: E731
        s.text(px, top - 16, title, 14, "start", "ink", 600)
        ylabel = ylabels[i] if ylabels is not None else ("元/次" if i % cols == 0 else None)
        if ylabel:
            s.text(px - 38, (top + base) / 2, ylabel, 12, "middle", "muted", rotate=True)  # left of this panel (px - 38 is 14 for the first column)
        v = 0
        while v <= ymax + 1e-9:
            s.line(px, Y(v), px + pw_, Y(v), "grid")
            s.text(px - 7, Y(v) + 4, f"{v:g}", 12, "end", "muted")
            v += step
        s.line(px, base, px + pw_, base, "axis", 1.4)
        slots = len(bars) + 0.6 * (len(groups) - 1)
        unit = pw_ / slots
        bw = min(30, unit * 0.62)
        x = px
        for gi, (glabel, bs) in enumerate(groups):
            gx0 = x
            for label, (est, lo, hi), style in bs:
                cx = x + unit / 2
                s.rect(cx - bw / 2, Y(est), bw, base - Y(est), colour[style])
                if hi > lo:
                    s.line(cx, Y(max(lo, 0)), cx, Y(hi), "ink", 1.6)
                s.text(cx, Y(hi) - 5, hu(est, nd), 12, "middle", "ink", 600)
                s.text(cx, base + 17, label, 12, "middle", "ink", 700 if style == "default" else 400)
                x += unit
            if glabel:
                s.line(gx0 + 4, base + 25, x - 4, base + 25, "grid", 1.4)
                s.text((gx0 + x) / 2, base + 41, glabel, 12, "middle", "ink2")
            x += 0.6 * unit
    s.save(out / f"{name}.svg")


def cost_by_limits(D: dict, out: Path) -> None:
    """Yuan per run by K and by depth, one panel per task. Every group of bars is one batch."""
    num = cd.num

    def cells(rows: list, col: str):
        def one(g, task=None):
            v = [(r["task"], num(r.get(col))) for r in rows if r["group"] == g and (task is None or r["task"] == task) and num(r.get(col)) is not None]
            m, lo, hi = tci([q for _, q in v])
            by = {}
            for t, q in v:
                by.setdefault(t, []).append(q)
            te = st.mean(st.mean(q) for q in by.values())
            return te, lo + te - m, hi + te - m
        return one

    office = cells([r for r in cd.R("results/analysis-office-confirm/rows-all.csv") if cd.complete(r)], "total_cost_peak")
    highk = cells([r for r in cd.R("results/analysis-office-highk/rows-all.csv") if cd.complete(r)], "total_cost_peak")
    wait = cells([r for r in cd.R("results/analysis-wait/rows.csv") if cd.complete(r)], "total_cost_peak")
    h1 = cells(_scored("results/analysis-drb2-h1", "drb2-rows.csv", "total"), "total_cost_peak")
    kd = cells(_scored("results/analysis-drb2-kd", "drb2-rows.csv", "total"), "total_cost_peak")
    code = cells(cd.R("results/analysis-v2/rows-code-c1w1.csv"), "model_cost_peak")
    dk = cells([r for r in cd.R("results/analysis-ctl-dk/rows.csv") if r["task"] == "pw-exercises"], "model_cost_peak")
    free = cells(cd.R("results/analysis-ctl-free-all/rows.csv"), "model_cost_peak")
    xl = cells(cd.R("results/analysis-xl-main/rows-all.csv"), "model_cost_peak")
    kb = lambda cell, pre, ks, default=None: [(str(k), cell(f"{pre}{k}"), "default" if k == default else "bar") for k in ks]  # noqa: E731
    bar_panels(out, "cost-by-k", [
        ("办公报告题（含搜索费）", [("", [("不开", office("D0"), "none")]), ("K", kb(office, "D1-K", (1, 2, 4, 8), 8)), ("另一批的 K", kb(highk, "W-D1-K", (8, 64), 8))]),
        ("评测集报告题（含搜索费）", [("", [("不开", h1("D0"), "none")]), ("K", kb(h1, "W-D1-K", (8,), 8)), ("另一批的 K", kb(kd, "W-D1-K", (1, 8), 8))]),
        ("读代码题", [("", [("不开", code("D0"), "none"), ("默认", code("D1-K8"), "default")]), ("题面加并行提示的 K", kb(code, "E-D1-K", (1, 2, 4, 8)))]),
        ("限时 24 题", [("", [("不开", dk("D0"), "none")]), ("题面加并行提示的 K", kb(dk, "W-E-D1-K", (1, 2, 4, 8, 16)))]),
        ("不限时 24 题", [("", [("不开", free("D0"), "none"), ("默认", free("W-D1-K8"), "default")]), ("题面加并行提示的 K", kb(free, "W-E-D1-K", (1, 2, 4, 8, 16, 64)))]),
        ("大型编码题", [("", [("不开", xl("D0"), "none")]), ("原题面的 K", kb(xl, "W-D1-K", (4, 8, 16), 8)), ("加不复核提示的 K", kb(xl, "W-N-D1-K", (1, 2, 4, 8, 16)))])])
    db = lambda cell, gs, default=True: [(f"深度 {i + 1}", cell(g), "default" if (i == 0 and default) else "bar") for i, g in enumerate(gs)]  # noqa: E731
    bar_panels(out, "cost-by-depth", [
        ("办公报告题，K=8（含搜索费）", [("", db(wait, ("W-D1-K8", "W-D2-K8", "W-D3-K8")))]),
        ("办公报告题，K=64（含搜索费）", [("", db(highk, ("W-D1-K64", "W-D2-K64", "W-D3-K64"), False))]),
        ("评测集报告题，K=8（含搜索费）", [("", db(kd, ("W-D1-K8", "W-D2-K8")))]),
        ("读代码题，题面加并行提示", [("", db(code, ("E-D1-K8", "E-D2-K8", "E-D3-K8"), False))]),
        ("不限时 24 题，题面加并行提示", [(f"K={k} 的深度", [(str(i + 1), free(g), "bar") for i, g in enumerate((f"W-E-D1-K{k}", f"W-E-D2-K{k}"))]) for k in (4, 8, 16)]),
        ("大型编码题，K=8", [("原题面", db(xl, ("W-D1-K8", "W-D2-K8"))), ("题面加不复核提示", db(xl, ("W-N-D1-K8", "W-N-D2-K8"), False))])])


# ------------------------------------------------------------------------------------------ public benchmarks
# ------------------------------------------------------------------------- figures added with the review of 2026-10-07
def _vbar(s, cx: float, bw: float, y: float, base: float, colour: str, label: str, size: int = 13) -> None:
    s.rect(cx - bw / 2, y, bw, base - y, colour)
    s.text(cx, y - 7, label, size, "middle", "ink", 600)


def fact_strata_fig(out: Path) -> None:
    """Which facts the default adds: facts right per report without subagents and with the default, in four groups of
    facts by how often a run without subagents states them (grouped in two batches, measured in the third)."""
    import clean_extra as ce
    rows = ce.fact_strata()["confirm"]["rows"]
    H = 440
    s = pb.Svg(W, H)
    left, right, top, base = 78, 24, 86, 320
    ymax = 30.0
    Y = lambda v: base - (base - top) * v / ymax  # noqa: E731
    for i, (name, col) in enumerate((("不开 subagent", "muted"), ("默认（开 subagent）", "l1"))):
        s.rect(left + i * 150, 14, 16, 16, col, rx=2)
        s.text(left + i * 150 + 23, 28, name, 14, color="ink")
    for v in (0, 10, 20, 30):
        s.line(left, Y(v), W - right, Y(v), "axis" if v == 0 else "grid", 1.4 if v == 0 else 1)
        s.text(left - 9, Y(v) + 5, str(v), 13, "end", "muted")
    s.text(24, (top + base) / 2, "每份报告写对的条数", 14, "middle", "ink2", rotate=True)
    slot = (W - left - right) / len(rows)
    bw = 62
    for i, r in enumerate(rows):
        cx = left + slot * (i + 0.5)
        _vbar(s, cx - bw / 2 - 3, bw, Y(r["low"]), base, "muted", hu(r["low"]))
        _vbar(s, cx + bw / 2 + 3, bw, Y(r["high"]), base, "l1", hu(r["high"]))
        s.text(cx, Y(max(r["low"], r["high"])) - 30, f"多写对 {shu(r['gain'])} 条，占 {hu(100 * r['share'], 0)}%", 13, "middle", "ink", 600)
        head, _, tail = r["name"].partition("（")
        s.text(cx, base + 24, head, 14, "middle", "ink", 600)
        s.text(cx, base + 44, "（" + tail, 13, "middle", "ink2")
        s.text(cx, base + 64, f"这一档 {hu(r['items'])} 条", 13, "middle", "ink2")
    s.text((left + W - right) / 2, H - 14, "不开 subagent 时，这条事实多常被写对", 14, "middle", "ink2")
    s.save(out / "facts-strata.svg")


def merge_cover_fig(out: Path) -> None:
    """One single-agent report, what two and four of them cover together, what the merged reports state, the default."""
    import clean_extra as ce
    mu = ce.merge_union()
    dflt = ce.fact_strata()["confirm"]["total"]["high"]
    bars = [("一份单 agent 报告", "", mu["M2"]["one"], "muted"), ("两份合起来", "覆盖到的", mu["M2"]["union"], "bar2"), ("两份的", "合并稿", mu["M2"]["merged"], "bar"),
            ("四份合起来", "覆盖到的", mu["M4"]["union"], "bar2"), ("四份的", "合并稿", mu["M4"]["merged"], "bar")]
    H = 400
    s = pb.Svg(W, H)
    left, right, top, base = 78, 150, 40, 318
    ymax = 100.0
    Y = lambda v: base - (base - top) * v / ymax  # noqa: E731
    for v in (0, 20, 40, 60, 80, 100):
        s.line(left, Y(v), W - right, Y(v), "axis" if v == 0 else "grid", 1.4 if v == 0 else 1)
        s.text(left - 9, Y(v) + 5, str(v), 13, "end", "muted")
    s.text(24, (top + base) / 2, "写对的条数（清单平均 97.5 条）", 14, "middle", "ink2", rotate=True)
    slot = (W - left - right) / len(bars)
    for i, (l1, l2, v, col) in enumerate(bars):
        cx = left + slot * (i + 0.5)
        _vbar(s, cx, 70, Y(v), base, col, hu(v, 0), 14)
        s.text(cx, base + 24, l1, 14, "middle", "ink")
        if l2:
            s.text(cx, base + 44, l2, 14, "middle", "ink")
    _dash(s, left, Y(dflt), W - right + 8, Y(dflt), "l1", 2.0)
    s.text(W - right + 14, Y(dflt) - 2, "默认（开 subagent）", 13, "start", "l1", 600)
    s.text(W - right + 14, Y(dflt) + 16, f"{hu(dflt, 0)} 条", 13, "start", "l1", 600)
    s.save(out / "merge-coverage.svg")


def price_ladder_fig(D: dict, out: Path) -> None:
    """Yuan more per fact more, by way of getting it: from no subagents, and on top of the default."""
    pr = D["cost"]["prices"]
    blocks = [("从不开 subagent 出发", [("两份报告合并", pr["M2_none"]), ("四份报告合并", pr["M4_none"]), ("K=1", pr["k1"]), ("多查 100/100", pr["more"])]
               + ([("多查 150/250", pr["dose150"]), ("多查 250/500", pr["dose250"])] if "dose150" in pr else [])
               + [("默认（开 subagent）", pr["default"])]),
              ("在默认之上再加", [("默认 + 都写进去提示", pr["keep"]), ("深度 2", pr["d2"])])]
    row_h, top = 34, 46
    n = sum(len(b) for _, b in blocks)
    H = top + row_h * (n + 1) + 34 * len(blocks) + 62
    s = pb.Svg(W, H)
    x0, x1, hi = 300, W - 350, 2.0
    X = lambda v: x0 + (x1 - x0) * v / hi  # noqa: E731
    bottom = H - 62
    for v in (0, 0.5, 1.0, 1.5, 2.0):
        s.line(X(v), top - 6, X(v), bottom, "axis" if v == 0 else "grid", 1.4 if v == 0 else 1)
        s.text(X(v), bottom + 20, f"{v:g}", 13, "middle", "muted")
    s.text((x0 + x1) / 2, H - 10, "每多写对一条事实多花的钱（元）", 14, "middle", "ink2")
    y = top
    for title, items in blocks:
        s.text(18, y + 6, title, 14, color="ink", weight=600)
        y += 30
        for label, e in items:
            strong = label.startswith("默认（")
            s.text(34, y + 5, label, 14, color="ink", weight=700 if strong else 400)
            s.rect(x0, y - 11, X(e["price"]) - x0, 22, "l1" if strong else "bar")
            weak = "（区间含 0）" if e.get("facts_lo", 1) < 0 else ""
            s.text(X(e["price"]) + 8, y + 5, f"{hu(e['price'], 2)} 元（多写对 {hu(e['facts'])} 条{weak}，多花 {hu(e['yuan'])} 元）", 13, color="ink")
            y += row_h
        y += 8
    s.text(34, y + 5, "深度 3、K=64（相当于旧默认）", 14, color="ink")
    s.text(x0 + 8, y + 5, f"多花 {hu(pr['old']['yuan'])} 元，多写对的测不出", 13, color="ink2")
    s.save(out / "price-ladder.svg")


def relay_fig(out: Path) -> None:
    """Of the facts right in what the subagents handed back: how many are in the final report and how many are not."""
    import clean_extra as ce
    rows = ce.relay()["rows"]
    pb.C.setdefault("white", "#ffffff")
    row_h, top = 44, 66
    H = top + row_h * len(rows) + 46
    s = pb.Svg(W, H)
    x0, x1, hi = 230, W - 250, 80.0
    X = lambda v: x0 + (x1 - x0) * v / hi  # noqa: E731
    for i, (name, col) in enumerate((("交回的消息里写对、也进了最终报告", "bar"), ("交回的消息里写对、没进最终报告", "l2"))):
        s.rect(x0 + i * 300, 14, 16, 16, col, rx=2)
        s.text(x0 + i * 300 + 23, 28, name, 14, color="ink")
    bottom = top + row_h * len(rows) - 14
    for v in (0, 20, 40, 60, 80):
        s.line(X(v), top - 18, X(v), bottom, "axis" if v == 0 else "grid", 1.4 if v == 0 else 1)
        s.text(X(v), bottom + 20, str(v), 13, "middle", "muted")
    s.text((x0 + x1) / 2, H - 6, "交回的消息里写对的条数（每份的平均）", 14, "middle", "ink2")
    y = top
    for r in rows:
        kept = r["handed"] - r["lost"]
        s.text(18, y + 5, r["label"], 14, color="ink")
        s.rect(x0, y - 12, X(kept) - x0, 24, "bar")
        s.rect(X(kept), y - 12, X(r["handed"]) - X(kept), 24, "l2")
        s.text(X(r["handed"]) + 8, y + 5, f"没进 {hu(r['lost'])} 条（{hu(100 * r['lost_share'])}%）；最终报告写对 {hu(r['final'])} 条", 13, color="ink")
        y += row_h
    s.save(out / "relay-loss.svg")


def scorecard_fig(out: Path) -> None:
    """Every primary comparison written down beforehand as one square, by experiment, coloured by its verdict."""
    import clean_extra as ce
    sc = ce.scorecard()
    pb.C.setdefault("white", "#ffffff")
    kinds = (("显著", "l1"), ("校正后不显著", "bar2"), ("没有差别", "muted"), ("没测出差别", "white"))
    row_h, top, x0, sq = 27, 58, 480, 20
    H = top + row_h * len(sc) + 14
    s = pb.Svg(W, H)
    lx = 18
    for name, col in kinds:
        s.rect(lx, 14, sq, sq, "ink2" if col == "white" else col, rx=3)
        if col == "white":
            s.rect(lx + 1.5, 15.5, sq - 3, sq - 3, "white", rx=2)
        s.text(lx + sq + 7, 30, name, 14, color="ink")
        lx += sq + 26 + 14 * len(name)
    counts = {k: 0 for k, _ in kinds}
    for i, g in enumerate(sc):
        y = top + row_h * i
        s.text(18, y + 15, g["title"], 13, color="ink")
        for j, r in enumerate(g["rows"]):
            kind = "显著" if r["word"].startswith("显著") else r["word"]
            counts[kind] += 1
            col = dict(kinds)[kind]
            x = x0 + j * (sq + 6)
            s.rect(x, y, sq, sq, "ink2" if col == "white" else col, rx=3)
            if col == "white":
                s.rect(x + 1.5, y + 1.5, sq - 3, sq - 3, "white", rx=2)
    s.save(out / "primary-scorecard.svg")
    print("primary-scorecard:", counts, sum(counts.values()))


def pages_fig(out: Path) -> None:
    """Pages opened per run by the way they were opened: web_fetch one by one, URLs written out in shell commands,
    pages a script of the run's own downloaded and saved. The two-dose batch adds its groups once it is analysed."""
    import clean_extra as ce
    pg = ce.pages()
    rows = [("不开 subagent", pg["D0"]), ("不开 subagent + 多查 100/100", pg["E-D0"]), ("默认（开 subagent）", pg["D1-K8"])]
    row_h, top = 46, 66
    H = top + row_h * len(rows) + 48
    s = pb.Svg(W, H)
    x0, x1, hi = 250, W - 200, 240.0
    X = lambda v: x0 + (x1 - x0) * v / hi  # noqa: E731
    lx = x0
    for name, col in (("web_fetch 逐个打开", "l1"), ("命令里直接抓", "bar2"), ("脚本成批下载存盘", "l2")):
        s.rect(lx, 14, 16, 16, col, rx=2)
        s.text(lx + 23, 28, name, 14, color="ink")
        lx += 48 + 14 * len(name)
    bottom = top + row_h * len(rows) - 14
    for v in (0, 50, 100, 150, 200):
        s.line(X(v), top - 18, X(v), bottom, "axis" if v == 0 else "grid", 1.4 if v == 0 else 1)
        s.text(X(v), bottom + 20, str(v), 13, "middle", "muted")
    s.text((x0 + x1) / 2, H - 6, "每次运行打开的不同网页数", 14, "middle", "ink2")
    y = top
    for label, e in rows:
        s.text(18, y + 5, label, 14, color="ink", weight=700 if label.startswith("默认") else 400)
        x = x0
        for v, col in ((e["fetch"], "l1"), (e["urls"] - e["fetch"], "bar2"), (e["saved"], "l2")):
            s.rect(x, y - 12, X(v) - x0, 24, col)
            x += X(v) - x0
        s.text(x + 8, y + 5, f"合计 {hu(e['low'], 0)}–{hu(e['high'], 0)} 个", 13, color="ink")
        y += row_h
    s.save(out / "pages-opened.svg")


# ------------------------------------------------------------------------------------------- design coverage
def coverage_grid(out: Path) -> None:
    """Which settings were run on which task: runs per cell (prompt variants together), empty where nothing was run."""
    import clean_extra as ce
    cv = ce.coverage()
    cells = cv["cells"]
    rows, cols = ce.COVER_ROWS, ce.COVER_COLS
    cw, rh, x0, top = 37, 34, 196, 84
    gap = 12                                        # between the blocks of columns
    blocks = [("", cols[:1]), ("深度 1 的 K", cols[1:7]), ("深度 2 的 K", cols[7:13]), ("深度 3 的 K", cols[13:])]
    Wd = x0 + cw * len(cols) + gap * (len(blocks) - 1) + 14
    H = top + rh * len(rows) + 16
    s = pb.Svg(Wd, H)
    pb.C.setdefault("white", "#ffffff")
    shade = lambda n: "#dfeaf8" if n < 25 else ("#b9d2f1" if n < 80 else "#8fb6e8")  # noqa: E731
    xs, x = {}, x0
    for bi, (title, bc) in enumerate(blocks):
        if title:
            s.text(x + cw * len(bc) / 2, 30, title, 14, "middle", "ink", 600)
            s.line(x + 3, 38, x + cw * len(bc) - 3, 38, "axis", 1.2)
        for key, label in bc:
            xs[key] = x
            s.text(x + cw / 2, 62, label, 13, "middle", "ink" if key in ("none", "1-8") else "ink2", 700 if key == "1-8" else 400)
            x += cw
        x += gap
    s.text(xs["1-8"] + cw / 2, 78, "默认", 11, "middle", "ink", 600)
    for ri, (rk, rn) in enumerate(rows):
        y = top + rh * ri
        s.text(14, y + rh / 2 + 5, rn, 14, color="ink")
        for key, _ in cols:
            n = cells.get(f"{rk}|{key}", 0)
            if n:
                s.rect(xs[key] + 2, y + 3, cw - 4, rh - 6, shade(n), rx=3)
                s.text(xs[key] + cw / 2, y + rh / 2 + 5, str(n), 13, "middle", "ink", 600 if key == "1-8" else 400)
            else:
                s.rect(xs[key] + 2, y + 3, cw - 4, rh - 6, "#f6f5f1", rx=3)
    s.save(out / "coverage-grid.svg")



def _scored(d: str, score_file: str, metric: str) -> list:
    flagged = set(cd.J(f"{d}/stats.json")["inputs"]["flagged"])
    sc = {r["id"]: r for r in cd.R(f"{d}/{score_file}")}
    out = []
    for r in cd.R(f"{d}/rows-all.csv"):
        if r["id"] in flagged or r["id"] not in sc or cd.num(sc[r["id"]].get(metric)) is None:
            continue
        out.append(dict(r, value=cd.num(sc[r["id"]][metric]), minutes=cd.answer_s(r) / 60))
    return out


def public_figs(out: Path) -> None:
    ws = _scored("results/analysis-ws-h1", "ws-rows.csv", "f1_item")
    h1 = _scored("results/analysis-drb2-h1", "drb2-rows.csv", "total")
    kd = _scored("results/analysis-drb2-kd", "drb2-rows.csv", "total")
    rows = [dict(r, group="ws:" + r["group"]) for r in ws] + [dict(r, group="h1:" + r["group"]) for r in h1] + [dict(r, group="kd:" + r["group"]) for r in kd]
    pw.METRIC["value"] = lambda r: r.get("value")
    pw.METRIC["tcost"] = lambda r: cd.num(r.get("total_cost_peak"))
    pw.METRIC["pmin"] = lambda r: r.get("minutes")
    layout = [("评测集填表题：逐项 F1", [("不开", "ws:D0", False), ("默认", "ws:W-D1-K8", True), ("默认 + 并行提示", "ws:W-E-D1-K8", False)]),
              ("评测集报告题：总分", [("不开", "h1:D0", False), ("默认", "h1:W-D1-K8", True)]),
              ("评测集报告题：换 K 和深度", [("K=1", "kd:W-D1-K1", False), ("默认", "kd:W-D1-K8", True), ("深度 2", "kd:W-D2-K8", False)])]
    lay2 = [(t.split("：")[0] + ("：换 K 和深度" if "换" in t else ""), cs) for t, cs in layout]
    pw.panels_figure(out, "pub-score", rows, layout, "value", "得分", "", None)
    pw.panels_figure(out, "pub-cost", rows, lay2, "tcost", "费用（元/次，模型费 + 搜索费）", "", None, fmt="{:.1f}")
    pw.panels_figure(out, "pub-time", rows, lay2, "pmin", "时长（分钟）", "", None)

    def pairs(data: list, a: str, b: str) -> list:
        by = {(r["task"], r["group"]): r["value"] for r in data}
        return [(by[(t, a)], by[(t, b)]) for (t, g) in sorted(by) if g == a and (t, b) in by]

    def scatter(name: str, panels: list) -> None:
        H = 470
        s = pb.Svg(W, H)
        pw_, gap, left, top, base = 372, 76, 78, 54, 388
        for i, (title, xl, yl, pts, lo, hi, step) in enumerate(panels):
            px = left + i * (pw_ + gap)
            lo = min(lo, step * math.floor(min(min(a, b) for a, b in pts) / step))
            X = lambda v, px=px, lo=lo, hi=hi: px + pw_ * (v - lo) / (hi - lo)  # noqa: E731
            Y = lambda v, lo=lo, hi=hi: base - (base - top) * (v - lo) / (hi - lo)  # noqa: E731
            s.text(px + pw_ / 2, 28, title, 15, "middle", "ink", 600)
            v = lo
            while v <= hi + 1e-9:
                s.line(px, Y(v), px + pw_, Y(v), "grid")
                s.line(X(v), top, X(v), base, "grid")
                s.text(px - 9, Y(v) + 5, f"{v:g}", 12, "end", "muted")
                s.text(X(v), base + 20, f"{v:g}", 12, "middle", "muted")
                v += step
            s.line(X(lo), Y(lo), X(hi), Y(hi), "muted", 1.6)
            up = sum(1 for a, b in pts if b > a + 1e-9)
            down = sum(1 for a, b in pts if b < a - 1e-9)
            for a, b in pts:
                s.circle(X(a), Y(b), 5, "l1" if b >= a else "l2")
            s.text(px + pw_ / 2, base + 44, xl, 13, "middle", "ink2")
            s.text(px - 46, (top + base) / 2, yl, 13, "middle", "ink2", rotate=True)
            s.circle(px + 16, top + 14, 5, "l1")
            s.text(px + 26, top + 19, f"线上或线上方 {len(pts) - down} 道", 13, "start", "ink2")
            s.circle(px + pw_ - 112, base - 16, 5, "l2")
            s.text(px + pw_ - 102, base - 11, f"线下方 {down} 道", 13, "start", "ink2")
            print(f"{name} | {title}: {len(pts)} tasks, above {up}, below {down}, same {len(pts) - up - down}")
        s.save(out / f"{name}.svg")

    scatter("pub-paired-delegation", [
        ("评测集报告题：每道题的总分", "不开 subagent", "默认", pairs(h1, "D0", "W-D1-K8"), 20, 90, 10),
        ("评测集填表题：每道题的得分（F1）", "不开 subagent", "默认", pairs(ws, "D0", "W-D1-K8"), 20, 100, 20)])
    scatter("pub-paired-kd", [
        ("评测集报告题：K=1 对默认", "默认（K=8）", "K=1", pairs(kd, "W-D1-K8", "W-D1-K1"), 20, 90, 10),
        ("评测集报告题：深度 2 对默认", "默认（深度 1）", "深度 2", pairs(kd, "W-D1-K8", "W-D2-K8"), 20, 90, 10)])


# ------------------------------------------------------- the two limits, every tested value against the default
def limits_fig(D: dict, out: Path) -> None:
    """limits-k.svg / limits-depth.svg: one block per kind of task and prompt: a heading line (the task's name, what
    it is, which prompt, the level of the reference group) and three panels under it (quality, cost, time); the
    horizontal axis is K (depth 1) or the depth limit (K = 8); every point is the contrast against the default-like
    group that ran with it (clean_extra.limits, the numbers of the K and depth tables). Thin line: 95% interval.
    Red / green: detected (worse / better on that measure); grey dot: no difference (quality only: the interval
    inside the margin); grey ring: not detected."""
    import clean_extra as ce
    L = ce.limits(D)
    figs = (("k", "limits-k", (1, 2, 4, 8, 16, 64), 8, lambda v: str(v), "横轴：同时存活上限 K（默认 8）；各行的深度上限都是 1。没有点的取值没有测。", "K=8 时"),
            ("depth", "limits-depth", (0, 1, 2, 3), 1, lambda v: "不开" if v == 0 else str(v), "横轴：深度上限（默认 1；“不开”= 不给开 subagent 的工具）；K 都是 8，标题里写明几个 K 合起来的两行除外。没有点的取值没有测。", "深度 1 时"))
    scales = {"k": {"q": ((-15.0, 9.0), (-10, -5, 0, 5)), "c": ((0.27, 1.8), (0.3, 0.5, 1, 1.5)), "t": ((0.5, 3.6), (0.5, 1, 2, 3))},
              "depth": {"q": ((-22.0, 12.0), (-20, -10, 0, 10)), "c": ((0.16, 4.2), (0.25, 0.5, 1, 2, 4)), "t": ((0.5, 3.2), (0.5, 1, 2, 3))}}
    cols = (("q", "质量：比默认高或低多少", "办公报告题：百分点；其余：分（满分 100）"),
            ("c", "费用：是默认的几倍", "一次任务花的钱"), ("t", "用户等的时间：是默认的几倍", "从开始到主 agent 给出最终回答"))
    GLOSS = {"office": "联网调研，写一份长报告（2 道）", "ws": "联网收集信息填表（WideSearch，24 道）", "drb2": "联网调研写报告（DeepResearch Bench II，30 道）",
             "code": "读 DSH 源码，回答问题、写方案（2 道）", "p4": "4 道 Python 练习", "wide": "24 道互不相关的 Python 小题，限时 3 分钟",
             "free": "同样 24 道小题，不限时", "xl": "写一个 48 模块、61 个文件的 Python 包", "xln": "写一个 48 模块、61 个文件的 Python 包"}
    left, tick_w, right, plot_h, head_h, pitch, top0 = 12, 40, 14, 74, 30, 150, 124
    pw_ = (W - left - right - 3 * tick_w - 2 * 16) / 3
    PX = lambda j: left + tick_w + j * (pw_ + tick_w + 16)  # noqa: E731
    wide_ = lambda t, size: sum(size if ord(ch) > 0x2e7f else size * 0.56 for ch in t)  # noqa: E731  (rough text width)

    def display_rows(key: str) -> list:
        """The rows as drawn. A row whose depth-2 point comes from the groups with the parallel hint (several K
        pooled) is drawn as two rows, so that every point of a row is compared with the group named in its heading."""
        rows = []
        for r in L[key]:
            if r["key"] == "chain":  # the 16-step task: the model opens none; one point at "none"
                continue
            if key == "depth" and r["sub"].startswith("深度 2："):
                rows.append(dict(r, sub="原题面", cells={0: r["cells"][0]}))
                rows.append(dict(r, sub=f"题面加并行提示，{r['cells'][2]['note']}", cells={2: r["cells"][2]}, base=None))
            else:
                rows.append(dict(r, sub=r["sub"] or "原题面"))
        return rows

    def marker(s, kind: str, x: float, y: float) -> None:
        if kind == "ref":
            s.out.append(f'<path d="M{x:.1f},{y - 6:.1f} L{x + 6:.1f},{y:.1f} L{x:.1f},{y + 6:.1f} L{x - 6:.1f},{y:.1f} Z" fill="{pb.C["ink"]}"/>')
        elif kind == "open":
            s.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.1" fill="#fbfbf9" stroke="{pb.C["muted"]}" stroke-width="2"/>')
        else:
            s.circle(x, y, 4.3, {"same": "muted"}.get(kind, kind))

    for key, name, xs, ref, xfmt, xtitle, ref_word in figs:
        rows = display_rows(key)
        H = top0 + pitch * len(rows) + 48
        s = pb.Svg(W, H)
        halo = lambda x, y, t, size, col, weight: s.out.append(  # noqa: E731  (a label that stays readable on top of lines)
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="middle" fill="{pb.C[col]}" font-weight="{weight}" '
            f'stroke="#fbfbf9" stroke-width="3.2" paint-order="stroke" stroke-linejoin="round">{pb.esc(t)}</text>')
        for j, (m_, title, sub_) in enumerate(cols):
            s.text(PX(j) + pw_ / 2 - tick_w / 2, 22, title, 15, "middle", "ink", 600)
            s.text(PX(j) + pw_ / 2 - tick_w / 2, 41, sub_, 11.5, "middle", "muted")
        s.line(left, 54, W - right, 54, "axis", 1.2)
        # the legend sits above the rows: every panel uses it
        lx, ly = left, 76
        for kind, text in (("ref", "默认（差是 0，倍数是 1）"), ("bad", "测得出：变差、更贵或更慢"), ("good", "测得出：变好、更便宜或更快")):
            marker(s, kind, lx + 7, ly - 4)
            s.text(lx + 19, ly, text, 12.5, color="ink2")
            lx += 40 + wide_(text, 12.5)
        lx, ly = left, 97
        for kind, text in (("same", "没有差别：区间整个在 ±5 分（办公报告题 ±8 个百分点）以内，只有质量分这一类"), ("open", "没测出差别：区间更宽，或校正后不显著")):
            marker(s, kind, lx + 7, ly - 4)
            s.text(lx + 19, ly, text, 12.5, color="ink2")
            lx += 40 + wide_(text, 12.5)
        slot = pw_ / len(xs)
        for i, r in enumerate(rows):
            head = top0 + i * pitch
            top = head + head_h
            base = top + plot_h
            b_ = r["base"]
            # the heading line: name, what the task is and which prompt, then the reference group's own level
            s.text(left, head + 12, r["name"], 14.5, "start", "ink", 700)
            s.text(left + wide_(r["name"], 14.5) + 12, head + 12, f"{GLOSS[r['key']]}；{r['sub']}", 12.5, "start", "ink2")
            if b_ is None:
                level = "每个 K 各和同样加提示的深度 1 比"
            else:
                nd_ = 2 if r.get("tests") else 1
                level = f"{ref_word}：" + (f"写对 {hu(b_['q'], 1)}% 的事实" if b_["qu"] == "%" else f"{hu(b_['q'], nd_)} 分") + f"，{hu(b_['c'], 2)} 元，" \
                    + ("限时 3 分钟" if b_["t"] is None else f"{hu(b_['t'], 1)} 分钟")
            s.text(W - right, head + 12, level, 12.5, "end", "muted")
            for j, (m_, _, _) in enumerate(cols):
                px = PX(j)
                (lo, hi), ticks = scales[key][m_]
                ratio = m_ != "q"
                T = (lambda v: math.log(v)) if ratio else (lambda v: v)
                Y = lambda v, lo=lo, hi=hi, T=T, top=top, base=base: base - (base - top) * (T(min(max(v, lo), hi)) - T(lo)) / (T(hi) - T(lo))  # noqa: E731
                X = lambda v, px=px: px + slot * (xs.index(v) + 0.5)  # noqa: E731
                s.rect(px, top, pw_, plot_h, "#fbfbf9")
                for t in ticks:
                    is_ref = t == (1 if ratio else 0)
                    s.line(px, Y(t), px + pw_, Y(t), "axis" if is_ref else "grid", 1.5 if is_ref else 1)
                    s.text(px - 6, Y(t) + 4, (f"×{t:g}" if ratio else (sgn(t, 0) if t else "0")), 11, "end", "muted")
                for v in xs:
                    s.text(X(v), base + 15, xfmt(v), 11.5, "middle", "ink" if v == ref else "muted", 700 if v == ref else 400)
                if m_ == "t" and r.get("limited"):
                    s.text(px + pw_ / 2, (top + base) / 2 + 5, "这道题限时 3 分钟，不比时间", 12.5, "middle", "muted")
                    continue
                pts = [(v, cl[m_], cl["corr"]["qct".index(m_)]) for v, cl in sorted(r["cells"].items()) if cl[m_] is not None]
                labels, marks = [], []
                line = sorted([(X(v), Y(c_["est"])) for v, c_, _ in pts] + [(X(ref), Y(1 if ratio else 0))])
                for (xa, ya), (xb, yb) in zip(line, line[1:]):
                    s.line(xa, ya, xb, yb, "ink2", 1.3)
                for v, c_, corr in pts:
                    strong = ce.strong(c_, corr)
                    worse = (c_["est"] > 1) if ratio else (c_["est"] < 0)
                    same = (not ratio) and (not strong) and c_["lo"] <= 0 <= c_["hi"] and max(abs(c_["lo"]), abs(c_["hi"])) <= r["margin"]
                    kind = ("bad" if worse else "good") if strong else ("same" if same else "open")
                    col = kind if strong else "muted"
                    ya, yb = Y(c_["hi"]), Y(c_["lo"])
                    if yb - ya > 0.5:
                        s.line(X(v), ya, X(v), yb, col, 2.0)
                    marks.append((kind, X(v), Y(c_["est"])))
                    nd = 2 if (ratio or r.get("tests")) else 1
                    txt = (f"×{hu(c_['est'], 2)}" if ratio else ("0" if abs(c_["est"]) < 0.5 * 10 ** -nd else shu(c_["est"], nd)))
                    above = ya - 5
                    ty = above if above > top + 9 else min(yb + 13, base - 2)
                    labels.append((X(v), ty, txt, col if strong else "ink2", 700 if strong else 400))
                for kind, mx, my in marks:
                    marker(s, kind, mx, my)
                marker(s, "ref", X(ref), Y(1 if ratio else 0))
                for lab in labels:
                    halo(lab[0], lab[1], lab[2], 11.5, lab[3], lab[4])
        s.text(W / 2, top0 + pitch * len(rows) + 4, xtitle, 12.5, "middle", "ink2")
        s.text(W / 2, top0 + pitch * len(rows) + 23, "点上的数是和默认的差或倍数，竖线是 95% 区间。", 12.5, "middle", "ink2")
        s.save(out / f"{name}.svg")


def metric_figs(D: dict, out: Path) -> None:
    """k-quality / k-cost / k-time / depth-quality / depth-cost / depth-time .svg: one measure per figure, one panel per
    kind of task; the horizontal axis is K (depth 1) or the depth limit (K = 8), the vertical axis the difference
    (quality) or the ratio (cost, time) against the default-like group that ran in the same batch
    (clean_extra.limits, the numbers of the K and depth tables). Thin line: 95% interval. Filled dot: detected (the
    interval leaves out the reference and, in a corrected family, survives the correction); ring: not detected.
    Quality panels: the pale band is the range inside which a difference counts as none (the task's margin).
    Not drawn: the quality of the tasks whose groups all score 96 or more (nothing to tell apart), and the depth-2
    points of the two 24-exercise tasks, which exist only with the parallel hint (several K pooled)."""
    import clean_extra as ce
    L = ce.limits(D)
    SUB = {"题面加并行提示": "加并行提示", "原题面": "原题面", "题面加不复核提示": "加不复核提示"}
    specs = {
        "k": {"xs": (1, 2, 4, 8, 16, 64), "ref": 8, "xfmt": str, "xtitle": "同时存活上限 K（深度上限都是 1）", "word": "K=8",
              "q": {"keys": ("office63", "office", "ws", "drb2", "code", "wide"), "cols": 3, "range": (-20.0, 11.0), "ticks": (-15, -10, -5, 0, 5, 10)},
              "c": {"keys": ("office", "ws", "drb2", "code", "wide", "free", "xl", "xln"), "cols": 4, "range": (0.25, 2.1), "ticks": (0.3, 0.5, 0.7, 1, 1.5, 2)},
              "t": {"keys": ("office", "ws", "drb2", "code", "free", "xl", "xln"), "cols": 4, "range": (0.5, 4.2), "ticks": (0.5, 0.7, 1, 1.5, 2, 3, 4)}},
        "depth": {"xs": (0, 1, 2, 3), "ref": 1, "xfmt": lambda v: "不开" if v == 0 else str(v), "xtitle": "深度上限（“不开”= 不给开 subagent 的工具；K 都是 8）", "word": "深度 1",
                  "q": {"keys": ("office63", "office", "ws", "drb2", "code", "wide"), "cols": 3, "range": (-21.0, 13.0), "ticks": (-20, -15, -10, -5, 0, 5, 10)},
                  "c": {"keys": ("office", "ws", "drb2", "code", "p4", "wide", "chain", "free", "xl", "xln"), "cols": 4, "range": (0.16, 3.2), "ticks": (0.2, 0.3, 0.5, 1, 2, 3)},
                  "t": {"keys": ("office", "ws", "drb2", "code", "p4", "chain", "free", "xl", "xln"), "cols": 4, "range": (0.55, 3.8), "ticks": (0.6, 0.8, 1, 1.5, 2, 3)}}}
    ytitle = {"k": {"q": "质量和 K=8 的差（分；办公报告题是百分点）", "c": "一次任务的费用是 K=8 的几倍", "t": "用户等的时间是 K=8 的几倍"},
              "depth": {"q": "质量和深度 1 的差（分；办公报告题是百分点）", "c": "一次任务的费用是深度 1 的几倍", "t": "用户等的时间是深度 1 的几倍"}}
    fname = {"q": "quality", "c": "cost", "t": "time"}

    def marker(s, kind: str, x: float, y: float) -> None:
        if kind == "ref":
            s.out.append(f'<path d="M{x:.1f},{y - 6:.1f} L{x + 6:.1f},{y:.1f} L{x:.1f},{y + 6:.1f} L{x - 6:.1f},{y:.1f} Z" fill="{pb.C["ink"]}"/>')
        elif kind == "open":
            s.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#ffffff" stroke="{pb.C["muted"]}" stroke-width="2"/>')
        else:
            s.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.6" fill="{pb.C["l1"]}"/>')

    for part, sp in specs.items():
        rows = {r["key"]: r for r in L[part]}
        xs, ref = sp["xs"], sp["ref"]
        for m_ in "qct":
            f_ = sp[m_]
            ratio = m_ != "q"
            panels = []
            for key in f_["keys"]:
                r = rows["office" if key == "office63" else key]
                pts = []
                for v, cl in sorted((ce.rule_cells(r) if part == "k" else r["cells"]).items()):  # the K figures follow the uniform rule of the main text
                    if part == "depth" and v == 2 and r["sub"].startswith("深度 2："):
                        continue  # measured only with the parallel hint, several K pooled: in the depth section
                    c_ = cl["legacy"] if key == "office63" else cl[m_]
                    if c_ is None:
                        continue
                    pts.append((v, c_, ce.strong(c_, cl["corr"]["qct".index(m_)])))
                if not pts:
                    continue
                sub = SUB.get(r["sub"], "")
                if key == "office63":
                    name, sub = "办公报告题", "事先定下的 63 条"
                elif key == "office" and m_ == "q":
                    name, sub = "办公报告题", "全清单 195 条"
                else:
                    name = r["name"]
                if part == "k" and "rule" in r:  # which numbers the uniform rule takes
                    if r["key"] == "office":
                        sub = (sub.replace("事先定下的 ", "").replace(" 195 条", "") + "；" if sub else "") + "K=1、2、4 两批合起来"
                    else:
                        name, sub = r["rule_name"], ("三题合起来，加并行提示" if f_["cols"] == 3 else "三题合起来")
                panels.append({"name": name, "sub": sub, "pts": pts, "margin": r["margin"]})
            cols = f_["cols"]
            nrow = math.ceil(len(panels) / cols)
            left, right, top0, gap_x, head, xlab, bottom = 74, 14, 46, 16, 24, 20, 40
            pw_ = (W - left - right - (cols - 1) * gap_x) / cols
            ph = 150
            pitch = head + ph + xlab + 12
            H = top0 + nrow * pitch + bottom
            s = pb.Svg(W, H)
            (lo, hi) = f_["range"]
            T = (lambda v: math.log(v)) if ratio else (lambda v: v)
            # the legend, one line at the top right
            lx = W - right
            for kind, text in (("open", "不显著"), ("fill", "显著"), ("ref", f"对照（{sp['word']}）")):
                wtxt = sum(13 if ord(ch) > 0x2e7f else 13 * 0.56 for ch in text)
                s.text(lx, 22, text, 13, "end", "ink2")
                marker(s, kind, lx - wtxt - 11, 17.5)
                lx -= wtxt + 40
            s.text(left - 58, top0 + nrow * pitch / 2 - 10, ytitle[part][m_], 13.5, "middle", "ink", 600, rotate=True)
            for i, p_ in enumerate(panels):
                ri, ci_ = divmod(i, cols)
                px = left + ci_ * (pw_ + gap_x)
                top = top0 + ri * pitch + head
                base = top + ph
                Y = lambda v, top=top, base=base: base - (base - top) * (T(min(max(v, lo), hi)) - T(lo)) / (T(hi) - T(lo))  # noqa: E731
                slot = pw_ / len(xs)
                X = lambda v, px=px, slot=slot: px + slot * (xs.index(v) + 0.5)  # noqa: E731
                s.text(px, top - 8, p_["name"], 13.5, "start", "ink", 700)
                if p_["sub"]:
                    s.text(px + sum(13.5 if ord(ch) > 0x2e7f else 13.5 * 0.56 for ch in p_["name"]) + 8, top - 8, p_["sub"], 11.5, "start", "muted")
                s.rect(px, top, pw_, ph, "#fbfbf9")
                if not ratio:
                    s.rect(px, Y(p_["margin"]), pw_, Y(-p_["margin"]) - Y(p_["margin"]), "#e9f1ea")
                for t in f_["ticks"]:
                    is_ref = t == (1 if ratio else 0)
                    s.line(px, Y(t), px + pw_, Y(t), "ink2" if is_ref else "grid", 1.2 if is_ref else 1)
                    if ci_ == 0:
                        s.text(px - 7, Y(t) + 4, (f"{t:g} 倍" if ratio else (sgn(t, 0) if t else "0")), 11.5, "end", "ink2")
                for v in xs:
                    s.text(X(v), base + 16, sp["xfmt"](v), 12, "middle", "ink" if v == ref else "ink2", 700 if v == ref else 400)
                line = sorted([(X(v), Y(c_["est"])) for v, c_, _ in p_["pts"]] + [(X(ref), Y(1 if ratio else 0))])
                for (xa, ya), (xb, yb) in zip(line, line[1:]):
                    s.line(xa, ya, xb, yb, "muted", 1.2)
                for v, c_, strong in p_["pts"]:
                    ya, yb = Y(c_["hi"]), Y(c_["lo"])
                    if yb - ya > 0.5:
                        s.line(X(v), ya, X(v), yb, "l1" if strong else "muted", 2.0)
                for v, c_, strong in p_["pts"]:
                    marker(s, "fill" if strong else "open", X(v), Y(c_["est"]))
                marker(s, "ref", X(ref), Y(1 if ratio else 0))
                for v, c_, strong in p_["pts"]:  # the estimate, above the interval (below it when there is no room)
                    ya, yb = Y(c_["hi"]), Y(c_["lo"])
                    nd = 2 if ratio else (1 if abs(c_["est"]) >= 0.05 else 0)
                    txt = hu(c_["est"], 2) if ratio else ("0" if abs(c_["est"]) < 0.05 else shu(c_["est"], nd))
                    yref = Y(1 if ratio else 0)
                    tx, anchor, ty = X(v), "middle", ya - 6
                    if yb - ya > 70:  # a long interval: the number goes beside the point, not at the far end of the line
                        right = xs.index(v) < len(xs) - 1
                        tx, anchor, ty = X(v) + (9 if right else -9), "start" if right else "end", Y(c_["est"]) + 4
                    elif ty < top + 10 or abs(ty - 4 - yref) < 10:  # no room above, or the label would sit on the reference line
                        ty = min(yb + 14, base - 3)
                        if abs(ty - 4 - yref) < 10:
                            ty = ya - 6
                    s.out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="10.5" text-anchor="{anchor}" fill="{pb.C["l1" if strong else "ink2"]}" '
                                 f'font-weight="{700 if strong else 400}" stroke="#fbfbf9" stroke-width="3" paint-order="stroke" stroke-linejoin="round">{pb.esc(txt)}</text>')
            s.text(left + (W - left - right) / 2, H - 14, sp["xtitle"], 13.5, "middle", "ink", 600)
            s.save(out / f"{'k' if part == 'k' else 'depth'}-{fname[m_]}.svg")


def deliver_fig(out: Path) -> None:
    """deliver-office.svg: the office task, by setting: the share of runs that crashed on exit and the share in which
    the root ended while subagents were still open (clean_extra.reliability). Left: the process does not wait for the
    subagents (the CLI as it is); right: the process waits (the experiment's patch; ended-early does not apply)."""
    import clean_extra as ce
    cells = ce.reliability()["cells"]
    S = ce.reliability_sum
    nw = lambda q: not q["waits"] and q["variant"] == "plain"  # noqa: E731
    left_ = [("不开", S(cells, "office", lambda q: q["col"] == "none"))] \
        + [(f"K={k}", S(cells, "office", lambda q, k=k: q["col"] == f"1-{k}" and nw(q))) for k in (1, 2, 4, 8)] \
        + [("K=1、2、4", S(cells, "office", lambda q: q["col"] in ("2-1", "2-2", "2-4") and nw(q))), ("K=8", S(cells, "office", lambda q: q["col"] == "2-8" and nw(q))),
           ("K=1、2、4", S(cells, "office", lambda q: q["col"] in ("3-1", "3-2", "3-4") and nw(q))), ("K=8", S(cells, "office", lambda q: q["col"] == "3-8" and nw(q)))]
    right_ = [(f"深度 {dd}", S(cells, "office", lambda q, dd=dd: q["col"].startswith(f"{dd}-") and q["waits"])) for dd in (1, 2, 3)]
    groups = [("", left_[:1]), ("深度 1", left_[1:5]), ("深度 2", left_[5:7]), ("深度 3", left_[7:9])]
    H, top, base, x0 = 404, 82, 286, 74
    s = pb.Svg(W, H)
    Y = lambda v: base - (base - top) * v / 40  # noqa: E731
    split = 640
    s.text(22, (top + base) / 2, "占这种设置全部运行的比例（%）", 13.5, "middle", "ink", 600, rotate=True)
    for v in (0, 10, 20, 30, 40):
        s.line(x0, Y(v), W - 14, Y(v), "ink2" if v == 0 else "grid", 1.2 if v == 0 else 1)
        s.text(x0 - 8, Y(v) + 4, f"{v}", 12, "end", "ink2")
    # legend
    s.rect(W - 400, 10, 14, 14, "bad")
    s.text(W - 380, 22, "退出时崩溃", 13, "start", "ink2")
    s.rect(W - 286, 10, 14, 14, "bar")
    s.text(W - 266, 22, "主 agent 结束时还有 subagent 没做完", 13, "start", "ink2")
    s.text(x0, 58, "进程不等 subagent（命令行一次性运行的现状）", 13.5, "start", "ink", 700)
    s.text(split + 26, 58, "进程等 subagent（实验加的补丁）", 13.5, "start", "ink", 700)
    s.line(split + 8, top - 6, split + 8, base + 62, "grid", 1.4)
    n_left = len(left_)
    unit = (split - x0) / (n_left + 0.5 * (len(groups) - 1))
    bw = 17
    x = x0
    for glabel, items in groups:
        gx0 = x
        for label, c_ in items:
            cx = x + unit / 2
            for dx, key, col in ((-bw / 2 - 5, "crash", "bad"), (bw / 2 + 5, "early", "bar")):
                if c_[key] is None:
                    continue
                share = 100 * c_[key] / c_["runs"]
                s.rect(cx + dx - bw / 2, Y(share), bw, base - Y(share), col)
                if c_[key]:
                    s.text(cx + dx, Y(share) - 5, f"{int(share + 0.5)}%", 11, "middle", "ink", 600)
            s.text(cx, base + 17, label, 12, "middle", "ink2")
            s.text(cx, base + 33, f"{c_['runs']} 次", 11, "middle", "muted")
            x += unit
        if glabel:
            s.line(gx0 + 6, base + 42, x - 6, base + 42, "grid", 1.4)
            s.text((gx0 + x) / 2, base + 58, glabel, 12.5, "middle", "ink", 600)
        x += 0.5 * unit
    unit_r = (W - 14 - split - 20) / len(right_)
    for i, (label, c_) in enumerate(right_):
        cx = split + 20 + unit_r * (i + 0.5)
        share = 100 * c_["crash"] / c_["runs"]
        s.rect(cx - bw / 2, Y(share), bw, base - Y(share), "bad")
        if c_["crash"]:
            s.text(cx, Y(share) - 5, f"{int(share + 0.5)}%", 11, "middle", "ink", 600)
        s.text(cx, base + 17, label, 12, "middle", "ink2")
        s.text(cx, base + 33, f"{c_['runs']} 次", 11, "middle", "muted")
    s.text((x0 + W - 14) / 2, H - 12, "设置（办公报告题）", 13.5, "middle", "ink", 600)
    s.save(out / "deliver-office.svg")


def xl_k_fig(out: Path) -> None:
    """xl-by-k.svg: the large coding task with the no-review hint, by K: how many subagents were alive at once at most,
    minutes until every file was written and until the final answer (clean_extra.xl_by_group; K = 64 from the depth
    batch, the others from the main batch)."""
    import clean_extra as ce
    g = ce.xl_by_group()
    ks = [(k, g[f"main:W-N-D1-K{k}"]) for k in (1, 2, 4, 8, 16)] + [(64, g["depth:W-N-D1-K64"])]
    H, top, base = 296, 62, 232
    s = pb.Svg(W, H)
    panels = (("同时活着的 subagent 最多有几个", 44, 420, 16, (0, 4, 8, 12, 16), "个"), ("从开始算起用了多少分钟", 494, W - 14, 24, (0, 6, 12, 18, 24), "分钟"))
    for pi, (title, x0, x1, ymax, ticks, unit_) in enumerate(panels):
        Y = lambda v, ymax=ymax: base - (base - top) * v / ymax  # noqa: E731
        s.text(x0 - 30, top - 22, title, 13.5, "start", "ink", 700)
        for v in ticks:
            s.line(x0, Y(v), x1, Y(v), "ink2" if v == 0 else "grid", 1.2 if v == 0 else 1)
            s.text(x0 - 8, Y(v) + 4, f"{v}", 12, "end", "ink2")
        unit = (x1 - x0) / len(ks)
        for i, (k, e) in enumerate(ks):
            cx = x0 + unit * (i + 0.5)
            if pi == 0:
                s.rect(cx - 13, Y(e["slot_peak"]), 26, base - Y(e["slot_peak"]), "bar")
                s.text(cx, Y(e["slot_peak"]) - 5, hu(e["slot_peak"], 1), 12, "middle", "ink", 600)
            else:
                for dx, key, col in ((-12, "written_min", "bar2"), (12, "answer_min", "l1")):
                    s.rect(cx + dx - 10, Y(e[key]), 20, base - Y(e[key]), col)
                    s.text(cx + dx, Y(e[key]) - 5, hu(e[key], 1), 11.5, "middle", "ink", 600)
            s.text(cx, base + 18, str(k), 12.5, "middle", "ink" if k == 8 else "ink2", 700 if k == 8 else 400)
        s.text((x0 + x1) / 2, base + 42, "同时存活上限 K", 13.5, "middle", "ink", 600)
    s.rect(W - 330, 8, 14, 14, "bar2")
    s.text(W - 310, 20, "到文件都写完", 13, "start", "ink2")
    s.rect(W - 196, 8, 14, 14, "l1")
    s.text(W - 176, 20, "到主 agent 给出最终回答", 13, "start", "ink2")
    s.save(out / "xl-by-k.svg")


def overlap_fig(out: Path) -> None:
    """overlap-agents.svg: the office task, per setting: distinct pages opened with web_fetch in one run, split into
    pages only one agent opened and pages two or more agents opened (clean_extra.overlap)."""
    import clean_extra as ce
    rows = ce.overlap()
    H, top, base, x0, x1 = 360, 46, 262, 78, W - 14
    s = pb.Svg(W, H)
    ymax = 450
    Y = lambda v: base - (base - top) * v / ymax  # noqa: E731
    s.text(22, (top + base) / 2, "一次运行打开的不同网页数", 13.5, "middle", "ink", 600, rotate=True)
    for v in range(0, ymax + 1, 100):
        s.line(x0, Y(v), x1, Y(v), "ink2" if v == 0 else "grid", 1.2 if v == 0 else 1)
        s.text(x0 - 8, Y(v) + 4, f"{v}", 12, "end", "ink2")
    s.rect(x1 - 388, 10, 14, 14, "bar2")
    s.text(x1 - 368, 22, "只有一个 agent 打开过", 13, "start", "ink2")
    s.rect(x1 - 204, 10, 14, 14, "l2")
    s.text(x1 - 184, 22, "两个以上的 agent 都打开过", 13, "start", "ink2")
    unit = (x1 - x0) / len(rows)
    for i, r in enumerate(rows):
        cx = x0 + unit * (i + 0.5)
        single = r["pages"] - r["page_cross"]
        s.rect(cx - 22, Y(single), 44, base - Y(single), "bar2")
        s.rect(cx - 22, Y(r["pages"]), 44, Y(single) - Y(r["pages"]), "l2")
        s.text(cx, Y(r["pages"]) - 7, f"{hu(r['pages'], 0)}（重复 {hu(r['page_cross'], 0)}）", 12.5, "middle", "ink", 600)
        s.text(cx, base + 18, r["label"], 12.5, "middle", "ink" if r["group"] == "D1-K8" else "ink2", 700 if r["group"] == "D1-K8" else 400)
        s.text(cx, base + 35, f"{hu(r['agents'], 1)} 个 agent 联网", 11, "middle", "muted")
    s.text((x0 + x1) / 2, H - 14, "设置（办公报告题）", 13.5, "middle", "ink", 600)
    s.save(out / "overlap-agents.svg")


def rejects_fig(out: Path) -> None:
    """rejects-office.svg: the main office batch, per setting and per run: subagents started, delegation calls rejected
    by the depth limit, delegation calls rejected by K (clean_extra.mechanism)."""
    import clean_extra as ce
    m = ce.mechanism()
    rej, tools = m["rejects"]["office-confirm"], m["tools_by_batch"]["office-confirm"]
    groups = (("D1-K1", "K=1"), ("D1-K2", "K=2"), ("D1-K4", "K=4"), ("D1-K8", "默认（K=8）"), ("D2-K8", "深度 2（K=8）"))
    series = (("开成的 subagent", "bar", lambda g: tools[g]["children"] / tools[g]["runs"]), ("被深度上限拒绝的调用", "l2", lambda g: rej[g]["depth"]), ("被 K 拒绝的调用", "l3", lambda g: rej[g]["cap"]))
    H, top, base, x0, x1 = 360, 50, 270, 78, W - 14
    s = pb.Svg(W, H)
    ymax = 10
    Y = lambda v: base - (base - top) * v / ymax  # noqa: E731
    s.text(22, (top + base) / 2, "每次运行的个数或次数", 13.5, "middle", "ink", 600, rotate=True)
    for v in range(0, ymax + 1, 2):
        s.line(x0, Y(v), x1, Y(v), "ink2" if v == 0 else "grid", 1.2 if v == 0 else 1)
        s.text(x0 - 8, Y(v) + 4, f"{v}", 12, "end", "ink2")
    lx = x1 - 520
    for i, (name, col, _) in enumerate(series):
        s.rect(lx + i * 178, 10, 14, 14, col)
        s.text(lx + i * 178 + 20, 22, name, 13, "start", "ink2")
    unit = (x1 - x0) / len(groups)
    for i, (g, label) in enumerate(groups):
        cx = x0 + unit * (i + 0.5)
        for j, (_, col, get) in enumerate(series):
            v = get(g)
            bx = cx - 66 + j * 46
            s.rect(bx, Y(v), 40, base - Y(v), col)
            s.text(bx + 20, Y(v) - 6, hu(v, 1) if v else "0", 12.5, "middle", "ink", 600)
        s.text(cx, base + 20, label, 13, "middle", "ink" if g == "D1-K8" else "ink2", 700 if g == "D1-K8" else 400)
    s.text((x0 + x1) / 2, H - 14, "设置（办公报告题，每种 40 次运行）", 13.5, "middle", "ink", 600)
    s.save(out / "rejects-office.svg")


def senders_fig(out: Path) -> None:
    """handback-senders.svg: the judged handed-back messages, per setting: facts stated correctly that are in the
    messages of one subagent only, and facts that another subagent's messages hold as well (clean_extra.mechanism)."""
    import clean_extra as ce
    sd = ce.mechanism()["senders"]
    groups = (("office-confirm/D1-K8", "默认"), ("office-confirm/D2-K8", "深度 2"), ("office-floor/D1-K8", "默认（和下一组同批）"), ("office-floor/N-D1-K8", "默认 + 都写进去提示"), ("office-highk/W-D2-K64", "深度 2、K=64"))
    H, top, base, x0, x1 = 360, 50, 262, 78, W - 14
    s = pb.Svg(W, H)
    ymax = 80
    Y = lambda v: base - (base - top) * v / ymax  # noqa: E731
    s.text(22, (top + base) / 2, "一次运行里写对的事实（条）", 13.5, "middle", "ink", 600, rotate=True)
    for v in range(0, ymax + 1, 20):
        s.line(x0, Y(v), x1, Y(v), "ink2" if v == 0 else "grid", 1.2 if v == 0 else 1)
        s.text(x0 - 8, Y(v) + 4, f"{v}", 12, "end", "ink2")
    s.rect(x1 - 470, 10, 14, 14, "bar2")
    s.text(x1 - 450, 22, "只在一个 subagent 的消息里", 13, "start", "ink2")
    s.rect(x1 - 252, 10, 14, 14, "l2")
    s.text(x1 - 232, 22, "别的 subagent 的消息里也有", 13, "start", "ink2")
    unit = (x1 - x0) / len(groups)
    for i, (k, label) in enumerate(groups):
        v = sd[k]
        cx = x0 + unit * (i + 0.5)
        one, also = v["only_one_sender"], v["also_elsewhere"]
        s.rect(cx - 24, Y(one), 48, base - Y(one), "bar2")
        s.rect(cx - 24, Y(one + also), 48, Y(one) - Y(one + also), "l2")
        s.text(cx, Y(one + also) - 7, f"{hu(one, 0)} + {hu(also, 0)}", 12.5, "middle", "ink", 600)
        s.text(cx, base + 18, label, 12.5, "middle", "ink" if i == 0 else "ink2", 700 if i == 0 else 400)
        s.text(cx, base + 35, f"{hu(v['senders'], 1)} 个 subagent 交回消息", 11, "middle", "muted")
    s.text((x0 + x1) / 2, H - 14, "设置（办公报告题）", 13.5, "middle", "ink", 600)
    s.save(out / "handback-senders.svg")


def tree_figs(out: Path) -> None:
    """tree-default.svg, tree-depth2.svg: who started whom in one run of the travel task (clean_extra.mechanism: the run
    of the group whose number of subagents is the median). One box per agent with the label the model gave it; under it
    the search requests it sent, the minutes it ran and the delegation calls of its own that were rejected."""
    import clean_extra as ce
    trees = ce.mechanism()["trees"]
    for key, name in (("D1-K8", "tree-default"), ("D2-K8", "tree-depth2")):
        data = trees[key]
        nodes = {n["id"]: n for n in data["nodes"]}
        kids = {}
        for n in data["nodes"]:
            kids.setdefault(n["parent"], []).append(n)
        for v in kids.values():
            v.sort(key=lambda n: (n["start_min"] or 0, n["label"] or ""))
        root = next(n for n in data["nodes"] if n["parent"] is None)
        depth_max = max(n["depth"] for n in data["nodes"])
        slots = []

        def place(n: dict) -> float:
            ch = kids.get(n["id"], [])
            if not ch:
                n["y"] = len(slots)
                slots.append(n)
            else:
                ys = [place(c) for c in ch]
                n["y"] = (ys[0] + ys[-1]) / 2
            return n["y"]
        place(root)
        pitch, top, box_w, box_h = 62, 46, 272, 50
        col_x = {0: 14, 1: 324, 2: 634} if depth_max >= 2 else {0: 110, 1: 520}
        H = top + pitch * len(slots) + 6
        s = pb.Svg(W, H)
        heads = {0: "主 agent", 1: "主 agent 开的 subagent", 2: "subagent 再开的 subagent"}
        for dpt, x in col_x.items():
            s.text(x, 24, heads[dpt], 13.5, "start", "ink", 700)
        for n in data["nodes"]:
            p_ = nodes.get(n["parent"])
            if p_ is None:
                continue
            x, y = col_x[n["depth"]], top + pitch * n["y"] + box_h / 2
            px, py = col_x[p_["depth"]] + box_w, top + pitch * p_["y"] + box_h / 2
            mx = (px + x) / 2
            s.out.append(f'<path d="M{px:.1f},{py:.1f} C{mx:.1f},{py:.1f} {mx:.1f},{y:.1f} {x:.1f},{y:.1f}" fill="none" stroke="{pb.C["axis"]}" stroke-width="1.4"/>')
        for n in data["nodes"]:
            x, y = col_x[n["depth"]], top + pitch * n["y"]
            s.rect(x, y, box_w, box_h, "#f3f2ec" if n["depth"] else "#dfe9f8", rx=5)
            label = "主 agent" if n["parent"] is None else str(n["label"] or "（没有标签）")
            s.text(x + 9, y + 17, label if len(label) <= 38 else label[:37] + "…", 12, "start", "ink", 600)
            s.text(x + 9, y + 32, f"搜索请求 {n['search_requests']} 个 · 运行 {hu(n['minutes'] or 0, 1)} 分钟 · 模型费 {hu(n['yuan'], 2)} 元", 11, "start", "ink2")
            rej = [f"被深度上限拒绝 {n['rejected_depth']} 次"] * bool(n["rejected_depth"]) + [f"被 K 拒绝 {n['rejected_cap']} 次"] * bool(n["rejected_cap"])
            s.text(x + 9, y + 45, "它自己开 subagent 的调用：" + "，".join(rej) if rej else ("开了 " + str(len(kids.get(n["id"], []))) + " 个 subagent" if kids.get(n["id"]) else "没有再开 subagent"), 11, "start", "l2" if rej else "muted")
        s.save(out / f"{name}.svg")


def told_fig(out: Path) -> None:
    """told-limit.svg: the told-limit batch (clean_extra.told): K = 2 and K = 8, each with and without the limit written
    into the tool description: the 63 items stated correctly, the cost, the minutes to the final answer (complete, judged
    runs; the two tasks weighted equally) and the delegation calls rejected by K (every run)."""
    import clean_extra as ce
    allrows = cd.R(ce.TOLD_ROWS)
    facts = {r["id"]: r for r in cd.R("results/analysis-facts-told/fact-rows.csv")}
    judged = [r for r in allrows if cd.complete(r) and r["id"] in facts]

    def cell(src: list, g: str, val) -> tuple:
        v = [(r["task"], val(r)) for r in src if r["group"] == g and val(r) is not None]
        m, lo, hi = tci([q for _, q in v])
        by = {}
        for t, q in v:
            by.setdefault(t, []).append(q)
        te = st.mean(st.mean(q) for q in by.values())
        return te, lo + te - m, hi + te - m

    def panel(src: list, val) -> list:
        return [("K=2", [("不告知", cell(src, "D1-K2", val), "bar"), ("告知", cell(src, "T-D1-K2", val), "alt")]),
                ("K=8（默认）", [("不告知", cell(src, "D1-K8", val), "default"), ("告知", cell(src, "T-D1-K8", val), "alt")])]
    Q = lambda r: cd.num(facts[r["id"]]["right_legacy_pct"])  # noqa: E731
    C = lambda r: cd.num(r["total_cost_peak"])  # noqa: E731
    T = lambda r: cd.answer_s(r) / 60  # noqa: E731
    K = lambda r: cd.num(r["capacity_rejects"]) or 0  # noqa: E731
    bar_panels(out, "told-limit", [("写对的事实占比：事先定下的 63 条（%）", panel(judged, Q)), ("费用（元/次，含搜索费）", panel(judged, C)),
                                   ("到最终回答（分钟）", panel(judged, T)), ("每次运行被 K 拒绝的调用（次）", panel(allrows, K))],
               cols=2, plot_h=150, ylabels=["%", "元/次", "分钟", "次"])


# ------------------------------------------------------------------------------- the figure of the conclusions
def conclusion_fig(D: dict, out: Path) -> None:
    """Two scatter panels for the conclusions, every point a setting against the default of its batch.
    Left, the office task: cost ratio against the difference in facts stated correctly (the 63 items fixed beforehand).
    Right, the large coding task with the no-review prompt: cost ratio against the ratio of the time to the answer.
    Vertical lines are 95% intervals; the dashed lines are the margins of the decision frame of the report."""
    import clean_extra as ce
    L = ce.limits(D)
    LK, LD = {r["key"]: r for r in L["k"]}, {r["key"]: r for r in L["depth"]}
    ok, od = ce.rule_cells(LK["office"]), LD["office"]["cells"]  # K = 1, 2, 4: the two batches together, as in the tables of the main text
    left = [("不开", od[0]["c"]["est"], od[0]["legacy"], "n", (12, 5, "start"), 0)]
    left += [(f"K={v}", ok[v]["c"]["est"], ok[v]["legacy"], "k", off, 0) for v, off in ((1, (-11, 5, "end")), (2, (-11, 5, "end")), (4, (0, -1, "top")), (64, (0, 1, "bottom")))]
    left += [("深度 2", od[2]["c"]["est"], od[2]["legacy"], "d", (0, -1, "top"), -5), ("深度 3", od[3]["c"]["est"], od[3]["legacy"], "d", (0, 1, "bottom"), 5),
             ("深度 3、K=64|（相当于旧默认）", LD["office"]["k64"][3]["c"]["est"], LD["office"]["k64"][3]["legacy"], "d", (0, -1, "top2"), 0)]
    xk, xd = LK["xln"]["cells"], LD["xln"]["cells"]
    right = [("不开", xd[0]["c"]["est"], xd[0]["t"], "n", (12, 5, "start"), 0)]
    right += [(f"K={v}", xk[v]["c"]["est"], xk[v]["t"], "k", off, 0) for v, off in ((1, (12, 5, "start")), (2, (-11, 5, "end")), (4, (-11, 5, "end")), (16, (12, 5, "start")))]
    right += [("深度 2", xd[2]["c"]["est"], xd[2]["t"], "d", (12, 5, "start"), 0)]
    H = 520
    s = pb.Svg(W, H)
    top, base = 96, H - 78
    pw_ = (W - 84 - 104 - 24) / 2
    col = {"k": "l1", "d": "l2", "n": "ink"}
    lx = 78
    for kind, name in (("k", "只改 K"), ("d", "只改深度"), ("n", "不开 subagent")):
        s.circle(lx, 20, 6, col[kind])
        s.text(lx + 12, 25, name, 13, "start", "ink2")
        lx += 40 + 14 * len(name)
    s.circle(lx, 20, 7, "ink", hollow=True)
    s.text(lx + 13, 25, "默认（D=1、K=8）", 13, "start", "ink2")
    s.text(W - 24, 25, "竖线是 95% 区间；虚线是“不差”的边界", 13, "end", "muted")

    def panel(px, title, sub, pts, xr, xticks, yr, yticks, ylog, ylabel, xlabel, margin, mlabel, mside):
        (xlo, xhi), (ylo, yhi) = xr, yr
        X = lambda v: px + pw_ * (math.log(v) - math.log(xlo)) / (math.log(xhi) - math.log(xlo))  # noqa: E731
        if ylog:
            Y = lambda v: base - (base - top) * (math.log(v) - math.log(ylo)) / (math.log(yhi) - math.log(ylo))  # noqa: E731
        else:
            Y = lambda v: base - (base - top) * (v - ylo) / (yhi - ylo)  # noqa: E731
        ref = 1 if ylog else 0
        s.text(px, 62, title, 15, "start", "ink", 600)
        s.text(px + 14 * len(title) + 14, 62, sub, 13, "start", "muted")
        for v in yticks:
            s.line(px, Y(v), px + pw_, Y(v), "axis" if v == ref else "grid", 1.6 if v == ref else 1)
            s.text(px - 9, Y(v) + 5, (f"×{v:g}" if ylog else (sgn(v, 0) if v else "0")), 13, "end", "muted")
        for v in xticks:
            s.line(X(v), top, X(v), base, "axis" if v == 1 else "grid", 1.6 if v == 1 else 1)
            s.text(X(v), base + 22, f"×{v:g}", 13, "middle", "muted")
        s.text(px + pw_ / 2, base + 50, xlabel, 14, "middle", "ink2")
        s.text(px - 60, (top + base) / 2, ylabel, 14, "middle", "ink2", rotate=True)
        _dash(s, px, Y(margin), px + pw_, Y(margin), "muted", 1.4)
        s.text(px + pw_ - 4 if mside == "right" else px + 5, Y(margin) + (17 if not ylog else -7), mlabel, 12.5, "end" if mside == "right" else "start", "muted")
        clip = lambda v: max(min(v, yhi), ylo)  # noqa: E731
        for label, x, c, kind, _, dx in pts:
            s.line(X(x) + dx, Y(clip(c["lo"])), X(x) + dx, Y(clip(c["hi"])), col[kind], 2.0)
        s.circle(X(1), Y(ref), 9, "ink", hollow=True)
        for label, x, c, kind, (ox, oy, anchor), dx in pts:
            cx, cy = X(x) + dx, Y(c["est"])
            s.circle(cx, cy, 5.5, col[kind])
            parts = label.split("|")
            if anchor in ("top", "top2"):       # above the upper end of the interval
                for li, part in enumerate(parts):
                    s.text(cx, Y(clip(c["hi"])) - 8 - 17 * (len(parts) - 1 - li), part, 13, "middle", "ink")
            elif anchor == "bottom":            # below the lower end of the interval
                s.text(cx, Y(clip(c["lo"])) + 19, parts[0], 13, "middle", "ink")
            else:
                s.text(cx + ox, cy + oy, parts[0], 13, anchor, "ink")
        return X, Y

    panel(84, "办公报告题", "和同批的默认比", left, (0.2, 3.6), (0.25, 0.5, 1, 2, 3), (-15.0, 9.0), (-12, -8, -4, 0, 4, 8), False,
          "写对的事实之差（个百分点，63 条）", "费用是默认的几倍（对数刻度）", -8, "质量不差的下限（−8）", "right")
    panel(84 + pw_ + 104, "大型编码题", "题面要求不复核；和 K=8、深度 1 比", right, (0.45, 1.3), (0.5, 0.75, 1, 1.25), (0.8, 3.6), (1, 1.5, 2, 3), True,
          "用时是默认的几倍（对数刻度）", "费用是默认的几倍（对数刻度）", 1.25, "时间不差的上限（×1.25）", "left")
    s.save(out / "conclusion-tradeoff.svg")
    print("conclusion-tradeoff:", [(p_[0], round(p_[1], 2), round(p_[2]["est"], 2)) for p_ in left], [(p_[0], round(p_[1], 2), round(p_[2]["est"], 2)) for p_ in right])


# ---------------------------------------------------------------------------------- K = 4 against K = 8, by task
def k4_fig(D: dict, out: Path) -> None:
    """k4-by-task.svg: K = 4 against K = 8 on every kind of task that ran both, one row per task: how many subagents the
    two settings start, the difference in quality, and three ratios: cost, the time until every file is written (the
    coding tasks) and the time to the final answer. The cells are those of the uniform rule (clean_extra.limits)."""
    import clean_extra as ce
    L = ce.limits(D)
    LK = {r["key"]: r for r in L["k"]}
    cell = lambda key: ce.rule_cells(LK[key])[4]  # noqa: E731
    b = D["build"]
    mtb = ce.mechanism()["tools_by_batch"]
    kids = lambda cells: sum(mtb[b_][g_]["children"] for b_, g_ in cells) / sum(mtb[b_][g_]["runs"] for b_, g_ in cells)  # noqa: E731
    pair = lambda batches, g4, g8: (kids([(b_, g4) for b_ in batches]), kids([(b_, g8) for b_ in batches]))  # noqa: E731
    rows = [  # label, (subagents at K = 4, at K = 8), quality, cost, files written, answer
        ("办公报告题", pair(("main-office", "office-confirm"), "D1-K4", "D1-K8"), cell("office")["legacy"], cell("office")["c"], None, cell("office")["t"]),
        ("评测集填表题", pair(("ws-k4",), "W-D1-K4", "W-D1-K8"), cell("ws")["q"], cell("ws")["c"], None, cell("ws")["t"]),
        ("评测集报告题", pair(("drb2-k4",), "W-D1-K4", "W-D1-K8"), cell("drb2")["q"], cell("drb2")["c"], None, cell("drb2")["t"]),
        ("读代码题和小编程题", pair(("main-code",), "E-D1-K4", "E-D1-K8"), cell("code")["q"], cell("code")["c"], None, cell("code")["t"]),
        ("不限时 24 题", pair(("ctl-free", "ctl-free-b2"), "W-E-D1-K4", "W-E-D1-K8"), cell("free")["q"], cell("free")["c"], b["free"]["cmp"]["K4"]["all_written_s"], cell("free")["t"]),
        ("大型编码题（默认，写完会复核）", pair(("xl-main",), "W-D1-K4", "W-D1-K8"), cell("xl")["q"], cell("xl")["c"], b["xl"]["cmp"]["NK4"]["all_written_s"], cell("xl")["t"]),
        ("大型编码题（题面要求不复核）", pair(("xl-main",), "W-N-D1-K4", "W-N-D1-K8"), cell("xln")["q"], cell("xln")["c"], b["xl"]["cmp"]["K4"]["all_written_s"], cell("xln")["t"]),
    ]
    heads = {0: "调研类任务：模型只开三四个", 3: "代码类任务"}
    row_h, top = 34, 64
    n_lines = len(rows) + len(heads)
    H = top + row_h * n_lines + 58
    s = pb.Svg(W, H)
    x_label, x_kids = 16, 292
    panels = [("质量之差", 352, 462, "diff", (-8.0, 8.0), (-5, 0, 5), 2),
              ("费用", 496, 612, "ratio", (0.45, 1.5), (0.5, 0.7, 1, 1.4), 3),
              ("文件写完的时间", 648, 752, "ratio", (0.8, 2.4), (1, 1.5, 2), 4),
              ("到最终回答的时间", 788, 904, "ratio", (0.55, 2.0), (0.6, 1, 1.5), 5)]
    bottom = top + row_h * n_lines - 10
    s.text(x_kids, 20, "开几个 subagent", 13.5, "middle", "ink", 600)
    s.text(x_kids, 38, "K=4 → K=8", 12, "middle", "muted")
    y = top
    for i, row in enumerate(rows):
        if i in heads:
            s.text(x_label, y + 5, heads[i], 14, color="ink", weight=700)
            s.line(x_label, y + 13, W - 12, y + 13, "grid")
            y += row_h
        s.text(x_label + 10, y + 5, row[0], 13.5, color="ink")
        s.text(x_kids, y + 5, f"{hu(row[1][0])} → {hu(row[1][1])}", 13.5, "middle", "ink2")
        y += row_h
    for title, x0, x1, kind, (lo, hi), ticks, col in panels:
        s.text((x0 + x1) / 2, 26, title, 14, "middle", "ink", 600)
        X = (lambda v, x0=x0, x1=x1, lo=lo, hi=hi: x0 + (x1 - x0) * (v - lo) / (hi - lo)) if kind == "diff" else \
            (lambda v, x0=x0, x1=x1, lo=lo, hi=hi: x0 + (x1 - x0) * (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo)))
        ref = 0 if kind == "diff" else 1
        for t in ticks:
            s.line(X(t), top - 18, X(t), bottom, "axis" if t == ref else "grid", 1.6 if t == ref else 1)
            s.text(X(t), bottom + 20, (sgn(t, 0) if t else "0") if kind == "diff" else f"×{t:g}", 12, "middle", "muted")
        y = top
        for i, row in enumerate(rows):
            if i in heads:
                y += row_h
            c_ = row[col]
            if c_ is None:
                s.text(X(ref), y + 5, "—", 13, "middle", "muted")
                y += row_h
                continue
            strong = not (c_["lo"] <= ref <= c_["hi"])
            if kind == "diff" and "大型编码题" in row[0] and c_.get("p") is not None and c_["p"] >= 0.05:
                strong = False  # scores next to full marks: the exact sign-flip test decides, not the t interval
            a, z = max(c_["lo"], lo), min(c_["hi"], hi)
            if c_["hi"] > c_["lo"]:
                s.line(X(a), y, X(z), y, "l1" if strong else "pre", 2.6)
            s.circle(X(min(max(c_["est"], lo), hi)), y, 5.2, "l1" if strong else "pre", hollow=not strong)
            y += row_h
        s.text((x0 + x1) / 2, H - 14, "K=4 − K=8" if kind == "diff" else "K=4 ÷ K=8", 12.5, "middle", "ink2")
    s.circle(x_label + 6, H - 18, 5.2, "l1")
    s.text(x_label + 17, H - 13, "蓝色：区间不含 0（倍数是不含 1）；空心：含", 12, "start", "muted")
    s.save(out / "k4-by-task.svg")
    print("k4-by-task:", [(r[0], round(r[1][0], 1), round(r[1][1], 1), round(r[3]["est"], 2), round(r[5]["est"], 2)) for r in rows])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=EXP / "results" / "analysis-clean")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    D = cd.load()
    summary(D, a.out)
    task_figures(D, a.out)
    office_tradeoff(D, a.out)
    office_repeats(D, a.out)
    office_levels(D, a.out)
    office_search(D, a.out)
    cost_distribution(D, a.out)
    cost_subagents(D, a.out)
    cost_by_limits(D, a.out)
    public_figs(a.out)
    coverage_grid(a.out)
    fact_strata_fig(a.out)
    merge_cover_fig(a.out)
    price_ladder_fig(D, a.out)
    relay_fig(a.out)
    scorecard_fig(a.out)
    pages_fig(a.out)
    metric_figs(D, a.out)
    deliver_fig(a.out)
    xl_k_fig(a.out)
    overlap_fig(a.out)
    rejects_fig(a.out)
    senders_fig(a.out)
    tree_figs(a.out)
    conclusion_fig(D, a.out)
    k4_fig(D, a.out)
    import clean_extra as ce
    if ce.TOLD_READY():
        told_fig(a.out)
    print("wrote", sorted(p.name for p in a.out.glob("*.svg")))


if __name__ == "__main__":
    main()
