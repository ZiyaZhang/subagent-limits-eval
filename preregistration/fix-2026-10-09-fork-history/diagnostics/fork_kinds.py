"""Every accepted subagent_fork call of the main batch: is the child's log seeded, what does its header say, how does it start."""
import collections
import csv
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, "judge-env/scripts")
import run_metrics as rm  # noqa: E402

calls = [r for r in csv.DictReader(open("results/master/raw/p2-main.spawn_calls.csv", encoding="utf-8")) if r["tool"] == "subagent_fork" and r["child"]]
by_run = collections.defaultdict(list)
for r in calls:
    by_run[r["id"]].append(r)
kinds = collections.Counter()
shown = 0
for run, rs in sorted(by_run.items()):
    logs, sessions = rm.load_sessions(Path("results/runs/p2-main") / run)
    by = {rm.norm_id((g["header"] or {}).get("id")): g for g in logs if g["header"]}
    for r in rs:
        g = by.get(rm.norm_id(r["child"]))
        if g is None:
            kinds[("no log for the child", r["run_in_background"])] += 1
            continue
        h = g["header"]
        first = [e.get("type") for e in g["events"][:6]]
        desc = next((e.get("data") for e in g["events"] if e.get("type") == "subagent/descriptor"), {}) or {}
        key = ("seeded" if h.get("isSeeded") else "not seeded", "inherited %s" % ("yes" if g.get("inherited") else "no"), "bg=" + str(r["run_in_background"]),
               "mode=" + str(desc.get("mode")), "provider=" + str(desc.get("provider")))
        kinds[key] += 1
        if not h.get("isSeeded") and shown < 3:
            shown += 1
            print(run, r["child"][:8], "header:", {k: (v if k != "cwd" else "...") for k, v in h.items()})
            print("    first events:", first, "| events", len(g["events"]), "| descriptor:", {k: desc.get(k) for k in list(desc)[:8]})
            users = [e for e in g["events"] if e.get("type") == "user/message"][:1]
            for u in users:
                print("    first user message source:", (u.get("data") or {}).get("source"), "| text:", " ".join(str((u.get("data") or {}).get("content"))[:200].split()))
            req = next((e for e in g["events"] if e.get("type") == "request/header"), None)
            a0 = next((e for e in g["events"] if e.get("type") == "assistant/message"), None)
            if a0:
                print("    first reply usage:", (a0.get("data") or {}).get("usage"))
for k, v in kinds.most_common():
    print(v, k)
