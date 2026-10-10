#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Judge the reports the ordinary GPT-5.5 scorer could not finish, with one change: an echoed rubric item that comes
back altered by a character or two is matched to the item it was asked about instead of failing the whole request.

Why. drb2_score_gpt.ask_batch sends a chunk of rubric items and accepts the reply only when every returned
"rubric_item" string is byte-identical to an item it asked about. For task drb2_zh_091 the judge reliably rewrites
one item of the second chunk — 模糊表达 -> 模糊表述, one character, both ordinary Chinese — so five attempts in a row
were rejected and six reports were left unjudged (probe of 2026-10-10: 40 of 41 items exact, the 41st differing in
that one character, the item's score present as usual).

What this changes. Only how a returned item is paired with the item it answers; the model, prompt, effort, chunking
and scoring rule are the deployed scorer's, imported unchanged. A returned item that is not an exact match is paired
with an asked item only when the pairing is unambiguous: both sides still unmatched, similarity >= MIN_RATIO, and no
other asked item that close. Every repair is written to <out>/../repairs-<run>.json and printed, so each one can be
read back.

Usage (the key comes from the environment, as for the deployed scorer):
  JUDGE_USER_SK=... PYTHONPATH=<judge-env/scripts> python drb2_score_gpt_repair.py --reports results/runs/p2-main \\
      --rows results/master/raw/p2-main.csv --out results/drb2-score-gpt/p2-main --ids a,b,c --parallel 2 --effort high
"""
from __future__ import annotations

import difflib
import json
import sys
import threading
from pathlib import Path

sys.dont_write_bytecode = True
import drb2_score as ds
import drb2_score_gpt as dsg

MIN_RATIO = 0.9  # a returned item must be at least this close to the asked item, and clearly closer than any other
GAP = 0.05       # how far the runner-up must be behind, so that two similar items are never confused
asked_items = threading.local()
repairs: list = []
lock = threading.Lock()


def repair(obj, items: list):
    """Rewrite returned rubric_item keys that are near-misses of an asked item. Returns the number repaired."""
    results = [r for r in obj.get("results") or [] if isinstance(r, dict)]
    returned = {str(r.get("rubric_item")) for r in results}
    free = [i for i in items if i not in returned]
    if not free:
        return 0
    n = 0
    for r in results:
        got = str(r.get("rubric_item"))
        if got in set(items):
            continue
        scored = sorted(((difflib.SequenceMatcher(None, i, got).ratio(), i) for i in free), reverse=True)
        if not scored or scored[0][0] < MIN_RATIO or (len(scored) > 1 and scored[0][0] - scored[1][0] < GAP):
            continue
        best = scored[0][1]
        r["rubric_item"] = best
        free.remove(best)
        n += 1
        with lock:
            repairs.append({"returned": got, "asked": best, "ratio": round(scored[0][0], 4)})
    return n


def main() -> None:
    orig_ask, orig_parse = dsg.ask_batch, ds.parse

    def ask_batch(items, *a, **k):
        asked_items.items = list(items)
        return orig_ask(items, *a, **k)

    def parse(text):
        obj = orig_parse(text)
        items = getattr(asked_items, "items", None)
        if obj is not None and items:
            n = repair(obj, items)
            if n:
                print(f"repaired {n} echoed rubric item(s) of this reply", flush=True)
        return obj

    dsg.ask_batch, ds.parse = ask_batch, parse
    try:
        dsg.main()
    finally:
        out = next((Path(a) for f, a in zip(sys.argv, sys.argv[1:]) if f == "--out"), Path("."))
        path = out.parent / f"repairs-{out.name}.json"
        path.write_text(json.dumps(repairs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(repairs)} repaired item(s) written to {path}", flush=True)


if __name__ == "__main__":
    main()
