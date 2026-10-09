#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""What do subagents hand on when they delegate? Semantic classification of every delegation call made by a subagent
(phase 2, protocol v5.1 section 六: "subagent 自己再派活的分类"; she decided on 2026-10-08 that the judgement is by
meaning, made by the judge model, with the text-overlap score kept only as a first screen, and that she checks a sample).

A UNIT is one subagent (depth >= 1) that called the delegation tool at least once, whether the calls were accepted or
rejected: its own task (the text its parent gave it) and the task texts it sent, identical retries collapsed.

  extract   reads the logs of a batch (run_digest.analyse: full texts) and writes <out>/units.jsonl
  annotate  the judge model (openai/gpt-5.5, Responses API, effort medium; the route of the DRB II judging) labels every
            child task of every unit with one class; --dry-run writes the prompts and calls nothing
              whole    the child gets essentially the caller's whole task                      原样转包
              part     the child gets one part of a division of the caller's task              分片
              narrow   the child gets one narrower piece, most of the task stays with the caller  收窄
              new      the child gets something the caller's task does not state                新子题
              review   the child is asked to check work that already exists                    复核
              unclear                                                                           拿不准
            The prompt carries the two task texts only: no group, no limits, no outcome of the call.
  check     build: a blind form of --per-class (6) child tasks per class for the human check; score: agreement and kappa
  summary   per unit the derived type (pass-through: every child task is "whole"; split: two or more "part"; else the
            most frequent class) and whether it delegated before doing anything itself; with --runs (the master table)
            the shares per cell and the length of pass-through chains. Only this step reads cells.

Usage (experiment directory on the dev box):
  delegation_classify.py extract results/runs/<batch> --out results/delegation/<batch>
  delegation_classify.py annotate results/delegation/<batch> [--dry-run] [--limit N]
  delegation_classify.py check build results/delegation/<batch> ; delegation_classify.py check score --answers F --key F
  delegation_classify.py summary results/delegation/<batch> [--runs results/master-p2/runs.csv]
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import csv
import hashlib
import json
import random
import re
import sys
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

MODEL, EFFORT = "openai/gpt-5.5", "medium"
CLASSES = ["whole", "part", "narrow", "new", "review", "unclear"]
ZH = {"whole": "原样转包", "part": "分片", "narrow": "收窄", "new": "新子题", "review": "复核", "unclear": "拿不准"}
ZH_BACK = {v: k for k, v in ZH.items()}
# Task texts are long (main batch: median 3,500 characters for the own task and for a child task); what a task is about stands
# at its start, so the prompt carries the heads. The evidence quote is checked against the full child text.
OWN_MAX, CHILD_MAX, CHILDREN_MAX = 1500, 1000, 6
GROUP_RE = re.compile(r"\b(?:W-)?(?:T-)?(?:P[a-z0-9]+-)?(?:E-)?(?:N-)?D[0-3](?:-K\d+)?\b")
RULES = """You are classifying delegation calls made by SUBAGENTS in runs of an agent harness. A subagent received a task from its parent (OWN TASK). It then called the delegation tool one or more times, each time with a task text for a child (CHILD TASKS, numbered). For every child task decide what kind of delegation it is by comparing its MEANING with the own task. Wording does not matter: a reworded, shortened or translated copy of the own task is still a copy.

Classes (exactly one per child task):
- "whole": the child is given essentially the caller's whole task (the same question and scope); the caller keeps no distinct part for itself.
- "part": the child is given one part of a division of the caller's task (by sub-topic, source, file, period, region ...); the parts given to the children together make up most or all of the caller's task.
- "narrow": the child is given one narrower piece of the caller's task (one sub-question, one source to read, one figure to find) while most of the caller's task plainly stays with the caller.
- "new": the child is given something the caller's task does not state: a follow-up question that came up, extra background, a tool or environment chore.
- "review": the child is asked to check, verify, review or test work that already exists (a draft, numbers, code).
- "unclear": the texts do not allow a decision.

Rules:
1. Judge only from the texts given. You are told nothing about the run's experimental condition and must not guess it.
2. For every child task give one evidence quote copied verbatim from that CHILD TASK (at most 120 characters), a one-line reason (at most 150 characters) and a confidence: "low", "medium" or "high".
3. Label every child task of every unit. Output strict JSON only: no prose before or after, no code fences."""
OUTPUT_FORMAT = """Output format (one key per unit id, one key per child number):
{"<unit id>": {"1": {"class": "whole|part|narrow|new|review|unclear", "evidence": "<verbatim quote>", "reason": "<one line>", "confidence": "low|medium|high"}, "2": {...}}, ...}"""


def cut(text: str, n: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n] + f" …[{len(text) - n} more characters]"


def scrub(text: str) -> str:
    return GROUP_RE.sub("[condition]", text)


# ------------------------------------------------------------------------------------------------ extract
def units_of(run: dict) -> list:
    import run_digest as rd
    a = rd.analyse(run)
    by_name = {e["agent"]: e for e in a.get("agents") or []}
    out = []
    for e in a.get("agents") or []:
        if e["depth"] < 1 or not e.get("delegations"):
            continue
        children, total = [], 0
        for d in e["delegations"]:
            n = d.get("n", 1)
            total += n
            if "child" in d:
                text, outcome = (by_name.get(d["child"]) or {}).get("task_text") or "", "accepted"
            elif "rejected" in d:
                text, outcome = d.get("task_text") or "", "rejected: " + str(d["rejected"])
            else:
                text, outcome = d.get("task_text") or "", "no result"
            same = next((c for c in children if c["task"] == text), None)
            if same:  # the same text sent again (after a rejection, or to a second child): one child task, counted
                same["n"] += n
                same["outcomes"].append(outcome)
                continue
            children.append({"task": text, "outcomes": [outcome], "n": n, "overlap": d.get("overlap"), "child": d.get("child")})
        for i, c in enumerate(children, 1):
            c["i"] = i
        out.append({"unit": f"{a['run']}:{e['agent']}", "run": a["run"], "task_id": a.get("task_id"), "agent": e["agent"], "depth": e["depth"],
                    "parent": e.get("parent") or "A0", "own_task": e.get("task_text") or "", "own_calls": e.get("calls"),
                    "before": e.get("before_first_delegation"), "calls": total, "children": children})
    return out


def one_run(run: dict) -> tuple:
    try:
        return units_of(run), None
    except Exception as exc:  # noqa: BLE001
        return [], f"{run.get('key')}: {type(exc).__name__}: {str(exc)[:160]}"


def cmd_extract(a) -> None:
    import run_metrics as rm
    runs, _ = rm.discover(a.batch)
    for r in runs:
        r["dir"] = str(r["dir"])
    runs.sort(key=lambda r: r["key"])
    a.out.mkdir(parents=True, exist_ok=True)
    if a.jobs > 1 and len(runs) > 1:
        with cf.ProcessPoolExecutor(max_workers=a.jobs) as ex:
            results = list(ex.map(one_run, runs, chunksize=4))
    else:
        results = [one_run(r) for r in runs]
    units = [u for us, _ in results for u in us]
    errors = [e for _, e in results if e]
    with open(a.out / "units.jsonl", "w", encoding="utf-8") as fh:
        for u in units:
            fh.write(json.dumps(u, ensure_ascii=False) + "\n")
    n_child = sum(len(u["children"]) for u in units)
    by_depth = collections.Counter(u["depth"] for u in units)
    stats = (f"{a.batch.name}: {len(runs)} runs, {len({u['run'] for u in units})} with a delegating subagent; {len(units)} units "
             f"(by depth {dict(sorted(by_depth.items()))}), {n_child} distinct child tasks, {sum(u['calls'] for u in units)} calls; "
             f"units with more than {CHILDREN_MAX} child tasks: {sum(len(u['children']) > CHILDREN_MAX for u in units)}; errors {len(errors)}")
    (a.out / "extract-stats.txt").write_text(stats + "\n" + "\n".join(errors) + "\n", encoding="utf-8")
    print(stats)
    for e in errors[:5]:
        print("  error:", e)


# ------------------------------------------------------------------------------------------------ annotate
def load_units(d: Path) -> list:
    return [json.loads(line) for line in (d / "units.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def unit_text(u: dict) -> str:
    kids = u["children"][:CHILDREN_MAX]
    lines = [f"### unit {u['unit']}", "OWN TASK:", scrub(cut(u["own_task"], OWN_MAX)), "", f"CHILD TASKS ({len(kids)}):"]
    for c in kids:
        lines += [f"[{c['i']}] " + scrub(cut(c["task"], CHILD_MAX)), ""]
    return "\n".join(lines)


def build_prompt(batch: list) -> str:
    return "\n".join([RULES, "", OUTPUT_FORMAT, "", f"Units ({len(batch)}):", ""] + [unit_text(u) for u in batch])


def parse_reply(text: str):
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
    for cand in (t, t[t.find("{"):t.rfind("}") + 1] if "{" in t and "}" in t else ""):
        try:
            return json.loads(cand)
        except ValueError:
            continue
    return None


def labels_of(reply, u: dict) -> dict:
    got = reply.get(u["unit"]) if isinstance(reply, dict) else None
    out = {}
    for c in u["children"][:CHILDREN_MAX]:
        v = (got or {}).get(str(c["i"])) if isinstance(got, dict) else None
        v = v if isinstance(v, dict) else {}
        cls = str(v.get("class", "")).strip().lower()
        note = ""
        if cls not in CLASSES:
            cls, note = "unclear", f"missing or invalid class ({v.get('class')!r})"
        ev = str(v.get("evidence", "") or "")[:300]
        out[str(c["i"])] = {"class": cls, "evidence": ev, "reason": str(v.get("reason", "") or "")[:300],
                            "confidence": str(v.get("confidence", "") or "").strip().lower(),
                            "evidence_verified": bool(ev.strip()) and re.sub(r"\s+", "", ev) in re.sub(r"\s+", "", c["task"]), "note": note}
    return out


def write_labels_csv(d: Path, units: list) -> int:
    rows = []
    by_unit = {u["unit"]: u for u in units}
    for f in sorted((d / "labels").glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        u = by_unit.get(rec["unit"])
        if not u:
            continue
        for c in u["children"][:CHILDREN_MAX]:
            lab = rec["labels"].get(str(c["i"]), {})
            rows.append({"unit": u["unit"], "run": u["run"], "task_id": u["task_id"], "agent": u["agent"], "depth": u["depth"], "child": c["i"],
                         "n_calls": c["n"], "overlap": c.get("overlap"), "accepted": int("accepted" in c["outcomes"]), "class": lab.get("class", ""),
                         "confidence": lab.get("confidence", ""), "evidence_verified": int(bool(lab.get("evidence_verified"))),
                         "evidence": lab.get("evidence", ""), "reason": lab.get("reason", "")})
    if rows:
        with open(d / "labels.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    return len(rows)


def cmd_annotate(a) -> None:
    units = load_units(a.dir)
    ldir = a.dir / "labels"
    ldir.mkdir(parents=True, exist_ok=True)
    name = lambda u: hashlib.sha1(u["unit"].encode()).hexdigest()[:16]  # noqa: E731
    todo = [u for u in units if a.force or a.dry_run or not (ldir / f"{name(u)}.json").exists()]
    if a.ids:
        want = set(a.ids.split(","))
        todo = [u for u in todo if u["unit"] in want or u["run"] in want]
    if a.limit:
        rng = random.Random(a.seed)
        todo = sorted(rng.sample(todo, min(a.limit, len(todo))), key=lambda u: u["unit"])
    batches, cur, chars = [], [], 0
    for u in todo:
        n = len(unit_text(u))
        if cur and (len(cur) >= a.batch_size or chars + n > a.max_batch_chars):
            batches.append(cur)
            cur, chars = [], 0
        cur.append(u)
        chars += n
    if cur:
        batches.append(cur)
    prompts = [(i, b, build_prompt(b)) for i, b in enumerate(batches, 1)]
    total_chars = sum(len(p) for _, _, p in prompts)
    if a.dry_run:
        pdir = a.dir / "prompts"
        pdir.mkdir(parents=True, exist_ok=True)
        for i, b, text in prompts[:20]:
            (pdir / f"batch-{i:04d}.txt").write_text(text, encoding="utf-8")
        print(f"dry run: {len(todo)} units, {sum(len(u['children'][:CHILDREN_MAX]) for u in todo)} child tasks, {len(prompts)} request(s), "
              f"{total_chars / 1e6:.2f} million prompt characters; first prompts in {pdir}; model {a.model} effort {a.effort} (not called)")
        return
    import drb2_score_gpt as dsg
    dsg.MODEL = a.model
    token = dsg.user_sk()
    rdir = a.dir / "replies"
    rdir.mkdir(parents=True, exist_ok=True)
    lock, done = threading.Lock(), [0]

    def work(job):
        i, b, prompt = job
        rep = None
        for attempt in range(1, 6):
            try:
                rep = dsg.responses_call(prompt, a.effort, token)
            except dsg.Transient as e:
                print(f"batch {i}: transient {e}; retrying", flush=True)
                time.sleep(15 * attempt)
                continue
            if (rep["usage"].get("input_tokens") or 0) < 100 and attempt < 3:
                time.sleep(20)
                continue
            break
        if rep is None:
            print(f"batch {i}: no reply after retries", flush=True)
            return
        sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        (rdir / f"batch-{sha[:12]}.json").write_text(json.dumps({"units": [u["unit"] for u in b], "prompt_sha256": sha, "model": rep.get("model"),
                                                                  "usage": rep["usage"], "seconds": rep["seconds"], "text": rep["text"]}, ensure_ascii=False, indent=1), encoding="utf-8")
        reply = parse_reply(rep["text"])
        if reply is None:
            print(f"batch {i}: reply did not parse; units left for a later pass", flush=True)
            return
        for u in b:
            rec = {"unit": u["unit"], "run": u["run"], "model": a.model, "effort": a.effort, "prompt_sha256": sha, "labels": labels_of(reply, u)}
            (ldir / f"{name(u)}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        with lock:
            done[0] += len(b)
            if done[0] % 60 < len(b):
                print(f"{done[0]} / {len(todo)} units; last request {rep['seconds']} s, in {rep['usage'].get('input_tokens')} out {rep['usage'].get('output_tokens')}", flush=True)

    print(f"{len(todo)} units in {len(prompts)} request(s), {total_chars / 1e6:.2f} million prompt characters; model {a.model} effort {a.effort}", flush=True)
    with cf.ThreadPoolExecutor(a.parallel) as pool:
        list(pool.map(work, prompts))
    print(f"labels.csv: {write_labels_csv(a.dir, units)} child tasks labelled so far")


# ------------------------------------------------------------------------------------------------ human check
def kappa(pairs: list):
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    cats = {a for a, _ in pairs} | {b for _, b in pairs}
    pe = sum((sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else None


def cmd_check(a) -> None:
    if a.action == "build":
        units = {u["unit"]: u for u in load_units(a.dir)}
        write_labels_csv(a.dir, list(units.values()))
        rows = [r for r in csv.DictReader(open(a.dir / "labels.csv", encoding="utf-8")) if r["class"] in CLASSES[:5]]
        rng = random.Random(a.seed)
        picked = []
        for cls in CLASSES[:5]:
            pool = [r for r in rows if r["class"] == cls]
            rng.shuffle(pool)
            seen_runs = set()
            for r in pool:  # at most one entry per run and class, so that one odd run does not fill a class
                if r["run"] in seen_runs:
                    continue
                seen_runs.add(r["run"])
                picked.append(r)
                if len(seen_runs) >= a.per_class:
                    break
        rng.shuffle(picked)
        out = a.dir / "check"
        out.mkdir(parents=True, exist_ok=True)
        form = ["# subagent 再派活的分类：人工核对", "",
                f"共 {len(picked)} 条。每条是一个 subagent 领到的任务和它派出去的一条任务，判断这条派出去的任务属于哪一类。不显示模型的判断、组别和运行编号。",
                "", "- 原样转包：把自己领到的整件事原样交给下一层，自己不留明确的一块",
                "- 分片：把自己的任务切成几块，这条是其中一块，几块合起来基本就是它自己的任务",
                "- 收窄：只把一小块交出去（一个子问题、一个来源、一个数），大部分还是自己做",
                "- 新子题：交出去的是自己任务里没写的事（做着做着冒出来的问题、补充背景、环境杂事）",
                "- 复核：让下一层检查、核实、评审已经做出来的东西", "- 拿不准", "",
                "在 check-answers-template.csv 的 answer 列填类名，另存为 check-answers.csv。", ""]
        key = {}
        for n, r in enumerate(picked, 1):
            u = units[r["unit"]]
            c = next(x for x in u["children"] if str(x["i"]) == str(r["child"]))
            key[str(n)] = {"unit": r["unit"], "child": r["child"], "model": r["class"]}
            form += [f"## 条目 {n}", "", "**这个 subagent 领到的任务**：", "", "> " + scrub(cut(u["own_task"], 700)).replace("\n", "\n> "), "",
                     f"**它一共派出 {len(u['children'])} 条不同的任务，要判的是这一条**：", "", "> " + scrub(cut(c["task"], 700)).replace("\n", "\n> "), ""]
            others = [x for x in u["children"] if x is not c][:5]
            if others:
                form += ["它派出去的其他任务（各取开头）："] + ["- " + scrub(cut(x["task"], 110)).replace("\n", " ") for x in others] + [""]
            form += ["[ ] 原样转包　[ ] 分片　[ ] 收窄　[ ] 新子题　[ ] 复核　[ ] 拿不准", "", "---", ""]
        (out / "check-form.md").write_text("\n".join(form), encoding="utf-8")
        with open(out / "check-answers-template.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["entry", "answer"])
            for n in range(1, len(picked) + 1):
                w.writerow([n, ""])
        (out / "check-key.json").write_text(json.dumps({"SEALED": "核对完成前不要打开", "entries": key}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(picked)} entries ({dict(collections.Counter(r['class'] for r in picked))}); form {sum(len(x) for x in form)} characters -> {out}; "
              f"key sha256 {hashlib.sha256((out / 'check-key.json').read_bytes()).hexdigest()[:16]}")
        return
    key = json.loads(a.key.read_text(encoding="utf-8"))["entries"]
    pairs, unsure = [], 0
    for r in csv.DictReader(open(a.answers, encoding="utf-8-sig")):
        ans = (r.get("answer") or "").strip()
        cls = ZH_BACK.get(ans, ans.lower())
        e = key.get(str(r["entry"]).strip())
        if not e or cls not in CLASSES:
            continue
        if cls == "unclear":
            unsure += 1
            continue
        pairs.append((e["model"], cls))
    print(f"answers sha256 {hashlib.sha256(a.answers.read_bytes()).hexdigest()}")
    print(f"{len(pairs)} entries with a class from the checker, {unsure} 拿不准; agreement {sum(m == h for m, h in pairs) / len(pairs):.3f}, kappa {kappa(pairs):.3f}" if pairs else "no usable answer")
    for cls in CLASSES[:5]:
        mine = [(m, h) for m, h in pairs if m == cls]
        if mine:
            wrong = collections.Counter(h for m, h in mine if h != m)
            print(f"  model said {ZH[cls]}: {len(mine)} entries, checker agreed on {sum(m == h for m, h in mine)}"
                  + ("; checker said instead: " + ", ".join(f"{ZH[k]} {v}" for k, v in wrong.items()) if wrong else ""))


# ------------------------------------------------------------------------------------------------ summary
def unit_type(classes: list) -> str:
    known = [c for c in classes if c != "unclear"]
    if not known:
        return "unclear"
    if all(c == "whole" for c in known):
        return "whole"
    if sum(c == "part" for c in known) >= 2:
        return "part"
    return collections.Counter(known).most_common(1)[0][0]


def cmd_summary(a) -> None:
    units = load_units(a.dir)
    write_labels_csv(a.dir, units)
    lab = collections.defaultdict(dict)
    for r in csv.DictReader(open(a.dir / "labels.csv", encoding="utf-8")):
        lab[r["unit"]][r["child"]] = r["class"]
    rows = []
    for u in units:
        if u["unit"] not in lab:
            continue
        classes = [lab[u["unit"]].get(str(c["i"]), "unclear") for c in u["children"][:CHILDREN_MAX]]
        before = u.get("before") or {}
        rows.append({"unit": u["unit"], "run": u["run"], "agent": u["agent"], "parent": u["parent"], "depth": u["depth"], "children": len(u["children"]),
                     "calls": u["calls"], "any_accepted": int(any("accepted" in c["outcomes"] for c in u["children"])),
                     "type": unit_type(classes), "first_thing": int((before.get("substantive_calls") or 0) == 0 and (before.get("seconds_after_start") or 1e9) <= 60),
                     "substantive_before": before.get("substantive_calls"), "seconds_before": before.get("seconds_after_start"),
                     "max_overlap": max((c.get("overlap") or 0) for c in u["children"]) if u["children"] else ""})
    # pass-through chains: a unit of type "whole" whose parent is also a unit of type "whole", and so on
    by = {(r["run"], r["agent"]): r for r in rows}
    for r in rows:
        n, cur = 0, r
        while cur is not None and cur["type"] == "whole":
            n += 1
            cur = by.get((cur["run"], cur["parent"]))
        r["whole_chain"] = n
    with open(a.dir / "unit-types.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    c = collections.Counter(r["type"] for r in rows)
    print(f"{len(rows)} labelled units of {len(units)}: " + ", ".join(f"{ZH[k]} {v} ({100 * v / len(rows):.0f}%)" for k, v in c.most_common())
          + f"; delegated before doing anything: {sum(r['first_thing'] for r in rows)} ({100 * sum(r['first_thing'] for r in rows) / len(rows):.0f}%)")
    if not a.runs:
        return
    cell = {}
    for r in csv.DictReader(open(a.runs, encoding="utf-8")):
        d = int(float(r["D"]))
        base = "D0" if d == 0 else (f"K{int(float(r['K']))}" if d == 1 else f"D{d}K{int(float(r['K']))}")
        tag = {"none": "", "split-3-delegate": "n3", "split-8-delegate": "n8", "search-150-250": "more", "split-8-self": "seg", "planner-only": "plan"}.get(r["hint"], "?")
        cell[r["id"]] = (r["batch"], tag if tag in ("more", "seg") else tag + base, int(float(r["agents"] or 1)) - 1)
    agg = collections.defaultdict(lambda: {"runs": set(), "units": 0, "types": collections.Counter(), "first": 0, "chain": collections.Counter()})
    for r in rows:
        if r["run"] not in cell:
            continue
        g = agg[cell[r["run"]][:2]]
        g["runs"].add(r["run"])
        g["units"] += 1
        g["types"][r["type"]] += 1
        g["first"] += r["first_thing"]
        if r["type"] == "whole":
            g["chain"][r["whole_chain"]] += 1
    runs_per_cell = collections.Counter(v[:2] for v in cell.values())
    subs_per_cell = collections.Counter()
    for v in cell.values():
        subs_per_cell[v[:2]] += v[2]
    out = []
    for k in sorted(runs_per_cell):
        g = agg.get(k)
        row = {"batch": k[0], "cell": k[1], "runs": runs_per_cell[k], "subagents": subs_per_cell[k], "runs_with_delegating_subagent": len(g["runs"]) if g else 0,
               "delegating_subagents": g["units"] if g else 0, "share_of_subagents_delegating": round(g["units"] / subs_per_cell[k], 4) if g and subs_per_cell[k] else 0,
               "first_thing": g["first"] if g else 0}
        for t in CLASSES:
            row[f"type_{t}"] = g["types"][t] if g else 0
        row["whole_chain_2plus"] = sum(v for n, v in g["chain"].items() if n >= 2) if g else 0
        out.append(row)
    with open(a.dir / "cells.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"per cell: {a.dir / 'cells.csv'} ({len(out)} cells)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extract")
    ex.add_argument("batch", type=Path)
    ex.add_argument("--out", type=Path, required=True)
    ex.add_argument("--jobs", type=int, default=8)
    an = sub.add_parser("annotate")
    an.add_argument("dir", type=Path)
    an.add_argument("--dry-run", action="store_true")
    an.add_argument("--ids", default="")
    an.add_argument("--limit", type=int, default=0, help="a seeded random sample of this many units (pilot)")
    an.add_argument("--seed", type=int, default=20261008)
    an.add_argument("--batch-size", type=int, default=6)
    an.add_argument("--max-batch-chars", type=int, default=24000)
    an.add_argument("--effort", default=EFFORT)
    an.add_argument("--model", default=MODEL)
    an.add_argument("--parallel", type=int, default=4)
    an.add_argument("--force", action="store_true")
    ck = sub.add_parser("check")
    ck.add_argument("action", choices=["build", "score"])
    ck.add_argument("dir", type=Path, nargs="?")
    ck.add_argument("--per-class", type=int, default=6)
    ck.add_argument("--seed", type=int, default=20261008)
    ck.add_argument("--answers", type=Path)
    ck.add_argument("--key", type=Path)
    sm = sub.add_parser("summary")
    sm.add_argument("dir", type=Path)
    sm.add_argument("--runs", type=Path)
    a = ap.parse_args()
    {"extract": cmd_extract, "annotate": cmd_annotate, "check": cmd_check, "summary": cmd_summary}[a.cmd](a)


if __name__ == "__main__":
    main()
