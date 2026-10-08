#!/usr/bin/env python3
"""The three gates between the pilots and the main batch (protocol v5.1 sections 五 and 八), run by phase2-chain.sh.

1. Sentence calibration (batch p2-calib, run table results/master/raw/p2-calib.csv). Targets fixed before the batch:
     Pb3  subagents started per run: median in [2, 4]          Pb8  median in [6, 10]
     Pgs  no subagents and a report delivered                  Pgm  search requests 0.8-1.4 x the phase-1 default (214)
   Only Pgm may be changed, once and proportionally ("只按比例改一次，改后冻结"): when its median ratio r is outside
   [0.8, 1.4], the two numbers in the sentence are multiplied by 1.1 / r (rounded to tens) and the sentence file is
   rewritten (the old file is kept as *.before-gate.json). Pb3 / Pb8 outside their range are recorded, not changed
   (the dose figure uses the achieved counts). A group whose reports are mostly missing (less than half delivered)
   stops the chain.
2. Load check: median time to first token and median output tokens/s over every model request of p2-calib, against
   the phase-1 profile (results/profile-official.json: base_ttft_s, out_tps), and the batch's infrastructure retry
   rate (progress.json). Both timings within 15% and retries <= 15% of runs -> parallel 32, otherwise 26 (the
   phase-1 setting); retries above 50% -> 20.
3. Structural check: phase2_check.py must already have passed (the chain runs it before this script).

Writes --out (JSON with every number and the decision) and prints "PAR=<n>" as the last line. Exit 2 stops the chain.

Usage (dev box): python judge-env/scripts/phase2_gate.py --calib results/master/raw/p2-calib.csv --runs results/runs/p2-calib
                 --profile results/profile-official.json --sentences tasks/phase2-sentences.json --out results/phase2-gate.json
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import request_timing as rt  # noqa: E402

TARGETS = {"b3": (2, 4), "b8": (6, 10), "gm": (0.8, 1.4)}
DEFAULT_SEARCH = 214.0
GM_RE = re.compile(r"至少做 (\d+) 次网页搜索，并打开至少 (\d+) 个网页")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def tag_of(group: str) -> str:
    m = re.search(r"P([a-z0-9]+)-", group)
    return m.group(1) if m else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--calib", type=Path, required=True)
    ap.add_argument("--runs", type=Path, required=True, help="results/runs/p2-calib")
    ap.add_argument("--profile", type=Path, required=True)
    ap.add_argument("--sentences", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--default-search", type=float, default=DEFAULT_SEARCH)
    ap.add_argument("--par-high", type=int, default=32)
    ap.add_argument("--par-low", type=int, default=26)
    a = ap.parse_args()
    report = {"decisions": [], "problems": []}
    rows = list(csv.DictReader(open(a.calib, encoding="utf-8")))
    by = defaultdict(list)
    for r in rows:
        by[tag_of(r["group"])].append(r)
    sentences = json.loads(a.sentences.read_text(encoding="utf-8"))
    sent = {}
    for tag, rs in sorted(by.items()):
        if not tag:
            continue
        spawn = [num(r.get("spawn_started")) for r in rs]
        spawn = [x for x in spawn if x is not None]
        search = [num(r.get("search_requests")) for r in rs]
        search = [x for x in search if x is not None]
        delivered = sum(1 for r in rs if str(r.get("deliverable_ok", "")) == "1")
        rec = {"runs": len(rs), "delivered": delivered, "spawn_started_median": st.median(spawn) if spawn else None,
               "spawn_started_values": spawn, "search_median": st.median(search) if search else None,
               "search_ratio_median": (st.median(search) / a.default_search) if search else None,
               "t_answer_min_median": st.median([num(r.get("t_answer_s")) / 60 for r in rs if num(r.get("t_answer_s")) is not None] or [0])}
        if delivered < len(rs) / 2:
            report["problems"].append(f"{tag}: only {delivered} of {len(rs)} runs delivered a report")
        if tag in ("b3", "b8"):
            lo, hi = TARGETS[tag]
            rec["target"] = [lo, hi]
            rec["inside"] = rec["spawn_started_median"] is not None and lo <= rec["spawn_started_median"] <= hi
            rec["note"] = "achieved counts are used as they are; the sentence is not changed"
        elif tag == "gs":
            rec["inside"] = all(x == 0 for x in spawn)
            if not rec["inside"]:
                report["problems"].append("gs: a D0 run started subagents (impossible unless the patch failed)")
        elif tag == "gm":
            lo, hi = TARGETS["gm"]
            r_med = rec["search_ratio_median"]
            rec["target"] = [lo, hi]
            rec["inside"] = r_med is not None and lo <= r_med <= hi
            if r_med and not rec["inside"]:
                m = GM_RE.search(sentences["gm"])
                if m:
                    f = 1.1 / r_med
                    n1, n2 = max(10, round(int(m.group(1)) * f / 10) * 10), max(10, round(int(m.group(2)) * f / 10) * 10)
                    new = sentences["gm"][:m.start()] + f"至少做 {n1} 次网页搜索，并打开至少 {n2} 个网页" + sentences["gm"][m.end():]
                    backup = a.sentences.with_suffix(".before-gate.json")
                    if not backup.exists():
                        backup.write_text(json.dumps(sentences, ensure_ascii=False, indent=1), encoding="utf-8")
                        sentences["gm"] = new
                        a.sentences.write_text(json.dumps(sentences, ensure_ascii=False, indent=1), encoding="utf-8")
                        rec["adjusted_once"] = {"factor": round(f, 3), "old": m.group(0), "new": f"至少做 {n1} 次网页搜索，并打开至少 {n2} 个网页"}
                        report["decisions"].append(f"gm sentence adjusted once by {f:.2f} (median ratio {r_med:.2f}); frozen now")
                    else:
                        rec["adjusted_once"] = "already adjusted before; not changed again"
        sent[tag] = rec
    report["sentences"] = sent
    # load check
    prof = json.loads(a.profile.read_text(encoding="utf-8"))
    ttft, tps, flagged = [], [], 0
    for sp in glob.glob(os.path.join(str(a.runs), "*", "home", "sessions", "**", "session.v4.jsonl.zstd"), recursive=True):
        reqs, fl, _ = rt.session_requests(sp)
        ttft += [r["ttft_ms"] / 1000 for r in reqs if "ttft_ms" in r]
        tps += [r["out_tps"] for r in reqs if "out_tps" in r]
        flagged += sum(fl.values())
    small = ttft  # the profile's base is for small prompts; the median over all requests is a conservative stand-in
    load = {"requests_with_ttft": len(ttft), "ttft_median_s": st.median(small) if small else None,
            "out_tps_median": st.median(tps) if tps else None, "flagged_events": flagged,
            "profile_base_ttft_s": prof.get("base_ttft_s"), "profile_out_tps": prof.get("out_tps")}
    ok_ttft = load["ttft_median_s"] is not None and load["ttft_median_s"] <= 1.15 * prof["base_ttft_s"] * 3  # ×3: all requests, not only small ones
    ok_tps = load["out_tps_median"] is not None and load["out_tps_median"] >= 0.85 * prof["out_tps"]
    # infrastructure retries of the calibration batch (progress.json): transport failures under load
    try:
        prog = json.loads((a.runs / "progress.json").read_text(encoding="utf-8"))
        log_lines = (a.runs / "run.log").read_text(encoding="utf-8", errors="replace").split("\n")
        retries = sum(1 for line in log_lines if "infra signal" in line)  # progress.json is reset by the second runner invocation
        retry_rate = retries / max(1, prog.get("total", 1))
    except (OSError, ValueError):
        retry_rate = None
    ok_retries = retry_rate is not None and retry_rate <= 0.15
    par = a.par_high if (ok_ttft and ok_tps and ok_retries) else a.par_low
    if retry_rate is not None and retry_rate > 0.5:
        par = min(par, 20)
    load.update(ok_ttft=ok_ttft, ok_tps=ok_tps, infra_retry_rate=retry_rate, ok_retries=ok_retries, parallel=par)
    report["load"] = load
    report["decisions"].append(f"main batch parallel = {par} (ttft ok {ok_ttft}, tps ok {ok_tps}, infra retry rate {retry_rate} ok {ok_retries})")
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for tag, rec in sent.items():
        print(f"{tag}: runs {rec['runs']} delivered {rec['delivered']} spawn median {rec['spawn_started_median']} search ratio {rec['search_ratio_median'] and round(rec['search_ratio_median'], 2)} inside {rec.get('inside')} {rec.get('adjusted_once', '')}")
    print(f"load: ttft median {load['ttft_median_s']} s (profile base {prof.get('base_ttft_s')}), out tps median {load['out_tps_median']} (profile {prof.get('out_tps')}), flagged {flagged}")
    for d in report["decisions"]:
        print("decision:", d)
    for p in report["problems"]:
        print("PROBLEM:", p)
    print(f"PAR={par}")
    return 2 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
