#!/usr/bin/env python3
"""Add the two code-building tasks (24 exercises without a time limit, 48-module package) to the user's wiki page
「Subagent问题」, into the sections that already exist. Only inserts; her text and figures are not changed.

The content is the list STEPS below (top of the page to the bottom). Two ways to use it:
  --preview OUT.md   write the content as Markdown, each piece under a line that says where it goes (no API call)
  (default)          insert into the page. Every step is anchored to block ids of the page as read on
                     2026-10-04T08:10Z (results/wiki/blocks-2026-10-04T0810Z.json); the page must still have exactly
                     those top-level blocks (plus the ones this script added), otherwise nothing is written. Finished
                     steps are recorded in results/wiki/applied.json, so a second run only does what is missing.

  --update           bring the blocks this script inserted earlier up to date with the content below
  --correct          corrections of the user's own conclusion sentences (CORRECTIONS below): the outdated phrase is
                     struck through and the corrected wording is put right after it, in the same block. She asked for
                     this on 2026-10-04 ("可以把它划掉，然后在旁边补充"). A block is only touched while it still reads
                     exactly as it did when the correction was written; what was changed is kept in
                     results/wiki/strikes.json (elements before and after), so every correction can be undone.

Usage: wiki_apply.py [--preview OUT.md] [--update] [--correct] [--dry-run] [--only STEP,STEP]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

EXP = Path(__file__).resolve().parent.parent
DOC = "MD7YdqJqio1gJ2x9E9ZcfPdQnwh"
DUMP = EXP / "results/wiki/blocks-2026-10-04T0810Z.json"
STATE = EXP / "results/wiki/applied.json"
STRIKES = EXP / "results/wiki/strikes.json"
FIG = "results/analysis-wiki"
NOREVIEW = "文件都写完以后，不要再另开子代理去复核、验证或补测试；需要检查就自己检查。"

A4_SHORT = ["**活做完以后主agent还会再派一批subagent复核**，多花钱、多等，通过的测试几乎不变；题面加一句“不复核”就不再派。",
            "agent用 shell 跑的进程没有内存上限，会把容器内存用满、被系统杀掉。"]

# item kinds: ("text", markup[, {"color": 7}]), ("bullet", markup), ("ordered", markup), ("h5", markup, bold),
#             ("image", file, caption), ("table", rows, widths)
# step kinds: "root" (insert before the page's top-level block number `before` of the dump), "nested" (insert under
#             the bullet `parent`, before its last child), "task-table" (two rows and one note in the 题目 table)
STEPS = [
    {"name": "A0-scope", "kind": "root", "before": 9, "where": "「初步结论」：“适用范围”那一段的下面",
     "items": [("text", "代码构建类的两道题（24 道练习不限时、48 模块的 Python 包）要写 24–61 个文件，单个agent要 10–20 分钟左右，不设时限；"
                        "这两道题各组得分都接近满分，结论只体现在时间和费用上。", {"color": 7}),
               ("text", "办公题只有 2 道（o1、o2），每组重复跑 20–40 次：下面的区间反映的是同一道题重复跑的波动，换别的办公题结论是否一样还没有测。", {"color": 7})]},
    {"name": "A1-depth", "kind": "root", "before": 11, "where": "「初步结论」：“深度上限 D 保持 1”那条的说明下面",
     "items": [("text", "代码构建题（24 道练习不限时、48 模块的包）上放开到 D=2，到最终回答的时间没有显著缩短，费用差别在一成以内；"
                        "第 2 层开出来的subagent很少（平均每次不到 2 个），48 模块的包上全部是复核用的。")]},
    {"name": "A2-k", "kind": "root", "before": 13, "where": "「初步结论」：“最大同时存活数K 可以保持 8”那条的说明下面",
     "items": [("text", "代码构建题上：K=16、64 没有好处。按现在的行为，K=4 和 K=8 相比到最终回答的时间、得分都没有显著差别，费用少 26%–30%——"
                        "K=8 把并行省下的时间花在了写完以后的复核上。题面加一句“不复核”以后，48 模块的包上 K=4 到最终回答的时间是 K=8 的 1.22 倍（显著），K=16 和 K=8 一样。"
                        "**所以把“写完又派复核”改掉以后 K 保持 8 合适；这个行为不改的话，K=4 更省。**")]},
    {"name": "A3-effect", "kind": "root", "before": 15, "where": "「初步结论」：“开subagent是否带来效果提升取决于任务类型”那条的三行说明下面",
     "items": [("text", "24 道独立练习不限时：题都写完的时间快 20%–28%，但主agent写完以后又派一批subagent复核，到最终回答的时间没有缩短，费用是 3–5 倍，得分差不到 1 分。\n"
                        "48 模块的 Python 包：按现在的行为，开subagent后到最终回答的时间是不开的 1.26 倍（不显著），费用 4.7 倍；"
                        "题面加一句“文件都写完以后不要再另开子代理复核”，到最终回答的时间是不开的 0.45 倍，费用 1.9 倍，得分不变。")]},
    {"name": "A4-other-problems", "kind": "nested", "parent": 15, "where": "「初步结论」：“其他问题”列表里，放在最后一条“在办公场景中……”的前面",
     "items": [("bullet", A4_SHORT[0]), ("bullet", A4_SHORT[1])]},
    {"name": "B-variables", "kind": "root", "before": 23, "where": "「变量」：“共 13 组……”那一段的下面",
     "items": [("text", "代码构建类的两道题（题目表最后两行）不设时限，K 另外测了 16（24 道练习还测了 64）；48 模块的包还测了题面末尾加一句"
                        f"“{NOREVIEW}”（下面叫“不复核句”）的组。这两道题上有委派工具的组都让进程等subagent回来再退出。")]},
    {"name": "C-task-table", "kind": "task-table", "table": 25, "where": "「题目」的表：末尾加两行；右边合并的说明栏里加一条",
     "rows": [["24 道练习不限时（代码构建）", "同样的 24 道 Python 练习，去掉 3 分钟时限，做到模型自己认为完成为止", "隐藏测试"],
              ["48 模块的 Python 包（代码构建）", "按规格实现一个 Python 包：12 个子包、48 个模块、61 个要写的文件；规格故意和标准库的行为不一样",
               "3737 个隐藏测试（给出其中 1267 个）"]],
     "note": "代码构建题：24 道练习不限时 14 组共 240 次（每组 10–20 次），48 模块的包 11 组各 10 次共 110 次；不联网，费用只有模型费；"
             "时长指从开始到主agent给出最终回答的时间。"},
    {"name": "D1-behavior-figures", "kind": "root", "before": 31, "where": "「模型自己倾向于开的subagent数量」：三张图的下面",
     "items": [("image", "ex24-review.png", "24 道练习不限时（题面鼓励开subagent）每次运行开的subagent数，橙色是题都写完以后才派的"),
               ("image", "pkg48-review.png", "48 模块的包每次运行开的subagent数，橙色是派去复核的（按任务说明数）")]},
    {"name": "D2-behavior-bullets", "kind": "root", "before": 35, "where": "「模型自己倾向于开的subagent数量」：四条要点的下面",
     "items": [("bullet", "**代码构建题上模型按“块”派subagent，K 多大就用多大**：24 道练习鼓励开subagent以后，K=1、2、4、8、16 时平均开 2.1、4.8、8.7、11.9、17.3 个；"
                          "48 模块的包不用提示，一上来就按子包派 12 个，K=8 时有 4 个左右被拒，被拒的子包一部分由主agent自己写。"),
               ("bullet", "**活做完以后还会再派一批subagent去复核**：48 模块的包原题面 39/40 次运行这样做，平均每次 5–12 个；24 道练习 K=8 时 15/20 次，"
                          "K 越大越常见（K=1 时 6/20 次）。")]},
    {"name": "E-scores", "kind": "root", "before": 38, "where": "「得分一览」：图下那段说明的下面",
     "items": [("text", "代码构建题用隐藏测试判分，各组都接近满分（24 道练习不限时 96.4–97.8 分，48 模块的包 99.96–100 分），各组之间的得分差都不到 1.5 分，"
                        "这两道题下面只比时间和费用。")]},
    {"name": "F1-depth-figures", "kind": "root", "before": 46, "where": "「深度」：代码题两张图的下面、“结论”的上面",
     "items": [("h5", "代码构建题（不限时）", False),
               ("image", "ex24-cost-by-d.png", "24 道练习不限时（题面鼓励开subagent）：固定k，深度对费用的影响"),
               ("image", "ex24-time-by-d.png", "24 道练习不限时（题面鼓励开subagent）：固定k，深度对到最终回答时间的影响"),
               ("image", "pkg48-cost-by-d.png", "48 模块的包：固定k，深度对费用的影响"),
               ("image", "pkg48-time-by-d.png", "48 模块的包：固定k，深度对到最终回答时间的影响")]},
    {"name": "F2-depth-conclusion", "kind": "root", "before": 47, "where": "「深度」：“结论：深度保持 1……”的下面",
     "items": [("text", "代码构建题上同样保持 1：放开到 D=2，到最终回答的时间没有显著缩短（24 道练习 ×0.93 [0.83, 1.05]；48 模块的包原题面 ×0.85 [0.66, 1.10]，"
                        "加不复核句反而更慢 ×1.34 [1.01, 1.77]），费用差别在一成以内。第 2 层开出来的subagent很少：24 道练习平均每次不到 1 个，"
                        "48 模块的包原题面平均 1.3 个，全部是复核用的。")]},
    {"name": "G1-k-figures", "kind": "root", "before": 56, "where": "「最大同时存活数量K」：代码题三张图的下面、“结论”的上面",
     "items": [("h5", "代码构建题（不限时）", False),
               ("image", "ex24-cost-by-k.png", "24 道练习不限时（题面鼓励开subagent）：固定深度，k对费用的影响"),
               ("image", "ex24-time-by-k.png", "24 道练习不限时（题面鼓励开subagent）：固定深度，k对到最终回答时间的影响"),
               ("image", "pkg48-cost-by-k.png", "48 模块的包（深度 1）：k对费用的影响"),
               ("image", "pkg48-time-by-k.png", "48 模块的包（深度 1）：k对到最终回答时间的影响")]},
    {"name": "G2-k-conclusion", "kind": "root", "before": 57, "where": "「最大同时存活数量K」：“结论：K 可以保持 8……”的下面",
     "items": [("text", "代码构建题上：K=16、64 没有好处（到最终回答的时间和 K=8 没有显著差别）。K 调小：按现在的行为，K=4 到最终回答的时间和 K=8 没有显著差别"
                        "（24 道练习 ×0.81 [0.59, 1.11]，48 模块的包 ×1.13 [0.67, 1.90]），费用少 26%–30%——K=8 写得更快，但省下的时间花在了写完以后的复核上。"
                        "题面加不复核句以后，48 模块的包上 K=8 最快：K=1、2、4 到最终回答的时间分别是 K=8 的 2.25、1.57、1.22 倍（都显著），K=16 和 K=8 一样（×1.02 [0.89, 1.16]）。"
                        "**所以把“写完又派复核”改掉以后 K 保持 8；这个行为不改的话，K=4 更省。**")]},
    {"name": "H1-effect", "kind": "root", "before": 68, "where": "「允许开subagent对任务效果的影响」：“对照组”那张表的下面、“结论”的上面",
     "items": [("h5", "代码构建题（不限时）", True),
               ("text", "基准是不给委派工具；时间从开始算到主agent给出最终回答（用户实际等的时间）。"),
               ("table", [["题", "组", "得分差 [95% 区间]", "模型费", "题/文件都写完的时间", "到最终回答的时间"],
                          ["24 道练习不限时", "出厂默认", "−0.2 [−1.0, +0.6]", "×2.98", "×0.80", "×1.07 [0.89, 1.28]"],
                          ["24 道练习不限时", "出厂默认 + 鼓励并行", "+0.5 [+0.0, +1.0]", "×4.60", "×0.72", "×1.39 [1.10, 1.76]"],
                          ["48 模块的包", "出厂默认", "+0.04 [+0.02, +0.05]", "×4.67", "×0.49", "×1.26 [0.97, 1.64]"],
                          ["48 模块的包", "出厂默认 + 不复核句", "+0.01 [−0.01, +0.04]", "×1.86", "×0.56", "×0.45 [0.38, 0.53]"]],
                [118, 132, 140, 70, 120, 150]),
               ("text", "48 模块的包上“写完又派复核”多做了什么：多花钱、多等，通过的测试只多 1 个左右"),
               ("table", [["指标", "原题面（D1-K8）", "加不复核句（D1-K8）"],
                          ["subagent数（其中复核的）", "20.0（10.2）", "9.5（0）"],
                          ["到最终回答的时间（分钟，中位）", "26.0", "9.2"],
                          ["模型费（元/次）", "19.85", "7.86"],
                          ["没通过的隐藏测试（共 3737 个，每次平均）", "0.0", "1.2"]],
                [260, 180, 180])]},
    {"name": "H2-effect-conclusion", "kind": "root", "before": 69, "where": "「允许开subagent对任务效果的影响」：“结论：开subagent对效果的影响看任务……”的下面",
     "items": [("text", "代码构建题上：开subagent让文件写得更快（20%–51%），但按现在的行为主agent写完以后又派一批subagent复核，到最终回答的时间没有缩短，费用是 3–5 倍；"
                        "题面加一句不复核以后，48 模块的包上到最终回答的时间是不开subagent的 0.45 倍，费用 1.9 倍，得分不变。")]},
    {"name": "I-problems", "kind": "root", "before": 76, "where": "「运行中发现的其他问题」：接在第 6 条后面（第 7、8 条）",
     "items": [("ordered", "活做完以后主agent还会再派一批subagent复核：48 模块的包原题面 40 次运行里 39 次，24 道练习不限时 220 次里 111 次。"
                           "48 模块的包上因此费用是 2.5 倍、到最终回答的时间是 2.8 倍，3737 个测试里平均只多对 1 个左右。"
                           f"题面加一句“{NOREVIEW}”，深度 1 的 50 次运行没有一次再派；深度 2 时有 2/10 次是写代码的subagent自己又派了复核（这句话只写在给主agent的题面里）。"),
               ("ordered", "agent用 shell 跑的进程没有内存上限：48 模块的包 110 次运行里 26 次有进程因为容器 16 GB 内存用满被系统杀掉，"
                           "日志里能认出的 6 条被杀命令都是agent自己写的随机测试或穷举检查脚本；其中 1 次被杀的是 DSH 进程本身。")]},
]


def regrade() -> dict | None:
    """Numbers of the fact-level re-grade of the office reports (results/analysis-facts), or None before it exists."""
    A = EXP / "results/analysis-facts"
    if not (A / "stats-facts.json").exists():
        return None
    import csv
    means = {(r["task"], r["group"]): r for r in csv.DictReader(open(A / "group-means.csv", encoding="utf-8"))}
    st_ = json.loads((A / "stats-facts.json").read_text(encoding="utf-8"))["metrics"]
    fa = json.loads((A / "stats-facts-factorial.json").read_text(encoding="utf-8"))["metrics"]
    val = json.loads((EXP / "results/judge-facts/validation.json").read_text(encoding="utf-8"))
    sec = json.loads((A / "second-pass.json").read_text(encoding="utf-8"))
    c = lambda m, k, src=st_: src[m]["comparisons"][k]  # noqa: E731
    f = lambda v, nd=1: f"{v:+.{nd}f}".replace("-", "−")  # noqa: E731
    ci = lambda x, nd=1: f"{f(x['est'], nd)} [{f(x['lo'], nd)}, {f(x['hi'], nd)}]"  # noqa: E731
    m0, m8 = means[("both", "D0")], means[("both", "D1-K8")]
    h1, k1, k2, k4 = c("right_pct", "H1"), c("right_pct", "FK1", fa), c("right_pct", "FK2", fa), c("right_pct", "FK4", fa)
    assert h1["lo"] > 0 and k1["hi"] < 0 and k2["hi"] < 0 and k4["lo"] < 0 < k4["hi"], "the re-grade outcome changed: rewrite the wiki text"
    assert all(c("right_pct", k)["lo"] < 0 < c("right_pct", k)["hi"] for k in ("H2a", "H2b", "H2c", "H3a", "H3b"))
    C = EXP / "results/analysis-facts-confirm"
    cs = json.loads((C / "stats.json").read_text(encoding="utf-8"))["metrics"]
    cm = {r["group"]: r for r in csv.DictReader(open(C / "group-means.csv", encoding="utf-8"))}
    c2 = json.loads((C / "second-pass.json").read_text(encoding="utf-8"))
    import math
    cc = lambda m, k: cs[m]["comparisons"][k]  # noqa: E731
    ratio = lambda k, m="total_cost_peak": math.exp(cc(m, k)["est"])  # noqa: E731
    ck1, ck2, ck4, ch1, cdn = (cc("right_pct", k) for k in ("K1", "K2", "K4", "H1", "DN"))
    assert ck1["hi"] < 0 and ck2["lo"] < 0 < ck2["hi"] and ck4["lo"] < 0 < ck4["hi"] and ch1["lo"] > 0 and cdn["lo"] < 0 < cdn["hi"], \
        "the confirmation outcome changed: rewrite the wiki text"
    slots = 97.5
    neg = lambda x: {"est": -x["est"], "lo": -x["hi"], "hi": -x["lo"]}  # noqa: E731
    money = lambda g: float(cm[g]["total_cost_peak"])  # noqa: E731
    line = lambda label, g, diff, verdict, times: [label, f"{float(cm[g]['right_n']):.1f}", diff, verdict,  # noqa: E731
                                                   f"{money(g):.2f}" + (f"（×{times:.2f}）" if times else ""), f"{float(cm[g]['right_n']) / money(g):.1f}"]
    sheet = [["系统设置", "写对的事实（条）", "和目前默认的差（个百分点，95% 区间）", "效果好坏判断", "估算总费用，元/次（倍数）", "每元写对的条数"],
             line("目前默认（最大深度 D=1，不允许递归；K=8）", "D1-K8", "—", "—", None),
             line("K 8 → 4", "D1-K4", ci(ck4), "没有差别", ratio("K4")),
             line("K 8 → 2", "D1-K2", ci(ck2), "没测出差别", ratio("K2")),
             line("K 8 → 1", "D1-K1", ci(ck1), "显著变差", ratio("K1")),
             line("D 1 → 2", "D2-K8", ci(cdn), "没测出差别", ratio("DN")),
             line("不允许开 subagent", "D0", ci(neg(ch1)), "显著变差", 1 / ratio("H1"))]
    assert abs(ck4["lo"]) < 8 and abs(ck4["hi"]) < 8, "K4 is no longer inside ±8: the verdict 没有差别 does not hold"
    mins = lambda g: float(cm[g]["seconds"]) / 60  # noqa: E731
    tcol = {"D1-K8": None, "D1-K4": ratio("K4", "seconds"), "D1-K2": ratio("K2", "seconds"), "D1-K1": ratio("K1", "seconds"),
            "D2-K8": ratio("DN", "seconds"), "D0": 1 / ratio("H1", "seconds")}
    order7 = ["D1-K8", "D1-K4", "D1-K2", "D1-K1", "D2-K8", "D0"]
    sheet7 = [sheet[0] + ["实际时长，分钟（倍数）"]] + [row + [f"{mins(g):.1f}" + (f"（×{tcol[g]:.2f}）" if tcol[g] else "")] for row, g in zip(sheet[1:], order7)]
    conf = {"k1": ci(ck1), "k2": ci(ck2), "k4": ci(ck4), "h1": ci(ch1), "dn": ci(cdn), "k1n": -ck1["est"] * slots / 100,
            "cost_k1": ratio("K1"), "cost_k2": ratio("K2"), "cost_dn": ratio("DN"), "cost_h1": ratio("H1"),
            "n0": float(cm["D0"]["right_n"]), "n8": float(cm["D1-K8"]["right_n"]),
            "per_fact_dn": (float(cm["D2-K8"]["total_cost_peak"]) - float(cm["D1-K8"]["total_cost_peak"])) / (float(cm["D2-K8"]["right_n"]) - float(cm["D1-K8"]["right_n"])),
            "judged": sum(int(r["n_judged"]) for r in cm.values()), "runs": sum(int(r["n_runs"]) for r in cm.values()),
            "second": 100 * c2["same"] / c2["n"], "second_n": c2["reports"], "sheet": sheet, "sheet7": sheet7,
            "wrong": (min(float(r["wrong_firm_n"]) for r in cm.values()), max(float(r["wrong_firm_n"]) for r in cm.values()))}
    return {"conf": conf, "n0": float(m0["right_n"]), "n8": float(m8["right_n"]), "gain": float(m8["right_n"]) - float(m0["right_n"]), "h1": ci(h1),
            "k1": -k1["est"], "k2": -k2["est"], "k1ci": ci(k1), "k2ci": ci(k2), "k4ci": ci(k4),
            "d1k1": ci(c("right_pct", "H2a")), "d2": ci(c("right_pct", "H3a")), "d3": ci(c("right_pct", "H3b")),
            "rows": [("写对的事实条数", f"{float(m0['right_n']):.1f}", f"{float(m8['right_n']):.1f}"),
                     ("写错的条数（没标待核验）", f"{float(m0['wrong_firm_n']):.2f}", f"{float(m8['wrong_firm_n']):.2f}"),
                     ("只写了“待核验”的条数", f"{float(m0['hedged_only_n']):.1f}", f"{float(m8['hedged_only_n']):.1f}"),
                     ("没写的条数", f"{float(m0['absent_n']):.1f}", f"{float(m8['absent_n']):.1f}")],
            "agree": (100 * val["o1"]["agree"], 100 * val["o2"]["agree"]), "second": 100 * sec["same"] / sec["n"], "second_n": sec["reports"]}


def ws() -> dict | None:
    """Numbers of the WideSearch screening and three-group comparison (plan: WideSearch), or None before they exist.
    The asserts are the plan's reading rules: the wiki text below is written for exactly this outcome."""
    A = EXP / "results/analysis-ws-h1"
    if not (A / "stats.json").exists():
        return None
    import csv
    import statistics as st
    S = json.loads((A / "stats.json").read_text(encoding="utf-8"))
    K = json.loads((A / "stats-with-flagged.json").read_text(encoding="utf-8"))
    sec = json.loads((A / "second-pass.json").read_text(encoding="utf-8"))
    sel = json.loads((EXP / "results/analysis-ws-screen/selection.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader(open(A / "ws-rows.csv", encoding="utf-8")))
    flagged = {r["id"] for r in json.loads((A / "sources.json").read_text(encoding="utf-8")) if r.get("n_hits")}
    f = lambda v, nd=1: f"{v:+.{nd}f}".replace("-", "−")  # noqa: E731
    ci = lambda x, nd=1: f"{f(x['est'], nd)} [{f(x['lo'], nd)}, {f(x['hi'], nd)}]"  # noqa: E731
    c = lambda m, k, src=S: src["metrics"][m]["comparisons"][k]  # noqa: E731
    for k in ("H1e", "H1n"):                                   # 没测出: the interval holds 0 and is not inside +-5
        assert c("f1_item", k)["lo"] < 0 < c("f1_item", k)["hi"] and c("f1_item", k)["hi"] > 5, "the WideSearch outcome changed: rewrite the wiki text"
        assert c("r_item", k)["lo"] > 0 and c("p_item", k)["lo"] < 0 < c("p_item", k)["hi"]
    assert -5 <= c("f1_item", "ENC")["lo"] and c("f1_item", "ENC")["hi"] <= 5
    assert c("r_item", "H1n")["hi"] < 11.8, "recall gain no longer below the office tasks' interval"
    by = {}
    for r in rows:
        by.setdefault(r["group"], []).append(r)
    kids = {g: [float(r["children"]) for r in rs] for g, rs in by.items()}
    G = S["groups"]
    names = {"D0": "不给委派工具", "W-D1-K8": "出厂默认", "W-E-D1-K8": "出厂默认 + 鼓励并行"}
    table = [["组", "逐项 F1", "和不给委派工具的差 [95% 区间]", "召回率", "精确率", "估算总费用（元/次）", "实际时长（分钟）", "subagent 数"]]
    for g, k in (("D0", None), ("W-D1-K8", "H1n"), ("W-E-D1-K8", "H1e")):
        v = G[g]
        table.append([names[g], f"{v['f1_item']:.1f}", ci(c("f1_item", k)) if k else "—", f"{v['r_item']:.1f}", f"{v['p_item']:.1f}",
                      f"{v['total_cost_peak']:.2f}" + (f"（×{c('total_cost_peak', k)['est']:.2f}）" if k else ""),
                      f"{v['minutes']:.1f}" + (f"（×{c('minutes', k)['est']:.2f}）" if k else ""), f"{v['children']:.1f}"])
    n_at_top = sum(1 for t in sel["tasks"] if t["f1_item"] >= 90)
    return {"table": table, "h1n": ci(c("f1_item", "H1n")), "h1e": ci(c("f1_item", "H1e")), "enc": ci(c("f1_item", "ENC")),
            "r1n": ci(c("r_item", "H1n")), "r1e": ci(c("r_item", "H1e")), "holm_r": max(c("r_item", "H1n")["p_holm"], c("r_item", "H1e")["p_holm"]),
            "cost_n": c("total_cost_peak", "H1n")["est"], "cost_e": c("total_cost_peak", "H1e")["est"],
            "pairs_n": c("f1_item", "H1n")["n"], "pairs_e": c("f1_item", "H1e")["n"], "n_tasks": len({r["task"] for r in rows}), "runs": len(rows),
            "screen_runs": sel["runs"], "screen_top": n_at_top, "screen_flagged": len(sel["flagged_runs"]),
            "flagged": len(flagged), "flag_by": {g: sum(r["id"] in flagged for r in rs) for g, rs in by.items()},
            "spawn_n": sum(x > 0 for x in kids["W-D1-K8"]), "spawn_e": sum(x > 0 for x in kids["W-E-D1-K8"]),
            "kids_n": st.mean(x for x in kids["W-D1-K8"] if x > 0), "kids_e": st.mean(x for x in kids["W-E-D1-K8"] if x > 0), "kids_max": int(max(kids["W-D1-K8"])),
            "cap_n": sum(float(r["capacity_rejects"] or 0) > 0 for r in by["W-D1-K8"]), "cap_e": sum(float(r["capacity_rejects"] or 0) > 0 for r in by["W-E-D1-K8"]),
            "all_n": ci(c("f1_item", "H1n", K)), "all_e": ci(c("f1_item", "H1e", K)),
            "sec_n": sec["runs"], "sec_abs": sec["mean_abs_diff"], "sec_max": sec["max_abs_diff"],
            "g_runs": (G["D0"]["n"], G["W-D1-K8"]["n"], G["W-E-D1-K8"]["n"])}


def mech() -> dict | None:
    """Numbers of step 1 of the follow-up plan (plan: 补强计划 第 1 步): the 180 office reports judged against the fact
    lists afterwards, the search-volume look at the confirmation batch and the context sizes; None before they exist.
    The asserts are the readings recorded in the plan: the wiki text below is written for exactly this outcome."""
    H, Wt, P1, M = (EXP / "results/analysis-facts-highk", EXP / "results/analysis-facts-wait2", EXP / "results/analysis-facts-step1",
                    EXP / "results/analysis-mechanism")
    if not (H / "stats.json").exists() or not (Wt / "stats.json").exists() or not (P1 / "pooled-depth-k8.json").exists():
        return None
    import csv
    import math
    import statistics as st
    hs = json.loads((H / "stats.json").read_text(encoding="utf-8"))["metrics"]
    ws_ = json.loads((Wt / "stats.json").read_text(encoding="utf-8"))["metrics"]
    pooled = json.loads((P1 / "pooled-depth-k8.json").read_text(encoding="utf-8"))
    eff = json.loads((M / "effort-curve-confirm.json").read_text(encoding="utf-8"))
    where = json.loads((M / "judge-where-check.json").read_text(encoding="utf-8"))
    gm = {(r["batch"], r["group"]): r for r in csv.DictReader(open(P1 / "group-means-all.csv", encoding="utf-8"))}
    f = lambda v, nd=1: f"{v:+.{nd}f}".replace("-", "−")  # noqa: E731
    ci = lambda x, nd=1: f"{f(x['est'], nd)} [{f(x['lo'], nd)}, {f(x['hi'], nd)}]"  # noqa: E731
    hc = lambda k, m="right_pct": hs[m]["comparisons"][k]  # noqa: E731
    wc = lambda k, m="right_pct": ws_[m]["comparisons"][k]  # noqa: E731
    h1, h2, h3, wd2, wd3, n2, n3 = hc("H1"), hc("H2"), hc("H3"), wc("WD2"), wc("WD3"), wc("N2"), wc("N3")
    assert h1["hi"] < 0 and h1["p_holm"] > 0.05, "H1 changed: rewrite the K = 64 sentence"
    assert h2["lo"] < 0 < h2["hi"] and h2["hi"] > 8, "H2 is no longer 没测出"
    assert h3["lo"] < 0 < h3["hi"] and -8 <= h3["lo"] and h3["hi"] <= 8, "H3 is no longer 没有差别"
    assert all(c["lo"] < 0 < c["hi"] and c["hi"] > 8 for c in (wd2, wd3)), "WD2 / WD3 are no longer 没测出"
    assert all(-8 <= c["lo"] and c["hi"] <= 8 for c in (n2, n3)), "N2 / N3 are no longer inside ±8"
    assert h2["hi"] < 10.5 and h3["hi"] < 11.4, "the intervals no longer lie below the straight-line prediction"
    assert pooled["DN"]["lo"] > 0, "the pooled depth-2 interval holds 0 again"
    rows = list(csv.DictReader(open(EXP / "results/analysis-office-highk/rows-all.csv", encoding="utf-8")))
    ans = lambda g: st.mean(float(r["answer_s"]) for r in rows if r["group"] == g and r["answer_s"]) / 60  # noqa: E731
    ratio = lambda c: math.exp(c["est"])  # noqa: E731
    g_ = lambda b, g, k: float(gm[(b, g)][k])  # noqa: E731

    def line(label, b, g, c, verdict, cost, mins, tr):
        return [label, f"{g_(b, g, 'right_n'):.1f}", ci(c) if c else "—", verdict, f"{g_(b, g, 'total_cost_peak'):.2f}" + (f"（×{cost:.2f}）" if cost else ""),
                f"{mins:.1f}" + (f"（×{tr:.2f}）" if tr else ""), f"{g_(b, g, 'children'):.1f}", str(int(g_(b, g, 'search_aux') + 0.5))]
    table = [["组", "写对的事实（条）", "和同批深度 1、K=8 的差（个百分点，95% 区间）", "判断", "估算总费用，元/次（倍数）", "时长，分钟（倍数）", "subagent 数", "搜索请求数"],
             line("K=64 那一批：深度 1、K=8（基准）", "highk", "W-D1-K8", None, "—", None, ans("W-D1-K8"), None),
             line("深度 1、K=64", "highk", "W-D1-K64", h1, "区间不含 0，校正后不显著", ratio(hc("H1", "total_cost_peak")), ans("W-D1-K64"), ratio(hc("H1", "answer_s"))),
             line("深度 2、K=64", "highk", "W-D2-K64", h2, "没测出差别", ratio(hc("H2", "total_cost_peak")), ans("W-D2-K64"), ratio(hc("H2", "answer_s"))),
             line("深度 3、K=64", "highk", "W-D3-K64", h3, "没有差别", ratio(hc("H3", "total_cost_peak")), ans("W-D3-K64"), ratio(hc("H3", "answer_s"))),
             line("等subagent回来那一批：深度 1、K=8（基准）", "wait2", "W-D1-K8", None, "—", None, g_("wait2", "W-D1-K8", "minutes"), None),
             line("深度 2、K=8", "wait2", "W-D2-K8", wd2, "没测出差别", ratio(wc("WD2", "total_cost_peak")), g_("wait2", "W-D2-K8", "minutes"), ratio(wc("WD2", "seconds"))),
             line("深度 3、K=8", "wait2", "W-D3-K8", wd3, "没测出差别", ratio(wc("WD3", "total_cost_peak")), g_("wait2", "W-D3-K8", "minutes"), ratio(wc("WD3", "seconds")))]
    per = lambda b, g, base: (g_(b, g, "total_cost_peak") - g_(b, base, "total_cost_peak")) / (g_(b, g, "right_n") - g_(b, base, "right_n"))  # noqa: E731
    cx = {n: json.loads((M / f"ctx-peak-{n}.json").read_text(encoding="utf-8"))["summary"] for n in ("office-confirm", "office-highk", "xl-main")}
    med = lambda n, g, d: next(x["peak_median"] for x in cx[n] if x["group"] == g and x["depth"] == d) / 1e4  # noqa: E731
    office_max = max(x["peak_max"] for n in ("office-confirm", "office-highk") for x in cx[n]) / 1e4
    l1 = [x["peak_median"] / 1e4 for x in cx["office-confirm"] if x["depth"] == 1]
    assert all(x["with_compact_events"] == 0 for n in cx for x in cx[n]), "a session was compacted after all"
    E, G = eff["search"], eff["groups"]
    sec = {k: json.loads((d / "second-pass.json").read_text(encoding="utf-8")) for k, d in (("h", H), ("w", Wt))}
    return {"table": table, "h1": ci(h1), "h1_holm": h1["p_holm"], "h2": ci(h2), "h3": ci(h3), "wd2": ci(wd2), "wd3": ci(wd3), "n2": ci(n2), "n3": ci(n3),
            "h2e": f(h2["est"]), "h3e": f(h3["est"]), "h2hi": f(h2["hi"]), "h3hi": f(h3["hi"]), "wd2e": f(wd2["est"]), "wd3e": f(wd3["est"]),
            "cost_h": (ratio(hc("H2", "total_cost_peak")), ratio(hc("H3", "total_cost_peak"))), "cost_w": (ratio(wc("WD2", "total_cost_peak")), ratio(wc("WD3", "total_cost_peak"))),
            "search_h": (ratio(hc("H2", "search_aux")), ratio(hc("H3", "search_aux"))), "ans_h": (ratio(hc("H2", "answer_s")), ratio(hc("H3", "answer_s"))),
            "kids": (g_("highk", "W-D1-K8", "children"), g_("highk", "W-D1-K64", "children"), g_("highk", "W-D2-K64", "children"), g_("highk", "W-D3-K64", "children")),
            "base_h": g_("highk", "W-D1-K8", "right_pct"), "base_w": g_("wait2", "W-D1-K8", "right_pct"),
            "search_k": (g_("highk", "W-D1-K8", "search_aux"), g_("highk", "W-D1-K64", "search_aux")),
            "search_d": (g_("highk", "W-D2-K64", "search_aux"), g_("highk", "W-D3-K64", "search_aux")),
            "dn": ci(pooled["DN"]), "dn_n": pooled["DN"]["n"], "dn_by": [pooled["DN"]["by_batch"][b]["mean"] for b in ("formal", "confirm", "wait2")],
            "per_fact": (per("wait2", "W-D2-K8", "W-D1-K8"), per("confirm", "D2-K8", "D1-K8")),
            "per_fact0": (g_("confirm", "D1-K8", "total_cost_peak") - g_("confirm", "D0", "total_cost_peak")) / (g_("confirm", "D1-K8", "right_n") - g_("confirm", "D0", "right_n")),
            "slope": E["slope_per_doubling"], "eq_k1": ci(E["at_equal_effort"]["D1-K1"]), "eq_d2": ci(E["at_equal_effort"]["D2-K8"]),
            "mins": (min(v["minutes"] for v in G.values()), max(v["minutes"] for v in G.values())),
            "s": {g: G[g]["search"] for g in G}, "d0_range": (G["D0"]["search_min"], G["D0"]["search_max"]), "k8_range": (G["D1-K8"]["search_min"], G["D1-K8"]["search_max"]),
            "ctx_root": (med("office-confirm", "D0", 0), med("office-confirm", "D1-K8", 0), med("office-confirm", "D2-K8", 0)), "ctx_office_max": office_max,
            "ctx_l1": (min(l1), max(l1)), "ctx_l2": med("office-confirm", "D2-K8", 2), "ctx_xl_max": max(x["peak_max"] for x in cx["xl-main"]) / 1e4,
            "sec": (100 * sec["h"]["same"] / sec["h"]["n"], 100 * sec["w"]["same"] / sec["w"]["n"]), "sec_n": sec["h"]["reports"] + sec["w"]["reports"],
            "where_b": 100 * where["b_vs_a1"]["right_vs_not"], "where_a": 100 * where["a1_vs_a2"]["right_vs_not"], "where_n": where["b_vs_a1"]["reports"],
            "where_diff": abs(where["b_vs_a1"]["mean_diff_right"])}


def pkg() -> dict | None:
    """Numbers of step 5 of the follow-up plan (48-module package, depth 1 / 2 with 16 and 64 slots), or None before
    they exist. The asserts are the readings recorded in the plan."""
    A = EXP / "results/analysis-xl-depth"
    if not (A / "stats.json").exists():
        return None
    import csv
    import math
    S = json.loads((A / "stats.json").read_text(encoding="utf-8"))["metrics"]
    rows = list(csv.DictReader(open(A / "rows-all.csv", encoding="utf-8")))
    ok = [r for r in rows if r["early_finish"] == "0" and r["no_answer"] == "0"]
    d2 = [r for r in ok if "-D2-" in r["group"]]
    assert sum(int(r["layer2_writers"]) for r in d2) == 0, "a second-level subagent wrote package files: rewrite the text"
    c = lambda k, m="answer_s": S[m]["comparisons"][k]  # noqa: E731
    for k in ("DE16", "DE64"):
        assert c(k)["lo"] < 0 < c(k)["hi"], "a depth contrast of the package batch no longer holds 1"
    r3 = lambda x: f"×{math.exp(x['est']):.2f} [{math.exp(x['lo']):.2f}, {math.exp(x['hi']):.2f}]"  # noqa: E731
    kids = [float(r["layer1_kids"]) for r in ok]
    return {"runs": len(rows), "d2_runs": len(d2), "d2_with_l2": sum(1 for r in d2 if int(r["layer2_kids"]) > 0), "early": sum(1 for r in rows if r["early_finish"] == "1"),
            "de16": r3(c("DE16")), "de64": r3(c("DE64")), "cost16": math.exp(c("DE16", "model_cost_peak")["est"]), "cost64": math.exp(c("DE64", "model_cost_peak")["est"]),
            "l1_kids": round(sum(kids) / len(kids), 1)}


def floor() -> dict | None:
    """Numbers of step 4 of the follow-up plan (batch office-floor: the single agent told to search more, and the
    default with the keep-everything sentence), or None before they exist. The asserts are the readings recorded in
    the plan (第 4 步的执行记录（六）、（八）): the wiki text below is written for exactly this outcome."""
    A, B = EXP / "results/analysis-facts-floor", EXP / "results/analysis-office-floor"
    if not (A / "stats.json").exists() or not (A / "stats-noopen.json").exists() or not (A / "extra.json").exists():
        return None
    import csv
    import math
    S = json.loads((A / "stats.json").read_text(encoding="utf-8"))["metrics"]
    N = json.loads((A / "stats-noopen.json").read_text(encoding="utf-8"))["metrics"]
    X = json.loads((A / "extra.json").read_text(encoding="utf-8"))
    sec = json.loads((A / "second-pass.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader(open(B / "rows-all.csv", encoding="utf-8")))
    facts = {r["id"]: r for r in csv.DictReader(open(A / "fact-rows.csv", encoding="utf-8"))}
    ov = {r["id"]: r for r in csv.DictReader(open(B / "search-overlap.csv", encoding="utf-8"))}
    ctx = json.loads((B / "ctx-peak.json").read_text(encoding="utf-8"))
    f = lambda v, nd=1: f"{v:+.{nd}f}".replace("-", "−")  # noqa: E731
    ci = lambda x, nd=1: f"{f(x['est'], nd)} [{f(x['lo'], nd)}, {f(x['hi'], nd)}]"  # noqa: E731
    neg = lambda x: {"est": -x["est"], "lo": -x["hi"], "hi": -x["lo"]}  # noqa: E731
    c = lambda k, m="right_pct", src=S: src[m]["comparisons"][k]  # noqa: E731
    ratio = lambda k, m, src=S: math.exp(c(k, m, src)["est"])  # noqa: E731
    r3 = lambda k, m, src=S: f"×{math.exp(c(k, m, src)['est']):.2f} [{math.exp(c(k, m, src)['lo']):.2f}, {math.exp(c(k, m, src)['hi']):.2f}]"  # noqa: E731
    prim, ef, h1, ka, ka_n = c("PRIM"), c("EF"), c("H1"), c("KA"), c("KA", src=N)
    gap, vol, fetch = X["gap_closed"], X["volume"], X["fetch"]
    reg, reg_f, itt = X["regression"]["E-D0_vs_D1-K8_at_equal_search"], X["regression_finished"]["E-D0_vs_D1-K8_at_equal_search"], X["keep_all_every_run"]
    assert prim["hi"] < 0 and ef["lo"] > 0 and h1["lo"] > 0, "the main contrasts of step 4 changed: rewrite the wiki text"
    assert vol["matched"] and fetch["padding_suspected"] and reg["hi"] < 0 and reg_f["hi"] < 0 and X["volume"]["regression_usable"], "the readings of step 4 changed"
    assert 0.3 < gap["est"] < 0.7 and gap["lo"] > 0, "the share of the gap closed changed"
    assert ka["lo"] < 0 < ka["hi"] and ka_n["lo"] > 0 and itt["hi"] < 0, "the keep-everything contrasts changed"
    assert c("PRIM", "seconds")["lo"] < 0 < c("PRIM", "seconds")["hi"], "the time ratio of E-D0 against the default no longer holds 1"
    assert c("PRIM", "wrong_firm_n")["lo"] > 0 and c("KA", "wrong_firm_n", N)["lo"] > 0, "the wrong-fact contrasts changed"
    early = [r for r in rows if r["group"] == "N-D1-K8" and float(r.get("open_children_at_end") or 0) > 0]
    assert len(early) == 8 and not [r for r in rows if r["group"] != "N-D1-K8" and float(r.get("open_children_at_end") or 0) > 0]
    G = X["finished_task_equal"]
    names = [("D0", "不给委派工具"), ("E-D0", "单agent + 多查的要求"), ("D1-K8", "出厂默认"), ("N-D1-K8", f"出厂默认 + “都写进去”（写完的 {G['N-D1-K8']['runs']} 次）")]
    diff = {"D0": ci(neg(h1)), "E-D0": ci(prim), "D1-K8": "—", "N-D1-K8": ci(ka_n)}
    cost = {"D0": 1 / ratio("H1", "total_cost_peak"), "E-D0": ratio("PRIM", "total_cost_peak"), "D1-K8": None, "N-D1-K8": ratio("KA", "total_cost_peak", N)}
    table = [["组", "写对的事实（条）", "和出厂默认的差（个百分点，95% 区间）", "搜索请求数", "打开的网页数", "估算总费用，元/次（倍数）", "时长，分钟", "报告字符数"]]
    for g, name in names:
        v = G[g]
        table.append([name, f"{v['right_n']:.1f}", diff[g], f"{v['search']:.0f}", f"{v['pages']:.0f}",
                      f"{v['cost']:.2f}" + (f"（×{cost[g]:.2f}）" if cost[g] else ""), f"{v['minutes']:.1f}", f"{v['chars'] / 1e4:.1f} 万"])
    big = [r for r in ctx["rows"] if r["group"] == "E-D0" and r["peak"] > 500000]
    pages_big = sorted(float(ov[r["id"]]["pages_distinct"]) for r in big)
    assert sum(1 for r in ctx["rows"] if r.get("compact")) == 1, "the number of runs with context pruning changed"
    adj = sorted((abs(reg["est"]), abs(reg_f["est"])))
    return {"table": table, "prim": ci(prim), "ef": ci(ef), "h1": ci(h1), "ka": ci(ka), "ka_n": ci(ka_n), "ka_pairs": ka_n["n"], "gap": gap,
            "adj": f"{adj[0]:.0f}–{adj[1]:.0f}", "itt": ci(itt),
            "cost_e": ratio("PRIM", "total_cost_peak"), "time_e": r3("PRIM", "seconds"), "search_e": G["E-D0"]["search"] / G["D1-K8"]["search"], "pages_share": 100 * fetch["ratio_distinct"],
            "search_up": ratio("EF", "search_aux"), "wrong_e": c("PRIM", "wrong_firm_n")["est"], "wrong_n": c("KA", "wrong_firm_n", N)["est"],
            "ctx_big": (min(r["peak"] for r in big) / 1e4, max(r["peak"] for r in big) / 1e4), "ctx_big_n": len(big), "pages_big": (pages_big[0], pages_big[-1]),
            "cost_ka": ratio("KA", "total_cost_peak", N), "time_ka": ratio("KA", "seconds", N), "chars_ka": ratio("KA", "deliv_chars", N),
            "early": len(early), "early_incomplete": sum(1 for r in early if str(r.get("incomplete")) == "1"), "runs": len(rows), "judged": len(facts),
            "kids": (G["D1-K8"]["children"], G["N-D1-K8"]["children"]), "h1_conf": 15.5,
            "second": 100 * sec["same"] / sec["n"], "second_n": sec["reports"]}


def _line_offsets() -> dict:
    """Where the groups of the batch office-floor and the merged reports lie relative to the straight line of the
    search-volume figure (plot_wiki5.py): group mean of right % minus the line's value at the group's search volume."""
    import math
    import plot_wiki5 as p5
    f = lambda v: p5.Y0 + p5.SLOPE * math.log2(v / p5.X0)  # noqa: E731
    return {(q["batch"], q["group"]): q["y"] - f(q["x"]) for q in p5.floor_points() + p5.merge_points()}


def _line_pairs(kind: str) -> dict:
    """Same-batch merged reports against the default of the same block: difference of the distances from the straight
    line of the search-volume figure, paired by block (t interval)."""
    import csv
    import math
    import statistics as st
    import plot_wiki5 as p5
    from merge_stats import paired
    f = lambda v: p5.Y0 + p5.SLOPE * math.log2(v / p5.X0)  # noqa: E731
    idx = json.loads((EXP / "tasks/merge-b-index.json").read_text(encoding="utf-8"))
    ms = json.loads((EXP / "results/analysis-office-merge-b/merge-stats.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader(open(EXP / "results/analysis-office-floor/rows-all.csv", encoding="utf-8")))
    facts = {r["id"]: r for r in csv.DictReader(open(EXP / "results/analysis-facts-floor/fact-rows.csv", encoding="utf-8"))}
    byid = {r["id"]: r for r in rows}
    by = {(r["task"], r["group"], int(r["rep"])): r for r in rows}
    d = []
    for r in ms["rows"]:
        if r["kind"] != kind:
            continue
        m = idx[r["task"]]
        dm = r["merged_right_pct"] - f(sum(float(byid[i]["search_aux"]) for i in m["inputs"]) + r["merge_search"])
        comp = [by[(m["base_task"], "D1-K8", rep)] for rep in m["reps"]]
        d.append(dm - st.mean(float(facts[c["id"]]["right_pct"]) - f(float(c["search_aux"])) for c in comp))
    x = paired(d)
    return {"est": float(x["est"]), "lo": float(x["lo"]), "hi": float(x["hi"])}


def merge() -> dict | None:
    """Numbers of the merge control (plan: 第 3 步 and 第 3 步的执行记录（三）): merged single-agent reports against the
    default, in the same batch (office-merge-b, the formal comparison) and across a day (office-merge, descriptive).
    None before the same-batch repeat exists. The asserts are the readings recorded in the plan."""
    fb, fa = EXP / "results/analysis-office-merge-b/merge-stats.json", EXP / "results/analysis-office-merge/merge-stats.json"
    if not fb.exists() or not fa.exists():
        return None
    B, A = json.loads(fb.read_text(encoding="utf-8")), json.loads(fa.read_text(encoding="utf-8"))
    f = lambda v, nd=1: f"{v:+.{nd}f}".replace("-", "−")  # noqa: E731
    ci = lambda x, nd=1: f"{f(x['est'], nd)} [{f(x['lo'], nd)}, {f(x['hi'], nd)}]"  # noqa: E731
    rr = lambda x: f"×{x['est']:.2f}"  # noqa: E731
    cb, ca, mb, ma = B["contrasts"], A["contrasts"], B["means"], A["means"]
    key = "right_pct_same_place"
    m2, m4, m2n, m4n = cb["M2_vs_D1-K8"][key], cb["M4_vs_D1-K8"][key], cb["M2_vs_N-D1-K8"][key], cb["M4_vs_N-D1-K8"][key]
    assert -8 <= m2["lo"] and m2["hi"] <= 8 and m2["lo"] < -6, "the two-report merge against the default changed: rewrite the sentence"
    assert m4["lo"] < 0 < m4["hi"], "the four-report merge against the default no longer holds 0"
    assert m2n["hi"] < 0 and m4n["lo"] < 0 < m4n["hi"], "the contrasts against the keep-everything default changed"
    assert not B["skipped"] and mb["M2"]["researched_again"] == 0 and mb["M4"]["researched_again"] == 0
    w = cb["M2_vs_D1-K8"]["wrong_firm_n_same_place"]
    assert w["lo"] < 0 < w["hi"], "the wrong-fact contrast of the two-report merge changed"

    def row(name: str, M: dict, c: dict, n: int) -> list:
        return [name, f"{M['merged_right_pct']:.1f}%（{M['merged_right_n']:.1f} 条）", ci(c[key]), f"{M['union_pct']:.1f}%", f"{100 * M['retention']:.0f}%",
                f"{M['total_cost']:.2f}（{rr(c['total_cost_ratio'])}）", f"{M['total_seconds_parallel'] / 60:.1f}（{rr(c['seconds_parallel_ratio'])}）", str(n)]
    table = [["做法", "合并稿写对的事实", "和出厂默认的差（个百分点，95% 区间）", "几份原稿的并集", "并集里留下的比例", "总费用，元（倍数）", "总时间，分钟（倍数）", "合并稿份数"],
             row("两份合并（同一批）", mb["M2"], cb["M2_vs_D1-K8"], mb["M2"]["tasks"]), row("四份合并（同一批）", mb["M4"], cb["M4_vs_D1-K8"], mb["M4"]["tasks"]),
             row("两份合并（原稿是前一天的）", ma["M2"], ca["M2_vs_D1-K8"], ma["M2"]["tasks"]), row("四份合并（原稿是前一天的）", ma["M4"], ca["M4_vs_D1-K8"], ma["M4"]["tasks"])]
    return {"table": table, "m2": ci(m2), "m4": ci(m4), "m2n": ci(m2n), "m4n": ci(m4n), "m2_old": ci(ca["M2_vs_D1-K8"][key]), "m4_old": ci(ca["M4_vs_D1-K8"][key]),
            "cost2": cb["M2_vs_D1-K8"]["total_cost_ratio"]["est"], "time2": cb["M2_vs_D1-K8"]["seconds_parallel_ratio"]["est"], "time2s": cb["M2_vs_D1-K8"]["seconds_serial_ratio"]["est"],
            "cost4": (cb["M4_vs_D1-K8"]["total_cost_ratio"]["est"], ca["M4_vs_D1-K8"]["total_cost_ratio"]["est"]),
            "keep": (100 * min(mb["M2"]["retention"], mb["M4"]["retention"], ma["M2"]["retention"], ma["M4"]["retention"]),
                     100 * max(mb["M2"]["retention"], mb["M4"]["retention"], ma["M2"]["retention"], ma["M4"]["retention"])),
            "one": mb["M2"]["input_mean_right_pct"], "m2e": ci(cb["M2_vs_E-D0"][key]), "n2": mb["M2"]["tasks"], "n4": mb["M4"]["tasks"], "line": _line_offsets(),
            "msearch": (min(mb["M2"]["merge_search"], mb["M4"]["merge_search"]), max(mb["M2"]["merge_search"], mb["M4"]["merge_search"])),
            "keep2": 100 * mb["M2"]["retention"], "keep4": 100 * mb["M4"]["retention"], "m4u": ci(cb["M4_vs_union"]["right_pct"]),
            "line2": ci(_line_pairs("M2")), "line4": ci(_line_pairs("M4"))}


def drb2() -> dict | None:
    """Numbers of the DeepResearch Bench II step (plan: 第 6 步的执行记录（一）到（三）): first stage, 30 Chinese tasks x
    {no delegation tools, default}, paired by task. None before it exists. The asserts are the plan's readings."""
    A = EXP / "results/analysis-drb2-h1"
    if not (A / "stats.json").exists() or not (A / "extra.json").exists():
        return None
    import csv
    S = json.loads((A / "stats.json").read_text(encoding="utf-8"))
    K = json.loads((A / "stats-with-flagged.json").read_text(encoding="utf-8"))
    E = json.loads((A / "extra.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader(open(A / "drb2-rows.csv", encoding="utf-8")))
    idx = json.loads((EXP / "tasks/drb2-index.json").read_text(encoding="utf-8"))
    probe = json.loads((EXP / "results/drb2-score/refusal-probe.json").read_text(encoding="utf-8")) if (EXP / "results/drb2-score/refusal-probe.json").exists() else {}
    f = lambda v, nd=1: f"{v:+.{nd}f}".replace("-", "−")  # noqa: E731
    ci = lambda x, nd=1: f"{f(x['est'], nd)} [{f(x['lo'], nd)}, {f(x['hi'], nd)}]"  # noqa: E731
    c = lambda m, k="H1", src=S: src["metrics"][m]["comparisons"][k]  # noqa: E731
    h = c("total")
    assert h["lo"] > 0 and c("info_recall")["lo"] > 0, "the first-stage outcome changed: rewrite the wiki text"
    assert c("analysis")["lo"] < 0 < c("analysis")["hi"] and c("presentation")["lo"] < 0 < c("presentation")["hi"]
    G = S["groups"]
    table = [["组", "总分", "和不给委派工具的差 [95% 区间]", "信息召回", "分析", "呈现", "估算总费用（元/次）", "时长（分钟）", "subagent 数"]]
    for g, name in (("D0", "不给委派工具"), ("W-D1-K8", "出厂默认")):
        v = G[g]
        table.append([name, f"{v['total']:.1f}", ci(h) if g != "D0" else "—", f"{v['info_recall']:.1f}", f"{v['analysis']:.1f}", f"{v['presentation']:.1f}",
                      f"{v['total_cost_peak']:.2f}" + (f"（×{c('total_cost_peak')['est']:.2f}）" if g != "D0" else ""),
                      f"{v['minutes']:.1f}" + (f"（×{c('minutes')['est']:.2f}）" if g != "D0" else ""), f"{v['children']:.1f}"])
    items = [sum(v["rubric_items"].values()) for v in idx.values() if v["set"] == "sample"]
    flagged = sum(E["flagged"].values())
    pt = E["per_task"]
    none = [x for x in pt if x["subagents"][1] == 0]
    used = [x for x in pt if x["subagents"][1] > 0]
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    return {"table": table, "h1": ci(h), "p": h["p"], "pairs": h["n"], "up": h["up"], "down": h["down"], "same": h["same"], "recall": ci(c("info_recall")),
            "analysis": ci(c("analysis")), "present": ci(c("presentation")), "cost": c("total_cost_peak")["est"], "time": c("minutes")["est"],
            "all": ci(c("total", src=K)), "runs": len(rows), "tasks": len({r["task"] for r in rows}), "flagged": flagged,
            "items": (min(items), max(items), sum(items)), "refused": sorted(int(k) for k, v in probe.items() if v.get("stop") == "refusal"), "probed": len(probe),
            "none_n": len(none), "none_range": (f(min(x["total"][1] - x["total"][0] for x in none)), f(max(x["total"][1] - x["total"][0] for x in none))), "sd": h["sd"],
            "sec_n": E["second"]["reports"], "sec_agree": 100 * E["second"]["item_agreement"], "sec_abs": E["second"]["mean_abs_diff_total"], "sec_max": E["second"]["max_abs_diff_total"],
            "kids": G["W-D1-K8"]["children"], "search": (G["D0"]["search_aux"], G["W-D1-K8"]["search_aux"])}


def depthall() -> dict | None:
    """The depth contrast of all five office batches side by side and pooled (scripts/depth_all.py), what the subagents
    handed back against the final reports (scripts/relay_loss.py) and the batch with the keep-everything sentence.
    None before they exist. The asserts are the readings recorded in the plan."""
    fd, fr, fk = EXP / "results/analysis-depth-all/depth-all.json", EXP / "results/analysis-relay/relay-loss.json", EXP / "results/analysis-facts-keepdepth/stats.json"
    if not fd.exists() or not fr.exists() or not fk.exists():
        return None
    import math
    D, R = json.loads(fd.read_text(encoding="utf-8")), json.loads(fr.read_text(encoding="utf-8"))
    K = json.loads(fk.read_text(encoding="utf-8"))["metrics"]
    f = lambda v, nd=1: f"{v:+.{nd}f}".replace("-", "−")  # noqa: E731
    ci = lambda x, nd=1: f"{f(x['est'], nd)} [{f(x['lo'], nd)}, {f(x['hi'], nd)}]"  # noqa: E731
    rows = {(r["batch"], r["depth"]): r for r in D["rows"]}
    p2, p3 = D["pooled"]["2"], D["pooled"]["3"]
    d2 = [r for r in D["rows"] if r["depth"] == 2]
    assert len(d2) == 5 and all(r["est"] > 0 and r["lo"] < 0 for r in d2), "a single batch's depth-2 contrast changed"
    assert p2["lo"] > 0 and p3["lo"] < 0 < p3["hi"], "the pooled depth contrasts changed"
    dk = K["right_pct"]["comparisons"]["DK"]
    assert dk["lo"] < 0 < dk["hi"] and dk["hi"] > 8, "the keep-everything depth contrast is no longer 没测出"
    order = [("formal", "正式实验（K=8，进程不等subagent）"), ("confirm", "确认实验（K=8，进程不等subagent）"), ("wait2", "进程等subagent回来（K=8）"),
             ("highk", "深度 2、3 的名额放到 64（进程等subagent回来）"), ("keep", "题面要求“都写进去”（K=8，进程等subagent回来）")]
    table = [["批（跑法）", "深度 2 对深度 1（个百分点，95% 区间）", "对数", "费用之比", "深度 3 对深度 1", "对数", "费用之比"]]
    for name, label in order:
        r2, r3 = rows[(name, 2)], rows.get((name, 3))
        table.append([label, ci(r2), str(r2["pairs"]), f"×{r2['cost_ratio']:.2f}", ci(r3) if r3 else "—", str(r3["pairs"]) if r3 else "—", f"×{r3['cost_ratio']:.2f}" if r3 else "—"])
    table.append(["合在一起（事后汇总）", ci(p2), str(p2["pairs"]), f"×{p2['cost_ratio']:.2f}", ci(p3), str(p3["pairs"]), f"×{p3['cost_ratio']:.2f}"])
    G = R["groups"]
    shares = [100 * g["lost_share"] for g in G.values()]
    assert max(shares) < 10, "a group lost more than a tenth of what was handed back"
    c = R["contrasts"]["office-confirm:D2-K8_vs_D1-K8"]["lost_n"]
    assert c["lo"] < 0 < c["hi"], "depth 2 now loses a different number of handed-back facts"
    est2 = [r["est"] for r in d2]
    later, k8, d32 = D["pooled"]["2_later_three"], D["pooled"]["2_k8"], D["pooled"]["3_vs_2"]
    assert later["lo"] > 0 and d32["lo"] < 0 < d32["hi"] and -8 <= d32["lo"] and d32["hi"] <= 8, "the later-three check or the depth-3-against-2 contrast changed"
    w2 = rows[("wait2", 2)]["by_task"]
    slots = 97.5
    return {"table": table, "p2": ci(p2), "p2n": p2["pairs"], "p2p": p2["p"], "p3": ci(p3), "p3n": p3["pairs"],
            "range2": (min(est2), max(est2)), "facts2": (p2["est"] * slots / 100, p2["lo"] * slots / 100, p2["hi"] * slots / 100),
            "later": ci(later), "later_n": later["pairs"], "later_p": later["p"], "cost_k8": (k8["cost_ratio"], k8["cost_lo"], k8["cost_hi"]),
            "cost_64": rows[("highk", 2)]["cost_ratio"], "d32": ci(d32), "d32n": d32["pairs"], "d32cost": d32["cost_ratio"], "w2": (f(w2["o1"]), f(w2["o2"])),
            "dk": ci(dk), "dk_cost": math.exp(K["total_cost_peak"]["comparisons"]["DK"]["est"]),
            "lost": (min(shares), max(shares)), "lost_runs": sum(g["runs"] for g in G.values()), "lost_d2": ci(c),
            "lost_n": (min(g["lost_n"] for g in G.values()), max(g["lost_n"] for g in G.values()))}


def drb2kd() -> dict | None:
    """Numbers of the second stage of the DeepResearch Bench II step (batch drb2-kd: the same 30 tasks x {W-D1-K1,
    W-D1-K8, W-D2-K8}, paired by task; plan: 第 6 步的执行记录（三）). None before it exists. The wording of each
    contrast follows the plan's reading rule and is chosen here from the numbers."""
    import os
    A = Path(os.environ["DRB2KD_DIR"]) if os.environ.get("DRB2KD_DIR") else EXP / "results/analysis-drb2-kd"  # the variable is for a dry test with made-up files
    if not (A / "stats.json").exists() or not (A / "extra.json").exists():
        return None
    S = json.loads((A / "stats.json").read_text(encoding="utf-8"))
    K = json.loads((A / "stats-with-flagged.json").read_text(encoding="utf-8"))
    E = json.loads((A / "extra.json").read_text(encoding="utf-8"))
    T = json.loads((A / "retest.json").read_text(encoding="utf-8")) if (A / "retest.json").exists() else None
    f = lambda v, nd=1: f"{v:+.{nd}f}".replace("-", "−")  # noqa: E731
    ci = lambda x, nd=1: f"{f(x['est'], nd)} [{f(x['lo'], nd)}, {f(x['hi'], nd)}]"  # noqa: E731
    c = lambda m, k, src=S: src["metrics"][m]["comparisons"][k]  # noqa: E731

    def reading(x: dict) -> str:
        if x.get("p_holm", x["p"]) < 0.05 and (x["lo"] > 0 or x["hi"] < 0):
            return "高" if x["lo"] > 0 else "低"
        if x["lo"] >= -5 and x["hi"] <= 5:
            return "没有实际差别"
        return "没测出差别"
    import csv
    names = (("W-D1-K8", "深度 1、K=8（出厂默认）", None), ("W-D1-K1", "深度 1、K=1", "K1"), ("W-D2-K8", "深度 2、K=8", "D2"))
    # group means over the tasks that have a usable run in all three groups, so that the rows can be compared with each other
    flag = {r["id"] for r in json.loads((A / "sources.json").read_text(encoding="utf-8")) if r.get("n_hits")}
    rows = [r for r in csv.DictReader(open(A / "drb2-rows.csv", encoding="utf-8")) if r["id"] not in flag and r.get("total") not in ("", None)]
    have = {}
    for r in rows:
        have.setdefault(r["task"], set()).add(r["group"])
    common = sorted(t for t, gs in have.items() if all(g in gs for g, _, _ in names))
    cols = {"total": "total", "info_recall": "info_recall", "total_cost_peak": "total_cost_peak", "minutes": "minutes", "children": "children", "search_aux": "search_aux"}
    G = {g: {k: sum(float(r[c_]) for r in rows if r["group"] == g and r["task"] in common) / len(common) for k, c_ in cols.items()} for g, _, _ in names}
    table = [["组", "总分", "和出厂默认的差 [95% 区间]", "判断", "信息召回", "估算总费用（元/次）", "时长（分钟）", "subagent 数", "搜索请求"]]
    for g, name, k in names:
        v = G[g]
        table.append([name, f"{v['total']:.1f}", ci(c("total", k)) if k else "—", reading(c("total", k)) if k else "—", f"{v['info_recall']:.1f}",
                      f"{v['total_cost_peak']:.2f}", f"{v['minutes']:.1f}", f"{v['children']:.1f}", f"{v['search_aux']:.0f}"])
    out = {"table": table, "pairs": (c("total", "K1")["n"], c("total", "D2")["n"]), "flagged": sum(E["flagged"].values()), "flagged_d2": E["flagged"].get("W-D2-K8", 0),
           "runs": E["runs"], "common": len(common), "kids": {g: G[g]["children"] for g, _, _ in names}}
    for k in ("K1", "D2"):
        x = c("total", k)
        out[k] = {"ci": ci(x), "reading": reading(x), "p_holm": x.get("p_holm", x["p"]), "recall": ci(c("info_recall", k)), "recall_reading": reading(c("info_recall", k)),
                  "cost": c("total_cost_peak", k)["est"], "time": c("minutes", k)["est"], "all": ci(c("total", k, K)), "est": x["est"]}
    if T is not None:
        out["retest"] = {"tasks": T["tasks"], "abs": T["total"]["mean_abs_diff"], "sd": T["total"]["sd_diff"], "mean": T["total"]["mean_diff"], "max": T["total"]["max_abs_diff"]}
    if "second" in E:
        out["second"] = {"n": E["second"]["reports"], "agree": 100 * E["second"]["item_agreement"], "abs": E["second"]["mean_abs_diff_total"]}
    return out


def all_steps() -> list:
    """STEPS plus the re-grade of the office reports, top of the page to the bottom."""
    steps = [dict(s_, items=list(s_.get("items", []))) for s_ in STEPS]
    R = regrade()
    if R is None:
        return steps
    by = {s_["name"]: s_ for s_ in steps}
    lead = "办公题按事实清单逐条判（o1 96 条、o2 99 条事实，逐条对照官方页面）"
    F = R["conf"]
    new = f"新跑 {F['runs']} 次确认"
    by["A1-depth"]["items"].insert(0, ("text", f"{lead}：深度对写对的事实条数没有显著影响（重评 D=2、3 对 D=1：{R['d2']}、{R['d3']} 个百分点；"
                                               f"{new}：D=2 对 D=1 {F['dn']}，费用 {F['cost_dn']:.1f} 倍）。"))
    by["A2-k"]["items"].insert(0, ("text", f"{lead}：**K=1 写对的事实更少**——{new}，写对的条目占比 K=1 对 K=8 是 {F['k1']} 个百分点（少写对约 {F['k1n']:.0f} 条，显著），"
                                           f"费用是 {F['cost_k1']:.2f} 倍；K=2 是 {F['k2']}，不显著；K=4 和 K=8 一样（{F['k4']}）。"))
    by["A3-effect"]["items"].insert(0, ("text", f"调研写报告的题按事实清单逐条判的数：不开subagent每份报告写对 {R['n0']:.0f}–{F['n0']:.0f} 条，开了以后 {R['n8']:.0f}–{F['n8']:.0f} 条"
                                                f"（正式实验的报告重评 {R['n0']:.0f} → {R['n8']:.0f}，{new} {F['n0']:.0f} → {F['n8']:.0f}），"
                                                f"写错的条数不变（每份 {F['wrong'][0]:.0f}–{F['wrong'][1]:.0f} 条）。"))
    by["F2-depth-conclusion"]["items"].insert(0, ("text", f"办公题按事实清单逐条判，深度对写对的事实条数没有显著影响：重评 K=8 下 D=2、3 对 D=1 是 {R['d2']}、{R['d3']} 个百分点；"
                                                          f"{new} D=2 对 D=1 是 {F['dn']}，费用 {F['cost_dn']:.1f} 倍。两批的点估计都是多 4–5 个百分点；"
                                                          f"按点估计算，深度 2 每多写对一条事实约多花 {F['per_fact_dn']:.1f} 元。"))
    by["G2-k-conclusion"]["items"].insert(0, ("text", f"办公题按事实清单逐条判：{new}，写对的条目占比 K=1 对 K=8 是 {F['k1']} 个百分点（少写对约 {F['k1n']:.0f} 条，显著；费用 {F['cost_k1']:.2f} 倍），"
                                                      f"K=2 是 {F['k2']}（不显著；费用 {F['cost_k2']:.2f} 倍），K=4 是 {F['k4']}（和 K=8 一样）。"
                                                      f"正式实验的报告重评方向相同（K=1 {R['k1ci']}，三个深度合并，事后对比）；重评里 K=2 的 {R['k2ci']} 在新跑的运行里没有复现。"
                                                      "K=1 不只是省钱，也少查到事实。"))
    by["H2-effect-conclusion"]["items"].insert(0, ("text", f"办公题按事实清单逐条判：开subagent后每份报告多写对约 {F['n8'] - F['n0']:.0f}–{R['gain']:.0f} 条事实"
                                                           f"（写对的条目占比：重评 {R['h1']}，{new} {F['h1']} 个百分点，都显著），写错的条数不变；"
                                                           f"也就是 3.4–{F['cost_h1']:.1f} 倍的费用换来查得更全。"))
    gain = f"{F['n8'] - F['n0']:.0f}–{R['gain']:.0f}"
    by["E-scores"]["items"].insert(0, ("text", f"图里办公题的数来自{new}实验（深度 1 → 3 没有新跑，用的是正式实验报告的重评）。评分表总分上，办公题这几项都测不出差别。"))
    by["C-task-table"]["note"] = by["C-task-table"]["note"] + f"办公题另{new}实验（o1、o2 × 6 组 × 20 次，跑法同正式实验，只按事实清单判）。"
    W = ws()
    extra_ws = []
    if W is not None:
        assert W["cap_n"] == 0, "the default group hit K = 8 after all: rewrite the behaviour bullet"
        by["A0-scope"]["items"][1] = ("text", f"办公题只有 2 道（o1、o2），每组重复跑 20–40 次：下面的区间反映的是同一道题重复跑的波动。换题的检验做了一次："
                                              f"{W['n_tasks']} 道表格收集题（公开评测集 WideSearch）上每题每组跑 1 次，开subagent的好处在主指标上没有测出来（召回率高约 5 个百分点），"
                                              "比办公题上小得多（见“允许开subagent对任务效果的影响”）。K 和深度没有在别的办公题上测。", {"color": 7})
        by["C-task-table"]["note"] = by["C-task-table"]["note"] + (
            f"表格收集题：先在 {W['screen_runs']} 道题上各跑 1 次不给委派工具的筛题，低于 90 分的 {W['n_tasks']} 道进对比；对比是 3 组 × {W['n_tasks']} 题各 1 次共 {W['runs']} 次，"
            f"按题配对。评测集是公开的，容器里屏蔽了答案所在的网站，日志里出现评测集名字的运行不计分（{W['runs']} 次里 {W['flagged']} 次）。")
        extra_ws = [
            {"name": "W5-summary", "kind": "root", "before": 15, "where": "「结论」：开subagent那条的说明下面（接在代码构建题两行后面）",
             "items": [("text", f"表格收集题（公开评测集 WideSearch 的中文题）：{W['screen_runs']} 道里有 {W['screen_top']} 道，单agent一次就做到 90 分以上；没到顶的 {W['n_tasks']} 道上，"
                                f"开subagent后逐项 F1 没测出差别（{W['h1n']}），召回率高约 5 个百分点，费用是 {W['cost_n']:.1f} 倍。")]},
            {"name": "W1-task-row", "kind": "table-row", "table": 25, "where": "「题目」的表：末尾加一行",
             "row": [f"表格收集题（公开评测集 WideSearch 的中文题，{W['n_tasks']} 道）", "联网收集信息，整理成一张指定列的表（例如“北京市文物局官网收录的免费博物馆，以及地址和开放时间”）；每题有一张人工核对的标准答案表",
                     "逐格对标准答案（精确匹配、数值容差，其余由 Opus 5.5 判是否同义），算逐项 F1"]},
            {"name": "W2-behavior", "kind": "root", "before": 35, "where": "「模型自己倾向于开的subagent数量」：要点的最后",
             "items": [("bullet", f"**表格收集题上不提醒也开subagent，但没有用满 K=8**：没到顶的 {W['n_tasks']} 道题上，出厂默认 {W['n_tasks']} 次里 {W['spawn_n']} 次开了，"
                                  f"开了的平均 {W['kids_n']:.1f} 个（最多 {W['kids_max']} 个），K=8 一次都没被碰到；题面加鼓励句以后 {W['spawn_e']} 次都开，平均 {W['kids_e']:.1f} 个，"
                                  f"{W['cap_e']} 次碰到 K=8。")]},
            {"name": "W3-effect", "kind": "root", "before": 68, "where": "「允许开subagent对任务效果的影响」：代码构建题的下面、“结论”的上面",
             "items": [("h5", f"表格收集题（WideSearch，{W['n_tasks']} 道）", True),
                       ("text", f"基准是不给委派工具；每题每组 1 次，按题配对。日志里出现评测集名字的 {W['flagged']} 次运行不计分，所以三组是 {W['g_runs'][0]}、{W['g_runs'][1]}、{W['g_runs'][2]} 次，"
                                f"两个对比是 {W['pairs_n']} 对和 {W['pairs_e']} 对。"),
                       ("table", W["table"], [150, 70, 170, 70, 70, 120, 110, 80]),
                       ("text", f"逐项 F1 没测出差别：出厂默认 {W['h1n']}，加鼓励句 {W['h1e']}；按这批的波动，约 4–6 个百分点以上的差能测出来。"
                                f"召回率（标准答案的格子里做对了多少）两组都高约 5 个百分点（{W['r1n']}、{W['r1e']}，两个对比一起校正后 p = {W['holm_r']:.3f}），精确率没有变化。"
                                f"费用是 {W['cost_n']:.1f} 倍和 {W['cost_e']:.1f} 倍。加不加鼓励句没有差别（{W['enc']}）。")]},
            {"name": "W4-effect-conclusion", "kind": "root", "before": 69, "where": "「允许开subagent对任务效果的影响」：结论的最后",
             "items": [("text", f"表格收集题（WideSearch）上：单agent在 {W['screen_runs']} 道题里的 {W['screen_top']} 道一次就做到 90 分以上；没到顶的 {W['n_tasks']} 道上，给了委派工具逐项 F1 没测出差别"
                                f"（{W['h1n']}），召回率高约 5 个百分点，费用 {W['cost_n']:.1f}–{W['cost_e']:.1f} 倍。和办公题方向相同，幅度小得多"
                                f"（办公题写对的事实占比是 {F['h1']} 个百分点）。")]},
            {"name": "W8-problems", "kind": "root", "before": 76, "where": "「运行中发现的其他问题」：接在最后",
             "items": [("ordered", f"题目来自公开评测集时，模型会在搜索结果里认出评测集，有的还会设法去找参考答案：表格收集题的 {W['runs']} 次对比运行里有 {W['flagged']} 次认出来了，"
                                   "其中几次换着地址和代理去下载评测集的文件。评测联网任务要屏蔽答案来源，并在日志里查评测集的名字。")]},
            {"name": "W7-appendix", "kind": "root", "before": 80, "where": "「附录·打分机制」：最后",
             "items": [("text", "表格收集题（WideSearch）的判分：按评测集自己的规则逐格判——主键列和需要判断同义的列由 Opus 5.5 判，数值列按给定的容差，其余精确匹配；"
                                "逐项 F1 是“交出的格子里做对的比例”（精确率）和“标准答案的格子里做对的比例”（召回率）的调和平均。"
                                f"{W['sec_n']} 份判了两遍，逐项 F1 平均相差 {W['sec_abs']:.2f} 分，最多 {W['sec_max']:.1f} 分。"
                                "这个评测集是公开的，模型拿题面去搜会搜到评测集本身，所以做了两件事：在容器里屏蔽答案所在的网站；日志里出现评测集名字或题号的运行一律不计分"
                                f"（筛题 {W['screen_runs']} 次里 {W['screen_flagged']} 次，对比 {W['runs']} 次里 {W['flagged']} 次，三组分别 {W['flag_by']['D0']}、{W['flag_by']['W-D1-K8']}、{W['flag_by']['W-E-D1-K8']} 次）。"
                                f"把这 {W['flagged']} 次也算进去，结论不变（出厂默认 {W['all_n']}，加鼓励句 {W['all_e']}）。")]},
        ]
    X = mech()
    extra_m = []
    if X is not None:
        by["A1-depth"]["items"].append(("text", f"名额放到 64、或者让进程等subagent回来再退出，结论一样（把以前两批的 180 份报告按事实清单补判，每个对比 20 对）："
                                                 f"深度 2、3 配 K=64 是 {X['h2']}、{X['h3']} 个百分点，费用 {X['cost_h'][0]:.1f}–{X['cost_h'][1]:.1f} 倍；"
                                                 f"等subagent回来、K=8 时是 {X['wd2']}、{X['wd3']}，费用 {X['cost_w'][0]:.1f}–{X['cost_w'][1]:.1f} 倍。四个区间都含 0。"))
        by["A2-k"]["items"].append(("text", f"办公题上把 K 从 8 调到 64 也没有好处：两组开的subagent一样多（{X['kids'][0]:.1f}、{X['kids'][1]:.1f} 个），名额都没被碰到；"
                                            f"写对的条目占比是 {X['h1']} 个百分点（补判 20 对，同批三个对比一起校正后 p = {X['h1_holm']:.2f}，不显著）。"))
        by["C-task-table"]["note"] = by["C-task-table"]["note"] + "办公题另把以前两批的 180 份报告（K=64 的 80 份、进程等subagent回来的 100 份）按事实清单补判。"
        extra_m = [
            {"name": "M1-effect-search", "kind": "root", "before": 63, "where": "「允许开subagent对任务效果的影响 · 办公题」：我那段“写对的条目占比相差……”的下面",
             "items": [("text", "写对多少和查了多少（事后分析，不是事前写定的对比）：把四批办公题运行的各组均值画在一起——正式实验 13 组、确认实验 6 组、补判的两批 9 组，"
                                "每组 20–40 份报告——写对的事实占比随搜索请求数上升。"),
                       ("image", "office-facts-by-search.png", "各组写对的事实条目占比和每次运行的搜索请求数（每个点是一批里的一组；直线按确认实验 6 组拟合，虚线是往外延长）"),
                       ("text", f"确认实验里，搜索请求数每翻一倍，写对的占比高约 {X['slope']:.0f} 个百分点；把搜索请求数算进去以后，各组之间剩下的差都不大，区间都含 0"
                                f"（K=1 对 K=8 是 {X['eq_k1']}，深度 2 对深度 1 是 {X['eq_d2']}）。各组用时都在 {X['mins'][0]:.1f}–{X['mins'][1]:.1f} 分钟，"
                                f"名额和深度放得越开，同样的时间里查得越多：K=1 每次约 {X['s']['D1-K1']:.0f} 个搜索请求，K=8 约 {X['s']['D1-K8']:.0f} 个，深度 2 约 {X['s']['D2-K8']:.0f} 个。"
                                f"不给委派工具的运行每次只有 {X['d0_range'][0]:.0f}–{X['d0_range'][1]:.0f} 个搜索请求，和开了subagent的（K=8 时 {X['k8_range'][0]:.0f}–{X['k8_range'][1]:.0f} 个）不重叠，"
                                "所以“单agent查同样多，写对的是不是一样多”这几批数据答不了。")]},
            {"name": "M2-depth-quota", "kind": "root", "before": 47, "where": "「深度」：结论的最后",
             "items": [("text", "名额充足（K=64）和进程等subagent回来时的深度：把以前跑过、当时只按评分表总分判的 180 份办公题报告按事实清单补判，每组 20 份，"
                                "按（题，第几次）配对。K=64 那一批的时长是到最终回答的时间，另一批是进程时长。"),
                       ("table", X["table"], [200, 70, 170, 110, 120, 110, 70, 70]),
                       ("text", f"名额放到 64 以后，深度 2、3 的subagent从 {X['kids'][0]:.1f} 个涨到 {X['kids'][2]:.0f}、{X['kids'][3]:.0f} 个，搜索请求是 {X['search_h'][0]:.1f}–{X['search_h'][1]:.1f} 倍，"
                                f"费用是 {X['cost_h'][0]:.1f}–{X['cost_h'][1]:.1f} 倍，到最终回答慢两成；写对的事实只多 {X['h2e']}、{X['h3e']} 个百分点，区间都含 0。"
                                f"按确认实验里“搜索请求每翻一倍多写对约 {X['slope']:.0f} 个百分点”的直线，这两组应该高 10–11 个百分点，实际的区间上限（{X['h2hi']}、{X['h3hi']}）都低于这个数："
                                f"搜索请求加到 {X['search_d'][0]:.0f}–{X['search_d'][1]:.0f} 个以后，再多查换来的写对条数变少了。这一批的深度 1 本身偏高（{X['base_h']:.1f}%，同样的配置在另一批是 {X['base_w']:.1f}%），"
                                f"所以少了多少定不准。进程等subagent回来（K=8）时深度 2、3 是 {X['wd2e']}、{X['wd3e']}，同样没测出；"
                                f"等不等对写对的条数没有差别（{X['n2']}、{X['n3']}）。"),
                       ("text", f"深度 2（K=8）在三批里的点估计是 {X['dn_by'][0]:+.1f}、{X['dn_by'][1]:+.1f}、{X['dn_by'][2]:+.1f} 个百分点，合起来 {X['dn_n']} 对是 {X['dn']}：方向一致，幅度小（约 4 条事实）。"
                                f"这个合并是事后做的，不算确认。费用是 1.8–1.9 倍，每多写对一条约 {X['per_fact'][1]:.1f}–{X['per_fact'][0]:.1f} 元（出厂默认相对不给委派工具是 {X['per_fact0']:.1f} 元）。"),
                       ("text", f"上下文用量：这个模型的上下文窗口是 100 万 token。办公题上，主agent单次请求的输入最多用到 {X['ctx_office_max']:.0f} 万"
                                f"（中位数：不给委派工具 {X['ctx_root'][0]:.0f} 万，出厂默认 {X['ctx_root'][1]:.0f} 万，深度 2 {X['ctx_root'][2]:.0f} 万），"
                                f"第 1 层subagent各组中位 {X['ctx_l1'][0]:.0f}–{X['ctx_l1'][1]:.0f} 万，第 2 层 {X['ctx_l2']:.0f} 万；48 模块的包上最多 {X['ctx_xl_max']:.0f} 万。"
                                "所有运行里没有一次触发上下文压缩：这些题上没有哪一层的活大到一个上下文装不下。"),
                       ("text", "对照：9 月的一篇论文（arXiv 2609.19759，模型是 DeepSeek-V4-Pro，框架是 Codex CLI）在调研报告和日常办公两个公开评测集上变过最大深度，"
                                "深度 1 → 3 的得分是 55.2 → 52.2 和 71.8 → 63.2，没有提高，方向和这里一致。")]},
            {"name": "M3-k-64", "kind": "root", "before": 57, "where": "「最大同时存活数量K」：结论的最后",
             "items": [("text", f"办公题上调大 K（补判，深度 1、K 8 → 64，20 对）：写对的条目占比 {X['h1']} 个百分点，同批三个对比一起校正后 p = {X['h1_holm']:.2f}。"
                                f"两组开的subagent一样多（{X['kids'][0]:.1f}、{X['kids'][1]:.1f} 个），名额都没被碰到，做法实际相同；同样的配置（深度 1、K=8、进程等subagent回来）"
                                f"在两批里分别是 {X['base_h']:.1f}% 和 {X['base_w']:.1f}%，相差和这个数一样大。调大 K 没有好处。"
                                f"K=1 少写对的那约 7 条事实，对应的是它每次少查四成（{X['s']['D1-K1']:.0f} 对 {X['s']['D1-K8']:.0f} 个搜索请求）。")]},
            {"name": "M4-appendix", "kind": "root", "before": 80, "where": "「附录·打分机制」：最后",
             "items": [("text", f"补判：K=64 那一批（80 份）和进程等subagent回来那一批（100 份）的报告，用同一份事实清单、同一种判法判了一遍，另 {X['sec_n']} 份判两遍"
                                f"（逐条一致率 {X['sec'][0]:.1f}%、{X['sec'][1]:.1f}%）。这次判分在开发机上跑（以前在本机）；取 {X['where_n']} 份确认实验的报告两处各判一遍对照："
                                f"“写对 / 没写对”的一致率 {X['where_b']:.1f}%，和本机自己重判一遍（{X['where_a']:.1f}%）相同，写对条数平均相差 {X['where_diff']:.2f} 条；"
                                "“待核验”和“没写”之间的互换略多，所以这两项不跨批比较。")]},
        ]
    Pk = pkg()
    if Pk is not None:
        def extend(step: str, start: str, more: str) -> None:
            items = by[step]["items"]
            i = next(i for i, it in enumerate(items) if it[0] == "text" and it[1].startswith(start))
            items[i] = ("text", items[i][1] + more) + tuple(items[i][2:])
        extend("A1-depth", "代码构建题（24 道练习不限时、48 模块的包）上放开到 D=2",
               f"名额放到 16、64 也一样：48 模块的包上，深度 2 的 {Pk['d2_runs']} 次运行没有一次用第 2 层写文件，到最终回答的时间和深度 1 相同。")
        extend("F2-depth-conclusion", "代码构建题上同样保持 1",
               f"名额够时也一样（新跑 {Pk['runs']} 次：48 模块的包，深度 1、2 各配 K=16、64，题面加不复核句）：主agent仍是一上来按子包派 11–12 个，"
               f"深度 2 的 {Pk['d2_runs']} 次有效运行里只有 {Pk['d2_with_l2']} 次出现第 2 层subagent（各 1 个，都是复核用的，没有写过要交的文件）；"
               f"到最终回答的时间，深度 2 对深度 1 是 {Pk['de16']}（K=16）和 {Pk['de64']}（K=64），模型费 ×{Pk['cost16']:.2f}、×{Pk['cost64']:.2f}。"
               f"另有 {Pk['early']} 次运行主agent说了一句要开始并行实现就结束了这一轮，一个文件没写，单列不计。")
    Fl = floor()
    if Fl is not None and X is not None:
        m1 = next(e for e in extra_m if e["name"] == "M1-effect-search")
        old_end = "所以“单agent查同样多，写对的是不是一样多”这几批数据答不了。"
        assert m1["items"][2][1].endswith(old_end)
        m1["items"][2] = ("text", m1["items"][2][1][:-len(old_end)] + "所以“单agent查同样多，写对的是不是一样多”这几批数据答不了，为此另做了下面的对照。")
        g = Fl["gap"]
        m1["items"] += [
            ("text", f"让单agent多查的对照（新跑 {Fl['runs']} 次：o1、o2 × 4 组 × 20 次，同一批，按（题，第几次）配对；对比是开跑前写定的，"
                     "“去掉提前结束的运行”这一条是开跑后、判分前补的）。"
                     "“单agent + 多查的要求”是不给委派工具、题面末尾加一句“写报告之前，请至少做 100 次网页搜索，并打开至少 100 个网页核对内容。”；"
                     "“都写进去”是出厂默认、题面末尾加一句“subagent 交回来的有来源的事实都写进最后的文件，重复的只写一次。”。"
                     "打开的网页数是 web_fetch 和命令行抓取（curl 等）合计的不同网址。"),
            ("table", Fl["table"], [190, 70, 170, 70, 70, 120, 70, 80]),
            ("text", f"**单agent多查，补上了一半左右的差距**：比不加这句多写对 {Fl['ef']} 个百分点，和出厂默认比仍是 {Fl['prim']} 个百分点。"
                     f"开subagent多写对的那部分（这一批是 {Fl['h1']}，确认实验是 +{Fl['h1_conf']}），有 {100 * g['est']:.0f}% [{100 * g['lo']:.0f}%, {100 * g['hi']:.0f}%] "
                     f"单agent多查就拿到了，费用是出厂默认的 {Fl['cost_e']:.2f} 倍，时长 {Fl['time_e']}；写错（没标待核验）的条数比出厂默认多 {Fl['wrong_e']:.1f} 条/份。"
                     f"剩下的差距这句要求没有补上。这不等于查找量已经拉平：单agent的搜索请求是出厂默认的 {Fl['search_e']:.2f} 倍，打开的网页是 {Fl['pages_share']:.0f}%；"
                     f"用回归把搜索量拉平来估，差仍有 {Fl['adj']} 个百分点（去不去掉那 2 份半成品，数不一样，只能看方向）。"
                     f"单agent上下文用得最多的 {Fl['ctx_big_n']} 次（打开了 {Fl['pages_big'][0]:.0f}–{Fl['pages_big'][1]:.0f} 页）用到 {Fl['ctx_big'][0]:.0f}–{Fl['ctx_big'][1]:.0f} 万 token（窗口 100 万），"
                     "其中一次触发了上下文裁剪。"),
            ("text", f"**要求主agent把subagent交回来的事实都写进去**：写完的 {Fl['ka_pairs']} 次比出厂默认多写对 {Fl['ka_n']} 个百分点，报告长 {100 * (Fl['chars_ka'] - 1):.0f}%，"
                     f"费用 {Fl['cost_ka']:.2f} 倍，时长 {Fl['time_ka']:.2f} 倍，写错的条数也多 {Fl['wrong_n']:.1f} 条/份（subagent也多开了，{Fl['kids'][1]:.1f} 对 {Fl['kids'][0]:.1f} 个）。"
                     f"但 40 次里有 {Fl['early']} 次主agent写一句“等待结果返回”就结束了这一轮，报告是空的或半成品（{Fl['early_incomplete']} 次不到 5,000 字符，"
                     f"另 {Fl['early'] - Fl['early_incomplete']} 次是六千多字符的半成品）；这一批进程不等subagent回来，它一结束运行就结束了。不加这句的 40 次里没有这种情况。"
                     f"把这 {Fl['early']} 次按实际交出的内容算进去（没有报告记 0），平均反而比出厂默认少：{Fl['itt']} 个百分点。"
                     "所以在进程不等subagent的跑法下，加这句话平均是亏的；多写对的那部分只出现在主agent等到subagent回来的运行里。"),
        ]
        by["C-task-table"]["note"] = by["C-task-table"]["note"] + f"办公题另新跑 {Fl['runs']} 次（让单agent多查的对照：o1、o2 × 4 组 × 20 次）。"
        m4 = next(e for e in extra_m if e["name"] == "M4-appendix")
        m4["items"].append(("text", f"让单agent多查的对照：{Fl['judged']} 份报告用同一份事实清单、同一种判法在开发机上判，另 {Fl['second_n']} 份判两遍，逐条一致率 {Fl['second']:.1f}%。"))

        def extend0(step: str, start: str, more: str) -> None:
            items = by[step]["items"]
            i = next(i for i, it in enumerate(items) if it[0] == "text" and it[1].startswith(start))
            items[i] = ("text", items[i][1] + more) + tuple(items[i][2:])
        extend0("A3-effect", "调研写报告的题按事实清单逐条判的数",
                f"多写对的这部分约一半靠“查得多”：不给委派工具、只在题面里要求多查，就能补上 {100 * g['est']:.0f}% [{100 * g['lo']:.0f}%, {100 * g['hi']:.0f}%] 的差距，"
                f"费用是出厂默认的 {Fl['cost_e']:.2f} 倍；剩下的差距这样补不上。")
        extend0("H2-effect-conclusion", "办公题按事实清单逐条判：开subagent后每份报告多写对约",
                f"多写对的这部分约一半靠“查得多”：不给委派工具、只在题面里要求多查的单agent能补上 {100 * g['est']:.0f}% [{100 * g['lo']:.0f}%, {100 * g['hi']:.0f}%] 的差距"
                f"（费用是出厂默认的 {Fl['cost_e']:.2f} 倍）；剩下的差距这样补不上，用回归把搜索量拉平来估还有 {Fl['adj']} 个百分点。")
    Mg = merge()
    if Mg is not None and Fl is not None and X is not None:
        m1 = next(e for e in extra_m if e["name"] == "M1-effect-search")
        m1["items"] += [
            ("text", "几份单agent报告合并的对照：让两个（或四个）互不通信的单agent各写一份，再由一个不给委派工具的agent合并成一份"
                     "（题面要求“有来源的事实都保留，重复的只写一次，说法不一致的重新核实”）。做了两批：一批用上面这 160 次里新跑的单agent报告，和同一批的出厂默认比，以这一批为准；"
                     "另一批用确认实验（前一天）的报告，只作描述。区组是（题，第几对），出厂默认取同样几次的平均。"),
            ("table", Mg["table"], [170, 120, 170, 90, 90, 110, 110, 70]),
            ("text", f"**两份单agent报告合并后，和一份出厂默认的没测出差别**（{Mg['m2']}；按事前定的 ±8 的范围算“一样多”，但区间下限接近 −7），"
                     f"总费用是 {Mg['cost2']:.2f} 倍，总时间 {Mg['time2']:.2f} 倍（两份原稿同时跑；一份接一份跑是 {Mg['time2s']:.2f} 倍）。"
                     f"和“要求都写进去”并且写完的出厂默认比，两份合并是 {Mg['m2n']} 个百分点，少了。"
                     f"四份合并对出厂默认在两批里是 {Mg['m4']} 和 {Mg['m4_old']}，费用 {Mg['cost4'][0]:.2f}–{Mg['cost4'][1]:.2f} 倍，同一批里区间含 0，没测出；"
                     f"对“要求都写进去”的出厂默认是 {Mg['m4n']}。"
                     f"合并这一步丢得很少：几份原稿并集里写对的条目，两份合并留下 {Mg['keep2']:.0f}%，四份合并留下 {Mg['keep4']:.0f}%（和并集的差 {Mg['m4u']} 个百分点）；"
                     f"合并这一步自己平均只做了 {Mg['msearch'][0]:.0f}–{Mg['msearch'][1]:.0f} 次搜索。"),
        ]
        L = Mg["line"]
        assert L[("floor", "E-D0")] < -3 and all(L[k] > 3 for k in (("merge-b", "M2"), ("merge-b", "M4"), ("merge", "M2"), ("merge", "M4"))) and abs(L[("floor", "D1-K8")]) < 2, \
            "the positions relative to the line changed: rewrite the sentence under the second search figure"
        lo_b, hi_b = sorted((L[("merge-b", "M2")], L[("merge-b", "M4")]))
        lo_a, hi_a = sorted((L[("merge", "M2")], L[("merge", "M4")]))
        m1["items"] += [
            ("image", "office-facts-by-search-2.png", "各组写对的事实条目占比和每次运行的搜索请求数，加上这一批的四组和几份单agent报告合并的结果"
                                                     "（合并稿的横坐标是几份原稿加合并那一步的搜索请求总和；直线同上一张图）"),
            ("text", f"把这一批的几组和合并稿放到上面那张图上看（各组均值在图上的位置，不是把搜索量拉平以后的对比）：出厂默认仍在那条线上；"
                     f"单agent被要求多查的那组比线低 {-L[('floor', 'E-D0')]:.0f} 个百分点左右；几份单agent报告合并的比线高 {lo_b:.0f}–{hi_b:.0f} 个百分点"
                     f"（原稿是前一天的那批高 {lo_a:.0f}–{hi_a:.0f} 个），“要求都写进去”并写完的出厂默认也比线高 {L[('floor', 'N-D1-K8')]:.0f} 个。"
                     f"合并稿比同批出厂默认离线更远的那部分，按区组配对是 {Mg['line2']}（两份）和 {Mg['line4']}（四份），区间都含 0。"
                     "所以这张图上能确定的只有一点：单agent在一个上下文里多查，同样的搜索量下写对的比开subagent少；“各做一遍再合并”是不是比开subagent更省搜索，这批数据定不了。"),
        ]
        by["C-task-table"]["note"] = by["C-task-table"]["note"] + f"几份单agent报告合并的对照：两批各 {Mg['n2'] + Mg['n4']} 份合并稿。"
        extend0("H2-effect-conclusion", "办公题按事实清单逐条判：开subagent后每份报告多写对约",
                f"和出厂默认差不多的条数也可以用“两个单agent各写一份、再合并”得到（差 {Mg['m2']}，没测出差别），费用是出厂默认的 {Mg['cost2']:.2f} 倍，时间 {Mg['time2']:.2f} 倍。")
    Da = depthall()
    if Da is not None and X is not None:
        m2 = next(e for e in extra_m if e["name"] == "M2-depth-quota")
        m2["items"] += [
            ("text", "深度 2、3 对深度 1 的对比，五批并排。每一批的对比都是那一批开跑前写定的，配对是同一批的（题，第几次）；最后一行是把所有配对放在一起，属于事后汇总。"),
            ("table", Da["table"], [230, 170, 50, 70, 150, 50, 70]),
            ("text", f"五批里深度 2 的点估计都是正的（{Da['range2'][0]:+.1f} 到 {Da['range2'][1]:+.1f}），没有一批单独显著；{Da['p2n']} 对合在一起是 {Da['p2']}，"
                     f"约 {Da['facts2'][0]:.0f} 条事实（区间 {Da['facts2'][1]:.0f}–{Da['facts2'][2]:.0f} 条）。合并是事后做的，而且批数增加的过程中看了不止一次，不算确认。"
                     f"可以当作检验的是：前两批提示“多 4 个百分点左右”以后才判分的三批，单独合起来是 {Da['later']}（{Da['later_n']} 对，p = {Da['later_p']:.3f}）。"
                     f"所以深度 2 在这两道办公题上有小幅提升这件事可以认为是有的；两道题在各批里并不总一致（进程等subagent回来那批 o1 {Da['w2'][0]}、o2 {Da['w2'][1]}）。"
                     "这些都是 K 不小于 8 的结果，K=1、2 时第 2 层开不出来。"
                     f"费用：K=8 的四批是 ×{Da['cost_k8'][0]:.2f} [{Da['cost_k8'][1]:.2f}, {Da['cost_k8'][2]:.2f}]，名额放到 64 时 ×{Da['cost_64']:.2f}；"
                     f"深度 3 和深度 2 直接比没有差别（{Da['d32']}，{Da['d32n']} 对，费用 ×{Da['d32cost']:.2f}）。"),
            ("text", f"多查到的东西是不是在主agent汇总时丢了：从交回的消息看不是。取 {Da['lost_runs']} 次运行，把subagent发给主agent的全部消息用同一份事实清单判一遍，"
                     f"里面写对的条目只有 {Da['lost'][0]:.0f}%–{Da['lost'][1]:.0f}% 没进最终报告（每份 {Da['lost_n'][0]:.0f}–{Da['lost_n'][1]:.0f} 条），"
                     f"深度 2 和深度 1 一样（差 {Da['lost_d2']} 条）；题面要求“subagent 交回来的有来源的事实都写进最后的文件”以后，深度 2 的好处也没有变大"
                     f"（上表最后一批，{Da['dk']}，费用 ×{Da['dk_cost']:.2f}）。"
                     "这只看了发给主agent的消息：subagent直接写进文件的笔记、深度 2 时第 2 层交给第 1 层的内容都不在里面。"),
        ]

        def extend1(step: str, start: str, more: str) -> None:
            items = by[step]["items"]
            i = next(i for i, it in enumerate(items) if it[0] == "text" and it[1].startswith(start))
            items[i] = ("text", items[i][1] + more) + tuple(items[i][2:])
        extend1("A1-depth", "名额放到 64、或者让进程等subagent回来再退出，结论一样",
                f"把五批的 {Da['p2n']} 对放在一起（事后汇总，不算确认），深度 2 是 {Da['p2']}，约 {Da['facts2'][0]:.0f} 条事实；后做的三批单独是 {Da['later']}。"
                f"K=8 时费用是 {Da['cost_k8'][0]:.2f} 倍，每多写对一条约多花 1.8 元；深度 3 和深度 2 没有差别。")
        extend1("F2-depth-conclusion", "办公题按事实清单逐条判，深度对写对的事实条数没有显著影响",
                f"加上另外三批以后（两批是以前跑的、后来补判，一批新跑；见下面的五批并排）：每一批都是 {Da['range2'][0]:+.1f} 到 {Da['range2'][1]:+.1f}、单独不显著，"
                f"{Da['p2n']} 对合在一起 {Da['p2']}（事后汇总）。更准确的说法是：深度 2 有小幅提升（约 {Da['facts2'][0]:.0f} 条事实，区间 {Da['facts2'][1]:.0f}–{Da['facts2'][2]:.0f} 条），"
                f"K=8 时费用是 {Da['cost_k8'][0]:.2f} 倍；按这个代价，保持 1 的建议不变。")
    Dr = drb2()
    extra_d = []
    if Dr is not None and W is not None:
        by["A0-scope"]["items"][1] = ("text", by["A0-scope"]["items"][1][1].replace(
            "K 和深度没有在别的办公题上测。",
            f"又在 {Dr['tasks']} 道调研报告题（公开评测集 DeepResearch Bench II）上每题每组跑了 1 次：开subagent总分高 {Dr['h1']} 分，方向和办公题相同，幅度小。"
            "K 和深度没有在别的办公题上测。"), {"color": 7})
        assert "DeepResearch Bench II" in by["A0-scope"]["items"][1][1]
        by["C-task-table"]["note"] = by["C-task-table"]["note"] + (
            f"调研报告题（DeepResearch Bench II）：{Dr['tasks']} 道中文题 × 2 组各 1 次共 {Dr['runs']} 次，按题配对；日志里出现评测集名字的运行不计分（{Dr['runs']} 次里 {Dr['flagged']} 次）。")
        extra_d = [
            {"name": "R5-summary", "kind": "root", "before": 15, "where": "「结论」：开subagent那条的说明下面（接在表格收集题那行后面）",
             "items": [("text", f"调研报告题（公开评测集 DeepResearch Bench II 的中文题，{Dr['tasks']} 道）：开subagent后总分高 {Dr['h1']} 分（满分 100；信息召回一项 {Dr['recall']}），"
                                f"费用是 {Dr['cost']:.1f} 倍。")]},
            {"name": "R1-task-row", "kind": "table-row", "table": 25, "rows_before": 11, "where": "「题目」的表：末尾再加一行",
             "row": [f"调研报告题（公开评测集 DeepResearch Bench II 的中文题，{Dr['tasks']} 道）",
                     "按题面要求联网调研，写一份报告；题面列出了报告的结构和要给出的内容。每道题对应一篇已发表的综述或报告，评分项从那篇文章里来，运行时不许打开那篇文章",
                     f"逐条评分项判报告里有没有（信息召回、分析、呈现三类，每题 {Dr['items'][0]}–{Dr['items'][1]} 条），总分是满足的评分项占比；判分提示词用评测集原文，判分模型是 Opus 5.5"]},
            {"name": "R2-effect", "kind": "root", "before": 68, "where": "「允许开subagent对任务效果的影响」：表格收集题的下面、“结论”的上面",
             "items": [("h5", f"调研报告题（DeepResearch Bench II，{Dr['tasks']} 道）", True),
                       ("text", f"基准是不给委派工具；每题每组 1 次，按题配对。有 1 道题两组的运行都在搜索结果里看到了评测集题目文件的链接并认出了评测集（没有打开），"
                                f"按规则不计分，所以是 {Dr['pairs']} 对。"),
                       ("table", Dr["table"], [110, 60, 170, 70, 60, 60, 120, 110, 80]),
                       ("text", f"开subagent总分高 {Dr['h1']} 分（p = {Dr['p']:.3f}；{Dr['pairs']} 题里 {Dr['up']} 题升、{Dr['down']} 题降、{Dr['same']} 题平），"
                                f"其中信息召回 {Dr['recall']}，分析 {Dr['analysis']}（没测出），呈现 {Dr['present']}（两组都在 92 分以上）。费用是 {Dr['cost']:.1f} 倍，时长 {Dr['time']:.2f} 倍。"
                                f"幅度比办公题小得多：这个评测集的题面把报告的结构和要给的内容都列出来了，比办公题封闭。"
                                f"每题每组只跑 1 次，单道题上的分差波动很大（配对差的标准差 {Dr['sd']:.1f} 分）：出厂默认有 {Dr['none_n']} 道题一个subagent也没开，"
                                f"这几道题的分差也有 {Dr['none_range'][0]} 到 {Dr['none_range'][1]} 分。上面的区间已经把这种波动算在内。")]},
            {"name": "R3-effect-conclusion", "kind": "root", "before": 69, "where": "「允许开subagent对任务效果的影响」：结论的最后",
             "items": [("text", f"调研报告题（DeepResearch Bench II）上：开subagent总分高 {Dr['h1']} 分，信息召回一项高 {Dr['recall']}，费用 {Dr['cost']:.1f} 倍。"
                                "三类调研题（办公题、表格收集题、调研报告题）方向相同：开subagent查到的更多。幅度在办公题上最大，另外两类小得多；三者的判分方式不同，幅度不能直接相比。")]},
            {"name": "R4-appendix", "kind": "root", "before": 80, "where": "「附录·打分机制」：最后",
             "items": [("text", "调研报告题（DeepResearch Bench II）的判分：用评测集自己的判分提示词（逐字相同），每次判 50 条评分项，每条判“满足 / 没提到 / 依据了不许用的来源”，"
                                "总分是满足的占比。和评测集不同的是判分模型：这里用 Opus 5.5（评测集用的是另一家的模型），所以分数不能和论文里的数直接比，只在各组之间比。"
                                f"{Dr['sec_n']} 份判了两遍，逐条一致率 {Dr['sec_agree']:.1f}%，总分平均相差 {Dr['sec_abs']:.1f} 分，最多 {Dr['sec_max']:.1f} 分。"
                                f"{Dr['probed']} 道中文题里有 {len(Dr['refused'])} 道（都是健康类）判分模型一律拒绝作答，抽题时跳过了；抽到的 {Dr['tasks']} 道是按固定的随机顺序取的，每个主题最多 2 道。"
                                "每道题不许使用的来源写在题面里；容器里屏蔽了评测集所在的网站；运行日志里出现评测集名字、或者把不许用的来源的内容读了进来的运行不计分"
                                f"（{Dr['runs']} 次里 {Dr['flagged']} 次，两组各 {Dr['flagged'] // 2} 次；把它们算进去是 {Dr['all']}，结论不变）。")]},
        ]
    Kd = drb2kd()
    extra_k = []
    if Kd is not None and Dr is not None and X is not None and Da is not None:
        def phrase(x: dict, what: str) -> str:
            """One clause for a contrast, worded by the plan's reading rule."""
            if x["reading"] in ("高", "低"):
                return f"{what}，总分更{x['reading']}，差 {x['ci']} 分（两个对比一起校正后 p = {x['p_holm']:.3f}）"
            if x["reading"] == "没有实际差别":
                return f"{what}，总分没有实际差别（{x['ci']}，整个在 ±5 分以内）"
            return f"{what}，总分没测出差别（{x['ci']}）"
        k1, d2 = Kd["K1"], Kd["D2"]
        rt = Kd.get("retest")
        noise = (f"同一个配置（出厂默认）在第一段和这一段各跑了一次，同一道题两次的总分平均相差 {rt['abs']:.1f} 分（差的标准差 {rt['sd']:.1f} 分，{rt['tasks']} 题）：这就是每题只跑 1 次时单题分数的波动。"
                 if rt else "")
        both_flat = k1["reading"] == "没有实际差别" and d2["reading"] == "没有实际差别"
        limit = (f"要注意精度：开subagent的好处在这个评测集上本身只有 {Dr['h1'].split(' ')[0]} 分，±5 分的范围比它还宽，"
                 "所以这里说的“没有实际差别”分不出 K=1 或深度 2 相对出厂默认有没有四五分以内的差别；能确定的是费用差得很多。" if both_flat else "")
        short = "；这个精度分不出四五分以内的差别" if both_flat else ""
        extra_k = [
            {"name": "R6-depth-drb2", "kind": "root", "before": 47, "where": "「深度」：结论的最后（接在五批并排的后面）",
             "items": [("text", f"调研报告题（公开评测集 DeepResearch Bench II 的中文题，30 道）上也测了一次 K 和深度：每题每组 1 次，进程等subagent回来，按题配对，"
                                f"同一批里重跑出厂默认作参照。日志里出现评测集名字、或者把不许用的来源读了进来的运行不计分（{Kd['runs']} 次里 {Kd['flagged']} 次，其中 {Kd['flagged_d2']} 次在深度 2 那组），"
                                f"所以 K=1 的对比是 {Kd['pairs'][0]} 对，深度 2 的对比是 {Kd['pairs'][1]} 对；把这几次也算进去结论相同（K=1 {k1['all']}，深度 2 {d2['all']}）。"
                                f"表里各组的均值按三组都有效的 {Kd['common']} 题算；“差”那一列和下面的倍数用各自对比的全部配对，所以和均值相减不完全一样。"),
                       ("table", Kd["table"], [150, 60, 170, 90, 70, 120, 110, 80, 70]),
                       ("text", phrase(d2, "深度 2 对深度 1") + f"，信息召回 {d2['recall']}，费用 ×{d2['cost']:.2f}，时长 ×{d2['time']:.2f}。"
                                + phrase(k1, "K=1 对 K=8") + f"，信息召回 {k1['recall']}，费用 ×{k1['cost']:.2f}，时长 ×{k1['time']:.2f}。" + noise + limit)]},
            {"name": "R7-k-drb2", "kind": "root", "before": 57, "where": "「最大同时存活数量K」：结论的最后",
             "items": [("text", "调研报告题（DeepResearch Bench II，30 道）上的 K：" + phrase(k1, "K=1 对 K=8（深度 1）")
                                + f"，费用 ×{k1['cost']:.2f}；subagent 数是 {Kd['kids']['W-D1-K1']:.1f} 对 {Kd['kids']['W-D1-K8']:.1f} 个。"
                                + "开subagent的好处在这个评测集上本身只有 3.5 分左右，这个精度分不出 K=1 是不是保住了它；这里不能当成“K=1 一样好、还便宜一半”的依据。表在“深度”一节的最后。")]},
        ]
        extend1("A1-depth", "名额放到 64、或者让进程等subagent回来再退出，结论一样",
                "调研报告题（30 道公开题）上：" + phrase(d2, "深度 2 对深度 1") + f"，费用 ×{d2['cost']:.2f}{short}。")
        a2 = by["A2-k"]["items"]
        a2.append(("text", "调研报告题（公开评测集 DeepResearch Bench II，30 道）上：" + phrase(k1, "K=1 对 K=8") + f"，费用 ×{k1['cost']:.2f}{short}"
                           "（开subagent的好处在这个评测集上本身只有 3.5 分左右），不能据此说 K=1 一样好。"))
        by["C-task-table"]["note"] = by["C-task-table"]["note"] + f"调研报告题另跑了第二段：同样 30 题 × 3 组各 1 次共 {Kd['runs']} 次（K=1、出厂默认、深度 2）。"
        old_tail = "K 和深度没有在别的办公题上测。"
        scope = by["A0-scope"]["items"][1]
        assert scope[1].endswith(old_tail), scope[1][-40:]
        if both_flat:
            by["A0-scope"]["items"][1] = ("text", scope[1][:-len(old_tail)] + "K 和深度也在这 30 道题上各测了一次：K=1 对 K=8、深度 2 对深度 1 的总分差都落在 ±5 分以内，"
                                                                              "更细的差别这次分不出来；费用是出厂默认的一半和 1.5 倍。别的办公题上没有测。", {"color": 7})
    extra = [
        {"name": "A5-sheet-note", "kind": "root", "before": 17, "where": "「初步结论」：办公场景那张带底色的表的下面",
         "items": [("text", f"按事实清单逐条判（o1 96 条、o2 99 条事实，逐条对照官方页面）；数据是{new}实验，每组 40 份报告。"
                            f"D 1 → 3 没有新跑：正式实验的报告重评是 {R['d3']} 个百分点，没测出差别。写错的条数各组一样（每份 {F['wrong'][0]:.0f}–{F['wrong'][1]:.0f} 条）。"),
                   ("table", F["sheet7"], [190, 70, 150, 90, 120, 70, 120])]},
        {"name": "F0-depth-office-figure", "kind": "root", "before": 43, "where": "「深度」：办公题两张图的下面",
         "items": [("image", "office-facts-by-d-k48.png", "固定k，深度对写对的事实条目占比的影响（按事实清单重评；虚线是不给委派工具）"),
                   ("text", "这三张图只画 K=4、8：K=1、2 时名额被第 1 层占满，第 2 层开不出来（D2-K1、D2-K2 的 40 次运行里是 0 次），这几组实际上和深度 1 一样。")]},
        {"name": "G0-k-office-figure", "kind": "root", "before": 52, "where": "「最大同时存活数量K」：办公题两张图的下面",
         "items": [("image", "office-facts-by-k.png", "固定深度，k对写对的事实条目占比的影响（按事实清单重评；虚线是不给委派工具）"),
                   ("image", "office-facts-confirm.png", f"{new}：k 和深度对写对的事实条目占比的影响（每组 40 份；虚线是不给委派工具）")]},
        {"name": "H0-effect-office", "kind": "root", "before": 63, "where": "「允许开subagent对任务效果的影响」：办公题“多做了什么”那张表的下面",
         "items": [("text", f"写对的条目占比相差 {R['h1']} 个百分点，显著；{new}：{F['h1']} 个百分点（{F['n0']:.1f} → {F['n8']:.1f} 条）。"
                            "表里的事实条数是对正式实验的报告按事实清单重评得到的。")]},
        {"name": "J-appendix-judging", "kind": "root", "before": 80, "where": "「附录·打分机制」：那张图的下面",
         "items": [("text", "按事实清单重评：o1 96 条、o2 99 条事实，每条都对照官方页面写明标准值和判定规则；Opus 5.5 逐条判每份报告对这一条是写对、写错、"
                            f"只写了“待核验”还是没写，看不到组别。先判 24 份样本报告和人工逐条归类对照，一致率 {R['agree'][0]:.1f}% 和 {R['agree'][1]:.1f}%；"
                            f"另取 {R['second_n']} 份判了两遍，逐条一致率 {R['second']:.1f}%。这是看了正式结果以后加的分析。"
                            f"{new}实验用同一份清单、同一种判法（判了 {F['judged']} 份报告，另 {F['second_n']} 份判两遍，一致率 {F['second']:.1f}%），对比是开跑前写定的。")]},
    ]
    order = ["A0-scope", "A1-depth", "A2-k", "A3-effect", "A4-other-problems", "A5-sheet-note", "B-variables", "C-task-table", "D1-behavior-figures",
             "D2-behavior-bullets", "E-scores", "F0-depth-office-figure", "F1-depth-figures", "F2-depth-conclusion", "G0-k-office-figure", "G1-k-figures",
             "G2-k-conclusion", "H0-effect-office", "H1-effect", "H2-effect-conclusion", "I-problems", "J-appendix-judging"]
    for e in extra_ws:                       # each goes right after the step whose section it continues
        after = {"W5-summary": "A3-effect", "W1-task-row": "C-task-table", "W2-behavior": "D2-behavior-bullets", "W3-effect": "H1-effect",
                 "W4-effect-conclusion": "H2-effect-conclusion", "W8-problems": "I-problems", "W7-appendix": "J-appendix-judging"}[e["name"]]
        order.insert(order.index(after) + 1, e["name"])
    for e in extra_m:
        after = {"M1-effect-search": "H0-effect-office", "M2-depth-quota": "F2-depth-conclusion", "M3-k-64": "G2-k-conclusion",
                 "M4-appendix": "W7-appendix" if "W7-appendix" in order else "J-appendix-judging"}[e["name"]]
        order.insert(order.index(after) + 1, e["name"])
    for e in extra_d:
        after = {"R5-summary": "W5-summary", "R1-task-row": "W1-task-row", "R2-effect": "W3-effect", "R3-effect-conclusion": "W4-effect-conclusion",
                 "R4-appendix": "M4-appendix" if "M4-appendix" in order else "W7-appendix"}[e["name"]]
        order.insert(order.index(after) + 1, e["name"])
    for e in extra_k:
        after = {"R6-depth-drb2": "M2-depth-quota", "R7-k-drb2": "M3-k-64"}[e["name"]]
        order.insert(order.index(after) + 1, e["name"])
    extra = extra + extra_ws + extra_m + extra_d + extra_k
    by.update({e["name"]: e for e in extra})
    assert sorted(order) == sorted(by), sorted(set(order) ^ set(by))
    return [by[n] for n in order]


BEFORE_STRIKE = EXP / "results/wiki/blocks-before-strike.json"      # the page as read right before the first correction
TEXT_KEYS = ("text", "bullet", "ordered", "heading1", "heading2", "heading3", "heading4", "heading5", "heading6")


def corrections() -> list:
    """Her sentences that the fact-list results (re-grade + confirmation experiment) and the code-building tasks
    changed. Each entry: the block, and (phrase to strike, wording to put after it)."""
    R = regrade()
    F = R["conf"]
    gain, k1 = f"{F['n8'] - F['n0']:.0f}–{R['gain']:.0f}", f"{F['k1n']:.0f}"
    assert (gain, k1) == ("15–16", "7"), (gain, k1)
    return [
        {"name": "S1-k-summary", "block": "FATtdvTFCoKIsxx69KQchokNnef", "where": "「初步结论」K 那条的说明",
         "edits": [("K 在 4 以上没有区别。", f"**办公题上 K 在 4 以上没有区别，K=1 显著变差**（每份报告少写对约 {k1} 条事实；读代码题上 K=1 也低 4.0 分）；"
                                             "代码构建题上模型会把名额用满，K=4 和 K=8 不一样（见下面两段）。")]},
        {"name": "S2-effect-summary", "block": "TOsQdL53aom3skxbJH9c91shn2g", "where": "「初步结论」开subagent那条的说明，第一行",
         "edits": [("得分没有显著提升", f"评分表总分没有显著提升，但按事实清单逐条判每份报告多写对约 {gain} 条事实（显著）")]},
        {"name": "S3-office-sheet-lead", "block": "J8NTdybpXoMLGaxfUXdcNCSbnbh", "where": "「初步结论」其他问题的最后一条（带底色表格上面那句）",
         "edits": [("允许递归和开subagent没有显著差别：", f"按评分表总分，允许递归和开subagent都没有显著差别（下面第一张表）；按事实清单逐条判，开subagent每份报告多写对约 {gain} 条事实、"
                                                          f"K=1 少写对约 {k1} 条（都显著），允许递归没有显著差别（第二张表）：")]},
        {"name": "S4-k-office-nofigure", "block": "EKWBdYy33oZC8gxpmybcFKtgnhd", "where": "「最大同时存活数量K」办公题标题下面那句",
         "edits": [("分数无显著差别不单独作图", "评分表总分无显著差别，不单独作图；按事实清单逐条判 K=1 写对的更少，见下面第三、四张图")]},
        {"name": "S5-k-conclusion", "block": "ARWFdFRJwoBAOVxKIYEc0a5JnFb", "where": "「最大同时存活数量K」的结论",
         "edits": [("当前深度 1 下 K 在 4 以上没有区别", "办公题上，深度 1 时 K 在 4 以上没有区别（读代码题上没测出差别；代码构建题不一样，见下面第二段）"),
                   ("办公题没测到显著得分损失", f"办公题按事实清单逐条判每份报告少写对约 {k1} 条事实（显著）")]},
        {"name": "S6-effect-table-verdict", "block": "MFnQdsCmQowmVpx4DFvcU0sGn6d", "where": "「允许开subagent对任务效果的影响」办公题那张表的“判断”一格",
         "edits": [("效果略微降低，不显著", f"评分表总分略微降低，不显著；按事实清单逐条判少写对约 {gain} 条事实，显著")]},
        {"name": "S7-effect-conclusion", "block": "PFljdyq3VoG9CgxRWRecbmXtnUd", "where": "「允许开subagent对任务效果的影响」的结论",
         "edits": [("得分差测不出", f"评分表总分的差测不出，按事实清单逐条判每份报告多写对约 {gain} 条事实（显著）")]},
        {"name": "S8-margin", "block": "Xjo6dchLIotF4jxBo1Lc2XEanDb", "where": "「题目」表右边说明栏的“得分”一条（方案和图里用的都是 ±5 分）",
         "edits": [("±2 分", "±5 分")]},
    ] + depth_corrections()


def depth_corrections() -> list:
    """Her three sentences on depth, corrected after the five-batch summary. She agreed on 2026-10-05 ("可以改") to
    change the sentence "递归在日常任务中暂时没有看到显著提升" to "有小幅提升（约 4 条事实），费用翻倍，不划算"; the two
    sentences below it state the same thing about the score and get the same correction. Empty before the summary exists."""
    Da = depthall()
    if Da is None:
        return []
    assert round(Da["facts2"][0]) == 4 and 1.8 <= Da["cost_k8"][0] <= 2.0, Da
    return [
        {"name": "S9-depth-headline", "block": "AO2yddrjuokzWhxtKEgc0QcAnSd", "where": "「结论」深度那一条",
         "edits": [("递归在日常任务中暂时没有看到显著提升", "办公题上放开到深度 2 有小幅提升（多写对约 4 条事实），费用近两倍，不划算；代码题上没有提升")]},
        {"name": "S10-depth-summary", "block": "QNemdzVN3oN9DixAX2Tcm8WTnoe", "where": "「结论」深度那一条下面的说明",
         "edits": [("得分无显著提高", "评分表总分无显著提高；办公题按事实清单逐条判，深度 2 多写对约 4 条事实")]},
        {"name": "S11-depth-conclusion", "block": "TmbldRQHpoDi3exMdq7ciBymnFf", "where": "「深度」一节的结论",
         "edits": [("得分没有显著差别", f"评分表总分没有显著差别；办公题按事实清单逐条判，深度 2 多写对约 4 条事实（五批合起来 {Da['p2']} 个百分点），深度 3 不比深度 2 多")]},
    ]


def correct(a) -> None:
    import datetime
    import wiki_edit as we
    dby = {b["block_id"]: b for b in json.loads(BEFORE_STRIKE.read_text(encoding="utf-8"))}
    rec = json.loads(STRIKES.read_text(encoding="utf-8")) if STRIKES.exists() else {}
    only = set(filter(None, a.only.split(",")))
    d = we.Doc(DOC)
    for c in corrections():
        if c["name"] in rec or (only and c["name"] not in only):
            continue
        b = dby[c["block"]]
        expected = we.plain(b[next(k for k in TEXT_KEYS if k in b)]["elements"])
        r = d.correct(c["block"], expected, c["edits"], dry_run=a.dry_run)
        shown = "".join(("~~" + e["text_run"]["content"] + "~~") if e["text_run"]["text_element_style"].get("strikethrough") else e["text_run"]["content"]
                        for e in r["after"])
        print(("would correct " if a.dry_run else "corrected ") + c["name"], "—", c["where"], "\n   ", shown.replace("\n", "\n    "))
        if a.dry_run:
            continue
        rec[c["name"]] = {"block": c["block"], "where": c["where"], "time": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                          "before": r["before"], "after": r["after"]}
        STRIKES.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")


def verify(a) -> None:
    """Read the page back and compare with the page as the user wrote it (the 08:10Z dump): every block of hers must
    still be there, in the same order under the same parent, with the same text — except the blocks listed in
    strikes.json, where the text must be her original words (now partly struck) plus the recorded additions."""
    import wiki_edit as we
    dump = json.loads(DUMP.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    rec = json.loads(STRIKES.read_text(encoding="utf-8")) if STRIKES.exists() else {}
    plain_markup = lambda m: re.sub(r"\*\*(.+?)\*\*", r"\1", m)  # noqa: E731
    fixes = {c["block"]: c["edits"] for c in corrections() if c["name"] in rec}
    mine = set(state["created"])
    d = we.Doc(DOC)
    hers = {b["block_id"] for b in dump}
    bad, same, corrected, props = [], 0, 0, []
    strip = lambda b: {k: v for k, v in b.items() if k not in ("children", "parent_id")}  # noqa: E731
    for b in dump:
        bid = b["block_id"]
        now = d.by.get(bid)
        if now is None:
            bad.append(f"missing {bid}")
            continue
        if [c for c in (now.get("children") or []) if c in hers] != (b.get("children") or []):
            bad.append(f"children order changed under {bid}")
        if bid in fixes:
            key = next(k for k in TEXT_KEYS if k in b)
            want = we.plain(b[key]["elements"])
            for phrase, new in fixes[bid]:
                want = want.replace(phrase, phrase + plain_markup(new))
            els = now[key]["elements"]
            crossed = [e["text_run"]["content"] for e in els if e["text_run"]["text_element_style"].get("strikethrough")]
            if we.plain(els) != want or "".join(crossed) != "".join(ph for ph, _ in fixes[bid]):
                bad.append(f"corrected block {bid} is not her text plus the recorded correction")
            corrected += 1
        elif strip(now) == strip(b):
            same += 1
        else:
            keys = sorted(k for k in set(strip(now)) | set(strip(b)) if strip(now).get(k) != strip(b).get(k))
            texts_same = all(now.get(k, {}).get("elements") == b.get(k, {}).get("elements") for k in TEXT_KEYS if k in b)
            (props if texts_same else bad).append(f"{bid} differs in {keys}")

    def owner(x: str) -> str:
        """Who a block that is not in her dump belongs to: one of this script's blocks (or something inside one), or a
        row this script appended to her 题目 table."""
        seen = x
        while seen and seen in d.by:
            if seen in mine:
                return "mine"
            par = d.by[seen].get("parent_id")
            if par in hers and d.by[par]["block_type"] == 31:
                return "row added to her table"
            seen = par
        return "other"

    new_blocks = [x for x in d.by if x not in hers]
    kinds = {}
    for x in new_blocks:
        kinds.setdefault(owner(x), []).append(x)
    print(f"her blocks: {len(dump)}; unchanged {same}; corrected by strike-through {corrected}; text same but properties differ {len(props)}: {props}")
    print("blocks not in her dump:", {k: len(v) for k, v in kinds.items()})
    for x in kinds.get("other", [])[:20]:
        print("   other new block:", x, d.by[x]["block_type"], we.fp.block_text(d.by[x])[:60])
    print("PROBLEMS:" if bad else "no problems found", *bad, sep="\n  " if bad else "")
    if a.out:
        a.out.write_text(json.dumps(d.blocks, ensure_ascii=False, indent=1), encoding="utf-8")


def preview(out: Path) -> None:
    L = ["# 「Subagent问题」待加入的内容（预览）", "",
         "两道代码构建题（24 道练习不限时、48 模块的 Python 包）的结果，和办公题按事实清单重评的结果，按你那页现有的小节分开放。"
         "下面每一块上面那行写的是它要放的位置；你原来的文字和图都不动。", ""]
    n_img = 0
    steps = all_steps()
    for i, s in enumerate(steps, 1):
        L += [f"## {i}. {s['where']}", ""]
        if s["kind"] == "table-row":
            L += ["表尾新增一行：", "", "| " + " | ".join(s["row"]) + " |", ""]
            continue
        if s["kind"] == "task-table":
            L += ["表尾新增两行：", "", "| 题 | 内容 | 判分 |", "|---|---|---|"] + ["| " + " | ".join(r) + " |" for r in s["rows"]]
            L += ["", "说明栏新增一条：", "", "- " + s["note"], ""]
            continue
        for it in s["items"]:
            k = it[0]
            if k == "text":
                L += [it[1].replace("\n", "\n\n"), ""]
            elif k == "bullet":
                L += ["- " + it[1], ""]
            elif k == "ordered":
                L += ["1. " + it[1], ""]
            elif k == "h5":
                L += ["##### " + it[1], ""]
            elif k == "image":
                n_img += 1
                L += [f"![{it[1]}]({FIG}/{it[1]})", "", f"图注 {n_img:02d}｜{it[2]}", ""]
            elif k == "table":
                rows = it[1]
                L += ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])] + ["| " + " | ".join(r) + " |" for r in rows[1:]] + [""]
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {out}: {len(steps)} places, {n_img} figures")


def apply(a) -> None:
    import wiki_edit as we
    mk = {"text": lambda it: we.text(it[1], **(it[2] if len(it) > 2 else {})), "bullet": lambda it: we.bullet(it[1]),
          "ordered": lambda it: we.ordered(it[1]), "h5": lambda it: we.heading5(it[1], bold=it[2])}
    dump = json.loads(DUMP.read_text(encoding="utf-8"))
    dby = {b["block_id"]: b for b in dump}
    top = next(b for b in dump if b["block_type"] == 1)["children"]
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"steps": {}, "created": []}
    d = we.Doc(DOC)
    root = d.root["block_id"]
    created = set(state["created"])
    CLEAN = EXP / "results/wiki/cleanup.json"
    removed = {o["block"] for o in json.loads(CLEAN.read_text(encoding="utf-8"))["ops"] if o["kind"] == "delete"} if CLEAN.exists() else set()
    if [c for c in d.children(root) if c not in created] != [c for c in top if c not in removed]:
        sys.exit("the page's top-level blocks changed since the dump (not counting this script's own blocks and what the clean-up removed); nothing written")
    only = set(filter(None, a.only.split(",")))

    def before(i: int) -> tuple:
        d.reload()
        ch = d.children(root)
        idx = ch.index(top[i])
        return idx, ch[idx - 1] if idx else None, top[i]

    def do_root(s: dict) -> list:
        ids = []
        for it in s["items"]:
            idx, prev, nxt = before(s["before"])
            d.expect(root, idx, prev, nxt)
            if it[0] == "image":
                ids.append(d.insert_image(root, idx, EXP / FIG / it[1], it[2]))
            elif it[0] == "table":
                ids.append(d.insert_table(root, idx, it[1], it[2]))
            else:
                ids += d.insert(root, idx, [mk[it[0]](it)])
        return ids

    def do_nested(s: dict) -> list:
        parent = top[s["parent"]]
        old = dby[parent]["children"]
        d.reload()
        if [k for k in d.children(parent) if k not in created] != old:
            sys.exit("the list under the anchor changed; nothing written")
        cur = d.children(parent)
        idx = cur.index(old[-1])
        d.expect(parent, idx, cur[idx - 1], old[-1])
        return d.insert(parent, idx, [mk[it[0]](it) for it in s["items"]])

    def do_table(s: dict) -> list:
        table = top[s["table"]]
        t = dby[table]
        assert t["table"]["property"]["row_size"] == 8 and t["table"]["property"]["merge_info"][3]["row_span"] == 8
        d.reload()
        if d.by[table]["table"]["property"]["row_size"] == 8:
            d.add_table_rows(table, s["rows"])
        d.reload()
        p = d.by[table]["table"]["property"]
        assert p["row_size"] == 10, p["row_size"]
        if p["merge_info"][3]["row_span"] != 10:
            we.fp.call("PATCH", f"/docx/v1/documents/{DOC}/blocks/{table}?document_revision_id=-1", d.token,
                       body={"merge_table_cells": {"row_start_index": 0, "row_end_index": 10, "column_start_index": 3, "column_end_index": 4}})
        d.reload()
        cell = d.by[table]["children"][3]
        kids = d.children(cell)
        old = dby[t["children"][3]]["children"]
        assert kids[:len(old)] == old, "the notes cell changed"
        last_bullet = max(i for i, k in enumerate(kids) if d.by[k]["block_type"] == 12)
        return d.insert(cell, last_bullet + 1, [we.bullet(s["note"])])

    def do_table_row(s: dict) -> list:
        """One more row at the end of her 题目 table (after the two rows of the task-table step); the merged notes cell
        on the right is extended over it. Returns no ids: the row's cells are not top-level blocks."""
        table = top[s["table"]]
        d.reload()
        p = d.by[table]["table"]["property"]
        nc = p["column_size"]
        last = [we.fp.block_text(d.by[d.children(c)[0]]) for c in d.by[table]["children"][-nc:]]
        n0 = s.get("rows_before", 10)
        if last[0] != s["row"][0]:
            assert p["row_size"] == n0, p["row_size"]
            d.add_table_rows(table, [s["row"]])
            d.reload()
            p = d.by[table]["table"]["property"]
        assert p["row_size"] >= n0 + 1, p["row_size"]
        if p["merge_info"][3]["row_span"] < n0 + 1:
            we.fp.call("PATCH", f"/docx/v1/documents/{DOC}/blocks/{table}?document_revision_id=-1", d.token,
                       body={"merge_table_cells": {"row_start_index": 0, "row_end_index": n0 + 1, "column_start_index": 3, "column_end_index": 4}})
        return []

    run = {"root": do_root, "nested": do_nested, "task-table": do_table, "table-row": do_table_row}
    for s in reversed(all_steps()):                 # bottom of the page first
        if s["name"] in state["steps"] or (only and s["name"] not in only):
            continue
        if a.dry_run:
            print("would do", s["name"], "—", s["where"])
            continue
        ids = run[s["kind"]](s)
        state["steps"][s["name"]] = ids
        state["created"] += ids
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        print("done", s["name"], len(ids), "blocks")
    print("steps recorded:", sorted(state["steps"]))


def update(a) -> None:
    """Bring the blocks this script inserted earlier up to date with the current content of all_steps(): the text of
    a text / bullet / numbered block is replaced when it differs; nothing else on the page is touched. Items that a
    step has gained since it was applied are inserted right after the step's last block."""
    import wiki_edit as we
    state = json.loads(STATE.read_text(encoding="utf-8"))
    steps = {s_["name"]: s_ for s_ in all_steps()}
    d = we.Doc(DOC)
    mine = set(state["created"])
    plain = lambda m: re.sub(r"\*\*(.+?)\*\*", r"\1", m)  # noqa: E731
    mk = {"text": lambda it: we.text(it[1], **(it[2] if len(it) > 2 else {})), "bullet": lambda it: we.bullet(it[1]), "ordered": lambda it: we.ordered(it[1])}
    only = set(filter(None, a.only.split(",")))
    for name, ids in state["steps"].items():
        if only and name not in only:
            continue
        s_ = steps.get(name)
        if s_ is not None and s_["kind"] == "task-table":
            bid = ids[0]
            if we.fp.block_text(d.by[bid]) != s_["note"]:
                if a.dry_run:
                    print("would update", name, bid, "->", s_["note"][:60])
                else:
                    we.fp.call("PATCH", f"/docx/v1/documents/{DOC}/blocks/{bid}?document_revision_id=-1", d.token,
                               body={"update_text_elements": {"elements": we.runs(s_["note"])}})
                    print("updated", name, bid)
            continue
        if s_ is None or s_["kind"] != "root":
            continue
        items = s_["items"]
        for bid, it in zip(ids, items):
            assert bid in mine and bid in d.by, (name, bid)
            if it[0] == "table":  # one of this script's own tables: cells whose text differs are rewritten in place
                tb = d.by[bid]
                assert tb["block_type"] == 31, (name, bid, tb["block_type"])
                want = [c for row in it[1] for c in row]
                cells = tb["children"]
                assert len(cells) == len(want), (name, bid, len(cells), len(want))
                for cid, w in zip(cells, want):
                    kids = d.children(cid)
                    if len(kids) != 1 or d.by[kids[0]]["block_type"] != 2:
                        sys.exit(f"a cell of table {bid} is not a single paragraph; nothing written to it")
                    if we.fp.block_text(d.by[kids[0]]) == plain(w):
                        continue
                    if a.dry_run:
                        print("would update cell of", name, bid, ":", we.fp.block_text(d.by[kids[0]]), "->", plain(w))
                        continue
                    we.fp.call("PATCH", f"/docx/v1/documents/{DOC}/blocks/{kids[0]}?document_revision_id=-1", d.token,
                               body={"update_text_elements": {"elements": we.runs(w)}})
                    print("updated cell of", name, bid, "->", plain(w))
                continue
            if it[0] not in mk:
                continue
            kind = {"text": 2, "bullet": 12, "ordered": 13}[it[0]]
            assert d.by[bid]["block_type"] == kind, (name, bid, d.by[bid]["block_type"])
            if we.fp.block_text(d.by[bid]) == plain(it[1]):
                continue
            if a.dry_run:
                print("would update", name, bid, "->", plain(it[1])[:60])
                continue
            color = (it[2] if len(it) > 2 else {}).get("color")
            we.fp.call("PATCH", f"/docx/v1/documents/{DOC}/blocks/{bid}?document_revision_id=-1", d.token,
                       body={"update_text_elements": {"elements": we.runs(it[1], color)}})
            print("updated", name, bid)
        for it in items[len(ids):]:
            d.reload()
            root = d.root["block_id"]
            ch = d.children(root)
            last = state["steps"][name][-1]
            idx = ch.index(last) + 1
            if a.dry_run:
                print("would add to", name, "->", it[0], str(it[1])[:50])
                continue
            d.expect(root, idx, last, ch[idx] if idx < len(ch) else None)
            if it[0] == "image":
                new = [d.insert_image(root, idx, EXP / FIG / it[1], it[2])]
            elif it[0] == "table":
                new = [d.insert_table(root, idx, it[1], it[2])]
            else:
                new = d.insert(root, idx, [mk[it[0]](it)])
            state["steps"][name] += new
            state["created"] += new
            STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
            print("added to", name, new)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update", action="store_true", help="update the blocks inserted earlier instead of inserting the steps")
    ap.add_argument("--correct", action="store_true", help="strike-through corrections of the user's own sentences (CORRECTIONS)")
    ap.add_argument("--verify", action="store_true", help="read the page back and compare it with the page as the user wrote it")
    ap.add_argument("--out", type=Path, help="with --verify: save the page's blocks to this file")
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    for s in all_steps():
        for it in s.get("items", []):
            if it[0] == "image":
                assert (EXP / FIG / it[1]).exists(), it[1]
    if a.preview:
        preview(a.preview)
    elif a.correct:
        correct(a)
    elif a.verify:
        verify(a)
    elif a.update:
        update(a)
    else:
        apply(a)


if __name__ == "__main__":
    main()
