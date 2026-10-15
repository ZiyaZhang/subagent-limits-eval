#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One JSON digest per run, built only from the run's logs, for the behaviour annotation (phase 2, module I).

The digest is what the annotating model (behavior_annotate.py) and the human check (behavior_check.py) read instead
of the logs. It holds, for one run: the task prompt (head), the delegation tree with every agent's task, times,
tool-call counts, delegation calls (accepted / rejected and why) and hand-back, the root agent's timeline of notable
events, the final answer (head), the deliverable check, repeated search queries, pages / files touched by several
agents, and the review waves. It never holds the run's group, K or D: no group name, no patch names, and the
rejection reasons are reduced to "depth limit" / "active-child limit" without the numbers.

Definitions (all from the session logs; same as run_table.py where the two overlap):
  t0                   the first event of any session log of the run; every time is seconds from t0
  root                 the session without a parent (lowest depth, earliest first event when there are several)
  agent names          A0 is the root; subagents are A1, A2, ... in the order of their first event (ties by id);
                       "session_ids" maps each name to the first 8 characters of its session id; an agent entry
                       names its parent only at depth 2 or more (a depth-1 agent's parent is A0)
  task of a subagent   the `prompt` argument of the delegation call that started it (its first user message says the
                       same); task of the root: the first user message (the task prompt: head shown, and its last 150
                       characters as task_prompt_tail when it is longer than the head, because a sentence appended to
                       the task sits at the end)
  calls                counts of the agent's own tool calls: web_search, web_fetch, read (read / read_image), write
                       (write / edit), bash, delegate (subagent / subagent_fork), other (todo_write, list_agents,
                       job_output, send_message, ...)
  delegations          the agent's subagent / subagent_fork calls in time order. Accepted: {"t", "child": "A3"} (the
                       child's own entry holds its task). Rejected: {"t", "rejected": reason, "task_head"}; consecutive
                       rejected calls with the same reason AND the same full task text are collapsed into one entry
                       with "n" (how many) and "t" = [first, last]. No result in the log: {"t", "no_result": true}.
  before_first_delegation
                       how many substantive tool calls (web_search, web_fetch, read, write, edit, bash, grep, glob)
                       the agent made before its first delegation call, and the seconds from its start to that call
  overlap              for each delegation call, the share of the child task's 4-character shingles that occur in
                       the caller's own task text (protocol v5.1 section 六, c_i); 1.0 = the child task is made of
                       the caller's task
  handback             of a subagent: the closing message in its subagent-settled notice to the parent (run_table's
                       handback_chars; head shown), the kind of ending the notice reports, when the parent received
                       it; and the messages it sent to the parent with send_message (count, chars, head of the last)
  end                  kind of the agent's last turn end (completed / aborted / ... / open when the log stops inside
                       a turn / none)
  root_timeline        first delegation; each rejection burst of the root (rejected calls at most 60 s apart);
                       messages the root sent to children (the same text to several children within 5 s is one
                       event); interrupts; every settlement notice the root received (one event each at levels 0-1,
                       one merged line at levels 2-3); the last file write (any agent, any path, as run_table's
                       t_last_write_s); the final answer (end of the root's last turn); the subagents still running
                       at the final answer (events more than 2 s after it: kids_after_answer)
  final_answer_head    the text of the root's last assistant message that has text
  deliverable          result.json's deliverable check (dsec_matrix check_deliverable): a file's existence and size,
                       or how many of the expected files changed
  repeated_queries     every string of every web_search `queries` list over the whole tree, normalised (trimmed,
                       case-folded, spaces collapsed): total, distinct, duplicates = total - distinct, and the most
                       repeated strings with the agents that issued them (an agent listed twice issued it twice)
  shared_pages / shared_files
                       URLs fetched (web_fetch) by two or more different agents; files written (write / edit) by
                       two or more different agents
  review               last_write_s: the last write / edit result of any agent. after_last_write: subagents whose
                       first event is after it, grouped into waves (a new wave when the start is more than 120 s
                       after the previous start). review_like: subagents whose label (the delegation call's
                       description) contains verify / review / check / audit / test / second opinion / 复核 / 检查 /
                       审查 / 验证 / 核对 / 测试, with the same waves; this catches reviewers that themselves fix files
                       (which moves the last write past their start: in xl-main/0gqtht0vci the last write is a
                       reviewer's scratch script at 971 s, so after_last_write is 0 while review_like is 14 in 3 waves)
  root_after_last_write
                       the root's tool calls after the last write, by name, and the seconds from the last write to
                       the final answer

Size: the texts are cut at the limits of level 0 (task 300, child task 120, hand-back 300, final answer 400, task
prompt 300). When the rendered digest is longer than --max-chars (5,000), the limits step down a fixed ladder of four
levels (the last: 120 / 60 / 120 / 280 / 160) until it fits or the ladder ends; the level used is written into the
digest ("text_limits"). The ladder stops there because below that the heads say nothing and the size is dominated by
the per-agent structure (about 350 characters an agent), so a tree of 9 agents lands near 8,000 characters whatever
the limits. --fixed-limits keeps level 0.
Everything is deterministic: no clocks, sorted sets, stable ordering.

Usage (experiment directory; reads files only):
  run_digest.py results/runs/<batch> [--out results/digests/<batch>/] [--ids a,b] [--jobs 8] [--max-chars 5000]
Writes <out>/<run id>.json and <out>/digest-stats.csv (chars per digest; chars at level 0; agents; level used).
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
import run_table as rt  # noqa: E402
import mechanism_extra as mx  # noqa: E402

SPAWN = mx.SPAWN
SUBSTANTIVE = ("web_search", "web_fetch", "read", "read_image", "write", "edit", "bash", "grep", "glob")
REVIEW_RE = re.compile(r"verif|review|check|audit|test|second opinion|复核|检查|审查|验证|核对|测试|复查", re.I)
LADDER = [  # task head, child task head (rejected calls), hand-back head, final answer head, task prompt head, message head
    {"task": 300, "child_task": 120, "handback": 300, "answer": 400, "prompt": 300, "message": 150},
    {"task": 220, "child_task": 100, "handback": 220, "answer": 360, "prompt": 240, "message": 110},
    {"task": 160, "child_task": 80, "handback": 160, "answer": 320, "prompt": 200, "message": 80},
    {"task": 120, "child_task": 60, "handback": 120, "answer": 280, "prompt": 160, "message": 60},
]
WAVE_GAP_S = 120.0
BURST_GAP_S = 60.0
AFTER_ANSWER_S = 2.0


def sec(a, b):
    return round((a - b) / 1000, 1) if a is not None and b is not None else None


def head(text, n: int):
    """The first n characters of a text, line breaks and tabs replaced by spaces; "" for no text; n <= 0 -> None."""
    if not isinstance(text, str):
        return ""
    if n <= 0:
        return None
    t = re.sub(r"[\r\n\t]+", " ", text).strip()
    return t[:n] + ("…" if len(t) > n else "")


def norm_query(q) -> str:
    return re.sub(r"\s+", " ", str(q)).strip().casefold()


def shingles(text: str, n: int = 4) -> set:
    t = re.sub(r"\s+", "", text or "")
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def overlap(child_task: str, own_task: str):
    """Share of the child task's 4-character shingles found in the caller's own task (protocol c_i)."""
    c = shingles(child_task)
    if not c:
        return None
    return round(len(c & shingles(own_task)) / len(c), 2)


def reject_reason(s: dict, cid: str) -> str:
    """"depth limit" / "active-child limit" / "other: <head>" for a rejected delegation call; no K or D numbers."""
    kind = mx.reject_kind(s, cid)
    if kind == "depth":
        return "depth limit"
    if kind == "cap":
        return "active-child limit"
    text = (s["results"].get(cid) or {}).get("text") or ""
    return "other: " + re.sub(r"\d+", "N", head(text, 80) or "")


def closing_of(content) -> tuple:
    """(kind, closing text or None) from one subagent-settled notice, as run_table.settlement reads it."""
    if isinstance(content, list):
        texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        summary, rest = (texts[0] if texts else ""), texts[1:]
        closing = "".join(rest[1:]) if rest and rest[0] == rt.CLOSING else "" if rest and rest[0] == rt.NO_CLOSING else None
    else:
        summary, _, rest = (content or "").partition("\n")
        closing = rest[len(rt.CLOSING) + 1:] if rest.startswith(rt.CLOSING + "\n") else "" if rest == rt.NO_CLOSING else None
    kind = next((k for needle, k in rt.SETTLED_KIND if needle in summary), "other" if summary else "")
    return kind, closing


def message_text(content) -> str:
    """The text of an agent-message as the receiver's inbox holds it, without the "Agent X sent a message: " prefix."""
    if isinstance(content, list):
        texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        if texts and texts[0].startswith("Agent ") and texts[0].rstrip().endswith("sent a message:"):
            texts = texts[1:]
        return "".join(texts)
    return content or ""


def last_text_message(log: dict) -> tuple:
    """(time, text) of the last assistant message with a text block in one raw session log."""
    for ev in reversed(log["events"]):
        if ev.get("type") != "assistant/message":
            continue
        content = ((ev.get("data") or {}).get("message") or {}).get("content") or []
        texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        if any(t.strip() for t in texts):
            return ev.get("time"), "".join(texts)
    return None, ""


def waves(starts: list) -> int:
    n = 0
    prev = None
    for t in sorted(starts):
        if prev is None or t - prev > WAVE_GAP_S:
            n += 1
        prev = t
    return n


def task_kind(res: dict) -> str:
    d = res.get("deliverable") or {}
    if d.get("kind") == "changed_files" or res.get("web") is False:
        return "code"
    if d.get("kind") == "file":
        return "report"
    return "other"


def exit_summary(res: dict, root) -> dict:
    mem = res.get("memory") or {}
    return {"code": res.get("exit"), "timeout": bool(res.get("timeout")), "crash": bool(res.get("crash5063")),
            "oom": bool(res.get("oom_kill", mem.get("oom_kill"))), "infra_signal": res.get("infra_signal"),
            "root_last_turn": rt.end_kind(root) if root is not None else "none"}


def deliverable_summary(res: dict):
    d = res.get("deliverable")
    if not d:
        return None
    if d.get("kind") == "changed_files":
        files = d.get("files") or {}
        unchanged = sorted(f for f, ch in files.items() if not ch)
        return {"kind": "changed_files", "expected": len(files), "changed": d.get("changed"),
                "unchanged": unchanged[:8] + (["…"] if len(unchanged) > 8 else [])}
    return {"kind": "file", "name": d.get("name"), "exists": bool(d.get("exists")), "bytes": d.get("bytes"),
            "min_bytes": d.get("min_bytes"), "ok": bool(d.get("ok"))}


def analyse(run: dict) -> dict:
    """Everything the digest needs from one run, with full texts (the rendering cuts them)."""
    res, d = run["result"], Path(run["dir"])
    rid = res.get("id", run["key"])
    logs, sessions = rm.load_sessions(d)
    out = {"run": rid, "task_id": res.get("task"), "task_kind": task_kind(res), "deliverable": deliverable_summary(res),
           "process_s": res.get("seconds"), "log_errors": sorted({(log.get("error") or "")[:60] for log in logs if log.get("error")}),
           "sessions_unparsed": len(logs) - len(sessions)}
    if not sessions:
        out.update(exit=exit_summary(res, None), agents=[], note="no session log could be read")
        return out
    by_id = {s["id"]: s for s in sessions}
    roots = [s for s in sessions if not s["parent"] or s["parent"] not in by_id]
    root = min(roots, key=lambda s: (s["depth"], s["first_time"] or 0)) if roots else sessions[0]
    firsts = [s["first_time"] for s in sessions if s["first_time"] is not None]
    lasts = [s["last_time"] for s in sessions if s["last_time"] is not None]
    t0 = min(firsts) if firsts else None
    order = sorted((s for s in sessions if s is not root), key=lambda s: (s["first_time"] if s["first_time"] is not None else float("inf"), s["id"]))
    name = {root["id"]: "A0"}
    for i, s in enumerate(order, 1):
        name[s["id"]] = f"A{i}"
    out["exit"] = exit_summary(res, root)

    # task texts: root = first user message; subagents = the prompt of the delegation call that started them
    task_text = {}
    first_user = next((u["text"] for u in root["users"] if u["kind"] == "user"), "")
    task_text[root["id"]] = first_user
    out["_root_task"] = first_user
    spawn_rows = rt.spawn_rows(run["batch"], rid, sessions, t0)  # same iteration order as below
    calls = [(s, cid) for s in sessions for cid in s["call_order"] if s["calls"][cid]["name"] in SPAWN]
    assert len(calls) == len(spawn_rows)
    started_by = {}  # child session id -> (caller session, call id)
    for (s, cid), row in zip(calls, spawn_rows):
        if row["child"]:
            started_by[row["child"]] = (s, cid)
    for s in order:
        if s["id"] in started_by:
            caller, cid = started_by[s["id"]]
            task_text[s["id"]] = (caller["calls"][cid]["args"] or {}).get("prompt") or ""
        else:
            task_text[s["id"]] = next((u["text"] for u in s["users"] if u["kind"] == "user"), "")
    labels = {}
    for s in order:
        if s["id"] in started_by:
            caller, cid = started_by[s["id"]]
            labels[s["id"]] = (caller["calls"][cid]["args"] or {}).get("description") or s["label"]
        else:
            labels[s["id"]] = s["label"]

    # settlement notices and messages received, per receiver
    notices = collections.defaultdict(dict)  # child -> notice id -> (time, kind, closing)
    received = collections.defaultdict(list)  # receiver -> [(time, sender, text)]
    for p in sessions:
        for ib in p["inbox"]:
            for msg in ib["messages"]:
                src = msg.get("source") or {}
                sender = rm.norm_id(src.get("senderSessionId"))
                if src.get("kind") == "subagent-settled" and by_id.get(sender, {}).get("parent") == p["id"]:
                    kind, closing = closing_of(msg.get("content"))
                    notices[sender].setdefault(msg.get("id") or f"inbox@{ib['time']}", (ib["time"], kind, closing))
                elif src.get("kind") == "agent-message":
                    received[p["id"]].append((ib["time"], sender, message_text(msg.get("content"))))
        for u in p["users"]:
            if u["kind"] == "subagent-settled" and by_id.get(u["sender"], {}).get("parent") == p["id"]:
                kind, closing = closing_of(u["text"])
                notices[u["sender"]].setdefault(u["id"] or f"user@{u['time']}", (u["time"], kind, closing))

    # per-agent entries
    agents = []
    tree_calls = collections.Counter()
    for s in [root] + order:
        names = [s["calls"][cid]["name"] for cid in s["call_order"]]
        cnt = {"web_search": names.count("web_search"), "web_fetch": names.count("web_fetch"), "read": names.count("read") + names.count("read_image"),
               "write": names.count("write") + names.count("edit"), "bash": names.count("bash"), "delegate": sum(names.count(n) for n in SPAWN)}
        cnt["other"] = len(names) - sum(cnt.values())
        for k, v in cnt.items():
            tree_calls[k] += v
        own = task_text.get(s["id"], "")
        delegations, before, first_t = [], None, None
        substantive = 0
        for cid in s["call_order"]:
            c = s["calls"][cid]
            if c["name"] not in SPAWN:
                substantive += c["name"] in SUBSTANTIVE
                continue
            if before is None:
                before, first_t = substantive, sec(c["time"], s["first_time"])
            r = s["results"].get(cid)
            args = c["args"] or {}
            t = sec(c["time"], t0)
            prompt = args.get("prompt") or ""
            if r is None:
                delegations.append({"t": t, "no_result": True, "task_text": prompt, "overlap": overlap(prompt, own)})
                continue
            rejected = r["is_error"] or r["text"].lstrip().startswith("Error")
            if not rejected:
                m = rm.STARTED_RE.search(r["text"])
                child = rm.norm_id(m.group(1)) if m else next((k for k, v in started_by.items() if v == (s, cid)), None)
                delegations.append({"t": t, "child": name.get(child, child[:8] if child else "?"), "overlap": overlap(prompt, own),
                                    "foreground": args.get("run_in_background") is False or None})
                continue
            reason = reject_reason(s, cid)
            last = delegations[-1] if delegations else None
            if last and last.get("rejected") == reason and last.get("task_text") == prompt:
                last["n"] = last.get("n", 1) + 1
                last["t"] = [last["t"][0] if isinstance(last["t"], list) else last["t"], t]
            else:
                delegations.append({"t": t, "rejected": reason, "task_text": prompt, "overlap": overlap(prompt, own)})
        entry = {"agent": name[s["id"]], "sid": s["id"][:8], "depth": s["depth"], "parent": name.get(s["parent"]) if s["parent"] in by_id else None,
                 "label": labels.get(s["id"]), "task_text": own if s is not root else None,
                 "start_s": sec(s["first_time"], t0), "end_s": sec(s["last_time"], t0), "end": rt.end_kind(s), "calls": cnt,
                 "turns": len(s["turns"])}
        if delegations:
            entry["delegations"] = delegations
            entry["before_first_delegation"] = {"substantive_calls": before, "seconds_after_start": first_t}
            entry["max_identical_rejections_in_a_row"] = max((x.get("n", 1) for x in delegations if x.get("rejected")), default=0)
        if s is not root:
            mine = sorted(notices.get(s["id"], {}).values(), key=lambda x: x[0] if x[0] is not None else -1)
            if mine:
                t_n, kind, closing = mine[-1]
                entry["handback"] = {"settled_s": sec(t_n, t0), "settled_kind": kind, "closing_chars": len(closing) if closing is not None else None,
                                     "closing_text": closing}
            else:
                entry["handback"] = {"settled_s": None, "settled_kind": None, "note": "no settlement notice reached the parent (process ended first)"}
            sent = [(t, tx) for (t, snd, tx) in received.get(s["parent"], []) if snd == s["id"]]
            if sent:
                entry["messages_to_parent"] = {"n": len(sent), "chars": sum(len(tx) for _, tx in sent),
                                               "last_s": sec(sent[-1][0], t0), "last_text": sent[-1][1]}
        agents.append(entry)
    out["agents"] = agents
    out["tree"] = {"agents": len(sessions), "by_depth": dict(sorted(collections.Counter(s["depth"] for s in order).items())),
                   "spawn_calls": len(calls), "accepted": sum(1 for r in spawn_rows if r["outcome"] == "accepted"),
                   "rejected_depth": sum(1 for r in spawn_rows if r["reject_kind"] == "depth"),
                   "rejected_cap": sum(1 for r in spawn_rows if r["reject_kind"] == "cap"),
                   "rejected_other": sum(1 for r in spawn_rows if r["outcome"] == "rejected" and r["reject_kind"] == "other"),
                   "root_turns": len(root["turns"]), "calls": dict(tree_calls)}
    root_sf = agents[0]["calls"]["web_search"] + agents[0]["calls"]["web_fetch"]
    tree_sf = tree_calls["web_search"] + tree_calls["web_fetch"]
    out["search_fetch"] = {"root_web_search": agents[0]["calls"]["web_search"], "root_web_fetch": agents[0]["calls"]["web_fetch"],
                           "tree_web_search": tree_calls["web_search"], "tree_web_fetch": tree_calls["web_fetch"],
                           "root_share": round(root_sf / tree_sf, 2) if tree_sf else None}

    # times
    ends = [b for _, b, _ in root["turns"] if b is not None]
    t_ans = max(ends) if ends else None
    writes = [(r["time"], s, c) for s in sessions for cid, c in s["calls"].items() if c["name"] in ("write", "edit")
              for r in [s["results"].get(cid)] if r and r["time"] is not None]
    last_write = max(writes, key=lambda x: x[0]) if writes else None
    kid_first = [s["first_time"] for s in order if s["first_time"] is not None]
    out["times_s"] = {"first_subagent_start": sec(min(kid_first), t0) if kid_first else None,
                      "last_write": sec(last_write[0], t0) if last_write else None, "final_answer": sec(t_ans, t0),
                      "last_event": sec(max(lasts), t0) if lasts else None, "process": res.get("seconds")}
    still = [s for s in order if t_ans is not None and s["last_time"] is not None and s["last_time"] > t_ans + AFTER_ANSWER_S * 1000]
    out["kids_after_answer"] = {"n": len(still), "agents": [f"{name[s['id']]} (ended {sec(s['last_time'], t0)} s)" for s in still]}

    # root timeline (each event keeps its millisecond time in "_ms" for the sort; render drops it)
    tl = []
    root_spawn = [(cid, s) for (s, cid) in calls if s is root]
    if root_spawn:
        first_cid = root_spawn[0][0]
        t_first = root["calls"][first_cid]["time"]
        same = [cid for cid, _ in root_spawn if abs((root["calls"][cid]["time"] or 0) - (t_first or 0)) <= 2000]
        acc = [name.get(c, "?") for c in [r["child"] for (s, cid), r in zip(calls, spawn_rows) if s is root and cid in same and r["outcome"] == "accepted"]]
        rej = [r["reject_kind"] or "other" for (s, cid), r in zip(calls, spawn_rows) if s is root and cid in same and r["outcome"] == "rejected"]
        tl.append({"t": sec(t_first, t0), "_ms": t_first, "e": f"first delegation: {len(same)} call(s) within 2 s, accepted {len(acc)} ({', '.join(acc) or '-'})"
                   + (f", rejected {len(rej)} ({', '.join(sorted(set(rej)))})" if rej else "")})
    bursts, cur = [], []
    for (s, cid), row in zip(calls, spawn_rows):
        if s is not root or row["outcome"] != "rejected":
            continue
        t = root["calls"][cid]["time"]
        if cur and t is not None and cur[-1][0] is not None and t - cur[-1][0] > BURST_GAP_S * 1000:
            bursts.append(cur)
            cur = []
        cur.append((t, row["reject_kind"] or "other"))
    if cur:
        bursts.append(cur)
    for b in bursts:
        kinds = collections.Counter(k for _, k in b)
        tl.append({"t": sec(b[0][0], t0), "_ms": b[0][0], "e": f"rejection burst: {len(b)} delegation call(s) rejected between {sec(b[0][0], t0)} and {sec(b[-1][0], t0)} s ("
                   + ", ".join(f"{ {'depth': 'depth limit', 'cap': 'active-child limit'}.get(k, k)} ×{n}" for k, n in sorted(kinds.items())) + ")"})
    sends = []  # (ms, head of the message, target) of the root's delivered send_message calls; same head within 5 s -> one event
    for cid in root["call_order"]:
        c = root["calls"][cid]
        if c["name"] == rm.SEND_TOOL:
            target = rm.norm_id((c["args"] or {}).get("agent_id"))
            r = root["results"].get(cid)
            if r and not r["is_error"] and c["time"] is not None:
                sends.append((c["time"], head((c["args"] or {}).get("message"), 80), name.get(target, "?")))
        elif c["name"] == "interrupt_agent":
            target = rm.norm_id((c["args"] or {}).get("agent_id"))
            tl.append({"t": sec(c["time"], t0), "_ms": c["time"], "e": f"root interrupted {name.get(target, '?')}"})
    i = 0
    while i < len(sends):
        j = i
        while j + 1 < len(sends) and sends[j + 1][1] == sends[i][1] and sends[j + 1][0] - sends[i][0] <= 5000:
            j += 1
        tl.append({"t": sec(sends[i][0], t0), "_ms": sends[i][0], "e": f"root sent a message to {', '.join(x[2] for x in sends[i:j + 1])}: \"{sends[i][1]}\""})
        i = j + 1
    settle = []
    for s in order:
        if s["parent"] != root["id"]:
            continue
        mine = sorted(notices.get(s["id"], {}).values(), key=lambda x: x[0] if x[0] is not None else -1)
        if mine:
            t_n, kind, closing = mine[-1]
            settle.append({"t": sec(t_n, t0), "_ms": t_n, "e": f"{name[s['id']]} settled: {kind or '?'}, closing message {len(closing) if closing else 0} chars",
                           "_short": f"{name[s['id']]} {sec(t_n, t0)}s {kind or '?'}/{len(closing) if closing else 0}"})
    out["_settlements"] = settle  # render() shows them one per line (level 0-1) or merged into one line (level 2+)
    if last_write:
        path = ((last_write[2]["args"] or {}).get("file_path") or "?").split("/workspace/")[-1]
        tl.append({"t": sec(last_write[0], t0), "_ms": last_write[0], "e": f"last file write by {name.get(last_write[1]['id'], '?')}: {path}"})
    if t_ans is not None:
        tl.append({"t": sec(t_ans, t0), "_ms": t_ans, "e": f"final answer (root's last turn ended: {rt.end_kind(root)}); subagents still running: {len(still)}"
                   + (" (" + ", ".join(name[s['id']] for s in still) + ")" if still else "")})
    out["root_timeline"] = tl

    # final answer
    root_log = next((log for log in logs if log.get("header") and rm.norm_id(log["header"].get("id")) == root["id"]), None)
    t_text, text = last_text_message(root_log) if root_log else (None, "")
    out["final_answer"] = {"t": sec(t_text, t0), "chars": len(text), "text": text}

    # after the last write
    if last_write and t_ans is not None:
        after = collections.Counter(root["calls"][cid]["name"] for cid in root["call_order"] if (root["calls"][cid]["time"] or 0) > last_write[0])
        out["root_after_last_write"] = {"seconds_to_final_answer": round((t_ans - last_write[0]) / 1000, 1), "root_calls": dict(sorted(after.items()))}

    # repeated queries, shared pages, shared files
    q_agents = collections.defaultdict(list)
    for s in sessions:
        for cid in s["call_order"]:
            c = s["calls"][cid]
            if c["name"] == "web_search":
                qs = (c["args"] or {}).get("queries")
                if isinstance(qs, str):
                    qs = [qs]
                for q in qs or []:
                    q_agents[norm_query(q)].append(name[s["id"]])
    total = sum(len(v) for v in q_agents.values())
    top = sorted(((len(v), q, v) for q, v in q_agents.items() if len(v) > 1), key=lambda x: (-x[0], x[1]))[:5]
    out["repeated_queries"] = {"total": total, "distinct": len(q_agents), "duplicates": total - len(q_agents),
                               "same_agent_repeats": sum(n - 1 for n, _, v in [(len(v), q, v) for q, v in q_agents.items()] for a, n in collections.Counter(v).items() if n > 1),
                               "top": [{"q": head(q, 90), "n": n, "agents": v} for n, q, v in top]}
    url_agents = collections.defaultdict(set)
    for s in sessions:
        for cid in s["call_order"]:
            c = s["calls"][cid]
            if c["name"] == "web_fetch" and (c["args"] or {}).get("url"):
                url_agents[str(c["args"]["url"]).strip()].add(name[s["id"]])
    shared = sorted(((u, sorted(a)) for u, a in url_agents.items() if len(a) > 1), key=lambda x: (-len(x[1]), x[0]))
    out["shared_pages"] = {"urls_fetched": len(url_agents), "by_2plus_agents": len(shared), "examples": [{"url": head(u, 80), "agents": a} for u, a in shared[:5]]}
    file_agents = collections.defaultdict(set)
    for s in sessions:
        for cid in s["call_order"]:
            c = s["calls"][cid]
            if c["name"] in ("write", "edit") and (c["args"] or {}).get("file_path"):
                file_agents[str(c["args"]["file_path"]).split("/workspace/")[-1]].add(name[s["id"]])
    sharedf = sorted(((f, sorted(a)) for f, a in file_agents.items() if len(a) > 1), key=lambda x: (-len(x[1]), x[0]))
    out["shared_files"] = {"files_written": len(file_agents), "by_2plus_agents": len(sharedf), "examples": [{"file": head(f, 80), "agents": a} for f, a in sharedf[:5]]}

    # review waves
    lw = last_write[0] if last_write else None
    after_lw = [s for s in order if lw is not None and s["first_time"] is not None and s["first_time"] > lw]
    like = [s for s in order if REVIEW_RE.search(labels.get(s["id"]) or "")]
    out["review"] = {"last_write_s": sec(lw, t0) if lw else None,
                     "after_last_write": {"subagents": len(after_lw), "waves": waves([sec(s["first_time"], t0) for s in after_lw]),
                                          "agents": [name[s["id"]] for s in after_lw]},
                     "review_like": {"subagents": len(like), "waves": waves([sec(s["first_time"], t0) for s in like]),
                                     "agents": [f"{name[s['id']]} ({head(labels.get(s['id']), 40)}) at {sec(s['first_time'], t0)} s" for s in like]}}
    return out


def render(a: dict, level: int) -> dict:
    """The digest at one level of the text-limit ladder."""
    lim = LADDER[level]
    d = {"run": a["run"], "task_id": a["task_id"], "task_kind": a["task_kind"]}
    if "note" in a:
        d["note"] = a["note"]
    prompt = a.get("_root_task") or ""
    d["task_prompt_head"] = head(prompt, lim["prompt"])
    if len(prompt) > lim["prompt"]:
        d["task_prompt_tail"] = "…" + re.sub(r"[\r\n\t]+", " ", prompt).strip()[-150:]
    d["task_prompt_chars"] = len(prompt)
    d["deliverable"] = a.get("deliverable")
    d["exit"] = a["exit"]
    for k in ("times_s", "tree", "search_fetch", "kids_after_answer"):
        if k in a:
            d[k] = a[k]
    agents = []
    for e in a.get("agents") or []:
        x = {k: e[k] for k in ("agent", "depth", "parent", "label", "start_s", "end_s", "end", "calls")}
        if e["depth"] < 2:
            x.pop("parent")  # a depth-1 agent's parent is A0 (the digest says so in session_ids' legend line)
        x["calls"] = {k: v for k, v in e["calls"].items() if v}
        if e["agent"] != "A0":
            x["task_head"] = head(e["task_text"], lim["task"])
            x["task_chars"] = len(e["task_text"] or "")
        if "delegations" in e:
            x["before_first_delegation"] = e["before_first_delegation"]
            ds = []
            for dl in e["delegations"]:
                y = {"t": dl["t"]}
                if "child" in dl:
                    y["child"] = dl["child"]
                    if dl.get("foreground"):
                        y["foreground"] = True
                elif "rejected" in dl:
                    y["rejected"] = dl["rejected"]
                    if dl.get("n", 1) > 1:
                        y["n"] = dl["n"]
                    y["task_head"] = head(dl["task_text"], lim["child_task"])
                else:
                    y["no_result"] = True
                    y["task_head"] = head(dl["task_text"], lim["child_task"])
                y["overlap"] = dl.get("overlap")
                ds.append(y)
            x["delegations"] = ds
            x["max_identical_rejections_in_a_row"] = e["max_identical_rejections_in_a_row"]
        if "handback" in e:
            h = dict(e["handback"])
            closing = h.pop("closing_text", None)
            if closing:
                h["closing_head"] = head(closing, lim["handback"])
            x["handback"] = h
        if "messages_to_parent" in e:
            m = dict(e["messages_to_parent"])
            last = m.pop("last_text", "")
            if lim["message"]:
                m["last_head"] = head(last, lim["message"])
            x["messages_to_parent"] = m
        agents.append(x)
    d["session_ids"] = {e["agent"]: e["sid"] for e in a.get("agents") or []}
    d["agents"] = agents
    if "root_timeline" in a:
        tl = list(a["root_timeline"])
        settle = a.get("_settlements") or []
        if level >= 2 and settle:
            tl.append({"t": settle[0]["t"], "_ms": settle[0]["_ms"], "e": "settlement notices received (agent, time, ending/closing chars): " + "; ".join(x["_short"] for x in settle)})
        else:
            tl += settle
        tl.sort(key=lambda x: (x["_ms"] if x["_ms"] is not None else -1, x["e"]))
        d["root_timeline"] = [{"t": x["t"], "e": x["e"]} for x in tl]
    if "final_answer" in a:
        fa = a["final_answer"]
        d["final_answer"] = {"t": fa["t"], "chars": fa["chars"], "head": head(fa["text"], lim["answer"])}
    for k in ("root_after_last_write", "repeated_queries", "shared_pages", "shared_files", "review"):
        if k in a:
            d[k] = a[k]
    if a.get("log_errors") or a.get("sessions_unparsed"):
        d["log_problems"] = {"errors": a.get("log_errors"), "sessions_unparsed": a.get("sessions_unparsed")}
    d["text_limits"] = {"level": level, **lim}
    return d


def dumps(obj, width: int = 150) -> str:
    """Valid JSON, one field per line, but a dict or list whose one-line form is at most `width` characters (and any
    list of scalars) stays on one line: readable, line-addressable for the check form, and not whitespace-heavy."""
    def inline(o):
        return json.dumps(o, ensure_ascii=False, separators=(", ", ": "))

    def rec(o, depth):
        s = inline(o)
        if not isinstance(o, (dict, list)) or len(s) <= width or (isinstance(o, list) and all(not isinstance(x, (dict, list)) for x in o)):
            return s
        pad, pad0 = " " * (depth + 1), " " * depth
        if isinstance(o, dict):
            return "{\n" + ",\n".join(f"{pad}{json.dumps(k, ensure_ascii=False)}: {rec(v, depth + 1)}" for k, v in o.items()) + "\n" + pad0 + "}"
        return "[\n" + ",\n".join(f"{pad}{rec(v, depth + 1)}" for v in o) + "\n" + pad0 + "]"
    return rec(obj, 0)


def one(args: tuple) -> dict:
    run, max_chars, fixed = args
    try:
        a = analyse(run)
    except Exception as exc:  # noqa: BLE001 - a run whose logs cannot be read still gets a stub digest
        a = {"run": run["result"].get("id", run["key"]), "task_id": run["result"].get("task"), "task_kind": task_kind(run["result"]),
             "deliverable": deliverable_summary(run["result"]), "exit": exit_summary(run["result"], None), "agents": [],
             "note": f"digest failed: {type(exc).__name__}: {str(exc)[:160]}"}
    text0 = dumps(render(a, 0))
    level_used, text, d = 0, text0, render(a, 0)
    if not fixed and len(text0) > max_chars:
        for level in range(1, len(LADDER)):
            d = render(a, level)
            text = dumps(d)
            level_used = level
            if len(text) <= max_chars:
                break
    return {"id": a["run"], "task": a.get("task_id"), "text": text, "chars": len(text), "chars_at_full_limits": len(text0),
            "level": level_used, "agents": len(a.get("agents") or []), "note": a.get("note", "")}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch", type=Path)
    ap.add_argument("--out", type=Path, default=None, help="default results/digests/<batch>/ next to the batch's results dir")
    ap.add_argument("--ids", default="", help="only these run ids (comma-separated)")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--max-chars", type=int, default=5000)
    ap.add_argument("--fixed-limits", action="store_true", help="keep the level-0 text limits whatever the size")
    a = ap.parse_args()
    out = a.out or (a.batch.parent.parent / "digests" / a.batch.name)
    out.mkdir(parents=True, exist_ok=True)
    runs, notes = rm.discover(a.batch)
    want = set(filter(None, a.ids.split(",")))
    if want:
        runs = [r for r in runs if r["key"] in want or r["result"].get("id") in want]
    for r in runs:
        r["dir"] = str(r["dir"])
    runs.sort(key=lambda r: r["key"])
    jobs = [(r, a.max_chars, a.fixed_limits) for r in runs]
    if a.jobs > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=a.jobs) as ex:
            results = list(ex.map(one, jobs, chunksize=1))
    else:
        results = [one(j) for j in jobs]
    rows = []
    for r in results:
        (out / f"{r['id']}.json").write_text(r["text"] + "\n", encoding="utf-8")
        rows.append({k: r[k] for k in ("id", "task", "chars", "chars_at_full_limits", "level", "agents", "note")})
    with open(out / "digest-stats.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "task", "chars", "chars_at_full_limits", "level", "agents", "note"])
        w.writeheader()
        w.writerows(rows)
    sizes = sorted(r["chars"] for r in rows)
    print(f"{a.batch.name}: {len(rows)} digests -> {out}; chars min {sizes[0] if sizes else '-'} median {sizes[len(sizes) // 2] if sizes else '-'} "
          f"max {sizes[-1] if sizes else '-'}; in 3000-5000: {sum(3000 <= c <= 5000 for c in sizes)}; above 5000: {sum(c > 5000 for c in sizes)}; "
          f"levels used: {dict(sorted(collections.Counter(r['level'] for r in rows).items()))}; notes {len(notes)}; failed {sum(1 for r in rows if r['note'])}")


if __name__ == "__main__":
    main()
