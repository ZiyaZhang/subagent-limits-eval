#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The figures of the phase-2 write-up, as hand-written SVG (no matplotlib), from the outputs of phase2_report.py.

One figure holds one message; axes are named in full, cells are written out (no code names on a figure), intervals are
95%. Reading notes and numbers belong in the text, not in the image. Points come from the model with only the two
cells (method mixed2), the same estimate as in the tables; --method joint draws the family's joint model instead.

  fig1-demand.svg        share of runs whose peak of live subagents exceeds k, by kind of task and model
  fig2-cost-quality.svg  every cell of the K x depth grid against the default: money multiple (x) and quality difference (y)
  fig3-k-curves.svg      quality, money, time against K: natural demand, the "8 parts" instruction, the large coding task
  fig4-depth-curves.svg  quality, money, time against depth, one line per K
  fig5-search.svg        inside one task: search requests against quality, coloured by depth
  fig6-mechanism.svg     where the gain comes from: single agent, told to search more, in segments, four merged, instructed 3 / 8, default
  fig7-models.svg        the same four cells on flash and on v4-pro
  fig8-coding-time.svg   large coding task: minutes until all files were written and until the final answer
  fig10-orchestration.svg  prescribed orchestration against the model's own, money and quality
  fig9-behaviors.svg     with --behavior: share of runs in which the judge model marked each behaviour of the checklist, by cell
  fig9b-delegation.svg   with --delegation: what subagents hand on when they delegate (classified by meaning), by cell
  figA-dose.svg          appendix, descriptive: module B, quality against the default on the number of subagents actually opened
  figA-capped.svg        appendix, descriptive: in each capped cell, runs that had a call rejected by the cap and runs that had none
  figA-rejections.svg    appendix, descriptive: rejected delegation calls of a run against its quality relative to the task's default

Usage: phase2_figures.py --in results/analysis-phase2 [--out results/analysis-phase2/figs] [--method mixed2]
       then: bash scripts/render-brief.sh results/analysis-phase2/figs
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics as st
from pathlib import Path

FONT = 'system-ui, -apple-system, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif'
C = {"ink": "#111111", "ink2": "#4a4946", "muted": "#8a8882", "grid": "#e4e3dc", "axis": "#bdbcb2", "l1": "#2a78d6", "l2": "#eb6834",
     "l3": "#eda100", "l4": "#2e8f5c", "l5": "#8b5fc7", "band": "#f3f2ec", "bad": "#c9463d", "bar": "#5b8fd9", "bar2": "#9bbce8", "warn": "#b3261e"}
W = 920
SIM_NOTE = "模拟数据，只为检查脚本，不是结果"


def esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    def __init__(self, w: int, h: int):
        self.w, self.h, self.out = w, h, []

    def text(self, x, y, s, size=14, anchor="start", color="ink2", weight=400, rotate=False):
        tr = f' transform="rotate(-90 {x:.1f} {y:.1f})"' if rotate else ""
        self.out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{C.get(color, color)}" '
                        f'font-weight="{weight}"{tr}>{esc(s)}</text>')

    def rect(self, x, y, w, h, color, rx=0, opacity=1.0):
        self.out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" fill="{C.get(color, color)}" '
                        f'rx="{rx}" opacity="{opacity}"/>')

    def line(self, x1, y1, x2, y2, color="axis", width=1.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{C.get(color, color)}" '
                        f'stroke-width="{width}"{d}/>')

    def path(self, pts, color, width=2.0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.out.append('<polyline fill="none" stroke="%s" stroke-width="%s"%s points="%s"/>'
                        % (C.get(color, color), width, d, " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)))

    def circle(self, x, y, r, color, hollow=False, width=2.2):
        fill = "#ffffff" if hollow else C.get(color, color)
        self.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{C.get(color, color)}" stroke-width="{width}"/>')

    def save(self, path: Path, sim: bool):
        if sim:
            self.rect(0, 0, self.w, 24, "#fdecea")
            self.text(self.w / 2, 17, SIM_NOTE, 13, "middle", "warn", 600)
        body = "\n".join(self.out)
        path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
                        f'font-family=\'{FONT}\'>\n<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>\n{body}\n</svg>\n', encoding="utf-8")
        print("wrote", path)


class Scale:
    """Maps a value to a pixel position; log=True for multiples."""

    def __init__(self, lo, hi, p0, p1, log=False):
        self.lo, self.hi, self.p0, self.p1, self.log = lo, hi, p0, p1, log

    def __call__(self, v):
        if self.log:
            return self.p0 + (self.p1 - self.p0) * (math.log(v) - math.log(self.lo)) / (math.log(self.hi) - math.log(self.lo))
        return self.p0 + (self.p1 - self.p0) * (v - self.lo) / (self.hi - self.lo)

    def clip(self, v):
        return self(min(max(v, self.lo), self.hi))


def name(cell: str) -> str:
    """A cell written out for a reader."""
    fixed = {"D0": "不开 subagent", "K8": "默认（深度 1，K=8）", "more": "单 agent，要求多查", "seg": "单 agent，分 8 段做", "merge4": "四份单 agent 报告合并",
             "planK8": "主 agent 只拆题和汇总"}
    if cell in fixed:
        return fixed[cell]
    if cell.startswith("n3") or cell.startswith("n8"):
        return f"指令拆 {cell[1]} 份，K={cell[3:]}"
    if cell.startswith("K"):
        return f"K={cell[1:]}"
    if cell.startswith("D"):
        d, k = cell[1:].split("K")
        return f"深度 {d}，K={k}"
    return cell


def short(cell: str) -> str:
    return {"D0": "不开", "K8": "默认"}.get(cell, name(cell))


class Data:
    def __init__(self, src: Path, method: str):
        R = lambda f: list(csv.DictReader(open(src / f, encoding="utf-8")))  # noqa: E731
        self.con, self.lev, self.dem, self.runs = R("contrasts.csv"), R("levels.csv"), R("demand.csv"), R("runs_used.csv")
        self.method = method
        self.sim = any(r["id"].startswith("sim-") for r in self.runs)

    def c(self, family, cell, ref, outcome, method=None):
        """(estimate, lower, upper) of a contrast or None."""
        for m in ([method] if method else [self.method, "mixed2", "paired-rep", "paired-t"]):
            for r in self.con:
                if (r["version"], r["family"], r["cell"], r["ref"], r["outcome"], r["method"]) == ("confirmatory", family, cell, ref, outcome, m) and r["estimate"] != "":
                    return float(r["estimate"]), float(r["lower"]), float(r["upper"])
        return None

    def l(self, family, cell, col):  # noqa: E743
        for r in self.lev:
            if r["family"] == family and r["cell"] == cell and r.get(col, "") != "":
                return float(r[col])
        return None


def text_w(text: str, size: float) -> float:
    return sum(size if ord(ch) > 0x2E7F else size * 0.56 for ch in text)


def place_labels(s: Svg, items, obstacles, size=12.5):
    """items: (x, y, text, colour, weight). Each label goes to the candidate position around its point that overlaps the fewest
    labels, markers and interval lines; a label that has to sit away from its point gets a thin leader line."""
    boxes = []
    cands = [(8, -9, "start"), (8, 18, "start"), (-8, -9, "end"), (-8, 18, "end"), (10, 4, "start"), (-10, 4, "end"), (26, -24, "start"),
             (26, 32, "start"), (-26, -24, "end"), (-26, 32, "end"), (44, -42, "start"), (-44, -42, "end"), (44, 50, "start"), (-44, 50, "end"),
             (62, -60, "start"), (-62, -60, "end"), (62, 68, "start"), (-62, 68, "end")]

    def hit(a, b):
        return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

    for x, y, text, color, weight in items:
        w = text_w(text, size)
        best = None
        for i, (dx, dy, anchor) in enumerate(cands):
            left = x + dx - (w if anchor == "end" else (w / 2 if anchor == "middle" else 0))
            box = (left - 2, y + dy - size, left + w + 2, y + dy + 3)
            if box[0] < 4 or box[2] > s.w - 4 or box[1] < 30:
                continue
            score = 20 * sum(hit(box, b) for b in boxes) + sum(wt for o, wt in obstacles if hit(box, o[:4]) and not (wt >= 8 and o[4:] == (x, y))) + 0.3 * i
            if best is None or score < best[0]:
                best = (score, dx, dy, anchor, box)
        if best is None:
            continue
        _, dx, dy, anchor, box = best
        boxes.append(box)
        if abs(dx) > 20:
            s.line(x, y, x + dx - (4 if dx > 0 else -4), y + dy - 4, "axis", 1.0)
        s.text(x + dx, y + dy, text, size, anchor, color, weight)


def whisker(s: Svg, x, y_lo, y_hi, color, width=1.8, cap=4):
    s.line(x, y_lo, x, y_hi, color, width)
    s.line(x - cap, y_lo, x + cap, y_lo, color, width)
    s.line(x - cap, y_hi, x + cap, y_hi, color, width)


def y_axis(s: Svg, sy: Scale, ticks, x0, x1, fmt, zero=None):
    for v in ticks:
        s.line(x0, sy(v), x1, sy(v), "grid")
        s.text(x0 - 8, sy(v) + 5, fmt(v), 13, "end", "muted")
    if zero is not None:
        s.line(x0, sy(zero), x1, sy(zero), "muted", 1.4)


def legend(s: Svg, x, y, items, gap=26):
    """items: (label, colour, hollow)."""
    for label, color, hollow in items:
        s.circle(x, y - 5, 5, color, hollow=hollow)
        s.text(x + 11, y, label, 13, "start", "ink2")
        x += gap + 13.5 * len(label)
    return x


# ------------------------------------------------------------------------------------------------ figures
def fig_demand(d: Data, out: Path):
    lines = list(dict.fromkeys(r["line"] for r in d.dem if r.get("main_figure", "1") in ("1", "")))
    rows_legend = (len(lines) + 1) // 2
    H = 400 + 24 * rows_legend
    s = Svg(W, H)
    x0, x1, y0, y1 = 80, W - 30, H - 88, 62 + 24 * rows_legend
    sx, sy = Scale(0, 16, x0, x1), Scale(0, 100, y0, y1)
    y_axis(s, sy, (0, 25, 50, 75, 100), x0, x1, lambda v: f"{v}%")
    for k in range(0, 17):
        s.line(sx(k), y0, sx(k), y0 + 5, "axis")
        s.text(sx(k), y0 + 22, str(k), 13, "middle", "muted")
    s.line(x0, y0, x1, y0, "axis", 1.4)
    s.text((x0 + x1) / 2, H - 42, "k：同时活着的 subagent 数", 14, "middle", "ink2")
    s.text(22, (y0 + y1) / 2, "峰值超过 k 的运行比例", 14, "middle", "ink2", rotate=True)
    cols = ["l1", "l2", "l4", "l5", "l3", "ink", "bad", "muted"]
    for i, line in enumerate(lines):
        pts = sorted(((int(r["k"]), 100 * float(r["share_above_k"]), r["kind"]) for r in d.dem if r["line"] == line and int(r["k"]) <= 16))
        col = cols[i % len(cols)]
        step = []
        for k, v, _ in pts:
            step += [(sx(k), sy(v))]
        s.path(step, col, 2.2)
        for k, v, kind in pts:
            s.circle(sx(k), sy(v), 3.6, col, hollow=(kind != "peak"))
        legend(s, x0 + (i % 2) * 400, 50 + 24 * (i // 2), [(line, col, False)])
    s.text((x0 + x1) / 2, H - 16, "每条线画到该格的上限为止；上限处的空心点是有调用被上限拒绝的运行比例", 12.5, "middle", "muted")
    s.save(out / "fig1-demand.svg", d.sim)


def fig_cost_quality(d: Data, out: Path, family="A", ref="K8", cells=None, fname="fig2-cost-quality.svg", ref_label="默认（深度 1，K=8）"):
    cells = cells or ["D0", "K1", "K2", "K3", "K4", "D2K2", "D2K4", "D2K8", "D2K16", "D3K2", "D3K4", "D3K8", "D3K16", "D3K64"]
    pts = []
    for c in cells:
        q, m = d.c(family, c, ref, "q"), d.c(family, c, ref, "total_yuan")
        if q and m:
            pts.append((c, q, m))
    if not pts:
        return
    H = 520
    s = Svg(W, H)
    x0, x1, y0, y1 = 86, W - 36, H - 70, 70
    xs = [m[1] for _, _, m in pts] + [m[2] for _, _, m in pts] + [1.0]
    ys = [q[1] for _, q, _ in pts] + [q[2] for _, q, _ in pts] + [0.0]
    xlo, xhi = min(0.25, min(xs) * 0.9), max(3.2, max(xs) * 1.1)
    ylo, yhi = math.floor(min(ys) - 1), math.ceil(max(ys) + 1)
    sx, sy = Scale(xlo, xhi, x0, x1, log=True), Scale(ylo, yhi, y0, y1)
    step = 2 if yhi - ylo <= 16 else 5
    y_axis(s, sy, [v for v in range(int(ylo), int(yhi) + 1) if v % step == 0], x0, x1, lambda v: f"{v:+d}" if v else "0", zero=0)
    for v in (0.25, 0.5, 1, 2, 4):
        if xlo <= v <= xhi:
            s.line(sx(v), y0, sx(v), y0 + 5, "axis")
            s.text(sx(v), y0 + 22, f"×{v:g}", 13, "middle", "muted")
    s.line(sx(1), y0, sx(1), y1, "muted", 1.4)
    s.line(x0, y0, x1, y0, "axis", 1.4)
    s.text((x0 + x1) / 2, H - 20, f"总费用相对{ref_label}的倍数（对数刻度）", 14, "middle", "ink2")
    s.text(22, (y0 + y1) / 2, "评分项通过率之差（百分点）", 14, "middle", "ink2", rotate=True)
    col = lambda c: "muted" if c == "D0" else ("l1" if c.startswith("K") else ("l2" if c.startswith("D2") else ("l4" if c.startswith("D3") else "l5")))  # noqa: E731
    for c, q, m in pts:
        x, y = sx(m[0]), sy(q[0])
        s.line(sx.clip(m[1]), y, sx.clip(m[2]), y, col(c), 1.4)
        s.line(x, sy.clip(q[1]), x, sy.clip(q[2]), col(c), 1.4)
    obstacles, items = [((sx(1) - 7, sy(0) - 7, sx(1) + 7, sy(0) + 7, sx(1), sy(0)), 8), ((x0, sy(0) - 2, x1, sy(0) + 2, None, None), 0.6),
                        ((sx(1) - 2, y1, sx(1) + 2, y0, None, None), 0.6)], []
    for c, q, m in pts:
        x, y = sx(m[0]), sy(q[0])
        s.circle(x, y, 5.5, col(c))
        obstacles.append(((x - 7, y - 7, x + 7, y + 7, x, y), 8))
        obstacles.append(((x - 2, sy.clip(q[2]), x + 2, sy.clip(q[1]), x, y), 1.5))
        obstacles.append(((sx.clip(m[1]), y - 2, sx.clip(m[2]), y + 2, x, y), 1.5))
        items.append((x, y, short(c), "ink2", 400))
    s.circle(sx(1), sy(0), 6.5, "ink")
    place_labels(s, [(sx(1), sy(0), ref_label, "ink", 600)] + sorted(items), obstacles)
    if family == "A":
        legend(s, x0, 44, [("不开 subagent", "muted", False), ("深度 1", "l1", False), ("深度 2", "l2", False), ("深度 3", "l4", False)])
    s.save(out / fname, d.sim)


def three_panels(s: Svg, top, bottom, titles):
    """Three panels side by side; returns [(x0, x1)]."""
    left, gap, pw = 70, 46, (W - 70 - 24 - 2 * 46) / 3
    spans = []
    for i, t in enumerate(titles):
        x0 = left + i * (pw + gap)
        spans.append((x0, x0 + pw))
        s.text(x0 + pw / 2, top - 16, t, 15, "middle", "ink", 600)
        s.line(x0, bottom, x0 + pw, bottom, "axis", 1.4)
    return spans


def curve_panel(s: Svg, span, top, bottom, series, sx, lo, hi, ratio, ticks, fmt):
    """series: [(colour, [(x, est, lo, hi)], dashed)]. Draws grid, zero line, intervals, lines, points."""
    x0, x1 = span
    sy = Scale(lo, hi, bottom, top, log=ratio)
    y_axis(s, sy, ticks, x0, x1, fmt, zero=(1 if ratio else 0))
    n = len(series)
    for i, (col, pts, dashed) in enumerate(series):
        off = (i - (n - 1) / 2) * 7
        pts = sorted(pts)
        for x, est, lo_, hi_ in pts:
            whisker(s, sx(x) + off, sy.clip(lo_), sy.clip(hi_), col, 1.5, 3)
        s.path([(sx(x) + off, sy.clip(e)) for x, e, _, _ in pts], col, 2.0, "5 4" if dashed else None)
        for x, est, _, _ in pts:
            s.circle(sx(x) + off, sy.clip(est), 4.2, col)
    return sy


def nice_bounds(vals, ratio):
    if ratio:
        lo, hi = min(vals + [1.0]), max(vals + [1.0])
        lo, hi = min(0.5, lo * 0.92), max(2.0, hi * 1.08)
        ticks = [v for v in (0.25, 0.35, 0.5, 0.7, 1, 1.4, 2, 3, 4, 6) if lo <= v <= hi]
        return lo, hi, ticks, (lambda v: f"×{v:g}")
    lo, hi = math.floor(min(vals + [0.0]) - 0.5), math.ceil(max(vals + [0.0]) + 0.5)
    lo, hi = min(lo, -4), max(hi, 4)
    step = 2 if hi - lo <= 14 else (5 if hi - lo <= 40 else 10)
    return lo, hi, [v for v in range(int(lo), int(hi) + 1) if v % step == 0], (lambda v: f"{v:+d}" if v else "0")


def fig_k_curves(d: Data, out: Path):
    series_def = [("l1", "自然需求（原题面，调研题）", "A", "K8", [("K1", 1), ("K2", 2), ("K3", 3), ("K4", 4)], 8, False),
                  ("l2", "指令拆 8 份（调研题）", "B", "n8K8", [("n8K2", 2), ("n8K4", 4), ("n8K6", 6)], 8, False),
                  ("l4", "大型编码题", "F:toolkit-xl", "K8", [("K1", 1), ("K2", 2), ("K4", 4), ("K16", 16)], 8, True)]
    panels = [("评分项通过率之差（百分点）", "q", False), ("总费用倍数", "total_yuan", True), ("用户等的时间倍数", "t_answer_s", True)]
    H = 520
    s = Svg(W, H)
    top, bottom = 128, H - 112
    spans = three_panels(s, top, bottom, [p[0] for p in panels])
    for (x0, x1), (_title, outcome, ratio) in zip(spans, panels):
        sx = Scale(math.log2(0.8), math.log2(20), x0, x1)
        fx = lambda k, sx=sx: sx(math.log2(k))  # noqa: E731
        series, vals = [], []
        for col, _lab, fam, ref, cells, refk, dashed in series_def:
            if fam.startswith("F:") and outcome == "q":
                continue
            pts = [(refk, 1.0 if ratio else 0.0, 1.0 if ratio else 0.0, 1.0 if ratio else 0.0)]
            for c, k in cells:
                v = d.c(fam, c, ref, outcome)
                if v:
                    pts.append((k, *v))
                    vals += list(v)
            if len(pts) > 1:
                series.append((col, pts, dashed))
        if not series:
            continue
        lo, hi, ticks, fmt = nice_bounds(vals, ratio)
        curve_panel(s, (x0, x1), top, bottom, series, fx, lo, hi, ratio, ticks, fmt)
        for k in (1, 2, 3, 4, 6, 8, 16):
            s.line(fx(k), bottom, fx(k), bottom + 5, "axis")
            s.text(fx(k), bottom + 21, str(k), 13, "middle", "muted")
        s.text((x0 + x1) / 2, bottom + 42, "K：同时活着的 subagent 上限", 13, "middle", "ink2")
    lx = 70
    for col, lab, *_ in series_def:
        lx = legend(s, lx, 52, [(lab, col, False)])
    s.text(70, 76, "每个点是该 K 对同一条线上 K=8 的差或倍数，竖线是 95% 区间；编码题的质量在顶，只画费用和时间", 12.5, "start", "muted")
    # share of runs stuck at the cap, under the panels
    y = H - 46
    s.text(70, y, "有调用被上限拒过的运行比例：", 12.5, "start", "ink2")
    yy = y
    for col, lab, fam, ref, cells, refk, _ in series_def:
        parts = []
        for c, k in cells + [(ref, refk)]:
            v = d.l(fam, c, "stuck_share")
            if v is not None:
                parts.append(f"K={k} {100 * v:.0f}%")
        if parts:
            s.circle(262, yy - 4, 4, col)
            s.text(272, yy, "　".join(sorted(parts, key=lambda p: int(p.split("=")[1].split(" ")[0]))), 12.5, "start", "ink2")
            yy += 18
    s.save(out / "fig3-k-curves.svg", d.sim)


def fig_depth_curves(d: Data, out: Path):
    lines = [("l3", "K=2", [("D2K2", "K2", 2), ("D3K2", "K2", 3)]), ("l4", "K=4", [("D2K4", "K4", 2), ("D3K4", "K4", 3)]),
             ("l1", "K=8", [("D0", "K8", 0), ("D2K8", "K8", 2), ("D3K8", "K8", 3)]), ("l2", "K=16", [("D2K16", "K8", 2), ("D3K16", "K8", 3)])]
    panels = [("评分项通过率之差（百分点）", "q", False), ("总费用倍数", "total_yuan", True), ("用户等的时间倍数", "t_answer_s", True)]
    H = 490
    s = Svg(W, H)
    top, bottom = 128, H - 78
    spans = three_panels(s, top, bottom, [p[0] for p in panels])
    for (x0, x1), (_t, outcome, ratio) in zip(spans, panels):
        sx = Scale(-0.5, 3.5, x0, x1)
        series, vals = [], []
        for col, _lab, cells in lines:
            pts = [(1, 1.0 if ratio else 0.0, 1.0 if ratio else 0.0, 1.0 if ratio else 0.0)]
            for c, ref, depth in cells:
                v = d.c("A", c, ref, outcome)
                if v:
                    pts.append((depth, *v))
                    vals += list(v)
            if len(pts) > 1:
                series.append((col, pts, False))
        if not series:
            continue
        lo, hi, ticks, fmt = nice_bounds(vals, ratio)
        curve_panel(s, (x0, x1), top, bottom, series, sx, lo, hi, ratio, ticks, fmt)
        for depth, lab in ((0, "不开"), (1, "深度 1"), (2, "深度 2"), (3, "深度 3")):
            s.line(sx(depth), bottom, sx(depth), bottom + 5, "axis")
            s.text(sx(depth), bottom + 21, lab, 13, "middle", "muted")
        s.text((x0 + x1) / 2, bottom + 44, "深度上限", 13, "middle", "ink2")
    lx = 70
    for col, lab, _ in lines:
        lx = legend(s, lx, 52, [(lab, col, False)])
    s.text(70, 76, "每个点是该深度对同一个 K 下深度 1 的差或倍数（K=16 的参照是深度 1 配 K=8：深度 1 下 K=8 不触顶），竖线是 95% 区间", 12.5, "start", "muted")
    s.save(out / "fig4-depth-curves.svg", d.sim)


def fig_search(d: Data, out: Path):
    rows = [r for r in d.runs if r["family_used"] == "A" and r["q"] not in ("", "nan") and r["search_requests"] not in ("", "nan", "0", "0.0")]
    by = {}
    for r in rows:
        by.setdefault(r["task"], []).append(r)
    pts = []
    for task, v in by.items():
        if len(v) < 4:
            continue
        mq = st.mean(float(r["q"]) for r in v)
        ml = st.mean(math.log2(float(r["search_requests"])) for r in v)
        for r in v:
            pts.append((math.log2(float(r["search_requests"])) - ml, float(r["q"]) - mq, int(float(r["D"]))))
    if len(pts) < 10:
        return
    H = 480
    s = Svg(W, H)
    x0, x1, y0, y1 = 86, W - 36, H - 70, 74
    sx, sy = Scale(-3, 3, x0, x1), Scale(-30, 30, y0, y1)
    y_axis(s, sy, (-30, -20, -10, 0, 10, 20, 30), x0, x1, lambda v: f"{v:+d}" if v else "0", zero=0)
    for v in (-3, -2, -1, 0, 1, 2, 3):
        s.line(sx(v), y0, sx(v), y0 + 5, "axis")
        s.text(sx(v), y0 + 22, f"×{2 ** v:g}", 13, "middle", "muted")
    s.line(x0, y0, x1, y0, "axis", 1.4)
    s.text((x0 + x1) / 2, H - 20, "这次运行的搜索请求数，相对同一道题各次运行的平均（对数刻度）", 14, "middle", "ink2")
    s.text(22, (y0 + y1) / 2, "评分项通过率，相对同一道题的平均（百分点）", 14, "middle", "ink2", rotate=True)
    col = {0: "muted", 1: "l1", 2: "l2", 3: "l4"}
    for x, y, depth in pts:
        if -3 <= x <= 3 and -30 <= y <= 30:
            s.out.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="2.6" fill="{C[col[depth]]}" opacity="0.45"/>')
    n = len(pts)
    mx, my = st.mean(p[0] for p in pts), st.mean(p[1] for p in pts)
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    slope = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
    resid = [p[1] - my - slope * (p[0] - mx) for p in pts]
    se = math.sqrt(sum(e * e for e in resid) / (n - 2) / sxx)
    s.line(sx(-2.5), sy(my + slope * (-2.5 - mx)), sx(2.5), sy(my + slope * (2.5 - mx)), "ink", 2.0)
    s.text(x1, 49, f"直线：搜索请求每翻一倍，通过率 {slope:+.1f} 个百分点（±{1.96 * se:.1f}）", 13, "end", "ink")
    legend(s, x0, 49, [("不开 subagent", "muted", False), ("深度 1", "l1", False), ("深度 2", "l2", False), ("深度 3", "l4", False)])
    s.save(out / "fig5-search.svg", d.sim)


def fig_mechanism(d: Data, out: Path):
    """Rows: the seven ways of doing the same 40 tasks. Two columns: quality and money against "no subagents", with intervals."""
    rows = [("D0", "不开 subagent", "参照"), ("more", "单 agent，要求多查", "a"), ("seg", "单 agent，分 8 段做", "a"), ("merge4", "四份单 agent 报告合并", "a"),
            ("n3K8", "指令拆 3 份，K=8", "b"), ("n8K8", "指令拆 8 份，K=8", "b"), ("K8", "默认（深度 1，K=8）", "b")]
    base_q, base_c = d.l("G", "D0", "q"), d.l("G", "D0", "total_yuan")
    got = [(c, lab, grp, d.c("G", c, "D0", "q"), d.c("G", c, "D0", "total_yuan")) for c, lab, grp in rows]
    if base_q is None or not any(g[3] for g in got):
        return
    row_h, top = 44, 96
    H = top + row_h * len(rows) + 64
    s = Svg(W, H)
    lab_w = 232
    p1 = (lab_w + 20, lab_w + 20 + 300)
    p2 = (p1[1] + 70, W - 40)
    qv = [v for g in got if g[3] for v in g[3]] + [0.0]
    cv = [v for g in got if g[4] for v in g[4]] + [1.0]
    qlo, qhi = math.floor(min(qv) - 1), math.ceil(max(qv) + 1)
    clo, chi = min(0.8, min(cv) * 0.9), max(2.0, max(cv) * 1.15)
    sq, sc = Scale(qlo, qhi, p1[0], p1[1]), Scale(clo, chi, p2[0], p2[1], log=True)
    bottom = top + row_h * len(rows)
    s.text((p1[0] + p1[1]) / 2, top - 34, "评分项通过率之差（百分点）", 15, "middle", "ink", 600)
    s.text((p2[0] + p2[1]) / 2, top - 34, "总费用倍数（对数刻度）", 15, "middle", "ink", 600)
    step = 2 if qhi - qlo <= 14 else 5
    for v in [v for v in range(int(qlo), int(qhi) + 1) if v % step == 0]:
        s.line(sq(v), top - 8, sq(v), bottom, "grid")
        s.text(sq(v), bottom + 20, f"{v:+d}" if v else "0", 13, "middle", "muted")
    for v in [v for v in (0.5, 1, 2, 3, 5, 8, 12) if clo <= v <= chi]:
        s.line(sc(v), top - 8, sc(v), bottom, "grid")
        s.text(sc(v), bottom + 20, f"×{v:g}", 13, "middle", "muted")
    s.line(sq(0), top - 8, sq(0), bottom, "muted", 1.4)
    s.line(sc(1), top - 8, sc(1), bottom, "muted", 1.4)
    k8 = next((g for g in got if g[0] == "K8"), None)
    if k8 and k8[3]:
        s.line(sq(k8[3][0]), top - 8, sq(k8[3][0]), bottom, "l1", 1.2, "4 4")
    for i, (c, lab, grp, q, m) in enumerate(got):
        y = top + row_h * (i + 0.5)
        if i in (1, 4):
            s.line(14, y - row_h / 2, W - 20, y - row_h / 2, "grid", 1.0)
        col = "muted" if grp == "参照" else ("ink2" if grp == "a" else "l1")
        if c == "D0":
            s.text(lab_w, y - 3, lab, 14, "end", "ink", 600)
            s.text(lab_w, y + 15, f"参照：通过率 {base_q:.0f}%" + (f"，每次 {base_c:.1f} 元" if base_c is not None else ""), 12, "end", "muted")
            s.circle(sq(0), y, 5.5, col, hollow=True)
            s.circle(sc(1), y, 5.5, col, hollow=True)
            continue
        s.text(lab_w, y + 5, lab, 14, "end", "ink", 600 if c == "K8" else 400)
        if q:
            s.line(sq.clip(q[1]), y, sq.clip(q[2]), y, col, 2.0)
            s.circle(sq(q[0]), y, 5.5, col)
            s.text(sq.clip(q[2]) + 9, y + 5, f"{q[0]:+.1f}", 12.5, "start", "ink")
        if m:
            s.line(sc.clip(m[1]), y, sc.clip(m[2]), y, col, 2.0)
            s.circle(sc(m[0]), y, 5.5, col)
            s.text(sc.clip(m[2]) + 9, y + 5, f"×{m[0]:.1f}", 12.5, "start", "ink")
    legend(s, 24, H - 16, [("不开 subagent 的做法", "ink2", False), ("开 subagent", "l1", False)])
    s.text(W - 30, H - 16, "同 40 道题；横线是 95% 区间；蓝色虚线是默认的位置", 12.5, "end", "muted")
    s.save(out / "fig6-mechanism.svg", d.sim)


def fig_models(d: Data, out: Path):
    cells = [("D0", "不开 subagent"), ("K2", "K=2"), ("D2K8", "深度 2，K=8"), ("D3K64", "深度 3，K=64")]
    panels = [("评分项通过率之差（百分点）", "q", False), ("总费用倍数", "total_yuan", True)]
    H = 440
    s = Svg(W, H)
    top, bottom = 122, H - 62
    half = (W - 80 - 30 - 70) / 2
    drew = False
    for i, (title, outcome, ratio) in enumerate(panels):
        x0 = 80 + i * (half + 70)
        x1 = x0 + half
        vals, got = [], []
        for c, lab in cells:
            a, b = d.c("A@D", c, "K8", outcome), d.c("D", c, "K8", outcome)
            got.append((lab, a, b))
            for v in (a, b):
                if v:
                    vals += list(v)
        if not vals:
            continue
        drew = True
        lo, hi, ticks, fmt = nice_bounds(vals, ratio)
        sy = Scale(lo, hi, bottom, top, log=ratio)
        s.text((x0 + x1) / 2, top - 18, title, 15, "middle", "ink", 600)
        y_axis(s, sy, ticks, x0, x1, fmt, zero=(1 if ratio else 0))
        s.line(x0, bottom, x1, bottom, "axis", 1.4)
        bw = (x1 - x0) / len(got)
        for j, (lab, a, b) in enumerate(got):
            cx = x0 + bw * (j + 0.5)
            for v, col, off in ((a, "l1", -11), (b, "l2", 11)):
                if v:
                    whisker(s, cx + off, sy.clip(v[1]), sy.clip(v[2]), col, 1.8, 4)
                    s.circle(cx + off, sy.clip(v[0]), 5, col)
            s.text(cx, bottom + 22, lab, 12.5, "middle", "ink2")
    if not drew:
        return
    legend(s, 80, 50, [("deepseek-flash", "l1", False), ("deepseek-v4-pro", "l2", False)])
    s.text(80, 74, "同一批题上，各格对各自模型的默认（深度 1，K=8）的差或倍数，竖线是 95% 区间", 12.5, "start", "muted")
    s.save(out / "fig7-models.svg", d.sim)


def fig_coding_time(d: Data, out: Path, family="F:toolkit-xl"):
    cells = [c for c in ("D0", "K1", "K2", "K4", "K8", "K16", "D2K8") if d.l(family, c, "t_answer_s") is not None]
    if not cells:
        return
    H = 400
    s = Svg(W, H)
    x0, x1, top, bottom = 80, W - 30, 84, H - 64
    vals = [(c, d.l(family, c, "all_written_s"), d.l(family, c, "t_answer_s")) for c in cells]
    hi = 10 * math.ceil(max(v[2] for v in vals) / 60 / 10 + 0.3)
    sy = Scale(0, hi, bottom, top)
    y_axis(s, sy, [v for v in range(0, int(hi) + 1, 10 if hi <= 60 else 20)], x0, x1, lambda v: f"{v}")
    s.line(x0, bottom, x1, bottom, "axis", 1.4)
    bw = (x1 - x0) / len(vals)
    for i, (c, written, answer) in enumerate(vals):
        cx = x0 + bw * (i + 0.5)
        a = answer / 60
        w_ = (written or 0) / 60
        s.rect(cx - bw * 0.3, sy(a), bw * 0.6, bottom - sy(a), "bar2", rx=2)
        if written:
            s.rect(cx - bw * 0.3, sy(w_), bw * 0.6, bottom - sy(w_), "bar", rx=2)
            s.text(cx, sy(w_) + 17, f"{w_:.0f}", 12.5, "middle", "#ffffff", 600)
        s.text(cx, sy(a) - 8, f"{a:.0f}", 12.5, "middle", "ink", 600)
        s.text(cx, bottom + 22, {"D0": "不开 subagent", "K8": "K=8（默认）"}.get(c, name(c)), 12.5, "middle", "ink2")
    s.text(22, (top + bottom) / 2, "分钟", 14, "middle", "ink2", rotate=True)
    s.rect(x0, 34, 14, 14, "bar", rx=2)
    s.text(x0 + 21, 46, "到要写的文件都写完", 13, "start", "ink2")
    s.rect(x0 + 180, 34, 14, 14, "bar2", rx=2)
    s.text(x0 + 201, 46, "写完以后到主 agent 给出最终回答", 13, "start", "ink2")
    s.save(out / "fig8-coding-time.svg", d.sim)


def task_default(d: Data, family="A", ref="K8") -> dict:
    """Mean quality of the reference cell per task, from the runs the analysis used."""
    by = {}
    for r in d.runs:
        if r["family_used"] == family and r["cell"] == ref and r["q"] not in ("", "nan"):
            by.setdefault(r["task"], []).append(float(r["q"]))
    return {t: st.mean(v) for t, v in by.items()}


def mean_ci(v: list):
    if len(v) < 3:
        return None
    m, se = st.mean(v), st.stdev(v) / math.sqrt(len(v))
    return m, m - 1.96 * se, m + 1.96 * se


def fig_dose(d: Data, out: Path):
    cells = [("K8", "原题面"), ("n3K8", "指令拆 3 份"), ("n8K2", "指令拆 8 份，K=2"), ("n8K4", "指令拆 8 份，K=4"), ("n8K6", "指令拆 8 份，K=6"), ("n8K8", "指令拆 8 份，K=8")]
    pts = []
    for c, lab in cells:
        x = d.l("B", c, "mean_opened")
        q = (0.0, 0.0, 0.0) if c == "K8" else d.c("B", c, "K8", "q")
        if x is not None and q:
            pts.append((c, lab, x, q))
    if len(pts) < 3:
        return
    H = 430
    s = Svg(W, H)
    x0, x1, y0, y1 = 86, W - 40, H - 70, 60
    vals = [v for p in pts for v in p[3]]
    lo, hi, ticks, fmt = nice_bounds(vals, False)
    xmax = max(10, math.ceil(max(p[2] for p in pts) + 1))
    sx, sy = Scale(0, xmax, x0, x1), Scale(lo, hi, y0, y1)
    y_axis(s, sy, ticks, x0, x1, fmt, zero=0)
    for v in range(0, int(xmax) + 1, 2):
        s.line(sx(v), y0, sx(v), y0 + 5, "axis")
        s.text(sx(v), y0 + 22, str(v), 13, "middle", "muted")
    s.line(x0, y0, x1, y0, "axis", 1.4)
    s.text((x0 + x1) / 2, H - 20, "每次运行实际开成的 subagent 数（各格平均）", 14, "middle", "ink2")
    s.text(22, (y0 + y1) / 2, "评分项通过率对原题面默认之差（百分点）", 14, "middle", "ink2", rotate=True)
    obstacles, items = [], []
    for c, lab, x, q in pts:
        col = "ink" if c == "K8" else ("l2" if c.startswith("n8") else "l1")
        if c != "K8":
            whisker(s, sx(x), sy.clip(q[1]), sy.clip(q[2]), col, 1.6, 4)
            obstacles.append(((sx(x) - 2, sy.clip(q[2]), sx(x) + 2, sy.clip(q[1]), sx(x), sy(q[0])), 1.5))
        s.circle(sx(x), sy(q[0]), 5.5, col)
        obstacles.append(((sx(x) - 7, sy(q[0]) - 7, sx(x) + 7, sy(q[0]) + 7, sx(x), sy(q[0])), 8))
        items.append((sx(x), sy(q[0]), lab, "ink2", 400))
    place_labels(s, sorted(items), obstacles)
    s.save(out / "figA-dose.svg", d.sim)


def fig_capped(d: Data, out: Path):
    base = task_default(d)
    groups = [("A", c, name(c)) for c in ("K1", "K2", "K3", "K4")] + [("B", c, name(c)) for c in ("n8K2", "n8K4", "n8K6")]
    ref_b = task_default(d, "B", "n8K8")
    rows = []
    for fam, c, lab in groups:
        ref = base if fam == "A" else ref_b
        hit = [float(r["q"]) - ref[r["task"]] for r in d.runs if r["family_used"] == fam and r["cell"] == c and r["q"] not in ("", "nan") and r["task"] in ref and float(r["rejected_cap"] or 0) > 0]
        free = [float(r["q"]) - ref[r["task"]] for r in d.runs if r["family_used"] == fam and r["cell"] == c and r["q"] not in ("", "nan") and r["task"] in ref and float(r["rejected_cap"] or 0) == 0]
        if hit or free:
            rows.append((lab, mean_ci(hit), len(hit), mean_ci(free), len(free)))
    if not rows:
        return
    row_h, top = 46, 86
    H = top + row_h * len(rows) + 70
    s = Svg(W, H)
    lab_w = 210
    x0, x1 = lab_w + 24, W - 150
    vals = [v for r in rows for ci in (r[1], r[3]) if ci for v in ci] + [0.0]
    lo, hi = math.floor(min(vals) - 1), math.ceil(max(vals) + 1)
    sx = Scale(lo, hi, x0, x1)
    bottom = top + row_h * len(rows)
    step = 2 if hi - lo <= 16 else 5
    for v in [v for v in range(int(lo), int(hi) + 1) if v % step == 0]:
        s.line(sx(v), top - 8, sx(v), bottom, "grid")
        s.text(sx(v), bottom + 20, f"{v:+d}" if v else "0", 13, "middle", "muted")
    s.line(sx(0), top - 8, sx(0), bottom, "muted", 1.4)
    s.text((x0 + x1) / 2, bottom + 46, "评分项通过率对同一道题参照格之差（百分点；参照：原题面看默认，指令拆 8 份看 K=8）", 13, "middle", "ink2")
    for i, (lab, hit, nh, free, nf) in enumerate(rows):
        y = top + row_h * (i + 0.5)
        s.text(lab_w, y + 5, lab, 14, "end", "ink")
        for ci, n, col, dy in ((hit, nh, "l2", -8), (free, nf, "l1", 8)):
            if ci:
                s.line(sx.clip(ci[1]), y + dy, sx.clip(ci[2]), y + dy, col, 2.0)
                s.circle(sx(ci[0]), y + dy, 4.6, col)
            s.text(x1 + 14, y + dy + 4, f"{n} 次" + ("" if ci else "，太少不画"), 12, "start", col)
    legend(s, lab_w + 24, 42, [("有调用被上限拒过的运行", "l2", False), ("没有被拒的运行", "l1", False)])
    s.text(lab_w + 18, 64, "只作描述：被拒不是随机分的，被拒那条消息本身也会改变模型的做法", 12.5, "start", "muted")
    s.save(out / "figA-capped.svg", d.sim)


def fig_rejections(d: Data, out: Path):
    base = task_default(d)
    pts = []
    for r in d.runs:
        if r["family_used"] != "A" or r["cell"] == "D0" or r["q"] in ("", "nan") or r["task"] not in base:
            continue
        rej = float(r.get("rejected_cap") or 0) + float(r.get("rejected_depth") or 0)
        pts.append((rej, float(r["q"]) - base[r["task"]], int(float(r["D"]))))
    if len(pts) < 20:
        return
    H = 460
    s = Svg(W, H)
    x0, x1, y0, y1 = 86, W - 36, H - 70, 70
    xmax = 30
    sx, sy = Scale(0, xmax, x0, x1), Scale(-30, 30, y0, y1)
    y_axis(s, sy, (-30, -20, -10, 0, 10, 20, 30), x0, x1, lambda v: f"{v:+d}" if v else "0", zero=0)
    for v in range(0, xmax + 1, 5):
        s.line(sx(v), y0, sx(v), y0 + 5, "axis")
        s.text(sx(v), y0 + 22, str(v) + ("+" if v == xmax else ""), 13, "middle", "muted")
    s.line(x0, y0, x1, y0, "axis", 1.4)
    s.text((x0 + x1) / 2, H - 20, "这次运行里被拒的开 subagent 调用数（被 K 拒加被深度拒）", 14, "middle", "ink2")
    s.text(22, (y0 + y1) / 2, "评分项通过率对同题默认之差（百分点）", 14, "middle", "ink2", rotate=True)
    col = {1: "l1", 2: "l2", 3: "l4"}
    for x, y, depth in pts:
        s.out.append(f'<circle cx="{sx(min(x, xmax)):.1f}" cy="{sy(max(-30, min(30, y))):.1f}" r="2.6" fill="{C[col.get(depth, "muted")]}" opacity="0.45"/>')
    for lo_, hi_ in ((0, 0), (1, 2), (3, 5), (6, 10), (11, 20), (21, 10 ** 6)):
        v = [y for x, y, _ in pts if lo_ <= x <= hi_]
        ci = mean_ci(v)
        if ci:
            cx = sx(min((lo_ + min(hi_, xmax)) / 2, xmax))
            whisker(s, cx, sy.clip(ci[1]), sy.clip(ci[2]), "ink", 1.8, 5)
            s.circle(cx, sy(ci[0]), 5, "ink")
    legend(s, x0, 44, [("深度 1", "l1", False), ("深度 2", "l2", False), ("深度 3", "l4", False), ("黑点：按被拒次数分段的平均和 95% 区间", "ink", False)])
    s.save(out / "figA-rejections.svg", d.sim)


BEHAVIORS = [("planner_self_work", "主 agent 自己做了大部分搜索"), ("premature_completion", "过早宣布完成"), ("pass_through", "原样转包"),
             ("duplicate_work", "重复分工"), ("over_spawning", "开得过多或开了不用"), ("handback_loss", "交回的内容丢了"),
             ("wall_banging", "被拒后原样重试三次以上"), ("looping", "原地重复"), ("phantom_coordination", "说做了其实没做"), ("repeated_review", "重复复核")]
SHOW_CELLS = ["K2", "K4", "K8", "D2K8", "D3K8", "D3K64", "n8K2", "n8K8"]


def cell_of_run(d: Data) -> dict:
    out = {}
    for r in d.runs:
        out.setdefault(r["id"], r["cell"])
    return out


def fig_behaviors(d: Data, out: Path, summary: Path, skip: set):
    """Rows: behaviours; columns: cells. A bar and a number: runs marked yes over runs marked yes or no."""
    cell = cell_of_run(d)
    yes, n = {}, {}
    for r in csv.DictReader(open(summary, encoding="utf-8")):
        c = cell.get(r["id"])
        if c is None or r["answer"] not in ("yes", "no"):
            continue
        n[(r["item"], c)] = n.get((r["item"], c), 0) + 1
        yes[(r["item"], c)] = yes.get((r["item"], c), 0) + (r["answer"] == "yes")
    cells = [c for c in SHOW_CELLS if any((it, c) in n for it, _ in BEHAVIORS)]
    if not cells:
        return
    lab_w, top, row_h = 232, 96, 38
    cw = (W - lab_w - 30) / len(cells)
    H = top + row_h * len(BEHAVIORS) + 46
    s = Svg(W, H)
    for j, c in enumerate(cells):
        x = lab_w + cw * j
        lines_ = ("默认，K=8" if c == "K8" else short(c)).replace("，", "\n").split("\n")
        for k, part in enumerate(lines_):
            s.text(x + cw / 2, top - 30 + 16 * k, part, 13, "middle", "ink", 600 if c == "K8" else 400)
    for i, (item, lab) in enumerate(BEHAVIORS):
        y = top + row_h * i
        s.line(14, y, W - 20, y, "grid")
        dim = item in skip
        s.text(lab_w - 12, y + row_h / 2 + 5, lab, 14, "end", "muted" if dim else "ink")
        for j, c in enumerate(cells):
            x = lab_w + cw * j
            k = n.get((item, c), 0)
            if not k:
                s.text(x + cw / 2, y + row_h / 2 + 5, "-", 13, "middle", "muted")
                continue
            share = yes.get((item, c), 0) / k
            if dim:
                s.text(x + cw / 2, y + row_h / 2 + 5, "只给例子", 12, "middle", "muted")
                continue
            s.rect(x + 8, y + 9, (cw - 54) * share, row_h - 18, "bar", rx=2)
            s.text(x + cw - 8, y + row_h / 2 + 5, f"{100 * share:.0f}%", 13, "end", "ink")
    s.line(14, top + row_h * len(BEHAVIORS), W - 20, top + row_h * len(BEHAVIORS), "grid")
    s.text(24, H - 16, ("每格：判分模型标“是”的运行占标了“是”或“否”的运行的比例；灰色的行人工核对时错得多，只在正文给例子" if skip else "每格：判分模型（GPT-5.5）标“是”的运行占标了“是”或“否”的运行的比例；未经人工核对"), 12.5, "start", "muted")
    s.save(out / "fig9-behaviors.svg", d.sim)


def fig_delegation(d: Data, out: Path, cells_csv: Path):
    rows = {r["cell"]: r for r in csv.DictReader(open(cells_csv, encoding="utf-8")) if r["batch"] == "p2-main"}
    kinds = [("whole", "原样转包", "bad"), ("part", "分片", "l1"), ("narrow", "收窄", "bar2"), ("new", "新子题", "l4"), ("review", "复核", "l3"), ("unclear", "拿不准", "grid")]
    cells = [c for c in ["K1", "K2", "K4", "K8", "D2K8", "D2K16", "D3K8", "D3K16", "D3K64", "n8K8"] if c in rows and int(rows[c]["delegating_subagents"]) > 0]
    if not cells:
        return
    lab_w, top, row_h = 190, 84, 36
    H = top + row_h * len(cells) + 64
    s = Svg(W, H)
    x0, x1 = lab_w + 16, W - 250
    for v in (0, 25, 50, 75, 100):
        x = x0 + (x1 - x0) * v / 100
        s.line(x, top - 6, x, top + row_h * len(cells), "grid")
        s.text(x, top + row_h * len(cells) + 20, f"{v}%", 13, "middle", "muted")
    for i, c in enumerate(cells):
        r = rows[c]
        y = top + row_h * i
        total = sum(int(r[f"type_{k}"]) for k, _, _ in kinds) or 1
        s.text(lab_w, y + row_h / 2 + 5, "默认（深度 1，K=8）" if c == "K8" else short(c), 14, "end", "ink", 600 if c == "K8" else 400)
        x = x0
        for k, _, col in kinds:
            w = (x1 - x0) * int(r[f"type_{k}"]) / total
            s.rect(x, y + 7, w, row_h - 14, col)
            x += w
        subs = int(r["subagents"]) or 1
        s.text(x1 + 14, y + row_h / 2 + 5, f"{int(r['delegating_subagents'])} 个，占全部 subagent 的 {100 * int(r['delegating_subagents']) / subs:.0f}%", 12.5, "start", "ink2")
    lx = x0
    for k, lab, col in kinds:
        s.rect(lx, 30, 14, 14, col, rx=2)
        s.text(lx + 20, 42, lab, 13, "start", "ink2")
        lx += 34 + 13.5 * len(lab)
    s.text(x0, H - 14, "横条：这一格里试图再派活的 subagent 按派出去的任务分类（含被上限拒绝的尝试）；右边：这样的 subagent 有多少", 12.5, "start", "muted")
    s.save(out / "fig9b-delegation.svg", d.sim)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--behavior", type=Path, help="behavior_annotate.py summary.csv")
    ap.add_argument("--behavior-skip", default="", help="checklist items whose human check failed (examples only), comma-separated")
    ap.add_argument("--delegation", type=Path, help="delegation_classify.py cells.csv")
    ap.add_argument("--in", dest="src", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--method", default="mixed2", choices=["mixed2", "joint", "paired-t"])
    a = ap.parse_args()
    out = a.out or (a.src / "figs")
    out.mkdir(parents=True, exist_ok=True)
    d = Data(a.src, a.method)
    fig_demand(d, out)
    fig_cost_quality(d, out)
    fig_k_curves(d, out)
    fig_depth_curves(d, out)
    fig_search(d, out)
    fig_mechanism(d, out)
    fig_models(d, out)
    fig_coding_time(d, out)
    fig_cost_quality(d, out, family="O", ref="K8", cells=["planK8"], fname="fig10-orchestration.svg", ref_label="模型自定（默认）")
    fig_dose(d, out)
    fig_capped(d, out)
    fig_rejections(d, out)
    if a.behavior and a.behavior.exists():
        fig_behaviors(d, out, a.behavior, set(filter(None, a.behavior_skip.split(","))))
    if a.delegation and a.delegation.exists():
        fig_delegation(d, out, a.delegation)


if __name__ == "__main__":
    main()
