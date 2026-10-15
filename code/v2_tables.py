#!/usr/bin/env python3
"""Group tables for the v2 report (experiment-plan-dsec-v2.md section 7): one row per group, from v2_rows.py's CSV.

Columns: runs; score mean and 95% interval (within-task t interval with task effects removed, the same as
paired_stats.group_summary; tasks weighted equally); model cost and estimated total at the peak and off-peak price
(CNY per run, mean); wall and standardized time (minutes, mean); subagents per run (mean, and the largest); slot
peak (mean); runs where DSH crashed at exit (#5063); runs with no score yet.

Usage: v2_tables.py ROWS.csv --tasks t1,t2 [--title TEXT] [--groups G1,G2,...]
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paired_stats import group_key, t_interval  # noqa: E402


def num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def truthy(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes")


def mean_by_task(rows: list, col: str):
    """Mean over tasks of the per-task means (equal task weights); None when no task has a value."""
    by = defaultdict(list)
    for r in rows:
        v = num(r.get(col))
        if v is not None:
            by[r["task"]].append(v)
    return st.mean(st.mean(v) for v in by.values()) if by else None


def rate(rows: list, num_col: str, den_col: str) -> str:
    """Pooled percentage over the runs (errors / calls); a dash when there were no calls."""
    den = sum(num(r.get(den_col)) or 0 for r in rows)
    return "—" if not den else f"{100 * sum(num(r.get(num_col)) or 0 for r in rows) / den:.1f}"


def fmt(v, nd=1, scale=1.0):
    return "—" if v is None else f"{v * scale:.{nd}f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rows", type=Path)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--groups", help="only these groups, in this order")
    ap.add_argument("--title", default="")
    ap.add_argument("--require-all-tasks", action="store_true",
                    help="leave out groups that lack a run for some task (a merged table must not mix task sets)")
    ap.add_argument("--transpose", action="store_true", help="rows = metrics, columns = groups (the report layout)")
    a = ap.parse_args()
    tasks = a.tasks.split(",")
    rows = [r for r in csv.DictReader(open(a.rows, encoding="utf-8")) if r["task"] in tasks]
    groups = a.groups.split(",") if a.groups else sorted({r["group"] for r in rows}, key=group_key)
    left_out = []
    if a.require_all_tasks:
        have = {g: {r["task"] for r in rows if r["group"] == g} for g in groups}
        left_out = [g for g in groups if have[g] != set(tasks)]
        groups = [g for g in groups if g not in left_out]
    if a.title:
        print(f"### {a.title}\n")
    print(f"题：{', '.join(tasks)}。数值是各题均值再按题平均；得分区间为扣除题目效应的 95% t 区间。"
          + (f"只有部分题跑过、没列入的组：{', '.join(left_out)}。" if left_out else "") + "\n")
    if a.transpose:
        transposed(rows, groups)
        return
    print("| 组 | 次数 | 得分 | 95% 区间 | 模型费 高峰/空闲（元） | 估算总费用 高峰/空闲（元） | 实际时长（分） | 标准化时长（分） "
          "| 子代理（均/最多） | 名额峰值 | 退出时崩溃 | 缺得分 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for g in groups:
        gr = [r for r in rows if r["group"] == g]
        if not gr:
            continue
        sbt = defaultdict(list)
        for r in gr:
            v = num(r.get("score"))
            if v is not None:
                sbt[r["task"]].append(v)
        ti = t_interval(dict(sbt)) if sbt else {"est": None, "lo": None, "hi": None}
        ci = "—" if ti.get("lo") is None else f"[{ti['lo']:.1f}, {ti['hi']:.1f}]"
        kids = [num(r.get("children")) for r in gr if num(r.get("children")) is not None]
        print(f"| {g} | {len(gr)} | {fmt(ti.get('est'))} | {ci} | "
              f"{fmt(mean_by_task(gr, 'model_cost_peak'), 2)} / {fmt(mean_by_task(gr, 'model_cost_off'), 2)} | "
              f"{fmt(mean_by_task(gr, 'total_cost_peak'), 2)} / {fmt(mean_by_task(gr, 'total_cost_off'), 2)} | "
              f"{fmt(mean_by_task(gr, 'seconds'), 1, 1 / 60)} | {fmt(mean_by_task(gr, 'std_seconds'), 1, 1 / 60)} | "
              f"{fmt(mean_by_task(gr, 'children'))} / {int(max(kids)) if kids else '—'} | "
              f"{fmt(mean_by_task(gr, 'slot_peak'))} | {sum(truthy(r.get('crash5063')) for r in gr)} | "
              f"{sum(num(r.get('score')) is None for r in gr)} |")


def transposed(rows: list, groups: list) -> None:
    """The report layout: one row per metric, one column per group; same numbers as the default layout plus the
    subagent depth split, the slot and depth rejections and the children still open when the root ended."""
    cols = {}
    for g in groups:
        gr = [r for r in rows if r["group"] == g]
        if not gr:
            continue
        sbt = defaultdict(list)
        for r in gr:
            v = num(r.get("score"))
            if v is not None:
                sbt[r["task"]].append(v)
        ti = t_interval(dict(sbt)) if sbt else {"est": None, "lo": None, "hi": None}
        kids = [num(r.get("children")) for r in gr if num(r.get("children")) is not None]
        cols[g] = [
            str(len(gr)), fmt(ti.get("est")),
            "—" if ti.get("lo") is None else f"[{ti['lo']:.1f}, {ti['hi']:.1f}]",
            fmt(mean_by_task(gr, "model_cost_peak"), 2), fmt(mean_by_task(gr, "model_cost_off"), 2),
            fmt(mean_by_task(gr, "total_cost_peak"), 2), fmt(mean_by_task(gr, "total_cost_off"), 2),
            fmt(mean_by_task(gr, "seconds"), 1, 1 / 60), fmt(mean_by_task(gr, "std_seconds"), 1, 1 / 60),
            f"{fmt(mean_by_task(gr, 'children'))} / {int(max(kids)) if kids else '—'}",
            fmt(mean_by_task(gr, "children_d2")), fmt(mean_by_task(gr, "children_d3")),
            fmt(mean_by_task(gr, "slot_peak")), fmt(mean_by_task(gr, "capacity_rejects")),
            fmt(mean_by_task(gr, "depth_rejects")), fmt(mean_by_task(gr, "open_children_at_end"), 2),
            str(sum(truthy(r.get("crash5063")) for r in gr)),
            f"{sum(1 for r in gr if (num(r.get('capacity_rejects')) or 0) > 0)}/{len(gr)}",
            f"{sum(1 for r in gr if (num(r.get('depth_rejects')) or 0) > 0)}/{len(gr)}",
            f"{sum(1 for r in gr if (num(r.get('open_children_at_end')) or 0) > 0)}/{len(gr)}",
            fmt(mean_by_task(gr, "search_aux"), 0), rate(gr, "web_search_errors", "web_search_calls"),
            rate(gr, "web_fetch_errors", "web_fetch_calls"), fmt(mean_by_task(gr, "cache_hit_share"), 1, 100),
            fmt(mean_by_task(gr, "deliv_chars"), 1, 1 / 1000), fmt(mean_by_task(gr, "cat_A")),
            fmt(mean_by_task(gr, "cat_B")), fmt(mean_by_task(gr, "cat_C")), fmt(mean_by_task(gr, "cat_D")),
            fmt(mean_by_task(gr, "severe"), 2)]
    names = ["次数", "得分", "得分 95% 区间", "模型费·高峰（元/次）", "模型费·空闲（元/次）", "估算总费用·高峰（元/次）",
             "估算总费用·空闲（元/次）", "实际时长（分钟）", "标准化时长（分钟）", "子代理数（均值 / 最多）", "第 2 层子代理（均值）",
             "第 3 层子代理（均值）", "名额峰值（均值）", "名额被拒（次/运行）", "深度被拒（次/运行）", "主代理结束时未回的子代理（均值）",
             "退出时崩溃（次）", "碰到名额上限的运行数", "碰到深度上限的运行数", "结束时仍有子代理未回的运行数", "搜索请求数（均值）",
             "web_search 报错率（%）", "web_fetch 报错率（%）", "缓存命中占比（%）", "交付物长度（千字符）", "A 类得分（%）",
             "B 类得分（%）", "C 类得分（%）", "D 类得分（%）", "严重错误（次/份打分）"]
    gs = list(cols)
    print("| 指标 | " + " | ".join(gs) + " |")
    print("|---|" + "---|" * len(gs))
    for i, n in enumerate(names):
        print(f"| {n} | " + " | ".join(cols[g][i] for g in gs) + " |")


if __name__ == "__main__":
    main()
