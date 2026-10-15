#!/usr/bin/env python3
"""DeepResearch Bench II scoring of our runs' reports (plan: 补强计划 第 6 步): a port of the benchmark's own evaluator
(data/drb2/repo-src/run_evaluation.py, Apache-2.0) to the judge we use everywhere else.

What is kept from the benchmark's evaluator:
  - its prompt template, word for word (PROMPT_TEMPLATE below is copied from run_evaluation.py)
  - all rubric items of a task in the order info_recall, analysis, presentation, judged in batches of 50
  - the report text is cut at 150,000 characters
  - a batch is accepted only if every rubric item comes back with its text unchanged; up to 5 attempts
  - a rubric item scores 1 / 0 / -1; a dimension's score = share of its items with 1; total = share of all items
    with 1; blocked rate = share of all items with -1 (aggregate_scores.py)
What differs:
  - the judge is Opus 5.5 at effort "high" through the company proxy (the benchmark uses GPT-5.5 at medium), so
    absolute scores are not comparable with the paper's; differences between our groups are
  - our client always sends a system message; it is one neutral sentence
  - replies with an implausible usage record (the proxy anomaly seen on 10/3 and 10/4) are discarded and asked again
  - a request the judge model declines (stop_reason "refusal", no text) is recorded as "judge refused" and not asked
    again; such a report has no score

Reads <reports>/<run id>/workspace/report.md. Writes <out>/<run id>.r<k>.json and prints one line per run.
Usage: drb2_score.py --reports results/runs/drb2-pilot --rows results/analysis-drb2-pilot/rows-all.csv --out results/drb2-score/drb2-pilot
                     [--ids a,b] [--limit N] [--parallel 4] [--repeat 1] [--effort high] [--force]
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
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from llm_client import TRANSIENT, stream_message  # noqa: E402

MODEL = "anthropic/claude-opus-5.5"
BASE_URL = "https://proxy.high-five-ai.xyz:8443/v1"
PRICE = {"input": 4.0, "cache_write_5m": 5.0, "cache_write_1h": 8.0, "cache_read": 0.20, "output": 20.0}
USD_CNY = 6.7351
SYSTEM = "You are an evaluation assistant. Follow the instructions in the user message exactly."
TASKS = ROOT / "data/drb2/repo-src/tasks_and_rubrics.jsonl"
DIMS = ("info_recall", "analysis", "presentation")
CHUNK, MAX_CHARS, RETRIES = 50, 150000, 5

# copied verbatim from run_evaluation.py of github.com/imlrz/DeepResearch-Bench-II (main, 2026-10-05)
PROMPT_TEMPLATE = """
You will receive an article, a task, and a list of grading rubric items. Your job is to assess whether the article satisfies each rubric item, and provide a THREE-WAY score for EACH rubric item.

Scoring rule per rubric item (strict):
- Score = 1: The article clearly satisfies the rubric item AND the specific supporting sentence(s) do NOT cite any reference listed in "blocked" (match by title/urls). For numerical data, exact values must be explicitly listed and match the rubric.
- Score = 0: The article does NOT mention this rubric item at all.
- Score = -1: The article mentions this rubric item, BUT the supporting sentence(s) cite a blocked reference.

For EACH rubric item, you MUST provide:
1. "score": 1, 0, or -1
2. "reason": A brief explanation
3. "evidence": The specific supporting sentence(s) from the article (empty string if score is 0)

The input format is:
<input_format>
{{
    "task": "...",
    "rubric_items": ["rubric item 1", "rubric item 2", ...],
    "blocked": {{
        "title": "...",
        "authors": ["...", "..."],
        "urls": ["...", "..."]
    }}
}}
</input_format>

Your output MUST strictly follow this JSON format (no extra keys, and the rubric item text MUST match the input EXACTLY):
<output_format>
{{
    "results": [
        {{
            "rubric_item": "rubric item 1",
            "score": 1 or 0 or -1,
            "reason": "brief explanation",
            "evidence": "supporting sentence(s) from the article"
        }},
        {{
            "rubric_item": "rubric item 2",
            "score": 1 or 0 or -1,
            "reason": "brief explanation",
            "evidence": "supporting sentence(s) from the article"
        }},
        ...
    ]
}}
</output_format>

CRITICAL: You MUST return results for ALL rubric items in the input, and the "rubric_item" text MUST match the input text EXACTLY (character-level match).

<passage>
{paper}
</passage>
<task_and_rubric>
{rubric}
</task_and_rubric>
Now, please begin your generation
"""


def cost(u: dict) -> float:
    cc = u.get("cache_creation") or {}
    w5 = cc.get("ephemeral_5m_input_tokens", u.get("cache_creation_input_tokens") or 0) or 0
    w1 = cc.get("ephemeral_1h_input_tokens", 0) or 0
    usd = ((u.get("input_tokens") or 0) * PRICE["input"] + w5 * PRICE["cache_write_5m"] + w1 * PRICE["cache_write_1h"]
           + (u.get("cache_read_input_tokens") or 0) * PRICE["cache_read"] + (u.get("output_tokens") or 0) * PRICE["output"]) / 1e6
    return round(usd * USD_CNY, 4)


def parse(text: str):
    """The JSON object of a reply: a ```json block if there is one, else the outermost braces."""
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    cand = m.group(1) if m else text[text.find("{"): text.rfind("}") + 1]
    try:
        obj = json.loads(cand)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) and isinstance(obj.get("results"), list) else None


def ask_batch(items: list, task: str, blocked: dict, paper: str, effort: str, label: str, calls: list):
    rubric_json = json.dumps({"task": task, "rubric_items": items, "blocked": blocked}, ensure_ascii=False, indent=2)
    prompt = PROMPT_TEMPLATE.format(paper=paper, rubric=rubric_json)
    for attempt in range(1, RETRIES + 1):
        anomalous = 0
        while True:
            for net in range(1, 4):
                try:
                    t0 = time.time()
                    system = SYSTEM if not anomalous else f"{SYSTEM}\n(request tag: {uuid.uuid4().hex[:12]})"
                    msg = stream_message(base_url=BASE_URL, model=MODEL, system=system, user=prompt, effort=effort)
                    break
                except TRANSIENT as e:
                    if net == 3:
                        raise
                    print(f"{label}: {type(e).__name__}: {str(e)[:200]}; retrying", flush=True)
                    time.sleep(15 * net)
            u = dict(msg.usage)
            rec = {"attempt": attempt, "items": len(items), "seconds": round(time.time() - t0, 1), "stop_reason": msg.stop_reason, "prompt_chars": len(prompt),
                   "usage": {k: u.get(k) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}, "cost_cny": cost(u)}
            if (u.get("input_tokens") or 0) < 100 and anomalous < 4:
                anomalous += 1
                rec["anomalous"] = True
                calls.append(rec)
                print(f"{label}: anomalous usage (input {u.get('input_tokens')}, output {u.get('output_tokens')}); asked again", flush=True)
                time.sleep(20)
                continue
            rec["anomalous"] = (u.get("input_tokens") or 0) < 100
            calls.append(rec)
            break
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        if msg.stop_reason == "refusal" and not text.strip():  # the judge model declines the request; asking again does not help (trial: task 65)
            print(f"{label}: the judge refused the request", flush=True)
            return "refused"
        obj = parse(text)
        if obj is None:
            print(f"{label}: reply did not parse (attempt {attempt}); asking again", flush=True)
            continue
        got = {r.get("rubric_item"): r for r in obj["results"] if isinstance(r, dict)}
        if all(i in got for i in items) and all(got[i].get("score") in (1, 0, -1) for i in items):
            return [got[i] for i in items]
        print(f"{label}: {sum(i not in got for i in items)} of {len(items)} rubric items missing or changed (attempt {attempt}); asking again", flush=True)
    return None


def score_one(run: dict, tasks: dict, a, k: int) -> dict:
    rid = run["id"]
    target = a.out / f"{rid}.r{k}.json"
    if target.exists() and not a.force:
        return json.loads(target.read_text(encoding="utf-8"))
    idx = int(run["task"].rsplit("_", 1)[1])
    content = tasks[idx]["content"]
    rec = {"id": rid, "task": run["task"], "idx": idx, "group": run.get("group"), "rep": run.get("rep"), "judge_rep": k, "model": MODEL, "effort": a.effort,
           "template_sha": hashlib.sha256(PROMPT_TEMPLATE.encode("utf-8")).hexdigest()[:12]}
    f = a.reports / rid / "workspace" / "report.md"
    calls = []
    if not f.exists():
        rec.update(note="no report.md", total=None, chars=0, llm={"calls": 0, "cost_cny": 0, "anomalous": 0})
        target.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        return rec
    paper = f.read_text(encoding="utf-8", errors="ignore")
    rec["chars"] = len(paper)
    paper = paper[:MAX_CHARS]
    items, dim_of = [], {}
    for d in DIMS:
        for it in content["rubric"].get(d) or []:
            items.append(it)
            dim_of[it] = d
    results, failed = [], False
    for b in range(0, len(items), CHUNK):
        got = ask_batch(items[b:b + CHUNK], content["task"], content.get("blocked") or {}, paper, a.effort, f"{rid} batch {b // CHUNK + 1}", calls)
        if got == "refused":
            llm = {"calls": len(calls), "cost_cny": round(sum(c["cost_cny"] for c in calls), 3), "anomalous": sum(1 for c in calls if c.get("anomalous")), "detail": calls}
            rec.update(note="judge refused", refused=True, total=None, llm=llm)
            target.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            return rec
        if got is None:
            failed = True
            break
        results += got
    llm = {"calls": len(calls), "cost_cny": round(sum(c["cost_cny"] for c in calls), 3), "anomalous": sum(1 for c in calls if c.get("anomalous")), "detail": calls}
    if failed:
        rec.update(note="a batch failed after 5 attempts; no score recorded", total=None, llm=llm)
        print(f"{rid} r{k}: a batch failed; left for a later run", flush=True)
        return rec  # not written, so that a later run tries again
    dims = {}
    for d in DIMS:
        rs = [r for r in results if dim_of[r["rubric_item"]] == d]
        dims[d] = {"n": len(rs), "ones": sum(r["score"] == 1 for r in rs), "minus": sum(r["score"] == -1 for r in rs),
                   "score": round(100 * sum(r["score"] == 1 for r in rs) / len(rs), 3) if rs else None}
    n = len(results)
    rec.update(dims=dims, n_items=n, total=round(100 * sum(r["score"] == 1 for r in results) / n, 3),
               blocked_rate=round(100 * sum(r["score"] == -1 for r in results) / n, 3),
               items=[{"dim": dim_of[r["rubric_item"]], "rubric_item": r["rubric_item"], "score": r["score"], "reason": r.get("reason", ""), "evidence": r.get("evidence", "")}
                      for r in results], llm=llm, note="")
    target.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reports", type=Path, required=True)
    ap.add_argument("--rows", type=Path, required=True, help="CSV with id, task (drb2_zh_NNN), group, rep[, incomplete]")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ids", default="")
    ap.add_argument("--limit", type=int, default=0, help="only the first N runs in run-id hash order (for a second pass)")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--repeat", type=int, default=1, help="write .r<repeat>.json (2 = a second, independent pass)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    tasks = {}
    for line in TASKS.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            t = json.loads(line)
            tasks[int(t["idx"])] = t
    rows = [r for r in csv.DictReader(open(a.rows, encoding="utf-8")) if r["task"].startswith("drb2_") and r.get("incomplete") != "1"]
    want = set(filter(None, a.ids.split(",")))
    if want:
        rows = [r for r in rows if r["id"] in want]
    if a.limit:
        rows = sorted(rows, key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())[:a.limit]
    print(f"{len(rows)} reports, pass {a.repeat}, template {hashlib.sha256(PROMPT_TEMPLATE.encode('utf-8')).hexdigest()[:12]} -> {a.out}", flush=True)
    lock, done = threading.Lock(), []

    def work(r):
        try:
            rec = score_one(r, tasks, a, a.repeat)
        except Exception as e:  # noqa: BLE001
            print(f"{r['id']} ERROR {type(e).__name__}: {str(e)[:300]}", flush=True)
            return
        with lock:
            done.append(rec)
        d = rec.get("dims") or {}
        print(f"{rec['id']} r{a.repeat} {rec['task']} {rec.get('group')} chars={rec.get('chars')} total={rec.get('total')} "
              + " ".join(f"{k}={(d.get(k) or {}).get('score')}" for k in DIMS)
              + f" blocked={rec.get('blocked_rate')} calls={rec['llm']['calls']} cost={rec['llm']['cost_cny']} {rec.get('note', '')}", flush=True)
    with cf.ThreadPoolExecutor(a.parallel) as pool:
        list(pool.map(work, rows))
    ok = [d for d in done if d.get("total") is not None]
    print(f"{len(ok)} of {len(rows)} reports scored; judge cost {sum(d['llm']['cost_cny'] for d in done):.2f} CNY; anomalous replies {sum(d['llm']['anomalous'] for d in done)}")


if __name__ == "__main__":
    main()
