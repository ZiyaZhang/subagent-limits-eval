#!/usr/bin/env python3
"""DeepResearch Bench II scoring with the benchmark's official judge, GPT-5.5 (phase 2, protocol v5.1 section 八).

What is kept from the benchmark's evaluator (data/drb2/repo-src/run_evaluation.py, Apache-2.0), as in drb2_score.py:
  - its prompt template word for word (imported from drb2_score.PROMPT_TEMPLATE), sent as the single user turn,
    no system message (the official script sends none either)
  - all rubric items of a task in the order info_recall, analysis, presentation, judged in batches of 50
  - the report text cut at 150,000 characters
  - a batch is accepted only if every rubric item comes back with its text unchanged; up to 5 attempts
  - a rubric item scores 1 / 0 / -1; dimension score = share of 1; total = share of 1; blocked rate = share of -1
  - the model is gpt-5.5, max 32,768 output tokens (the official default); reasoning effort high (the official default is
    medium; calibration 2026-10-08 on 12 phase-1 reports: two-pass item agreement medium 0.959, high 0.978)
What differs:
  - the request goes through the company proxy, which serves openai/gpt-5.5 on the Responses API only (its
    chat-completions route rejects this model); the same prompt text goes in the `input` field
  - replies with an implausible usage record (input tokens under 100, the proxy anomaly of 10/3) are discarded and asked
    again; a refusal (a `refusal` content item, or a message without text) is recorded and not asked again
  - the judge never sees the group: this script reads only the run id and the task from --rows and writes no group
    or repeat into its output; the unblinding join happens later in master_table.py

Reads <reports>/<run id>/workspace/report.md. Writes <out>/<run id>.r<k>.json and prints one line per run.
Key: JUDGE_USER_SK in the environment (dev box), else the macOS keychain item dsllm-usersk.
Usage: drb2_score_gpt.py --reports results/runs/<batch> --rows <csv with id,task> --out results/drb2-score-gpt/<batch>
                         [--ids a,b] [--limit N] [--parallel 8] [--repeat 1] [--effort medium] [--force]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import drb2_score as ds  # noqa: E402  (the official prompt template, chunking and parsing)

MODEL = "openai/gpt-5.5"
JUDGE = "gpt-5.5"
BASE_URL = "https://proxy.high-five-ai.xyz:8443/v1"
MAX_OUTPUT_TOKENS = 32768
TASKS = ROOT / "data/drb2/repo-src/tasks_and_rubrics.jsonl"
DIMS, CHUNK, MAX_CHARS, RETRIES = ds.DIMS, ds.CHUNK, ds.MAX_CHARS, ds.RETRIES
READ_TIMEOUT_S = 900
TEMPLATE_SHA = hashlib.sha256(ds.PROMPT_TEMPLATE.encode("utf-8")).hexdigest()[:12]


def user_sk() -> str:
    key = os.environ.get("JUDGE_USER_SK", "").strip()
    if key:
        return key
    return subprocess.run(["security", "find-generic-password", "-a", "zhangziya", "-s", "dsllm-usersk", "-w"],
                          check=True, capture_output=True, text=True).stdout.strip()


class Transient(Exception):
    """A network failure or a 5xx / 429 from the proxy: ask again after a pause."""


class Refused(Exception):
    """The judge declined the request (a refusal item, or a message with no text)."""


def responses_call(prompt: str, effort: str, token: str, max_output_tokens: int = MAX_OUTPUT_TOKENS) -> dict:
    """One Responses API call. Returns {"text", "usage", "status", "seconds", "refusal"}."""
    import httpx
    body = {"model": MODEL, "input": prompt, "reasoning": {"effort": effort}, "max_output_tokens": max_output_tokens}
    headers = {"authorization": f"Bearer {token}", "content-type": "application/json"}
    t0 = time.time()
    try:
        with httpx.Client(trust_env=False, timeout=httpx.Timeout(connect=60, read=READ_TIMEOUT_S, write=120, pool=60)) as client:
            r = client.post(BASE_URL + "/responses", headers=headers, json=body)
    except (httpx.TransportError, httpx.TimeoutException) as e:
        raise Transient(f"{type(e).__name__}") from None
    if r.status_code >= 500 or r.status_code == 429:
        raise Transient(f"HTTP {r.status_code}: {r.text[:200]}")
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    texts, refusal = [], None
    for item in data.get("output") or []:
        if item.get("type") != "message":
            continue
        for c in item.get("content") or []:
            if c.get("type") == "output_text":
                texts.append(c.get("text") or "")
            elif c.get("type") == "refusal":
                refusal = c.get("refusal") or "refusal"
    u = data.get("usage") or {}
    usage = {"input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
             "reasoning_tokens": (u.get("output_tokens_details") or {}).get("reasoning_tokens"),
             "cached_tokens": (u.get("input_tokens_details") or {}).get("cached_tokens")}
    return {"text": "".join(texts), "usage": usage, "status": data.get("status"), "model": data.get("model"),
            "seconds": round(time.time() - t0, 1), "refusal": refusal,
            "incomplete": (data.get("incomplete_details") or {}).get("reason")}


def ask_batch(items: list, task: str, blocked: dict, paper: str, effort: str, label: str, calls: list, token: str):
    rubric_json = json.dumps({"task": task, "rubric_items": items, "blocked": blocked}, ensure_ascii=False, indent=2)
    prompt = ds.PROMPT_TEMPLATE.format(paper=paper, rubric=rubric_json)
    for attempt in range(1, RETRIES + 1):
        anomalous = 0
        while True:
            for net in range(1, 4):
                try:
                    tagged = prompt if not anomalous else prompt + f"\n(request tag: {uuid.uuid4().hex[:12]})"
                    rep = responses_call(tagged, effort, token)
                    break
                except Transient as e:
                    if net == 3:
                        raise
                    print(f"{label}: transient {e}; retrying", flush=True)
                    time.sleep(15 * net)
            u = rep["usage"]
            rec = {"attempt": attempt, "items": len(items), "seconds": rep["seconds"], "status": rep["status"], "model": rep["model"],
                   "incomplete": rep["incomplete"], "prompt_chars": len(prompt), "usage": u}
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
        if rep["refusal"] or (not rep["text"].strip() and rep["status"] == "completed"):
            print(f"{label}: the judge refused the request", flush=True)
            return "refused"
        obj = ds.parse(rep["text"])
        if obj is None:
            print(f"{label}: reply did not parse (attempt {attempt}, status {rep['status']}, {rep['incomplete']}); asking again", flush=True)
            continue
        got = {r.get("rubric_item"): r for r in obj["results"] if isinstance(r, dict)}
        if all(i in got for i in items) and all(got[i].get("score") in (1, 0, -1) for i in items):
            return [got[i] for i in items]
        print(f"{label}: {sum(i not in got for i in items)} of {len(items)} rubric items missing or changed (attempt {attempt}); asking again", flush=True)
    return None


def score_one(run: dict, tasks: dict, a, k: int, token: str) -> dict:
    rid = run["id"]
    target = a.out / f"{rid}.r{k}.json"
    if target.exists() and not a.force:
        return json.loads(target.read_text(encoding="utf-8"))
    idx = int(run["task"].rsplit("_", 1)[1])
    content = tasks[idx]["content"]
    rec = {"id": rid, "task": run["task"], "idx": idx, "judge_rep": k, "judge": JUDGE, "model": MODEL, "effort": a.effort,
           "template_sha": TEMPLATE_SHA}
    f = a.reports / rid / "workspace" / "report.md"
    calls = []
    if not f.exists():
        rec.update(note="no report.md", total=None, chars=0, llm={"calls": 0, "anomalous": 0})
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
        got = ask_batch(items[b:b + CHUNK], content["task"], content.get("blocked") or {}, paper, a.effort, f"{rid} batch {b // CHUNK + 1}", calls, token)
        if got == "refused":
            rec.update(note="judge refused", refused=True, total=None,
                       llm={"calls": len(calls), "anomalous": sum(1 for c in calls if c.get("anomalous")), "detail": calls})
            target.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            return rec
        if got is None:
            failed = True
            break
        results += got
    llm = {"calls": len(calls), "anomalous": sum(1 for c in calls if c.get("anomalous")),
           "input_tokens": sum((c["usage"].get("input_tokens") or 0) for c in calls),
           "output_tokens": sum((c["usage"].get("output_tokens") or 0) for c in calls),
           "reasoning_tokens": sum((c["usage"].get("reasoning_tokens") or 0) for c in calls),
           "seconds": round(sum(c["seconds"] for c in calls), 1), "detail": calls}
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
               items=[{"dim": dim_of[r["rubric_item"]], "rubric_item": r["rubric_item"], "score": r["score"],
                       "reason": r.get("reason", ""), "evidence": r.get("evidence", "")} for r in results], llm=llm, note="")
    target.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


def load_tasks() -> dict:
    tasks = {}
    for line in TASKS.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            t = json.loads(line)
            tasks[int(t["idx"])] = t
    return tasks


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reports", type=Path, required=True)
    ap.add_argument("--rows", type=Path, required=True, help="CSV with at least id and task (drb2_zh_NNN); other columns are ignored")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ids", default="")
    ap.add_argument("--limit", type=int, default=0, help="only the first N runs in run-id hash order (for a second pass)")
    ap.add_argument("--parallel", type=int, default=8)
    ap.add_argument("--effort", default="high", help="the official default is medium; high chosen after the 2026-10-08 calibration (two-pass agreement 0.978 vs 0.959)")
    ap.add_argument("--repeat", type=int, default=1, help="write .r<repeat>.json (2 = a second, independent pass)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks()
    rows = [{"id": r["id"], "task": r["task"]} for r in csv.DictReader(open(a.rows, encoding="utf-8"))
            if r["task"].startswith("drb2_") and r.get("incomplete") != "1"]
    want = set(filter(None, a.ids.split(",")))
    if want:
        rows = [r for r in rows if r["id"] in want]
    if a.limit:
        rows = sorted(rows, key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())[:a.limit]
    token = user_sk()
    print(f"{len(rows)} reports, pass {a.repeat}, judge {JUDGE} effort {a.effort}, template {TEMPLATE_SHA} -> {a.out}", flush=True)
    lock, done = threading.Lock(), []

    def work(r):
        try:
            rec = score_one(r, tasks, a, a.repeat, token)
        except Exception as e:  # noqa: BLE001
            print(f"{r['id']} ERROR {type(e).__name__}: {str(e)[:300]}", flush=True)
            return
        with lock:
            done.append(rec)
        d = rec.get("dims") or {}
        print(f"{rec['id']} r{a.repeat} {rec['task']} chars={rec.get('chars')} total={rec.get('total')} "
              + " ".join(f"{k}={(d.get(k) or {}).get('score')}" for k in DIMS)
              + f" blocked={rec.get('blocked_rate')} calls={rec['llm']['calls']} s={rec['llm'].get('seconds')} {rec.get('note', '')}", flush=True)
    with cf.ThreadPoolExecutor(a.parallel) as pool:
        list(pool.map(work, rows))
    ok = [d for d in done if d.get("total") is not None]
    secs = [c["seconds"] for d in done for c in (d["llm"].get("detail") or [])]
    print(f"{len(ok)} of {len(rows)} reports scored; {len(secs)} calls, median {sorted(secs)[len(secs) // 2] if secs else None} s per call; "
          f"anomalous replies {sum(d['llm']['anomalous'] for d in done)}; refused {sum(1 for d in done if d.get('refused'))}")


if __name__ == "__main__":
    main()
