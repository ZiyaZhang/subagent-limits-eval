#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blind human check of the DRB II judge (protocol v5.1 section 八): the sample, the blind form, and the scoring.

A unit is a PAIR: the same task and the same rubric item judged on the "no subagent" report (group D0) and on the
"default" report (group W-D1-K8, rep 1) of that task. Pairs come only from tasks where BOTH reports were judged by
GPT-5.5 and by Opus (Opus judges a fifth of the reports in run-id hash order, so `make` prints how many such tasks
exist and writes opus-missing.csv: the counterpart reports that still need an Opus judgement). Pairs with a -1
(blocked-source) score on any side are left out: the human form has no such verdict. 50 pairs are drawn where
GPT-5.5 and Opus agree on both judgements and 50 where they disagree on at least one, each stratum spread as evenly
as the pool allows over tasks and, within a task, over item dimensions (round robin with a seeded random order).

`make` writes:
  sample.json          the SEALED key: every pair with task, rubric item, dimension, run id, group, GPT and Opus
                       scores per side, and the form entry number of each side. Not to be opened before the check.
  form.md              the blind form: one entry per judgement (2 per pair), in random order; each shows the entry
                       number, the rubric item, one line of the task, and the report excerpt: the paragraph(s) where
                       a judge's cited evidence occurs (GPT-5.5's first, then Opus's); without a hit, the 3
                       paragraphs around the best keyword match of the rubric item (numbers, quoted names, character
                       bigrams); without any match, the report's headings and the note "判分未引用原文". Never the
                       group, the run id, a score or a reason.
  answer-template.csv  entry, verdict - to be filled with 满足 / 不满足 / 拿不准
  sha256.txt           the sha256 of form.md and sample.json (also printed)
`score` reads the filled csv and sample.json and prints: human-vs-GPT agreement and Cohen's kappa overall, per
stratum (agree / disagree), per dimension and per excerpt method; the same against Opus; accuracy weighted by the
population shares of the two strata; and the paired difference default - D0 (percentage points of items satisfied)
under the human verdicts against the GPT and Opus verdicts on the same pairs, unweighted and stratum-weighted.

Usage:
  human_check_sample.py make --gpt results/drb2-score-gpt/<batch> --opus results/drb2-score/<batch> \
      --runs results/master/raw/<batch>.csv --reports results/runs/<batch> --out results/human-check/<batch> \
      [--seed 20261008] [--n-agree 50] [--n-disagree 50] [--rep 1] [--group-a D0] [--group-b W-D1-K8] [--rep-b 1]
  human_check_sample.py score --answers results/human-check/<batch>/answers.csv --sample results/human-check/<batch>/sample.json
Reads and writes files only; no API call.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import random
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "data/drb2/repo-src/tasks_and_rubrics.jsonl"
INDEX = ROOT / "tasks/phase2-drb2-index.json"
DIMS = ("info_recall", "analysis", "presentation")
HEADING = re.compile(r"^#{1,6}\s")
FENCE = re.compile(r"^\s*(```|~~~)")
SCAFFOLD = re.compile(r"^(?:在[^，,。]{1,14}[，,])?(?:报告|文章|正文)?(?:中|应|必须)?(?:明确|正确|准确|清晰地?|具体)?(?:指出|提及|提到|说明|给出|列出|列举|填写|描述|解释|阐述|提出|将|把)?")
STOP = set("的了是在和与及或对于为把被从到由并也都及其等这那其中以及通过进行作为明确指出提及应当必须可以")
BLOCK_CAP = 2000
VERDICT = {"满足": 1, "1": 1, "y": 1, "yes": 1, "是": 1, "true": 1,
           "不满足": 0, "0": 0, "n": 0, "no": 0, "否": 0, "false": 0,
           "拿不准": None, "?": None, "": None, "unsure": None, "u": None, "不确定": None}


# ----------------------------------------------------------------------------------------------------- reports
def blocks_of(text: str) -> list:
    """The paragraphs of a markdown text as strings: runs of non-blank lines, whole fenced code blocks, headings."""
    out, cur, in_fence = [], [], False
    for line in text.splitlines():
        if in_fence:
            cur.append(line)
            if FENCE.match(line):
                out.append("\n".join(cur))
                cur, in_fence = [], False
            continue
        if FENCE.match(line):
            if cur:
                out.append("\n".join(cur))
            cur, in_fence = [line], True
            continue
        if not line.strip():
            if cur:
                out.append("\n".join(cur))
                cur = []
        elif HEADING.match(line):
            if cur:
                out.append("\n".join(cur))
            cur = [line]
        else:
            cur.append(line)
    if cur:
        out.append("\n".join(cur))
    return out


def norm(s: str) -> str:
    return re.sub(r"[\s*_`>|#]+", "", s)


def evidence_pieces(ev: str) -> list:
    parts = re.split(r"[；;\n]|……|…|\.\.\.|\s{3,}", ev or "")
    out = []
    for p in parts:
        p = norm(p.strip(" \"“”'‘’「」"))
        if len(p) >= 6:
            out.append(p)
            if len(p) >= 24:  # a judge often shortens or re-punctuates a quote: its ends still locate it
                out += [p[:14], p[-14:]]
    return out


def key_terms(item: str) -> list:
    """(term, weight): numbers and quoted names weigh 3, CJK character bigrams of the item's statement weigh 1."""
    s = SCAFFOLD.sub("", item.strip(), count=1)
    terms = []
    for m in re.finditer(r"\d[\d,.]*%?", s):
        terms.append((m.group(0).rstrip("."), 3))
    for m in re.finditer(r"[‘“《「(（]([^’”》」)）]{2,30})[’”》」)）]", s):
        terms.append((norm(m.group(1)), 3))
    cjk = re.sub(r"[^一-鿿]", " ", s)
    for word in cjk.split():
        for i in range(len(word) - 1):
            bg = word[i:i + 2]
            if bg[0] not in STOP and bg[1] not in STOP:
                terms.append((bg, 1))
    seen, out = set(), []
    for t, w in terms:
        if t not in seen:
            seen.add(t)
            out.append((t, w))
    return out


def excerpt_for(blocks: list, evidences: list, item: str) -> tuple:
    """(method, blocks to show, note). method: evidence / keyword / none."""
    normed = [norm(b) for b in blocks]
    hits = []
    for ev in evidences:
        for piece in evidence_pieces(ev):
            for i, nb in enumerate(normed):
                if piece in nb and i not in hits:
                    hits.append(i)
        if hits:
            break
    if hits:
        hits = sorted(hits)[:5]
        return "evidence", [blocks[i] for i in hits], ""
    terms = key_terms(item)
    total = sum(w for _, w in terms) or 1
    best, best_score, best_hits = None, 0.0, 0
    for i, nb in enumerate(normed):
        if HEADING.match(blocks[i]) and len(nb) < 30:
            continue
        got = [(t, w) for t, w in terms if t in nb]
        score = sum(w for _, w in got) / total
        if score > best_score:
            best, best_score, best_hits = i, score, len(got)
    if best is not None and best_score >= 0.25 and best_hits >= 2:
        lo, hi = max(0, best - 1), min(len(blocks), best + 2)
        return "keyword", blocks[lo:hi], ""
    heads = [b.splitlines()[0] for b in blocks if HEADING.match(b)]
    return "none", heads[:40], "判分未引用原文"


# ----------------------------------------------------------------------------------------------------- inputs
def load_scores(d: Path, rep: int) -> dict:
    out = {}
    for p in sorted(d.glob(f"*.r{rep}.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("total") is not None:
            out[rec["id"]] = rec
    return out


def task_lines(tasks_path: Path, index_path: Path) -> dict:
    """task id -> one line describing the task (first line of the prompt; else the index description)."""
    out = {}
    if index_path.exists():
        for tid, meta in json.loads(index_path.read_text(encoding="utf-8")).items():
            out[tid] = meta.get("description", "")
    if tasks_path.exists():
        for line in tasks_path.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                t = json.loads(line)
                if t.get("language") != "zh":
                    continue
                first = (t["content"]["task"].strip().split("\n")[0]).strip()
                out[f"drb2_zh_{int(t['idx']):03d}"] = first[:110] + ("…" if len(first) > 110 else "")
    return out


def pick_runs(rows: list, group: str, rep: str) -> dict:
    """task -> run of that group; the run with the wanted rep, else the lowest rep."""
    by = {}
    for r in rows:
        if r.get("group") != group:
            continue
        cur = by.get(r["task"])
        if cur is None or (str(r.get("rep")) == rep and str(cur.get("rep")) != rep) or (
                str(cur.get("rep")) != rep and str(r.get("rep")) < str(cur.get("rep"))):
            by[r["task"]] = r
    return by


def draw(pool: dict, n: int, rng: random.Random) -> list:
    """n pairs from pool[task][dim] = [pairs], round robin over tasks (seeded order) and, within a task, the dimension
    with the fewest picks so far; as even as the pool allows."""
    tasks = sorted(pool)
    rng.shuffle(tasks)
    for t in tasks:
        for d in pool[t]:
            rng.shuffle(pool[t][d])
    count = {t: {d: 0 for d in pool[t]} for t in tasks}
    out = []
    while len(out) < n:
        progressed = False
        for t in tasks:
            dims = [d for d in pool[t] if pool[t][d]]
            if not dims:
                continue
            d = min(dims, key=lambda d: (count[t][d], rng.random()))
            out.append(pool[t][d].pop())
            count[t][d] += 1
            progressed = True
            if len(out) >= n:
                break
        if not progressed:
            break
    return out


def sha256_of(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ----------------------------------------------------------------------------------------------------- make
def cmd_make(a) -> None:
    rows = [r for r in csv.DictReader(open(a.runs, encoding="utf-8")) if r["task"].startswith("drb2_") and r.get("incomplete") != "1"]
    run_a, run_b = pick_runs(rows, a.group_a, "1"), pick_runs(rows, a.group_b, a.rep_b)
    gpt, opus = load_scores(a.gpt, a.rep), load_scores(a.opus, a.rep)
    both_runs = sorted(t for t in run_a if t in run_b)
    both_gpt = [t for t in both_runs if run_a[t]["id"] in gpt and run_b[t]["id"] in gpt]
    both_opus = [t for t in both_gpt if run_a[t]["id"] in opus and run_b[t]["id"] in opus]
    print(f"tasks with a {a.group_a} run and a {a.group_b} rep-{a.rep_b} run: {len(both_runs)}; both GPT-judged: {len(both_gpt)}; "
          f"both Opus-judged (eligible): {len(both_opus)}")
    a.out.mkdir(parents=True, exist_ok=True)
    missing = [{"id": run[t]["id"], "task": t, "group": g} for t in both_gpt if t not in both_opus
               for g, run in ((a.group_a, run_a), (a.group_b, run_b)) if run[t]["id"] not in opus]
    with open(a.out / "opus-missing.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "task", "group"])
        w.writeheader()
        w.writerows(missing)
    print(f"reports that would make more tasks eligible if Opus judged them: {len(missing)} (opus-missing.csv; "
          f"drb2_score.py --ids on them, then run make again)")
    if not both_opus:
        sys.exit("no eligible task")
    # the population of pairs
    pairs, excluded, pop = [], 0, {"agree": 0, "disagree": 0}
    for t in both_opus:
        ia, ib = run_a[t]["id"], run_b[t]["id"]
        ga = {it["rubric_item"]: it for it in gpt[ia]["items"]}
        gb = {it["rubric_item"]: it for it in gpt[ib]["items"]}
        oa = {it["rubric_item"]: it for it in opus[ia]["items"]}
        ob = {it["rubric_item"]: it for it in opus[ib]["items"]}
        for item, it in ga.items():
            if item not in gb or item not in oa or item not in ob:
                continue
            s = (it["score"], gb[item]["score"], oa[item]["score"], ob[item]["score"])
            if -1 in s:
                excluded += 1
                continue
            stratum = "agree" if (s[0] == s[2] and s[1] == s[3]) else "disagree"
            pop[stratum] += 1
            pairs.append({"task": t, "rubric_item": item, "dim": it["dim"], "stratum": stratum,
                          "a": {"id": ia, "group": a.group_a, "rep": str(run_a[t].get("rep")), "gpt": s[0], "opus": s[2],
                                "evidence": [it.get("evidence") or "", oa[item].get("evidence") or ""]},
                          "b": {"id": ib, "group": a.group_b, "rep": str(run_b[t].get("rep")), "gpt": s[1], "opus": s[3],
                                "evidence": [gb[item].get("evidence") or "", ob[item].get("evidence") or ""]}})
    by_sd = {}
    for p in pairs:
        by_sd[(p["stratum"], p["dim"])] = by_sd.get((p["stratum"], p["dim"]), 0) + 1
    print(f"population: {len(pairs)} pairs over {len(both_opus)} tasks ({pop['agree']} agree, {pop['disagree']} disagree; "
          f"{excluded} left out for a -1 score); " + ", ".join(f"{s}/{d} {by_sd.get((s, d), 0)}" for s in ("agree", "disagree") for d in DIMS))
    # the sample
    rng = random.Random(a.seed)
    sample = []
    for stratum, n in (("agree", a.n_agree), ("disagree", a.n_disagree)):
        pool = {}
        for p in pairs:
            if p["stratum"] == stratum:
                pool.setdefault(p["task"], {}).setdefault(p["dim"], []).append(p)
        got = draw(pool, n, rng)
        if len(got) < n:
            print(f"only {len(got)} {stratum} pairs available, {n} wanted")
        sample += got
    for k, p in enumerate(sample, 1):
        p["pair"] = f"P{k:03d}"
    entries = [(p, side) for p in sample for side in ("a", "b")]
    rng.shuffle(entries)
    # the form
    descr = task_lines(a.tasks, a.index)
    texts, methods = {}, {"evidence": 0, "keyword": 0, "none": 0}
    lines = ["# 判分人工核对表（盲）", "",
             f"共 {len(entries)} 条，顺序随机；每条是一个评分项对一份报告的一次判定。生成于 {dt.datetime.now().isoformat(timespec='seconds')}，种子 {a.seed}。", "",
             "填写说明：", "",
             "- 只根据所给节选判断这份报告是否满足该评分项。判定标准与判分模型相同：报告明确、具体地满足评分项才算“满足”；数字类评分项要求数值明确写出并与评分项一致；只提到相关话题而没有给出评分项要求的内容，算“不满足”。",
             "- 节选是报告里与评分项最相关的段落（按判分引用的原文定位，没有引用时按关键词定位），可能有删节。节选里找不到、但你怀疑报告别处有的，选“拿不准”。",
             "- 把判定写进 answer-template.csv 的 verdict 列：满足 / 不满足 / 拿不准。不要改 entry 列。",
             "- 不要打开 sample.json，它是答案（哪条来自哪份报告、判分模型给了几分）。", "", "---", ""]
    for k, (p, side) in enumerate(entries, 1):
        rid = p[side]["id"]
        if rid not in texts:
            f = a.reports / rid / "workspace" / "report.md"
            texts[rid] = blocks_of(f.read_text(encoding="utf-8")) if f.exists() else []
        method, blocks, note = excerpt_for(texts[rid], p[side]["evidence"], p["rubric_item"])
        methods[method] += 1
        p[side]["entry"], p[side]["excerpt_method"] = k, method
        lines += [f"## 条目 {k:03d}", "", f"**评分项**：{p['rubric_item']}", "",
                  f"**题目**：{p['task']} — {descr.get(p['task'], '')}", "", "**报告节选**：", ""]
        if method == "none":
            lines += [f"（{note}；下面是这份报告的各级标题）", ""]
        for b in blocks:
            if len(b) > BLOCK_CAP:
                b = b[:BLOCK_CAP] + "……（节选，后略）"
            lines += ["> " + l for l in b.splitlines()] + [">"]
        if blocks:
            lines.pop()
        lines += ["", "**判定**：[ ] 满足  [ ] 不满足  [ ] 拿不准", "", "---", ""]
    form = a.out / "form.md"
    form.write_text("\n".join(lines), encoding="utf-8")
    with open(a.out / "answer-template.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["entry", "verdict"])
        for k in range(1, len(entries) + 1):
            w.writerow([k, ""])
    # the sealed key
    by_task = {}
    for p in sample:
        by_task[p["task"]] = by_task.get(p["task"], 0) + 1
    sd_sample = {}
    for p in sample:
        sd_sample[f"{p['stratum']}/{p['dim']}"] = sd_sample.get(f"{p['stratum']}/{p['dim']}", 0) + 1
    key = {"SEALED": "答案文件。人工核对完成、答案 csv 的 sha256 记录之前不要打开。The key of the blind form: do not open before the human check is done.",
           "meta": {"created": dt.datetime.now().isoformat(timespec="seconds"), "seed": a.seed, "judge_rep": a.rep,
                    "groups": {"a": a.group_a, "b": a.group_b, "rep_b": a.rep_b}, "gpt_dir": str(a.gpt), "opus_dir": str(a.opus),
                    "reports_dir": str(a.reports), "runs": str(a.runs),
                    "tasks": {"with_both_runs": len(both_runs), "both_gpt": len(both_gpt), "both_opus": len(both_opus)},
                    "population": {"pairs": len(pairs), "agree": pop["agree"], "disagree": pop["disagree"], "excluded_minus1": excluded,
                                   "by_stratum_dim": {f"{s}/{d}": v for (s, d), v in sorted(by_sd.items())}},
                    "sample": {"pairs": len(sample), "agree": sum(1 for p in sample if p["stratum"] == "agree"),
                               "disagree": sum(1 for p in sample if p["stratum"] == "disagree"), "entries": len(entries),
                               "by_task": dict(sorted(by_task.items())), "by_stratum_dim": dict(sorted(sd_sample.items()))},
                    "excerpt_methods": methods, "form_sha256": sha256_of(form)},
           "pairs": [{"pair": p["pair"], "task": p["task"], "rubric_item": p["rubric_item"], "dim": p["dim"], "stratum": p["stratum"],
                      "a": {k: v for k, v in p["a"].items() if k != "evidence"}, "b": {k: v for k, v in p["b"].items() if k != "evidence"}}
                     for p in sorted(sample, key=lambda p: p["pair"])],
           "entries": [{"entry": p[side]["entry"], "pair": p["pair"], "side": side, "id": p[side]["id"], "group": p[side]["group"],
                        "task": p["task"], "dim": p["dim"], "stratum": p["stratum"], "gpt": p[side]["gpt"], "opus": p[side]["opus"],
                        "excerpt_method": p[side]["excerpt_method"]} for p, side in sorted(entries, key=lambda e: e[0][e[1]]["entry"])]}
    sample_f = a.out / "sample.json"
    sample_f.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    shas = {"form.md": sha256_of(form), "sample.json": sha256_of(sample_f)}
    (a.out / "sha256.txt").write_text("".join(f"{v}  {k}\n" for k, v in shas.items()), encoding="utf-8")
    print(f"sample: {len(sample)} pairs ({key['meta']['sample']['agree']} agree, {key['meta']['sample']['disagree']} disagree) over "
          f"{len(by_task)} tasks, {len(entries)} entries; excerpts by evidence {methods['evidence']}, by keyword {methods['keyword']}, none {methods['none']}")
    print("per task: " + ", ".join(f"{t} {n}" for t, n in sorted(by_task.items())))
    print("per stratum/dim: " + ", ".join(f"{k} {v}" for k, v in sorted(sd_sample.items())))
    for k, v in shas.items():
        print(f"sha256 {k}: {v}")
    print(f"written: {form}, {a.out / 'answer-template.csv'}, {sample_f} (SEALED), {a.out / 'sha256.txt'}")


# ----------------------------------------------------------------------------------------------------- score
def kappa(pairs: list):
    n = len(pairs)
    if not n:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    cats = {a for a, _ in pairs} | {b for _, b in pairs}
    pe = sum((sum(1 for a, _ in pairs if a == c) / n) * (sum(1 for _, b in pairs if b == c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else None


def t_quantile(df: int, conf: float = 0.95) -> float:
    try:
        from scipy import stats as sps
        return float(sps.t.ppf(0.5 + conf / 2, df))
    except ImportError:
        from statistics import NormalDist
        return NormalDist().inv_cdf(0.5 + conf / 2)


def agree_line(label: str, pairs: list) -> None:
    n = len(pairs)
    if not n:
        print(f"  {label:34s} n=0")
        return
    agr = sum(1 for a, b in pairs if a == b) / n
    k = kappa(pairs)
    tab = {(a, b): sum(1 for x, y in pairs if (x, y) == (a, b)) for a in (1, 0) for b in (1, 0)}
    print(f"  {label:34s} n={n:4d} agreement {agr:.3f} kappa {k if k is None else round(k, 3)}  "
          f"(human 1/judge 1 {tab[(1, 1)]}, 1/0 {tab[(1, 0)]}, 0/1 {tab[(0, 1)]}, 0/0 {tab[(0, 0)]})")


def mean_ci(xs: list) -> str:
    n = len(xs)
    if n < 2:
        return f"n={n}"
    m, sd = st.mean(xs), st.stdev(xs)
    half = t_quantile(n - 1) * sd / math.sqrt(n)
    return f"{100 * m:+.1f} pp [{100 * (m - half):+.1f}, {100 * (m + half):+.1f}] (n={n})"


def cmd_score(a) -> None:
    key = json.loads(a.sample.read_text(encoding="utf-8"))
    answers = {}
    for r in csv.DictReader(open(a.answers, encoding="utf-8")):
        v = (r.get("verdict") or "").strip().lower()
        if v not in VERDICT:
            sys.exit(f"entry {r.get('entry')}: verdict {r.get('verdict')!r} not understood (满足 / 不满足 / 拿不准)")
        answers[int(r["entry"])] = VERDICT[v]
    ents = key["entries"]
    missing = [e["entry"] for e in ents if e["entry"] not in answers]
    if missing:
        print(f"{len(missing)} entries without a row in the answers: {missing[:20]}{' …' if len(missing) > 20 else ''}")
    for e in ents:
        e["human"] = answers.get(e["entry"])
    done = [e for e in ents if e["human"] is not None]
    unsure = [e for e in ents if e["entry"] in answers and answers[e["entry"]] is None]
    unsure_by = {s: sum(1 for e in unsure if e["stratum"] == s) for s in ("agree", "disagree")}
    print(f"{len(ents)} entries; answered {len(done)}, 拿不准 {len(unsure)} (agree {unsure_by['agree']}, disagree {unsure_by['disagree']}); "
          f"answers sha256 {sha256_of(a.answers)}")
    for judge in ("gpt", "opus"):
        print(f"\nhuman vs {judge.upper()} (entries with a 满足/不满足 verdict):")
        agree_line("all", [(e["human"], e[judge]) for e in done])
        for s in ("agree", "disagree"):
            agree_line(f"stratum {s}", [(e["human"], e[judge]) for e in done if e["stratum"] == s])
        for d in DIMS:
            agree_line(f"dim {d}", [(e["human"], e[judge]) for e in done if e["dim"] == d])
        for m in ("evidence", "keyword", "none"):
            agree_line(f"excerpt by {m}", [(e["human"], e[judge]) for e in done if e["excerpt_method"] == m])
    pop = key["meta"]["population"]
    w = {s: pop[s] / (pop["agree"] + pop["disagree"]) for s in ("agree", "disagree")}
    for judge in ("gpt", "opus"):
        acc, var = 0.0, 0.0
        parts = []
        for s in ("agree", "disagree"):
            xs = [e["human"] == e[judge] for e in done if e["stratum"] == s]
            if xs:
                p = sum(xs) / len(xs)
                acc += w[s] * p
                var += w[s] ** 2 * p * (1 - p) / len(xs)
                parts.append(f"{s} {p:.3f} x {w[s]:.3f}")
        print(f"\n{judge.upper()} accuracy weighted by the population shares of the strata: {acc:.3f} "
              f"[{acc - 1.96 * math.sqrt(var):.3f}, {acc + 1.96 * math.sqrt(var):.3f}] ({'; '.join(parts)})")
    # paired difference default - D0
    by_pair = {}
    for e in done:
        by_pair.setdefault(e["pair"], {})[e["side"]] = e
    full = {k: v for k, v in by_pair.items() if "a" in v and "b" in v}
    strat = {p["pair"]: p["stratum"] for p in key["pairs"]}
    print(f"\npaired difference, {key['meta']['groups']['b']} minus {key['meta']['groups']['a']}, on the {len(full)} pairs with both sides answered "
          f"(share of items satisfied, percentage points):")
    for who in ("human", "gpt", "opus"):
        d_all = [v["b"][who] - v["a"][who] for v in full.values()]
        line = f"  {who:6s} {mean_ci(d_all)}"
        wm, parts = 0.0, []
        for s in ("agree", "disagree"):
            ds = [v["b"][who] - v["a"][who] for k, v in full.items() if strat[k] == s]
            if ds:
                wm += w[s] * st.mean(ds)
                parts.append(f"{s} {100 * st.mean(ds):+.1f} (n={len(ds)})")
        print(line + f"; stratum-weighted {100 * wm:+.1f} pp ({'; '.join(parts)})")
    dh = [v["b"]["human"] - v["a"]["human"] for v in full.values()]
    dg = [v["b"]["gpt"] - v["a"]["gpt"] for v in full.values()]
    if dg and st.mean(dg) != 0 and dh:
        print(f"  the GPT-judged difference on these pairs that survives the human verdicts: {100 * st.mean(dh) / st.mean(dg):.0f}%")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make", help="draw the sample and write the blind form and the sealed key")
    mk.add_argument("--gpt", type=Path, required=True, help="dir of GPT-5.5 judgements <id>.r<rep>.json")
    mk.add_argument("--opus", type=Path, required=True, help="dir of Opus judgements <id>.r<rep>.json")
    mk.add_argument("--runs", type=Path, required=True, help="run table CSV with id, task, group, rep[, incomplete]")
    mk.add_argument("--reports", type=Path, required=True, help="dir of runs: <id>/workspace/report.md")
    mk.add_argument("--out", type=Path, required=True)
    mk.add_argument("--seed", type=int, default=20261008)
    mk.add_argument("--n-agree", type=int, default=50)
    mk.add_argument("--n-disagree", type=int, default=50)
    mk.add_argument("--rep", type=int, default=1, help="judge pass to read")
    mk.add_argument("--group-a", default="D0")
    mk.add_argument("--group-b", default="W-D1-K8")
    mk.add_argument("--rep-b", default="1", help="which repeat of group b")
    mk.add_argument("--tasks", type=Path, default=TASKS)
    mk.add_argument("--index", type=Path, default=INDEX)
    mk.set_defaults(fn=cmd_make)
    sc = sub.add_parser("score", help="score the filled form against the sealed key")
    sc.add_argument("--answers", type=Path, required=True, help="the filled answer-template.csv")
    sc.add_argument("--sample", type=Path, required=True, help="sample.json")
    sc.set_defaults(fn=cmd_score)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
