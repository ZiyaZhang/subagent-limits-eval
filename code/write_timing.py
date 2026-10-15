#!/usr/bin/env python3
"""When was the work done? Per-run timing of file writes and of the delegation waves, for the exercise-set tasks.

For every run of a batch (dsec_matrix layout) all persisted session logs are read (root and subagents) and, with
t0 = the first event of the run:
  first_write_s      first write/edit of an exercise's implementation file by any agent
  all_written_s      the moment every exercise had been written at least once (None if some never were)
  last_write_s       the last write/edit of any exercise implementation file
  answer_s           end of the root's last turn (the time the user waits; same definition as controls_rows.py)
  after_last_write_s answer_s - last_write_s: review and waiting after the last change to the deliverable
Delegation: subagents by wave (a wave = subagents started within 60 s of each other), how many started after
all_written_s, each subagent's duration, requests, output tokens, exercises it wrote; exercises written by more
than one agent; subagents whose last turn was aborted.

Writes are the tool calls `write` and `edit` whose file_path is exercises/<name>/<file>.py and not a test file, plus
bash commands that write such a file (redirect, tee, sed -i, cp, mv); the latter are also counted in bash_writes.

Usage: write_timing.py BATCH_DIR [BATCH_DIR ...] --out OUT.json [--csv OUT.csv] [--task pw-exercises-free]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics as st
import subprocess
import sys
from pathlib import Path

EX = re.compile(r"(?:^|/)exercises/([^/]+)/([^/]+\.py)$")
BASH_TARGET = re.compile(r"""(?:>>?\s*|\btee\s+(?:-a\s+)?|\bcp\s+(?:-\S+\s+)*\S+\s+|\bmv\s+(?:-\S+\s+)*\S+\s+)["']?([^\s"'|;&<>()]+)"""
                         r"""|open\(\s*["']([^"']+)["']\s*,\s*["'][wax]"""
                         r"""|Path\(\s*["']([^"']+)["']\s*\)\s*\.\s*write_(?:text|bytes)""")
BASH_WRITE = re.compile(r"(?:>\s*|tee\s+|sed\s+-i[^|;&]*\s|cp\s+\S+\s+|mv\s+\S+\s+)(?:\S*/)?exercises/([a-z0-9-]+)/(?!\S*_test)\S*\.py")
# Other tasks: --file-regex names the deliverable files (group 1 = the unit that counts as "written"), --units how many
# units a complete deliverable has. Examples:
#   toolkit tasks   --file-regex '(?:^|/)workspace/(toolkit/.+\.py)$' --units 16
#   plugin task     --file-regex '(?:^|/)workspace/(token-cost/.+)$' --units 3
#   one report file --file-regex '(?:^|/)workspace/(answer\.md)$' --units 1
CUSTOM = None
UNITS = 24


def read_session(path: Path) -> list:
    if path.name.endswith(".zstd"):
        raw = subprocess.run(["zstd", "-dc", str(path)], capture_output=True, check=False).stdout
    else:
        raw = path.read_bytes()
    out = []
    for line in raw.splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def analyse(run: Path) -> dict | None:
    try:
        res = json.loads((run / "result.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    sessions = []
    for p in sorted(set((run / "home" / "sessions").rglob("session*.jsonl")) | set((run / "home" / "sessions").rglob("session*.jsonl.zstd"))):
        ev = read_session(p)
        if not ev:
            continue
        head = ev[0] if ev[0].get("type", "session") == "session" else {}
        hd = head.get("data") or head
        times = [e["time"] for e in ev if isinstance(e.get("time"), (int, float))]
        if not times:
            continue
        turn_ends = [(e["time"], ((e.get("data") or {}).get("reason") or {})) for e in ev if e.get("type") == "turn/end"]
        writes, bash_w, reqs, out_tok = [], 0, 0, 0
        for e in ev:
            d = e.get("data") or {}
            if e.get("type") == "tool/call":
                try:
                    args = json.loads(d.get("arguments") or "{}")
                except ValueError:
                    args = {}
                if d.get("name") in ("write", "edit"):
                    path = str(args.get("file_path") or args.get("path") or "")
                    if CUSTOM is not None:
                        m = CUSTOM.search(path)
                        if not m and path and not path.startswith("/"):  # relative to the workspace
                            m = CUSTOM.search("workspace/" + path.removeprefix("./"))
                        if m:
                            writes.append((e["time"], m.group(1)))
                    else:
                        m = EX.search(path)
                        if m and not m.group(2).endswith("_test.py"):
                            writes.append((e["time"], m.group(1)))
                elif d.get("name") == "bash" and CUSTOM is None:
                    for m in BASH_WRITE.finditer(str(args.get("command") or "")):
                        bash_w += 1
                        writes.append((e["time"], m.group(1)))
                elif d.get("name") == "bash":
                    # other tasks: files written from the shell (redirects, tee, cp, mv, open(..., "w"), write_text)
                    for m in BASH_TARGET.finditer(str(args.get("command") or "")):
                        path = next(g for g in m.groups() if g)
                        hit = CUSTOM.search(path) or (None if path.startswith("/") else CUSTOM.search("workspace/" + path.removeprefix("./")))
                        if hit:
                            bash_w += 1
                            writes.append((e["time"], hit.group(1)))
            elif e.get("type") == "assistant/message":
                reqs += 1
                out_tok += int((d.get("usage") or {}).get("outputTokens") or 0)
        label = next(((e.get("data") or {}).get("label") or "" for e in ev[:20] if e.get("type") == "subagent/descriptor"), "")
        sessions.append({"id": hd.get("id") or p.parent.name, "parent": hd.get("parentSession"), "label": label,
                         "depth": hd.get("delegationDepth", 0) or 0, "first": min(times), "last": max(times),
                         "turn_ends": turn_ends, "writes": writes, "bash_writes": bash_w, "requests": reqs, "out_tokens": out_tok})
    if not sessions:
        return None
    t0 = min(s["first"] for s in sessions)
    roots = [s for s in sessions if not s["parent"]]
    root = min(roots, key=lambda s: s["first"]) if roots else None
    kids = sorted((s for s in sessions if s["parent"]), key=lambda s: s["first"])
    sec = lambda t: round((t - t0) / 1000, 1)  # noqa: E731
    all_writes = sorted((t, ex, s["id"]) for s in sessions for t, ex in s["writes"])
    first, last, writers = {}, {}, {}
    for t, ex, sid in all_writes:
        first.setdefault(ex, t)
        last[ex] = t
        writers.setdefault(ex, set()).add(sid)
    n_ex = UNITS
    answer = sec(max(t for t, _ in root["turn_ends"])) if root and root["turn_ends"] else None
    all_written = sec(max(first.values())) if len(first) >= n_ex else None
    last_write = sec(max(last.values())) if last else None
    waves, cur = [], []
    for k in kids:
        if cur and k["first"] - cur[-1]["first"] > 60_000:
            waves.append(cur)
            cur = []
        cur.append(k)
    if cur:
        waves.append(cur)
    kid_rows = []
    for k in kids:
        end = max((t for t, _ in k["turn_ends"]), default=k["last"])
        kid_rows.append({"start_s": sec(k["first"]), "end_s": sec(end), "minutes": round((end - k["first"]) / 60000, 1), "depth": k["depth"],
                         "requests": k["requests"], "out_tokens": k["out_tokens"], "exercises": len({ex for _, ex in k["writes"]}),
                         "writes": len(k["writes"]), "label": k["label"],
                         "aborted": bool(k["turn_ends"] and (k["turn_ends"][-1][1] or {}).get("kind") == "aborted"),
                         "no_turn_end": not k["turn_ends"]})
    late = [k for k in kid_rows if all_written is not None and k["start_s"] > all_written]
    return {"id": run.name, "task": res.get("task"), "group": res.get("group"), "rep": res.get("rep"), "exit": res.get("exit"),
            "seconds": res.get("seconds"), "answer_s": answer, "first_write_s": sec(all_writes[0][0]) if all_writes else None,
            "exercises_written": len(first), "all_written_s": all_written, "last_write_s": last_write,
            "after_last_write_s": round(answer - last_write, 1) if answer is not None and last_write is not None else None,
            "after_all_written_s": round(answer - all_written, 1) if answer is not None and all_written is not None else None,
            "root_turns": len(root["turn_ends"]) if root else None, "root_writes": len(root["writes"]) if root else None,
            "root_exercises": len({ex for _, ex in root["writes"]}) if root else None,
            "children": len(kids), "waves": [len(w) for w in waves], "wave_starts_s": [sec(w[0]["first"]) for w in waves],
            "children_after_all_written": len(late), "child_minutes_median": st.median(k["minutes"] for k in kid_rows) if kid_rows else None,
            "child_minutes_max": max((k["minutes"] for k in kid_rows), default=None),
            "exercises_with_2plus_writers": sum(1 for v in writers.values() if len(v) > 1),
            "aborted_children": sum(k["aborted"] for k in kid_rows), "children_without_turn_end": sum(k["no_turn_end"] for k in kid_rows),
            "bash_writes": sum(s["bash_writes"] for s in sessions), "out_tokens": sum(s["out_tokens"] for s in sessions),
            "requests": sum(s["requests"] for s in sessions), "kids": kid_rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batches", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--task")
    ap.add_argument("--file-regex", help="deliverable files of another task; group 1 is the unit")
    ap.add_argument("--units", type=int, default=24, help="units of a complete deliverable (default: the 24 exercises)")
    a = ap.parse_args()
    global CUSTOM, UNITS
    CUSTOM = re.compile(a.file_regex) if a.file_regex else None
    UNITS = a.units
    rows = []
    for b in a.batches:
        for run in sorted(p for p in b.iterdir() if p.is_dir() and not p.name.startswith("_") and (p / "result.json").exists()):
            r = analyse(run)
            if r and (not a.task or r["task"] == a.task):
                r["batch"] = b.name
                rows.append(r)
    a.out.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    if a.csv:
        cols = [k for k in rows[0] if k != "kids"]
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({k: (json.dumps(r[k]) if isinstance(r[k], list) else r[k]) for k in cols})
    by = {}
    for r in rows:
        by.setdefault(r["group"], []).append(r)
    med = lambda v: st.median(v) / 60 if v else float("nan")  # noqa: E731
    print("group runs | answer med | all-written med (n) | last-write med | after-last-write med | kids | late kids | 2+writers | root turns")
    for g, v in sorted(by.items()):
        aw = [r["all_written_s"] for r in v if r["all_written_s"] is not None]
        print(f"{g:12s} {len(v):3d} | {med([r['answer_s'] for r in v if r['answer_s'] is not None]):5.1f} | {med(aw):5.1f} ({len(aw)}) | "
              f"{med([r['last_write_s'] for r in v if r['last_write_s'] is not None]):5.1f} | "
              f"{med([r['after_last_write_s'] for r in v if r['after_last_write_s'] is not None]):5.1f} | "
              f"{st.mean(r['children'] for r in v):4.1f} | {st.mean(r['children_after_all_written'] for r in v):4.1f} | "
              f"{st.mean(r['exercises_with_2plus_writers'] for r in v):4.1f} | {st.mean(r['root_turns'] or 0 for r in v):3.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
