"""Arguments of the accepted subagent_fork calls: what differs between the forks that got a copy of the parent's history and the rest."""
import collections
import csv
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, "judge-env/scripts")
import run_metrics as rm  # noqa: E402

calls = [r for r in csv.DictReader(open("results/master/raw/p2-main.spawn_calls.csv", encoding="utf-8")) if r["tool"] == "subagent_fork" and r["child"]]
by_run = collections.defaultdict(list)
for r in calls:
    by_run[r["id"]].append(r)
tab = collections.Counter()
for run, rs in sorted(by_run.items()):
    logs, sessions = rm.load_sessions(Path("results/runs/p2-main") / run)
    seeded = {rm.norm_id((g["header"] or {}).get("id")): bool((g["header"] or {}).get("isSeeded")) for g in logs if g["header"]}
    for s in sessions:
        for cid in s["call_order"]:
            c = s["calls"][cid]
            if c["name"] != "subagent_fork":
                continue
            res = s["results"].get(cid) or {}
            m = rm.STARTED_RE.search(res.get("text") or "")
            if not m:
                continue
            a = c["args"] if isinstance(c["args"], dict) else {}
            child = rm.norm_id(m.group(1))
            extra = {k: v for k, v in a.items() if k not in ("task", "prompt", "description", "label", "message")}
            tab[("seeded" if seeded.get(child) else "not seeded", "caller depth %d" % s["depth"], "args: " + ",".join(sorted(a)), "extra: " + str(extra)[:90])] += 1
for k, v in sorted(tab.items(), key=lambda kv: -kv[1]):
    print(v, k)
