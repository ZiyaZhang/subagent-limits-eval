#!/usr/bin/env python3
"""Pages a run downloaded to its workspace with its own scripts (curl / python loops over a list of URLs).

search_overlap.py counts the pages opened with web_fetch and the URLs written out in shell commands. A run that is
told to open hundreds of pages instead writes a crawler: the URLs sit in a file or are harvested by the script, and the
pages are saved under the workspace. Those pages are counted here from the files they left behind (added 2026-10-07,
before the main batch of the two-dose experiment):

  saved_files   files under the workspace outside library folders, not scripts, not the deliverable, at least 500 bytes
  saved_pages   distinct file stems among them (page-0001.html and page-0001.txt are one page), counted only in
                folders that hold at least 10 such files (a folder of downloaded pages, not a handful of notes)
  saved_mb      their size

A lower bound of what was downloaded (pages fetched and not saved are not seen) and an upper bound of what was read:
a page saved to disk enters the model's context only through what the model greps or reads out of it.

Usage (experiment dir on the dev box): pages_saved.py --batches office-floor,office-confirm --out results/analysis-pages-saved/saved.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

SKIP_DIRS = ("pylibs", ".pylibs", "__pycache__", "site-packages", "node_modules", ".git", "dist-info")
SKIP_EXT = (".py", ".sh", ".pyc", ".js", ".log", ".lock", ".csv.tmp")
DELIVERABLES = ("singapore.md", "report.md")


def scan_listing(listing: Path) -> dict:
    """Same counts from the v6.1 read-back listing (.ws-listing: sha256 \t size \t path of every changed workspace
    file, copied or not); used when the run was collected by dsec_matrix v6.1, whose workspace copy is size-capped."""
    per_dir = {}
    for line in listing.read_text(encoding="utf-8", errors="replace").split("\n"):
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        size, path = int(parts[1] or 0), parts[2]
        rel, f = (os.path.split(path) if "/" in path else (".", path))
        rel = rel or "."
        if any(s in rel for s in SKIP_DIRS) or f.lower().endswith(SKIP_EXT) or (rel == "." and f in DELIVERABLES) or size < 500:
            continue
        per_dir.setdefault(rel, []).append((os.path.splitext(f)[0], size))
    files = sum(len(v) for v in per_dir.values())
    stems, mb = set(), 0.0
    for rel, v in per_dir.items():
        if len(v) >= 10:
            stems |= {s for s, _ in v}
            mb += sum(sz for _, sz in v) / 1e6
    return {"saved_files": files, "saved_pages": len(stems), "saved_mb": round(mb, 1), "largest_dir": max((len(v) for v in per_dir.values()), default=0), "from_listing": 1}


def scan(ws: Path) -> dict:
    per_dir = {}
    for root, dirs, files in os.walk(ws):
        if any(s in root for s in SKIP_DIRS):
            continue
        rel = os.path.relpath(root, ws)
        for f in files:
            if f.lower().endswith(SKIP_EXT) or (rel == "." and f in DELIVERABLES):
                continue
            p = os.path.join(root, f)
            try:
                size = os.path.getsize(p)
            except OSError:
                continue
            if size < 500:
                continue
            per_dir.setdefault(rel, []).append((os.path.splitext(f)[0], size))
    files = sum(len(v) for v in per_dir.values())
    stems, mb = set(), 0.0
    for rel, v in per_dir.items():
        if len(v) >= 10:
            stems |= {s for s, _ in v}
            mb += sum(sz for _, sz in v) / 1e6
    return {"saved_files": files, "saved_pages": len(stems), "saved_mb": round(mb, 1), "largest_dir": max((len(v) for v in per_dir.values()), default=0)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batches", required=True)
    ap.add_argument("--runs", default="results/runs")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rows = []
    for b in a.batches.split(","):
        for rd in sorted(Path(a.runs, b).glob("*/")):
            rj = rd / "result.json"
            if not rj.exists():
                continue
            res = json.loads(rj.read_text(encoding="utf-8"))
            rows.append({"batch": b, "id": res.get("id", rd.name), "task": res.get("task"), "group": res.get("group"), "rep": res.get("rep"), **(scan_listing(rd / ".ws-listing") if (rd / ".ws-listing").exists() else scan(rd / "workspace"))})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    import collections
    import statistics as st
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["batch"], r["group"])].append(r)
    for (b, g), v in sorted(by.items()):
        sp = sorted(r["saved_pages"] for r in v)
        print(f"{b:20s} {g:10s} runs {len(v):3d}  saved pages: mean {st.mean(sp):6.1f} median {st.median(sp):6.1f} max {sp[-1]:5d}  runs with 50+ {sum(1 for x in sp if x >= 50):3d}  files mean {st.mean(r['saved_files'] for r in v):6.1f}")


if __name__ == "__main__":
    main()
