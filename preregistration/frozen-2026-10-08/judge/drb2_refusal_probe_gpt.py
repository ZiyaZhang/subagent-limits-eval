#!/usr/bin/env python3
"""Does GPT-5.5 (the official judge) refuse to score a DeepResearch Bench II task? (protocol v5.1 section 八)

Same probe as drb2_refusal_probe.py, for the Responses API: for each task the scoring prompt of its first 50 rubric
items with the task's own prompt as the stand-in passage, cut off after a few hundred output tokens. A refusal is a
`refusal` content item or a completed message without text; an incomplete reply (max_output_tokens) counts as accepted.

Usage: drb2_refusal_probe_gpt.py --idx all-zh --out results/drb2-score-gpt/refusal-probe.json [--parallel 8]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drb2_score as ds  # noqa: E402
import drb2_score_gpt as g  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--idx", default="all-zh", help="all-zh, or comma-separated task idx")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--parallel", type=int, default=8)
    a = ap.parse_args()
    tasks = g.load_tasks()
    want = sorted(i for i, t in tasks.items() if t["language"] == "zh") if a.idx == "all-zh" else [int(x) for x in a.idx.split(",")]
    done = json.loads(a.out.read_text(encoding="utf-8")) if a.out.exists() else {}
    token = g.user_sk()

    def probe(i: int) -> tuple:
        if str(i) in done:
            return i, done[str(i)]
        c = tasks[i]["content"]
        items = [it for d in ds.DIMS for it in (c["rubric"].get(d) or [])][:50]
        rubric_json = json.dumps({"task": c["task"], "rubric_items": items, "blocked": c.get("blocked") or {}}, ensure_ascii=False, indent=2)
        prompt = ds.PROMPT_TEMPLATE.format(paper=tasks[i]["prompt"], rubric=rubric_json)
        for net in range(3):
            try:
                rep = g.responses_call(prompt, "medium", token, max_output_tokens=400)
                break
            except g.Transient as e:
                if net == 2:
                    return i, {"stop": f"error {e}", "theme": tasks[i]["theme"]}
        refused = bool(rep["refusal"]) or (not rep["text"].strip() and rep["status"] == "completed")
        return i, {"stop": "refusal" if refused else (rep["incomplete"] or rep["status"]), "in": rep["usage"]["input_tokens"],
                   "out": rep["usage"]["output_tokens"], "seconds": rep["seconds"], "theme": tasks[i]["theme"]}
    with cf.ThreadPoolExecutor(a.parallel) as pool:
        for i, rec in pool.map(probe, want):
            done[str(i)] = rec
            print(i, rec, flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    ref = sorted(int(i) for i, r in done.items() if r["stop"] == "refusal")
    print(f"{len(done)} tasks probed; refused: {ref}")


if __name__ == "__main__":
    main()
