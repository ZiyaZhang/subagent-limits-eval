#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read what happened in one run, for picking the excerpts of the write-up's finding cards.

  run_excerpt.py RUN_DIR --tree
      the agents of the run (A0 = root, A1 ... in start order, the names of run_digest.py): depth, parent, label,
      tool-call counts, delegations (accepted / rejected), how it ended
  run_excerpt.py RUN_DIR --agent A3 [--from-s N] [--to-s M] [--max 300] [--kinds say,think,call,result,user] [--md]
      that agent's own timeline: what it said (说), what it reasoned when the log keeps it (想), every tool call
      (调用) with the head of its main argument, every result (结果, errors marked), every message it received (收到).
      --md prints a block that can be pasted into a card.

Reads the session logs only. Times are seconds from the run's first event.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
MAIN_ARG = {"web_search": "query", "web_fetch": "url", "bash": "command", "read": "file_path", "write": "file_path", "edit": "file_path",
            "subagent": "prompt", "subagent_fork": "prompt", "send_message": "message", "todo_write": "todos"}


def head(text, n: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n] + "…"


def run_of(d: Path) -> dict:
    return {"result": json.loads((d / "result.json").read_text(encoding="utf-8")), "dir": str(d), "key": d.name, "batch": d.parent.name}


def main() -> None:
    import run_digest as rd
    import run_metrics as rm
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", type=Path)
    ap.add_argument("--tree", action="store_true")
    ap.add_argument("--agent")
    ap.add_argument("--from-s", type=float, default=None)
    ap.add_argument("--to-s", type=float, default=None)
    ap.add_argument("--max", type=int, default=300)
    ap.add_argument("--kinds", default="say,think,call,result,user")
    ap.add_argument("--md", action="store_true")
    a = ap.parse_args()
    an = rd.analyse(run_of(a.run))
    agents = an.get("agents") or []
    if a.tree or not a.agent:
        print(f"run {an['run']} task {an.get('task_id')}: {len(agents)} agents; exit {an.get('exit')}")
        for e in agents:
            dl = e.get("delegations") or []
            acc = sum(1 for d in dl if "child" in d)
            rej = sum(d.get("n", 1) for d in dl if "rejected" in d)
            c = e["calls"]
            print(f"{'  ' * e['depth']}{e['agent']} depth {e['depth']} parent {e.get('parent') or '-'} [{e['start_s']}–{e['end_s']} s] "
                  f"search {c['web_search']} fetch {c['web_fetch']} bash {c['bash']} write {c['write']} | delegated {acc}, rejected {rej} | end {e['end']}"
                  + (f" | {head(e.get('label'), 60)}" if e.get("label") else ""))
        return
    entry = next((e for e in agents if e["agent"] == a.agent), None)
    if entry is None:
        raise SystemExit(f"no agent {a.agent}; there are {[e['agent'] for e in agents]}")
    logs, sessions = rm.load_sessions(a.run)
    t0 = min(s["first_time"] for s in sessions if s["first_time"] is not None)
    log = next(lg for lg in logs if lg.get("header") and rm.norm_id(lg["header"].get("id")).startswith(entry["sid"]))
    kinds = set(a.kinds.split(","))
    lines, names = [], {}
    for ev in log["events"]:
        t = ev.get("time")
        if not isinstance(t, (int, float)):
            continue
        s = (t - t0) / 1000
        if (a.from_s is not None and s < a.from_s) or (a.to_s is not None and s > a.to_s):
            continue
        d = ev.get("data") if isinstance(ev.get("data"), dict) else {}
        ty = ev.get("type")
        if ty == "assistant/message":
            for b in (d.get("message") or {}).get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and "say" in kinds and (b.get("text") or "").strip():
                    lines.append((s, "说", head(b["text"], a.max)))
                elif b.get("type") in ("reasoning", "thinking") and "think" in kinds:
                    txt = b.get("text") or b.get("thinking") or ""
                    if txt.strip():
                        lines.append((s, "想", head(txt, a.max)))
                elif b.get("type") == "tool-call":
                    names[b.get("toolCallId") or b.get("id")] = b.get("toolName") or b.get("name")
        elif ty == "tool/call" and "call" in kinds:
            args = rm.parse_args_json(d.get("arguments")) or {}
            name = d.get("name")
            names[d.get("callId")] = name
            key = MAIN_ARG.get(name)
            main_arg = args.get(key) if isinstance(args, dict) and key and args.get(key) not in (None, "", []) else args
            extra = f"（{head(args.get('description'), 50)}）" if isinstance(args, dict) and args.get("description") and name in ("subagent", "subagent_fork") else ""
            lines.append((s, f"调用 {name}{extra}", head(main_arg if not isinstance(main_arg, (dict, list)) else json.dumps(main_arg, ensure_ascii=False), a.max)))
        elif ty == "tool/result" and "result" in kinds:
            for block in rm.result_blocks(d):
                txt = rm.text_of(block.get("content"))
                lines.append((s, "结果（出错）" if block.get("isError") or txt.lstrip().startswith("Error") else "结果", head(txt, a.max)))
        elif ty == "user/message" and "user" in kinds:
            src = d.get("source") or {}
            lines.append((s, f"收到（{src.get('kind') or 'user'}）", head(rm.text_of(d.get("content")), a.max)))
    if a.md:
        print(f"> {a.agent}（第 {entry['depth']} 层）" + (f"，任务：{head(entry.get('task_text'), 160)}" if entry.get("task_text") else ""))
        for s, k, txt in lines:
            print(f"> - {int(s // 60)}:{int(s % 60):02d} **{k}** {txt}")
        return
    print(f"{a.agent} depth {entry['depth']} [{entry['start_s']}–{entry['end_s']} s], {len(lines)} lines")
    for s, k, txt in lines:
        print(f"[{s:7.0f}s] {k}: {txt}")


if __name__ == "__main__":
    main()
