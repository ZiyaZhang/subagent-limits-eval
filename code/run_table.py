#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One row per run, straight from the run directories, every column with ONE definition for every batch.

Why: until 2026-10-08 each batch had its own run table, written by the analysis script of that batch. Columns were
added over time, so the early batches lack some (the time of the final answer, the tokens by kind), and the code that
read them fell back to another quantity without saying so. This script reads the raw material of a run (result.json,
stderr.log, the session logs) and writes the same columns for every run. A value that cannot be read stays EMPTY;
nothing is replaced by something else.

Columns (times in seconds; "t0" is the first event of any session log of the run):
  identity   batch, id, task, group, rep, order, block_pos, attempts, started_utc, ended_utc
  how it ran patches (the config patches of the run: the group's depth and K are in the last one), hint_a, hint_b
             (first 8 hex digits of the hash of each sentence appended to the task prompt; empty without one),
             prompt (same for the whole prompt), layers (the image layers: the DSH build), web, cpu_cores, memory_mb,
             parallel (runs at once in the batch), dsh, wait_for_subagents (the process was told to stay up until
             the subagents settle), timeout_s
  how it ended
             exit, timeout, crash5063, infra_signal, oom_kill, mem_peak_gb, root_end (kind of the root agent's last
             turn end: completed / aborted / ... / open when the log stops inside a turn / none when it has no turn)
  times      process_s        the dsh process from start to exit (the runner's clock)
             t_first_kid_s    t0 -> the first event of the first subagent
             t_last_write_s   t0 -> the last result of a call of the write or edit tool, any agent
             t_answer_s       t0 -> the end of the root agent's last turn: what the user waits for
             t_last_event_s   t0 -> the last event of any session
  agents     agents (sessions of the run, root included), kids_d1, kids_d2, kids_d3, kids_aborted (subagents whose
             last turn was aborted), kids_after_answer (subagents with events more than 2 s after the root's answer)
  root       root_turns
  tokens     tok_miss (input not read from cache), tok_hit (input read from cache), tok_out (output); every agent of
             the run together; tok_root_* the root agent alone
  tools      search_requests (requests of the search plugin's own model), n_web_search, n_web_fetch, n_bash,
             n_write_edit, n_read
  delegation spawn_calls (calls of subagent / subagent_fork), spawn_started, rejected_depth, rejected_cap
  phase 2    sentence_tag, sentence_sha256 (the sentence a P<tag>- group appended; dsec_matrix_v6), deliverable_ok (the
             runner's own check of the deliverable: 1 / 0, empty when the task has none), model_probe (the model id the
             endpoint reported at the last probe before the run)
  wait patch waited_s, idle_wait_s, wait_cap (what the wait patch printed at exit; empty without the patch)
  problems   log_error (a session log that could not be read completely), sessions_unparsed
  alive      peak_alive: the most subagents at once that held a slot of DSH's maxActiveSubagents limit (K), counted as
             DSH counts them. In dsh-v0.2.0-rc.2, packages/subagent/subagent/src/continuation-activation.ts: a slot is
             taken by ActivationPool.reserve (lines 45-56; over capacity -> "subagent limit reached (active child
             limit: K)"), called from ContinuableActivationRegistry.materialize (lines 488-489) for every fresh creation
             and every cold resume of a background (continuable) child, and returned by finishDisposal (line 863,
             activation.releaseSlot()) right before the settlement notice goes to the parent (line 864). The pool is the
             parent's own pool when the parent is itself a continuable child, else the pool of that parent agent (line
             488), so all continuable descendants of the root share the root's pool; a one-shot (foreground) child takes
             no slot and its continuable children form a pool of their own. From the logs (run_metrics.slot_epochs, the
             reconstruction of the "slots" section of run_metrics.py): a slot is held from the parent's subagent /
             subagent_fork call that started the child until the parent's log shows the child's subagent-settled notice
             (the end of the run when it never does); a successful send_message to a child that had settled holds a slot
             again from the send. peak_alive = the most slots held at once in any one pool (what DSH compares with K);
             peak_alive_d1 = the same counting the root's direct children only; peak_alive_time_s = t0 -> the moment
             peak_alive was first reached (empty when peak_alive is 0). All three are empty when the start of a slot
             cannot be read (a child without a creation record and without a log header).
             wait_max_busy, wait_max_resident: what the wait patch saw while it kept the process alive after the root's
             first turn end (sampled every 0.5 s from then until exit, not before): the most agents other than the root
             running at once, and the most resident continuable activations at once (= slots held, all pools together)
  model      model_id: the model identifier the API returned for the root agent's requests. The session logs of DSH
             0.2.0-rc.2 do not record it (llm-deepseek translate.ts stores the requested id in the replay state and
             events.jsonl names no model), so it is empty. model_requested: the model id the root agent's requests
             asked for (source.model of its assistant messages; several joined with +).

Two more tables next to the run table, one file per batch:
  <batch>.spawn_calls.csv  one row per delegation call (subagent / subagent_fork): batch, id, caller (session id),
             caller_depth, t_call_s, t_result_s, tool, run_in_background (the argument as the caller gave it, empty when
             omitted), outcome (accepted / rejected / no_result: the log has no result for the call), reject_kind
             (depth / cap / other), error (first 160 chars of a rejection), description (the label the caller gave),
             task (the first 300 chars of the task text passed in `prompt`, line breaks replaced by spaces), child (the
             session the call started: the id in the "started subagent" result; for a foreground call, the caller's
             one-shot child created between the call and its result)
  <batch>.agents.csv       one row per agent session: batch, id, session, parent, depth, mode (continuable / one-shot,
             from the subagent descriptor or the parent's catalog; empty for the root), label, t_first_s, t_last_s,
             turns, last_end (as root_end), requests (assistant messages), tok_miss, tok_hit, tok_cwrite (input written
             to the cache), tok_out, search_requests, n_web_search, n_web_fetch, n_bash, n_read, n_write_edit,
             n_tool_calls, spawn_calls, rejected_depth, rejected_cap, sent_to_parent_n and sent_to_parent_chars
             (send_message calls to the parent that were delivered, and the length of their text), settled_n
             (settlement notices from this agent in its parent's log), settled_kind (how the last notice says the agent
             ended: completed / aborted / max-tokens / refusal / error / other), handback_chars (length of the closing
             message in that last notice: what the agent handed back to its parent when it finished; 0 when the notice
             says it left none; empty without a notice, e.g. when the process exited first)

Usage (experiment directory on the dev box; reads files only):
  python judge-env/scripts/run_table.py results/runs/office-confirm [more batches] --out results/master/raw [--jobs 16]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_metrics as rm  # noqa: E402
import mechanism_extra as mx  # noqa: E402

WAIT = re.compile(r"dsh-exp-wait: first_busy=(-?\d+) max_busy=(\d+) waited_ms=(\d+) live_at_end=(\d+)"
                  r"(?: first_resident=(-?\d+) max_resident=(\d+) resident_at_end=(\d+) idle_wait_ms=(\d+) wait_cap=(\d))?")
COLS = ["batch", "id", "task", "group", "rep", "order", "block_pos", "attempts", "started_utc", "ended_utc",
        "patches", "hint_a", "hint_b", "prompt", "layers", "web", "cpu_cores", "memory_mb", "parallel", "dsh",
        "wait_for_subagents", "timeout_s", "exit", "timeout", "crash5063", "infra_signal", "oom_kill", "mem_peak_gb", "root_end",
        "process_s", "t_first_kid_s", "t_last_write_s", "t_answer_s", "t_last_event_s",
        "agents", "kids_d1", "kids_d2", "kids_d3", "kids_aborted", "kids_after_answer", "root_turns",
        "tok_miss", "tok_hit", "tok_out", "tok_root_miss", "tok_root_hit", "tok_root_out",
        "search_requests", "n_web_search", "n_web_fetch", "n_bash", "n_write_edit", "n_read",
        "spawn_calls", "spawn_started", "rejected_depth", "rejected_cap",
        "waited_s", "idle_wait_s", "wait_cap", "log_error", "sessions_unparsed",
        "peak_alive", "peak_alive_d1", "peak_alive_time_s", "wait_max_busy", "wait_max_resident", "model_id", "model_requested",
        "sentence_tag", "sentence_sha256", "deliverable_ok", "model_probe"]
SPAWN_COLS = ["batch", "id", "caller", "caller_depth", "t_call_s", "t_result_s", "tool", "run_in_background", "outcome",
              "reject_kind", "error", "description", "task", "child"]
AGENT_COLS = ["batch", "id", "session", "parent", "depth", "mode", "label", "t_first_s", "t_last_s", "turns", "last_end", "requests",
              "tok_miss", "tok_hit", "tok_cwrite", "tok_out", "search_requests", "n_web_search", "n_web_fetch", "n_bash", "n_read",
              "n_write_edit", "n_tool_calls", "spawn_calls", "rejected_depth", "rejected_cap", "sent_to_parent_n", "sent_to_parent_chars",
              "settled_n", "settled_kind", "handback_chars"]
SETTLED_KIND = (("finished and will do no further work", "completed"), ("was stopped before it finished", "aborted"),
                ("ran out of room", "max-tokens"), ("declined the task", "refusal"), ("failed before it finished", "error"))
CLOSING, NO_CLOSING = "Its closing message:", "It left no closing message."  # dsh-subagent continuation-messages.ts


def sec(a, b):
    return round((a - b) / 1000, 1) if a is not None and b is not None else ""


def one_line(text, n: int) -> str:
    """The first n characters of a text, line breaks and tabs replaced by spaces (one CSV line per cell)."""
    return re.sub(r"[\r\n\t]+", " ", text[:n]) if isinstance(text, str) else ""


def end_kind(s: dict) -> str:
    """Kind of a session's last turn end: completed / aborted / ... / open when the log stops inside a turn / none."""
    if not s["turns"]:
        return "none"
    if not s["turns"][-1][2]:
        return "open"
    return (s["turn_ends"][-1][1] or {}).get("kind") or "?" if s["turn_ends"] else "?"


def peak_of(entries, t_end) -> tuple:
    """(peak, time it was first reached) of the number of slot epochs held at once; an entry is (start, end or None, ...).
    A release and a start at the same instant count the release first (as run_metrics.slot_metrics sweeps)."""
    points = sorted([(e[0], 1) for e in entries] + [(e[1] if e[1] is not None else t_end, -1) for e in entries])
    cur, best, best_t = 0, 0, None
    for t, d in points:
        cur += d
        if cur > best:
            best, best_t = cur, t
    return best, best_t


def settlement(content) -> tuple:
    """(how the child ended, length of its closing message) from one subagent-settled notice: the content blocks of
    the message as the parent's agent/inbox/spliced event holds it, or its joined text from the parent's user/message."""
    if isinstance(content, list):
        texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        summary, rest = (texts[0] if texts else ""), texts[1:]
        chars = sum(len(t) for t in rest[1:]) if rest and rest[0] == CLOSING else 0 if rest and rest[0] == NO_CLOSING else ""
    else:
        summary, _, rest = (content or "").partition("\n")
        chars = len(rest) - len(CLOSING) - 1 if rest.startswith(CLOSING + "\n") else 0 if rest == NO_CLOSING else ""
    kind = next((k for needle, k in SETTLED_KIND if needle in summary), "other" if summary else "")
    return kind, chars


def spawn_rows(batch: str, rid, sessions: list, t0) -> list:
    rows = []
    for s in sessions:
        one_shot = sorted((c for c in sessions if c["parent"] == s["id"] and c["mode"] != "continuable"),
                          key=lambda c: c["created"] if c["created"] is not None else (c["first_time"] or 0))
        taken = set()
        for cid in s["call_order"]:
            c = s["calls"][cid]
            if c["name"] not in mx.SPAWN:
                continue
            r, args = s["results"].get(cid), c["args"] or {}
            rejected = r is not None and (r["is_error"] or r["text"].lstrip().startswith("Error"))
            bg = args.get("run_in_background")
            row = {"batch": batch, "id": rid, "caller": s["id"], "caller_depth": s["depth"], "t_call_s": sec(c["time"], t0),
                   "t_result_s": sec(r["time"], t0) if r else "", "tool": c["name"], "run_in_background": "" if bg is None else bg,
                   "outcome": "no_result" if r is None else "rejected" if rejected else "accepted",
                   "reject_kind": (mx.reject_kind(s, cid) or "other") if rejected else "", "error": one_line(r["text"], 160) if rejected else "",
                   "description": one_line(args.get("description"), 120), "task": one_line(args.get("prompt"), 300), "child": ""}
            if row["outcome"] == "accepted":
                m = rm.STARTED_RE.search(r["text"])
                if m:
                    row["child"] = rm.norm_id(m.group(1))
                elif c["time"] is not None:  # a foreground call: the caller's one-shot child created between call and result
                    for k in one_shot:
                        t = k["created"] if k["created"] is not None else k["first_time"]
                        if k["id"] not in taken and t is not None and c["time"] - 1000 <= t <= (r["time"] if r["time"] is not None else t):
                            row["child"] = k["id"]
                            taken.add(k["id"])
                            break
            rows.append(row)
    return rows


def agent_rows(batch: str, rid, sessions: list, by_id: dict, t0) -> list:
    notices = collections.defaultdict(dict)  # child -> notice id -> (time, content); the spliced message before its user/message copy
    for p in sessions:
        for ib in p["inbox"]:
            for msg in ib["messages"]:
                src = msg.get("source") or {}
                child = rm.norm_id(src.get("senderSessionId"))
                if src.get("kind") == "subagent-settled" and by_id.get(child, {}).get("parent") == p["id"]:
                    notices[child].setdefault(msg.get("id") or f"inbox@{ib['time']}", (ib["time"], msg.get("content")))
        for u in p["users"]:
            if u["kind"] == "subagent-settled" and by_id.get(u["sender"], {}).get("parent") == p["id"]:
                notices[u["sender"]].setdefault(u["id"] or f"user@{u['time']}", (u["time"], u["text"]))
    rows = []
    for s in sessions:
        names = [c["name"] for c in s["calls"].values()]
        kinds = [mx.reject_kind(s, cid) for cid, c in s["calls"].items() if c["name"] in mx.SPAWN]
        sent = [s["calls"][cid] for cid in s["call_order"] if s["calls"][cid]["name"] == rm.SEND_TOOL and s["parent"]
                and rm.norm_id((s["calls"][cid]["args"] or {}).get("agent_id")) == s["parent"]
                and s["results"].get(cid) and not s["results"][cid]["is_error"]]
        mode = s["mode"]
        if mode is None and s["parent"] in by_id:
            mode = next((c["mode"] for c in by_id[s["parent"]]["catalog"] if c["child"] == s["id"]), None)
        mine = sorted(notices.get(s["id"], {}).values(), key=lambda x: x[0] if x[0] is not None else -1)
        kind, chars = settlement(mine[-1][1]) if mine else ("", "")
        rows.append({"batch": batch, "id": rid, "session": s["id"], "parent": s["parent"] or "", "depth": s["depth"], "mode": mode or "",
                     "label": one_line(s["label"], 120), "t_first_s": sec(s["first_time"], t0), "t_last_s": sec(s["last_time"], t0),
                     "turns": len(s["turns"]), "last_end": end_kind(s), "requests": len(s["messages"]),
                     "tok_miss": int(s["usage"].get("inputTokens", 0)), "tok_hit": int(s["usage"].get("cacheReadTokens", 0)),
                     "tok_cwrite": int(s["usage"].get("cacheWriteTokens", 0)), "tok_out": int(s["usage"].get("outputTokens", 0)),
                     "search_requests": s["search_aux"], "n_web_search": names.count("web_search"), "n_web_fetch": names.count("web_fetch"),
                     "n_bash": names.count("bash"), "n_read": names.count("read"), "n_write_edit": names.count("write") + names.count("edit"),
                     "n_tool_calls": len(names), "spawn_calls": len(kinds), "rejected_depth": kinds.count("depth"), "rejected_cap": kinds.count("cap"),
                     "sent_to_parent_n": len(sent), "sent_to_parent_chars": sum(len(c["args"]["message"]) for c in sent if isinstance(c["args"].get("message"), str)),
                     "settled_n": len(mine), "settled_kind": kind, "handback_chars": chars})
    return rows


def one(run: dict) -> tuple:
    """(run row, spawn_calls rows, agents rows) of one run."""
    res, d = run["result"], Path(run["dir"])
    mem = res.get("memory") or {}
    row = {c: "" for c in COLS}
    row.update({"batch": run["batch"], "id": res.get("id", run["key"]), "task": res.get("task"), "group": res.get("group"), "rep": res.get("rep"),
                "order": res.get("order", ""), "block_pos": res.get("block_pos", ""), "attempts": res.get("attempts", ""),
                "started_utc": res.get("started_utc", ""), "ended_utc": res.get("ended_utc", ""),
                "patches": "+".join(res.get("patches") or []), "hint_a": (res.get("encourage_sha256") or "")[:8], "hint_b": (res.get("noreview_sha256") or "")[:8],
                "prompt": (res.get("prompt_sha256") or "")[:8], "layers": "+".join(Path(str(x)).name for x in res.get("layers") or []),
                "web": res.get("web", ""), "cpu_cores": res.get("cpu_cores", ""), "memory_mb": res.get("memory_mb", ""), "parallel": res.get("parallel", ""),
                "dsh": json.dumps(res.get("dsh"), ensure_ascii=False)[:60] if res.get("dsh") is not None else "",
                "wait_for_subagents": res.get("wait_for_subagents", ""), "timeout_s": res.get("timeout_s", ""),
                "sentence_tag": res.get("sentence_tag") or "", "sentence_sha256": res.get("sentence_sha256") or "", "model_probe": res.get("model_probe") or "",
                "deliverable_ok": ("" if res.get("deliverable") is None else int(bool((res.get("deliverable") or {}).get("ok", (res.get("deliverable") or {}).get("changed"))))),
                "exit": res.get("exit", ""), "timeout": res.get("timeout", ""), "crash5063": res.get("crash5063", ""),
                "infra_signal": res.get("infra_signal", ""), "oom_kill": res.get("oom_kill", mem.get("oom_kill", "")),
                "mem_peak_gb": round(mem["peak_bytes"] / 2 ** 30, 2) if mem.get("peak_bytes") else "",
                "process_s": res.get("seconds", "")})
    err = (d / "stderr.log").read_text(encoding="utf-8", errors="replace") if (d / "stderr.log").exists() else ""
    if row["crash5063"] == "":
        row["crash5063"] = all(s in err for s in rm.CRASH5063)
    m = WAIT.search(err)
    if m:
        row["waited_s"], row["wait_max_busy"] = round(int(m.group(3)) / 1000, 1), int(m.group(2))
        if m.group(5) is not None:
            row["idle_wait_s"], row["wait_cap"], row["wait_max_resident"] = round(int(m.group(8)) / 1000, 1), int(m.group(9)), int(m.group(6))
    try:
        logs, sessions = rm.load_sessions(d)
    except Exception as exc:  # a run directory that cannot be read: the row keeps what result.json gave
        row["log_error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
        return row, [], []
    bad = [log for log in logs if log.get("error")]
    row["log_error"] = "; ".join(sorted({log["error"][:60] for log in bad}))[:200]
    row["sessions_unparsed"] = len(logs) - len(sessions)
    if not sessions:
        return row, [], []
    by_id = {s["id"]: s for s in sessions}
    roots = [s for s in sessions if not s["parent"] or s["parent"] not in by_id]
    root = min(roots, key=lambda s: (s["depth"], s["first_time"] or 0)) if roots else None
    kids = [s for s in sessions if s is not root]
    firsts = [s["first_time"] for s in sessions if s["first_time"] is not None]
    lasts = [s["last_time"] for s in sessions if s["last_time"] is not None]
    t0 = min(firsts) if firsts else None
    row["agents"] = len(sessions)
    for depth in (1, 2, 3):
        row[f"kids_d{depth}"] = sum(1 for s in kids if s["depth"] == depth)
    row["kids_aborted"] = sum(1 for s in kids if s["turn_ends"] and (s["turn_ends"][-1][1] or {}).get("kind") == "aborted")
    kid_first = [s["first_time"] for s in kids if s["first_time"] is not None]
    row["t_first_kid_s"] = sec(min(kid_first), t0) if kid_first else ""
    writes = [r["time"] for s in sessions for cid, c in s["calls"].items() if c["name"] in ("write", "edit") for r in [s["results"].get(cid)] if r and r["time"] is not None]
    row["t_last_write_s"] = sec(max(writes), t0) if writes else ""
    row["t_last_event_s"] = sec(max(lasts), t0) if lasts else ""
    if root is not None:
        ends = [b for _, b, _ in root["turns"] if b is not None]
        t_ans = max(ends) if ends else None
        row["t_answer_s"] = sec(t_ans, t0)
        row["root_turns"] = len(root["turns"])
        row["root_end"] = end_kind(root)
        if t_ans is not None:
            row["kids_after_answer"] = sum(1 for s in kids if s["last_time"] is not None and s["last_time"] > t_ans + 2000)
        for k, name in (("miss", "inputTokens"), ("hit", "cacheReadTokens"), ("out", "outputTokens")):
            row[f"tok_root_{k}"] = int(root["usage"].get(name, 0))
        row["model_requested"] = "+".join(sorted(m for m in root["models"] if isinstance(m, str)))
    for k, name in (("miss", "inputTokens"), ("hit", "cacheReadTokens"), ("out", "outputTokens")):
        row[f"tok_{k}"] = int(sum(s["usage"].get(name, 0) for s in sessions))
    row["search_requests"] = sum(s["search_aux"] for s in sessions)
    names = [c["name"] for s in sessions for c in s["calls"].values()]
    row["n_web_search"], row["n_web_fetch"], row["n_bash"] = names.count("web_search"), names.count("web_fetch"), names.count("bash")
    row["n_write_edit"], row["n_read"] = names.count("write") + names.count("edit"), names.count("read")
    spawn = [(s, cid) for s in sessions for cid, c in s["calls"].items() if c["name"] in mx.SPAWN]
    kinds = [mx.reject_kind(s, cid) for s, cid in spawn]
    row["spawn_calls"], row["rejected_depth"], row["rejected_cap"] = len(spawn), kinds.count("depth"), kinds.count("cap")
    row["spawn_started"] = len(kids)
    if root is not None:
        se = rm.slot_epochs({"sessions": sessions, "by_id": by_id, "root": root})
        if not se["stats"]["no_start_time"]:
            t_end = max(lasts) if lasts else t0
            peaks = [peak_of(entries, t_end) for entries in se["pools"].values()]
            row["peak_alive"] = max((p for p, _ in peaks), default=0)
            if row["peak_alive"]:
                row["peak_alive_time_s"] = sec(min(t for p, t in peaks if p == row["peak_alive"]), t0)
            d1 = [e for entries in se["pools"].values() for e in entries if se["parent_of"].get(e[2]) == root["id"]]
            row["peak_alive_d1"] = peak_of(d1, t_end)[0]
    return row, spawn_rows(run["batch"], row["id"], sessions, t0), agent_rows(run["batch"], row["id"], sessions, by_id, t0)


def write(path: Path, cols: list, rows: list) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batches", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    for batch in a.batches:
        runs, notes = rm.discover(batch)
        for r in runs:
            r["dir"] = str(r["dir"])
        with ProcessPoolExecutor(max_workers=a.jobs) as ex:
            results = list(ex.map(one, runs, chunksize=4))
        rows = [row for row, _, _ in results]
        write(a.out / f"{batch.name}.csv", COLS, rows)
        write(a.out / f"{batch.name}.spawn_calls.csv", SPAWN_COLS, [x for _, sp, _ in results for x in sp])
        write(a.out / f"{batch.name}.agents.csv", AGENT_COLS, [x for _, _, ag in results for x in ag])
        empty = {c: sum(1 for r in rows if r[c] == "") for c in ("t_answer_s", "tok_out", "root_end", "peak_alive")}
        print(f"{batch.name}: {len(rows)} runs; rows without t_answer_s {empty['t_answer_s']}, without tokens {empty['tok_out']}, "
              f"without peak_alive {empty['peak_alive']}; log errors {sum(1 for r in rows if r['log_error'])}; notes {len(notes)}; "
              f"spawn calls {sum(len(sp) for _, sp, _ in results)}, agents {sum(len(ag) for _, _, ag in results)}", flush=True)
    (a.out / "done.txt").write_text("done\n", encoding="utf-8")


if __name__ == "__main__":
    main()
