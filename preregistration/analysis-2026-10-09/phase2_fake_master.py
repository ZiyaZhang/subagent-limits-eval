#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SIMULATED phase-2 rows in the layout of the master table, for dry runs of phase2_report.py and phase2_figures.py.

Nothing here is a result. The rows follow the planned cells (tasks/cells-phase2-*.json) and carry effects chosen in
TRUTH below, so a dry run can check that the analysis recovers them. Every id starts with "sim-" and q_metric is
"SIMULATED"; the output goes to a directory with "dryrun" in its name and phase2_report.py prints a warning banner when
it sees such rows.

Usage: phase2_fake_master.py [--out results/analysis-phase2-dryrun/master] [--seed 20261009] [--null]
  --null   every quality effect is 0 (to see how often a contrast comes out by chance)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent
COLS = ("id batch task family rep block group D K hint told wait web started_utc order status exit root_end oom_kill "
        "kids_after_answer wait_cap complete recognized q q_metric facts63 facts_all facts_wrong facts_right_n tests_failed "
        "rubric_score report_chars t_answer_s process_s t_first_kid_s t_last_write_s t_last_event_s all_written_s agents "
        "kids_d1 kids_d2 kids_d3 review_kids spawn_calls rejected_depth rejected_cap tok_miss tok_hit tok_out "
        "search_requests n_web_search n_web_fetch pages_saved model_yuan search_yuan total_yuan root_turns mem_peak_gb "
        "parallel module model model_requested peak_alive peak_alive_d1 peak_alive_time_s model_yuan_offpeak drb2_recall "
        "drb2_analysis drb2_presentation drb2_blocked_rate judge_calls judge_anomalous q_opus q_gpt_r2 judge_note").split()
TAG_HINT = {"b3": "split-3-delegate", "b8": "split-8-delegate", "gs": "split-8-self", "gm": "search-150-250", "po": "planner-only"}
# (quality points against the default, cost multiple, time multiple, subagents the model wants at depth 1, per extra level)
TRUTH = {
    "D0": (-3.5, 0.32, 0.90, 0, 0), "K1": (-1.0, 0.52, 1.60, 3.4, 0), "K2": (-0.5, 0.70, 1.25, 3.4, 0), "K3": (0.0, 0.85, 1.08, 3.4, 0),
    "K4": (0.0, 1.00, 1.02, 3.4, 0), "K8": (0.0, 1.00, 1.00, 3.4, 0), "D2K8": (0.6, 1.65, 1.20, 3.6, 4.0), "D2K16": (0.5, 1.90, 1.20, 3.6, 5.5),
    "D3K8": (0.4, 1.70, 1.25, 3.6, 4.2), "D2K2": (-0.5, 0.80, 1.30, 3.4, 1.0), "D2K4": (0.0, 1.20, 1.10, 3.4, 2.0), "D3K2": (-0.6, 0.80, 1.35, 3.4, 1.0),
    "D3K4": (0.0, 1.25, 1.15, 3.4, 2.0), "D3K16": (0.5, 2.00, 1.30, 3.6, 6.0), "D3K64": (0.8, 2.90, 1.40, 3.8, 9.0),
    "b3K8": (0.5, 1.00, 1.00, 3.0, 0), "b8K8": (1.0, 2.00, 1.05, 8.0, 0), "b8K6": (0.7, 1.90, 1.15, 8.0, 0), "b8K4": (0.2, 1.80, 1.30, 8.0, 0),
    "b8K2": (-0.8, 1.60, 1.80, 8.0, 0), "gmD0": (-1.5, 0.78, 1.30, 0, 0), "gsD0": (-3.0, 0.40, 1.00, 0, 0), "poK8": (-0.5, 1.10, 1.05, 4.5, 0),
    "merge": (-0.5, 0.25, 0.35, 0, 0),
}
CODE = {  # task -> (family, base yuan, base minutes, subagents wanted)
    "toolkit-xl": ("xl", 19.0, 26.0, 20), "pw-exercises-free": ("free24", 4.3, 9.0, 24), "n1-chain16": ("chain", 0.6, 3.0, 1)}


def base_of(group: str) -> tuple:
    """group name -> (truth key, D, K, hint)."""
    g = group[2:] if group.startswith("W-") else group
    tag = None
    if g.startswith("P"):
        tag, g = g[1:].split("-", 1)
    parts = g.split("-")
    D = int(parts[0][1:])
    K = int(parts[1][1:]) if len(parts) > 1 else ""
    name = "D0" if D == 0 else (f"K{K}" if D == 1 else f"D{D}K{K}")
    key = (tag + name) if tag else name
    return key, D, K, (TAG_HINT[tag] if tag else "none")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=EXP / "results/analysis-phase2-dryrun/master")
    ap.add_argument("--seed", type=int, default=20261009)
    ap.add_argument("--null", action="store_true")
    a = ap.parse_args()
    assert "dryrun" in str(a.out), "simulated rows only go to a directory with 'dryrun' in its name"
    rng = random.Random(a.seed)
    index = json.loads((EXP / "tasks/phase2-drb2-index.json").read_text(encoding="utf-8"))
    g40 = sorted(k for k, v in index.items() if "g40" in v.get("sets", []))
    rows, n = [], 0
    task_fx = {}

    def tfx(model: str, task: str) -> float:
        return task_fx.setdefault((model, task), rng.gauss(0, 18.0))

    def row(batch, module, task, group, rep, model="deepseek-flash", merge=False) -> dict:
        nonlocal n
        n += 1
        key, D, K, hint = base_of(group)
        if merge:
            key = "merge"
        dq, cm, tm, want1, deeper = TRUTH[key]
        if a.null:
            dq = 0.0
        pro = model == "deepseek-v4-pro"
        q = (62.0 if pro else 57.0) + tfx(model, task.replace("_m4_", "_zh_")) + dq + rng.gauss(0, 4.0) + rng.gauss(0, 5.0)
        q = min(100.0, max(0.0, q))
        want = max(0, round(rng.gauss(want1, 1.2))) if want1 else 0
        if D == 0:
            want = 0
        opened1 = want
        rej_cap = 0
        peak = min(want, K or 0)
        if D and want > K:  # the cap binds: some calls are rejected, most are retried later
            rej_cap = (want - K) + rng.randint(0, 3)
        kids2 = max(0, round(rng.gauss(deeper * 0.7, 1.5))) if D >= 2 else 0
        kids3 = max(0, round(rng.gauss(deeper * 0.3, 1.0))) if D >= 3 else 0
        if D >= 2:
            peak = min(K, opened1 + kids2 // 2)
            if opened1 + kids2 > K:
                rej_cap += rng.randint(0, 4)
        rej_depth = rng.randint(0, 3) if (D == 1 and rng.random() < 0.3) else 0
        search = max(5.0, rng.lognormvariate(math.log(210 * cm ** 0.8), 0.35))
        model_yuan = (4.2 if not pro else 19.0) * cm * rng.lognormvariate(0, 0.30)
        search_yuan = search * 0.0158
        t_answer = 760.0 * tm * rng.lognormvariate(0, 0.30)
        status = "ok"
        u = rng.random()
        if D >= 2 and u < 0.05:
            status = "crash_at_exit"
        elif u > 0.99:
            status = "no_answer"
        complete = 0 if status == "no_answer" else 1
        r = {c: "" for c in COLS}
        r.update(id=f"sim-{n:05d}", batch=batch, task=task, family="drb2", rep=rep, block=f"{batch}|{task}|{rep}", group=group, D=D, K=K,
                 hint=hint, told=0, wait=int(group.startswith("W-")), web=1, order=n, status=status, exit=0 if status != "crash_at_exit" else 1,
                 root_end="completed" if status != "no_answer" else "aborted", oom_kill=0, kids_after_answer=0, complete=complete,
                 recognized=int(rng.random() < 0.03), q=round(q, 2) if complete else "", q_metric="SIMULATED",
                 report_chars=int(rng.gauss(9000, 2000)), t_answer_s=round(t_answer, 1), process_s=round(t_answer + 20, 1),
                 t_first_kid_s=round(rng.uniform(40, 200), 1) if opened1 else "", t_last_write_s=round(t_answer * 0.9, 1),
                 t_last_event_s=round(t_answer + 5, 1), agents=1 + opened1 + kids2 + kids3, kids_d1=opened1, kids_d2=kids2, kids_d3=kids3,
                 spawn_calls=opened1 + kids2 + kids3 + rej_cap + rej_depth, rejected_depth=rej_depth, rejected_cap=rej_cap,
                 search_requests=round(search), n_web_search=round(search * 0.6), n_web_fetch=round(search * 0.9),
                 model_yuan=round(model_yuan, 4), search_yuan=round(search_yuan, 4), total_yuan=round(model_yuan + search_yuan, 4),
                 root_turns=rng.randint(8, 40), mem_peak_gb=round(rng.uniform(0.6, 2.5), 2), parallel=32, module=module, model=model,
                 model_requested=model, peak_alive=peak, peak_alive_d1=min(opened1, K or 0), peak_alive_time_s=round(rng.uniform(60, 400), 1) if peak else "",
                 model_yuan_offpeak=round(model_yuan / 2, 4), drb2_recall=round(q - 3, 2) if complete else "", drb2_analysis=round(q + 2, 2) if complete else "",
                 drb2_presentation=round(min(100, q + 20), 2) if complete else "", judge_calls=2 if complete else "", judge_anomalous=0 if complete else "")
        return r

    def module_main(group: str, task: str, rep: int) -> str:
        if group == "D0":
            return "A" if rep == 1 else "G"
        if group.startswith("W-Pb"):
            return "B"
        if group in ("Pgm-D0", "Pgs-D0"):
            return "G"
        if group == "W-D3-K64":
            return "C"
        if group in ("W-D2-K2", "W-D2-K4", "W-D3-K2", "W-D3-K4", "W-D3-K16"):
            return "H"
        return "A"

    for task, group, rep in json.loads((EXP / "tasks/cells-phase2-main.json").read_text(encoding="utf-8")):
        rows.append(row("p2-main", module_main(group, task, rep), task, group, rep))
    for task in g40:
        rows.append(row("p2-merge", "G", task.replace("_zh_", "_m4_"), "D0", 1, merge=True))
    for task, group, rep in json.loads((EXP / "tasks/cells-phase2-d.json").read_text(encoding="utf-8")):
        rows.append(row("p2-d", "D", task, group, rep, model="deepseek-v4-pro"))
    for task, group, rep in json.loads((EXP / "tasks/cells-phase2-o.json").read_text(encoding="utf-8")):
        rows.append(row("p2-o", "O", task, group, rep))
    for task, group, rep in json.loads((EXP / "tasks/cells-phase2-f.json").read_text(encoding="utf-8")):
        fam, yuan, minutes, want = CODE[task]
        key, D, K, hint = base_of(group)
        n += 1
        opened = 0 if D == 0 else want
        rej = max(0, want - (K or 0)) + (rng.randint(0, 6) if D and want > (K or 0) else 0) if D else 0
        speed = 1.0 if D == 0 else max(0.45, 1.0 / math.sqrt(min(K, want)))
        written = minutes * 60 * speed * rng.lognormvariate(0, 0.2)
        answer = written * (1.0 if D == 0 else 2.3) * rng.lognormvariate(0, 0.15)
        cost = yuan * (1.0 if D == 0 else 3.6) * rng.lognormvariate(0, 0.2)
        r = {c: "" for c in COLS}
        r.update(id=f"sim-{n:05d}", batch="p2-f", task=task, family=fam, rep=rep, block=f"p2-f|{task}|{rep}", group=group, D=D, K=K, hint="none",
                 told=0, wait=int(group.startswith("W-")), web=0, order=n, status="ok", exit=0, root_end="completed", oom_kill=0, kids_after_answer=0,
                 complete="", recognized="", q=100.0 if rng.random() > 0.08 else round(rng.uniform(90, 99.9), 2), q_metric="SIMULATED",
                 t_answer_s=round(answer, 1), process_s=round(answer + 15, 1), t_last_write_s=round(answer * 0.95, 1), t_last_event_s=round(answer + 3, 1),
                 all_written_s=round(written, 1) if fam != "chain" else "", agents=1 + opened, kids_d1=opened if D < 2 else min(opened, 8),
                 kids_d2=0 if D < 2 else max(0, opened - 8), kids_d3=0, spawn_calls=opened + rej, rejected_depth=0, rejected_cap=rej,
                 search_requests=0, model_yuan=round(cost, 4), search_yuan=0.0, total_yuan=round(cost, 4), root_turns=rng.randint(10, 60),
                 mem_peak_gb=round(rng.uniform(2, 20), 2), parallel=12, module="F", model="deepseek-flash", model_requested="deepseek-flash",
                 peak_alive=min(opened, K or 0), peak_alive_d1=min(opened, K or 0), model_yuan_offpeak=round(cost / 2, 4))
        rows.append(r)
    a.out.mkdir(parents=True, exist_ok=True)
    with open(a.out / "runs.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    (a.out / "TRUTH.json").write_text(json.dumps({"null": a.null, "seed": a.seed, "truth": {k: list(v) for k, v in TRUTH.items()},
                                                   "note": "SIMULATED rows; nothing here is a result"}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"SIMULATED: {len(rows)} rows -> {a.out / 'runs.csv'}")


if __name__ == "__main__":
    main()
