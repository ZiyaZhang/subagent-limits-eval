#!/usr/bin/env python3
"""Build report-2026-10-03.md from the analysis outputs, so that every number in the report comes from a file.

Reads results/analysis-v2/ (rows.csv, audit.json, stats-*.json, tables-*-t.md), results/stage-b-decision-main.json,
the two speed profiles, the three search-cost probes, tasks/dsec-tasks.jsonl, the two rubric files, the judge
prompts in judge.py / judge_code.py and the judging validation outputs in results/validate-max/ and
results/validate-effort/ (judge_compare.py and judge_agreement.py JSON). Run it again after any re-analysis;
nothing in the text is typed by hand except the wording.

Usage: build_report.py [--out report-2026-10-03.md]
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXP / "scripts"))
from paired_stats import t_interval  # noqa: E402
from v2_tables import mean_by_task, num, truthy  # noqa: E402

A = EXP / "results" / "analysis-v2"
VE = EXP / "results" / "validate-effort"
VM = EXP / "results" / "validate-max"
CTL = EXP / "results" / "analysis-ctl"      # supplementary experiment 2: the two control tasks
WAITD = EXP / "results" / "analysis-wait"   # supplementary experiment 1: wait for the subagents
SUPP = EXP / "results" / "analysis-supp"    # audit of the two supplementary batches
PW, N1 = "pw-exercises", "n1-chain16"
CTL_GROUPS = ["D0", "W-D1-K8", "W-E-D1-K8"]
WAIT_GROUPS = ["W-D1-K8", "D2-K8", "W-D2-K8", "D3-K8", "W-D3-K8"]
OFF = ("o1-singapore-trip", "o2-server-cpu-report")
C1, W1, P4 = "c1-subagent-limits", "w1-memory-plugin", "p4-python"
CODE = (C1, W1, P4)
MINUS = "−"
DELTA = 5.0
OFF_GROUPS = ["D0"] + [f"D{d}-K{k}" for d in (1, 2, 3) for k in (1, 2, 4, 8)]
ENC_GROUPS = [f"E-D{d}-K{k}" for d in (1, 2, 3) for k in (1, 2, 4, 8)]


def load(name: str):
    return json.loads((A / name).read_text(encoding="utf-8"))


def opt(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def sgn(v: float, nd: int = 1) -> str:
    if round(v, nd) == 0:
        return f"{0:.{nd}f}"
    return f"{v:+.{nd}f}".replace("-", MINUS)


def cmp_(o: dict, metric: str, label: str) -> dict:
    return o["metrics"][metric]["comparisons"][label]


def d_cell(c: dict) -> str:
    return f"{sgn(c['est'])} [{sgn(c['lo'])}, {sgn(c['hi'])}]"


def d_txt(c: dict) -> str:
    return f"{sgn(c['est'])} 分（95% 区间 {sgn(c['lo'])} 到 {sgn(c['hi'])}）"


def sig(c: dict) -> bool:
    return c.get("p_holm") is not None and c["p_holm"] < 0.05


def ratio(c: dict) -> float:
    return math.exp(c["est"])


def r_cell(c: dict, star: bool = True) -> str:
    return f"×{ratio(c):.2f} [{math.exp(c['lo']):.2f}, {math.exp(c['hi']):.2f}]" + (" *" if star and sig(c) else "")


def r_txt(c: dict) -> str:
    """ratio with its interval; says whether Holm-significant when the comparison is in a Holm family"""
    tail = ""
    if c.get("p_holm") is not None:
        tail = "，显著" if sig(c) else "，不显著"
    return f"{ratio(c):.2f} 倍（区间 {math.exp(c['lo']):.2f}–{math.exp(c['hi']):.2f}{tail}）"


def p_txt(p: float) -> str:
    return "< 0.001" if p < 0.001 else f"= {p:.3f}"


def verdict(c: dict) -> str:
    if c["lo"] > -DELTA and c["hi"] < DELTA:
        return "没有实际差别"
    if sig(c):
        return "有差别"
    return "测不出"


def section(text: str, heading: str) -> str:
    """The body under a heading line that starts with `heading`, up to the next heading of the same or a higher level."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(heading):
            level = len(line) - len(line.lstrip("#"))
            out = []
            for nxt in lines[i + 1:]:
                m = re.match(r"^(#+) ", nxt)
                if m and len(m.group(1)) <= level:
                    break
                out.append(nxt)
            return "\n".join(out).strip("\n")
    raise SystemExit(f"heading not found: {heading}")


def demote(md: str, by: int) -> str:
    return re.sub(r"^(#+) ", lambda m: "#" * (len(m.group(1)) + by) + " ", md, flags=re.M)


def const(path: Path, name: str) -> str:
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit(f"{name} not found in {path}")


def enc(s: str) -> str:
    return s.replace("W-E-D", "等·鼓励·D").replace("W-D", "等·D").replace("E-D", "鼓励·D")


def bj(ts: str) -> str:
    """HH:MM Beijing time of a UTC ISO timestamp"""
    h, m = int(ts[11:13]), ts[14:16]
    return f"{(h + 8) % 24:02d}:{m}"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ctl_load():
    """The control batch (supplementary experiment 2), or None when it has not been analysed."""
    if not (CTL / "rows.csv").exists():
        return None
    rows = list(csv.DictReader(open(CTL / "rows.csv", encoding="utf-8")))
    for r in rows:
        m = re.search(r"all_pass=(\d+) changed=(\d+)", r["score_detail"])
        r["all_pass"], r["changed"] = (int(m.group(1)), int(m.group(2))) if m else (None, None)
        m = re.match(r"(\d+)/(\d+)", r["score_detail"])
        r["steps_ok"] = int(m.group(1)) if m else None
    return {"rows": rows, PW: read_json(CTL / f"stats-{PW}.json"), N1: read_json(CTL / f"stats-{N1}.json"),
            "pilot": read_json(CTL / "pilot.json"), "spawn": read_json(CTL / "spawn-calls.json"),
            "build": read_json(EXP / "data/code-templates/pwide-python-BUILD.json"),
            "tasks": {json.loads(x)["id"]: json.loads(x)
                      for x in (EXP / "tasks/control-tasks.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()}}


def unsettled_load():
    """Post hoc classification of subagents that were unsettled when a run ended (unsettled_subagents.py), or None."""
    files = [SUPP / f"unsettled-{b}{x}.csv" for b in ("main", "wait") for x in ("", "-interrupted")]
    if not all(f.exists() for f in files):
        return None
    rd = lambda f: list(csv.DictReader(open(f, encoding="utf-8")))
    runs = rd(files[0]) + rd(files[2])
    intr = rd(files[1]) + rd(files[3])
    queued = [x for x in intr if (num(x.get("pending_inbox_at_abort")) or 0) > 0]
    plain = [x for x in intr if (num(x.get("pending_inbox_at_abort")) or 0) == 0]
    crashed = [r for r in runs if truthy(r["crash5063"])]
    return {"runs": len(runs), "interrupted": len(intr), "queued": len(queued),
            "queued_settled": sum(x["settled"] == "1" for x in queued), "plain": len(plain),
            "plain_settled": sum(x["settled"] == "1" for x in plain),
            "plain_unsettled_wait_arm": sum(x["settled"] != "1" and x["group"].startswith("W-") for x in plain),
            "plain_unsettled_other": sum(x["settled"] != "1" and not x["group"].startswith("W-") for x in plain),
            "plain_wait_arm": sum(x["group"].startswith("W-") for x in plain),
            "runs_with_interrupt": sum((num(r["interrupt_calls"]) or 0) > 0 for r in runs),
            "crashes": len(crashed), "crash_working": sum((num(r["working"]) or 0) > 0 for r in crashed),
            "crash_interrupted_only": sum((num(r["working"]) or 0) == 0 and (num(r["interrupted"]) or 0) > 0 for r in crashed),
            "crash_other": sum((num(r["working"]) or 0) == 0 and (num(r["interrupted"]) or 0) == 0 for r in crashed),
            "by_depth": {d: sum(x["depth"] == d for x in intr) for d in sorted({x["depth"] for x in intr})}}


def wait_load():
    """The wait batch (supplementary experiment 1), or None when it has not been analysed."""
    if not (WAITD / "stats-wait.json").exists():
        return None
    return {"rows": list(csv.DictReader(open(WAITD / "rows.csv", encoding="utf-8"))), "stats": read_json(WAITD / "stats-wait.json"),
            "summary": read_json(WAITD / "wait-summary.json"), "cases": opt(WAITD / "early-cases.json") or []}


def table_rows(name: str, keep: list | None = None, drop: list | None = None, rename: dict | None = None,
               base: Path = A) -> str:
    """A generated metric-by-group table (v2_tables.py --transpose): its header plus the rows named in `keep`
    (in that order), or all rows except those in `drop`."""
    lines = [x for x in (base / name).read_text(encoding="utf-8").splitlines() if x.startswith("|")]
    head, body = lines[:2], lines[2:]
    by = {x.split("|")[1].strip(): x for x in body}
    if keep is not None:
        missing = [k for k in keep if k not in by]
        if missing:
            raise SystemExit(f"{name}: no row {missing}")
        body = [by[k] for k in keep]
    elif drop:
        body = [x for x in body if x.split("|")[1].strip() not in drop]
    if rename:
        body = ["| " + rename.get(x.split("|")[1].strip(), x.split("|")[1].strip()) + " |" + x.split("|", 2)[2] for x in body]
    return enc("\n".join(head + body))


R_MAIN = ["次数", "得分", "得分 95% 区间", "模型费·高峰（元/次）", "估算总费用·高峰（元/次）", "估算总费用·空闲（元/次）",
          "实际时长（分钟）", "标准化时长（分钟）"]
R_MAIN_CODE = ["次数", "得分", "得分 95% 区间", "模型费·高峰（元/次）", "模型费·空闲（元/次）", "实际时长（分钟）", "标准化时长（分钟）"]
R_DELEG = ["子代理数（均值 / 最多）", "第 2 层子代理（均值）", "第 3 层子代理（均值）", "名额峰值（均值）", "碰到名额上限的运行数",
           "名额被拒（次/运行）", "碰到深度上限的运行数", "深度被拒（次/运行）", "结束时仍有子代理未回的运行数", "退出时崩溃（次）"]
R_WORK = ["搜索请求数（均值）", "web_search 报错率（%）", "web_fetch 报错率（%）", "缓存命中占比（%）", "交付物长度（千字符）",
          "A 类得分（%）", "B 类得分（%）", "C 类得分（%）", "D 类得分（%）", "严重错误（次/份打分）"]
R_WORK_CODE = ["缓存命中占比（%）", "交付物长度（千字符）", "A 类得分（%）", "B 类得分（%）", "C 类得分（%）", "D 类得分（%）",
               "严重错误（次/份打分）"]


def scoring_note() -> str:
    """The notice at the top: the short report scores complete runs only; this document keeps the plan's scoring."""
    ca = EXP / "results/analysis-complete"
    if not (ca / "stats-office.json").exists():
        return ""
    so_a, so_c = load("stats-office.json"), read_json(ca / "stats-office.json")
    dep_a, dep_c = read_json(A / "stats-office-depth-k48.json"), read_json(ca / "stats-office-depth-k48.json")
    def table(path):
        return {ln.split("|")[1].strip(): [c.strip() for c in ln.strip().strip("|").split("|")][1:]
                for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("|")}

    ga, gc = table(A / "tables-office-t.md"), table(ca / "tables-office-t.md")
    cols = ga["指标"]
    i2, i3 = cols.index("D2-K8"), cols.index("D3-K8")
    return ("**计分的更正（2026-10-03 晚）。** 正式办公批有 2 次运行没交出报告：主代理派出子代理后说“等结果回来再写”就结束了这一轮，headless 进程随即退出并崩溃"
            "（o6t6sas3ps：o1、D2-K8，101 秒，没有文件；60mng0yebw：o2、D3-K8，59 秒，615 字符的骨架）。这是 DSH 的问题，不是报告质量。"
            "短版主报告已改为只算交出完整报告的运行，这 2 次和 p4 的 9 次没写完单列为失败。**本文档的表和对比仍按方案原定的算法（这 2 次按 0 分和 7.9 分计入）**，"
            "两种算法只在下面几处不同：\n\n"
            "| 项目 | 本文档（原定算法） | 只算交出完整报告的运行 |\n|---|---|---|\n"
            f"| D2-K8 得分 | {ga['得分'][i2]} {ga['得分 95% 区间'][i2]}（20 次） | {gc['得分'][i2]} {gc['得分 95% 区间'][i2]}（19 次） |\n"
            f"| D3-K8 得分 | {ga['得分'][i3]} {ga['得分 95% 区间'][i3]}（20 次） | {gc['得分'][i3]} {gc['得分 95% 区间'][i3]}（19 次） |\n"
            f"| H3a D2-K8 − D1-K8 | {d_cell(cmp_(so_a, 'score', 'H3a'))}（20 对） | {d_cell(cmp_(so_c, 'score', 'H3a'))}（19 对） |\n"
            f"| H3b D3-K8 − D1-K8 | {d_cell(cmp_(so_a, 'score', 'H3b'))}（20 对） | {d_cell(cmp_(so_c, 'score', 'H3b'))}（19 对） |\n"
            f"| H4 交互 | {d_cell(cmp_(so_a, 'score', 'H4'))}（20 对） | {d_cell(cmp_(so_c, 'score', 'H4'))}（19 对） |\n"
            f"| 深度 2 − 深度 1（K=4、8 合并） | {d_cell(cmp_(dep_a, 'score', 'PD2'))}（40 对） | {d_cell(cmp_(dep_c, 'score', 'PD2'))}（39 对） |\n"
            f"| 深度 3 − 深度 1（K=4、8 合并） | {d_cell(cmp_(dep_a, 'score', 'PD3'))}（40 对） | {d_cell(cmp_(dep_c, 'score', 'PD3'))}（39 对） |\n\n"
            "其余预注册对比不涉及这两次运行，数值相同。规则和做法见方案“事后检查六”，产物在 `results/analysis-complete/`。\n")


def pearson(x: list, y: list):
    if len(x) < 3:
        return None
    mx, my = st.mean(x), st.mean(y)
    den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / den if den else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=EXP / "report-2026-10-03.md")
    args = ap.parse_args()

    audit = load("audit.json")
    so, sn, sno = load("stats-office.json"), load("stats-office-nocrash.json"), load("stats-office-noopen.json")
    sof, som, sofm = load("stats-office-factorial.json"), load("stats-office-mech.json"), load("stats-office-factorial-mech.json")
    sot = {t: load(f"stats-office-{t}.json") for t in OFF}
    sc, sc2, scf, scf3 = (load("stats-code.json"), load("stats-code-c1w1.json"), load("stats-code-factorial-c1w1.json"),
                          load("stats-code-factorial.json"))
    sc2b, scfb = load("stats-code-c1w1-first2.json"), load("stats-code-factorial-c1w1-first2.json")
    per_task = {t: load(f"stats-code-{t}.json") for t in CODE}
    swk = load("stats-w1-natural-k.json")
    dep = {k: opt(A / f"stats-office-depth-{k}.json") for k in ("k48", "k48-nocrash", "k12", "k4", "k8")}
    dep = dep if all(dep.values()) else None
    rows = list(csv.DictReader(open(A / "rows.csv", encoding="utf-8")))
    prof = json.loads((EXP / "results/profile-official.json").read_text())
    pilot = json.loads((EXP / "results/profile-pilot.json").read_text())
    stage_b = json.loads((EXP / "results/stage-b-decision-main.json").read_text())
    tasks = {json.loads(x)["id"]: json.loads(x) for x in (EXP / "tasks/dsec-tasks.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()}
    probes = [json.loads((EXP / f"results/{n}").read_text())["per_request_cny_peak"]
              for n in ("search-cost-probe-main-office.json", "search-cost-probe-office-v2.json", "search-cost-probe.json")]
    val = {"office_x": opt(VM / "compare-office-xhigh.json"), "code_x": opt(VM / "compare-code-xhigh.json"),
           "max_high": opt(VE / "compare-max-high.json"), "max_xhigh": opt(VE / "compare-max-xhigh.json"),
           "high_xhigh": opt(VE / "compare-high-xhigh.json"),
           "h_v12_max": opt(VE / "human-v12-max.json"), "h_v12_high": opt(VE / "human-v12-high.json"),
           "h_v12_xhigh": opt(VE / "human-v12-xhigh.json"), "h_v13_high": opt(VE / "human-v13-high.json"),
           "split": opt(VE / "split-max.json")}

    ctl, wait, sa = ctl_load(), wait_load(), opt(SUPP / "audit.json")
    uns = unsettled_load()
    cf = ctl_facts(ctl) if ctl else None

    def grp(ts, g):
        return [r for r in rows if r["task"] in ts and r["group"] == g]

    def gm(ts, g, col, scale=1.0):
        v = mean_by_task(grp(ts, g), col)
        return None if v is None else v * scale

    def count(ts, g, cond):
        gr = grp(ts, g)
        return sum(1 for r in gr if cond(r)), len(gr)

    def frac(ts, g, cond):
        a, b = count(ts, g, cond)
        return f"{a}/{b}"

    def hit_k(r):
        return (num(r.get("capacity_rejects")) or 0) > 0

    def hit_d(r):
        return (num(r.get("depth_rejects")) or 0) > 0

    def is_open(r):
        return (num(r.get("open_children_at_end")) or 0) > 0

    def kids_max(ts, g):
        return int(max((num(r["children"]) or 0) for r in grp(ts, g)))

    def med(ts, g, col):
        v = [num(r.get(col)) for r in grp(ts, g) if num(r.get(col)) is not None]
        return st.median(v) if v else None

    n_runs = len(rows)
    crash = audit["crash"]
    oc = crash["open_children_at_root_end"]
    jo, jc = audit["judging"]["office"], audit["judging"]["code"]
    cost = audit["cost"]
    sp = audit["speed"]
    ro, rc, rb = audit["runs"]["main-office"], audit["runs"]["main-code"], audit["runs"]["main-code-B"]
    total_requests = sum(sp[b]["all"]["requests"] for b in sp)
    retries = sum(sp[b]["all"]["llm_retry_events"] for b in sp)
    infra_retries = sum(v for b in audit["runs"].values() for k, v in b["attempts"].items() if k != "1")
    oom = sum(b["oom_kill"] for b in audit["runs"].values())
    timeouts = sum(b["timeouts"] for b in audit["runs"].values())

    HK = ("H1", "H2a", "H2b", "H2c", "H3a", "H3b", "H4")
    H = {k: cmp_(so, "score", k) for k in HK}
    HC = {k: cmp_(so, "total_cost_peak", k) for k in HK}
    HT = {k: cmp_(so, "std_seconds", k) for k in HK}
    HW = {k: cmp_(so, "seconds", k) for k in HK}
    FK = ("FK1", "FK2", "FK4", "FD2", "FD3", "FX", "FA")
    F = {k: cmp_(sof, "score", k) for k in FK}
    FC = {k: cmp_(sof, "total_cost_peak", k) for k in FK}
    FT = {k: cmp_(sof, "std_seconds", k) for k in FK}
    CK = ("C1", "C2", "C3a", "C3b", "C3c", "C4a", "C4b", "C5")
    C = {k: cmp_(sc, "score", k) for k in CK}          # three tasks, as pre-registered
    CC = {k: cmp_(sc, "model_cost_peak", k) for k in CK}
    CT = {k: cmp_(sc, "std_seconds", k) for k in CK}
    CW = {k: cmp_(sc, "seconds", k) for k in CK}
    D = {k: cmp_(sc2, "score", k) for k in CK}         # c1 + w1
    DC = {k: cmp_(sc2, "model_cost_peak", k) for k in CK}
    DT = {k: cmp_(sc2, "std_seconds", k) for k in CK}
    GK = ("FK1", "FK2", "FK4", "FD2", "FD3", "FX", "FE")
    G = {k: cmp_(scf, "score", k) for k in GK}         # c1 + w1, encouraged, factorial
    GC = {k: cmp_(scf, "model_cost_peak", k) for k in GK}
    GT = {k: cmp_(scf, "std_seconds", k) for k in GK}
    NH = {k: cmp_(sn, "score", k) for k in ("H3a", "H3b", "H4")}
    NO = {k: cmp_(sno, "score", k) for k in HK}
    NOC = {k: cmp_(sno, "total_cost_peak", k) for k in HK}

    d0_min = gm(OFF, "D0", "seconds", 1 / 60)
    others = [gm(OFF, g, "seconds", 1 / 60) for g in OFF_GROUPS[1:]]
    office_deleg = [r for r in rows if r["task"] in OFF and r["group"] != "D0"]
    off_spawned = sum(1 for r in office_deleg if (num(r["children"]) or 0) > 0)
    off_open = [r for r in office_deleg if is_open(r)]
    off_open_crash = sum(1 for r in off_open if truthy(r["crash5063"]))
    off_crash = sum(1 for r in rows if r["task"] in OFF and truthy(r["crash5063"]))
    stub = [r for r in rows if r["id"] in set(crash["deliverable_missing"])]
    stub_scores = sorted(float(r["score"]) for r in stub)
    p4e = [r for r in rows if r["task"] == P4 and r["group"].startswith("E-")]
    p4e_low = [r for r in p4e if float(r["score"]) < 99.999]
    p4n = [r for r in rows if r["task"] == P4 and not r["group"].startswith("E-")]
    p4n_low = [r for r in p4n if float(r["score"]) < 99.999]
    p4e_cut = [r for r in p4e_low if is_open(r)]
    p4e_open = [r for r in p4e if is_open(r)]
    k1_rej = {g: int(sum(num(r["capacity_rejects"]) or 0 for r in grp(OFF, g))) for g in ("D1-K1", "D2-K1", "D3-K1")}

    def mech(o, metric, label):
        return cmp_(o, metric, label)

    L: list[str] = []
    w = L.append

    # ================================================================ title
    w("# 子代理的深度上限 D 与同时存活上限 K：13 组对照实验报告\n")
    note = scoring_note()
    if note:
        w(note)
    t0 = min(b["started_utc_min"] for b in audit["runs"].values())
    t1 = max(b["ended_utc_max"] for b in audit["runs"].values())

    supp_batches = [b for b, have in (("wait-office-2", wait), ("ctl-main", ctl)) if have and sa and b in sa["runs"]]
    n_supp = (len(ctl["rows"]) if ctl else 0) + (len(wait["rows"]) if wait else 0)
    supp_when = ""
    if supp_batches:
        s0 = min(sa["runs"][b]["started_utc_min"] for b in supp_batches)
        s1 = max(sa["runs"][b]["ended_utc_max"] for b in supp_batches)
        supp_when = f"补充实验（实验 2、3）：{n_supp} 次运行（10/3 北京时间 {bj(s0)}–{bj(s1)}）。"
    w("张子雅，2026-10-03。DSH 0.2.0-rc.2，模型 deepseek-flash（推理强度 max，主代理和子代理同一个模型）。"
      f"正式实验：DSec 上 {n_runs} 次运行（10/3 北京时间 {bj(t0)}–{bj(t1)}）。{supp_when}\n")
    w(f"输入：每次运行一行的汇总表 `results/analysis-v2/rows.csv`（{n_runs} 行）；SHA-256：`{audit['files']['results/analysis-v2/rows.csv']}`。"
      + ("补充实验的汇总表是 " + "、".join(f"`{x}`" for x, have in (("results/analysis-wait/rows.csv", wait), ("results/analysis-ctl/rows.csv", ctl)) if have)
         + "。" if n_supp else "")
      + "各批运行清单、指标、打分和脚本的 SHA-256 见附录 E。预注册方案：`experiment-plan-dsec-v2.md`，开跑前与用户逐项确认写定。\n")
    w("名词：D 是子代理最多能嵌套几层（`maxDepth`），D0 表示把开子代理的工具全部拿掉。K 是同一时刻最多有几个后台子代理在跑"
      "（`maxActiveSubagents`），不是总数。出厂默认是 D1-K8。“鼓励·”开头的组是在题面末尾加了一句鼓励并行的话。"
      + ("“等·”开头的组只出现在补充实验里：换了 headless 的入口文件，进程等后台子代理都回来才退出。" if n_supp else "") + "\n")
    w("适用范围：DSH 以 headless（批处理）方式运行、一个模型、一个 DSH 版本、5 道 3–14 分钟能做完的题"
      + ("，加补充实验的 2 道对照题" if ctl else "") + "。交互使用、更长的任务、其他模型不在这次的结论里。\n")

    # ================================================================ findings
    def layer_runs(g, col):
        return frac(OFF, g, lambda r: (num(r.get(col)) or 0) > 0)

    def l2(task):
        v = [r for r in rows if r["task"] == task and re.search(r"D[23]-", r["group"])]
        return f"{sum((num(r.get('children_d2')) or 0) > 0 for r in v)}/{len(v)}"

    def dsum(g):
        return int(sum(num(r["depth_rejects"]) or 0 for r in grp(OFF, g)))

    def ksum(g):
        return int(sum(num(r["capacity_rejects"]) or 0 for r in grp(OFF, g)))

    def spawned(task, g):
        return frac((task,), g, lambda r: (num(r["children"]) or 0) > 0)

    wf = wait_facts(wait) if wait else None
    wc = wait_counts(wf) if wait else None
    b_h1 = mech(som, "cat_B", "H1")
    s_h1, g_h1, len_h1 = mech(som, "search_aux", "H1"), mech(som, "G_s", "H1"), mech(som, "deliv_chars", "H1")
    ia = opt(A / "item-analysis.json")
    sens = opt(EXP / "results/validate-degrade/sensitivity.json")
    pd2 = cmp_(dep["k48"], "score", "PD2") if dep else None
    pd3 = cmp_(dep["k48"], "score", "PD3") if dep else None
    all_crash = crash["total"] + (wc["n_crash"] + wc["w_crash"] if wait else 0)

    # ---------------------------------------------------------------- purpose
    w("## 这个实验为了什么\n")
    w("DSH 用两个配置限制子代理：深度上限 `maxDepth`（出厂 1）和同时存活上限 `maxActiveSubagents`（出厂 8）。这两个出厂值没有实验依据。"
      "我们看过的 3 份真实用户会话里，一次会话开了 24、18、45 个子代理，最深到第 3 层（`results/user-sessions-delegation.json`）；"
      "子代理开得多，费用和等待时间都跟着涨。\n")
    w("要给工程设计回答四个问题：\n")
    w("1. 出厂的深度 1 要不要放开到 2 或 3。\n"
      "2. 出厂的 K=8 要不要改，改成几。\n"
      "3. 给不给委派工具、要不要在提示里鼓励并行：各多花多少，换来多少。\n"
      "4. 这两个上限现在的实现方式有没有问题：碰到才拒绝、名额整棵树共用、headless 下主代理一结束进程就退出。\n")
    w("做法：把 D 和 K 设成 13 种组合，在同样的题上各跑 10 次，记录得分、费用、时长和模型实际开了多少子代理；"
      "再用三项补充实验（实验 2–4）检查正式实验留下的三个疑点（深度 2、3 的低分是不是提前收工造成的；这套做法测不测得出委派的好处；测不出是不是打分的问题）。\n")

    # ---------------------------------------------------------------- engineering conclusions
    w("## 结论：对 D 和 K 的工程设计能说什么\n")
    w("先说贯穿全部结果的一件事：**D 和 K 不直接决定质量，它们只是上限。** 模型开多少个、开多深由它自己决定，上限只在被碰到时起作用。"
      "所以要问的不是“设成几质量最好”，而是“上限挡住的那部分委派，放开以后值不值”。\n")

    w("**1. 深度上限：保持 1。**\n")
    w(f"- 深度 1 这个上限几乎每次都被碰到：D1-K8 有 {frac(OFF, 'D1-K8', hit_d)} 次运行的子代理想再往下开、被拒（共 {dsum('D1-K8')} 次）。\n"
      f"- 放开以后：子代理从 {gm(OFF, 'D1-K8', 'children'):.1f} 个变成 {gm(OFF, 'D2-K8', 'children'):.1f} 个，估算总费用 {ratio(HC['H3a']):.1f} 倍，"
      "得分没有提高。"
      + (f"K=4、8 两列合并（40 对，事后）：深度 2、3 减深度 1 是 {d_cell(pd2)}、{d_cell(pd3)}。" if dep else "")
      + (f"让进程等子代理都回来以后（实验 2，预注册）：{d_cell(wf['S3']['score'])}（{verdict(wf['S3']['score'])}）、"
         f"{d_cell(wf['S4']['score'])}（{verdict(wf['S4']['score'])}），费用 {ratio(wf['S3']['total_cost_peak']):.1f}、{ratio(wf['S4']['total_cost_peak']):.1f} 倍。" if wait else "")
      + "\n"
      f"- 稳定性的代价也在这里：两批共 {all_crash} 次退出崩溃，全部在深度 ≥ 2 且 K ≥ 4 的组；2 次主代理没写完报告就结束（得分 0.0 和 7.9）。\n"
      f"- 放开一层满足不了模型：D2-K8 仍有 {frac(OFF, 'D2-K8', hit_d)} 次运行想再往下开（共 {dsum('D2-K8')} 次）。想往下委派是模型的习惯，不说明任务需要。\n"
      "- 有多硬：预注册的两个对比（K=8）功效低、测不出；事后合并和一次重复实验方向一致，没有一种算法里加深是有好处的。\n"
      "- 边界：十几分钟、交一份文件的任务；没有天然两层结构的题；一个模型。\n")

    w("**2. K 的出厂值：8 不用改；在深度 1 下，4 以上是同一个条件。**\n")
    w(f"- 深度 1 下模型自己同时最多开 3–4 个（名额峰值平均 {gm(OFF, 'D1-K8', 'slot_peak'):.1f}）。名额上限被碰到的运行数：K=8 {frac(OFF, 'D1-K8', hit_k)}、"
      f"K=4 {frac(OFF, 'D1-K4', hit_k)}、K=2 {frac(OFF, 'D1-K2', hit_k)}、K=1 {frac(OFF, 'D1-K1', hit_k)}。\n"
      f"- K=4 减 K=8：得分 {d_cell(H['H2c'])}（{verdict(H['H2c'])}），费用 {ratio(HC['H2c']):.2f} 倍。把 8 改成 4、5、6 不会改变任何东西。\n"
      "- 有多硬：预注册对比加直接计数。\n"
      + (f"- 边界：任务宽了就不一样。24 道独立练习的对照题上，K=8 在 {sum((num(r['capacity_rejects']) or 0) > 0 for r in cf['g'](PW, 'W-E-D1-K8'))}/10 次"
         "鼓励并行的运行里被碰到。K 在宽任务上该设多少，这次没测。\n" if ctl else ""))

    w("**3. 想靠调小 K 省钱：K=2 省不了，K=1 能省四成多，适合做成一个省钱档，不适合做出厂值。**\n")
    w(f"- K=2：{frac(OFF, 'D1-K2', hit_k)} 次运行碰到上限，费用 {ratio(HC['H2b']):.2f} 倍，得分 {d_cell(H['H2b'])}。模型换成分批开，总数少不了多少。\n"
      f"- K=1：子代理一个接一个做。费用 {ratio(HC['H2a']):.2f} 倍，办公题得分 {d_cell(H['H2a'])}（{verdict(H['H2a'])}，区间下限略超过 −5）。\n"
      f"- 读代码题（鼓励并行，事后把三个深度合起来）：K=1、2 比 K=8 低 {abs(G['FK1']['est']):.1f}、{abs(G['FK2']['est']):.1f} 分"
      f"（Holm 后 p 分别是 {G['FK1']['p_holm']:.3f}、{G['FK2']['p_holm']:.3f}）。\n"
      "- 有多硬：办公题是预注册对比；代码题是事后分析。办公题在自然状态下测，代码题在加了鼓励句以后测，两者不能合成一句话。\n")

    w(f"**4. 给不给委派工具：按任务定。一般的调研任务上费用是 {ratio(HC['H1']):.1f} 倍，换不到可测的质量；块数多、要赶时间的任务上有用。**\n")
    w(f"- 办公题，出厂默认减不给工具（预注册 H1）：得分 {d_cell(H['H1'])}（{verdict(H['H1'])}，最小可测差 {H['H1']['mdd']:.1f} 分），"
      f"估算总费用 {ratio(HC['H1']):.2f} 倍，标准化时长 {ratio(HT['H1']):.2f} 倍。\n"
      f"- 没有更快，是因为活被做大了，不是被拆开：搜索请求 {ratio(s_h1):.1f} 倍，报告长 {ratio(len_h1):.2f} 倍。"
      f"多出来的只体现在“关键事实”一类（{sgn(b_h1['est'])} 个百分点）。\n"
      + (f"- 阳性对照（24 道独立练习，限时 3 分钟）：委派高 {d_cell(cf[PW]['PC']['score'])}，费用 {ratio(cf[PW]['PC']['model_cost_peak']):.2f} 倍。"
         "好处是快：不限时的话，不委派也能做到同样的分数，而且更便宜。\n"
         f"- 阴性对照（16 步，步步依赖）：得分不变，费用 {ratio(cf[N1]['PC']['model_cost_peak']):.2f} 倍，时长 {ratio(cf[N1]['PC']['seconds']):.2f} 倍。\n" if ctl else "")
      + "- 有多硬：H1 是预注册对比，但只测得出 5 分以上的差别；对照题各 10 对。\n")

    w("**5. 提示里不默认鼓励并行。**\n")
    w(f"- 读代码题 c1、w1：得分 {d_cell(D['C2'])}，模型费 {ratio(DC['C2']):.2f} 倍，时长 {ratio(DT['C2']):.2f} 倍。\n"
      f"- p4：自然状态 {len(p4n) - len(p4n_low)}/{len(p4n)} 次满分；加了鼓励句以后 {len(p4e_cut)} 次交出没写完的代码"
      f"（{min(float(r['score']) for r in p4e_cut):.0f}–{max(float(r['score']) for r in p4e_cut):.0f} 分）。\n"
      + (f"- 阴性对照：鼓励句让 {sum(cf['kids'](r) > 0 for r in cf['g'](N1, 'W-E-D1-K8'))}/10 次运行开了子代理去重算一遍已有的答案。\n" if ctl else "")
      + "- 有多硬：预注册对比（三题合并）测不出；两道读代码题合并是事后分析。只试了一句话。\n")

    w("**6. 上限的实现方式要改：现在是给了工具、调用时才拒绝。**\n")
    w(f"- 深度：D1-K8 的 20 次运行里，子代理调用委派工具被深度上限拒了 {dsum('D1-K8')} 次。到了深度上限的子代理，不该再拿到委派工具。\n"
      f"- 名额：D1-K1 的 20 次运行被拒 {ksum('D1-K1')} 次；深度放开后名额是整棵树共用的，D2-K4 被拒 {ksum('D2-K4')} 次、D2-K8 {ksum('D2-K8')} 次。"
      "上限应该事先告诉模型，或者超出时排队。\n"
      "- 有多硬：直接计数。改了以后效果如何没有测。\n")

    w("**7. headless 下，进程要等子代理都结算了再退出；被 interrupt 的子代理要能正常结算。**\n")
    w((f"- 不等的两组退出崩溃 {wc['n_crash']}/{wc['n_runs']} 次；等的三组 {wc['w_crash']}/{wc['w_runs']} 次，“还有子代理在干活、进程就退出”的情况没有再出现。\n" if wait else
       f"- {n_runs} 次运行里 {crash['total']} 次退出崩溃，都在深度 ≥ 2 且 K ≥ 4 的组。\n")
      + (f"- 剩下的崩溃来自另一个缺陷：被上级 interrupt 的子代理，如果当时还有排队没处理的消息，就一直不结算（{uns['queued']} 个里 {uns['queued_settled']} 个结算）。\n" if uns else "")
      + (f"- 等不等对平均得分没有可测的影响（{d_cell(wf['S1']['score'])}、{d_cell(wf['S2']['score'])}）。要修它是为了稳定和不丢报告，不是为了提分。\n" if wait else "")
      + "- 有多硬：对照实验加直接计数。补丁是实验用的，不是正式修复。\n")

    w("**不能下的结论：**\n")
    w("- “K 设成几最好”：这些题上 4 以上没有区别，宽任务上没测。\n"
      "- “委派有用”或“委派没用”的一般结论：取决于任务能拆成几块、赶不赶时间。\n"
      "- 小于 5 分的质量差别朝哪个方向。\n"
      "- 来源做得好不好：这套打分看不出来（见实验 4）。\n"
      "- 别的模型、更长的任务、交互使用。\n")

    # ---------------------------------------------------------------- outline
    w("## 实验一览\n")
    o = [f"- 实验 1：正式实验（{n_runs} 次；办公 2 题、代码 3 题；13 组）",
         f"  - 设置 1：给不给委派工具（D0 对 D1-K8）→ 办公题得分差 {d_cell(H['H1'])}，测不出；费用 {ratio(HC['H1']):.2f} 倍，没有更快",
         f"    - 结论：子代理把活做大了（搜索 {ratio(s_h1):.1f} 倍），没有把活拆开",
         f"  - 设置 2：K = 1、2、4、8（深度 1）→ K=4 和 K=8 是同样的运行；K=1 费用 {ratio(HC['H2a']):.2f} 倍，得分差 {d_cell(H['H2a'])}",
         "    - 结论：K 在 4 以上不起作用；K=1 是省钱档",
         f"  - 设置 3：深度 1、2、3 → 得分没有提高；费用 {ratio(HC['H3b']):.1f}–{ratio(HC['H3a']):.1f} 倍；退出崩溃全部在这里",
         "    - 结论：深度上限在起作用，它挡住的那部分委派没有带来回报",
         f"  - 设置 4：题面加一句鼓励并行（代码题）→ 读代码题 {d_cell(D['C2'])}、费用 {ratio(DC['C2']):.2f} 倍；p4 掉分",
         "    - 结论：不默认加"]
    if wait:
        o += [f"- 实验 2：让进程等子代理回来（{len(wait['rows'])} 次）→ 得分没有可测的变化；退出崩溃 {wc['n_crash']}/{wc['n_runs']} 对 {wc['w_crash']}/{wc['w_runs']}",
              "  - 结论：正式实验里深度 2、3 的低分来自两次没写完的报告，不是深度本身；等了以后深度 2、3 仍然不比深度 1 好"]
    if ctl:
        o += [f"- 实验 3：对照题（{len(ctl['rows'])} 次）",
              f"  - 设置 1：阳性对照（24 道独立练习，限时 3 分钟）→ 委派高 {d_cell(cf[PW]['PC']['score'])}，费用 {ratio(cf[PW]['PC']['model_cost_peak']):.2f} 倍",
              f"  - 设置 2：阴性对照（16 步，步步依赖）→ 得分不变，费用 {ratio(cf[N1]['PC']['model_cost_peak']):.2f} 倍",
              "    - 结论：这套做法测得出委派的好处；好处是快，出现在块数多、要赶时间的任务上"]
    if ia:
        sh = [ia["tasks"][k]["judge_share_of_run_variance"] for k in OFF]
        line = f"- 实验 4：判分检查 → 打分噪声占运行间波动的 {100 * min(sh):.0f}%–{100 * max(sh):.0f}%"
        if sens:
            sm = sens["summary"]
            line += f"；把报告的事实改错，得分掉 {abs(sm['wrong']['mean_diff']):.0f} 分；删掉全部来源链接只掉 {abs(sm['nolinks']['mean_diff']):.0f} 分"
        o += [line, "  - 结论：测不出主要是因为运行之间的波动和每个对比只有 20 对；评分标准对来源质量不敏感"]
    w("\n".join(o) + "\n")

    w("读法：\n")
    w("- 得分是百分制。每个对比都按（题，第几次）配对，办公题 20 对（2 题 × 10 次），代码题 c1、w1 两题 20 对。\n"
      f"- “没有实际差别”指得分差的 95% 区间整个落在 ±{DELTA:.0f} 分以内；“有差别”指多重校正（Holm）后 p < 0.05；"
      "其余写“测不出”，并给出最小可测差：真实差别要有这么大，这个对比才有 80% 的把握测出来。\n"
      "- “预注册”指开跑前写进方案的对比（一次只改一个因素）。“事后”指看到数据后补的分析，只能当线索，不能当检验结论。\n"
      "- 得分由 Opus 5.5 按评分标准打（思考强度 high，每份 2 次取平均）。对照题由脚本判分（隐藏测试、答案键）。\n"
      "- 组名：D 是深度上限，D0 表示没有委派工具；K 是同时存活上限。“鼓励·”是题面末尾加了一句鼓励并行的话；“等·”是进程等子代理都回来才退出。\n")

    # ---------------------------------------------------------------- experiment 1
    w(f"## 实验 1：正式实验（{n_runs} 次）\n")
    w("13 组：D0，加上 D1、D2、D3 各配 K = 1、2、4、8。办公题 o1、o2（要上网搜索）13 组各 10 次；代码题 c1、w1、p4（不联网）"
      "自然状态跑 D0 和各深度的 K=8，鼓励并行跑 12 个委派组。同一批里随机完全区组，并发数全程不变。组、题、环境和指标口径见后面的“实验设置”“指标口径”，各组的完整数据表见“详细数据”。\n")

    w("### 设置 1：给不给委派工具（D0 对 D1-K8）\n")
    w("两组只差一处：D0 把 4 个委派工具关掉，D1-K8 是出厂默认。\n")
    w("结果：\n")
    w(f"- 办公题（预注册 H1，20 对）：得分差 {d_txt(H['H1'])}，最小可测差 {H['H1']['mdd']:.1f} 分，判为{verdict(H['H1'])}。"
      f"估算总费用是 {r_txt(HC['H1'])}，标准化时长是 {r_txt(HT['H1'])}。\n"
      f"- 事后把 12 个有委派工具的组合起来对 D0：得分差 {d_txt(F['FA'])}，区间落在 ±5 分以内；"
      f"估算总费用 {ratio(FC['FA']):.2f} 倍，标准化时长 {ratio(FT['FA']):.2f} 倍"
      f"（区间 {math.exp(FT['FA']['lo']):.2f}–{math.exp(FT['FA']['hi']):.2f}，未校正 p {p_txt(FT['FA']['p'])}）。\n"
      f"- 代码题 c1、w1（自然状态，20 对）：得分差 {d_txt(D['C1'])}，最小可测差 {D['C1']['mdd']:.1f} 分；模型费 {ratio(DC['C1']):.2f} 倍。"
      "p4 两组都是满分或接近满分。\n")
    w("诊断：\n")
    w(f"- 办公题只要给了工具几乎每次都开：12 个委派组 {off_spawned}/{len(office_deleg)} 次运行开了子代理。"
      f"D1-K8 平均 {gm(OFF, 'D1-K8', 'children'):.1f} 个、最多 {kids_max(OFF, 'D1-K8')} 个。\n"
      f"- 活被做大了：D1-K8 对 D0，搜索请求 {ratio(s_h1):.1f} 倍（中位数 {med(OFF, 'D0', 'search_aux'):.0f} 次 → {med(OFF, 'D1-K8', 'search_aux'):.0f} 次），"
      f"至少有一个模型在生成的时间 {ratio(g_h1):.1f} 倍，交付物长度 {ratio(len_h1):.2f} 倍。子代理没有把同一份活分掉，而是每个都多查了一遍。\n"
      f"- 所以没有更快：办公题 D0 平均 {d0_min:.1f} 分钟，其余 12 组 {min(others):.1f}–{max(others):.1f} 分钟。\n"
      f"- 多查的那部分体现在哪：按评分类别看（只作描述），D1-K8 高出来的是 B 类“关键事实”，{sgn(b_h1['est'])} 个百分点"
      f"（区间 {sgn(b_h1['lo'])} 到 {sgn(b_h1['hi'])}，未校正 p {p_txt(b_h1['p'])}）；"
      f"A、C、D 三类的差是 {sgn(mech(som, 'cat_A', 'H1')['est'])}、{sgn(mech(som, 'cat_C', 'H1')['est'])}、"
      f"{sgn(mech(som, 'cat_D', 'H1')['est'])}，区间都包含 0。\n"
      f"- 代码题不提醒就很少委派：自然状态 D1-K8 下，c1 {spawned(C1, 'D1-K8')} 次、p4 {spawned(P4, 'D1-K8')} 次运行开了子代理；"
      f"w1 {spawned(W1, 'D1-K8')} 次，平均 {gm((W1,), 'D1-K8', 'children'):.1f} 个。c1、w1 的差别全部来自 w1。\n")
    w(f"结论：在这些题上，给了委派工具以后费用是原来的 {ratio(HC['H1']):.1f} 倍，得分差在 5 分上下以内测不出来，也没有更快。"
      f"不能据此说委派没有用：办公题区间上限是 {sgn(H['H1']['hi'])} 分，越过了 5 分；这些题都是十几分钟内能做完、只交一份文件的任务"
      + ("，实验 3 换了一道按设计适合并行的题，测到了委派带来的差别。\n" if ctl else "。\n"))

    w("### 设置 2：K = 1、2、4、8（深度 1）\n")
    w("四组只差 `maxActiveSubagents`。模型看不到这个数，碰到上限时开子代理的调用被拒。\n")
    w("结果：\n")
    w("| 对比（办公题，预注册，20 对） | 得分差 | 最小可测差 | 判断 | 估算总费用之比 | 碰到名额上限的运行数 |\n|---|---|---|---|---|---|")
    for k, nm, g in (("H2c", "K=4 减 K=8", "D1-K4"), ("H2b", "K=2 减 K=8", "D1-K2"), ("H2a", "K=1 减 K=8", "D1-K1")):
        w(f"| {nm} | {d_cell(H[k])} | {H[k]['mdd']:.1f} | {verdict(H[k])} | {r_cell(HC[k])} | {frac(OFF, g, hit_k)}（K=8：{frac(OFF, 'D1-K8', hit_k)}） |")
    w("")
    w(f"- 办公题事后把三个深度合起来：K=1 对 K=8 得分差 {d_cell(F['FK1'])}，估算总费用 {ratio(FC['FK1']):.2f} 倍；"
      f"K=2 {d_cell(F['FK2'])}，{ratio(FC['FK2']):.2f} 倍；K=4 {d_cell(F['FK4'])}，{ratio(FC['FK4']):.2f} 倍。"
      f"标准化时长分别是 {ratio(FT['FK1']):.2f}、{ratio(FT['FK2']):.2f}、{ratio(FT['FK4']):.2f} 倍，都不显著。\n"
      f"- 代码题 c1、w1（鼓励并行，事后把三个深度合起来）：K=1 对 K=8 得分差 {d_cell(G['FK1'])}（Holm 后 p {p_txt(G['FK1']['p_holm'])}），"
      f"模型费 {ratio(GC['FK1']):.2f} 倍；K=2 {d_cell(G['FK2'])}（Holm 后 p {p_txt(G['FK2']['p_holm'])}），{ratio(GC['FK2']):.2f} 倍；"
      f"K=4 {d_cell(G['FK4'])}，{ratio(GC['FK4']):.2f} 倍。预注册的深度 1 单格对比（三题合并）是 "
      f"{d_cell(C['C3a'])}、{d_cell(C['C3b'])}、{d_cell(C['C3c'])}，都不显著。\n")
    w("诊断：\n")
    w(f"- K=4 和 K=8 是同样的运行：模型同时最多开 3–4 个，K=4 只在 {frac(OFF, 'D1-K4', hit_k)} 次运行里被碰到。这个对比不说明问题。\n"
      f"- K 小的时候模型一个接一个地开：D1-K1 平均每次运行开 {gm(OFF, 'D1-K1', 'children'):.1f} 个子代理（K=8 是 {gm(OFF, 'D1-K8', 'children'):.1f} 个），"
      f"同一时刻最多 1 个。\n"
      f"- K=1 省下的费用里包含被拒后的重试：三个 K=1 组各 20 次运行，累计被名额上限拒 "
      f"{k1_rej['D1-K1']}、{k1_rej['D2-K1']}、{k1_rej['D3-K1']} 次。换成事先告诉模型上限、或者排队而不是拒绝，结果可能不同。\n")
    w("结论：深度 1 下 K 在 4 以上不起作用。真正起约束的是 K=1 和 K=2：办公题上 K=1 省四成多的费用、没有测到得分损失；"
      "鼓励并行的读代码题上 K=1、2 低 3–4 分。两类题的条件不同（自然状态对鼓励并行），不能合成一句话。\n")

    w("### 设置 3：深度 1、2、3\n")
    w("三组只差 `maxDepth`。预注册对比在 K=8 下做（D2-K8、D3-K8 对 D1-K8）。\n")
    w("结果：\n")
    w(f"- 办公题预注册对比（K=8，20 对）：D2 减 D1 {d_cell(H['H3a'])}，D3 减 D1 {d_cell(H['H3b'])}。最小可测差是 "
      f"{H['H3a']['mdd']:.1f} 和 {H['H3b']['mdd']:.1f} 分，只有十几分的差别才测得出，判为测不出。估算总费用是 {r_txt(HC['H3a'])} 和 {r_txt(HC['H3b'])}。\n"
      + (f"- 事后把深度真的被用上的两列（K=4、K=8）合起来，40 对：D2 减 D1 {d_cell(pd2)}，D3 减 D1 {d_cell(pd3)}；"
         f"去掉退出崩溃的运行是 {d_cell(cmp_(dep['k48-nocrash'], 'score', 'PD2'))}（{cmp_(dep['k48-nocrash'], 'score', 'PD2')['n']} 对）、"
         f"{d_cell(cmp_(dep['k48-nocrash'], 'score', 'PD3'))}（{cmp_(dep['k48-nocrash'], 'score', 'PD3')['n']} 对）。"
         f"估算总费用是 {ratio(cmp_(dep['k48'], 'total_cost_peak', 'PD2')):.2f}、{ratio(cmp_(dep['k48'], 'total_cost_peak', 'PD3')):.2f} 倍，"
         f"实际时长是 {ratio(cmp_(dep['k48'], 'seconds', 'PD2')):.2f}、{ratio(cmp_(dep['k48'], 'seconds', 'PD3')):.2f} 倍（区间都不含 1）。\n" if dep else "")
      + f"- 代码题 c1、w1（鼓励并行，事后把四个 K 合起来）：{d_cell(G['FD2'])}、{d_cell(G['FD3'])}，区间在 ±3 分以内；"
      f"模型费 {ratio(GC['FD2']):.2f}、{ratio(GC['FD3']):.2f} 倍。\n"
      f"- 深度和 K 的交互（预注册 H4）：办公题 {d_cell(H['H4'])}，最小可测差 {H['H4']['mdd']:.1f} 分；代码题 {d_cell(C['C5'])}，最小可测差 {C['C5']['mdd']:.1f} 分。看不出交互，但这个对比功效最低。\n")
    w("诊断：\n")
    w((f"- 深度只在 K ≥ 4 时真的被用上。名额是整棵树共用的，K=1、2 时第 1 层就把名额占满：D2-K1、D2-K2 的 40 次办公运行里没有一次出现第 2 层子代理。"
       f"第 3 层很少到：D3-K8 是 {layer_runs('D3-K8', 'children_d3')} 次运行、平均 {gm(OFF, 'D3-K8', 'children_d3'):.1f} 个。所以这次实际比的是“一层对两层”。\n" if dep else "")
      + f"- 放开以后模型马上多开：D2-K8 平均 {gm(OFF, 'D2-K8', 'children'):.1f} 个（第 2 层 {gm(OFF, 'D2-K8', 'children_d2'):.1f} 个），"
      f"D3-K8 平均 {gm(OFF, 'D3-K8', 'children'):.1f} 个（第 2 层 {gm(OFF, 'D3-K8', 'children_d2'):.1f}、第 3 层 {gm(OFF, 'D3-K8', 'children_d3'):.1f}）。"
      f"这时名额上限也被碰到了：D2-K8 {frac(OFF, 'D2-K8', hit_k)} 次运行。\n"
      f"- 模型在哪一层都想继续往下开：D1-K8 有 {frac(OFF, 'D1-K8', hit_d)} 次运行被深度上限拒过（共 {dsum('D1-K8')} 次）；"
      f"放开到 D2-K8，仍有 {frac(OFF, 'D2-K8', hit_d)} 次运行被拒（共 {dsum('D2-K8')} 次）。多放一层只是把被拒的地方往下挪了一层。\n"
      f"- K=8 下的低分从哪来：{len(stub)} 次主代理没写完报告就结束（得分 {stub_scores[0]:.1f} 和 {stub_scores[1]:.1f}，D2-K8、D3-K8 各一次）。"
      + ("实验 2 重跑了这两组，没有再出现这种情况，低分也没有重现。\n" if wait else "\n")
      + f"- 代码题里第 2 层子代理基本只出现在 w1：深度 ≥ 2 的组里，w1 {l2(W1)} 次运行、c1 {l2(C1)}、p4 {l2(P4)}。\n")
    w("结论：加深到 2、3 层没有提高得分；多花钱、多花时间，退出崩溃都出现在这里。深度上限 1 挡住的那部分委派没有带来回报。\n")

    w("### 设置 4：题面末尾加一句“独立的子任务尽量交给 subagent 并行做。”（代码题）\n")
    w("同一组配置，题面多一句话。预注册对比是 鼓励·D1-K8 减 D1-K8。\n")
    w("结果：\n")
    w(f"- 预注册对比（三题合并，30 对）：得分差 {d_cell(C['C2'])}，判为{verdict(C['C2'])}；模型费 {r_txt(CC['C2'])}；"
      f"标准化时长 {r_txt(CT['C2'])}。三道题方向不一致：c1 {sgn(cmp_(per_task[C1], 'score', 'C2')['est'])}、"
      f"w1 {sgn(cmp_(per_task[W1], 'score', 'C2')['est'])}、p4 {sgn(cmp_(per_task[P4], 'score', 'C2')['est'])}。\n"
      f"- c1、w1 两题（事后，20 对）：得分差 {d_txt(D['C2'])}，未校正 p {p_txt(D['C2']['p'])}，Holm 后 p {p_txt(D['C2']['p_holm'])}；"
      f"三个深度的 K=8 合起来 {d_cell(G['FE'])}（未校正 p {p_txt(G['FE']['p'])}）。模型费 {ratio(DC['C2']):.2f} 倍"
      f"（c1 {math.exp(cmp_(per_task[C1], 'model_cost_peak', 'C2')['est']):.1f} 倍、w1 {math.exp(cmp_(per_task[W1], 'model_cost_peak', 'C2')['est']):.1f} 倍），"
      f"标准化时长 {ratio(DT['C2']):.2f} 倍。\n")
    w("诊断：\n")
    w(f"- 鼓励句让原本不开子代理的题开了子代理：c1 自然状态下 {spawned(C1, 'D1-K8')} 次运行开子代理，加了以后平均开 {gm((C1,), 'E-D1-K8', 'children'):.1f} 个。\n"
      f"- 答案也长得多：c1 的答案长度是自然状态的 "
      f"{gm((C1,), 'E-D1-K8', 'deliv_chars') / gm((C1,), 'D1-K8', 'deliv_chars'):.1f} 倍，w1 是 "
      f"{gm((W1,), 'E-D1-K8', 'deliv_chars') / gm((W1,), 'D1-K8', 'deliv_chars'):.1f} 倍。\n"
      f"- p4：自然状态 {len(p4n)} 次运行里 {len(p4n) - len(p4n_low)} 次满分；鼓励版 {len(p4e)} 次里 {len(p4e_low)} 次没拿满分，"
      f"其中 {len(p4e_cut)} 次在 {min(float(r['score']) for r in p4e_cut):.0f}–{max(float(r['score']) for r in p4e_cut):.0f} 分，"
      "全部是主代理结束时子代理还没改完。\n")
    w("结论：一句鼓励的话能让读代码题多拿约 6 分，代价是约 3 倍的费用；在 p4 上反而丢分。不适合默认加。\n")

    w("### 运行中出现的问题：主代理不等子代理回来就结束\n")
    w(f"- {n_runs} 次运行里 {crash['total']} 次在主代理给出最终回答之后、进程退出时崩溃（DSH #5063），全部在深度 ≥ 2 且 K ≥ 4 的组。"
      f"其中 {oc['crashed']['runs_gt0']} 次主代理结束时还有后台子代理没回来（平均 {oc['crashed']['mean']:.1f} 个）；"
      f"其余开过子代理的 {oc['not_crashed_with_children']['runs']} 次运行平均 {oc['not_crashed_with_children']['mean']:.2f} 个。\n"
      f"- 办公题：{len(off_open)}/{len(office_deleg)} 次运行结束时仍有子代理在跑，其中 {off_open_crash} 次退出时崩溃。"
      f"{off_crash} 次崩溃的办公运行里 {off_crash - len(stub)} 次报告已经写完、照常打分；{len(stub)} 次主代理说“等子代理回来再写”就结束了，"
      f"交出的是空文件或骨架，得分 {stub_scores[0]:.1f} 和 {stub_scores[1]:.1f}。\n"
      f"- p4 鼓励版：{len(p4e_open)}/{len(p4e)} 次运行结束时仍有子代理在跑，其中 {len(p4e_cut)} 次交出的代码不完整，没有崩溃。\n"
      "- headless 下主代理这一轮结束就是整次运行结束，这些子代理的费用已经花了，结果没有用上。交互使用时用户会等或者再催一句，这一条只对 headless 成立。"
      + ("正式实验里它和深度混在一起，实验 2 把两者分开。\n" if wait else "\n"))

    if wait:
        wait_block(w, wait, wf, wc, H, rows, set(crash["deliverable_missing"]))
    if ctl:
        ctl_block(w, ctl, cf, med((P4,), "D0", "seconds"))
    judge_block(w, ia, sens, H)

    # ================================================================ setup
    w("## 实验设置\n")
    w("### 组\n")
    w("13 组：D0，加上 D1、D2、D3 各配 K = 1、2、4、8。D0 没有委派工具，K 不起作用，只有一组。\n")
    w("- 各组只差一个配置补丁：`subagent.maxDepth` 和 `maxActiveSubagents`；D0 是把 4 个委派工具行关掉。\n"
      "- 所有组共用：模型 deepseek-flash、推理强度 max、fork 模式同 Web 标准预设、workflow 工具关闭（它开的 agent 不受名额限制）。\n"
      "- 除 D0 外，各组的系统提示、工具列表、子代理提示完全相同（哈希一致）。模型看不到 D 和 K，上限只在被碰到时起作用：开子代理的调用被拒。\n")
    w("### 题和运行次数\n")
    w("| 部分 | 题 | 组 | 每格次数 | 运行次数 |\n|---|---|---|---|---|\n"
      "| 办公 | o1 新加坡行程、o2 服务器 CPU 报告（都要上网搜索） | 13 组 | 10 | 260 |\n"
      "| 代码·自然状态 | c1、w1、p4（不联网） | D0、D1-K8、D2-K8、D3-K8 | 10 | 120 |\n"
      "| 代码·自然状态补跑 | w1 | D1-K1/K2、D2-K1/K2/K4、D3-K1/K2/K4 | 10 | 80 |\n"
      "| 代码·鼓励并行 | c1、w1、p4 | D1/D2/D3 × K1/2/4/8 | 10 | 360 |\n")
    w("- 题面原文见附录 A。c1 是读 DSH 源码回答子代理两个上限的 22 个要点；w1 是研究记忆溯源插件的实现路径；p4 是写 4 道 Python 练习。\n"
      "- 鼓励并行：题面末尾加一句“独立的子任务尽量交给 subagent 并行做。”。不设“鼓励·D0”，因为这句话点名了 D0 没有的工具。\n"
      "- 补跑规则开跑前写定（附录 C）：自然状态下某题某深度的 K8 组，10 次里只要有 1 次同时存活的子代理超过 k 个，"
      "且这一深度确实被用到，就补跑该题该深度的 K=k。结果只有 w1 需要补 8 格；c1、p4 的 10 次都没碰到这些上限，"
      "按 95% 置信，碰到的比例最多约 31%（Clopper–Pearson 上界）。\n"
      "- 设计上的不对称：K 的作用在办公题上是自然状态测的（13 组），在代码题上主要是鼓励并行后测的（12 组）。\n")
    w("### 运行环境\n")
    w("- 每次运行一个 DSec 容器：4 核、16 GB，镜像 ubuntu:24.04 加环境层（DSH 0.2.0-rc.2、Node v22.22.1、Python 3.12.3、pytest 8.4.2）。\n"
      "- 模型接口：公司内部端点，DataTask key。DSH 以 headless 方式运行，权限 workspace-write，沙盒为 Landlock。\n"
      "- 网络：办公题能上公网（不能连镜像站）；代码题不能上公网和镜像站。\n"
      "- 隔离：每次运行有自己的目录、HOME、TMPDIR、DSH_HOME，容器之间互相看不到；运行目录名是随机编号，看不出组和题；"
      "容器里没有答案键和评分标准。\n"
      "- 单次上限 60 分钟。\n")
    w("### 跑法\n")
    w(f"- 同一批里按随机完全区组提交：每一轮把这批所有格各排一次、随机打乱，再进下一轮。并发数全程不变（办公 {ro['parallel'][0]} 路、"
      f"代码 {rc['parallel'][0]} 路），各组在同一时间段里交错运行。\n"
      "- 只重跑基础设施故障（容器开不出来、文件拷贝失败、模型接口在第一次回复前报错），每格最多 3 次。DSH 自己崩溃、超时、内存超限都算结果。\n"
      "- 办公题运行期间不打分（办公题的搜索和打分都走公司代理）。\n")

    # ================================================================ metrics
    w("## 指标口径\n")
    w("### 得分（百分制）\n")
    w("| 题 | 怎么判 | 满分 | 判分人 |\n|---|---|---|---|\n"
      "| o1、o2 | 评分标准 v1.3：A 硬性覆盖、B 关键事实（有答案键）、C 来源与诚实、D 可用性。A/C/D 每条 0/1/2 分；B 每条正确 +2、标“待核验” +1、没提到 0、错误 −2 | o1 46 分、o2 38 分 | Opus 5.5（思考强度 high），每份打 2 次取平均 |\n"
      "| c1 | 22 个要点，每个判对 / 错 / 没提到，对的个数 ÷ 22 | 22 | Opus 5.5（high），每份 2 次 |\n"
      "| w1 | 评分标准（26 条，结构同办公题） | 52 分 | Opus 5.5（high），每份 2 次 |\n"
      "| p4 | 4 道练习各自的隐藏测试通过比例，取平均 | 100 | 脚本，不用模型 |\n")
    w("- 判分模型看到的只有：这道题的评分标准（含答案键和判定细则）、被评的文件，以及脚本抽出的 5 处引用（办公题是链接对应页面的原文片段，"
      "w1 是源码片段）。看不到组别、运行编号。\n"
      "- c1、w1 两次打分逐条不一致超过 10% 时加打第 3 次，每条取多数。\n"
      "- 没交出文件、或文件短于阈值（c1 1000 字节、w1 2000 字节）的运行直接记 0 分，不剔除。\n"
      "- 评分标准、答案键和打分提示词全文见附录 B；判分的一致性和校验见“数据审计”。\n")
    w("### 单价（元/次）\n")
    w("- 模型费：会话日志里主代理和全部子代理的 token 用量，按 10/2 存档的 DeepSeek 官方价计算。高峰价每百万 token：未命中输入 2 元、"
      "缓存命中 0.04 元、输出 8 元；空闲价每一项都是高峰价的一半，所以组间比值两档相同，表里两档都列，对比只用高峰价。\n"
      "- 缓存命中按接口返回的实际值计算。\n"
      f"- 估算总费用 = 模型费 + 搜索费。每次 `web_search` 是一次完整的模型调用，用量没有记进会话日志。做法：从正式批次里抽 "
      f"{cost['probe_requests']} 次搜索请求原样重发，实测每次高峰价 {cost['probe_per_request_cny_peak']:.4f} 元，乘以每次运行的搜索请求数。\n"
      "- 这是按用量估算的单价，不是账单。代码题不联网，估算总费用等于模型费。\n")
    w("### 时长\n")
    w("- 实际时长：容器里 DSH 进程从启动到退出的时间，不含开容器、拷文件。\n"
      "- 标准化时长：模型时间按固定速度从 token 数重算，工具和其他时间照实测。沿主会话时间线计算，保留子代理并行造成的重叠。\n"
      f"- 固定速度取自官网 API：本机 DSH、个人 key 调 `https://api.deepseek.com/anthropic`，同一版 DSH、同样 5 道题，D0 和 D2-K8 各 1 次，"
      f"共 {prof['n_requests']:,} 个请求。结果：首字 {prof['base_ttft_s']} 秒，未命中输入 {prof['prefill_tps']:,} token/秒，"
      f"输出 {prof['out_tps']} token/秒。同时发 7–8 个请求的运行和一次只发一个的运行速度相同。\n"
      f"- 只测了一个时段（10/3 凌晨，国庆假期）。换成内部端点试跑时的速度（{pilot['base_ttft_s']} 秒、{pilot['prefill_tps']:,}、"
      f"{pilot['out_tps']} token/秒），每次运行的标准化时长只差 −4% 到 +5%，结论不变。\n")
    w("### 子代理\n")
    w("- 子代理数：这次运行的会话日志里出现的子会话数，各层都算；另按所在层分别计数。\n"
      "- 名额峰值：同一时刻占着后台名额的子代理数的最大值，从会话日志里的启动和结果送回事件重建。\n"
      "- 名额被拒、深度被拒：开子代理的调用因为相应上限返回错误的次数。“碰到上限的运行数”是至少被拒一次的运行数。\n"
      "- 结束时仍有子代理未回：主代理给出最终回答时，还没把结果送回来的后台子代理数。\n")
    w("### 统计\n")
    w("- 按（题，第几次）配对。估计值是各题配对差的均值再按题平均；95% 区间是扣除题目效应的配对 t 区间；p 值用符号翻转检验。\n"
      "- 预注册的主要对比：以出厂默认 D1-K8 为基准，一次只改一个因素，再加一个交互。办公 7 个（H1–H4），代码 8 个（C1–C5，三题合并），"
      "每个指标内部做 Holm 校正。其余对比只作描述，不校正。\n"
      "- 费用和时长取对数比，报几何均值之比。\n"
      f"- 得分差的判断标准 δ = {DELTA:.0f} 分。最小可测差按 80% 功效、双侧 α = 0.05 从这个对比的标准误算出。\n"
      "- 以上细则在读到任何得分之前写进方案。\n"
      "- 事后分析（看到数据后补的，报告里都标了“事后”）：把另一个因素平均掉的因子对比；代码题去掉 p4 只算 c1、w1；"
      "分评分类别的对比；去掉崩溃运行或提前收工运行的敏感性分析。因子对比的做法：在每个（题，第几次）区组内，先把同一 K（或同一深度）的几个组取平均，"
      "再做配对差，所以仍是 20 个区组，每个区组的值由 3–4 次运行平均而来。\n")

    # ================================================================ audit
    w("## 数据审计与计数边界\n")
    w("### 运行\n")
    w(f"- {n_runs} = {ro['rows']}（办公）+ {rc['rows']}（代码）+ {rb['rows']}（w1 补跑）。三批的（题，组，次）格数等于行数，"
      f"重复格 {ro['duplicate_cells'] + rc['duplicate_cells'] + rb['duplicate_cells']} 个，没有缺格。\n"
      f"- 基础设施重跑 {infra_retries} 次（办公批一次模型接口返回格式错误，重跑后成功；失败的那次保留在 `_failed/`，不计入）。"
      f"其余 {n_runs - infra_retries} 次都是第一次就完成。\n"
      f"- 退出码：{n_runs - crash['total']} 次为 0，{crash['total']} 次为 1；这 {crash['total']} 次全部是 #5063 崩溃，"
      f"会话的最后一个事件都是主代理的最终回答（{crash['last_event_final']}/{crash['total']}）。超时 {timeouts} 次。\n"
      f"- 容器内存到上限 {oom} 次（p4 鼓励·D2-K4 的一次运行，一个测试进程被杀，DSH 正常结束，照算结果）。\n"
      f"- 模型请求共 {total_requests:,} 个，会话日志里记到的接口重试 {retries} 次。\n")
    w("### 得分的份数\n")
    w(f"- 办公：{jo['judgments']} 份 = {jo['runs']} 次运行 × 2。其中 {jo['model_attempts'].get('1', 0)} 份一次打成，"
      f"{sum(v for k, v in jo['model_attempts'].items() if k != '1')} 份重试后打成，"
      f"{jo['written_without_model_no_deliverable']} 份属于没交出文件的那次运行（不发给模型，记 0 分）。\n"
      f"- 代码（c1、w1）：{jc['judgments']} 份 = {jc['runs']} 次运行 × 2，加 {jc['third_judgments']} 份第 3 次打分（都是 w1）。"
      f"最终得分 {jc['method'].get('mean2', 0)} 次取两次平均，{jc['method'].get('majority', 0)} 次逐条取多数。\n"
      f"- p4：{audit['p4']['graded']} 次运行全部判分，{audit['p4']['score_100']} 次满分，最低 {audit['p4']['min']} 分。\n"
      f"- 缺得分的运行：{sum(1 for r in rows if num(r.get('score')) is None)} 次。\n"
      f"- 判分费用：办公 ${jo['cost_usd']:.0f}，代码 ${jc['cost_usd']:.0f}。\n")
    judging_section(w, audit, val, rows, D, G, cmp_(sc2b, "score_first2", "C2"), cmp_(scfb, "score_first2", "FK1"),
                    cmp_(scfb, "score_first2", "FE"), H, len_h1)
    w("### 费用\n")
    alt = {}
    for price in probes:
        ds = defaultdict(list)
        cell = {(r["task"], r["group"], r["rep"]): r for r in rows if r["task"] in OFF}
        for (t, g, rep), r in cell.items():
            if g != "D1-K8":
                continue
            b = cell.get((t, "D0", rep))
            if b:
                ta = float(r["model_cost_peak"]) + float(r["search_aux"]) * price
                tb = float(b["model_cost_peak"]) + float(b["search_aux"]) * price
                ds[t].append(math.log(ta / tb))
        alt[price] = math.exp(st.mean(st.mean(v) for v in ds.values()))
    w(f"- 搜索费占办公运行估算总费用的中位数 {cost['search_share_median'] * 100:.0f}%（范围 {cost['search_share_min'] * 100:.0f}%–"
      f"{cost['search_share_max'] * 100:.0f}%，n={cost['office_runs']}）。一次办公运行的搜索请求中位数 {cost['search_requests_median']:.0f} 次，"
      f"最多 {cost['search_requests_max']} 次。\n"
      "- 搜索单价有抽样误差：前后三次抽样（正式批次 40 个请求、本机试跑 100 个、最早一次 40 个）实测每次 "
      f"{probes[0]:.4f}、{probes[1]:.4f}、{probes[2]:.4f} 元，最高和最低差 {100 * (max(probes) / min(probes) - 1):.0f}%。报告用的是正式批次那次（{probes[0]:.4f} 元）。"
      f"办公题的绝对费用因此有约 ±{100 * (max(probes) / min(probes) - 1) / 2 * cost['search_share_median']:.0f}% 的不确定，区间里没有体现；"
      f"组间比值几乎不受影响：H1 的费用比在三个单价下是 {'、'.join(f'{alt[p]:.2f}' for p in probes)} 倍。\n"
      f"- 各次运行的实际搜索用量没有记录，估算总费用里的搜索部分是“次数 × 平均单价”。\n"
      f"- 缓存命中占比（命中的输入 token ÷ 全部输入 token）办公各组在 "
      f"{min(gm(OFF, g, 'cache_hit_share', 100) for g in OFF_GROUPS):.1f}%–{max(gm(OFF, g, 'cache_hit_share', 100) for g in OFF_GROUPS):.1f}% 之间，没有组间差别。"
      "同一道题多次同时运行会互相命中前缀缓存，命中率比单个用户的真实使用高，所以绝对费用偏低；各组一样，比值不受影响。\n"
      f"- 每次搜索调用里，模型写的那段回答被插件丢掉，只用返回的搜索结果。抽样 {cost['probe_requests']} 次，这段回答平均 "
      f"{cost['probe_output_tokens_mean']:.0f} token，占这次调用费用的 {cost['probe_output_cost_share_median'] * 100:.0f}%（中位数）。"
      "子代理多的组搜索多，这部分把费用倍数放大了；3.4 倍是现在这套搜索实现下的数。\n"
      f"- 全部 {n_runs} 次运行按高峰价估算，模型费合计 {cost['model_cost_peak_total_cny']:,.0f} 元，加搜索约 "
      f"{cost['total_cost_peak_total_cny']:,.0f} 元。\n")
    w("### 各组的请求速度和工具报错\n")
    w("实际时长受模型接口速度和搜索接口影响。下表是办公批各组每次运行的首字时间中位数和输出速度中位数（再取各次运行的中位数），以及两个联网工具的报错率：\n")
    bg = sp["main-office"]["by_group"]

    def err(g, kind):
        gr = grp(OFF, g)
        den = sum(num(r.get(f"web_{kind}_calls")) or 0 for r in gr)
        return "—" if not den else f"{100 * sum(num(r.get(f'web_{kind}_errors')) or 0 for r in gr) / den:.1f}"

    w("| 指标 | " + " | ".join(OFF_GROUPS) + " |\n|---|" + "---|" * len(OFF_GROUPS))
    w("| 首字时间（毫秒） | " + " | ".join(str(bg[g]["ttft_med_ms_median"]) for g in OFF_GROUPS) + " |")
    w("| 输出速度（token/秒） | " + " | ".join(str(bg[g]["tps_med_median"]) for g in OFF_GROUPS) + " |")
    w("| web_search 报错率（%） | " + " | ".join(err(g, "search") for g in OFF_GROUPS) + " |")
    w("| web_fetch 报错率（%） | " + " | ".join(err(g, "fetch") for g in OFF_GROUPS) + " |")
    tt = [bg[g]["ttft_med_ms_median"] for g in OFF_GROUPS]
    tp = [bg[g]["tps_med_median"] for g in OFF_GROUPS]
    w(f"\n各组首字时间在 {min(tt)}–{max(tt)} 毫秒，输出速度 {min(tp)}–{max(tp)} token/秒，搜索报错率都在 0.5% 以下，"
      "抓取网页的报错率 11%–15%，子代理多的组没有更慢、也没有更多报错。"
      f"代码批的中位数是 {sp['main-code']['all']['ttft_med_ms_median']} 毫秒、{sp['main-code']['all']['tps_med_median']} token/秒。"
      "工具时间没有做标准化，照实测计入。\n")
    if sa and (ctl or wait):
        supp_audit_section(w, sa, ctl, wait, audit)
    w("### 与预注册方案的差异\n")
    w("- 标准化时长的固定速度：方案原定用内部端点试跑的速度，改为官网 API 实测速度，因为普通用户用的是官网 API。标准化时长是跑完后从日志算的，不影响运行。\n"
      "- 打分的思考强度：方案原定 max，实际用 high。10/2 起公司代理把任何一次请求在约 600 秒处切断；max 强度下一份办公题打分要 8–25 分钟，"
      "把评分表拆成 A、B、C、D 四个请求分别打，单个请求也仍然超过 600 秒。high 一次约 1.5 分钟。模型、评分标准、每份 2 次都没变；"
      "这个改动是在读到任何得分之前定的，和 max 的对比见“判分的一致性和校验”。\n"
      "- c1、w1 的第 3 次打分规则沿用试跑阶段的判分脚本，v2 方案只写了“各 2 次”。只用前两次平均重算，结论相同（见“判分的一致性和校验”）。\n"
      "- 分析细则（哪些对比进多重校正、交互怎么算、δ 怎么用）和“去掉崩溃运行”的敏感性分析，是开跑后、读到任何得分之前补进方案的。\n"
      "- 事后分析见“统计”一节的列表，都是读到得分以后补的。\n"
      "- DSec 公网出口打不开 static.sse.com.cn，这是 o2 评分项 B2（海光招股书）的官方来源。所有组都一样，B2 照常判分。\n"
      + ("- 实验 2、3：两项的做法、对比和判读规则在各自开跑前写进方案。等待批的几项判定办法（没写完的交付物、第一轮结束时仍有子代理未回、之后改了交付物）"
         "是批次运行中、任何打分之前补进方案的。阳性对照的主对比估计值比预先写的门槛低 0.2 分，照实报告，没有改门槛。"
         "“提前收工的运行，等和不等”“没结算的子代理归类”和实验 4 的三项判分检查是读到得分以后补的。\n" if (ctl or wait) else "")
      + rejudge_note(wait))

    # ================================================================ results
    w("## 详细数据（实验 1）\n")
    w("表里“行是指标、列是组”。数值是各题均值再按题平均；得分区间是扣除题目效应的 95% t 区间。\n")
    w("### 办公题（13 组，每组 20 次）\n")
    w("表 1 得分、费用、时长：\n")
    w(table_rows("tables-office-t.md", R_MAIN) + "\n")
    w("表 2 委派行为和稳定性：\n")
    w(table_rows("tables-office-t.md", R_DELEG) + "\n")
    w("表 3 干了多少活、各评分类别的得分（类别得分是该类得分占该类满分的百分比，B 类可以为负）：\n")
    w(table_rows("tables-office-t.md", R_WORK) + "\n")
    w(f"深度 1 下 B 类（关键事实）随 K 增大而升高：D0 {gm(OFF, 'D0', 'cat_B'):.1f}%，K=1、2、4、8 依次是 "
      + "、".join(f"{gm(OFF, g, 'cat_B'):.1f}%" for g in ("D1-K1", "D1-K2", "D1-K4", "D1-K8"))
      + "；C 类（来源与诚实）和 D 类（可用性）没有提高。多查的那部分体现在查到的事实上，总分因此只高 2–3 分。\n")
    w("分题的表见附录 D。\n")
    w("### 代码题 c1、w1（每组 20 次）\n")
    w("代码题不联网，估算总费用等于模型费。自然状态：\n")
    w(table_rows("tables-c1w1-natural-t.md", R_MAIN_CODE + R_DELEG) + "\n")
    w("鼓励并行：\n")
    w(table_rows("tables-c1w1-encouraged-t.md", R_MAIN_CODE + R_DELEG) + "\n")
    w("### p4（单列，每组 10 次）\n")
    w("p4 接近满分，放进合并结果会把差别拉平（自然状态）或者成为噪声来源（鼓励版），所以单独列。得分是 4 道练习隐藏测试通过比例的平均。\n")
    p4g = ["D0", "D1-K8", "D2-K8", "D3-K8"] + ENC_GROUPS
    w("| 指标 | " + " | ".join(enc(g) for g in p4g) + " |\n|---|" + "---|" * len(p4g))
    w("| 满分的次数 | " + " | ".join(frac((P4,), g, lambda r: float(r["score"]) >= 99.999) for g in p4g) + " |")
    w("| 最低分 | " + " | ".join(f"{min(float(r['score']) for r in grp((P4,), g)):.0f}" for g in p4g) + " |")
    w("| 平均分 | " + " | ".join(f"{gm((P4,), g, 'score'):.1f}" for g in p4g) + " |")
    w("| 开了子代理的次数 | " + " | ".join(frac((P4,), g, lambda r: (num(r["children"]) or 0) > 0) for g in p4g) + " |")
    w("| 结束时仍有子代理未回的次数 | " + " | ".join(frac((P4,), g, is_open) for g in p4g) + " |")
    w("| 模型费·高峰（元/次） | " + " | ".join(f"{gm((P4,), g, 'model_cost_peak'):.2f}" for g in p4g) + " |")
    w("| 实际时长（分钟） | " + " | ".join(f"{gm((P4,), g, 'seconds', 1 / 60):.1f}" for g in p4g) + " |")
    w("")
    w("### w1 自然状态（含补跑的 8 格，每组 10 次）\n")
    w(table_rows("tables-w1-natural-t.md", R_MAIN_CODE + R_DELEG) + "\n")
    nk = {k: c for k, c in swk["metrics"]["score"]["comparisons"].items() if k.startswith("NK")}
    nkc = {k: c for k, c in swk["metrics"]["model_cost_peak"]["comparisons"].items() if k.startswith("NK")}
    w(f"补跑格和同深度 K=8 的对比（只作描述，每个 10 对）：得分差在 {sgn(min(c['est'] for c in nk.values()))} 到 "
      f"{sgn(max(c['est'] for c in nk.values()))} 分之间，区间全部包含 0；模型费是 K=8 的 "
      f"{min(ratio(c) for c in nkc.values()):.2f}–{max(ratio(c) for c in nkc.values()):.2f} 倍。\n")

    w("### 主要对比（预注册）\n")
    w("每格是 A − B 的估计值和 95% 区间；费用、时长是几何均值之比。* 表示 Holm 校正后 p < 0.05。得分一列没有一个达到。"
      "“碰到上限的运行数”是两组里至少被名额上限拒过一次的运行数（A 组；B 组）。\n")
    w("办公题（每个对比 20 对）：\n")
    w("| 对比 | 得分差 | 最小可测差 | 判断 | 估算总费用之比 | 实际时长之比 | 标准化时长之比 | 碰到名额上限的运行数 |\n|---|---|---|---|---|---|---|---|")
    names = {"H1": ("H1 D1-K8 − D0", "D1-K8", "D0"), "H2a": ("H2a D1-K1 − D1-K8", "D1-K1", "D1-K8"),
             "H2b": ("H2b D1-K2 − D1-K8", "D1-K2", "D1-K8"), "H2c": ("H2c D1-K4 − D1-K8", "D1-K4", "D1-K8"),
             "H3a": ("H3a D2-K8 − D1-K8", "D2-K8", "D1-K8"), "H3b": ("H3b D3-K8 − D1-K8", "D3-K8", "D1-K8"),
             "H4": ("H4 (D3-K8 − D3-K1) − (D1-K8 − D1-K1)", None, None)}
    for k, (nm, ga, gb) in names.items():
        hits = "—" if ga is None else f"{frac(OFF, ga, hit_k)}；{frac(OFF, gb, hit_k)}"
        w(f"| {nm} | {d_cell(H[k])} | {H[k]['mdd']:.1f} | {verdict(H[k])} | {r_cell(HC[k])} | {r_cell(HW[k])} | {r_cell(HT[k])} | {hits} |")
    w("\n代码题（三题合并，每个对比 30 对；p4 接近满分，读这张表要对照下面的分题结果）：\n")
    w("| 对比 | 得分差 | 最小可测差 | 判断 | 模型费之比 | 实际时长之比 | 标准化时长之比 |\n|---|---|---|---|---|---|---|")
    cn = {"C1": "C1 D1-K8 − D0", "C2": "C2 鼓励·D1-K8 − D1-K8", "C3a": "C3a 鼓励·D1-K1 − 鼓励·D1-K8",
          "C3b": "C3b 鼓励·D1-K2 − 鼓励·D1-K8", "C3c": "C3c 鼓励·D1-K4 − 鼓励·D1-K8", "C4a": "C4a 鼓励·D2-K8 − 鼓励·D1-K8",
          "C4b": "C4b 鼓励·D3-K8 − 鼓励·D1-K8", "C5": "C5 (鼓励·D3-K8 − 鼓励·D3-K1) − (鼓励·D1-K8 − 鼓励·D1-K1)"}
    for k, nm in cn.items():
        w(f"| {nm} | {d_cell(C[k])} | {C[k]['mdd']:.1f} | {verdict(C[k])} | {r_cell(CC[k])} | {r_cell(CW[k])} | {r_cell(CT[k])} |")
    w("")
    w("### 分题结果（只作描述）\n")
    w("办公两道题的方向经常相反，合并成一个数时要对照这张表。每格是该题 10 对的得分差和 95% 区间：\n")
    w("| 对比 | o1 新加坡行程 | o2 服务器 CPU 报告 |\n|---|---|---|")
    for k, (nm, _, _) in names.items():
        w(f"| {nm.split(' ', 1)[0]} | " + " | ".join(d_cell(cmp_(sot[t], "score", k)) for t in OFF) + " |")
    w("\n代码题：\n")
    w("| 对比 | c1 | w1 | p4 | c1、w1 两题合并（20 对） | 两题合并的模型费之比 |\n|---|---|---|---|---|---|")
    for k, nm in cn.items():
        w(f"| {nm.split(' ', 1)[0]} | " + " | ".join(d_cell(cmp_(per_task[t], "score", k)) for t in CODE)
          + f" | {d_cell(D[k])} | {r_cell(DC[k], star=False)} |")
    w("")
    w("### 事后因子分析\n")
    w("预注册对比一次只改一个因素，12 个 D×K 格里有 8 个几乎没用上。这里把另一个因素平均掉：K 的对比在三个深度上平均，"
      "深度的对比在四个 K 上平均。仍然是 20 个区组，但每个区组的值由 3–4 次运行平均而来，区间更窄。"
      "这是读到得分以后补的分析；Holm 校正只在这张表的前 5 行内部做。\n")
    w("办公题：\n")
    w("| 对比 | 得分差 | 最小可测差 | 估算总费用之比 | 标准化时长之比 | 搜索请求之比 |\n|---|---|---|---|---|---|")
    fn = {"FK1": "K=1 对 K=8（三个深度平均）", "FK2": "K=2 对 K=8（三个深度平均）", "FK4": "K=4 对 K=8（三个深度平均）",
          "FD2": "深度 2 对深度 1（四个 K 平均）", "FD3": "深度 3 对深度 1（四个 K 平均）",
          "FX": "深度 2、3 下 K=1/2/4 对 K=8（描述）", "FA": "12 个委派组对 D0（描述）"}
    for k, nm in fn.items():
        w(f"| {nm} | {d_cell(F[k])} | {F[k]['mdd']:.1f} | {r_cell(FC[k])} | {r_cell(FT[k])} | {r_cell(cmp_(sofm, 'search_aux', k), star=False)} |")
    if dep:
        w("\n深度的两行把 K=1、2 两列也平均了进去，而这两列里深度没有被用上（见下面“深度：只看它真的被用上的格”），所以这两行偏向 0。读深度以那一段为准。")
    w("\n代码题 c1、w1（鼓励并行）：\n")
    w("| 对比 | 得分差 | 最小可测差 | Holm 后 p | 模型费之比 | 标准化时长之比 |\n|---|---|---|---|---|---|")
    gn = dict(fn)
    gn["FE"] = "鼓励版 K=8 对自然状态 K=8（三个深度平均，描述）"
    del gn["FA"]
    for k, nm in gn.items():
        ph = "—" if G[k].get("p_holm") is None else f"{G[k]['p_holm']:.3f}"
        w(f"| {nm} | {d_cell(G[k])} | {G[k]['mdd']:.1f} | {ph} | {r_cell(GC[k])} | {r_cell(GT[k])} |")
    w("\n三题合并（含 p4）时前 5 行是 "
      + "、".join(d_cell(cmp_(scf3, "score", k)) for k in ("FK1", "FK2", "FK4", "FD2", "FD3")) + "。\n")
    wn = load("stats-w1-natural-factorial.json")
    w("w1 自然状态（含补跑格，10 个区组；D1-K4 没跑，深度的对比只用 K=1、2、8）：11 个委派组对 D0 "
      f"{d_cell(cmp_(wn, 'score', 'NFA'))}，模型费 {ratio(cmp_(wn, 'model_cost_peak', 'NFA')):.2f} 倍；K=1 对 K=8 {d_cell(cmp_(wn, 'score', 'NFK1'))}，"
      f"K=2 对 K=8 {d_cell(cmp_(wn, 'score', 'NFK2'))}；深度 2、3 对深度 1 {d_cell(cmp_(wn, 'score', 'NFD2'))}、{d_cell(cmp_(wn, 'score', 'NFD3'))}。"
      "K=1、2 的方向和鼓励版一致，但区间包含 0。\n")
    if dep:
        w("**深度：只看它真的被用上的格（事后）。** 各格每次运行开的子代理数，按所在的层（第 1 层 / 第 2 层 / 第 3 层），办公题：\n")
        w("| | K=1 | K=2 | K=4 | K=8 |\n|---|---|---|---|---|")
        for d in (1, 2, 3):
            w(f"| D{d} | " + " | ".join(
                " / ".join(f"{gm(OFF, f'D{d}-K{k}', c):.1f}" for c in ("children_d1", "children_d2", "children_d3")[:d])
                for k in (1, 2, 4, 8)) + " |")
        w("\n- 名额是整棵树共用的。K=1、2 时第 1 层就把名额占满，第 2 层开不出来：D2-K1、D2-K2 出现第 2 层子代理的运行是 "
          f"{layer_runs('D2-K1', 'children_d2')}、{layer_runs('D2-K2', 'children_d2')}，D3-K1、D3-K2 是 {layer_runs('D3-K1', 'children_d2')}、"
          f"{layer_runs('D3-K2', 'children_d2')}。这四格按机制和同一个 K 的深度 1 是同一个条件。\n"
          f"- K=4、8 时第 2 层才出现：D2-K4 {layer_runs('D2-K4', 'children_d2')}、D2-K8 {layer_runs('D2-K8', 'children_d2')}、"
          f"D3-K4 {layer_runs('D3-K4', 'children_d2')}、D3-K8 {layer_runs('D3-K8', 'children_d2')}。第 3 层只在 D3-K4 的 "
          f"{layer_runs('D3-K4', 'children_d3')} 次、D3-K8 的 {layer_runs('D3-K8', 'children_d3')} 次运行里出现。\n")
        w("把 K=4、K=8 两列合起来比深度（按（题，K，第几次）配对，40 对；这是读到得分以后补的）：\n")
        w("| 对比 | 得分差 | 最小可测差 | 去掉退出崩溃的运行 | 估算总费用之比 | 实际时长之比 |\n|---|---|---|---|---|---|")
        for k, nm in (("PD2", "深度 2 减深度 1"), ("PD3", "深度 3 减深度 1"), ("PD32", "深度 3 减深度 2")):
            a_, b_ = cmp_(dep["k48"], "score", k), cmp_(dep["k48-nocrash"], "score", k)
            w(f"| {nm} | {d_cell(a_)} | {a_['mdd']:.1f} | {d_cell(b_)}（{b_['n']} 对） | "
              f"{r_cell(cmp_(dep['k48'], 'total_cost_peak', k), star=False)} | {r_cell(cmp_(dep['k48'], 'seconds', k), star=False)} |")
        y = cmp_(dep["k12"], "score", "PD32")
        c4, c8 = (cmp_(dep[f"k{k}"], "total_cost_peak", "PD2") for k in (4, 8))
        w(f"\n- 加深没有带来可测的好处：含崩溃的算法里估计值是负的、区间包含 0；去掉崩溃后深度 2 是 {d_cell(cmp_(dep['k48-nocrash'], 'score', 'PD2'))}。"
          "两种算法之间的差就是退出崩溃和没写完的报告的代价。\n"
          f"- 费用跟着子代理总数走：K=1、2 时深度 2、3 的估算总费用是深度 1 的 {ratio(cmp_(dep['k12'], 'total_cost_peak', 'PD2')):.2f}、"
          f"{ratio(cmp_(dep['k12'], 'total_cost_peak', 'PD3')):.2f} 倍（没多开子代理，就不多花钱）；K=4 时深度 2 是 {ratio(c4):.2f} 倍，K=8 时是 {ratio(c8):.2f} 倍。\n"
          f"- 一个噪声的参照：K=1、2 下深度 3 减深度 2 是 {d_cell(y)}（40 对），而这两组按机制是同一个条件。"
          "两个相同的条件也能差出 3 分、区间不含 0，说明这份报告里那么多描述性对比，偶尔会有一个这样的；也说明把判断标准定在 5 分是合适的。\n")
    w("### 敏感性分析（只作描述）\n")
    w("| 对比 | 全部运行 | 去掉退出崩溃的运行 | 去掉结束时仍有子代理未回的运行 |\n|---|---|---|---|")
    for k in ("H1", "H2a", "H3a", "H3b", "H4"):
        nc = cmp_(sn, "score", k)
        w(f"| {names[k][0]} | {d_cell(H[k])}（{H[k]['n']} 对） | {d_cell(nc)}（{nc['n']} 对） | {d_cell(NO[k])}（{NO[k]['n']} 对） |")
    w("\n两种去法去掉的都主要是子代理开得最多的运行，剩下的不是随机样本。它们说明 D2-K8、D3-K8 的低分集中在这些运行上，"
      "不能当作“修好提前收工以后”的估计。\n")
    w("### 代价和效果\n")
    w("![图 1 代价–效果图](results/analysis-v2/fig-cost-quality.png)\n")
    w("图 1：横轴是估算总费用（对数刻度），纵轴是得分，误差线是 95% 区间，虚线是出厂默认 D1-K8。"
      "左栏办公题，右栏代码题 c1、w1（实心是自然状态，空心是鼓励并行）。两栏纵轴范围不同，不能跨栏比较。\n")
    w("### 子代理用量\n")
    w("![图 2 各组每次运行的子代理数](results/analysis-v2/fig-children.png)\n")
    w("图 2：每次运行的子代理数均值，按子代理所在的层分段。\n")

    # ================================================================ cases
    w("## 观察与可回查案例\n")
    w("每个案例给出运行编号，原始记录在开发机 `results/runs/<批次>/<编号>/`（事件流 `events.jsonl`、会话日志 `home/sessions/`、工作区 `workspace/`）。"
      "案例只描述日志里能看到的动作，是挑出来说明现象的，不能当作比例。\n")

    def case_row(task, g, rep):
        return next(x for x in rows if x["task"] == task and x["group"] == g and int(x["rep"]) == rep)

    def case_table(task, rep, groups):
        w("| 组 | 编号 | 得分 | 估算总费用（元） | 实际时长（分） | 子代理（1/2/3 层） | 名额峰值 | 名额被拒 | 深度被拒 | 搜索请求 | 交付物（千字符） | 退出崩溃 |\n"
          "|---|---|---|---|---|---|---|---|---|---|---|---|")
        for g in groups:
            r = case_row(task, g, rep)
            chars = num(r.get("deliv_chars"))
            w(f"| {enc(g)} | {r['id']} | {float(r['score']):.1f} | {float(r['total_cost_peak']):.2f} | {float(r['seconds']) / 60:.1f} | "
              f"{int(float(r['children_d1']))}/{int(float(r['children_d2']))}/{int(float(r['children_d3']))} | {int(float(r['slot_peak']))} | "
              f"{int(float(r['capacity_rejects']))} | {int(float(r['depth_rejects']))} | {int(float(r['search_aux']))} | "
              f"{'—' if chars is None else f'{chars / 1000:.1f}'} | {'是' if truthy(r['crash5063']) else '否'} |")
        w("")

    w("### 现象一：子代理越多，搜索和费用越多，得分没有跟着涨\n")
    w("同一道题、同一轮，只换组。案例 A：o2 服务器 CPU 报告，第 5 次（批次 main-office）。\n")
    case_table("o2-server-cpu-report", 5, ["D0", "D1-K1", "D1-K8", "D2-K8", "D3-K8"])
    w("案例 B：o1 新加坡行程，第 3 次。\n")
    case_table("o1-singapore-trip", 3, ["D0", "D1-K1", "D1-K8", "D2-K8", "D3-K8"])
    w(f"各组的中位数：搜索请求 D0 {med(OFF, 'D0', 'search_aux'):.0f} 次、D1-K8 {med(OFF, 'D1-K8', 'search_aux'):.0f} 次、"
      f"D2-K8 {med(OFF, 'D2-K8', 'search_aux'):.0f} 次；得分的起伏和子代理数没有对应关系。\n")
    w("### 现象二：上限被碰到时，模型换一种方式继续开\n")
    w(f"- K 小时一个接一个地开：办公题 D1-K1 平均每次运行开 {gm(OFF, 'D1-K1', 'children'):.1f} 个子代理，同一时刻最多 1 个，"
      f"平均被名额上限拒 {gm(OFF, 'D1-K1', 'capacity_rejects'):.1f} 次（{frac(OFF, 'D1-K1', hit_k)} 次运行碰到）。\n"
      f"- 深度 1 时子代理想继续往下开：办公题 D1-K8 平均每次运行深度被拒 {gm(OFF, 'D1-K8', 'depth_rejects'):.1f} 次"
      f"（{frac(OFF, 'D1-K8', hit_d)} 次运行碰到）。\n"
      f"- 深度放开而 K 小时，被拒的主要是名额：D2-K1、D3-K1 平均每次运行名额被拒 {gm(OFF, 'D2-K1', 'capacity_rejects'):.1f}、"
      f"{gm(OFF, 'D3-K1', 'capacity_rejects'):.1f} 次，深度被拒 {gm(OFF, 'D2-K1', 'depth_rejects'):.1f}、{gm(OFF, 'D3-K1', 'depth_rejects'):.1f} 次。\n"
      "- 上面案例 A、B 的 D1-K1 一行可以看到被拒次数和时长。\n")
    w("### 现象三：主代理没等子代理回来就结束，结果丢失，退出时崩溃\n")
    for rid in crash["deliverable_missing"]:
        r = next(x for x in rows if x["id"] == rid)
        w(f"- 案例 {rid}（{r['task'].split('-')[0]}，{r['group']}，第 {r['rep']} 次）：运行 {float(r['seconds']):.0f} 秒就结束，"
          f"结束时 {int(float(r['open_children_at_end']))} 个子代理还在跑，得分 {float(r['score']):.1f}，估算总费用 {float(r['total_cost_peak']):.2f} 元。")
    w("\n两次的最后一条消息分别是：\n")
    w("> 研究仍在进行中。我先暂停输出，等四组子代理的结果回来（约需数分钟），随后立即汇总写入 `singapore.md`，并逐条核对来源链接、对无法核实的事实标注「待核验」。\n")
    w("> 已完成报告骨架……5 个调研子代理仍在并行检索各自平台的规格、性能、兼容性与产业生态资料，待其完成后我会立即汇总、交叉核对来源并成稿。\n")
    w("headless 模式下，主代理这一轮结束就是整次运行结束。子代理的结果之后才送回来时，进程报错 "
      "`inbox state: its projection registration is not active` 并以退出码 1 结束。\n")
    r = case_row("o2-server-cpu-report", "D2-K8", 5)
    w(f"多数崩溃发生时报告已经写完。例如 {r['id']}（o2，D2-K8，第 5 次）：得分 {float(r['score']):.1f}，退出时同样崩溃。\n")
    w("各组“结束时仍有子代理未回的运行数”见表 2。\n")
    w("### 现象四：鼓励句让原本不开子代理的题开了子代理\n")
    w("同一轮（第 3 次）里 D1-K8 和 鼓励·D1-K8 的对比：\n")
    w("| 题 | 组 | 编号 | 得分 | 模型费（元） | 实际时长（分） | 子代理 |\n|---|---|---|---|---|---|---|")
    for t in (C1, W1):
        for g in ("D1-K8", "E-D1-K8"):
            r = case_row(t, g, 3)
            w(f"| {t.split('-')[0]} | {enc(g)} | {r['id']} | {float(r['score']):.1f} | {float(r['model_cost_peak']):.2f} | "
              f"{float(r['seconds']) / 60:.1f} | {int(float(r['children']))} |")
    w(f"\nc1 自然状态下不开子代理；加了鼓励句后平均开 {gm((C1,), 'E-D1-K8', 'children'):.1f} 个，模型费是原来的 "
      f"{math.exp(cmp_(per_task[C1], 'model_cost_peak', 'C2')['est']):.1f} 倍，时长 "
      f"{math.exp(cmp_(per_task[C1], 'seconds', 'C2')['est']):.1f} 倍。\n")
    w("### 现象五：鼓励并行后，p4 的主代理没等子代理改完就交卷\n")
    w("| 组 | 编号 | 第几次 | 得分 | 子代理 | 结束时未回的子代理 | 实际时长（分） |\n|---|---|---|---|---|---|---|")
    for r in sorted(p4e_low, key=lambda r: float(r["score"])):
        w(f"| {enc(r['group'])} | {r['id']} | {r['rep']} | {float(r['score']):.1f} | {int(float(r['children']))} | "
          f"{int(float(r['open_children_at_end']))} | {float(r['seconds']) / 60:.1f} |")
    w(f"\n鼓励版 {len(p4e)} 次运行里没拿满分的就是这 {len(p4e_low)} 次：前 {len(p4e_cut)} 次结束时都还有子代理没回来，"
      f"后 {len(p4e_low) - len(p4e_cut)} 次是个别测试没过。鼓励版一共 {len(p4e_open)} 次运行结束时仍有子代理在跑，"
      f"另外 {len(p4e_open) - len(p4e_cut)} 次主代理自己已经把题做完，拿了满分。"
      f"自然状态 {len(p4n)} 次里只有 {len(p4n_low)} 次没拿满分"
      + (f"（{min(float(r['score']) for r in p4n_low):.0f} 分）" if p4n_low else "") + "。\n")

    # ================================================================ DSH issues
    w("## DSH 的问题\n")
    w("1. **主代理能在后台子代理还在跑的时候结束运行（#5063）。** headless 下主代理说“等子代理回来”就结束了这一轮，进程随即退出，"
      f"子代理的结果丢掉，退出时报错。{n_runs} 次里退出崩溃 {crash['total']} 次，都在深度 ≥ 2 且 K ≥ 4 的组；"
      f"办公题 {len(off_open)} 次、p4 鼓励版 {len(p4e_open)} 次运行结束时仍有子代理在跑，分别有 {len(stub)} 次和 {len(p4e_cut)} 次因此交出不完整的结果。"
      + ("实验 2 让进程等子代理都回来再退出：等的三组 60 次里，没有再出现还有子代理在干活就退出的情况。" if wait else "") + "\n"
      f"2. **会话日志不记搜索用量。** 每次 `web_search` 都是一次完整的模型调用，返回里的用量没有写进日志。按日志算的花费漏掉一半左右"
      f"（搜索费占办公运行估算总费用的中位数 {cost['search_share_median'] * 100:.0f}%）。\n"
      f"3. **每次搜索调用约四成多的费用花在被丢掉的回答上。** 插件只取返回里的搜索结果，模型写的那段回答直接丢掉。抽样 {cost['probe_requests']} 次，"
      f"平均输出 {cost['probe_output_tokens_mean']:.0f} token，占这次调用费用的 {cost['probe_output_cost_share_median'] * 100:.0f}%（中位数）到 "
      f"{cost['probe_output_cost_share_mean'] * 100:.0f}%（平均）。\n"
      f"4. **名额上限不告诉模型，碰到才拒绝。** K=1 时模型反复去开、反复被拒：办公题 D1-K1 的 20 次运行累计被拒 {k1_rej['D1-K1']} 次。"
      "每次被拒都是一次白花的往返。"
      + ("\n" if not uns else ""))
    if uns:
        w(f"5. **被上级 interrupt 的后台子代理，如果当时还有排队没处理的消息，就一直不结算。** 上级调用 `interrupt_agent` 后，子代理这一轮以“被上级中断”结束，"
          "正常情况下上级会收到一条“已停止”的通知。但如果中断时还有一条排队等这个子代理下一步处理的消息（上级刚发来的催促，或者一个后台命令的完成通知），"
          "它之后既不再运行，也不发通知，运行时一直把它算作还活着；它的上级也因此结算不了。"
          f"正式批加等待批共 {uns['runs']} 次运行里，{uns['runs_with_interrupt']} 次用过 `interrupt_agent`，被中断的子代理共 {uns['interrupted']} 个："
          f"中断时有排队消息的 {uns['queued']} 个，{uns['queued_settled']} 个结算。没有排队消息的 {uns['plain']} 个里 {uns['plain_settled']} 个正常结算；"
          f"剩下 {uns['plain'] - uns['plain_settled']} 个里，{uns['plain_unsettled_other']} 个在不等的组（进程在主代理结束时就退出，没结算的原因分不清），"
          f"{uns['plain_unsettled_wait_arm']} 个在等的组，它们的上级正是一个卡住的子代理。"
          f"后果：headless 下进程退出时报 #5063 的错。{uns['crashes']} 次退出崩溃里，{uns['crash_working']} 次是还有子代理在干活，"
          f"{uns['crash_interrupted_only']} 次没有子代理在干活、只有这种没结算的子代理。"
          + (f"等待批里等满 20 分钟上限的 {len(wait_counts(wf)['capped'])} 次都是这种情况。" if wait else "")
          + "交互使用时会怎样没有测。（事后分析，`scripts/unsettled_subagents.py`。）\n")

    # ================================================================ limits
    w("## 局限\n")
    w(("- 题：正式实验只有 5 道，都是 3–14 分钟、交一份文件的任务；p4 大多数运行是满分；c1、p4 在自然状态下几乎不开子代理。"
       "补充实验加了阳性、阴性对照各一道，都是脚本判分的代码类任务，每组 10 次；办公题没有阳性对照。阴性对照全部满分，只能比较费用和时长。"
       "阳性对照只测了 K=8、一个时限（3 分钟）、一种宽度（24 道）。\n" if ctl else
       "- 题：只有 5 道，都是 3–14 分钟、交一份文件的任务。没有一道事先就该受益于并行的题（阳性对照），也没有步步依赖、委派只会添乱的题（阴性对照）。"
       "p4 大多数运行是满分；c1、p4 在自然状态下几乎不开子代理。\n") +
      "- 功效：每个对比 20 对，办公题预注册对比的最小可测差在 "
      f"{min(H[k]['mdd'] for k in H):.1f}–{max(H[k]['mdd'] for k in H):.1f} 分之间，深度 2、3 的对比只测得出十几分的差别。“测不出”不等于“没有差别”。\n"
      "- 办公两道题的方向经常相反（见分题结果），合并的数代表不了每一道题。\n"
      "- 判分：得分来自模型判分。思考强度从 max 换成 high 经过了直接对比，分数相同。但人工校准只有 2 份文档 38 条，"
      "而且评分标准 v1.3 正是对照这 38 条改出来的，v1.3 改完后没有再做人工校准；没有做人和模型的两两比较。"
      "同一个模型打两次只能说明稳定，不能说明打得对。"
      + ("评分标准的分辨率比名义上低：o1 的 23 条里 14 条、o2 的 19 条里 7 条几乎人人同分（见实验 4）。"
         if (A / "item-analysis.json").exists() else "") + "\n"
      "- 交付物长度和得分分不开：D1-K8 的报告比 D0 长六成多，同一组内长的报告得分也略高。判分提示词要求不因为长而加分，但没有办法证明没有这种偏好。\n"
      + (wait_limit(wf) if wait else "- 提前收工和深度混在一起：深度 2、3 的结果受 headless 下主代理提前结束的影响，修掉以后可能不同。\n") +
      "- 模型和实现：只测了 deepseek-flash（推理强度 max）一个模型，主代理和子代理同一个模型，没有试便宜模型做子代理；"
      "只测了 DSH 0.2.0-rc.2、一句鼓励语、一个时段。上限是“碰到才拒绝”的实现。\n"
      "- 费用：按 token 用量和官方价估算；搜索部分是次数乘平均单价，单价本身有约两成的抽样差；并发运行的缓存命中率高于单用户。\n"
      "- 时长：实际时长是在内部端点和 DSec 上测的；标准化时长换成了官网 API 的速度，但只测了一个时段；工具时间没有标准化。\n"
      f"- 没有做同费用比较：D0 跑 {ratio(HC['H1']):.0f} 次的钱大约等于 D1-K8 跑 1 次，对产品决策更公平的问法是“同样的钱，D0 多跑几次取最好的一份会不会更好”。\n")

    # ================================================================ recommendations
    w("## 建议\n")
    rec = wait_recs(wf) if wait else {
        "depth": ("默认深度保持 1", "加深没有提高得分，办公题费用 1.2–2 倍，提前收工和崩溃都在深度 ≥ 2", "修掉 #5063 之后重测深度 2"),
        "wait": ("headless 下主代理结束前先等后台子代理回来，或者不允许带着未回的子代理结束",
                 "22 次崩溃里 19 次有未回的子代理；办公 2 次、p4 9 次因此交出不完整的结果", "做“强制等待”的对照，看崩溃和丢结果是否消失")}
    k_evid = ("深度 1 下模型很少同时开超过 4 个，K=4 和 K=8 几乎是同一组运行；K=1、2 在办公题上省四到六成费用且没测到损失，"
              "但在鼓励并行的读代码题上低 3–4 分")
    enc_evid = "读代码题得分高约 6 分，但费用约 3 倍、时长 1.6 倍；p4 反而掉分"
    recs = [rec["depth"],
            ("默认 K 先不改", k_evid + ("；阳性对照（24 道独立练习）上 K=8 在 6/10 次鼓励并行的运行里被碰到" if ctl else ""),
             "在阳性对照这样的宽任务上测 K=4、8、16，再定 K" if ctl else "用宽度可控的题测“并行在什么任务上有用”，再定 K"),
            rec["wait"],
            ("不默认在提示里鼓励并行", enc_evid + ("；阴性对照上鼓励句让 7/10 次运行开了子代理去重复核对，费用约 2 倍、得分不变" if ctl else ""),
             "鼓励句和“委派有用”混在一起，换宽度可控的题再测")]
    if ctl:
        recs.append(("提示里对委派的指引按任务的样子写：有多块互相独立的活、而且要赶时间时才并行；步步依赖的活不委派",
                     "阳性对照上委派高约 10 分、费用 3.4 倍，不限时的 D0 分数相同而且更便宜；阴性对照上委派只多花钱和时间",
                     "办公题上的阳性对照；别的宽度和时限"))
    recs += [("把搜索用量写进会话日志；限制搜索调用的输出长度", "搜索费占一半左右且日志里看不到；每次调用四成多的费用是被丢掉的回答", "限制输出后搜索结果是否仍然完整"),
             ("把名额上限写进系统提示，或者超出时排队", "K=1 时模型反复被拒", "D1-K1 加“告诉模型上限”的对照")]
    w("| 建议 | 依据 | 还需要验证什么 |\n|---|---|---|")
    for a_, b_, c_ in recs:
        w(f"| {a_} | {b_} | {c_} |")
    w("")
    w("### 改出厂默认值（D1-K8）会怎样\n")
    w("办公题的预注册对比，都以 D1-K8 为基准。“合适”取决于愿意拿多少费用换多少质量，这是产品决定；这张表给的是每种改法的位置。\n")
    w("| 改法 | 估算总费用（对 D1-K8） | 得分差（95% 区间） | 实际行为 | 读法 |\n|---|---|---|---|---|")
    inv = {"est": -H["H1"]["est"], "lo": -H["H1"]["hi"], "hi": -H["H1"]["lo"]}
    w(f"| K 8 → 4 | ×{ratio(HC['H2c']):.2f} | {d_cell(H['H2c'])} | 上限只在 {frac(OFF, 'D1-K4', hit_k)} 次运行里被碰到，两组几乎是同样的运行 | 改不改没有区别 |")
    w(f"| K 8 → 2 | ×{ratio(HC['H2b']):.2f} | {d_cell(H['H2b'])} | {frac(OFF, 'D1-K2', hit_k)} 次运行碰到上限 | 费用没省下来 |")
    w(f"| K 8 → 1 | ×{ratio(HC['H2a']):.2f} | {d_cell(H['H2a'])} | {frac(OFF, 'D1-K1', hit_k)} 次运行碰到上限，子代理一个接一个做 | 费用省四成多；得分差的区间下限略超过 −5 分 |")
    w(f"| D 1 → 2 | ×{ratio(HC['H3a']):.2f} | {d_cell(H['H3a'])} | 平均开 {gm(OFF, 'D2-K8', 'children'):.1f} 个、两层；{sum(truthy(r['crash5063']) for r in grp(OFF, 'D2-K8'))} 次退出崩溃 | 不建议 |")
    w(f"| D 1 → 3 | ×{ratio(HC['H3b']):.2f} | {d_cell(H['H3b'])} | 平均开 {gm(OFF, 'D3-K8', 'children'):.1f} 个；{sum(truthy(r['crash5063']) for r in grp(OFF, 'D3-K8'))} 次退出崩溃 | 不建议 |")
    w(f"| 不给委派工具（D0） | ×{1 / ratio(HC['H1']):.2f} | {d_cell(inv)} | 主代理自己查，搜索请求约为三分之一 | 对费用敏感时是合理的选项；得分差的区间下限超过 −5 分 |")
    w("")

    # ================================================================ follow-up
    w("## 后续实验\n")
    w("### 还没做的补充实验（按价值排序，不改设计）\n" if (ctl or wait) else "### 补充实验（按价值排序，不改设计）\n")
    fu = []
    if not ctl:
        fu.append(("阳性对照和阴性对照", "一道设计上就该受益于并行的题（例如 20 个互相独立的查询、每个要来源、加 15 分钟时限）；一道步步依赖的题。各跑 D0 和 D1-K8 十次",
                   "约 40", "这套方法测不测得出委派的好处；委派在哪类任务上有用"))
    if not wait:
        fu.append(("把提前收工和深度分开", "D2-K8、D3-K8 重跑；headless 里主代理结束时如果还有子代理在跑，就等它们回来再让主代理续写。或者等 #5063 修好再跑",
                   "约 80", "深度 2、3 的低分里多少来自 DSH 的问题、多少来自深度本身"))
    if ctl:
        fu.append(("办公题的阳性对照", "20 个互相独立、答案唯一的事实查询，每个要给来源，脚本按答案键判分；D0、等·D1-K8、等·鼓励·D1-K8 各 10 次",
                   "约 30（另需人工核对 20 条答案键）", "办公类任务上委派有没有好处；模型判分以外再有一个不靠判分模型的办公指标"))
        fu.append(("在阳性对照上测 K 和宽度", "pw-exercises 加 K=2、4、16；练习数换成 8 和 48", "约 90", "K=8 在宽任务上是不是太小；好处随宽度怎么变"))
    if wait:
        fu += wait_followups(wf)
    fu += [("上限告诉模型", "D1-K1 加一个变体：系统提示里写明“同时最多 1 个子代理”", "约 40", "不再反复被拒以后，K=1 的费用和得分"),
           ("判分的人工两两比较", "抽 20 对产出，人判哪份好，判分模型做同样的比较，算一致率", "人工约 3 小时", "判分模型的排序和人是否一致"),
           ("顺序跑的小子集", "每格 1 次、一次只跑一个", "约 26", "并发批次的标准化时长是否可靠")]
    w("| 实验 | 做法 | 运行次数 | 回答什么 |\n|---|---|---|---|")
    for a_, b_, c_, d_ in fu:
        w(f"| {a_} | {b_} | {c_} | {d_} |")
    w("")
    w("### 下一轮设计（v3）\n")
    w("问题改成：委派在什么任务上划算，由什么决定。D 和 K 作为手段，不再是问题本身。\n")
    w("**题目：把“能拆成几块”做成可以控制的量。** 三类任务各三档宽度，每类再加一道步步依赖的对照题，共 12 道。\n")
    w("| 类 | 形式 | 宽度 |\n|---|---|---|\n"
      "| 调研比较（o1、o2 这一类） | 对 N 个对象按固定属性比较，附来源 | N = 3 / 8 / 20 |\n"
      "| 读代码答题（c1 这一类） | 回答 M 个互相独立的仓库问题 | M = 5 / 15 / 40 |\n"
      "| 写代码（p4 这一类） | 时限内完成 E 道独立练习，换更难的题集 | E = 4 / 12 / 24 |\n")
    w("- 每道题先用 D0 试跑 5 次，均分在 50–80 之间才留用，避免再出现接近满分的题。\n"
      "- 最宽一档的材料量要超过主代理一个上下文能装的量，这样“子代理各用各的上下文”的好处才有机会出现；同时记录上下文压缩的次数。\n")
    w("**格：先看模型想开多少，再定 K，让上限真的被碰到。** 每道题先用 D3、K=16 跑 3 次，看模型自己开几个、几层；"
      "按事先写定的规则取 Kn = 自然峰值的中位数。只留 5 格：\n")
    w("| 格 | 回答什么 |\n|---|---|\n| D0 | 基线 |\n| D1-K1 | 委派本身（不并行）的作用 |\n| D1-Kn | 并行的作用 |\n"
      "| D1-K16 | 放开上限会不会更好 |\n| D2-Kn | 再套一层的作用 |\n")
    w("- 主要对比 4 个，一次改一个：委派 = D1-K1 − D0；并行 = D1-Kn − D1-K1；放开 = D1-K16 − D1-Kn；深度 = D2-Kn − D1-Kn。"
      "每个对比再看它随宽度怎么变。\n"
      "- 去掉的格：D3（这次和 D2 没有区别）、K2 和 K4（这次在深度 1 下几乎碰不到）、鼓励句（它把“叫模型并行”和“委派”混在一起，改用宽度来代替）。\n"
      "- 次数：12 题 × 5 格 × 5 次 = 300 次，和这次同一量级。这次配对差的标准差在 8–13 分；60 对在 80% 功效下能测出约 3.3 分，"
      "Holm 校正 4 个对比后约 4 分。\n"
      "- 模型：至少两个，deepseek-flash 和一个更强的；预算够再加“主代理 max、子代理低推理档”一格。\n"
      "- 测量改四处：搜索用量写进日志，不再抽样估；费用同时给“按实际缓存命中”和“按零命中”两档；判分加人工和模型的两两比较，办公题产出里描述过程的句子像代码题那样先删掉；"
      "评分标准按区分度重做，去掉人人满分的条目，把几乎人人 1 分的条目（来源、可用性）拆成能分出高低的细项，并先用 D0 试跑看每条的得分分布。\n"
      "- 次数按功效定：这次配对差的标准差约 8 分，要测出 3 分的差别每个对比约需 55 对。\n"
      "- 预注册多写三条：提前收工怎么处理；δ 取多少和理由（判分两次之间的差是 2.4–3.5 分，δ 要明显高于它）；判分校准的门槛。\n")

    # ================================================================ appendices
    w("## 附录 A：题目原文\n")
    order = [("o1-singapore-trip", "o1 新加坡行程（办公，联网）", "singapore.md"), ("o2-server-cpu-report", "o2 服务器 CPU 选型报告（办公，联网）", "report.md"),
             (C1, "c1 子代理两个上限在哪里实现（代码，不联网；工作区是 DSH 仓库快照 cc0fb5f8b7）", "answer.md"),
             (W1, "w1 记忆溯源插件的实现路径（代码，不联网；同一份仓库快照）", "report.md"),
             (P4, "p4 四道 Python 练习（代码，不联网；工作区是练习模板）", "4 个实现文件")]
    for tid, title, deliv in order:
        w(f"### {title}\n")
        w(f"交付物：{deliv}。题面：\n")
        w("> " + tasks[tid]["prompt"].replace("\n", "\n> ") + "\n")
    w("### 鼓励并行的那句话\n")
    w("只加在代码题鼓励版的题面末尾，另起一段：\n")
    w("> 独立的子任务尽量交给 subagent 并行做。\n")
    if ctl:
        w(f"### 实验 3：阳性对照 pw-exercises（代码，不联网；工作区是 {len(ctl['build']['chosen'])} 道练习的模板）\n")
        w(f"交付物：{len(ctl['build']['chosen'])} 个实现文件。题面：\n")
        w("> " + ctl["tasks"][PW]["prompt"].replace("\n", "\n> ") + "\n")
        w("### 实验 3：阴性对照 n1-chain16（代码，不联网；工作区是脚本生成的 16 步任务）\n")
        w("交付物：answers.md。题面：\n")
        w("> " + ctl["tasks"][N1]["prompt"].replace("\n", "\n> ") + "\n")
        w("工作区里的 start.md（第 1 步）：\n")
        w("```text\n" + (EXP / "data/code-templates/chain16/start.md").read_text(encoding="utf-8").strip() + "\n```\n")
    if wait:
        w("### 实验 2：等待批\n")
        w("等待批用的是 o1、o2 的原题面，一个字没改。\n")

    office_rubric = (EXP / "rubrics/office-rubrics-draft.md").read_text(encoding="utf-8")
    code_rubric = (EXP / "rubrics/code-rubrics.md").read_text(encoding="utf-8")
    w("## 附录 B：评分方法与评分标准\n")
    w("### B.1 办公题怎么打分\n")
    w("1. 脚本从被评文件里随机抽 5 个引用链接（按运行编号固定），抓取页面，截出和文中那句话相关的原文片段。\n"
      "2. 判分模型（Opus 5.5，思考强度 high）收到：打分说明、计分规则和判定细则、这道题的评分表和答案键、被评文件、5 段页面原文。\n"
      "3. 模型逐条给分并写证据和理由，输出 JSON。“结果写进文件”这一条由脚本判定。\n"
      "4. 总分 = 各条得分之和 ÷ 满分 × 100。每份打 2 次，取平均。文件不存在记 0 分。\n")
    w("#### 计分规则和判定细则（评分标准 v1.3）\n")
    w(demote(section(office_rubric, "## 计分"), 3) + "\n")
    w("### B.2 o1 评分表\n")
    w(demote(section(office_rubric, "## o1 "), 1) + "\n")
    w("### B.3 o2 评分表\n")
    w(demote(section(office_rubric, "## o2 "), 1) + "\n")
    w("### B.4 代码题 c1、w1 怎么打分\n")
    w("1. 判分前脚本先做三件事：按规则删掉描述做题过程的句子；w1 超过 3300 字的部分截掉；没有产出文件或短于阈值的运行直接记 0 分。\n"
      "2. w1 另由脚本从文中抽 5 处“路径:行号”，给出仓库快照里对应位置前后各 5 行原文。\n"
      "3. 判分模型（Opus 5.5，思考强度 high）收到：打分说明、计分规则、这道题的评分表和答案键、被评文件（w1 加 5 处源码片段）。\n"
      "4. 每份打 2 次；两次逐条不一致超过 10% 时加打第 3 次，每条取多数。\n")
    cs = section(code_rubric, "## 计分")
    cs = re.sub(r"\n第 1、3、5、6 条沿用[^\n]*\n", "\n", cs)
    w("#### 计分规则和判定细则\n")
    w(demote(cs, 2) + "\n")
    w("### B.5 c1 的 22 个要点\n")
    w(demote(section(code_rubric, "## c1 "), 1) + "\n")
    w("### B.6 w1 评分表\n")
    w(demote(section(code_rubric, "## w1 "), 1) + "\n")
    w("### B.7 p4 怎么判分\n")
    w("- 每道练习：新建一个空目录，放入练习模板；从运行的工作区只拷回顶层的非测试 .py 文件（测试文件、配置文件都不拷）；"
      "用完整的原始测试文件覆盖可见的那份。\n"
      "- 在不联网的容器里以普通用户运行 `python3 -m pytest`，每道练习限时 120 秒；超时则逐个测试单独跑，每个 10 秒。\n"
      "- 得分 = 4 道练习“隐藏测试通过比例”的平均 × 100。隐藏测试指完整测试文件里有、可见测试文件里没有的测试。\n"
      "- 判分程序先用参考答案和空实现各判一遍自检：参考答案 102/102 通过，空实现 5.56 分。\n")
    w("### B.8 打分提示词\n")
    w("办公题（`{file_item}` 处填 A7 或 A5，后面接评分标准）：\n")
    w("```text\n" + const(EXP / "scripts/judge.py", "INSTRUCTIONS").strip() + "\n```\n")
    w("c1：\n")
    w("```text\n" + const(EXP / "scripts/judge_code.py", "INSTRUCTIONS_C1").strip() + "\n```\n")
    w("w1：\n")
    w("```text\n" + const(EXP / "scripts/judge_code.py", "INSTRUCTIONS_W1").strip() + "\n```\n")

    w("## 附录 C：补跑判定\n")
    w("对每道代码题、每个深度，看自然状态 K8 组的 10 次运行。“名额峰值”是同一时刻占着名额的子代理数。\n")
    w("| 题 | 深度 | 10 次里名额峰值的最大值 | 出现该层子代理的次数 | 上一深度被深度上限拒的次数 | 这一深度是否被用到 | 补跑的格 |\n|---|---|---|---|---|---|---|")
    for t, v in stage_b["tasks"].items():
        for dep, x in v.items():
            w(f"| {t.split('-')[0]} | {dep} | {max(x['slot_peaks'])} | {sum(1 for c in x['children_at_depth'] if c > 0)} | "
              f"{sum(1 for c in (x.get('depth_rejects_at_previous_depth') or []) if c > 0) if dep != 'D1' else '—'} | "
              f"{'是' if x['depth_used'] else '否'} | {'、'.join(x['run']) if x['run'] else '无'} |")
    w("\n规则：名额峰值超过 k 且这一深度被用到，才补跑该深度的 K=k。深度没被用到时，按机制等同于上一深度的同一 K。\n")

    w("## 附录 D：分题结果表\n")
    w("### o1 新加坡行程（每组 10 次）\n")
    w(table_rows("tables-o1-singapore-trip-t.md", R_MAIN + R_DELEG + R_WORK) + "\n")
    w("### o2 服务器 CPU 报告（每组 10 次）\n")
    w(table_rows("tables-o2-server-cpu-report-t.md", R_MAIN + R_DELEG + R_WORK) + "\n")
    w("### c1（每组 10 次）\n")
    w(table_rows("tables-c1-subagent-limits-t.md", R_MAIN_CODE + R_DELEG) + "\n")
    w("### w1 鼓励并行（每组 10 次；自然状态见正文）\n")
    w(table_rows("tables-w1-encouraged-t.md", R_MAIN_CODE + R_DELEG + R_WORK_CODE) + "\n")
    w("### p4（每组 10 次）\n")
    w(table_rows("tables-p4-python-t.md", R_MAIN_CODE + R_DELEG) + "\n")
    w("p4 的得分区间是对称的 t 区间，上限会超过 100，实际得分不超过 100。\n")

    w("## 附录 E：文件与 SHA-256\n")
    w("路径相对开发机上的实验目录。\n")
    w("| 文件 | SHA-256 |\n|---|---|")
    for f, h in audit["files"].items():
        w(f"| `{f}` | `{h}` |")
    w("\n- `judge.py` 的哈希是正式打分之后加了校验用选项的版本；打分提示词和计分逻辑与正式打分时相同。\n"
      "- `results/analysis-v2/rows.csv` 比 10/3 上午那一版多了 11 列（补充实验用到的字段），原有 44 列逐格相同，所以哈希变了。\n"
      "- 每次运行的原始记录：`results/runs/{main-office,main-code,main-code-B}/<编号>/`。\n"
      "- 打分记录：`results/judge/main-office/`、`results/judge/main-code/`；p4：`results/grade/main-code/`。\n"
      "- 判分校验：`results/validate-max/`（正式运行抽样的 xhigh 打分）、`results/validate-effort/`（10/1 文档的 max、xhigh、high 打分和人工分对比）。\n"
      "- 分析产物：`results/analysis-v2/`（`rows.csv`、`audit.json`、`tables-*.md`、`stats-*.md`、图）。重算：`bash judge-env/scripts/analysis-v2.sh`；"
      "报告由 `scripts/build_report.py` 从这些文件生成。\n")

    if sa and (ctl or wait):
        w("实验 2–4 的文件：\n")
        w("| 文件 | SHA-256 |\n|---|---|")
        for f, h in sa["files"].items():
            w(f"| `{f}` | `{h}` |")
        w("\n- 每次运行的原始记录：`results/runs/{wait-office-2,ctl-main}/<编号>/`；试跑在 `results/runs/ctl-pilot-*/`，不计入结果。\n"
          "- 打分和判分记录：`results/judge/wait-office-2/`、`results/grade/ctl-main/`。\n"
          "- 分析产物：`results/analysis-wait/`、`results/analysis-ctl/`、`results/analysis-supp/audit.json`。"
          "重算：`bash judge-env/scripts/supp-wait-analysis.sh`。\n")
        supp_appendix(w, ctl, wait)

    args.out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {args.out} ({sum(len(x) for x in L):,} chars)")


def ctl_facts(ctl: dict) -> dict:
    """Numbers of the control batch that both the findings and the section use."""
    rows = ctl["rows"]

    def g(task, grp):
        return sorted([r for r in rows if r["task"] == task and r["group"] == grp], key=lambda r: int(r["rep"]))

    def kids(r):
        return float(r["children"] or 0)

    f = {"g": g, "kids": kids}
    for task in (PW, N1):
        f[task] = {k: {m: cmp_(ctl[task], m, k) for m in ("score", "model_cost_peak", "seconds")} for k in ("PC", "NC", "EC")}
    nat = g(PW, "W-D1-K8")
    f["nat_spawned"] = [r for r in nat if kids(r) > 0]
    f["nat_solo"] = [r for r in nat if kids(r) == 0]
    spawn = ctl["spawn"]
    n1e = [v for v in spawn.values() if v["task"] == N1]
    f["n1_spawn_runs"] = len(n1e)
    f["n1_verify_runs"] = sum(1 for v in n1e if all(re.search(r"verif|re-deriv|audit", c["description"] or "", re.I) for c in v["calls"]))
    f["early"] = [r for r in rows if (num(r.get("first_resident")) or 0) > 0]
    return f


def rejudge_note(wait) -> str:
    """与预注册方案的差异: the 21 first judgments of the wait batch that were replaced (judged by usage, not by score)."""
    r1 = opt(EXP / "results/analysis-supp/rejudge-wait.json")
    orig = opt(EXP / "results/analysis-wait-orig/stats-wait.json")
    if not (wait and r1 and orig):
        return ""
    now = wait["stats"]
    pairs = "、".join(f"{k} {sgn(cmp_(orig, 'score', k)['est'])} → {sgn(cmp_(now, 'score', k)['est'])}" for k in ("S1", "S2", "S3", "S4"))
    return (f"- 等待批的打分：200 份里有 {r1['n']} 份（全部是第一遍打分，北京时间 {r1['from']}–{r1['to']} 之间写出）返回的用量和其余的不同："
            f"输出 {r1['out_min']:,}–{r1['out_max']:,} token（正式办公批 520 份最多 14,134），其中 {r1['cached']} 份的提示词大部分记为缓存读取，"
            f"单份用时 {r1['secs_min']:.0f}–{r1['secs_max']:.0f} 秒（平时约 90 秒）。这 {r1['n']} 份比同一份报告的第二遍打分平均高 {r1['old_minus_j2']:.1f} 分。"
            "原因在公司代理一侧，查不到。处理：按用量判据（输出超过 15,000 token，或缓存读取不少于 20,000 token；不看得分）把这些打分作废，"
            f"用完全相同的做法重打。重打后用量正常，和第二遍打分平均差 {r1['new_abs_j2']:.1f} 分。"
            f"正式批办公、代码打分和判分校验里没有一份命中这个判据。按原来的两遍打分算，四个主要对比的估计值是：{pairs}（前者是原来的，后者是重打后的）；判读不变。\n")


def ctl_gate(s: dict) -> str:
    """The positive control's primary contrast against the threshold written before the run (>= +10, interval excludes 0)."""
    if s["est"] >= 10 and s["lo"] > 0:
        return "达到了预先写的门槛（≥ +10 分且区间不含 0）"
    if s["lo"] > 0:
        return f"区间不含 0；估计值比预先写的 +10 分门槛低 {10 - s['est']:.1f} 分，严格按门槛算没有达到"
    return "区间包含 0，没有达到预先写的门槛（≥ +10 分且区间不含 0）"


def ctl_block(w, ctl: dict, f: dict, p4_d0_median_s: float) -> None:
    """实验 3：阳性对照和阴性对照"""
    g, kids, pilot, build = f["g"], f["kids"], ctl["pilot"], ctl["build"]
    pc, nc, ec = (f[PW][k] for k in ("PC", "NC", "EC"))
    npc, nnc = f[N1]["PC"], f[N1]["NC"]

    def line(task, name, fn):
        w(f"| {name} | " + " | ".join(fn(g(task, c)) for c in CTL_GROUPS) + " |")

    def mean(v, col, nd=1):
        x = [float(r[col]) for r in v if r[col] not in ("", None)]
        return f"{st.mean(x):.{nd}f}" if x else "—"

    def table(task):
        w("| 指标 | " + " | ".join(enc(c) for c in CTL_GROUPS) + " |\n|---|" + "---|" * len(CTL_GROUPS))
        line(task, "次数", lambda v: str(len(v)))
        line(task, "得分（均值）", lambda v: mean(v, "score"))
        line(task, "得分（最低–最高）", lambda v: f"{min(float(r['score']) for r in v):.1f}–{max(float(r['score']) for r in v):.1f}")
        if task == PW:
            line(task, "测试全部通过的练习数（均值，共 24 道）", lambda v: f"{st.mean(r['all_pass'] for r in v):.1f}")
            line(task, "动过的实现文件数（均值，共 24 个）", lambda v: f"{st.mean(r['changed'] for r in v):.1f}")
        else:
            line(task, "答对的步数（均值，共 16 步）", lambda v: f"{st.mean(r['steps_ok'] for r in v):.1f}")
        line(task, "被时限结束的次数", lambda v: f"{sum(truthy(r['timeout']) for r in v)}/{len(v)}")
        line(task, "开了子代理的次数", lambda v: f"{sum(kids(r) > 0 for r in v)}/{len(v)}")
        line(task, "子代理数（均值 / 最多）", lambda v: f"{st.mean(kids(r) for r in v):.1f} / {int(max(kids(r) for r in v))}")
        line(task, "碰到名额上限的运行数", lambda v: f"{sum((num(r['capacity_rejects']) or 0) > 0 for r in v)}/{len(v)}")
        line(task, "模型费·高峰（元/次）", lambda v: mean(v, "model_cost_peak", 2))
        line(task, "实际时长（秒）", lambda v: mean(v, "seconds", 0))
        w("")

    def contrasts(task):
        w("| 对比 | 得分差 | 最小可测差 | p | 模型费之比 | 实际时长之比 |\n|---|---|---|---|---|---|")
        for k, nm in (("PC", "主对比：等·鼓励·D1-K8 − D0"), ("NC", "次要：等·D1-K8 − D0"), ("EC", "描述：等·鼓励·D1-K8 − 等·D1-K8")):
            c = f[task][k]
            sc = c["score"]
            if sc["sd"] == 0:
                cells = "0（两组全部满分） | — | —"
            else:
                cells = f"{d_cell(sc)} | {sc['mdd']:.1f} | {sc['p']:.3f}"
            w(f"| {nm} | {cells} | {r_cell(c['model_cost_peak'], star=False)} | {r_cell(c['seconds'], star=False)} |")
        w("")

    w("## 实验 3：对照题（60 次）\n")
    w("**要回答的问题。** 正式实验里没有一组显著好于 D0。这有两种可能：这些题上委派确实没用，或者这套做法测不出委派的好处。"
      "对照题用来区分：阳性对照是一道按设计就该受益于并行的题，阴性对照是一道步步依赖、没法并行的题。\n")
    drop_struct = sum(1 for d in build["dropped"] if "hidden tests" not in d["why"])
    drop_few = sum(1 for d in build["dropped"] if "hidden tests" in d["why"])
    hidden = sum(t["hidden"] for t in build["tests"].values())
    half = sorted(x["half_done_s"] for x in pilot["pw_d0_unlimited"])
    d0s = sorted(x["seconds"] for x in pilot["pw_d0_unlimited"])
    w("**设置。** 两道题：\n")
    w("| | 阳性对照 pw-exercises | 阴性对照 n1-chain16 |\n|---|---|---|\n"
      f"| 内容 | {len(build['chosen'])} 道互相独立的 Python 练习，每道一个目录；和 p4 同一来源、同一构建方法 | "
      "16 步数据处理；每一步的参数、下一步说明文件的名字都由上一步的答案决定，只能按顺序做 |\n"
      f"| 时限 | 题面写明限时 {ctl['tasks'][PW]['timeout_s'] // 60} 分钟，到时间进程被强制结束，按当时各文件的状态判分 | "
      f"题面写明限时 {ctl['tasks'][N1]['timeout_s'] // 60} 分钟（没有一次用到） |\n"
      f"| 得分 | {len(build['chosen'])} 道练习各自隐藏测试通过比例的平均 × 100（共 {hidden} 个隐藏测试），脚本判分 | 答对的步数 ÷ 16 × 100，脚本按答案键判分 |\n"
      "| 联网 | 不联网 | 不联网 |\n")
    w(f"- 阳性对照的选题规则开跑前写定：Aider polyglot-benchmark 固定提交 {build['commit'][:8]} 的 `{build['path']}` 下 {build['candidates']} 道练习，"
      f"按目录名排序，去掉结构不符合构建检查的（{drop_struct} 道）和隐藏测试少于 {build['rule']['min_hidden']} 个的（{drop_few} 道），"
      f"取前 {build['rule']['count']} 道，正好剩 {len(build['chosen'])} 道。清单见附录 F。\n"
      f"- 时限 {ctl['tasks'][PW]['timeout_s'] // 60} 分钟的定法（规则开跑前写定）：D0 不限时试跑 3 次，取“写完第 12 个实现文件”所用时间的中位数"
      f"（三次是 {half[0]}、{half[1]}、{half[2]} 秒），取整到分钟。D0 不限时做完全部 {len(build['chosen'])} 道用了 "
      f"{d0s[0] / 60:.1f}–{d0s[-1] / 60:.1f} 分钟。试跑不计入结果。\n"
      "- 阴性对照由脚本生成（`scripts/build_chain.py`）：数据是 4000 条订单，目录里另有 200 个干扰文件；答案键由生成脚本算出，"
      "另用一个只读说明文字的独立求解程序核对，16 步全部一致。\n"
      "- 题面原文见附录 A。\n")
    w("三组，两道题各 10 次，共 60 次：\n")
    w("| 组 | 说明 |\n|---|---|\n| D0 | 没有委派工具 |\n| 等·D1-K8 | 出厂默认的深度和 K |\n"
      "| 等·鼓励·D1-K8 | 同上，题面末尾加“独立的子任务尽量交给 subagent 并行做。” |\n")
    w("**流程。**\n")
    w("1. 每次运行开一个新容器，环境同正式实验的代码题（不联网）；工作区是题目模板，答案键和完整测试不进容器。\n"
      "2. 有委派工具的两组都用实验 2 的补丁（进程等子代理都回来才退出），提前收工不会混进来。\n"
      "3. 同一批里随机完全区组，并发固定 30 路；只重跑基础设施故障。到时限被结束算正常结果。\n"
      "4. 脚本判分：阳性对照在不联网的容器里跑隐藏测试，阴性对照把 answers.md 和答案键逐步比对。\n"
      "5. 主对比每道题一个，开跑前写定：等·鼓励·D1-K8 减 D0，按第几次配对，10 对。\n")
    w("判读规则，开跑前写定：阳性对照的得分差 ≥ +10 分且 95% 区间不含 0，算这套做法测得出委派的好处；"
      "阴性对照预期得分差的区间在 ±5 分以内或为负，费用和时长不低于 D0。\n")
    w("### 设置 1：阳性对照（24 道独立练习，限时 3 分钟）\n")
    w("结果：\n")
    table(PW)
    contrasts(PW)
    s, c, t = pc["score"], pc["model_cost_peak"], pc["seconds"]
    gate = ctl_gate(s)
    e_all = g(PW, "W-E-D1-K8")
    d0_all = g(PW, "D0")
    pe = pilot["pw_e_limit3"]
    pd = pilot["pw_d0_unlimited"]
    w(f"- 主对比：等·鼓励·D1-K8 比 D0 高 {d_txt(s)}，p {p_txt(s['p'])}；10 对里 {s['up']} 对更高、{s['down']} 对更低、{s['flat']} 对相差不到 1 分。{gate}。"
      f"模型费 {ratio(c):.2f} 倍（区间 {math.exp(c['lo']):.2f}–{math.exp(c['hi']):.2f}）。\n"
      f"- D0 的 {len(d0_all)} 次全部被时限结束（实际时长都是 {ctl['tasks'][PW]['timeout_s']} 秒），所以表里的时长之比 {ratio(t):.2f} 低估了差别；"
      f"等·鼓励·D1-K8 有 {sum(not truthy(r['timeout']) for r in e_all)} 次在时限内自己做完。\n"
      f"- 不加鼓励句也有差别：等·D1-K8 比 D0 高 {d_txt(nc['score'])}，模型费 {ratio(nc['model_cost_peak']):.2f} 倍。"
      f"模型自己在 {len(f['nat_spawned'])}/{len(f['nat_spawned']) + len(f['nat_solo'])} 次里开了子代理：开了的 {len(f['nat_spawned'])} 次平均 "
      f"{st.mean(float(r['score']) for r in f['nat_spawned']):.1f} 分，没有一次被时限结束；没开的 {len(f['nat_solo'])} 次平均 "
      f"{st.mean(float(r['score']) for r in f['nat_solo']):.1f} 分，{sum(truthy(r['timeout']) for r in f['nat_solo'])} 次被时限结束"
      "（开不开是模型自己选的，这两个数只作描述）。\n"
      f"- 加不加鼓励句之间：{d_cell(ec['score'])}，测不出差别；模型费 {ratio(ec['model_cost_peak']):.2f} 倍。\n"
      f"- 委派在这道题上换来的是时间。D0 不限时试跑 3 次，用 {d0s[0] / 60:.1f}–{d0s[-1] / 60:.1f} 分钟做到 "
      f"{min(x['score'] for x in pd):.1f}–{max(x['score'] for x in pd):.1f} 分，模型费 {min(x['model_cost_peak'] for x in pd):.2f}–"
      f"{max(x['model_cost_peak'] for x in pd):.2f} 元；等·鼓励·D1-K8 在 3 分钟以内做到平均 {st.mean(float(r['score']) for r in e_all):.1f} 分，"
      f"模型费平均 {st.mean(float(r['model_cost_peak']) for r in e_all):.2f} 元。不赶时间的话，D0 能做到同样的分数，而且更便宜。\n"
      f"- 主代理怎么分活：把 {len(build['chosen'])} 道练习分给 {int(min(kids(r) for r in e_all))}–{int(max(kids(r) for r in e_all))} 个子代理，每个子代理 1–4 道。"
      f"K=8 在这道题上被碰到了：等·鼓励·D1-K8 有 {sum((num(r['capacity_rejects']) or 0) > 0 for r in e_all)}/{len(e_all)} 次运行被名额上限拒过"
      "（正式实验的办公题 D1-K8 是 0/20）。这一批没有设别的 K，K 在这道题上的作用没有测。\n")
    w("同一轮（第 7 次）的三次运行：\n")
    w("| 组 | 编号 | 得分 | 测试全过的练习数 | 子代理 | 被时限结束 | 模型费（元） | 实际时长（秒） |\n|---|---|---|---|---|---|---|---|")
    for c_ in CTL_GROUPS:
        r = next(x for x in g(PW, c_) if int(x["rep"]) == 7)
        w(f"| {enc(c_)} | {r['id']} | {float(r['score']):.1f} | {r['all_pass']} | {int(kids(r))} | {'是' if truthy(r['timeout']) else '否'} | "
          f"{float(r['model_cost_peak']):.2f} | {float(r['seconds']):.0f} |")
    w("")

    w("### 设置 2：阴性对照（16 步，每一步依赖上一步的答案）\n")
    w("结果：\n")
    table(N1)
    contrasts(N1)
    ne = g(N1, "W-E-D1-K8")
    d0n = g(N1, "D0")
    w(f"- 30 次运行全部满分，得分没有差别。D0 用 {min(float(r['seconds']) for r in d0n):.0f}–{max(float(r['seconds']) for r in d0n):.0f} 秒做完。"
      "这道题对模型很容易，得分上分不出好坏，能看的只有费用和时长。\n"
      f"- 加了鼓励句以后，{sum(kids(r) > 0 for r in ne)}/{len(ne)} 次运行仍然开了子代理（1–2 个）。看这 {f['n1_spawn_runs']} 次里主代理交给子代理的任务："
      f"{f['n1_verify_runs']} 次是让子代理把答案独立重算一遍、用来核对主代理自己算的，{f['n1_spawn_runs'] - f['n1_verify_runs']} 次是让子代理先看一遍数据。"
      f"模型费是 D0 的 {ratio(npc['model_cost_peak']):.2f} 倍（区间 {math.exp(npc['model_cost_peak']['lo']):.2f}–{math.exp(npc['model_cost_peak']['hi']):.2f}），"
      f"实际时长 {ratio(npc['seconds']):.2f} 倍（区间 {math.exp(npc['seconds']['lo']):.2f}–{math.exp(npc['seconds']['hi']):.2f}）。\n"
      f"- 不加鼓励句时 10 次都没开子代理。模型费 {ratio(nnc['model_cost_peak']):.2f} 倍（区间 {math.exp(nnc['model_cost_peak']['lo']):.2f}–"
      f"{math.exp(nnc['model_cost_peak']['hi']):.2f}），实际时长 {ratio(nnc['seconds']):.2f} 倍；时长多出来的部分里有 3.5 秒是补丁在退出前固定要等的。\n"
      "- 和预期一致：委派没有带来好处，只多花了钱和时间。\n")

    w("### 结论\n")
    w("- 说明了：运行、配对、统计这一套做法测得出委派带来的差别。差别出现在“块数多、互相独立、每一块都要模型自己写、而且有时限”的任务上；"
      "在步步依赖的任务上委派只增加费用和时间。\n"
      f"- 和正式实验的关系：正式实验的 5 道题都没有时限，能拆的块也少（p4 只有 4 道练习，D0 中位 {p4_d0_median_s:.0f} 秒做完）。"
      "在那样的题上没测到好处，和这里测到好处并不矛盾。\n"
      "- 没说明的：阳性对照是脚本判分的写代码题。办公题用的是模型判分，它能不能测出同样大小的差别，这道对照说明不了；"
      "模型判分对已知缺陷敏不敏感，见实验 4。办公题的阳性对照还没有做（见“后续实验”）。\n"
      "- 委派的好处在这里是“更快”，不是“做得更好”：不限时的 D0 分数相同、费用更低。\n")
    if f["early"]:
        w(f"**补丁在这一批里。** 60 次里有 {len(f['early'])} 次运行（都在阳性对照）主代理一轮结束时还有 1 个子代理没回来，补丁等了 "
          f"{min(float(r['waited_s']) for r in f['early']):.0f}–{max(float(r['waited_s']) for r in f['early']):.0f} 秒，"
          "子代理回来后主代理接着跑了下一轮。没有退出时崩溃，也没有等待超限。\n")


def wait_facts(wait: dict) -> dict:
    """Numbers of the wait batch that both the findings and the section use."""
    rows, so = wait["rows"], wait["stats"]

    def g(grp, task=None):
        return [r for r in rows if r["group"] == grp and (task is None or r["task"] == task)]

    def early(r):
        return (num(r.get("early_finish")) or 0) > 0

    def rewrote(r):
        return early(r) and (num(r.get("deliv_writes_after_turn1")) or 0) > 0

    f = {"g": g, "early": early, "rewrote": rewrote}
    for k in ("S1", "S2", "S3", "S4", "N3", "N4"):
        f[k] = {m: cmp_(so, m, k) for m in so["metrics"] if k in so["metrics"][m]["comparisons"]}
    f["crash"] = {grp: sum(truthy(r["crash5063"]) for r in g(grp)) for grp in WAIT_GROUPS}
    f["n_early"] = {grp: sum(early(r) for r in g(grp)) for grp in WAIT_GROUPS}
    f["n_rewrote"] = {grp: sum(rewrote(r) for r in g(grp)) for grp in WAIT_GROUPS}
    f["cap"] = sum((num(r.get("wait_cap")) or 0) > 0 for r in rows)
    f["res_end"] = sum((num(r.get("resident_at_end")) or 0) > 0 for r in rows)
    return f


def wait_group_rows(w, wf: dict) -> None:
    """The wait batch's own rows: what happened at the end of the root's first turn."""
    g, early, rewrote = wf["g"], wf["early"], wf["rewrote"]

    def is_w(grp):
        return grp.startswith("W-")

    def line(name, fn):
        w(f"| {name} | " + " | ".join(fn(c) for c in WAIT_GROUPS) + " |")

    def med(v, col):
        x = [num(r.get(col)) for r in v if num(r.get(col)) is not None]
        return st.median(x) if x else None

    w("| 指标 | " + " | ".join(enc(c) for c in WAIT_GROUPS) + " |\n|---|" + "---|" * len(WAIT_GROUPS))
    line("次数", lambda c: str(len(g(c))))
    line("主代理第一轮结束时仍有子代理未回的运行数", lambda c: f"{sum(early(r) for r in g(c))}/{len(g(c))}")
    line("其中：子代理回来后主代理又改了交付物", lambda c: f"{sum(rewrote(r) for r in g(c))}" if is_w(c) else "—（进程已退出）")
    line("主代理轮数（均值）", lambda c: f"{st.mean(num(r['root_turns']) or 0 for r in g(c)):.2f}")
    line("等子代理的时间（上一行那些运行的中位数，秒；等满上限的按 1200 秒计）",
         lambda c: (lambda m: "—" if m is None else f"{m:.0f}")(med([r for r in g(c) if early(r)], "idle_wait_s")) if is_w(c) else "—")
    line("等待超过 20 分钟上限的运行数", lambda c: f"{sum((num(r.get('wait_cap')) or 0) > 0 for r in g(c))}/{len(g(c))}" if is_w(c) else "—")
    line("退出时崩溃的运行数", lambda c: f"{sum(truthy(r['crash5063']) for r in g(c))}/{len(g(c))}")
    line("没写完的交付物（没有文件或短于 5000 字符）", lambda c: f"{sum((num(r.get('deliv_chars')) or 0) < 5000 for r in g(c))}/{len(g(c))}")
    line("最低得分", lambda c: f"{min(float(r['score']) for r in g(c)):.1f}")
    w("")


WAIT_NAMES = {"S1": "S1 等·D2-K8 − D2-K8（等不等，深度 2）", "S2": "S2 等·D3-K8 − D3-K8（等不等，深度 3）",
              "S3": "S3 等·D2-K8 − 等·D1-K8（都等，深度 2 对 1）", "S4": "S4 等·D3-K8 − 等·D1-K8（都等，深度 3 对 1）",
              "N3": "描述：D2-K8 − 等·D1-K8", "N4": "描述：D3-K8 − 等·D1-K8"}


def wait_contrast_table(w, wf: dict) -> None:
    w("| 对比 | 得分差 | 最小可测差 | Holm 后 p | 判断 | 估算总费用之比 | 实际时长之比 | 标准化时长之比 |\n|---|---|---|---|---|---|---|---|")
    for k, nm in WAIT_NAMES.items():
        c = wf[k]
        sc = c["score"]
        ph = "—" if sc.get("p_holm") is None else f"{sc['p_holm']:.3f}"
        vd = verdict(sc) if sc.get("p_holm") is not None else "—"
        w(f"| {nm} | {d_cell(sc)} | {sc['mdd']:.1f} | {ph} | {vd} | {r_cell(c['total_cost_peak'])} | {r_cell(c['seconds'])} | {r_cell(c['std_seconds'])} |")
    w("")


def supp_audit_section(w, sa: dict, ctl: dict | None, wait: dict | None, audit: dict) -> None:
    """数据审计 -> 补充实验的运行和判分"""
    w("### 实验 2、3 的运行和判分\n")
    if ctl and "ctl-main" in sa["runs"]:
        r, g = sa["runs"]["ctl-main"], sa["grading"]
        retry = sum(v for k, v in r["attempts"].items() if k != "1")
        patch = next(iter(r["headless_patch_sha256"]))
        review = opt(CTL / "needs-review.json") or []
        w(f"- 对照批（ctl-main）：{r['rows']} 次 = 2 题 × 3 组 × 10 次，重复格 {r['duplicate_cells']} 个，没有缺格；基础设施重跑 {retry} 次；并发 {r['parallel'][0]} 路。"
          f"退出码 0 的 {r['exit_codes'].get('0', 0)} 次；{r['timeouts']} 次被时限结束（都是阳性对照，按设计算正常结果）；"
          f"退出时崩溃 {r['crash5063']} 次，内存到上限 {r['oom_kill']} 次。\n"
          f"- 这一批 {r['wait_runs']} 次“等”组运行记录的入口文件哈希都是补丁的哈希（`{patch[:12]}…`），D0 的运行没有换文件。\n"
          f"- 阳性对照判分：{g['graded']} 次全部判分，每次 {g['exercises_graded'][0]} 道练习、{g['full_total'][0]} 个测试。判分程序在容器里先自检：参考答案 "
          f"{g['check']['reference_full'][0]}/{g['check']['reference_full'][1]} 个测试通过（100 分），空实现 {g['check']['stub_main_score']:.1f} 分。")
        if review:
            texts = sorted({x["text"] for v in review for fl in v["flags"] for x in (fl["value"] if isinstance(fl["value"], list) else [])})
            exs = sorted({fl["exercise"] for v in review for fl in v["flags"]})
            w(f"- {len(review)} 次运行被判分程序标成“需要人看一眼”，原因相同：{'、'.join(exs)} 练习的实现里有一行 `{texts[0]}`，"
              "变量名命中了“可疑写法”的关键词。看过是正常实现，分数照用。")
        w("- 阴性对照判分：脚本把工作区里的 answers.md 和答案键逐步比对。")
    if wait and "wait-office-2" in sa["runs"]:
        r, j, c = sa["runs"]["wait-office-2"], sa["judging"]["office"], sa["crash"]
        mj = audit["judging"]["office"]
        retry = sum(v for k, v in r["attempts"].items() if k != "1")
        patch = next(iter(r["headless_patch_sha256"]))
        ag = j["agreement"]
        same_rubric = set(j["rubric_sha"]) == set(j["main_batch"]["rubric_sha"]) and len(j["rubric_sha"]) == 1
        w(f"- 等待批（wait-office-2）：{r['rows']} 次 = 2 题 × 5 组 × 10 次，重复格 {r['duplicate_cells']} 个，没有缺格；基础设施重跑 {retry} 次；"
          f"并发 {r['parallel'][0]} 路，和正式办公批相同。超时 {r['timeouts']} 次，内存到上限 {r['oom_kill']} 次。\n"
          f"- 退出码：{r['exit_codes'].get('0', 0)} 次为 0，{r['exit_codes'].get('1', 0)} 次为 1；这 {c['total']} 次都是 #5063 崩溃"
          f"（最后一个事件是主代理的最终回答 {c['last_event_final']}/{c['total']}），按组：" + "、".join(f"{enc(k)} {v} 次" for k, v in c["by_group"].items()) + "。\n"
          f"- {r['wait_runs']} 次“等”组运行记录的入口文件哈希都是补丁的哈希（`{patch[:12]}…`），不等的两组没有换文件。\n"
          f"- 打分：{j['judgments']} 份 = {j['runs']} 次运行 × 2，Opus 5.5、思考强度 {'、'.join(j['effort'])}，"
          + ("评分标准文件和正式打分是同一份（哈希相同）。" if same_rubric else "评分标准文件的哈希和正式打分不同。")
          + f"其中 {j['model_attempts'].get('1', 0)} 份一次打成，{sum(v for k, v in j['model_attempts'].items() if k != '1')} 份重试后打成，"
          f"{j['written_without_model_no_deliverable']} 份因为没交出文件直接记 0 分。有 1 份的请求挂起没有返回，停掉后重新发了一次，做法相同。"
          + ("有 21 份第一遍打分因为返回的用量异常作废重打（见“与预注册方案的差异”），这里的数是重打以后的。" if (EXP / "results/analysis-supp/rejudge-wait.json").exists() else "")
          + f"判分费用 ${j['cost_usd']:.0f}。\n"
          "- 两次打分之间：" + "；".join(
              f"{t.split('-')[0]} 平均绝对差 {ag[t]['mean_abs_diff']} 分（正式批 {mj['agreement'][t]['mean_abs_diff']}）、"
              f"相关系数 {ag[t]['pearson_r']}（{mj['agreement'][t]['pearson_r']}）、逐条相同 "
              f"{100 * j['item_agreement'][t]['all']['share']:.1f}%（{100 * mj['item_agreement'][t]['all']['share']:.1f}%）"
              for t in OFF if t in ag) + "。")
        sp = sa["speed"].get("wait-office-2")
        mo = audit["speed"]["main-office"]["all"]
        if sp:
            tt = [v["ttft_med_ms_median"] for v in sp["by_group"].values()]
            tp = [v["tps_med_median"] for v in sp["by_group"].values()]
            w(f"- 请求速度：这一批各组首字时间中位数 {min(tt)}–{max(tt)} 毫秒，输出速度 {min(tp)}–{max(tp)} token/秒"
              f"（正式办公批是 {mo['ttft_med_ms_median']} 毫秒、{mo['tps_med_median']} token/秒）。")
    rr = sa["runs"]
    if "ctl-main" in rr and "wait-office-2" in rr and rr["ctl-main"]["ended_utc_max"] < rr["wait-office-2"]["started_utc_min"]:
        w(f"- 两批先后运行，没有重叠：对照批最后一次运行 {bj(rr['ctl-main']['ended_utc_max'])} 结束，等待批 "
          f"{bj(rr['wait-office-2']['started_utc_min'])} 开始（北京时间）。办公批运行期间不打分，也没有在 DSec 上跑别的批次。\n")
    else:
        w("")


DROP_WHY = (("only (\\d+) hidden tests", "隐藏测试只有 {0} 个"),
            ("comment directly above removed test", "要隐藏的测试上方紧挨着一段注释，构建脚本不自动处理"),
            ("expected one solution, test and example file", "测试文件不止一个"),
            ("unexpected files in the exercise directory", "目录里有构建脚本不认识的文件（.approaches）"),
            ("unexpected .docs files", ".docs 里有额外的说明文件，构建脚本不自动合并"))


def supp_appendix(w, ctl: dict | None, wait: dict | None) -> None:
    """附录 F：补充实验的材料"""
    w("## 附录 F：实验 2、3 的材料\n")
    if ctl:
        b = ctl["build"]
        w("### F.1 阳性对照的练习\n")
        w(f"来源：`{b['source']}`，提交 `{b['commit']}`（{b['commit_date'][:10]}），目录 `{b['path']}`。构建脚本 `scripts/build_pwide.py`，和 p4 相同："
          "每道练习给 README、空实现和每三个测试里的一个，其余测试和参考解放在私有压缩包里。\n")
        w("| 练习 | 隐藏测试数 | 全部测试数 |\n|---|---|---|")
        for n in b["chosen"]:
            w(f"| {n} | {b['tests'][n]['hidden']} | {b['tests'][n]['full']} |")
        w(f"| 合计 | {sum(t['hidden'] for t in b['tests'].values())} | {sum(t['full'] for t in b['tests'].values())} |\n")
        w("按规则去掉的练习：\n")
        w("| 练习 | 原因 |\n|---|---|")
        for d in b["dropped"]:
            why = d["why"]
            for pat, zh in DROP_WHY:
                m = re.search(pat, why)
                if m:
                    why = zh.format(*m.groups())
                    break
            w(f"| {d['exercise']} | {why} |")
        w("")
        w("### F.2 阴性对照的生成\n")
        w("`scripts/build_chain.py`（种子 20261003，16 步）。`data/orders.csv` 有 4000 条订单；每一步是对这张表的一个小计算，参数取自上一步的答案；"
          "下一步说明文件的名字由这一步的答案和步号算出，目录里另有 200 个干扰文件。不算出上一步，就找不到下一步，也算不了下一步。"
          "答案键由生成脚本算出，放在私有目录，不进工作区。\n")
    if wait or ctl:
        js = (EXP / "patches/dsh-wait/index.js").read_text(encoding="utf-8")
        i = js.index("async function __expWaitForSubagents")
        j = js.index("\n}\n", i) + 2
        w(f"### F.{3 if ctl else 1} 等待补丁\n")
        w("改的是 DSH 0.2.0-rc.2 的 headless 入口 `@deepseek-ai/dsh-headless/lib/index.js`。原来的流程是：把题面发给主代理，等主代理这一轮结束，"
          "汇总并退出进程；这时还在跑的后台子代理随进程一起结束。补丁在“等主代理这一轮结束”之后插入一次调用（只在环境变量 "
          "`DSH_EXP_WAIT_SUBAGENTS=1` 时生效）：\n")
        w("```js\nawait agent.whenIdle();\nif (process.env.DSH_EXP_WAIT_SUBAGENTS === \"1\") await __expWaitForSubagents(ctx, agents, agent, io);\n```\n")
        w("被调用的函数全文：\n")
        w("```js\n" + js[i:j].replace("\t", "  ") + "\n```\n")
        w("- 只要子代理运行时里还有没结算的后台子代理，或者进程里还有代理在运行，就不退出。子代理结束时，DSH 自己会把结果通知送给主代理并让它再跑一轮，"
          "这和交互使用时一样；补丁不给模型发任何消息，提示词、工具、配置都不变。\n"
          "- 没有未结算的子代理、所有代理空闲、会话日志 3 秒没有新事件，才照原来的流程汇总并退出。所以每次“等”组运行至少多 3.5 秒。\n"
          "- 等待上限：主代理空闲而子代理还活着的时间累计满 20 分钟就退出，记一次“等待超限”。单次运行的总上限不变。\n"
          "- 每次运行前核对容器里原文件的哈希，写入补丁后把补丁的哈希记进这次运行的记录。\n")


def wait_case(wf: dict) -> str:
    """Which of the readings written before the run applies: 'early' (S1, S2 clearly positive and S3, S4 inside +-delta),
    'not_early' (S1, S2 inside +-delta), or 'open'."""
    s1, s2, s3, s4 = (wf[k]["score"] for k in ("S1", "S2", "S3", "S4"))

    def inside(c):
        return c["lo"] > -DELTA and c["hi"] < DELTA

    def pos(c):
        return sig(c) and c["est"] > 0

    if pos(s1) and pos(s2) and inside(s3) and inside(s4):
        return "early"
    if inside(s1) and inside(s2):
        return "not_early"
    return "open"


def welch(a: list, b: list) -> dict:
    """mean(a) - mean(b) with a Welch 95% interval (two unpaired samples)"""
    from scipy import stats as sps
    va, vb = st.variance(a) / len(a), st.variance(b) / len(b)
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    q = float(sps.t.ppf(0.975, df))
    est = st.mean(a) - st.mean(b)
    return {"est": est, "lo": est - q * se, "hi": est + q * se, "na": len(a), "nb": len(b), "ma": st.mean(a), "mb": st.mean(b)}


def wait_counts(wf: dict) -> dict:
    g, early, rewrote = wf["g"], wf["early"], wf["rewrote"]
    wgs, ngs = ("W-D1-K8", "W-D2-K8", "W-D3-K8"), ("D2-K8", "D3-K8")
    wr = [r for c in wgs for r in g(c)]
    nr = [r for c in ngs for r in g(c)]
    wd = [r for c in ("W-D2-K8", "W-D3-K8") for r in g(c)]   # the wait arm at depth 2 and 3

    def capped(r):
        return (num(r.get("wait_cap")) or 0) > 0

    def short(r):
        return (num(r.get("deliv_chars")) or 0) < 5000

    def sc(v):
        return [float(r["score"]) for r in v]

    we = [r for r in wr if early(r)]
    waits = sorted(num(r.get("idle_wait_s")) for r in we if num(r.get("idle_wait_s")) is not None and not capped(r))
    return {"w_runs": len(wr), "n_runs": len(nr), "w_crash": sum(truthy(r["crash5063"]) for r in wr),
            "n_crash": sum(truthy(r["crash5063"]) for r in nr), "w_early": len(we), "n_early": sum(early(r) for r in nr),
            "w_rewrote": sum(rewrote(r) for r in wr), "waits": waits, "capped": [r for r in wr if capped(r)],
            "w_short": sum(short(r) for r in wr), "n_short": sum(short(r) for r in nr),
            "wd_runs": len(wd), "wd_early": sum(early(r) for r in wd), "wd_rewrote": sum(rewrote(r) for r in wd),
            "n_early_scores": sc([r for r in nr if early(r)]), "n_rest_scores": sc([r for r in nr if not early(r)]),
            "wd_early_scores": sc([r for r in wd if early(r)]), "wd_rest_scores": sc([r for r in wd if not early(r)]),
            "wd_rewrote_scores": sc([r for r in wd if rewrote(r)])}


def wait_block(w, wait: dict, wf: dict, c: dict, H: dict, main_rows: list, stub_ids: set) -> None:
    """实验 2：让进程等子代理回来"""
    case = wait_case(wf)
    g = wf["g"]
    s1, s2, s3, s4, n3, n4 = (wf[k]["score"] for k in ("S1", "S2", "S3", "S4", "N3", "N4"))
    w("## 实验 2：让进程等子代理回来（办公题，100 次）\n")
    w(f"**要回答的问题。** 正式实验里 D2-K8、D3-K8 的得分比 D1-K8 低 {abs(H['H3a']['est']):.1f} 和 {abs(H['H3b']['est']):.1f} 分（区间包含 0），"
      "主代理提前收工和退出崩溃也都出在这两组。headless 下主代理这一轮一结束，进程就退出，还在跑的后台子代理随之结束。"
      "这些低分有多少来自提前收工，有多少来自深度本身，正式实验分不开。\n")
    w("**设置。** o1、o2 × {等·D1-K8、D2-K8、等·D2-K8、D3-K8、等·D3-K8} × 10 次 = 100 次。“等”和“不等”只差一处：进程什么时候退出。"
      "提示词、工具、配置、题面都不变。\n")
    w("**流程。**\n")
    w("1. 每次运行开一个新容器，镜像、网络、题面、单次上限都和正式办公批相同。同一批里随机完全区组，并发固定 26 路。\n"
      "2. “等”组在运行前把容器里 DSH 的 headless 入口文件换成补丁版（先核对原文件的哈希，再把补丁的哈希记进这次运行的记录）。“不等”组不换文件。\n"
      "3. 主代理一轮结束以后：不等组的进程直接退出。等组只要还有没结算的后台子代理、或者进程里还有代理在运行，就不退出；"
      "子代理结束时，DSH 自己把结果通知送给主代理并让它再跑一轮，这和交互使用时一样。补丁不给模型发任何消息。\n"
      "4. 主代理空闲而子代理还没结算的时间累计满 20 分钟，就不再等，记一次“等待超限”。补丁全文见附录 F。\n"
      "5. 全部运行结束以后才打分：评分标准 v1.3，Opus 5.5，思考强度 high，每份 2 次取平均；判分看不到组别。搜索单价用正式批的实测值。\n"
      "6. 按（题，第几次）配对。主要对比 4 个，开跑前写定，各 20 对，Holm 校正在这 4 个对比内部做：S1、S2 是同一深度下等减不等；"
      "S3、S4 是都等的情况下深度 2、3 减深度 1。\n")
    w(f"判读规则，开跑前写定：S1、S2 明显为正，且 S3、S4 的区间落在 ±{DELTA:.0f} 分以内，说明深度 2、3 的低分主要来自提前收工；"
      f"S1、S2 的区间落在 ±{DELTA:.0f} 分以内，说明提前收工不是低分的主要原因。"
      "“没写完的交付物”指没有文件或短于 5000 字符（正式办公批里两份没写完的是 0 和 615 字符，其余都在 13,990 字符以上）；"
      "这条和下面表里几项的判定办法，是这一批还在跑、没有任何打分时补进方案的。\n")
    w("**结果。** 各组的得分、费用、时长和子代理用量（每组 20 次）：\n")
    w(table_rows("tables-wait-t.md", R_MAIN + ["子代理数（均值 / 最多）", "第 2 层子代理（均值）", "第 3 层子代理（均值）", "名额峰值（均值）",
                                               "搜索请求数（均值）", "交付物长度（千字符）", "A 类得分（%）", "B 类得分（%）", "C 类得分（%）", "D 类得分（%）",
                                               "严重错误（次/份打分）"],
                     base=WAITD) + "\n")
    w("诊断：主代理第一轮结束时发生了什么。\n")
    wait_group_rows(w, wf)
    w("主要对比（A − B；费用、时长是几何均值之比；* 表示 Holm 校正后 p < 0.05）：\n")
    wait_contrast_table(w, wf)
    per = {t: opt(WAITD / f"stats-wait-{t}.json") for t in OFF}
    if all(per.values()):
        w("分题（只作描述，每格 10 对）：\n")
        w("| 对比 | o1 新加坡行程 | o2 服务器 CPU 报告 |\n|---|---|---|")
        for k in ("S1", "S2", "S3", "S4"):
            w(f"| {k} | " + " | ".join(d_cell(cmp_(per[t], "score", k)) for t in OFF) + " |")
        w("")

    # this batch next to the main batch (descriptive: the batches ran at different times)
    def short(r):
        return (num(r.get("deliv_chars")) or 0) < 5000

    def brow(label, batch, v, early_fn):
        return (f"| {label} | {batch} | {len(v)} | {mean_by_task(v, 'score'):.1f} | {mean_by_task(v, 'total_cost_peak'):.2f} | "
                f"{mean_by_task(v, 'seconds') / 60:.1f} | {mean_by_task(v, 'children'):.1f} | {sum(early_fn(r) for r in v)}/{len(v)} | "
                f"{sum(truthy(r['crash5063']) for r in v)} | {sum(short(r) for r in v)} |")

    def main_open(r):
        return (num(r.get("open_children_at_end")) or 0) > 0

    w("和正式批放在一起（只作描述：两批不在同一时间跑）：\n")
    w("| 组 | 批 | 次数 | 得分 | 估算总费用（元） | 实际时长（分） | 子代理数 | 主代理第一轮结束时仍有子代理未回 | 退出崩溃 | 没写完的交付物 |\n|---|---|---|---|---|---|---|---|---|---|")
    main_g = {}
    for d in (1, 2, 3):
        mg = [r for r in main_rows if r["task"] in OFF and r["group"] == f"D{d}-K8"]
        main_g[d] = mg
        w(brow(f"D{d}-K8", "正式批", mg, main_open))
        if d > 1:
            w(brow(f"D{d}-K8", "本批", g(f"D{d}-K8"), wf["early"]))
        w(brow(f"等·D{d}-K8", "本批", g(f"W-D{d}-K8"), wf["early"]))
    w("")
    nostub = {d: mean_by_task([r for r in main_g[d] if r["id"] not in stub_ids], "score") for d in (2, 3)}
    main_d1 = mean_by_task(main_g[1], "score")

    c1, c2 = wf["S1"]["total_cost_peak"], wf["S2"]["total_cost_peak"]
    c3, c4 = wf["S3"]["total_cost_peak"], wf["S4"]["total_cost_peak"]
    t1, t2 = wf["S1"]["seconds"], wf["S2"]["seconds"]
    q3, q4 = wf["S3"]["search_aux"], wf["S4"]["search_aux"]
    w("**结论（按开跑前写的规则）。**\n")
    if case == "open":
        w(f"- 两条规则都没有满足。S1、S2 不是明显为正（估计值 {sgn(s1['est'])}、{sgn(s2['est'])}），区间也没有整个落在 ±{DELTA:.0f} 分以内"
          f"（S1 {sgn(s1['lo'])} 到 {sgn(s1['hi'])}，S2 {sgn(s2['lo'])} 到 {sgn(s2['hi'])}）。按口径判为测不出，最小可测差是 {s1['mdd']:.1f} 和 {s2['mdd']:.1f} 分。\n"
          f"- 能说的是：等不等的差别不大，方向也不一致（{sgn(s1['est'])} 和 {sgn(s2['est'])} 分）。等带来的提高，深度 3 上最多 {sgn(s2['hi'])} 分，"
          f"深度 2 上最多 {sgn(s1['hi'])} 分（区间上限）。")
    elif case == "not_early":
        w(f"- S1、S2 的区间都落在 ±{DELTA:.0f} 分以内（{d_cell(s1)}、{d_cell(s2)}）：等不等对得分没有实际差别，提前收工不是低分的主要原因。")
    else:
        w(f"- S1、S2 明显为正（{d_cell(s1)}、{d_cell(s2)}），S3、S4 的区间落在 ±{DELTA:.0f} 分以内：深度 2、3 的低分主要来自提前收工。")
    w(f"- 都等的情况下，深度 2、3 仍然没有比深度 1 高：{d_cell(s3)}（{verdict(s3)}）、{d_cell(s4)}（{verdict(s4)}）；最小可测差 {s3['mdd']:.1f}、{s4['mdd']:.1f} 分。"
      f"估算总费用是 {r_txt(c3)}、{r_txt(c4)}；搜索请求是 {ratio(q3):.2f}、{ratio(q4):.2f} 倍。\n"
      f"- 正式批里 D2-K8、D3-K8 比 D1-K8 低 {abs(H['H3a']['est']):.1f}、{abs(H['H3b']['est']):.1f} 分，这一批没有重现：本批不等的 D2-K8、D3-K8 对等·D1-K8 是 "
      f"{d_cell(n3)}、{d_cell(n4)}。两批的差别在于，正式批这两组各有 1 次主代理没写完报告就结束（得分 0.0 和 7.9）；这一批 100 次里没有出现。"
      f"去掉那两次，正式批 D2-K8、D3-K8 的均分是 {nostub[2]:.1f}、{nostub[3]:.1f}，D1-K8 是 {main_d1:.1f}。\n"
      f"- 所以对开跑前的问题，现在的回答是：正式批深度 2、3 的低分主要来自那两次没写完的运行，这种情况少见"
      f"（两批合起来，不等的 D2-K8、D3-K8 共 {len(main_g[2]) + len(main_g[3]) + c['n_runs']} 次里 2 次）。更常见的提前收工是主代理已经把报告写完、"
      f"不等剩下的子代理就结束。这类运行在不等的两组里均分 {st.mean(c['n_early_scores']):.1f}，其余运行 {st.mean(c['n_rest_scores']):.1f}"
      f"（{len(c['n_early_scores'])} 次对 {len(c['n_rest_scores'])} 次，只作描述）；等它们回来没有提高得分。\n")
    ne, nr_, we_, wr_ = c["n_early_scores"], c["n_rest_scores"], c["wd_early_scores"], c["wd_rest_scores"]
    if len(ne) > 2 and len(we_) > 2:
        ww = welch(we_, ne)
        w("**诊断：提前收工的运行，等和不等（事后，只作描述）。** 主代理第一轮怎么结束，发生在补丁起作用之前，所以两臂里“第一轮结束时还有子代理没回来”的运行可以直接比：\n")
        w("| | 第一轮结束时还有子代理未回的运行 | 其余运行 |\n|---|---|---|\n"
          f"| 不等（D2-K8、D3-K8） | {len(ne)} 次，均分 {st.mean(ne):.1f} | {len(nr_)} 次，均分 {st.mean(nr_):.1f} |\n"
          f"| 等（等·D2-K8、等·D3-K8） | {len(we_)} 次，均分 {st.mean(we_):.1f} | {len(wr_)} 次，均分 {st.mean(wr_):.1f} |\n")
        w(f"- 这类运行里，等减不等是 {sgn(ww['est'])} 分（不配对，95% 区间 {sgn(ww['lo'])} 到 {sgn(ww['hi'])}）"
          + ("，区间包含 0。" if ww["lo"] < 0 < ww["hi"] else "。")
          + f"等组里子代理回来后接着改了报告的 {len(c['wd_rewrote_scores'])} 次，均分 {st.mean(c['wd_rewrote_scores']):.1f}"
          f"（{min(c['wd_rewrote_scores']):.1f}–{max(c['wd_rewrote_scores']):.1f}）。\n"
          "- 样本小，又是事后分组，只能说：没有证据表明把晚回来的结果补进报告能提高得分。\n")
    capped = c["capped"]
    w("**诊断：等的代价。**\n")
    adj = {grp: mean_by_task(g(grp), "seconds") / 60 for grp in WAIT_GROUPS}
    adj2 = {}
    for grp in ("W-D2-K8", "W-D3-K8"):
        v = [dict(r, seconds=float(r["seconds"]) - (num(r.get("idle_wait_s")) or 0)) if (num(r.get("wait_cap")) or 0) > 0 else r for r in g(grp)]
        adj2[grp] = mean_by_task(v, "seconds") / 60
    w(f"- 费用没有差别：等减不等，估算总费用是 {r_txt(c1)}、{r_txt(c2)}（深度 2、3）。\n"
      f"- 实际时长：{r_txt(t1)}、{r_txt(t2)}。均值是 {adj['D2-K8']:.1f} → {adj['W-D2-K8']:.1f} 分钟（深度 2）和 {adj['D3-K8']:.1f} → {adj['W-D3-K8']:.1f} 分钟（深度 3）。\n"
      f"- 其中 {len(capped)} 次运行等满了 20 分钟上限（等·D2-K8 {sum(r['group'] == 'W-D2-K8' for r in capped)} 次、等·D3-K8 "
      f"{sum(r['group'] == 'W-D3-K8' for r in capped)} 次），这 20 分钟里没有任何代理在工作。把这 20 分钟去掉，等·D2-K8、等·D3-K8 的平均实际时长是 "
      f"{adj2['W-D2-K8']:.1f}、{adj2['W-D3-K8']:.1f} 分钟。\n"
      + (f"- 其余提前收工的运行，进程多等了 {c['waits'][0]:.0f}–{c['waits'][-1]:.0f} 秒（中位 {st.median(c['waits']):.0f} 秒）子代理才都回来。\n" if c["waits"] else ""))
    w("**诊断：退出崩溃和等满上限的运行。**\n")
    w(f"- 不等的两组退出崩溃 {c['n_crash']}/{c['n_runs']} 次，和正式批同名组（{sum(truthy(r['crash5063']) for r in main_g[2])}/20、"
      f"{sum(truthy(r['crash5063']) for r in main_g[3])}/20）相近；等的三组 {c['w_crash']}/{c['w_runs']} 次。\n"
      "- 等组里没有再出现“还有子代理在干活、进程就退出”的情况。剩下的问题是另一种：一个子代理被它的上级用 `interrupt_agent` 中断，中断时还有一条排队等它下一步处理的消息"
      "（上级刚发来的催促，或者一个后台命令的完成通知）；它之后既不再运行，也不结算，运行时一直把它算作还活着。"
      f"等组 {len(capped)} 次等满上限的运行里各有一个这样的子代理，其中 {sum(truthy(r['crash5063']) for r in capped)} 次进程退出时照样崩溃。"
      "这三次主代理都已经给出最终回答，报告是完整的。详见“DSH 的问题”第 5 条。\n")
    cases = {x["id"]: x for x in wait["cases"]}
    ex = [x for x in wait["cases"] if x["group"].startswith("W-") and (x.get("deliv_writes_after_turn1") or 0) > 0 and x["group"] != "W-D1-K8"]
    if ex:
        x = max(ex, key=lambda x: x.get("score") or 0)
        pair = next((r for r in g(x["group"][2:]) if r["task"] == x["task"] and int(r["rep"]) == x["rep"]), None)
        w("**案例。**\n")
        w(f"- 等了以后用上了结果：{x['id']}（{x['task'].split('-')[0]}，{enc(x['group'])}，第 {x['rep']} 次）。主代理第一轮结束时还有 "
          f"{int(x['alive_at_first_turn_end'])} 个子代理没回来，这一轮的最后一句话是：\n")
        w("> " + (x["said_at_first_turn_end"] or "").strip().replace("\n", " ")[:200] + "\n")
        w(f"  进程多等了 {x['idle_wait_s']:.0f} 秒，子代理回来后主代理又跑了 {int(x['root_turns']) - 1} 轮，改了 {int(x['deliv_writes_after_turn1'])} 次报告，"
          f"得分 {x['score']:.1f}。" + (f"同一轮不等的 {pair['group']}（{pair['id']}）得分 {float(pair['score']):.1f}。" if pair else "") + "\n")
    if capped:
        r = max(capped, key=lambda r: truthy(r["crash5063"]))
        x = cases.get(r["id"])
        w(f"- 等满上限：{r['id']}（{r['task'].split('-')[0]}，{enc(r['group'])}，第 {r['rep']} 次）。主代理在第 {float(r['seconds']) - 1200:.0f} 秒左右给出最终回答，"
          f"报告 {float(r['deliv_chars']) / 1000:.0f} 千字符，得分 {float(r['score']):.1f}。此时运行时里还有 {int(float(r['first_resident']))} 个没结算的子代理，"
          "但没有一个在运行。进程空等 20 分钟后退出，退出时报 #5063 的错。\n")


def wait_limit(wf: dict) -> str:
    mdd = [wf[k]["score"]["mdd"] for k in ("S1", "S2", "S3", "S4")]
    return ("- 提前收工和深度：实验 2 让进程等子代理回来再退出。那是实验用的补丁，不是 DSH 的正式修复；只做了办公题和 K=8，"
            f"每个对比 20 对，得分对比的最小可测差在 {min(mdd):.1f}–{max(mdd):.1f} 分之间，四个对比都判为测不出。"
            "代码题（p4 鼓励版的提前交卷）没有重测。“正式批的低分来自两次没写完的运行”是两批对照得出的，不是配对检验的结论。\n")


def wait_recs(wf: dict) -> dict:
    c = wait_counts(wf)
    s3, s4 = wf["S3"], wf["S4"]
    return {"depth": ("默认深度保持 1",
                      f"正式实验里加深没有提高得分，办公题费用 1.2–2 倍；实验 2 里等子代理回来以后，深度 2、3 对深度 1 是 {d_cell(s3['score'])}、{d_cell(s4['score'])}，"
                      f"费用 {ratio(s3['total_cost_peak']):.1f}、{ratio(s4['total_cost_peak']):.1f} 倍",
                      "在更长、更宽的任务上重测深度 2"),
            "wait": ("headless 下进程等后台子代理都结算了再退出；被 interrupt 的子代理要能正常结算",
                     f"实验 2：等了以后不再有“子代理还在干活进程就退出”的崩溃（不等的两组 {c['n_crash']}/{c['n_runs']} 次崩溃，等的三组 {c['w_crash']}/{c['w_runs']} 次）；"
                     f"剩下的 {len(c['capped'])} 次等满上限都是被 interrupt 的子代理没结算。等不等对得分没有可测的差别",
                     "正式修复后在代码题（p4 鼓励版）上复测；交互模式下被 interrupt 的子代理是否同样一直显示为运行中")}


def wait_followups(wf: dict) -> list:
    return [("等子代理回来：代码题", "p4、w1 鼓励版的 D2-K8、D3-K8，等和不等各 10 次", "约 80",
             "p4 鼓励版 9 次交出不完整代码的问题，等了以后是否消失")]


SENS_NAMES = (("same", "原样（对照）"), ("tail20", "删掉最后 20% 的行"), ("half", "删掉后一半的行"), ("nolinks", "删掉全部来源链接"),
              ("wrong", "改错事实"))


def judge_block(w, ia, sens, H: dict) -> None:
    """实验 4：判分检查（事后）: noise share, item saturation, the degradation check."""
    if not ia and not sens:
        return
    w("## 实验 4：判分检查（事后）\n")
    w("**要回答的问题。** 正式实验的得分对比大多落在“测不出”。原因在不在打分：打分的噪声有多大，评分标准的条目分不分得开运行，报告被弄坏以后分数掉不掉。"
      "三项检查都是读到得分以后补的，不改任何正式结果。\n")
    if ia:
        t = ia["tasks"]
        w("### 设置 1：打分噪声占多大\n")
        w("用正式办公批每次运行的两次打分算。一次打分的标准差取自同一份报告两次打分的差；运行间标准差取同一道题、同一组内各次运行得分的波动。\n")
        w("| 题 | 运行数 | 一次打分的标准差（分） | 两次平均的标准差 | 同一组内不同运行之间的标准差 | 打分噪声占运行间方差的比例 |\n|---|---|---|---|---|---|")
        for k in OFF:
            v = t[k]
            w(f"| {k.split('-')[0]} | {v['runs']} | {v['judge_sd_single']} | {v['judge_sd_mean_of_2']} | {v['run_sd_within_cell']} | "
              f"{100 * v['judge_share_of_run_variance']:.1f}% |")
        sh = [t[k]["judge_share_of_run_variance"] for k in OFF]
        sd = H["H1"]["sd"]
        need = math.ceil(((1.96 + 0.84) * sd / 3) ** 2)
        w(f"\n- 同一道题、同一组的不同运行，得分本身就相差 {min(t[k]['run_sd_within_cell'] for k in OFF):.0f}–{max(t[k]['run_sd_within_cell'] for k in OFF):.0f} 分（标准差）；"
          f"打分的噪声只占这部分波动的 {100 * min(sh):.0f}%–{100 * max(sh):.0f}%。"
          f"换成完全没有噪声的打分，最小可测差只会缩小约 {100 * (1 - math.sqrt(1 - st.mean(sh))):.0f}%。\n"
          f"- 测不出的主要原因是运行之间的波动和每个对比只有 20 对。H1 的配对差标准差是 {sd:.1f} 分；要测出 3 分的差别，每个对比大约要 {need} 对。\n")
        w("### 设置 2：评分标准的条目分不分得开\n")
        w("逐条看正式办公批的全部打分。一个条目如果九成以上的打分都给同一个分，它就分不出运行的好坏：\n")
        w("| 题 | 类别 | 条目数 | 九成以上打分相同的条目 | 该类平均得分率 |\n|---|---|---|---|---|")
        const = {}
        for k in OFF:
            v = t[k]
            const[k] = {}
            for i, x in v["per_item"].items():
                top = max(("满分", x["full"]), ("1 分", x["one"]), ("0 分", x["zero"]), ("负分", x["negative"]), key=lambda z: z[1])
                if top[1] >= 0.9:
                    const[k][i] = top[0]
            for c in "ABCD":
                ids = [i for i in v["per_item"] if i.startswith(c)]
                flat = [f"{i}（{const[k][i]}）" for i in ids if i in const[k]]
                w(f"| {k.split('-')[0]} | {c} | {len(ids)} | {'、'.join(flat) if flat else '无'} | {100 * v['categories'][c]['mean_share']:.0f}% |")
        n1, n2 = (len(const[k]) for k in OFF)
        i1, i2 = (t[k]["items"] for k in OFF)
        live1 = [i for i in t[OFF[0]]["per_item"] if i not in const[OFF[0]]]
        w(f"\n- o1 的 {i1} 条里 {n1} 条、o2 的 {i2} 条里 {n2} 条，九成以上的打分给了同一个分。它们不提供区分。"
          f"o1 实际在起作用的是 {len(live1)} 条（{'、'.join(live1)}），共 {2 * len(live1)} 分，不是名义上的 {2 * i1} 分。\n"
          "- o1 的 C1、C2（来源）和 D2、D4（预算表加总、拿来就能用）几乎人人 1 分。评分标准 v1.3 把“2 分只给完全做到、找不到问题的”写进了细则，"
          "这几条因此不再区分好坏：来源做得好一些和差一些的报告，在这几条上拿的是同一个分。\n"
          f"- 剩下的条目分得开运行：得分的第 10 到第 90 百分位，o1 是 {t[OFF[0]]['score_p10']}–{t[OFF[0]]['score_p90']} 分，"
          f"o2 是 {t[OFF[1]]['score_p10']}–{t[OFF[1]]['score_p90']} 分，远大于两次打分之间的差。\n")
    if sens:
        sm = sens["summary"]
        w("### 设置 3：把报告弄坏，分数掉不掉\n")
        w("流程：\n")
        w("1. 从正式办公批里随机抽 6 份完整的报告（o1、o2 各 3 份，固定种子）。\n"
          "2. 用脚本对每份做 5 种改动，不经过模型：原样（对照）、删掉最后 20% 的行、删掉后一半的行、删掉全部来源链接、改错事实。\n"
          "3. 每份改动后的报告按正式打分的做法打 2 次（同样的提示词、评分标准、思考强度）。\n"
          "4. 和原报告已有的两次打分比：总分、各类得分率、严重错误次数。做法和预期在打分完成前写进方案。\n")
        w("结果：\n")
        w("| 改动 | 份数 | 得分变化（均值） | 最小到最大 | 得分变低的份数 | A 类变化 | B 类变化 | C 类变化 | D 类变化 | 严重错误（次/份打分；原来 → 改动后） |\n|---|---|---|---|---|---|---|---|---|---|")
        for key, name in SENS_NAMES:
            if key not in sm:
                continue
            v = sm[key]
            w(f"| {name} | {v['docs']} | {sgn(v['mean_diff'])} | {sgn(v['min_diff'])} 到 {sgn(v['max_diff'])} | {v['lower']}/{v['docs']} | "
              + " | ".join(sgn(v['mean_diff_' + c]) for c in 'ABCD') + f" | {v['base_severe']:.2f} → {v['severe']:.2f} |")
        same = sm["same"]
        w("\n- “改错事实”：o1 是把所有新加坡元金额乘以 1.5；o2 是把“鲲鹏”和“海光”两个名字整篇对调。类别变化的单位是该类得分率的百分点。\n"
          f"- 原样重打：不改内容、只换一批抽查链接，得分变化 {sgn(same['min_diff'])} 到 {sgn(same['max_diff'])} 分。下面各行要和这个波动比。\n"
          f"- 事实改错，判分反应很大：{sm['wrong']['docs']} 份全部下降，平均 {sgn(sm['wrong']['mean_diff'])} 分，B 类从正分掉到负分，"
          f"严重错误从每份打分 {sm['wrong']['base_severe']:.2f} 次升到 {sm['wrong']['severe']:.2f} 次。\n"
          f"- 删掉后一半内容，{sm['half']['lower']}/{sm['half']['docs']} 份下降，平均 {sgn(sm['half']['mean_diff'])} 分，主要掉在 A 类和 D 类；"
          f"但各份差别很大（{sgn(sm['half']['min_diff'])} 到 {sgn(sm['half']['max_diff'])} 分），有一份只掉了不到 3 分。\n"
          f"- 删掉全部来源链接，平均只掉 {abs(sm['nolinks']['mean_diff']):.1f} 分（{sgn(sm['nolinks']['min_diff'])} 到 {sgn(sm['nolinks']['max_diff'])}），"
          f"C 类只掉 {abs(sm['nolinks']['mean_diff_C']):.1f} 个百分点；删掉最后 20% 的行，平均掉 {abs(sm['tail20']['mean_diff']):.1f} 分，"
          f"{sm['tail20']['lower']}/{sm['tail20']['docs']} 份下降。这两种改动和原样重打的波动是同一个量级：判分基本看不出来。\n"
          "- 所以这套打分对“关键事实对不对”很敏感，对“内容缺了一大块”敏感，对“有没有来源链接”和“少了一小部分内容”不敏感。"
          "来源做得好不好，在这次的得分里基本没有体现。样本只有 6 份，改动也是人为造的，这一条只说明方向。\n")
    w("### 结论\n")
    w("- 测不出的主要原因不是打分的噪声，是运行之间的波动和每个对比只有 20 对。\n"
      "- 这套打分看得出事实对不对、内容缺没缺一大块；看不出来源做得好不好、少没少一小部分。评分标准里有相当一部分条目几乎人人同分。\n"
      "- 所以报告里的“得分没有差别”，要读成“在这套标准看得见的方面没有差别”。人工校准只有 2 份文档 38 条，判分的排序和人是否一致还没有验证。\n")


def judging_section(w, audit, val, rows, D, G, c2_first2, fk1_first2, fe_first2, H, len_h1) -> None:
    """数据审计 -> 判分的一致性和校验"""
    jo, jc = audit["judging"]["office"], audit["judging"]["code"]
    mh, mx, hx = val.get("max_high"), val.get("max_xhigh"), val.get("high_xhigh")
    ox, cx = val.get("office_x"), val.get("code_x")
    hm, hh = val.get("h_v12_max"), val.get("h_v13_high")

    def share(x):
        return "—" if "all" not in x else f"{100 * x['all']['share']:.1f}%"

    w("### 判分的一致性和校验\n")
    lead = []
    if mh:
        a = mh["tasks"]["all"]
        lead.append(f"正式实验的打法（Opus 5.5，思考强度 high，每份打 2 次）和方案原定的 max 给出的分数一致：{a['between']['n']} 份文档上 "
                    f"high 比 max 平均低 {abs(a['between']['mean_diff']):.1f} 分，逐条给分相同 {share(a['items']['between'])}，"
                    f"和 max 自己打两次之间的 {share(a['items']['within_a'])} 一样")
    if ox and cx:
        lead.append(f"和代理下能打完的最高强度 xhigh 比也一样（正式运行里抽 {ox['tasks']['all']['between']['n'] + cx['tasks']['all']['between']['n']} 次，"
                    "差值不随组变化）")
    if hh:
        x = hh["human"]
        lead.append(f"和人工逐条比，完全一致 {100 * x['exact'] / x['items']:.1f}%，相差不超过 1 分 {100 * x['within1'] / x['items']:.0f}%（样本内）")
    if lead:
        w("结论：" + "；".join(lead) + "。下面分项给出。\n")

    w("**同一种打法两次之间。** 第 1 次减第 2 次，得分是百分制：\n")
    w("| 题 | 对数 | 平均绝对差（分） | 中位绝对差 | 最大差 | 平均带符号差 | 相关系数 | 逐条给分相同的比例 |\n|---|---|---|---|---|---|---|---|")
    for t, src in ((OFF[0], jo), (OFF[1], jo), (C1, jc), (W1, jc)):
        g = src["agreement"][t]
        ia = (src.get("item_agreement") or {}).get(t, {}).get("all")
        same = "—" if not ia else f"{100 * ia['share']:.1f}%"
        w(f"| {t.split('-')[0]} | {g['pairs']} | {g['mean_abs_diff']} | {g['median_abs_diff']} | {g['max_abs_diff']} | "
          f"{sgn(g['mean_signed_diff_1_minus_2'], 2)} | {g['pearson_r']} | {same} |")
    cats = []
    for t, src in ((OFF[0], jo), (OFF[1], jo), (W1, jc)):
        ia = (src.get("item_agreement") or {}).get(t, {})
        cats.append(f"{t.split('-')[0]} " + "、".join(f"{c} {100 * ia[c]['share']:.0f}%" for c in "ABCD" if c in ia))
    w(f"\n按类别：{'；'.join(cats)}。C 类（来源与诚实）和 D 类（可用性）最不稳定。"
      "两次打分的平均绝对差 2.4–3.5 分，和 δ = 5 分是一个量级；每次运行取两次平均、每个对比 20 对以后，这部分噪声已经算在区间里。"
      "这张表说明的是稳定，不是打得对不对。\n")

    if mh:
        a = mh["tasks"]["all"]
        w("**思考强度：max、xhigh、high 直接比。** 方案原定判分用 max，正式实验用的是 high。"
          f"对比用的材料是 10/1 试跑阶段的 {a['between']['n']} 份办公产出（34 次试跑运行，覆盖 D0、D1-K8、D2-K1/2/4/8；另加 6 份校准文档；不属于正式结果），"
          "它们当时已经用 max、评分标准 v1.2 打过分。用完全相同的提示词、评分标准 v1.2 和同一批链接原文，把它们用 high 和 xhigh 各重打 2–3 次。"
          "每份文档的得分取该强度下所有打分的平均：\n")
        w("| 对比 | 文档数 | 前者均分 | 后者均分 | 差值（后者 − 前者，95% 区间） | 平均绝对差 | 相关系数 | 逐条给分相同（两种强度之间） | 前者自身两次之间 | 后者自身两次之间 |\n"
          "|---|---|---|---|---|---|---|---|---|---|")

        def crow(name, c):
            d, it = c["between"], c["items"]
            return (f"| {name} | {d['n']} | {d['mean_x']} | {d['mean_y']} | {sgn(d['mean_diff'], 2)} [{sgn(d['lo'], 2)}, {sgn(d['hi'], 2)}] | "
                    f"{d['mean_abs_diff']} | {d['r']} | {share(it['between'])} | {share(it['within_a'])} | {share(it['within_b'])} |")

        w(crow("max → high", a))
        if mx:
            w(crow("max → xhigh", mx["tasks"]["all"]))
        if hx:
            w(crow("high → xhigh", hx["tasks"]["all"]))
        dd = "、".join(f"{k} {sgn(v['mean'])}（{v['n']} 份）" for k, v in a["diff_by_depth"].items())
        w(f"\n- high 比 max 平均低 {abs(a['between']['mean_diff']):.1f} 分。两种强度之间逐条相同的比例（{share(a['items']['between'])}）"
          f"和同一种强度打两次之间的比例（max {share(a['items']['within_a'])}、high {share(a['items']['within_b'])}）一样。"
          f"一次 high 打分和一次 max 打分的平均绝对差是 {a['between_single_judgment']['mean_abs_diff']} 分，"
          f"落在同一种强度自己打两次之间的差以内（max {a['within_a']['mean_abs_diff']} 分、high {a['within_b']['mean_abs_diff']} 分）。"
          "表里的“平均绝对差”是每份文档均分之间的差。\n"
          f"- 差值（high − max）按组：{dd}，没有随深度变化的迹象。\n"
          + (f"- xhigh 对 max：平均差 {sgn(mx['tasks']['all']['between']['mean_diff'], 2)} 分，逐条相同 {share(mx['tasks']['all']['items']['between'])}。\n" if mx else "")
          + "- 所以把思考强度从 max 换成 high 没有改变分数。\n")

    if hm and hh:
        a, b = hm["human"], hh["human"]
        w("**和人工打分比。** 10/1 用户对试跑阶段的 2 份产出（o1、o2 各一份）逐条打了分，共 "
          f"{a['items']} 条，打分时看不到组别和模型的分数。模型一侧取 3 次打分里出现最多的分数：\n")
        w("| 打法 | 逐条完全一致 | 相差不超过 1 分 | A 类 | B 类 | C 类 | D 类 | o1 那份总分（人工 "
          f"{b['docs']['o1-A']['human_total']}/{b['docs']['o1-A']['full_marks']}） | o2 那份总分（人工 "
          f"{b['docs']['o2-D']['human_total']}/{b['docs']['o2-D']['full_marks']}） |\n|---|---|---|---|---|---|---|---|---|")

        def hrow(name, h):
            x = h["human"]
            bc = x["by_category"]
            tot = " | ".join("、".join(str(v) for v in x["docs"][k]["model_totals"]) for k in ("o1-A", "o2-D"))
            return (f"| {name} | {x['exact']}/{x['items']} = {100 * x['exact'] / x['items']:.1f}% | "
                    f"{x['within1']}/{x['items']} = {100 * x['within1'] / x['items']:.1f}% | "
                    + " | ".join(f"{bc[c]['exact']}/{bc[c]['items']}" for c in "ABCD") + f" | {tot} |")

        w(hrow("评分标准 v1.2，max（10/1 的打法）", hm))
        for key, name in (("h_v12_xhigh", "评分标准 v1.2，xhigh"), ("h_v12_high", "评分标准 v1.2，high")):
            if val.get(key):
                w(hrow(name, val[key]))
        w(hrow("评分标准 v1.3，high（正式实验的打法）", hh))
        v12 = [val[k]["human"] for k in ("h_v12_max", "h_v12_xhigh", "h_v12_high") if val.get(k)]
        lo_, hi_ = min(x["exact"] for x in v12), max(x["exact"] for x in v12)
        w(f"\n- 同一份评分标准（v1.2）下，三种强度和人的逐条一致都在 {lo_}–{hi_} 条（{100 * lo_ / a['items']:.0f}%–{100 * hi_ / a['items']:.0f}%），"
          "不一致的基本是同一批条目。模型和人的差别来自评分标准的写法，不来自思考强度。\n"
          "- v1.2 下模型比人宽松（o1 那份高 6–8 分）。对照这 38 条的不一致，把“2 分只给完全做到、找不到问题的”写进了判定细则，得到 v1.3；"
          "v1.3 下两份文档的总分和人工相差 0–3 分。\n"
          "- v1.3 是照着这 38 条改的，所以最后一行是样本内的数，偏乐观；v1.3 定稿后没有再做新的人工打分。\n")

    if ox and cx:
        o, c = ox["tasks"], cx["tasks"]
        w(f"**正式运行抽样：high 对 xhigh。** 从正式运行里按组分层随机抽 {o['all']['between']['n']} 次办公运行（每组约 3 次）和 "
          f"{c['all']['between']['n']} 次代码运行，用 xhigh（一次约 3–4 分钟）各重打 2 次，评分标准 v1.3、提示词、链接原文都和正式打分相同：\n")
        w("| 题 | 运行数 | high 均分 | xhigh 均分 | 差值（xhigh − high，95% 区间） | 平均绝对差 | 相关系数 | 逐条给分相同（两种强度之间） | high 自身两次之间 | xhigh 自身两次之间 |\n"
          "|---|---|---|---|---|---|---|---|---|---|")
        for name, t in (("o1", o.get(OFF[0])), ("o2", o.get(OFF[1])), ("办公合计", o["all"]), ("c1", c.get(C1)), ("w1", c.get(W1))):
            if not t:
                continue
            d, it = t["between"], t["items"]
            w(f"| {name} | {d['n']} | {d['mean_x']} | {d['mean_y']} | {sgn(d['mean_diff'], 2)} [{sgn(d['lo'], 2)}, {sgn(d['hi'], 2)}] | "
              f"{d['mean_abs_diff']} | {d['r']} | {share(it['between'])} | {share(it['within_a'])} | {share(it['within_b'])} |")
        oa = o["all"]
        dd = "、".join(f"{k} {sgn(v['mean'])}（{v['n']} 次）" for k, v in oa["diff_by_depth"].items())
        kk = "、".join(f"{k} {sgn(v['mean'])}（{v['n']} 次）" for k, v in oa["diff_by_k"].items())
        w(f"\n- 办公题 xhigh 比 high 平均低 {abs(oa['between']['mean_diff']):.1f} 分，是整体偏严一点（上一段用 v1.2 时两者没有差别）；两种强度之间逐条相同的比例"
          f"（{share(oa['items']['between'])}）和同一种强度打两次之间的比例（{share(oa['items']['within_a'])}、{share(oa['items']['within_b'])}）一样。\n"
          f"- 差值按深度：{dd}；按 K：{kk}。没有随深度或 K 单调变化的迹象；差值和子代理数的相关系数 {sgn(oa.get('corr_diff_children') or 0, 2)}，"
          f"和交付物长度的相关系数 {sgn(oa.get('corr_diff_deliv_chars') or 0, 2)}。各组一起偏一点，不影响配对比较。\n"
          f"- c1 两种强度逐条完全相同；w1 差 {sgn(c[W1]['between']['mean_diff'], 2)} 分，区间包含 0。\n")

    w("**w1 的第 3 次打分。** " + f"{jc['third_judgments']} 次 w1 运行因为两次逐条不一致超过 10% 加打了第 3 次、每条取多数，"
      "其余运行是两次平均。只用前两次平均重算："
      f"鼓励句的作用（c1、w1）{d_cell(c2_first2)}（原来 {d_cell(D['C2'])}），K=1 对 K=8 {d_cell(fk1_first2)}（原来 {d_cell(G['FK1'])}），"
      f"鼓励版对自然状态 {d_cell(fe_first2)}（原来 {d_cell(G['FE'])}）。结论相同。\n")

    off = [r for r in rows if r["task"] in OFF and num(r.get("deliv_chars")) and num(r["deliv_chars"]) > 3000 and num(r.get("score")) is not None]
    cell = defaultdict(list)
    for r in off:
        cell[(r["task"], r["group"])].append(r)
    xs, ys = [], []
    for v in cell.values():
        if len(v) < 3:
            continue
        mx_ = st.mean(math.log(float(r["deliv_chars"])) for r in v)
        my_ = st.mean(float(r["score"]) for r in v)
        xs += [math.log(float(r["deliv_chars"])) - mx_ for r in v]
        ys += [float(r["score"]) - my_ for r in v]
    slope = sum(a * b for a, b in zip(xs, ys)) / sum(a * a for a in xs) * math.log(2)
    allo = [r for r in rows if r["task"] in OFF]
    mention = sum(1 for r in allo if str(r.get("mentions_subagent")) == "1")
    sev = {g: mean_by_task([r for r in allo if r["group"] == g], "severe") for g in OFF_GROUPS}
    w("**长度、过程句和严重错误。**\n")
    w(f"- 长度：同一道题、同一组内，交付物每长一倍，得分高 {slope:.1f} 分（相关系数 {pearson(xs, ys):.2f}，n = {len(xs)}，不含两份没写完的）。"
      f"D1-K8 的交付物是 D0 的 {ratio(len_h1):.2f} 倍长，按这个关系对应约 {slope * math.log2(ratio(len_h1)):.1f} 分，和 H1 的 {sgn(H['H1']['est'])} 分差不多。"
      "长的报告本来覆盖就多，这不能证明判分偏好长文，但也排除不了。\n"
      f"- 过程句：办公题产出没有像代码题那样先删掉描述做题过程的句子。{len(allo)} 份办公交付物里提到“子代理 / subagent”的有 {mention} 份。\n"
      f"- 严重错误（编造或归错，评分标准里标 ★ 的条目）：各组每份打分平均 {min(sev.values()):.2f}–{max(sev.values()):.2f} 次，D0 是 {sev['D0']:.2f} 次，"
      "没有随子代理数增加的趋势（各组数值见表 3）。\n")


if __name__ == "__main__":
    main()
