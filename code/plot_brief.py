#!/usr/bin/env python3
"""The four figures of the short report (report-brief), as hand-written SVG (no matplotlib).

Each figure holds the chart only: bars or points, axes, category labels and a colour legend. Titles, reading notes and
every table of numbers live in the report body (build_brief.py), not in the image. The canvas is about 920 px wide so
that the labels stay readable at document width.

  fig1-behavior.svg     subagents per run by nesting level in each D x K cell (office tasks)
  fig2-contrasts.svg    the contrasts of the two "what if the default changes" tables: score difference with its 95%
                        interval and the +-5 band
  fig3-controls.svg     the two control tasks: mean score per group with the min-max range
  fig4-sensitivity.svg  the judge's score change when a report is degraded in a known way

Reads the analysis outputs through build_report's loaders, so the numbers are the report's numbers. Like the report,
the office figures count only runs that handed in a complete report (results/analysis-complete).
Usage: plot_brief.py [--out results/analysis-brief]     then bash scripts/render-brief.sh
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_report as b  # noqa: E402
from v2_tables import mean_by_task  # noqa: E402

FONT = 'system-ui, -apple-system, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif'
C = {"ink": "#111111", "ink2": "#4a4946", "muted": "#8a8882", "grid": "#e4e3dc", "axis": "#bdbcb2", "l1": "#2a78d6",
     "l2": "#eb6834", "l3": "#eda100", "band": "#e3f3e6", "pre": "#1f1f1f", "post": "#8a8882", "good": "#2e8f5c",
     "bad": "#c9463d", "bar": "#5b8fd9", "bar2": "#9bbce8"}
OFF = b.OFF
W = 920


def esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    def __init__(self, w: int, h: int):
        self.w, self.h, self.out = w, h, []

    def text(self, x, y, s, size=14, anchor="start", color="ink2", weight=400, rotate=False):
        tr = f' transform="rotate(-90 {x:.1f} {y:.1f})"' if rotate else ""
        self.out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{C[color]}" '
                        f'font-weight="{weight}"{tr}>{esc(s)}</text>')

    def rect(self, x, y, w, h, color, rx=0, opacity=1.0):
        self.out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" fill="{C.get(color, color)}" '
                        f'rx="{rx}" opacity="{opacity}"/>')

    def line(self, x1, y1, x2, y2, color="axis", width=1.0):
        self.out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{C.get(color, color)}" '
                        f'stroke-width="{width}"/>')

    def circle(self, x, y, r, color, hollow=False):
        fill = "#ffffff" if hollow else C.get(color, color)
        self.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{C.get(color, color)}" stroke-width="2.4"/>')

    def save(self, path: Path):
        body = "\n".join(self.out)
        path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
                        f'font-family=\'{FONT}\'>\n<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>\n{body}\n</svg>\n',
                        encoding="utf-8")


def fig_behavior(rows, out: Path):
    H = 470
    s = Svg(W, H)
    top, base, ymax = 86, 386, 9.0
    x0, pw, gap = 66, 270, 14
    lx = W - 318
    for i, (name, col) in enumerate((("第 1 层", "l1"), ("第 2 层", "l2"), ("第 3 层", "l3"))):
        s.rect(lx + i * 106, 12, 16, 16, col, rx=2)
        s.text(lx + i * 106 + 23, 26, name, 15, color="ink")
    s.text(22, (top + base) / 2, "每次运行的子代理数", 14, "middle", "ink2", rotate=True)
    for p_, d in enumerate((1, 2, 3)):
        px = x0 + p_ * (pw + gap)
        s.text(px + pw / 2, 62, f"深度上限 {d}" + ("（出厂默认）" if d == 1 else ""), 17, "middle", "ink", 600)
        for v in (0, 2, 4, 6, 8):
            y = base - (base - top) * v / ymax
            s.line(px, y, px + pw, y, "grid")
            if p_ == 0:
                s.text(px - 9, y + 5, str(v), 13, "end", "muted")
        s.line(px, base, px + pw, base, "axis", 1.4)
        for j, k in enumerate((1, 2, 4, 8)):
            g = [r for r in rows if r["task"] in OFF and r["group"] == f"D{d}-K{k}"]
            cx = px + pw * (j + 0.5) / 4
            bw, y = 46, base
            for col, key in (("l1", "children_d1"), ("l2", "children_d2"), ("l3", "children_d3")):
                v = mean_by_task(g, key) or 0.0
                h = (base - top) * v / ymax
                s.rect(cx - bw / 2, y - h, bw, h, col)
                y -= h
            s.text(cx, y - 8, f"{mean_by_task(g, 'children'):.1f}", 16, "middle", "ink", 600)
            s.text(cx, base + 26, f"K={k}", 16, "middle", "ink", 700 if (d, k) == (1, 8) else 400)
        s.text(px + pw / 2, base + 54, "同时存活上限", 13, "middle", "muted")
    s.save(out / "fig1-behavior.svg")


def fig_contrasts(items, out: Path):
    """items: ("header", text) or (label, est, lo, hi, kind) with kind "pre" (written before the run) or "post"."""
    row_h, top = 31, 30
    H = top + row_h * len(items) + 62
    s = Svg(W, H)
    x0, x1, lo, hi = 372, W - 24, -16.0, 14.0

    def X(v):
        return x0 + (x1 - x0) * (v - lo) / (hi - lo)

    bottom = top + row_h * len(items) - 6
    s.rect(X(-5), top - 16, X(5) - X(-5), bottom - top + 16, "band")
    for v in (-15, -10, -5, 0, 5, 10):
        s.line(X(v), top - 16, X(v), bottom, "grid" if v else "axis", 1 if v else 1.6)
        s.text(X(v), bottom + 20, f"{v:+d}" if v else "0", 13, "middle", "muted")
    s.text((x0 + x1) / 2, bottom + 46, "得分差（分）", 14, "middle", "ink2")
    y = top
    for it in items:
        if it[0] == "header":
            s.text(16, y + 5, it[1], 15, color="ink", weight=700)
            s.line(16, y + 13, W - 16, y + 13, "grid")
        else:
            label, est, a, c, kind = it
            s.text(28, y + 5, label, 14, color="ink")
            col = "pre" if kind == "pre" else "post"
            s.line(X(max(a, lo)), y, X(min(c, hi)), y, col, 2.8)
            s.circle(X(est), y, 5.5, col, hollow=(kind != "pre"))
        y += row_h
    s.save(out / "fig2-contrasts.svg")


def fig_controls(f, out: Path):
    H = 392
    s = Svg(W, H)
    g = f["g"]
    panels = ((b.PW, "对照·宽：24 道独立练习，限时 3 分钟"), (b.N1, "对照·串：16 步，每步依赖上一步"))
    names = {"D0": "不给委派工具", "W-D1-K8": "出厂默认", "W-E-D1-K8": "默认 + 鼓励并行"}
    top, base = 72, 330
    s.text(20, (top + base) / 2, "得分", 14, "middle", "ink2", rotate=True)
    for p, (task, title) in enumerate(panels):
        pw = 400
        px = 62 + p * (pw + 44)
        s.text(px + pw / 2, 28, title, 16, "middle", "ink", 600)
        for v in (0, 25, 50, 75, 100):
            y = base - (base - top) * v / 100
            s.line(px, y, px + pw, y, "grid")
            if p == 0:
                s.text(px - 9, y + 5, str(v), 13, "end", "muted")
        s.line(px, base, px + pw, base, "axis", 1.4)
        for j, grp in enumerate(b.CTL_GROUPS):
            sc = [float(r["score"]) for r in g(task, grp)]
            cx = px + pw * (j + 0.5) / 3
            bw, m = 74, st.mean(sc)
            s.rect(cx - bw / 2, base - (base - top) * m / 100, bw, (base - top) * m / 100, "bar" if grp != "D0" else "bar2")
            s.line(cx, base - (base - top) * min(sc) / 100, cx, base - (base - top) * max(sc) / 100, "ink", 2.2)
            s.text(cx, base - (base - top) * max(sc) / 100 - 9, f"{m:.1f}", 17, "middle", "ink", 600)
            s.text(cx, base + 26, names[grp], 14, "middle", "ink")
    s.save(out / "fig3-controls.svg")


def fig_sensitivity(sens, out: Path):
    sm = sens["summary"]
    order = (("same", "原样重打（对照）"), ("tail20", "删掉最后 20%"), ("nolinks", "删掉全部来源链接"), ("half", "删掉后一半"),
             ("wrong", "把事实改错"))
    top, row = 22, 50
    H = top + row * len(order) + 62
    s = Svg(W, H)
    x0, x1, lo, hi = 230, W - 30, -75.0, 10.0

    def X(v):
        return x0 + (x1 - x0) * (v - lo) / (hi - lo)

    bottom = top + row * len(order)
    for v in (-70, -60, -50, -40, -30, -20, -10, 0, 10):
        s.line(X(v), top - 8, X(v), bottom, "grid" if v else "axis", 1 if v else 1.6)
        s.text(X(v), bottom + 20, f"{v:+d}" if v else "0", 13, "middle", "muted")
    s.text((x0 + x1) / 2, bottom + 46, "得分变化（分）", 14, "middle", "ink2")
    for i, (key, name) in enumerate(order):
        v = sm[key]
        y = top + row * i + 22
        s.text(x0 - 62, y + 5, name, 15, "end", "ink")
        m = v["mean_diff"]
        s.rect(min(X(m), X(0)), y - 12, abs(X(m) - X(0)), 24, "bad" if m < -8 else "muted", rx=2)
        s.line(X(v["min_diff"]), y, X(v["max_diff"]), y, "ink", 2.2)
        s.text(X(min(v["min_diff"], m)) - 10, y + 5, b.sgn(m), 16, "end", "ink", 600)
    s.save(out / "fig4-sensitivity.svg")


def fig_dk(rows, out: Path):
    """Experiment 5: score by K for depth 1 and 2 on the wide control task, one panel per time limit; D0 as a line."""
    H = 420
    s = Svg(W, H)
    panels = (("pw-exercises", "时限 3 分钟"), ("pw-exercises-120", "时限 2 分钟"))
    ks = (1, 2, 4, 8, 16)
    top, base = 78, 340
    lx = W - 430
    for i, (name, col) in enumerate((("深度 1", "bar"), ("深度 2", "l2"))):
        s.rect(lx + i * 110, 10, 16, 16, col, rx=2)
        s.text(lx + i * 110 + 23, 24, name, 15, color="ink")
    s.out.append(f'<line x1="{lx + 226}" y1="18" x2="{lx + 262}" y2="18" stroke="{C["ink2"]}" stroke-width="1.8" stroke-dasharray="6 4"/>')
    s.text(lx + 270, 24, "不给委派工具", 15, color="ink")
    s.text(20, (top + base) / 2, "得分", 14, "middle", "ink2", rotate=True)

    def sc(task, grp):
        return [float(r["score"]) for r in rows if r["task"] == task and r["group"] == grp and r["score"] not in ("", None)]

    for p_, (task, title) in enumerate(panels):
        pw = 400
        px = 62 + p_ * (pw + 44)
        s.text(px + pw / 2, 52, title, 16, "middle", "ink", 600)
        for v in (0, 25, 50, 75, 100):
            y = base - (base - top) * v / 100
            s.line(px, y, px + pw, y, "grid")
            if p_ == 0:
                s.text(px - 9, y + 5, str(v), 13, "end", "muted")
        s.line(px, base, px + pw, base, "axis", 1.4)
        d0 = sc(task, "D0")
        if d0:
            y0 = base - (base - top) * st.mean(d0) / 100
            s.out.append(f'<line x1="{px:.1f}" y1="{y0:.1f}" x2="{px + pw:.1f}" y2="{y0:.1f}" stroke="{C["ink2"]}" stroke-width="1.6" stroke-dasharray="6 4"/>')
        for j, k in enumerate(ks):
            cx = px + pw * (j + 0.5) / len(ks)
            for i, (dd, col) in enumerate(((1, "bar"), (2, "l2"))):
                v = sc(task, f"W-E-D{dd}-K{k}")
                if not v:
                    continue
                m, bw = st.mean(v), 30
                bx = cx - bw - 1 if i == 0 else cx + 1
                s.rect(bx, base - (base - top) * m / 100, bw, (base - top) * m / 100, col)
                s.line(bx + bw / 2, base - (base - top) * min(v) / 100, bx + bw / 2, base - (base - top) * max(v) / 100, "ink", 2)
                s.text(bx + bw / 2, base + 20, f"{m:.0f}", 13, "middle", "ink", 600)
            s.text(cx, base + 44, f"K={k}", 15, "middle", "ink", 700 if k == 8 else 400)
        s.text(px + pw / 2, base + 68, "同时存活上限", 13, "middle", "muted")
    s.save(out / "fig5-dk.svg")


def fig_free(rows, out: Path):
    """The wide control task without a time limit (depth 1 groups): for each group the median time until every
    exercise had been written once and the median time until the root's final answer."""
    H = 430
    s = Svg(W, H)
    groups = [("D0", "不给\n委派工具"), ("W-D1-K8", "出厂默认\n不加鼓励"), ("W-E-D1-K1", "鼓励\nK=1"), ("W-E-D1-K2", "鼓励\nK=2"),
              ("W-E-D1-K4", "鼓励\nK=4"), ("W-E-D1-K8", "鼓励\nK=8"), ("W-E-D1-K16", "鼓励\nK=16"), ("W-E-D1-K64", "鼓励\nK=64")]
    top, base, left = 60, 330, 70
    ymax = 20
    lx = W - 470
    for i, (name, col) in enumerate((("24 道题都写过一遍", "bar"), ("给出最终回答", "l2"))):
        s.rect(lx + i * 220, 12, 16, 16, col, rx=2)
        s.text(lx + i * 220 + 23, 26, name, 15, color="ink")
    s.text(22, (top + base) / 2, "分钟（中位数）", 14, "middle", "ink2", rotate=True)
    for v in (0, 5, 10, 15, 20):
        y = base - (base - top) * v / ymax
        s.line(left, y, W - 20, y, "grid")
        s.text(left - 9, y + 5, str(v), 13, "end", "muted")
    s.line(left, base, W - 20, base, "axis", 1.4)

    def med(g, col):
        v = [float(r[col]) / 60 for r in rows if r["group"] == g and r.get(col) not in ("", None)]
        return st.median(v) if v else None

    pw = (W - 20 - left) / len(groups)
    for j, (g, label) in enumerate(groups):
        cx = left + pw * (j + 0.5)
        for i, (col, color) in enumerate((("all_written_s", "bar"), ("answer_s", "l2"))):
            m = med(g, col)
            if m is None:
                continue
            bw = 34
            bx = cx - bw - 1 if i == 0 else cx + 1
            h = (base - top) * min(m, ymax) / ymax
            s.rect(bx, base - h, bw, h, color)
            s.text(bx + bw / 2, base - h - 6, f"{m:.1f}", 13, "middle", "ink", 600)
        for n, part in enumerate(label.split("\n")):
            s.text(cx, base + 22 + n * 20, part, 14, "middle", "ink")
    s.save(out / "fig6-free.svg")


def fig_xl(rows, out: Path):
    """The 48-module package (supplementary experiment 7): for each group the median time until all 61 package files
    had been written once and the median time until the root's final answer."""
    H = 450
    s = Svg(W, H)
    groups = [("D0", "不给\n委派工具"), ("W-D1-K4", "K=4"), ("W-D1-K8", "K=8"), ("W-D1-K16", "K=16"), ("W-D2-K8", "深度 2\nK=8"),
              ("W-N-D1-K1", "K=1"), ("W-N-D1-K2", "K=2"), ("W-N-D1-K4", "K=4"), ("W-N-D1-K8", "K=8"), ("W-N-D1-K16", "K=16"),
              ("W-N-D2-K8", "深度 2\nK=8")]
    top, base, left = 60, 320, 70

    def med(g, col):
        v = [float(r[col]) / 60 for r in rows if r["group"] == g and r.get(col) not in ("", None)]
        return st.median(v) if v else None

    peak = max((med(g, c) or 0) for g, _ in groups for c in ("all_written_s", "answer_s"))
    ymax = 10 * math.ceil((peak + 2) / 10)
    lx = W - 470
    for i, (name, col) in enumerate((("61 个文件都写过一遍", "bar"), ("给出最终回答", "l2"))):
        s.rect(lx + i * 220, 12, 16, 16, col, rx=2)
        s.text(lx + i * 220 + 23, 26, name, 15, color="ink")
    s.text(22, (top + base) / 2, "分钟（中位数）", 14, "middle", "ink2", rotate=True)
    for v in range(0, ymax + 1, 10):
        y = base - (base - top) * v / ymax
        s.line(left, y, W - 20, y, "grid")
        s.text(left - 9, y + 5, str(v), 13, "end", "muted")
    s.line(left, base, W - 20, base, "axis", 1.4)
    pw = (W - 20 - left) / len(groups)
    for j, (g, label) in enumerate(groups):
        cx = left + pw * (j + 0.5)
        for i, (col, color) in enumerate((("all_written_s", "bar"), ("answer_s", "l2"))):
            m = med(g, col)
            if m is None:
                continue
            bw = 27
            bx = cx - bw - 1 if i == 0 else cx + 1
            h = (base - top) * min(m, ymax) / ymax
            s.rect(bx, base - h, bw, h, color)
            s.text(bx + bw / 2, base - h - 6, f"{m:.1f}", 12, "middle", "ink", 600)
        for n, part in enumerate(label.split("\n")):
            s.text(cx, base + 22 + n * 19, part, 14, "middle", "ink")
    # the two prompt conditions, under the group labels
    y = base + 78
    for a_, b_, text in ((1, 4, "原题面"), (5, 10, "题面加不复核句")):
        x1, x2 = left + pw * a_ + 8, left + pw * (b_ + 1) - 8
        s.line(x1, y, x2, y, "axis", 1.2)
        s.text((x1 + x2) / 2, y + 22, text, 15, "middle", "ink", 600)
    s.save(out / "fig7-xl.svg")


def contrast_items(so, sc2, scf, dep) -> list:
    """The rows of the two "what if the default changes" tables, in the tables' order (changed minus default)."""
    def it(label, c, kind="pre", flip=False):
        est, lo, hi = (-c["est"], -c["hi"], -c["lo"]) if flip else (c["est"], c["lo"], c["hi"])
        return (label, est, lo, hi, kind)

    S = lambda k: b.cmp_(so, "score", k)      # noqa: E731
    Cc = lambda k: b.cmp_(sc2, "score", k)    # noqa: E731
    return [("header", "办公题（基准：深度 1、K=8）"),
            it("K 8 → 4", S("H2c")), it("K 8 → 2", S("H2b")), it("K 8 → 1", S("H2a")),
            it("深度 1 → 2", S("H3a")), it("深度 1 → 3", S("H3b")),
            it("深度 1 → 2（K=4、8 合并）", b.cmp_(dep, "score", "PD2"), "post"),
            it("深度 1 → 3（K=4、8 合并）", b.cmp_(dep, "score", "PD3"), "post"),
            it("不给委派工具", S("H1"), flip=True),
            ("header", "代码题 c1、w1"),
            it("不给委派工具（不加鼓励）", Cc("C1"), flip=True),
            it("题面加一句鼓励并行", Cc("C2")),
            it("K 8 → 4（鼓励并行）", Cc("C3c")), it("K 8 → 2（鼓励并行）", Cc("C3b")), it("K 8 → 1（鼓励并行）", Cc("C3a")),
            it("深度 1 → 2（鼓励并行）", Cc("C4a")), it("深度 1 → 3（鼓励并行）", Cc("C4b")),
            it("K 8 → 1（鼓励并行，三个深度合并）", b.cmp_(scf, "score", "FK1"), "post")]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=b.EXP / "results" / "analysis-brief")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    CA = b.EXP / "results/analysis-complete"
    rows = list(csv.DictReader(open(CA / "rows-complete.csv", encoding="utf-8")))
    so, scf, sc2 = b.read_json(CA / "stats-office.json"), b.load("stats-code-factorial-c1w1.json"), b.load("stats-code-c1w1.json")
    dep = b.read_json(CA / "stats-office-depth-k48.json")
    cf = b.ctl_facts(b.ctl_load())
    sens = b.read_json(b.EXP / "results/validate-degrade/sensitivity.json")
    fig_behavior(rows, a.out)
    fig_contrasts(contrast_items(so, sc2, scf, dep), a.out)
    fig_controls(cf, a.out)
    fig_sensitivity(sens, a.out)
    dk = b.EXP / "results/analysis-ctl-dk/rows.csv"
    if dk.exists():
        fig_dk(list(csv.DictReader(open(dk, encoding="utf-8"))), a.out)
    free = b.EXP / "results/analysis-ctl-free-all/rows.csv"
    if free.exists():
        fig_free(list(csv.DictReader(open(free, encoding="utf-8"))), a.out)
    xl = b.EXP / "results/analysis-xl-main/rows-all.csv"
    if xl.exists():
        fig_xl(list(csv.DictReader(open(xl, encoding="utf-8"))), a.out)
    print("wrote", sorted(p.name for p in a.out.glob("*.svg")))


if __name__ == "__main__":
    main()
