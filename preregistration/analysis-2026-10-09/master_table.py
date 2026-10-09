#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The run-level table of the whole experiment: one row per run, every batch, one definition per column.

  step 1 (dev box)  scripts/run_table.py reads the raw material of every run (result.json, stderr.log, session logs)
                    and writes results/master/raw/<batch>.csv (its version of 2026-10-08 adds peak_alive,
                    peak_alive_d1, peak_alive_time_s, wait_max_busy, wait_max_resident, model_id, model_requested and
                    the side tables <batch>.spawn_calls.csv, <batch>.agents.csv)
  step 2 (here)     this script joins those rows with the quality scores (which come from the judges and graders,
                    one file per batch) and writes results/master/runs.csv and results/master/columns.md

Rules:
  * a value that is not known stays empty; nothing is replaced by a similar quantity;
  * the design of a run (depth, K, added sentences, whether the process waits) is read from what the runner recorded
    in result.json, not from the name of the group;
  * the money is computed here from the token counts and the price table below, so a new price is one edit;
  * every run gets one exit status from one rule (see STATUS below); quality is given for every judged run, and
    the column `complete` says whether the run handed in what the task asked for.

Phase 1 (the 22 batches in BATCHES, 2,873 runs): the raw rows are joined with the per-batch tables of the analysis
scripts (ROWS, FACTS, BENCH, XL_GRADE), which hold the judgements; their rows and columns are fixed.
Phase 2 (the batches in P2_BATCHES, protocol phase2-experiment-protocol-2026-10-08.md section 十): the raw table is
the only run-level source; the judgements come from the judge files (results/drb2-score-gpt/<batch>/<id>.r<k>.json
by drb2_score_gpt.py, results/drb2-score/<batch>/ by drb2_score.py), the leak check from
results/analysis-<batch>-sources.json. A phase-2 batch is built when its raw table exists. Two quantities the raw
table does not carry are resolved as follows:
  * the sentence appended to the prompt: run_table.py writes hint_a / hint_b (the E- / N- sentences of phase 1) but
    not the runner's sentence_sha256; the builder takes the `prompt` column (the hash of the whole prompt as the
    runner recorded it) and matches it against the hash of the task's prompt text with and without each sentence of
    tasks/phase2-sentences.json; a column sentence_sha256 / sentence_tag is used first when a later run_table.py has it;
  * complete (report.md existed with at least 2,000 bytes): run_table.py does not write the runner's deliverable_ok;
    a column deliverable_ok is used when present, else the batch's manifest.jsonl (results/runs-dsec/<batch>/), else
    the judge file (note "no report.md" -> 0; at least 2,000 characters -> 1, as a character is at least one byte);
    otherwise the value stays empty and the run is listed.

Usage: master_table.py [--out results/master] [--raw-dir results/master/raw] [--judge-dir results] [--batches a,b]
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import re
import statistics as st
import sys
from pathlib import Path

sys.dont_write_bytecode = True
EXP = Path(os.environ["EXP_ROOT"]).resolve() if os.environ.get("EXP_ROOT") else Path(__file__).resolve().parent.parent  # dev box: EXP_ROOT=<experiment dir>

# ---- configuration: prices (yuan per million tokens, the public price of the model; results/price-snapshot-2026-10-08.md) and the search fee
PRICES = {"deepseek-flash": {"peak": {"miss": 2.0, "hit": 0.04, "out": 8.0}, "offpeak": {"miss": 1.0, "hit": 0.02, "out": 4.0}},
          "deepseek-v4-pro": {"peak": {"miss": 9.0, "hit": 0.30, "out": 27.0}, "offpeak": {"miss": 4.5, "hit": 0.15, "out": 13.5}}}
PRICE = PRICES["deepseek-flash"]["peak"]  # phase 1 ran deepseek-flash only
SEARCH_PROBE = "results/search-cost-probe-main-office.json"  # yuan per request of the search plugin's own model, measured on a sample

BATCHES = ["main-office", "main-code", "main-code-B", "ctl-main", "wait-office-2", "ctl-dk", "ctl-free", "ctl-free-b2", "xl-main", "xl-depth", "office-confirm", "office-highk",
           "office-floor", "office-keep-depth", "ws-screen", "ws-h1", "drb2-h1", "drb2-kd", "office-dose", "ws-k4", "drb2-k4", "office-told"]
PRE_WAIT = {"main-office", "main-code", "main-code-B", "office-confirm"}  # the runner of these batches did not record the field; none of their groups used the wait patch (checked against the group names below)
FAMILY = {"o1-singapore-trip": "office", "o2-server-cpu-report": "office", "c1-subagent-limits": "reading", "w1-memory-plugin": "reading", "p4-python": "p4",
          "pw-exercises": "timed24", "pw-exercises-120": "timed24-120", "n1-chain16": "chain", "pw-exercises-free": "free24", "toolkit-xl": "xl"}
HINT = {"eb1386bb": "parallel", "edfbd10b": "no-review", "c408b44d": "search-100-100", "9ab9b59e": "search-150-250", "cb7985c2": "search-250-500", "7ba63c92": "keep-all"}
HINT_TEXT = {"parallel": "独立的子任务尽量交给 subagent 并行做。", "no-review": "文件都写完以后，不要再另开子代理去复核、验证或补测试；需要检查就自己检查。",
             "search-100-100": "写报告之前，请至少做 100 次网页搜索，并打开至少 100 个网页核对内容。", "search-150-250": "写报告之前，请至少做 150 次网页搜索，并打开至少 250 个网页核对内容。",
             "search-250-500": "写报告之前，请至少做 250 次网页搜索，并打开至少 500 个网页核对内容。", "keep-all": "subagent 交回来的有来源的事实都写进最后的文件，重复的只写一次。"}
ROWS = ["results/analysis-v2/rows.csv", "results/analysis-ctl/rows.csv", "results/analysis-wait/rows.csv", "results/analysis-ctl-dk/rows.csv", "results/analysis-ctl-free-all/rows.csv",
        "results/analysis-xl-main/rows-all.csv", "results/analysis-xl-depth/rows-all.csv", "results/analysis-office-confirm/rows-all.csv", "results/analysis-office-highk/rows-all.csv",
        "results/analysis-office-floor/rows-all.csv", "results/analysis-office-keep-depth/rows-all.csv", "results/analysis-ws-screen/rows-all.csv", "results/analysis-ws-h1/rows-all.csv",
        "results/analysis-drb2-h1/rows-all.csv", "results/analysis-drb2-kd/rows-all.csv", "results/analysis-office-dose/rows-all.csv", "results/analysis-ws-k4/rows-all.csv",
        "results/analysis-drb2-k4/rows-all.csv", "results/analysis-office-told/rows-all.csv"]
FACTS = {"main-office": "results/analysis-facts/fact-rows.csv", "office-confirm": "results/analysis-facts-confirm/fact-rows.csv", "wait-office-2": "results/analysis-facts-wait2/fact-rows.csv",
         "office-highk": "results/analysis-facts-highk/fact-rows.csv", "office-floor": "results/analysis-facts-floor/fact-rows.csv", "office-keep-depth": "results/analysis-facts-keepdepth/fact-rows.csv",
         "office-dose": "results/analysis-facts-dose/fact-rows.csv", "office-told": "results/analysis-facts-told/fact-rows.csv"}
BENCH = {"ws-screen": ("results/analysis-ws-screen/ws-rows.csv", "f1_item"), "ws-h1": ("results/analysis-ws-h1/ws-rows.csv", "f1_item"), "ws-k4": ("results/analysis-ws-k4/ws-rows.csv", "f1_item"),
         "drb2-h1": ("results/analysis-drb2-h1/drb2-rows.csv", "total"), "drb2-kd": ("results/analysis-drb2-kd/drb2-rows.csv", "total"), "drb2-k4": ("results/analysis-drb2-k4/drb2-rows.csv", "total")}
XL_GRADE = {"xl-main": "results/grade/xl-main/index.jsonl", "xl-depth": "results/grade/xl-depth/index.jsonl"}  # the grader's own counts of hidden tests

# ---- phase 2 (protocol phase2-experiment-protocol-2026-10-08.md, sections 四 and 十; batch names from scripts/phase2-run.sh)
P2_BATCHES = ["p2-smoke", "p2-smoke-d", "p2-calib", "p2-main", "p2-d", "p2-f", "p2-merge", "p2-o", "p2-smoke-f", "p2-smoke-f64", "phase2-smoke-f"]  # built when the raw table exists
P2_PILOT = {"p2-smoke", "p2-smoke-d", "p2-calib", "p2-smoke-f", "p2-smoke-f64", "phase2-smoke-f"}  # smoke and calibration runs: module "pilot", never in a contrast
P2_MODEL = {"p2-d": "deepseek-v4-pro", "p2-smoke-d": "deepseek-v4-pro"}  # the model of a batch; the other batches ran deepseek-flash
P2_MODULE = {"p2-d": "D", "p2-f": "F", "p2-merge": "G", "p2-o": "O"}  # whole batches; the main batch by group (p2_module below)
P2_MAIN_GROUPS = {"A": ("W-D1-K1", "W-D1-K2", "W-D1-K3", "W-D1-K4", "W-D1-K8", "W-D2-K8", "W-D2-K16", "W-D3-K8"),  # plus D0 repeat 1
                  "C": ("W-D3-K64",), "H": ("W-D2-K2", "W-D2-K4", "W-D3-K2", "W-D3-K4", "W-D3-K16"), "G": ("Pgm-D0", "Pgs-D0")}  # plus D0 repeats 2-4 on the g40 tasks
P2_SENTENCES = "tasks/phase2-sentences.json"
P2_TAG_HINT = {"b3": "split-3-delegate", "b8": "split-8-delegate", "gs": "split-8-self", "gm": "search-150-250", "po": "planner-only"}  # gm is phase 1's search-150-250 sentence, byte for byte (checked below)
P2_TASK_FILES = ["tasks/phase2-drb2-tasks.jsonl", "tasks/phase2-drb2-tasks-v4pro.jsonl", "tasks/phase2-code-tasks.jsonl", "tasks/phase2-code-tasks-64g.jsonl", "tasks/phase2-merge-tasks.jsonl"]  # the prompts the runner hashed
P2_INDEX = "tasks/phase2-drb2-index.json"  # the task sets (g40: the 40 tasks of modules D and G)
JUDGE_GPT, JUDGE_OPUS = "drb2-score-gpt", "drb2-score"  # under --judge-dir: <judge-dir>/drb2-score-gpt/<batch>/<id>.r<k>.json
GROUP = re.compile(r"^(W-)?(T-)?(?:P([a-z0-9]+)-)?(E-)?(N-)?(D\d(?:-K\d+)?)$")  # the prefixes of a group name, in the runner's order (dsec_matrix_v6.group_flags)

COLS = [  # (name, meaning)
    ("id", "run id given by the runner"), ("batch", "batch: the settings that were run and judged together"), ("task", "task"),
    ("family", "kind of task: office (2 research reports), ws (WideSearch), drb2 (DeepResearch Bench II), reading (2 tasks on the DSH source), p4 (4 exercises), timed24 / timed24-120 (24 exercises with a time limit), chain (16 serial steps), free24 (24 exercises, no limit), xl (the 61-file package)"),
    ("rep", "repetition number inside the batch"), ("block", "batch|task|rep: the runs of one block ran in the same round; contrasts pair runs inside a block"),
    ("group", "group name in the batch (kept for look-ups; the design columns below are read from the run record, not from this name)"),
    ("D", "depth limit of the run (0 = no subagents)"), ("K", "limit on subagents alive at once (empty when D = 0)"),
    ("hint", "sentence appended to the task prompt: none / parallel / no-review / search-100-100 / search-150-250 / search-250-500 / keep-all; phase 2 adds split-3-delegate / split-8-delegate / split-8-self / planner-only (texts in the phase-2 section)"),
    ("told", "1 when the limit was written into the tool description (group prefix T-)"), ("wait", "1 when the process was told to stay up until the subagents settle"),
    ("web", "1 when the task may use the web"), ("started_utc", "start of the run's container"), ("order", "position of the run in the batch's random order"),
    ("status", "how the run ended, first rule that applies: timeout (the runner stopped it at the time limit) / crash_at_exit (the process crashed while leaving, issue 5063) / no_answer (the root agent's last turn did not complete) / nonzero_exit / ok"),
    ("exit", "exit code of the process"), ("root_end", "kind of the root agent's last turn end"), ("oom_kill", "1 when the kernel killed a process inside the container for memory"),
    ("kids_after_answer", "subagents still active more than 2 s after the root agent's final answer"), ("wait_cap", "1 when the waiting process gave up after its 20-minute cap"),
    ("complete", "1 when the run handed in what the task asked for and it was judged; 0 when the judge marked the deliverable incomplete; empty when the task has no such check"),
    ("recognized", "1 when the logs show the agent recognized the public benchmark (such runs are left out of the benchmark contrasts)"),
    ("q", "quality on the family's own scale, 0-100 (see q_metric)"), ("q_metric", "what q is: facts63 / f1_item / drb2_total / judge_score / tests"),
    ("facts63", "office: % of the 63 items fixed before any run that the report states correctly"), ("facts_all", "office: % of the whole list (195 items) stated correctly"),
    ("facts_wrong", "office: items the report states wrongly (firm statements)"), ("facts_right_n", "office: items stated correctly, count"),
    ("tests_failed", "xl: hidden tests that did not pass (of 3,737; the grader's count)"), ("rubric_score", "office, first batch only: total of the old scoring rubric"),
    ("report_chars", "length of the deliverable in characters"),
    ("t_answer_s", "seconds from the first log event to the end of the root agent's last turn: what the user waits for"),
    ("process_s", "seconds the dsh process ran (runner's clock)"), ("t_first_kid_s", "seconds to the first event of the first subagent"),
    ("t_last_write_s", "seconds to the last result of a write or edit call, any agent"), ("t_last_event_s", "seconds to the last event of any agent"),
    ("all_written_s", "xl and free24: seconds until every required file existed (path analysis of the batch)"),
    ("agents", "agents of the run, root included"), ("kids_d1", "subagents at depth 1"), ("kids_d2", "subagents at depth 2"), ("kids_d3", "subagents at depth 3"),
    ("review_kids", "xl: subagents started after every file was written"),
    ("spawn_calls", "calls of the delegation tools"), ("rejected_depth", "delegation calls rejected by the depth limit"), ("rejected_cap", "delegation calls rejected by K"),
    ("tok_miss", "input tokens not read from cache, every agent"), ("tok_hit", "input tokens read from cache"), ("tok_out", "output tokens"),
    ("search_requests", "requests of the search plugin's own model"), ("n_web_search", "web_search calls"), ("n_web_fetch", "web_fetch calls"), ("pages_saved", "office-dose: pages the agents saved to disk (downloads by script included)"),
    ("model_yuan", "tokens times the price table"), ("search_yuan", "search requests times the measured price per request"), ("total_yuan", "model_yuan + search_yuan"),
    ("root_turns", "turns of the root agent"), ("mem_peak_gb", "memory peak of the container"), ("parallel", "runs at once in the batch"),
    # ---- added 2026-10-08 for phase 2 (empty in phase-1 rows unless said otherwise)
    ("module", "phase 2: module of the protocol the run belongs to: A (K and depth curves, natural demand) / B (fixed demand: the split-n-delegate sentence) / C (loose limit, D3-K64) / H (K x D grid) / G (mechanism: the search or split-self sentence on one agent, D0 repeats 2-4 on the g40 tasks, the merge batch) / D (v4-pro) / F (code) / pilot (smoke and calibration batches)"),
    ("model", "model the run asked for: deepseek-flash / deepseek-v4-pro (phase 1: deepseek-flash, the model its price was computed with)"),
    ("model_requested", "model id in the root agent's requests as the session log records it (raw tables of the new run_table.py only)"),
    ("peak_alive", "most subagents holding a slot of the K limit at once, in any one pool, as DSH counts them (run_table.py's rule; raw tables of the new run_table.py only)"),
    ("peak_alive_d1", "the same, counting the root agent's direct children only"),
    ("peak_alive_time_s", "seconds from the first log event to the moment peak_alive was first reached (empty when peak_alive is 0)"),
    ("model_yuan_offpeak", "tokens times the off-peak price table of the model"),
    ("drb2_recall", "phase 2 drb2: info_recall dimension of the GPT-5.5 judge, % of its rubric items met"),
    ("drb2_analysis", "phase 2 drb2: analysis dimension, % of its rubric items met"), ("drb2_presentation", "phase 2 drb2: presentation dimension, % of its rubric items met"),
    ("drb2_blocked_rate", "phase 2 drb2: % of rubric items judged -1 (supported only by a blocked source)"),
    ("judge_calls", "phase 2 drb2: calls to the judge model in the first GPT-5.5 pass"),
    ("judge_anomalous", "phase 2 drb2: calls of that pass whose usage record was implausible (such replies were asked again)"),
    ("q_opus", "phase 2 drb2: total of the Opus second judge, when its file exists"), ("q_gpt_r2", "phase 2 drb2: total of the second, independent GPT-5.5 pass, when its file exists"),
    ("judge_note", "phase 2 drb2: why the first GPT-5.5 pass has no score: judge refused / no report.md; empty when scored"),
]


def R(path) -> list:
    with open(path if isinstance(path, Path) else EXP / path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(v):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def truthy(v) -> bool:
    return str(v).lower() in ("true", "1")


def sha8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def jsonl(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def parse_group(g: str) -> dict:
    """The prefixes of a group name (W- wait, T- told, P<tag>- sentence, E- encourage, N- no-review) and its D-K base.
    Used to check that the name says the same as the run record; never as a source."""
    m = GROUP.match(g)
    assert m, ("a group name this script cannot read", g)
    return {"wait": bool(m.group(1)), "told": bool(m.group(2)), "tag": m.group(3), "E": bool(m.group(4)), "N": bool(m.group(5)), "base": m.group(6)}


def p2_context() -> dict:
    """Phase 2: the sentence hashes (HINT is extended with them), the hash of every prompt the runner can have sent
    (task prompt, optionally + "\\n\\n" + a sentence of tasks/phase2-sentences.json, + the E- / N- sentences of phase 1,
    in the runner's order), and the g40 task set."""
    sentences = json.loads((EXP / P2_SENTENCES).read_text(encoding="utf-8"))
    assert set(sentences) == set(P2_TAG_HINT), (set(sentences) ^ set(P2_TAG_HINT))
    for tag, text in sentences.items():
        h = sha8(text)
        assert HINT.get(h, P2_TAG_HINT[tag]) == P2_TAG_HINT[tag], ("a phase-2 sentence hashes like another hint", tag, HINT[h])
        HINT[h] = P2_TAG_HINT[tag]
    extras = ["", "\n\n" + HINT_TEXT["parallel"], "\n\n" + HINT_TEXT["no-review"], "\n\n" + HINT_TEXT["parallel"] + "\n\n" + HINT_TEXT["no-review"]]
    prompts, tasks = {}, set()
    for f in P2_TASK_FILES:
        for t in jsonl(EXP / f):
            tasks.add(t["id"])
            for tag, text in [(None, "")] + [(tag, "\n\n" + s) for tag, s in sentences.items()]:
                for extra in extras:
                    h = sha8(t["prompt"] + text + extra)
                    found = prompts.setdefault(h, (t["id"], P2_TAG_HINT[tag] if tag else "none"))
                    assert found == (t["id"], P2_TAG_HINT[tag] if tag else "none"), ("two prompts with the same 8-digit hash", h, found, t["id"])
    index = read_json(EXP / P2_INDEX) or {}
    return {"sentences": sentences, "prompts": prompts, "tasks": tasks, "g40": {k for k, v in index.items() if "g40" in v.get("sets", [])}}


def p2_sentence(x: dict, ctx: dict, b: str) -> tuple:
    """(hint, source) of the sentence appended to a phase-2 run's prompt, from the run record: a sentence column of
    the raw table when it has one, else the hash of the whole prompt. hint is "" when it cannot be resolved."""
    sha = (x.get("sentence_sha256") or x.get("sentence") or "")[:8]
    if sha:
        assert sha in HINT, ("a sentence hash this script does not know", b, x["id"], sha)
        return HINT[sha], "sentence column"
    if x.get("sentence_tag"):
        return P2_TAG_HINT[x["sentence_tag"]], "sentence_tag column"
    found = ctx["prompts"].get(x["prompt"])
    if found is None:
        return "", "unresolved" + ("" if x["task"] in ctx["tasks"] else " (task not in the task files)")
    assert found[0] == x["task"], ("the prompt hash belongs to another task", b, x["id"], found[0], x["task"])
    return found[1], "prompt hash"


def p2_module(b: str, g: str, task: str, rep, ctx: dict) -> str:
    if b in P2_PILOT:
        return "pilot"
    if b in P2_MODULE:
        return P2_MODULE[b]
    assert b == "p2-main", ("a phase-2 batch with no module rule", b)
    if g == "D0":
        if int(rep) == 1:
            return "A"
        assert task in ctx["g40"], ("a D0 repeat beyond 1 on a task outside the g40 set", task, rep)
        return "G"
    if g.startswith("W-Pb3-") or g.startswith("W-Pb8-"):
        return "B"
    for mod, groups in P2_MAIN_GROUPS.items():
        if g in groups:
            return mod
    raise AssertionError(("a group of the main batch with no module", g))


def p2_complete(x: dict, man: dict | None, judge: dict | None) -> tuple:
    """(complete, source) for a phase-2 report task: 1 when workspace/report.md existed with at least 2,000 bytes."""
    if x.get("deliverable_ok", "") != "":
        return int(truthy(x["deliverable_ok"])), "deliverable_ok column"
    if man is not None and man.get("deliverable_ok") is not None:
        return int(bool(man["deliverable_ok"])), "manifest"
    if judge is not None:
        if judge.get("note") == "no report.md":
            return 0, "judge file (no report.md)"
        if (judge.get("chars") or 0) >= 2000:
            return 1, "judge file (>= 2,000 characters)"
        return "", "unresolved (report under 2,000 characters; bytes unknown)"
    return "", "unresolved (no judge file)"


def build(raw_dir: Path, judge_dir: Path, batches: list) -> tuple:
    price_search = json.loads((EXP / SEARCH_PROBE).read_text(encoding="utf-8"))["per_request_cny_peak"]
    old_batches = [b for b in batches if b in BATCHES]
    old, facts, bench, recog, xl_grade = {}, {}, {}, {}, {}
    if old_batches:
        for f in ROWS:
            for r in R(f):
                assert r["id"] not in old, ("a run id in two per-batch tables", r["id"], f)
                old[r["id"]] = dict(r, _file=f)
        facts = {b: {r["id"]: r for r in R(f)} for b, f in FACTS.items()}
        bench = {b: ({r["id"]: r for r in R(f)}, col) for b, (f, col) in BENCH.items()}
        for b in BENCH:
            src = EXP / f"results/analysis-{b}/sources.json"
            if src.exists():
                for x in json.loads(src.read_text(encoding="utf-8")):
                    recog[x["id"]] = int((x.get("n_hits") or 0) > 0)
        for b, f in XL_GRADE.items():
            for g in jsonl(EXP / f):
                xl_grade[g["id"]] = g
    ctx = p2_context() if any(b not in BATCHES for b in batches) else None
    rows, checks, p2_notes = [], collections.defaultdict(list), {}
    for b in batches:
        is_p2 = b not in BATCHES
        if is_p2:
            assert b in P2_BATCHES, ("not a batch this script knows", b)
            p2_recog = {x["id"]: int((x.get("n_hits") or 0) > 0) for x in (read_json(judge_dir / f"analysis-{b}-sources.json") or [])}
            human_leak = set(read_json(judge_dir / "human-leak-flags.json") or {})  # the human look before unblinding (leak_top20.py score)
            manifest = {m["id"]: m for m in jsonl(judge_dir / "runs-dsec" / b / "manifest.jsonl")}
            grade = {g["id"]: g for g in jsonl(judge_dir / "grade" / b / "index.jsonl")}
            # module F's two other tasks (phase2-chain*.sh, stage 6): the 24 exercises are graded by dsec_grade_px.py into
            # grade/<batch>-free/index.jsonl (grade_tests.py's rows: run, graded, main_score), the 16-step chain by
            # build_chain.score into grade/<batch>-chain.jsonl (id, main_score)
            grade_free = {g["run"]: g for g in jsonl(judge_dir / "grade" / f"{b}-free" / "index.jsonl") if g.get("run")}
            grade_chain = {g["id"]: g for g in jsonl(judge_dir / "grade" / f"{b}-chain.jsonl") if g.get("id")}
            # time until every required file existed (write_timing.py, run by phase2-post.sh): analysis-<batch>-timing-<xl|free>.json
            timing = {t_["id"]: t_ for name_ in ("xl", "free") for t_ in (read_json(judge_dir / f"analysis-{b}-timing-{name_}.json") or [])}
            note = p2_notes[b] = {"rows": 0, "module": collections.Counter(), "hint_source": collections.Counter(), "complete_source": collections.Counter(),
                                  "judged": 0, "judge_note": collections.Counter(), "unresolved": []}
        for x in R(raw_dir / f"{b}.csv"):
            o = old.get(x["id"])
            if not is_p2:
                assert o is not None, ("a run of the raw table is missing from the per-batch tables", b, x["id"])
                assert (o["task"], o["group"], str(o["rep"])) == (x["task"], x["group"], str(x["rep"])), (b, x["id"])
            m = re.search(r"D(\d)(?:-K(\d+))?\.patch\.yml$", x["patches"])
            assert m, x["patches"]
            D, K = int(m.group(1)), (int(m.group(2)) if m.group(2) else "")
            hints = [HINT[h] for h in (x["hint_a"], x["hint_b"]) if h]
            src = ""
            if is_p2:
                h, src = p2_sentence(x, ctx, b)
                note["hint_source"][src] += 1
                if h and h != "none":
                    hints.append(h)
            assert len(hints) <= 1, ("two sentences on one prompt", x["id"])
            if x["wait_for_subagents"] == "":
                assert b in PRE_WAIT, ("no wait field outside the batches that predate the patch", b)
            wait = int(truthy(x["wait_for_subagents"]))
            fam = FAMILY.get(x["task"]) or ("ws" if x["task"].startswith("ws_") else "drb2" if x["task"].startswith("drb2_") else None)
            assert fam, x["task"]
            # the name of the group must say the same as the run record (a check of the names, not a source)
            g = x["group"]
            name = parse_group(g)
            assert name["wait"] == bool(wait), (b, g, wait)
            if src.startswith("unresolved"):
                note["unresolved"].append(x["id"])
            else:
                assert (name["E"] or name["N"] or name["tag"] is not None) == bool(hints), ("the group name and the run record disagree on whether a sentence was appended", b, g, hints)
                if name["tag"] is not None:
                    assert hints == [P2_TAG_HINT[name["tag"]]], ("the sentence in the record is not the one the group name says", b, g, hints)
            assert name["base"] == f"D{D}" + (f"-K{K}" if D else ""), (g, D, K)
            if truthy(x["timeout"]):
                status = "timeout"
            elif truthy(x["crash5063"]):
                status = "crash_at_exit"
            elif x["root_end"] != "completed":
                status = "no_answer"
            elif str(x["exit"]) not in ("0", "0.0"):
                status = "nonzero_exit"
            else:
                status = "ok"
            model_name = x.get("model_requested", "") or (P2_MODEL.get(b, "deepseek-flash") if is_p2 else "deepseek-flash")
            assert model_name == (P2_MODEL.get(b, "deepseek-flash") if is_p2 else "deepseek-flash"), ("the model the run asked for is not the model of its batch", b, x["id"], model_name)
            price = PRICES[model_name]
            tm, th, to = (num(x[k]) for k in ("tok_miss", "tok_hit", "tok_out"))
            model = (tm * price["peak"]["miss"] + th * price["peak"]["hit"] + to * price["peak"]["out"]) / 1e6
            offpeak = (tm * price["offpeak"]["miss"] + th * price["offpeak"]["hit"] + to * price["offpeak"]["out"]) / 1e6
            sr = num(x["search_requests"])
            row = {"id": x["id"], "batch": b, "task": x["task"], "family": fam, "rep": x["rep"], "block": f"{b}|{x['task']}|{x['rep']}", "group": g, "D": D, "K": K,
                   "hint": hints[0] if hints else ("" if src.startswith("unresolved") else "none"), "told": int(name["told"]), "wait": wait, "web": int(truthy(x["web"])),
                   "started_utc": x["started_utc"], "order": x["order"],
                   "status": status, "exit": x["exit"], "root_end": x["root_end"], "oom_kill": int(truthy(x["oom_kill"]) or ((num(o.get("oom_kill")) or 0) > 0 if o else False)),
                   "kids_after_answer": x["kids_after_answer"], "wait_cap": x["wait_cap"],
                   "t_answer_s": x["t_answer_s"], "process_s": x["process_s"], "t_first_kid_s": x["t_first_kid_s"], "t_last_write_s": x["t_last_write_s"], "t_last_event_s": x["t_last_event_s"],
                   "all_written_s": o.get("all_written_s", "") if o else "", "agents": x["agents"], "kids_d1": x["kids_d1"], "kids_d2": x["kids_d2"], "kids_d3": x["kids_d3"],
                   "review_kids": o.get("review_kids", "") if o else "",
                   "spawn_calls": x["spawn_calls"], "rejected_depth": x["rejected_depth"], "rejected_cap": x["rejected_cap"],
                   "tok_miss": x["tok_miss"], "tok_hit": x["tok_hit"], "tok_out": x["tok_out"], "search_requests": x["search_requests"], "n_web_search": x["n_web_search"], "n_web_fetch": x["n_web_fetch"],
                   "pages_saved": o.get("pages_saved", "") if o else "", "model_yuan": round(model, 4), "search_yuan": round(sr * price_search, 4) if fam in ("office", "ws", "drb2") else 0.0,
                   "root_turns": x["root_turns"], "mem_peak_gb": x["mem_peak_gb"], "parallel": x["parallel"], "report_chars": o.get("deliv_chars", "") if o else "",
                   "complete": "", "recognized": recog.get(x["id"], ""), "q": "", "q_metric": "", "facts63": "", "facts_all": "", "facts_wrong": "", "facts_right_n": "", "tests_failed": "", "rubric_score": "",
                   "module": "", "model": model_name, "model_requested": x.get("model_requested", ""),
                   "peak_alive": x.get("peak_alive", ""), "peak_alive_d1": x.get("peak_alive_d1", ""), "peak_alive_time_s": x.get("peak_alive_time_s", ""),
                   "model_yuan_offpeak": round(offpeak, 4), "drb2_recall": "", "drb2_analysis": "", "drb2_presentation": "", "drb2_blocked_rate": "",
                   "judge_calls": "", "judge_anomalous": "", "q_opus": "", "q_gpt_r2": "", "judge_note": ""}
            row["total_yuan"] = round(row["model_yuan"] + row["search_yuan"], 4)
            if is_p2:
                row["module"] = p2_module(b, g, x["task"], x["rep"], ctx)
                row["recognized"] = 1 if x["id"] in human_leak else p2_recog.get(x["id"], "")
                note.setdefault("human_leak", 0)
                note["human_leak"] += int(x["id"] in human_leak)
                note["rows"] += 1
                note["module"][row["module"]] += 1
                if fam == "drb2":
                    g1 = read_json(judge_dir / JUDGE_GPT / b / f"{x['id']}.r1.json")
                    g2 = read_json(judge_dir / JUDGE_GPT / b / f"{x['id']}.r2.json")
                    o1 = read_json(judge_dir / JUDGE_OPUS / b / f"{x['id']}.r1.json")
                    for rec in (g1, g2, o1):
                        assert rec is None or (rec.get("id"), rec.get("task")) == (x["id"], x["task"]), ("a judge file of another run", b, x["id"], rec and (rec.get("id"), rec.get("task")))
                    if g1 is not None:
                        llm = g1.get("llm") or {}
                        row.update(judge_calls=llm.get("calls", ""), judge_anomalous=llm.get("anomalous", ""))
                        if g1.get("total") is not None:
                            d = g1["dims"]
                            row.update(q=g1["total"], q_metric="drb2_total_gpt55", drb2_blocked_rate=g1.get("blocked_rate", ""),
                                       drb2_recall=d["info_recall"].get("score") if d["info_recall"].get("score") is not None else "",
                                       drb2_analysis=d["analysis"].get("score") if d["analysis"].get("score") is not None else "",
                                       drb2_presentation=d["presentation"].get("score") if d["presentation"].get("score") is not None else "")
                            note["judged"] += 1
                        else:
                            row["judge_note"] = g1.get("note") or "no score"
                            note["judge_note"][row["judge_note"]] += 1
                        if g1.get("note") != "no report.md" and g1.get("chars") is not None:
                            row["report_chars"] = g1["chars"]
                    if g2 is not None and g2.get("total") is not None:
                        row["q_gpt_r2"] = g2["total"]
                    if o1 is not None and o1.get("total") is not None:
                        row["q_opus"] = o1["total"]
                    row["complete"], csrc = p2_complete(x, manifest.get(x["id"]), g1)
                    note["complete_source"][csrc] += 1
                elif fam == "xl" and x["id"] in grade:
                    g_ = grade[x["id"]]
                    row.update(q=g_["score"], q_metric="tests", tests_failed=g_["total"] - g_["passed"])
                    note["judged"] += 1
                elif fam == "free24" and grade_free.get(x["id"], {}).get("graded"):
                    row.update(q=grade_free[x["id"]]["main_score"], q_metric="tests")
                    note["judged"] += 1
                elif fam == "chain" and grade_chain.get(x["id"], {}).get("main_score") is not None:
                    row.update(q=grade_chain[x["id"]]["main_score"], q_metric="tests")
                    note["judged"] += 1
                if fam in ("xl", "free24") and timing.get(x["id"], {}).get("all_written_s") is not None:
                    row["all_written_s"] = timing[x["id"]]["all_written_s"]
                rows.append(row)
                continue
            if fam == "office":
                row["complete"] = "" if "incomplete" not in o else int(str(o["incomplete"]) != "1")
                row["rubric_score"] = o.get("score", "") if b in ("main-office", "wait-office-2", "office-highk") else ""
                f = facts.get(b, {}).get(x["id"])
                if f:
                    row.update(facts63=f["right_legacy_pct"], facts_all=f["right_pct"], facts_wrong=f["wrong_firm_n"], facts_right_n=f["right_n"], q=f["right_legacy_pct"], q_metric="facts63")
            elif fam in ("ws", "drb2"):
                tab, col = bench[b]
                f = tab.get(x["id"])
                row["complete"] = "" if "incomplete" not in o else int(str(o["incomplete"]) != "1")
                if f and num(f.get(col)) is not None:
                    row.update(q=f[col], q_metric="f1_item" if fam == "ws" else "drb2_total")
            else:
                s = num(o.get("score"))
                if s is not None:
                    row.update(q=o["score"], q_metric="judge_score" if fam == "reading" else "tests")
                    if fam == "xl":
                        g_ = xl_grade[x["id"]]
                        row["tests_failed"] = g_["total"] - g_["passed"]
            rows.append(row)
            # the same quantity in the old per-batch tables, where they have it
            for name_, new, oldv in (("answer time", num(x["t_answer_s"]), num(o.get("answer_s"))), ("model yuan", model, num(o.get("model_cost_peak"))),
                                     ("search requests", sr, num(o.get("search_aux"))), ("total yuan", row["total_yuan"], num(o.get("total_cost_peak"))),
                                     ("subagents", sum(num(x[k]) or 0 for k in ("kids_d1", "kids_d2", "kids_d3")), num(o.get("children"))),
                                     ("rejected by K", num(x["rejected_cap"]), num(o.get("capacity_rejects"))), ("rejected by depth", num(x["rejected_depth"]), num(o.get("depth_rejects"))),
                                     ("process seconds", num(x["process_s"]), num(o.get("seconds")))):
                if new is not None and oldv is not None and oldv != 0 or (new is not None and oldv == 0):
                    checks[name_].append((new - oldv, b, x["id"]))
    return rows, checks, price_search, p2_notes


def p2_doc(p2_notes: dict) -> list:
    """The section of columns.md on phase 2: batches, modules, sentences, prices, the complete rule and the judge join."""
    sentences = json.loads((EXP / P2_SENTENCES).read_text(encoding="utf-8"))
    lines = ["", "## 第二阶段（p2-*）的批、新列和规则", "",
             "第二阶段的批由 2026-10-08 版 scripts/run_table.py 抽取（多出 peak_alive、peak_alive_d1、peak_alive_time_s、wait_max_busy、wait_max_resident、model_id、model_requested 七列，"
             "另有 <batch>.spawn_calls.csv 和 <batch>.agents.csv 两张边表）。本脚本在 results/master/raw/<batch>.csv 存在时接入下面的批；第二阶段没有各批自己的分析表，"
             "运行记录只有原始表一个来源，判分从判分文件读（方案第十节）。新列从 module 起列在上面的列表末尾；第一阶段的行里这些列留空，只有 model（全是 deepseek-flash，"
             "即算它们价格用的模型）和 model_yuan_offpeak（空闲价）有值。", "",
             "| 批 | module | model | 内容 |", "|---|---|---|---|",
             "| p2-smoke | pilot | deepseek-flash | 冒烟：smoke 题 × 各 flash 组各 1 次，不计分 |",
             "| p2-smoke-d | pilot | deepseek-v4-pro | 冒烟：smoke 题 × 五个 v4-pro 组 |",
             "| p2-calib | pilot | deepseek-flash | 四句附加句各 4 题 × 2 次的校准，不计分 |",
             "| p2-main | A / B / C / H / G，按组 | deepseek-flash | 主批：方案第四节的 A、B、C、G、H 同一批 |",
             "| p2-d | D | deepseek-v4-pro | 换模型 |",
             "| p2-f | F | deepseek-flash | 代码题，不联网 |",
             "| p2-merge | G | deepseek-flash | 四份单 agent 报告合并（任务 drb2_m4_<idx>） |",
             "| p2-o | O | deepseek-flash | 编排对照（探索性，10/8 加入）：g40 题上主 agent 加角色句（planner-only）对同批默认 K=8，各 1 次 |",
             "| p2-smoke-f64 | pilot | deepseek-flash | 大型编码题在 64 GB 容器里跑 1 次，只用来定模块 F 的内存 |",
             "| p2-smoke-f（phase2-run.sh 里的名字；phase2-smoke-f 也认） | pilot | deepseek-flash | 代码题冒烟 |", "",
             "主批里组到 module：D0 第 1 次和 " + "、".join(P2_MAIN_GROUPS["A"]) + " → A；W-Pb3-*、W-Pb8-* → B；"
             + "、".join(P2_MAIN_GROUPS["C"]) + " → C；" + "、".join(P2_MAIN_GROUPS["H"]) + " → H；"
             + "、".join(P2_MAIN_GROUPS["G"]) + " 和 g40 题（tasks/phase2-drb2-index.json 里 sets 含 g40 的 40 道）上 D0 的第 2–4 次 → G。", "",
             "第二阶段的题面附加句（tasks/phase2-sentences.json；hint 列新增的值）：", "", "| 标签 | hint | sha256 前 8 位 | 原文 |", "|---|---|---|---|"]
    for tag, text in sentences.items():
        lines.append(f"| {tag} | {P2_TAG_HINT[tag]} | {sha8(text)} | {text}" + ("（与第一阶段 search-150-250 逐字相同，哈希核对过）" if tag == "gm" else "") + " |")
    lines += ["",
              "句子怎么定：run_table.py 只输出 hint_a / hint_b（第一阶段 E- / N- 两句的哈希），不输出运行记录里的 sentence_sha256。本脚本拿原始表的 prompt 列"
              "（运行记录里整段题面的 sha256 前 8 位）和「题面文件里的题面 + 空行 + 句子」算出的哈希对照来定（题面文件：" + "、".join(P2_TASK_FILES) + "）；"
              "原始表若有 sentence_sha256 / sentence_tag 列则先用它。对不上的行 hint 留空并在运行时打印。组名里的 P<标签>- 只用来核对，不作来源。", "",
              "价格（元 / 百万 token，results/price-snapshot-2026-10-08.md）：", "", "| 模型 | 读缓存的输入 高峰 / 空闲 | 没进缓存的输入 高峰 / 空闲 | 输出 高峰 / 空闲 |", "|---|---|---|---|"]
    for mdl, p in PRICES.items():
        lines.append(f"| {mdl} | {p['peak']['hit']} / {p['offpeak']['hit']} | {p['peak']['miss']} / {p['offpeak']['miss']} | {p['peak']['out']} / {p['offpeak']['out']} |")
    lines += ["",
              "model_yuan 按高峰价、model_yuan_offpeak 按空闲价，模型取 model 列（原始表的 model_requested；没有这一列时按批：p2-d、p2-smoke-d 为 deepseek-v4-pro，其余 deepseek-flash；"
              "两者不一致时脚本停下）；search_yuan 仍是搜索请求数 × 抽样实测单价；total_yuan 仍是高峰模型费加搜索费。", "",
              "complete（报告题，family = drb2）：workspace/report.md 存在且不少于 2,000 字节记 1，否则 0。run_table.py 不输出 runner 的 deliverable_ok，依次取：原始表的 deliverable_ok 列；"
              "results/runs-dsec/<batch>/manifest.jsonl 的 deliverable_ok；判分文件（note 为 no report.md → 0；chars ≥ 2,000 → 1，一个字符至少一个字节）；都没有则留空并打印。", "",
              "判分（family = drb2）：q = results/drb2-score-gpt/<batch>/<id>.r1.json 的 total（q_metric = drb2_total_gpt55），drb2_recall / drb2_analysis / drb2_presentation 为三个维度的 score，"
              "drb2_blocked_rate 为 blocked_rate，judge_calls / judge_anomalous 为 llm.calls / llm.anomalous，report_chars 为 chars。没有这个文件时 q 留空，不用别的替；"
              "note 为 judge refused 或 no report.md 时 q 留空、judge_note 记 note。q_opus = results/drb2-score/<batch>/<id>.r1.json 的 total（Opus 复判），"
              "q_gpt_r2 = results/drb2-score-gpt/<batch>/<id>.r2.json 的 total（GPT-5.5 第二遍）。recognized 取 results/analysis-<batch>-sources.json 的 n_hits > 0。"
              "代码题（p2-f，toolkit-xl）：results/grade/<batch>/index.jsonl 存在时 q = score（q_metric = tests）、tests_failed = total − passed；其余代码题的分还没有接。"]
    if p2_notes:
        lines += ["", "### 第二阶段各批", "", "| 批 | 运行 | module | 判了分 | 句子定不下来 | complete 的来源 |", "|---|---|---|---|---|---|"]
        for b, n in p2_notes.items():
            lines.append(f"| {b} | {n['rows']} | " + "、".join(f"{k} {v}" for k, v in sorted(n["module"].items())) + f" | {n['judged']} | {len(n['unresolved'])} | "
                         + "；".join(f"{k} {v}" for k, v in n["complete_source"].items()) + " |")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=EXP / "results" / "master")
    ap.add_argument("--raw-dir", type=Path, default=EXP / "results" / "master" / "raw", help="where <batch>.csv of run_table.py are")
    ap.add_argument("--judge-dir", type=Path, default=EXP / "results",
                    help="where the judgements of phase 2 are looked up: <dir>/drb2-score-gpt/<batch>/, <dir>/drb2-score/<batch>/, <dir>/analysis-<batch>-sources.json, "
                         "<dir>/grade/<batch>/index.jsonl, <dir>/runs-dsec/<batch>/manifest.jsonl")
    ap.add_argument("--batches", default="", help="comma-separated: build only these (default: the 22 phase-1 batches and every phase-2 batch whose raw table exists)")
    a = ap.parse_args()
    batches = [b for b in a.batches.split(",") if b] or BATCHES + [b for b in P2_BATCHES if (a.raw_dir / f"{b}.csv").exists()]
    rows, checks, price_search, p2_notes = build(a.raw_dir, a.judge_dir, batches)
    names = [c for c, _ in COLS]
    assert set(names) == set(rows[0]), (set(names) ^ set(rows[0]))
    n_old = sum(1 for r in rows if r["batch"] in BATCHES)
    assert n_old == 2873 or set(BATCHES) - set(batches), ("the phase-1 batches must give 2,873 runs", n_old)
    assert len({r["id"] for r in rows}) == len(rows), "a run id twice"
    a.out.mkdir(parents=True, exist_ok=True)
    with open(a.out / "runs.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=names)
        w.writeheader()
        w.writerows(rows)
    by = collections.Counter((r["family"], r["status"]) for r in rows)
    fam = collections.Counter(r["family"] for r in rows)
    lines = ["# 运行级总表 results/master/runs.csv", "",
             f"一行一次运行，共 {len(rows):,} 行，{len(batches)} 批。由 scripts/run_table.py（开发机，读原始日志）和 scripts/master_table.py（本机，接上判分）两步生成。",
             "", "规则：不知道的值留空，不用别的量顶替；运行的设置（深度、K、题面加的句子、进程等不等）取自运行记录，不靠组名；钱由 token 数乘价格表算出。", "",
             f"价格表（元 / 百万 token，公开高峰价）：没进缓存的输入 {PRICE['miss']}，读缓存的输入 {PRICE['hit']}，输出 {PRICE['out']}；搜索每个请求 {price_search:.4f} 元（抽样实测）。", "",
             "## 列", "", "| 列 | 含义 |", "|---|---|"] + [f"| {c} | {d} |" for c, d in COLS] + ["",
             "## 题面加的句子", "", "| hint | 原文 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in HINT_TEXT.items()] + ["",
             "## 各类任务的运行数和退出状态", "", "| 任务类 | 运行 | ok | crash_at_exit | timeout | no_answer | nonzero_exit |", "|---|---|---|---|---|---|---|"]
    for f_, n in sorted(fam.items()):
        lines.append(f"| {f_} | {n} | " + " | ".join(str(by[(f_, s)]) for s in ("ok", "crash_at_exit", "timeout", "no_answer", "nonzero_exit")) + " |")
    lines += ["", "## 和各批原来的表对照（同一个量，新表减旧表）", "", "| 量 | 对得上的运行 | 差的中位数 | 差的最大绝对值 | 差超过 1% 或 1 个单位的运行 |", "|---|---|---|---|---|"]
    for k, v in checks.items():
        d = [x[0] for x in v]
        big = sum(1 for x in d if abs(x) > 1)
        lines.append(f"| {k} | {len(d)} | {st.median(d):+.3f} | {max(abs(x) for x in d):.3f} | {big} |")
        print(f"check {k:18s}: n={len(d):4d} median diff {st.median(d):+.3f} max abs {max(abs(x) for x in d):9.3f} runs off by more than 1: {big}")
    lines += p2_doc(p2_notes)
    (a.out / "columns.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {a.out / 'runs.csv'}: {len(rows)} rows, {len(names)} columns")
    for f_, n in sorted(fam.items()):
        print(f"  {f_:12s} {n:4d} " + " ".join(f"{s}={by[(f_, s)]}" for s in ("ok", "crash_at_exit", "timeout", "no_answer", "nonzero_exit") if by[(f_, s)]))
    judged = collections.Counter((r["family"], bool(r["q"] != "")) for r in rows)
    print("  judged:", {f_: f"{judged[(f_, True)]}/{fam[f_]}" for f_ in sorted(fam)})
    for b, n in p2_notes.items():
        print(f"phase 2 {b}: {n['rows']} rows; module " + " ".join(f"{k}={v}" for k, v in sorted(n["module"].items()))
              + "; sentence from " + ", ".join(f"{k} {v}" for k, v in n["hint_source"].items()) + f"; judged {n['judged']}"
              + ("; no score: " + ", ".join(f"{k} {v}" for k, v in n["judge_note"].items()) if n["judge_note"] else "")
              + "; complete from " + (", ".join(f"{k} {v}" for k, v in n["complete_source"].items()) or "-")
              + f"; flagged by the human leak look {n.get('human_leak', 0)}")
        if n["unresolved"]:
            print(f"  WARNING {b}: the sentence of {len(n['unresolved'])} runs could not be resolved (hint left empty): " + ", ".join(n["unresolved"][:10]) + (" ..." if len(n["unresolved"]) > 10 else ""))


if __name__ == "__main__":
    main()
