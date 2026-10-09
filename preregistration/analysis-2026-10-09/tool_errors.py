#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Failed web searches and page fetches per run (balance check of the search route; protocol v5.1 sections 五 and 七).

Per run, over every session: web_search calls and how many returned an error, the same for web_fetch, and the kind
of each search error (HTTP status when the message has one, else its first words). Names no outcome of the experiment.

Usage: tool_errors.py results/runs/<batch> --out results/analysis-<batch>-toolerrors.json [--jobs 16]
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
HTTP = re.compile(r"HTTP (\d{3})")


def one(run_dir: str) -> dict:
    import run_metrics as rm
    d = Path(run_dir)
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    out = {"id": res.get("id") or d.name, "task": res.get("task"), "group": res.get("group"), "rep": res.get("rep"), "started_utc": res.get("started_utc"),
           "web_search": 0, "web_search_error": 0, "web_fetch": 0, "web_fetch_error": 0, "search_error_kinds": {}, "first_error_text": ""}
    kinds = collections.Counter()
    try:
        _, sessions = rm.load_sessions(d)
    except Exception as exc:  # noqa: BLE001
        out["note"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        return out
    for s in sessions:
        for cid in s["call_order"]:
            name = s["calls"][cid]["name"]
            if name not in ("web_search", "web_fetch"):
                continue
            r = s["results"].get(cid)
            out[name] += 1
            if r is None:
                continue
            text = r["text"] or ""
            if r["is_error"] or text.lstrip().startswith("Error"):
                out[name + "_error"] += 1
                if name == "web_search":
                    m = HTTP.search(text)
                    kinds["HTTP " + m.group(1) if m else " ".join(text.split()[:6])[:60]] += 1
                    out["first_error_text"] = out["first_error_text"] or " ".join(text.split())[:240]
    out["search_error_kinds"] = dict(kinds)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    runs = sorted(str(p.parent) for p in a.batch.glob("*/result.json"))
    with cf.ProcessPoolExecutor(max_workers=a.jobs) as ex:
        rows = list(ex.map(one, runs, chunksize=4))
    a.out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    s, se = sum(r["web_search"] for r in rows), sum(r["web_search_error"] for r in rows)
    f, fe = sum(r["web_fetch"] for r in rows), sum(r["web_fetch_error"] for r in rows)
    kinds = collections.Counter()
    for r in rows:
        kinds.update(r["search_error_kinds"])
    print(f"{len(rows)} runs; web_search {s} calls, {se} errors ({100 * se / max(s, 1):.1f}%); web_fetch {f} calls, {fe} errors ({100 * fe / max(f, 1):.1f}%); "
          f"runs with a search error {sum(r['web_search_error'] > 0 for r in rows)}; search error kinds {dict(kinds.most_common(6))}")
    by_hour = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        h = (r.get("started_utc") or "")[5:13]
        by_hour[h][0] += r["web_search"]
        by_hour[h][1] += r["web_search_error"]
    print("search error rate by start hour (UTC): " + "  ".join(f"{h} {100 * e / max(n, 1):.0f}%" for h, (n, e) in sorted(by_hour.items())))
    by_group = collections.defaultdict(lambda: [0, 0, 0])
    for r in rows:
        by_group[r["group"]][0] += r["web_search"]
        by_group[r["group"]][1] += r["web_search_error"]
        by_group[r["group"]][2] += 1
    print("search error rate by group: " + "  ".join(f"{g} {100 * e / max(n, 1):.1f}%" for g, (n, e, _) in sorted(by_group.items())))


if __name__ == "__main__":
    main()
