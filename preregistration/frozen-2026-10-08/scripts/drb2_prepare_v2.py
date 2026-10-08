#!/usr/bin/env python3
"""Task, index and cell files for the phase-2 DeepResearch Bench II runs (phase2-experiment-protocol-2026-10-08.md v5.1).

Tasks: every Chinese task of the benchmark (66) minus the ones the judge refuses (--exclude, from
results/drb2-score-gpt/refusal-probe.json). Each prompt is built exactly as in drb2_prepare.py (benchmark prompt,
the output-file paragraph, the blocked-source paragraph), so the 30 tasks of phase 1 keep the same prompt bytes
(prompt_sha256 in the index). Blocked hosts: the WideSearch list plus the benchmark's site, as in phase 1.

A fixed random order of the tasks (seed 20261008) gives the subsets: d40 (module D, v4-pro) = the first 40, g40
(module G) = the same 40, calib = the last 4 of the order (sentence calibration runs, never scored), smoke = the
first task of the order.

Cells (group names: W- = the process waits for the subagents; P<tag>- = the sentence tasks/phase2-sentences.json[tag]):
  main (flash, one batch, block = task x repeat):
    A  D0 x1, W-D1-K1 x1, W-D1-K2 x1, W-D1-K3 x1, W-D1-K4 x1, W-D1-K8 x2, W-D2-K8 x2, W-D2-K16 x1, W-D3-K8 x1
    B  W-Pb3-D1-K8 x1, W-Pb8-D1-K2 x1, W-Pb8-D1-K6 x1, W-Pb8-D1-K4 x2, W-Pb8-D1-K8 x2
    C  W-D3-K64 x1
    H  W-D2-K2, W-D2-K4, W-D3-K2, W-D3-K4, W-D3-K16 x1
    G  (g40 only) Pgm-D0 x1, Pgs-D0 x1, D0 repeats 2-4 (the four single-agent reports of the merge control are
       D0 rep 1-4; the merge runs are built afterwards by build_merge_tasks_drb2.py)
  d (v4-pro, its own batch and task file with extra_patches v4pro.patch.yml, 120-minute limit):
    d40 x {D0, W-D1-K2, W-D1-K8, W-D2-K8} x1; the first 20 of d40 x W-D3-K64 x1
  calib: calib x {W-Pb3-D1-K8, W-Pb8-D1-K8, Pgs-D0, Pgm-D0} x2
  smoke: smoke task x every flash group without a sentence x1; smoke-d: smoke task x the five v4-pro groups x1

Usage: drb2_prepare_v2.py [--exclude 63,65]
Writes tasks/phase2-drb2-tasks.jsonl, tasks/phase2-drb2-tasks-v4pro.jsonl, tasks/phase2-drb2-index.json and
tasks/cells-phase2-{main,d,calib,smoke,smoke-d}.json; prints the counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

EXP = Path(__file__).resolve().parent.parent
SRC = EXP / "data/drb2/repo-src/tasks_and_rubrics.jsonl"
SEED = 20261008
EXTRA_HOSTS = ["agentresearchlab.org", "www.agentresearchlab.org"]
OUT_PARA = "请把报告写到 report.md。"
BLOCK_PARA = "下面这篇文献以及它的任何转载页、摘要页都不要打开，也不要引用：《{title}》（{authors}）。网址：{urls}"
TIMEOUT_FLASH, TIMEOUT_V4PRO = 5400, 7200

A = [("D0", 1), ("W-D1-K1", 1), ("W-D1-K2", 1), ("W-D1-K3", 1), ("W-D1-K4", 1), ("W-D1-K8", 2), ("W-D2-K8", 2), ("W-D2-K16", 1), ("W-D3-K8", 1)]
B = [("W-Pb3-D1-K8", 1), ("W-Pb8-D1-K2", 1), ("W-Pb8-D1-K6", 1), ("W-Pb8-D1-K4", 2), ("W-Pb8-D1-K8", 2)]
C = [("W-D3-K64", 1)]
H = [("W-D2-K2", 1), ("W-D2-K4", 1), ("W-D3-K2", 1), ("W-D3-K4", 1), ("W-D3-K16", 1)]
G = [("Pgm-D0", 1), ("Pgs-D0", 1)]
G_EXTRA_D0_REPS = (2, 3, 4)
D_CELLS = ["D0", "W-D1-K2", "W-D1-K8", "W-D2-K8"]
D_LOOSE = "W-D3-K64"
CALIB_GROUPS = ["W-Pb3-D1-K8", "W-Pb8-D1-K8", "Pgs-D0", "Pgm-D0"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exclude", default="", help="comma-separated idx the judge refuses")
    a = ap.parse_args()
    exclude = {int(x) for x in a.exclude.split(",") if x}
    tasks = [json.loads(l) for l in SRC.read_text(encoding="utf-8").split("\n") if l.strip()]
    zh = sorted((t for t in tasks if t["language"] == "zh" and t["idx"] not in exclude), key=lambda t: t["idx"])
    order = zh[:]
    random.Random(SEED).shuffle(order)
    d40 = order[:40]
    calib = order[-4:]
    smoke = order[0]
    base_hosts = json.loads((EXP / "tasks/ws-tasks-v2.jsonl").read_text(encoding="utf-8").split("\n")[0])["block_hosts"]
    hosts = base_hosts + [h for h in EXTRA_HOSTS if h not in base_hosts]
    tid = lambda t: f"drb2_zh_{t['idx']:03d}"  # noqa: E731
    out, out_v4, index = [], [], {}
    for t in zh:
        b = t["content"].get("blocked") or {}
        para = BLOCK_PARA.format(title=b.get("title", ""), authors="、".join(b.get("authors") or []), urls="；".join(b.get("urls") or []))
        prompt = t["prompt"] + "\n\n" + OUT_PARA + "\n\n" + para
        row = {"id": tid(t), "type": "research-report", "prompt": prompt, "deliverable": "report.md", "min_bytes": 2000, "web": True,
               "timeout_s": TIMEOUT_FLASH, "block_hosts": hosts}
        out.append(row)
        if t in d40:
            out_v4.append({**row, "timeout_s": TIMEOUT_V4PRO, "extra_patches": ["v4pro.patch.yml"]})
        r = t["content"]["rubric"]
        index[tid(t)] = {"idx": t["idx"], "theme": t["theme"], "description": t["description"], "license": t.get("license"),
                         "order": order.index(t), "sets": [s for s, members in (("d40", d40), ("g40", d40), ("calib", calib), ("smoke", [smoke])) if t in members],
                         "phase1": False, "rubric_items": {k: len(v) for k, v in r.items()}, "blocked": b,
                         "prompt_sha256": hashlib.sha256(t["prompt"].encode("utf-8")).hexdigest(),
                         "full_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest()}
    old = json.loads((EXP / "tasks/drb2-index.json").read_text(encoding="utf-8"))
    for k, v in index.items():
        if k in old:
            v["phase1"] = True
            if old[k]["prompt_sha256"] != v["prompt_sha256"]:
                raise SystemExit(f"{k}: prompt differs from phase 1")
    (EXP / "tasks/phase2-drb2-tasks.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in out), encoding="utf-8")
    (EXP / "tasks/phase2-drb2-tasks-v4pro.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in out_v4), encoding="utf-8")
    (EXP / "tasks/phase2-drb2-index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")

    main_cells = []
    for t in zh:
        for g, reps in A + B + C + H:
            main_cells += [[tid(t), g, r] for r in range(1, reps + 1)]
        if t in d40:
            main_cells += [[tid(t), g, 1] for g, _ in G] + [[tid(t), "D0", r] for r in G_EXTRA_D0_REPS]
    d_cells = [[tid(t), g, 1] for t in d40 for g in D_CELLS] + [[tid(t), D_LOOSE, 1] for t in d40[:20]]
    calib_cells = [[tid(t), g, r] for t in calib for g in CALIB_GROUPS for r in (1, 2)]
    flash_groups = sorted({g for g, _ in A + B + C + H + G if "P" not in g.split("-")[0] and not g.startswith("W-P")})
    smoke_cells = [[tid(smoke), g, 1] for g in flash_groups]
    smoke_d_cells = [[tid(smoke), g, 1] for g in D_CELLS + [D_LOOSE]]
    for name, cells in (("main", main_cells), ("d", d_cells), ("calib", calib_cells), ("smoke", smoke_cells), ("smoke-d", smoke_d_cells)):
        (EXP / f"tasks/cells-phase2-{name}.json").write_text(json.dumps(cells, ensure_ascii=False), encoding="utf-8")
        print(f"cells-phase2-{name}.json: {len(cells)} runs, {len({(c[0], c[1]) for c in cells})} cells, {len({c[0] for c in cells})} tasks")
    print(f"tasks: {len(zh)} (excluded {sorted(exclude)}); phase-1 tasks among them: {sum(v['phase1'] for v in index.values())}")
    print(f"d40/g40 idx: {sorted(t['idx'] for t in d40)}")
    print(f"calib idx: {[t['idx'] for t in calib]}; smoke idx: {smoke['idx']}")
    n_items = [sum(v["rubric_items"].values()) for v in index.values()]
    print(f"rubric items per task: mean {sum(n_items) / len(n_items):.1f}, min {min(n_items)}, max {max(n_items)}")
    print(f"flash groups in smoke: {flash_groups}")
    for name in ("phase2-drb2-tasks.jsonl", "phase2-drb2-tasks-v4pro.jsonl", "phase2-sentences.json"):
        print(f"{name} sha256 {hashlib.sha256((EXP / 'tasks' / name).read_bytes()).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
