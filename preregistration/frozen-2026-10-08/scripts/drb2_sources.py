#!/usr/bin/env python3
"""DeepResearch Bench II runs: did a run use what it must not use? (plan: 补强计划 第 6 步; rule revised after the trial,
plan: 第 6 步的执行记录（一）)

Per run directory of a batch, over the root session and every subagent session:
  names    a log names the benchmark itself (DeepResearch Bench, its repository, its rubric file, its site). The task
           text never does, so an occurrence comes from the web or from the model's own notes.
  source   a tool call fetches one of the task's blocked URLs AND the fetched content reaches the model:
             web_fetch on that URL with a non-empty, non-error result, or
             a shell command in which the fetching program (curl, wget, python requests ...) and the URL are in the
             same simple command, unless the download goes to a file that is never read afterwards.
  unread   a blocked URL downloaded to a file that no later command of that session reads before it is removed or
           overwritten (seen in the trial: the main agent used the banned PDF's address to test curl, noticed, and
           deleted the file). Listed, not flagged.
  mention  a shell command that fetches something and merely contains a blocked URL elsewhere (seen in the trial: a
           filter script with the ban list). Listed, not flagged.
The block list itself is in the task prompt and is repeated in messages between agents, so occurrences outside tool
calls never count. A run with a "names" or "source" hit is flagged (n_hits > 0, the field ws_stats.py reads) and is
not scored in the main analysis.

Usage (dev box): python drb2_sources.py results/runs/<batch> --index tasks/drb2-index.json [--out FILE.json]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_metrics as rm  # noqa: E402

NAMES = re.compile(r"deep\s?research[\s_-]?bench|\bDRB[\s-]?II\b|tasks_and_rubrics|agentresearchlab|muset-ai", re.I)
FETCHERS = re.compile(r"\b(curl|wget|requests\.(?:get|post)|urlopen|urlretrieve|httpx|aiohttp)\b")
SPLIT = re.compile(r"\n|;|&&|\|\|")
TO_FILE = re.compile(r"(?:\s-o\s*(\S+)|\s--output[= ](\S+)|\s>>?\s*(\S+))")
HARMLESS = re.compile(r"^\s*(?:ls|rm|wc|file|stat|du|test|echo|\[|true|cd)\b")


def lines_of(path: Path):
    data = path.read_bytes()
    if path.suffix == ".zstd":
        import zstandard
        data = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(data)).read()
    return data.decode("utf-8", "replace").split("\n")


def core(url: str) -> str:
    u = re.sub(r"^https?://", "", url.strip().lower())
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")


def strings(v) -> list:
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [x for x in v if isinstance(x, str)]
    return []


def read_later(session: dict, after: int, path: str) -> bool:
    """Does a later shell command of this session read the downloaded file before it is removed or overwritten?"""
    name = os.path.basename(path.strip("\"'"))
    if not name or name in ("null", "-"):
        return False
    order = session["call_order"]
    for cid in order[after + 1:]:
        call = session["calls"][cid]
        args = call["args"] if isinstance(call["args"], dict) else {}
        if call["name"] == "read" and name in json.dumps(args, ensure_ascii=False):
            return True
        if call["name"] != "bash":
            continue
        for seg in SPLIT.split(str(args.get("command") or "")):
            if name not in seg:
                continue
            if re.match(r"^\s*rm\b", seg):
                return False
            if FETCHERS.search(seg) and TO_FILE.search(seg):  # a new download to the same path
                return False
            if not HARMLESS.match(seg):
                return True
    return False


def check_session(session: dict, blocked: list, tag: str) -> tuple:
    source, unread, mention = [], [], []
    order = session["call_order"]
    for pos, cid in enumerate(order):
        call = session["calls"][cid]
        args = call["args"] if isinstance(call["args"], dict) else {}
        res = session["results"].get(cid) or {}
        if call["name"] == "web_fetch":
            for u in strings(args.get("url")) + strings(args.get("urls")):
                hit = next((b for b in blocked if b in core(u)), None)
                if hit:
                    ok = bool(res) and not res.get("is_error") and len(res.get("text") or "") >= 200
                    (source if ok else unread).append({"log": tag, "tool": "web_fetch", "url": hit, "args": u[:240], "result_chars": len(res.get("text") or "")})
        elif call["name"] == "bash":
            cmd = str(args.get("command") or "")
            low = cmd.lower()
            hits = [b for b in blocked if b in low]
            if not hits or not FETCHERS.search(cmd):
                continue
            direct = False
            for seg in SPLIT.split(cmd):
                sl = seg.lower()
                hit = next((b for b in hits if b in sl), None)
                if not hit or not FETCHERS.search(seg):
                    continue
                direct = True
                m = TO_FILE.search(seg)
                path = next((g for g in m.groups() if g), "") if m else ""
                if not path and re.search(r"\bwget\b", seg) and not re.search(r"-q?O\s*-", seg):
                    path = hit.rsplit("/", 1)[-1]  # wget writes a file named after the URL
                rec = {"log": tag, "tool": "bash", "url": hit, "args": seg.strip()[:240], "to_file": path}
                if path and not read_later(session, pos, path):
                    unread.append(rec)
                else:
                    source.append(rec)
            if not direct:
                mention.append({"log": tag, "tool": "bash", "url": hits[0], "args": cmd[:240]})
    return source, unread, mention


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch", type=Path)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    index = json.loads(a.index.read_text(encoding="utf-8"))
    out = []
    for res in sorted(a.batch.glob("*/result.json")):
        d = res.parent
        r = json.loads(res.read_text())
        blocked = [core(u) for u in ((index.get(r.get("task")) or {}).get("blocked") or {}).get("urls") or []]
        blocked = [b for b in blocked if len(b) >= 12]
        names = []
        logs = [p for p in [d / "events.jsonl", *sorted(d.glob("home/sessions/*/*/session.v4.jsonl*"))] if p.exists()]
        for log in logs:
            tag = log.name if log.name == "events.jsonl" else log.parent.name[-12:]
            for line in lines_of(log):
                m = NAMES.search(line)
                if m:
                    names.append({"log": tag, "match": m.group(0), "around": line[max(0, m.start() - 120):m.end() + 160]})
        source, unread, mention = [], [], []
        _, sessions = rm.load_sessions(d)
        for s in sessions:
            x, y, z = check_session(s, blocked, str(s["id"])[-12:])
            source += x
            unread += y
            mention += z
        rec = {"id": d.name, "task": r.get("task"), "group": r.get("group"), "rep": r.get("rep"), "sessions": len(sessions),
               "n_name_hits": len(names), "n_source_calls": len(source), "n_unread": len(unread), "n_mentions": len(mention),
               "n_hits": len(names) + len(source), "names": names[:5], "source": source[:8], "unread": unread[:8], "mention": mention[:8]}
        out.append(rec)
        note = ""
        if rec["n_hits"]:
            first = (source or names)[0]
            note = f"FLAGGED names x{len(names)} source x{len(source)}: " + (first.get("args") or first.get("around") or "")[:150]
        elif unread or mention:
            note = f"not flagged; unread downloads x{len(unread)}, mentions x{len(mention)}: " + ((unread or mention)[0].get("args") or "")[:120]
        print(d.name, rec["task"], rec["group"], "sessions", rec["sessions"], note)
    by = {}
    for r in out:
        by.setdefault(r["group"], [0, 0, 0, 0])
        by[r["group"]][0] += 1
        by[r["group"]][1] += 1 if r["n_hits"] else 0
        by[r["group"]][2] += 1 if r["n_unread"] else 0
        by[r["group"]][3] += 1 if r["n_mentions"] else 0
    print(f"{len(out)} runs; flagged {sum(1 for r in out if r['n_hits'])}; by group (runs, flagged, with an unread download, with a mention only): {by}")
    if a.out:
        a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
