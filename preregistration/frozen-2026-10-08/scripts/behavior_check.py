#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The human check of the behaviour annotation (phase 2, module I): a blind form from behavior_annotate.py's
summary.csv, and the scoring of the filled form.

  build   from summary.csv draw, for every checklist item, --per-side (3) runs the model answered "yes" and 3 it
          answered "no" (seeded), and write
            check-form.md              the entries in random order; each shows only the item's definition, the model's
                                       evidence quote with 2-3 lines of the digest around it, and the three boxes
                                       [ ] 是  [ ] 否  [ ] 拿不准 — never the model's answer
            check-answers-template.csv entry, answer (to fill: 是 / 否 / 拿不准)
            check-key.json             entry -> run, item, model answer (sealed: its sha256 is printed; keep the file
                                       unchanged until the form is filled)
  score   read the filled csv and the key; per item print the model's precision (share of its "yes" entries the
          checker confirmed) and miss rate (share of its "no" entries the checker marked 是); entries answered 拿不准 are
          counted apart; an item whose error (1 - precision, or the miss rate) is above one third is marked
          "examples only" (its rate is not reported as a measurement, only its examples are shown).

Usage (experiment directory):
  behavior_check.py build --summary results/behavior/<batch>/summary.csv --digests results/digests/<batch> \\
                          --out results/behavior/<batch>/check [--seed 20261008] [--per-side 3]
  behavior_check.py score --answers <filled csv> --key results/behavior/<batch>/check/check-key.json [--out DIR]
"""
from __future__ import annotations

import argparse
import collections
import csv
import difflib
import hashlib
import json
import random
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from behavior_annotate import ITEMS, ITEM_NAMES  # noqa: E402  (the fixed definitions)

DEFINITION = {name: definition for name, definition, _ in ITEMS}
YES = {"是", "yes", "y", "1", "true", "对"}
NO = {"否", "no", "n", "0", "false", "不是"}
UNSURE = {"拿不准", "unclear", "u", "?", "不确定", "unsure"}
LINE_WIDTH = 320


def squeeze(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def locate(lines: list, quote: str) -> tuple:
    """(index of the line holding the quote, how it was found): exact substring; else whitespace-insensitive; else the
    closest line by difflib. Returns (None, "not found") only for an empty quote."""
    q = quote.strip()
    if not q:
        return None, "empty"
    for i, line in enumerate(lines):
        if q in line:
            return i, "exact"
    sq = squeeze(q)
    if sq:
        for i, line in enumerate(lines):
            if sq in squeeze(line):
                return i, "whitespace-insensitive"
        # a quote that spans lines: the first line whose squeezed text starts the quote
        for i, line in enumerate(lines):
            s = squeeze(line)
            if s and sq.startswith(s[:40]) and len(s) >= 20:
                return i, "spans lines"
    best, score = None, 0.0
    for i, line in enumerate(lines):
        r = difflib.SequenceMatcher(None, q[:200], line[:400]).ratio()
        if r > score:
            best, score = i, r
    return best, f"closest line (similarity {score:.2f})"


def window(line: str, quote: str, width: int = LINE_WIDTH) -> str:
    """A line cut to `width` characters, keeping the quote visible when the line is long."""
    if len(line) <= width:
        return line
    pos = line.find(quote.strip()[:60]) if quote.strip() else -1
    if pos < 0:
        return line[:width] + "…"
    start = max(0, min(pos - width // 3, len(line) - width))
    return ("…" if start else "") + line[start:start + width] + ("…" if start + width < len(line) else "")


def context(digest_text: str, quote: str) -> tuple:
    """(context block, how the quote was located)."""
    lines = digest_text.split("\n")
    i, how = locate(lines, quote)
    if i is None:
        return "（模型没有给出引文）", how
    lo, hi = max(0, i - 1), min(len(lines), i + 2)
    block = []
    for j in range(lo, hi):
        mark = "▶ " if j == i else "  "
        block.append(mark + window(lines[j].rstrip(), quote if j == i else ""))
    return "\n".join(block), how


def cmd_build(a) -> None:
    rows = list(csv.DictReader(open(a.summary, encoding="utf-8")))
    digests = {}
    for p in a.digests.glob("*.json"):
        digests[p.stem] = p.read_text(encoding="utf-8")
    rng = random.Random(a.seed)
    entries, short = [], []
    for name in ITEM_NAMES:
        for side in ("yes", "no"):
            pool = sorted({r["id"] for r in rows if r["item"] == name and r["answer"] == side and r["id"] in digests})
            take = pool if len(pool) <= a.per_side else rng.sample(pool, a.per_side)
            if len(pool) < a.per_side:
                short.append(f"{name}/{side}: only {len(pool)} run(s) available")
            for rid in take:
                r = next(x for x in rows if x["id"] == rid and x["item"] == name)
                entries.append({"run": rid, "item": name, "model_answer": side, "evidence": r.get("evidence", ""),
                                "confidence": r.get("confidence", ""), "reason": r.get("reason", "")})
    rng.shuffle(entries)
    for k, e in enumerate(entries, 1):
        e["entry"] = k
    a.out.mkdir(parents=True, exist_ok=True)
    form = ["# 行为标注人工核对表", "",
            f"共 {len(entries)} 条，顺序随机。每条只给出一个行为的定义、模型从运行摘要里引用的一句证据和摘要里它前后 2-3 行的上下文；不给模型的判断。",
            "请只按定义和这几行判断该行为在这次运行里是否发生：在 check-answers-template.csv 对应 entry 行的 answer 列填 是 / 否 / 拿不准（看不出来就填拿不准，不要猜）。",
            "摘要字段说明：A0 是主 agent，A1、A2… 是 subagent（按开始时间编号）；时间都是距运行开始的秒数；delegations 里 child 表示该次派活成功，rejected 表示被拒（n 为连续原样重试的次数）；overlap 是子任务文本与自己任务文本的四字片段重合率；handback 是 subagent 结束时交回的收尾消息；▶ 标出含引文的那一行。",
            "", "---", ""]
    for e in entries:
        block, how = context(digests[e["run"]], e["evidence"])
        form += [f"## 条目 {e['entry']}", "", f"**行为定义（{e['item']}）**：{DEFINITION[e['item']]}", "",
                 f"**运行**：{e['run']}", "", "**模型引用的证据**：", "", "> " + (e["evidence"].replace("\n", " ") or "（无）"), "",
                 f"**摘要上下文**（引文定位：{how}）：", "", "```", block, "```", "",
                 "[ ] 是  [ ] 否  [ ] 拿不准", "", "---", ""]
    (a.out / "check-form.md").write_text("\n".join(form), encoding="utf-8")
    with open(a.out / "check-answers-template.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["entry", "item", "run", "answer"])
        for e in entries:
            w.writerow([e["entry"], e["item"], e["run"], ""])
    key = {"seed": a.seed, "per_side": a.per_side, "summary": str(a.summary), "entries": sorted(entries, key=lambda e: e["entry"])}
    key_text = json.dumps(key, ensure_ascii=False, indent=1)
    (a.out / "check-key.json").write_text(key_text, encoding="utf-8")
    sha = hashlib.sha256(key_text.encode("utf-8")).hexdigest()
    (a.out / "check-key.sha256").write_text(sha + "  check-key.json\n", encoding="utf-8")
    by_item = collections.Counter((e["item"], e["model_answer"]) for e in entries)
    print(f"{len(entries)} entries -> {a.out}/check-form.md; per item (yes/no): "
          + ", ".join(f"{n} {by_item[(n, 'yes')]}/{by_item[(n, 'no')]}" for n in ITEM_NAMES))
    if short:
        print("short of runs: " + "; ".join(short))
    print(f"check-key.json sha256 {sha}")


def read_answer(raw: str) -> str:
    v = (raw or "").strip().lower()
    if v in YES:
        return "yes"
    if v in NO:
        return "no"
    if v in UNSURE:
        return "unclear"
    return ""


def cmd_score(a) -> None:
    key = json.loads(a.key.read_text(encoding="utf-8"))
    sha = hashlib.sha256(a.key.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    print(f"key sha256 {sha}")
    answers = {}
    for r in csv.DictReader(open(a.answers, encoding="utf-8")):
        answers[str(r.get("entry", "")).strip()] = read_answer(r.get("answer", ""))
    per = collections.defaultdict(lambda: collections.Counter())
    for e in key["entries"]:
        h = answers.get(str(e["entry"]), "")
        per[e["item"]][(e["model_answer"], h or "blank")] += 1
    rows = []
    print(f"{'item':22s} {'model yes: n':>12s} {'confirmed':>9s} {'precision':>9s} | {'model no: n':>11s} {'missed':>6s} {'miss rate':>9s} | unsure/blank  verdict")
    for name in ITEM_NAMES:
        c = per[name]
        yes_def = c[("yes", "yes")] + c[("yes", "no")]
        no_def = c[("no", "yes")] + c[("no", "no")]
        prec = c[("yes", "yes")] / yes_def if yes_def else None
        miss = c[("no", "yes")] / no_def if no_def else None
        unsure = c[("yes", "unclear")] + c[("no", "unclear")]
        blank = c[("yes", "blank")] + c[("no", "blank")]
        bad = (yes_def - c[("yes", "yes")]) * 3 > yes_def or c[("no", "yes")] * 3 > no_def  # error above one third, in integers
        verdict = "examples only" if bad else ("rate usable" if yes_def or no_def else "no data")
        rows.append({"item": name, "model_yes": yes_def, "confirmed": c[("yes", "yes")], "precision": "" if prec is None else round(prec, 3),
                     "model_no": no_def, "missed": c[("no", "yes")], "miss_rate": "" if miss is None else round(miss, 3),
                     "unsure": unsure, "blank": blank, "verdict": verdict})
        print(f"{name:22s} {yes_def:12d} {c[('yes', 'yes')]:9d} {('-' if prec is None else f'{prec:.2f}'):>9s} | {no_def:11d} {c[('no', 'yes')]:6d} "
              f"{('-' if miss is None else f'{miss:.2f}'):>9s} | {unsure:3d}/{blank:<3d}        {verdict}")
    out = a.out or a.key.parent
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "check-score.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"-> {out / 'check-score.csv'}; an item is 'examples only' when 1 - precision > 1/3 or miss rate > 1/3 "
          f"(拿不准 and blank entries are left out of both rates)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build")
    p.add_argument("--summary", type=Path, required=True)
    p.add_argument("--digests", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, default=20261008)
    p.add_argument("--per-side", type=int, default=3)
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("score")
    p.add_argument("--answers", type=Path, required=True)
    p.add_argument("--key", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    p.set_defaults(fn=cmd_score)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
