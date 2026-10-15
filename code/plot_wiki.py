#!/usr/bin/env python3
"""Figures for the two code-building tasks in the style of the wiki page's figures (scripts/plot_extra.py):
small panels of bars, one bar per group, value on top, thin line = 95% t interval of the group mean, the
no-delegation group as a dashed reference line. Same SVG helpers and colours as plot_brief.

  24 independent exercises without a time limit  results/analysis-ctl-free-all/rows.csv
  48-module package                             results/analysis-xl-main/rows-all.csv (when it exists)

Per task: time to the final answer and model cost "by K at fixed depth" and "by depth at fixed K", and the
subagents per run by nesting level. Runs without a final answer are left out of the time figures.

Usage: plot_wiki.py [--out results/analysis-wiki]      then: bash scripts/render-brief.sh results/analysis-wiki
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics as st
import sys
from pathlib import Path

from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plot_brief as pb  # noqa: E402

EXP = pb.b.EXP
FREE = EXP / "results/analysis-ctl-free-all/rows.csv"
XL = EXP / "results/analysis-xl-main/rows-all.csv"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def minutes(r):
    if r.get("no_answer") == "1" or r.get("final_event") == "0":
        return None
    v = num(r.get("answer_s"))
    return None if v is None else v / 60


METRIC = {"minutes": minutes, "cost": lambda r: num(r.get("model_cost_peak")), "score": lambda r: num(r.get("score")),
          "right_pct": lambda r: num(r.get("right_pct")), "right_n": lambda r: num(r.get("right_n")),
          "wrong_firm_n": lambda r: num(r.get("wrong_firm_n"))}
FACTS = EXP / "results/analysis-facts/fact-rows.csv"


def cell(rows, group, metric):
    """(mean, lo, hi, n): 95% t interval of the mean over the group's runs."""
    v = [x for x in (METRIC[metric](r) for r in rows if r["group"] == group) if x is not None]
    if not v:
        return None
    m = st.mean(v)
    if len(v) < 2:
        return m, m, m, len(v)
    h = sps.t.ppf(0.975, len(v) - 1) * st.stdev(v) / math.sqrt(len(v))
    return m, m - h, m + h, len(v)


def nice_max(v):
    for step in (1, 2, 5, 10, 20, 25, 50):
        if v / step <= 5:
            return step * math.ceil(v / step), step
    return 50 * math.ceil(v / 50), 50


def panels_figure(out, name, rows, layout, metric, ylab, footer, ref=None, fmt="{:.1f}", widths=None):
    """layout: [(panel title, [(x label, group, bold)])]; ref: (group, legend text) drawn as a dashed line."""
    npan = len(layout)
    W, H = pb.W, 470
    s = pb.Svg(W, H)
    top, base, gap, x0 = 86, 386, 14, 66
    cells = {g: cell(rows, g, metric) for _, cs in layout for _, g, _ in cs}
    refv = cell(rows, ref[0], metric)[0] if ref else None
    peak = max([c[2] for c in cells.values() if c] + ([refv] if refv else []))
    ymax, step = nice_max(peak * 1.08)
    weights = widths or [len(cs) for _, cs in layout]
    avail = W - x0 - 20 - gap * (npan - 1)
    if ref:
        cur = W - 20 - (15 * len(ref[1]) + 30)
        s.out.append(f'<line x1="{cur:.1f}" y1="20" x2="{cur + 18:.1f}" y2="20" stroke="{pb.C["ink2"]}" stroke-width="2" stroke-dasharray="5,4"/>')
        s.text(cur + 23, 26, ref[1], 15, color="ink")
    s.text(22, (top + base) / 2, ylab, 14, "middle", "ink2", rotate=True)
    Y = lambda v: base - (base - top) * v / ymax  # noqa: E731
    px = x0
    for p_, (title, cs) in enumerate(layout):
        pw = avail * weights[p_] / sum(weights)
        s.text(px + pw / 2, 62, title, 17, "middle", "ink", 600)
        v = 0
        while v <= ymax + 1e-9:
            s.line(px, Y(v), px + pw, Y(v), "grid")
            if p_ == 0:
                s.text(px - 9, Y(v) + 5, f"{v:g}", 13, "end", "muted")
            v += step
        s.line(px, base, px + pw, base, "axis", 1.4)
        if refv is not None:
            s.out.append(f'<line x1="{px:.1f}" y1="{Y(refv):.1f}" x2="{px + pw:.1f}" y2="{Y(refv):.1f}" '
                         f'stroke="{pb.C["ink2"]}" stroke-width="1.6" stroke-dasharray="5,4"/>')
        nb = len(cs)
        bw = min(46, pw / nb * 0.6)
        for j, (xl, grp, bold) in enumerate(cs):
            cx = px + pw * (j + 0.5) / nb
            c = cells[grp]
            if c is None:
                continue
            est, lo, hi, _ = c
            s.rect(cx - bw / 2, Y(est), bw, base - Y(est), "bar")
            s.line(cx, Y(max(lo, 0)), cx, Y(hi), "ink", 2.0)
            s.text(cx, Y(hi) - 8, fmt.format(est), 15, "middle", "ink", 600)
            s.text(cx, base + 26, xl, 16, "middle", "ink", 700 if bold else 400)
        s.text(px + pw / 2, base + 54, footer, 13, "middle", "muted")
        px += pw + gap
    s.save(out / f"{name}.svg")


def behavior_figure(out, name, rows, layout, footer, review=None):
    """Subagents per run (stacked), same drawing as the wiki's behaviour figures: by nesting level, or — with
    review=(column, legend for the others, legend for that column) — split into the subagents counted in that
    column (review subagents) and the rest."""
    npan = len(layout)
    W, H = pb.W, 470
    s = pb.Svg(W, H)
    top, base, gap, x0 = 86, 386, 14, 66
    if review:
        col = review[0]
        rows = [dict(r, _rest=(num(r.get("children")) or 0) - (num(r.get(col)) or 0)) for r in rows]
        keys = [("_rest", review[1], "l1"), (col, review[2], "l2")]
    else:
        keys = [("children_d1", "第 1 层", "l1"), ("children_d2", "第 2 层", "l2")]
    mean = lambda g, k: st.mean(num(r.get(k)) or 0 for r in rows if r["group"] == g)  # noqa: E731
    tot = {g: sum(mean(g, k) for k, _, _ in keys) for _, cs in layout for _, g, _ in cs}
    ymax, step = nice_max(max(tot.values()) * 1.12)
    lw = [15 * len(label) + 46 for _, label, _ in keys]
    lx = W - 20 - sum(lw)
    for i, (_, label, col) in enumerate(keys):
        s.rect(lx + sum(lw[:i]), 12, 16, 16, col, rx=2)
        s.text(lx + sum(lw[:i]) + 23, 26, label, 15, color="ink")
    s.text(22, (top + base) / 2, "每次运行的子代理数", 14, "middle", "ink2", rotate=True)
    weights = [len(cs) for _, cs in layout]
    avail = W - x0 - 20 - gap * (npan - 1)
    px = x0
    for p_, (title, cs) in enumerate(layout):
        pw = avail * weights[p_] / sum(weights)
        s.text(px + pw / 2, 62, title, 17, "middle", "ink", 600)
        v = 0
        while v <= ymax + 1e-9:
            y = base - (base - top) * v / ymax
            s.line(px, y, px + pw, y, "grid")
            if p_ == 0:
                s.text(px - 9, y + 5, f"{v:g}", 13, "end", "muted")
            v += step
        s.line(px, base, px + pw, base, "axis", 1.4)
        nb = len(cs)
        bw = min(46, pw / nb * 0.6)
        for j, (xl, grp, bold) in enumerate(cs):
            cx = px + pw * (j + 0.5) / nb
            y = base
            for k, _, col in keys:
                h = (base - top) * mean(grp, k) / ymax
                s.rect(cx - bw / 2, y - h, bw, h, col)
                y -= h
            s.text(cx, y - 8, f"{tot[grp]:.1f}", 16, "middle", "ink", 600)
            s.text(cx, base + 26, xl, 16, "middle", "ink", 700 if bold else 400)
        s.text(px + pw / 2, base + 54, footer, 13, "middle", "muted")
        px += pw + gap
    s.save(out / f"{name}.svg")


def free_figures(out):
    rows = list(csv.DictReader(open(FREE, encoding="utf-8")))
    g = lambda d, k: f"W-E-D{d}-K{k}"  # noqa: E731
    by_k = [(f"深度上限 {d}" + ("（出厂默认）" if d == 1 else ""), [(f"K={k}", g(d, k), (d, k) == (1, 8)) for k in (1, 2, 4, 8, 16, 64)]) for d in (1, 2)]
    by_d = [(f"K={k}" + ("（出厂默认）" if k == 8 else ""), [(f"深度 {d}", g(d, k), (d, k) == (1, 8)) for d in (1, 2)]) for k in (4, 8, 16, 64)]
    ref = ("D0", "不给委派工具")
    panels_figure(out, "ex24-time-by-k", rows, by_k, "minutes", "到最终回答（分钟）", "同时存活上限", ref)
    panels_figure(out, "ex24-cost-by-k", rows, by_k, "cost", "模型费（元/次）", "同时存活上限", ref, fmt="{:.2f}")
    panels_figure(out, "ex24-time-by-d", rows, by_d, "minutes", "到最终回答（分钟）", "深度上限", ref)
    panels_figure(out, "ex24-cost-by-d", rows, by_d, "cost", "模型费（元/次）", "深度上限", ref, fmt="{:.2f}")
    behavior_figure(out, "ex24-behavior", rows, by_k, "同时存活上限")
    behavior_figure(out, "ex24-review", rows, by_k, "同时存活上限", review=("children_after_all_written", "写题的", "题都写完以后才派的"))


def xl_figures(out):
    rows = list(csv.DictReader(open(XL, encoding="utf-8")))
    by_k = [("原题面", [(f"K={k}", f"W-D1-K{k}", k == 8) for k in (4, 8, 16)]),
            ("题面加一句“不复核”", [(f"K={k}", f"W-N-D1-K{k}", False) for k in (1, 2, 4, 8, 16)])]
    by_d = [("原题面，K=8", [("深度 1", "W-D1-K8", True), ("深度 2", "W-D2-K8", False)]),
            ("题面加一句“不复核”，K=8", [("深度 1", "W-N-D1-K8", False), ("深度 2", "W-N-D2-K8", False)])]
    ref = ("D0", "不给委派工具")
    panels_figure(out, "pkg48-time-by-k", rows, by_k, "minutes", "到最终回答（分钟）", "同时存活上限（深度 1）", ref)
    panels_figure(out, "pkg48-cost-by-k", rows, by_k, "cost", "模型费（元/次）", "同时存活上限（深度 1）", ref, fmt="{:.1f}")
    panels_figure(out, "pkg48-time-by-d", rows, by_d, "minutes", "到最终回答（分钟）", "深度上限", ref)
    panels_figure(out, "pkg48-cost-by-d", rows, by_d, "cost", "模型费（元/次）", "深度上限", ref, fmt="{:.1f}")
    both = [(t, cs + (d[1] if i < 2 else [])) for i, ((t, cs), d) in enumerate(zip(by_k, by_d))]
    behavior_figure(out, "pkg48-behavior", rows,
                    [("原题面", [(f"K={k}", f"W-D1-K{k}", k == 8) for k in (4, 8, 16)] + [("深度 2·K=8", "W-D2-K8", False)]),
                     ("题面加一句“不复核”", [(f"K={k}", f"W-N-D1-K{k}", False) for k in (1, 2, 4, 8, 16)] + [("深度 2·K=8", "W-N-D2-K8", False)])],
                    "同时存活上限")
    del both
    behavior_figure(out, "pkg48-review", rows,
                    [("原题面", [(f"K={k}", f"W-D1-K{k}", k == 8) for k in (4, 8, 16)] + [("深度 2·K=8", "W-D2-K8", False)]),
                     ("题面加一句“不复核”", [(f"K={k}", f"W-N-D1-K{k}", False) for k in (1, 2, 4, 8, 16)] + [("深度 2·K=8", "W-N-D2-K8", False)])],
                    "同时存活上限", review=("review_kids", "写代码的", "复核的"))


def facts_figures(out):
    """Office reports re-graded against the fact lists: % of the listed facts stated correctly, by K and by depth
    (same layout as the wiki's office figures: one panel per depth / per K, 20 reports per bar)."""
    rows = list(csv.DictReader(open(FACTS, encoding="utf-8")))
    by_k = [(f"深度上限 {d}" + ("（出厂默认）" if d == 1 else ""), [(f"K={k}", f"D{d}-K{k}", (d, k) == (1, 8)) for k in (1, 2, 4, 8)]) for d in (1, 2, 3)]
    by_d = [(f"K={k}" + ("（出厂默认）" if k == 8 else ""), [(f"深度 {d}", f"D{d}-K{k}", (d, k) == (1, 8)) for d in (1, 2, 3)]) for k in (1, 2, 4, 8)]
    ref = ("D0", "不给委派工具")
    panels_figure(out, "office-facts-by-k", rows, by_k, "right_pct", "写对的事实条目（%）", "同时存活上限", ref)
    panels_figure(out, "office-facts-by-d", rows, by_d, "right_pct", "写对的事实条目（%）", "深度上限", ref)
    panels_figure(out, "office-wrong-by-k", rows, by_k, "wrong_firm_n", "写错的条目数（没标待核验）", "同时存活上限", ref, fmt="{:.2f}")


CONFIRM = EXP / "results/analysis-facts-confirm/fact-rows.csv"


def confirm_figures(out):
    """Confirmation batch (240 new office runs): % of the listed facts stated correctly, K at depth 1 and depth 2 at K = 8."""
    rows = list(csv.DictReader(open(CONFIRM, encoding="utf-8")))
    layout = [("深度上限 1（出厂默认）", [(f"K={k}", f"D1-K{k}", k == 8) for k in (1, 2, 4, 8)]), ("深度上限 2", [("K=8", "D2-K8", False)])]
    panels_figure(out, "office-facts-confirm", rows, layout, "right_pct", "写对的事实条目（%）", "同时存活上限", ("D0", "不给委派工具"), widths=[4, 1.4])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=EXP / "results" / "analysis-wiki")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    free_figures(a.out)
    if XL.exists():
        xl_figures(a.out)
    if FACTS.exists():
        facts_figures(a.out)
    if CONFIRM.exists():
        confirm_figures(a.out)
    print("wrote", sorted(p.name for p in a.out.glob("*.svg")))


if __name__ == "__main__":
    main()
