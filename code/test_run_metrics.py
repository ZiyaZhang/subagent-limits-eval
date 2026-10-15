"""Tests for run_metrics.py and the delegation_stats.read_lines line splitting.

Synthetic session logs exercise every rule with known answers; the last tests run the metrics over the real
batches named in REAL_BATCHES (read-only) when they exist. Run: /usr/bin/python3 -m pytest -q scripts/test_run_metrics.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delegation_stats  # noqa: E402
import run_metrics as rm  # noqa: E402

EXP = Path(__file__).resolve().parent.parent
REAL_BATCHES = [EXP / "results" / "runs" / "pilot-2026-10-01", EXP / "results" / "runs" / "stage1-office-2026-10-01",
                EXP / "results" / "void" / "stage1-seq-old-runner"]
LIMIT_TEXT = ("Error: subagent limit reached (active child limit: {k}); wait for an existing child to finish or "
              "complete this work with the current agents")


# ---------------------------------------------------------------- synthetic logs

class Log:
    """One session log built event by event (times in ms; seq numbers are assigned in order)."""

    def __init__(self, sid, created, parent=None, depth=0, mode=None, cwd="/stage/x/workspace", seeded=False):
        self.id, self.created = sid, created
        self.header = {"type": "session", "version": 4, "id": sid, "createdAt": created, "cwd": cwd,
                       "isSeeded": seeded, "delegationDepth": depth}
        if parent:
            self.header.update(parentSession=parent, origin="subagent")
        self.events = []
        if mode:
            self.add("subagent/descriptor", created, {"version": 3, "mode": mode, "provider": "spawn", "label": sid})

    def add(self, etype, t, data=None):
        self.events.append({"type": etype, "seq": len(self.events), "time": t, "data": data or {}})
        return self

    def turn(self, t_start, t_end=None, turn=1, kind="completed", error=None):
        self.add("turn/start", t_start, {"turn": turn})
        if t_end is not None:
            reason = {"kind": kind}
            if error:
                reason["error"] = {"message": "x", "code": error}
            self.add("turn/end", t_end, {"turn": turn, "reason": reason})
        return self

    def step(self, t_start, chunks, turn=1, step=1, out_tokens=100, calls=(), usage=None):
        """A step: step/start, assistant/message whose stream spans `chunks` (first, last), then tool calls
        (call_id, name, args, t_call, t_result, text, is_error)."""
        self.add("step/start", t_start, {"turn": turn, "step": step})
        first, last = chunks
        stream = [{"type": "chunk", "time": first, "chunk": {"type": "block-start", "index": 0, "blockType": "text"}},
                  {"type": "text-chunks", "time0": first + 1, "index": 0, "dt": [last - first - 1], "texts": ["a", "b"]}]
        content = [{"type": "tool-call", "id": c[0], "name": c[1], "arguments": json.dumps(c[2])} for c in calls]
        self.add("assistant/message", last + 1, {
            "turn": turn, "step": step, "message": {"role": "assistant", "content": content},
            "usage": usage or {"inputTokens": 10, "outputTokens": out_tokens, "cacheReadTokens": 5}, "stream": stream})
        for cid, name, args, t_call, t_result, text, is_error in calls:
            self.add("tool/call", t_call, {"turn": turn, "step": step, "callId": cid, "name": name,
                                           "arguments": json.dumps(args, ensure_ascii=False)})
            if t_result is not None:
                self.add("tool/result", t_result, {"turn": turn, "step": step, "message": {
                    "role": "tool", "toolCallId": cid, "content": [{"type": "text", "text": text}], "isError": is_error}})
        end = max([last + 1] + [c[4] for c in calls if c[4] is not None])
        self.add("step/end", end, {"turn": turn, "step": step})
        return self

    def settled(self, child, t_inbox, t_user=None, mid=None):
        """The child's subagent-settled notice: spliced into the inbox, optionally claimed as a user/message."""
        mid = mid or f"settled-{child}-{t_inbox}"
        msg = {"content": [{"type": "text", "text": f"Subagent {child} finished."}],
               "source": {"kind": "subagent-settled", "form": "notice", "senderSessionId": child},
               "role": "user", "id": mid}
        self.add("agent/inbox/spliced", t_inbox, {"target": "next-step", "start": 0, "inserted": [msg]})
        if t_user is not None:
            self.add("agent/inbox/spliced", t_user, {"target": "next-step", "start": 0, "removedCount": 1, "inserted": []})
            self.add("user/message", t_user, dict(msg))
        return self

    def write(self, sessions_dir: Path, zstd=False):
        folder = sessions_dir / "--stage--" / self.id
        folder.mkdir(parents=True, exist_ok=True)
        text = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in [self.header] + self.events)
        if zstd:
            import zstandard
            (folder / "session.v4.jsonl.zstd").write_bytes(zstandard.ZstdCompressor().compress(text.encode("utf-8")))
        else:
            (folder / "session.v4.jsonl").write_text(text, encoding="utf-8")


def spawn(cid, t_call, t_result, child=None, k=None, background=None, label="task"):
    """A subagent tool call: started (child id) or rejected by the limit k."""
    args = {"description": label, "prompt": f"do {label}"}
    if background is not None:
        args["run_in_background"] = background
    if child:
        return (cid, "subagent", args, t_call, t_result, f"started subagent {child}", False)
    return (cid, "subagent", args, t_call, t_result, LIMIT_TEXT.format(k=k), True)


def send(cid, target, t_call, t_result, error=None):
    return (cid, "send_message", {"agent_id": target, "message": "go on"}, t_call, t_result,
            error or f"message delivered to agent {target}", bool(error))


def bash(cid, command, t_call, t_result, text="ok"):
    return (cid, "bash", {"command": command, "description": "x"}, t_call, t_result, text, False)


def make_run(tmp_path, logs, group="D2-K2", seconds=10.0, task="t1", rep=1, name=None, layout="old", zstd=False):
    """An old-layout run dir (<task>__<group>__r<rep>) with result.json and the logs; returns the run record."""
    run_dir = tmp_path / (name or f"{task}__{group}__r{rep}")
    for log in logs:
        log.write(run_dir / "home" / "sessions", zstd=zstd)
    result = {"run_id": run_dir.name, "task": task, "group": group, "rep": rep, "exit": 0, "seconds": seconds}
    (run_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
    return {"dir": run_dir, "key": run_dir.name, "layout": layout, "batch": tmp_path.name, "manifest": {},
            "result": result, "failed": False}


def root_log(created=0, cwd="/stage/x/workspace", prompt="题面"):
    log = Log("session-root", created, cwd=cwd)
    msg = {"content": [{"type": "text", "text": prompt}], "source": {"kind": "user"}, "role": "user", "id": "u1"}
    log.add("user/message", created + 1, msg)
    return log


# ---------------------------------------------------------------- reading logs

def test_read_log_splits_on_newline_only_and_counts_bad_lines(tmp_path):
    path = tmp_path / "session.v4.jsonl"
    header = {"type": "session", "version": 4, "id": "s", "createdAt": 1, "delegationDepth": 0}
    event = {"type": "tool/result", "seq": 0, "time": 2, "data": {"text": "a b c\u0085d"}}
    path.write_text(json.dumps(header) + "\n" + json.dumps(event, ensure_ascii=False) + "\n{broken\n", encoding="utf-8")
    log = rm.read_log(path)
    assert log["header"]["id"] == "s"
    assert len(log["events"]) == 1 and log["events"][0]["data"]["text"] == "a b c\u0085d"
    assert log["unparsable"] == 1
    lines = delegation_stats.read_lines(path)
    assert len(lines) == 3  # header, event, broken line; splitlines() would give 6
    assert delegation_stats.read_lines.unparsable[str(path)] == 1


def test_read_log_survives_a_truncated_zstd_stream(tmp_path):
    import hashlib
    import zstandard
    lines = [json.dumps({"type": "session", "version": 4, "id": "s", "createdAt": 1, "delegationDepth": 0})]
    lines += [json.dumps({"type": "tool/result", "seq": i, "time": 10 + i,
                          "data": {"text": hashlib.sha256(str(i).encode()).hexdigest() * 4}}) for i in range(4000)]
    text = ("\n".join(lines) + "\n").encode()
    frames = [zstandard.ZstdCompressor().compress(text[:200]), zstandard.ZstdCompressor().compress(text[200:])]
    path = tmp_path / "session.v4.jsonl.zstd"
    path.write_bytes(frames[0] + frames[1][: int(len(frames[1]) * 0.7)])  # two frames, the second cut short
    log = rm.read_log(path)
    assert log["header"]["id"] == "s" and log["error"] == "zstd: truncated stream"
    assert 1000 < len(log["events"]) < 4000 and log["unparsable"] <= 1
    path.write_bytes(frames[0] + frames[1])
    assert len(rm.read_log(path)["events"]) == 4000 and rm.read_log(path)["error"] is None


def test_forked_agent_log_counts_only_its_own_events(tmp_path):
    """A subagent_fork log starts with a copy of the parent's events, closed by session/end-seed."""
    usage = {"inputTokens": 10, "outputTokens": 5}
    copied = [{"type": "user/message", "seq": 0, "time": 5, "data": {"source": {"kind": "user"}, "content": "root task"}},
              {"type": "assistant/message", "seq": 1, "time": 10, "data": {"turn": 0, "step": 0, "usage": usage, "message": {"content": []}}},
              {"type": "tool/call", "seq": 2, "time": 11, "data": {"callId": "parent-call", "name": "web_search", "arguments": "{}"}},
              {"type": "web/deepseek-search-llm-request", "seq": 3, "time": 12, "data": {}}]
    own = [{"type": "session/end-seed", "seq": 4, "time": 100, "data": {"inherited": True}},
           {"type": "subagent/descriptor", "seq": 5, "time": 100, "data": {"mode": "continuable", "provider": "fork", "label": "x"}},
           {"type": "assistant/message", "seq": 6, "time": 110, "data": {"turn": 1, "step": 0, "usage": usage, "message": {"content": []}}},
           {"type": "tool/call", "seq": 7, "time": 111, "data": {"callId": "own-call", "name": "web_fetch", "arguments": "{}"}}]
    header = {"type": "session", "version": 4, "id": "fork", "parentSession": "root", "createdAt": 99, "delegationDepth": 1,
              "isSeeded": True}
    path = tmp_path / "session.fork.jsonl"
    path.write_text("\n".join(json.dumps(x) for x in [header] + copied + own) + "\n", encoding="utf-8")
    log = rm.read_log(path)
    assert log["inherited"] == 4 and log["error"] is None and log["events"][0]["type"] == "session/end-seed"
    s = rm.parse_session(log)
    assert s["call_order"] == ["own-call"] and s["search_aux"] == 0 and s["first_time"] == 100
    assert dict(s["usage"]) == usage and s["users"] == [] and s["label"] == "x" and len(s["end_seeds"]) == 1
    rec = delegation_stats.read_session(path)
    assert dict(rec["usage"]) == usage and rec["search_aux_requests"] == 0 and rec["first_time"] == 100
    # a log that is not seeded keeps everything before a session/end-seed (a resumed child writes one too)
    header2 = dict(header, isSeeded=False, id="resumed")
    path2 = tmp_path / "session.resumed.jsonl"
    path2.write_text("\n".join(json.dumps(x) for x in [header2] + copied + own) + "\n", encoding="utf-8")
    log2 = rm.read_log(path2)
    assert log2["inherited"] == 0 and len(log2["events"]) == 8 and rm.parse_session(log2)["call_order"] == ["parent-call", "own-call"]
    # a fork that ended while the copy was being written has no events of its own, and the log says so
    path3 = tmp_path / "session.cut.jsonl"
    path3.write_text("\n".join(json.dumps(x) for x in [header] + copied) + "\n", encoding="utf-8")
    log3 = rm.read_log(path3)
    assert log3["events"] == [] and log3["inherited"] == 4 and "end-seed" in log3["error"]


def test_delegation_stats_read_lines_survives_damaged_logs(tmp_path):
    import zstandard
    lines = [json.dumps({"type": "session", "version": 4, "id": "s", "createdAt": 1, "delegationDepth": 0})]
    lines += [json.dumps({"type": "x", "seq": i, "time": i, "data": {"t": "汉字内容" * 30}}, ensure_ascii=False)
              for i in range(3000)]
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    comp = zstandard.ZstdCompressor().compress(raw)
    path = tmp_path / "session.v4.jsonl.zstd"
    path.write_bytes(comp)
    assert delegation_stats.read_lines(path) == lines and str(path) not in getattr(
        delegation_stats.read_lines, "errors", {})
    path.write_bytes(comp[: len(comp) // 2])  # cut inside a frame, usually inside a multi-byte character too
    cut = delegation_stats.read_lines(path)
    assert 100 < len(cut) < len(lines) and cut[0] == lines[0]
    assert delegation_stats.read_lines.errors[str(path)] == "zstd: truncated stream"
    assert delegation_stats.read_lines.unparsable[str(path)] <= 1
    plain = tmp_path / "session.v4.jsonl"
    plain.write_bytes(raw[: raw.index("汉".encode()) + 1])  # a plain log cut inside a character
    assert delegation_stats.read_lines(plain)[0] == lines[0]
    assert delegation_stats.read_lines.errors[str(plain)].startswith("utf-8:")


# ---------------------------------------------------------------- bash analysis

@pytest.mark.parametrize("command,expected", [
    ('echo "run claude later"', {}),
    ("claude -p hi", {"claude": 1}),
    ("FOO=1 timeout 30 codex exec 'do x'", {"codex": 1}),
    ("bash -c 'gemini -p x'", {"gemini": 1}),
    ('echo "$(opencode run x)"', {"opencode": 1}),
    ("ls ~/.local/bin/claude", {}),
    ("/Users/ziya/.local/bin/claude -p x", {"claude": 1}),
    ("# claude -p x\necho done", {}),
    ("cat > /tmp/notes.txt <<'EOF'\nclaude -p x\nEOF", {}),
    ("command -v claude && which codex", {}),
    ("xargs -I{} gh issue view {} < ids.txt", {"gh": 1}),
    ("find . -name '*.md' -exec dsh {} \\;", {"dsh": 1}),
    ("cd /tmp && npx some-tool --version", {"npx": 1}),
    ("python3 -m pip install pypdf", {}),
    ("env -i PATH=/usr/bin lark-cli send 'hi'", {"lark-cli": 1}),
    ("for f in a b; do kimi-daimon run $f; done", {"kimi-daimon": 1}),
    ("grep -rn 'claude' src/", {}),
])
def test_agent_cli_detection_uses_command_words_only(command, expected):
    assert dict(rm.analyze_bash(command, "/w", "/home")["agent_clis"]) == expected


@pytest.mark.parametrize("command,kinds", [
    ("curl -s https://x.com -o a.html", {"curl", "http url"}),
    ("wget -qO- http://x", {"wget", "http url"}),
    ("pip3 install requests", {"pip install"}),
    ("python3 -m pip install --quiet pypdf", {"pip install"}),
    ("uv pip install x", {"pip install"}),
    ("git clone https://github.com/a/b /tmp/b", {"git clone", "http url"}),
    ("python3 -c \"import urllib.request as u; u.urlopen('https://x')\"", {"http url"}),
    ("ls -la", set()),
])
def test_network_detection(command, kinds):
    assert rm.analyze_bash(command, "/w", "/home")["network"] == kinds


def refs(command, cwd="/tmp"):
    return [(k, rm.canon(p)) for k, p in rm.analyze_bash(command, cwd, "/home")["refs"]]


def test_file_roles_for_downloads_and_reads():
    assert refs("curl -sL https://x -o /tmp/a.html; wc -c /tmp/a.html", "/w") == [
        ("write", "/private/tmp/a.html"), ("read", "/private/tmp/a.html")]
    assert refs("cd /tmp && curl -o gw1.html https://x && grep -c hygon gw1.html", "/w") == [
        ("read", "/private/tmp"), ("write", "/private/tmp/gw1.html"), ("read", "/private/tmp/gw1.html")]
    assert refs("curl -sSLo /tmp/b.pdf https://x") == [("write", "/private/tmp/b.pdf")]
    assert refs("python3 -m json.tool /tmp/a.json") == []  # module arguments have unknown roles
    assert refs("mkdir -p /tmp/res/sub") == [("mkdir", "/private/tmp/res/sub")]
    assert refs("cp /tmp/a.txt /tmp/b.txt") == [("read", "/private/tmp/a.txt"), ("write", "/private/tmp/b.txt")]
    assert refs("sed -i 's/a/b/' x_test.py", "/w") == [("write", "/w/x_test.py")]


def test_file_roles_for_code_helpers_and_computed_names():
    code = "python3 - <<'EOF'\nopen('/tmp/x.txt','w').write('a')\nprint(open('/tmp/y.txt').read())\np = '/tmp/z.txt'\nEOF"
    assert refs(code) == [("write", "/private/tmp/x.txt"), ("read", "/private/tmp/y.txt")]
    assert refs('dl(){ curl -o "$2" "$1"; }; dl https://x out.html') == [("write", "/private/tmp/out.html")]
    assert refs('./fetch.sh https://x uss_main') == [("read", "/private/tmp/fetch.sh"),
                                                      ("write-pattern", "/private/tmp/uss_main*")]
    assert refs('curl -o "rws_$(echo $p | tr / _).html" https://x') == [("write-pattern", "/private/tmp/rws_*.html")]
    assert refs('curl -o "$f" https://x') == []  # too little of the name is literal
    assert refs("python3 -c \"open(f'/tmp/pg_{h}.html','w')\"") == [("write-pattern", "/private/tmp/pg_*.html")]
    assert refs("python3 -c \"import bs4; bs4.BeautifulSoup(s, 'html.parser')\"") == []


def test_file_roles_for_relative_dirs_and_loop_variables():
    # Relative mkdir and write targets without a file extension (`cd /tmp && mkdir -p kp`) are recorded.
    assert refs("cd /tmp && rm -rf sr && mkdir sr && cd sr", "/w") == [
        ("read", "/private/tmp"), ("mkdir", "/private/tmp/sr"), ("read", "/private/tmp/sr")]
    assert refs("echo x > notes") == [("write", "/private/tmp/notes")]
    assert refs("grep x notes") == []  # a read of an extension-less relative word stays unresolved (lower bound)
    # for-loop variables, and names derived from them with ${v%%pat} / ${v#pat}, give the concrete names.
    assert refs("cd /tmp && for f in rfp2017 cint2017; do curl -s -o $f.txt https://x/$f/; done", "/w") == [
        ("read", "/private/tmp"), ("write", "/private/tmp/rfp2017.txt"), ("write", "/private/tmp/cint2017.txt")]
    assert refs('for pair in "skypark https://a" "art_tix https://b"; do name=${pair%% *}; url=${pair#* }; '
                'curl -s "$url" > /tmp/$name.md; done', "/w") == [
        ("write", "/private/tmp/skypark.md"), ("write", "/private/tmp/art_tix.md")]
    assert refs('for k in a b; do code=$(curl -s -o "/tmp/my_$k.html" -w "%{http_code}" "https://x/$k"); done') == [
        ("write", "/private/tmp/my_a.html"), ("write", "/private/tmp/my_b.html")]  # through $(...)
    assert refs('for f in "a b.pdf"; do curl -o lh_$f https://x; done') == [("write-pattern", "/private/tmp/lh_*")]
    assert refs("i=0; for u in x y; do i=$((i+1)); curl -o kb_$i.html $u; done") == [
        ("write-pattern", "/private/tmp/kb_*.html")]  # i is reassigned to something unknown
    assert (rm.trim_param("skypark https://a", "%%", " *"), rm.trim_param("skypark https://a", "#", "* "),
            rm.trim_param("a.b.c", "%", ".*"), rm.trim_param("a.b.c", "%%", ".*"),
            rm.trim_param("a/b/c", "#", "*/"), rm.trim_param("a/b/c", "##", "*/")) == (
        "skypark", "https://a", "a.b", "a", "b/c", "c")
    # An assigned f-string path is an output name pattern (it feeds curl -o or open(f, 'w')).
    assert refs("python3 - <<'EOF'\nfor k in ks:\n    f=f'/tmp/s_{k}.html'\n    run(['curl','-o',f,u])\nEOF") == [
        ("write-pattern", "/private/tmp/s_*.html")]


def test_tmp_read_check_counts_same_call_writes_globs_and_dirs(tmp_path):
    root = root_log(cwd="/Users/tester/exp/runs/b/r1/workspace")
    root.turn(0, 9000)
    root.step(10, (20, 100), calls=[
        bash("c1", "cd /tmp && mkdir -p kp && cd kp && curl -so a.pdf https://x", 200, 300),
        bash("c2", "cd /tmp/kp && python3 -c \"print(open('/tmp/kp/b.txt').read())\"", 400, 500),  # dir made here
        bash("c3", 'cd /tmp; for u in a b; do code=$(curl -s -o "/tmp/my_$u.html" https://x/$u); done; '
                   "python3 - <<'EOF'\nimport glob\nprint(glob.glob('/tmp/my_*.html'))\nEOF", 600, 700),
        bash("c4", 'cd /tmp && i=0; for u in x y; do i=$((i+1)); curl -o kb_$i.html "$u"; done; cat /tmp/kb_?.html',
             800, 900),
        bash("c5", "python3 - <<'EOF'\nfor k in ['dm']:\n    f=f'/tmp/s_{k}.html'\n    run(['curl','-o',f,u])\nEOF",
             1000, 1100),
        bash("c6", "cat /tmp/s_dm.html /tmp/f_rc.html; head /tmp/kp_old/x.txt", 1200, 1300),
    ])
    p = rm.compute_run(make_run(tmp_path, [root], group="D0"))["paths"]
    assert sorted(p["tmp_unwritten_examples"]) == ["/private/tmp/f_rc.html", "/private/tmp/kp_old/x.txt"]
    assert p["tmp_unwritten_reads"] == 2 and p["tmp_unwritten_read_calls"] == 1


def test_pytest_runs_are_counted():
    assert rm.analyze_bash("cd exercises/poker && python3 -m pytest -q poker_test.py", "/w", "/h")["pytest"] == 1
    assert rm.analyze_bash("pytest -x && echo pytest", "/w", "/h")["pytest"] == 1


def test_outside_refs_and_tmp_reads(tmp_path):
    # Old layout: the stage is the run dir (parent of the workspace), HOME the /Users/<name> the cwd starts with.
    stage = "/Users/tester/exp/runs/b/r1"
    root = root_log(cwd=stage + "/workspace")
    root.turn(0, 9000)
    root.step(10, (20, 100), calls=[
        bash("c1", "curl -s https://x -o /tmp/a.html && cat /tmp/a.html", 200, 300),
        bash("c2", "cat /tmp/old.html; ls ~/Library; cat " + str(EXP / "tasks" / "answer-keys.md"), 400, 500),
        bash("c3", f"cat {stage}/workspace/notes.md {stage}/home/x.txt", 600, 700),
        ("c4", "read", {"file_path": "/private/tmp/old.html"}, 800, 900, "x", False),
    ])
    r = rm.compute_run(make_run(tmp_path, [root], group="D0"))
    p = r["paths"]
    assert p["stage"] == stage
    assert p["tmp_unwritten_reads"] == 2 and p["tmp_unwritten_read_calls"] == 2
    assert p["tmp_unwritten_examples"] == ["/private/tmp/old.html"]
    assert p["outside_calls"] == 3  # c1, c2 and c4; c3 stays inside the stage
    assert p["outside_refs"] == {"tmp": 3, "users": 2}
    assert sorted(p["outside_examples"]["users"]) == sorted([str(EXP / "tasks" / "answer-keys.md"), "/Users/tester/Library"])
    assert p["outside_via_home"] == 1  # ~/Library -> /Users/tester/Library
    assert p["experiment_dir_refs"] == 1
    assert r["bash"]["network_calls"] == 1 and r["bash"]["calls"] == 3


# ---------------------------------------------------------------- slot reconstruction

def test_slots_rejection_matches_limit_and_release_at_spliced_notice(tmp_path):
    root = root_log()
    root.turn(0, 9000)
    root.step(10, (20, 900), calls=[spawn("a", 1000, 1010, child="A"), spawn("b", 1001, 1011, child="B"),
                                    spawn("c", 1002, 1005, k=2)])
    root.add("subagent/catalog", 1009, {"version": 0, "childId": "A", "mode": "continuable", "label": "task"})
    root.settled("A", 5000, t_user=5300)
    root.step(5300, (5310, 5400), step=2, calls=[spawn("d", 5500, 5510, child="C")])
    root.settled("B", 6000, t_user=6100)
    a = Log("A", 1005, parent="session-root", depth=1, mode="continuable").turn(1006, 4900)
    b = Log("B", 1006, parent="session-root", depth=1, mode="continuable").turn(1007, 5900)
    c = Log("C", 5505, parent="session-root", depth=1, mode="continuable").turn(5506)  # cut off at the end
    c.step(5507, (5508, 5600), calls=[bash("cb", "cat > exercises/poker/poker.py <<'EOF'\nx = 1\nEOF", 5700, 5710),
                                      ("cw", "write", {"file_path": "exercises/react/react.py", "content": "y"},
                                       5800, 5810, "ok", False)])
    r = rm.compute_run(make_run(tmp_path, [root, a, b, c]))
    s = r["slots"]
    assert s["K"] == 2 and s["peak"] == 2 and s["pools"] == 1
    assert s["rejections"] == 1 and s["rejections_consistent"] == 1
    check = s["rejection_checks"][0]
    assert check["occupancy_min"] == 2 == check["occupancy_max"] and check["k_message"] == 2
    assert s["starts_checked"] == 3 and s["starts_ok"] == 3 and not s["over_capacity"]
    assert s["unreleased_at_end"] == 1 and s["release_sources"] == {"inbox": 2, "run end": 1}
    epochs = {e["child"]: e for e in s["epoch_list"]}
    assert epochs["A"]["to_s"] == 5.0  # the spliced notice (5000), not the user/message (5300)
    assert epochs["B"]["from_s"] == 1.001 and epochs["B"]["to_s"] == 6.0
    assert r["turn_overlap"]["peak_bg"] == 2
    assert r["unfinished"]["children_open_at_root_end"] == 1 and r["unfinished"]["ids"] == ["C"]
    assert r["unfinished"]["files_written"] == {"C": ["exercises/poker/poker.py", "exercises/react/react.py"]}
    assert r["unfinished"]["child_messages_to_root"] == 2 and r["unfinished"]["child_messages_after_root_last_write"] == 0


def test_slots_reoccupied_when_send_message_wakes_a_settled_child(tmp_path):
    root = root_log()
    root.turn(0, 9000)
    root.step(10, (20, 900), calls=[spawn("a", 1000, 1010, child="A")])
    root.settled("A", 5000)
    root.step(5100, (5110, 5150), step=2, calls=[send("s1", "A", 5200, 5210), spawn("b", 5201, 5203, k=1)])
    root.settled("A", 7000)
    a = Log("A", 1005, parent="session-root", depth=1, mode="continuable").turn(1006, 4900)
    a.add("session/end-seed", 5205).turn(5206, 6900, turn=2)
    r = rm.compute_run(make_run(tmp_path, [root, a], group="D1-K1"))
    s = r["slots"]
    assert s["epochs"] == 2 and s["resume_epochs"] == 1 and s["end_seed_mismatch"] == 0
    assert [(e["from_s"], e["to_s"]) for e in s["epoch_list"]] == [(1.0, 5.0), (5.2, 7.0)]
    assert s["rejections"] == 1 and s["rejections_consistent"] == 1  # the resumed A holds the only slot


def test_slots_send_while_child_is_closing_resumes_after_the_release(tmp_path):
    root = root_log()
    root.turn(0, 9000)
    root.step(10, (20, 900), calls=[spawn("a", 1000, 1010, child="A")])
    root.step(4000, (4010, 4900), step=2, calls=[send("s1", "A", 4950, 5100)])
    root.settled("A", 5000)
    root.settled("A", 8000)
    a = Log("A", 1005, parent="session-root", depth=1, mode="continuable").turn(1006, 4940)
    a.add("session/end-seed", 5050).turn(5060, 7900, turn=2)
    s = rm.compute_run(make_run(tmp_path, [root, a], group="D1-K8"))["slots"]
    assert [(e["from_s"], e["to_s"], e["kind"]) for e in s["epoch_list"]] == [(1.0, 5.0, "create"), (5.0, 8.0, "resume")]


def test_slots_foreground_child_takes_no_slot_and_owns_a_pool(tmp_path):
    root = root_log()
    root.turn(0, 9000)
    root.step(10, (20, 900), calls=[spawn("a", 1000, 1010, child="A"),
                                    ("f", "subagent", {"description": "fg", "prompt": "x", "run_in_background": False},
                                     1001, 6000, "the answer", False)])
    root.add("subagent/catalog", 1003, {"version": 0, "childId": "F", "mode": "one-shot", "label": "fg"})
    root.settled("A", 5000)
    a = Log("A", 1005, parent="session-root", depth=1, mode="continuable").turn(1006, 4900)
    f = Log("F", 1002, parent="session-root", depth=1, mode="one-shot").turn(1003, 5990)
    f.step(1004, (1005, 1050), calls=[spawn("g", 1100, 1110, child="G"), spawn("h", 1101, 1105, k=1)])
    f.settled("G", 3000)
    g = Log("G", 1105, parent="F", depth=2, mode="continuable").turn(1106, 2900)
    r = rm.compute_run(make_run(tmp_path, [root, a, f, g], group="D2-K1"))
    s = r["slots"]
    assert s["pools"] == 2 and s["peak_by_pool"] == {"root": 1, "one-shot:F": 1} and s["peak_total"] == 2
    assert s["rejections"] == 1 and s["rejection_checks"][0]["pool"] == "one-shot:F"
    assert s["rejections_consistent"] == 1 and s["starts_ok"] == s["starts_checked"] == 2
    assert r["delegation"]["foreground_calls"] == 1 and r["turn_overlap"]["peak_fg"] == 1


def test_slots_nested_continuable_child_shares_the_root_pool(tmp_path):
    root = root_log()
    root.turn(0, 9000)
    root.step(10, (20, 900), calls=[spawn("a", 1000, 1010, child="A"), spawn("b", 1001, 1011, child="B")])
    root.settled("A", 7000)
    root.settled("B", 7100)
    a = Log("A", 1005, parent="session-root", depth=1, mode="continuable")
    a.turn(1006, 4000).step(1007, (1008, 1100), calls=[spawn("a1", 1200, 1203, k=2)])
    b = Log("B", 1006, parent="session-root", depth=1, mode="continuable").turn(1007, 7050)
    r = rm.compute_run(make_run(tmp_path, [root, a, b], group="D2-K2"))
    s = r["slots"]
    assert s["pools"] == 1 and s["rejections_consistent"] == 1
    assert s["rejection_checks"][0]["depth"] == 1 and s["rejection_checks"][0]["pool"] == "root"
    assert r["delegation"]["nested_delegation_calls"] == 1


def test_slot_check_can_fail(tmp_path):
    """A rejection the reconstruction cannot explain (here: the only child already released) is reported."""
    root = root_log()
    root.turn(0, 9000)
    root.step(10, (20, 900), calls=[spawn("a", 1000, 1010, child="A")])
    root.settled("A", 2000)
    root.step(3000, (3010, 3100), step=2, calls=[spawn("b", 3200, 3205, k=2)])
    a = Log("A", 1005, parent="session-root", depth=1, mode="continuable").turn(1006, 1900)
    s = rm.compute_run(make_run(tmp_path, [root, a], group="D2-K2"))["slots"]
    assert s["rejections"] == 1 and s["rejections_consistent"] == 0


# ---------------------------------------------------------------- time split and other metrics

def test_time_split_and_steps(tmp_path):
    root = root_log()
    root.turn(0, 3000)
    root.step(0, (100, 900), calls=[bash("t1", "sleep 1", 950, 1950), bash("t2", "true", 951, 1000)])
    root.step(2000, (2100, 2500), step=2, out_tokens=50)
    child = Log("C", 950, parent="session-root", depth=1, mode="continuable").turn(950, 1500)
    child.step(1000, (1000, 1400), out_tokens=50)  # model time inside the root's tool time
    r = rm.compute_run(make_run(tmp_path, [root, child], seconds=3.0))
    t = r["time"]
    # G = [0, 900] + [1000, 1400] + [2000, 2500] = 1.8 s; T = [950, 1950] minus G = 0.6 s; O = 3 - 1.8 - 0.6.
    assert (t["G_s"], t["T_s"], t["O_s"], t["non_generation_s"]) == (1.8, 0.6, 0.6, 1.2)
    assert t["agent_seconds"] == 1.8 and t["root_model_s"] == 1.4
    st = r["steps"]
    assert st["replies"] == 3 and st["multi_tool_replies"] == 1 and st["multi_tool_share"] == round(1 / 3, 4)
    assert st["tool_batch_p50_s"] == 1.0
    api = r["api"]
    assert api["gen_speed_steps"] == 3 and api["gen_speed_median_tps"] == 125.0  # 100 / 0.8 s, 50 / 0.4 s
    assert api["ttft_median_s"] == 0.1


def test_conflicts_duplicates_errors_cache_config_relay(tmp_path):
    enc = rm.DEFAULT_ENCOURAGE[0]
    root = root_log(prompt="做题\n\n" + enc)
    root.add("system/message", 2, {"message": {"role": "system", "content": [
        {"type": "text", "text": "You are an agent.\n\nYour working directory is /stage/x/workspace."}]}})
    root.add("request/header", 3, {"header": {"config": {}, "tools": [{"name": "bash"}, {"name": "subagent"}]}})
    root.turn(0, 9000)
    root.step(10, (20, 100), usage={"inputTokens": 4000, "outputTokens": 50, "cacheReadTokens": 384}, calls=[
        ("r1", "read", {"file_path": "src/a.py"}, 200, 210, "x", False),
        ("w1", "edit", {"file_path": "src/a.py", "old_string": "a", "new_string": "b"}, 300, 310,
         'cannot edit "src/a.py": file changed since it was read — re-read the file, then retry', True),
        ("w2", "write", {"file_path": "src/b.py", "content": "x"}, 320, 330,
         'cannot modify "src/b.py": file has not been read — read the file, then retry', True),
        spawn("a", 400, 410, child="A", label="并行查资料"),
    ])
    a = Log("A", 405, parent="session-root", depth=1, mode="continuable")
    a.turn(406, 2000, kind="error", error="STREAM_CLOSED")
    a.step(407, (408, 500), calls=[("r2", "read", {"file_path": "/stage/x/workspace/src/a.py"}, 600, 610, "x", False)])
    a.add("assistant/attempt", 700, {"turn": 1, "step": 2, "stream": [{"type": "chunk", "time": 699, "chunk": {
        "type": "finish", "reason": {"kind": "error", "failure": {"message": "x", "code": "STREAM_CLOSED"}}}}]})
    root.settled("A", 2500)  # after the root's last write (320): a result that came too late to be used
    run = make_run(tmp_path, [root, a], group="E-D2-K8")
    r = rm.compute_run(run)
    assert r["unfinished"]["child_messages_after_root_last_write"] == 1
    assert r["conflicts"] == {"write_conflicts": 2, "stale": 1, "not_read": 1}
    assert r["duplicate_reads"] == {"count": 1, "files": ["/stage/x/workspace/src/a.py"]}
    assert r["api"]["failed_attempts"] == 1 and r["api"]["attempt_error_codes"] == {"STREAM_CLOSED": 1}
    assert r["api"]["child_sessions_ended_api_error"] == 1 and r["api"]["child_attempt_api_errors"] == 1
    assert r["cache"]["first_request"] == {"cacheReadTokens": 384, "inputTokens": 4000, "outputTokens": 50}
    cfg = r["config"]
    assert cfg["system_prompt_sha256"] == rm.sha256_text("You are an agent.\n")
    assert cfg["tool_names"] == ["bash", "subagent"] and cfg["web_tools"] is False
    assert cfg["prompt_has_encourage"] and cfg["prompt_encourage_ok"] and cfg["project_root"] is None
    assert cfg["group_visible"] is False  # cwd /stage/x/workspace names no group
    assert r["relay"] == {"root_tasks": 1, "with_encourage": 0, "with_subagent": 0, "with_parallel": 1}
    assert r["K"] == 8 and r["encourage_group"] is True


# ---------------------------------------------------------------- layouts and outputs

def test_old_and_v2_layouts_and_outputs(tmp_path):
    old = tmp_path / "old-batch"
    old.mkdir()
    root = root_log()
    root.turn(0, 1000).step(10, (20, 100))
    make_run(old, [root], group="D0", task="c1", zstd=True)
    (old / "c1__D1-K8__r1" / "home").mkdir(parents=True)  # no result.json: skipped with a note

    v2 = tmp_path / "v2-batch"
    v2.mkdir()
    manifest = []
    for rid, group in (("aaaaaaaaaa", "D1-K8"), ("bbbbbbbbbb", "E-D2-K2")):
        root = root_log(cwd=f"/private/tmp/dshx/{rid}/workspace")
        root.turn(0, 1000).step(10, (20, 100), calls=[bash("c", "cat ~/x.txt /private/tmp/dshx/zzzzzzzzzz/a.txt", 200, 300)])
        rec = make_run(v2, [root], group=group, task="p4", name=rid)
        res = dict(rec["result"], id=rid, runner="run_matrix_v2", cwd=f"/private/tmp/dshx/{rid}/workspace", timeout=False,
                   crash5063=False, attempts=1, prompt_sha256=rm.sha256_text("题面" if rid == "aaaaaaaaaa" else "x"))
        (v2 / rid / "result.json").write_text(json.dumps(res), encoding="utf-8")
        manifest.append({"task": "p4", "group": group, "rep": 1, "id": rid})
    (v2 / "manifest.jsonl").write_text("".join(json.dumps(m) + "\n" for m in manifest), encoding="utf-8")
    failed = v2 / "_failed" / "cccccccccc"
    root = root_log()
    root.turn(0, 500)
    root.write(failed / "home" / "sessions")
    (failed / "attempt.json").write_text(json.dumps({"task": "p4", "group": "D0", "rep": 1, "seconds": 1.0}))

    out = tmp_path / "out"
    with pytest.raises(SystemExit):
        rm.main([str(old), "--out", str(old / "metrics")])  # never write into a batch
    assert rm.main([str(old), str(v2), "--out", str(out), "--include-failed"]) == 0
    rows = list(csv.DictReader(open(out / "summary.csv", encoding="utf-8")))
    assert sorted(r["run_key"] for r in rows) == ["_failed/cccccccccc", "aaaaaaaaaa", "bbbbbbbbbb", "c1__D0__r1"]
    by_key = {r["run_key"]: r for r in rows}
    assert by_key["bbbbbbbbbb"]["K"] == "2" and by_key["_failed/cccccccccc"]["failed_attempt"] == "True"
    assert by_key["aaaaaaaaaa"]["search_aux"] == "0"  # paired_stats needs it to price total_cost
    assert (out / "runs" / "v2-batch" / "aaaaaaaaaa.json").exists()
    assert (out / "runs" / "v2-batch" / "_failed__cccccccccc.json").exists()
    rec = json.loads((out / "runs" / "v2-batch" / "aaaaaaaaaa.json").read_text(encoding="utf-8"))
    # v2: HOME is the stage's fakehome, so ~/x.txt stays inside; another run's stage is an outside /tmp access.
    assert rec["paths"]["outside_refs"] == {"tmp": 1} and rec["paths"]["outside_via_home"] == 0
    assert rec["config"]["group_visible"] is False and rec["log"]["unparsable_lines"] == 0
    assert rec["config"]["prompt_matches_result"] is True
    other = json.loads((out / "runs" / "v2-batch" / "bbbbbbbbbb.json").read_text(encoding="utf-8"))
    assert other["config"]["prompt_matches_result"] is False and other["config"]["prompt_encourage_ok"] is False
    md = (out / "summary.md").read_text(encoding="utf-8")
    assert "名额重建校验" in md and "c1__D1-K8__r1: no result.json" in md
    assert len(json.loads((out / "summary.json").read_text(encoding="utf-8"))) == 4


# ---------------------------------------------------------------- real batches (read-only)

@pytest.fixture(scope="module")
def real_records():
    batches = [b for b in REAL_BATCHES if b.is_dir()]
    if not batches:
        pytest.skip("no real batches on this machine")
    records, _ = rm.analyze_batches(batches)
    return records


def test_real_batches_slot_reconstruction_invariant(real_records):
    with_rejections = [r for r in real_records if r["slots"]["rejections"]]
    assert with_rejections, "the stage-1 office batch has capacity rejections"
    for r in real_records:
        s = r["slots"]
        assert s["rejections_consistent"] == s["rejections"], (r["run_key"], s["rejection_checks"])
        assert s["starts_ok"] == s["starts_checked"], (r["run_key"], s["start_violations"])
        assert not s["over_capacity"], r["run_key"]
        assert s["k_in_messages"] in ([], [r["K"]]), r["run_key"]
        assert s["end_seed_mismatch"] == 0 and s["unmatched_notices"] == 0, r["run_key"]
        assert s["peak_total"] >= r["turn_overlap"]["peak_bg"], r["run_key"]
        assert r["log"]["unparsable_lines"] == 0 and not r["log"]["incomplete"], r["run_key"]


def test_real_batches_match_delegation_stats(real_records):
    for r in real_records[::7]:  # a spread of runs keeps this test short
        st = delegation_stats.analyze(Path(r["run_dir"]) / "home" / "sessions")
        assert r["turn_overlap"]["peak_bg"] == st["peak_running_background"], r["run_key"]
        assert r["turn_overlap"]["peak_fg"] == st["peak_running_foreground_oneshot"], r["run_key"]
        assert r["delegation"]["children"] == st["children"], r["run_key"]
        assert r["delegation"]["capacity_rejects"] == st["capacity_rejects"], r["run_key"]
        assert r["delegation"]["depth_rejects"] == st["depth_rejects"], r["run_key"]
        assert r["usage_all"] == st["usage_all"], r["run_key"]


def test_real_batches_time_split_is_consistent(real_records):
    for r in real_records:
        t = r["time"]
        assert t["G_s"] + t["T_s"] <= t["log_span_s"] + 0.01, r["run_key"]
        assert t["O_s"] >= -0.01 and t["agent_seconds"] + 0.01 >= t["G_s"], r["run_key"]
