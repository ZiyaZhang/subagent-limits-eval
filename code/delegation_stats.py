#!/usr/bin/env python3
"""Delegation-tree statistics for DSH session logs.

Reads every file named ``session*.jsonl`` under each input directory (an
exported ZIP, extracted: ``session.v3.jsonl`` plus ``subagents/*/session.v3.jsonl``),
rebuilds the parent/child tree from the session headers, and reports:

- how many child sessions exist at each delegation depth, and who created them;
- delegation tool calls by tool name, and rejected starts (depth or capacity limit);
- the peak number of child sessions with an open turn at the same time;
- token usage (uncached input, cache read, output; the buckets are disjoint) for
  the root and for all children, plus auxiliary search-request counts;
- how many child results reached a parent, by message kind.

Usage:
  delegation_stats.py DIR [DIR ...] [--json OUT.json]
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

# DeepSeek public API, deepseek-flash, CNY per 1M tokens (api-docs.deepseek.com pricing page, read 2026-10-01).
# Off-peak (weekday 9-12/14-18 Beijing time are peak; all other times off-peak) is exactly half of peak.
PRICES_CNY_PER_M = {"peak": {"inputTokens": 2.0, "cacheReadTokens": 0.04, "outputTokens": 8.0},
                    "offpeak": {"inputTokens": 1.0, "cacheReadTokens": 0.02, "outputTokens": 4.0}}


def cost_cny(usage: dict, period: str = "peak") -> float:
    price = PRICES_CNY_PER_M[period]
    return sum(usage.get(k, 0) * v for k, v in price.items()) / 1_000_000


DELEGATION_TOOLS = ("subagent", "subagent_fork", "workflow", "spawn_teammate", "ralph")
DEPTH_REJECT = re.compile(r"exceeds maxDepth|depth \d+ exceeds", re.I)
CAPACITY_REJECT = re.compile(r"subagent limit reached|ACTIVATION_LIMIT_REACHED|total agent cap|AGENT_CAP", re.I)


def norm_id(value: str | None) -> str | None:
    if value is None:
        return None
    return value[len("session-"):] if value.startswith("session-") else value


def text_of(content) -> str:
    out = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    out.append(block.get("text", ""))
                elif block.get("type") == "tool-result":
                    out.append(text_of(block.get("content")))
    elif isinstance(content, str):
        out.append(content)
    return "\n".join(out)


def read_lines(path: Path) -> list[str]:
    """Lines of one session log, split on "\\n" only: str.splitlines() also breaks inside JSON strings at
    U+2028, U+2029 and U+0085, and read_session silently skipped the broken halves. The number of non-empty
    lines that are not valid JSON (expected 0) is kept in read_lines.unparsable[str(path)]. A damaged log does
    not raise here (plan 7.2(f)): a truncated or corrupt zstd stream keeps the frames and blocks that decoded,
    bytes that are not UTF-8 are replaced, and the problem is kept in read_lines.errors[str(path)]."""
    error = None
    if path.name.endswith(".zstd"):
        import zstandard
        rest, chunks = path.read_bytes(), []
        try:
            while rest:  # frame by frame; an incomplete last frame keeps its complete blocks
                frame = zstandard.ZstdDecompressor().decompressobj()
                chunks.append(frame.decompress(rest))
                if not frame.eof:
                    error = "zstd: truncated stream"
                    break
                rest = frame.unused_data
        except zstandard.ZstdError as exc:
            error = f"zstd: {exc}"
        data = b"".join(chunks)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            text = data.decode("utf-8", errors="replace")
            error = error or f"utf-8: {exc.reason} at byte {exc.start}"
    else:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            text = path.read_text(encoding="utf-8", errors="replace")
            error = f"utf-8: {exc.reason} at byte {exc.start}"
    if error:
        read_lines.__dict__.setdefault("errors", {})[str(path)] = error
    lines = text.split("\n")
    if lines and not lines[-1]:
        lines.pop()  # the newline that ends the last record
    bad = 0
    for line in lines:
        if line.strip():
            try:
                json.loads(line)
            except ValueError:
                bad += 1
    read_lines.__dict__.setdefault("unparsable", {})[str(path)] = bad
    return lines


def read_session(path: Path) -> dict:
    lines = read_lines(path)
    header = json.loads(lines[0])
    rec = {
        "file": str(path),
        "id": norm_id(header.get("id")),
        "parent": norm_id(header.get("parentSession")),
        "depth": header.get("delegationDepth", 0),
        "origin": header.get("origin"),
        "created": header.get("createdAt"),
        "provider": None, "mode": None, "label": None, "model": None, "effort": None,
        "first_time": None, "last_time": None,
        "turns": [], "tool_calls": collections.Counter(),
        "delegation_calls": [], "depth_rejects": 0, "capacity_rejects": 0, "tool_errors": 0,
        "usage": collections.Counter(), "assistant_messages": 0, "failed_attempts": 0,
        "search_aux_requests": 0, "catalog_children": [],
        "received_from_children": collections.Counter(), "received_chars": collections.Counter(),
    }
    open_turn = None
    call_names = {}
    own = lines[1:]
    if header.get("isSeeded"):  # a forked agent: skip the copy of its parent's history (see run_metrics.read_log)
        cut = next((i for i, line in enumerate(own) if '"session/end-seed"' in line), len(own))
        own = own[cut:]
    for line in own:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype, data, t = ev.get("type"), ev.get("data") or {}, ev.get("time")
        if t is not None:
            rec["first_time"] = t if rec["first_time"] is None else min(rec["first_time"], t)
            rec["last_time"] = t if rec["last_time"] is None else max(rec["last_time"], t)
        if etype == "subagent/descriptor":
            rec.update(provider=data.get("provider"), mode=data.get("mode"), label=data.get("label"))
            rec["model"] = data.get("agentModel") or rec["model"]
            rec["effort"] = data.get("agentReasoningEffort") or rec["effort"]
        elif etype == "request/header":
            cfg = (data.get("header") or {}).get("config") or {}
            if rec["model"] is None:
                rec["model"] = cfg.get("model")
            if rec["effort"] is None:
                rec["effort"] = cfg.get("reasoningEffort")
        elif etype == "turn/start":
            open_turn = t
        elif etype == "turn/end":
            if open_turn is not None and t is not None:
                rec["turns"].append((open_turn, t))
            open_turn = None
        elif etype == "assistant/message":
            rec["assistant_messages"] += 1
            for key, value in (data.get("usage") or {}).items():
                if isinstance(value, (int, float)) and key != "totalTokens":
                    rec["usage"][key] += value
        elif etype == "assistant/attempt":
            rec["failed_attempts"] += 1
        elif etype == "tool/call":
            name = data.get("name")
            rec["tool_calls"][name] += 1
            call_names[data.get("callId")] = name
            if name in DELEGATION_TOOLS:
                rec["delegation_calls"].append({"time": t, "tool": name, "callId": data.get("callId")})
        elif etype == "tool/result":
            message = data.get("message") or {}
            if "toolCallId" in message:
                # v4: the message itself is the result.
                results = [message]
            else:
                # v3: results are tool-result blocks inside the message content.
                results = [b for b in message.get("content") or [] if b.get("type") == "tool-result"]
            for block in results:
                body = text_of(block.get("content"))
                if block.get("isError"):
                    rec["tool_errors"] += 1
                rejected = block.get("isError") or body.lstrip().startswith("Error")
                if rejected and call_names.get(block.get("toolCallId")) in DELEGATION_TOOLS:
                    if DEPTH_REJECT.search(body):
                        rec["depth_rejects"] += 1
                    elif CAPACITY_REJECT.search(body):
                        rec["capacity_rejects"] += 1
        elif etype == "subagent/catalog":
            rec["catalog_children"].append(norm_id(data.get("childId")))
        elif etype == "web/deepseek-search-llm-request":
            rec["search_aux_requests"] += 1
        elif etype == "user/message":
            kind = (data.get("source") or {}).get("kind")
            if kind in ("agent-message", "subagent-settled"):
                rec["received_from_children"][kind] += 1
                rec["received_chars"][kind] += len(text_of(data.get("content")))
    if open_turn is not None and rec["last_time"] is not None:
        rec["turns"].append((open_turn, rec["last_time"]))
    return rec


def peak_overlap(intervals) -> tuple[int, int | None]:
    points = []
    for start, end in intervals:
        points.append((start, 1))
        points.append((end, -1))
    points.sort(key=lambda p: (p[0], p[1]))
    current = best = 0
    best_time = None
    for time, delta in points:
        current += delta
        if current > best:
            best, best_time = current, time
    return best, best_time


def analyze(directory: Path) -> dict:
    files = sorted(set(directory.rglob("session*.jsonl")) | set(directory.rglob("session*.jsonl.zstd")))
    sessions = [read_session(path) for path in files]
    by_id = {s["id"]: s for s in sessions}
    roots = [s for s in sessions if not s["parent"] or s["parent"] not in by_id]
    root = min(roots, key=lambda s: s["depth"])
    children = [s for s in sessions if s is not root]
    kids = collections.defaultdict(list)
    for s in children:
        kids[s["parent"]].append(s["id"])

    def subtree(sid):
        total = 1
        for child in kids.get(sid, []):
            total += subtree(child)
        return total

    depth_counts = collections.Counter(s["depth"] for s in children)
    fanout = [len(kids.get(s["id"], [])) for s in sessions if kids.get(s["id"])]
    running = [iv for s in children for iv in s["turns"]]
    running_bg = [iv for s in children if s["mode"] == "continuable" for iv in s["turns"]]
    running_fg = [iv for s in children if s["mode"] != "continuable" for iv in s["turns"]]
    alive = [(s["created"] or s["first_time"], s["last_time"]) for s in children if s["last_time"]]
    peak_running, peak_running_at = peak_overlap(running)
    peak_alive, _ = peak_overlap(alive)
    peak_bg, _ = peak_overlap(running_bg)
    peak_fg, _ = peak_overlap(running_fg)

    def usage_sum(group):
        total = collections.Counter()
        for s in group:
            total.update(s["usage"])
        return {k: int(v) for k, v in total.items()}

    tools_all = collections.Counter()
    for s in sessions:
        tools_all.update(s["tool_calls"])
    deleg_by_tool = collections.Counter(c["tool"] for s in sessions for c in s["delegation_calls"])
    received = collections.Counter()
    received_chars = collections.Counter()
    for s in sessions:
        received.update(s["received_from_children"])
        received_chars.update(s["received_chars"])
    start = min(s["first_time"] for s in sessions if s["first_time"])
    end = max(s["last_time"] for s in sessions if s["last_time"])
    branch = [
        {"label": by_id[c]["label"], "provider": by_id[c]["provider"], "subtree_sessions": subtree(c)}
        for c in kids.get(root["id"], [])
    ]
    return {
        "input": str(directory),
        "root_id": root["id"],
        "sessions": len(sessions),
        "children": len(children),
        "children_by_depth": dict(sorted(depth_counts.items())),
        "max_depth": max(depth_counts) if depth_counts else 0,
        "children_by_provider": dict(collections.Counter(s["provider"] for s in children)),
        "children_by_mode": dict(collections.Counter(s["mode"] for s in children)),
        "child_models": dict(collections.Counter(f'{s["model"]}@{s["effort"]}' for s in children)),
        "direct_children_of_root": len(kids.get(root["id"], [])),
        "children_created_by_children": len(children) - len(kids.get(root["id"], [])),
        "fanout_per_delegating_session": {"sessions": len(fanout), "mean": round(sum(fanout) / len(fanout), 2) if fanout else 0, "max": max(fanout) if fanout else 0},
        "delegation_calls_by_tool": dict(deleg_by_tool),
        "depth_rejects": sum(s["depth_rejects"] for s in sessions),
        "capacity_rejects": sum(s["capacity_rejects"] for s in sessions),
        "peak_children_running": peak_running,
        "peak_children_alive": peak_alive,
        "peak_running_background": peak_bg,
        "peak_running_foreground_oneshot": peak_fg,
        "wall_clock_minutes": round((end - start) / 60000, 1),
        "usage_root": usage_sum([root]),
        "usage_children": usage_sum(children),
        "usage_all": usage_sum(sessions),
        "cost_cny_peak": {"root": round(cost_cny(usage_sum([root])), 3), "children": round(cost_cny(usage_sum(children)), 3),
                          "all": round(cost_cny(usage_sum(sessions)), 3)},
        "assistant_messages": {"root": root["assistant_messages"], "children": sum(s["assistant_messages"] for s in children)},
        "failed_attempts": sum(s["failed_attempts"] for s in sessions),
        "search_aux_requests": sum(s["search_aux_requests"] for s in sessions),
        "web_tool_calls": {k: tools_all[k] for k in ("web_search", "web_fetch") if tools_all[k]},
        "results_received_from_children": {k: {"messages": received[k], "chars": received_chars[k]} for k in received},
        "root_branches": branch,
    }


def fmt_usage(u: dict) -> str:
    unc, cache, out = u.get("inputTokens", 0), u.get("cacheReadTokens", 0), u.get("outputTokens", 0)
    return f"uncached {unc:,} | cache-read {cache:,} | output {out:,} | sum {unc + cache + out:,}"


def print_text(r: dict) -> None:
    print(f"== {r['input']}")
    print(f"  sessions {r['sessions']} (root + {r['children']} children); wall clock {r['wall_clock_minutes']} min")
    print(f"  children by depth {r['children_by_depth']}; root created {r['direct_children_of_root']}, children created {r['children_created_by_children']}")
    print(f"  provider {r['children_by_provider']}; mode {r['children_by_mode']}; model {r['child_models']}")
    print(f"  delegation calls {r['delegation_calls_by_tool']}; rejected: depth {r['depth_rejects']}, capacity {r['capacity_rejects']}")
    print(f"  fan-out per delegating session {r['fanout_per_delegating_session']}")
    print(f"  peak children with an open turn {r['peak_children_running']} (background {r['peak_running_background']}, foreground one-shot {r['peak_running_foreground_oneshot']}); peak alive {r['peak_children_alive']}")
    print(f"  tokens root:     {fmt_usage(r['usage_root'])}")
    print(f"  tokens children: {fmt_usage(r['usage_children'])}")
    print(f"  cost at deepseek-flash peak price (CNY): {r['cost_cny_peak']} (off-peak is half; search-request fees not included)")
    print(f"  web tools {r['web_tool_calls']}; search auxiliary requests {r['search_aux_requests']}; failed attempts {r['failed_attempts']}")
    print(f"  results reaching parents {r['results_received_from_children']}")
    for b in r["root_branches"]:
        print(f"    branch {b['subtree_sessions']:>3} sessions  [{b['provider']}] {b['label']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dirs", nargs="+", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    results = [analyze(d) for d in args.dirs]
    for r in results:
        print_text(r)
    if args.json:
        args.json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}", file=sys.stderr)


if __name__ == "__main__":
    main()
