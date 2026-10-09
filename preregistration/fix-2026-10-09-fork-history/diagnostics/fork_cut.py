"""Event types around the end of the copied history in each forked log of the three runs."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, "judge-env/scripts")
import run_metrics as rm  # noqa: E402

for run in ("844gcwcw22", "vj1vzxympf", "x677n9f24r"):
    logs, _ = rm.load_sessions(Path("results/runs/p2-main") / run)
    for g in logs:
        h = g["header"] or {}
        if not h.get("isSeeded"):
            continue
        ev = g["events"]
        cut = next(i for i, e in enumerate(ev) if e.get("type") == "session/end-seed")
        desc = [i for i, e in enumerate(ev) if e.get("type") == "subagent/descriptor"]
        sysm = [i for i, e in enumerate(ev) if e.get("type") == "system/message"]
        reqh = [i for i, e in enumerate(ev) if e.get("type") == "request/header"]
        print(run, str(h.get("id"))[-36:][:8], "cut", cut, "of", len(ev), "| descriptor at", desc, "| system/message at", sysm[:3], "| request/header at", reqh[:2], reqh[-1:] if reqh else "")
        print("    around the cut:", [e.get("type") for e in ev[cut - 2:cut + 7]])
        e = ev[cut]
        print("    end-seed event:", {k: (v if k != "data" else v) for k, v in e.items()} if len(str(e)) < 300 else str(e)[:300])
    print()
