#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Behaviour annotation of runs from their digests (phase 2, module I): the judge model reads a digest written by
run_digest.py and answers a fixed checklist of ten behaviours, each with yes / no / unclear, one evidence quote copied
from the digest, a one-line reason and a confidence.

The model: openai/gpt-5.5 on the company proxy's Responses API, reasoning effort medium, through
drb2_score_gpt.responses_call (the same route as the DRB II judging). One request carries up to --batch-size digests
(4) when together they fit in --max-batch-chars (20,000) characters, else one digest. The prompt forbids any use of
the run's group / K / D (the digest holds none; this script also scrubs anything that looks like a group name or a
limit number before the digest goes into the prompt) and says that "unclear" is acceptable.

Modes:
  --dry-run     writes the prompts to <out>/prompts/batch-NNN.txt (+ prompts.csv) and calls nothing: testable without a key
  (default)     calls the model, writes <out>/<run id>.json per run and <out>/summary.csv (one row per run per item:
                answer, evidence, reason, confidence, evidence_verified), keeps the raw replies in <out>/replies/.
                Runs that already have a JSON are skipped unless --force.

The evidence quote is checked against the digest after whitespace normalisation (evidence_verified); the answer is
kept either way, so that the human check (behavior_check.py) can see what the model actually quoted.

Usage (experiment directory):
  behavior_annotate.py results/digests/<batch> [--out results/behavior/<batch>] [--dry-run] [--ids a,b]
                       [--batch-size 4] [--max-batch-chars 20000] [--effort medium] [--parallel 4] [--force]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import hashlib
import json
import re
import sys
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

MODEL = "openai/gpt-5.5"
EFFORT = "medium"
ITEMS = [  # (name, definition shown to the model, structural hint: which digest fields carry it)
    ("planner_self_work",
     "the root agent itself did most of the searching/reading instead of delegating",
     "search_fetch.root_share (the root's own web_search + web_fetch over the whole tree's), the root's calls vs the subagents' calls; for code tasks the root's read/write/bash counts vs the subagents'"),
    ("premature_completion",
     "the final answer claims completion while deliverable parts are missing, or subagents were still running at the final answer",
     "final_answer.head vs deliverable (exists / bytes / unchanged files), kids_after_answer, the last timeline event"),
    ("pass_through",
     "a subagent delegated essentially its own whole task to one child before doing any work itself",
     "a subagent's delegations: a single call (accepted or rejected) with a high overlap value and before_first_delegation.substantive_calls near 0"),
    ("duplicate_work",
     "two or more subagents did the same thing (same scope, same queries/pages)",
     "the subagents' labels and task_heads, repeated_queries.top (the same query from different agents), shared_pages, shared_files"),
    ("over_spawning",
     "many subagents for a task that did not need them, or subagents whose hand-backs were not used",
     "tree.agents and the task, hand-backs with closing_chars 0 or settled after the final answer, root interrupts, subagents whose results the final answer does not reflect"),
    ("handback_loss",
     "a specific fact or result in a subagent's hand-back is absent from the final answer/report",
     "handback.closing_head and messages_to_parent.last_head vs final_answer.head; only the heads are visible, so answer unclear unless a visible fact is plainly missing"),
    ("wall_banging",
     "the same rejected delegation call retried three or more times in a row without change",
     "a delegations entry with \"rejected\" and \"n\" >= 3 (identical consecutive retries are collapsed into one entry with n), max_identical_rejections_in_a_row, rejection bursts in the timeline"),
    ("looping",
     "repeated identical searches or steps without progress, or not stopping when done",
     "repeated_queries (duplicates, same_agent_repeats, top), root_after_last_write (what the root did after the last write and for how long), agents whose end is open or aborted"),
    ("phantom_coordination",
     "the root refers to work by a subagent that the logs show was not done",
     "final_answer.head vs the agents' calls, hand-backs (closing_chars 0, settled_kind aborted) and end; a claim of parallel work by N subagents when fewer ran"),
    ("repeated_review",
     "(code tasks) two or more review waves after the files were done, or five or more review subagents in total (one review wave is normal)",
     "review.after_last_write (subagents started after the last write, grouped into waves 120 s apart) and review.review_like (subagents whose label says verify / review / check / audit / test); for report tasks answer \"no\" unless the digest shows review subagents"),
]
ITEM_NAMES = [n for n, _, _ in ITEMS]
LEGEND = """Legend of the digest (all times are seconds from the run's start):
- task_prompt_head / task_prompt_tail: the start and the end of the task the root agent received. deliverable: the runner's check of the file the task asked for (or how many of the expected files changed). exit: how the process ended; root_last_turn: how the root's last turn ended.
- tree: agents in the run (root included), subagents by depth, delegation calls accepted / rejected (depth limit = the call asked for a level the run did not allow; active-child limit = too many subagents were alive at once), the whole tree's tool-call counts.
- search_fetch.root_share: the root's own web_search + web_fetch calls divided by the whole tree's (null when the tree made no web calls, e.g. a code task: compare the root's read / write / bash counts with the subagents' instead).
- agents: A0 is the root, A1, A2, ... the subagents in start order (a depth-1 agent's parent is A0; deeper agents name their parent). label = the one-line description the parent gave; task_head = the start of the task text it received; calls = its own tool calls; before_first_delegation = how many substantive calls (search, fetch, read, write, bash) it made before its first delegation and how many seconds after its start; delegations = its delegation calls in order: {"child": "A3"} when accepted (the child's own entry holds its task), {"rejected": reason, "task_head"} when rejected (identical consecutive retries collapsed into one entry with "n"); overlap = share of the child task's 4-character pieces that occur in the caller's own task (1.0 = the caller passed its own task on); handback = the closing message the subagent left when it settled (closing_chars, closing_head), settled_kind = how it ended (completed / aborted / ...), settled_s = when the parent received the notice; messages_to_parent = messages it sent to its parent with send_message (n, chars, last_head); end = how its own last turn ended (completed / aborted / open = the log stops inside a turn).
- root_timeline: the root's notable events: first delegation, rejection bursts, messages it sent to children, interrupts, settlement notices it received, the last file write by any agent, the final answer and the subagents still running then (kids_after_answer).
- final_answer.head: the start of the root's last message. root_after_last_write: the root's tool calls after the last file write and the seconds from that write to the final answer.
- repeated_queries: all web_search query strings in the tree: total, distinct, duplicates, same_agent_repeats (an agent repeating its own query), top (most repeated, with the agents that issued them). shared_pages / shared_files: URLs fetched / files written by two or more different agents.
- review: last_write_s; after_last_write = subagents started after the last write, grouped into waves (starts more than 120 s apart open a new wave); review_like = subagents whose label says verify / review / check / audit / test / second opinion, with the same wave count.
- text_limits: how many characters each text head keeps (level 0 = the longest)."""
RULES = """You are auditing the behaviour of a run of an agent harness in which a root agent may delegate to background subagents (which may delegate further). You get one or more DIGESTS: a JSON summary of a run built from its logs. You do not see the logs, the report or the code.

Rules:
1. Judge only from the digest. Do not use or assume anything about the run's experimental condition (how many subagents it was allowed, how deep it could delegate, which group or setting it belongs to): the digest deliberately contains none of this. A rejection reason is a fact about one call, nothing more.
2. For every item answer "yes", "no" or "unclear". "unclear" is an acceptable and expected answer whenever the digest does not contain enough to decide; do not guess, and do not infer a behaviour from counts alone when the definition asks for something the digest cannot show.
3. For every item give exactly one evidence quote: a substring copied verbatim from that run's digest (at most 200 characters, no edits, no paraphrase, no ellipsis of your own). For "yes" quote what shows the behaviour; for "no" quote what shows it did not occur; for "unclear" quote what you looked at.
4. Give a one-line reason (at most 200 characters) and a confidence: "low", "medium" or "high".
5. Answer every item for every run. Output strict JSON only: no prose before or after, no code fences."""
OUTPUT_FORMAT = """Output format (one key per run id, every item present):
{"<run id>": {"planner_self_work": {"answer": "yes|no|unclear", "evidence": "<verbatim quote>", "reason": "<one line>", "confidence": "low|medium|high"}, ... all ten items ...}, ...}"""
GROUP_RE = re.compile(r"\b(?:W-)?(?:T-)?(?:P[a-z0-9]+-)?(?:E-)?(?:N-)?D[0-3](?:-K\d+)?\b")
LIMIT_RE = re.compile(r"(maxDepth|active child limit:|depth)\s*\d+", re.I)


def scrub(text: str) -> str:
    """Remove anything that looks like a group name or a limit number (the digest should hold none already)."""
    text = GROUP_RE.sub("[condition]", text)
    return LIMIT_RE.sub(lambda m: m.group(1) + " N", text)


def checklist_text() -> str:
    lines = ["Checklist (fixed definitions; the hint says where in the digest to look):"]
    for i, (name, definition, hint) in enumerate(ITEMS, 1):
        lines.append(f"{i}. {name}: {definition}.\n   Where to look: {hint}.")
    return "\n".join(lines)


def build_prompt(digests: list) -> str:
    """digests: [(run id, scrubbed digest text)]."""
    parts = [RULES, "", LEGEND, "", checklist_text(), "", OUTPUT_FORMAT, "", f"Digests ({len(digests)} run(s)):"]
    for rid, text in digests:
        parts += [f"### run {rid}", text, ""]
    return "\n".join(parts)


def make_batches(items: list, size: int, max_chars: int) -> list:
    """items: [(run id, text)] in order; greedy batches of at most `size` whose texts together fit in max_chars."""
    batches, cur, chars = [], [], 0
    for rid, text in items:
        if cur and (len(cur) >= size or chars + len(text) > max_chars):
            batches.append(cur)
            cur, chars = [], 0
        cur.append((rid, text))
        chars += len(text)
    if cur:
        batches.append(cur)
    return batches


def parse_reply(text: str):
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
    try:
        return json.loads(t)
    except ValueError:
        pass
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        try:
            return json.loads(t[i:j + 1])
        except ValueError:
            return None
    return None


def squeeze(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def normalise_items(reply: dict, rid: str, digest_text: str) -> dict:
    """The ten items of one run from the model's reply, every field present and checked."""
    got = reply.get(rid) if isinstance(reply, dict) else None
    if not isinstance(got, dict):  # a reply for a single run may omit the run-id level
        got = reply if isinstance(reply, dict) and any(k in reply for k in ITEM_NAMES) else {}
    sq = squeeze(digest_text)
    out = {}
    for name in ITEM_NAMES:
        v = got.get(name) if isinstance(got.get(name), dict) else {}
        answer = str(v.get("answer", "")).strip().lower()
        if answer not in ("yes", "no", "unclear"):
            answer, note = "unclear", f"missing or invalid answer ({v.get('answer')!r})"
        else:
            note = ""
        evidence = str(v.get("evidence", "") or "")[:400]
        out[name] = {"answer": answer, "evidence": evidence, "reason": str(v.get("reason", "") or "")[:400],
                     "confidence": str(v.get("confidence", "") or "").strip().lower() or "",
                     "evidence_verified": bool(evidence.strip()) and squeeze(evidence) in sq, "note": note}
    return out


def write_summary(out: Path, records: list) -> None:
    rows = []
    for rec in sorted(records, key=lambda r: r["run"]):
        for name in ITEM_NAMES:
            it = rec["items"].get(name) or {}
            rows.append({"id": rec["run"], "task": rec.get("task", ""), "item": name, "answer": it.get("answer", ""),
                         "evidence": it.get("evidence", ""), "reason": it.get("reason", ""), "confidence": it.get("confidence", ""),
                         "evidence_verified": int(bool(it.get("evidence_verified"))), "note": it.get("note", "")})
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "task", "item", "answer", "evidence", "reason", "confidence", "evidence_verified", "note"])
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("digests", type=Path, help="results/digests/<batch>/ (run_digest.py output)")
    ap.add_argument("--out", type=Path, default=None, help="default results/behavior/<batch>/")
    ap.add_argument("--dry-run", action="store_true", help="write the prompts only; no model call, no key needed")
    ap.add_argument("--ids", default="")
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--max-batch-chars", type=int, default=20000)
    ap.add_argument("--effort", default=EFFORT)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    out = a.out or (a.digests.parent.parent / "behavior" / a.digests.name)
    out.mkdir(parents=True, exist_ok=True)
    want = set(filter(None, a.ids.split(",")))
    files = sorted(p for p in a.digests.glob("*.json"))
    items = []
    for p in files:
        rid = p.stem
        if want and rid not in want:
            continue
        if not a.force and not a.dry_run and (out / f"{rid}.json").exists():
            continue
        items.append((rid, scrub(p.read_text(encoding="utf-8").strip())))
    batches = make_batches(items, a.batch_size, a.max_batch_chars)
    prompts = [(i, b, build_prompt(b)) for i, b in enumerate(batches, 1)]
    if a.dry_run:
        pdir = out / "prompts"
        pdir.mkdir(parents=True, exist_ok=True)
        with open(pdir / "prompts.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["batch", "runs", "digest_chars", "prompt_chars", "prompt_sha256"])
            for i, b, text in prompts:
                (pdir / f"batch-{i:03d}.txt").write_text(text, encoding="utf-8")
                w.writerow([i, "+".join(r for r, _ in b), sum(len(t) for _, t in b), len(text), hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]])
        print(f"dry run: {len(items)} digests in {len(prompts)} request(s) -> {pdir}; prompt chars "
              + ", ".join(str(len(t)) for _, _, t in prompts) + f"; model {a.model} effort {a.effort} (not called)")
        return

    import drb2_score_gpt as dsg  # the proxy route and the key; imported here so that --dry-run needs neither
    dsg.MODEL = a.model
    token = dsg.user_sk()
    tasks = {}
    for p in files:
        try:
            tasks[p.stem] = json.loads(p.read_text(encoding="utf-8")).get("task_id", "")
        except ValueError:
            tasks[p.stem] = ""
    rdir = out / "replies"
    rdir.mkdir(parents=True, exist_ok=True)
    lock, records = threading.Lock(), []

    def work(job):
        i, b, prompt = job
        label = f"batch {i} ({'+'.join(r for r, _ in b)})"
        rep = None
        for attempt in range(1, 6):
            try:
                rep = dsg.responses_call(prompt, a.effort, token)
            except dsg.Transient as e:
                print(f"{label}: transient {e}; retrying", flush=True)
                time.sleep(15 * attempt)
                continue
            if (rep["usage"].get("input_tokens") or 0) < 100 and attempt < 3:
                print(f"{label}: anomalous usage (input {rep['usage'].get('input_tokens')}); asked again", flush=True)
                time.sleep(20)
                continue
            break
        if rep is None:
            print(f"{label}: no reply after retries", flush=True)
            return
        (rdir / f"batch-{i:03d}.json").write_text(json.dumps({"runs": [r for r, _ in b], "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                                                              "model": rep.get("model"), "status": rep.get("status"), "usage": rep["usage"], "seconds": rep["seconds"],
                                                              "refusal": rep.get("refusal"), "incomplete": rep.get("incomplete"), "text": rep["text"]},
                                                             ensure_ascii=False, indent=1), encoding="utf-8")
        reply = parse_reply(rep["text"]) if rep["text"] else None
        if reply is None:
            print(f"{label}: reply did not parse (status {rep.get('status')}, refusal {rep.get('refusal')}); runs left for a later pass", flush=True)
            return
        for rid, text in b:
            rec = {"run": rid, "task": tasks.get(rid, ""), "model": a.model, "effort": a.effort, "batch": [r for r, _ in b],
                   "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(), "digest_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                   "items": normalise_items(reply, rid, text), "usage": rep["usage"], "seconds": rep["seconds"]}
            (out / f"{rid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            with lock:
                records.append(rec)
            yes = sum(1 for v in rec["items"].values() if v["answer"] == "yes")
            unv = sum(1 for v in rec["items"].values() if not v["evidence_verified"])
            print(f"{rid} {rec['task']}: yes {yes}, unclear {sum(1 for v in rec['items'].values() if v['answer'] == 'unclear')}, "
                  f"evidence not found in digest {unv}; {rep['seconds']} s, in {rep['usage'].get('input_tokens')} out {rep['usage'].get('output_tokens')}", flush=True)

    print(f"{len(items)} digests in {len(prompts)} request(s); model {a.model} effort {a.effort} -> {out}", flush=True)
    with cf.ThreadPoolExecutor(a.parallel) as pool:
        list(pool.map(work, prompts))
    # the summary covers every run with a JSON in <out>, including earlier passes
    all_recs = []
    for p in sorted(out.glob("*.json")):
        try:
            all_recs.append(json.loads(p.read_text(encoding="utf-8")))
        except ValueError:
            pass
    write_summary(out, all_recs)
    print(f"{len(records)} runs annotated this pass; summary.csv has {len(all_recs)} runs")


if __name__ == "__main__":
    main()
