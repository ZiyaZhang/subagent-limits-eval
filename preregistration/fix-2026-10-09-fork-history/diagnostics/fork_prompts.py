# -*- coding: utf-8 -*-
"""The prompts of forks that started without the parent's context: how long they are, and how many lean on the conversation."""
import collections
import csv
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, "judge-env/scripts")
import run_metrics as rm  # noqa: E402

calls = [r for r in csv.DictReader(open("results/master/raw/p2-main.spawn_calls.csv", encoding="utf-8")) if r["tool"] == "subagent_fork" and r["child"]]
runs = sorted(set(r["id"] for r in calls))
LEAN = re.compile(r"this conversation|in the conversation|conversation above|as (described|discussed|outlined|specified) (above|earlier|before)|described above|see above|"
                  r"the (original|user'?s) (task|brief|request|question) (above|earlier)|you (already )?(have|know|saw|see) the|context above|earlier in this|"
                  "上文|上述|如前|前文|本对话|对话中|刚才|之前的对话|你已经看到|你已知", re.I)
rows = []
for run in runs:
    logs, sessions = rm.load_sessions(Path("results/runs/p2-main") / run)
    seeded = {rm.norm_id((g["header"] or {}).get("id")): bool((g["header"] or {}).get("isSeeded")) for g in logs if g["header"]}
    for s in sessions:
        root_first = None
        for cid in s["call_order"]:
            c = s["calls"][cid]
            if c["name"] not in ("subagent_fork", "subagent"):
                continue
            res = s["results"].get(cid) or {}
            m = rm.STARTED_RE.search(res.get("text") or "")
            if not m:
                continue
            a = c["args"] if isinstance(c["args"], dict) else {}
            rows.append({"run": run, "tool": c["name"], "seeded": seeded.get(rm.norm_id(m.group(1))), "depth": s["depth"], "chars": len(str(a.get("prompt") or "")),
                         "lean": bool(LEAN.search(str(a.get("prompt") or ""))), "prompt": " ".join(str(a.get("prompt") or "").split())})
fk = [r for r in rows if r["tool"] == "subagent_fork"]
med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
for name, sel in (("fork, no copy", [r for r in fk if not r["seeded"]]), ("fork, with copy", [r for r in fk if r["seeded"]]), ("ordinary subagent calls of the same runs", [r for r in rows if r["tool"] == "subagent"])):
    print(f"{name}: {len(sel)} calls; prompt chars median {med([r['chars'] for r in sel])}, min {min((r['chars'] for r in sel), default=None)}; prompts with a phrase that points at the conversation: {sum(r['lean'] for r in sel)}")
print("examples of fork prompts without a copy that point at the conversation:")
for r in [r for r in fk if not r["seeded"] and r["lean"]][:6]:
    m = LEAN.search(r["prompt"])
    print("  ", r["run"], "depth", r["depth"], "chars", r["chars"], "| ...", r["prompt"][max(0, m.start() - 110):m.end() + 60])
short = sorted([r for r in fk if not r["seeded"]], key=lambda r: r["chars"])[:4]
print("shortest fork prompts without a copy:")
for r in short:
    print("  ", r["run"], "chars", r["chars"], "|", r["prompt"][:260])
