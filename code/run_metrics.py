#!/usr/bin/env python3
"""Offline metrics for every run of a DSH subagent-experiment batch (code-stage-plan-draft.md, sections 3.4
and 5, with the corrections of appendix C). Reads the batch only; never starts DSH or uses the network.

Batch layouts (detected per batch):
  - run_matrix.py: run dirs <task>__<group>__r<rep>/ with result.json and home/sessions/; dirs without
    result.json are listed as skipped;
  - run_matrix_v2.py: random-id run dirs listed in manifest.jsonl, each with result.json and home/sessions/
    (--include-failed also reads the infrastructure failures kept in _failed/<id>/ with attempt.json).

Per run (times from the session logs, wall clock from result.json):
  slots         名额 reconstruction. A continuable (background) child holds a slot of its pool from the
                parent's subagent/subagent_fork call until the parent's agent/inbox/spliced event that inserts
                the child's subagent-settled notice (the user/message carrying that notice when there is no
                spliced event; the end of the run when there is neither). A successful send_message to a child
                whose slot was released wakes it and takes a slot again from the call (from the release when
                the send was waiting for the child's disposal). One-shot (foreground) children take no slot.
                The pool belongs to the nearest ancestor that is not a continuable child (the root, or a
                one-shot child): DSH dsh-subagent ActivationPool.reserve / materialize / rootPool /
                finishDisposal. Checks: at every "subagent limit reached" rejection with limit k, the
                occupancy of the caller's pool reaches exactly k inside the rejected call's call-to-result
                window; every successful start finds at most k-1 other slots taken; no pool exceeds k.
  turn_overlap  the existing peak of child sessions with an open turn (delegation_stats.py peak_running_*).
  time          G = union over all sessions of [step/start, last chunk of that step's stream]; T = union of
                tool call-to-result intervals, minus G; O = wall - G - T; non-generation time = T + O;
                agent_seconds = sum over sessions of each session's model time.
  steps         share of assistant replies with >= 2 tool calls; per-step tool batch time (first call to
                last result) P50/P95.
  conflicts     write/edit results with "file changed since it was read" or "has not been read".
  unfinished    child sessions with an open turn at the root's last event, and the files they wrote.
  duplicate     files read with the read tool by the root and by at least one child.
  api           failed attempts (assistant/attempt) by error code, sessions that ended with an error,
                median generation speed (output tokens / first-to-last chunk), median time to first chunk.
  cache         the root's first request: cache-read, uncached input and output tokens.
  config        system prompt sha256 without the working-directory line, tool list sha256 and names,
                projectRoot (agent-instructions baseline), cwd, whether the group or task id is visible, the
                first user message and whether it carries the encourage sentence as its group requires.
  paths         tool calls touching paths outside the run's own stage (the parent of the workspace): under
                /Users, under /private/tmp (= /tmp), or through ~ / $HOME (HOME is the stage's fakehome for
                run_matrix_v2 runs, /Users/<name> for old runs); references to the experiment directory; reads of
                /tmp files that neither an earlier tool call nor the same call of the run wrote. The last one is
                a static analysis of the commands and heuristic: reads come from read/grep/glob, `cd`, known
                reading commands (cat, grep, ls, python SCRIPT, ...) and file literals in inline code; writes from
                write/edit, redirections, curl -o, mkdir (relative names too: `cd /tmp && mkdir -p kp`), cp/mv
                targets, open(..., "w") and the like, and every file argument of helper functions, scripts and
                unfamiliar tools; a file inside a directory the run made counts as written; `for f in a b; do
                curl -o $f.txt` writes a.txt and b.txt; other computed names (-o "x_$i.html", f-strings,
                `fetch.sh URL name`) count as written patterns, which a later glob such as x_?.html matches. A
                script that builds its output name in code (open(f + ".txt", "w")) still yields a false flag, so
                the flagged paths are listed for review.
  bash          calls running another agent's CLI or a package runner as a real command word (not text in
                echo or comments), network commands (curl, wget, pip install, git clone, http(s) URLs),
                pytest runs, writes to test files.
  delegation    children by depth and mode, delegation calls by tool (skill, subagent_fork, foreground
                subagent calls), depth and capacity rejections; relay: whether the tasks the root writes to
                children carry the encourage sentence, "subagent" or "并行".
  log           unparsable log lines (expected 0) and damaged logs ("incomplete").

Usage:
  run_metrics.py BATCH_DIR [BATCH_DIR ...] --out OUT_DIR [--include-failed] [--encourage TEXT ...]
Writes OUT_DIR/runs/<batch>/<run>.json, OUT_DIR/summary.json (every run), OUT_DIR/summary.csv (one row per
run) and OUT_DIR/summary.md (tables and the slot-reconstruction check).
"""

from __future__ import annotations

import argparse
import collections
import csv
import fnmatch
import hashlib
import json
import os
import re
import statistics
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
EXP_ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
from delegation_stats import (CAPACITY_REJECT, DELEGATION_TOOLS, DEPTH_REJECT, cost_cny, norm_id,  # noqa: E402
                              peak_overlap, text_of)

SPAWN_TOOLS = ("subagent", "subagent_fork")
SEND_TOOL = "send_message"
FS_WRITE_TOOLS = ("write", "edit")
READ_TOOLS = ("read", "read_image")
SEARCH_TOOLS = ("grep", "glob")
STARTED_RE = re.compile(r"started subagent (\S+)")
LIMIT_RE = re.compile(r"subagent limit reached(?: \(active child limit: (\d+)\))?")
GROUP_K_RE = re.compile(r"K(\d+)$")
CWD_LINE_RE = re.compile(r"\n?^Your working directory is [^\n]*$", re.M)
STALE_TEXT = "file changed since it was read"
NOT_READ_TEXT = "has not been read"
# Provider error codes that mean the endpoint or the network failed (appendix C; run_matrix_v2 INFRA_CODES).
INFRA_CODES = frozenset({"TRANSPORT", "TIMEOUT", "SERVER", "RATE_LIMIT", "EMPTY_RESPONSE", "STREAM_CLOSED",
                         "MALFORMED_RESPONSE", "AUTH", "QUOTA", "ACCOUNT_QUOTA", "MISSING_CREDENTIAL",
                         "INVALID_CREDENTIAL", "REQUEST_EXTENSION"})
HTTP_5XX_RE = re.compile(r"HTTP_5\d\d$")
CRASH5063 = ("fatal load failure", "cannot read inbox state")
DEFAULT_ENCOURAGE = ("独立的子任务尽量交给 subagent 并行做。", "请把相互独立的部分交给 subagent 并行做。")
# Other agents' CLIs and package runners (plan 7.2(e) and appendix C; pnpx, yarn and uvx are runners too).
AGENT_CLIS = frozenset({"claude", "codex", "gemini", "opencode", "lark-cli", "gh", "hfai", "buddycn", "openclaw",
                        "kimi-daimon", "agy", "antigravity", "raft-computer", "screenpipe", "agent-browser", "dsh",
                        "npx", "npm", "pnpm", "uv", "pnpx", "yarn", "uvx"})
TEST_FILE_RE = re.compile(r"(^|/)(test_[^/]*\.py|[^/]*_test\.py|conftest\.py|pytest\.ini|tox\.ini|setup\.cfg)$")
EXAMPLES = 20  # list lengths kept in the per-run JSON


# ---------------------------------------------------------------- small helpers

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def rnd(value, digits: int = 2):
    return None if value is None else round(value, digits)


def percentile(values, q: float):
    """Linear-interpolation percentile (numpy's default); None for no values."""
    xs = sorted(values)
    if not xs:
        return None
    pos = (len(xs) - 1) * q / 100
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def median(values):
    return statistics.median(values) if values else None


def union(intervals) -> list:
    """Merged, sorted [start, end] pairs of the non-empty intervals."""
    merged = []
    for a, b in sorted((a, b) for a, b in intervals if num(a) and num(b) and b > a):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def measure(merged) -> float:
    return sum(b - a for a, b in merged)


def overlap(xs, ys) -> float:
    """Total length of the intersection of two merged interval lists."""
    i = j = 0
    total = 0.0
    while i < len(xs) and j < len(ys):
        a, b = max(xs[i][0], ys[j][0]), min(xs[i][1], ys[j][1])
        if b > a:
            total += b - a
        if xs[i][1] < ys[j][1]:
            i += 1
        else:
            j += 1
    return total


def canon(path: str) -> str:
    """Normalized absolute path with macOS's /tmp and /var symlinks spelled out (/private/tmp, /private/var)."""
    p = os.path.normpath(path)
    if p.startswith("//"):
        p = "/" + p.lstrip("/")
    for alias in ("/tmp", "/var", "/etc"):
        if p == alias or p.startswith(alias + "/"):
            return "/private" + p
    return p


def inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def group_k(group) -> int | None:
    m = GROUP_K_RE.search(group or "")
    return int(m.group(1)) if m else None


def infra_code(code) -> bool:
    return bool(code) and (code in INFRA_CODES or bool(HTTP_5XX_RE.match(code)))


# ---------------------------------------------------------------- session logs

def read_log(path: Path) -> dict:
    """One session log (.jsonl or .jsonl.zstd) as {"path", "header", "events", "unparsable", "error", "inherited"}.

    "events" are the session's own events: for a forked agent (header isSeeded) the copy of the parent's history
    at the start of the log is left out and its length is reported as "inherited".

    Lines are split on "\\n" only: str.splitlines() also breaks inside JSON strings at U+2028, U+2029 and
    U+0085. A damaged log never raises: a truncated zstd stream keeps what decoded, bytes that are not UTF-8
    are replaced, and every non-empty line that is not a JSON object counts as unparsable."""
    error = None
    try:
        if path.name.endswith(".zstd"):
            import zstandard
            rest, chunks, dctx = path.read_bytes(), [], zstandard.ZstdDecompressor()
            try:
                while rest:  # frame by frame; an incomplete last frame keeps its complete blocks
                    frame = dctx.decompressobj()
                    chunks.append(frame.decompress(rest))
                    if not frame.eof:
                        error = "zstd: truncated stream"
                        break
                    rest = frame.unused_data
            except zstandard.ZstdError as exc:
                error = f"zstd: {exc}"
            data = b"".join(chunks)
        else:
            data = path.read_bytes()
    except OSError as exc:
        return {"path": str(path), "header": None, "events": [], "unparsable": 0, "error": f"read: {exc}"}
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        text = data.decode("utf-8", errors="replace")
        error = error or f"utf-8: {exc.reason} at byte {exc.start}"
    lines = text.split("\n")
    if lines and not lines[-1]:
        lines.pop()  # the newline that ends the last record
    header, events, bad = None, [], 0
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if not isinstance(obj, dict):
            bad += 1
        elif index == 0 and obj.get("type") == "session":
            header = obj
        else:
            events.append(obj)
    if header is None and error is None:
        error = "no session header"
    inherited = 0
    if header is not None and header.get("isSeeded"):
        # The log of an agent started with subagent_fork begins with a copy of its parent's history (the parent's own
        # events, same callIds and times), closed by a session/end-seed event. Those events are the parent's work and
        # are already in the parent's log: only what follows the marker is this agent's. The marker itself is kept.
        cut = next((i for i, e in enumerate(events) if e.get("type") == "session/end-seed"), None)
        if cut is None:  # the fork ended while the copy was being written: nothing in the log is its own
            error = error or "seeded log without session/end-seed: every event is a copy of the parent's"
            cut = len(events)
        inherited, events = cut, events[cut:]
    return {"path": str(path), "header": header, "events": events, "unparsable": bad, "error": error,
            "inherited": inherited}


def stream_span(stream) -> tuple:
    """(first, last) chunk time of one assistant stream. A packed run (text-/reasoning-/tool-call-chunks) ends at
    time0 + sum(dt), as dsh-session-format-v1-to-v2 recordLastTime computes it."""
    first = last = None
    for rec in stream or ():
        if not isinstance(rec, dict):
            continue
        if rec.get("type") == "chunk":
            times = [rec.get("time")]
        else:
            t0 = rec.get("time0")
            times = [t0, t0 + sum(d for d in rec.get("dt") or () if num(d))] if num(t0) else []
        for t in times:
            if num(t):
                first = t if first is None else min(first, t)
                last = t if last is None else max(last, t)
    return first, last


def stream_error_code(stream):
    """The provider error code of a stream that finished with an error, else None."""
    for rec in stream or ():
        if isinstance(rec, dict) and rec.get("type") == "chunk":
            chunk = rec.get("chunk") or {}
            if chunk.get("type") == "finish" and (chunk.get("reason") or {}).get("kind") == "error":
                return ((chunk.get("reason") or {}).get("failure") or {}).get("code") or "error"
    return None


def result_blocks(data: dict) -> list:
    message = data.get("message") or {}
    if "toolCallId" in message:  # v4: the message itself is the result
        return [message]
    return [b for b in message.get("content") or [] if isinstance(b, dict) and b.get("type") == "tool-result"]


def parse_args_json(raw):
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw) if isinstance(raw, str) else None
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def new_step() -> dict:
    return {"start": None, "end": None, "chunk_first": None, "chunk_last": None, "resp": None}


def parse_session(log: dict) -> dict | None:
    """Everything the metrics need from one session log, in one pass."""
    header = log["header"]
    if header is None:
        return None
    s = {
        "file": log["path"], "id": norm_id(header.get("id")), "parent": norm_id(header.get("parentSession")),
        "depth": header.get("delegationDepth") or 0, "origin": header.get("origin"),
        "created": header.get("createdAt") if num(header.get("createdAt")) else None,
        "cwd": header.get("cwd"), "seeded": bool(header.get("isSeeded")),
        "first_time": None, "last_time": None, "mode": None, "provider": None, "label": None,
        "steps": {}, "messages": [], "attempts": [], "calls": {}, "call_order": [], "results": {},
        "turns": [], "turn_ends": [], "inbox": [], "users": [], "system": None, "tools": None,
        "catalog": [], "end_seeds": [], "search_aux": 0, "usage": collections.Counter(),
        "models": collections.Counter(),  # requested model id of each assistant message (source.model)
    }
    open_turn = None
    for ev in log["events"]:
        etype = ev.get("type")
        data = ev.get("data") if isinstance(ev.get("data"), dict) else {}
        t = ev.get("time") if num(ev.get("time")) else None
        if t is not None:
            s["first_time"] = t if s["first_time"] is None else min(s["first_time"], t)
            s["last_time"] = t if s["last_time"] is None else max(s["last_time"], t)
        key = (data.get("turn"), data.get("step"))
        if etype == "step/start":
            step = s["steps"].setdefault(key, new_step())
            if step["start"] is None:
                step["start"] = t
        elif etype == "step/end":
            s["steps"].setdefault(key, new_step())["end"] = t
        elif etype in ("assistant/message", "assistant/attempt"):
            first, last = stream_span(data.get("stream"))
            step = s["steps"].setdefault(key, new_step())
            if first is not None:
                step["chunk_first"] = first if step["chunk_first"] is None else min(step["chunk_first"], first)
                step["chunk_last"] = last if step["chunk_last"] is None else max(step["chunk_last"], last)
            if t is not None:
                step["resp"] = t if step["resp"] is None else max(step["resp"], t)
            if etype == "assistant/message":
                usage = data.get("usage") or {}
                for name, value in usage.items():
                    if num(value) and name != "totalTokens":
                        s["usage"][name] += value
                s["models"][((data.get("message") or {}).get("source") or {}).get("model")] += 1
                content = (data.get("message") or {}).get("content") or []
                n_calls = sum(1 for b in content if isinstance(b, dict) and b.get("type") == "tool-call")
                s["messages"].append({"time": t, "key": key, "usage": usage, "first": first, "last": last,
                                      "n_calls": n_calls})
            else:
                s["attempts"].append({"time": t, "key": key, "code": stream_error_code(data.get("stream"))})
        elif etype == "tool/call":
            cid = data.get("callId")
            s["calls"][cid] = {"id": cid, "name": data.get("name"), "args": parse_args_json(data.get("arguments")),
                               "time": t, "key": key, "session": s["id"]}
            s["call_order"].append(cid)
        elif etype == "tool/result":
            for block in result_blocks(data):
                s["results"][block.get("toolCallId")] = {"time": t, "is_error": bool(block.get("isError")),
                                                         "text": text_of(block.get("content"))}
        elif etype == "turn/start":
            open_turn = t
        elif etype == "turn/end":
            if open_turn is not None and t is not None:
                s["turns"].append((open_turn, t, True))
            open_turn = None
            s["turn_ends"].append((t, data.get("reason") or {}))
        elif etype == "agent/inbox/spliced":
            inserted = [m for m in data.get("inserted") or [] if isinstance(m, dict)]
            if inserted:
                s["inbox"].append({"time": t, "messages": inserted})
        elif etype == "user/message":
            src = data.get("source") or {}
            s["users"].append({"time": t, "kind": src.get("kind"), "sender": norm_id(src.get("senderSessionId")),
                               "id": data.get("id"), "text": text_of(data.get("content")), "source": src})
        elif etype == "system/message":
            if s["system"] is None:
                s["system"] = text_of((data.get("message") or {}).get("content"))
        elif etype == "request/header":
            if s["tools"] is None:
                s["tools"] = (data.get("header") or {}).get("tools") or []
        elif etype == "subagent/descriptor":
            s.update(mode=data.get("mode"), provider=data.get("provider"), label=data.get("label"))
        elif etype == "subagent/catalog":
            s["catalog"].append({"time": t, "child": norm_id(data.get("childId")), "mode": data.get("mode"),
                                 "label": data.get("label")})
        elif etype == "session/end-seed":
            s["end_seeds"].append(t)
        elif etype == "web/deepseek-search-llm-request":
            s["search_aux"] += 1
    if open_turn is not None and s["last_time"] is not None:
        s["turns"].append((open_turn, s["last_time"], False))  # still open when the log ends
    return s


# ---------------------------------------------------------------- bash static analysis

_OPERATORS = ("&&", "||", "|&", ";;", "&>>", ">>", "&>", ">&", "<&", "<<<", "<<-", "<<", ">|", "<>",
              "|", "&", ";", "(", ")", "<", ">", "\n")
_SEPARATORS = frozenset({"&&", "||", "|&", ";;", "|", "&", ";", "(", ")", "\n"})
_REDIRECTS = frozenset({"&>>", ">>", "&>", ">&", "<&", "<<<", ">|", "<>", "<", ">"})
_WRITE_REDIRECTS = frozenset({"&>>", ">>", "&>", ">|", ">", "<>"})
_HEREDOCS = frozenset({"<<", "<<-"})
_WORD_BREAK = " \t\r\n;&|()<>"
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\[[^\]]*\])?\+?=")
_KEYWORDS = frozenset({"if", "then", "else", "elif", "fi", "do", "done", "while", "until", "!", "{", "}", "coproc"})
_HEADER_KEYWORDS = frozenset({"for", "select", "case", "function", "esac", "in"})
_WRAPPERS = {  # command that runs another command -> its options that take a separate value
    "sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U"}, "doas": {"-u", "-C"},
    "env": {"-u", "-C", "-S", "-P"}, "nohup": set(), "exec": {"-a"}, "command": set(), "builtin": set(),
    "noglob": set(), "nice": {"-n"}, "ionice": {"-c", "-n", "-p"}, "time": {"-f", "-o"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"}, "gtimeout": {"-s", "-k", "--signal", "--kill-after"},
    "xargs": {"-I", "-L", "-n", "-P", "-s", "-d", "-E", "-a", "-J", "-R", "-S"},
    "caffeinate": {"-t", "-w"}, "stdbuf": {"-i", "-o", "-e"}, "unbuffer": set(), "watch": {"-n", "-d"},
}
_SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh"})
_CODE_RUNNERS = re.compile(r"^(python[0-9.]*|node|perl|ruby|php)$")
_URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
# A relative shell word counts as a path only when it looks like one: components without spaces or markup and a
# last component with a file extension (gw11183.html, res/s.html, ./bulk.sh), so option values such as
# "Mozilla/5.0" or "%{http_code}" are not mistaken for files.
_REL_PATH_RE = re.compile(r"^(\.{1,2}/)*([\w@+-][\w.@+-]*/)*[\w@+-][\w.@+-]*\.[A-Za-z][A-Za-z0-9]{0,7}$")
_CODE_LIT_RE = re.compile(r"""(?P<q>['"])(?P<p>(?:/|~/|\./|\.\./)[^'"\n]*|[\w@+-][\w.@+-]*\.[A-Za-z][A-Za-z0-9]{0,7})(?P=q)""")
_CODE_OPEN_WRITE_AFTER = re.compile(r"""\s*,\s*(?:mode\s*=\s*)?[rbt]*['"][^'"]*[wax][^'"]*['"]""")
_CODE_PATH_WRITE_AFTER = re.compile(r"""\s*\)\s*\.\s*(?:write_text|write_bytes|mkdir|touch)\b""")
_CODE_WRITE_CALL_BEFORE = re.compile(r"(?:urlretrieve|savefig|to_csv|to_excel|to_json|to_parquet|makedirs|mkdir|"
                                     r"copyfile|copy2?|copytree|move|rename|replace|extractall)\([^()]*$")
_CODE_ASSIGN_BEFORE = re.compile(r"(?:^|[^=!<>])=\s*$")
_ABS_REF_RE = re.compile(r"""(?<![\w$.~/-])/(?:Users|private/tmp|tmp)(?=$|[/\s'"`;|&<>(){}\[\],:])[^\s'"`;|&<>(){}\[\],]*""")
_TILDE_REF_RE = re.compile(r"""(?<![\w$.~/-])~(?=$|[/\s'"`;|&<>(){}])[^\s'"`;|&<>(){}\[\],]*""")
_HOME_REF_RE = re.compile(r"""\$\{?HOME\}?(?![\w])[^\s'"`;|&<>(){}\[\],]*""")


def _match_close(text: str, i: int, open_ch: str = "(", close_ch: str = ")") -> int:
    """Index of the bracket that closes text[i] (quotes respected); len(text) - 1 when it never closes."""
    depth, j, n = 0, i, len(text)
    while j < n:
        ch = text[j]
        if ch == "\\":
            j += 2
            continue
        if ch == "'" and open_ch == "(":
            k = text.find("'", j + 1)
            j = n if k < 0 else k + 1
            continue
        if ch == '"':
            k = j + 1
            while k < n and text[k] != '"':
                k += 2 if text[k] == "\\" else 1
            j = k + 1
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return n - 1


def shell_tokens(text: str) -> tuple:
    """Tokens of a bash command for static analysis: ("word", text) and ("op", text), plus the inner texts of
    command substitutions ($(...), `...`, <(...), >(...)) and the bodies of here-documents. Quote removal and
    escapes as in bash; "#" at a word start comments out the rest of the line; a newline is a separator.
    Never raises."""
    tokens, subs, docs, pending = [], [], [], []
    word = None
    i, n = 0, len(text)

    def add(chars: str) -> None:
        nonlocal word
        if word is None:
            word = []
        word.append(chars)

    def flush() -> None:
        nonlocal word
        if word is not None:
            tokens.append(("word", "".join(word)))
            word = None

    while i < n:
        c = text[i]
        if c in " \t\r":
            flush()
            i += 1
        elif c == "\\":
            if not text.startswith("\\\n", i):
                add(text[i + 1:i + 2])
            i += 2
        elif c == "#" and word is None:
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif c == "'":
            j = text.find("'", i + 1)
            j = n if j < 0 else j
            add(text[i + 1:j])
            i = j + 1
        elif text.startswith("$'", i):
            j = i + 2
            while j < n and text[j] != "'":
                j += 2 if text[j] == "\\" else 1
            add(text[i + 2:j])
            i = j + 1
        elif c == '"':
            j, buf = i + 1, []
            while j < n and text[j] != '"':
                ch = text[j]
                if ch == "\\" and j + 1 < n:
                    if text[j + 1] in '"\\$`':
                        buf.append(text[j + 1])
                    elif text[j + 1] != "\n":
                        buf.append(text[j:j + 2])
                    j += 2
                elif text.startswith("$(", j):
                    k = _match_close(text, j + 1)
                    if not text.startswith("$((", j):
                        subs.append(text[j + 2:k])
                    buf.append(text[j:k + 1])
                    j = k + 1
                elif ch == "`":
                    k = text.find("`", j + 1)
                    k = n if k < 0 else k
                    subs.append(text[j + 1:k])
                    buf.append(text[j:k + 1])
                    j = k + 1
                else:
                    buf.append(ch)
                    j += 1
            add("".join(buf))
            i = j + 1
        elif text.startswith("$(", i):
            k = _match_close(text, i + 1)
            if not text.startswith("$((", i):
                subs.append(text[i + 2:k])
            add(text[i:k + 1])
            i = k + 1
        elif text.startswith("${", i):
            k = _match_close(text, i + 1, "{", "}")
            add(text[i:k + 1])
            i = k + 1
        elif c == "`":
            k = text.find("`", i + 1)
            k = n if k < 0 else k
            subs.append(text[i + 1:k])
            add(text[i:k + 1])
            i = k + 1
        elif c in "<>" and text.startswith("(", i + 1):
            k = _match_close(text, i + 1)
            subs.append(text[i + 2:k])
            flush()
            tokens.append(("word", text[i:k + 1]))
            i = k + 1
        else:
            op = next((o for o in _OPERATORS if text.startswith(o, i)), None)
            if op is None:
                add(c)
                i += 1
                continue
            if op in _REDIRECTS and word is not None and "".join(word).isdigit():
                word = None  # "2>": the digits name a file descriptor
            flush()
            i += len(op)
            tokens.append(("op", op))
            if op in _HEREDOCS:
                while i < n and text[i] in " \t":
                    i += 1
                j = i
                while j < n and text[j] not in _WORD_BREAK:
                    j += 1
                delim = text[i:j].replace("'", "").replace('"', "").replace("\\", "")
                pending.append((delim, op == "<<-"))
                i = j
            elif op == "\n" and pending:
                for delim, strip_tabs in pending:
                    body = []
                    while i < n:
                        j = text.find("\n", i)
                        line = text[i:] if j < 0 else text[i:j]
                        i = n if j < 0 else j + 1
                        if (line.lstrip("\t") if strip_tabs else line) == delim:
                            break
                        body.append(line)
                    docs.append("\n".join(body))
                pending = []
    flush()
    docs.extend("" for _ in pending)  # here-document operator without a body: keep docs aligned with operators
    return tokens, subs, docs


def simple_commands(tokens: list) -> list:
    """Simple commands of a token list: {"words": [...], "redirs": [(op, target or None), ...]}."""
    cmds, words, redirs = [], [], []
    i = 0
    while i < len(tokens):
        kind, val = tokens[i]
        if kind == "word":
            words.append(val)
        elif val in _SEPARATORS:
            if words or redirs:
                cmds.append({"words": words, "redirs": redirs})
            words, redirs = [], []
        else:
            target = None
            if val not in _HEREDOCS and i + 1 < len(tokens) and tokens[i + 1][0] == "word":
                target = tokens[i + 1][1]
                i += 1
            redirs.append((val, target))
        i += 1
    if words or redirs:
        cmds.append({"words": words, "redirs": redirs})
    return cmds


def command_words(words: list) -> list:
    """(index, basename) of every command one simple command runs: the first word after assignments and shell
    keywords, followed through wrappers such as env, timeout, xargs or sudo, and find's -exec."""
    out, i, n = [], 0, len(words)
    while i < n:
        w = words[i]
        if _ASSIGN_RE.match(w):
            i += 1
            continue
        if w in _HEADER_KEYWORDS:
            break
        if w in _KEYWORDS:
            i += 1
            continue
        name = os.path.basename(w.rstrip("/")) or w
        out.append((i, name))
        if name not in _WRAPPERS or (name == "command" and i + 1 < n and words[i + 1] in ("-v", "-V")):
            break
        takes_value = _WRAPPERS[name]
        i += 1
        while i < n and words[i].startswith("-") and words[i] != "-":
            i += 2 if words[i] in takes_value else 1
        if name in ("timeout", "gtimeout") and i < n:
            i += 1  # the duration
    if out and out[-1][1] == "find":
        for j in range(out[-1][0] + 1, n - 1):
            if words[j] in ("-exec", "-execdir", "-ok", "-okdir"):
                out.append((j + 1, os.path.basename(words[j + 1]) or words[j + 1]))
    return out


_REL_NAME_RE = re.compile(r"^(?:\.{1,2}/)*[\w@+%-][\w.@+%~-]*(?:/[\w@+%-][\w.@+%~-]*)*/?$")


def resolve_word(word: str, cwd, home: str, any_name: bool = False):
    """Absolute normalized path a shell word names, or None for options, URLs, unexpanded variables and words that
    do not look like paths. any_name: the word is known to be a path (a mkdir argument, a write target), so a
    relative name without a file extension counts too (`cd /tmp && mkdir -p kp`)."""
    if not word or word.startswith("-") or " " in word or "\n" in word or _URL_RE.match(word) or "`" in word:
        return None
    if word == "~" or word.startswith("~/"):
        word = home + word[1:]
    elif re.match(r"^\$\{?HOME\}?(/|$)", word):
        word = home + word[word.index("/"):] if "/" in word else home
    if "$" in word:
        return None
    if word.startswith("/"):
        return os.path.normpath(word)
    if cwd and (_REL_PATH_RE.match(word) or (any_name and _REL_NAME_RE.match(word))) \
            and not re.fullmatch(r"[\d.]+", word):
        return os.path.normpath(os.path.join(cwd, word))
    return None


def resolve_dir(word: str, cwd, home: str):
    """The directory a `cd` argument names (any relative name, unlike resolve_word), or None."""
    if word in ("~", ""):
        return home
    if word.startswith("~/"):
        return os.path.normpath(home + word[1:])
    if re.match(r"^\$\{?HOME\}?(/|$)", word):
        return os.path.normpath(home + (word[word.index("/"):] if "/" in word else ""))
    if "$" in word or "`" in word or _URL_RE.match(word) or word == "-":
        return None
    if word.startswith("/"):
        return os.path.normpath(word)
    return os.path.normpath(os.path.join(cwd, word)) if cwd else None


_VAR_RE = re.compile(r"\$\([^)]*\)|\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*|\$[0-9@*#?!]|`[^`]*`")
_TEMPLATE_RE = re.compile(r"\{[^{}]*\}|%[-#0 +]*\d*(?:\.\d+)?[sdifr]")


def resolve_pattern(word: str, cwd, home: str, bare_prefix: bool = False):
    """Glob pattern for an output name the command computes: `rws_$(echo $p).html` -> <cwd>/rws_*.html, and with
    bare_prefix a helper's bare name argument `uss_main` -> <cwd>/uss_main* (helpers such as `fetch.sh URL NAME`
    write NAME.html). None when too little of the name is literal to say anything."""
    if "$" in word or "`" in word:
        if word.startswith(("~/", "$HOME/", "${HOME}/")):
            word = home + word[word.index("/"):]
        pattern = _VAR_RE.sub("*", word)
    elif bare_prefix and re.fullmatch(r"[\w@+.-]+", word) and not re.fullmatch(r"[\d.]+", word):
        pattern = word + "*"
    else:
        return None
    if " " in pattern or "\n" in pattern or _URL_RE.match(pattern):
        return None
    stem = os.path.basename(pattern)
    stem = stem.rsplit(".", 1)[0] if "." in stem.lstrip("*") else stem
    if len(stem.replace("*", "")) < 2:
        return None
    if not pattern.startswith("/"):
        if not cwd:
            return None
        pattern = os.path.join(cwd, pattern)
    return os.path.normpath(pattern)


def code_refs(code: str, cwd, home: str) -> list:
    """(kind, path) for the path literals in a code snippet (python and similar): "mkdir" for makedirs/mkdir,
    "write" for open(..., 'w'), Path(...).write_text, urlretrieve and the like, nothing for a plain assignment
    of a fixed path (the use is not visible), a name pattern for a template ('/tmp/{n}.html', '$f', '%s') that
    is written or assigned (f = f'/tmp/s_{k}.html' feeds curl -o or open(f, 'w') far more often than a read),
    else "read". Relative literals count only as arguments of file functions (open, Path, read_csv, ...), so
    strings such as 'html.parser' are not taken for files."""
    out = []
    for m in _CODE_LIT_RE.finditer(code):
        lit = m.group("p")
        template = any(ch in lit for ch in "{}$%")
        before, after = code[max(0, m.start() - 120):m.start()], code[m.end():m.end() + 60]
        before = re.sub(r"(?<![\w])[rbfuRBFU]{1,2}$", "", before)  # string prefix: f'...', rb'...'

        if re.search(r"(?:makedirs|mkdir)\([^()]*$", before) or re.match(r"\s*\)\s*\.\s*mkdir\b", after):
            kind = "mkdir"
        elif (re.search(r"open\(\s*$", before) and _CODE_OPEN_WRITE_AFTER.match(after)) \
                or _CODE_PATH_WRITE_AFTER.match(after) or _CODE_WRITE_CALL_BEFORE.search(before) \
                or re.search(r"""['"]-[oO]['"]\s*,\s*$""", before):
            kind = "write"
        elif _CODE_ASSIGN_BEFORE.search(before) and not re.search(r"\(\s*$", before):
            if not template:
                continue
            kind = "write"
        else:
            kind = "read"
        if lit.startswith("~/"):
            lit = home + lit[1:]
        if not lit.startswith("/"):
            file_call = re.search(r"(?:open|Path|read_csv|read_excel|read_json|read_text|read_bytes|load|exists|"
                                  r"isfile|isdir|getsize|listdir|glob|PdfReader|parse)\(\s*$", before)
            if not cwd or not (kind != "read" or file_call):
                continue
            lit = os.path.join(cwd, lit)
        if template:  # f-string / % / shell template: only a write tells something (a pattern of names)
            if kind != "read":
                pattern = resolve_pattern(_TEMPLATE_RE.sub("$x", lit), None, home)
                if pattern:
                    out.append(("write-pattern", pattern))
            continue
        out.append((kind, os.path.normpath(lit)))
    return out


# Commands whose file arguments are read (the first positional of the grep family, sed, awk and jq is a pattern or
# program, not a file); commands that touch no file content; and the writers with their write / value options.
_READ_CMDS = frozenset({
    "cat", "head", "tail", "less", "more", "grep", "egrep", "fgrep", "zgrep", "rg", "ag", "awk", "gawk", "sed", "wc",
    "file", "strings", "pdftotext", "pdfinfo", "pdftohtml", "cut", "sort", "uniq", "diff", "cmp", "comm", "jq",
    "xmllint", "iconv", "unzip", "zcat", "gunzip", "gzcat", "bzcat", "xzcat", "md5", "md5sum", "shasum", "sha1sum",
    "sha256sum", "stat", "du", "od", "hexdump", "xxd", "base64", "nl", "column", "paste", "join", "ls", "find", "tree",
    "readlink", "realpath", "open", "textutil", "source", ".", "cp", "mv", "ln", "install", "rsync", "ditto", "tar",
    "pandoc", "html2text", "w3m", "lynx", "test", "[", "[[", "tee", "dd", "split", "fold", "fmt", "rev", "tac",
    "mkdir", "touch", "git"})
_PATTERN_FIRST = frozenset({"grep", "egrep", "fgrep", "zgrep", "rg", "ag", "sed", "awk", "gawk", "jq"})
_NEUTRAL_CMDS = frozenset({
    "echo", "printf", "rm", "rmdir", "unlink", "chmod", "chown", "chgrp", "basename", "dirname", "export", "unset",
    "set", "true", "false", "sleep", "kill", "pkill", "killall", "which", "type", "whereis", "date", "pwd", "read",
    "local", "declare", "typeset", "alias", "exit", "return", "wait", "jobs", "trap", "shift", ":", "seq", "expr",
    "let", "ps", "uname", "whoami", "id", "hostname", "sw_vers", "printenv", "history", "clear", "tput", "cd",
    "pushd", "popd", "curl", "wget", "pip", "pip3", "uv", "npm", "npx", "pnpm", "yarn", "brew", "ping", "dig",
    "nslookup", "host", "nc", "lsof", "top", "df", "sysctl", "defaults", "tr", "bc"})
_WRITE_OPTS = {  # command -> (options whose value is written, options whose value is no file)
    "curl": ({"-o", "--output", "-D", "--dump-header", "-c", "--cookie-jar", "--trace", "--trace-ascii"},
             {"-A", "--user-agent", "-H", "--header", "-d", "--data", "--data-raw", "--data-binary",
              "--data-urlencode", "-e", "--referer", "-u", "--user", "-X", "--request", "-w", "--write-out", "-m",
              "--max-time", "--connect-timeout", "-x", "--proxy", "--retry", "-r", "--range", "-F", "--form",
              "--resolve", "-b", "--cookie", "--ciphers", "--retry-delay", "-Y", "-y"}),
    "wget": ({"-O", "--output-document", "-P", "--directory-prefix", "-o", "--output-file", "-a"},
             {"-U", "--user-agent", "--header", "-t", "--tries", "-T", "--timeout", "-e", "-w", "--wait",
              "--post-data", "-l", "--level"}),
    "pip": ({"-t", "--target", "--prefix", "--root"}, {"-r", "--requirement", "-i", "--index-url"}),
    "unzip": ({"-d"}, set()), "tar": ({"-C", "--directory"}, set()), "sort": ({"-o"}, {"-k", "-t", "-S"}),
    "grep": (set(), {"-A", "-B", "-C", "-m", "--max-count", "-e", "--regexp"}),
}
_RUNNER_RE = re.compile(r"^(python[0-9.]*|node|perl|ruby|php|bash|sh|zsh|Rscript)$")
_FUNC_DEF_RE = re.compile(r"(?:^|[\s;&|{(])(?:function\s+)?([A-Za-z_][\w-]*)\s*\(\s*\)\s*\{")


def _file_roles(name: str, words: list, idx: int, local_funcs) -> dict:
    """Role of the words after the command word: "read", "write", "mkdir"; absent = no file or unknown. File
    arguments of helper functions, scripts and unfamiliar tools count as written (they are mostly download
    helpers such as `dl URL out.html`), so the /tmp check below is a lower bound."""
    roles = {}
    args = list(range(idx + 1, len(words)))
    if name in _NEUTRAL_CMDS and name not in _WRITE_OPTS:
        return roles
    if name in local_funcs or (name not in _READ_CMDS and name not in _WRITE_OPTS and not _RUNNER_RE.match(name)):
        roles.update((j, "write?") for j in args if not words[j].startswith("-"))
        return roles
    if _RUNNER_RE.match(name):
        j = idx + 1
        while j < len(words) and words[j].startswith("-") and words[j] != "-":
            if words[j] in ("-c", "-e", "-m", "-r", "--require", "-W", "-X") or re.fullmatch(r"-[a-zA-Z]*c", words[j]):
                return roles  # inline code (scanned separately) or a module: its arguments' roles are unknown
            j += 1
        if j < len(words) and words[j] != "-":
            roles[j] = "read"  # the script
            roles.update((k, "write?") for k in range(j + 1, len(words)) if not words[k].startswith("-"))
        return roles
    write_opts, plain_opts = _WRITE_OPTS.get("pip" if name == "pip3" else name, (set(), set()))
    cluster = {"curl": "o", "wget": "O"}.get(name)  # -sSLo FILE / -qO FILE: a flag cluster ending in o / O
    positional = []
    j = idx + 1
    while j < len(words):
        w = words[j]
        if (w in write_opts or (cluster and re.fullmatch(rf"-[A-Za-z]+{cluster}", w))) and j + 1 < len(words):
            roles[j + 1] = "write"
            j += 2
            continue
        if w in plain_opts and j + 1 < len(words):
            j += 2
            continue
        if w.startswith("--") and "=" in w and w.split("=", 1)[0] in write_opts:
            roles[j] = "write"
            words[j] = w.split("=", 1)[1]
        elif cluster and re.fullmatch(rf"-{cluster}[^-].*", w):  # -o/tmp/x, -O/tmp/x
            roles[j] = "write"
            words[j] = w[2:]
        elif name == "dd" and w.startswith(("if=", "of=")):
            roles[j] = "write" if w.startswith("of=") else "read"
            words[j] = w[3:]
        elif not w.startswith("-") or w == "-":
            positional.append(j)
        j += 1
    if name in ("curl", "wget", "pip", "pip3"):
        return roles
    if name in ("tee", "touch"):
        roles.update((k, "write") for k in positional)
    elif name == "mkdir":
        roles.update((k, "mkdir") for k in positional)
    elif name == "git":
        if positional and words[positional[0]] == "clone" and len(positional) >= 3:
            roles[positional[2]] = "mkdir"
    elif name in ("cp", "mv", "ln", "install", "rsync", "ditto") and len(positional) >= 2:
        roles.update((k, "read") for k in positional[:-1])
        roles[positional[-1]] = "write"
    elif name == "pdftotext" and len(positional) >= 2:
        roles[positional[0]] = "read"
        if words[positional[-1]] != "-":
            roles[positional[-1]] = "write"
    elif name == "tar":
        flags = "".join(words[k] for k in args if words[k].startswith("-")) + (words[idx + 1] if args else "")
        for k in args:
            if words[k] in ("-f", "--file") or re.fullmatch(r"-[A-Za-z]*f", words[k]):
                if k + 1 < len(words):
                    roles[k + 1] = "read" if re.search(r"[xt]", flags) else "write"
    else:
        files = positional
        explicit = any(words[k] in ("-e", "-f", "--regexp", "--file") or words[k].startswith(("-e", "--regexp="))
                       for k in args)
        if name in _PATTERN_FIRST and not explicit:
            files = positional[1:]
        if name == "sed" and any(words[k].startswith("-i") for k in args):
            roles.update((k, "write") for k in files)
        else:
            roles.update((k, "read") for k in files)
    return roles


_SIMPLE_VAR_RE = re.compile(r"\$(?:\{([A-Za-z_]\w*)\}|([A-Za-z_]\w*))")
_TRIM_RE = re.compile(r"^\$\{([A-Za-z_]\w*)(%%|%|##|#)([^}]*)\}$")


def trim_param(value: str, op: str, pattern: str) -> str:
    """bash ${v%pat} / ${v%%pat} (shortest / longest matching suffix removed), ${v#pat} / ${v##pat} (prefix)."""
    n = len(value)
    if op in ("%", "%%"):
        for i in (range(n, -1, -1) if op == "%" else range(n + 1)):
            if fnmatch.fnmatchcase(value[i:], pattern):
                return value[:i]
        return value
    for i in (range(n + 1) if op == "#" else range(n, -1, -1)):
        if fnmatch.fnmatchcase(value[:i], pattern):
            return value[i:]
    return value


def note_assignment(word: str, loopvars: dict) -> None:
    """NAME=VALUE built from for-loop variables (`name=${pair%% *}`, `f="$k.html"`) gets the derived values."""
    name, _, value = word.partition("=")
    if not re.fullmatch(r"[A-Za-z_]\w*", name):
        return
    m = _TRIM_RE.match(value)
    if m and m.group(1) in loopvars:
        loopvars[name] = [trim_param(v, m.group(2), m.group(3)) for v in loopvars[m.group(1)]]
        return
    expanded = expand_loop_vars(value, loopvars)
    if expanded != [value] or (value and "$" not in value and "`" not in value):
        loopvars[name] = expanded
    else:
        loopvars.pop(name, None)  # reassigned to something unknown


def expand_loop_vars(word: str, loopvars: dict) -> list:
    """The words a write target stands for when it only uses variables of enclosing `for VAR in w1 w2 ...`
    loops (`-o $f.txt` with `for f in rfp2017 cint2017` -> rfp2017.txt, cint2017.txt); [word] otherwise."""
    found = _SIMPLE_VAR_RE.findall(word)
    names = [a or b for a, b in found]
    if not names or word.count("$") != len(names) or "`" in word or any(n not in loopvars for n in names):
        return [word]
    out = [word]
    for name in dict.fromkeys(names):
        rx = re.compile(r"\$\{" + name + r"\}|\$" + name + r"(?!\w)")
        out = [rx.sub(lambda _m, v=v: v, w) for w in out for v in loopvars[name]]
        if len(out) > 64:
            return [word]
    return out


def analyze_bash(command: str, workdir, home: str, depth: int = 0, local_funcs=frozenset(), loopvars=None) -> dict:
    """Static facts about one bash command: commands run (basenames, through wrappers, `bash -c`, eval and
    command substitutions), agent CLIs among them, network kinds, pytest runs, and the ordered (kind, path)
    references used for the /tmp read-before-write check. Heuristic by design; never raises."""
    info = {"commands": [], "agent_clis": collections.Counter(), "network": set(), "pytest": 0, "refs": []}
    if depth > 4 or not command:
        return info
    if re.search(r"https?://", command):
        info["network"].add("http url")
    local_funcs = set(local_funcs) | set(_FUNC_DEF_RE.findall(command))
    loopvars = dict(loopvars or {})
    tokens, subs, docs = shell_tokens(command)
    doc_iter = iter(docs)
    cwd = workdir

    def merge(other: dict) -> None:
        info["commands"] += other["commands"]
        info["agent_clis"].update(other["agent_clis"])
        info["network"] |= other["network"]
        info["pytest"] += other["pytest"]
        info["refs"] += other["refs"]

    def add_write(word: str, role: str) -> None:
        """A write target ("write", "write?" = guessed, "mkdir"), through for-loop variables; computed names
        become patterns. A known target may be any relative name; a guessed one needs a file extension, else
        it stands for NAME* (helpers such as `fetch.sh URL NAME` write NAME.html)."""
        expanded = expand_loop_vars(word, loopvars)
        for w in expanded:
            path = resolve_word(w, cwd, home, any_name=role in ("mkdir", "write"))
            if path and any(ch in path for ch in "*?["):
                info["refs"].append(("write-pattern", path))
            elif path:
                info["refs"].append((role.rstrip("?"), path))
            else:
                pattern = resolve_pattern(w, cwd, home, bare_prefix=role == "write?")
                if pattern is None and w != word:  # a loop value that is no file name: keep the computed pattern
                    pattern = resolve_pattern(word, cwd, home, bare_prefix=role == "write?")
                if pattern:
                    info["refs"].append(("write-pattern", pattern))

    for cmd in simple_commands(tokens):
        words = list(cmd["words"])
        if len(words) >= 3 and words[0] == "for" and words[2] == "in" and re.fullmatch(r"[A-Za-z_]\w*", words[1]):
            loopvars[words[1]] = [w for w in words[3:] if w not in ("do", ";")]
        lead = 0
        while lead < len(words) and (words[lead] in _KEYWORDS
                                     or words[lead] in ("local", "export", "declare", "typeset", "readonly")):
            lead += 1
        for w in words[lead:]:
            if not _ASSIGN_RE.match(w):
                break
            note_assignment(w, loopvars)
        for op, _ in cmd["redirs"]:
            if op in _HEREDOCS:
                info["refs"] += code_refs(next(doc_iter, ""), cwd, home)
        cws = command_words(words)
        for _, cname in cws:
            info["commands"].append(cname)
            if cname in AGENT_CLIS and cname not in local_funcs:
                info["agent_clis"][cname] += 1
        # The innermost command (after wrappers) decides network, pytest and file roles.
        idx, name = (cws[-1][0], cws[-1][1]) if cws else (len(words), "")
        args = words[idx + 1:]
        if name in ("curl", "wget"):
            info["network"].add(name)
        if (name in ("pip", "pip3") and "install" in args) \
                or (name.startswith("python") and args[:2] in (["-m", "pip"], ["-m", "pip3"]) and "install" in args) \
                or (name == "uv" and (args[:2] == ["pip", "install"] or args[:1] == ["add"])):
            info["network"].add("pip install")
        if name == "git" and next((a for a in args if not a.startswith("-")), None) == "clone":
            info["network"].add("git clone")
        if name in ("pytest", "py.test") or (name.startswith("python") and "-m" in args
                                             and args.index("-m") + 1 < len(args)
                                             and args[args.index("-m") + 1] == "pytest"):
            info["pytest"] += 1
        if name in _SHELLS:
            for j in range(idx + 1, len(words) - 1):
                if re.fullmatch(r"-[a-zA-Z]*c[a-zA-Z]*", words[j]):
                    merge(analyze_bash(words[j + 1], cwd, home, depth + 1, local_funcs))
                    break
        elif name == "eval":
            merge(analyze_bash(" ".join(args), cwd, home, depth + 1, local_funcs))
        if _CODE_RUNNERS.match(name):
            for j in range(idx + 1, len(words) - 1):
                if words[j] in ("-c", "-e"):
                    info["refs"] += code_refs(words[j + 1], cwd, home)
                    break
        if name == "cd":
            target = next((w for w in args if not w.startswith("-")), "~")
            resolved = resolve_dir(target, cwd, home)
            if resolved:
                info["refs"].append(("read", resolved))
                cwd = resolved
            continue
        if cws and "/" in words[idx]:  # running a script file reads it
            path = resolve_word(words[idx], cwd, home)
            if path:
                info["refs"].append(("read", path))
        for op, target in cmd["redirs"]:
            if target is not None and op == "<":
                path = resolve_word(target, cwd, home)
                if path:
                    info["refs"].append(("read", path))
        roles = _file_roles(name, words, idx, local_funcs) if cws else {}
        for j in sorted(k for k, v in roles.items() if v == "read"):
            path = resolve_word(words[j], cwd, home)
            if path:
                info["refs"].append(("read", path))
        for role in ("mkdir", "write", "write?"):
            for j in sorted(k for k, v in roles.items() if v == role):
                add_write(words[j], role)
        for op, target in cmd["redirs"]:
            if target is not None and op in _WRITE_REDIRECTS:
                add_write(target, "write")
    for sub in subs:
        merge(analyze_bash(sub, cwd, home, depth + 1, local_funcs, loopvars))
    return info


def outside_refs(text: str, home: str) -> list:
    """Absolute paths a text mentions under /Users or /tmp (/private/tmp), and ~ or $HOME references
    (resolved to `home`), as (path, via_home)."""
    out = []
    for m in _ABS_REF_RE.finditer(text):
        out.append((m.group(0).rstrip(".,:;)"), False))
    for m in _TILDE_REF_RE.finditer(text):
        out.append((home + m.group(0)[1:].rstrip(".,:;)"), True))
    for m in _HOME_REF_RE.finditer(text):
        rest = re.sub(r"^\$\{?HOME\}?", "", m.group(0)).rstrip(".,:;)")
        out.append((home + rest, True))
    return out


# ---------------------------------------------------------------- batch discovery

def discover(batch: Path, include_failed: bool = False) -> tuple:
    """(runs, notes) of one batch directory. A run is {"dir", "key", "layout", "batch", "result", "manifest",
    "failed"}; notes list dirs that were skipped and why."""
    runs, notes = [], []
    if not os.access(batch, os.R_OK | os.X_OK):
        raise SystemExit(f"run_metrics: cannot read {batch} (a run_matrix_v2 batch is locked while it runs)")
    manifest = batch / "manifest.jsonl"
    if manifest.exists():
        seen = set()
        for line in manifest.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                notes.append(f"{batch.name}: unreadable manifest line: {line[:80]}")
                continue
            rid = rec.get("id")
            if not rid or rid in seen:
                continue
            seen.add(rid)
            d = batch / rid
            if not (d / "result.json").exists():
                notes.append(f"{batch.name}/{rid}: in manifest.jsonl but has no result.json")
                continue
            runs.append({"dir": d, "key": rid, "layout": "v2", "batch": batch.name, "manifest": rec,
                         "result": json.loads((d / "result.json").read_text(encoding="utf-8")), "failed": False})
        for d in sorted(p for p in batch.iterdir() if p.is_dir() and not p.name.startswith("_")):
            if d.name not in seen and (d / "result.json").exists():
                notes.append(f"{batch.name}/{d.name}: has result.json but is not in manifest.jsonl (skipped)")
        if include_failed and (batch / "_failed").is_dir():
            for d in sorted(p for p in (batch / "_failed").iterdir() if p.is_dir()):
                attempt = d / "attempt.json"
                if attempt.exists():
                    runs.append({"dir": d, "key": f"_failed/{d.name}", "layout": "v2", "batch": batch.name,
                                 "manifest": {}, "result": json.loads(attempt.read_text(encoding="utf-8")),
                                 "failed": True})
    else:
        for d in sorted(p for p in batch.iterdir() if p.is_dir()):
            if (d / "result.json").exists():
                runs.append({"dir": d, "key": d.name, "layout": "old", "batch": batch.name, "manifest": {},
                             "result": json.loads((d / "result.json").read_text(encoding="utf-8")), "failed": False})
            elif (d / "home").is_dir():
                notes.append(f"{batch.name}/{d.name}: no result.json (skipped)")
    return runs, notes


# ---------------------------------------------------------------- per-run metrics

def load_sessions(run_dir: Path) -> tuple:
    folder = run_dir / "home" / "sessions"
    if not folder.is_dir():
        return [], []
    files = sorted(set(folder.rglob("session*.jsonl")) | set(folder.rglob("session*.jsonl.zstd")))
    logs = [read_log(f) for f in files]
    return logs, [s for s in (parse_session(log) for log in logs) if s is not None]


def result_fields(run: dict) -> dict:
    """result.json facts kept with the metrics (both runners), plus #5063 and timeout flags for old runs."""
    res = run["result"]
    keep = ("exit", "seconds", "timeout", "crash5063", "infra_code", "attempts", "failed_attempt_ids", "order",
            "started_utc", "ended_utc", "prompt_sha256", "task_sha256", "patch_sha256", "patches", "suffix", "cwd",
            "runner", "dsh", "web", "deliverable", "deliverable_ok", "dry_run")
    out = {k: res[k] for k in keep if k in res}
    if "timeout" not in out:
        out["timeout"] = res.get("exit") == "timeout"
    if "crash5063" not in out:
        stderr = run["dir"] / "stderr.log"
        text = stderr.read_text(encoding="utf-8", errors="replace") if stderr.exists() else ""
        out["crash5063"] = all(s in text for s in CRASH5063)
    if "leftover_processes" in res:
        out["leftover_processes"] = len(res["leftover_processes"] or {})
    if "tmp_leftovers" in res:
        out["tmp_leftovers"] = (res["tmp_leftovers"] or {}).get("count")
    return out


def slot_epochs(ctx: dict) -> dict:
    """The slot epochs of a run as the module docstring ("slots") defines them, shared by slot_metrics and
    run_table.py. {"epochs": child -> [{"start", "end" (None when never released), "release", "kind", "window_end"}],
    "pools": pool owner -> [(start, end, child, index)], "owner": session id -> its pool owner (the nearest ancestor
    that is not a continuable child), "parent_of", "cont", "creation", "missing_logs", "stats"}. Needs ctx["sessions"],
    ctx["by_id"], ctx["root"]."""
    sessions, by_id, root = (ctx[k] for k in ("sessions", "by_id", "root"))
    creation = {}  # child -> the parent call that started it as a continuable child
    for p in sessions:
        for cid in p["call_order"]:
            call = p["calls"][cid]
            res = p["results"].get(cid)
            if call["name"] in SPAWN_TOOLS and res and not res["is_error"]:
                m = STARTED_RE.search(res["text"])
                if m:
                    creation[norm_id(m.group(1))] = {"parent": p["id"], "call": call["time"], "result": res["time"]}
    parent_of = {s["id"]: s["parent"] for s in sessions}
    cont = {}
    for s in sessions:
        if s is root:
            cont[s["id"]] = False
            continue
        mode = s["mode"]
        if mode is None and s["parent"] in by_id:
            mode = next((c["mode"] for c in by_id[s["parent"]]["catalog"] if c["child"] == s["id"]), None)
        cont[s["id"]] = (mode == "continuable") if mode else s["id"] in creation
    missing_logs = 0
    for child, info in creation.items():
        if child not in by_id:  # started, but its own log is missing: the parent's log still has its slot
            cont[child], parent_of[child] = True, info["parent"]
            missing_logs += 1

    def owner(sid):
        seen = set()
        while cont.get(sid) and sid not in seen:
            seen.add(sid)
            sid = parent_of.get(sid)
        return sid

    settled = collections.defaultdict(dict)  # child -> {notice id: (source, time)}
    for p in sessions:
        for ib in p["inbox"]:
            for msg in ib["messages"]:
                src = msg.get("source") or {}
                if src.get("kind") == "subagent-settled" and num(ib["time"]):
                    child = norm_id(src.get("senderSessionId"))
                    if parent_of.get(child) == p["id"]:
                        settled[child].setdefault(msg.get("id") or f"inbox@{ib['time']}", ("inbox", ib["time"]))
        for u in p["users"]:
            if u["kind"] == "subagent-settled" and num(u["time"]) and parent_of.get(u["sender"]) == p["id"]:
                settled[u["sender"]].setdefault(u["id"] or f"user@{u['time']}", ("user/message", u["time"]))
    sends = collections.defaultdict(list)  # child -> successful parent send_message calls
    for p in sessions:
        for cid in p["call_order"]:
            call = p["calls"][cid]
            if call["name"] != SEND_TOOL or not num(call["time"]):
                continue
            target = norm_id((call["args"] or {}).get("agent_id"))
            res = p["results"].get(cid)
            if parent_of.get(target) == p["id"] and res and not res["is_error"]:
                sends[target].append((call["time"], res["time"]))

    epochs = {}
    stats = collections.Counter()
    for child in sorted(c for c, v in cont.items() if v):
        notices = sorted(settled[child].values(), key=lambda x: x[1])
        pos = 0

        def take(after):
            nonlocal pos
            while pos < len(notices) and notices[pos][1] < after:
                pos += 1
                stats["notices_before_epoch"] += 1
            if pos < len(notices):
                pos += 1
                return notices[pos - 1]
            return None

        info = creation.get(child)
        start = info["call"] if info and num(info["call"]) else by_id.get(child, {}).get("created")
        if start is None:
            stats["no_start_time"] += 1
            continue
        if not info:
            stats["start_from_child_header"] += 1
        notice = take(start)
        eps = [{"start": start, "end": notice[1] if notice else None, "release": notice[0] if notice else "run end",
                "kind": "create", "window_end": info["result"] if info else start}]
        for call_t, result_t in sorted(sends[child]):
            last = eps[-1]["end"]
            if last is None:
                continue
            if call_t >= last:
                new_start = call_t  # the child had settled: the send cold-resumes it
            elif num(result_t) and call_t < last <= result_t:
                new_start = last  # the send waited for the child's disposal, then resumed it
            else:
                continue
            notice = take(new_start)
            eps.append({"start": new_start, "end": notice[1] if notice else None,
                        "release": notice[0] if notice else "run end", "kind": "resume",
                        "window_end": result_t if num(result_t) else new_start})
        stats["unmatched_notices"] += len(notices) - pos
        resumes = sum(1 for e in eps if e["kind"] == "resume")
        if child in by_id:
            markers = len(by_id[child]["end_seeds"]) - (1 if by_id[child]["seeded"] else 0)
            stats["end_seed_mismatch"] += abs(markers - resumes)
        epochs[child] = eps

    pools = collections.defaultdict(list)  # owner -> [(start, end or None, child, index)]
    for child, eps in epochs.items():
        pool = owner(parent_of.get(child))
        for i, e in enumerate(eps):
            pools[pool].append((e["start"], e["end"], child, i))
    return {"epochs": epochs, "pools": pools, "owner": owner, "parent_of": parent_of, "cont": cont,
            "creation": creation, "missing_logs": missing_logs, "stats": stats}


def slot_metrics(ctx: dict) -> dict:
    """Section 3.4 slot reconstruction and its consistency checks (see the module docstring)."""
    sessions, by_id, root, t0, t_end, k_group = (ctx[k] for k in ("sessions", "by_id", "root", "t0", "t_end", "K"))
    rel = (lambda t: rnd((t - t0) / 1000, 3) if num(t) else None)
    se = slot_epochs(ctx)
    epochs, pools, owner, parent_of = se["epochs"], se["pools"], se["owner"], se["parent_of"]
    stats, missing_logs = se["stats"], se["missing_logs"]

    def label(pool):
        return "root" if pool == root["id"] else f"one-shot:{str(pool)[:8]}"

    def sweep(entries):
        points = sorted([(s, 1) for s, e, _, _ in entries] + [(e if e is not None else t_end, -1)
                                                               for s, e, _, _ in entries])
        cur = best = 0
        segments, seg_start = [], None
        for t, d in points:
            cur += d
            best = max(best, cur)
            if k_limit is not None:
                if cur > k_limit and seg_start is None:
                    seg_start = t
                elif cur <= k_limit and seg_start is not None:
                    segments.append((seg_start, t))
                    seg_start = None
        return best, segments

    def values(pool, a, b, skip=None):
        eps = [(s, e) for s, e, c, i in pools.get(pool, []) if (c, i) != skip]
        points = {a} | {x for s, e in eps for x in (s, e) if x is not None and a < x <= b}
        return [sum(1 for s, e in eps if s <= t and (e is None or t < e)) for t in sorted(points)]

    k_messages = set()
    rejections = []
    for p in sessions:
        for cid in p["call_order"]:
            call = p["calls"][cid]
            res = p["results"].get(cid)
            if call["name"] not in SPAWN_TOOLS + (SEND_TOOL,) or not res or not num(call["time"]):
                continue
            m = LIMIT_RE.search(res["text"])
            if not m or not (res["is_error"] or res["text"].lstrip().startswith("Error")):
                continue
            if m.group(1):
                k_messages.add(int(m.group(1)))
            rejections.append((p, call, res, int(m.group(1)) if m.group(1) else None))
    k_limit = k_group if k_group is not None else (max(k_messages) if k_messages else None)

    peaks, excess = {}, []
    for pool, entries in pools.items():
        best, segments = sweep(entries)
        peaks[label(pool)] = best
        excess += [(label(pool), a, b) for a, b in segments]
    total_peak = sweep([e for entries in pools.values() for e in entries])[0] if pools else 0

    checked = []
    for p, call, res, k_msg in rejections:
        k = k_msg if k_msg is not None else k_limit
        pool = owner(p["id"])
        b = res["time"] if num(res["time"]) else call["time"]
        vals = values(pool, call["time"], b)
        checked.append({"session": p["id"][:12], "depth": p["depth"], "tool": call["name"], "t_s": rel(call["time"]),
                        "window_ms": b - call["time"], "pool": label(pool), "k_message": k_msg,
                        "occupancy_min": min(vals), "occupancy_max": max(vals),
                        "occupancy_at_result": values(pool, b, b)[0], "consistent": k is not None and k in vals})
    start_checks, start_bad = 0, []
    if k_limit is not None:
        for child, eps in epochs.items():
            pool = owner(parent_of.get(child))
            for i, e in enumerate(eps):
                b = e["window_end"] if num(e["window_end"]) and e["window_end"] >= e["start"] else e["start"]
                vals = values(pool, e["start"], b, skip=(child, i))
                start_checks += 1
                if min(vals) > k_limit - 1:
                    start_bad.append({"child": child[:12], "kind": e["kind"], "t_s": rel(e["start"]),
                                      "pool": label(pool), "others_min": min(vals)})
    all_eps = [e for eps in epochs.values() for e in eps]
    return {
        "K": k_group, "k_in_messages": sorted(k_messages), "k_used": k_limit,
        "pools": len(pools), "peak": max(peaks.values()) if peaks else 0, "peak_by_pool": peaks,
        "peak_total": total_peak,
        "slot_seconds": rnd(sum(((e["end"] if e["end"] is not None else t_end) - e["start"]) for e in all_eps) / 1000),
        "epochs": len(all_eps), "resume_epochs": sum(1 for e in all_eps if e["kind"] == "resume"),
        "unreleased_at_end": sum(1 for e in all_eps if e["end"] is None),
        "release_sources": dict(collections.Counter(e["release"] for e in all_eps)),
        "children_without_log": missing_logs, "start_from_child_header": stats["start_from_child_header"],
        "children_without_start_time": stats["no_start_time"],
        "unmatched_notices": stats["unmatched_notices"] + stats["notices_before_epoch"],
        "end_seed_mismatch": stats["end_seed_mismatch"],
        "over_capacity": bool(excess),
        "over_capacity_ms": sum(b - a for _, a, b in excess),
        "over_capacity_segments": [{"pool": pl, "from_s": rel(a), "to_s": rel(b)} for pl, a, b in excess[:EXAMPLES]],
        "rejections": len(checked), "rejections_consistent": sum(1 for r in checked if r["consistent"]),
        "rejection_checks": checked[:200],
        "starts_checked": start_checks, "starts_ok": start_checks - len(start_bad),
        "start_violations": start_bad[:EXAMPLES],
        "epoch_list": [{"child": c[:12], "pool": label(owner(parent_of.get(c))), "kind": e["kind"],
                        "from_s": rel(e["start"]), "to_s": rel(e["end"]), "release": e["release"]}
                       for c, eps in sorted(epochs.items(), key=lambda kv: kv[1][0]["start"]) for e in eps][:200],
    }


def model_intervals(s: dict, t_end) -> list:
    """[step/start, last chunk of the step's stream] per step; a step with no chunk ends at its response event,
    else at step/end, else (cut off while waiting) at the end of the run."""
    out = []
    for step in s["steps"].values():
        a = step["start"]
        if a is None:
            continue
        b = next((x for x in (step["chunk_last"], step["resp"], step["end"]) if x is not None), t_end)
        out.append((a, max(a, b)))
    return out


def time_metrics(ctx: dict, wall) -> dict:
    sessions, t_end, t0 = ctx["sessions"], ctx["t_end"], ctx["t0"]
    g = union(iv for s in sessions for iv in model_intervals(s, t_end))
    tools = union((c["time"], (s["results"].get(cid) or {}).get("time") or t_end)
                  for s in sessions for cid, c in s["calls"].items() if num(c["time"]))
    g_s = measure(g) / 1000
    t_s = (measure(tools) - overlap(tools, g)) / 1000
    agent = sum(measure(union(model_intervals(s, t_end))) for s in sessions) / 1000
    root_model = measure(union(model_intervals(ctx["root"], t_end))) / 1000
    span = (t_end - t0) / 1000 if num(t_end) and num(t0) else None
    wall_s = wall if num(wall) else span
    o_s = wall_s - g_s - t_s if wall_s is not None else None
    return {"wall_s": rnd(wall_s), "wall_from": "result.json" if num(wall) else "log span", "log_span_s": rnd(span),
            "G_s": rnd(g_s), "T_s": rnd(t_s), "O_s": rnd(o_s), "non_generation_s": rnd(None if o_s is None else t_s + o_s),
            "agent_seconds": rnd(agent), "root_model_s": rnd(root_model)}


def step_metrics(ctx: dict) -> dict:
    sessions, root, t_end = ctx["sessions"], ctx["root"], ctx["t_end"]
    replies = [m for s in sessions for m in s["messages"]]
    multi = sum(1 for m in replies if m["n_calls"] >= 2)
    root_multi = sum(1 for m in root["messages"] if m["n_calls"] >= 2)
    batches = []
    for s in sessions:
        by_step = collections.defaultdict(list)
        for cid, c in s["calls"].items():
            if num(c["time"]):
                by_step[c["key"]].append((c["time"], (s["results"].get(cid) or {}).get("time") or t_end))
        for calls in by_step.values():
            batches.append((max(b for _, b in calls) - min(a for a, _ in calls)) / 1000)
    return {"replies": len(replies), "multi_tool_replies": multi,
            "multi_tool_share": rnd(multi / len(replies), 4) if replies else None,
            "root_replies": len(root["messages"]), "root_multi_tool_replies": root_multi,
            "root_multi_tool_share": rnd(root_multi / len(root["messages"]), 4) if root["messages"] else None,
            "tool_batches": len(batches), "tool_batch_p50_s": rnd(percentile(batches, 50), 3),
            "tool_batch_p95_s": rnd(percentile(batches, 95), 3)}


def tool_path(value, cwd, home):
    if not isinstance(value, str) or not value:
        return None
    if value == "~" or value.startswith("~/"):
        value = home + value[1:]
    if not value.startswith("/"):
        if not cwd:
            return None
        value = os.path.join(cwd, value)
    return os.path.normpath(value)


def delegation_metrics(ctx: dict) -> dict:
    sessions, root = ctx["sessions"], ctx["root"]
    children = [s for s in sessions if s is not root]
    calls = collections.Counter(c["name"] for s in sessions for c in s["calls"].values())
    depth_rej = cap_rej = cap_rej_send = 0
    foreground = nested = 0
    for s in sessions:
        for cid, c in s["calls"].items():
            if c["name"] in SPAWN_TOOLS:
                if (c["args"] or {}).get("run_in_background") is False:
                    foreground += 1
                if s["depth"] >= 1:
                    nested += 1
            res = s["results"].get(cid)
            if not res or not (res["is_error"] or res["text"].lstrip().startswith("Error")):
                continue
            if c["name"] in DELEGATION_TOOLS:  # same rule as delegation_stats.read_session
                if DEPTH_REJECT.search(res["text"]):
                    depth_rej += 1
                elif CAPACITY_REJECT.search(res["text"]):
                    cap_rej += 1
            elif c["name"] == SEND_TOOL and CAPACITY_REJECT.search(res["text"]):
                cap_rej_send += 1
    return {"children": len(children),
            "children_by_depth": {str(k): v for k, v in sorted(collections.Counter(s["depth"] for s in children).items())},
            "children_by_mode": dict(collections.Counter(str(s["mode"]) for s in children)),
            "direct_children_of_root": sum(1 for s in children if s["parent"] == root["id"]),
            "calls_by_tool": {k: calls[k] for k in sorted(calls, key=str) if k in SPAWN_TOOLS + (SEND_TOOL, "skill",
                              "interrupt_agent", "list_agents", "workflow", "job_output")},
            "subagent_calls": calls["subagent"], "fork_calls": calls["subagent_fork"], "foreground_calls": foreground,
            "send_message_calls": calls[SEND_TOOL], "skill_calls": calls["skill"], "nested_delegation_calls": nested,
            "depth_rejects": depth_rej, "capacity_rejects": cap_rej, "capacity_rejects_send_message": cap_rej_send}


def misc_metrics(ctx: dict) -> dict:
    """Write conflicts, unfinished children, duplicate reads, API quality and the first request's cache."""
    sessions, root, t_end, home = ctx["sessions"], ctx["root"], ctx["t_end"], ctx["home"]
    stale = not_read = 0
    for s in sessions:
        for cid, c in s["calls"].items():
            res = s["results"].get(cid)
            if c["name"] in FS_WRITE_TOOLS and res:
                stale += STALE_TEXT in res["text"]
                not_read += NOT_READ_TEXT in res["text"]
    root_last = root["last_time"]
    open_children, written = [], {}
    for s in sessions:
        if s is root or root_last is None:
            continue
        if any(a <= root_last and (not closed or b > root_last) for a, b, closed in s["turns"]):
            open_children.append(s["id"])
            ws = ctx["workspace"]
            files = {canon(p) for p in (tool_path((c["args"] or {}).get("file_path"), s["cwd"], home)
                                        for c in s["calls"].values() if c["name"] in FS_WRITE_TOOLS) if p}
            for c in s["calls"].values():  # files the child wrote from bash inside the workspace (cat > x, sed -i)
                if c["name"] == "bash":
                    cmd = (c["args"] or {}).get("command") or ""
                    workdir = tool_path((c["args"] or {}).get("workdir"), s["cwd"], home) or s["cwd"]
                    files |= {canon(p) for kind, p in analyze_bash(cmd, workdir, home)["refs"]
                              if kind == "write" and ws and inside(canon(p), ws)}
            written[s["id"][:12]] = [os.path.relpath(f, ws) if ws and inside(f, ws) else f for f in sorted(files)]
    # Plan 6.7: child results the root got only after its last file write (write/edit) came too late to be used.
    root_writes = [c["time"] for c in root["calls"].values() if c["name"] in FS_WRITE_TOOLS and num(c["time"])]
    child_msgs = [ib["time"] for ib in root["inbox"] if num(ib["time"]) for m in ib["messages"]
                  if (m.get("source") or {}).get("kind") in ("agent-message", "subagent-settled")]
    late = sum(1 for t in child_msgs if root_writes and t > max(root_writes))
    reads = {}
    for s in sessions:
        reads[s["id"]] = {canon(p) for p in (tool_path((c["args"] or {}).get("file_path"), s["cwd"], home)
                                             for c in s["calls"].values() if c["name"] == "read") if p}
    child_reads = set().union(*[v for k, v in reads.items() if k != root["id"]]) if len(reads) > 1 else set()
    both = sorted(reads.get(root["id"], set()) & child_reads)
    attempts = [(s, a) for s in sessions for a in s["attempts"]]
    codes = collections.Counter(a["code"] for _, a in attempts if a["code"])
    replies = [(s, m) for s in sessions for m in s["messages"]]
    speeds = [(s is root, m["usage"].get("outputTokens") / ((m["last"] - m["first"]) / 1000)) for s, m in replies
              if num(m["usage"].get("outputTokens")) and m["usage"].get("outputTokens") > 0
              and m["first"] is not None and m["last"] > m["first"]]
    ttft = [(st["chunk_first"] - st["start"]) / 1000 for s in sessions for st in s["steps"].values()
            if st["start"] is not None and st["chunk_first"] is not None and st["chunk_first"] >= st["start"]]
    endings = []
    for s in sessions:
        if s["turn_ends"]:
            reason = s["turn_ends"][-1][1]
            if reason.get("kind") == "error":
                code = (reason.get("error") or {}).get("code") or "error"
                endings.append({"session": s["id"][:12], "depth": s["depth"], "code": code, "infra": infra_code(code)})
    first = root["messages"][0]["usage"] if root["messages"] else {}
    return {
        "conflicts": {"write_conflicts": stale + not_read, "stale": stale, "not_read": not_read},
        "unfinished": {"children_open_at_root_end": len(open_children), "ids": [c[:12] for c in open_children],
                       "files_written": written, "child_messages_to_root": len(child_msgs),
                       "child_messages_after_root_last_write": late},
        "duplicate_reads": {"count": len(both), "files": both[:EXAMPLES]},
        "api": {"failed_attempts": len(attempts),
                "failed_attempts_children": sum(1 for s, _ in attempts if s is not root),
                "attempt_error_codes": dict(codes),
                "child_attempt_api_errors": sum(1 for s, a in attempts if s is not root and infra_code(a["code"])),
                "sessions_ended_with_error": endings,
                "child_sessions_ended_api_error": sum(1 for e in endings if e["depth"] > 0 and e["infra"]),
                "root_ended_with_error": next((e["code"] for e in endings if e["session"] == root["id"][:12]), None),
                "gen_speed_median_tps": rnd(median([v for _, v in speeds]), 1),
                "gen_speed_root_median_tps": rnd(median([v for r, v in speeds if r]), 1),
                "gen_speed_steps": len(speeds), "ttft_median_s": rnd(median(ttft), 3)},
        "cache": {"first_request": {k: first.get(k) for k in ("cacheReadTokens", "inputTokens", "outputTokens")},
                  "attempts_before_first_reply": sum(1 for a in root["attempts"] if root["messages"]
                                                     and num(a["time"]) and num(root["messages"][0]["time"])
                                                     and a["time"] <= root["messages"][0]["time"])},
    }


def config_metrics(ctx: dict, encourage: tuple) -> dict:
    root, sessions, group, task = ctx["root"], ctx["sessions"], ctx["group"] or "", ctx["task"] or ""
    system = root["system"] or ""
    tools = root["tools"] or []
    names = sorted(t.get("name") for t in tools if isinstance(t, dict) and t.get("name"))
    project_root = None
    for u in root["users"]:
        if u["kind"] == "agent-instructions":
            try:
                project_root = json.loads(u["source"].get("baselineIdentity") or "{}").get("projectRoot")
            except (ValueError, AttributeError):
                project_root = "?"
            break
    prompt = next((u["text"] for u in root["users"] if u["kind"] == "user"), None)
    has_enc = bool(prompt) and any(prompt.rstrip().endswith(e.rstrip()) for e in encourage)
    runtime = " ".join(u["text"] for u in root["users"] if u["kind"] == "runtime-context")
    base = group[2:] if group.startswith("E-") else group
    texts = [root["cwd"] or "", system, runtime]

    def visible(word):
        return bool(word) and any(re.search(r"(?<![A-Za-z0-9])" + re.escape(word) + r"(?![A-Za-z0-9])", t) for t in texts)

    child_hashes = sorted({sha256_text(CWD_LINE_RE.sub("", s["system"]))[:16] for s in sessions
                           if s is not root and s["system"]})
    return {"system_prompt_sha256": sha256_text(CWD_LINE_RE.sub("", system)) if system else None,
            "child_system_prompt_sha256": child_hashes,
            "tool_list_sha256": sha256_text(json.dumps(tools, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
            if tools else None,
            "tool_names": names, "web_tools": any(n in ("web_search", "web_fetch") for n in names),
            "delegation_tools": [n for n in names if n in SPAWN_TOOLS + (SEND_TOOL,)],
            "project_root": project_root, "cwd": root["cwd"],
            "group_visible": visible(base), "task_visible": visible(task),
            "cwd_mentions_experiment": bool(re.search(r"experiment|subagent|实验", root["cwd"] or "", re.I)),
            "runtime_context_mentions_experiment": bool(re.search(r"experiment|实验", runtime, re.I)),
            "prompt_sha256": sha256_text(prompt) if prompt else None,
            "prompt_matches_result": None if not prompt or not ctx["result_prompt_sha256"]
            else sha256_text(prompt) == ctx["result_prompt_sha256"],
            "prompt_has_encourage": has_enc,
            "prompt_encourage_ok": None if not prompt or not group else has_enc == group.startswith("E-")}


def relay_metrics(ctx: dict, encourage: tuple) -> dict:
    root, by_id = ctx["root"], ctx["by_id"]
    texts = []
    for cid in root["call_order"]:
        c = root["calls"][cid]
        args = c["args"] or {}
        if c["name"] in SPAWN_TOOLS:
            texts.append(args.get("prompt") or "")
        elif c["name"] == SEND_TOOL and (by_id.get(norm_id(args.get("agent_id"))) or {}).get("parent") == root["id"]:
            texts.append(args.get("message") or "")
    cores = [e.rstrip("。. ") for e in encourage]
    return {"root_tasks": len(texts),
            "with_encourage": sum(1 for t in texts if any(c in t for c in cores)),
            "with_subagent": sum(1 for t in texts if "subagent" in t.lower()),
            "with_parallel": sum(1 for t in texts if "并行" in t)}


def path_metrics(ctx: dict) -> tuple:
    """(paths, bash) metrics from every tool call of the run in time order."""
    sessions, home, stage = ctx["sessions"], ctx["home"], ctx["stage"]
    exp_root = canon(str(EXP_ROOT))
    calls = sorted((c for s in sessions for c in s["calls"].values()), key=lambda c: c["time"] if num(c["time"]) else 0)
    by_id = ctx["by_id"]
    written, written_patterns = set(), set()
    out_calls, out_refs, via_home = 0, collections.Counter(), 0
    out_examples, exp_refs, exp_examples = collections.defaultdict(collections.Counter), 0, collections.Counter()
    tmp_reads, tmp_calls, tmp_examples = 0, 0, collections.Counter()
    bash_calls, cli_calls, cli_names, net_calls, net_kinds, pytest, test_writes = 0, 0, collections.Counter(), 0, \
        collections.Counter(), 0, 0

    def sample(glob_pattern):  # one name a glob matches: kb_?.html -> kb_x.html
        return re.sub(r"\[[^\]]*\]", "x", glob_pattern).replace("*", "x").replace("?", "x")

    def is_written(path):
        probe = path
        if any(ch in probe for ch in "*?["):
            # A glob reads this run's files when it matches one of them or overlaps a name pattern written here
            # (kb_?.html after `-o kb_$i.html`), or when its directory was made here.
            if path in written_patterns or any(fnmatch.fnmatchcase(w, path) for w in written) \
                    or any(fnmatch.fnmatchcase(sample(path), pat) or fnmatch.fnmatchcase(sample(pat), path)
                           for pat in written_patterns):
                return True
            probe = os.path.dirname(re.split(r"[*?\[]", probe, maxsplit=1)[0])
        while inside(probe, "/private/tmp") and probe != "/private/tmp":
            if probe in written or any(fnmatch.fnmatchcase(probe, pat) for pat in written_patterns):
                return True
            probe = os.path.dirname(probe)
        return False

    for c in calls:
        s = by_id[c["session"]]
        args = c["args"] or {}
        name = c["name"]
        refs, mentions = [], []  # mentions: (path, via_home) for the outside check
        if name in READ_TOOLS + FS_WRITE_TOOLS:
            p = tool_path(args.get("file_path"), s["cwd"], home)
            if p:
                refs.append(("write" if name in FS_WRITE_TOOLS else "read", p))
                mentions.append((p, str(args.get("file_path", "")).startswith("~")))
                if name in FS_WRITE_TOOLS and TEST_FILE_RE.search(p):
                    test_writes += 1
        elif name in SEARCH_TOOLS:
            for key in ("path", "pattern"):
                value = args.get(key)
                if key == "pattern" and not (isinstance(value, str) and value.startswith(("/", "~"))):
                    continue
                p = tool_path(value, s["cwd"], home) if value else None
                if p:
                    refs.append(("read", p))
                    mentions.append((p, str(value).startswith("~")))
        elif name == "bash":
            bash_calls += 1
            command = args.get("command") or ""
            workdir = tool_path(args.get("workdir"), s["cwd"], home) or s["cwd"]
            info = analyze_bash(command, workdir, home)
            refs = info["refs"]
            mentions = outside_refs(command, home)
            if args.get("workdir"):
                mentions.append((workdir, str(args["workdir"]).startswith("~")))
            if info["agent_clis"]:
                cli_calls += 1
                cli_names.update(info["agent_clis"])
            if info["network"]:
                net_calls += 1
                net_kinds.update(info["network"])
            pytest += info["pytest"]
            test_writes += sum(1 for kind, p in refs if kind == "write" and TEST_FILE_RE.search(p))
        flagged_out = set()
        for p, home_ref in mentions:
            pc = canon(p)
            if inside(pc, stage):
                continue
            where = "users" if inside(pc, "/Users") else "tmp" if inside(pc, "/private/tmp") else None
            if where is None:
                continue
            if pc not in flagged_out:
                flagged_out.add(pc)
                out_refs[where] += 1
                via_home += home_ref
                out_examples[where][pc] += 1
                if inside(pc, exp_root):
                    exp_refs += 1
                    exp_examples[pc] += 1
        out_calls += bool(flagged_out)
        flagged_tmp = set()
        tmp_refs = [(kind, canon(p)) for kind, p in refs]
        tmp_refs = [(kind, pc) for kind, pc in tmp_refs
                    if inside(pc, "/private/tmp") and pc != "/private/tmp" and not inside(pc, stage)]
        # Writes of the same call count before its reads: the order inside one command is not reliable (a write
        # in $(...) is analysed after the rest of the command, a helper is defined before it is called).
        for kind, pc in tmp_refs:
            if kind == "mkdir":  # mkdir -p, os.makedirs: the parents exist after it as well
                while inside(pc, "/private/tmp") and pc != "/private/tmp":
                    written.add(pc)
                    pc = os.path.dirname(pc)
            elif kind == "write":
                written.add(pc)
            elif kind == "write-pattern":
                written_patterns.add(pc)
        for kind, pc in tmp_refs:
            if kind == "read" and not is_written(pc) and pc not in flagged_tmp:
                flagged_tmp.add(pc)
                tmp_examples[pc] += 1
        tmp_reads += len(flagged_tmp)
        tmp_calls += bool(flagged_tmp)
    paths = {"stage": stage, "outside_calls": out_calls, "outside_refs": dict(out_refs), "outside_via_home": via_home,
             "outside_examples": {where: [p for p, _ in c.most_common(EXAMPLES)] for where, c in out_examples.items()},
             "experiment_dir_refs": exp_refs, "experiment_dir_examples": [p for p, _ in exp_examples.most_common(EXAMPLES)],
             "tmp_unwritten_reads": tmp_reads, "tmp_unwritten_read_calls": tmp_calls,
             "tmp_unwritten_paths": len(tmp_examples),
             "tmp_unwritten_examples": [p for p, _ in tmp_examples.most_common(EXAMPLES)]}
    bash = {"calls": bash_calls, "agent_cli_calls": cli_calls, "agent_cli_by_name": dict(cli_names),
            "network_calls": net_calls, "network_by_kind": dict(net_kinds), "pytest_runs": pytest,
            "test_file_writes": test_writes}
    return paths, bash


def usage_metrics(ctx: dict) -> dict:
    sessions, root = ctx["sessions"], ctx["root"]

    def total(group):
        out = collections.Counter()
        for s in group:
            out.update(s["usage"])
        return {k: int(v) for k, v in out.items()}

    children = [s for s in sessions if s is not root]
    return {"usage_root": total([root]), "usage_children": total(children), "usage_all": total(sessions),
            "cost_cny_peak": {"root": round(cost_cny(total([root])), 3), "children": round(cost_cny(total(children)), 3),
                              "all": round(cost_cny(total(sessions)), 3)},
            "search_aux_requests": sum(s["search_aux"] for s in sessions)}


def turn_overlap_metrics(ctx: dict) -> dict:
    """The existing definition (delegation_stats.analyze): peaks of overlapping child turns; background =
    descriptor mode "continuable"."""
    children = [s for s in ctx["sessions"] if s is not ctx["root"]]

    def ivs(group):
        return [(a, b) for s in group for a, b, _ in s["turns"]]

    return {"peak_all": peak_overlap(ivs(children))[0],
            "peak_bg": peak_overlap(ivs([s for s in children if s["mode"] == "continuable"]))[0],
            "peak_fg": peak_overlap(ivs([s for s in children if s["mode"] != "continuable"]))[0]}


def compute_run(run: dict, encourage: tuple = DEFAULT_ENCOURAGE) -> dict:
    """Every metric of one run (see the module docstring)."""
    res = run["result"]
    group = res.get("group") or run["manifest"].get("group")
    out = {"run_key": run["key"], "batch": run["batch"], "layout": run["layout"], "run_dir": str(run["dir"]),
           "task": res.get("task") or run["manifest"].get("task"), "group": group,
           "rep": res.get("rep", run["manifest"].get("rep")), "K": group_k(group),
           "encourage_group": bool(group and group.startswith("E-")), "failed_attempt": run["failed"],
           "result": result_fields(run)}
    logs, sessions = load_sessions(run["dir"])
    errors = [{"file": os.path.relpath(log["path"], run["dir"]), "error": log["error"]} for log in logs if log["error"]]
    out["log"] = {"session_files": len(logs), "sessions": len(sessions),
                  "unparsable_lines": sum(log["unparsable"] for log in logs), "errors": errors,
                  "incomplete": bool(errors) or not sessions}
    if not sessions:
        return out
    by_id = {s["id"]: s for s in sessions}
    roots = [s for s in sessions if not s["parent"] or s["parent"] not in by_id]
    root = min(roots, key=lambda s: s["depth"]) if roots else sessions[0]
    times = [t for s in sessions for t in (s["first_time"], s["last_time"]) if t is not None]
    t0 = root["created"] if root["created"] is not None else (min(times) if times else None)
    t_end = max(times) if times else t0
    cwd = root["cwd"] or res.get("cwd")
    stage = canon(os.path.dirname(os.path.normpath(cwd))) if cwd else canon(str(run["dir"]))
    v2 = run["layout"] == "v2" or res.get("runner") == "run_matrix_v2"
    m = re.match(r"^(/Users/[^/]+)", cwd or "")
    home = os.path.join(stage, "fakehome") if v2 else (m.group(1) if m else os.path.expanduser("~"))
    ctx = {"sessions": sessions, "by_id": by_id, "root": root, "t0": t0, "t_end": t_end, "K": out["K"],
           "group": group, "task": out["task"], "stage": stage, "home": home,
           "workspace": canon(cwd) if cwd else None, "result_prompt_sha256": res.get("prompt_sha256")}
    out["log"].update(root_id=root["id"], start_ms=t0, end_ms=t_end,
                      root_last_ms=root["last_time"], log_span_s=rnd((t_end - t0) / 1000) if t0 and t_end else None)
    out["delegation"] = delegation_metrics(ctx)
    out["slots"] = slot_metrics(ctx)
    out["turn_overlap"] = turn_overlap_metrics(ctx)
    out["time"] = time_metrics(ctx, res.get("seconds"))
    out["steps"] = step_metrics(ctx)
    out.update(misc_metrics(ctx))
    out["config"] = config_metrics(ctx, encourage)
    out["relay"] = relay_metrics(ctx, encourage)
    out["paths"], out["bash"] = path_metrics(ctx)
    out.update(usage_metrics(ctx))
    return out


# ---------------------------------------------------------------- outputs

def flat(r: dict) -> dict:
    """One CSV row: the scalar metrics most tables need."""
    g = (lambda *keys: _dig(r, keys))
    return collections.OrderedDict([
        ("batch", r["batch"]), ("run_key", r["run_key"]), ("task", r["task"]), ("group", r["group"]), ("rep", r["rep"]),
        ("K", r["K"]), ("failed_attempt", r["failed_attempt"]), ("exit", g("result", "exit")),
        ("seconds", g("result", "seconds")), ("timeout", g("result", "timeout")), ("crash5063", g("result", "crash5063")),
        ("attempts", g("result", "attempts")), ("sessions", g("log", "sessions")),
        ("unparsable_lines", g("log", "unparsable_lines")), ("log_incomplete", g("log", "incomplete")),
        ("children", g("delegation", "children")), ("children_depth2", g("delegation", "children_by_depth", "2")),
        ("subagent_calls", g("delegation", "subagent_calls")), ("fork_calls", g("delegation", "fork_calls")),
        ("foreground_calls", g("delegation", "foreground_calls")), ("skill_calls", g("delegation", "skill_calls")),
        ("send_message_calls", g("delegation", "send_message_calls")),
        ("nested_delegation_calls", g("delegation", "nested_delegation_calls")),
        ("depth_rejects", g("delegation", "depth_rejects")), ("capacity_rejects", g("delegation", "capacity_rejects")),
        ("capacity_rejects_send", g("delegation", "capacity_rejects_send_message")),
        ("slot_peak", g("slots", "peak")), ("slot_peak_total", g("slots", "peak_total")),
        ("slot_pools", g("slots", "pools")), ("slot_seconds", g("slots", "slot_seconds")),
        ("slot_unreleased_at_end", g("slots", "unreleased_at_end")),
        ("slot_rejections", g("slots", "rejections")), ("slot_rejections_consistent", g("slots", "rejections_consistent")),
        ("slot_starts_checked", g("slots", "starts_checked")), ("slot_starts_ok", g("slots", "starts_ok")),
        ("slot_over_capacity", g("slots", "over_capacity")),
        ("turn_overlap_peak_bg", g("turn_overlap", "peak_bg")), ("turn_overlap_peak_fg", g("turn_overlap", "peak_fg")),
        ("wall_s", g("time", "wall_s")), ("G_s", g("time", "G_s")), ("T_s", g("time", "T_s")), ("O_s", g("time", "O_s")),
        ("non_generation_s", g("time", "non_generation_s")), ("agent_seconds", g("time", "agent_seconds")),
        ("multi_tool_share", g("steps", "multi_tool_share")), ("tool_batch_p50_s", g("steps", "tool_batch_p50_s")),
        ("tool_batch_p95_s", g("steps", "tool_batch_p95_s")),
        ("write_conflicts", g("conflicts", "write_conflicts")),
        ("unfinished_children", g("unfinished", "children_open_at_root_end")),
        ("child_messages_after_root_last_write", g("unfinished", "child_messages_after_root_last_write")),
        ("duplicate_reads", g("duplicate_reads", "count")),
        ("failed_attempts", g("api", "failed_attempts")), ("child_sessions_api_error", g("api", "child_sessions_ended_api_error")),
        ("root_error", g("api", "root_ended_with_error")),
        ("gen_speed_median_tps", g("api", "gen_speed_median_tps")), ("ttft_median_s", g("api", "ttft_median_s")),
        ("first_cache_read", g("cache", "first_request", "cacheReadTokens")),
        ("system_prompt_sha256", (g("config", "system_prompt_sha256") or "")[:16]),
        ("tool_list_sha256", (g("config", "tool_list_sha256") or "")[:16]),
        ("web_tools", g("config", "web_tools")), ("project_root", g("config", "project_root")),
        ("group_visible", g("config", "group_visible")), ("prompt_encourage_ok", g("config", "prompt_encourage_ok")),
        ("relay_tasks", g("relay", "root_tasks")), ("relay_encourage", g("relay", "with_encourage")),
        ("relay_subagent", g("relay", "with_subagent")), ("relay_parallel", g("relay", "with_parallel")),
        ("outside_calls", g("paths", "outside_calls")), ("experiment_dir_refs", g("paths", "experiment_dir_refs")),
        ("tmp_unwritten_reads", g("paths", "tmp_unwritten_reads")),
        ("agent_cli_calls", g("bash", "agent_cli_calls")), ("network_calls", g("bash", "network_calls")),
        ("pytest_runs", g("bash", "pytest_runs")), ("test_file_writes", g("bash", "test_file_writes")),
        ("cost_cny_peak", g("cost_cny_peak", "all")), ("search_aux", g("search_aux_requests")),
    ])


def _dig(d, keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def _cell(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".") if abs(v) < 1e6 else f"{v:.0f}"
    return str(v)


def summary_markdown(records: list, notes: list, batches: list) -> str:
    rows = [flat(r) for r in records]
    lines = [f"# 运行指标汇总（run_metrics.py）", "",
             f"批次：{', '.join(batches)}；运行 {len(records)} 次。口径见 run_metrics.py 文件头和 code-stage-plan-draft.md 第 5 节、3.4 节。", ""]
    cols = [("task", "题"), ("group", "组"), ("rep", "次"), ("exit", "退出"), ("seconds", "秒"), ("children", "子代理"),
            ("slot_peak", "名额峰值"), ("turn_overlap_peak_bg", "轮次重叠峰值"), ("capacity_rejects", "上限被拒"),
            ("depth_rejects", "深度被拒"), ("G_s", "G 秒"), ("T_s", "T 秒"), ("O_s", "O 秒"), ("agent_seconds", "代理·秒"),
            ("multi_tool_share", "多工具步占比"), ("write_conflicts", "写冲突"), ("unfinished_children", "退出时未完成"),
            ("duplicate_reads", "重复读"), ("failed_attempts", "失败尝试"), ("gen_speed_median_tps", "生成速度中位数"),
            ("first_cache_read", "首请求缓存命中"), ("outside_calls", "越界调用"), ("tmp_unwritten_reads", "读未写/tmp"),
            ("agent_cli_calls", "智能体CLI"), ("network_calls", "联网命令"), ("unparsable_lines", "未解析行")]
    lines += ["## 每次运行", "", "| " + " | ".join(h for _, h in cols) + " |", "|" + "---|" * len(cols)]
    order = (lambda r: (str(r["task"]), str(r["group"]), r["rep"] if isinstance(r["rep"], int) else 0, r["run_key"]))
    for row in sorted(rows, key=order):
        lines.append("| " + " | ".join(_cell(row[k]) for k, _ in cols) + " |")
    lines += ["", "## 名额重建校验（3.4 节）", "",
              "每次“subagent limit reached”被拒：被拒调用从发出到返回的窗口内，调用方名额池的重建占用数应恰好等于上限 k；"
              "每次成功创建或唤醒子代理：窗口内其他占用最少不超过 k−1；任何时刻不超过 k。", ""]
    checked = [r for r in records if _dig(r, ("slots", "rejections")) or _dig(r, ("slots", "starts_checked"))]
    tot_rej = sum(r["slots"]["rejections"] for r in checked)
    tot_ok = sum(r["slots"]["rejections_consistent"] for r in checked)
    tot_st = sum(r["slots"]["starts_checked"] for r in checked)
    tot_st_ok = sum(r["slots"]["starts_ok"] for r in checked)
    over = [r for r in checked if r["slots"]["over_capacity"]]
    lines.append(f"合计：被拒 {tot_rej} 次，其中与重建一致 {tot_ok} 次；成功启动 {tot_st} 次，其中满足 ≤ k−1 的 {tot_st_ok} 次；"
                 f"出现占用超过 k 的运行 {len(over)} 次。")
    lines += ["", "| 运行 | 组 | k | 被拒 | 一致 | 成功启动 | 满足 | 超过 k | 名额峰值 | 轮次重叠峰值 | 未释放 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(checked, key=lambda r: (str(r["group"]), r["run_key"])):
        sl = r["slots"]
        if not sl["rejections"] and not sl["over_capacity"] and sl["starts_ok"] == sl["starts_checked"]:
            continue
        lines.append(f"| {r['batch']}/{r['run_key']} | {r['group']} | {sl['k_used']} | {sl['rejections']} | "
                     f"{sl['rejections_consistent']} | {sl['starts_checked']} | {sl['starts_ok']} | {_cell(sl['over_capacity'])} | "
                     f"{sl['peak']} | {r['turn_overlap']['peak_bg']} | {sl['unreleased_at_end']} |")
    bad = [(r, c) for r in checked for c in r["slots"]["rejection_checks"] if not c["consistent"]]
    if bad:
        lines += ["", "不一致的被拒：", ""]
        for r, c in bad[:50]:
            lines.append(f"- {r['batch']}/{r['run_key']}：{c['tool']} @ {c['t_s']} 秒（深度 {c['depth']}，{c['pool']}），"
                         f"k={c['k_message']}，窗口内占用 {c['occupancy_min']}–{c['occupancy_max']}")
    viol = [(r, v) for r in checked for v in r["slots"]["start_violations"]]
    if viol:
        lines += ["", "启动时其他占用已满的情况：", ""]
        for r, v in viol[:50]:
            lines.append(f"- {r['batch']}/{r['run_key']}：{v['kind']} {v['child']} @ {v['t_s']} 秒，其他占用 {v['others_min']}")
    lines += ["", "## 按题和组", "",
              "峰值>k：名额峰值超过 k 的运行数（3.4 节的 f_k 分子）。后几列是敏感性分析要剔除的运行数：退出时还有子代理没跑完、"
              "任一子会话以接口错误结束、#5063 崩溃、超时、越界或联网或调用其他智能体。", "",
              "| 题 | 组 | 次数 | 名额峰值均值 | 峰值>1 | 峰值>2 | 峰值>4 | 轮次重叠峰值均值 | 上限被拒合计 | 深度被拒合计 | "
              "退出时未完成 | 子会话接口错误 | #5063 | 超时 | 越界/联网/智能体 | 系统提示哈希 | 工具列表哈希 |",
              "|" + "---|" * 17]
    cells = collections.defaultdict(list)
    for r in records:
        if r.get("slots"):
            cells[(str(r["task"]), str(r["group"]))].append(r)
    for (task, group), rs in sorted(cells.items()):
        n = len(rs)
        peaks = [r["slots"]["peak"] for r in rs]
        share = (lambda k: f"{sum(1 for p in peaks if p > k)}/{n}")
        hashes = sorted({(r["config"]["system_prompt_sha256"] or "")[:8] for r in rs})
        tools = sorted({(r["config"]["tool_list_sha256"] or "")[:8] for r in rs})
        count = (lambda pred: sum(1 for r in rs if pred(r)))
        lines.append(f"| {task} | {group} | {n} | {sum(peaks) / n:.2f} | {share(1)} | {share(2)} | {share(4)} | "
                     f"{sum(r['turn_overlap']['peak_bg'] for r in rs) / n:.2f} | {sum(r['delegation']['capacity_rejects'] for r in rs)} | "
                     f"{sum(r['delegation']['depth_rejects'] for r in rs)} | "
                     f"{count(lambda r: r['unfinished']['children_open_at_root_end'])} | "
                     f"{count(lambda r: r['api']['child_sessions_ended_api_error'])} | "
                     f"{count(lambda r: r['result'].get('crash5063'))} | {count(lambda r: r['result'].get('timeout'))} | "
                     f"{count(lambda r: r['paths']['outside_calls'] or r['bash']['network_calls'] or r['bash']['agent_cli_calls'])} | "
                     f"{' '.join(hashes)} | {' '.join(tools)} |")
    enc_bad = [r for r in records if _dig(r, ("config", "prompt_encourage_ok")) is False]
    vis = [r for r in records if _dig(r, ("config", "group_visible"))]
    lines += ["", "## 配置核对", "",
              f"- 鼓励句与组别不符的运行：{len(enc_bad)}" + ("（" + "、".join(r["run_key"] for r in enc_bad[:20]) + "）" if enc_bad else ""),
              f"- 组名出现在 cwd、系统提示或运行时上下文里的运行：{len(vis)} / {len(records)}",
              f"- projectRoot 取值：{dict(collections.Counter(repr(_dig(r, ('config', 'project_root'))) for r in records))}",
              f"- 工具列表含 web_search/web_fetch 的运行：{sum(1 for r in records if _dig(r, ('config', 'web_tools')))} / {len(records)}"]
    if notes:
        lines += ["", "## 跳过和问题", ""] + [f"- {n}" for n in notes]
    damaged = [r for r in records if _dig(r, ("log", "incomplete"))]
    if damaged:
        lines += ["", "日志不完整（指标可能不全）：", ""] + [f"- {r['batch']}/{r['run_key']}：{r['log']['errors']}" for r in damaged]
    return "\n".join(lines) + "\n"


def write_outputs(records: list, notes: list, out: Path, batches: list) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for r in records:
        target = out / "runs" / r["batch"] / (r["run_key"].replace("/", "__") + ".json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(records, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = [flat(r) for r in records]
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["run_key"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    (out / "summary.md").write_text(summary_markdown(records, notes, batches), encoding="utf-8")


def analyze_batches(batches: list, include_failed: bool = False, encourage: tuple = DEFAULT_ENCOURAGE) -> tuple:
    records, notes = [], []
    for batch in batches:
        runs, batch_notes = discover(batch, include_failed)
        notes += batch_notes
        for run in runs:
            records.append(compute_run(run, encourage))
    return records, notes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("batches", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--include-failed", action="store_true", help="also read run_matrix_v2 _failed/ attempts")
    parser.add_argument("--encourage", action="append", help="encourage sentence(s); default: both plan sentences")
    args = parser.parse_args(argv)
    for b in args.batches:
        if not b.is_dir():
            parser.error(f"not a directory: {b}")
        if inside(str(args.out.resolve()), str(b.resolve())):
            parser.error(f"--out must not be inside a batch (batches are read-only): {args.out}")
    encourage = tuple(args.encourage) if args.encourage else DEFAULT_ENCOURAGE
    records, notes = analyze_batches(args.batches, args.include_failed, encourage)
    write_outputs(records, notes, args.out, [b.name for b in args.batches])
    rej = sum(_dig(r, ("slots", "rejections")) or 0 for r in records)
    rej_ok = sum(_dig(r, ("slots", "rejections_consistent")) or 0 for r in records)
    bad_lines = sum(_dig(r, ("log", "unparsable_lines")) or 0 for r in records)
    print(f"run_metrics: {len(records)} runs; capacity rejections {rej}, consistent with the slot reconstruction "
          f"{rej_ok}; unparsable log lines {bad_lines}; wrote {args.out}")
    for n in notes:
        print(f"  note: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
