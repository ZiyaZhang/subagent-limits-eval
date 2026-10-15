#!/usr/bin/env python3
"""Build the report on the two subagent limits (report-clean-2026-10-06.md; the body of the wiki page「Subagent问题」).
Every number is formatted from the analysis files through clean_data.py; the sentences that state a verdict are
guarded by asserts, so a changed result stops the build instead of leaving a wrong sentence.

Layout (2026-10-07): conclusions (three lines, the reasoning in three steps, the overview figure and table, the
recommendations); how the experiment was run; results by QUESTION, one small table across the tasks per question
(what the model opens by itself, is delegating worth it, K, depth, where money and time go, can the measurement
be trusted); problems of DSH; scope; appendix with the tables per task and every sentence about how something was
computed.

Rules of the text (the owner's): final results only; a number appears once (what a table holds is not repeated in
the text; the text gives the judgement and one or two key numbers); how something was computed goes to the appendix
and the body keeps only a label; one name per condition (不开 subagent, 默认, 并行提示, 不复核提示); every setting is
compared with the default it was run with; agent / 主 agent / subagent, never 代理.

Usage: build_clean.py [--out report-clean-2026-10-06.md] [--wiki-body wiki-body-2026-10-06.md]
"""
from __future__ import annotations

import argparse
import collections
import json
import math
from decimal import ROUND_HALF_UP, Decimal
import re
import statistics as st
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean_data as cd  # noqa: E402
import clean_extra as ce  # noqa: E402  (numbers added after the review of 2026-10-07)
import wiki_apply as wa  # noqa: E402  (loaders only: context use, agreement of the judge with the manual labels)

EXP = cd.EXP
NEW = "results/analysis-clean"
SEC = {"cost": "一", "open": "二", "worth": "三", "k": "四", "depth": "五", "spend": "六", "deliver": "七", "trust": "八"}  # the result sections
ENCOURAGE = "独立的子任务尽量交给 subagent 并行做。"
NOREVIEW = "文件都写完以后，不要再另开子代理去复核、验证或补测试；需要检查就自己检查。"
SEARCHMORE = "写报告之前，请至少做 100 次网页搜索，并打开至少 100 个网页核对内容。"
KEEPALL = (EXP / "tasks/keepall-sentence.txt").read_text(encoding="utf-8").strip()
RELATED = "和别人的结果对照"
POINTER = "打分机制、各题的题面原文、两份事实清单和评分标准原文见[《Subagent问题》](https://trtgsjkv6r.feishu.cn/wiki/IctcwDfDNiNspFkNvvwcCcqJn8c)一页的附录。"


# ------------------------------------------------------------------------------------------------- formatting
def rnd(v: float, nd: int = 1) -> str:
    """v with nd decimals, exact halves away from zero (3.55 -> 3.6; the binary default gives 3.5 here and 3.7 for 3.65)."""
    return str(Decimal(repr(round(float(v), 9))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP))


def sg(v: float, nd: int = 1) -> str:
    t = rnd(v, nd)
    return (t if t.startswith("-") else "+" + t).replace("-", "−")


def ci(c: dict, nd: int = 1) -> str:
    return f"{sg(c['est'], nd)} [{sg(c['lo'], nd)}, {sg(c['hi'], nd)}]"


def x(c, nd: int = 2) -> str:
    return f"×{rnd(c['est'] if isinstance(c, dict) else c, nd)}"


def xci(c: dict, nd: int = 2) -> str:
    b = lambda v: rnd(v, nd + 1) if v != 1 and rnd(v, nd) == rnd(1, nd) else rnd(v, nd)  # noqa: E731  (1.004 is not shown as 1.00)
    return f"×{rnd(c['est'], nd)} [{b(c['lo'])}, {b(c['hi'])}]"


def f(v, nd: int = 1) -> str:
    return "—" if v is None else rnd(v, nd)


def pct(v: float, nd: int = 0) -> str:
    return f"{rnd(100 * v, nd)}%"


def table(rows: list) -> list:
    head, *body = rows
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in body] + [""]


def verdict(c: dict, margin: float, corrected: bool = False, better: str = "显著变好", worse: str = "显著变差") -> str:
    """The words of the report. corrected: the contrast belongs to a family that was corrected together."""
    out = c["lo"] > 0 or c["hi"] < 0
    holm = c.get("holm", c.get("p_holm"))
    if out:
        if corrected and not (holm is not None and holm < 0.05):
            return "校正后不显著"
        return better if c["lo"] > 0 else worse
    if abs(c["lo"]) <= margin and abs(c["hi"]) <= margin:
        return "没有差别"
    return "没测出差别"


def split_caption(cap: str, limit: int) -> tuple:
    """A caption longer than `limit` keeps its first sentence (two when the first is very short); the rest becomes a
    note under the figure or the table. A full stop inside brackets does not end a sentence."""
    if len(cap) <= limit:
        return cap, ""
    depth, cuts = 0, []
    for i, ch in enumerate(cap):
        depth += ch == "（"
        depth -= ch == "）"
        if ch == "。" and depth == 0:
            cuts.append(i + 1)
    cuts = [c for c in cuts if c < len(cap)]
    if not cuts:
        return cap, ""
    cut = cuts[0] if cuts[0] >= 25 or len(cuts) == 1 else cuts[1]
    return cap[:cut], cap[cut:]


class Doc:
    """The report, collected section by section. A second- or third-level heading starts a section named by the
    heading line (while `auto` is on); sec(name) starts one by hand. Figures and tables get a key and stand in a
    section as one placeholder line; the text refers to them as {fig:key} / {tab:key}. text(order) puts sections
    together and numbers figures and tables in the order of the finished text, so a section can move, be left out,
    or give a figure or a table to another section (place)."""

    def __init__(self):
        self.sections, self.order, self.blocks, self.held, self.auto = {}, [], {}, [], True
        self.sec("front")

    def sec(self, name: str):
        assert not self.held, "a held figure was never released"
        assert name not in self.sections, f"section {name!r} twice"
        self.sections[name] = self.cur = []
        self.order.append(name)

    def at(self, name: str):
        """Go on writing at the end of a section that exists."""
        assert not self.held
        self.cur = self.sections[name]

    def add(self, *lines):
        for ln in lines:
            if self.auto and ln.startswith(("## ", "### ")):
                self.sec(ln)
            self.cur.append(ln)

    def p(self, text: str):
        self.cur += [text, ""]

    def figure(self, key: str, path: str, caption: str, hold: bool = False):
        """hold: put the figure into the text at the next release() (after the sentences under a table)."""
        assert (EXP / path).exists(), path
        assert f"fig:{key}" not in self.blocks, key
        self.blocks[f"fig:{key}"] = ("fig", path, caption)
        (self.held if hold else self.cur).append(f"\x00fig:{key}")

    def release(self):
        self.cur += self.held
        self.held = []

    def tbl(self, key: str, caption: str, rows: list):
        assert f"tab:{key}" not in self.blocks, key
        self.blocks[f"tab:{key}"] = ("tab", rows, caption)
        self.cur.append(f"\x00tab:{key}")

    def place(self, key: str, caption: str | None = None):
        """Move a figure or a table that an earlier section made to this place (key: "fig:name" or "tab:name"), with a new caption if given."""
        mark = f"\x00{key}"
        homes = [lines for lines in self.sections.values() if mark in lines]
        assert len(homes) == 1, (key, len(homes))
        homes[0].remove(mark)
        kind, payload, cap = self.blocks[key]
        self.blocks[key] = (kind, payload, caption or cap)
        self.cur.append(mark)

    def text(self, order: list | None = None, change: dict | None = None, unnumbered: dict | None = None) -> str:
        """order: section names (default: every section in the order of writing). change: {section: function(lines) -> lines}.
        unnumbered: {key: words that refer to it}: these figures and tables get a caption without a number."""
        unnumbered = unnumbered or {}
        assert not self.held, "a held figure was never released"
        lines = []
        for name in (order or self.order):
            sec = self.sections[name]
            lines += (change or {}).get(name, lambda q: q)(list(sec))
        n, num, out = {"fig": 0, "tab": 0}, {}, []
        for ln in lines:
            if not ln.startswith("\x00"):
                out.append(ln)
                continue
            key = ln[1:]
            kind, payload, cap = self.blocks[key]
            if key in unnumbered:
                num[key] = None
                out += ([f"![]({payload})", "", f"图：{cap}", ""] if kind == "fig" else [f"表：{cap}", ""] + table(payload))
                continue
            n[kind] += 1
            num[key] = n[kind]
            cap, note = split_caption(cap, 110 if kind == "fig" else 130)
            if kind == "fig":
                out += [f"![]({payload})", "", f"图 {n[kind]} {cap}", ""] + ([f"说明（图 {n[kind]}）：{note}", ""] if note else [])
            else:
                out += [f"表 {n[kind]} {cap}", ""] + table(payload) + ([f"说明（表 {n[kind]}）：{note}", ""] if note else [])
        text = "\n".join(out) + "\n"
        missing = sorted({m.group(0) for m in re.finditer(r"\{((?:fig|tab):[a-z0-9-]+)\}", text) if m.group(1) not in num})
        assert not missing, f"references to figures or tables that are not in the text: {missing}"
        return re.sub(r"\{((fig|tab):[a-z0-9-]+)\}", lambda m: unnumbered[m.group(1)] if m.group(1) in unnumbered else ("图 " if m.group(2) == "fig" else "表 ") + str(num[m.group(1)]), text)


# ---------------------------------------------------------------------------------------------------- content
def rb_seconds() -> float:
    """Time ratio default / no subagents in the first office batch."""
    c_ = cd.J("results/analysis-complete/stats-office.json")["metrics"]["seconds"]["comparisons"]["H1"]
    return math.exp(c_["est"])


def rc(c: dict, nd: int = 2, corrected: bool = False) -> str:
    """A ratio for a table cell, with the word that the interval allows: a ratio whose interval holds 1 is 没测出差别."""
    if c["lo"] <= 1 <= c["hi"]:
        return f"{x(c, nd)}，没测出差别"
    holm = c.get("holm", c.get("p_holm"))
    if corrected and not (holm is not None and holm < 0.05):
        return f"{x(c, nd)}，校正后不显著"
    return x(c, nd)


def eff(c: dict, margin: float, unit: str, corrected: bool = False) -> str:
    """A difference for a table cell: the number when it is significant, otherwise the word with the estimate in brackets."""
    v = verdict(c, margin, corrected)
    if v in ("显著变好", "显著变差"):
        return f"{sg(c['est'])} {unit}"
    if v == "校正后不显著":
        return f"{sg(c['est'])} {unit}，校正后不显著"
    return f"{v}（{sg(c['est'])}）"


def rat(c: dict, label: str, corrected: bool = False) -> str:
    """A ratio for a table cell, with what it is a ratio of: 费用 ×0.57 / 费用没测出差别（×1.00） / 费用 ×0.74，校正后不显著."""
    if c["lo"] <= 1 <= c["hi"]:
        return f"{label}没测出差别（{x(c)}）"
    holm = c.get("holm", c.get("p_holm"))
    tail = "，校正后不显著" if corrected and not (holm is not None and holm < 0.05) else ""
    return f"{label} {x(c)}{tail}".strip()


def est(c: dict, nd: int = 1, word: str | None = None) -> str:
    """A difference for a compact table cell: in brackets when its interval holds 0 or, given the row's word, when the
    word is not a significant one (lost in the correction); a difference that rounds to nothing is 0."""
    s = "0" if abs(c["est"]) < 0.5 * 10 ** -nd else sg(c["est"], nd)
    weak = c["lo"] <= 0 <= c["hi"] or (word is not None and not word.startswith("显著"))
    return f"（{s}）" if weak else s


def mul(c: dict, corrected: bool = False) -> str:
    """A ratio for a compact table cell: in brackets when its interval holds 1 or it does not survive the correction."""
    holm = c.get("holm", c.get("p_holm"))
    weak = c["lo"] <= 1 <= c["hi"] or (corrected and not (holm is not None and holm < 0.05))
    return f"（{x(c)}）" if weak else x(c)


def told_reading(TD: dict) -> dict:
    """The told-limit batch read the way its plan wrote beforehand (追加实验：把同时存活上限写进工具说明, 怎么读 1–4):
    quality on the 63 items fixed beforehand with the ±8 margin, P1 and P2 corrected together; a ratio has changed when
    its corrected interval leaves out 1; the behaviour at K = 2 by the calls rejected told / not told."""
    c, ex = TD["cmp"], TD["extra"]
    changed = lambda r: not (r["lo"] <= 1 <= r["hi"]) and (r.get("holm") is None or r["holm"] < 0.05)  # noqa: E731
    q = {k: verdict(c[k]["right_legacy_pct"], 8, True) for k in ("P1", "P2")}
    qf = {k: verdict(c[k]["right_pct"], 8, True) for k in ("P1", "P2")}
    cost = {k: changed(c[k]["total_cost_peak"]) for k in ("P1", "P2")}
    time = {k: changed(c[k]["answer_s"]) for k in ("P1", "P2")}
    ratio = ex["reject_ratio"]
    kids8 = c["P2"]["children"]
    if q["P1"] == "没有差别" and not cost["P1"] and not time["P1"]:
        case = "same"
    elif q["P1"].startswith("显著") or cost["P1"] or time["P1"]:
        case = "changed"
    else:
        case = "unclear"
    s1 = c["S1"]
    p2c = c["P2"]["total_cost_peak"]
    return {"q": q, "qf": qf, "cost": cost, "time": time, "beh2": ratio is not None and ratio < 0.5, "beh8": not (kids8["lo"] <= 0 <= kids8["hi"]), "case": case,
            "s1_ok": abs(s1["right_legacy_pct"]["lo"]) <= 8 and abs(s1["right_legacy_pct"]["hi"]) <= 8 and s1["total_cost_peak"]["hi"] < 1,
            "p2": ("more" if p2c["est"] > 1 else "less") if cost["P2"] else "none", "ratio": ratio}


def build() -> str:
    D = cd.load()
    E = ce.load()
    o, rb, c, k, b, p, gr, iss = D["office"], D["rubric"], D["code"], D["ctl"], D["build"], D["pub"], D["grid"], D["issues"]
    d = Doc()
    m = o["means"]
    h1 = o["h1"]
    pooled = o["depth_pooled"]
    p2, p3, p32, p32k8 = pooled["2"], pooled["3"], pooled["3_vs_2"], pooled["3_vs_2_k8"]
    p2a, p2b, p2k8 = pooled["2_first_two"], pooled["2_later_three"], pooled["2_k8"]
    free, xl = b["free"], b["xl"]
    ws, drb, kd = p["ws"], p["drb2"], p["drb2kd"]
    ms = o["merge_raw"]
    mp2, mp4 = o["merge_pooled"]["M2"], o["merge_pooled"]["M4"]
    fl = o["floor"]
    cmp_ = o["cmp"]
    od = o["old_default"]
    bb = o["both_base"]
    beh = o["behavior"]
    facts = lambda v: v * cd.SLOTS / 100  # noqa: E731  percentage points -> facts
    depth2 = [r for r in o["depth_rows"] if r["depth"] == 2]
    wd, ch = k["wide"], k["chain"]
    g3, g2 = gr["m3"]["cmp"], gr["m2"]["means"]
    xm, fm_ = xl["means"], free["means"]
    c3 = c["three"]   # the three code tasks together: the contrasts fixed before the runs
    wfl = wa.floor()  # the group told to write everything in: runs that ended early
    kd_ = o["keep_done"]  # that group, finished runs only
    kall = o["keep_all_runs"]  # that group, every run (the contrast as written down beforehand)
    m2n = o["m2_vs_keep"]  # two merged reports against the default with the keep-everything sentence, task means removed
    assert abs(m2n["est"] - ms["contrasts"]["M2_vs_N-D1-K8"]["right_pct"]["est"]) < 0.01
    t3 = sorted([rb_seconds(), h1["seconds"]["est"], fl["H1"]["seconds"]["est"]])
    leg = {g: cmp_[g]["right_legacy_pct"] for g in cmp_}  # the same contrasts on the 63 items fixed before any report was read
    h1leg = o["h1"]["right_legacy_pct"]
    # depth 2 against depth 1 with nothing else changed: the four comparisons at K = 8 (the fifth also raises K to 64)
    p2leg = {"est": p2k8["legacy_est"], "lo": p2k8["legacy_lo"], "hi": p2k8["legacy_hi"]}
    p2time = {"est": p2k8["time_ratio"], "lo": p2k8["time_lo"], "hi": p2k8["time_hi"]}
    p2cost = {"est": p2k8["cost_ratio"], "lo": p2k8["cost_lo"], "hi": p2k8["cost_hi"]}
    wt, dtm, kt = ws["time"]["H1n"], drb["time"]["H1"], kd["time"]

    # ---- guards: the sentences below are written for exactly these outcomes
    assert h1["right_pct"]["lo"] > 0 and all(r["lo"] > 0 for r in o["h1_reps"]) and all(r["lo"] > 0 for r in o["h1_legacy"]) and h1leg["lo"] > 0
    assert cmp_["D1-K1"]["right_pct"]["hi"] < 0 and cmp_["D1-K1"]["right_pct"]["holm"] < 0.05 and leg["D1-K1"]["lo"] < 0 < leg["D1-K1"]["hi"]
    assert verdict(cmp_["D1-K4"]["right_pct"], 8) == "没有差别" and verdict(cmp_["D1-K2"]["right_pct"], 8) == "没测出差别" and verdict(leg["D1-K4"], 8) == "没有差别"
    assert verdict(cmp_["D2-K8"]["right_pct"], 8) == "没测出差别" and p2["lo"] > 0 and p3["lo"] < 0 < p3["hi"] and verdict(p32, 8) == "没有差别"
    assert p2leg["lo"] < 0 < p2leg["hi"] and p2leg["est"] > 0 and p2k8["lo"] > 0 and p2k8["batches"] == 4 and p2time["lo"] < 1 < p2time["hi"] and p2time["est"] > 1.05 and p2cost["lo"] > 1.5
    assert len(depth2) == 5 and all(r["est"] > 0 and r["lo"] < 0 for r in depth2)
    d2k8 = [r for r in depth2 if r["batch"] != "highk"]
    assert len(d2k8) == 4
    assert o["k64"]["right_pct"]["holm"] > 0.05 and o["k64"]["right_pct"]["hi"] < 0 and abs(o["k64"]["children"]["est"]) < 0.5 and o["k64_caps"] == 0
    assert od["cap_rejects"] == 0 and od["facts"]["lo"] < 0 < od["facts"]["hi"] and bb["W-D3-K64"]["facts"]["lo"] < 0 < bb["W-D3-K64"]["facts"]["hi"] and od["cost"]["lo"] > 2
    assert od["answer"]["lo"] < 1 < od["answer"]["hi"] and bb["W-D2-K64"]["facts"]["lo"] > 0 and 0 < od["facts"]["est"] < bb["W-D3-K64"]["facts"]["est"]
    assert all(o["by_task"][t]["H1"]["lo"] > 0 for t in ("o1", "o2")) and all(o["by_task"][t]["DN"]["est"] > 0 for t in ("o1", "o2"))
    assert fl["PRIM"]["right_pct"]["hi"] < 0 and fl["EF"]["right_pct"]["lo"] > 0 and fl["PRIM"]["search_aux"]["hi"] < 1
    assert verdict(mp2["facts"], 8) == "没有差别" and mp4["facts"]["lo"] > 0 and all(v > 0 for v in mp4["by_batch"].values()) and mp2["cost"]["hi"] < 1 and mp4["cost"]["lo"] > 1
    assert abs(cmp_["D2-K8"]["deliv_chars"]["est"] - 1) < 0.05 and cmp_["D0"]["wrong_firm_n"]["lo"] < 0 < cmp_["D0"]["wrong_firm_n"]["hi"]
    assert h1["seconds"]["lo"] >= 1 and beh["D1-K8"]["cap"]["hit"] == 0
    assert all(cmp_[g]["total_cost_peak"]["lo"] < 1 < cmp_[g]["total_cost_peak"]["hi"] for g in ("D1-K4",)) and o["k64"]["total_cost_peak"]["lo"] < 1 < o["k64"]["total_cost_peak"]["hi"]
    assert verdict(c3["C1"]["score"], 5) == "没有差别" and verdict(c3["C2"]["score"], 5) == "没测出差别"
    assert all(c3[q]["score"]["lo"] < 0 < c3[q]["score"]["hi"] for q in ("C3a", "C3b", "C3c", "C4a", "C4b"))
    assert c["cmp"]["C2"]["score"]["lo"] > 0 and c["cmp"]["C2"]["score"]["holm"] > 0.05      # two reading tasks only: looked at afterwards
    assert c["cmp"]["C3a"]["score"]["lo"] < 0 < c["cmp"]["C3a"]["score"]["hi"] and c["fact"]["FK1"]["score"]["hi"] < 0
    assert verdict(c["cmp"]["C4a"]["score"], 5) == "没有差别" and verdict(c["cmp"]["C4b"]["score"], 5) == "没有差别"
    assert kd_["right_pct"]["lo"] > 0 and kd_["right_pct"]["n"] == wfl["ka_pairs"] and m2n["hi"] < 0 and wfl["early"] == 8 and kall["hi"] < 0 and kall["n"] == 40
    assert kd_["total_cost_peak"]["lo"] > 1 and kd_["seconds"]["lo"] > 1 and fl["KA"]["right_pct"]["n"] == 34 and verdict(fl["KA"]["right_pct"], 8) == "没有差别"
    assert wfl["early_incomplete"] == 6
    fd_ = free["cmp"]["FD"]
    assert fd_["model_cost_peak"]["hi"] < 1 and fd_["model_cost_peak"]["holm"] < 0.05 and fd_["score"]["lo"] > 0 and fd_["score"]["holm"] < 0.05 and fd_["score"]["est"] < 1
    assert free["cmp"]["K1"]["score"]["hi"] < 0 and free["cmp"]["K1"]["score"]["holm"] < 0.05 and abs(free["cmp"]["K1"]["score"]["est"]) < 1.5
    assert free["cmp"]["K4"]["model_cost_peak"]["holm"] > 0.05 and all(free["cmp"][q]["model_cost_peak"]["holm"] < 0.05 for q in ("K1", "K2"))
    assert all(free["cmp"][q]["model_cost_peak"]["lo"] < 1 < free["cmp"][q]["model_cost_peak"]["hi"] for q in ("K16", "K64"))
    assert free["cmp"]["K4"]["all_written_s"]["lo"] > 1 and xl["cmp"]["NK4"]["all_written_s"]["lo"] > 1 and xl["cmp"]["NK4"]["model_cost_peak"]["hi"] < 1
    assert xl["cmp"]["K4"]["model_cost_peak"]["hi"] < 1 and xl["cmp"]["K4"]["model_cost_peak"]["holm"] < 0.05
    assert verdict(free["cmp"]["NC"]["score"], 5) == "没有差别" and xl["cmp"]["NC"]["score"]["lo"] > 0 and xl["cmp"]["NC"]["score"]["est"] < 0.1
    assert c["p4"]["c1"]["model_cost_peak"]["hi"] < 1 and c["p4"]["c1"]["model_cost_peak"]["holm"] > 0.05
    assert c["p4"]["c1"]["seconds"]["lo"] < 1 < c["p4"]["c1"]["seconds"]["hi"] and verdict(c["p4"]["c1"]["score"], 5) == "没有差别"
    assert all(gr[t]["cmp"]["K4"]["lo"] < 0 < gr[t]["cmp"]["K4"]["hi"] for t in ("m3", "m2"))
    assert c["c1"]["spawn_runs"] == 0 and c["w1"]["spawn_runs"] == c["w1"]["runs_default"] and c["p4"]["means"]["D1-K8"]["kids"] == 0
    assert wd["cmp"]["NC"]["score"]["lo"] > 0 and ch["cmp"]["NC"]["score"]["est"] == 0 and ch["means"]["W-D1-K8"]["kids"] == 0
    assert g3["K1"]["hi"] < 0 and g3["K1"]["holm"] < 0.05 and gr["m2"]["cmp"]["FK1"]["hi"] < 0 and gr["m2"]["cmp"]["FK2"]["hi"] < 0
    assert all(gr[t]["cmp"]["FD"]["lo"] < 0 < gr[t]["cmp"]["FD"]["hi"] for t in ("m3", "m2")) and verdict(g3["K16"], 5) == "没有差别"
    assert xl["cmp"]["U"]["answer_s"]["hi"] < 1 and xl["cmp"]["K16"]["answer_s"]["lo"] < 1 < xl["cmp"]["K16"]["answer_s"]["hi"]
    assert all(xl["cmp"][q]["answer_s"]["lo"] > 1 and xl["cmp"][q]["answer_s"]["holm"] < 0.05 for q in ("K1", "K2", "K4"))
    assert free["cmp"]["NC"]["answer_s"]["lo"] < 1 < free["cmp"]["NC"]["answer_s"]["hi"] and xl["cmp"]["NC"]["answer_s"]["lo"] < 1 < xl["cmp"]["NC"]["answer_s"]["hi"]
    assert all(free["cmp"][q]["answer_s"]["lo"] < 1 < free["cmp"][q]["answer_s"]["hi"] for q in ("K4", "K16", "K64", "FD"))
    assert all(xl["cmp"][q]["answer_s"]["lo"] < 1 < xl["cmp"][q]["answer_s"]["hi"] for q in ("NK4", "DN")) and xl["cmp"]["DE"]["answer_s"]["lo"] > 1
    assert all(xl["depth_hi"][q]["answer_s"]["lo"] < 1 < xl["depth_hi"][q]["answer_s"]["hi"] for q in ("DE16", "DE64"))
    assert verdict(ws["cmp"]["H1n"]["f1_item"], 5) == "没测出差别" and ws["cmp"]["H1n"]["r_item"]["p_holm"] > 0.05 and drb["cmp"]["H1"]["total"]["lo"] > 0
    assert all(abs(kd["cmp"][q]["total"][e]) <= 5 for q in ("K1", "D2") for e in ("lo", "hi"))
    assert wt["lo"] < 1 < wt["hi"] and dtm["lo"] < 1 < dtm["hi"] and all(kt[q]["lo"] < 1 < kt[q]["hi"] for q in ("K1", "D2"))
    assert iss["all_crashes_shallow"] == 0 and iss["crashes_depth1"] == 0
    fw = free["wave"]
    assert fw["W-D1-K8"]["late"]["answer"] > 1.5 * fw["W-D1-K8"]["rest"]["answer"] and abs(fw["W-D1-K8"]["rest"]["answer"] - fw["D0"]["rest"]["answer"]) < 1.5

    h1_lo, h1_hi = min(r["est"] for r in o["h1_reps"]), max(r["est"] for r in o["h1_reps"])
    t1 = {t: (min(o["h1_by_task"][n][t]["est"] for n in o["h1_by_task"]), max(o["h1_by_task"][n][t]["est"] for n in o["h1_by_task"])) for t in ("o1", "o2")}
    h1_cost = h1["total_cost_peak"]["est"]
    d2_cost = cmp_["D2-K8"]["total_cost_peak"]["est"]
    save_cost = 1 - xl["cmp"]["S8"]["model_cost_peak"]["est"]
    save_time = 1 - xl["cmp"]["S8"]["answer_s"]["est"]
    build_cost = sorted([free["cmp"]["NC"]["model_cost_peak"]["est"], free["cmp"]["PC"]["model_cost_peak"]["est"], xl["cmp"]["NC"]["model_cost_peak"]["est"]])
    k4_slower = xl["cmp"]["K4"]["answer_s"]["est"] - 1
    k4_cheaper = 1 - xl["cmp"]["K4"]["model_cost_peak"]["est"]
    review_groups = ("W-D1-K4", "W-D1-K8", "W-D1-K16", "W-D2-K8")
    review_runs = sum(xl["review_runs"][g] for g in review_groups)
    review_all = sum(xm[g]["n"] for g in review_groups)
    extra_failed = xl["failed"]["W-N-D1-K8"] - xl["failed"]["W-D1-K8"]
    ctx = wa.mech()
    lv = o["default_levels"]
    dt = drb["cmp"]["H1"]["total"]
    rt = kd["retest"]["total"]
    op = o["opens"]
    d2_full = sum(1 for q in op["D2-K8"]["peaks"] if q >= 8)
    wso, dro = ws["opens"], drb["opens"]
    # yuan per additional fact stated correctly: on the whole list and on the 63 items fixed beforehand
    pf = o["per_fact"]  # yuan per additional fact on the whole list, between neighbouring groups of the main office table
    gain = h1["right_n"]["est"]                      # facts per report, whole list
    k1_lost = -cmp_["D1-K1"]["right_n"]["est"]
    d2_gain = facts(p2k8["est"])
    assert 14 < gain < 16 and 6.5 < k1_lost < 7.5 and 3.4 < d2_gain < 4.1
    xl_depth = sorted([xl["cmp"]["DN"]["answer_s"]["est"], xl["cmp"]["DE"]["answer_s"]["est"], xl["depth_hi"]["DE16"]["answer_s"]["est"], xl["depth_hi"]["DE64"]["answer_s"]["est"]])
    old_gain = sorted([od["facts"]["est"], bb["W-D3-K64"]["facts"]["est"]])
    pubtime = sorted([wt["est"], dtm["est"]])

    # =========================================================================================== title, background
    d.add("# Subagent 的深度上限和同时存活上限该设多少", "")
    d.add("## 背景", "")
    d.p("在小红书上收到大量用户反馈 DSH 喜欢开很多 subagent，Token 消耗很快。以其中三个外部用户的 session log 为例：")
    d.add(*table([["日志", "任务", "subagent", "递归数量（第 1/2/3 层）", "主 agent 开的 subagent 数量", "第四层递归尝试被拒数量", "最大同时存活数", "Subagent token（不含缓存 / 缓存命中 / 输出）"],
                  ["A", "新加坡、韩国旅游攻略（办公，联网）", "24", "2 / 4 / 18", "2", "21", "22", "249 万 / 8207 万 / 59 万"],
                  ["B", "调研 DSH 记忆插件（读代码）", "18", "5 / 10 / 3", "5", "0", "18", "220 万 / 9224 万 / 64 万"],
                  ["C", "硬件选型报告（办公，联网）", "45", "7 / 14 / 24", "7", "15", "27", "282 万 / 3790 万 / 43 万"]]))
    d.add("- subagent 倾向于递归而不是同一层级内追加。", "- 一般会用到允许的最大递归深度，A、C 里第 3 层 subagent 数量最多，还分别有 21、15 次尝试开第 4 层。", "")
    # The background is the page owner's text as it stands on the page (she rewrote these lines on 2026-10-07, after the
    # thirteenth version; the page update no longer replaces this section: build with --wiki-from 结论).
    d.p("**问题探讨：DSH 可以设置 subagent 的最大递归深度 D（maxDepth）和最大同时存活数量 K（maxActiveSubagents）。在日常任务（代码任务和办公任务）上，这两个上限各设多少合适？目前的默认是 D=1、K=8。这涉及到每次任务的花费以及subagent的收益。**")

    # ================================================================================================ conclusions
    # Layout (the owner's reviewer, 2026-10-07): three lines, the reasoning in three steps, the overview figure and
    # table, the recommendations. The results are organised by question, one small table across the tasks per
    # question; the tables per task and every sentence about how something was computed are in the appendix.
    res_cost = sorted([h1_cost, ws["cmp"]["H1n"]["total_cost_peak"]["est"], drb["cmp"]["H1"]["total_cost_peak"]["est"]])
    res_runs = op["D1-K8"]["runs"] + wso["runs"] + dro["runs"]
    gain_pp = sorted([h1leg["est"], h1["right_pct"]["est"]])            # percentage points: the 63 items fixed beforehand, the whole list
    d2_pp = sorted([p2leg["est"], p2k8["est"]])
    xo = xl["opens"]
    assert op["D1-K8"]["cap_runs"] == 0 and wso["cap_runs"] == 0 and dro["cap_runs"] == 0 and xo["cap_runs"] == xo["runs"]
    assert all(v["cap_runs"] <= 1 for v in (c["opens"], c["p4"]["opens"], wd["opens"], ch["opens"], free["opens"]))
    assert 2.5 < res_cost[0] < 3.05 and 3.5 < res_cost[-1] < 4.2
    code_scores = [c["cmp"]["C1"]["score"], c["p4"]["c1"]["score"], free["cmp"]["NC"]["score"], xl["cmp"]["NC"]["score"]]
    code_times = [c["cmp"]["C1"]["seconds"], c["p4"]["c1"]["seconds"], free["cmp"]["NC"]["answer_s"], xl["cmp"]["NC"]["answer_s"]]
    assert all(abs(q["est"]) < 2 for q in code_scores) and all(q["lo"] <= 1 <= q["hi"] for q in code_times)
    assert free["cmp"]["K16"]["answer_s"]["lo"] < 1 < free["cmp"]["K16"]["answer_s"]["hi"] and o["k64"]["right_pct"]["est"] < 0
    d.add("## 结论", "")
    cst = D["cost"]
    ck = cst["by_key"]
    wp, dp = ws["pair"], drb["pair"]
    fitc = cst["fit"]
    assert 1.3 < fitc["per_subagent"] < 1.6 and fitc["r2"] > 0.7 and fitc["max_group_gap"] < 0.16 and 1.9 < ck["none"]["mean"] < 2.2 and 7.8 < ck["default"]["mean"] < 8.4
    assert 3.3 < ck["default"]["kids"] < 3.8 and cst["default_all"]["max"] == ck["default"]["max"] and cst["default_all"]["n"] == 140
    res_none = [ck["none"]["mean"], wp["D0"]["cost"], dp["D0"]["cost"]]
    res_dflt = [ck["default"]["mean"], wp["W-D1-K8"]["cost"], dp["W-D1-K8"]["cost"]]
    res_kids = [ck["default"]["kids"], wp["W-D1-K8"]["kids"], dp["W-D1-K8"]["kids"]]
    assert all(2 < v < 2.5 for v in res_none) and all(7.5 < v < 8.5 for v in res_dflt) and all(2.8 < v < 3.7 for v in res_kids) and 7.5 < ck["d2"]["kids"] < 8.5 and 14 < ck["d2"]["mean"] < 15.5
    assert mp4["facts"]["lo"] > 0 and mp4["legacy"]["lo"] > 0 and 6.5 < mp4["legacy"]["est"] < mp4["facts"]["est"] < 7.5 and 0.9 < o["merge_search_ratio"]["M4"] < 1.1
    L = ce.limits(D)
    LK, LD = {r["key"]: r for r in L["k"]}, {r["key"]: r for r in L["depth"]}
    SHORT = {"office": "办公报告题", "ws": "评测集填表题", "drb2": "评测集报告题", "code": "读代码题", "p4": "小编程题", "wide": "限时 24 题", "chain": "16 步串行题",
             "free": "不限时 24 题", "xl": "大型编码题", "xln": "大型编码题（加不复核提示）"}
    WORDS = {"c": ("更便宜", "更贵"), "t": ("更快", "更慢")}

    def digest(rows: list, v, m_: str) -> str:
        """One cell of the two tables of the conclusions: the detected differences by task, then what the rest did."""
        i_ = "qct".index(m_)
        cells = [(r, r["cells"][v]) for r in rows if v in r["cells"] and r["cells"][v][m_] is not None]
        if not cells:
            return "—"
        ref = 0 if m_ == "q" else 1

        def one(r, cl):
            nm = SHORT[r["key"]] + ("" if SHORT[r["key"]].endswith("）") else " ")
            if m_ != "q":
                return f"{nm}{x(cl[m_])}"
            t = f"{nm}{sg(cl['q']['est'], cl['nd'])}"
            if r.get("tests") and ce.strong(cl["q"], cl["corr"][0]):
                t += f"（{rnd(abs(xl['failed'][cl['q']['a']] - xl['failed'][cl['q']['b']]))} 个测试）"
            return t
        hit = [(r, cl) for r, cl in cells if ce.strong(cl[m_], cl["corr"][i_])]
        rest = [(r, cl) for r, cl in cells if not ce.strong(cl[m_], cl["corr"][i_])]
        lost = [(r, cl) for r, cl in rest if not cl[m_]["lo"] <= ref <= cl[m_]["hi"]]  # outside its interval, lost in the correction
        note = ("；" + "、".join(one(r, cl) for r, cl in lost) + " 校正后不显著") if lost else ""
        if m_ != "q" and len(hit) >= 5 and len({cl[m_]["est"] > 1 for _, cl in hit}) == 1:
            es = sorted(cl[m_]["est"] for _, cl in hit)
            word = WORDS[m_][es[0] > 1]
            if not rest:
                return f"都{word}（{x(es[0])}–{x(es[-1])}）"
            return f"除{'、'.join(SHORT[r['key']] for r, _ in rest)}外都{word}（{x(es[0])}–{x(es[-1])}）{note}"
        head = "、".join(one(r, cl) for r, cl in hit)
        tail = (("其余" if hit else "都") + "不显著" + note) if rest else ""
        return "；".join(q for q in (head, tail) if q)
    tested = lambda rows, v: "全部任务" if all(v in r["cells"] for r in rows) else "、".join(SHORT[r["key"]] for r in rows if v in r["cells"])  # noqa: E731
    kq = lambda key, v, m_="q": LK[key]["cells"][v][m_]  # noqa: E731
    dq = lambda key, v, m_="q": LD[key]["cells"][v][m_]  # noqa: E731
    p3k8 = pooled["3_k8"]
    # ---- guards for the sentences of the conclusions
    assert verdict(kq("office", 4), 8, True) == "没有差别" and not ce.strong(kq("office", 4, "c"), True) and not ce.strong(kq("office", 4, "t"))
    assert not ce.strong(kq("office", 64), True) and kq("office", 64)["hi"] < 0 and o["k64_caps"] == 0
    assert all(not ce.strong(r["cells"][v][m_], r["cells"][v]["corr"]["qct".index(m_)]) for r in L["k"] for v in (16, 64) if v in r["cells"] for m_ in "qct" if r["cells"][v][m_] is not None)
    low_cost = sorted(r["cells"][v]["c"]["est"] for r in L["k"] for v in (1, 2) if v in r["cells"])
    assert all(ce.strong(r["cells"][v]["c"], r["cells"][v]["corr"][1]) for r in L["k"] for v in (1, 2) if v in r["cells"]) and 0.35 < low_cost[0] < low_cost[-1] < 0.8
    assert ce.strong(kq("office", 1), True) and ce.strong(kq("wide", 1), True) and ce.strong(kq("xln", 1, "t"), True) and ce.strong(kq("xln", 2, "t"), True)
    assert not ce.strong(kq("office", 2), True) and not ce.strong(kq("wide", 2), True) and kq("wide", 2)["hi"] < 0 and kq("office", 2)["est"] < 0
    assert kq("wide", 2)["est"] < kq("office", 2)["est"] < kq("code", 2)["est"] < 0 and not ce.strong(kq("code", 2), True)
    assert ce.strong(kq("free", 1), True) and verdict(kq("free", 4), 5, True) == "没有差别" and verdict(kq("code", 4), 5, True) == verdict(kq("wide", 4), 5, True) == "没测出差别"
    assert ce.strong(dq("code", 2, "t")) and ce.strong(dq("free", 2), True) and ce.strong(dq("free", 2, "c"), True) and 0.4 < xl["cmp"]["U"]["answer_s"]["est"] < 0.5
    assert ce.strong(kq("xl", 4, "c")) and ce.strong(kq("xln", 4, "c"), True) and ce.strong(kq("xln", 4, "t"), True) and not ce.strong(kq("xl", 4, "t")) and ce.strong(kq("xl", 4))
    assert not ce.strong(kq("free", 4, "c"), True) and kq("free", 4, "c")["hi"] < 1
    k4_tests = abs(xl["failed"]["W-D1-K4"] - xl["failed"]["W-D1-K8"])
    assert 0.3 < k4_tests < 0.5
    step1, step2 = pf["none_default"], pf["default_d2"]
    assert 0.38 < step1 < 0.43 and 1.8 < step2 < 1.9 and 4 < step2 / step1 < 5
    assert ce.strong(dq("office", 2)) and ce.strong(dq("drb2", 2, "c"), True) and ce.strong(dq("code", 2, "c")) and not ce.strong(dq("drb2", 2)) and not ce.strong(dq("code", 2))
    assert not ce.strong(dq("office", 3)) and abs(dq("office", 3, "c")["est"] - dq("office", 2, "c")["est"]) < 0.05 and p32k8["lo"] < 0 < p32k8["hi"]
    spent_c = sorted(q["model_cost_peak"]["est"] for q in (c["cmp"]["C1"], wd["cmp"]["NC"], free["cmp"]["NC"], xl["cmp"]["NC"]))
    b4 = mp4["batch"]
    ds = E["dose"]  # one agent told to search more, two sentences (the batch written into the plan on 2026-10-07)
    dc, dm, dpg = ds["cmp"], ds["means"], E["pages"]["dose"]
    TD = E["told"]  # the limit written into the tool description (the batch office-told); None until its analysis exists
    TR = told_reading(TD) if TD else None
    told_concl = told_scope = told_adv_tail = told_defect = told_method = ""
    if TD:
        tm, tc = TD["means"], TD["cmp"]
        word_ct = lambda k_, m_: ("有变化" if (TR["cost"] if m_ == "total_cost_peak" else TR["time"])[k_] else "没测出变化") + f"（{x(tc[k_][m_])}）"  # noqa: E731
        dep_ = lambda g_: rnd(tm[g_]["depth_rejects"])  # noqa: E731  (calls rejected by the depth limit per run)
        told_concl = (f"K=2 时每次运行被 K 拒绝的调用从 {rnd(tm['D1-K2']['cap_rejects'])} 次变成 {rnd(tm['T-D1-K2']['cap_rejects'])} 次（{'基本不再超出上限' if TR['beh2'] else '告知以后仍然超出'}），被深度上限拒绝的从 {dep_('D1-K2')} 次变成 {dep_('T-D1-K2')} 次（{ci(tc['P1']['depth_rejects'])}）；"
                      f"写对的事实{TR['q']['P1']}（{ci(tc['P1']['right_legacy_pct'])}），费用{word_ct('P1', 'total_cost_peak')}，时间{word_ct('P1', 'answer_s')}；"
                      f"K=8（默认）时开的数量{'有变化' if TR['beh8'] else '没测出变化'}（{sg(tc['P2']['children']['est'])} 个），写对的事实{TR['q']['P2']}（{ci(tc['P2']['right_legacy_pct'])}），费用{word_ct('P2', 'total_cost_peak')}，"
                      f"被深度上限拒绝的调用从 {dep_('D1-K8')} 次变成 {dep_('T-D1-K8')} 次（{ci(tc['P2']['depth_rejects'])}，校正后 p = {rnd(tc['P2']['depth_rejects']['holm'], 2)}）。")
        changed_what = [n_ for n_, f_ in (("写对的事实", TR["q"]["P1"].startswith("显著")), ("费用", TR["cost"]["P1"]), ("时间", TR["time"]["P1"])) if f_]
        if TR["case"] == "same":
            told_scope = f"- K 的结论对两种实现都成立：超出上限的那次调用被拒绝，工具说明里写不写上限都一样（K=2 上两种做法写对的事实没有差别，费用、时间没测出变化；细节{SEC['k']}）。到了上限排队等空位的做法没有测。"
        elif TR["case"] == "changed":
            told_scope = f"- K=1、2 的结论只对现在的实现成立：工具说明里不写上限，超出上限的那次调用被拒绝。把上限写进说明以后，K=2 的{'、'.join(changed_what)}变了（细节{SEC['k']}）。"
        else:
            told_scope = f"- K 的结论只对现在的实现成立：工具说明里不写上限，超出上限的那次调用被拒绝。把上限写进工具说明的一批（K=2、8 各 {tc['P1']['right_legacy_pct']['n']} 对）分不出有没有差别（细节{SEC['k']}）。"
        if TR["p2"] == "more":
            told_adv_tail = f"把上限写进工具说明会让模型在默认值下多开、费用 {x(tc['P2']['total_cost_peak'])}，写法要再试；到了上限就不再给它开 subagent 的工具。"
        elif TR["p2"] == "less":
            told_adv_tail = f"把上限写进工具说明：默认值下模型开得更少、费用 {x(tc['P2']['total_cost_peak'])}（细节{SEC['k']}）。"
        else:
            told_adv_tail = "把上限写进工具说明（默认值下开的数量、质量、费用都没测出变化" + ("，K=2 时省掉了被拒的调用" if TR["beh2"] else "") + "），或者到了上限就不再给它开 subagent 的工具。"
        if TR["s1_ok"]:
            told_adv_tail += f" 告知以后的 K=2 比默认便宜（{x(tc['S1']['total_cost_peak'])}）、写对的和默认没有差别，可以作为候选改动，只在两道办公报告题上测过。"
        told_defect = f"把上限写进工具说明的一批里，K=2 时每次运行被拒的调用从 {rnd(tm['D1-K2']['cap_rejects'])} 次变成 {rnd(tm['T-D1-K2']['cap_rejects'])} 次（细节{SEC['k']}）。"
        told_method = ("- **把同时存活上限写进工具说明。** 容器里 DSH 的 tool-subagent 包换成只改一行的版本：拼两个开 subagent 的工具的说明时，末尾加上环境变量里的一句话，内容和超出上限时的拒绝消息相同（上限是几，超出了怎么办）；不告知的组用原来的文件。"
                       "跑完先核对全部运行的会话头：告知组里凡是带这两个工具的会话，说明都以这句话结尾、数字和该组的 K 一致，其余组一个都没有。"
                       f"读法在开跑前写定：质量以 63 条为准，边界 ±8 个百分点；K=2、K=8 两个主要对比每个指标一起校正；K=2 上被 K 拒绝的调用降到不告知的一半以下才写“基本不再超出”；不完整的运行不进对比，另按全部运行算一遍" + ("（这一批 160 次都交出了完整报告，两种算法的数相同）。" if all(v_["incomplete"] == 0 for v_ in tm.values()) else f"（K=2 上告知对不告知的 63 条之差全算是 {ci(TD['every']['P1']['right_legacy_pct'])}）。"))
    assert all(dc[q]["right_pct"]["hi"] < 0 and dc[q]["right_pct"]["holm"] < 0.05 for q in ("P150", "P250")) and all(dc[q]["search_aux"]["lo"] < 1 < dc[q]["search_aux"]["hi"] for q in ("P150", "P250"))
    assert all(dc[q]["total_cost_peak"]["hi"] < 1 and dc[q]["answer_s"]["lo"] > 1 for q in ("P150", "P250")) and abs(dc["P150"]["total_cost_peak"]["est"] - dc["P250"]["total_cost_peak"]["est"]) < 0.01
    assert abs(dc["P150"]["answer_s"]["est"] - dc["P250"]["answer_s"]["est"]) < 0.02 and 0.75 < dc["P150"]["total_cost_peak"]["est"] < 0.82 and 1.55 < dc["P150"]["answer_s"]["est"] < 1.7
    assert b4["a"]["lo"] > 0 and b4["b"]["lo"] < 0 < b4["b"]["hi"] and verdict(o["m4_vs_keep"], 8) == "没有差别" and 1.1 < mp4["cost"]["est"] < 1.2 and 1.65 < mp4["time"]["est"] < 1.8
    tests_more = xl["failed"]["D0"] - xl["failed"]["W-D1-K8"]
    assert 1.5 < tests_more < 2.5
    assert all(ce.strong(dq(k_, 2, "t"), LD[k_]["cells"][2]["corr"][2]) for k_ in ("code", "xln")) and not ce.strong(dq("office", 2, "t"), LD["office"]["cells"][2]["corr"][2])
    cheap3 = sorted(dq(k_, 0, "c")["est"] for k_ in ("office", "ws", "drb2"))        # none / default, the three research tasks
    cheapc = sorted(dq(k_, 0, "c")["est"] for k_ in ("code", "wide", "free", "xl"))  # the code tasks on which the model opens subagents
    assert 0.24 < cheap3[0] < cheap3[-1] < 0.38 and abs(1 / cheap3[0] - res_cost[-1]) < 0.05 and abs(1 / cheap3[-1] - res_cost[0]) < 0.05
    assert abs(1 / cheapc[0] - spent_c[-1]) < 0.05 and abs(1 / cheapc[-1] - spent_c[0]) < 0.05 and all(ce.strong(dq(k_, 0, "c"), LD[k_]["cells"][0]["corr"][1]) for k_ in ("code", "wide", "free", "xl"))
    wk4, dk4_ = kq("ws", 4), kq("drb2", 4)  # K = 4 on the two public benchmarks (the batches ws-k4 and drb2-k4), the primary family of two
    assert verdict(wk4, 5, True) == "没测出差别" and verdict(dk4_, 5, True) == "没有差别" and wk4["lo"] > -5 and wk4["hi"] > 5 and verdict(kq("ws", 1), 5) == "没有差别"
    assert not any(ce.strong(kq(k_, 4, m_)) for k_ in ("ws", "drb2") for m_ in "ct") and ce.strong(kq("ws", 1, "c")) and not ce.strong(kq("ws", 1, "t"))
    assert 0.68 < kq("xl", 4, "c")["est"] < 0.72 and 0.80 < kq("xln", 4, "c")["est"] < 0.84 and 1.18 < kq("xln", 4, "t")["est"] < 1.26 and 2.1 < dq("xln", 0, "t")["est"] < 2.4
    # ---- delivery, the yardstick of the office task, rejected calls: what the conclusions rest on
    lg = o["legacy"]  # contrasts on the 63 items fixed beforehand that the batch statistics do not carry
    RL = E["reliability"]["cells"]
    RS = ce.reliability_sum
    plain_nowait = lambda q: q["variant"] == "plain" and not q["waits"]  # noqa: E731
    rel_k = {v: RS(RL, "office", lambda q, v=v: q["col"] == f"1-{v}" and plain_nowait(q)) for v in (1, 2, 4, 8)}
    rel_d2 = RS(RL, "office", lambda q: q["col"] == "2-8" and plain_nowait(q))
    rel_d3 = RS(RL, "office", lambda q: q["col"] == "3-8" and plain_nowait(q))
    rel_keep = RS(RL, "office", lambda q: q["col"] == "1-8" and q["variant"] == "N" and not q["waits"])
    rel_none = RS(RL, "office", lambda q: q["col"] == "none")
    rel_w = {dd: RS(RL, "office", lambda q, dd=dd: q["col"].startswith(f"{dd}-") and q["waits"]) for dd in (1, 2, 3)}
    assert [rel_k[v]["runs"] for v in (1, 2, 4, 8)] == [60, 60 + (40 if TD else 0), 60, 140 + (40 if TD else 0)] and all(rel_k[v]["crash"] == 0 for v in rel_k) and rel_d2["runs"] == 80 and rel_d3["runs"] == 40
    assert rel_keep["runs"] == 40 and rel_keep["incomplete"] == wfl["early_incomplete"] and rel_keep["early"] == wfl["early"] and rel_none["crash"] == 0 and rel_none["incomplete"] == 1
    deep_crash = (rel_d2["crash"] + rel_d3["crash"]) / (rel_d2["runs"] + rel_d3["runs"])
    shallow_runs = sum(q["runs"] for q in RL if q["col"] == "none" or q["col"].startswith("1-"))
    assert 0.32 < deep_crash < 0.36 and sum(q["crash"] for q in RL if q["col"] == "none" or q["col"].startswith("1-")) == 0 and shallow_runs > 1500
    assert sum(q["crash"] for q in RL) == iss["all_crashes"] and sum(q["runs"] for q in RL) + 175 == iss["all_runs"]
    dep_rej = beh["D1-K8"]["depth"]["total"] / beh["D1-K8"]["depth"]["runs"]
    dep_rej2 = beh["D1-K2"]["depth"]["total"] / beh["D1-K2"]["depth"]["runs"]
    cap_rej2 = beh["D1-K2"]["cap"]["total"] / beh["D1-K2"]["cap"]["runs"]
    MX = E["mechanism"]  # read from the session logs: rejected delegation calls, the two delegation tools, who handed back which fact, two trees
    mrj, mtl, mtb = MX["rejects"], MX["tools"], MX["tools_by_batch"]
    made = lambda b_, g_: mtb[b_][g_]["children"] / mtb[b_][g_]["runs"]  # noqa: E731  (subagents started per run)
    rj8, made8 = mrj["office-confirm"]["D1-K8"], made("office-confirm", "D1-K8")
    assert abs(rj8["depth"] - dep_rej) < 0.01 and rj8["cap"] == 0 and abs(mrj["office-confirm"]["D1-K2"]["cap"] - cap_rej2) < 0.01 and abs(mrj["office-confirm"]["D1-K2"]["depth"] - dep_rej2) < 0.01
    assert rj8["args_share"] + rj8["dead_share"] < 0.03 and 3.4 < made8 < 3.7 and mtl["runs"] == iss["all_runs"] and MX["rejected"]["runs"] == iss["all_runs"]
    m_calls = mtl["subagent"] + mtl["subagent_fork"]
    m_rej = MX["rejected"]["depth"] + MX["rejected"]["cap"]
    assert abs(m_rej - round(m_rej)) < 1e-6 and 0 <= m_calls - mtl["children"] - round(m_rej) <= 5 and mtl["subagent_fork"] < 100 and 11000 < mtl["children"] - (sum(v_["children"] for v_ in mtb["office-told"].values()) if TD else 0) < 12000
    assert 7 < dep_rej < 8 and 4 < dep_rej2 < 5 and 1.4 < cap_rej2 < 1.7 and beh["D1-K8"]["cap"]["total"] == 0
    # the reading tasks, K = 1 and 2 against 8, the three depths together (pooled after the first batch had been read; corrected in its own family)
    fk1, fk2, fk4 = c["fact"]["FK1"]["score"], c["fact"]["FK2"]["score"], c["fact"]["FK4"]["score"]
    assert verdict(fk4, 5, True) == "没有差别" and fk4["n"] == 20
    assert fk1["hi"] < 0 and fk1["holm"] < 0.05 and fk2["hi"] < 0 and fk2["holm"] > 0.05 and -4.5 < fk1["est"] < fk2["est"] < -3
    assert verdict(kq("code", 1), 5, True) == verdict(kq("code", 2), 5, True) == "没测出差别"
    # the four tasks without a time limit that are graded by tests or a key: every run that finished scores near full marks
    low_runs = {}
    for f_, fixed_ in ce.every_rows().items():
        for r_ in cd.R(f_):
            key_ = fixed_ or ce.TASK_ROW[r_["task"]]
            if key_ in ("p4", "chain", "free", "xl"):
                s_ = cd.num(r_.get("score"))
                e_ = low_runs.setdefault(key_, {"runs": 0, "low": 0, "low_early": 0, "low_none": 0, "min_rest": 100.0})
                e_["runs"] += 1
                if s_ is None or s_ < 90:
                    e_["low"] += 1
                    kids_ = cd.num(r_.get("children")) or 0
                    e_["low_early"] += kids_ > 0 and r_.get("early_finish") == "1"   # the root ended while its subagents were still working
                    e_["low_none"] += kids_ == 0                                       # the run ended at once, nothing written
                else:
                    e_["min_rest"] = min(e_["min_rest"], s_)
    assert low_runs["chain"]["low"] == low_runs["free"]["low"] == 0 and low_runs["p4"]["low"] == low_runs["p4"]["low_early"] == 9
    assert low_runs["xl"]["low"] == low_runs["xl"]["low_none"] == 1 and low_runs["xl"]["low_early"] == 0
    assert min(v["min_rest"] for v in low_runs.values()) > 94 and low_runs["p4"]["runs"] == 160 and low_runs["xl"]["runs"] == 150
    near_full = [abs(cl["q"]["est"]) for part in (L["k"], L["depth"]) for r_ in part if r_["key"] in ("p4", "chain", "free", "xl", "xln") for cl in r_["cells"].values() if cl["q"] is not None]
    assert len(near_full) >= 18 and max(near_full) < 1.05
    kept_means = {}  # the same four tasks, batch by batch: the group means without the runs below 90
    for f_, fixed_ in ce.every_rows().items():
        g_ = {}
        for r_ in cd.R(f_):
            key_ = fixed_ or ce.TASK_ROW[r_["task"]]
            s_ = cd.num(r_.get("score"))
            if key_ in ("p4", "chain", "free", "xl") and s_ is not None and s_ >= 90:
                g_.setdefault((key_, r_["group"]), []).append(s_)
        for (key_, _grp), v_ in g_.items():
            kept_means.setdefault((f_, key_), []).append(st.mean(v_))
    near_spread = max(max(v_) - min(v_) for v_ in kept_means.values())
    assert len(kept_means) == 5 and 1.3 < near_spread < 1.4
    assert verdict(leg["D1-K1"], 8, True) == verdict(leg["D1-K2"], 8, True) == "没测出差别" and verdict(lg["k64"], 8) == "没有差别" and verdict(p2leg, 8) == "没有差别"
    p3leg_ = {"est": p3k8["legacy_est"], "lo": p3k8["legacy_lo"], "hi": p3k8["legacy_hi"]}
    assert verdict(p3leg_, 8) == "没有差别" and h1leg["lo"] > 0 and lg["keep_done"]["lo"] < 0 < lg["keep_done"]["hi"] and kd_["right_pct"]["lo"] > 0
    assert verdict(dq("drb2", 2), 5) == "没有差别" and verdict(lg["old"], 8) == "没有差别" and all(abs(dq(k_, 2)["est"]) < 1 or not ce.strong(dq(k_, 2), LD[k_]["cells"][2]["corr"][0]) for k_ in LD if 2 in LD[k_]["cells"] and k_ != "office")
    assert all(1.08 < dq(k_, 2, "t")["est"] < 1.4 for k_ in ("office", "code", "xln")) and not ce.strong(kq("xl", 4, "t"))
    # depth 2 and the time: nowhere clearly faster; the two clear slowdowns both have a lower end of 1.01 (the office tasks: the interval holds 1)
    assert all(1.0 < dq(k_, 2, "t")["lo"] < 1.015 for k_ in ("code", "xln")) and 0.97 < dq("office", 2, "t")["lo"] < 1
    assert not any(r_["cells"][2]["t"] is not None and r_["cells"][2]["t"]["hi"] < 1 for r_ in L["depth"] if 2 in r_["cells"])
    assert fd_["answer_s"]["hi"] > 1 and c["cmp"]["C4a"]["seconds"]["hi"] > 1 and not ce.strong(kq("xln", 4))
    # delegation on the 63 items, task by task: clear on the travel task in every batch, on the CPU task in one batch of four
    hlt = o["h1_legacy_by_task"]
    assert len(hlt) == 4 and all(v["o1"]["lo"] > 0 for v in hlt.values()) and sum(1 for v in hlt.values() if v["o2"]["lo"] > 0) == 1 and all(v["o2"]["est"] > 0 for v in hlt.values())
    wk4all = wsk_all = p["wsk"]["with_flagged"]["K4"]
    assert wk4all["lo"] < -5 < 0 < wk4all["hi"] < 5 and wk4["lo"] > -5 and wk4["hi"] > 5
    d2pub = sorted([dq("drb2", 2, "c")["est"], dq("code", 2, "c")["est"]])
    assert 1.4 < d2pub[0] < d2pub[1] < 1.55

    # =============================================================================== the conclusions, in short
    d.p(f"**深度上限 D 保持 1。同时存活上限 K 保持 8：不用调大，也不要低于 4；深度 1 下，4 和 8 之间质量上显著的差别只有大型编码题上的 {rnd(-kq('xl', 4)['est'], 2)} 分。**")
    d.p(f"下面都是和现在的默认（D=1、K=8）比。一个取值要在交付、质量、用户等的时间上都不比默认差，才看它省不省钱。调研类任务指联网查资料的三种：办公报告题（联网调研后写长报告，2 道）和两个公开评测集的题（评测集报告题、评测集填表题）。"
        f"办公报告题的质量按事先定下的 63 条事实算；把后补的条目也算上的数（下文叫全清单）在括号里，或者在细节{SEC['worth']}到{SEC['spend']}的表里。“显著”指差的 95% 置信区间不含 0（倍数是不含 1），细的定义和其余任务的说明在后面的“实验一览”。"
        "背景里的三份用户日志是旧默认（9 月中旬以前：深度上限 3、数量不设上限）下的运行。")
    d.p("**深度**")
    d.add(f"- 不开 subagent：调研类任务的费用是默认的 {rnd(cheap3[0], 2)}–{rnd(cheap3[-1], 2)} 倍；办公报告题少写对 {rnd(h1leg['est'])} 个百分点（主要在旅行攻略题上），评测集报告题低 {rnd(dt['est'])} 分，都显著。",
          f"- 深度 2：办公报告题一次约 {m['D1-K8']['cost']:.0f} 元变成约 {m['D2-K8']['cost']:.0f} 元，多写对 {rnd(p2leg['est'])} 个百分点（区间 [{sg(p2leg['lo'])}, {sg(p2leg['hi'])}]，没有差别；全清单 {sg(p2k8['est'])}，显著）；评测集报告题、读代码题贵到约 1.5 倍，质量一个没有差别、一个没测出差别。",
          "- 深度 2 没有让任何一种任务显著更快；读代码题和题面要求不复核的大型编码题上慢一到三成，都只是刚好显著（区间下端 1.01），办公报告题上没测出。命令行一次性运行时，办公报告题上三分之一的运行退出时崩溃（多数已交出报告，进程以出错结束）。",
          "- 深度 3 没测出比深度 2 好；办公报告题上两者费用相同。", "")
    d.p("**K**")
    d.add("- 调研类任务上模型一次运行只开三四个 subagent：K=4 对 8（三种任务）、K=64 对 8（办公报告题），质量、费用、时间都不显著。K=16、64 在代码类任务上没测出更快。",
          "- 大型编码题（按规格写一个 61 个文件的 Python 包）上，模型写完代码会再派一批 subagent 复核。K=4 比 8 便宜两到三成；题面要求不复核时，K=4 慢两成。",
          f"- K=1 显著变差：题面要求不复核时，大型编码题慢到 {rnd(kq('xln', 1, 't')['est'], 2)} 倍（K=2 是 {rnd(kq('xln', 2, 't')['est'], 2)} 倍）；限时 24 题（24 道小题限时 3 分钟）低 {rnd(-kq('wide', 1)['est'])} 分，不过实际使用没有时限，带时限的题按方案只作参考。",
          "- 4 还是 8：按方案的规则，原题面下 4 就够。后来在两个公开评测集上又跑了 K=4，跑之前写好“两个的质量差区间都整个落在 ±5 分以内才降到 4”；评测集填表题没做到，所以保持 8。", "")
    d.p("**上限之外的三个问题**")
    d.add(f"- 复核（代码写完以后，模型再派一批 subagent 检查、补测试）：大型编码题上占六成费用、三分之二时间，只多修好最后 1–{xl['failed_max']['W-N-D1-K8']} 个测试。",
          f"- 题面要求把 subagent 查到的都写进报告：多写对 {rnd(lg['keep_done']['est'])} 个百分点（区间含 0），但 {wfl['runs'] // 4} 次里有 {wfl['early']} 次主 agent 没等 subagent 做完就结束。",
          f"- 上限不告诉模型，调用被拒绝了才知道：默认设置下，办公报告题每次运行开成 {rnd(made8)} 个 subagent，另有 {rnd(dep_rej)} 次调用被深度上限拒绝（subagent 想再往下开）。这些调用本身花的钱不到模型费的 3%"
          + (f"。把 K 写进工具说明以后（细节{SEC['k']}）：{told_concl}" if TD else "；对质量的影响没有测。"), "")
    d.p("**适用条件**")
    d.add(told_scope if TD else "- K 的结论只对现在的实现成立：工具说明里不写上限，超出上限的那次调用被拒绝。",
          f"- 不限时、用测试或标准答案判分的四种任务得分都接近满分（去掉 {sum(v['low'] for v in low_runs.values())} 次没做完的运行，同一批里各组的平均分最多差 {rnd(near_spread)} 分），只比得出费用和时间；办公报告题只有两道；一个模型、一个 DSH 版本、命令行一次性运行。", "")
    d.add("**建议**", "",
          "1. 深度保持 1，K 保持 8。",
          "2. 想把 K 降到 4 省钱，先补两样：评测集填表题上 K=4 的质量（现在区间上端超出范围）；复核留不留（留着时 K=4 的时间没测出差别，去掉以后慢两成）。",
          "3. 换一种第一遍错得多的任务看复核值不值；原题面里“判分会用更完整的测试”一句可能引出复核，去掉再测。",
          "4. 改两处 DSH 的行为：命令行一次性运行时让进程等 subagent 做完再退出；" + (told_adv_tail if TD else "把上限告诉模型，或者到了上限就不再给它开 subagent 的工具。"), "")

    # ============================================================================== what was done, in one place
    d.add("### 实验一览", "")
    d.add("- DSH（DeepSeek Harness）里，主 agent 可以把一部分活交给 subagent；subagent 在后台运行，做完把结果作为一条消息送回上级。",
          "- 两个上限。深度上限 D：subagent 还能不能再往下开 subagent；D=0 是连主 agent 也不给开 subagent 的工具，下文叫“不开 subagent”，也叫单 agent。同时存活上限 K：同一时刻最多有几个 subagent 没结束，各层合在一起数。"
          "模型事先看不到这两个数，超出上限的那次调用会被拒绝。" + (f"另有一批把 K 写进了工具说明，看告知以后有没有变化（细节{SEC['k']}）。" if TD else ""),
          f"- 比什么。九种任务上一共跑了约 {round(iss['all_runs'], -2):,} 次；每个设置和默认（D=1、K=8）比三样：质量、一次任务的费用（元；联网任务含搜索费）、用户等的时间（从开始到主 agent 给出最终回答）。主要的对比每次只改一个上限。",
          "- 怎么配对。实验分批做，一个设置只和同一批里的对照组比（多数是默认设置；题面加了并行提示或不复核提示的各组，对照的是同样加提示的深度 1、K=8）。同一道题的同一次重复，两个设置各有一次运行，配成一对算差；下文的“20 对”“40 对”指这个。",
          "- 进程等不等 subagent。命令行一次性运行时，主 agent 给出最终回答，进程就退出，不管 subagent 是不是还在运行。一部分批次给进程打了补丁，让它等 subagent 做完再退出，下文叫“进程等 subagent”。", "")
    scr = ws["screen"]
    per_test = st.mean((100 - xm[g_]["score"]) / xl["failed"][g_] for g_ in ("D0", "W-D1-K4", "W-N-D1-K8"))  # score points one failed hidden test costs on the big coding task
    assert 0.015 < per_test < 0.022 and all(xl["failed"][g_] > 0 for g_ in ("D0", "W-D1-K4", "W-N-D1-K8"))
    d.tbl("tasks", "九种任务。第二列是下文用的名字；质量的满分都是 100。调研类就是背景里说的办公任务：联网查资料，写报告或填表。", [
        ["类", "下文的叫法", "做什么", "质量怎么算", "每种设置跑几次"],
        ["调研类", "办公报告题", "联网调研后写一份长报告，2 道，取自背景里的用户日志 A、C：新加坡 4 天自由行攻略（下文叫旅行攻略题）；鲲鹏 920、海光 7000、飞腾 S5000C 三款服务器 CPU 的选型对比（下文叫 CPU 选型题）",
         "对照事实清单逐条核对，报告写对了其中百分之几（写对的事实占比）。清单两题共 195 条（下文叫全清单）：63 条是任何运行之前定下的，132 条是看过第一批报告以后补的。结论以事先定下的 63 条为准，全清单的数并排给",
         f"每题 10 或 20 次；正文的数多数出自每题 {m['D1-K8']['n'] // 2} 次的主要一批（{m['D1-K8']['n']} 对）"],
        ["", "评测集填表题", f"联网收集信息，填一张指定列的表；公开评测集 WideSearch 的 {scr['picked']} 道中文题", "和标准答案逐格比对的得分（逐项 F1）", "每题 1 次"],
        ["", "评测集报告题", f"联网调研，按题面要求写报告；公开评测集 DeepResearch Bench II 的 {drb['tasks']} 道中文题", "评测集自带的评分项满足了百分之几", "每题 1 次"],
        ["代码类", "读代码题", "不联网，读 DSH 源码，2 道：回答“subagent 的两个上限在哪里实现”（问答题）；写一个记忆溯源插件的实现方案（写方案题，取自用户日志 B）", "问答题按要点、写方案题按评分表，由判分模型打分", "每题 10 次"],
        ["", "小编程题", "4 道 Python 练习，一次运行做完 4 道", "各题隐藏测试通过比例的平均", "10 次"],
        ["", "限时 24 题", "24 道互不相关的 Python 小题，限时 3 分钟；特意设计成适合分给几个 subagent 同时做", "到时间为止，各题隐藏测试通过比例的平均", "10 次"],
        ["", "16 步串行题", "16 步数据处理，后一步的题目要靠前一步的答案才找得到；特意设计成没法同时做", "和标准答案对", "10 次"],
        ["", "不限时 24 题", "同样 24 道小题，不限时", "各题隐藏测试通过比例的平均", "10–20 次"],
        ["", "大型编码题", "按规格写一个 Python 包：48 个模块、61 个文件", f"{xl['tests']:,} 个隐藏测试，各测试文件通过比例的平均（少过 1 个测试约少 {per_test:.2f} 分，所以这道题同时给没通过的测试个数）", "10 次"]])
    d.p("有些组在题面末尾另加了一句提示，下文用这四个名字；不加提示的叫“原题面”：")
    d.add(f"- 并行提示：“{ENCOURAGE}”用来让模型多开一些 subagent，上限才有机会起作用。",
          "- 不复核提示：要求文件都写完以后不要再另开 subagent 去复核（检查、验证、补测试），需要检查就自己检查。只用在大型编码题；原题面下模型写完会再派一批 subagent 复核。",
          f"- 多查提示：“{SEARCHMORE}”加在不开 subagent 的组上，让一个 agent 自己多查。一共三种，按要求的搜索次数和网页数叫多查 100/100、多查 150/250、多查 250/500。只用在办公报告题。",
          f"- 都写进去提示：“{KEEPALL}”只用在办公报告题。", "")
    d.p("另外，小编程题、两道 24 题和大型编码题的原题面里本来就有一句“给的只是部分测试，判分会用更完整的测试，所以要按规格写对”。")
    d.p("**图表里的判断用词。** 每个差或倍数都带 95% 区间，判断分四种：")
    d.add("- 显著（正文也说“测得出”）：区间不含 0（倍数是不含 1）；事前写定要一起看的几个对比，按 Holm 方法一起校正以后仍然成立。",
          "- 校正后不显著：单看区间不含 0，一起校正以后不成立。",
          "- 没有差别：区间含 0，并且整个落在 ±5 分（办公报告题是 ±8 个百分点）以内。只有质量分这一类。",
          "- 没测出差别：区间含 0，但比上面的范围宽。可能有差别，这些次数分不出来。",
          "- 图例和表里的“不显著”是后三种的合称。", "")

    # ================================================================================== how a value is judged
    d.add("### 怎么判断一个取值", "")
    d.p("两个上限是不分任务类型的全局设置，所以每个取值都和现在的默认比，分三步：")
    d.add(f"1. 交付：交出完整结果的比例不低于默认，退出时不出错（各设置的数在细节{SEC['deliver']}）。",
          "2. 质量和用户等的时间不比默认差。",
          "3. 满足前两步的取值里取最小的，也就是最省钱的。", "")
    d.p("第 2、3 步沿用 10 月 3 日写进方案的定 K 的规则。那条规则写的时候一部分结果已经看过，门槛按任务各不相同。第 1 步是这一版加的。"
        "K 另有一条在数据之前写定的读法，是补测 K=4 之前写的，“保持 8”按的是它（见{tab:k-rule} 下面）。"
        "深度没有一条跨任务的取值规则；各批事前写过自己的读法，没有一条给出放开。{tab:d-rule} 把深度也按这三步排一遍，是事后的做法。"
        "各条读法是什么时候写的、写的时候看过哪些结果、按它得到什么，列在附录的{tab:k-readings}（K）和{tab:d-readings}（深度）。")
    d.p(f"门槛有三种。一种是“区间不整个在差的一边”，区间很宽的对比也过得去；一种是“区间下限高于 −5 分（大型编码题是 −1 分）”，小而显著的下降过得去；一种只看估计值、不看区间（大型编码题的时间：倍数不超过 1.15），原题面下 K=4 的时间是 {xci(kq('xl', 4, 't'))}，靠这一种满足。三种都不等于没有损失，所以两张表把“没有差别”和“没测出差别”分开写。")
    d.p(f"多大的差算一样，用的是“没有差别”的范围。参照：办公报告题上 K=64 和 K=8 两组里，K 都没有拒绝过一次调用，开的 subagent 一样多，等于同一种设置跑了两遍，"
        f"{o['k64']['right_pct']['n']} 对的写对占比仍差 {rnd(abs(lg['k64']['est']))} 个百分点（全清单差 {rnd(abs(o['k64']['right_pct']['est']))}）。")

    # ======================================================================================== K, value by value
    d.add("### K 取不同值的结果", "")
    d.figure("k-quality", f"{NEW}/k-quality.png", "K 取不同值时的质量：比同一批里的 K=8 高或低多少（深度上限都是 1）。每格一种任务，办公报告题占两格（事先定下的 63 条、全清单）；点是估计值，竖线是 95% 区间，没有点的取值没有测。"
             "浅绿色的带是“没有差别”的范围。实心点是显著；空心点是不显著，包括区间不含 0、但和同批的几个对比一起校正以后不成立的。"
             "读代码题和限时 24 题的各组题面都加了并行提示（不加的话模型开得少，K 起不了作用），对照的 K=8 组也加；读代码题画的是深度 1 的各组，定 K 的规则用的三个深度合起来的对比在细节" + SEC["k"] + "。"
             "限时 24 题带时限，按方案只作参考。不限时 24 题和大型编码题各组得分都接近满分，没有画，数在附录的{tab:limits-ci}。")
    d.figure("k-cost", f"{NEW}/k-cost.png", "K 取不同值时一次任务的费用：是同一批里 K=8 的几倍（纵轴是对数刻度）。办公报告题和两个公开评测集的费用含搜索费，其余是模型费。大型编码题分原题面和加不复核提示两套，各自和同一套里的 K=8 比。")
    d.figure("k-time", f"{NEW}/k-time.png", "K 取不同值时用户等的时间：是同一批里 K=8 的几倍（纵轴是对数刻度）。限时 24 题限时 3 分钟，不比时间。")
    ke = lambda v: rel_k[v]["early"]  # noqa: E731
    assert all(rel_k[v]["early"] is not None for v in rel_k) and rel_k[1]["incomplete"] == 1 and all(rel_k[v]["incomplete"] == 0 for v in (2, 4, 8))
    k1c = sorted(r["cells"][1]["c"]["est"] for r in L["k"] if 1 in r["cells"])
    k2c_ = sorted(r["cells"][2]["c"]["est"] for r in L["k"] if 2 in r["cells"])
    assert all(ce.strong(r["cells"][v]["c"], r["cells"][v]["corr"][1]) for r in L["k"] for v in (1, 2) if v in r["cells"])
    assert not any(ce.strong(r["cells"][4][m_], r["cells"][4]["corr"]["qct".index(m_)]) for r in L["k"] if 4 in r["cells"] and r["key"] not in ("xl", "xln") for m_ in "qct" if r["cells"][4][m_] is not None)
    assert verdict(leg["D1-K4"], 8, True) == verdict(dk4_, 5, True) == verdict(kq("free", 4), 5, True) == "没有差别"
    assert verdict(wk4, 5, True) == verdict(kq("code", 4), 5, True) == verdict(kq("wide", 4), 5, True) == "没测出差别"
    assert ce.strong(kq("wide", 1), True) and not ce.strong(kq("wide", 2), True) and kq("wide", 2)["hi"] < 0 and ce.strong(kq("xln", 4, "t"), True) and not ce.strong(kq("xl", 4, "t"))
    assert ce.strong(kq("free", 1), True) and kq("free", 1)["lo"] > -5 and kq("xl", 4)["hi"] < 0 and kq("xl", 4)["lo"] > -1 and verdict(lg["k64"], 8) == "没有差别"
    assert verdict(o["k64"]["right_pct"], 8, True) == "校正后不显著" and all(orig_oom >= 3 for orig_oom in (E["xl_groups"][f"main:W-D1-K{v}"]["oom_runs"] for v in (4, 8, 16)))
    x64 = cd.contrast(cd.R("results/analysis-xl-depth/rows-all.csv"), "W-N-D1-K64", "W-N-D1-K16", lambda r_: cd.num(r_["answer_s"]), "ratio")  # the large coding task: K = 64 has no K = 8 in its batch
    assert x64["lo"] < 1 < x64["hi"] and x64["n"] == 10
    rel16 = [q for q in RL if q["col"] == "1-16"]
    rel64 = [q for q in RL if q["col"] == "1-64"]
    assert sum(q["crash"] for q in rel16 + rel64) == 0 and {q["task"] for q in rel16} == {"wide", "free", "xl"} and {q["task"] for q in rel64} == {"office", "free", "xl"} and all(q["waits"] for q in rel16 + rel64)
    d.tbl("k-rule", "K 的每个取值按上面三步看下来的结果（都和同批的 K=8 比，深度上限都是 1）。交付一列，K=1、2、4、8 是办公报告题、进程不等 subagent 的各批：有没有退出时崩溃，以及主 agent 结束时还有 subagent 没做完（表里叫提前结束）的运行数。"
          "办公报告题的质量按事先定下的 63 条。读代码题另给“三个深度合起来”的对比：第一批在深度上限 1、2、3 下各跑了一套 K=1、2、4、8（都加并行提示），三套里 K 对 K=8 的差取平均；定 K 的规则用的是它。各任务的估计值和区间在三张图和附录的{tab:limits-ci}。", [
        ["K", "交付", "质量", "用户等的时间", "费用", "按方案的规则"],
        ["1", f"没有退出时崩溃；提前结束 {ke(1)}/{rel_k[1]['runs']}，1 次报告不完整",
         f"显著变差：限时 24 题 {sg(kq('wide', 1)['est'])} 分（带时限，按方案只作参考）；读代码题三个深度合起来 {sg(fk1['est'])} 分（只看深度 1 是 {sg(kq('code', 1)['est'])}，没测出差别）。办公报告题 {sg(leg['D1-K1']['est'])} 个百分点，没测出差别。两个公开评测集没有差别。"
         f"不限时 24 题 {sg(kq('free', 1)['est'])} 分，显著，在方案的 −5 分门槛以内",
         f"大型编码题（加不复核提示）{rnd(kq('xln', 1, 't')['est'], 2)} 倍，显著", f"{rnd(k1c[0], 2)}–{rnd(k1c[-1], 2)} 倍，都显著", f"不满足（读代码题的质量；办公报告题第一批的评分表总分 {ci(rb['H2a'])}，下限低于 −5 分；大型编码题的时间）"],
        ["2", f"没有退出时崩溃；提前结束 {ke(2)}/{rel_k[2]['runs']}",
         f"没有显著的。读代码题三个深度合起来 {sg(fk2['est'])} 分，校正后不显著（规则的门槛不做校正，按它算不满足）；只看深度 1 是 {sg(kq('code', 2)['est'])}，没测出差别。"
         f"限时 24 题 {sg(kq('wide', 2)['est'])} 分，校正后不显著。办公报告题 {sg(leg['D1-K2']['est'])} 个百分点，没测出差别",
         f"大型编码题（加不复核提示）{rnd(kq('xln', 2, 't')['est'], 2)} 倍，显著", f"{rnd(k2c_[0], 2)}–{rnd(k2c_[-1], 2)} 倍，都显著", "不满足（读代码题的质量，大型编码题的时间）"],
        ["4", f"没有退出时崩溃；提前结束 {ke(4)}/{rel_k[4]['runs']}",
         f"没有差别：办公报告题、评测集报告题、不限时 24 题、读代码题三个深度合起来（{sg(fk4['est'])}；只看深度 1 是 {ci(kq('code', 4))}，没测出差别）。"
         f"没测出差别：评测集填表题 {ci(wk4)}（超出范围的是上端）、限时 24 题 {ci(kq('wide', 4))}（{kq('wide', 4)['n']} 对；带时限，只作参考）。"
         f"大型编码题原题面 {sg(kq('xl', 4)['est'], 2)} 分（平均多留 {rnd(k4_tests)} 个没通过的测试），区间不含 0，在方案的 −1 分门槛以内",
         f"大型编码题加不复核提示 {rnd(kq('xln', 4, 't')['est'], 2)} 倍，显著；原题面 {rnd(kq('xl', 4, 't')['est'], 2)} 倍，没测出差别（这几组里三到六成的运行有进程因内存不够被杀，时间的比较受影响，见细节{SEC['deliver']}）；其余不显著",
         f"大型编码题 {rnd(kq('xl', 4, 'c')['est'], 2)} 倍（原题面）、{rnd(kq('xln', 4, 'c')['est'], 2)} 倍（加不复核提示），显著；不限时 24 题 {rnd(kq('free', 4, 'c')['est'], 2)} 倍，校正后不显著；调研类不显著",
         "原题面下满足，是满足的取值里最小的（补测的读法见表下）；加不复核提示时不满足（时间）"],
        ["8（默认）", f"没有退出时崩溃；提前结束 {ke(8)}/{rel_k[8]['runs']}", "—", "—", "—", "对照"],
        ["16", "没有退出时崩溃（限时 24 题、不限时 24 题、大型编码题）", "没有差别（限时 24 题、不限时 24 题；大型编码题都接近满分）", "不显著，没测出更快", "不显著", "没测出好处，不调大"],
        ["64", "没有退出时崩溃（办公报告题、不限时 24 题、大型编码题，进程都等 subagent）",
         f"没有差别：办公报告题 {sg(lg['k64']['est'])} 个百分点（全清单 {sg(o['k64']['right_pct']['est'])}，校正后不显著）、不限时 24 题；大型编码题都接近满分", f"办公报告题、不限时 24 题不显著；大型编码题上只和同批的 K=16 比过（{x(x64)}，区间含 1）", "不显著", "没测出好处，不调大"]])
    assert verdict(kq("wide", 16), 5, True) == verdict(kq("free", 16), 5, True) == verdict(kq("free", 64), 5, True) == "没有差别" and all(abs(kq(k_, 16)["est"]) < 0.05 for k_ in ("xl", "xln"))
    d.add(f"- 按写进方案的规则（各条读法在附录的{{tab:k-readings}}）：10 月 3 日的三条给出 4；10 月 4 日为大型编码题补的两条，原题面下给出 4，题面加不复核提示时给出 8（这时 K=4 要等的时间是 {rnd(kq('xln', 4, 't')['est'], 2)} 倍）。",
          f"- 后来在两个公开评测集上加跑了 K=4（下文叫补测）。加跑之前写定的读法是：两个评测集都是“没有差别”才降到 4，有一个“没测出差别”就保持 8。结果评测集报告题没有差别（{ci(dk4_)}）；"
          f"评测集填表题没测出差别（{ci(wk4)}，{wk4['n']} 对；把 {p['wsk']['flagged']} 次不计分的运行也算上是 {ci(wk4all)}）。按这条读法，保持 8。",
          f"- 所以建议保持 8。深度 1 下，4 和 8 之间显著的差别都在大型编码题上：K=4 更便宜，不复核时更慢，原题面下得分低 {rnd(-kq('xl', 4)['est'], 2)} 分（各组都接近满分）。", "")

    # ==================================================================================== depth, value by value
    d.add("### 深度取不同值的结果", "")
    d.figure("d-quality", f"{NEW}/depth-quality.png", "深度上限取不同值时的质量：比同一批里的深度 1 高或低多少（K 都是 8）。“不开”是不给开 subagent 的工具，由一个 agent 自己做。每格一种任务，办公报告题占两格；读法同{fig:k-quality}。"
             "办公报告题的深度 2、3 是几批合起来的数。两道 24 题的深度 2 只在题面加并行提示时测过，没有画，见细节" + SEC["depth"] + "。限时 24 题带时限，按方案只作参考。小编程题、16 步串行题、不限时 24 题和大型编码题各组得分都接近满分，没有画。")
    d.figure("d-cost", f"{NEW}/depth-cost.png", "深度上限取不同值时一次任务的费用：是同一批里深度 1 的几倍（纵轴是对数刻度）。办公报告题和两个公开评测集的费用含搜索费，其余是模型费。小编程题和 16 步串行题上模型在深度 1 时自己不开 subagent。")
    d.figure("d-time", f"{NEW}/depth-time.png", "深度上限取不同值时用户等的时间：是同一批里深度 1 的几倍（纵轴是对数刻度）。大型编码题两格里的“不开”是同一组运行，分别和原题面的默认、加不复核提示的默认比，所以两个倍数不一样。限时 24 题不比时间。")
    assert ce.strong(dq("office", 0, "t")) and dq("office", 0, "t")["est"] < 1 and all(not ce.strong(dq(k_, 0, "t"), LD[k_]["cells"][0]["corr"][2]) for k_ in ("ws", "drb2"))
    assert ce.strong(dq("drb2", 0), LD["drb2"]["cells"][0]["corr"][0]) and ce.strong(dq("wide", 0)) and verdict(dq("ws", 0), 5, True) == "没测出差别"
    d2c = {k_: dq(k_, 2, "c") for k_ in ("office", "drb2", "code")}
    assert all(ce.strong(d2c[k_], LD[k_]["cells"][2]["corr"][1]) for k_ in d2c) and not any(ce.strong(dq(k_, 2, "c"), LD[k_]["cells"][2]["corr"][1]) and dq(k_, 2, "c")["est"] > 1 for k_ in ("ws", "p4", "xl", "xln"))
    d3c = {k_: dq(k_, 3, "c") for k_ in ("office", "code", "p4")}
    assert verdict(dq("ws", 2), 5) == verdict(dq("code", 2), 5) == verdict(dq("code", 3), 5) == "没测出差别" and verdict(dq("drb2", 2), 5) == "没有差别" and ce.strong(dq("free", 2), True) and dq("free", 2)["est"] < 0.5
    assert ce.strong(dq("p4", 3, "t")) and not ce.strong(dq("code", 3, "t")) and dq("xl", 0)["hi"] < 0 and abs(dq("xl", 0)["est"]) < 0.1
    assert all(ce.strong(v) for v in d3c.values()) and ce.strong(dq("office", 3, "t")) and rel_d2["crash"] == 28 and rel_d3["crash"] == 13
    d.tbl("d-rule", "深度上限的每个取值按同样的三步看下来的结果（都和同批的深度 1 比，K 都是 8）。深度没有一条跨任务的取值规则，这一张是事后按三步排的；各批事前写过的读法和结果在附录的{tab:d-readings}。交付一列是办公报告题、进程不等 subagent 的各批。"
          "办公报告题的质量按事先定下的 63 条。各任务的估计值和区间在三张图和附录的{tab:limits-ci-d}。", [
        ["深度", "交付", "质量", "用户等的时间", "费用", "按同样的三步"],
        ["不开 subagent", "没有退出时崩溃",
         f"显著变差：办公报告题 {sg(-h1leg['est'])} 个百分点、评测集报告题 {sg(-dt['est'])} 分、限时 24 题 {sg(dq('wide', 0)['est'])} 分（带时限，按方案只作参考）。评测集填表题 {sg(dq('ws', 0)['est'])} 分，没测出差别。"
         f"大型编码题 {sg(dq('xl', 0)['est'], 2)} 分（少通过 {rnd(tests_more, 0)} 个测试），区间不含 0，各组都接近满分",
         f"调研类不显著或更快（办公报告题 {rnd(dq('office', 0, 't')['est'], 2)} 倍，显著）；大型编码题和加不复核提示的默认比是 {rnd(dq('xln', 0, 't')['est'], 2)} 倍，显著",
         f"调研类 {rnd(cheap3[0], 2)}–{rnd(cheap3[-1], 2)} 倍；模型会开 subagent 的代码类任务 {rnd(cheapc[0], 2)}–{rnd(cheapc[-1], 2)} 倍", "不满足（质量）"],
        ["1（默认）", f"没有退出时崩溃；提前结束 {ke(8)}/{rel_k[8]['runs']}", "—", "—", "—", "对照"],
        ["2", f"{rel_d2['runs']} 次里 {rel_d2['crash']} 次退出时崩溃",
         f"没有差别：办公报告题 {sg(p2leg['est'])} 个百分点（全清单 {sg(p2k8['est'])}，显著）、评测集报告题。没测出差别：评测集填表题、读代码题。不限时 24 题 {sg(dq('free', 2)['est'])} 分，显著（加并行提示的各组，都接近满分）",
         f"办公报告题 {rnd(dq('office', 2, 't')['est'], 2)} 倍、读代码题 {rnd(dq('code', 2, 't')['est'], 2)} 倍、大型编码题（加不复核提示）{rnd(dq('xln', 2, 't')['est'], 2)} 倍，都只是刚好显著（区间下端 1.01）",
         f"办公报告题 {rnd(d2c['office']['est'], 2)} 倍、评测集报告题 {rnd(d2c['drb2']['est'], 2)} 倍、读代码题 {rnd(d2c['code']['est'], 2)} 倍，显著；其余任务没有显著变贵", "不满足（交付、时间），也更贵"],
        ["3", f"{rel_d3['runs']} 次里 {rel_d3['crash']} 次退出时崩溃",
         f"没有差别：办公报告题 {sg(p3leg_['est'])} 个百分点。没测出差别：读代码题",
         f"办公报告题 {rnd(dq('office', 3, 't')['est'], 2)} 倍、小编程题 {rnd(dq('p4', 3, 't')['est'], 2)} 倍，显著",
         f"办公报告题 {rnd(d3c['office']['est'], 2)} 倍、读代码题 {rnd(d3c['code']['est'], 2)} 倍、小编程题 {rnd(d3c['p4']['est'], 2)} 倍，显著", "不满足（交付、时间），也更贵"]])
    d.add(f"- 进程等 subagent 做完再退出时，深度 2、3 的崩溃少得多：{rel_w[2]['runs'] + rel_w[3]['runs']} 次里 {rel_w[2]['crash'] + rel_w[3]['crash']} 次；另有 {rel_w[2]['wait_cap'] + rel_w[3]['wait_cap']} 次等了 20 分钟还有 subagent 没结束。",
          f"- 深度 3、K=64 相当于旧默认：费用是现在的 {rnd(od['cost']['est'])} 倍，一次任务中位 {ck['old']['median']:.0f} 元、最高 {ck['old']['max']:.0f} 元（现在的默认中位 {ck['default']['median']:.0f} 元、最高 {ck['default']['max']:.0f} 元），"
          f"写对的事实占比没有差别（{sg(lg['old']['est'])} 个百分点）。", "")

    # ================================================================================================== method
    d.add("## 实验怎么做的", "")
    d.p("九种任务、四种提示和判断用词见结论里的“实验一览”（{tab:tasks}）。下文还用到两个合称：两个公开评测集指评测集填表题和评测集报告题；对照题指限时 24 题和 16 步串行题，一道特意适合分给几个 subagent 同时做，一道特意没法同时做。")
    d.add("### 运行环境和 subagent 的机制", "")
    th = cd.J("results/analysis-mechanism/tools-in-header.json")  # what a subagent is given, from the session headers (scripts/tools_in_header.py)
    tl = th["tool_lists"]
    assert all(len(tl[k_]) == 1 for k_ in tl) and tl["with/root"] == tl["with/child"] and th["configs"]["with/root"] == th["configs"]["with/child"] == th["configs"]["without/root"]
    assert th["child_prompt_is_root_prompt"] == th["runs_with_children"] > 40 and th["sessions"]["with/child"] > 150
    TOOLS_ALL, TOOLS_NONE, TOOLS_NOWEB = len(tl["with/root"][0]), len(tl["without/root"][0]), len(tl["noweb-with/root"][0])
    hosts_ = {b_: set(re.findall(r"https?://([A-Za-z0-9.\-]+)", json.dumps(cd.J(f"results/runs/{b_}/batch.json")))) for b_ in ("office-v2", "calib-official-code")}
    assert "api-internal.deepseek.com" in hosts_["office-v2"] and "api.deepseek.com" not in hosts_["office-v2"] and "api.deepseek.com" in hosts_["calib-official-code"] and "api-internal.deepseek.com" not in hosts_["calib-official-code"]
    assert th["source"] == "results/runs/office-v2, results/runs/calib-official-code" and th["sessions"]["with/root"] + th["sessions"]["without/root"] == 60
    assert tl["noweb-with/root"] == tl["noweb-with/child"] and TOOLS_NOWEB == TOOLS_ALL - 2 and len(tl["noweb-without/root"][0]) == TOOLS_NONE - 2
    assert set(tl["with/root"][0]) - set(tl["noweb-with/root"][0]) == {"web_search", "web_fetch"}
    assert set(tl["with/root"][0]) - set(tl["without/root"][0]) == {"subagent", "subagent_fork", "send_message", "list_agents", "interrupt_agent"} and TOOLS_ALL == 23
    conf = cd.R("results/analysis-office-confirm/rows-all.csv")
    calls_d = st.mean(cd.num(r["web_search_calls"]) for r in conf if r["group"] == "D1-K8")
    reqs_d = st.mean(cd.num(r["search_aux"]) for r in conf if r["group"] == "D1-K8")
    assert 70 < calls_d < 80 and 230 < reqs_d < 245
    d.add("- **环境。** 模型是内部端点的 v41flash，推理强度 max（最高一档）；DSH 版本 0.2.0-rc.2。每次运行在一个独立容器里（4 核 16 GB），用命令行一次性运行：一条指令做到底，中间没有人回复。单次运行有时间上限（多数批是 60 分钟，最长的几批 90 分钟）。",
          "- **subagent 怎么运行。** 主 agent 调用开 subagent 的工具，subagent 在后台做，做完把结果作为一条消息送回上级；上级这时可以接着干别的，也可以再开。"
          "开 subagent 的工具有两个：名叫 subagent 的那个新开一个空的上下文，任务说明要写全；名叫 subagent_fork 的那个让 subagent 带着主 agent 到这时为止的对话。这里不区分，都算 subagent。"
          f"全部运行里这两个工具一共被调用 {m_calls:,} 次，其中 subagent_fork 只有 {mtl['subagent_fork']} 次。"
          f"subagent 用的模型、推理强度、系统提示和工具都和主 agent 一样：联网的任务里是 {TOOLS_ALL} 个工具（不联网的任务少两个联网工具，{TOOLS_NOWEB} 个），其中 {TOOLS_ALL - TOOLS_NONE} 个是管 subagent 的（开的两个，加上给它发消息、查看、打断各一个）。"
          f"不开 subagent 的组是把这 {TOOLS_ALL - TOOLS_NONE} 个都拿掉。这几个数是从本机试跑的日志里读的：同一版 DSH，配置文件和正式实验的相同（逐个比过哈希）；联网的 {th['sessions']['with/root'] + th['sessions']['without/root']} 次走内部端点，不联网的只有 {th['sessions']['noweb-with/root'] + th['sessions']['noweb-without/root']} 次、走官网接口。"
          "DSH 另有一个编排多个 agent 的 workflow 工具，它开的 agent 不受 K 限制，各组都关掉了。",
          f"- **两个上限怎么起作用。** K 数的是整棵树上同一时刻没结束的后台 subagent，各层共用。模型还可以开一种做完才返回、不占 K 的前台 subagent，这次几乎没用到（全部 {iss['all_runs']:,} 次运行开成的 {mtl['children']:,} 个 subagent 里，这样开成的只有 7 个；这样发出的调用是 {mtl['foreground']} 次）。"
          "工具说明里不写这两个上限；到了深度上限的 subagent，工具列表里仍然有开 subagent 的工具。超出上限的那次调用返回一条错误，错误消息里写了上限是几"
          "（K=2 时被 K 拒绝的那条是“subagent limit reached (active child limit: 2); wait for an existing child to finish or complete this work with the current agents”），模型到这时才知道上限。",
          "- **进程等不等 subagent。** 命令行一次性运行时，主 agent 给出最终回答，进程就退出，不管 subagent 是不是还在运行（DSH 缺陷第 4 条）。第一批、办公报告题主要的一批和多查的两批照这个原样跑。"
          "其余各批给进程打了补丁：主 agent 这一轮结束时如果还有 subagent 没结束，就等它们结束、主 agent 把送回来的结果处理完再退出（最多空等 20 分钟）。每一批是哪种跑法见附录的{tab:batches}，两种跑法的组不配在一起比。",
          f"- **搜索。** DSH 的搜索工具背后没有专门的搜索接口。模型调一次搜索工具可以带几个查询词，每个查询词由搜索插件向模型接口另发一个带联网搜索的请求（下文的“搜索请求”），取回搜索结果。"
          f"办公报告题默认设置下一次运行平均调 {calls_d:.0f} 次搜索工具、发 {reqs_d:.0f} 个搜索请求。多查提示里说的“网页搜索”模型是按工具调用还是按查询词来数，没有查；下文的搜索量都按搜索请求数。",
          "- **几份报告合并。** 同一道题先让几个单 agent 各自独立写一份报告（互不通信），再起一次不开 subagent 的运行，题面加一段话，让它把这几份合并成一份：有来源的事实都保留，重复的只写一次，说法不一致的重新核实。"
          "费用算全部这几次运行的总和；时间按几份同时写、写完再合并算。",
          "- **判分。** 事实清单、评分表和两个公开评测集由 Opus 5.5 判分，判分时看不到是哪一组；小编程题、两道 24 题和大型编码题用隐藏测试，16 步串行题对标准答案。各题的题面原文、两份事实清单和评分标准原文在本页最后三节（打分机制、题目、评分标准）。", "")
    chain_s = [cd.num(r_["seconds"]) for r_ in cd.R("results/analysis-ctl/rows.csv") if r_["task"] == "n1-chain16"]  # the serial task: its prompt names a limit of ten minutes
    assert len(chain_s) == 30 and max(chain_s) < 150 and "限时 10 分钟" in (EXP / "tasks/control-tasks.jsonl").read_text(encoding="utf-8")
    d.add("### 测了哪些取值", "")
    d.add("- 深度上限 D：0（不开 subagent）、1、2、3。",
          "- 同时存活上限 K：1、2、4、8；办公报告题另测了 64，限时 24 题另测了 16，不限时 24 题和大型编码题另测了 16、64。",
          "- 读代码题、限时 24 题和不限时 24 题上，换 K 和深度的各组题面都加了并行提示（让模型多开一些，上限才有机会起作用），和同样加了并行提示的深度 1、K=8 的组比。"
          "读代码题和小编程题另有原题面的深度 2、3 两组（K=8）。大型编码题的各组分原题面和加不复核提示两套，各自和同一套里的 K=8 比。",
          f"- 评测集填表题的选法：WideSearch 的 {scr['runs']} 道中文题先不开 subagent 各做一次，{scr['top']} 道做到 90 分以上（已经到顶，比不出差别），{scr['named']} 道模型在搜索时认出了评测集，用的是剩下的 {scr['picked']} 道。",
          "- 限时 24 题带时限，对照题批和限时 24 题批里都是。方案 10 月 3 日 17:20Z 写明（这时对照题批的结果已经看过，限时 24 题批的统计还没有出）：实际使用没有时限，带时限的结果只作参考，开 subagent 快不快、K 和深度的作用以不限时 24 题为准。"
          "这份报告仍然给出限时 3 分钟一版的结果；正文的任务表里标了“只作参考”，各处的限时 24 题都按这一条读。另有限时 2 分钟的一版，波动很大，只在后面的分任务结果里给。",
          f"- 16 步串行题的题面也写着限时 10 分钟；{len(chain_s)} 次运行都在 {min(chain_s):.0f}–{max(chain_s):.0f} 秒做完，没有一次到时限，下文把它算作不限时的任务。", "")
    cv = E["coverage"]
    mu_n = E["merge_union"]["M2"]["n"] + E["merge_union"]["M4"]["n"]
    assert mu_n == 60
    cell = lambda r_, c_: cv["cells"].get(f"{r_}|{c_}", 0)  # noqa: E731
    assert cv["total"] == iss["all_runs"] and cv["in_grid"] + sum(cv["extra"].values()) == cv["total"] and cv["extra"] == {"wide120": 110, "screen": scr["runs"]}
    assert all(cell(r_, c_) > 0 for r_ in ("ws", "drb2") for c_ in ("none", "1-1", "1-4", "1-8", "2-8")) and cell("ws", "3-8") == 0 and cell("drb2", "3-8") == 0
    assert all(cell("office", f"{dd}-{kk}") > 0 for dd in (1, 2, 3) for kk in (1, 2, 4, 8, 64)) and cell("office", "1-16") == 0
    d.figure("coverage", f"{NEW}/coverage-grid.png", "每种设置在每个任务上一共跑了多少次：各批、原题面的组和题面加了提示的组都加在一起，所以比{tab:tasks} 里“每种设置跑几次”多；灰格是没测。"
             f"另有评测集填表题选题用的 {cv['extra']['screen']} 次和限时 24 题限时 2 分钟的那一版 {cv['extra']['wide120']} 次没有画进去；"
             f"把几份报告合成一份的 {mu_n} 次合并运行不在这 {cv['total']:,} 次里。")
    d.p("K 和深度在办公报告题上扫得最全。两个公开评测集上测了不开 subagent、K=1、K=4 和深度 2；深度 3 只在办公报告题、读代码题和小编程题上测过。")
    d.add("### 指标和读法", "")
    first = next(r for r in o["h1_reps"] if r["name"] == "formal")
    from scipy import stats as sps

    def mdd(q: dict, df: int | None = None, ratio: bool | None = None) -> float:
        """Smallest difference the contrast could show with 80% power: as paired_stats.py recorded it, or from the
        interval, (t.975 + t.80) x SE with SE = half width / t.975 (the contrasts with a task as the pair)."""
        if q.get("mdd") is not None:
            return q["mdd"]
        df = df or q["n"] - 2  # pairs of two tasks, the task effect removed
        k_ = 1 + sps.t.ppf(0.8, df) / sps.t.ppf(0.975, df)
        if q.get("ratio") if ratio is None else ratio:  # a ratio: half the width on the log scale, back as a factor
            return math.exp((math.log(q["hi"]) - math.log(q["lo"])) / 2 * k_)
        return (q["hi"] - q["lo"]) / 2 * k_
    S_ = ce.stat
    FC, FF, FH, FW, FK, F1 = ("results/analysis-facts-confirm/stats.json", "results/analysis-facts-floor/stats.json", "results/analysis-facts-highk/stats.json",
                              "results/analysis-facts-wait2/stats.json", "results/analysis-facts-keepdepth/stats.json", "results/analysis-facts/stats-facts.json")
    md40 = sorted([mdd(S_(FC, "right_pct", q)) for q in ("K1", "K2", "K4", "H1", "DN")] + [mdd(S_(FF, "right_pct", q)) for q in ("PRIM", "H1")])
    md20 = sorted([mdd(S_(FH, "right_pct", q)) for q in ("H1", "H2", "H3")] + [mdd(S_(FW, "right_pct", q)) for q in ("WD2", "WD3")] + [mdd(S_(FK, "right_pct", "DK"))]
                  + [mdd(S_(F1, "right_pct", q)) for q in ("H1", "H2a", "H2b", "H2c", "H3a", "H3b")])
    md_ws = sorted(mdd(ws["cmp"][q]["f1_item"], ws["cmp"][q]["f1_item"]["n"] - 1) for q in ("H1n", "H1e"))
    md_drb = sorted([mdd(dt, dt["n"] - 1)] + [mdd(kd["cmp"][q]["total"], kd["cmp"][q]["total"]["n"] - 1) for q in ("K1", "D2")])
    md_code = sorted(mdd(c["cmp"][q]["score"]) for q in ("C1", "C3a", "C3c", "C4a", "C4b"))
    # ratios: the comparisons with 40 pairs on the office task, the reading tasks, the research reports ...
    md_ra = sorted([mdd(S_(FC, m_, q)) for m_ in ("total_cost_peak", "seconds") for q in ("K1", "K2", "K4", "H1", "DN")]
                   + [mdd(c["cmp"][q][m_]) for m_ in ("model_cost_peak", "seconds") for q in ("C1", "C3a", "C3c", "C4a", "C4b")]
                   + [mdd(drb["cmp"]["H1"]["total_cost_peak"], dt["n"] - 1, True), mdd(dtm, dt["n"] - 1, True)])
    # ... and the ones with 10 to 20 pairs: table collection, the two code-building tasks, the 20-pair office batches
    md_rb = sorted([mdd(ws["cmp"]["H1n"]["total_cost_peak"], ws["cmp"]["H1n"]["f1_item"]["n"] - 1, True), mdd(wt, ws["cmp"]["H1n"]["f1_item"]["n"] - 1, True)]
                   + [mdd(free["cmp"][q][m_]) for m_ in ("answer_s", "model_cost_peak") for q in ("K1", "K2", "K4", "K16", "K64", "NC")]
                   + [mdd(xl["cmp"][q][m_]) for m_ in ("answer_s", "model_cost_peak") for q in ("NC", "NK4", "NK16", "K1", "K2", "K4", "K16", "DN", "DE")]
                   + [mdd(S_(FH, m_, q)) for m_ in ("total_cost_peak", "answer_s") for q in ("H1", "H2", "H3")])
    assert 4.9 < md40[0] and md40[-1] < 7.3 and 5.3 < md20[0] and 11 < md20[-1] < 12.2 and 4.2 < md_ws[0] and md_ws[-1] < 6 and 3.1 < md_drb[0] and md_drb[-1] < 6
    assert 5.4 < md_code[0] and md_code[-1] < 7.8 and 1.1 < md_ra[0] and md_ra[-1] < 1.4 and 1.1 < md_rb[0] and 1.9 < md_rb[-1] < 2.2 and st.median(md_rb) > 1.3
    rb_typ = [md_rb[len(md_rb) // 4], md_rb[-2]]  # the bulk of them; the largest one is named separately
    conf_hit = {g_: st.mean(cd.num(r["cache_hit_share"]) for r in conf if r["group"] == g_) for g_ in sorted({r["group"] for r in conf})}
    assert len(conf_hit) == 6 and 0.965 < min(conf_hit.values()) < max(conf_hit.values()) < 0.98
    d.add("- **质量**：办公报告题用“写对的事实占比”，即报告里写对的条目数除以清单条目数。结论以事先定下的 63 条为准：后补的 132 条是看过第一批报告以后整理的，"
          "参考的样本多数来自开 subagent 的组，可能偏向这些组，也更难写到（细节" + SEC["trust"] + "）。事前写定的主要对比和校正是按全清单做的，所以办公报告题的各表两套数都给，各带自己的判断；两套读法不一样的地方，正文按 63 条下结论并写明。其余任务用各自的得分（满分 100）。",
          f"- **费用**（元/次）：模型费按这个模型在 DeepSeek 官网的公开高峰价算（每百万 token：没命中缓存的输入 2 元，命中缓存的输入 0.04 元，输出 8 元；空闲时段是一半），命中多少按接口返回的实际用量。"
          f"各组输入里命中缓存的都在 97% 左右（办公报告题主要的一批各组 {100 * min(conf_hit.values()):.1f}%–{100 * max(conf_hit.values()):.1f}%），缓存不造成组间的差别；同一道题同时跑几十次对命中率有没有影响，没有单独量过。"
          f"联网任务再加搜索费，每个搜索请求按抽样实测的 {iss['search_price']:.4f} 元算（搜索请求的用量没有记进会话日志，只能这样估）。不联网的任务只有模型费。",
          "- **时间**：从开始到主 agent 给出最终回答的时间，也就是用户等的时间。",
          "- **对比**：每种设置都和同一批里的默认组比（各批有哪些设置见附录的{tab:batches}）。同一道题的同一次重复，两组各有一次运行，配成一对算差，给 95% 区间。倍数按每一对分别算、再取几何平均。"
          "加了并行提示或不复核提示的各组，对照的是同一批里题面相同的深度 1、K=8 的组。",
          "- **判断**：四种判断用词的定义见前面的“任务、提示和判断用词”。一起做 Holm 校正的，是同一批里事前写定的那一组主要对比（表里带 ★ 的行）：质量、费用、时间各自在这一组里一起校正，把这一组按题拆开重算时也照样校正。"
          "接近满分、配对差多数为 0 的对比（大型编码题的得分），t 区间不可靠，按精确的符号翻转检验判断。不在这一组里的次要对比和事后的对比不校正；例外是读代码题把另一个因素合起来算的五个对比（K=1、2、4 对 K=8 是三个深度合起来，深度 2、3 对深度 1 是四个 K 合起来），它们是事后合并的，在这五个里一起校正。★ 只表示这一行在事前的清单里；清单写明的主要指标多数是质量，不限时 24 题和大型编码题是时间。表里的“判断”一列只说质量之差。",
          f"- **“没有差别”的范围**：±5 分是第一批开跑之前写进方案的。办公报告题的 ±8 个百分点，是在第一批看到开 subagent 的效果（{sg(first['est'])} 个百分点；正文用的 {sg(h1['right_pct']['est'])} 是后来重做的那一批）以后、后面各次对比判分之前定的，"
          "取的是这个效果的一半左右；所以办公报告题上的“没有差别”只说明差别不超过 8 个百分点。",
          f"- **质量上能测出多大的差别**（按 80% 的把握算）：办公报告题 40 对的对比是 {md40[0]:.0f}–{md40[-1]:.0f} 个百分点，只有 20 对的是 {md20[0]:.0f}–{md20[-1]:.0f} 个；"
          f"评测集填表题 {md_ws[0]:.0f}–{md_ws[-1]:.0f} 分，评测集报告题 {md_drb[0]:.0f}–{md_drb[-1]:.0f} 分，读代码题 {md_code[0]:.0f}–{md_code[-1]:.0f} 分。",
          f"- **费用和时间上能测出多大的倍数**：办公报告题 40 对的对比、读代码题和评测集报告题，要差到 {rnd(md_ra[0])}–{rnd(md_ra[-1])} 倍才测得出；"
          f"评测集填表题、不限时 24 题、大型编码题和办公报告题 20 对的对比，多数要差到 {rnd(rb_typ[0])}–{rnd(rb_typ[1])} 倍，最大的一个要 {rnd(md_rb[-1])} 倍。"
          "比这小的差别，“没测出差别”不等于没有；不限时 24 题和大型编码题上的“没测出更快”只说明没有快出三分之一以上。",
          "- **哪些是事前写定的**：每一批的主要对比和读法，都是在读到结果之前写进实验方案的；附录的{tab:score} 列出全部主要对比和结果，表前写明了哪几处不是在开跑之前写的。"
          "“次要对比”是方案里列明、但不进校正的对比；标“事后”的是看到结果以后加的分析，只作描述。", "")

    # ============================================================================================ results by question
    fr = cd.R("results/analysis-v2/rows-office.csv")
    l2 = sum(1 for r in fr if r["group"] in ("D2-K1", "D2-K2") and (cd.num(r.get("children_d2")) or 0) > 0)
    n_l2 = sum(1 for r in fr if r["group"] in ("D2-K1", "D2-K2"))
    assert l2 == 0 and c["c1"]["spawn_runs"] == 0 and c["p4"]["opens"]["open"] == 0 and ch["opens"]["open"] == 0
    d.add("## 结果", "")

    # ---- 1. what one task costs
    d.add(f"### {SEC['cost']}、一次任务花多少钱", "")
    d.p(f"**费用随开的 subagent 数涨；K 和深度改变了开的数量，费用跟着变。开 subagent 既多了搜索费、也多了模型费：单 agent 靠多查提示把搜索请求做到默认的水平时，费用是默认的 {rnd(dc['P150']['total_cost_peak']['est'], 2)} 倍"
        f"（搜索费差不多，模型费不到一半；细节{SEC['spend']}）。开多少个由模型自己和两个上限决定，见细节{SEC['open']}。**")
    pt, cf2 = cst["per_task"], cst["code_fit"]
    web = sorted(pt[q]["slope"] for q in ("office", "ws", "drb2"))
    offline = sorted(pt[q]["slope"] for q in ("code", "p4", "wide", "chain"))
    assert all(1.3 < v < 2.2 for v in web) and all(0.05 < v < 0.65 for v in offline) and 0.45 < fitc["model_part"] / fitc["per_subagent"] < 0.55
    assert all(2.5 * cf2[t]["write"] < cf2[t]["review"] < 4 * cf2[t]["write"] for t in ("xl", "free"))
    MT = list(cd.master().values())  # the run-level table: one row per run, the same columns for every batch
    msel = lambda **kw: [r_ for r_ in MT if all(r_[k_] == str(v_) for k_, v_ in kw.items())]  # noqa: E731
    mnum = lambda r_, c_: cd.num(r_[c_])  # noqa: E731
    mmean = lambda v_, c_: st.mean(mnum(r_, c_) for r_ in v_ if mnum(r_, c_) is not None)  # noqa: E731
    assert len(MT) == iss["all_runs"] and len({r_["id"] for r_ in MT}) == len(MT)
    # tokens of one run, every agent together (10k tokens): input (share read from cache) / output
    tok = lambda v_: tuple(mmean(v_, c_) / 1e4 for c_ in ("tok_miss", "tok_hit", "tok_out"))  # noqa: E731
    tok_fmt = lambda v_: (lambda t_: f"{t_[0] + t_[1]:,.0f}（{100 * t_[1] / (t_[0] + t_[1]):.0f}% 读缓存） / {t_[2]:.1f}")(tok(v_))  # noqa: E731
    TOKB = {"办公报告题": ("office", ("office-confirm",), "D1-K8"), "评测集填表题": ("ws", ("ws-h1",), "W-D1-K8"), "评测集报告题": ("drb2", ("drb2-h1",), "W-D1-K8"), "读代码题": ("reading", ("main-code",), "D1-K8"),
            "小编程题": ("p4", ("main-code",), "D1-K8"), "限时 24 题": ("timed24", ("ctl-main",), "W-D1-K8"), "16 步串行题": ("chain", ("ctl-main",), "W-D1-K8"),
            "不限时 24 题": ("free24", ("ctl-free", "ctl-free-b2"), "W-D1-K8"), "大型编码题": ("xl", ("xl-main",), "W-D1-K8")}
    tok_of = {t_: [r_ for r_ in MT if r_["family"] == f_ and r_["batch"] in b_ and r_["group"] == g_] for t_, (f_, b_, g_) in TOKB.items()}
    for t_, b_ in (("评测集填表题", "ws-h1"), ("评测集报告题", "drb2-h1")):  # the same runs as the cost of the row: tasks scored in both groups, the benchmark not recognized
        scored_ = lambda r_: r_["q"] != "" and r_["recognized"] != "1"  # noqa: E731
        both_ = {r_["task"] for r_ in MT if r_["batch"] == b_ and r_["group"] == "D0" and scored_(r_)}
        tok_of[t_] = [r_ for r_ in tok_of[t_] if scored_(r_) and r_["task"] in both_]
    assert len(tok_of["评测集填表题"]) == 19 and len(tok_of["评测集报告题"]) == 29
    assert all(len(v_) >= 10 for v_ in tok_of.values()) and abs(mmean(tok_of["办公报告题"], "model_yuan") - m["D1-K8"]["model_cost"]) < 0.2
    assert abs(mmean(tok_of["大型编码题"], "model_yuan") - xm["W-D1-K8"]["cost"]) < 0.05 and abs(mmean(tok_of["不限时 24 题"], "model_yuan") - fm_["W-D1-K8"]["cost"]) < 0.05
    yuan = lambda v: rnd(v, 2)  # noqa: E731
    d.tbl("cost-task", "各任务一次运行的平均费用（元，按高峰价；联网的三种任务含估算的搜索费）和每多开一个 subagent 多花的钱。“默认开几个”是默认设置下一次运行一共开的 subagent 数；最后一列是费用对开的数量做直线拟合的斜率。", [
        ["任务", "不开 subagent", "默认", "默认开几个", "每多开一个 subagent 多花（元）", "默认一次的 token（万）：输入 / 输出"],
        ["办公报告题", yuan(m["D0"]["cost"]), yuan(m["D1-K8"]["cost"]), f(m["D1-K8"]["kids"]), f"{rnd(pt['office']['slope'])}（旅行攻略题 {rnd(fitc['by_task']['o1'])}，CPU 选型题 {rnd(fitc['by_task']['o2'])}）", tok_fmt(tok_of["办公报告题"])],
        ["评测集填表题", yuan(wp["D0"]["cost"]), yuan(wp["W-D1-K8"]["cost"]), f(wp["W-D1-K8"]["kids"]), rnd(pt["ws"]["slope"]), tok_fmt(tok_of["评测集填表题"])],
        ["评测集报告题", yuan(dp["D0"]["cost"]), yuan(dp["W-D1-K8"]["cost"]), f(dp["W-D1-K8"]["kids"]), rnd(pt["drb2"]["slope"]), tok_fmt(tok_of["评测集报告题"])],
        ["读代码题", yuan(c["means"]["D0"]["cost"]), yuan(c["means"]["D1-K8"]["cost"]), f(c["means"]["D1-K8"]["kids"]), rnd(pt["code"]["slope"]), tok_fmt(tok_of["读代码题"])],
        ["小编程题", yuan(c["p4"]["means"]["D0"]["cost"]), yuan(c["p4"]["means"]["D1-K8"]["cost"]), "0", f"{rnd(pt['p4']['slope'])}（题面加并行提示时才开）", tok_fmt(tok_of["小编程题"])],
        ["限时 24 题", yuan(wd["means"]["D0"]["cost"]), yuan(wd["means"]["W-D1-K8"]["cost"]), f(wd["means"]["W-D1-K8"]["kids"]), rnd(pt["wide"]["slope"]), tok_fmt(tok_of["限时 24 题"])],
        ["16 步串行题", yuan(ch["means"]["D0"]["cost"]), yuan(ch["means"]["W-D1-K8"]["cost"]), "0", f"{rnd(pt['chain']['slope'])}（题面加并行提示时才开）", tok_fmt(tok_of["16 步串行题"])],
        ["不限时 24 题", yuan(fm_["D0"]["cost"]), yuan(fm_["W-D1-K8"]["cost"]), f(fm_["W-D1-K8"]["kids"]), f"文件写完之前开的 {rnd(cf2['free']['write'])}，之后开的 {rnd(cf2['free']['review'])}", tok_fmt(tok_of["不限时 24 题"])],
        ["大型编码题", yuan(xm["D0"]["cost"]), yuan(xm["W-D1-K8"]["cost"]), f(xm["W-D1-K8"]["kids"]), f"写代码的 {rnd(cf2['xl']['write'])}，复核的 {rnd(cf2['xl']['review'])}", tok_fmt(tok_of["大型编码题"])]])
    lv3 = fitc["by_level"]
    d.figure("cost-sub", f"{NEW}/cost-subagents.png", f"每个点是一次运行：横轴是这次运行开的 subagent 数，纵轴是费用。左边是办公报告题（含搜索费），黑线是最小二乘拟合（{rnd(fitc['intercept'])} 元 + {rnd(fitc['per_subagent'])} 元 × 开的数量）；右边是大型编码题（模型费），两条线分别按两种题面拟合；原题面的那条把写代码的和复核的 subagent 合在一起算，所以斜率在{{tab:cost-task}} 的两个数之间。", hold=True)
    assert max(offline + [cf2["xl"]["review"], cf2["free"]["review"]]) < web[0] and 38 < fitc["search_per_subagent"] < 47 and fl["EF"]["total_cost_peak"]["lo"] > 2
    d.add("- 一次任务的费用随开的 subagent 数直线上涨（{fig:cost-sub}）。联网的调研类任务上一个 subagent 最贵，其中一半是搜索费。小编程题上默认时模型不开 subagent，默认和不开两组做的是同一件事，两组的费用差校正后不显著。",
          f"- 办公报告题上每多开一个 subagent，平均多 {fitc['search_per_subagent']:.0f} 个搜索请求。单 agent 只在题面加多查提示，费用也是原来的两倍多（{{tab:spend}}：对默认从 ×0.24 到 ×0.59）。",
          f"- 办公报告题上 subagent 开在第几层，价钱差不多（三层分别约 {rnd(lv3[0])}、{rnd(lv3[1])}、{rnd(lv3[2])} 元）。",
          "- 不限时 24 题和大型编码题上，用途不同价钱不同：文件写完以后再派去复核的 subagent，一个的钱够开三个左右写代码的。", "")
    d.release()
    crow = lambda e: [e["label"], str(e["n"]), f(e["kids"]), yuan(e["mean"]), yuan(e["median"]), yuan(e["p90"]), yuan(e["max"]), "—" if e["base_mean"] is None else yuan(e["base_mean"])]  # noqa: E731
    d.tbl("cost-office", "办公报告题各种设置下一次运行的费用（元，含估算的搜索费）。这些设置来自三批，最后一列是同一批里默认组的均值（所以有三个不同的数）。K=1 有一次运行没交出完整报告，没有算。", [
        ["设置", "运行次数", "开的 subagent 数", "均值", "中位", "九成不超过", "最高", "同批的默认"]] + [crow(e) for e in cst["settings"]])
    logs = cst["logs"]
    assert cst["old_over_logs"] == 3 and ck["old"]["n"] == 20 and all(37 < v < 40 for v in cst["logs_web"]) and logs["B"]["search_requests"] == 0
    assert ck["k4"]["kids"] - ck["default"]["kids"] < 0.2 and abs(ck["k64"]["kids"] - ck["default"]["kids"]) < 0.3 and ck["d2"]["kids"] > 2 * ck["default"]["kids"]
    gap4 = max(abs(e["mean"] / (fitc["intercept"] + fitc["per_subagent"] * e["kids"]) - 1) for e in cst["settings"] if e["kids"] > 0)  # the settings of the table against the line
    assert sum(1 for e in cst["settings"] if e["kids"] > 0) == 9 and 0.10 < gap4 < 0.13 and fitc["max_group_gap"] < 0.16
    da = cst["default_all"]
    assert da["max"] == ck["default"]["max"] and 0.25 < da["r2_kids"] < 0.32 and 2 < da["min"] < 2.5
    d.figure("cost-dist", f"{NEW}/cost-distribution.png", "办公报告题：每个点是一次运行的费用（含搜索费），横线是中位数；每列是{tab:cost-office} 里的一种设置。虚线是背景里两份联网的用户日志（A、C）按同样算法得到的整场费用，两份都在 38 元上下。", hold=True)
    d.add("- K 和深度改变了开的数量，费用跟着变（{tab:cost-office} 的第三、四列一起变）：K 到 4 以后开的数量不再变，费用也不变；放开深度以后数量翻倍，费用跟着翻倍。"
          f"表里开了 subagent 的九种设置，平均费用和按{{fig:cost-sub}} 那条直线算出来的相差不超过 {math.ceil(100 * gap4)}%。",
          f"- 同一种设置里各次运行差得远：默认设置在五批里一共跑过 {da['n']} 次（多查 150/250、250/500 那一批{'和告知上限批' if TD else ''}的默认组没有算进来），最便宜的一次 {da['min']:.0f} 元，最贵的一次 {da['max']:.0f} 元；同是默认设置，开的数量只能解释这些运行之间费用差别的 {pct(da['r2_kids'])}（上面说的直线上涨是跨设置看的）。",
          f"- 背景里两份联网的用户日志（A、C）是多轮对话，按同样的算法每份整场约 {st.mean(cst['logs_web']):.0f} 元；相当于旧默认的 {ck['old']['n']} 次单任务运行里有 {cst['old_over_logs']} 次超过这个数（{{fig:cost-dist}}）。", "")
    d.release()

    # ---- 2. how many the model wants
    d.add(f"### {SEC['open']}、模型自己想开多少", "")
    assert wso["over4"] == 9 and wso["runs"] == 24 and wso["peak_max"] == 8 and free["opens"]["cap_runs"] == 1 and free["opens"]["runs"] == 20
    wko, dko = p["wsk"]["opens"], p["drbk"]["opens"]
    assert wko["W-D1-K4"]["cap_runs"] == 9 and wko["W-D1-K4"]["runs"] == 24 and dko["W-D1-K4"]["cap_runs"] == 3 and dko["W-D1-K4"]["runs"] == 30 and wko["W-D1-K8"]["cap_runs"] == dko["W-D1-K8"]["cap_runs"] == 0
    d.p(f"**调研类任务上模型一次运行一共只开三四个 subagent，K=8 没有拒绝过它的调用（评测集填表题 {wso['runs']} 次里有 {wso['over4']} 次同时活着超过 4 个，最多到过 8 个）；"
        "深度上限在多数运行里都拒绝过调用。大型编码题上模型想开的比 8 多。**")
    brow = lambda name, v: [name, f"{v['open']}/{v['runs']}", f"{v['over4']}/{v['runs']}", f"{v['peak_max']:.0f}", f"{v['cap_runs']}/{v['runs']}", f"{v['depth_runs']}/{v['runs']}"]  # noqa: E731
    d.tbl("behave", "默认设置（深度 1、K=8）下模型自己怎么开 subagent。“同时活着”指同一时刻没结束的 subagent 数（各层合计）；“同时活着最多”一列是各次运行里到过的最大值，其余各列是运行次数（分母是默认组的运行数）。", [
        ["任务", "开了 subagent", "同时活着超过 4 个", "同时活着最多", "有调用被 K=8 拒绝", "有调用被深度上限拒绝"],
        brow("办公报告题", op["D1-K8"]), brow("评测集填表题", wso), brow("评测集报告题", dro), brow("读代码题：问答", c["opens_task"]["c1-subagent-limits"]), brow("读代码题：写方案", c["opens_task"]["w1-memory-plugin"]), brow("小编程题", c["p4"]["opens"]),
        brow("限时 24 题", wd["opens"]), brow("16 步串行题", ch["opens"]), brow("不限时 24 题", free["opens"]), brow("大型编码题", xo)])
    d.figure("levels", f"{NEW}/office-levels.png", "办公报告题：放开深度和 K 以后，每一层开了多少 subagent（每次运行的平均数）。K 是各层合起来数的。", hold=True)
    lev = dict(o["levels"])
    assert c["opens"]["open"] == c["w1"]["spawn_runs"] == 10 and abs(lev["深度 1、K=64"][0] - lev["深度 1、K=8（默认）"][0]) < 0.5
    assert lev["深度 3、K=8"][2] < 1 < 5 < lev["深度 3、K=64（相当于旧默认）"][2] and lev["深度 2、K=64"][1] > 1.5 * lev["深度 2、K=8"][1]
    d.add("- 调研类任务上 K=8 没有拒绝过任何调用，多数运行同时活着的不超过 4 个；大型编码题每次运行都有调用被 K 拒绝。问答题、小编程题和 16 步串行题，模型自己不开。",
          f"- 调研类任务上大多数运行都有调用被深度上限拒绝。办公报告题放开到深度 2 以后，仍有 {beh['D2-K8']['depth']['hit']}/{beh['D2-K8']['depth']['runs']} 次。",
          f"- 全部 {iss['all_runs']:,} 次运行里，开 subagent 的调用一共 {m_calls:,} 次，开成了 {mtl['children']:,} 个，其余几乎都是被上限拒绝的（被深度上限 {MX['rejected']['depth']:,.0f} 次，被 K {MX['rejected']['cap']:,.0f} 次；这个总数里包括各个把 K 调小了的组）。"
          f"默认设置下，办公报告题一次运行开成 {rnd(made8)} 个，另有 {rnd(rj8['depth'])} 次调用被深度上限拒绝（{{fig:rejects}}）：是 subagent 想再往下开，{{fig:tree-default}} 是其中一次运行。"
          f"放开到深度 2，第 1 层的 subagent 有的又开了几个，K=8 就满了，这时每次运行有 {rnd(mrj['office-confirm']['D2-K8']['cap'])} 次调用被 K 拒绝（{{fig:tree-depth2}}）。",
          f"- 深度和 K 互相影响（{{fig:levels}}）：只放开 K 不放开深度，开的数量不变；深度 2 时 K=8 经常不够用（{d2_full}/{op['D2-K8']['runs']} 次同时活着的到了 8 个）；第 3 层要把 K 放到 64 才开得多。"
          f"K 是各层合起来数的，K=1、2 时第 1 层就把它用满了：第一批里深度 2、K=1 和深度 2、K=2 的 {n_l2} 次运行，第 2 层一个都没开出来。",
          f"- 不限时 24 题和大型编码题上，K 到 16 为止越大开得越多：不限时 24 题在题面加并行提示时，K=1 平均开 {f(fm_['W-E-D1-K1']['kids'])} 个，K=16 开 {f(fm_['W-E-D1-K16']['kids'])} 个，K=64 没有再多。",
          f"- 按够不够用看 K（{{tab:behave}} 的“同时活着超过 4 个”和“有调用被 K=8 拒绝”两列）：K=8 满足了调研类任务和读代码题全部默认运行的需要，其中同时活着超过 4 个的是少数。"
          f"办公报告题实际跑过 K=4：{beh['D1-K4']['cap']['runs']} 次里 {beh['D1-K4']['cap']['hit']} 次有调用被拒绝，开的数量、写对的事实都和 K=8 没有差别（{{tab:cost-office}}、{{tab:k}}）。两个公开评测集上 K=4 时，评测集填表题 {wko['W-D1-K4']['runs']} 次里 {wko['W-D1-K4']['cap_runs']} 次、评测集报告题 {dko['W-D1-K4']['runs']} 次里 {dko['W-D1-K4']['cap_runs']} 次有调用被拒绝。写代码的两种任务要得更多：K 放到 64 时，大型编码题（加不复核提示）同时活着的最多时中位 {st.median(cst['demand']['xl']):.0f} 个，不限时 24 题（加并行提示）中位 {st.median(cst['demand']['free']):.0f} 个。", "")
    d.release()
    assert all(2 * v["over4"] < v["runs"] for v in (op["D1-K8"], wso, dro)) and beh["D1-K4"]["cap"]["hit"] == 2 and beh["D1-K4"]["cap"]["runs"] == 40
    tr1, tr2 = MX["trees"]["D1-K8"], MX["trees"]["D2-K8"]
    t1k = [n_ for n_ in tr1["nodes"] if n_["depth"] == 1]
    t2k1, t2k2 = [n_ for n_ in tr2["nodes"] if n_["depth"] == 1], [n_ for n_ in tr2["nodes"] if n_["depth"] == 2]
    assert tr1["result"]["task"] == tr2["result"]["task"] == "o1-singapore-trip" and len(t1k) == 3 and all(3 <= n_["rejected_depth"] <= 4 for n_ in t1k) and len(tr1["nodes"]) == 4
    assert len(t2k1) == 5 and len(t2k2) == 3 and len({n_["parent"] for n_ in t2k2}) == 1 and sum(n_["rejected_cap"] for n_ in t2k1) == 12 and sum(n_["rejected_depth"] for n_ in tr2["nodes"]) == 0
    d.figure("rejects", f"{NEW}/rejects-office.png", "办公报告题：各种设置下，一次运行开成几个 subagent，有几次开 subagent 的调用被深度上限拒绝、几次被 K 拒绝（每种设置 40 次运行的平均）。被深度上限拒绝的，都是 subagent 自己想再往下开的调用。")
    d.figure("tree-default", f"{NEW}/tree-default.png", f"默认设置下的一次运行（旅行攻略题；开的 subagent 数等于这一组中位数的运行里取重复号最小的一次）：主 agent 一开始就开了 {len(t1k)} 个 subagent，各查一块。"
             "每个方框是一个 agent，第一行是模型自己给它起的标签（原文是英文），下面是它发出的搜索请求数、运行了多久、花了多少模型费，以及它自己开 subagent 的调用被拒绝了几次。")
    t2parent = next(n_ for n_ in t2k1 if n_["id"] == t2k2[0]["parent"])  # the first-level subagent that opened the second level
    t2rej = [n_ for n_ in t2k1 if n_["rejected_cap"]]
    d.figure("tree-depth2", f"{NEW}/tree-depth2.png", f"深度 2 下的一次运行（同一道题，取法同{{fig:tree-default}}）：主 agent 开了 {len(t2k1)} 个，其中一个又开了 {len(t2k2)} 个，同时活着的到了 8 个；"
             f"第 1 层的 {len(t2k1)} 个里有 {len(t2rej)} 个自己再开 subagent 的调用被 K 拒绝，一共 {sum(n_['rejected_cap'] for n_ in t2k1)} 次（开成了 {len(t2k2)} 个的那个也被拒 {t2parent['rejected_cap']} 次）。")
    kk = [fm_[f"W-E-D1-K{q}"]["kids"] for q in (1, 2, 4, 8, 16, 64)]
    assert kk[:5] == sorted(kk[:5]) and kk[5] < kk[4]

    # ---- 2. is delegating worth it
    d.add(f"### {SEC['worth']}、开不开值不值", "")
    spent = sorted(q["model_cost_peak"]["est"] for q in (c["cmp"]["C1"], wd["cmp"]["NC"], free["cmp"]["NC"], xl["cmp"]["NC"]))
    assert 1.5 < spent[0] and spent[-1] < 4.8 and c["p4"]["opens"]["open"] == 0 and ch["opens"]["open"] == 0
    d.p(f"**调研类任务上，开 subagent 换来查得更全（评测集填表题上没测出）；代码类任务上，模型会开 subagent 的四种任务费用是不开的 {rnd(spent[0])}–{rnd(spent[-1])} 倍，得分只有限时 24 题（带时限，按方案只作参考）多了 {rnd(wd['cmp']['NC']['score']['est'])} 分、大型编码题多通过 2 个测试，不限时 24 题没有差别，读代码题没测出差别；"
        "两类任务上，原题面下用户等的时间都没有测出缩短。**")
    reps3 = "、".join(sg(v) for v in sorted(r["est"] for r in o["h1_reps"]))
    CN = {2: "两", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九"}
    wcost, dcost = ws["cmp"]["H1n"]["total_cost_peak"], drb["cmp"]["H1"]["total_cost_peak"]
    assert ws["cmp"]["H1n"]["r_item"]["lo"] > 0 and ws["cmp"]["H1n"]["r_item"]["p_holm"] > 0.05 and drb["cmp"]["H1"]["info_recall"]["lo"] > 0
    tl1 = (min(v["o1"]["est"] for v in hlt.values()), max(v["o1"]["est"] for v in hlt.values()))  # the 63 items, by task, over the four batches
    tl2 = (min(v["o2"]["est"] for v in hlt.values()), max(v["o2"]["est"] for v in hlt.values()))
    assert 14 < tl1[0] < tl1[1] < 23 and 2.5 < tl2[0] < tl2[1] < 11
    d.figure("summary", f"{NEW}/summary-by-task.png", "各类任务上默认（深度 1、K=8）和不开 subagent 的差别：默认下模型自己开几个 subagent、质量高多少、费用和时间是不开的几倍。"
             "点是估计值，横线是 95% 区间。质量一栏：办公报告题是写对的事实占比（个百分点；实心点是事先定下的 63 条，空心点是全清单），其余是得分（满分 100）。“默认开几个 subagent”是一次运行一共开的个数。")
    d.tbl("worth", "开 subagent（默认）对不开 subagent。质量之差：办公报告题是写对的事实占比（个百分点），其余是得分；费用和时间是倍数；方括号里是 95% 区间。"
          "带 ★ 的行是事前写定的主要对比；办公报告题、限时 24 题、16 步串行题、不限时 24 题和大型编码题的行是方案里列明的次要对比（办公报告题的主要对比是第一批的那个，这一行用的是次数更多的主要一批）；读代码题、小编程题两行是把事前写定的三题合起来的对比按题拆开，属事后（三题合起来的结果见附录的{tab:code3}）。", [
        ["任务", "质量之差", "判断", "只算事先定下的 63 条", "费用倍数", "时间倍数"],
        ["办公报告题", ci(h1["right_pct"]), verdict(h1["right_pct"], 8), ci(h1leg), xci(h1["total_cost_peak"]), xci(h1["seconds"])],
        ["评测集填表题 ★", ci(ws["cmp"]["H1n"]["f1_item"]), verdict(ws["cmp"]["H1n"]["f1_item"], 5), "—", xci(wcost), xci(wt)],
        ["评测集报告题 ★", ci(dt), verdict(dt, 5), "—", xci(dcost), xci(dtm)],
        ["读代码题", ci(c["cmp"]["C1"]["score"]), verdict(c["cmp"]["C1"]["score"], 5), "—", xci(c["cmp"]["C1"]["model_cost_peak"]), xci(c["cmp"]["C1"]["seconds"])],
        ["小编程题", ci(c["p4"]["c1"]["score"]), verdict(c["p4"]["c1"]["score"], 5), "—", f"{xci(c['p4']['c1']['model_cost_peak'])}（校正后不显著）", xci(c["p4"]["c1"]["seconds"])],
        ["限时 24 题", ci(wd["cmp"]["NC"]["score"]), verdict(wd["cmp"]["NC"]["score"], 5), "—", xci(wd["cmp"]["NC"]["model_cost_peak"]), "限时"],
        ["16 步串行题", "0（都是满分）", "—", "—", xci(ch["cmp"]["NC"]["model_cost_peak"]), xci(ch["cmp"]["NC"]["seconds"])],
        ["不限时 24 题", ci(free["cmp"]["NC"]["score"]), verdict(free["cmp"]["NC"]["score"], 5), "—", xci(free["cmp"]["NC"]["model_cost_peak"]), xci(free["cmp"]["NC"]["answer_s"])],
        ["大型编码题", ci(xl["cmp"]["NC"]["score"], 2), "显著变好（约 2 个测试）", "—", xci(xl["cmp"]["NC"]["model_cost_peak"]), xci(xl["cmp"]["NC"]["answer_s"])]])
    gb = cst["gain_behaviour"]
    assert all(abs(gb[q]["r_subagents"]) < 0.15 and abs(gb[q]["r_peak"]) < 0.15 for q in gb)
    assert all(-0.45 < gb[q]["ci_subagents"][0] < -0.35 and 0.3 < gb[q]["ci_subagents"][1] < 0.55 for q in gb)
    d.figure("pub-pair", f"{NEW}/pub-paired-delegation.png", "两个公开评测集，每道题一个点：横轴是不开 subagent 的得分，纵轴是默认的得分；斜线上方是默认更高。", hold=True)
    assert verdict(xl["cmp"]["NC"]["score"], 5) == "显著变好" and verdict(ws["cmp"]["H1e"]["f1_item"], 5) in ("没有差别", "没测出差别")
    assert ch["cmp"]["EC"]["model_cost_peak"]["lo"] > 1 and ch["cmp"]["EC"]["seconds"]["lo"] > 1 and ch["cmp"]["EC"]["score"]["est"] == 0
    d.add(f"- 调研类任务上，开 subagent 换来的是查得更全：办公报告题的事实占比显著更高，评测集报告题的召回（评分项里“该有的信息找到没有”那一类满足了百分之几）{ci(drb['cmp']['H1']['info_recall'])}，"
          f"评测集填表题的召回（标准答案的格子里填对了多少）{ci(ws['cmp']['H1n']['r_item'])}、校正后不显著。按全清单，办公报告题两道题都成立（各批里旅行攻略题多 {t1['o1'][0]:.0f}–{t1['o1'][1]:.0f} 个百分点，CPU 选型题多 {t1['o2'][0]:.0f}–{t1['o2'][1]:.0f} 个）；"
          f"按事先定下的 63 条，旅行攻略题在四批里都显著（多 {tl1[0]:.0f}–{tl1[1]:.0f} 个），CPU 选型题多 {tl2[0]:.0f}–{tl2[1]:.0f} 个、只有一批显著。办公报告题的这个对比"
          f"在{CN[len(o['h1_reps'])]}批里重复过（各批的全清单结果是 {reps3}；第一批的那个是事前写定的主要对比，正文别处用的是主要一批的数）；写错的条数没有变多。",
          f"- 代码类任务上，限时 24 题做完的更多（测试全过的题从 {f(wd['solved']['D0'])} 道到 {f(wd['solved']['W-D1-K8'])} 道，共 24 道），其余几种任务的得分见{{tab:worth}}。"
          f"不限时 24 题和大型编码题上，文件写得更快（从开始到要写的文件都写完的时间，是不开的 {x(free['cmp']['NC']['all_written_s'])} 和 {x(xl['cmp']['NC']['all_written_s'])}），用户等的时间却没有缩短，原因在细节{SEC['spend']}。",
          f"- 题面加并行提示，模型开得更多、费用更高，得分没有显著提高：读代码题对默认 {ci(c['cmp']['C2']['score'])} 分（校正后不显著）、模型费 {x(c['cmp']['C2']['model_cost_peak'], 1)}；"
          f"评测集填表题对不开 subagent {ci(ws['cmp']['H1e']['f1_item'])} 分；16 步串行题对默认模型费 {x(ch['cmp']['EC']['model_cost_peak'], 1)}、时间 {x(ch['cmp']['EC']['seconds'], 1)}，得分不变。",
          f"- 按题看，没看到“模型开得多的题涨得更多”：两个公开评测集上，每道题的涨幅和这道题默认开了几个 subagent 的相关系数是 {sg(gb['ws']['r_subagents'], 2)} 和 {sg(gb['drb2']['r_subagents'], 2)}"
          f"（两组的运行都计分的 {gb['ws']['n']} 道和 {gb['drb2']['n']} 道题；区间约 ±0.4，中等强度的关系排除不了；事后分析）。", "")
    d.release()
    # which facts the default adds (looked at afterwards): grouped by how often a run without subagents states them
    sa, sb_ = E["strata"]["confirm"], E["strata"]["floor"]
    srow = lambda r: [r["name"], f(r["items"]), f(r["legacy"]), f(r["low"]), f(r["high"]), sg(r["gain"]), pct(r["share"])]  # noqa: E731
    mid = lambda s_: s_["rows"][1]["share"] + s_["rows"][2]["share"]  # noqa: E731  (the two middle groups)
    assert abs(sa["total"]["gain"] - cmp_["D0"]["right_n"]["est"] * -1) < 0.2 and all(0.75 < mid(s_) < 0.9 for s_ in (sa, sb_))
    assert all(0.08 < s_["rows"][0]["share"] < 0.23 and s_["rows"][3]["share"] < 0.05 for s_ in (sa, sb_)) and E["strata"]["items"] == 195 and E["strata"]["legacy"] == 63
    assert all((s_["rows"][2]["legacy"] + s_["rows"][3]["legacy"]) / sum(r["legacy"] for r in s_["rows"]) > 0.65 for s_ in (sa, sb_))
    d.tbl("strata", "办公报告题：默认比不开 subagent 多写对的是哪些事实（事后分析）。195 条事实按“不开 subagent 时多常被写对”分成四档；分档用第一批和多查 100/100 那一批里不开 subagent 的运行，多写对的条数在办公报告题主要的一批里量（分档和量用同一批的话，碰巧没写到的条目会平白显出涨幅）。条数都是每题每份报告的平均（清单每题平均 97.5 条）。", [
        ["不开 subagent 时", "这一档有几条", "其中事先定下的", "不开时写对", "默认写对", "多写对", "占多写对的"]] + [srow(r) for r in sa["rows"]]
        + [["合计", f(sum(r["items"] for r in sa["rows"])), f(sum(r["legacy"] for r in sa["rows"])), f(sa["total"]["low"]), f(sa["total"]["high"]), sg(sa["total"]["gain"]), "100%"]])
    sm = E["strata_merged"]
    r0, r1 = sa["rows"][0], sa["rows"][1]
    up0, up1 = r0["high_rate"] - r0["low_rate"], r1["high_rate"] - r1["low_rate"]
    assert 0.19 < up0 < 0.23 and 0.20 < up1 < 0.24 and abs(up0 - up1) < 0.03 and 14 < r0["items"] < 16
    m4a, m4b = sm["confirm"]["rows"][0], sm["floor"]["rows"][0]
    assert abs(m4a["default"] - r0["high"]) < 0.05 and m4a["m4"] > m4a["default"] and m4b["m4"] < m4b["default"] and all(v["merges"]["M4"][t] == 5 for v in sm.values() for t in v["merges"]["M4"])
    assert 3.8 < m["D1-K8"]["chars"] / 1e4 < 4.0 and 2.2 < m["D0"]["chars"] / 1e4 < 2.4
    d.add(f"- 多写对的四分之三以上，落在单 agent 有时写到、有时写不到的两档。最低一档只占一到两成，是因为清单里这样的条目少（每题约 {r0['items']:.0f} 条）："
          f"按每条算，这一档被写对的比例从 {pct(r0['low_rate'])} 涨到 {pct(r0['high_rate'])}，涨幅和“偶尔写到”那一档（{pct(r1['low_rate'])} 到 {pct(r1['high_rate'])}）一样大。",
          f"- 最低一档的事实单 agent 也查得到，只是每次查到的少：四份单 agent 报告合并以后，这一档写对 {rnd(m4a['m4'])} 条，默认是 {rnd(m4a['default'])} 条；换一批量，合并稿是 {rnd(m4b['m4'])} 条、默认是 {rnd(m4b['default'])} 条，两批里谁多谁少不一样。",
          "- 这张表有两个限制。清单主要收的是多份样本报告都写到的事实，很少被查到的事实进不了清单，所以它说明不了 subagent 多查到的东西里有多少是单 agent 查不到的。"
          f"写没写对看的是最终报告，默认的报告也更长（{m['D1-K8']['chars'] / 1e4:.1f} 万字对 {m['D0']['chars'] / 1e4:.1f} 万字），表里分不开“查到的更多”和“写进去的更多”。",
          "- 事先定下的 63 条大多落在单 agent 本来就常写对的两档，可涨的余地小；这是只算 63 条时效果小一截的原因之一（细节" + SEC["trust"] + "）。", "")
    d.figure("strata", f"{NEW}/facts-strata.png", "办公报告题：默认比不开 subagent 多写对的事实落在哪一档（事后分析）。195 条事实按不开 subagent 时被写对的频率分成四档；"
             "两根柱子是每份报告在这一档里写对的条数。")

    # ---- 3. K
    d.add(f"### {SEC['k']}、K", "")
    d.p(f"**K 调大（16、64）没测出好处。K=1 有显著的损失：大型编码题的时间和限时 24 题的得分（后一个带时限，按方案只作参考）；读代码题三个深度合起来算也显著（事后合并），只看深度 1 没测出差别。K=2 校正后显著的损失只有大型编码题加不复核提示时慢到 {rnd(kq('xln', 2, 't')['est'], 2)} 倍；三处质量的估计值偏低，都不显著（读代码题三个深度合起来和限时 24 题两处，单看区间不含 0，校正后不成立）。"
        "K=4 和 8 显著的差别只在大型编码题上：4 更便宜，加了不复核提示以后慢两成。三种调研类任务上 K=4 的质量、费用、时间都不显著，其中评测集填表题的区间宽。**")
    fk, xk = free["cmp"], xl["cmp"]
    K1o, K4o, K64o = cmp_["D1-K1"], cmp_["D1-K4"], o["k64"]
    lg = o["legacy"]  # contrasts on the 63 items fixed beforehand that the batch statistics do not carry
    assert verdict(K4o["right_pct"], 8) == verdict(leg["D1-K4"], 8) == "没有差别" and lg["k64"]["lo"] < 0 < lg["k64"]["hi"]

    def pkv(q: dict, corrected: bool = False) -> str:
        """The word for a score difference of the package, with the difference in hidden tests failed per run behind it."""
        v = verdict(q, 5, corrected)
        tests_ = abs(xl["failed"][q["a"]] - xl["failed"][q["b"]])
        if v in ("显著变好", "显著变差") and q.get("p") is not None and q["p"] >= 0.05:  # nearly every paired difference is 0: the sign-flip test decides, not the t interval
            return f"没测出差别（区间不含 0，精确检验 p = {rnd(q['p'], 2)}；平均差 {rnd(tests_)} 个测试）"
        return f"{v}（平均差 {rnd(tests_)} 个测试）" if v in ("显著变好", "显著变差") else v
    SUBL = {"": "", "题面加并行提示": "（加并行提示）", "原题面": "（原题面）", "题面加不复核提示": "（加不复核提示）"}

    def leg_cell(q, margin: float = 8) -> str:
        """The cell of the 63 items fixed beforehand: the estimate (in brackets when its interval holds 0) and its own
        verdict (corrected where the contrast was corrected with its family)."""
        if not q:
            return "—"
        return f"{est(q)}，{verdict(q, margin, q.get('holm', q.get('p_holm')) is not None)}"

    def lrow(r: dict, label: str, what: str, cl: dict) -> list:
        """A row of the K or depth table from a cell of clean_extra.limits (the numbers of the two overview figures)."""
        word = pkv(cl["q"], cl["corr"][0]) if r.get("tests") else verdict(cl["q"], r["margin"], cl["corr"][0])
        exact_no = bool(r.get("tests")) and cl["q"].get("p") is not None and cl["q"]["p"] >= 0.05  # the exact test says no where the t interval says yes
        assert (not est(cl["q"], cl["nd"], word).startswith("（")) == (ce.strong(cl["q"], cl["corr"][0]) and not exact_no), (r["key"], what)
        return [label, what + (" ★" if cl["star"] else ""), est(cl["q"], cl["nd"], word), word, leg_cell(cl["legacy"], r["margin"]),
                mul(cl["c"], cl["corr"][1]) if cl["c"] else "—", "限时" if r.get("limited") else mul(cl["t"], cl["corr"][2])]
    krows = [lrow(r, (r["name"] + SUBL[r["sub"]]) if i == 0 else "", str(v), cl) for r in L["k"] for i, (v, cl) in enumerate(sorted(r["cells"].items()))]
    d.tbl("k", "换 K 对 K=8 的差别（深度都是 1；各批自己的数。正文的{tab:limits-ci} 和{fig:k-quality}、{fig:k-cost}、{fig:k-time} 里，办公报告题的 K=1、2、4 是两批合起来的数，读代码题是和小编程题三道题合起来的数）。质量之差：办公报告题是写对的事实占比（个百分点），其余是得分。办公报告题的“质量之差”和“判断”两列是全清单的，旁边一列是事先定下的 63 条和它自己的判断，结论以 63 条为准。费用（办公报告题和评测集报告题含搜索费，其余是模型费）和时间是倍数。"
          "带括号的数：区间含 0（倍数是含 1），或者校正后不显著；区间在附录的{tab:limits-ci}。带 ★ 的行是事前写定的主要对比。限时 24 题的费用是限时 3 分钟里花掉的模型费。", [
        ["任务", "K", "质量之差", "判断", "办公报告题：事先定下的 63 条", "费用倍数", "时间倍数"]] + krows)
    d.figure("cost-k", f"{NEW}/cost-by-k.png", "各任务一次运行的平均费用（元）随 K 怎么变，深度都是 1。细线是各组均值的 95% 区间；深蓝色是默认，灰色是不开 subagent。横轴下面每条灰色短线标出同一批跑的几组；“另一批的 K”是另一批里的 K 和它自己的 K=8。""读代码题和两道 24 题换 K 的各组题面都加了并行提示，要和同一条短线上的 K=8 比，不和深蓝色的默认比。", hold=True)
    assert all(fk[q]["answer_s"]["lo"] < 1 < fk[q]["answer_s"]["hi"] for q in ("K16", "K64")) and verdict(K4o["right_pct"], 8) == "没有差别"
    assert verdict(kd["cmp"]["K1"]["total"], 5) == "没有差别" and xk["K1"]["answer_s"]["est"] > 2 and 0.45 < kd["cmp"]["K1"]["total_cost_peak"]["est"] < 0.56
    assert xk["K4"]["model_cost_peak"]["hi"] < 1 < xk["K4"]["answer_s"]["lo"] and g3["K4"]["est"] < g3["K1"]["est"] < 0 and verdict(g3["K4"], 5) == "没测出差别"
    assert xk["NK4"]["model_cost_peak"]["hi"] < 1 and xk["NK4"]["answer_s"]["lo"] < 1 < xk["NK4"]["answer_s"]["hi"] and xk["NK16"]["answer_s"]["lo"] < 1 < xk["NK16"]["answer_s"]["hi"]
    assert verdict(K1o["right_pct"], 8, True) == "显著变差" and verdict(g3["K1"], 5, True) == "显著变差" and verdict(fk["K1"]["score"], 5, True) == "显著变差" and abs(fk["K1"]["score"]["est"]) < 1.5
    assert all(abs(xk[q]["score"]["est"]) < 0.03 for q in ("NK4", "NK16", "K1", "K2", "K4", "K16"))
    k2c = sorted(r["cells"][2]["c"]["est"] for r in L["k"] if 2 in r["cells"])
    assert 0.5 < k2c[0] < k2c[-1] < 0.8 and verdict(cmp_["D1-K2"]["right_pct"], 8, True) == "没测出差别" and verdict(g3["K2"], 5, True) == "校正后不显著"
    geo = {q_: math.exp(st.mean(math.log(cd.num(r_["answer_s"])) for r_ in cd.R("results/analysis-xl-main/rows-all.csv") if r_["group"] == f"W-N-D1-K{q_}")) for q_ in (1, 2, 4, 8, 16)}
    geo4 = geo[4] / min(geo.values())  # the pre-written rule for "the model stops when the files are written": time within 1.15 of the fastest group
    frows_ = cd.R("results/analysis-ctl-free-all/rows.csv")  # the reading written two hours before the rule: K against K = 64 on the 24 exercises without a limit
    v64 = {q_: cd.contrast(frows_, f"W-E-D1-K{q_}", "W-E-D1-K64", lambda r_: cd.num(r_["answer_s"]), "ratio") for q_ in (4, 8, 16)}
    assert all(not (0.9 <= v_["lo"] and v_["hi"] <= 1.1) for v_ in v64.values()) and len({v_["n"] for v_ in v64.values()}) == 1 and abs(v64[8]["est"] * fk["K64"]["answer_s"]["est"] - 1) < 0.01
    assert 1.18 < geo4 < 1.26 and min(geo, key=geo.get) == 8 and all(geo[q_] / geo[8] > 1.15 for q_ in (1, 2, 4))
    crows3_ = [r_ for r_ in cd.R("results/analysis-v2/rows.csv") if r_["task"] in ("c1-subagent-limits", "w1-memory-plugin")]
    k4d = {dep_: cd.contrast(crows3_, f"E-D{dep_}-K4", f"E-D{dep_}-K8", lambda r_: cd.num(r_["score"]), "diff") for dep_ in (1, 2, 3)}  # K = 4 against 8 on the reading tasks, depth by depth
    assert abs(k4d[1]["est"] - kq("code", 4)["est"]) < 0.01 and k4d[2]["lo"] > 0 and k4d[3]["lo"] < 0 < k4d[3]["hi"] and abs(st.mean(k4d[q_]["est"] for q_ in k4d) - fk4["est"]) < 0.01
    assert all(v_["n"] == 20 for v_ in k4d.values()) and abs(fk2["holm"] / fk2["p"] - 4) < 0.01 and abs(fk1["holm"] / fk1["p"] - 5) < 0.01
    d.add("- K 只在模型想开得比它多的时候起作用：办公报告题上模型只开三四个，K=4 和 8 没有差别。读代码题上 K=4 和 8 没测出差别；限时 24 题上 K=4 的估计值偏低，但 10 对的区间很宽（附录{tab:limits-ci}），也没测出差别。",
          f"- 上面都是深度 1 下的对比。读代码题在第一批里还在深度 2、3 下各跑过一套：深度 2 那一套 K=4 比 K=8 高（{ci(k4d[2])}，{k4d[2]['n']} 对；没有校正，只作描述），深度 3 是 {sg(k4d[3]['est'])}；三个深度合起来 {sg(fk4['est'])}，没有差别。",
          f"- 两个公开评测集上补测的 K=4（事前写定的主要对比，两个一起校正）：评测集报告题没有差别（{ci(dk4_)}，{dk4_['n']} 对）；评测集填表题没测出差别（{ci(wk4)}，{wk4['n']} 对，这些对数能测出的最小差别约 {mdd(wk4, wk4['n'] - 1):.0f} 分）。"
          f"两处的费用和时间都没测出差别（费用 {x(kq('ws', 4, 'c'))}、{x(kq('drb2', 4, 'c'))}，时间 {x(kq('ws', 4, 't'))}、{x(kq('drb2', 4, 't'))}）。事前写定的读法在附录的{{tab:k-readings}}。",
          f"- K=1 在办公报告题上按事先定下的 63 条少写对 {rnd(-leg['D1-K1']['est'])} 个百分点、没测出差别（全清单少 {rnd(-K1o['right_pct']['est'])}，显著），在限时 24 题上少做完，在大型编码题（加不复核提示）上慢得多；"
          "评测集报告题和评测集填表题上没有差别（±5 分以内），费用是一半多一点。不限时 24 题上 K=1 的得分低 1 分，大型编码题各组的得分差都不到 1 个测试。",
          f"- K=2 的费用是 K=8 的 {rnd(k2c[0], 2)}–{rnd(k2c[-1], 2)} 倍。办公报告题和限时 24 题上质量的估计值偏低，一个没测出、一个校正后不显著；大型编码题加了不复核提示以后慢到 {rnd(xk['K2']['answer_s']['est'], 2)} 倍。",
          "- 费用跟着开的数量走（{fig:cost-k}）：办公报告题上 K 到 4 就不再涨；不限时 24 题和大型编码题上从 K=1 到 8 费用在涨，K=16 没测出比 8 更贵。",
          "- K=4 和 8 的差别只在大型编码题上测得出，是费用和时间的取舍：原题面下 K=4 更便宜（少派了复核的 subagent），时间没测出差别；加了不复核提示以后，K=4 更便宜也更慢。"
          f"原题面下 K=4 平均多留 {rnd(k4_tests)} 个没通过的测试（{xm['W-D1-K4']['n']} 次里 {xm['W-D1-K4']['n'] - xl['all_pass_runs']['W-D1-K4']} 次各留 {xl['failed_max']['W-D1-K4']} 个，K=8 的 {xm['W-D1-K8']['n']} 次全过），"
          f"得分差 {sg(kq('xl', 4)['est'], 2)} 分：t 区间不含 0，但 10 对里只有 4 对不为 0，按精确检验 p = {rnd(xk['NK4']['score']['p'], 2)}，没测出差别；也远在方案定的 −1 分门槛以内（{{tab:k-readings}}）。原题面的这几组还有三到六成的运行把内存用满（细节{SEC['deliver']}），时间的比较带着这个影响。",
          f"- K=16、64 没测出更快（大型编码题上 K=64 只和同批的 K=16 比过：{x(x64)}，区间含 1）。大型编码题加不复核提示时，这不是内存不够造成的：模型同时最多只开十一二个，文件写得更快了，到最终回答的时间没有缩短（细节{SEC['deliver']}的{{tab:xl-k}}）。",
          "- 给出 K 取值的读法先后写过四条，另有两条判断小 K 有没有损失；什么时候写的、写的时候看过哪些结果、各给出什么，列在附录的{tab:k-readings}。"
          "10 月 3 日的三条规则写的时候有两条的结果已经在手，不算事前写定，按它得到的是 4；10 月 4 日为大型编码题补的两条，原题面下给出 4，加不复核提示时给出 8。"
          "补测 K=4 之前写定的那一条给出的是保持 8，建议按的是它。正文方法里的判断框架是这些规则的概括，交付那一步方案里没有。",
          "- 各组的绝对数在附录的分任务结果表和图里（{fig:office}、{fig:code}、{fig:pkg}、{fig:ex}）。", "")
    assert xm["W-D1-K4"]["review"] < 0.6 * xm["W-D1-K8"]["review"] and fm_["W-E-D1-K16"]["cost"] > fm_["W-E-D1-K8"]["cost"] > fm_["W-E-D1-K4"]["cost"]
    assert all(q["model_cost_peak"]["lo"] < 1 < q["model_cost_peak"]["hi"] for q in (fk["K16"], fk["K64"], xk["NK16"], xk["K16"]))
    assert all(q["model_cost_peak"]["hi"] < 1 for q in (fk["K1"], xk["K1"], xk["K4"], xk["NK4"]))
    d.release()
    if TD:  # the limit written into the tool description: the batch office-told, read as its plan wrote beforehand
        inter = TD["extra"]["interaction"].get("right_legacy_pct")
        s1_ = tc["S1"]
        d.add(f"- **把同时存活上限写进工具说明（{{tab:told}}、{{tab:told-cmp}}、{{fig:told}}）。** 现在的工具说明里不写 K，模型超出上限、被拒绝一次才知道。追加的一批在两个开 subagent 的工具的说明末尾加一句和拒绝消息内容相同的话（上限是几，超出了怎么办），"
              f"K=2 和 K=8（默认）各配加与不加，每组 {tm['D1-K2']['runs']} 次，办公报告题原题面，进程不等 subagent；质量以事先定下的 63 条为准，K=2、K=8 两个主要对比每个指标一起校正。{told_concl}"
              f"告知以后的 K=2 对默认：写对的 {ci(s1_['right_legacy_pct'])}（{verdict(s1_['right_legacy_pct'], 8)}），费用 {xci(s1_['total_cost_peak'])}，时间 {xci(s1_['answer_s'])}"
              + ("，质量没有差别、费用更低，可以作为 DSH 的候选改动。" if TR["s1_ok"] else "。")
              + f"这一批里重复出来的 K=2 对默认是 {ci(tc['S2']['right_legacy_pct'])}（主要的一批是 {ci(leg['D1-K2'])}）。"
              + (f"告知的作用在两个 K 上的差（K=2 上的差减 K=8 上的差）是 {ci(inter)}（{inter['n']} 个区组，只作描述）。" if inter else ""), "")
        G = (("D1-K2", "K=2"), ("T-D1-K2", "K=2，告知上限"), ("D1-K8", "K=8（默认）"), ("T-D1-K8", "K=8，告知上限"))
        d.tbl("told", "办公报告题：把同时存活上限写进工具说明的一批，各组的结果（每题每组 20 次；质量、费用、时间按交出完整报告并判了分的运行，两道题等权；开的 subagent、同时活着最多和被拒绝的调用按全部运行）。", [
            ["组", "运行次数（判了分的）", "写对的事实占比：63 条（%）", "全清单（%）", "费用（元/次）", "到最终回答（分钟）", "开的 subagent", "同时活着最多", "被 K 拒绝（次/运行；有被拒的运行数）", "被深度上限拒绝（次/运行）", "主 agent 结束时还有 subagent 没做完"]]
            + [[lb, f"{tm[g]['runs']}（{tm[g]['n']}）", rnd(tm[g]["right_legacy_pct"]), rnd(tm[g]["right_pct"]), rnd(tm[g]["cost"], 2), rnd(tm[g]["minutes"]), rnd(tm[g]["kids"]), rnd(tm[g]["slot_peak"]),
                f"{rnd(tm[g]['cap_rejects'])}；{tm[g]['cap_reject_runs']}/{tm[g]['runs']}", rnd(tm[g]["depth_rejects"]), str(tm[g]["early"])] for g, lb in G])
        CM = (("P1", "K=2：告知对不告知 ★", True), ("P2", "K=8：告知对不告知 ★", True), ("S1", "告知的 K=2 对默认", False), ("S2", "K=2 对默认（重复主要的一批）", False))
        d.tbl("told-cmp", "同一批里的四个对比（按题和第几次配对）。带 ★ 的是事前写定的主要对比，质量、费用、时间各自两个一起做 Holm 校正；另两个是事前列明的次要对比，只作描述。质量是写对的事实占比之差（个百分点）；费用和时间是倍数；最后两列是每次运行的差。", [
            ["对比", "63 条", "全清单", "费用", "时间", "被 K 拒绝的调用", "开的 subagent"]]
            + [[lb, eff(tc[k]["right_legacy_pct"], 8, "个百分点", corr), eff(tc[k]["right_pct"], 8, "个百分点", corr), rc(tc[k]["total_cost_peak"], 2, corr), rc(tc[k]["answer_s"], 2, corr), ci(tc[k]["capacity_rejects"]), ci(tc[k]["children"])] for k, lb, corr in CM])
        d.figure("told", f"{NEW}/told-limit.png", "办公报告题：K=2 和 K=8 各配工具说明里写明上限与否，四样量的组均值（细线是各组均值的 95% 区间；写对的占比、费用、时间按交出完整报告并判了分的运行，被拒绝的调用按全部运行）。")

    # ---- 4. depth
    d.add(f"### {SEC['depth']}、深度", "")
    p2all = {"est": p2["legacy_est"], "lo": p2["legacy_lo"], "hi": p2["legacy_hi"]}  # the 63 items, the fifth batch (K = 64) included
    assert p2["batches"] == 5 and p2all["lo"] > 0 and p2leg["lo"] < 0 < p2leg["hi"] and abs(p2all["est"] - p2leg["est"]) < 0.3
    d.p(f"**放开到深度 2，办公报告题的费用近两倍，写对的按事先定下的 63 条只多 {rnd(p2leg['est'])} 个百分点、区间含 0（全清单多 {rnd(p2k8['est'])}，显著）；评测集报告题和读代码题只是变贵；深度 3 没测出比深度 2 多写对。**")
    drow = lambda task, what, sc, word, legacy, cost, time, nd=1: [task, what, est(sc, nd, word), word, legacy, cost, time]  # noqa: E731
    p3leg = {"est": p3k8["legacy_est"], "lo": p3k8["legacy_lo"], "hi": p3k8["legacy_hi"]}
    p3time = {"est": p3k8["time_ratio"], "lo": p3k8["time_lo"], "hi": p3k8["time_hi"]}
    p3cost = {"est": p3k8["cost_ratio"], "lo": p3k8["cost_lo"], "hi": p3k8["cost_hi"]}
    srow = lambda key, label, v, what: lrow(LD[key], label, what, LD[key]["cells"][v])  # noqa: E731  (a row of the table from the cell behind the figure)
    d.tbl("depth", "放开深度以后的差别（{fig:d-quality}、{fig:d-cost}、{fig:d-time} 画了其中的大部分行；办公报告题深度 3 对 2、读代码题加并行提示的两行和两道 24 题的深度 2 没有画）。质量之差：办公报告题是写对的事实占比（个百分点），其余是得分；费用和时间是倍数。带括号的数：区间含 0（倍数是含 1），或者校正后不显著。办公报告题的“质量之差”和“判断”是全清单的，旁边一列是事先定下的 63 条和它自己的判断，结论以 63 条为准。"
          "带 ★ 的行是事前写定的主要对比，其余是事前列明的次要对比（没有校正）或事后合并。办公报告题前两行的时间里，有一批记的是整个进程的时长（含等 subagent 结束的时间）。", [
        ["任务", "对比", "质量之差", "判断", "办公报告题：事先定下的 63 条", "费用倍数", "时间倍数"],
        drow("办公报告题", "深度 2 对 1（K=8，四批合起来算，99 对，事后）", p2k8, verdict(p2k8, 8), leg_cell(p2leg), mul(p2cost), mul(p2time)),
        drow("", "深度 3 对 1（K=8，两批合起来算，事后）", p3k8, verdict(p3k8, 8), leg_cell(p3leg), mul(p3cost), mul(p3time)),
        drow("", "深度 3 对 2（K=8，两批合起来算，事后）", p32k8, verdict(p32k8, 8), leg_cell({"est": p32k8["legacy_est"], "lo": p32k8["legacy_lo"], "hi": p32k8["legacy_hi"]}), "—", "—"),
        drow("", "深度 3、K=64 对默认（相当于旧默认）★", od["facts"], verdict(od["facts"], 8), leg_cell(lg["old"]), mul(od["cost"]), mul(od["answer"])),
        srow("ws", "评测集填表题", 2, "深度 2 对 1"),
        srow("drb2", "评测集报告题", 2, "深度 2 对 1"),
        srow("code", "读代码题（原题面）", 2, "深度 2 对 1"), srow("code", "", 3, "深度 3 对 1"),
        drow("读代码题（加并行提示）", "深度 2 对 1", c["cmp"]["C4a"]["score"], verdict(c["cmp"]["C4a"]["score"], 5, True), "—", mul(c["cmp"]["C4a"]["model_cost_peak"], True), mul(c["cmp"]["C4a"]["seconds"], True)),
        drow("", "深度 3 对 1", c["cmp"]["C4b"]["score"], verdict(c["cmp"]["C4b"]["score"], 5, True), "—", mul(c["cmp"]["C4b"]["model_cost_peak"], True), mul(c["cmp"]["C4b"]["seconds"], True)),
        srow("p4", "小编程题（原题面）", 2, "深度 2 对 1"), srow("p4", "", 3, "深度 3 对 1"),
        srow("wide", "限时 24 题（加并行提示，五个 K 合起来）", 2, "深度 2 对 1"),
        srow("free", "不限时 24 题（加并行提示，K=4、8、16 合起来）", 2, "深度 2 对 1"),
        srow("xl", "大型编码题（原题面）", 2, "深度 2 对 1"),
        srow("xln", "大型编码题（加不复核提示）", 2, "深度 2 对 1")])
    assert lg["old"]["lo"] < 0 < lg["old"]["hi"]
    d.figure("cost-d", f"{NEW}/cost-by-depth.png", "各任务一次运行的平均费用（元）随深度怎么变。细线是各组均值的 95% 区间；深蓝色是默认。每一格只画同一批跑的几组，所以数和别的表里另一批的数会差一点；“办公报告题，K=64”一格的深度 1 也是 K=64，不是默认。""读代码题一格画的是题面加并行提示的三组（原题面的深度 2、3 在{tab:depth}）；不限时 24 题一格横轴上的 1、2 是深度。", hold=True)
    dk8 = cst["depth_k8"]
    more8 = sorted([dk8[1]["mean"] - dk8[0]["mean"], dk8[2]["mean"] - dk8[0]["mean"]])
    more64 = sorted([ck["d2k64"]["mean"] - ck["d2k64"]["base_mean"], ck["old"]["mean"] - ck["old"]["base_mean"]])
    assert 6 < more8[0] < more8[1] < 8.5 and 14 < more64[0] < more64[1] < 17.5 and kd["cmp"]["D2"]["total_cost_peak"]["lo"] > 1
    assert verdict(xk["DN"]["score"], 5) == "没有差别" and verdict(p32k8, 8) == "没有差别" and p32k8["batches"] == 2 and p3k8["batches"] == 2 and p3k8["lo"] < 0 < p3k8["hi"]
    assert fd_["score"]["lo"] > 0 and fd_["model_cost_peak"]["hi"] < 1 and all(q["lo"] < 1 < q["hi"] for q in (c["cmp"]["C4a"]["model_cost_peak"], xk["DN"]["model_cost_peak"]))
    assert xl_depth[-1] == xk["DE"]["answer_s"]["est"] and xk["DE"]["answer_s"]["lo"] > 1 and all(xl["depth_hi"][q]["answer_s"]["lo"] < 1 for q in ("DE16", "DE64"))
    assert verdict(p2k8, 8) == "显著变好" and verdict(od["facts"], 8) == "没有差别" and verdict(fd_["score"], 5, True) == "显著变好" and fd_["score"]["est"] < 0.5
    cn2, cn3 = LD["code"]["cells"][2], LD["code"]["cells"][3]
    assert cn2["c"]["lo"] > 1 and cn3["c"]["lo"] > 1 and cn2["t"]["lo"] > 1 and cn3["t"]["lo"] < 1 < cn3["t"]["hi"] and verdict(cn2["q"], 5) == verdict(cn3["q"], 5) == "没测出差别"
    crows_ = cd.R("results/analysis-v2/rows-code-c1w1.csv")
    w1 = lambda g, col: st.mean(cd.num(r.get(col)) or 0 for r in crows_ if r["group"] == g and r["task"] == "w1-memory-plugin")  # noqa: E731
    c1k = [st.mean(cd.num(r.get("children")) or 0 for r in crows_ if r["group"] == g and r["task"] == "c1-subagent-limits") for g in ("D1-K8", "D2-K8", "D3-K8")]
    w1c = cd.contrast([r for r in crows_ if r["task"] == "w1-memory-plugin"], "D2-K8", "D1-K8", lambda r: cd.num(r["model_cost_peak"]), "ratio")
    assert 2.5 < w1("D2-K8", "children_d2") < 3.5 and w1c["lo"] > 1 and 1.7 < w1c["est"] < 1.9 and c1k[0] == 0 and max(c1k) < 0.5
    p4rows = [r for r in cd.R("results/analysis-v2/rows-code.csv") if r["task"] == "p4-python"]
    opened = lambda r: (cd.num(r.get("children")) or 0) > 0  # noqa: E731
    p4open = {g: sum(1 for r in p4rows if r["group"] == g and opened(r)) for g in ("D1-K8", "D2-K8", "D3-K8")}
    p4deep = [r for r in p4rows if r["group"] in ("D2-K8", "D3-K8")]
    p4cost = [st.mean(cd.num(r["model_cost_peak"]) for r in p4deep if opened(r) == flag) for flag in (True, False)]
    assert p4open == {"D1-K8": 0, "D2-K8": 1, "D3-K8": 4} and len(p4deep) == 20 and p4cost[0] > 2 * p4cost[1]
    conf_t2 = next({"est": r_["time_ratio"], "lo": r_["time_lo"], "hi": r_["time_hi"]} for r_ in o["depth_rows"] if r_["batch"] == "confirm" and r_["depth"] == 2)  # the main office batch alone
    assert conf_t2["lo"] < 1 < conf_t2["hi"] and dq("xl", 2, "t")["lo"] < 1 < dq("xl", 2, "t")["hi"] and c["cmp"]["C4a"]["seconds"]["lo"] < 1
    d.add(f"- 办公报告题上，放开到深度 2 或 3，一次任务多花 {rnd(more8[0])}–{rnd(more8[1])} 元；K 也放到 64，多花 {more64[0]:.0f}–{more64[1]:.0f} 元（{{fig:cost-d}}）。"
          f"换来的写对的事实占比只多几个百分点。按事先定下的 63 条，四批合起来是 {ci(p2leg)}，区间含 0；把 K 也放到 64 的第五批算上是 {ci(p2all)}。"
          f"按全清单是 {ci(p2k8)}：四批单看都测不出，合起来算才显著（附录的{{fig:depth}}）。深度 3 没测出比深度 2 多。",
          f"- 评测集报告题上深度 2 也更贵；评测集填表题上质量、费用、时间都没测出差别（{ci(dq('ws', 2))}，{x(dq('ws', 2, 'c'))}，{x(dq('ws', 2, 't'))}）。读代码题原题面下，深度 2、3 的模型费是 {rnd(cn2['c']['est'], 2)}、{rnd(cn3['c']['est'], 2)} 倍，得分没测出变化："
          f"多花的钱在写方案那道题上，模型在第 2 层又开了 {rnd(w1('D2-K8', 'children_d2'), 0)} 个左右，这道题的模型费是深度 1 的 {rnd(w1c['est'], 2)} 倍。题面加并行提示时，深度 1 的费用本来就高（{{fig:cost-d}} 的读代码题一格画的是这一套），深度 2、3 没测出更贵。",
          f"- 小编程题上模型在深度 1 时一次都不开 subagent；深度 2 的 10 次里有 {p4open['D2-K8']} 次、深度 3 有 {p4open['D3-K8']} 次开了（各 1–2 个），"
          f"这 {p4open['D2-K8'] + p4open['D3-K8']} 次的模型费平均 {rnd(p4cost[0], 2)} 元，其余没开的 {rnd(p4cost[1], 2)} 元，得分都是满分。主 agent 看到的工具和提示在三种深度下完全相同，各只有 10 次，这个差别是不是偶然分不清（只作描述）。",
          "- 各批事前写的、会影响深度放不放开的读法有八条（附录的{tab:d-readings}），没有一条给出放开；其中两条的结果落在读法没有预设说法的地方。",
          f"- 时间：深度 2 没有让任何一种任务显著更快。显著更慢的两处（读代码题原题面 {x(dq('code', 2, 't'))}、大型编码题加不复核提示 {x(dq('xln', 2, 't'))}），都只是刚好显著，区间下端都是 1.01；"
          f"办公报告题四批合起来是 {xci(dq('office', 2, 't'))}、主要的一批单看是 {xci(conf_t2)}，读代码题加并行提示时是 {x(c['cmp']['C4a']['seconds'])}，大型编码题原题面是 {x(dq('xl', 2, 't'))}，区间都含 1。",
          "- 办公报告题以外，测出好处的只有不限时 24 题（得分高不到半分、模型费略低），不值得为它改默认。大型编码题加不复核提示时深度 2 更慢，K 放到 16、64 以后这个差别没有再出现（附录{tab:score} 的“大型编码题：K=16、64 时的深度 2”两行）。",
          f"- 相当于旧默认的设置开的 subagent 是现在的近 5 倍（最多一次 {od['kids_max']:.0f} 个），多花的钱没有换来测得出的提高；把对照换成同批的默认和深度 1、K=64 两组的平均，结果相近（{{tab:other}} 注 2）。",
          f"- 别人的实验里放开深度是变差的，见“{RELATED}”。", "")
    d.release()
    assert 4.3 < od["kids"] / m["D1-K8"]["kids"] < 5.3

    # ---- 5. where the money and the time go
    d.add(f"### {SEC['spend']}、钱和时间花在哪", "")
    mu, rl, pg = E["merge_union"], E["relay"], E["pages"]
    assert 0.6 < pg["more_over_default"]["widest"][0] < pg["more_over_default"]["low"] < pg["more_over_default"]["widest"][1] < 0.8 and abs(pg["more_over_default"]["low"] - pg["more_over_default"]["high"]) < 0.03
    assert pg["E-D0"]["n"] == 40 and 15 < pg["E-D0"]["saved50"] < 25 and pg["D0"]["saved50"] == 0
    assert abs(mu["M2"]["merged"] - sa["total"]["high"]) < 1.5 and mu["M4"]["merged"] > sa["total"]["high"] + 5 and mu["M2"]["union"] < mu["M4"]["union"] and 52 < mu["M2"]["one"] < 56
    assert rl["runs"] == 90 and 0.02 < rl["share_range"][0] < rl["share_range"][1] < 0.06 and rl["depth"]["lo"] < 0 < rl["depth"]["hi"] and rl["keep"]["est"] < 0 and rl["keep"]["lo"] < 0 < rl["keep"]["hi"] + 0.5
    fshare = [(fm_["W-D1-K8"]["cost"] - fw["W-D1-K8"]["rest"]["cost"]) / fm_["W-D1-K8"]["cost"], (fm_["W-D1-K8"]["answer"] - fw["W-D1-K8"]["rest"]["answer"]) / fm_["W-D1-K8"]["answer"]]
    xshare = [(xm["W-D1-K8"]["cost"] - xm["W-N-D1-K8"]["cost"]) / xm["W-D1-K8"]["cost"], (xm["W-D1-K8"]["answer"] - xm["W-N-D1-K8"]["answer"]) / xm["W-D1-K8"]["answer"]]
    assert 0.2 < fshare[0] < 0.26 and 0.15 < fshare[1] < 0.2 and all(0.58 < v < 0.68 for v in xshare)
    z150, z250, dh1 = dc["Z150"]["right_pct"], dc["Z250"]["right_pct"], dc["H1"]["right_pct"]
    assert z150["lo"] > 0 and z250["lo"] < 0 < z250["hi"] and dh1["lo"] > 0 and 0.5 < z150["est"] / dh1["est"] < 0.6 and z250["est"] / dh1["est"] < 0.3
    dl150, dl250 = dc["P150"]["right_legacy_pct"], dc["P250"]["right_legacy_pct"]
    zl150, zl250, dh1l = dc["Z150"]["right_legacy_pct"], dc["Z250"]["right_legacy_pct"], dc["H1"]["right_legacy_pct"]
    assert verdict(dl150, 8, True) == "没测出差别" and verdict(dl250, 8, True) == "显著变差" and zl150["lo"] > 0 and zl250["lo"] < 0 < zl250["hi"] and 0.5 < zl150["est"] / dh1l["est"] < 0.65
    assert verdict(lg["more"], 8) == "显著变差" and all(verdict(dc[q]["right_pct"], 8, True) == "显著变差" for q in ("P150", "P250"))
    d.p(f"**调研类任务的钱一半是搜索费。办公报告题上让单 agent 自己多查（题面加多查提示），搜索量到了默认的水平：按事先定下的 63 条，多查 150/250 比默认少写对 {rnd(-dl150['est'])} 个百分点、没测出差别，"
        f"多查 250/500 少 {rnd(-dl250['est'])} 个、显著（全清单少 {rnd(-dc['P150']['right_pct']['est'])} 和 {rnd(-dc['P250']['right_pct']['est'])} 个，都显著）；"
        "默认比不开多写对的那些，它补上的不到六成；四份独立的单 agent 报告合并，才不比默认少。"
        f"大型编码题的钱和时间大半花在复核上（代码写完以后，模型又派一批 subagent 去检查）；不限时 24 题上复核占钱的 {pct(fshare[0])}、时间的 {pct(fshare[1])}。**")
    fnone = o["floor_none"]  # no subagents, in the batch of the search-more sentence
    share_full = 1 - fl["PRIM"]["right_pct"]["est"] / fnone["right_pct"]["est"]  # part of the gap to the default that searching more closes
    share_leg = 1 - lg["more"]["est"] / fnone["legacy"]["est"]
    msr = o["merge_search_ratio"]
    search_share = (m["D1-K8"]["cost"] - m["D1-K8"]["model_cost"]) / m["D1-K8"]["cost"]
    dnone = {k_: cd.flip(dict({"a": "D1-K8", "b": "D0"}, **dc["H1"][k_])) for k_ in ("right_pct", "right_legacy_pct", "total_cost_peak", "answer_s", "search_aux")}  # no subagents against the default, the two-dose batch
    one_ = lambda q: q["lo"] <= 1 <= q["hi"]  # noqa: E731
    xq = lambda q: x(q) + ("（区间含 1）" if one_(q) else "")  # noqa: E731
    drow_ = lambda label, q: ["", label, str(dc[q]["right_pct"]["n"]), (xq(dc[q]["search_aux"]) if dc[q]["search_aux"]["n"] == dc[q]["right_pct"]["n"] else xq(dc[q]["search_aux"]).replace("）", f"；{dc[q]['search_aux']['n']} 对）")), xq(dc[q]["total_cost_peak"]), xq(dc[q]["answer_s"]), ci(dc[q]["right_pct"]), ci(dc[q]["right_legacy_pct"])]  # noqa: E731
    d.tbl("spend", "办公报告题：不开 subagent 的几种做法（另加一行默认加都写进去提示）和默认比。每行只和同一批里的默认比，按批分成三段；搜索请求、费用、时间三列是对默认的倍数。"
          "合并指同一道题让几个单 agent 各自独立写一份报告，再由一个单 agent 合并成一份（下文叫合并稿）；费用算这几次运行的总和，时间按几份同时写、写完再合并算。"
          f"第一段的第三行是默认设置加都写进去提示：{wfl['runs'] // 4} 次里有 {wfl['early']} 次主 agent 没等 subagent 回来就结束，没交出完整的报告，这一行只算其余的（{wfl['runs'] // 4} 次全算的数在方法补充）。", [
        ["批", "做法", "配对数", "搜索请求", "费用", "时间", "写对的事实占比之差（个百分点）", "只算事先定下的 63 条"],
        ["多查 100/100 那一批", "不开 subagent", str(fnone["right_pct"]["n"]), xq(fnone["search_aux"]), xq(fnone["total_cost_peak"]), xq(fnone["seconds"]), ci(fnone["right_pct"]), ci(fnone["legacy"])],
        ["", "不开 subagent + 多查 100/100", str(fl["PRIM"]["right_pct"]["n"]), xq(fl["PRIM"]["search_aux"]), xq(fl["PRIM"]["total_cost_peak"]), xq(fl["PRIM"]["seconds"]), ci(fl["PRIM"]["right_pct"]), ci(lg["more"])],
        ["", "默认 + 都写进去提示（只算交出完整报告的）", str(kd_["right_pct"]["n"]), xq(kd_["search_aux"]), xq(kd_["total_cost_peak"]), xq(kd_["seconds"]), ci(kd_["right_pct"]), ci(lg["keep_done"])],
        ["多查 150/250、250/500 那一批", "不开 subagent", str(dnone["right_pct"]["n"]), xq(dnone["search_aux"]), xq(dnone["total_cost_peak"]), xq(dnone["answer_s"]), ci(dnone["right_pct"]), ci(dnone["right_legacy_pct"])],
        drow_("不开 subagent + 多查 150/250", "P150"), drow_("不开 subagent + 多查 250/500", "P250"),
        ["合并稿（两批合起来算）", "两份报告合并", str(mp2["facts"]["n"]), x(msr["M2"]), xq(mp2["cost"]), xq(mp2["time"]), ci(mp2["facts"]), ci(mp2["legacy"])],
        ["", "四份报告合并", str(mp4["facts"]["n"]), x(msr["M4"]), xq(mp4["cost"]), xq(mp4["time"]), ci(mp4["facts"]), ci(mp4["legacy"])]])
    assert kd_["search_aux"]["lo"] < 1 < kd_["search_aux"]["hi"] and all(q["hi"] < 1 for q in (fnone["search_aux"], fl["PRIM"]["search_aux"])) and fnone["seconds"]["hi"] < 1 and dnone["right_pct"]["hi"] < 0
    assert fnone["right_pct"]["hi"] < 0 and fnone["legacy"]["hi"] < 0 and lg["more"]["hi"] < 0 and lg["more_vs_none"]["lo"] < 0 < lg["more_vs_none"]["hi"]
    assert 0.3 < share_leg < 0.4 and 0.45 < share_full < 0.55 and fl["EF"]["right_pct"]["lo"] > 0
    assert verdict(mp2["facts"], 8) == verdict(mp2["legacy"], 8) == "没有差别" and mp4["facts"]["lo"] > 0 and mp4["legacy"]["lo"] > 0 and 0.9 < msr["M4"] < 1.1 and msr["M2"] < 0.6
    assert mp2["cost"]["hi"] < 1 and kd_["right_pct"]["lo"] > 0 and lg["keep_done"]["lo"] < 0 < lg["keep_done"]["hi"] and 0.45 < search_share < 0.56
    bt1, bt2 = ds["by_task"]["o1-singapore-trip"], ds["by_task"]["o2-server-cpu-report"]
    dleg = {q: dc[q]["right_legacy_pct"] for q in ("P150", "P250")}
    hm = dc["HM"]["right_pct"]
    vol = {g: dm[g]["search"] / dm["D1-K8"]["search"] for g in ("E-D0", "N-D0")}
    st1, st2 = ds["search_task"]["o1-singapore-trip"], ds["search_task"]["o2-server-cpu-report"]
    assert st1["E-D0"]["lo"] > 1 and st1["N-D0"]["est"] > 1.25 and all(q["lo"] < 1 < q["hi"] for q in st2.values()) and ds["timeouts"] == 0
    hm_all = ds["extra"]["every_run"]["more_vs_less"]
    assert hm_all["lo"] < 0 < hm_all["hi"] and ds["extra"]["volume"]["more_searches"]["more"] == "N-D0" and ds["extra"]["volume"]["more_searches"]["ratio"] < 1.3
    assert all(0.7 <= v <= 1.4 for v in vol.values()) and all(dpg[g]["low"] >= 0.6 * dpg["D1-K8"]["low"] for g in ("E-D0", "N-D0")) and all(dm[g]["search"] < 0.7 * 455.4 for g in ("E-D0", "N-D0"))
    assert all(bt1[q]["hi"] < 0 for q in ("P150", "P250")) and all(bt2[q]["lo"] < 0 < bt2[q]["hi"] for q in ("P150", "P250")) and dleg["P150"]["lo"] < 0 < dleg["P150"]["hi"] and dleg["P250"]["hi"] < 0
    assert hm["hi"] < 0 and dc["HM"]["search_aux"]["lo"] < 1 < dc["HM"]["search_aux"]["hi"] and dm["E-D0"]["pruned"] == 1 and dm["N-D0"]["pruned"] == 0 and dm["E-D0"]["n"] == 39 and dm["N-D0"]["n"] == 40
    assert 350 < dpg["E-D0"]["saved"] < 400 and 780 < dpg["N-D0"]["saved"] < 830 and dpg["E-D0"]["fetch"] < 25 and dpg["N-D0"]["fetch"] < 16 and dpg["D1-K8"]["fetch"] > 100 and dpg["D1-K8"]["saved"] < 20
    assert all(22 < dm[g]["peak_median"] / 1e4 < 24.5 for g in ("E-D0", "N-D0", "D1-K8")) and dc["P150"]["model_cost_peak"]["hi"] < 0.55 and dc["P250"]["model_cost_peak"]["hi"] < 0.5
    assert {q_["n"] for q_ in (bt1["P150"], bt1["P250"], bt2["P150"], bt2["P250"])} <= {19, 20}
    d.tbl("dose-task", "办公报告题：多查 150/250 和多查 250/500 对同批默认，按题分开（每题 19–20 对）。", [
        ["题", "提示", "写对的事实占比之差（个百分点）", "搜索请求（对默认的倍数）"],
        ["旅行攻略题", "多查 150/250", ci(bt1["P150"]), xci(st1["E-D0"])], ["", "多查 250/500", ci(bt1["P250"]), xci(st1["N-D0"])],
        ["CPU 选型题", "多查 150/250", ci(bt2["P150"]), xci(st2["E-D0"])], ["", "多查 250/500", ci(bt2["P250"]), xci(st2["N-D0"])]])
    d.figure("dose", f"{NEW}/task-dose.png", "办公报告题：不开 subagent、题面加多查 150/250 或多查 250/500 的两组，和同一批的不开 subagent、默认比。五栏从上到下是写对的事实占比、搜索请求数、打开的网页数（下限）、费用、时间。"
             "“命令里直接抓”指模型在 shell 命令里用 curl 一类的办法抓网页。细线是各组均值的 95% 区间；每组 39–40 份报告。", hold=True)
    d.figure("search", f"{NEW}/office-search.png", "办公报告题：各组写对的事实占比和搜索请求数一起涨；同样的搜索量，单 agent 多查的三组（黑点）落在线下面，几份报告合并的（⊕）落在线上面。每个点是一组运行的均值，同一种设置跑过几批的各算一个点；"
             f"直线按{{tab:office}} 的六组拟合（不开、K=1、K=2、K=4、默认、深度 2）。", hold=True)
    mgs = sorted(r_["merge_search"] for b_ in ("office-merge", "office-merge-b") for r_ in cd.J(f"results/analysis-{b_}/merge-stats.json")["rows"])
    assert len(mgs) == 60 and mgs[0] == 0 and mgs[-1] == 22 and 6 < st.mean(mgs) < 9
    OV = E["overlap"]
    SD = MX["senders"]  # the judged handed-back messages: which subagent's message holds each fact stated correctly
    sd_also, sd_quote, sd_short = (sum(v_[k_] for v_ in SD.values()) for k_ in ("also_total", "also_quote_total", "also_value_short_total"))
    assert sd_quote < 20 and 0.55 < sd_short / (sd_also - sd_quote) < 0.7 and all(0.93 < v_["only_one_share6"] < 0.99 for v_ in SD.values()) and sum(v_["messages"] for v_ in SD.values()) > 600
    SDL = (("office-confirm/D1-K8", "默认"), ("office-confirm/D2-K8", "深度 2"), ("office-floor/D1-K8", "默认（和下一组同批）"), ("office-floor/N-D1-K8", "默认 + 都写进去提示"), ("office-highk/W-D2-K64", "深度 2、K=64"))
    assert [k_ for k_, _ in SDL] == list(SD) and [r_["label"] for r_ in rl["rows"]] == [lb_ for _, lb_ in SDL] and all(abs(SD[k_]["facts_right"] - r_["handed"]) < 0.05 and SD[k_]["runs"] == r_["runs"] for (k_, _), r_ in zip(SDL, rl["rows"]))
    assert all(0.85 < v_["only_one_share"] < 0.93 and 0.93 < v_["placed_share"] < 0.96 and 0.35 < v_["top_sender_share"] < 0.6 and 3 < v_["senders"] < 4.2 for v_ in SD.values())
    ovd = next(r_ for r_ in OV if r_["group"] == "D1-K8")
    assert len(OV) == 7 and all(0.04 < r_["page_cross_share"] < 0.12 and r_["query_cross"] < 1.6 and r_["query_cross_share"] < 0.004 for r_ in OV) and ovd["query_cross"] < 1 and ovd["n"] == 40
    assert all(r_["page_cross_share"] < 0.12 for r_ in OV if r_["group"] in ("D2-K8", "W-D2-K64", "W-D3-K64")) and min(r_["page_cross_share"] for r_ in OV if r_["group"] in ("D2-K8", "W-D2-K64", "W-D3-K64")) > 0.08
    d.add(f"- **让单 agent 多查，能补上一部分；三种提示里两种仍显著少于默认。** 多查 100/100 的搜索请求是默认的 {rnd(fl['PRIM']['search_aux']['est'], 2)} 倍，按事先定下的 63 条比不开多 {rnd(lg['more_vs_none']['est'])} 个百分点、区间含 0（全清单多 {rnd(fl['EF']['right_pct']['est'])}，显著），"
          f"补上了不开和默认之间差距的 {pct(share_leg)}（全清单 {pct(share_full)}），仍比默认少 {rnd(-lg['more']['est'])} 个百分点，显著。"
          f"多查 150/250 和多查 250/500 的搜索请求和默认没测出差别。按 63 条，同一批里默认比不开多写对 {rnd(dh1l['est'])} 个百分点，这两种比不开多 {rnd(zl150['est'])} 和 {rnd(zl250['est'])} 个（后一个区间含 0），"
          f"比默认少 {rnd(-dl150['est'])}（没测出差别）和 {rnd(-dl250['est'])}（显著）。按全清单，比不开多 {rnd(z150['est'])} 和 {rnd(z250['est'])} 个（后一个区间含 0），比默认少 {rnd(-dc['P150']['right_pct']['est'])} 和 {rnd(-dc['P250']['right_pct']['est'])} 个（都显著）"
          f"（{{tab:spend}}、{{fig:dose}}、{{fig:search}}；各组的数在附录的{{tab:dose}}）。",
          "- **少写对的主要在旅行攻略题上（{tab:dose-task}）。** 这道题上多查 150/250 的搜索请求比默认还多，多查 250/500 的估计值也更高（区间含 1），写对的仍然少；CPU 选型题上写对的差区间含 0。",
          f"- **多出来的是搜索请求和下载量，逐个打开来读的网页并没有多。** 多查 150/250 和多查 250/500 用 web_fetch 逐个打开的网页只有 {rnd(dpg['E-D0']['fetch'], 0)} 和 {rnd(dpg['N-D0']['fetch'], 0)} 个（同批不开 subagent 是 {rnd(dpg['D0']['fetch'], 0)} 个，默认 {rnd(dpg['D1-K8']['fetch'], 0)} 个），"
          f"模型费是默认的 {rnd(dc['P150']['model_cost_peak']['est'], 2)} 和 {rnd(dc['P250']['model_cost_peak']['est'], 2)} 倍。要求打开的网页越多，模型越是写脚本成批下载、存到磁盘再检索，而不是一个一个读："
          f"存盘的网页，多查 100/100 平均 {rnd(pg['E-D0']['saved'], 0)} 个（{{fig:pages}}），多查 150/250 和多查 250/500 是 {rnd(dpg['E-D0']['saved'], 0)} 和 {rnd(dpg['N-D0']['saved'], 0)} 个（{{fig:dose}}）。"
          "所以搜索量到了默认的水平时，单 agent 更便宜（搜索费差不多，模型费不到一半），但要多等六成时间。",
          f"- **再多查一档会不会更好，没有回答。** 事前想用多查 250/500 对多查 150/250 来看，但前者实际的搜索请求只是后者的 {x(dc['HM']['search_aux'])}，没有拉开；写对的反而少 {rnd(-hm['est'])} 个百分点（{ci(hm)}；"
          f"把没交出完整报告的那一次运行也算进去是 {ci(hm_all)}）。这一批只试了“题面加一句要求”这一种让单 agent 多查的办法。",
          f"- **上下文窗口没有用满。** 这两种提示下，主 agent 单次请求的输入最多时，中位是 {rnd(dm['E-D0']['peak_median'] / 1e4)} 万和 {rnd(dm['N-D0']['peak_median'] / 1e4)} 万 token（同批默认的主 agent {rnd(dm['D1-K8']['peak_median'] / 1e4)} 万；"
          f"各组里最大的一次是 {dm['E-D0']['peak_max'] / 1e4:.0f} 万和 {dm['N-D0']['peak_max'] / 1e4:.0f} 万，窗口是 100 万）；被 DSH 裁剪过上下文的运行各有 {dm['E-D0']['pruned']} 次和 {dm['N-D0']['pruned']} 次（DSH 不等窗口用满就会裁剪），没有一次运行超时。"
          "但下载的网页是存盘检索的，没有读进上下文；少写对和一个上下文能读多少有没有关系，这份数据说明不了。",
          f"- **两份合并和默认没有差别，四份合并不比默认少。** 四份合并的搜索量和默认差不多，两批合起来算，比默认多写对 {rnd(mp4['legacy']['est'])} 个百分点（按事先定下的 63 条；全清单 {rnd(mp4['facts']['est'])}，都显著）；按全清单分批是 {ci(mp4['batch']['a'])} 和 {ci(mp4['batch']['b'])}，后一批区间含 0"
          "（前一批拿来合并的报告和对照的默认组是前一天跑的，后一批是同一批）。合并用的那段话要求“有来源的事实都保留”，默认的主 agent 没有被这样要求；"
          f"和题面加了都写进去提示、交出完整报告的默认比（只有后一批能比），四份合并是 {ci(o['m4_vs_keep'])}（{o['m4_vs_keep']['n']} 对），两份合并是 {ci(o['m2_vs_keep'])}。"
          "所以能说的是：四份合并写对的不比默认少；默认比不开多写对的那些，不一定要靠 subagent 才补得上。",
          f"- **合并稿里的事实从哪来（{{fig:merge-cover}}）。** 一份单 agent 报告平均写对 {mu['M2']['one']:.0f} 条；两份里至少有一份写对的是 {mu['M2']['union']:.0f} 条，四份是 {mu['M4']['union']:.0f} 条；"
          f"合并稿写对 {mu['M2']['merged']:.0f} 条和 {mu['M4']['merged']:.0f} 条，默认是 {sa['total']['high']:.0f} 条。合并这一步自己查得很少（一次平均 {st.mean(mgs):.0f} 个搜索请求，最多 {mgs[-1]:.0f} 个），题面要求它只在几份说法不一致、需要核实的时候再去查。",
          f"- **主 agent 汇总时丢得不多。** subagent 交回的消息里写对的事实，有 {pct(rl['share_range'][0])}–{pct(rl['share_range'][1])} 没进最终报告（每份 {rl['lost_range'][0]:.0f}–{rl['lost_range'][1]:.0f} 条）。"
          "这只算了 subagent 发回的文字，它们直接写进文件的不算；深度 2 时第 2 层交给第 1 层的那一步没有量。深度 2 没测出比深度 1 丢得更多（附录的{tab:relay}）。",
          f"- **同一次运行里，各个 agent 查的东西很少重复（{{fig:overlap}}、{{tab:overlap}}）。** 办公报告题主要的一批里，默认设置下一次运行用 web_fetch 打开 {rnd(ovd['pages'], 0)} 个不同的网页，其中 {rnd(ovd['page_cross'], 0)} 个（{pct(ovd['page_cross_share'])}）有两个以上的 agent 打开过；"
          f"搜索的查询词 {rnd(ovd['queries'], 0)} 个里重复的平均不到 1 个。放开深度以后开的 agent 多了，重复的仍只有一成左右。这是按网址和查询词逐字比的：换个说法的查询词、内容相同的不同网页算不出来。",
          f"- **各个 subagent 交回的事实也很少重复（{{fig:senders}}、{{tab:senders}}）。** 判过的 {sum(v_['runs'] for v_ in SD.values())} 次运行（subagent 一共交回 {sum(v_['messages'] for v_ in SD.values())} 条消息）里，写对的事实有 {pct(min(v_['placed_share'] for v_ in SD.values()))}–{pct(max(v_['placed_share'] for v_ in SD.values()))} 能对上是哪个 subagent 交回的；"
          f"对得上的里面，{pct(min(v_['only_one_share'] for v_ in SD.values()))}–{pct(max(v_['only_one_share'] for v_ in SD.values()))} 只在一个 subagent 的消息里出现。交得最多的那个 subagent 占三成半到六成（一次运行有 3–4 个 subagent 交回消息）。这是按原话和取值逐字找的，换了说法的重复找不出来。算作“别的 subagent 也有”的 {sd_also} 条里，原话在两个 subagent 的消息里都有的只有 {sd_quote} 条，其余是取值在别处也出现，"
          f"其中 {pct(sd_short / (sd_also - sd_quote))} 的取值不到 6 个字（比如 S$14）；只算 6 个字以上的取值，只在一个 subagent 的消息里出现的是 {pct(min(v_['only_one_share6'] for v_ in SD.values()))}–{pct(max(v_['only_one_share6'] for v_ in SD.values()))}。",
          f"- **被拒绝的调用本身花的钱很少（{{tab:rejects}}）。** 模型为没开成的 subagent 写的任务说明，办公报告题默认设置下每次运行约 {rnd(rj8['args_yuan'], 2)} 元，占模型费的 {pct(rj8['args_share'], 1)}；"
          f"发出的工具调用全是被拒绝的开 subagent 调用的模型请求，每次运行 {rnd(rj8['dead_steps'])} 步，整步的费用 {rnd(rj8['dead_step_yuan'], 2)} 元（{pct(rj8['dead_share'], 1)}）。两个数有重叠，合起来不到这一组模型费的 3%。"
          f"全部运行加在一起，这两项是 {MX['rejected']['args_yuan']:.0f} 元和 {MX['rejected']['dead_step_yuan']:.0f} 元，模型费一共 {MX['rejected']['model_yuan']:,.0f} 元。被拒绝以后模型怎么改做法、对质量有没有影响，这里没有量。",
          f"- **都写进去提示**让交出完整报告的运行多写对几个百分点（只算事先定下的条目时区间含 0），其中从汇总这一步少丢的不到 2 条；这些运行开的 subagent 也更多（{rnd(wfl['kids'][1])} 个对 {rnd(wfl['kids'][0])} 个）。"
          "代价是主 agent 更容易没等 subagent 回来就结束（DSH 缺陷第 4 条）。",
          f"- **搜索费。** 联网任务的费用有一半左右是搜索费（办公报告题默认组 {pct(search_share)}）。每个搜索请求里，模型顺带写的那段回答占这个请求费用的 {iss['answer_share']:.0f}%，搜索插件并不用它。", "")
    d.release()
    d.figure("overlap", f"{NEW}/overlap-agents.png", "办公报告题：一次运行里各个 agent（主 agent 和 subagent）用 web_fetch 打开的不同网页数，橙色是两个以上的 agent 都打开过的。柱子上是总数和其中重复的个数；设置下面的灰字是平均每次运行有几个 agent 联过网。"
             "前五种设置来自办公报告题主要的一批（各 40 次运行），后两种来自 K=64 批（各 20 次）。")
    d.tbl("overlap", "办公报告题：同一次运行里各个 agent 查的东西重复多少（每次运行的平均；前五行是办公报告题主要的一批，后两行是 K=64 批）。查询词按小写、去掉多余空格以后逐字比；网页按网址比（去掉协议、www. 和末尾的斜杠）。只算搜索工具和 web_fetch，不含在 shell 命令里抓的网页。", [
        ["设置", "联网的 agent 数", "不同的查询词", "两个以上的 agent 都查过的", "用 web_fetch 打开的不同网页", "两个以上的 agent 都打开过的", "占打开的网页"]]
        + [[r_["label"], rnd(r_["agents"]), rnd(r_["queries"], 0), rnd(r_["query_cross"]), rnd(r_["pages"], 0), rnd(r_["page_cross"]), pct(r_["page_cross_share"])] for r_ in OV])
    d.figure("senders", f"{NEW}/handback-senders.png", "办公报告题：subagent 交回给主 agent 的消息里写对的事实，只在一个 subagent 的消息里出现的有多少条，别的 subagent 的消息里也有的有多少条（柱子上是这两个数；每次运行的平均）。五组各取前 10 次重复。")
    d.tbl("senders", "办公报告题：交回的消息里写对的事实是哪个 subagent 交回的（个数和条数是每次运行的平均，两个百分比是各次运行合起来算的比例）。一条事实按判分时引的那句原文去找它出自哪个 subagent 的消息；"
          "原文在两个 subagent 的消息里都有，或者这条事实的取值在别的 subagent 的消息里也出现，就算“别的 subagent 也有”。", [
        ["组", "运行数", "交回过消息的 subagent（其中有事实对得上的）", "交回的消息里写对", "对得上是谁交回的", "只在一个 subagent 的消息里", "别的 subagent 也有", "交得最多的一个占"]]
        + [[lb_, str(SD[k_]["runs"]), f"{rnd(SD[k_]['senders'])}（{rnd(SD[k_]['senders_with_facts'])}）", rnd(SD[k_]["facts_right"]), pct(SD[k_]["placed_share"]), f"{rnd(SD[k_]['only_one_sender'])}（{pct(SD[k_]['only_one_share'])}）", rnd(SD[k_]["also_elsewhere"]), pct(SD[k_]["top_sender_share"])] for k_, lb_ in SDL])
    def rjrow(task_, label_, cells_):  # one row of the table of rejected calls: the groups of `cells_` (batch, group) together
        vs_ = [(mrj[b_][g_], mtb[b_][g_]) for b_, g_ in cells_]
        n_ = sum(v_["runs"] for v_, _ in vs_)
        w_ = lambda k_: sum(v_[k_] * v_["runs"] for v_, _ in vs_) / n_  # noqa: E731
        fee_ = w_("model_yuan")
        return [task_, label_, str(n_), rnd(sum(t_["children"] for _, t_ in vs_) / n_), rnd(w_("depth")), rnd(w_("cap")), f"{rnd(w_('args_yuan'), 2)}（{pct(w_('args_yuan') / fee_, 1)}）",
                f"{rnd(w_('dead_steps'))} 步，{rnd(w_('dead_step_yuan'), 2)}（{pct(w_('dead_step_yuan') / fee_, 1)}）"]
    off_def = sorted(mrj[b_][g_]["depth"] for b_, g_ in (("main-office", "D1-K8"), ("office-confirm", "D1-K8"), ("office-dose", "D1-K8"), ("office-floor", "D1-K8"), ("office-highk", "W-D1-K8"), ("wait-office-2", "W-D1-K8")) + ((("office-told", "D1-K8"),) if TD else ()))
    assert 6 < off_def[0] < off_def[-1] < 9
    d.tbl("rejects", f"被拒绝的开 subagent 的调用和它们花的钱（每次运行的平均）。办公报告题各行出自办公报告题主要的一批（默认组在{CN[len(off_def)]}批里被深度上限拒绝的调用是每次运行 "
          f"{rnd(off_def[0])}–{rnd(off_def[-1])} 次），其余各行依次出自评测集填表题批、评测集报告题第一批、第一批、不限时 24 题批、大型编码题批。"
          "“任务说明”一列是模型为没开成的 subagent 写调用参数用掉的输出 token 折成的钱（把这一步的输出按各个调用的参数长度分摊，含思考，是偏高的估计）；"
          "“整步都被拒绝的请求”是一次模型请求发出的工具调用全是被拒绝的开 subagent 调用时，这次请求的全部费用（输入、命中缓存的输入和输出）。括号里是占这一组模型费的比例。两列有重叠，不能相加。", [
        ["任务", "设置", "运行数", "开成的 subagent", "被深度上限拒绝", "被 K 拒绝", "任务说明（元）", "整步都被拒绝的请求（元）"],
        rjrow("办公报告题", "K=1", [("office-confirm", "D1-K1")]), rjrow("", "K=2", [("office-confirm", "D1-K2")]), rjrow("", "K=4", [("office-confirm", "D1-K4")]),
        rjrow("", "默认", [("office-confirm", "D1-K8")]), rjrow("", "深度 2", [("office-confirm", "D2-K8")]),
        rjrow("评测集填表题", "默认", [("ws-h1", "W-D1-K8")]), rjrow("评测集报告题", "默认", [("drb2-h1", "W-D1-K8")]),
        rjrow("读代码题和小编程题", "默认", [("main-code", "D1-K8")]),
        rjrow("不限时 24 题", "默认", [("ctl-free", "W-D1-K8"), ("ctl-free-b2", "W-D1-K8")]), rjrow("", "加并行提示，K=1", [("ctl-free", "W-E-D1-K1"), ("ctl-free-b2", "W-E-D1-K1")]),
        rjrow("大型编码题", "默认", [("xl-main", "W-D1-K8")]), rjrow("", "加不复核提示，K=1", [("xl-main", "W-N-D1-K1")])])
    assert max(v_["args_share"] + v_["dead_share"] for g_ in mrj.values() for v_ in g_.values()) < 0.08
    d.figure("pages", f"{NEW}/pages-opened.png", "办公报告题：一次运行打开的不同网页数，按打开的办法分（多查 100/100 那一批）。命令里直接抓的和脚本存盘的会有重叠，合计给的是下限和上限。")
    d.figure("merge-cover", f"{NEW}/merge-coverage.png", "办公报告题：一份单 agent 报告写对多少条，两份、四份里至少有一份写对的有多少条，合并稿写对多少条。虚线是默认。")
    pr = cst["prices"]
    prow = lambda label, base, e, note="": [label, base, f"{sg(e['facts'])}{note}", sg(e["yuan"]), rnd(e["price"], 2)]  # noqa: E731
    assert pr["M2_none"]["price"] < pr["M4_none"]["price"] < pr["default"]["price"] - 0.05 and pr["M2_none"]["price"] < pr["more"]["price"] < pr["default"]["price"] - 0.05
    assert abs(pr["M4_none"]["price"] - pr["more"]["price"]) < 0.03 and abs(pr["k1"]["price"] - pr["more"]["price"]) < 0.03 and pr["keep"]["price"] < 0.3 * pr["d2"]["price"]
    assert pr["dose150"]["facts_lo"] > 0 and pr["dose250"]["facts_lo"] < 0 < pr["dose250"]["facts_hi"] and pr["default"]["price"] < pr["dose150"]["price"] < pr["dose250"]["price"]
    assert pr["d2"]["facts_lo"] < 0 and pr["old"]["facts_lo"] < 0 and mp4["facts"]["est"] > p2k8["est"] and mp4["cost"]["est"] < 1.3 < p2cost["lo"]
    assert pr["M4"]["facts"] > pr["d2"]["facts"] and pr["M4"]["yuan"] < pr["d2"]["yuan"] and 1.6 < mp4["time"]["est"] < 1.9
    NONE = "一次不开 subagent 的运行"
    d.tbl("price", "办公报告题：多写对一条事实要多花多少钱（多花的钱 ÷ 多写对的条数）。单位是条，不是百分点（一份清单平均 97.5 条）。前七行从不开 subagent 出发，后三行在默认之上再加；"
          f"每行只用一批的数、和同一批里的参照比，所以深度 2 这一行（一批 40 对）和{{tab:depth}} 里四批合起来的数不一样。条数按全清单算，没有另按事先定下的 63 条算。", [
        ["做法", "和谁比", "多写对（条）", "多花（元）", "每条（元）"],
        prow("两份报告合并", NONE, pr["M2_none"]), prow("四份报告合并", NONE, pr["M4_none"]), prow("K=1", NONE, pr["k1"]),
        prow("不开 subagent + 多查 100/100", NONE, pr["more"]), prow("不开 subagent + 多查 150/250", NONE, pr["dose150"]),
        prow("不开 subagent + 多查 250/500", NONE, pr["dose250"], "（区间含 0）"), prow("默认（开 subagent）", NONE, pr["default"]),
        prow("默认 + 都写进去提示（只算交出完整报告的）", "默认", pr["keep"]), prow("深度 2", "默认", pr["d2"], "（区间含 0）"),
        ["深度 3、K=64（相当于旧默认）", "默认", f"{sg(pr['old']['facts'])}（区间含 0）", sg(pr["old"]["yuan"]), "测不出多写对"]])
    d.add(f"- 从不开 subagent 出发，多写对一条事实：两份报告合并最便宜；四份合并、K=1 和多查 100/100 约 {rnd(pr['more']['price'], 2)} 元，默认 {rnd(pr['default']['price'], 2)} 元；"
          f"多查 150/250 和多查 250/500 是 {rnd(pr['dose150']['price'], 2)} 和 {rnd(pr['dose250']['price'], 2)} 元（后者多写对的区间含 0）。在默认之上再加，放开深度比都写进去提示贵得多。",
          "- 按对默认的估计值，四份合并比深度 2 多写对，费用低得多（{tab:spend}、{tab:depth}），只是要等的时间是默认的 1.7 倍。", "")
    d.figure("price", f"{NEW}/price-ladder.png", "办公报告题：每多写对一条事实多花的钱（{tab:price} 的数）。上面七种做法和一次不开 subagent 的运行比，下面的在默认之上再加。")
    wv = fw["W-D1-K8"]
    d.tbl("review", "不限时 24 题和大型编码题：代码写完以后有没有再派 subagent 复核。", [
        ["", "到最终回答（分钟）", "模型费（元/次）", f"没通过的隐藏测试（共 {xl['tests']:,} 个）"],
        ["大型编码题，不开 subagent", f(xm["D0"]["answer"]), f(xm["D0"]["cost"], 2), f(xl["failed"]["D0"])],
        [f"大型编码题，默认（{xl['review_runs']['W-D1-K8']}/{xm['W-D1-K8']['n']} 次派了复核）", f(xm["W-D1-K8"]["answer"]), f(xm["W-D1-K8"]["cost"], 2), f(xl["failed"]["W-D1-K8"])],
        ["大型编码题，题面加不复核提示", f(xm["W-N-D1-K8"]["answer"]), f(xm["W-N-D1-K8"]["cost"], 2), f(xl["failed"]["W-N-D1-K8"])],
        ["不限时 24 题，不开 subagent", f(fw["D0"]["rest"]["answer"]), f(fw["D0"]["rest"]["cost"], 2), "—"],
        [f"不限时 24 题，默认里文件写完又派了 subagent 的 {wv['late']['n']} 次", f(wv["late"]["answer"]), f(wv["late"]["cost"], 2), "—"],
        [f"不限时 24 题，默认里没再派的 {wv['rest']['n']} 次", f(wv["rest"]["answer"]), f(wv["rest"]["cost"], 2), "—"]])
    without_wave = sorted([xl["cmp"]["U"]["model_cost_peak"]["est"], wv["rest"]["cost"] / fw["D0"]["rest"]["cost"]])  # cost against no subagents when the wave is not sent
    wave_part = [(xm["W-D1-K8"]["cost"] - xm["W-N-D1-K8"]["cost"]) / (xm["W-D1-K8"]["cost"] - xm["D0"]["cost"]), (wv["late"]["cost"] - wv["rest"]["cost"]) / (wv["late"]["cost"] - fw["D0"]["rest"]["cost"])]
    nrun, npass = xm["W-N-D1-K8"]["n"], xl["all_pass_runs"]["W-N-D1-K8"]
    assert 0.57 < save_cost < 0.63 and 0.62 < save_time < 0.69 and all(q > 0.6 for q in wave_part) and 1.7 < without_wave[0] < without_wave[1] < 2.7
    assert xl["all_pass_runs"]["W-D1-K8"] == xm["W-D1-K8"]["n"] == nrun == 10 and npass == 1 and xl["failed_max"]["W-N-D1-K8"] == 3
    d.add(f"- 这两种任务上多等的时间，花在文件写完以后又派去复核的 subagent 上；派了复核的运行，比不开 subagent 多花的钱也大半在复核上。不派复核时，模型费仍是不开 subagent 的 {rnd(without_wave[0])}–{rnd(without_wave[1])} 倍。"
          f"不限时 24 题默认的 {fm_['W-D1-K8']['n']} 次里只有 {wv['late']['n']} 次派了复核。",
          f"- 大型编码题不让复核（加不复核提示），费用少六成、用户等的时间少三分之二，代价是 {nrun} 次里有 {nrun - npass} 次留下 1–{xl['failed_max']['W-N-D1-K8']} 个没通过的测试（有复核时 {xl['all_pass_runs']['W-D1-K8']} 次都全部通过）。"
          "复核在代码写完第一遍时错得多的任务上值不值，没有测。",
          "- 要写代码的四种任务（小编程题、两道 24 题、大型编码题），原题面都写了“给的只是部分测试，判分会用更完整的测试，所以要按规格写对”。复核有可能是模型对这句话的反应；去掉这句话的对照还没有做。", "")

    # ---- 7. how the runs ended
    d.add(f"### {SEC['deliver']}、各设置交付得怎么样", "")
    XG = E["xl_groups"]
    dash = lambda v: "—" if v is None else str(v)  # noqa: E731
    low4 = {dd: RS(RL, "office", lambda q, dd=dd: q["col"] in (f"{dd}-1", f"{dd}-2", f"{dd}-4") and plain_nowait(q)) for dd in (2, 3)}
    keep_w = RS(RL, "office", lambda q: q["col"] == "1-8" and q["variant"] == "N" and q["waits"])
    office_all = RS(RL, "office", lambda q: True)
    drows7 = [("不开 subagent（含题面加多查提示的各组）", "不等", rel_none)] + [(f"深度 1，K={v}" + ("（默认）" if v == 8 else ""), "不等", rel_k[v]) for v in (1, 2, 4, 8)] \
        + [("深度 1，K=8，题面加都写进去提示", "不等", rel_keep), ("深度 2，K=1、2、4", "不等", low4[2]), ("深度 2，K=8", "不等", rel_d2), ("深度 3，K=1、2、4", "不等", low4[3]), ("深度 3，K=8", "不等", rel_d3),
           ("深度 1（K=8、64；含加都写进去提示的一组）", "等", rel_w[1]), ("深度 2（K=8、64；含加都写进去提示的一组）", "等", rel_w[2]), ("深度 3（K=8、64）", "等", rel_w[3])]
    if TD:  # the told-limit batch: its plain groups are counted with K = 2 and K = 8 above; the told groups get rows of their own
        rel_t = {v: RS(RL, "office", lambda q, v=v: q["col"] == f"1-{v}" and q["variant"] == "T" and not q["waits"]) for v in (2, 8)}
        assert all(rel_t[v]["runs"] == 40 for v in rel_t)
        drows7 = drows7[:5] + [(f"深度 1，K={v}，工具说明里写明上限", "不等", rel_t[v]) for v in (2, 8)] + drows7[5:]
    assert sum(e["runs"] for _, _, e in drows7) == office_all["runs"] and sum(e["crash"] for _, _, e in drows7) == office_all["crash"]
    assert low4[2]["crash"] + low4[3]["crash"] == 4 and low4[2]["runs"] == low4[3]["runs"] == 60 and rel_d2["incomplete"] == rel_d3["incomplete"] == 1 and keep_w["runs"] == 20 and keep_w["incomplete"] == 0
    early_share = sorted(rel_k[v]["early"] / rel_k[v]["runs"] for v in rel_k)
    assert 0.03 < early_share[0] < early_share[-1] <= 0.10 and rel_w[1]["crash"] == 0 and rel_w[1]["wait_cap"] == 0
    d.p(f"**深度 1 以内（含不开 subagent）的 {shallow_runs:,} 次运行没有一次退出时崩溃；办公报告题放开到深度 2、3，进程不等 subagent 时，K=8 的运行有三分之一退出时崩溃。"
        "大型编码题原题面下，三到六成的运行里有进程把容器的内存用满被杀，加不复核提示以后很少；K=16、64 没有更快，不是内存不够造成的。**")
    d.figure("deliver", f"{NEW}/deliver-office.png", "办公报告题各种设置下，运行是怎么结束的。红柱是退出时崩溃的运行占的比例，蓝柱是主 agent 结束时还有 subagent 没做完的运行占的比例（进程不等 subagent 时，这些 subagent 的活白做了）。"
             "右边三组的进程等 subagent 做完再退出，蓝柱不适用。设置下面的灰字是这种设置一共跑了多少次。", hold=True)
    d.tbl("deliver", "办公报告题：各种设置下运行是怎么结束的（各批加在一起）。报告不完整指没交报告或报告不到 5,000 字符。“—”是这一列对这种跑法不适用。", [
        ["设置", "进程等不等 subagent", "运行次数", "报告不完整", "主 agent 结束时还有 subagent 没做完", "退出时崩溃", "等了 20 分钟还有 subagent 没结束"]]
        + [[label, w_, str(e["runs"]), dash(e["incomplete"]), dash(e["early"]), str(e["crash"]), dash(e["wait_cap"])] for label, w_, e in drows7])
    # the other tasks, by depth and by whether the process waits (the appendix table); the sentences below use the same sums
    OTHER = (("ws", "评测集填表题"), ("drb2", "评测集报告题"), ("code", "读代码题"), ("p4", "小编程题"), ("wide", "限时 24 题"), ("chain", "16 步串行题"), ("free", "不限时 24 题"), ("xl", "大型编码题"))
    VAR = {"E": "并行提示", "N": "不复核提示"}
    arows, asum = [], {}
    for key_, name_ in OTHER:
        first_ = True
        for dd in ("none", "1", "2", "3"):
            for waits_ in (False, True):
                sel = [q for q in RL if q["task"] == key_ and q["waits"] == waits_ and (q["col"] == "none" if dd == "none" else q["col"].startswith(dd + "-"))]
                if not sel:
                    continue
                e = RS(RL, key_, lambda q, sel=sel: q in sel)
                asum[(key_, dd, waits_)] = e
                ks_ = sorted({int(q["col"].split("-")[1]) for q in sel}) if dd != "none" else []
                hints = sorted({VAR[q["variant"]] for q in sel if q["variant"] in VAR})
                label = "不开 subagent" if dd == "none" else f"深度 {dd}（K=" + "、".join(str(v) for v in ks_) + ("；含加" + "、".join(hints) + "的组" if hints else "") + "）"
                arows.append([name_ if first_ else "", label, "等" if waits_ else "不等", str(e["runs"]), dash(e["incomplete"]), dash(e["early"]), str(e["crash"]), str(e["other_exit"]),
                              "限时题" if key_ == "wide" else str(e["timeout"]), dash(e["wait_cap"]), dash(e["oom"])])
                first_ = False
    pub_w = [asum[(k_, dd, True)] for k_ in ("ws", "drb2") for dd in ("1", "2")]
    code_deep = [asum[("code", dd, False)] for dd in ("2", "3")]
    p4_hint = RS(RL, "p4", lambda q: q["variant"] == "E")
    assert sum(e["crash"] for e in pub_w) == 1 and asum[("ws", "2", True)]["crash"] == 1 and sum(e["timeout"] for e in pub_w) == 3 and sum(e["crash"] for e in code_deep) == 5 and sum(e["runs"] for e in code_deep) == 260
    assert RS(RL, "p4", lambda q: True)["crash"] == 0 and p4_hint["runs"] == 120 and p4_hint["early"] == 26 and asum[("code", "1", False)]["crash"] == 0
    assert sum(e["crash"] for e in asum.values()) + office_all["crash"] == iss["all_crashes"]
    d.add(f"- 深度 1：各个 K 都没有退出时崩溃。主 agent 结束时还有 subagent 没做完的运行占 {pct(early_share[0])}–{pct(early_share[-1])}，各个 K 差不多。",
          f"- 深度 2、3：崩溃集中在 K=8（{rel_d2['crash']}/{rel_d2['runs']}、{rel_d3['crash']}/{rel_d3['runs']}）；K=1、2、4 的 {low4[2]['runs'] + low4[3]['runs']} 次里 {low4[2]['crash'] + low4[3]['crash']} 次。"
          f"崩溃的运行几乎都交出了完整的报告（K=8 的 {rel_d2['runs'] + rel_d3['runs']} 次里 {rel_d2['incomplete'] + rel_d3['incomplete']} 次不完整），但进程以出错结束，没做完的 subagent 的结果丢了。",
          f"- 进程等 subagent 做完再退出（实验加的补丁）：深度 2、3 的 {rel_w[2]['runs'] + rel_w[3]['runs']} 次里崩溃 {rel_w[2]['crash'] + rel_w[3]['crash']} 次，另有 {rel_w[2]['wait_cap'] + rel_w[3]['wait_cap']} 次等了 20 分钟还有 subagent 没结束。",
          f"- 题面加都写进去提示：进程不等 subagent 的 {rel_keep['runs']} 次里，{rel_keep['early']} 次主 agent 没等 subagent 做完就结束，{rel_keep['incomplete']} 次报告不完整；进程等 subagent 的 {keep_w['runs']} 次都交了完整的报告。",
          f"- 其它任务（附录的{{tab:deliver-all}}）：两个公开评测集开 subagent 的各组进程都等，{sum(e['runs'] for e in pub_w)} 次里 1 次退出时崩溃（评测集填表题的深度 2）、{sum(e['timeout'] for e in pub_w)} 次到了时限。"
          f"读代码题进程不等，深度 2、3 的 {sum(e['runs'] for e in code_deep)} 次里 {sum(e['crash'] for e in code_deep)} 次崩溃。小编程题没有崩溃，但题面加并行提示的各组 {p4_hint['runs']} 次里有 {p4_hint['early']} 次主 agent 提前结束，"
          f"其中 {low_runs['p4']['low']} 次得分低于 90 分。", "")
    d.release()
    xg = lambda b_, g_: XG[f"{b_}:{g_}"]  # noqa: E731
    xrow = lambda label, e: [label, f"{rnd(e['kids'])}（{rnd(e['review_kids'])}）", rnd(e["slot_peak"]), rnd(e["cap_rejects"]), rnd(e["written_min"]), rnd(e["answer_min"]), f"{e['oom_runs']}/{e['n']}", rnd(e["mem_peak"])]  # noqa: E731
    nk = {v: xg("main", f"W-N-D1-K{v}") for v in (1, 2, 4, 8, 16)}
    n16b, n64 = xg("depth", "W-N-D1-K16"), xg("depth", "W-N-D1-K64")
    orig = {v: xg("main", f"W-D1-K{v}") for v in (4, 8, 16)}
    wide_open = [nk[16], n16b, n64]
    full16 = nk[16]["full_runs"] + n16b["full_runs"]
    assert all(10.5 < e["slot_peak"] < 12.6 for e in wide_open) and max(e["slot_max"] for e in wide_open) == 16 and all(e["cap_rejects"] == 0 for e in wide_open) and full16 == 1 and n64["full_runs"] == 0
    assert all(4 < e["written_min"] < 5 for e in wide_open) and 6.4 < nk[8]["written_min"] < 6.8 and all(9.8 < e["answer_min"] < 11.4 for e in wide_open) and 9.5 < nk[8]["answer_min"] < 9.8
    assert all(4.9 < e["after_written_min"] < 6.8 for e in wide_open) and 2.9 < nk[8]["after_written_min"] < 3.1 and all(e["dead"] == 0 for e in wide_open + [nk[8]])
    assert all(e["oom_runs"] <= 2 and 4 < e["mem_peak"] < 5 for e in wide_open) and [orig[v]["oom_runs"] for v in (4, 8, 16)] == [6, 3, 6] and xg("main", "W-D2-K8")["oom_runs"] == 6
    assert sum(e["oom_runs"] for k_, e in XG.items() if k_.startswith("main:")) == iss["oom_runs"] and all(abs(geo[v] / 60 - nk[v]["answer_geo_min"]) < 0.01 for v in nk)
    d2k16 = xg("depth", "W-N-D2-K16")
    assert d2k16["dead"] == 1 and sum(e["dead"] for e in XG.values()) == 1
    d.figure("xl-k", f"{NEW}/xl-by-k.png", "大型编码题，题面加不复核提示：K 取不同值时，同时活着的 subagent 最多有几个（左），以及从开始到文件都写完、到主 agent 给出最终回答各用了多少分钟（右）。每个 K 是 10 次运行的平均；K=64 来自另一批。", hold=True)
    d.tbl("xl-k", "大型编码题各组：开了多少 subagent（括号里是文件写完以后才开的，即复核用的）、同时活着的最多几个、被 K 拒绝的调用数、从开始到文件写完和到最终回答的分钟数、有进程因内存被杀的运行数、内存峰值（容器上限 16 GB）。"
          "除“有进程因内存被杀的运行”一列以外都是每次运行的平均；每组 10 次。标“另一批”的四行来自大型编码题深度批；其中深度 2、K=16 一组有 1 次运行一开始就结束了、没有写文件，这一行的两个时间只算其余 9 次。", [
        ["题面", "设置", "开的 subagent（其中复核的）", "同时活着最多", "被 K 拒绝的调用", "文件写完（分钟）", "到最终回答（分钟）", "有进程因内存被杀的运行", "内存峰值（GB）"],
        ["原题面"] + xrow("不开 subagent", xg("main", "D0")), [""] + xrow("K=4", orig[4]), [""] + xrow("K=8（默认）", orig[8]), [""] + xrow("K=16", orig[16]), [""] + xrow("深度 2（K=8）", xg("main", "W-D2-K8")),
        ["加不复核提示"] + xrow("K=1", nk[1])] + [[""] + xrow(f"K={v}", nk[v]) for v in (2, 4, 8, 16)]
        + [[""] + xrow("K=16（另一批）", n16b), [""] + xrow("K=64（另一批）", n64), [""] + xrow("深度 2（K=8）", xg("main", "W-N-D2-K8")), [""] + xrow("深度 2、K=16（另一批）", d2k16), [""] + xrow("深度 2、K=64（另一批）", xg("depth", "W-N-D2-K64"))])
    d.add(f"- 加不复核提示时，K 从 8 放到 16、64，模型同时最多开 {rnd(min(e['slot_peak'] for e in wide_open), 0)}–{rnd(max(e['slot_peak'] for e in wide_open), 0)} 个（各次运行的平均）；K=16 的 {nk[16]['n'] + n16b['n']} 次里只有 {full16} 次开满了 16 个，没有调用被拒绝。",
          f"- 文件写完的时间从 K=8 的 {rnd(nk[8]['written_min'])} 分钟降到 {rnd(min(e['written_min'] for e in wide_open))}–{rnd(max(e['written_min'] for e in wide_open))} 分钟，到最终回答的时间没有缩短（{rnd(min(e['answer_min'] for e in wide_open))}–{rnd(max(e['answer_min'] for e in wide_open))} 分钟，K=8 是 {rnd(nk[8]['answer_min'])}）："
          f"文件写完以后到最终回答的这一段，从 {rnd(nk[8]['after_written_min'])} 分钟变成 {rnd(min(e['after_written_min'] for e in wide_open))}–{rnd(max(e['after_written_min'] for e in wide_open))} 分钟。多开的 subagent 只缩短了写文件的一段。",
          f"- 这几组的内存峰值平均 4–5 GB，10 次里至多 {max(e['oom_runs'] for e in wide_open)} 次有进程被杀，所以 K=16、64 没有更快不是内存不够造成的。CPU 的占用没有记录，4 核够不够判断不了。",
          f"- 原题面下不一样：K=4、8、16 的 10 次里各有 {orig[4]['oom_runs']}、{orig[8]['oom_runs']}、{orig[16]['oom_runs']} 次有进程把 16 GB 内存用满被杀（深度 2 是 {xg('main', 'W-D2-K8')['oom_runs']} 次），内存峰值平均 10–14 GB。"
          "所以原题面各组之间的时间比较带着容器内存的影响，“K=4 的时间没测出差别”要带着这个限制读。", "")
    d.release()

    # ---- 6. can the measurement be trusted
    d.add(f"### {SEC['trust']}、量得准吗", "")
    og, sp, pz = E["origin"], E["speed"], E["price"]
    assert all(0.55 < min(v["explained"], v["explained_rev"]) and max(v["explained"], v["explained_rev"]) < 1.15 and v["added_none"] < 50 < 70 < v["fixed_none"] for v in og.values())
    assert sum(1 for v in og.values() for q in v["groups"] if abs(q["fixed_gain"] - q["added_gain"]) < 4) >= 5
    CPU, TRIP = "o2-server-cpu-report", "o1-singapore-trip"
    cpu_fx = sorted(v["by_task"][CPU]["fixed_gain"] for v in og.values())
    cpu_ad = sorted(v["by_task"][CPU]["added_gain"] for v in og.values())
    assert 2.5 < cpu_fx[0] < cpu_fx[1] < 4.5 and 13 < cpu_ad[0] < cpu_ad[1] < 17 and max(v["by_task"][CPU]["explained"] for v in og.values()) <= 0.505
    assert og["confirm"]["by_task"][TRIP]["explained"] > 0.65 and abs(og["floor"]["by_task"][TRIP]["fixed_gain"] - og["floor"]["by_task"][TRIP]["added_gain"]) < 2.5
    assert sp["office_max_gap"] < 0.02 and 230 < sp["sub_min"] < sp["sub_max"] < sp["none_max"] < 256 and pz["n"] == 40 and 0.2 < pz["rel"] < 0.3 and pz["max_shift"] < 0.07
    assert pz["shift_rest"] < 0.01 and 0.6 < pz["share_more"] < 0.7 and 0.47 < pz["share_others"][0] < pz["share_others"][1] < 0.56
    share_d = (m["D1-K8"]["cost"] - m["D1-K8"]["model_cost"]) / m["D1-K8"]["cost"]
    share_m = [o["merge_search"][q] * iss["search_price"] / pr[q]["cost"] for q in ("M2", "M4")]
    merge_shift = sorted(max(abs((1 + sign * pz["rel"] * q) / (1 + sign * pz["rel"] * share_d) - 1) for sign in (1, -1)) for q in share_m)
    assert 0.018 < merge_shift[0] <= merge_shift[1] < 0.032 and all(0.38 < q < 0.46 for q in share_m)
    more_shift, more_share = pz["shift_more"], pz["share_more_all"]
    assert len(more_shift) == 3 and 0.04 < more_shift[0] < more_shift[-1] < 0.07 and 0.65 < more_share[0] < more_share[-1] < 0.77 and pz["shift_rest"] < 0.01
    sa_ = sorted(q["share"] for q in E["second_all"])
    assert len(sa_) == 7 + (1 if TD else 0) and 0.98 < sa_[0] < sa_[-1] < 0.996
    d.p("**同一份报告判两遍结果几乎一样；办公报告题上五到七个百分点以内（只有 20 对的对比更宽）、公开评测集上三到六分以内的差别，这些次数测不出来；事实清单的判分没有和人工对照过。**")
    cat = cd.J("results/analysis-complete/stats-office-cat.json")["metrics"]
    cb = cat["score_B"]["comparisons"]["H1"]
    ni = o["new_items"]
    sec = {k_: 100 * v["same"] / v["n"] for k_, v in o["second"].items()}
    rg = wa.regrade()
    assert cb["lo"] > 0 and verdict(rb["h1"], 5) == "没测出差别" and len(rb["groups"]) == 13 and o["samples"]["n"] == 24 and o["samples"]["none"] == 4
    assert p["with_flagged"]["ws_recall"]["lo"] > 0 and p["with_flagged"]["ws_recall"]["p_holm"] < 0.05
    k64v = verdict(o["k64"]["right_pct"], 8, corrected=True)
    assert k64v == "校正后不显著" and abs(o["other_kids"]["k64"] - od["kids_default"]) < 0.5 and 4.5 < -o["k64"]["right_pct"]["est"] < 5
    assert 1.8 < ni["H1"]["est"] / h1leg["est"] < 2.3
    wk2nd, dk2nd = cd.J("results/analysis-ws-k4/second-pass.json"), cd.J("results/analysis-drb2-k4/extra.json")["second"]
    assert wk2nd["runs"] == 32 and dk2nd["reports"] == 12 and wk2nd["mean_abs_diff"] < 0.5 and dk2nd["item_agreement"] > 0.97
    d.tbl("trust", "对测量本身做过的检查。", [
        ["检查", "结果"],
        ["评分表总分能不能看出差别", f"不能。开不开 subagent 是 {ci(rb['h1'])} 分，{verdict(rb['h1'], 5)}；其中“关键事实”一类高 {cb['est']:.0f} 个百分点。所以另建了逐条核对的事实清单"],
        ["两套条目的结果为什么差一截", f"后补的 132 条参考的样本，每题 12 份里有 10 份来自开 subagent 的组，可能偏向这些组。开 subagent 的效果在后补的条目上是 {ci(ni['H1'])}，是事先定下的 63 条上（{{tab:worth}}）的两倍。"
         f"一部分原因是后补的条目本来就更难写到（不开 subagent 时写对 {og['confirm']['added_none']:.0f}%，63 条是 {og['confirm']['fixed_none']:.0f}%），可涨的余地大。"
         f"按难度分档再比（事后分析）：旅行攻略题上差别的大半能用难度解释；CPU 选型题上 63 条只涨 {cpu_fx[0]:.0f}–{cpu_fx[1]:.0f} 个百分点、后补的涨 {cpu_ad[0]:.0f}–{cpu_ad[1]:.0f} 个，"
         "难度至多解释一半。所以后补条目偏向开 subagent 的组这种可能排除不了；结论以事先定下的 63 条为准，全清单的数并排给"],
        ["同一种设置重复跑，差多少", f"默认设置在{CN[len(lv)]}批里都跑过，各批的写对的事实占比在 {min(lv.values()):.1f}% 到 {max(lv.values()):.1f}% 之间。深度 1 下 K=64 和 K=8 开的 subagent 一样多，K 都没有起作用，写对的事实占比却差了近 5 个百分点（只算 63 条差 {rnd(abs(lg['k64']['est']), 0)} 个；{{tab:k}}）"],
        ["同一份报告判两遍，一致吗", f"事实清单：{CN[len(sa_)]}批各抽一部分判了第二遍，逐条一致 {100 * sa_[0]:.1f}%–{100 * sa_[-1]:.1f}%；评测集报告题逐条一致 {100 * drb['second']['item_agreement']:.1f}%（补测 K=4 那一批 {100 * dk2nd['item_agreement']:.1f}%）；评测集填表题两遍的得分平均差 {ws['second']['mean_abs_diff']:.2f} 分（补测那一批 {wk2nd['mean_abs_diff']:.2f} 分）"],
        ["判分和别的判法一致吗", f"事实清单的判分只和另一个模型对照过：写清单的 agent 通读样本报告时的逐条归类，一致 {rg['agree'][0]:.1f}%、{rg['agree'][1]:.1f}%。评分表在试跑阶段由人打过 2 份对照，逐条一致 71%，之后改了评分表。报告整体好不好没有人评过"],
        ["各组用的模型速度一样吗", f"不限时 24 题的两批里量过每路请求的输出速度：开 subagent 的各组 {sp['sub_min']:.0f}–{sp['sub_max']:.0f} token/秒，不开的 {sp['none_min']:.0f}–{sp['none_max']:.0f}。"
         "办公报告题把每个请求按同一个速度重算时间，各组对默认的时间倍数变化不超过 0.02"],
        ["搜索费估得准吗", f"单价是抽 {pz['n']} 个搜索请求实测的均值，95% 区间是 ±{pct(pz['rel'])}，所以办公报告题默认组的搜索费是 {rnd(pz['default_search_fee'])} ± {rnd(pz['default_fee_half'])} 元。"
         f"各组的搜索费都占一半左右（{pct(pz['share_others'][0])}–{pct(pz['share_others'][1])}），单价在这个范围里变，费用倍数的变化不到 1%（合并稿的两行约 {pct(merge_shift[0])}–{pct(merge_shift[1])}，它们的搜索费占得少一些）；"
         f"不开 subagent 加多查提示的三组，搜索费占到三分之二到四分之三，它们对默认的费用倍数会变 {pct(more_shift[0])}–{pct(more_shift[-1])}"],
        ["公开评测集会不会搜到答案", f"容器里屏蔽了答案所在的网站；日志里出现评测集名字或读到不许用的来源的运行不计分（评测集填表题 {ws['flagged']}/{ws['runs']} 次，评测集报告题 {drb['flagged']}/{drb['runs']} 次；补测 K=4 的两批是 {p['wsk']['flagged']}/{p['wsk']['runs']} 次和 {p['drbk']['flagged']}/{p['drbk']['runs']} 次）。"
         f"把它们算进去：评测集报告题 {ci(p['with_flagged']['drb'])}，评测集填表题 {ci(p['with_flagged']['ws_f1'])}"]])
    d.add(f"- 所以办公报告题上只有 20 对运行的对比，{md20[0]:.0f} 个百分点以内的差别测不出来，单看一批不能当结论；办公报告题的各张表都给了只算事先定下的 63 条的结果。",
          f"- 评测集报告题上 ±5 分的范围偏宽：同一个设置重跑一遍，单道题的总分平均就差 {rt['mean_abs_diff']:.1f} 分，而开 subagent 的全部好处才 {dt['est']:.1f} 分。那上面 K=1、深度 2 的“没有差别”只能读成没有看到大的差别。", "")

    # ====================================================================================================== issues
    assert fm_["W-E-D1-K8"]["answer"] > fm_["W-D1-K8"]["answer"] > fm_["D0"]["answer"] > 10 and xm["W-D1-K16"]["cost"] > xm["W-D1-K8"]["cost"] > xm["W-D1-K4"]["cost"]
    assert xm["W-D1-K4"]["answer"] > xm["W-D1-K8"]["answer"] and xm["W-N-D1-K1"]["answer"] > xm["W-N-D1-K4"]["answer"] > xm["W-N-D1-K8"]["answer"]
    assert 3 < o["k64_d2"]["right_pct"]["est"] < 4 and 1 < o["k64_d3"]["right_pct"]["est"] < 2
    d.add("## 和事前预想不一样的地方", "")
    fmore = o["floor_more"]
    k2d, k3d = o["k64_d2"]["right_pct"], o["k64_d3"]["right_pct"]
    assert free["cmp"]["NC"]["answer_s"]["lo"] < 1 < free["cmp"]["NC"]["answer_s"]["hi"] and free["cmp"]["PC"]["answer_s"]["lo"] > 1
    assert fk["K1"]["answer_s"]["lo"] < 1 < fk["K1"]["answer_s"]["hi"] and 2.8 < fm_["W-E-D1-K16"]["cost"] / fm_["W-E-D1-K1"]["cost"] < 3.6
    assert fmore["n"] == 40 and fmore["over200"] == 12 and 13 < o["floor_means"]["E-D0"]["minutes"] < 15 and 270000 < fmore["ctx_median"] < 285000
    assert max(k2d["est"], k3d["est"], bb["W-D2-K64"]["facts"]["est"], bb["W-D3-K64"]["facts"]["est"]) < 7 and verdict(mp2["facts"], 8) == "没有差别"
    lo_hi = sorted([k2d["est"], k3d["est"]])
    alt = sorted([bb["W-D2-K64"]["facts"]["est"], bb["W-D3-K64"]["facts"]["est"]])
    assert 1 < lo_hi[0] < lo_hi[1] < 4 and 3.5 < alt[0] < alt[1] < 6.5
    d.p("有 14 批事前写下过预计的结果（其中后来改按事实清单判分的那一批，预计写在重新判分之前，那时运行已经做完）；预计、实际和对没对上，都列在附录的{tab:expect}。改变了结论的是三处没对上的（其余没对上的几处没有改变结论）：")
    d.add(f"- **不限时 24 题。** 预计开 subagent 能把时间从 6 分钟缩到 2.5 分钟，K 越大越快。实际没有更快，题面加并行提示还更慢；查原因才看到慢在文件写完以后又派 subagent 去复核（细节{SEC['spend']}）。",
          "- **两份不开 subagent 的报告合并。** 预计写对的比默认低 3–9 个百分点。实际和默认没有差别；“默认多写对的不一定要靠 subagent”是从这里来的。",
          f"- **按搜索量直线推算。** 把深度和 K 都放开，按{{fig:search}} 那条直线（各组的搜索请求数对写对的事实占比），该多写对 10–11 个百分点。实际的估计值只有 {lo_hi[0]:.0f}–{lo_hi[1]:.0f} 个（把对照换成同批两个深度 1 组的平均是 {alt[0]:.0f}–{alt[1]:.0f} 个），都低于直线推算。", "")

    # ====================================================================================================== defects
    d.add("## 运行中发现的 DSH 缺陷", "")
    d.p(f"“代码写完又派 subagent 复核”是模型的行为（题面里的一句话可能有影响），放在细节{SEC['spend']}。下面六条是 DSH 自己的缺陷：")
    d.add(f"1. **搜索请求的 token 用量没有记进会话日志**（日志里只有每个请求的记录，所以搜索费只能按抽样实测的单价估）；每个搜索请求里模型顺带写的那段回答，搜索插件没有用（细节{SEC['spend']}）。",
          f"2. **到了深度上限，工具列表里还留着开 subagent 的工具，调用了才被拒绝。** 办公报告题默认设置的 {beh['D1-K8']['depth']['runs']} 次运行共被拒 {beh['D1-K8']['depth']['total']} 次，写任务说明和发请求的 token 都浪费了。",
          f"3. **模型事先不知道同时存活数量的上限，开到超出的那一个才被拒绝。** K=1 的 {mrj['office-confirm']['D1-K1']['runs']} 次运行被拒 {mrj['office-confirm']['D1-K1']['cap'] * mrj['office-confirm']['D1-K1']['runs']:.0f} 次，K=2 的 {mrj['office-confirm']['D1-K2']['runs']} 次被拒 {mrj['office-confirm']['D1-K2']['cap'] * mrj['office-confirm']['D1-K2']['runs']:.0f} 次。可以把上限告诉模型，或者改成排队。{told_defect}",
          f"4. **命令行一次性运行时，主 agent 这一轮结束进程就退出，不管 subagent 是不是还在运行。** 全部 {iss['all_runs']:,} 次运行里有 {iss['all_crashes']} 次退出时崩溃（进程在处理 subagent 送回的消息时报错；这些运行照样算结果，交出了完整报告的照常计分），都出在深度 2、3 的组；"
          f"其中一次主 agent 说了一句等四组 subagent 的结果回来就汇总，然后就结束了，报告没有写出来。深度 1 的组没有崩溃，但题面加都写进去提示以后，{wfl['runs'] // 4} 次里有 {wfl['early']} 次主 agent 没等 subagent 回来就结束，交出的是半成品或者没交。",
          "5. **被上级中断（用 interrupt_agent 工具）的 subagent，如果当时还有没处理的消息在排队，就一直不结束**，DSH 一直当它还活着（各批里见到 31 个，没有一个结束）。",
          f"6. **agent 用 shell 跑的进程没有内存上限。** 大型编码题批的 {iss['xl_runs']} 次运行里 {iss['oom_runs']} 次有进程把容器 16 GB 内存用满被系统杀掉，其中 1 次被杀的是 DSH 进程本身。", "")

    # ======================================================================================================= scope
    cf_ = o["ctx_floor"]["E-D0"]
    d.add(f"## {RELATED}", "")
    assert 2 < ws["cmp"]["H1n"]["f1_item"]["est"] < 3.5 and mp4["facts"]["lo"] > 0
    d.tbl("related", "别人量过的相近问题。数字都对过原文；模型、任务和判分都和这里不同，只比方向。", [
        ["来源", "量了什么", "结果", "和这里的关系"],
        ["Anthropic 工程博客《How we built our multi-agent research system》（2025-06）", "多 agent 调研系统在 BrowseComp 上的成绩差别由什么解释",
         "token 用量一项解释了 80%；多 agent 系统用的 token 约是普通对话的 15 倍", "一致：这里单 agent 加多查 150/250、多查 250/500 的两组，搜索请求到了默认的水平，模型费不到默认的一半；写对的按全清单都显著更少，按事先定下的 63 条一组没测出差别、一组显著更少"],
        ["Google《Towards a Science of Scaling Agent Systems》（arXiv 2512.08296）", "四种多 agent 结构在 6 个评测集上和单 agent 比",
         "相对单 agent 的变化从 +80.8%（金融分析）到 −70.0%（要按顺序规划的任务），全部平均 −0.3%", "一致：值不值看任务"],
        ["ArcticSwarm（arXiv 2609.01870）", "同时运行的 subagent 上限从 8 到 48，BrowseComp-Plus 前 100 题，每档 3 次",
         "准确率 76.0%–79.3%，作者认为差别在重复跑的波动以内；上限 8 用的 token 最多，是上限 16 的 1.49 倍", "上限调大没有好处，一致。费用方向相反：他们上限 8 用的 token 最多（作者的说法是查多少由主 agent 定，不由上限定）；这里上限小了模型就少开、少查"],
        ["同上", "单 agent 重复 20 次再投票，token 和多 agent 系统相同", "准确率 62.5%，多 agent 系统 82.6%",
         "方向相反：这里四份单 agent 报告合并，写对的不比默认少。他们一题一个答案，重复只能投票；这里是写报告，各份查到的事实可以并起来"],
        ["W&D（arXiv 2602.07359）", "单 agent 每轮并行调用 1 到 8 个工具，BrowseComp 前 100 题，各 1 次", "每轮 3 个对每轮 1 个：准确率 68% 对 66%，钱和时间少约四成；每轮 5、8 个准确率更低",
         f"相同的只有一点：不开 subagent 也能把一次查的量做上去。他们量到的是轮数、钱和时间变少，查得多并没有更准；这里的三种多查提示让单 agent 写对的事实按全清单多了 {rnd(dc['Z250']['right_pct']['est'], 0)}–{rnd(fl['EF']['right_pct']['est'], 0)} 个百分点（按 63 条多 {rnd(zl250['est'], 0)}–{rnd(zl150['est'], 0)} 个），仍少于默认：按全清单三种都显著，按 63 条两种显著"],
        ["WideSearch（arXiv 2508.07999）", "多 agent 对单 agent，200 道联网收集信息填表的题", "逐项得分高 3.0–6.8 分，搜索次数是 2–4 倍", "和这里的评测集填表题同一量级"],
        ["《Rethinking Multi-Agent Collaboration: When More Is Less》（arXiv 2609.19759）", "在他们提出的协作办法 SAIGE 上，把最大深度从 1 调到 3；模型 DeepSeek-V4-Pro，框架 Codex CLI", "DeepResearch Bench II（和这里的评测集报告题是同一个评测集）55.2 降到 52.2，日常办公任务 71.8 降到 63.2", f"他们放开深度是变差；这里评测集报告题深度 2 没有差别（{sg(dq('drb2', 2)['est'])} 分），办公报告题略有提高；两边都没看到值得这个价钱的好处"],
        ["Cognition《Multi-Agents: What's Actually Working》（2026-04）", "Devin 在生产中的做法", "只让一个 agent 写，其余 agent 提供信息或做审查；审查 agent 平均每个 PR 找出 2 个 bug",
         "这里代码写完后的复核也能修掉最后一两个没通过的测试；几份报告交给一个 agent 合并是同一种分工"]])
    assert all(q_["hi"] < 0 for q_ in (fl["PRIM"]["right_pct"], dc["P150"]["right_pct"], dc["P250"]["right_pct"], lg["more"], dl250)) and dl150["lo"] < 0 < dl150["hi"]
    d.add("## 适用范围、会推翻结论的结果和下一步", "")
    d.tbl("falsify", "每条结论对应的反面结果和下一步。", [
        ["结论", "什么结果会推翻它", "下一步"],
        ["K 保持 8：调大没测出好处；比 8 小的取值各有一样没过（K=4 是读代码题的质量没测出、大型编码题不复核时慢两成）", "读代码题上加跑以后，K=4 的质量区间下限收进 −5 分以内，并且定下保留复核（原题面下 K=4 的时间没测出差别；这几组内存不够，要在内存更大的容器里重测）：这时可以降到 4。"
         "或者把上限告诉模型、超出上限时改成排队以后，K=1、2 的损失没有了；或者在模型想同时开十个以上的任务上，K=16 测得出更快",
         "读代码题上加跑 K=4；在内存更大的容器里重测原题面的大型编码题 K=4 和 8；" + ("到了上限排队等空位的做法没有测；告知上限只在办公报告题的 K=2、8 上测过，K=1 和代码类任务没有测" if TD else "把上限写进工具说明，重测办公报告题的 K=2 和 K=8")],
        ["深度保持 1", "一个上下文装不下的大任务上，深度 2 明显更好", "找一类深度 1 时单个 subagent 的上下文装不下的任务测深度（这次的任务都装得下）"],
        ["办公报告题上，让单 agent 自己多查只补上一部分（按 63 条，三种提示里两种仍显著少于默认；按全清单三种都是），四份独立的单 agent 报告合并不比默认少", f"换一种让单 agent 多查的办法以后，同样的搜索量下它和默认没有差别；或者四份合并稿和同样要求都写进去的默认比，写对的明显少（现在是 {ci(o['m4_vs_keep'])}；能这样比的只有后一批合并稿，{o['m4_vs_keep']['n']} 对）",
         "合并稿换题重复；多查提示只试了“题面加一句要求”这一种办法，换分阶段查、先列提纲再逐项查这类办法再测"],
        ["代码类任务上开 subagent 得分几乎不变", "代码写完第一遍时错得多的任务上，复核把通过率明显提了上去", "在写完第一遍时通过率低的任务上比有没有复核；去掉题面里“判分会用更完整的测试”一句，看模型还派不派复核"],
        ["各组的差别不是判分造成的", "人工逐条核对和判分模型的判定对不上，而且偏向某一类组", "抽 100 条判定请人核对"]])
    d.add(f"- 四种不限时、用测试或标准答案判分的任务（小编程题、16 步串行题、不限时 24 题、大型编码题）上，全部 {sum(v['runs'] for v in low_runs.values())} 次运行里有 {sum(v['low'] for v in low_runs.values())} 次得分低于 90 分："
          f"{low_runs['p4']['low_early']} 次是小编程题加并行提示时主 agent 没等 subagent 做完就结束，1 次是大型编码题一开始就结束了、没有写文件。其余的得分都在 {math.floor(min(v['min_rest'] for v in low_runs.values()))} 分以上；去掉这 {sum(v['low'] for v in low_runs.values())} 次，同一批里各组的平均分最多差 {rnd(near_spread)} 分。所以这些任务上只比得出费用、时间和交没交完。",
          "- 一个模型（v41flash，推理强度 max）、一个 DSH 版本（0.2.0-rc.2）、命令行一次性运行，任务都是一次运行做完的，平均用时最长的一组约半小时，个别运行到一小时。换模型、在桌面端多轮对话里用、更长的任务，都没有测。",
          "- 重复跑的办公报告题只有两道，而且取自用户日志里的任务。文中的区间反映的是同一道题重复跑的波动；换题以后幅度会变（开 subagent 的效果在两道题之间就差一倍，公开评测集上更小）。",
          "- 事实清单量的是“查得全不全”，不是报告好不好用。报告更长、事实更多，用户是不是更愿意要，没有测。",
          f"- 这些任务都没有大到一个上下文装不下。窗口是 100 万 token；单次请求的输入，办公报告题各组最多用到 {ctx['ctx_office_max']:.0f} 万，大型编码题最多 {ctx['ctx_xl_max']:.0f} 万（不开 subagent 的一次）。"
          f"单 agent 加多查提示的几组更高：多查 100/100 最多 {cf_['max'] / 1e4:.0f} 万，多查 150/250 最多 {dm['E-D0']['peak_max'] / 1e4:.0f} 万，各有 {cf_['pruned']} 次被 DSH 裁剪过上下文（输入最多才六十多万，可见 DSH 不等窗口用满就会裁剪）。深度可能有用的场景是更大的任务，这里没有。",
          "- 不让模型复核只在大型编码题上测过，而且不复核提示是加在题面里的，没有放进系统提示。", "")

    # ==================================================================================================== appendix
    d.add("## 附录", "", "### 各批实验", "")
    BATCHES = [  # (the name used in the text, rows file, tasks, settings, does the process wait for subagents, how quality is judged)
        ("第一批", "results/analysis-v2/rows.csv", "办公报告题；读代码题和小编程题",
         "办公报告题：不开，深度 1、2、3 各配 K=1、2、4、8（每题 10 次）。读代码题和小编程题：原题面的不开和深度 1、2、3（K=8；另按事前的规则补了几格小 K），加并行提示的深度 1、2、3 各配 K=1、2、4、8（每题 10 次）",
         "不等", "办公报告题先按评分表打总分，后来改按事实清单判；读代码题按要点和评分表；小编程题用隐藏测试"),
        ("对照题批", "results/analysis-ctl/rows.csv", "限时 24 题、16 步串行题", "不开、默认、默认加并行提示（各 10 次）", "等", "隐藏测试、对答案"),
        ("等 subagent 批", "results/analysis-wait/rows.csv", "办公报告题", "进程等 subagent 的默认、深度 2、深度 3，和不等的深度 2、深度 3（每题 10 次）", "两种都有", "先按评分表打总分，后来改按事实清单判"),
        ("限时 24 题批", "results/analysis-ctl-dk/rows.csv", "限时 24 题（限时 3 分钟和 2 分钟两版）", "不开；加并行提示的深度 1、2 各配 K=1、2、4、8、16（每版 10 次）", "等", "隐藏测试"),
        ("不限时 24 题批", "results/analysis-ctl-free-all/rows.csv", "不限时 24 题", "不开、默认；加并行提示的深度 1、2 各配 K=1、2、4、8、16、64（10 或 20 次）", "等", "隐藏测试"),
        ("大型编码题批", "results/analysis-xl-main/rows-all.csv", "大型编码题", "不开；原题面的 K=4、8、16 和深度 2；加不复核提示的 K=1、2、4、8、16 和深度 2（各 10 次）", "等", "隐藏测试"),
        ("大型编码题深度批", "results/analysis-xl-depth/rows-all.csv", "大型编码题", "加不复核提示的深度 1、2 各配 K=16、64（各 10 次）", "等", "隐藏测试"),
        ("办公报告题主要的一批", "results/analysis-office-confirm/rows-all.csv", "办公报告题", "不开、K=1、K=2、K=4、默认、深度 2（每题 20 次）。重做一遍来确认第一批的结果，正文办公报告题的数多数出自这一批", "不等", "事实清单"),
        ("K=64 批", "results/analysis-office-highk/rows-all.csv", "办公报告题", "四种：默认；K=64；深度 2、K=64；深度 3、K=64（每题 10 次）", "等", "先按评分表打总分，后来改按事实清单判"),
        ("多查 100/100 那一批", "results/analysis-office-floor/rows-all.csv", "办公报告题", "不开、不开加多查 100/100、默认、默认加都写进去提示（每题 20 次）", "不等", "事实清单"),
        ("都写进去提示的深度批", "results/analysis-office-keep-depth/rows-all.csv", "办公报告题", "加都写进去提示的默认和深度 2（每题 10 次）", "等", "事实清单"),
        ("评测集填表题选题", "results/analysis-ws-screen/rows-all.csv", "WideSearch 的 65 道中文题", "不开（每题 1 次）", "—", "逐项 F1"),
        ("评测集填表题批", "results/analysis-ws-h1/rows-all.csv", "评测集填表题", "不开、默认、默认加并行提示（每题 1 次）", "等", "逐项 F1"),
        ("评测集报告题第一批", "results/analysis-drb2-h1/rows-all.csv", "评测集报告题", "不开、默认（每题 1 次）", "等", "评测集的评分项"),
        ("评测集报告题第二批", "results/analysis-drb2-kd/rows-all.csv", "评测集报告题", "K=1、默认、深度 2（每题 1 次）", "等", "评测集的评分项"),
        ("多查 150/250、250/500 那一批", "results/analysis-office-dose/rows-all.csv", "办公报告题", "不开、不开加多查 150/250、不开加多查 250/500、默认（每题 20 次）", "不等", "事实清单"),
        ("评测集填表题补测批", "results/analysis-ws-k4/rows-all.csv", "评测集填表题", "K=1、K=4、默认、深度 2（每题 1 次）", "等", "逐项 F1"),
        ("评测集报告题补测批", "results/analysis-drb2-k4/rows-all.csv", "评测集报告题", "K=4、默认（每题 1 次）", "等", "评测集的评分项")]
    if TD:
        BATCHES.append(("告知上限批", ce.TOLD_ROWS, "办公报告题", "K=2、默认，各配工具说明里写明上限与否（每题 20 次）", "不等", "事实清单"))
    files_ = ce.every_rows()
    assert {b_[1] for b_ in BATCHES} == set(files_), sorted(set(files_) ^ {b_[1] for b_ in BATCHES})
    brun = {b_[1]: len(ce.R(b_[1])) for b_ in BATCHES}
    for b_ in BATCHES:  # the column "waits" against the groups of the batch: the groups run with the waiting patch are named W-...
        gs_ = {r["group"] for r in ce.R(b_[1]) if r["group"] != "D0" and not r["group"].endswith("-D0")}
        w_ = {g_.startswith("W-") for g_ in gs_}
        assert b_[4] == ("—" if not gs_ else "两种都有" if len(w_) == 2 else "等" if w_ == {True} else "不等"), (b_[0], sorted(gs_))
    assert sum(brun.values()) == cv["total"]
    d.tbl("batches", f"各批实验：任务、设置、进程等不等 subagent、质量怎么判、运行次数（共 {cv['total']:,} 次）。每一批按随机完全区组跑：一轮把各组各跑一次，顺序用固定的种子打乱，同时运行的个数固定；对比都在批内做。"
          f"另有两批合并稿，各 {mu_n // 2} 次合并运行（每题 10 个两份合并、5 个四份合并），不计入这个总数：前一批合并的是“办公报告题主要的一批”里不开 subagent 的报告，后一批合并的是“多查 100/100 那一批”里不开 subagent 的报告。", [
        ["批（下文的叫法）", "任务", "有哪些设置", "进程等不等 subagent", "质量怎么判", "运行次数"]] + [[b_[0], b_[2], b_[3], b_[4], b_[5], f"{brun[b_[1]]:,}"] for b_ in BATCHES])
    d.add("### K、深度各取值对默认的差和区间", "")
    # The decision frame of the main text (fixed when the report was written): a value is not worse in quality when the
    # lower end of the interval of its difference stays above the margin, not slower when the upper end of the interval
    # of its time ratio stays below TM; beyond the margin it is worse when the whole interval lies on the bad side.
    QM = lambda key_: 8 if key_ == "office" else 5  # noqa: E731  (margin of "not worse": points; percentage points on the office task)
    TM = 1.25                                        # margin of "not slower": upper end of the interval of the time ratio
    SYM = {"ok": "✓", "worse": "✗", "open": "?"}

    def qstate(cl_: dict, key_: str):
        c_ = cl_.get("legacy") if key_ == "office" else cl_["q"]   # the office task on the 63 items fixed beforehand
        return None if c_ is None else "ok" if c_["lo"] > -QM(key_) else "worse" if c_["hi"] < 0 else "open"

    def tstate(cl_: dict):
        c_ = cl_["t"]
        return None if c_ is None else "ok" if c_["hi"] < TM else "worse" if c_["lo"] > 1 else "open"

    def sgz(v: float, nd: int) -> str:
        """Signed v; more decimals when it would print as zero without being zero (an interval end just off 0)."""
        for k_ in (nd, nd + 1, nd + 2):
            if v == 0 or abs(v) >= 0.5 * 10 ** -k_:
                return "0" if v == 0 else sg(v, k_)
        return sg(v, nd + 2)

    def irow(r: dict, label: str, what: str, cl: dict) -> list:
        """A row of the two full tables of the main text: the difference in quality with its interval and its state in
        the decision frame, the cost ratio, the time ratio with its state. The office task on the 63 items fixed
        beforehand, the whole list in brackets behind it; the timed task is for reference and gets no state."""
        office = r["key"] == "office"
        assert not office or cl["legacy"] is not None
        qd = cl["legacy"] if office else cl["q"]
        est_ = "0" if abs(qd["est"]) < 0.5 * 10 ** -cl["nd"] else sg(qd["est"], cl["nd"])
        qtxt = "0（都是满分）" if qd["est"] == qd["lo"] == qd["hi"] == 0 else f"{est_} [{sgz(qd['lo'], cl['nd'])}, {sgz(qd['hi'], cl['nd'])}]"
        if office:
            qtxt += f"（全清单 {ci(cl['q'])}）"
        pairs = str(qd.get("n") or "—")
        if cl["t"] and cl["t"].get("n") and qd.get("n") and cl["t"]["n"] != qd["n"]:
            pairs += f"（时间 {cl['t']['n']}）"
        limited = bool(r.get("limited"))
        bold = lambda t_, on_: f"**{t_}**" if on_ else t_  # noqa: E731  (a difference the report counts as detected: ce.strong, the filled points of the figures)
        exact_no = bool(r.get("tests")) and qd.get("p") is not None and qd["p"] >= 0.05  # scores next to full marks: the exact test decides
        q_on = not limited and not exact_no and not (qd["est"] == qd["lo"] == qd["hi"] == 0) and ce.strong(qd, cl["corr"][0] and not office)
        qcell = bold(qtxt.split("（全清单")[0], q_on) + ("（全清单" + qtxt.split("（全清单")[1] if "（全清单" in qtxt else "")
        ccell = bold(xci(cl["c"]), ce.strong(cl["c"], cl["corr"][1])) if cl["c"] else "—"
        tcell = "限时" if limited else bold(xci(cl["t"]), ce.strong(cl["t"], cl["corr"][2]))
        return [label, what, pairs, qcell, ccell, tcell]
    irows = [irow(r, (r.get("rule_name", r["name"]) + (f"（{r['rule_sub']}）" if "rule_sub" in r else SUBL[r["sub"]])) if i == 0 else "",
                  f"K={v}" + (f"（{r['rule_what']}）" if r.get("rule_what") and v in r["rule"] else ""), cl)
             for r in L["k"] for i, (v, cl) in enumerate(sorted(ce.rule_cells(r).items()))]  # the uniform rule of the main text
    DSUB = {"": "", "原题面": "（原题面）", "题面加不复核提示": "（加不复核提示）", "深度 2：题面加并行提示": ""}
    dname = {0: "不开 subagent", 2: "深度 2", 3: "深度 3"}
    drows_ = []
    several = {2: f"（{CN[p2k8['batches']]}批合起来算）", 3: f"（{CN[p3k8['batches']]}批合起来算）"}
    for r in L["depth"]:
        for i, (v, cl) in enumerate(sorted(r["cells"].items())):
            what = dname[v] + (f"（{cl['note']}，题面加并行提示）" if cl["note"] else "") + (several[v] if r["key"] == "office" and v in several else "")
            drows_.append(irow(r, (r["name"] + DSUB[r["sub"]]) if i == 0 else "", what, cl))
        for v, cl in sorted(r.get("k64", {}).items()):
            drows_.append(irow(r, "", f"深度 {v}、K=64（对同批的默认）", cl))
    d.tbl("limits-ci", "{fig:k-quality}、{fig:k-cost}、{fig:k-time} 各点的估计值和 95% 区间：换 K 对同批的 K=8（深度都是 1）。质量是差（办公报告题是写对的事实占比，个百分点；其余是得分；大型编码题上少过 1 个测试约少 0.02 分），费用和时间是倍数。"
          "题面加了并行提示或不复核提示的各行，对照的 K=8 组也加了同样的提示。", [["任务（题面）", "取值", "对数", "质量之差", "费用倍数", "时间倍数"]] + irows)
    d.tbl("limits-ci-d", "{fig:d-quality}、{fig:d-cost}、{fig:d-time} 各点的估计值和 95% 区间：换深度对同批的深度 1（K 都是 8）。读法同上一张表。“不开 subagent”的各行是把默认对不开的对比反过来写；"
          "大型编码题（加不复核提示）一行的“不开 subagent”，用的是同一批里原题面的不开 subagent 组。办公报告题最后两行是深度 2、3 同时把 K 放到 64 的两组，图里没有画。",
          [["任务（题面）", "取值", "对数", "质量之差", "费用倍数", "时间倍数"]] + drows_)
    d.add("### 各设置下运行是怎么结束的", "")
    d.tbl("deliver-all", "办公报告题以外的任务：各种设置下运行是怎么结束的（各批、各个 K 和加提示的组加在一起；办公报告题见{tab:deliver}）。"
          "“提前结束”指主 agent 结束时还有 subagent 没做完，只对进程不等 subagent 的组统计；“等到上限”指进程等了 20 分钟还有 subagent 没结束；内存一列只在大型编码题上记录。“—”是没有记录或不适用。限时 24 题到时限是设计如此，不列。", [
        ["任务", "设置", "进程等不等 subagent", "运行次数", "交付不完整", "提前结束", "退出时崩溃", "其它非正常退出", "到时限", "等到上限", "有进程因内存被杀"]] + arows)
    d.add("### 分任务结果表", "")
    # ---- office tasks
    d.add("#### 办公报告题", "")
    d.figure("office", f"{NEW}/task-office.png", "办公报告题主要的一批：各组的质量、费用、时间和 subagent 数。细线是各组均值的 95% 区间；每组 39–40 份报告。")
    order = ["D0", "D1-K1", "D1-K2", "D1-K4", "D1-K8", "D2-K8"]
    name = {"D0": "不开 subagent", "D1-K1": "K=1", "D1-K2": "K=2", "D1-K4": "K=4", "D1-K8": "默认（K=8）", "D2-K8": "深度 2（K=8）"}
    vd = {g: verdict(cmp_[g]["right_pct"], 8, corrected=g in ("D1-K1", "D1-K2", "D1-K4")) for g in order if g != "D1-K8"}
    row = lambda label, fn: [label] + [fn(g) for g in order]  # noqa: E731
    d.tbl("office", "办公报告题主要的一批各组结果（每组 39–40 份报告；差和倍数都是对默认，按配对算，所以和两列均值直接相减会差一点）。", [
        ["指标"] + [name[g] for g in order],
        row("写对的事实占比（%）", lambda g: f(m[g]["right_pct"])),
        row("和默认的差（个百分点）", lambda g: "—" if g == "D1-K8" else ci(cmp_[g]["right_pct"])),
        row("判断", lambda g: "—" if g == "D1-K8" else vd[g]),
        row("只算事先定下的 63 条：和默认的差", lambda g: "—" if g == "D1-K8" else ci(leg[g])),
        row("费用（元/次）", lambda g: f(m[g]["cost"], 2)),
        row("其中模型费", lambda g: f(m[g]["model_cost"], 2)),
        row("其中搜索费", lambda g: f(m[g]["cost"] - m[g]["model_cost"], 2)),
        row("费用倍数", lambda g: "—" if g == "D1-K8" else x(cmp_[g]["total_cost_peak"])),
        row("时间（分钟）", lambda g: f(m[g]["minutes"])),
        row("subagent 数", lambda g: f(m[g]["kids"])),
        row("搜索请求数", lambda g: f(m[g]["search"], 0))])
    d.figure("tradeoff", f"{NEW}/office-tradeoff.png", "办公报告题：各种设置对同批默认的费用倍数和质量之差。竖线是 95% 区间。往右是更贵，往上是写对的更多。多查提示只画了多查 100/100；多查 150/250、多查 250/500 和默认加都写进去提示没有画，数在{tab:other}。")
    d.figure("depth", f"{NEW}/office-repeats.png", "办公报告题：深度 2 减去深度 1 的写对的事实占比。上面四批只改深度（K=8），空心点是各批的结果，实心点是四批合起来算；最下面一行同时把 K 放到 64，不计入合计。横线是 95% 区间。批的名字见{tab:batches}。")
    ok_ = o["other_kids"]
    orow = lambda batch, label, diff, vtext, cost, time, kids, legacy: [batch, label, str(diff["n"]), ci(diff), vtext, ci(legacy), x(cost), time, kids]  # noqa: E731
    assert verdict(o["wait"]["WD3"]["right_pct"], 8) == "没测出差别" and verdict(o["k64_d2"]["right_pct"], 8) == "没测出差别" and verdict(fl["PRIM"]["right_pct"], 8) == "显著变差"
    d.tbl("other", "办公报告题的其它设置（差和倍数都是对同一批里的默认；批的名字见{tab:batches}）。", [
        ["批", "设置", "配对数", "写对的事实占比之差（个百分点）", "判断", "只算事先定下的 63 条", "费用倍数", "时间倍数", "subagent 数"],
        orow("K=64 批", "K=64（深度 1）", o["k64"]["right_pct"], k64v, o["k64"]["total_cost_peak"], x(o["k64"]["answer_s"]), f(ok_["k64"]), lg["k64"]),
        orow("等 subagent 批", "深度 3（K=8）", o["wait"]["WD3"]["right_pct"], "没测出差别", o["wait"]["WD3"]["total_cost_peak"], f"{x(o['wait']['WD3']['seconds'])}（注 1）", f(ok_["d3"]), lg["d3k8"]),
        orow("K=64 批", "深度 2、K=64", o["k64_d2"]["right_pct"], "没测出差别（注 2）", o["k64_d2"]["total_cost_peak"], x(o["k64_d2"]["answer_s"]), f(ok_["d2k64"]), lg["d2k64"]),
        orow("K=64 批", "深度 3、K=64（相当于旧默认）", o["k64_d3"]["right_pct"], f"{verdict(o['k64_d3']['right_pct'], 8)}（注 2）", o["k64_d3"]["total_cost_peak"], x(o["k64_d3"]["answer_s"]), f(ok_["d3k64"]), lg["old"]),
        orow("多查 100/100 那一批", "默认 + 都写进去提示（只算交出完整报告的）", kd_["right_pct"], "显著变好（注 3）", kd_["total_cost_peak"], x(kd_["seconds"]), f(wfl["kids"][1]), lg["keep_done"]),
        orow("多查 100/100 那一批", "不开 subagent + 多查 100/100", fl["PRIM"]["right_pct"], "显著变差", fl["PRIM"]["total_cost_peak"], x(fl["PRIM"]["seconds"]), "0", lg["more"]),
        orow("多查 150/250、250/500 那一批", "不开 subagent + 多查 150/250", dc["P150"]["right_pct"], verdict(dc["P150"]["right_pct"], 8, True), dc["P150"]["total_cost_peak"], x(dc["P150"]["answer_s"]), "0", dc["P150"]["right_legacy_pct"]),
        orow("多查 150/250、250/500 那一批", "不开 subagent + 多查 250/500", dc["P250"]["right_pct"], verdict(dc["P250"]["right_pct"], 8, True), dc["P250"]["total_cost_peak"], x(dc["P250"]["answer_s"]), "0", dc["P250"]["right_legacy_pct"]),
        orow("合并稿（两批合起来算）", "两份不开 subagent 的报告合并", mp2["facts"], verdict(mp2["facts"], 8), mp2["cost"], x(mp2["time"]), "0", mp2["legacy"]),
        orow("合并稿（两批合起来算）", "四份不开 subagent 的报告合并", mp4["facts"], "显著变好", mp4["cost"], x(mp4["time"]), "0", mp4["legacy"])])
    d.p(f"注 1：这一组只记了整个进程的时长，含等 subagent 结束的时间。注 2：这两组所在的 K=64 批里，深度 1 有两组：默认（K=8）和 K=64。表里是对默认比；改成对这两个深度 1 组的平均比，这两行分别是 {ci(bb['W-D2-K64']['facts'])} 和 {ci(bb['W-D3-K64']['facts'])}。"
        "注 3：只算交出完整报告的运行；另外两种算法见“方法补充”。")
    dg_ = ["D0", "E-D0", "N-D0", "D1-K8"]
    dname_ = {"D0": "不开 subagent", "E-D0": "多查 150/250", "N-D0": "多查 250/500", "D1-K8": "默认"}
    dline = lambda label, fn: [label] + [fn(g) for g in dg_]  # noqa: E731
    assert verdict(dc["P150"]["right_pct"], 8, True) == verdict(dc["P250"]["right_pct"], 8, True) == "显著变差"
    d.tbl("dose", "办公报告题：让不开 subagent 的 agent 多查的那一批各组结果（每题每组 20 次；没交出完整报告的 1 次不算）。", [
        ["指标"] + [dname_[g] for g in dg_],
        dline("算进来的运行数", lambda g: str(dm[g]["n"])),
        dline("写对的事实占比（%）", lambda g: f(dm[g]["right_pct"])),
        dline("只算事先定下的 63 条（%）", lambda g: f(dm[g]["right_legacy_pct"])),
        dline("写错的条数", lambda g: f(dm[g]["wrong"])),
        dline("搜索请求数", lambda g: f(dm[g]["search"], 0)),
        dline("打开的网页数（下限）", lambda g: f(dpg[g]["low"], 0)),
        dline("其中脚本存盘的", lambda g: f(dpg[g]["saved"], 0)),
        dline("其中 web_fetch 逐个打开的", lambda g: f(dpg[g]["fetch"], 0)),
        dline("其余（命令里直接抓的，至少这么多）", lambda g: f(dpg[g]["low"] - dpg[g]["saved"] - dpg[g]["fetch"], 0)),
        dline("费用（元/次）", lambda g: f(dm[g]["cost"], 2)),
        dline("其中模型费", lambda g: f(dm[g]["model_cost"], 2)),
        dline("到最终回答的时间（分钟）", lambda g: f(dm[g]["minutes"])),
        dline("报告字数（万）", lambda g: f(dm[g]["chars"] / 1e4)),
        dline("主 agent 输入峰值中位（万 token）", lambda g: f(dm[g]["peak_median"] / 1e4)),
        dline("发生上下文裁剪的运行", lambda g: str(dm[g]["pruned"]))])
    rrow = lambda r: [r["label"], str(r["runs"]), f(r["handed"]), f(r["final"]), f(r["lost"]), f"{100 * r['lost_share']:.1f}%", f(r["own"])]  # noqa: E731
    d.tbl("relay", f"办公报告题：subagent 交回给主 agent 的消息里写对的事实，有多少没进最终报告（五组各取前 10 次重复，判了 {rl['runs']} 份；条数是每份的平均）。", [
        ["组", "运行数", "交回的消息里写对", "最终报告写对", "交回了但没进最终报告", "占交回的", "最终报告里有、消息里没有"]] + [rrow(r) for r in rl["rows"]])
    d.p(f"交回的消息只算 subagent 发给主 agent 的文字，它们直接写进工作目录的文件不算，所以“交回的消息里写对”是下限。同批配对：深度 2 对深度 1 没进最终报告的条数 {ci(rl['depth'])}；"
        f"加了都写进去提示以后是 {ci(rl['keep'])}，同时“最终报告里有、消息里没有”的是 {ci(rl['keep_own'])}。")
    d.figure("relay", f"{NEW}/relay-loss.png", "办公报告题：subagent 交回的消息里写对的事实，进了最终报告和没进的各有多少（{tab:relay} 的数）。")
    # ---- public benchmarks
    wp, dp = ws["pair"], drb["pair"]
    d.add("#### 两个公开评测集", "")
    d.figure("pub", f"{NEW}/task-public.png", "两个公开评测集：不开 subagent 和默认的得分、费用和时间。只算两组的运行都有效的题。细线是各组均值的 95% 区间。")
    prow = lambda a, b_, g, sc, rc_, diff: [a, b_, f(g[sc]), diff, f(g[rc_]), f(g["cost"], 2), f(g["model"], 2), f(g["answer_minutes"]), f(g["kids"])]  # noqa: E731
    d.tbl("public", f"两个公开评测集上开不开 subagent（每题每组 1 次；两组的运行都有效的题，评测集填表题 {wp['n']} 道、评测集报告题 {dp['n']} 道）。召回指标准答案要的内容找到了多少。", [
        ["评测集", "组", "得分", "和不开的差", "召回", "费用（元/次）", "其中模型费", "时间（分钟）", "subagent 数"],
        prow("评测集填表题", "不开 subagent", wp["D0"], "f1_item", "r_item", "—"),
        prow("", "默认", wp["W-D1-K8"], "f1_item", "r_item", ci(ws["cmp"]["H1n"]["f1_item"])),
        prow("评测集报告题", "不开 subagent", dp["D0"], "total", "info_recall", "—"),
        prow("", "默认", dp["W-D1-K8"], "total", "info_recall", ci(dt))])
    d.figure("pub-kd", f"{NEW}/pub-paired-kd.png", "评测集报告题，每道题一个点：横轴是默认的总分，纵轴是 K=1（左）和深度 2（右）的总分。")
    d.tbl("pubkd", "评测集报告题第二批：换 K 和深度（差和倍数都是对同批的默认）。", [
        ["设置", "总分之差", "召回之差", "费用倍数", "时间倍数", "subagent 数"],
        ["K=1", ci(kd["cmp"]["K1"]["total"]), ci(kd["cmp"]["K1"]["info_recall"]), x(kd["cmp"]["K1"]["total_cost_peak"]), rc(kt["K1"]), f(kd["groups"]["W-D1-K1"]["children"])],
        ["深度 2", ci(kd["cmp"]["D2"]["total"]), ci(kd["cmp"]["D2"]["info_recall"]), x(kd["cmp"]["D2"]["total_cost_peak"]), rc(kt["D2"]), f(kd["groups"]["W-D2-K8"]["children"])]])
    wsk_, drbk_ = p["wsk"], p["drbk"]
    kcell = lambda b_, q_, key_, lab, word: [lab, str(b_["cmp"][q_][key_]["n"]), ci(b_["cmp"][q_][key_]), word,  # noqa: E731
                                             ci(b_["cmp"][q_]["r_item" if key_ == "f1_item" else "info_recall"]), xci(b_["cmp"][q_]["total_cost_peak"]), xci(b_["time"][q_])]
    orun = lambda o_: f"{o_['cap_runs']}/{o_['runs']}"  # noqa: E731
    kids_every = {(b_, g_): st.mean(cd.num(r_["children"]) or 0 for r_ in cd.R(f"results/analysis-{b_}/rows-all.csv") if r_["group"] == g_)  # subagents opened, every run of the group
            for b_, gs_ in (("ws-k4", ("W-D1-K1", "W-D1-K4", "W-D1-K8", "W-D2-K8")), ("drb2-k4", ("W-D1-K4", "W-D1-K8"))) for g_ in gs_}
    d.tbl("pubk", f"两个公开评测集补测 K=4 的两批（每题每组 1 次；差和倍数都是对同批的默认，按题配对；带 ★ 的两行是事前写定的主要对比，两个一起校正）。评测集填表题有 {wsk_['flagged']} 次运行在日志里出现了评测集的名字或题号，不计分；"
          f"把它们算进去，K=4 那一行是 {ci(wsk_['with_flagged']['K4'])}（24 对）。最后两列是这一组自己的数，按全部运行算（含不计分的）。", [
        ["评测集", "设置", "配对数", "质量之差", "判断", "召回之差", "费用倍数", "时间倍数", "开的 subagent 数", "有调用被 K 拒绝的运行"],
        ["评测集填表题"] + kcell(wsk_, "K4", "f1_item", "K=4 ★", verdict(wk4, 5, True)) + [f(kids_every[("ws-k4", "W-D1-K4")]), orun(wko["W-D1-K4"])],
        [""] + kcell(wsk_, "K1", "f1_item", "K=1", verdict(kq("ws", 1), 5)) + [f(kids_every[("ws-k4", "W-D1-K1")]), orun(wko["W-D1-K1"])],
        [""] + kcell(wsk_, "D2", "f1_item", "深度 2", verdict(dq("ws", 2), 5)) + [f(kids_every[("ws-k4", "W-D2-K8")]), orun(wko["W-D2-K8"])],
        ["", "默认", "—", f"（{f(wsk_['groups']['W-D1-K8']['f1_item'])} 分）", "—", f"（{f(wsk_['groups']['W-D1-K8']['r_item'])}）", f"（{f(wsk_['groups']['W-D1-K8']['total_cost_peak'], 2)} 元）", f"（{f(wsk_['base']['answer_minutes'])} 分钟）",
         f(kids_every[("ws-k4", "W-D1-K8")]), orun(wko["W-D1-K8"])],
        ["评测集报告题"] + kcell(drbk_, "K4", "total", "K=4 ★", verdict(dk4_, 5, True)) + [f(kids_every[("drb2-k4", "W-D1-K4")]), orun(dko["W-D1-K4"])],
        ["", "默认", "—", f"（{f(drbk_['groups']['W-D1-K8']['total'])} 分）", "—", f"（{f(drbk_['groups']['W-D1-K8']['info_recall'])}）", f"（{f(drbk_['groups']['W-D1-K8']['total_cost_peak'], 2)} 元）", f"（{f(drbk_['base']['answer_minutes'])} 分钟）",
         f(kids_every[("drb2-k4", "W-D1-K8")]), orun(dko["W-D1-K8"])]])
    assert ce.strong(drbk_["cmp"]["K4"]["search_aux"]) and drbk_["cmp"]["K4"]["search_aux"]["est"] > 1.2
    d.p(f"评测集报告题上 K=4 的搜索请求是默认的 {xci(drbk_['cmp']['K4']['search_aux'])}（没有校正；K=4 这组开的 subagent 也略多），费用和时间的估计值跟着偏高，区间都含 1。")

    # ---- code reading
    d.add("#### 读代码题（含和小编程题三题一起的对比）", "")
    d.figure("code", f"{NEW}/task-code.png", "读代码题（两题平均）：各组的得分、模型费和时间。细线是各组均值的 95% 区间；每组 20 次。")
    cm_ = c["means"]
    cg = ["D0", "D1-K8", "D2-K8", "D3-K8", "E-D1-K8", "E-D1-K4", "E-D1-K2", "E-D1-K1", "E-D2-K8", "E-D3-K8"]
    cname = {"D0": "不开 subagent", "D1-K8": "默认", "D2-K8": "深度 2", "D3-K8": "深度 3", "E-D1-K8": "并行提示，K=8", "E-D1-K4": "并行提示，K=4", "E-D1-K2": "并行提示，K=2", "E-D1-K1": "并行提示，K=1", "E-D2-K8": "并行提示，深度 2", "E-D3-K8": "并行提示，深度 3"}
    d.tbl("code", "读代码题各组结果（两题平均，每组 20 次；不联网，费用只有模型费）。", [
        ["指标"] + [cname[g] for g in cg],
        ["得分"] + [f(cm_[g]["score"]) for g in cg],
        ["模型费（元/次）"] + [f(cm_[g]["cost"], 2) for g in cg],
        ["时间（分钟）"] + [f(cm_[g]["minutes"]) for g in cg],
        ["subagent 数"] + [f(cm_[g]["kids"]) for g in cg]])
    crow = lambda label, q: [label, ci(c3[q]["score"]), verdict(c3[q]["score"], 5), x(c3[q]["model_cost_peak"]), x(c3[q]["seconds"]), ci(c["cmp"][q]["score"])]  # noqa: E731
    d.tbl("code3", "读代码题和小编程题三道题一起的对比（每个对比 30 对；这是事先定的算法），最后一列是只看两道读代码题。", [
        ["对比", "得分差（三道题）", "判断", "模型费倍数", "时间倍数", "得分差（只看两道读代码题）"],
        crow("默认对不开 subagent", "C1"), crow("并行提示（K=8）对默认", "C2"),
        crow("K=1 对 K=8（都加并行提示）", "C3a"), crow("K=2 对 K=8", "C3b"), crow("K=4 对 K=8", "C3c"),
        crow("深度 2 对深度 1（都加并行提示）", "C4a"), crow("深度 3 对深度 1", "C4b")])
    # ---- control tasks
    d.add("#### 两道对照题", "")
    d.figure("controls", f"{NEW}/task-controls.png", "两道对照题：各组的得分、模型费、时间和 subagent 数。细线是各组均值的 95% 区间；每组 10 次。")
    cgs = ["D0", "W-D1-K8", "W-E-D1-K8"]
    d.tbl("controls", "两道对照题各组结果（每组 10 次；不联网，费用只有模型费）。", [
        ["题", "指标", "不开 subagent", "默认", "并行提示，K=8"],
        ["限时 24 题", "得分"] + [f(wd["means"][g]["score"]) for g in cgs],
        ["", "测试全过的题数（共 24 道）"] + [f(wd["solved"][g]) for g in cgs],
        ["", "模型费（元/次）"] + [f(wd["means"][g]["cost"], 2) for g in cgs],
        ["", "时间（分钟）"] + [f(wd["means"][g]["minutes"]) for g in cgs],
        ["", "subagent 数"] + [f(wd["means"][g]["kids"]) for g in cgs],
        ["16 步串行题", "得分"] + [f(ch["means"][g]["score"]) for g in cgs],
        ["", "模型费（元/次）"] + [f(ch["means"][g]["cost"], 2) for g in cgs],
        ["", "时间（分钟）"] + [f(ch["means"][g]["minutes"]) for g in cgs],
        ["", "subagent 数"] + [f(ch["means"][g]["kids"]) for g in cgs]])
    d.figure("grid", f"{NEW}/task-grid.png", f"限时 24 题（题面加并行提示）换 K 和深度以后的得分。虚线是不开 subagent（这一组是 {gr['m3']['means']['D0']:.0f} 分，{{tab:controls}} 那一组是 {wd['means']['D0']['score']:.0f} 分，各 10 次）；"
             "细线是 10 次运行里的最低和最高。右边限时 2 分钟的一版波动很大，只作参考。")
    # ---- code building
    d.add("#### 不限时 24 题和大型编码题", "")
    d.figure("pkg", f"{NEW}/task-package.png", "大型编码题：各组到最终回答的时间、模型费和 subagent 数。细线是各组均值的 95% 区间；每组 10 次。")
    xg = ["D0", "W-D1-K4", "W-D1-K8", "W-D1-K16", "W-N-D1-K1", "W-N-D1-K2", "W-N-D1-K4", "W-N-D1-K8", "W-N-D1-K16"]
    xname = {"D0": "不开 subagent", "W-D1-K4": "原题面，K=4", "W-D1-K8": "默认（原题面，K=8）", "W-D1-K16": "原题面，K=16", "W-N-D1-K1": "不复核提示，K=1", "W-N-D1-K2": "不复核提示，K=2",
             "W-N-D1-K4": "不复核提示，K=4", "W-N-D1-K8": "不复核提示，K=8", "W-N-D1-K16": "不复核提示，K=16"}
    d.tbl("pkg", "大型编码题各组结果（每组 10 次；不联网，费用只有模型费）。", [
        ["指标"] + [xname[g] for g in xg],
        ["到最终回答的时间（分钟）"] + [f(xm[g]["answer"]) for g in xg],
        ["文件都写完的时间（分钟）"] + [f(xm[g]["written"]) for g in xg],
        ["模型费（元/次）"] + [f(xm[g]["cost"], 2) for g in xg],
        ["subagent 数（其中复核的）"] + [f"{f(xm[g]['kids'])}（{f(xm[g]['review'])}）" for g in xg],
        [f"没通过的隐藏测试（共 {xl['tests']:,} 个）"] + [f(xl["failed"][g]) for g in xg]])
    d.figure("ex", f"{NEW}/task-exercises.png", f"不限时 24 题：各组到最终回答的时间、模型费和 subagent 数。细线是各组均值的 95% 区间；每组 20 次（K=64 是 10 次，其中 {fm_['W-E-D1-K64']['n_answer']} 次给出了最终回答）。")
    eg = ["D0", "W-D1-K8"] + [f"W-E-D1-K{q}" for q in (1, 2, 4, 8, 16, 64)]
    ename = dict({"D0": "不开 subagent", "W-D1-K8": "默认"}, **{f"W-E-D1-K{q}": f"并行提示，K={q}" for q in (1, 2, 4, 8, 16, 64)})
    d.tbl("ex", "不限时 24 题各组结果（不联网，费用只有模型费）。", [
        ["指标"] + [ename[g] for g in eg],
        ["得分"] + [f(fm_[g]["score"]) for g in eg],
        ["到最终回答的时间（分钟）"] + [f(fm_[g]["answer"]) + ("" if fm_[g]["n_answer"] == fm_[g]["n"] else f"（{fm_[g]['n_answer']} 次）") for g in eg],
        ["文件都写完的时间（分钟）"] + [f(fm_[g]["written"]) for g in eg],
        ["模型费（元/次）"] + [f(fm_[g]["cost"], 2) for g in eg],
        ["subagent 数（其中文件都写完以后才派的）"] + [f"{f(fm_[g]['kids'])}（{f(fm_[g]['review'])}）" for g in eg]])
    # ---- how things were computed
    # ---- the primary comparisons written down beforehand, and the results expected beforehand
    d.add("### 事前写定的主要对比", "")
    sc, ex = E["scorecard"], E["expect"]

    def sword(r: dict, g: dict) -> str:
        """The word for a primary comparison (clean_extra.primary_word); for differences it must agree with verdict()."""
        assert g["ratio"] or r["word"] == verdict(r, g["margin"], corrected=r["family_size"] > 1), (g["title"], r["key"])
        return r["word"]
    srows, n_all, n_sig = [], 0, 0
    for g in sc:
        for i, r in enumerate(g["rows"]):
            word = sword(r, g)
            n_all += 1
            n_sig += word.startswith("显著")
            zero = lambda v: "0.0" if abs(v) < 0.05 else sg(v)  # noqa: E731
            res = f"×{r['est']:.2f} [{r['lo']:.2f}, {r['hi']:.2f}]" if g["ratio"] else (f"{zero(r['est'])} [{zero(r['lo'])}, {zero(r['hi'])}]" if abs(r["est"]) + abs(r["hi"]) > 0 else "0（都是满分）")
            srows.append([g["title"] if i == 0 else "", r["label"], str(r["n"]), res, word])
    assert n_all == (79 if TD else 77) and 11 <= n_sig <= 17
    d.p(f"主要对比和读法都是在读到结果之前写进方案的。全部 {n_all} 个主要对比的结果在{{tab:score}}（各批自己的统计，同一批的几个对比一起做 Holm 校正），其中显著的 {n_sig} 个。"
        "正文各表里不在这张表上的对比，是事前列明的次要对比或标了“事后”的分析。")
    fc = ex["first_complete"]
    m2k, m4k = o["m2_vs_keep"], o["m4_vs_keep"]
    assert m2k["hi"] < 0 and verdict(m4k, 8) == "没有差别" and all(v["n"] == 19 for v in fc.values())
    d.add("不是在开跑之前写定的地方：", "",
          "- 第一批实验的对比清单是开跑以后、读到结果之前定的。",
          f"- 第一批实验里“没交出完整报告的运行不计分”这条规则是看到得分以后加的。表里第一组按原来写定的算法（全部运行）。按后来的规则，深度 2、深度 3 和最后一行分别是 {ci(fc['H3a'])}、{ci(fc['H3b'])}、{ci(fc['H4'])}（各 19 对）。",
          "- 按事实清单重新判分，是对已经跑完的运行换一种判法；对比写在重新判分之前。",
          "- 不限时 24 题：第二轮的设计是第一轮还在跑的时候写的，第二轮开跑之前已经看过第一轮的结果，20 对的各行是两轮合在一起；K=64 那两行只有 8 对，“没有最终回答的运行不算时间”这条规则是看到结果以后加的。",
          "- 大型编码题 K=16 的深度那一行只有 9 对：有一次运行 27 秒就结束、一个文件没写，去掉它的规则是看到这次运行以后加的。",
          "- 深度 2 配都写进去提示：读法在开跑 5 分钟后改过（区间从 97% 改成 95%，不再跑第二段），当时还没有运行结束。",
          "- 限时 24 题批：限时 3 分钟和 2 分钟两版在方案里是同等的两组主要对比；方案 10 月 3 日 17:20Z（这一批出统计之前）又写明带时限的两批只作参考。"
          "正文给 3 分钟的一版、把 2 分钟的一版只放在附录，是看到结果（2 分钟的一版波动很大）以后定的。", "")
    d.add("另外几点：", "",
          "- 办公报告题第一批用评分表判，后来改用事实清单，所以两种判法各有一组。",
          "- 限时 24 题“并行提示对不开 subagent”这一行，这一批自己事前写的标准是至少高 10 分且区间不含 0；结果差 0.2 分没到 10 分，表里的判断词按全篇统一的定义写。",
          f"- 两份、四份报告合并的两批，对比的定位先后改过（只作描述，或者作主要对比），没有列进这张表。合并稿对默认的结果在{{tab:spend}}；对加了都写进去提示、交出完整报告的默认，两份合并是 {ci(m2k)}，四份合并是 {ci(m4k)}。",
          "- K 的各条读法和各批的深度读法，什么时候写的、写的时候看过哪些结果，在{tab:k-readings} 和{tab:d-readings}。10 月 3 日的定 K 规则写在不限时 24 题第二轮的数据读出来之前，"
          "但读代码题、办公报告题两条的结果那时已经在手，不算事前写定；按它得到的是 K=4。加上 10 月 4 日为大型编码题补的两条，原题面下是 4，题面加不复核提示时是 8。补测 K=4 之前另写的读法得到的是保持 8，报告的建议照后一条写。",
          "- 表里每一批只列方案里写定的那一个主指标。",
          "- 多查 150/250、250/500 那一批：试跑 8 次以后两种提示的原话都没有改；“打开的网页数”的数法在正式跑之前改过（把脚本存盘的算进去）；读法在正式跑之前按试跑看到的行为调整过"
          "（每种提示都对默认的量和深度 2 的量两个参照报告比值），主要对比和校正的范围没有变。", "")
    words = [r["word"] for g in sc for r in g["rows"]]
    n_weak, n_same, n_open = words.count("校正后不显著"), words.count("没有差别"), words.count("没测出差别")
    assert n_sig + n_weak + n_same + n_open == n_all
    d.figure("scoreboard", f"{NEW}/primary-scorecard.png", f"事前写定的 {n_all} 个主要对比，每个方块是一个对比（各行里的顺序同{{tab:score}}）："
             f"显著 {n_sig} 个，校正后不显著 {n_weak} 个，没有差别 {n_same} 个，没测出差别 {n_open} 个。")
    d.tbl("score", "事前写定的主要对比和结果。得分和事实占比是差（办公报告题的事实占比是全清单，单位个百分点），时间和费用是倍数；方括号里是 95% 区间。", [
        ["实验", "对比", "配对数", "结果", "判断"]] + srows)
    mg = ex["merged"]
    fl_ = ex["facts_line"]
    xs = sorted(v["score"] for v in xm.values())
    assert ex["more200"]["contrast"]["hi"] < 0 and ex["more200"]["contrast"]["est"] < -5 and ex["dk"]["k1_none"]["lo"] < 0 < ex["dk"]["k1_none"]["est"] and ex["dk"]["k16_2min"]["lo"] < 0 < ex["dk"]["k16_2min"]["hi"]
    assert 230 <= dm["E-D0"]["search"] <= 300 and 64 <= dm["E-D0"]["right_pct"] <= 69 and 3 <= -dc["P150"]["right_pct"]["est"] <= 8 and 6 <= dm["E-D0"]["cost"] <= 8 and 17.8 < dm["E-D0"]["minutes"] < 18
    assert not (90 <= dpg["E-D0"]["urls"] <= 130) and not (90 <= dpg["E-D0"]["low"] <= 130) and not (120 <= dpg["N-D0"]["urls"] <= 180) and not (120 <= dpg["N-D0"]["low"] <= 180)
    assert abs(dc["P150"]["right_pct"]["lo"]) > 8 and dm["N-D0"]["search"] > dm["E-D0"]["search"] and 64 <= dm["E-D0"]["right_pct"] <= 71 and dm["N-D0"]["right_pct"] < 64 and -dc["P250"]["right_pct"]["est"] > 8
    assert dm["N-D0"]["search"] < 350 and dm["N-D0"]["right_pct"] < 65 and -hm["est"] > 4 and dm["N-D0"]["minutes"] < 30 and dm["N-D0"]["cost"] < 10 and 15 <= dh1["est"] <= 18
    assert ex["more200"]["n"] == 12 and -5.5 < ex["more200"]["diff"] < -4.5 and xs[0] > 99.8 and all(62 < v for v in mg["M2"]) and max(mg["M2"]) > 68 and all(72 < v < 82 for v in mg["M4"])
    assert all(v["lo"] <= 1 <= v["hi"] for q in ex["wait"].values() for v in q.values()) and 1.8 > ex["keep_depth"]["total_cost_peak"]["est"] > 1.6 and 2 < ex["keep_depth"]["right_pct"]["est"] < 6
    assert all(0.95 < v["answer_s"]["est"] < 1.3 and 0.95 < v["model_cost_peak"]["est"] < 1.2 for v in ex["xl_depth"].values())
    assert all(abs(kd["cmp"][q]["total"]["lo"]) < 5 and abs(kd["cmp"][q]["total"]["hi"]) < 5 for q in ("K1", "D2")) and all(fl_[q]["est"] < 7 for q in fl_)
    hc = ex["highk_cost"]
    assert hc["H1"]["lo"] < 1 < hc["H1"]["hi"] and 2 < hc["H2"]["est"] < 4 and abs(hc["H3"]["est"] - hc["H2"]["est"]) < 0.2 and all(verdict(v, 5, True) in ("没有差别", "没测出差别") for v in ex["highk_score"].values())
    okd = o["other_kids"]
    told_expect_row = None
    if TD:  # the predictions written into the plan on 2026-10-07T16:27Z against the batch, item by item
        within = lambda v, lo_, hi_: lo_ <= v <= hi_  # noqa: E731
        kids_ratio8 = tm["T-D1-K8"]["kids"] / tm["D1-K8"]["kids"]
        preds = [("K=2 被拒 1.2–2.0 次", within(tm["D1-K2"]["cap_rejects"], 1.2, 2.0)), ("K=2 开 2.4–2.9 个", within(tm["D1-K2"]["kids"], 2.4, 2.9)), ("K=2 费用 5.5–7 元", within(tm["D1-K2"]["cost"], 5.5, 7)),
                 ("默认开 3.3–3.8 个", within(tm["D1-K8"]["kids"], 3.3, 3.8)), ("默认没有被 K 拒绝", tm["D1-K8"]["cap_rejects"] == 0), ("默认费用 7.5–8.8 元", within(tm["D1-K8"]["cost"], 7.5, 8.8)),
                 ("告知的 K=2 被拒 0–0.4 次", within(tm["T-D1-K2"]["cap_rejects"], 0, 0.4)), ("告知的 K=2 开 2.2–3.2 个", within(tm["T-D1-K2"]["kids"], 2.2, 3.2)),
                 ("K=2 告知对不告知费用 0.9–1.15 倍", within(tc["P1"]["total_cost_peak"]["est"], 0.9, 1.15)), ("时间 0.95–1.15 倍", within(tc["P1"]["answer_s"]["est"], 0.95, 1.15)), ("63 条差在 ±4 以内", abs(tc["P1"]["right_legacy_pct"]["est"]) <= 4),
                 ("告知的 K=8 开 3.3–4.5 个", within(tm["T-D1-K8"]["kids"], 3.3, 4.5)), ("K=8 告知对不告知开的倍数 1.0–1.25", within(kids_ratio8, 1.0, 1.25)), ("费用 0.95–1.25 倍", within(tc["P2"]["total_cost_peak"]["est"], 0.95, 1.25)), ("63 条差在 ±4 以内", abs(tc["P2"]["right_legacy_pct"]["est"]) <= 4),
                 ("S2 全清单 −6 到 −1", within(tc["S2"]["right_pct"]["est"], -6, -1)), ("S2 63 条 −6 到 −1", within(tc["S2"]["right_legacy_pct"]["est"], -6, -1)), ("S1 质量差 −5 到 +1", within(tc["S1"]["right_legacy_pct"]["est"], -5, 1)), ("S1 费用 0.7–0.85 倍", within(tc["S1"]["total_cost_peak"]["est"], 0.7, 0.85))]
        miss = [p_ for p_, ok_ in preds if not ok_]
        told_expect_row = ["告知上限批", "K=2：每次运行被 K 拒绝 1.2–2.0 次，开 2.4–2.9 个 subagent，费用 5.5–7 元。默认：开 3.3–3.8 个，没有被 K 拒绝的调用，费用 7.5–8.8 元。告知的 K=2 对不告知：被拒 0–0.4 次，开 2.2–3.2 个，费用 0.9–1.15 倍，时间 0.95–1.15 倍，63 条的差在 ±4 以内。"
                           "告知的 K=8 对不告知：开 3.3–4.5 个（1.0–1.25 倍），费用 0.95–1.25 倍，质量差在 ±4 以内。S2 在 −6 到 −1；S1 质量差 −5 到 +1，费用 0.7–0.85 倍",
                           f"K=2：被拒 {rnd(tm['D1-K2']['cap_rejects'])} 次，开 {rnd(tm['D1-K2']['kids'])} 个，{rnd(tm['D1-K2']['cost'])} 元；默认：开 {rnd(tm['D1-K8']['kids'])} 个，被拒 {rnd(tm['D1-K8']['cap_rejects'])} 次，{rnd(tm['D1-K8']['cost'])} 元；"
                           f"告知的 K=2：被拒 {rnd(tm['T-D1-K2']['cap_rejects'])} 次，开 {rnd(tm['T-D1-K2']['kids'])} 个，对不告知费用 {x(tc['P1']['total_cost_peak'])}、时间 {x(tc['P1']['answer_s'])}、63 条 {sg(tc['P1']['right_legacy_pct']['est'])}；"
                           f"告知的 K=8：开 {rnd(tm['T-D1-K8']['kids'])} 个（{rnd(kids_ratio8, 2)} 倍），费用 {x(tc['P2']['total_cost_peak'])}，63 条 {sg(tc['P2']['right_legacy_pct']['est'])}；"
                           f"S2：全清单 {sg(tc['S2']['right_pct']['est'])}、63 条 {sg(tc['S2']['right_legacy_pct']['est'])}；S1：{sg(tc['S1']['right_legacy_pct']['est'])}，费用 {x(tc['S1']['total_cost_peak'])}",
                           f"{len(preds) - len(miss)}/{len(preds)} 项对上（预计按第三列的数拆成 {len(preds)} 项逐项比）" + ("" if not miss else "；没对上的：" + "、".join(miss))]
    d.tbl("expect", "写下过预计结果的批次：预计和实际。", [
        ["实验", "事前写下的预计", "实际", "对上了吗"],
        ["对照题批（16 步串行题）", "题面加并行提示对不开 subagent，得分差在 ±5 分以内或为负，费用和时间不低于不开", f"得分相同；模型费 {x(ch['cmp']['PC']['model_cost_peak'])}，时间 {x(ch['cmp']['PC']['seconds'])}", "对上"],
        ["限时 24 题批", "得分随 K 升高，限时 3 分钟时在 K=8 附近到顶，限时 2 分钟时 K=16 仍高于 K=8；K=1 接近或低于不开 subagent；深度 2 不高于深度 1",
         f"限时 3 分钟：K=1 对 K=8 {sg(g3['K1']['est'])} 分，K=16 对 K=8 {sg(g3['K16']['est'])} 分，深度 2 对深度 1 {sg(g3['FD']['est'])} 分，K=1 对不开 subagent {ci(ex['dk']['k1_none'])}；"
         f"限时 2 分钟：K=16 对 K=8 {ci(ex['dk']['k16_2min'])}", "大体对上；K=1 对不开 subagent 的方向和预计相反，区间含 0"],
        ["不限时 24 题批", "不开 subagent 约 6 分钟，题面加并行提示（K=8）约 2.5 分钟；时间随 K 缩短；费用基本不随 K 变；深度 2 不比深度 1 快",
         f"{f(fm_['D0']['answer'])} 和 {f(fm_['W-E-D1-K8']['answer'])} 分钟；K=1 对 K=8 的时间 {x(fk['K1']['answer_s'])}；模型费 K=16 是 K=1 的 {fm_['W-E-D1-K16']['cost'] / fm_['W-E-D1-K1']['cost']:.1f} 倍；深度 2 的时间 {x(fd_['answer_s'])}",
         "前三项没对上，深度那一项对上"],
        ["K=64 批（按评分表打总分）", "费用：K=64 约 ×1.0，深度 2、K=64 是 ×2–4，深度 3、K=64 更高；开的 subagent 分别是 3–4 个、8–20 个、更多；得分都没有差别",
         f"费用 {x(hc['H1'])}、{x(hc['H2'])}、{x(hc['H3'])}；开 {f(okd['k64'])}、{f(okd['d2k64'])}、{f(okd['d3k64'])} 个；评分表总分的区间都含 0", "基本对上（深度 3 的费用没有比深度 2 更高）"],
        ["大型编码题批", "各组得分都在 99.8 分以上", f"{xs[0]:.2f}–{xs[-1]:.2f} 分", "对上"],
        ["K=64 批和等 subagent 批，改按事实清单判分（预计写在重新判分之前）", "按搜索量直线推算，对同批默认：K=64 是 +1.0，深度 2、K=64 +10.5，深度 3、K=64 +11.4，深度 2 +5.8，深度 3 +6.9；估计回报会变平，K=64 的两组只多 4–7",
         f"{sg(fl_['k64']['est'])}、{sg(fl_['d2k64']['est'])}、{sg(fl_['d3k64']['est'])}、{sg(fl_['wd2']['est'])}、{sg(fl_['wd3']['est'])}", "五个都低于直线推算"],
        ["合并稿两批", "两份合并写对 62%–68%，比默认低 3–9 个百分点；四份合并 72%–80%",
         f"两份 {mg['M2'][0]:.1f}%、{mg['M2'][1]:.1f}%（两批），和默认没有差别；四份 {mg['M4'][0]:.1f}%、{mg['M4'][1]:.1f}%", "两份没对上；四份基本对上（一批略高于预计的上限）"],
        ["多查 100/100 那一批", "搜索请求到 200 个以上时，写对的和默认相差 ±5 个百分点以内；用时 25–40 分钟；上下文用到 50–80 万",
         f"{fmore['n']} 次里 {ex['more200']['n']} 次到了 200 个，这 {ex['more200']['n']} 次和默认相差 {ci(ex['more200']['contrast'])}；平均用时 {o['floor_means']['E-D0']['minutes']:.0f} 分钟；上下文中位 {fmore['ctx_median'] / 10000:.0f} 万", "三项都没对上"],
        ["大型编码题深度批", "深度 2 对深度 1，时间 ×1.0–1.3，费用 ×1.0–1.2",
         f"时间 {x(ex['xl_depth']['DE16']['answer_s'])}、{x(ex['xl_depth']['DE64']['answer_s'])}，模型费 {x(ex['xl_depth']['DE16']['model_cost_peak'])}、{x(ex['xl_depth']['DE64']['model_cost_peak'])}", "对上"],
        ["都写进去提示的深度批", "深度 2 对深度 1 是 +2 到 +6 个百分点，费用 ×1.8–2.2", f"{sg(ex['keep_depth']['right_pct']['est'])} 个百分点，费用 {x(ex['keep_depth']['total_cost_peak'])}", "质量对上，费用略低"],
        ["评测集报告题第二批", "K=1 和深度 2 对默认的差多半都落在 ±5 分以内", f"{ci(kd['cmp']['K1']['total'])}、{ci(kd['cmp']['D2']['total'])}", "对上"],
        ["多查 150/250、250/500 那一批", "多查 150/250：搜索请求 230–300 个，不同网页 90–130 个，写对 64%–69%、比默认低 3–8 个百分点、区间多半不能整个落在 ±8 以内，上下文峰值中位 35–50 万，用时 18–25 分钟，费用 6–8 元。"
         "多查 250/500：搜索请求 350–480 个，不同网页 120–180 个，写对 65%–70%、和多查 150/250 相差 ±4 以内，峰值 50–80 万且四分之一以上的运行发生裁剪，用时 30–45 分钟，费用 10–14 元。默认对不开 subagent 多 15–18。"
         "试跑以后、正式跑之前补了一条：两种提示写对的都在 64%–71%、比默认低 2–8 个百分点，搜得多的那种高 0–4 个",
         f"多查 150/250：{dm['E-D0']['search']:.0f} 个请求，写对 {rnd(dm['E-D0']['right_pct'])}%、比默认低 {rnd(-dc['P150']['right_pct']['est'])}，峰值中位 {rnd(dm['E-D0']['peak_median'] / 1e4)} 万，{rnd(dm['E-D0']['minutes'])} 分钟，{rnd(dm['E-D0']['cost'])} 元。"
         f"多查 250/500：{dm['N-D0']['search']:.0f} 个请求，写对 {rnd(dm['N-D0']['right_pct'])}%、比多查 150/250 低 {rnd(-hm['est'])}，峰值中位 {rnd(dm['N-D0']['peak_median'] / 1e4)} 万、没有裁剪，{rnd(dm['N-D0']['minutes'])} 分钟，{rnd(dm['N-D0']['cost'])} 元。"
         f"默认对不开 {sg(dh1['est'])}。网页数：按预计时的数法（不算脚本存盘的）是 {rnd(dpg['E-D0']['urls'], 0)} 和 {rnd(dpg['N-D0']['urls'], 0)} 个，算上存盘的是 {rnd(dpg['E-D0']['low'], 0)} 和 {rnd(dpg['N-D0']['low'], 0)} 个",
         "多查 150/250 的搜索量、写对的占比、区间和费用对上，网页数和上下文峰值没对上，用时差 0.1 分钟；多查 250/500 都没对上；补的那一条前者对上、后者没对上，搜得多的那种反而低；默认对不开对上"],
        ["等 subagent 批", "进程等 subagent 的组费用和时间更高", f"费用 {x(ex['wait']['S1']['total_cost_peak'])}、{x(ex['wait']['S2']['total_cost_peak'])}，时间 {x(ex['wait']['S1']['seconds'])}、{x(ex['wait']['S2']['seconds'])}，区间都含 1", "没测出"],
        ["两个公开评测集补测 K=4 的两批", "评测集填表题 K=4：逐项 F1 的差在 −3 到 +3 之间，费用 0.85–1.0 倍，时间 0.9–1.15 倍，24 次里 6–10 次有调用被 K 拒绝。K=1：逐项 F1 低 0–5 分，召回低 2–7 分，费用 0.45–0.65 倍，时间 0.9–1.3 倍。"
         "深度 2：逐项 F1 的差在 −3 到 +3 之间，费用 1.4–2.0 倍，时间 1.0–1.3 倍。评测集报告题 K=4：总分的差在 −3 到 +3 之间，费用 0.9–1.05 倍，30 次里至多 3 次有调用被 K 拒绝。两个主要对比都读成“没有差别”或“没测出”",
         f"评测集填表题 K=4：{sg(wk4['est'])} 分，费用 {x(kq('ws', 4, 'c'))}，时间 {x(kq('ws', 4, 't'))}，{wko['W-D1-K4']['cap_runs']} 次被拒绝。K=1：{sg(kq('ws', 1)['est'])} 分，召回 {sg(wsk_['cmp']['K1']['r_item']['est'])}，费用 {x(kq('ws', 1, 'c'))}，时间 {x(kq('ws', 1, 't'))}。"
         f"深度 2：{sg(dq('ws', 2)['est'])} 分，费用 {x(dq('ws', 2, 'c'))}，时间 {x(dq('ws', 2, 't'))}。评测集报告题 K=4：{sg(dk4_['est'])} 分，费用 {x(kq('drb2', 4, 'c'))}，{dko['W-D1-K4']['cap_runs']} 次被拒绝。主要对比一个没测出、一个没有差别",
         "多数对上；评测集填表题深度 2 的费用和评测集报告题 K=4 的费用没对上（一个比预计低，一个比预计高）"]] + ([told_expect_row] if TD else []))

    # ---- the readings of K and of depth, one row each: when written, what had been seen, what it says, what it gives
    assert rb["H2a"]["lo"] < -5 < rb["H2b"]["lo"] and rb["H2c"]["lo"] > -5 and all(kq("free", v_)["lo"] > -5 and kq("free", v_, "t")["lo"] < 1 for v_ in (1, 2, 4))
    assert all(fk[q_]["answer_s"]["lo"] < 1 < fk[q_]["answer_s"]["hi"] for q_ in ("K16", "K64")) and xk["NK16"]["answer_s"]["lo"] < 1 < xk["NK16"]["answer_s"]["hi"]
    assert kq("xl", 4, "t")["est"] <= 1.15 and kq("xl", 4)["lo"] > -1 and geo4 > 1.15 and min(geo, key=geo.get) == 8 and fk1["hi"] < 0 and fk2["hi"] < 0 and fk4["lo"] < 0 < fk4["hi"]
    xdr_ = cd.R("results/analysis-xl-depth/rows-all.csv")  # the depth batch of the large coding task: did a second-layer subagent write a deliverable file
    l2w = {g_: (sum(1 for r_ in xdr_ if r_["group"] == g_ and (cd.num(r_["score"]) or 0) >= 90 and (cd.num(r_["layer2_writers"]) or 0) > 0),
                sum(1 for r_ in xdr_ if r_["group"] == g_ and (cd.num(r_["score"]) or 0) >= 90)) for g_ in ("W-N-D2-K16", "W-N-D2-K64")}
    assert l2w == {"W-N-D2-K16": (0, 9), "W-N-D2-K64": (0, 10)}
    assert g3["K1"]["hi"] < 0 and g3["K1"]["holm"] < 0.05 and g3["K2"]["hi"] < 0 and g3["K2"]["holm"] > 0.05 and kq("wide", 4)["lo"] < 0 < kq("wide", 4)["hi"]
    assert abs(g3["K1"]["est"] - kq("wide", 1)["est"]) < 1e-9 and abs(g3["K2"]["est"] - kq("wide", 2)["est"]) < 1e-9
    assert cmp_["D1-K1"]["right_pct"]["hi"] < 0 and cmp_["D1-K1"]["right_pct"]["holm"] < 0.05 and leg["D1-K1"]["lo"] < 0 < leg["D1-K1"]["hi"] and cmp_["D1-K2"]["right_pct"]["lo"] < 0 < cmp_["D1-K2"]["right_pct"]["hi"]
    cik2 = f"{sg(g3['K2']['est'])} [{sg(g3['K2']['lo'])}, {sg(g3['K2']['hi'], 2)}]"  # the upper end is -0.05: one decimal would print it as -0.0
    g2c = gr["m2"]["cmp"]  # the same batch with the limit of two minutes
    assert all(g2c[q_]["lo"] < 0 < g2c[q_]["hi"] for q_ in ("K1", "K2", "K4", "K16", "FD")) and -5 < g3["K16"]["lo"] and g3["K16"]["hi"] < 5
    assert not (g2c["FD"]["lo"] > -5 and g2c["FD"]["hi"] < 5) and kq("free", 1)["hi"] < 0 and cmp_["D1-K4"]["right_pct"]["lo"] > -8 and cmp_["D1-K4"]["right_pct"]["hi"] < 8
    assert cmp_["D1-K2"]["right_pct"]["est"] > -5 and cmp_["D1-K4"]["right_pct"]["lo"] < 0 < cmp_["D1-K4"]["right_pct"]["hi"]
    d.tbl("k-readings", "和 K 的结论有关的六条读法，按写的先后排：什么时候写的、写的时候看过哪些结果、按它得到什么。第 2、3、4、6 行给出取值，第 1、5 行判断某个 K 有没有损失或好处。"
          "另有几处只判断某个 K 有没有差别的读法没有列；各批全部的主要对比和结果在{tab:score}。", [
        ["读法", "什么时候写的", "写的时候看过什么", "内容", "实际", "按它得到"],
        ["限时 24 题上小 K 有没有损失、调大有没有用", "10 月 3 日 16:30Z，限时 24 题批开跑之前", "这一批一次都没跑；以前各批的结果看过",
         "限时 3 分钟、2 分钟两版分别读。K=4、2、1 对 K=8 的得分差：区间整个小于 0，写“调小 K 有得分损失”，连同费用一起报告。K=16 对 K=8：区间整个大于 0，建议把 K 做成可以调大；区间在 ±5 分以内，8 和 16 没有实际差别；其余写测不出",
         f"限时 3 分钟：K=1 {ci(g3['K1'])}；K=2 {cik2}（和同批的对比一起校正以后不显著）；K=4 {ci(kq('wide', 4))}；K=16 {ci(g3['K16'])}。"
         f"限时 2 分钟：{ci(g2c['K1'])}、{ci(g2c['K2'])}、{ci(g2c['K4'])}、{ci(g2c['K16'])}，四个区间都含 0",
         "限时 3 分钟：K=1 有损失；K=2 按原文也算（原文只看区间），报告按校正后的判断写成不显著；K=4 的区间含 0；8 和 16 没有实际差别。限时 2 分钟：四个都测不出。"
         f"方案当天 17:20Z（这一批出统计之前）又写明带时限的两批只作参考，K 的作用以不限时 24 题批为准；那一批上 K=1 对 K=8 是 {ci(kq('free', 1))} 分"],
        ["K 对 K=64 的时间", "10 月 3 日 18:46Z，给不限时 24 题批加 K=64 的各组时", "这一批的前一半已经在跑，结果还没看过；K=64 的各组还没有跑",
         "K 对 K=64 的时间倍数，区间整个落在 0.9–1.1 以内算够用，取满足的最小的 K；都不满足就写“不设上限最快，报告整条曲线”",
         f"K=4、8、16 都不满足：{xci(v64[4])}、{xci(v64[8])}、{xci(v64[16])}（各 {v64[4]['n']} 对）",
         f"按原文该写“不设上限最快”。报告没有照写：不满足是因为区间宽，K=8、16 的估计值是 {rnd(v64[8]['est'], 2)}、{rnd(v64[16]['est'], 2)} 倍"],
        ["定 K 的规则（三条）", "10 月 3 日 20:46Z",
         "第一批（读代码题、办公报告题）、对照题批、等 subagent 批、限时 24 题批已经出了结果，不限时 24 题看过前一半；大型编码题、办公报告题主要的一批、K=64 批和以后各批还没有做。"
         "读代码题和办公报告题两条的结果写的时候已经在手（原文里就写着“已有结果”），所以不算事前写定",
         "取同时满足三条的最小的 K，小于 8 就建议改成它；费用不作门槛。读代码题：质量的区间不整个在 0 以下（原文没写用哪个对比，它写的“已有结果”对得上的是三个深度合起来的那一个；这个合并是事后做的）。"
         "不限时 24 题：时间的区间不整个在 1 以上，质量的区间下限高于 −5 分。办公报告题：质量的区间下限高于 −5 分（第一批的评分表总分）。K=16、64：时间的区间整个在 1 以下才算调大有好处",
         f"读代码题：K=1、2 不满足（{ci(fk1)}、{ci(fk2)}；后一个和同组的对比一起校正以后不显著，规则不做校正），K=4 满足（{ci(fk4)}）。"
         f"办公报告题：K=1 不满足（{ci(rb['H2a'])}），K=2、4 满足。不限时 24 题：K=1、2、4 都满足。K=16、64 的时间区间都含 1",
         "4"],
        ["大型编码题补的两条", "10 月 4 日 02:35Z", "大型编码题的正式运行一次都没有；同一道题试跑过两批（每组 2 次，有原题面的 K=4、8、16 和深度 2，加不复核提示的 K=1、8、16），结果看过；以前各批的结果看过",
         "按模型现在的行为（原题面）：上面三条都满足，并且这道题上 K 对 K=8 的时间倍数不超过 1.15（只看估计值）、质量的区间下限高于 −1 分的最小的 K。"
         "如果模型写完就收工（加不复核提示）：时间（组内几何平均）不超过最快一组 1.15 倍的最小的 K。K=16：时间的区间整个在 1 以下才写“放大到 16 有好处”",
         f"原题面 K=4：时间 {xci(kq('xl', 4, 't'))}，质量的区间下限 {sg(kq('xl', 4)['lo'], 2)} 分。加不复核提示：K=8 最快，K=4 是它的 {rnd(geo4, 2)} 倍。K=16 的时间区间含 1",
         "原题面 4；加不复核提示 8"],
        ["办公报告题上 K=1、2 少写对有没有得到确认", "10 月 4 日 11:53Z，办公报告题主要的一批开跑之前", "这一批一次都没跑；第一批按事实清单重新判分的结果看过（这一批是为确认它做的）",
         "K=1、K=2 对 K=8 写对的事实占比：区间整个在 0 以下，写“确认”；区间含 0 而且估计值高于 −5 个百分点，写“没有复现”。有一个得到确认，“K 不要低于 4”才算有事前写定的对比支持；两个都没有复现，就只剩读代码题一处依据。"
         "K=4：区间含 0 且整个在 ±8 个百分点以内，写“K=4 和 K=8 没有差别”",
         f"K=1 按全清单 {ci(cmp_['D1-K1']['right_pct'])}（校正后仍显著），按事先定下的 63 条 {ci(leg['D1-K1'])}；K=2 {ci(cmp_['D1-K2']['right_pct'])}，K=4 {ci(cmp_['D1-K4']['right_pct'])}（都是全清单）",
         "按全清单：K=1 得到确认，K=2 没有复现，K=4 和 K=8 没有差别。按 63 条，K=1 没有得到确认"],
        ["补测 K=4 的读法", "10 月 7 日 09:40Z", "补测一次都没跑；以前各批的结果都看过",
         "两个公开评测集上 K=4 对 K=8 的质量差都是“没有差别”（区间含 0 且整个在 ±5 分以内），才照上面的规则降到 4；有一个“没测出差别”或者显著变差，就保持 8",
         f"评测集报告题 {ci(dk4_)}，没有差别；评测集填表题 {ci(wk4)}，没测出差别（把不计分的运行也算上是 {ci(wk4all)}）",
         "保持 8"]])
    step1_ = [o["k64_d2"]["right_pct"], o["k64_d3"]["right_pct"], o["wait"]["WD2"]["right_pct"], o["wait"]["WD3"]["right_pct"]]
    kdp = ex["keep_depth"]["right_pct"]
    assert not (g3["FD"]["lo"] > -5 and g3["FD"]["hi"] < 5) and g3["FD"]["lo"] < -5 and g3["FD"]["hi"] > 0
    assert not (0.9 <= fd_["answer_s"]["lo"] and fd_["answer_s"]["hi"] <= 1.1) and fd_["answer_s"]["lo"] < 1 < fd_["answer_s"]["hi"]
    assert xk["DN"]["answer_s"]["hi"] > 1 and xk["DE"]["answer_s"]["hi"] > 1 and all(q_["lo"] < 0 < q_["hi"] for q_ in step1_) and cmp_["D2-K8"]["right_pct"]["lo"] < 0 < cmp_["D2-K8"]["right_pct"]["hi"]
    assert all(q_["answer_s"]["lo"] < 0.9 and q_["answer_s"]["hi"] > 1.1 for q_ in (xl["depth_hi"]["DE16"], xl["depth_hi"]["DE64"])) and kdp["lo"] < 0 < kdp["hi"] and kdp["hi"] > 8 and dq("ws", 2)["lo"] < 5
    d.tbl("d-readings", "各批事前写的、会影响深度放不放开的读法和结果，按写的先后排。读法都写在这一批的结果出来之前，特别的情况写在第一列的括号里。"
          "第一批和评测集报告题第二批没有专门为深度写读法，按通用的判断用词读；另有三处写到深度、但不涉及放不放开的读法没有列。", [
        ["批", "读法", "实际", "按读法"],
        ["限时 24 题批", "限时 3 分钟、2 分钟两版分别读。深度 2 对深度 1 的得分差（五个 K 合起来）：区间在 ±5 分以内或整个小于 0，写“深度 2 也没有好处”；整个大于 0，写“深度在这类任务上有用”，回头改结论的适用范围",
         f"限时 3 分钟 {ci(g3['FD'])}；限时 2 分钟 {ci(g2c['FD'])}", "两版都是两条都不符合（区间超出 ±5 分，又不整个在 0 的一边），读法没有预设这种情况的说法"],
        ["不限时 24 题批（读法写在前一半开跑以后，结果还没看过）", "深度 2 对深度 1 的时间倍数：区间整个在 0.9–1.1 以内或整个大于 1，写“深度 2 也不更快”", xci(fd_["answer_s"]), "两条都不符合，读法没有预设这种情况的说法"],
        ["大型编码题批（写之前看过同一道题的两批试跑，每组 2 次，有深度 2）", "深度 2 对深度 1 的时间倍数区间整个在 1 以下、并且费用倍数不超过 1.25，才建议放开深度；否则保持 1",
         f"原题面 {xci(xk['DN']['answer_s'])}，加不复核提示 {xci(xk['DE']['answer_s'])}", "保持 1"],
        ["办公报告题主要的一批", "深度 2 对深度 1 写对的事实占比：区间整个在 0 以上才写“深度 2 多查到事实”；否则写没测出", f"{ci(cmp_['D2-K8']['right_pct'])}（全清单）", "没测出"],
        ["K=64 批和等 subagent 批，改按事实清单判分（读法写在重新判分之前；这时运行已经做完，评分表的结果已经看过）",
         "四个对比（K=64 批里深度 2、3 加 K=64 对同批默认，等 subagent 批里深度 2、3 对同批默认）：每多写对一条事实的花费超过 1.2 元，或者区间含 0，建议仍是深度保持 1",
         "、".join(ci(q_) for q_ in step1_) + "，四个区间都含 0", "保持 1"],
        ["大型编码题深度批", "先看第 2 层用没用：K=16、64 两个深度 2 的组里，第 2 层 subagent 写过要交的文件的运行都不到 3/10，就写“这道题上量不到深度的作用”。"
         "时间：深度 2 对深度 1 的倍数，区间整个在 1 以下并且费用倍数不超过 1.25，写“名额够时深度 2 更快”；整个在 1 以上写更慢；整个在 0.9–1.1 之间写没有实际差别；其余写没测出",
         f"第 2 层写过文件的运行 {l2w['W-N-D2-K16'][0]}/{l2w['W-N-D2-K16'][1]}、{l2w['W-N-D2-K64'][0]}/{l2w['W-N-D2-K64'][1]}；时间 {xci(xl['depth_hi']['DE16']['answer_s'])}、{xci(xl['depth_hi']['DE64']['answer_s'])}",
         "量不到深度的作用；时间没测出"],
        ["都写进去提示的深度批（开跑 5 分钟、还没有结果时改过一次读法）", "深度 2 对深度 1 写对的事实占比：区间整个在 0 以上并且估计值不低于 8 个百分点，才把建议改成“配合这句要求可以考虑深度 2”；区间含 0、上限超过 +8，写没测出",
         ci(kdp), "没测出"],
        ["评测集填表题补测批", "深度 2 对深度 1 的逐项得分：区间整个在 +5 分以上，才写明并提出在这类题上复测", ci(dq("ws", 2)), "不提"]])

    assert ce.strong(dq("xln", 2, "t")) and 1.3 < dq("xln", 2, "t")["est"] < 1.4
    assert xl["all_pass_runs"]["W-D1-K4"] == 6 and xl["failed_max"]["W-D1-K4"] == 1 and xl["all_pass_runs"]["W-D1-K8"] == 10 and 0.1 < xk["NK4"]["score"]["p"] < 0.15
    d.add("### 方法补充", "")
    d.add("- **进程等不等 subagent。** 两种跑法见“运行环境和 subagent 的机制”，每一批是哪种见{tab:batches}。等的那种是给 DSH 命令行入口打的一个补丁：主 agent 一轮结束后，只要还有后台 subagent 没结束就不退出；"
          "subagent 结束时 DSH 自己会把结果送给主 agent、让它再跑一轮。主 agent 空闲而 subagent 还没结束的时间累计满 20 分钟就退出。补丁不给模型发任何消息。"
          f"{{fig:levels}} 只数每层开了几个，六种设置里两种跑法都有；每层开多少和跑法几乎无关（深度 2、K=8 按等 subagent 的跑法是 {f(o['levels_wait_d2'][0])} 和 {f(o['levels_wait_d2'][1])} 个）。",
          "- **事实清单怎么建的。** 两份清单共 195 条，每条都对照官方页面写明标准值和判定规则。63 条是看任何报告之前就定下的评分要点；其余 132 条是看到评分表总分测不出差别以后，"
          "参考每题 12 份样本报告补的，主要收 4 份以上样本写到、又有官方出处的事实。12 份样本里 2 份来自不开 subagent 的组，10 份来自开 subagent 的组。",
          f"- **为什么每个设置只对同批的默认比。** 同一个默认设置在不同的批里重复跑，均值会差几个百分点（细节{SEC['trust']}），所以每个设置都只和同一批里的默认组配对，不直接比各自的占比或得分。",
          "- **统计。** 区间是配对差的 t 区间（两道题的任务扣掉题目之间的差别），p 值用符号翻转的随机化检验。主要对比都在看到对应的判分结果之前写定；同一批里的几个主要对比一起做 Holm 校正；没交出完整报告的运行不进对比。公开评测集每题每组只跑 1 次，按题配对。"
          "几个 K 合起来的深度对比（限时 24 题、不限时 24 题），先在每次重复里把几个 K 的结果取平均（费用和时间是取对数以后再平均），再配对。"
          f"大型编码题原题面下 K=4 对 K=8 的得分：K=4 的 {xm['W-D1-K4']['n']} 次里有 {xm['W-D1-K4']['n'] - xl['all_pass_runs']['W-D1-K4']} 次各留下 {xl['failed_max']['W-D1-K4']} 个没过的测试，K=8 全过；"
          f"区间不含 0，按符号翻转的精确检验 p = {rnd(xk['NK4']['score']['p'], 2)}，t 区间不含 0 只靠这 4 次运行，按精确检验判成没测出差别。",
          f"- **事先没有写定的分析。** 深度 2 四批合起来算的数（{{fig:depth}}）、深度 3 两批合起来算的数、合并稿按档写对的条数、只看两道读代码题的结果、深度 2、3 配 K=64 的两组换对照的数、都写进去提示那一组 40 次全算的数、两批合并稿合起来算的数、"
          "不限时 24 题按有没有再派 subagent 分开的数、只算 63 条或只算后补条目的数、费用和 subagent 数的拟合、每条事实的价钱、K 够不够用的统计。",
          f"- **时间。** 时间都是到主 agent 给出最终回答为止，每次运行都从会话日志里读（最早的几批当时没有记这个时刻，10 月 8 日统一从日志重读；在那之前这几批用的是整个进程的时长，"
          f"进程等 subagent 的组会多算进退出前等待的时间）。深度 2、3 配 K=64 的两组各有 {od['stuck']['W-D2-K64']} 次、{od['stuck']['W-D3-K64']} 次，"
          "主 agent 回答以后还有 subagent 没结束，进程等到 20 分钟的上限才退出，这段不算在时间里。"
          f"不限时 24 题 K=64 的 {fm_['W-E-D1-K64']['n']} 次里有 {fm_['W-E-D1-K64']['n'] - fm_['W-E-D1-K64']['n_answer']} 次没有给出最终回答（其中 1 次进程被系统杀掉），时间按其余 {fm_['W-E-D1-K64']['n_answer']} 次算，得分按 {fm_['W-E-D1-K64']['n']} 次算。",
          f"- **深度 2 在几批里的对比。** 只改深度、K 保持 8 的有四批，每批的估计值在 {sg(min(r['est'] for r in d2k8))} 到 {sg(max(r['est'] for r in d2k8))} 之间；K=64 批里的深度 2、K=64 也算进去是 {ci(p2)}。深度 3 对深度 2，K=8 的两批合起来算是 {ci(p32k8)}，把 K=64 批也算进去是 {ci(p32)}。"
          f"办公报告题主要的一批里，深度 2 的时间是 {x(cmp_['D2-K8']['seconds'])}，四批合起来算是 {x(p2time)}。",
          f"- **都写进去提示的三种算法。** {wfl['runs'] // 4} 次里有 {wfl['early']} 次主 agent 没等 subagent 回来就结束：{wfl['early_incomplete']} 次没交出完整报告，{wfl['early'] - wfl['early_incomplete']} 次交的是半成品。"
          f"判分之前定了两种算法，结论不一样时以后一种为准：只去掉没交出完整报告的是 {ci(fl['KA']['right_pct'])}（{fl['KA']['right_pct']['n']} 对）；再去掉半成品是 {ci(kd_['right_pct'])}（{wfl['ka_pairs']} 对）。"
          f"事后加的第三种是 {kall['n']} 次全算、没交出报告的记 0 分：{ci(kall)}。",
          f"- **读代码题的两种算法。** 事先定的是读代码题和小编程题三道题一起算（{{tab:code3}}）；正文按任务类型分开，读代码题一行只看两道读代码题。两种算法下，开不开 subagent、换 K、换深度的得分差都不显著。"
          f"只看两道读代码题时 K=1 偏低；把三个深度合在一起看（事后合并）是 {ci(c['fact']['FK1']['score'])}。",
          f"- **合并稿。** 两批设计相同的合并稿合在一起算（事后合并）；分开看，两份合并是 {ci(mp2['batch']['a'])} 和 {ci(mp2['batch']['b'])}，四份合并是 {ci(mp4['batch']['a'])} 和 {ci(mp4['batch']['b'])}。"
          "第一批拿来合并的报告和对照的默认组是前一天跑的，第二批是同一批；方案里写的是两批不一致时以同批的为准。时间按几份同时写、写完再合并算。合并稿的搜索量倍数是两组均值之比（其余各行是每一对分别算再取几何平均）。"
          f"和加了都写进去提示、交出完整报告的默认比，两份合并是 {ci(m2n)}，四份合并是 {ci(o['m4_vs_keep'])}。",
          f"- **公开评测集。** 评测集填表题按评测集自己的规则逐格判；评测集报告题用评测集自己的判分提示词，判分模型换成了 Opus 5.5，所以分数只在各组之间比，不和论文里的数比。"
          f"费用倍数是每道题分别算再取几何平均；按两组的平均费用算，评测集填表题是 {wp['W-D1-K8']['cost'] / wp['D0']['cost']:.1f} 倍，评测集报告题是 {dp['W-D1-K8']['cost'] / dp['D0']['cost']:.1f} 倍，有几道题特别贵。"
          f"把不计分的运行也算进去，评测集填表题的召回是 {ci(p['with_flagged']['ws_recall'])}（校正后显著）。",
          f"- **费用。** 模型费按公开高峰价算（空闲时段是一半）；搜索费 = 搜索请求数 × {iss['search_price']:.4f} 元。办公报告题默认组在各批的均值是 {yuan(cst['default_batches'][0])}–{yuan(cst['default_batches'][-1])} 元。"
          f"“每多开一个 subagent 多花多少”是费用对开的 subagent 数做最小二乘的斜率：办公报告题用题面不加提示的 {fitc['n']} 次运行，费用 ≈ {rnd(fitc['intercept'])} + {yuan(fitc['per_subagent'])} × 数量"
          f"（R² {yuan(fitc['r2'])}；把是哪种设置也放进去，R² 只到 {yuan(fitc['r2_with_setting'])}；{fitc['groups']} 种开了 subagent 的设置里，平均费用和这条线相差最大的是 {pct(fitc['max_group_gap'])}，不开 subagent 的组比这条线低两成）；其它任务用该任务的全部运行。"
          f"同样这些运行里，搜索请求数能解释的费用差别更多（R² {yuan(fitc['r2_search'])}；只看模型费是 {yuan(fitc['r2_model_search'])}，对开的数量是 {yuan(fitc['r2_model_kids'])}）。"
          f"开的数量和搜索请求数一起变（相关系数 {yuan(fitc['corr_kids_search'])}），这些运行分不开“开了几个”和“查了多少”各占多少；多查 150/250、250/500 那一批没有进这个拟合，它里面不开 subagent、搜索请求到了默认水平的两组，模型费不到默认的一半。"
          f"不限时 24 题和大型编码题按用途分成两个数量一起拟合（大型编码题 R² {yuan(cf2['xl']['r2'])}，不限时 24 题 R² {yuan(cf2['free']['r2'])}）。",
          f"- **用户日志的费用。** 三份日志整场的 token（主 agent 和全部 subagent）按同样的单价算，A、B、C 分别是 {rnd(logs['A']['model'])}、{rnd(logs['B']['model'])}、{rnd(logs['C']['model'])} 元；"
          f"A、C 有 {logs['A']['search_requests']:,}、{logs['C']['search_requests']:,} 个搜索请求，按同样的单价估 {rnd(logs['A']['search_fee'])}、{rnd(logs['C']['search_fee'])} 元；B 没有联网。"
          f"A、C 是 {logs['A']['human_messages']} 轮和 {logs['C']['human_messages']} 轮的多轮对话，和实验里的单任务运行不是同一个单位。",
          f"- **每条事实的价钱。** 多花的钱和多写对的条数都是同一批里配对的差（每份报告的清单平均 {cd.SLOTS:g} 条）；合并稿在这张表里对的是拿来合并的那几份不开 subagent 的报告：多写对的条数是合并稿减去这几份的平均，多花的钱是合并的全部费用（几份报告加合并那一步）减去一份报告的费用。"
          f"深度 2 用的是办公报告题主要的一批；按四批合起来算的 {sg(d2_gain)} 条算，约 {pf['default_d2_at_pooled']:.1f} 元一条。",
          f"- **多写对的是哪些事实（{{tab:strata}} 怎么算的）。** 先给每条事实定一个难度：它在不开 subagent 的运行里被写对的比例，用第一批和多查 100/100 那一批里不开 subagent 的运行来算（每题 {sa['total']['strata_runs']['o1-singapore-trip']} 份）。"
          "按这个比例分成四档，再到办公报告题主要的一批里（每题每组 20 份）数各档默认比不开多写对多少。定难度和数多写对的不用同一批，是因为同一批里碰巧没写到的条目会平白显出涨幅。"
          f"换一种分法复核（用主要的一批和第一批定难度，在多查 100/100 那一批里数），四档占多写对的 {pct(sb_['rows'][0]['share'])}、{pct(sb_['rows'][1]['share'])}、{pct(sb_['rows'][2]['share'])}、{pct(sb_['rows'][3]['share'])}。",
          f"- **两套条目为什么差一截（细节{SEC['trust']}那一格怎么算的）。** 问题是：后补的 132 条上开 subagent 的效果比事先定下的 63 条大一倍，有多少只是因为后补的条目更难？"
          "把条目按难度并成三档（不开 subagent 时写对的比例不到一半、一半到九成、九成以上；每档里两套条目都不少于 10 条），在两批里各量一次（主要的一批、多查 100/100 那一批）。"
          f"先看同一档里两套条目各涨多少：两批、三档共六个比较，有五个相差不到 4 个百分点，另一个是 {sg(og['confirm']['groups'][1]['fixed_gain'])} 对 {sg(og['confirm']['groups'][1]['added_gain'])}。"
          f"再算难度能解释两套条目涨幅之差的多少：假设后补的条目在每一档都只涨 63 条在这一档的涨幅，按后补条目在各档的条数加权算出一个涨幅，看它把两套条目的差距补上了多少，两批是 {pct(og['confirm']['explained'])} 和 {pct(og['floor']['explained'])}；"
          f"反过来用后补条目各档的涨幅配 63 条在各档的条数，是 {pct(og['confirm']['explained_rev'])} 和 {pct(og['floor']['explained_rev'])}。"
          f"上面是两道题的条目放在一起算的。分题算（前一种算法）：旅行攻略题是 {pct(og['confirm']['by_task'][TRIP]['explained'])}，另一批里两套条目涨得几乎一样多"
          f"（{sg(og['floor']['by_task'][TRIP]['fixed_gain'])} 对 {sg(og['floor']['by_task'][TRIP]['added_gain'])}）；"
          f"CPU 选型题是 {pct(og['confirm']['by_task'][CPU]['explained'])} 和 {pct(og['floor']['by_task'][CPU]['explained'])}。",
          f"- **多查 150/250 和多查 250/500。** 不开 subagent 的两组各在题面末尾加一句：“写报告之前，请至少做 150 次网页搜索，并打开至少 250 个网页核对内容。”和数字换成 250、500 的同一句；和同批的不开 subagent、默认各 {dm['D0']['runs']} 次一起跑。"
          f"事前写定：搜索请求数在默认的 0.7–1.4 倍、打开的网页数不低于默认的 0.6 倍，算查到了默认的量。两种的搜索请求是默认的 {rnd(vol['E-D0'], 2)} 和 {rnd(vol['N-D0'], 2)} 倍（组均值之比），网页数是 {rnd(dpg['E-D0']['low'] / dpg['D1-K8']['low'])} 和 {rnd(dpg['N-D0']['low'] / dpg['D1-K8']['low'])} 倍，都算查到了；"
          f"网页数这一条靠的是把脚本存盘的网页算进去（数法在试跑以后、正式跑之前改的），按改之前的数法只有默认的 {rnd(dpg['E-D0']['urls'] / dpg['D1-K8']['urls'], 2)} 和 {rnd(dpg['N-D0']['urls'] / dpg['D1-K8']['urls'], 2)} 倍。"
          f"离深度 2 的搜索量（455 个请求）还差四成左右。有 1 次运行没交出完整报告，不进对比；把它也算进去（记 0 分），多查 150/250 对默认是 {ci(ds['extra']['every_run']['E-D0_vs_default'])}，对同批不开 subagent 的组是 {ci(ds['every']['Z150'])}。"
          f"多查 250/500 有 {dpg['N-D0']['no_search']} 次运行一次搜索工具都没用，全靠脚本下载。"
          f"按不开 subagent 的三组拟合，搜索请求数每翻一倍多写对 {rnd(ds['extra']['curve']['search']['per_doubling'])} 个百分点；按这条线推到默认的搜索量，比默认低 {rnd(-ds['extra']['curve']['search']['diff'])} 个百分点"
          f"（区间 {rnd(-ds['extra']['curve']['search']['hi'])}–{rnd(-ds['extra']['curve']['search']['lo'])}）；换成按打开的网页数拟合，是每翻一倍 {rnd(ds['extra']['curve']['pages']['per_doubling'])} 个百分点、推到默认的网页数低 {rnd(-ds['extra']['curve']['pages']['diff'])} 个"
          f"（两个量的对数相关 {rnd(ds['extra']['curve']['corr_log_search_log_pages'], 2)}，分不开）。费用的拟合和默认组各批的合计（细节{SEC['cost']}）没有把这一批算进去。",
          "- **打开的网页数。** 模型打开网页有三种办法：用 web_fetch 工具一个一个打开；在 shell 命令里直接抓（命令里写出了网址）；写脚本成批下载、存在工作目录里（按留下的文件数，同名不同后缀的算一个）。"
          "后两种会重叠（脚本要下载的网址有的也写在命令里），所以总数给下限：“web_fetch 和命令里出现过的不同网址数”与“web_fetch 打开的加存盘的”，取大的那个。{tab:dose} 里前两行“其中”是存盘的和 web_fetch 打开的，第三行是下限里剩下的部分，三行相加就是下限。"
          f"按上限（“web_fetch 和命令里出现过的不同网址数”和存盘的直接相加）算，多查 100/100 的那一组是默认的 {pct(pg['more_over_default']['high'])}。"
          "存到磁盘的网页只有被检索到的片段进了模型的上下文。",
          "- **汇总时丢了多少。** 从主 agent 的会话日志里取出 subagent 交回的全部消息，用同一份事实清单、同一个判分模型判一遍，再和最终报告的判分逐条对：消息里写对、最终报告里没写对的算“没进最终报告”。交回的文字不到 1,000 字符的运行不判。",
          "- **K 够不够用。** 一次运行里同时活着的 subagent 最多到过几个、有没有调用被 K 拒绝，都从会话日志里数。按题的相关系数的区间用 Fisher 变换算。K 放到 64 时的两个数，来自大型编码题题面加不复核提示的组和不限时 24 题题面加并行提示的组。",
          *([told_method] if TD else []),
          "- **留下来可以再用的材料。** 两份事实清单（195 条，带出处和判定规则）和判分提示词；大型编码题（规格和 3,737 个隐藏测试）；24 道小题和隐藏测试；16 步串行题；"
          "加在题面末尾的四种提示；跑批、判分和统计的脚本。题面、清单和评分标准的原文在本页后面。", "")
    d.sec("old:names")
    d.p("本页最后三节（打分机制、题目、评分标准）是早先写的，没有随这一版改名，对照如下：办公题 = 办公报告题（o1 是旅行攻略题，o2 是 CPU 选型题）；表格收集题 = 评测集填表题；调研报告题 = 评测集报告题；"
        "c1、w1 = 读代码题的问答题和写方案题；p4、写代码小题 = 小编程题；24 道限时练习 = 限时 24 题；16 步依赖题 = 16 步串行题；24 道练习不限时 = 不限时 24 题；48 模块的包 = 大型编码题；"
        "两道对照题 = 限时 24 题和 16 步串行题；代码构建题 = 不限时 24 题和大型编码题；鼓励版 = 加并行提示；不复核组 = 加不复核提示；确认实验 = 办公报告题主要的一批；“子代理”就是 subagent。")
    d.sec("old:pointer")
    d.add(POINTER, "")
    # ================================================================================================================
    # The main text (second pass of 2026-10-08, after a cold read, the eighteenth round of the independent check and the
    # owner's request to keep costs, spawning behaviour, the full comparison tables and the scatter plots in the body):
    # abstract; conclusions with evidence grades; the four claims; the method with one decision frame; the results as
    # units of one figure or table with at most three sentences; one discussion. What stood before becomes the appendix
    # (sections put together at the end of this function). Everything here words numbers computed and guarded above.
    d.auto = False

    def cstate(cl_: dict):
        c_ = cl_["c"]
        return "cheaper" if c_["hi"] < 1 else "dearer" if c_["lo"] > 1 else "same"

    def states(part_: str, v_) -> dict:
        """State of every task for one value of a limit; the timed task is for reference only and is left out."""
        out_ = {"q": {}, "t": {}, "c": {}}
        for r_ in L[part_]:
            cells_ = ce.rule_cells(r_) if part_ == "k" else r_["cells"]  # K: the uniform rule (two office batches together, three code tasks together)
            if r_["key"] == "wide" or v_ not in cells_:
                continue
            cl_ = cells_[v_]
            for m_, s_ in (("q", qstate(cl_, r_["key"])), ("t", tstate(cl_)), ("c", cstate(cl_))):
                if s_ is not None:
                    out_[m_][r_["key"]] = s_
        return out_
    worst = lambda dct_: "worse" if "worse" in dct_.values() else "open" if "open" in dct_.values() else "ok"  # noqa: E731
    which = lambda dct_, s_: sorted(k_ for k_, v_ in dct_.items() if v_ == s_)  # noqa: E731
    SK = {v_: states("k", v_) for v_ in (1, 2, 4, 16, 64)}
    SDP = {v_: states("depth", v_) for v_ in (0, 2, 3)}
    # the sentences under the two overview tables are written for exactly these outcomes
    assert which(SK[1]["q"], "worse") == ["office"] and which(SK[1]["q"], "open") == [] and which(SK[1]["t"], "worse") == ["code", "xln"] and set(SK[1]["c"].values()) == {"cheaper"}
    assert which(SK[2]["q"], "open") == ["code"] and which(SK[2]["q"], "worse") == [] and which(SK[2]["t"], "worse") == ["xln"] and set(SK[2]["c"].values()) == {"cheaper"}
    assert worst(SK[4]["q"]) == "ok" and which(SK[4]["t"], "worse") == ["xln"] and which(SK[4]["c"], "cheaper") == ["free", "xl", "xln"] and "dearer" not in SK[4]["c"].values()
    rk = lambda key_, v_, m_="q": ce.rule_cells(LK[key_])[v_][m_]  # noqa: E731  (a K contrast as the main text reads it)
    kc_rule = {v_: sorted(ce.rule_cells(r_)[v_]["c"]["est"] for r_ in L["k"] if r_["key"] != "wide" and v_ in ce.rule_cells(r_)) for v_ in (1, 2)}
    NAME_ = {"office": "办公报告题", "ws": "评测集填表题", "drb2": "评测集报告题", "code": "读代码题", "p4": "小编程题", "chain": "16 步串行题", "free": "不限时 24 题",
             "xl": "大型编码题（原题面）", "xln": "大型编码题（不复核题面）"}

    def found(part_: str, v_) -> dict:
        """What one value of a limit changes against the default, task by task: the contrasts the report counts as
        detected (ce.strong: the interval leaves out 0, or 1 for a ratio, and survives the correction where one
        applies; the bold cells of the full tables). The timed task is for reference only and is left out."""
        out_ = {"better": [], "worse": [], "cheaper": [], "dearer": [], "keys": {"better": [], "worse": [], "cheaper": [], "dearer": []}}
        for r_ in L[part_]:
            cells_ = ce.rule_cells(r_) if part_ == "k" else r_["cells"]
            if r_["key"] == "wide" or v_ not in cells_:
                continue
            cl_ = cells_[v_]
            nm_ = r_["rule_name"] if part_ == "k" and "rule_name" in r_ and v_ in r_["rule"] else NAME_[r_["key"]]
            q_ = cl_["legacy"] if r_["key"] == "office" else cl_["q"]
            exact_no_ = bool(r_.get("tests")) and q_.get("p") is not None and q_["p"] >= 0.05
            flat_ = q_["est"] == q_["lo"] == q_["hi"] == 0
            if not exact_no_ and not flat_ and ce.strong(q_, cl_["corr"][0] and r_["key"] != "office"):
                side_ = "better" if q_["est"] > 0 else "worse"
                out_[side_].append(f"{nm_}质量 {sg(q_['est'], cl_['nd'])}")
                out_["keys"][side_].append(("q", r_["key"]))
            if cl_["t"] is not None and ce.strong(cl_["t"], cl_["corr"][2]):
                side_ = "better" if cl_["t"]["est"] < 1 else "worse"
                out_[side_].append(f"{nm_}用时 {x(cl_['t'])}")
                out_["keys"][side_].append(("t", r_["key"]))
            if cl_["c"] is not None and ce.strong(cl_["c"], cl_["corr"][1]):
                side_ = "cheaper" if cl_["c"]["est"] < 1 else "dearer"
                out_[side_].append((nm_, cl_["c"]["est"]))
                out_["keys"][side_].append(("c", r_["key"]))
        return out_

    def cost_txt(items_: list, word_: str) -> list:
        if len(items_) >= 4:
            es_ = sorted(e_ for _, e_ in items_)
            return [f"费用：{len(items_)} 个对比都{word_}（{rnd(es_[0], 2)}–{rnd(es_[-1], 2)} 倍）"]
        return [f"{n_}费用 ×{rnd(e_, 2)}" for n_, e_ in items_]
    frow = lambda label_, f_, crash_: [label_, crash_, "；".join(f_["better"] + cost_txt(f_["cheaper"], "更省")) or "没有", "；".join(f_["worse"] + cost_txt(f_["dearer"], "更贵")) or "没有"]  # noqa: E731
    FK = {v_: found("k", v_) for v_ in (1, 2, 4, 16, 64)}
    FD = {v_: found("depth", v_) for v_ in (0, 2, 3)}
    # the sentences under the two tables are written for exactly these findings
    assert ("q", "office") in FK[1]["keys"]["worse"] and ("t", "xln") in FK[1]["keys"]["worse"] and len(FK[1]["cheaper"]) >= 5 and not FK[1]["dearer"]
    assert FK[2]["keys"]["worse"] == [("t", "xln")] and len(FK[2]["cheaper"]) >= 4 and not FK[2]["better"]
    assert FK[4]["keys"]["worse"] == [("t", "xln")] and sorted(FK[4]["keys"]["cheaper"]) == [("c", "xl"), ("c", "xln")] and not FK[4]["better"] and not FK[4]["dearer"]
    assert all(not FK[v_][k_] for v_ in (16, 64) for k_ in ("better", "worse", "cheaper", "dearer"))
    assert {("q", "office"), ("q", "drb2"), ("t", "xln")} <= set(FD[0]["keys"]["worse"]) and ("t", "office") in FD[0]["keys"]["better"] and len(FD[0]["cheaper"]) >= 6
    assert sorted(FD[2]["keys"]["dearer"]) == [("c", "code"), ("c", "drb2"), ("c", "office")] and sorted(FD[2]["keys"]["worse"]) == [("t", "code"), ("t", "xln")]
    assert FD[2]["keys"]["better"] == [("q", "free")] and FD[2]["keys"]["cheaper"] == [("c", "free")]
    # K = 4: runs in which a delegation call was rejected by K (the limit was reached)
    capped4 = {b_: (sum(1 for r_ in msel(batch=b_, D=1, K=4, hint="none") if mnum(r_, "rejected_cap") > 0), len(msel(batch=b_, D=1, K=4, hint="none"))) for b_ in ("office-confirm", "drb2-k4", "ws-k4")}
    assert capped4 == {"office-confirm": (2, 40), "drb2-k4": (3, 30), "ws-k4": (9, 24)}
    # the large coding task: runs in which every hidden test passes (the grader's own counts)
    xpass = {g_: (sum(1 for r_ in msel(batch="xl-main", group=g_) if mnum(r_, "tests_failed") == 0), len(msel(batch="xl-main", group=g_))) for g_ in ("D0", "W-D1-K8", "W-D1-K4", "W-N-D1-K8")}
    assert xpass == {"D0": (1, 10), "W-D1-K8": (10, 10), "W-D1-K4": (6, 10), "W-N-D1-K8": (1, 10)} and all(xl["all_pass_runs"][g_] == v_[0] for g_, v_ in xpass.items())
    # how every run ended, one rule for all batches (scripts/master_table.py)
    ends = {k_: sum(1 for r_ in MT if r_["status"] == k_) for k_ in ("ok", "timeout", "crash_at_exit", "no_answer", "nonzero_exit")}
    na_scored = sum(1 for r_ in MT if r_["status"] == "no_answer" and r_["q"] != "")
    assert sum(ends.values()) == len(MT) and ends["no_answer"] == 15 and na_scored == 12 and ends["nonzero_exit"] == 1 and ends["crash_at_exit"] == iss["all_crashes"]
    assert all(r_["family"].startswith("timed24") or r_["family"] == "ws" for r_ in MT if r_["status"] == "timeout") and sum(1 for r_ in MT if r_["status"] == "timeout" and r_["family"] == "ws") == 3
    # delegation with one subagent at a time (K = 1) between no subagents and the default, the main office batch
    oc_ = msel(batch="office-confirm")
    done_ = lambda r_: r_["complete"] != "0"  # noqa: E731
    step_ = lambda a_, b_, c_, kind_="diff": cd.contrast(oc_, a_, b_, lambda r_: mnum(r_, c_), kind_, ok=done_)  # noqa: E731
    k1s = {c_: (step_("D1-K1", "D0", c_, k_), step_("D1-K8", "D1-K1", c_, k_)) for c_, k_ in (("facts63", "diff"), ("facts_all", "diff"), ("total_yuan", "ratio"), ("t_answer_s", "ratio"))}
    assert abs(step_("D1-K8", "D0", "facts63")["est"] - h1leg["est"]) < 0.01 and all(q_["lo"] < 0 < q_["hi"] and 3.5 < q_["est"] < 5.5 for q_ in k1s["facts63"]) and all(q_["lo"] > 0 for q_ in k1s["facts_all"])
    assert k1s["t_answer_s"][0]["lo"] > 1 and k1s["t_answer_s"][1]["lo"] < 1 < k1s["t_answer_s"][1]["hi"] and 2.1 < k1s["total_yuan"][0]["est"] < 2.4 and 1.6 < k1s["total_yuan"][1]["est"] < 1.9
    k1kids = mmean([r_ for r_ in oc_ if r_["group"] == "D1-K1" and done_(r_)], "kids_d1")
    assert 1.7 < k1kids < 2.1
    # the single agent told to search more: what it spent on the model against the default of its batch
    od_ = msel(batch="office-dose")
    dose_model = [cd.contrast(od_, g_, "D1-K8", lambda r_: mnum(r_, "model_yuan"), "ratio", ok=done_) for g_ in ("E-D0", "N-D0")]
    assert all(0.40 < q_["est"] < 0.48 and q_["hi"] < 0.55 for q_ in dose_model)
    tok_none = tok([r_ for r_ in oc_ if r_["group"] == "D0"])
    tok_def = tok(tok_of["办公报告题"])
    assert 3.5 < tok_def[2] / tok_none[2] < 4.6 and 3.5 < (tok_def[0] + tok_def[1]) / (tok_none[0] + tok_none[1]) < 4.2
    # the judge's effort level, checked on the old rubric (results/validate-effort): high against max on the same 40 reports
    ve = cd.J("results/validate-effort/compare-max-high.json")["tasks"]["all"]
    ve_share = lambda k_: sum(v_["same"] for c_, v_ in ve["items"][k_].items() if c_ in "ABCD") / sum(v_["items"] for c_, v_ in ve["items"][k_].items() if c_ in "ABCD")  # noqa: E731
    assert ve["between"]["n"] == 40 and -1 < ve["between"]["mean_diff"] < 0 and 0.935 < ve_share("between") < 0.945 and abs(ve_share("between") - ve_share("within_a")) < 0.005
    # the two passes of the fact judge, item by item (scripts/facts_kappa.py on the dev box): Cohen's kappa
    kap_t = collections.Counter()
    for d_, v_ in cd.J("results/master/facts-kappa.json").items():
        if "merge" not in d_:
            kap_t.update(v_["table"])

    def kappa_(t_: dict) -> tuple:
        n_ = sum(t_.values())
        cats_ = sorted({k_.split("|")[0] for k_ in t_} | {k_.split("|")[1] for k_ in t_})
        po_ = sum(v_ for k_, v_ in t_.items() if k_.split("|")[0] == k_.split("|")[1]) / n_
        pe_ = sum((sum(v_ for k_, v_ in t_.items() if k_.split("|")[0] == c_) / n_) * (sum(v_ for k_, v_ in t_.items() if k_.split("|")[1] == c_) / n_) for c_ in cats_)
        return n_, po_, (po_ - pe_) / (1 - pe_)
    kap_all = kappa_(kap_t)
    kap_two = collections.Counter()
    for k_, v_ in kap_t.items():
        a_, b_ = k_.split("|")
        kap_two[("对" if a_ == "对" else "其余") + "|" + ("对" if b_ == "对" else "其余")] += v_
    kap_right = kappa_(kap_two)
    assert kap_all[0] == 15015 and 0.96 < kap_all[2] < 0.985 and 0.98 < kap_right[2] < 0.995  # the eight batches with a second pass (the two merged-report batches left out)
    assert sorted(FD[3]["keys"]["dearer"]) == [("c", "code"), ("c", "office"), ("c", "p4")] and sorted(FD[3]["keys"]["worse"]) == [("t", "office"), ("t", "p4")] and not FD[3]["better"] and not FD[3]["cheaper"]
    assert all(worst(SK[v_]["q"]) == "ok" and worst(SK[v_]["t"]) == "open" and "cheaper" not in SK[v_]["c"].values() for v_ in (16, 64))
    assert which(SK[16]["t"], "open") == ["free", "xl"] and which(SK[64]["t"], "open") == ["free"] and set(SK[16]["q"]) == {"free", "xl", "xln"} and set(SK[64]["q"]) == {"free", "office"}
    assert which(SDP[0]["q"], "worse") == ["drb2", "office"] and which(SDP[0]["t"], "worse") == ["xln"] and all(SDP[0]["c"][k_] == "cheaper" for k_ in ("office", "ws", "drb2", "code", "free", "xl", "xln"))
    assert SDP[0]["c"]["p4"] == "dearer" and SDP[0]["c"]["chain"] == "same" and SDP[0]["t"]["office"] == "ok" and dq("office", 0, "t")["hi"] < 1
    assert worst(SDP[2]["q"]) == "ok" and which(SDP[2]["t"], "worse") == ["code", "xln"] and which(SDP[2]["c"], "dearer") == ["code", "drb2", "office"] and which(SDP[2]["c"], "cheaper") == ["free"]
    assert worst(SDP[3]["q"]) == "ok" and which(SDP[3]["t"], "worse") == ["office", "p4"] and which(SDP[3]["c"], "dearer") == ["code", "office", "p4"]
    crash23 = rel_d2["crash"] + rel_d3["crash"]
    runs23 = rel_d2["runs"] + rel_d3["runs"]
    assert crash23 == 41 and runs23 == 120 and all(rel_k[v_]["crash"] == 0 for v_ in rel_k) and rel_none["crash"] == 0
    deep_nowait = [q_ for q_ in RL if q_["col"][:2] in ("2-", "3-") and not q_["waits"]]  # every run at depth 2 or 3 whose process did not wait
    deep_by = {t_: (sum(q_["crash"] for q_ in deep_nowait if q_["task"] == t_), sum(q_["runs"] for q_ in deep_nowait if q_["task"] == t_)) for t_ in ("office", "code", "p4")}
    assert deep_by == {"office": (45, 240), "code": (5, 260), "p4": (0, 100)} and sum(q_["runs"] for q_ in deep_nowait) == 600
    # what a batch on its own says, for the table of repeated results (the grades of the conclusions rest on it)
    floor_leg = cd.flip(o["floor_none"]["legacy"])
    h1l4 = [next(r_ for r_ in o["h1_legacy"] if r_["name"] == "formal"), next(r_ for r_ in o["h1_legacy"] if r_["name"] == "confirm"), floor_leg, next(r_ for r_ in o["h1_legacy"] if r_["name"] == "dose")]
    assert all(r_["lo"] > 0 for r_ in h1l4) and abs(h1l4[1]["est"] - h1leg["est"]) < 1e-9 and abs(floor_leg["est"] + o["floor_none"]["legacy"]["est"]) < 1e-9
    frows_ = cd.R("results/analysis-facts/fact-rows.csv")  # the first batch judged against the fact lists
    fx63 = cd.R("results/analysis-facts-confirm/fact-rows.csv")  # the main office batch
    kfirst = {v_: cd.contrast(frows_, f"D1-K{v_}", "D1-K8", lambda r_: cd.num(r_["right_legacy_pct"])) for v_ in (1, 2, 4)}
    k4first, k1first = kfirst[4], kfirst[1]
    assert qstate({"legacy": k4first}, "office") == "ok" and all(q_["lo"] < 0 < q_["hi"] and q_["n"] == 20 for q_ in kfirst.values())

    def pair_diffs(rows_: list, a_: str, b_: str, get_) -> dict:
        """Pair differences a - b by task (pairs are (task, repeat)), the way paired_stats.py pairs them."""
        conv_ = [{"task": r_["task"], "group": r_["group"], "rep": r_["rep"], "m": get_(r_)} for r_ in rows_ if r_["group"] in (a_, b_)]
        dbt_, _, _ = cd.ps.paired(cd.ps.index_rows([q_ for q_ in conv_ if q_["m"] is not None]), a_, b_, "m", "diff")
        return {t_: (list(v_.values()) if isinstance(v_, dict) else list(v_)) for t_, v_ in dbt_.items()}
    kpool = {}  # K against 8 on the office task, the first batch and the main batch together (the plan of 2026-10-04 11:53Z asks for this estimate)
    for v_ in (1, 2, 4):
        for col_ in ("right_legacy_pct", "right_pct"):
            strata_ = {}
            for name_, rows_ in (("first", frows_), ("main", fx63)):
                for t_, dv_ in pair_diffs(rows_, f"D1-K{v_}", "D1-K8", lambda r_, col_=col_: cd.num(r_[col_])).items():
                    strata_[(name_, t_)] = dv_
            kpool[(v_, col_)] = cd.pooled(strata_)
    k1p, k2p, k4p = (LK["office"]["rule"][v_]["legacy"] for v_ in (1, 2, 4))
    k1pf, k4pf = LK["office"]["rule"][1]["q"], LK["office"]["rule"][4]["q"]
    assert all(abs(LK["office"]["rule"][v_]["legacy"][e_] - kpool[(v_, "right_legacy_pct")][e_]) < 1e-9 and abs(LK["office"]["rule"][v_]["q"][e_] - kpool[(v_, "right_pct")][e_]) < 1e-9
               for v_ in (1, 2, 4) for e_ in ("est", "lo", "hi"))
    assert k1p["hi"] < 0 and k1p["lo"] < -QM("office") and k1p["n"] == 59 and kpool[(1, "right_pct")]["hi"] < 0 and k2p["lo"] > -QM("office") and k2p["lo"] < 0 < k2p["hi"] and k4p["lo"] > -QM("office") and k4p["lo"] < 0 < k4p["hi"]
    strata_ = {}  # the default against no subagents on the 63 items, the four batches together
    for name_, rp_, fp_ in (("formal", "results/analysis-v2/rows-office.csv", "results/analysis-facts/fact-rows.csv"), ("confirm", "results/analysis-office-confirm/rows-all.csv", "results/analysis-facts-confirm/fact-rows.csv"),
                            ("floor", "results/analysis-office-floor/rows-all.csv", "results/analysis-facts-floor/fact-rows.csv"), ("dose", "results/analysis-office-dose/rows-all.csv", "results/analysis-facts-dose/fact-rows.csv")):
        fx_ = {r_["id"]: r_ for r_ in cd.R(fp_)}
        rr_ = [r_ for r_ in cd.R(rp_) if r_["id"] in fx_ and cd.complete(r_) and r_["task"].startswith("o")]
        for t_, dv_ in pair_diffs(rr_, "D1-K8", "D0", lambda r_, fx_=fx_: cd.num(fx_[r_["id"]]["right_legacy_pct"])).items():
            strata_[(name_, t_)] = dv_
    h1pool = cd.pooled(strata_)
    assert h1pool["lo"] > 8 and h1pool["n"] == sum(r_["n"] for r_ in h1l4) == 140
    # ---- pooling over batches, three ways (review of 2026-10-08): the report pools all pairs, deviations taken inside (batch, task)
    def mstrata(spec: list, col: str, kind: str = "diff", ok=done_) -> dict:
        out_ = {}
        for bt_, ga_, gb_ in spec:
            ra_ = {(r_["task"], r_["rep"]): r_ for r_ in MT if r_["batch"] == bt_ and r_["group"] == ga_ and ok(r_) and mnum(r_, col) is not None}
            rb_ = {(r_["task"], r_["rep"]): r_ for r_ in MT if r_["batch"] == bt_ and r_["group"] == gb_ and ok(r_) and mnum(r_, col) is not None}
            for k_ in ra_:
                if k_ in rb_:
                    x_, y_ = mnum(ra_[k_], col), mnum(rb_[k_], col)
                    out_.setdefault((bt_, k_[0]), []).append(math.log(x_ / y_) if kind == "ratio" else x_ - y_)
        return out_

    def pool_ways(d_: dict) -> dict:
        """all = every pair together (the report); eq = each batch computed on its own, then the plain mean of the
        batches; hk = the batch as a random factor (DerSimonian-Laird weights, Hartung-Knapp interval, t on batches - 1
        degrees of freedom, never narrower than the plain random-effects interval); tau2 = variance between batches."""
        from scipy import stats as sps_
        per_ = []
        for bt_ in sorted({k_[0] for k_ in d_}):
            sub_ = {k_: v_ for k_, v_ in d_.items() if k_[0] == bt_}
            z_ = cd.dal.tci(sub_, equal=True)
            df_ = z_["n"] - len(sub_)
            per_.append((z_["est"], (z_["hi"] - z_["lo"]) / (2 * sps_.t.ppf(0.975, df_)), df_))
        k_ = len(per_)
        eq_, eq_se_ = sum(e_ for e_, _, _ in per_) / k_, math.sqrt(sum(s_ ** 2 for _, s_, _ in per_)) / k_
        h_ = sps_.t.ppf(0.975, sum(df_ for _, _, df_ in per_)) * eq_se_
        w_ = [1 / s_ ** 2 for _, s_, _ in per_]
        fe_ = sum(wi_ * e_ for wi_, (e_, _, _) in zip(w_, per_)) / sum(w_)
        q_ = sum(wi_ * (e_ - fe_) ** 2 for wi_, (e_, _, _) in zip(w_, per_))
        tau2_ = max(0.0, (q_ - (k_ - 1)) / (sum(w_) - sum(wi_ ** 2 for wi_ in w_) / sum(w_)))
        wr_ = [1 / (s_ ** 2 + tau2_) for _, s_, _ in per_]
        re_ = sum(wi_ * e_ for wi_, (e_, _, _) in zip(wr_, per_)) / sum(wr_)
        re_se_ = math.sqrt(1 / sum(wr_))
        hk_se_ = math.sqrt(sum(wi_ * (e_ - re_) ** 2 for wi_, (e_, _, _) in zip(wr_, per_)) / ((k_ - 1) * sum(wr_)))
        hh_ = sps_.t.ppf(0.975, k_ - 1) * max(hk_se_, re_se_)
        a_ = cd.dal.tci(d_)
        return {"all": {"est": a_["est"], "lo": a_["lo"], "hi": a_["hi"], "n": a_["n"]}, "eq": {"est": eq_, "lo": eq_ - h_, "hi": eq_ + h_}, "tau2": tau2_,
                "hk": {"est": re_, "lo": re_ - hh_, "hi": re_ + hh_}, "k": k_}
    K1B = [("main-office", "D1-K1", "D1-K8"), ("office-confirm", "D1-K1", "D1-K8")]
    D2B = [("main-office", "D2-K8", "D1-K8"), ("office-confirm", "D2-K8", "D1-K8"), ("wait-office-2", "W-D2-K8", "W-D1-K8"), ("office-keep-depth", "W-N-D2-K8", "W-N-D1-K8")]
    H1B = [("main-office", "D1-K8", "D0"), ("office-confirm", "D1-K8", "D0"), ("office-floor", "D1-K8", "D0"), ("office-dose", "D1-K8", "D0")]
    pw_k1, pw_d2, pw_d2f, pw_h1 = pool_ways(mstrata(K1B, "facts63")), pool_ways(mstrata(D2B, "facts63")), pool_ways(mstrata(D2B, "facts_all")), pool_ways(mstrata(H1B, "facts63"))
    assert abs(pw_k1["all"]["est"] - k1p["est"]) < 0.05 and abs(pw_k1["all"]["lo"] - k1p["lo"]) < 0.05 and pw_k1["all"]["n"] == k1p["n"]
    assert abs(pw_d2["all"]["est"] - p2leg["est"]) < 0.05 and abs(pw_d2f["all"]["est"] - p2k8["est"]) < 0.05 and abs(pw_d2f["all"]["lo"] - p2k8["lo"]) < 0.05 and abs(pw_h1["all"]["est"] - h1pool["est"]) < 0.05
    assert pw_k1["tau2"] == pw_d2["tau2"] == pw_d2f["tau2"] == pw_h1["tau2"] == 0  # the batches agree within their sampling error
    assert -0.1 < pw_k1["eq"]["hi"] < 0.1 and pw_d2f["hk"]["lo"] < 0 < pw_d2f["hk"]["hi"] and pw_d2f["eq"]["lo"] > 0 and pw_h1["hk"]["lo"] > 5
    # the three code tasks with the parallel sentence, K against 8: without the pairs that hold a run whose root agent did not finish
    c3fin = {k_: cd.dal.tci(mstrata([("main-code", f"E-D1-K{k_}", "E-D1-K8")], "q", ok=lambda r_: r_["status"] != "no_answer"), equal=True) for k_ in (1, 2, 4)}
    c3all = {k_: cd.dal.tci(mstrata([("main-code", f"E-D1-K{k_}", "E-D1-K8")], "q", ok=lambda r_: True), equal=True) for k_ in (1, 2, 4)}
    assert all(abs(c3all[k_]["est"] - c3[q_]["score"]["est"]) < 0.05 for k_, q_ in ((1, "C3a"), (2, "C3b"), (4, "C3c"))) and all(v_["lo"] < 0 < v_["hi"] and v_["est"] < -1 for v_ in c3fin.values())
    lv63 = {g_: cd.means(fx63, g_, "right_legacy_pct") for g_ in ("D0", "D1-K8", "D2-K8")}  # the level on the 63 items, the main batch
    assert abs(lv63["D1-K8"] - lv63["D0"] - h1leg["est"]) < 0.05 and 76 < lv63["D0"] < 77 and 85 < lv63["D1-K8"] < 86
    d2rows = [r_ for r_ in o["depth_rows"] if r_["depth"] == 2 and r_["batch"] != "highk"]  # depth 2 against 1 at K = 8, batch by batch
    assert [r_["batch"] for r_ in d2rows] == ["formal", "confirm", "wait2", "keep"] and all(r_["cost_lo"] > 1 for r_ in d2rows) and all(r_["legacy_lo"] < 0 < r_["legacy_hi"] and r_["legacy_est"] > 0 for r_ in d2rows)
    assert sum(1 for r_ in d2rows if r_["time_lo"] > 1) == 1 and min(r_["time_ratio"] for r_ in d2rows) > 0.99 and sum(1 for r_ in d2rows if r_["time_ratio"] > 1.1) == 2
    d2c_rng = sorted(r_["cost_ratio"] for r_ in d2rows)
    crash_by = []  # runs of depth 2 that crashed on exit, batch by batch (the process does not wait for the subagents)
    for f_, g_ in (("results/analysis-v2/rows.csv", "D2-K8"), ("results/analysis-office-confirm/rows-all.csv", "D2-K8"), ("results/analysis-wait/rows.csv", "D2-K8")):
        sub_ = [r_ for r_ in cd.R(f_) if r_["group"] == g_ and r_["task"] in ce.TASKS]
        crash_by.append((sum(1 for r_ in sub_ if r_.get("crash5063") == "True"), len(sub_)))
    assert sum(a_ for a_, _ in crash_by) == rel_d2["crash"] and sum(b_ for _, b_ in crash_by) == rel_d2["runs"] and all(a_ > 0 for a_, _ in crash_by)
    # the whole study: yuan and container hours of every run of the report, and the yuan the judging files record
    st_runs, st_model, st_total, st_sec = 0, 0.0, 0.0, 0.0
    for f_ in ce.every_rows():
        for r_ in cd.R(f_):
            st_runs += 1
            st_model += cd.num(r_.get("model_cost_peak")) or 0
            st_total += cd.num(r_.get("total_cost_peak")) or cd.num(r_.get("model_cost_peak")) or 0
            st_sec += cd.num(r_.get("seconds")) or 0
    jc_dev, jc_mac = cd.J("results/analysis-mechanism/judge-cost-devbox.json"), cd.J("results/analysis-mechanism/judge-cost-mac.json")
    st_judge = sum(v_["yuan"] for v_ in jc_dev.values()) + sum(v_["yuan"] for k_, v_ in jc_mac.items() if k_ not in jc_dev)
    st_valid = sum(v_["yuan"] for k_, v_ in jc_dev.items() if k_.startswith(("validate-effort", "validate-max")))  # the two rounds that checked the judge's effort setting
    assert st_runs == iss["all_runs"] and abs(st_model - MX["rejected"]["model_yuan"]) < 1 and 15000 < st_total < 17000 and 450 < st_sec / 3600 < 520 and 10000 < st_judge < 11000 and 2000 < st_valid < 2500
    n_asserts = sum(1 for ln_ in Path(__file__).read_text(encoding="utf-8").splitlines() if ln_.lstrip().startswith("assert "))
    CHECK_ROUNDS = 20  # rounds of the independent recomputation up to this text (the checker does not read this file)

    def scored_pairs(dir_: str, score_file_: str, metric_: str) -> list:
        """(score without subagents, score of the default) per task of a public benchmark, the tasks scored in both groups."""
        flagged_ = set(cd.J(f"{dir_}/stats.json")["inputs"]["flagged"])
        sc_ = {r_["id"]: r_ for r_ in cd.R(f"{dir_}/{score_file_}")}
        by_ = {(r_["task"], r_["group"]): cd.num(sc_[r_["id"]][metric_]) for r_ in cd.R(f"{dir_}/rows-all.csv")
               if r_["id"] not in flagged_ and r_["id"] in sc_ and cd.num(sc_[r_["id"]].get(metric_)) is not None}
        return [(by_[(t_, "D0")], by_[(t_, "W-D1-K8")]) for (t_, g_) in sorted(by_) if g_ == "D0" and (t_, "W-D1-K8") in by_]
    pp_d, pp_w = scored_pairs("results/analysis-drb2-h1", "drb2-rows.csv", "total"), scored_pairs("results/analysis-ws-h1", "ws-rows.csv", "f1_item")
    up_d, up_w = sum(1 for a_, b_ in pp_d if b_ >= a_ - 1e-9), sum(1 for a_, b_ in pp_w if b_ >= a_ - 1e-9)
    assert (len(pp_d), up_d, len(pp_w), up_w) == (29, 24, 19, 13) and len(pp_d) == gb["drb2"]["n"] and len(pp_w) == gb["ws"]["n"]
    wsq = ws["cmp"]["H1n"]["f1_item"]
    assert -wsq["hi"] < -5 and wsq["lo"] < 0 < wsq["hi"]  # no subagents against the default: the worse end beyond the margin, the interval holds 0
    nf_ = [(c["p4"]["means"]["D0"]["score"], c["p4"]["means"]["D1-K8"]["score"]), (ch["means"]["D0"]["score"], ch["means"]["W-D1-K8"]["score"]),
           (fm_["D0"]["score"], fm_["W-D1-K8"]["score"]), (xm["D0"]["score"], xm["W-D1-K8"]["score"])]  # the four tasks graded by tests or a key, no time limit
    assert min(min(a_, b_) for a_, b_ in nf_) > 96 and max(abs(a_ - b_) for a_, b_ in nf_) < 0.3 and 74 < c["means"]["D0"]["score"] < 75.5 and 75.5 < c["means"]["D1-K8"]["score"] < 77
    all_times_ = [h1["seconds"], wt, dtm, c["cmp"]["C1"]["seconds"], c["p4"]["c1"]["seconds"], ch["cmp"]["NC"]["seconds"], free["cmp"]["NC"]["answer_s"], xl["cmp"]["NC"]["answer_s"]]
    assert all(q_["hi"] >= 1 for q_ in all_times_)  # nowhere does the default answer clearly sooner than a single agent
    srch2 = cmp_["D2-K8"]["search_aux"]
    assert srch2["lo"] > 1 and 1.6 < srch2["est"] < 2.2
    tk_ = [r_["cells"][v_]["t"]["est"] for r_ in L["k"] for v_ in (16, 64) if r_["key"] != "wide" and v_ in r_["cells"] and r_["cells"][v_]["t"] is not None]
    assert len(tk_) == 5 and 0.9 < min(tk_) and max(tk_) < 1.1
    mb4 = mp4["batch_legacy"]  # four merged reports on the 63 items, batch by batch (a: the comparison group ran a day earlier; b: the same batch)
    assert mb4["a"]["lo"] > 0 and mb4["b"]["lo"] < 0 < mb4["b"]["hi"] and mb4["b"]["lo"] > -QM("office") and mb4["a"]["n"] == mb4["b"]["n"] == 10
    k4exact = xk["NK4"]["score"]["p"]  # original prompt, K = 4 against K = 8: the sign-flip test of the batch statistics
    assert 0.1 < k4exact < 0.15 and kq("xl", 4)["hi"] < 0 and rb["h1"]["lo"] < 0 < rb["h1"]["hi"] and p2k8["lo"] > 0 and cmp_["D1-K1"]["right_pct"]["hi"] < 0
    assert conf_t2["lo"] < 1 < conf_t2["hi"] and dq("office", 2, "t")["lo"] < 1 < dq("office", 2, "t")["hi"] and fk1["hi"] < 0 and kq("code", 1)["lo"] < 0 < kq("code", 1)["hi"]
    first_full = next(r_ for r_ in o["h1_reps"] if r_["name"] == "formal")["est"]  # the first batch on the whole list: what the margin of 8 points was half of
    assert 15.5 < first_full < 17.5
    xci_m = lambda q_: (f"×{rnd(q_['est'], 2)} [{rnd(q_['lo'], 2)}, {rnd(q_['hi'], 4 if rnd(q_['hi'], 3) == rnd(TM, 3) else 3)}]"
                        if rnd(q_["hi"], 2) == rnd(TM, 2) else xci(q_))  # noqa: E731  (an upper end that rounds to the margin: more decimals, until it differs)
    code_rows_ = cd.R("results/analysis-v2/rows-code-c1w1.csv")  # the two reading tasks, original prompt
    code_d2_raw = cd.contrast(code_rows_, "D2-K8", "D1-K8", lambda r_: cd.num(r_["seconds"]), "ratio")
    code_d2_std = cd.contrast(code_rows_, "D2-K8", "D1-K8", lambda r_: cd.num(r_["std_seconds"]), "ratio")  # every request recomputed at one model speed
    assert abs(code_d2_raw["est"] - dq("code", 2, "t")["est"]) < 0.005 and code_d2_std["lo"] < 1 < code_d2_std["hi"] and code_d2_std["hi"] > TM
    de16_, de64_ = xl["depth_hi"]["DE16"]["answer_s"], xl["depth_hi"]["DE64"]["answer_s"]  # depth 2 against 1 on the large coding task at K = 16 and 64 (no-review prompt)
    assert tstate({"t": de16_}) == "open" and tstate({"t": de64_}) == "open" and tstate({"t": dq("xl", 2, "t")}) == "ok"
    m2k_ = o["m2_vs_keep"]  # two merged reports against the default told to write everything in (whole list)
    assert m2k_["hi"] < 0 and m2k_["lo"] < -QM("office") and m2k_["n"] == 19
    m4k_task = {}  # the same contrast for four merged reports, task by task
    for r_ in cd.J("results/analysis-office-merge-b/merge-stats.json")["rows"]:
        if r_["kind"] == "M4" and r_.get("N-D1-K8_right_pct") is not None:
            m4k_task.setdefault(r_["base_task"], []).append(r_["merged_right_pct"] - r_.get("N-D1-K8_right_pct_hg", r_["N-D1-K8_right_pct"]))
    m4k_task = {t_: st.mean(v_) for t_, v_ in m4k_task.items()}
    assert m4k_task["o1-singapore-trip"] < -4 and m4k_task["o2-server-cpu-report"] > 4 and abs(st.mean(m4k_task.values()) - o["m4_vs_keep"]["est"]) < 0.05
    hk8med = st.median(cd.num(r_["total_cost_peak"]) for r_ in cd.R("results/analysis-office-highk/rows-all.csv") if r_["group"] == "W-D1-K8" and cd.complete(r_))  # the default of the batch of the old default
    assert 7.5 < hk8med < 8.2 and 7 < ck["default"]["median"] < 7.6
    kids3_ = sorted(made(b_, g_) for b_, g_ in (("office-confirm", "D1-K8"), ("ws-h1", "W-D1-K8"), ("drb2-h1", "W-D1-K8")))  # subagents started per default run, every run
    assert 2.7 < kids3_[0] < kids3_[-1] < 4.1
    rej_share = (MX["rejected"]["args_yuan"] + MX["rejected"]["dead_step_yuan"]) / MX["rejected"]["model_yuan"]  # the two amounts overlap: an upper bound
    assert 0.01 < rej_share < 0.02
    hi_d, lo_d = sum(1 for a_, b_ in pp_d if b_ > a_ + 1e-9), sum(1 for a_, b_ in pp_d if b_ < a_ - 1e-9)
    hi_w, lo_w = sum(1 for a_, b_ in pp_w if b_ > a_ + 1e-9), sum(1 for a_, b_ in pp_w if b_ < a_ - 1e-9)
    assert (hi_d, lo_d, hi_w, lo_w) == (19, 5, 10, 6)
    assert qstate({"q": c3["C3c"]["score"]}, "code") == "ok" and qstate({"legacy": k2p}, "office") == "ok" and qstate({"legacy": kfirst[2]}, "office") == "ok"

    # ---------------------------------------------------------------------------------------------------- abstract
    d.sec("new:abstract")
    d.add("## 摘要", "")
    d.p(f"DSH（DeepSeek Harness）里，主 agent 可以把活交给 subagent 去做，有两个上限管着：深度上限 D（subagent 还能不能再开 subagent）和同时存活上限 K（同一时刻最多几个没结束）。"
        f"九种任务约 {round(iss['all_runs'], -2):,} 次运行，把各个取值和默认（D=1、K=8）比质量、费用和用户等的时间。")
    d.add(f"- K 调大没用，调小有代价。联网调研的任务上模型一次只开三四个，K=4 的质量不比 8 差、也不省钱，办公报告题（联网调研后写长报告）上 K=64 也一样；K=1 让办公报告题少写对约 {rnd(-k1p['est'], 0)} 个百分点；"
          f"大型编码题在题面要求不复核时，K=1、2 的用时是 K=8 的 {rnd(kq('xln', 1, 't')['est'], 1)}、{rnd(kq('xln', 2, 't')['est'], 1)} 倍。",
          f"- 放开深度主要是多花钱。办公报告题一次约 {m['D1-K8']['cost']:.0f} 元变成约 {m['D2-K8']['cost']:.0f} 元，写对的事实只多 {rnd(p2leg['est'], 0)}–{rnd(p2k8['est'], 0)} 个百分点（按事先定下的 63 条是 {sg(p2leg['est'])}，区间含 0）。",
          f"- 开 subagent 有用也贵。办公报告题多写对 {rnd(h1leg['est'], 0)} 个百分点，费用是不开的 {rnd(h1_cost, 1)} 倍。", "")
    d.p("建议：两个默认值都不改。要改两处行为：进程退出前等 subagent 做完；把上限告诉模型" + (f"（写进工具说明以后 K=2 上被拒的调用{'基本没有了' if TR['beh2'] else '仍然有'}，质量{TR['q']['P1']}）。" if TD else "（效果还在测）。"))

    # ------------------------------------------------------------------------------------------------- conclusions
    d.sec("new:conclusion")
    d.add("## 结论", "")
    # The page owner cut the list of terms down to this one line and reworded the answer (2026-10-08); the other terms
    # are explained where the method first uses them.
    d.p("调研类任务：联网查资料的三种（办公报告题、评测集填表题、评测集报告题）。其余六种不联网，叫代码类任务")
    d.p("**两个默认值（D=1、K=8）不需要调整。** 依据：")
    d.add(f"- 开 subagent 有用也贵：办公报告题写对的事实从 {rnd(lv63['D0'])}% 到 {rnd(lv63['D1-K8'])}%（+{rnd(h1leg['est'])} 个百分点，{CN[len(h1l4)]}批都显著），两个公开评测集高 3 分上下；调研类任务的费用是不开的 {rnd(res_cost[0], 1)}–{rnd(res_cost[-1], 1)} 倍。代码类任务平均分几乎不变；大型编码题上全部隐藏测试都通过的运行，默认 {xpass['W-D1-K8'][0]}/{xpass['W-D1-K8'][1]}，不开 {xpass['D0'][0]}/{xpass['D0'][1]}（结果 1、2）。",
          "- K 调大没用：K=16、64 在质量、时间、费用上都没测出好处。调研类任务上这个模型一次只开三四个，碰不到上限（结果 3、4）。",
          f"- K 调小有代价：K=1 让办公报告题少写对 {rnd(-k1p['est'])} 个百分点（两批合起来）；大型编码题在题面要求不复核时，K=1、2、4 的用时是 K=8 的 {rnd(kq('xln', 1, 't')['est'], 2)}、{rnd(kq('xln', 2, 't')['est'], 2)}、{rnd(kq('xln', 4, 't')['est'], 2)} 倍。"
          "调研类任务上 K=4 和 8 没测出差别，也不省钱（结果 4）。",
          f"- 放开到深度 2 主要是多花钱：办公报告题的费用是 {rnd(p2cost['est'], 2)} 倍，{CN[len(d2rows)]}批都显著；写对的事实只多 {rnd(p2leg['est'], 0)}–{rnd(p2k8['est'], 0)} 个百分点（63 条 {sg(p2leg['est'])}、区间含 0，全清单 {sg(p2k8['est'])}）；评测集报告题、读代码题贵到约 1.5 倍，评测集填表题没测出变贵（结果 5）。",
          f"- 深度 2、3 交付有问题：命令行一次性运行时，办公报告题 K=8 的 {runs23} 次里 {crash23} 次退出时崩溃，三批都出现；这是 DSH 的缺陷，让进程等 subagent 以后基本消失（结果 8）。",
          "- 多写对来自分头去查，不一定要靠 subagent：四个单 agent 各写一份再合并，写对的不比默认少，费用相当，要多等三到七成（结果 7）。", "")
    assert (EXP / NEW / "conclusion-tradeoff.png").exists()  # drawn by plot_clean.conclusion_fig from the same cells as the two full tables
    d.add(f"![]({NEW}/conclusion-tradeoff.png)", "",
          "图：上面几条依据画在一起。左边是办公报告题，每个点是一种设置和同批的默认比：横轴是费用的倍数，纵轴是写对的事实差多少（63 条）。"
          "右边是大型编码题在题面要求不复核时的费用和用时，都是和 K=8、深度 1 比。深度 2 和深度 3 的费用倍数一样，画的时候左右错开了一点。", "")
    d.p(f"背景里的三份用户日志是旧默认（9 月中旬以前：深度上限 3、数量不设上限）下的运行。现在的默认下 subagent 开不出第 2 层；办公报告题一次任务的中位数，相当于旧默认的设置是 {ck['old']['median']:.0f} 元，现在的默认是 {ck['default']['median']:.0f}–{hk8med:.0f} 元（结果 2）。")
    d.p("适用范围：一个模型（v41flash，推理强度最高一档）、一个 DSH 版本、命令行一次性运行；重复跑的办公报告题只有两道；质量量的是事实写对了多少，由模型判分，还没有人工核对；"
        "代码类任务上 K 和深度的结论是在题面加了并行提示或不复核提示时得到的。")
    d.add("**建议**", "",
          "1. 改两处 DSH 行为：命令行一次性运行时，进程退出前等 subagent 做完；把上限告诉模型，或者到了上限就不再给它开 subagent 的工具" + (f"（写进工具说明以后，K=2 上被拒的调用{'基本没有了' if TR['beh2'] else '仍然有'}，写对的事实{TR['q']['P1']}；默认值下{'费用 ' + x(tc['P2']['total_cost_peak']) if TR['p2'] != 'none' else '开的数量、质量、费用都没测出变化'}；结果 9）。" if TD else "（效果还在测）。"),
          f"2. K 保持 8。降到 4 不是明显更差，是费用和等待时间的取舍：调研类任务上没测出变化（多数运行同时活着的不到 4 个；评测集填表题有 {capped4['ws-k4'][0]}/{capped4['ws-k4'][1]} 次碰到了 4）；能拆成很多块的编码任务省两到三成的钱（费用是 K=8 的 {rnd(kq('xl', 4, 'c')['est'], 2)}–{rnd(kq('xln', 4, 'c')['est'], 2)} 倍），写代码那一段慢两到七成。"
          "想省编码任务的钱，先管复核（占大型编码题六成费用），比调 K 有效（结果 4、结果 6）。", "")

    # -------------------------------------------------------------------------------------------- the four claims
    d.sec("new:claims")
    d.add("## 要检验的四个说法", "")
    assert 2.5 < o["k64_d2"]["total_cost_peak"]["est"] < 3.1 and o["k64_d2"]["total_cost_peak"]["lo"] > 2 and kq("free", 4, "c")["hi"] < 1 and kq("xl", 4, "c")["est"] < kq("free", 4, "c")["est"] < kq("xln", 4, "c")["est"]
    d.tbl("claims", "四个说法、所在批开跑之前写进方案的预想、结果。", [
        ["说法", "开跑前写下的预想", "结果", "在哪"],
        ["1. K 只在模型想开得比它多时起作用", "限时 24 题上得分随 K 升高，到 8 附近到顶", f"成立，依据是被拒绝的调用：调研类任务 {res_runs} 次默认运行没有一次被 K=8 拒绝，大型编码题每次都被拒绝。写下的预想是在只作参考的限时题上，大体对上", "结果 3、4"],
        ["2. 放开深度，费用上去，质量不变", "深度 2、K=64：费用 2–4 倍，评分表总分没有差别",
         f"成立：那一组费用是 {rnd(o['k64_d2']['total_cost_peak']['est'], 1)} 倍，只放开深度是 {rnd(d2pub[0], 1)}–{rnd(p2cost['est'], 1)} 倍；写对的事实多 2–4 个百分点（63 条的区间含 0，全清单显著）", "结果 5"],
        ["3. 开 subagent 让用户少等", "不限时 24 题上开 subagent 用时不到不开的一半，K 越大越快", "不成立：文件写完得更早，最终回答没有更早；大型编码题去掉复核以后才更快", "结果 6"],
        ["4. 多写对靠的是查得多，不是靠分给几个 agent 各查一块", "单 agent 查够同样多，写对的和默认相差 5 个百分点以内", "前一半没检验成：题面要求多查以后，单 agent 的搜索请求到了默认的水平，花在模型上的钱不到默认的一半，写对的少 4–9 个百分点。后一半成立：四个单 agent 各把整道题做一遍再合并，不比默认少", "结果 7"]])
    d.p("这四条预想都是所在批开跑之前写的；全部预想和实际的对照在附录的{tab:expect}。说法 3 不成立，说明代码类任务上开 subagent 换来的不是少等；说法 4 回答“多写对是不是非要靠 subagent”。这两条不直接决定 K 和 D 取几，放在结果 6、7。")

    # ------------------------------------------------------------------------------------------------------ method
    d.sec("new:method")
    d.add("## 方法", "")
    d.tbl("tasks-short", "九种任务。前三种是调研类，后六种是代码类。", [
        ["任务", "做什么", "质量怎么算", "每组跑几次"],
        ["办公报告题", "联网调研后写长报告，2 道（新加坡旅行攻略、三款服务器 CPU 选型），取自背景里的用户日志", "写对的事实占比（63 条的清单）", f"每题 {m['D1-K8']['n'] // 2} 次"],
        ["评测集填表题", f"联网收集信息填表：公开评测集 WideSearch 的 {scr['runs']} 道中文题里，去掉单 agent 已经做到 90 分的 {scr['top']} 道和搜索时认出评测集的 {scr['named']} 道，剩下的 {scr['picked']} 道；对比用的不开组是和默认同一批重新跑的", "和标准答案逐格比对", "每题 1 次"],
        ["评测集报告题", f"联网调研写报告，公开评测集 DeepResearch Bench II 的 {drb['tasks']} 道", "评测集自带的评分项", "每题 1 次"],
        ["读代码题", "读 DSH 源码，回答问题、写方案，2 道", "判分模型按要点和评分表打分", "每题 10 次"],
        ["小编程题", "4 道 Python 练习", "隐藏测试", "10 次"],
        ["限时 24 题（只作参考）", "24 道 Python 小题，限时 3 分钟。实际使用没有时限，所以方案里写明只作参考", "隐藏测试", "10 次"],
        ["16 步串行题", "16 步数据处理，后一步要用前一步的答案，没法分头做", "对标准答案", "10 次"],
        ["不限时 24 题", "同样 24 道小题，不限时", "隐藏测试", "10–20 次"],
        ["大型编码题", "按规格写一个 61 个文件的 Python 包", f"{xl['tests']:,} 个隐藏测试", "10 次"]])
    assert scr["runs"] == scr["top"] + scr["named"] + scr["picked"]
    d.add("- **取值。** D：0（不开，这时只有一个 agent 在做，下文也叫单 agent）、1、2、3；K：1、2、4、8、16、64。主要的对比每次只改一个上限；另有几组两个一起改（比如深度 3、K=64，相当于旧默认），用到的地方会写明。"
          "不是每个取值都在每种任务上测过：K=16 没在调研类任务上测，K=64 在调研类任务里只测了办公报告题，深度 3 只在办公报告题、读代码题和小编程题上测过（附录的{fig:coverage}）。",
          f"- **设计。** 实验分 {len(BATCHES)} 批做，一批是一起跑、一起判分的几组设置。一批里每一轮把各组各跑一次，顺序随机，同时运行的个数固定。每个取值只和同一批里的对照组比：同一道题同一轮的两次运行配成一对算差，给 95% 区间，下文的“40 对”指这个。"
          "“显著”指区间不含 0（倍数是不含 1）；同一批里事前写定要一起看的几个对比，还要一起校正以后仍然成立，图里的空心点包括校正以后不成立的。"
          "每批的主要对比都在这一批判分之前写定；后面的批是看过前面的结果以后设计的，跨批合起来算的数都是事后的。",
          f"- **题面。** 调研类任务和大型编码题用原题面。读代码题和两道 24 题换 K 的各组，题面末尾加了一句并行提示（“{ENCOURAGE}”；不加的话模型开得少，K 起不了作用），对照的 K=8 也加。"
          "大型编码题另有一套题面加了不复核提示（复核指代码写完以后，模型再派一批 subagent 去检查、补测试；这句提示要求文件写完以后不要再派），两套都测，各自和同一套里的 K=8 比。{tab:limits-ci} 和{tab:limits-ci-d} 每一行都写了是哪套题面。",
          "- **环境。** 模型是 DeepSeek 内部端点的 v41flash，推理强度开到最高一档；DSH 版本 0.2.0-rc.2；每次运行一个 4 核 16 GB 的容器，用命令行一次性运行（一条指令做到底，主 agent 给出最终回答，进程就退出）。事实清单、评分表和两个公开评测集由 Opus 5.5 判分，判分时看不到是哪一组；写代码的任务用隐藏测试。",
          "- **指标。** 质量见上表，满分都是 100。费用是元/次：模型费按这个模型官网公开的高峰时段价格算，联网任务另加搜索费。时间是从开始到主 agent 给出最终回答，也就是用户等的时间。",
          f"- **办公报告题的质量指标换过一次。** 第一批按评分表打总分，测不出开不开 subagent 的差别（{ci(rb['h1'])}）。之后改成对照事实清单逐条核对：63 条是任何运行之前定下的评分要点，另外 132 条是看过第一批报告以后补的，合起来 195 条叫全清单。"
          "各批事前写定的主要对比按全清单做；10 月 7 日看过两套结果以后改成以 63 条为准，因为后补的条目参考的样本多数来自开 subagent 的组。正文的判断都按 63 条，全清单的数并排给。",
          "- **一个对比做过不止一批时用哪个数。** 办公报告题上换 K（K=1、2、4，各两批）和放开深度（深度 2 四批、深度 3 两批）都用各批合起来的数；开不开四批都显著，正文用每组 40 次的主要一批。"
          "读代码题换 K 按事前写定的算法，和小编程题三道题一起算。各批各自的数在{tab:reps}，换一种算法结论变不变在{tab:sens}。", "")
    d.p("**怎么读每个取值。** 每个取值都和默认比质量、费用、用户等的时间，各给估计值和 95% 区间；进程退出时崩不崩单独看。"
        "区间不含 0（倍数是不含 1），并且和同批事前写定的几个对比一起校正以后仍然成立的，写“更好”或“更差”，表里用粗体；其余写“没测出差别”。")
    d.p(f"“没测出差别”不等于没有差别：区间有多宽，这次能排除的差别就多大。按 80% 的把握算，办公报告题 40 对的对比能测出的最小差别是 {md40[0]:.0f}–{md40[-1]:.0f} 个百分点，20 对的是 {md20[0]:.0f}–{md20[-1]:.0f} 个；"
        f"评测集填表题 {md_ws[0]:.0f}–{md_ws[-1]:.0f} 分，评测集报告题 {md_drb[0]:.0f}–{md_drb[-1]:.0f} 分；费用和时间多数要差到 {rnd(md_ra[0])}–{rnd(rb_typ[1])} 倍才测得出。")
    d.p("换不换默认值按这一条：另一个取值有一样更好、别的都没有更差，才值得换；有好有坏的是取舍，报告把两边的数摆出来。"
        "各批当时写的判断规则记在实验方案里：深度的八条没有一条给出放开；K 的几条先后给出过 4 和 8，最后一条（补测 K=4 之前写的）给出保持 8。")
    d.add(f"- **判分稳不稳。** 同一份报告判两遍，事实清单逐条相同的占 {100 * kap_all[1]:.1f}%，kappa {kap_all[2]:.2f}（只分判对和没判对是 {kap_right[2]:.2f}；{kap_all[0]:,} 条）。"
          f"判分强度用 high：在旧评分表上拿同样 {ve['between']['n']} 份报告比过最高一档 max，总分平均差 {abs(ve['between']['mean_diff']):.1f} 分，逐条相同的占 {100 * ve_share('between'):.1f}%，和 max 自己判两遍一样（{100 * ve_share('within_a'):.1f}%）。"
          "这些都是判分模型和自己比；和人工的对照还没做。")
    d.add(f"- **花费。** {st_runs:,} 次运行按公开高峰价约 {st_total / 1e4:.1f} 万元（模型费 {st_model:,.0f} 元，其余是搜索费）；判分约 {st_judge / 1e4:.2f} 万元，其中约 {round(st_valid, -2):,.0f} 元用在校验判分强度的两轮上；容器一共运行约 {round(st_sec / 3600, -1):.0f} 小时。",
          f"- **数字怎么保证。** 所有数由脚本从数据文件生成，带 {n_asserts // 10 * 10} 多条断言；另由一个不读生成脚本的 agent 从原始数据独立重算了 {CHECK_ROUNDS} 轮。材料和脚本的位置在附录。", "")

    # ----------------------------------------------------------------------------------------------------- results
    d.sec("new:results")
    d.add("## 结果", "")
    d.p("每个小节是几张图或表，每张下面一到三句话。")

    # ---- 1. what delegating buys
    d.add("### 结果 1：开 subagent 换来什么", "")
    d.place("fig:summary", "默认对不开 subagent（都是原题面）：默认下模型开几个、质量高多少、费用和时间是不开的几倍。点是估计值，横线是 95% 区间；办公报告题的空心点是全清单。")
    d.add(f"- 调研类任务：办公报告题写对的事实从 {rnd(lv63['D0'])}% 到 {rnd(lv63['D1-K8'])}%（{ci(h1leg)}，{h1leg['n']} 对），评测集报告题高 {rnd(dt['est'])} 分，评测集填表题没测出（{ci(wsq)}）。费用是不开的 {rnd(res_cost[0], 1)}–{rnd(res_cost[-1], 1)} 倍。",
          f"- 写错的事实各组每份报告都是 {min(m[g_]['wrong'] for g_ in m):.1f}–{max(m[g_]['wrong'] for g_ in m):.1f} 条，开不开、放不放开深度都没测出差别（默认对不开 {ci(cd.flip(cmp_['D0']['wrong_firm_n']), 2)}）。",
          f"- 代码类任务：小编程题、16 步串行题、不限时 24 题和大型编码题两组的平均分都在 96 分以上，相差不到 0.3 分；读代码题 {c['means']['D0']['score']:.0f} 分上下，没测出差别（{ci(c['cmp']['C1']['score'])}）；"
          f"限时 24 题（只作参考）高 {rnd(wd['cmp']['NC']['score']['est'])} 分。模型会开 subagent 的四种任务，费用是不开的 {rnd(spent[0], 1)}–{rnd(spent[-1], 1)} 倍。",
          "- 用户等的时间，没有一种任务测出缩短（结果 6）。小编程题和 16 步串行题上默认时模型一个 subagent 也不开，两组做的是同一件事。", "")
    d.place("fig:pub-pair", "两个公开评测集，每道题一个点：横轴是不开 subagent 的得分，纵轴是默认的得分，斜线上方是默认更高。")
    d.add(f"- 按题看：评测集报告题 {len(pp_d)} 道里默认更高的 {hi_d} 道、更低的 {lo_d} 道，其余相同；评测集填表题 {len(pp_w)} 道里更高 {hi_w} 道、更低 {lo_w} 道。",
          f"- 每道题涨多少，和这道题默认开了几个 subagent 没看出关系（相关系数 {sg(gb['drb2']['r_subagents'], 2)} 和 {sg(gb['ws']['r_subagents'], 2)}；事后分析）。", "")
    d.place("fig:strata", "办公报告题：默认比不开多写对的事实落在哪一档。全清单的 195 条按不开 subagent 时被写对的频率分成四档；柱子是每份报告在这一档里写对的条数（事后分析）。")
    d.add(f"- 默认每份报告多写对约 {sa['total']['gain']:.0f} 条（全清单每题平均 97.5 条）。其中四分之三以上落在单 agent 有时写到、有时写不到的两档；单 agent 几乎都写到的一档只多 {rnd(sa['rows'][3]['gain'])} 条。",
          f"- 两道题分开看（按 63 条）：旅行攻略题四批都显著，多 {tl1[0]:.0f}–{tl1[1]:.0f} 个百分点；CPU 选型题多 {tl2[0]:.0f}–{tl2[1]:.0f} 个，只有一批显著。",
          f"- 这把尺子量的是查得全不全，不是报告好不好用：默认的报告也更长（{m['D1-K8']['chars'] / 1e4:.1f} 万字对 {m['D0']['chars'] / 1e4:.1f} 万字）；判分由模型做，还没有人工核对。", "")

    # ---- 2. what one task costs
    d.add("### 结果 2：一次任务花多少钱", "")
    d.place("tab:cost-task", "各任务一次运行的平均费用（元；联网的三种任务含搜索费）、每多开一个 subagent 多花的钱（费用对开的个数做直线拟合的斜率）和默认一次运行的 token 数（各 agent 合计，和同一行的费用是同一些运行）。")
    d.add(f"- 调研类任务默认一次 {min(res_dflt):.1f}–{max(res_dflt):.1f} 元，不开 {min(res_none):.1f}–{max(res_none):.1f} 元；大型编码题默认约 {xm['W-D1-K8']['cost']:.0f} 元，不开约 {xm['D0']['cost']:.0f} 元。",
          f"- 每多开一个 subagent，调研类任务多花 {rnd(web[0])}–{rnd(web[-1])} 元（约一半是搜索费），读代码题、小编程题、限时 24 题和 16 步串行题 {rnd(offline[0])}–{rnd(offline[-1])} 元。"
          f"大型编码题上写完以后派去复核的 subagent 一个 {rnd(cf2['xl']['review'])} 元，写代码的 {rnd(cf2['xl']['write'])} 元。",
          f"- 按 token 看：办公报告题默认一次约 {tok_def[0] + tok_def[1]:,.0f} 万输入（{100 * tok_def[1] / (tok_def[0] + tok_def[1]):.0f}% 读缓存）和 {tok_def[2]:.0f} 万输出，输入是不开的 {(tok_def[0] + tok_def[1]) / (tok_none[0] + tok_none[1]):.1f} 倍，输出 {tok_def[2] / tok_none[2]:.1f} 倍。", "")
    d.place("fig:cost-sub", "每个点是一次运行：横轴是这次运行开的 subagent 数，纵轴是费用。左边是办公报告题（含搜索费），右边是大型编码题（模型费）；直线是拟合线。")
    d.add(f"- 费用随开的个数直线上涨：办公报告题约 {rnd(fitc['intercept'])} 元加 {rnd(fitc['per_subagent'])} 元乘开的个数。K 和深度是通过改变开的个数来改变费用的（结果 4、5）。",
          f"- 同一种设置里各次运行差得远：默认设置跑过的 {da['n']} 次，最便宜 {da['min']:.0f} 元，最贵 {da['max']:.0f} 元。", "")
    d.place("fig:cost-dist", "办公报告题：每个点是一次运行的费用（含搜索费），横线是中位数。虚线是背景里两份联网的用户日志按同样算法得到的整场费用。")
    d.add(f"- 一次任务的中位数：不开 {ck['none']['median']:.0f} 元，默认 {ck['default']['median']:.0f} 元，深度 2 是 {ck['d2']['median']:.0f} 元，深度 3、K=64（相当于旧默认）{ck['old']['median']:.0f} 元，最贵的一次 {ck['old']['max']:.0f} 元。",
          f"- 背景里两份联网的用户日志是多轮对话，按同样的算法每份整场约 {st.mean(cst['logs_web']):.0f} 元；相当于旧默认的 {ck['old']['n']} 次单任务运行里有 {cst['old_over_logs']} 次超过这个数。",
          f"- 联网任务的费用约一半是搜索费（办公报告题默认组 {pct(search_share)}）。", "")
    deep4_ = [(cmp_["D2-K8"]["total_cost_peak"]["est"], cmp_["D2-K8"]["right_pct"]), (o["wait"]["WD3"]["total_cost_peak"]["est"], o["wait"]["WD3"]["right_pct"]),
              (o["k64_d2"]["total_cost_peak"]["est"], o["k64_d2"]["right_pct"]), (o["k64_d3"]["total_cost_peak"]["est"], o["k64_d3"]["right_pct"])]  # the four points with a deeper limit
    assert all(q_["lo"] < 0 < q_["hi"] and q_["est"] > 0 for _, q_ in deep4_) and 1.7 < min(c_ for c_, _ in deep4_) and max(c_ for c_, _ in deep4_) < 3
    d.place("fig:tradeoff", "办公报告题：每种设置和同批的默认比，横轴是费用的倍数，纵轴是写对的事实之差（全清单，个百分点）。竖线是 95% 区间；往右更贵，往上写对的更多。")
    d.add(f"- 放开深度的四个点都在右边：费用是默认的 {rnd(min(c_ for c_, _ in deep4_), 1)}–{rnd(max(c_ for c_, _ in deep4_), 1)} 倍，写对的事实高 {rnd(min(q_['est'] for _, q_ in deep4_), 0)}–{rnd(max(q_['est'] for _, q_ in deep4_), 0)} 个百分点，区间都跨过 0。",
          "- 只改 K 的点在左边或正中：K=1、2 便宜，写对的也少；K=4、64 的费用和默认一样。", "")

    # ---- 3. how many the model wants
    d.add("### 结果 3：模型自己想开多少", "")
    d.place("tab:behave", "默认设置下模型自己怎么开 subagent。“同时活着”指同一时刻没结束的 subagent 数；“同时活着最多”是各次运行里到过的最大值，其余各列是运行次数。")
    dep_runs3 = op["D1-K8"]["depth_runs"] + wso["depth_runs"] + dro["depth_runs"]
    assert res_runs == 94 and 70 < dep_runs3 < 80
    d.add(f"- 调研类任务：一次运行平均开 {rnd(kids3_[0])}–{rnd(kids3_[-1])} 个，{res_runs} 次默认运行没有一次调用被 K=8 拒绝；其中 {dep_runs3} 次有调用被深度上限拒绝，是 subagent 自己想再往下开。",
          f"- 大型编码题一次开 {xm['W-D1-K8']['kids']:.0f} 个，每次运行都有调用被 K 拒绝。读代码题里的问答题、小编程题和 16 步串行题上，模型自己不开。", "")
    d.place("fig:rejects", "办公报告题：各种设置下一次运行开出几个 subagent，有几次开 subagent 的调用被深度上限拒绝、几次被 K 拒绝（每种设置 40 次运行的平均）。")
    rejc_ = [q_ for q_ in cd.J("results/analysis-mechanism/calls-office-confirm.json") if q_["group"] == "D1-K8" and q_["kind"] == "depth"]  # delegation calls of subagents that the depth limit rejected (scripts/log_extra.py calls)
    rejc = {"n": len(rejc_), "runs": len({q_["run"] for q_ in rejc_}), "chars": st.mean(q_["new_chars"] for q_ in rejc_), "same": sum(1 for q_ in rejc_ if q_["repeat"] >= 0.8)}
    assert rejc["n"] == 302 and rejc["runs"] == 39 and 1900 < rejc["chars"] < 2000 and rejc["same"] < 10 and abs(rejc["n"] / 40 - rj8["depth"]) < 0.2
    half_ = round(m_rej) / m_calls
    assert 0.48 < half_ < 0.52
    d.add(f"- 默认下每次运行开出 {rnd(made8)} 个，另有 {rnd(rj8['depth'])} 次调用被深度上限拒绝。放开到深度 2，开出 {rnd(made('office-confirm', 'D2-K8'))} 个，K=8 开始不够用（每次运行 {rnd(mrj['office-confirm']['D2-K8']['cap'])} 次调用被 K 拒绝）。",
          f"- 全部运行合起来，开 subagent 的调用有一半被上限拒绝（{m_calls:,} 次里 {round(m_rej):,} 次，含把 K 调小的各组）：工具说明里不写上限，模型被拒绝了才知道。"
          "这些调用本身花的钱很少，不到全部模型费的 2%。",
          f"- 被深度上限拒绝的调用不是重复劳动：办公报告题默认组 {rejc['runs']} 次运行里的 {rejc['n']} 次这样的调用，任务说明平均约 {round(rejc['chars'], -2):,.0f} 字，"
          f"是 subagent 把自己那一块再拆小（比如负责行前准备的 subagent 想再开三个，分别查支付方式、法规和保险、实用信息）；和它自己接到的任务大体相同的不到 10 次。", "")
    d.place("fig:levels", "办公报告题：放开深度和 K 以后，每一层开了多少 subagent（每次运行的平均数）。K 是各层合起来数的。")
    d.add(f"- 只放开 K 不放开深度，开的个数不变。深度 2 时 K=8 经常用满（{d2_full}/{op['D2-K8']['runs']} 次同时活着的到了 8 个）；第 3 层要把 K 放到 64 才开得多，这就是旧默认下的三层递归。", "")

    # ---- 4. K
    d.add("### 结果 4：K（说法 1）", "")
    d.tbl("k-matrix", "K 的每个取值和 K=8 比（深度都是 1）：哪些任务上测出了更好，哪些测出了更差；没列出的都是没测出差别。"
          "办公报告题的 K=1、2、4 做过两批，用两批合起来的数；读代码题按事前写定的算法，和小编程题三道题一起算。各任务的数和区间在{tab:limits-ci}。", [
        ["取值", "退出时崩溃", "测出更好的", "测出更差的"]] + [frow(f"K={v_}", FK[v_], "没有") for v_ in (1, 2, 4, 16, 64)])
    assert not ce.strong(kq("xl", 4, "t")) and kq("xl", 4, "t")["lo"] < 1 < kq("xl", 4, "t")["hi"]
    assert 0.5 < kc_rule[2][0] < kc_rule[2][-1] < 0.85 and 0.35 < kc_rule[1][0] < kc_rule[1][-1] < 0.7 and rk("code", 2)["lo"] < -5 and rk("code", 2)["hi"] > 0
    d.add("- 没有一个取值只有好处。K=1、2、4 都更省钱，也都让大型编码题在题面要求不复核时更慢；K=1 还让办公报告题少写对。K=16、64 没有测出任何好处。所以 K 保持 8。",
          "- K=4 是比 8 小的取值里代价最小的：只在大型编码题不复核时更慢，原题面下没测出（" + xci(kq("xl", 4, "t")) + "）。它是费用和等待时间的取舍，下面单独画出来。",
          f"- 这些对比多数只有 10–40 对。K=16、64 的时间估计值在 {rnd(min(tk_), 2)}–{rnd(max(tk_), 2)} 倍之间，区间宽到 0.74–1.42 倍：快慢差三成以内，这次测不出。", "")
    # K = 4 against K = 8, task by task: the one value below 8 that fails on a single count
    w4 = sorted(q_["est"] for q_ in (free["cmp"]["K4"]["all_written_s"], xl["cmp"]["NK4"]["all_written_s"], xl["cmp"]["K4"]["all_written_s"]))  # time until every file is written
    save4 = sorted(1 - rk(k_, 4, "c")["est"] for k_ in ("free", "xl", "xln"))
    rev4 = {g_: xm[g_]["answer"] - xm[g_]["written"] for g_ in ("W-D1-K4", "W-D1-K8")}  # minutes between the last file and the final answer, original prompt
    assert all(q_["lo"] > 1 for q_ in (free["cmp"]["K4"]["all_written_s"], xl["cmp"]["NK4"]["all_written_s"], xl["cmp"]["K4"]["all_written_s"])) and all(rk(k_, 4, "c")["hi"] < 1 for k_ in ("free", "xl", "xln"))
    assert all(20 < v_ < 26 for v_ in rev4.values()) and 4.5 < xm["W-D1-K4"]["review"] < 5.5 and 9.5 < xm["W-D1-K8"]["review"] < 11 and (EXP / NEW / "k4-by-task.png").exists()
    assert all(not ce.strong(rk(k_, 4, m_)) for k_ in ("office", "ws", "drb2", "code") for m_ in "ct") and all(qstate(ce.rule_cells(LK[k_])[4], k_) == "ok" for k_ in ("office", "ws", "drb2", "code"))
    d.add(f"![]({NEW}/k4-by-task.png)", "",
          "图：K=4 和 K=8 比，一行一种任务。从左到右：两种设置各开几个 subagent、质量之差、费用倍数、文件写完的时间倍数（只有写代码的任务有）、到最终回答的时间倍数；横线是 95% 区间。", "")
    d.add(f"- 调研类任务和读代码题：K=4 开的个数和 K=8 差不多（三四个），质量、费用、时间都没测出差别。K=4 时有调用被 K 拒绝的运行，办公报告题 {capped4['office-confirm'][0]}/{capped4['office-confirm'][1]}，"
          f"评测集报告题 {capped4['drb2-k4'][0]}/{capped4['drb2-k4'][1]}，评测集填表题 {capped4['ws-k4'][0]}/{capped4['ws-k4'][1]}。调研类任务的费用，降到 4 省不了；降到 1、2 能省（{rnd(kc_rule[2][0], 2)}–{rnd(kc_rule[2][-1], 2)} 倍和更低），K=1 在办公报告题上少写对。",
          f"- 能拆成很多块的编码任务（不限时 24 题、大型编码题）：K=4 开得少，钱省 {pct(save4[0])}–{pct(save4[-1])}；写代码那一段更慢，文件写完的时间是 K=8 的 {rnd(w4[0], 2)}–{rnd(w4[-1], 2)} 倍。",
          f"- 最后要多等多少，看写完以后还做不做别的。题面要求不复核时多等 {pct(rk('xln', 4, 't')['est'] - 1)}。默认（写完会复核）时没测出差别（{xci(kq('xl', 4, 't'))}）：复核自己要二十多分钟、各次差得远，"
          f"这时省下的钱主要来自少派了一半复核的 subagent（{rnd(xm['W-D1-K4']['review'], 0)} 个对 {rnd(xm['W-D1-K8']['review'], 0)} 个）。", "")
    d.place("tab:limits-ci", "K 的每个取值对同一批的 K=8（深度都是 1）：质量之差、费用倍数、时间倍数和 95% 区间。"
            "粗体是测出的差别（区间不含 0 或 1，校正以后仍然成立）。办公报告题按 63 条，括号里是全清单，K=1、2、4 是第一批和主要一批合起来的数；读代码题按事前写定的算法，和小编程题三道题一起算；限时 24 题只作参考。题面加了提示的各行，对照的 K=8 组也加了同样的提示。")
    tk_all = [ce.rule_cells(r_)[v_]["t"] for r_ in L["k"] for v_ in (16, 64) if r_["key"] != "wide" and v_ in ce.rule_cells(r_) and ce.rule_cells(r_)[v_]["t"] is not None]
    assert 0.73 < min(q_["lo"] for q_ in tk_all) < 0.75 and 1.41 < max(q_["hi"] for q_ in tk_all) < 1.43
    assert not any(ce.strong(rk(k_, 4, m_)) for k_ in ("office", "ws", "drb2") for m_ in "ct")
    d.add("- 调研类任务上 K=4 对 8：三种任务的质量、费用、时间都没测出差别，估计值都贴着 0 和 1。默认下这三种任务同时活着超过 4 个的运行是少数（{tab:behave}）。",
          f"- K=2：费用是 K=8 的 {rnd(kc_rule[2][0], 2)}–{rnd(kc_rule[2][-1], 2)} 倍。质量的估计值在办公报告题和读代码题上偏低（{sg(k2p['est'])}、{sg(rk('code', 2)['est'])}），都没测出；大型编码题不复核时用时 {rnd(kq('xln', 2, 't')['est'], 2)} 倍。",
          "- 不限时 24 题 K=64 的 10 次里有 2 次没有最终回答（其中 1 次进程非正常退出），没有算进时间。", "")
    d.place("fig:k-quality", "K 取不同值时的质量：比同一批里的 K=8 高或低多少。实心点显著，空心点不显著；浅绿带是 ±5 分（办公报告题 ±8 个百分点），只作参照。")
    assert kq("office", 64)["hi"] < 0 and kq("wide", 2)["hi"] < 0 and not ce.strong(kq("office", 64), True) and not ce.strong(kq("wide", 2), True)
    assert ce.strong(k1p) and ce.strong(k1pf) and ce.strong(kq("wide", 1), True)
    d.add(f"- 办公报告题的 K=1 是实心点：两批合起来按 63 条 {sg(k1p['est'])}，全清单 {sg(k1pf['est'])}，区间都不含 0。限时 24 题的 K=1（{sg(kq('wide', 1)['est'])}）也是实心点，带时限，只作参考。",
          "- 全清单的 K=64 和限时 24 题的 K=2 两个空心点，区间不含 0，和同批的几个对比一起校正以后不显著。", "")
    d.place("fig:k-time", "K 取不同值时用户等的时间：是同一批里 K=8 的几倍。")
    fkt_ = sorted(kq("free", v_, "t")["est"] for v_ in (1, 2, 4))
    assert all(kq("free", v_, "t")["lo"] < 1 < kq("free", v_, "t")["hi"] for v_ in (1, 2, 4)) and fkt_[-1] < 0.85
    assert rk("code", 1, "t")["lo"] > 1 and not ce.strong(rk("code", 1, "t"), True)
    d.add(f"- 用时随 K 变小而变长的是大型编码题不复核时（K=1、2、4 是 {rnd(kq('xln', 1, 't')['est'], 2)}、{rnd(kq('xln', 2, 't')['est'], 2)}、{rnd(kq('xln', 4, 't')['est'], 2)} 倍）；K=16 没有更快，这时模型同时最多只开十一二个。"
          f"读代码题和小编程题上 K=1 是 {xci(rk('code', 1, 't'))}，区间不含 1，和同批的几个对比一起校正以后不显著。",
          f"- 不限时 24 题上 K=1、2、4 的估计值是 {rnd(fkt_[0], 2)}–{rnd(fkt_[-1], 2)} 倍，区间含 1，没有测出 K 小了更慢。", "")
    d.place("fig:cost-k", "各任务一次运行的平均费用（元）随 K 怎么变，深度都是 1。深蓝色是默认，灰色是不开；加了提示的几组要和同一条短线上的 K=8 比。")
    d.add(f"- 费用跟着开的个数走：办公报告题 K=1、2 是 {m['D1-K1']['cost']:.1f}、{m['D1-K2']['cost']:.1f} 元，到 4 以后停在 {m['D1-K8']['cost']:.0f} 元上下；不限时 24 题和大型编码题上 K 从 1 到 16 一路在涨。", "")

    # ---- 5. depth
    d.add("### 结果 5：深度（说法 2）", "")
    crash_txt = lambda q_, w_: f"办公报告题 K=8：{q_['crash']}/{q_['runs']}；让进程等 subagent 以后 {w_['crash']}/{w_['runs']}"  # noqa: E731
    d.tbl("d-matrix", "深度的每个取值和深度 1 比（K 都是 8）：测出更好的、测出更差的；没列出的都是没测出差别。退出时崩溃是 DSH 的缺陷（结果 8）。各任务的数和区间在{tab:limits-ci-d}。", [
        ["取值", "退出时崩溃", "测出更好的", "测出更差的"],
        frow("不开", FD[0], "没有"), frow("深度 2", FD[2], crash_txt(rel_d2, rel_w[2])), frow("深度 3", FD[3], crash_txt(rel_d3, rel_w[3]))])
    p32leg = {"est": p32k8["legacy_est"], "lo": p32k8["legacy_lo"], "hi": p32k8["legacy_hi"]}
    assert p32leg["lo"] < 0 < p32leg["hi"] and abs(dq("office", 3, "c")["est"] - dq("office", 2, "c")["est"]) < 0.05
    leg_all_, hits_ = ce._hits()  # the 63 items fixed beforehand: how much of them the best group of each batch states correctly
    top63 = sorted(100 * max(st.mean(st.mean(hits_[b_][g_][k_]) for k_, v_ in leg_all_.items() if v_) for g_ in hits_[b_]) for b_ in hits_)
    never63 = sum(1 for k_, v_ in leg_all_.items() if v_ and max(st.mean(hits_[b_][g_][k_]) for b_ in hits_ for g_ in hits_[b_]) == 0)
    waitrows = [r_ for r_ in d2rows if r_["batch"] in ("wait2", "keep")]  # depth 2 against 1 in the two batches whose process waits for the subagents
    assert len(top63) == 3 and 86 < top63[0] < top63[-1] < 92 and never63 == 0 and len(waitrows) == 2 and all(r_["cost_lo"] > 1 and r_["legacy_lo"] < 0 < r_["legacy_hi"] for r_ in waitrows)
    assert 4 < pr["d2"]["price"] / pr["default"]["price"] < 5
    d.add(f"- 放开到深度 2 是小提升、贵一倍：办公报告题一次约 {m['D1-K8']['cost']:.0f} 元变成约 {m['D2-K8']['cost']:.0f} 元（{CN[len(d2rows)]}批合起来 {rnd(p2cost['est'], 2)} 倍，各批 {rnd(d2c_rng[0], 2)}–{rnd(d2c_rng[-1], 2)} 倍），"
          f"写对的事实多 {rnd(p2leg['est'], 0)}–{rnd(p2k8['est'], 0)} 个百分点（63 条 {ci(p2leg)}，全清单 {ci(p2k8)}）。每多写对一条事实，开 subagent 本身是 {rnd(pr['default']['price'], 2)} 元，再放开一层是 {rnd(pr['d2']['price'], 2)} 元。",
          f"- 63 条这把尺子在上面快到头了：默认已经写对 {rnd(lv63['D1-K8'])}%，三批里最好的组是 {rnd(top63[0], 0)}%–{rnd(top63[-1], 0)}%，所以深度 2 在 63 条上涨得少、在全清单上显著。两套数说的是同一件事。",
          f"- 退出时崩溃不算深度本身的代价，修掉以后账还是一样：进程等 subagent 的两批里，深度 2 的费用是 {'、'.join(rnd(r_['cost_ratio'], 2) for r_ in waitrows)} 倍，写对的事实 {'、'.join(sg(r_['legacy_est']) for r_ in waitrows)} 个百分点。"
          f"深度 3 和深度 2 花的一样多，没测出比深度 2 多写对（{ci(p32leg)}）。", "")
    d.place("tab:limits-ci-d", "深度的每个取值对同一批的深度 1（K 都是 8），读法同{tab:limits-ci}：粗体是测出的差别。“不开”各行是把默认对不开的对比反过来写；办公报告题的深度 2、3 是几批合起来的数，最后两行同时把 K 放到 64。")
    assert not ce.strong(dq("ws", 2, "c")) and not ce.strong(dq("xl", 2, "c")) and dq("free", 2, "c")["hi"] < 1
    d.add(f"- 变贵的是办公报告题、评测集报告题（{x(dq('drb2', 2, 'c'))}）和读代码题（{x(dq('code', 2, 'c'))}）。评测集填表题和大型编码题没测出变贵，不限时 24 题略便宜（{x(dq('free', 2, 'c'))}）。",
          f"- 相当于旧默认的设置（深度 3、K=64）：费用是现在默认的 {rnd(od['cost']['est'])} 倍，写对的事实 {ci(lg['old'])}，没测出增加。",
          f"- 深度 2 测出更慢的两处（读代码题、大型编码题不复核），区间下限都只到 1.01，换一种算法就不成立（{{tab:sens}}）；办公报告题四批合起来是 {xci(p2time)}，没测出。"
          "不开 subagent 时办公报告题更快、质量更差，大型编码题不复核时更慢。", "")
    d.place("fig:cost-d", "各任务一次运行的平均费用（元）随深度怎么变。每一格只画同一批跑的几组；深蓝色是默认。")
    d.add(f"- 办公报告题放开到深度 2 或 3，一次多花 {rnd(more8[0])}–{rnd(more8[1])} 元；K 也放到 64，多花 {more64[0]:.0f}–{more64[1]:.0f} 元。大型编码题和不限时 24 题的费用不随深度涨。", "")
    d.place("fig:d-quality", "深度取不同值时的质量：比同一批里的深度 1 高或低多少。读法同{fig:k-quality}。")
    d.add(f"- 放开深度以后，没有一种任务的质量测出变差。图里全清单的深度 2（{sg(p2k8['est'])}）是实心点，按 63 条是 {sg(p2leg['est'])}、区间含 0。",
          f"- 不在图里的不限时 24 题多 {rnd(dq('free', 2)['est'])} 分（各组都接近满分），是唯一测出提高的。", "")
    d.place("fig:d-time", "深度取不同值时用户等的时间：是同一批里深度 1 的几倍。限时 24 题不比时间。")
    d.add("- 深度 2 没有让任何一种任务显著更快。", "")
    d.place("fig:tree-depth2", f"深度 2 下的一次运行（旅行攻略题，开的 subagent 数是这一组的中位数）：主 agent 开了 {len(t2k1)} 个 subagent，其中一个又开了 {len(t2k2)} 个，同时活着的到了 8 个。")
    d.add(f"- 钱花在多出来的一层上：第 1 层的 subagent 有的又往下开，搜索请求是默认的 {rnd(srch2['est'], 1)} 倍。", "")

    # ---- 6. time
    d.add("### 结果 6：时间（说法 3）", "")
    d.place("fig:pkg", "大型编码题各组：到最终回答的时间、模型费、开的 subagent 数（橙色是写完以后派去复核的）。先看第一行：默认 28 分钟，不开 22 分钟，加不复核提示的 K=8 是 10 分钟。")
    h1t = h1["seconds"]
    fw_, xw_ = free["cmp"]["NC"]["all_written_s"], xl["cmp"]["NC"]["all_written_s"]
    fa_, xa_ = free["cmp"]["NC"]["answer_s"], xl["cmp"]["NC"]["answer_s"]
    assert h1t["lo"] >= 1 and fw_["hi"] < 1 and xw_["hi"] < 1 and fa_["lo"] < 1 < fa_["hi"] and xa_["lo"] < 1 < xa_["hi"] and 0.55 < save_cost < 0.65 and 0.6 < save_time < 0.72
    assert 27.5 < xm["W-D1-K8"]["answer"] < 29 and 21 < xm["D0"]["answer"] < 22.5 and 9 < xm["W-N-D1-K8"]["answer"] < 10.5
    assert 1.15 < t3[0] < t3[-1] < 1.45 and h1["search_aux"]["lo"] > 3
    d.add(f"- 调研类任务没有更快：办公报告题默认比不开慢（{xci(h1t)}；三批是 {rnd(t3[0], 2)}–{rnd(t3[-1], 2)} 倍），两个评测集没测出差别。并行省下的时间，模型拿去多查了：搜索请求是不开的 {rnd(h1['search_aux']['est'], 1)} 倍。",
          f"- 不限时 24 题和大型编码题：文件写完得更早（是不开的 {x(fw_)} 和 {x(xw_)}），最终回答没有更早（{x(fa_)} 和 {x(xa_)}，这两个的区间含 1）。原因是复核：模型写完以后又派一批 subagent 去检查。",
          f"- 大型编码题去掉复核（题面加不复核提示），费用少 {pct(save_cost)}、时间少 {pct(save_time)}，代价是 {nrun} 次里 {nrun - npass} 次留下 1–{xl['failed_max']['W-N-D1-K8']} 个没通过的测试（3,737 个里；有复核时 {xpass['W-D1-K8'][0]} 次全过，不开 subagent 时 {xpass['D0'][1] - xpass['D0'][0]} 次留下 1–{xl['failed_max']['D0']} 个）。这时不开要等的时间是开 subagent 的 {rnd(dq('xln', 0, 't')['est'], 2)} 倍。", "")

    # ---- 7. where the additional facts come from
    d.add("### 结果 7：多写对靠什么（说法 4）", "")
    h4 = lambda label_, q_, none_: [label_, x(q_["search_aux"]), ci(q_["right_legacy_pct"]) if "right_legacy_pct" in q_ else ci(lg["more"]), x(q_["total_cost_peak"]), x(q_["answer_s"] if "answer_s" in q_ else q_["seconds"]), ci(none_)]  # noqa: E731
    d.tbl("h4", "办公报告题：不开 subagent 的几种做法和默认比。搜索请求、费用、时间是默认的几倍；“写对的事实”是和默认的差，单位是百分点，按 63 条。多查的三行各和同一批的默认比，最后一列是同一批里什么提示都不加的单 agent。", [
        ["做法", "搜索请求", "写对的事实", "费用", "时间", "同一批里不加提示的单 agent"],
        h4("单 agent，题面要求至少搜索 100 次、打开 100 个网页（多查 100/100）", fl["PRIM"], fnone["legacy"]),
        h4("单 agent，要求 150 次、250 个网页（多查 150/250）", dc["P150"], dnone["right_legacy_pct"]),
        h4("单 agent，要求 250 次、500 个网页（多查 250/500）", dc["P250"], dnone["right_legacy_pct"]),
        ["两份单 agent 报告合并成一份（两批合起来）", x(msr["M2"]), ci(mp2["legacy"]), x(mp2["cost"]), x(mp2["time"]), "—"],
        ["四份单 agent 报告合并成一份（两批合起来）", x(msr["M4"]), ci(mp4["legacy"]), x(mp4["cost"]), x(mp4["time"]), "—"]])
    assert mp4["legacy"]["lo"] > 0 and mp2["legacy"]["lo"] < 0 < mp2["legacy"]["hi"] and dl250["hi"] < 0 and lg["more"]["hi"] < 0 and 0.9 < msr["M4"] < 1.1
    assert dc["P150"]["right_legacy_pct"] is dl150 and dc["P250"]["right_legacy_pct"] is dl250 and dl150["lo"] < 0 < dl150["hi"]
    d.add(f"- 题面要求单 agent 多查：后两种提示把搜索请求提到了默认的水平，写对的事实比默认少 {rnd(-dl150['est'])} 和 {rnd(-dl250['est'])} 个百分点（前一个区间含 0）。"
          f"但这两组花在模型上的钱只有默认的 {rnd(dose_model[0]['est'], 2)} 和 {rnd(dose_model[1]['est'], 2)} 倍，逐个打开读的网页是默认的一到两成（图 18）：搜索量追平了，读进去的没有追平。"
          "所以“一个 agent 自己查够同样多能不能追上”这次没有检验成。",
          f"- K=1（一次只许一个 subagent 活着，平均先后开 {rnd(k1kids)} 个）落在不开和默认中间：比不开多写对 {ci(k1s['facts63'][0])}，默认比它再多 {ci(k1s['facts63'][1])}"
          f"（63 条，两步的区间都含 0；全清单是 {ci(k1s['facts_all'][0])} 和 {ci(k1s['facts_all'][1])}，都显著）。费用是不开的 {rnd(k1s['total_yuan'][0]['est'], 2)} 倍，用时 {xci(k1s['t_answer_s'][0])}。按估计值，好处的一半在一次只开一个时就有了，另一半来自同时开。",
          f"- 几个单 agent 各写一份再合并，和默认比：两份没有差别，四份不比默认少。四份合并两批合起来是 {ci(mp4['legacy'])}；分批是 {ci(mb4['a'])}（对照的默认组是前一天跑的，方案里写明只作描述）和 {ci(mb4['b'])}（同一批，区间含 0）。",
          f"- 合并那一步的题面要求“有来源的事实都保留”，默认的主 agent 没有被这样要求。和题面加了同样要求的默认比（全清单）：四份合并是 {ci(o['m4_vs_keep'])}（{o['m4_vs_keep']['n']} 对；旅行攻略题 {sg(m4k_task['o1-singapore-trip'])}，CPU 选型题 {sg(m4k_task['o2-server-cpu-report'])}），"
          f"两份合并是 {ci(m2k_)}（{m2k_['n']} 对），更差。所以说法 4 只对了一半。", "")
    d.place("fig:search", "办公报告题：每个点是一组运行的平均，横轴是每次运行的搜索请求数，纵轴是写对的事实占比（全清单）。直线按主要一批的六组拟合。")
    d.add("- 搜索请求越多，写对的越多。同样的搜索量，单 agent 多查的三组（黑点）落在线下面。几份报告合并的（⊕）画出来在线上面，但合并是不是更省搜索，这批数据定不了。",
          "- 各批的水平不一样（同时测 K=64 的那一批，默认组自己就在 77%），点只能和同一批的默认比；按 63 条下判断的差在{tab:h4} 和{tab:limits-ci-d}。", "")
    d.place("fig:dose", "办公报告题：单 agent 加多查 150/250、多查 250/500 的两组，和同一批的不开、默认比。五栏从上到下是写对的事实占比（全清单）、搜索请求数、打开的网页数、费用、时间。")
    d.add(f"- 多出来的是搜索请求和下载量，逐个打开来读的网页并没有多：两组用 web_fetch 打开的只有 {rnd(dpg['E-D0']['fetch'], 0)} 和 {rnd(dpg['N-D0']['fetch'], 0)} 个（默认 {rnd(dpg['D1-K8']['fetch'], 0)} 个），"
          f"模型改成写脚本成批下载、存到磁盘再检索（{rnd(dpg['E-D0']['saved'], 0)} 和 {rnd(dpg['N-D0']['saved'], 0)} 个）。",
          f"- 搜索量到了默认的水平时，单 agent 的费用是默认的 {rnd(dc['P150']['total_cost_peak']['est'], 2)} 倍（搜索费差不多，模型费不到一半），时间是 {rnd(dc['P150']['answer_s']['est'], 1)} 倍。",
          f"- 少写对的主要在旅行攻略题上（全清单少 {rnd(-bt1['P150']['est'])} 和 {rnd(-bt1['P250']['est'])} 个百分点）；CPU 选型题上的差区间含 0。", "")
    d.place("fig:merge-cover", "办公报告题：一份单 agent 报告写对多少条（全清单），两份、四份里至少有一份写对的有多少条，合并稿写对多少条。虚线是默认。")
    d.add(f"- 一份单 agent 报告平均写对 {mu['M2']['one']:.0f} 条；两份里至少有一份写对的是 {mu['M2']['union']:.0f} 条，四份是 {mu['M4']['union']:.0f} 条。合并稿写对 {mu['M2']['merged']:.0f} 和 {mu['M4']['merged']:.0f} 条，默认 {sa['total']['high']:.0f} 条。",
          f"- 合并这一步自己查得很少（一次平均 {st.mean(mgs):.0f} 个搜索请求）：多出来的事实是几个 agent 各自查到的不一样。", "")
    d.place("fig:price", "办公报告题：每多写对一条事实多花的钱（全清单，条）。上面七种做法和一次不开 subagent 的运行比，下面的在默认之上再加。")
    d.add(f"- 从不开出发，每多写对一条：两份合并 {rnd(pr['M2_none']['price'], 2)} 元，四份合并、K=1 和多查 100/100 约 {rnd(pr['more']['price'], 2)} 元，默认 {rnd(pr['default']['price'], 2)} 元。",
          f"- 在默认之上再加：题面要求把 subagent 查到的都写进报告是 {rnd(pr['keep']['price'], 2)} 元一条，放开到深度 2 是 {rnd(pr['d2']['price'], 2)} 元一条（多写对的区间含 0）。", "")
    d.place("fig:relay", "办公报告题：subagent 交回给主 agent 的消息里写对的事实，进了最终报告和没进的各有多少。")
    d.add(f"- 主 agent 汇总时丢得不多：交回的消息里写对的事实，只有 {pct(rl['share_range'][0])}–{pct(rl['share_range'][1])} 没进最终报告。深度 2 多查了没有多写对多少，不是主 agent 汇总这一步丢的（第 2 层交给第 1 层的那一步没有量）。", "")
    d.place("fig:senders", "办公报告题：subagent 交回的消息里写对的事实，只在一个 subagent 的消息里出现的和别的 subagent 也有的各多少条。")
    d.add(f"- 分头查到的东西很少重复：交回的写对的事实，{pct(min(v_['only_one_share'] for v_ in SD.values()))}–{pct(max(v_['only_one_share'] for v_ in SD.values()))} 只在一个 subagent 的消息里出现；"
          f"默认下各 agent 打开的网页只有 {pct(ovd['page_cross_share'])} 被两个以上的 agent 打开过。", "")

    # ---- 8. delivery
    d.add("### 结果 8：交付", "")
    d.place("fig:deliver", "办公报告题各种设置下运行是怎么结束的：红柱是退出时崩溃的运行占的比例，蓝柱是主 agent 结束时还有 subagent 没做完的运行占的比例。右边三组的进程等 subagent 做完再退出。")
    assert all(rel_k[v_]["early"] is not None for v_ in rel_k) and rel_k[8]["incomplete"] == 0 and rel_k[8]["early"] < 0.06 * rel_k[8]["runs"]  # holds with or without the told-limit batch
    d.add(f"- 深度不超过 1 的 {shallow_runs:,} 次运行没有一次退出时崩溃。办公报告题深度 2、3 在 K=8 下是 {rel_d2['crash']}/{rel_d2['runs']} 和 {rel_d3['crash']}/{rel_d3['runs']}，K=1、2、4 下，深度 2 是 {low4[2]['crash']}/{low4[2]['runs']}、深度 3 是 {low4[3]['crash']}/{low4[3]['runs']}；"
          f"读代码题深度 2、3 的 {deep_by['code'][1]} 次里 {deep_by['code'][0]} 次，小编程题 {deep_by['p4'][1]} 次里没有。崩溃的运行绝大多数已经交出报告、照常计分：办公报告题 K=8 的这 {runs23} 次里报告不完整的只有 {rel_d2['incomplete'] + rel_d3['incomplete']} 次。",
          f"- 让进程等 subagent 做完再退出，深度 2、3 的崩溃降到 {rel_w[2]['crash'] + rel_w[3]['crash']}/{rel_w[2]['runs'] + rel_w[3]['runs']}。",
          f"- 全部 {len(MT):,} 次运行按同一条规则分：正常结束 {ends['ok']:,} 次，到时限被停 {ends['timeout']} 次（限时题和 3 次填表题），退出时崩溃 {ends['crash_at_exit']} 次，"
          f"主 agent 最后一轮没有正常结束 {ends['no_answer']} 次，其余 {ends['nonzero_exit']} 次。没有正常结束的 {ends['no_answer']} 次里 {na_scored} 次交了东西、照常判了分；办公报告题主要一批里没有这样的运行，小编程题有 4 次（去掉以后的数在{{tab:sens}}）。",
          f"- 蓝柱是另一回事：主 agent 没等 subagent 做完就给出回答，那些 subagent 的活白做了。默认下 {rel_k[8]['early']}/{rel_k[8]['runs']} 次，报告都是完整的；题面要求把 subagent 查到的都写进报告时 {rel_keep['early']}/{rel_keep['runs']} 次，其中 {rel_keep['incomplete']} 次没交出完整报告。", "")

    # ---- 9. the limit written into the tool description (the batch office-told), when its analysis exists
    if TD:
        tq = lambda k_: tc[k_]["right_legacy_pct"]  # noqa: E731
        det = lambda c_, ref=0: (c_["hi"] < ref or c_["lo"] > ref) and (c_.get("holm") is None or c_["holm"] < 0.05)  # noqa: E731  (detected: the interval leaves out 0 / 1 and, in a corrected family, survives the correction)
        bold = lambda s_, c_, ref=0: f"**{s_}**" if det(c_, ref) else s_  # noqa: E731  (the main text's tables mark detected differences in bold)
        z = lambda c_: "0" if max(abs(c_["est"]), abs(c_["lo"]), abs(c_["hi"])) < 0.05 else (ci(c_) if abs(c_["est"]) >= 0.05 else f"0 [{sg(c_['lo'])}, {sg(c_['hi'])}]")  # noqa: E731
        qword = lambda c_: "没测出差别" if not det(c_) else ("测出更少" if c_["hi"] < 0 else "测出更多")  # noqa: E731
        rword = lambda c_: "没测出差别" if not det(c_, 1) else ("测出更低" if c_["hi"] < 1 else "测出更高")  # noqa: E731
        TG = (("D1-K2", "K=2"), ("T-D1-K2", "K=2，告知"), ("D1-K8", "K=8（默认）"), ("T-D1-K8", "K=8，告知"))
        TC = (("P1", "K=2：告知对不告知"), ("P2", "K=8：告知对不告知"), ("S1", "告知的 K=2 对 K=8"))
        told_cap = ("办公报告题：K=2 和 K=8（默认）各配工具说明里写明上限与否，每组 40 次（两道题各 20 次）。前四行是各组的均值；后三行是按题和第几次配对的差或倍数，括号里是 95% 区间，粗体是区间不含 0（倍数不含 1）的差别。"
                    "写对的事实按 63 条；开的 subagent 和被拒绝的调用按全部运行，其余按交出完整报告并判了分的运行。")
        told_rows = [["组或对比", "写对的事实（%）", "费用（元/次）", "到最终回答（分钟）", "被 K 拒绝（次/运行）", "开的 subagent"]] \
            + [[lb, rnd(tm[g]["right_legacy_pct"]), rnd(tm[g]["cost"], 2), rnd(tm[g]["minutes"]), rnd(tm[g]["cap_rejects"]), rnd(tm[g]["kids"])] for g, lb in TG] \
            + [[lb, bold(ci(tq(k_)), tq(k_)), bold(xci(tc[k_]["total_cost_peak"]), tc[k_]["total_cost_peak"], 1), bold(xci(tc[k_]["answer_s"]), tc[k_]["answer_s"], 1),
                bold(z(tc[k_]["capacity_rejects"]), tc[k_]["capacity_rejects"]), bold(z(tc[k_]["children"]), tc[k_]["children"])] for k_, lb in TC]
        told_fig_cap = "办公报告题：K=2 和 K=8 各配工具说明里写明上限与否，四样量的组均值和 95% 区间（写对的占比、费用、时间按交出完整报告并判了分的运行，被拒绝的调用按全部运行）。"
        s1q, s1c = tq("S1"), tc["S1"]["total_cost_peak"]
        within8 = lambda c_: "，区间在 ±8 个百分点以内" if abs(c_["lo"]) <= 8 and abs(c_["hi"]) <= 8 else ""  # noqa: E731
        inter_ = TD["extra"]["interaction"].get("right_legacy_pct")
        told_bullets = [
            f"- 告知以后 K=2 上被 K 拒绝的调用从每次 {rnd(tm['D1-K2']['cap_rejects'])} 次变成 {rnd(tm['T-D1-K2']['cap_rejects'])} 次（{'基本不再超出上限' if TR['beh2'] else '仍然超出'}）；"
            f"写对的事实{qword(tq('P1'))}（{ci(tq('P1'))}{within8(tq('P1'))}），费用{rword(tc['P1']['total_cost_peak'])}（{xci(tc['P1']['total_cost_peak'])}），时间{rword(tc['P1']['answer_s'])}（{xci(tc['P1']['answer_s'])}）。",
            f"- 默认值（K=8）下写进去：开的 subagent {qword(tc['P2']['children'])}（{z(tc['P2']['children'])} 个），写对的事实{qword(tq('P2'))}（{ci(tq('P2'))}{within8(tq('P2'))}），费用{rword(tc['P2']['total_cost_peak'])}（{xci(tc['P2']['total_cost_peak'])}）；"
            f"被深度上限拒绝的调用从每次 {rnd(tm['D1-K8']['depth_rejects'])} 次变成 {rnd(tm['T-D1-K8']['depth_rejects'])} 次（{ci(tc['P2']['depth_rejects'])}）。",
            (f"- 告知以后的 K=2 比默认少写对 {rnd(-s1q['est'])} 个百分点（{ci(s1q)}，次要对比，没校正），费用 {xci(s1c)}；" if s1q["hi"] < 0 else f"- 告知以后的 K=2 对默认：写对的 {ci(s1q)}，费用 {xci(s1c)}；")
            + f"K=2 告知前后是 {ci(tq('P1'))}，区间含 0" + (f"，告知的作用在两个 K 上的差 {ci(inter_)}" if inter_ else "") + "。这一批说明不了告知让 K=2 变好或变坏，能确定的是被 K 拒绝的调用没有了"
            + ("；K 的结论不用改。" if TR["case"] == "same" else "；K=1、2 的结论要看上限怎么告诉模型。" if TR["case"] == "changed" else "。") + "读法是开跑前写定的，各组的全部数在附录的细节四。"]
        d.add("### 结果 9：把上限告诉模型", "")
        d.tbl("told-main", told_cap, told_rows)
        d.add(*told_bullets, "")
        d.place("fig:told", told_fig_cap)
        # the same section on its own, for the page (inserted before "结果 9：结论稳不稳" without touching the rest): captions without numbers
        globals()["TOLD_SECTION_MD"] = "\n".join(["### 结果 9：把上限告诉模型", "", "表：" + told_cap, ""] + table(told_rows) + told_bullets + ["", f"![]({NEW}/told-limit.png)", "图：" + told_fig_cap, ""])

    # ---- 10 (9 while the told-limit batch is not in): how firm the conclusions are
    d.add(f"### 结果 {10 if TD else 9}：结论稳不稳", "")
    xde_ = sorted([xl["depth_hi"]["DE16"]["answer_s"]["est"], xl["depth_hi"]["DE64"]["answer_s"]["est"]])
    k64full = kq("office", 64)
    assert k64full["hi"] < 0 and k64full["lo"] < -QM("office") and qstate({"q": c3["C3a"]["score"]}, "code") == "ok" and qstate({"q": c3["C3c"]["score"]}, "code") == "ok" and tstate({"t": dq("xl", 2, "t")}) == "ok"
    assert fk1["lo"] < -5 and fk1["hi"] < 0 and qstate({"legacy": k4p}, "office") == "ok" and h1["right_pct"]["lo"] > 0
    assert -10 < leg["D1-K2"]["lo"] < -8 and leg["D1-K2"]["hi"] > 0 and qstate({"legacy": leg["D1-K1"]}, "office") == "open" and qstate({"legacy": leg["D1-K4"]}, "office") == "ok" and k1pf["hi"] < 0 and k4pf["lo"] > -8
    assert qstate({"q": kq("code", 1)}, "code") == "open" and qstate({"q": kq("code", 2)}, "code") == "open" and qstate({"q": kq("code", 4)}, "code") == "open" and qstate({"q": c3["C3b"]["score"]}, "code") == "open"
    d.tbl("sens", "换一种算法，结论变不变。每行先写正文用的算法和数，再写换成什么、换了以后是多少。", [
        ["结论（正文的算法）", "正文的数", "换成", "换了以后", "变不变"],
        ["开 subagent 让办公报告题多写对（主要一批，63 条）", ci(h1leg), "全清单", ci(h1["right_pct"]), "不变"],
        ["", "", f"{CN[len(h1l4)]}批合起来（63 条）", ci(h1pool), "不变"],
        ["", "", f"评分表总分（第一批；同一批按 63 条是 {sg(h1l4[0]['est'])}）", ci(rb["h1"]), "变：评分表测不出"],
        [f"深度 2 没测出让办公报告题多写对（{CN[len(d2rows)]}批合起来，63 条）", ci(p2leg), "全清单", ci(p2k8), "变：全清单下显著"],
        ["", "", "全清单，把批当成随机因素（区间按只有四批放宽）", ci(pw_d2f["hk"]), "变回区间含 0"],
        [f"K=1 让办公报告题少写对（两批合起来，63 条，{k1p['n']} 对）", ci(k1p), "只看主要一批（40 对）", ci(leg["D1-K1"]), "变：单批没测出"],
        ["", "", "全清单（两批合起来）", ci(k1pf), "不变"],
        ["", "", "两批各算各的，再等权平均", ci(pw_k1["eq"]), "区间的上端刚好到 0"],
        ["K=2、K=4 在办公报告题上没测出差别（两批合起来，63 条）", f"{ci(k2p)}；{ci(k4p)}", "只看主要一批", f"{ci(leg['D1-K2'])}；{ci(leg['D1-K4'])}", "不变"],
        ["K=64 在办公报告题上没测出差别（63 条）", ci(lg["k64"]), "全清单", ci(k64full), "区间不含 0，校正后不显著；这两组等于同一种设置跑了两遍，见表下"],
        ["K=1 在读代码题和小编程题上没测出差别（三道题一起算，事前写定的算法）", ci(c3["C3a"]["score"]), "只看两道读代码题；再把三个深度下的 K=1 都算上", f"{ci(kq('code', 1))}；{ci(fk1)}", "前一种不变；后一种变：更差（事后合并）"],
        ["K=2、K=4 在读代码题和小编程题上没测出差别（三道题一起算）", f"{ci(c3['C3b']['score'])}；{ci(c3['C3c']['score'])}", "只看两道读代码题", f"{ci(kq('code', 2))}；{ci(kq('code', 4))}", "不变"],
        ["K=1、2、4 在读代码题和小编程题上没测出差别（三道题一起算）", "见上两行", "去掉主 agent 最后一轮没有正常结束的运行所在的 1–2 对", f"{ci(c3fin[1])}；{ci(c3fin[2])}；{ci(c3fin[4])}", "不变：估计值更低，区间仍含 0"],
        ["K=4 让大型编码题变慢（不复核题面）", xci(kq("xln", 4, "t")), "原题面", xci(kq("xl", 4, "t")), "变：没测出"],
        ["深度 2 让大型编码题变慢（不复核题面）", xci(dq("xln", 2, "t")), "原题面；K=16、64 下的深度 2（不复核题面）", f"{xci(dq('xl', 2, 't'))}；{xci(de16_)}、{xci(de64_)}", "变：都没测出"],
        ["深度 2 让读代码题变慢", xci(dq("code", 2, "t")), "把每个请求按同一个模型速度重算时间", xci(code_d2_std), "变：没测出"],
        ["大型编码题原题面 K=4 的得分没测出差别", f"{sg(kq('xl', 4)['est'], 2)} 分（10 次里 4 次各留 1 个没过的测试）", "t 区间不含 0；按精确检验", f"p = {rnd(k4exact, 2)}", "正文按精确检验"]])
    d.tbl("reps", "办公报告题上同一个对比在几批里各做了一遍的结果，和合起来的数。写对的事实按 63 条，单位是百分点。各批用的是同两道题，一致说明能重复，不说明换题也成立。", [
        ["对比", "各批的结果", "合起来", "几批一致吗"],
        ["默认对不开：写对的事实", "、".join(sg(r_["est"]) for r_ in h1l4) + "（都显著）", ci(h1pool), "四批一致"],
        ["K=4 对 8：写对的事实", f"{ci(k4first)}、{ci(leg['D1-K4'])}", ci(k4p), "两批都没测出差别"],
        ["K=2 对 8：写对的事实", f"{ci(kfirst[2])}、{ci(leg['D1-K2'])}", ci(k2p), "两批都没测出差别"],
        ["K=1 对 8：写对的事实", f"{ci(k1first)}、{ci(leg['D1-K1'])}", ci(k1p), "方向一致；单批都含 0，合起来不含"],
        ["深度 2 对 1：费用", "、".join(x(r_["cost_ratio"]) for r_ in d2rows) + "（都显著）", xci(p2cost), "四批一致"],
        ["深度 2 对 1：写对的事实", "、".join(sg(r_["legacy_est"]) for r_ in d2rows) + "（都含 0）", ci(p2leg), "方向一致；合起来仍含 0"],
        ["深度 2 对 1：时间", "、".join(x(r_["time_ratio"]) for r_ in d2rows) + "（一批显著）", xci(p2time), "两批偏慢、两批持平；合起来区间含 1"],
        ["深度 2 退出时崩溃（K=8）", "、".join(f"{a_}/{b_}" for a_, b_ in crash_by), f"{rel_d2['crash']}/{rel_d2['runs']}", "三批一致"]])
    d.add("- 跨批合起来的数，批与批之间的方差估出来都是 0（各批的估计值相差在抽样误差以内），所以把批当成随机因素和现在的算法给出同样的估计值。但只有两到四批，批间方差本身估不准："
          f"“合起来才显著”的两处，K=1 的 {sg(k1p['est'])} 和深度 2 全清单的 {sg(p2k8['est'])}，换成更保守的算法区间都碰到或含 0。默认对不开的 {sg(h1pool['est'])} 怎么算都显著（{ci(pw_h1['hk'])}）。",
          "- 换算法以后，“两个默认值都不改”没有一处被推翻。会变的三处：K=1 在办公报告题上的损失单批测不出；大型编码题换回原题面，K=4 和深度 2 更慢都测不出；深度 2 的好处在全清单下显著，仍然是多写对 2–4 个百分点、费用近两倍。",
          "- 全清单里后补的 132 条是看过第一批报告以后整理的，参考的样本多数来自开 subagent 的组，所以以 63 条为准。",
          f"- 两个公开评测集和写代码的各题都只做过一批。重复跑本身的波动：办公报告题上 K=64 和 K=8 两组里 K 都没有拒绝过一次调用，等于同一种设置跑了两遍，{o['k64']['right_pct']['n']} 对的写对的事实仍差 {rnd(abs(lg['k64']['est']))} 个百分点。", "")

    # -------------------------------------------------------------------------------------------------- discussion
    d.sec("new:discussion")
    d.add("## 讨论", "")
    d.add("- **为什么 K 调大没用。** K 限的是同时活着的个数，调研类任务上模型自己只开三四个。调用会被 K 拒绝的是能拆成十几块的编码任务：K 小了文件写得慢，要等多久还看写完以后复核不复核。",
          f"- **为什么放开深度主要是多花钱。** 多出来的一层把搜索量提到 {rnd(srch2['est'], 1)} 倍，写对的事实只多 2–4 个百分点。多查了为什么没有多写对多少，这次没有测；只知道不是主 agent 汇总这一步丢的（结果 7）。",
          "- **上限不告诉模型。** 工具说明里不写上限，到了深度上限的 subagent，工具列表里仍然有开 subagent 的工具，所以开 subagent 的调用有一半被拒绝（结果 3）。这些调用本身花的钱很少；" + (f"把上限写进工具说明以后，K=2 上被拒的调用从每次 {rnd(tm['D1-K2']['cap_rejects'])} 次变成 {rnd(tm['T-D1-K2']['cap_rejects'])} 次，写对的事实{TR['q']['P1']}、费用和时间{'有变化' if TR['cost']['P1'] or TR['time']['P1'] else '没测出变化'}；默认值下{'费用 ' + x(tc['P2']['total_cost_peak']) if TR['p2'] != 'none' else '开的数量、写对的事实、费用都没测出变化'}，被深度上限拒绝的调用从每次 {rnd(tm['D1-K8']['depth_rejects'])} 次变成 {rnd(tm['T-D1-K8']['depth_rejects'])} 次（结果 9）。" if TD else "把上限写进工具说明会不会改变模型的做法，正在测。"),
          f"- **和预想不一样的两处。** 不限时的题上开 subagent 没有更快（复核把省下的时间用掉了）；两份单 agent 报告合并就和默认没有差别（默认没有被要求把查到的都写进去；和加了这个要求的默认比，两份合并少 {rnd(-m2k_['est'], 0)} 个百分点）。",
          "- **和别人的结果。** 上限调大没测出好处，和 ArcticSwarm（arXiv 2609.01870；同时运行的 subagent 上限从 8 调到 48，准确率在波动以内）一致。"
          "放开深度：SAIGE（arXiv 2609.19759 提出的一种多 agent 协作办法）把最大深度从 1 调到 3，得分是降的；这里是没测出值得这个价钱的好处。"
          "单 agent 重复多次再合并：ArcticSwarm 的题一题只有一个答案，只能投票，结果不如多 agent；这里合并的是报告，写对的不比默认少。产品的默认值两种都有：Codex CLI 和 Gemini CLI 的 subagent 不能再往下开，Claude Code 现在默认允许三层（2026 年改过两次，没有公布测量）；这里的结果支持前一种。各项的数在附录的{tab:related}。",
          f"- **数据提出的问题比“默认值取几”大。** 同一个 K，在调研类任务上从不起作用（{res_runs} 次默认运行没有一次碰到 8，却有 {dep_runs3} 次被深度上限拒绝），在能拆成很多块的编码任务上每次都起作用。"
          "按任务类型设上限，或者把上限告诉模型让它自己安排，比改这两个数更对症；告知上限的一批（结果 9）只是第一步。",
          "- **局限。** 一个模型、一个推理强度、一个 DSH 版本、命令行一次性运行：“K 调大没用”靠的是这个模型在调研类任务上一次只开三四个，换模型可能不一样。"
          "重复跑的办公报告题只有两道，区间只反映同一道题重复跑的波动。质量量的是事实写对了多少，由模型判分，还没有人工核对。"
          "代码类任务上 K 和深度的结论是在题面加了并行提示或不复核提示时得到的，用户不会这样写题面。K 的结论只对现在的实现成立（工具说明里不写上限，超出上限的调用被拒绝）。"
          "别人的结果里深度有用的两种情形（执行的模型弱、任务本身一层套一层；输入远超一个上下文、工作量比输入涨得快），这次的任务都不属于：“深度保持 1”只对一个上下文装得下的日常任务成立。",
          "- **下一步。** " + ("到了上限排队等空位（不拒绝）的做法；告知上限只在办公报告题的 K=2、8 上测过，K=1 和代码类任务没有测；" if TD else "把上限写进工具说明的实验（在跑）；") + "在第一遍错得多的任务上比有没有复核；读代码题上补测 K=4。运行中发现的 DSH 缺陷和每条结论会被什么结果推翻，在附录的“运行中发现的 DSH 缺陷”和“适用范围、会推翻结论的结果和下一步”两节。", "")
    # ------------------------------------------------------------------------- the appendix: what stood before
    d.sec("new:app-head")
    d.p("附录按这个顺序：名字对照；各批实验；各条判断规则是什么时候写的；任务、提示和判断用词；方法的细节（三小节）；结果的细节（细节一到八，带各批的名字和全部数字）；"
        "和预想不一样的地方、DSH 缺陷、别人的结果、会推翻结论的结果；各设置下运行是怎么结束的；分任务结果表；事前写定的主要对比；方法补充；材料和脚本在哪。")
    d.p("附录的表沿用各批当时的四种判断用词（显著、校正后不显著、没有差别、没测出差别，定义在“任务、提示和判断用词”一节），和正文按统一框架给的三种判断不是一套；两边不一致的地方以正文为准。")
    d.add("### 名字对照", "")
    d.sec("new:app-readings")
    d.add("### 各条判断规则是什么时候写的", "")
    d.p("方法里的判断框架是写报告时定的。各批当时写下的判断规则（方案里叫读法）列在下面两张表里：什么时候写的、写的时候看过哪些结果、按它得到什么。")
    d.place("tab:k-readings")
    d.place("tab:d-readings")
    d.sec("new:app-materials")
    d.add("### 材料和脚本在哪", "")
    d.add("- 实验目录在张子雅的电脑上：~/harness/subagent-experiment/。方案（每一批开跑前写的设计、读法和预想）是其中的 experiment-plan-dsec-v2.md。",
          "- 题目、隐藏测试和加在题面末尾的提示句在 tasks/；改上限和改进程行为的补丁在 patches/。",
          "- 跑批、判分、统计和生成这份报告的脚本在 scripts/：跑批 dsec_matrix.py（早先各批）、dsec_matrix_v4.py 和 dsec_matrix_v5.py，判分 judge_facts.py、ws_score.py、drb2_score.py，配对统计 paired_stats.py，生成报告 build_clean.py。",
          "- 每次运行的原始会话日志在开发机上：/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp/results/runs/，一批一个目录。各批的运行表和统计结果在实验目录的 results/ 下。",
          "- 可以直接再用的：两份事实清单（195 条，带出处和判定规则）和判分提示词；大型编码题的规格和隐藏测试；24 道小题；16 步串行题。", "")
    d.at("### 实验一览")
    d.p("附录里还用到两个合称：两个公开评测集指评测集填表题和评测集报告题；对照题指限时 24 题和 16 步串行题，一道特意适合分给几个 subagent 同时做，一道特意没法同时做。")
    d.at("### 四、K")
    d.place("fig:k-cost", "K 取不同值时一次任务的费用：是同一批里 K=8 的几倍。")
    d.at("### 五、深度")
    d.place("fig:d-cost", "深度取不同值时一次任务的费用：是同一批里深度 1 的几倍。“不开”是不给开 subagent 的工具。")

    def detail(lines_: list) -> list:
        """A result section of the earlier text as a detail section of the appendix."""
        num_, _, name_ = lines_[0][4:].partition("、")
        assert lines_[0].startswith("### ") and num_ in "一二三四五六七八" and name_
        return [f"### 细节{num_}：{name_}"] + lines_[1:]

    def demote(lines_: list) -> list:
        assert lines_[0].startswith("## ")
        return ["#" + lines_[0]] + lines_[1:]
    retitle = lambda title_: (lambda lines_: [f"### {title_}"] + lines_[1:])  # noqa: E731
    old_results = [n_ for n_ in d.order if re.match(r"### [一二三四五六七八]、", n_)]
    old_talk = ["## 和事前预想不一样的地方", "## 运行中发现的 DSH 缺陷", "## 和别人的结果对照", "## 适用范围、会推翻结论的结果和下一步"]
    assert len(old_results) == 8
    order = (["front", "new:abstract", "## 背景", "new:conclusion", "new:claims", "new:method", "new:results", "new:discussion",
              "## 附录", "new:app-head", "old:names", "### 各批实验", "new:app-readings", "### 实验一览",
              "### 运行环境和 subagent 的机制", "### 测了哪些取值", "### 指标和读法"] + old_results + old_talk
             + ["### 各设置下运行是怎么结束的", "### 分任务结果表", "### 事前写定的主要对比", "### 方法补充", "new:app-materials", "old:pointer"])
    dropped = [n_ for n_ in d.order if n_ not in order]
    assert dropped == ["## 结论", "### 怎么判断一个取值", "### K 取不同值的结果", "### 深度取不同值的结果", "## 实验怎么做的", "## 结果", "### K、深度各取值对默认的差和区间"], dropped
    left_ = sorted(ln_[1:] for n_ in dropped for ln_ in d.sections[n_] if ln_.startswith("\x00"))  # blocks that leave the text with their section
    assert left_ == ["tab:d-rule", "tab:k-rule"], left_
    change = {n_: detail for n_ in old_results}
    change.update({n_: demote for n_ in old_talk})
    change["### 实验一览"] = retitle("任务、提示和判断用词")
    change["front"] = lambda lines_: ["# Subagent 的两个上限：K 调大没用、调小有代价，放开深度主要是多花钱", ""]
    told_words = {"tab:told-main": "结果 9 的表", "fig:told": "结果 9 的图", "tab:told": "结果 9 的表", "tab:told-cmp": "结果 9 的表"}
    return d.text(order, change, unnumbered={k_: v_ for k_, v_ in told_words.items() if k_ in d.blocks} if PAGE_NUMBERING else None)


def wiki_parts(text: str) -> str:
    """The report for the wiki page「Subagent问题」, which has its own title and keeps its own sections on judging, the task
    prompts and the rubrics after this text: everything but the title line and the closing pointer to that page."""
    body = text.split("\n", 1)[1].lstrip("\n")
    body, pointer, rest = body.rpartition("\n" + POINTER)
    assert body.startswith("## 摘要") and "\n## 背景\n" in body and pointer and not rest.strip() and "### 方法补充" in body
    return body.rstrip("\n") + "\n"


PAGE_NUMBERING = False  # set by --page-numbering


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=EXP / "report-clean-2026-10-06.md")
    ap.add_argument("--wiki-body", type=Path, help="also write the text for the wiki page that keeps its own sections on judging, prompts and rubrics")
    ap.add_argument("--wiki-from", help="start the wiki body at this second-level heading (the page keeps what stands before it)")
    ap.add_argument("--wiki-abstract", type=Path, help="also write the abstract on its own (it goes to the top of the wiki page: scripts/feishu_top_block.py)")
    ap.add_argument("--told-section", type=Path, help="also write the section on the told-limit batch on its own, captions without numbers (goes into the page with scripts/feishu_insert_section.py)")
    ap.add_argument("--page-numbering", action="store_true", help="number figures and tables the way the wiki page does: the tables and the figure of the told-limit batch carry no number")
    a = ap.parse_args()
    globals()["PAGE_NUMBERING"] = a.page_numbering
    text = build()
    a.out.write_text(text, encoding="utf-8")
    if a.told_section:
        assert "TOLD_SECTION_MD" in globals(), "the told-limit batch has no analysis yet (results/analysis-facts-told/stats.json)"
        a.told_section.write_text(TOLD_SECTION_MD + "\n", encoding="utf-8")
        print(f"told section: {a.told_section.name}, {len(TOLD_SECTION_MD)} characters")
    main_part = text.split("\n## 附录\n")[0]
    prose = lambda t: sum(len(ln) for ln in t.splitlines() if ln and not ln.startswith(("|", "![")))  # noqa: E731
    print(f"wrote {a.out.name}: {len(text)} characters; before the appendix {len(main_part)} ({prose(main_part)} outside tables); "
          f"{text.count('![](')} figures, {sum(1 for ln in text.splitlines() if ln.startswith('表 '))} tables")
    if a.wiki_body:
        wb = wiki_parts(text)
        if a.wiki_from:
            assert wb.count(f"\n## {a.wiki_from}\n") == 1, a.wiki_from
            wb = wb[wb.index(f"\n## {a.wiki_from}\n") + 1:]
        a.wiki_body.write_text(wb, encoding="utf-8")
        print(f"wiki body: {len(wb)} characters, {wb.count('![](')} figures")
    if a.wiki_abstract:
        ab = text[text.index("\n## 摘要\n") + 1:text.index("\n## 背景\n") + 1]
        assert ab.startswith("## 摘要") and "|" not in ab and "![" not in ab
        a.wiki_abstract.write_text(ab, encoding="utf-8")
        print(f"abstract: {sum(len(ln) for ln in ab.splitlines()[1:])} characters")


if __name__ == "__main__":
    main()
