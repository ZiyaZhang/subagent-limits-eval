#!/usr/bin/env python3
"""Figure for the wiki's office section, second version of "facts right against search requests": the 28 group means of
plot_wiki3.py plus the batch office-floor (single agent told to search more, default, default + keep-everything) and
the merged single-agent reports (x = search requests of the input runs plus the merge run).

The straight line is the same as in plot_wiki3.py (fit on the confirmation batch, 6.77 points per doubling), solid over
the range it was fitted on and dashed beyond. Same drawing code and colours as the other wiki figures.

Usage: plot_wiki5.py     then bash scripts/render-brief.sh results/analysis-wiki5
"""
from __future__ import annotations

import csv
import json
import math
import statistics as st
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXP / "scripts"))
import plot_brief as pb  # noqa: E402

OUT = EXP / "results" / "analysis-wiki5"
SRC = EXP / "results/analysis-facts-step1/group-means-all.csv"
SLOPE, X0, Y0 = 6.77, 239.4, 71.5  # the confirmation batch: D1-K8 at 239.4 requests and 71.5 %
LABEL = {("formal", "D0"): ("不给委派工具", 14, 5, "start"), ("confirm", "D1-K1"): ("K=1", -10, -12, "end"), ("confirm", "D1-K2"): ("K=2", -10, -12, "end"),
         ("confirm", "D2-K8"): ("深度 2、3，K=8", 14, 26, "start"), ("highk", "W-D2-K64"): ("深度 2、K=64", -12, -14, "end"),
         ("highk", "W-D3-K64"): ("深度 3、K=64", 10, 26, "end"), ("formal", "D2-K1"): ("深度 2、3 配 K=1、2", 4, 26, "middle"),
         ("floor", "E-D0"): ("单agent被要求多查", 12, 20, "start"), ("floor", "N-D1-K8"): ("默认 + “都写进去”", 10, -12, "start"),
         ("merge", "M2"): ("两份合并（原稿是前一天的）", -12, -12, "end"), ("merge", "M4"): ("四份合并（原稿是前一天的）", -12, -12, "end"),
         ("merge-b", "M2"): ("两份单agent报告合并", -12, 22, "end"), ("merge-b", "M4"): ("四份合并", -14, -12, "end")}


def kind(batch: str, group: str) -> str:
    if batch.startswith("merge"):
        return "merge"
    g = group.replace("W-", "")
    if g == "E-D0":
        return "floor"
    g = g.replace("N-", "")
    return "d0" if g == "D0" else ("d1" if g.startswith("D1") else "d23")


def floor_points() -> list:
    A, B = EXP / "results/analysis-facts-floor", EXP / "results/analysis-office-floor"
    if not (A / "fact-rows.csv").exists():
        return []
    rows = list(csv.DictReader(open(B / "rows-all.csv", encoding="utf-8")))
    facts = {r["id"]: r for r in csv.DictReader(open(A / "fact-rows.csv", encoding="utf-8"))}
    out = []
    for g in ("D0", "E-D0", "D1-K8", "N-D1-K8"):
        x = [r for r in rows if r["group"] == g and r["id"] in facts and float(r.get("open_children_at_end") or 0) == 0]
        out.append({"batch": "floor", "group": g, "x": st.mean(float(r["search_aux"]) for r in x), "y": st.mean(float(facts[r["id"]]["right_pct"]) for r in x)})
    return out


def merge_points() -> list:
    out = []
    for name, batch, index, source in (("merge", "office-merge", "tasks/merge-index.json", "office-confirm"), ("merge-b", "office-merge-b", "tasks/merge-b-index.json", "office-floor")):
        f = EXP / f"results/analysis-{batch}/merge-stats.json"
        if not f.exists() or not (EXP / index).exists():
            continue
        idx = json.loads((EXP / index).read_text(encoding="utf-8"))
        src = {r["id"]: r for r in csv.DictReader(open(EXP / f"results/analysis-{source}/rows-all.csv", encoding="utf-8"))}
        by = {}
        for r in json.loads(f.read_text(encoding="utf-8"))["rows"]:
            total = sum(float(src[i]["search_aux"]) for i in idx[r["task"]]["inputs"]) + r["merge_search"]
            by.setdefault(r["kind"], []).append((total, r["merged_right_pct"]))
        for k, v in by.items():
            out.append({"batch": name, "group": k, "x": st.mean(a for a, _ in v), "y": st.mean(b for _, b in v)})
    return out


def main() -> None:
    pts = [{"batch": r["batch"], "group": r["group"], "x": float(r["search_aux"]), "y": float(r["right_pct"])} for r in csv.DictReader(open(SRC, encoding="utf-8"))]
    pts += floor_points() + merge_points()
    W, H = pb.W, 500
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
    s.text(24, (y0 + y1) / 2, "写对的事实条目（%）", 14, "middle", "ink2", rotate=True)
    f = lambda v: Y0 + SLOPE * math.log2(v / X0)  # noqa: E731
    s.line(X(60), Y(f(60)), X(455), Y(f(455)), "muted", 1.6)
    n = 14
    for i in range(n):  # dashed continuation of the line beyond the fitted range
        a, b = 455 * (800 / 455) ** (i / n), 455 * (800 / 455) ** ((i + 0.55) / n)
        s.line(X(a), Y(min(f(a), yhi)), X(b), Y(min(f(b), yhi)), "muted", 1.6)
    col = {"d0": "muted", "d1": "l1", "d23": "l2", "floor": "ink", "merge": "ink"}
    for p in pts:
        k = kind(p["batch"], p["group"])
        x, y = X(p["x"]), Y(p["y"])
        if k == "merge":
            s.circle(x, y, 7, col[k], hollow=True)
            s.line(x - 4, y, x + 4, y, "ink", 1.6)
            s.line(x, y - 4, x, y + 4, "ink", 1.6)
        elif k == "floor":
            s.circle(x, y, 7, col[k])
        else:
            s.circle(x, y, 6, col[k], hollow=p["batch"] in ("highk", "wait2"))
    for p in pts:
        lab = LABEL.get((p["batch"], p["group"]))
        if lab:
            text, dx, dy, anchor = lab
            s.text(X(p["x"]) + dx, Y(p["y"]) + dy, text, 13, anchor, "ink2")
    lx = x0 + 6
    for k, name in (("d0", "不给委派工具"), ("d1", "深度 1"), ("d23", "深度 2、3")):
        s.circle(lx, 22, 6, col[k])
        s.text(lx + 12, 27, name, 13, "start", "ink2")
        lx += 40 + 14 * len(name)
    s.circle(lx, 22, 7, "ink")
    s.text(lx + 12, 27, "单agent被要求多查", 13, "start", "ink2")
    lx = x0 + 6
    s.circle(lx, 46, 7, "ink", hollow=True)
    s.line(lx - 4, 46, lx + 4, 46, "ink", 1.6)
    s.line(lx, 42, lx, 50, "ink", 1.6)
    s.text(lx + 12, 51, "几份单agent报告合并", 13, "start", "ink2")
    lx += 40 + 14 * 10
    s.circle(lx, 46, 6, "ink2", hollow=True)
    s.text(lx + 12, 51, "空心：补判的两批", 13, "start", "ink2")
    s.text(x1, 51, "直线：按确认实验 6 组拟合，虚线是往外延长", 13, "end", "muted")
    OUT.mkdir(parents=True, exist_ok=True)
    s.save(OUT / "office-facts-by-search-2.svg")
    print("wrote", OUT / "office-facts-by-search-2.svg", len(pts), "points")
    for p in pts[28:]:
        print("  ", p["batch"], p["group"], round(p["x"], 1), round(p["y"], 1), "line at this x:", round(f(p["x"]), 1), "difference:", round(p["y"] - f(p["x"]), 1))


if __name__ == "__main__":
    main()
