"""The runs with forked agents: per run the over-count, and a check of the cut rule (everything before the first
session/end-seed of a seeded log is a copy of the parent's log; nothing after it is)."""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, "judge-env/scripts")
import run_metrics as rm  # noqa: E402

rows = [r for r in json.load(open("analysis-dev/fork-inflation-p2.json")) if r.get("forks")]
for r in rows:
    print(r["run"], r["batch"], r["group"], r["task"], "forks", r["forks"], "| cost", r["cost_now"], "->", r["cost_own"], "| calls", r["calls_now"], "->", r["calls_own"],
          "| search", r["search_now"], "->", r["search_own"], "| fetch", r["fetch_now"], "->", r["fetch_own"], "| search requests", r["aux_now"], "->", r["aux_own"])
    logs, _ = rm.load_sessions(Path("results/runs") / r["batch"] / r["run"])
    by = {rm.norm_id((g["header"] or {}).get("id")): g for g in logs if g["header"]}
    for g in logs:
        h = g["header"] or {}
        if not h.get("isSeeded"):
            continue
        ev = g["events"]
        marks = [i for i, e in enumerate(ev) if e.get("type") == "session/end-seed"]
        cut = marks[0] if marks else 0
        parent = by.get(rm.norm_id(h.get("parentSession")))
        pcalls = {e["data"].get("callId") for e in parent["events"] if e.get("type") == "tool/call"} if parent else set()
        before = [e["data"].get("callId") for e in ev[:cut] if e.get("type") == "tool/call"]
        after = [e["data"].get("callId") for e in ev[cut:] if e.get("type") == "tool/call"]
        own_spawn = [e["data"].get("name") for e in ev[cut:] if e.get("type") == "tool/call" and e["data"].get("name") in ("subagent", "subagent_fork", "send_message")]
        print("   fork", str(h.get("id"))[-36:][:8], "depth", h.get("delegationDepth"), "parent seeded:", bool((parent or {}).get("header", {}).get("isSeeded")) if parent else None,
              "| end-seed markers", len(marks), "| calls before cut", len(before), "all in parent:", all(c in pcalls for c in before),
              "| calls after cut", len(after), "any in parent:", any(c in pcalls for c in after), "| own spawn/message calls", len(own_spawn))
