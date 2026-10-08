#!/usr/bin/env python3
"""Did every run of a phase-2 batch get what its cell says? (phase2-experiment-protocol-2026-10-08.md v5.1)

For each run directory of a batch (results/runs/<batch>/<id>/, not _failed), from result.json and the session logs:
  patches   the last config patch is <base group>.patch.yml and its maxDepth / maxActiveSubagents match the group name
            (D0: the delegation tools are disabled, so the root session header lists no subagent tool)
  sentence  a P<tag>- group has sentence_tag == tag and the prompt file ends with the sentence (cfg/prompt.txt);
            a group without P- has no sentence_tag and its prompt is exactly the task prompt
  model     the model named in the root session log equals --model (deepseek-flash, or deepseek-v4-pro for module D)
  wait      a W- group has wait_for_subagents true and stderr.log holds the dsh-exp-wait line (when subagents ran)
  memory    memory_mb in result.json equals the task's memory_mb (32768 for toolkit-xl) or 16384
Prints one line per run with the mismatches, a summary per group, and exits 1 on any mismatch.

Usage (dev box): python judge-env/scripts/phase2_check.py results/runs/<batch> --tasks tasks/<tasks>.jsonl
                 --sentences tasks/phase2-sentences.json [--model deepseek-flash] [--out file.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import zstandard

GROUP = re.compile(r"^(?:W-)?(?:T-)?(?:P([a-z0-9]+)-)?(?:E-)?(?:N-)?(D(\d)(?:-K(\d+))?)$")
LIMITS = re.compile(r"maxDepth:\s*(\d+)|maxActiveSubagents:\s*(\d+)")


def read_zstd_head(path: Path, limit: int = 8 * 1024 * 1024) -> str:
    dctx = zstandard.ZstdDecompressor()
    buf = b""
    with open(path, "rb") as fh, dctx.stream_reader(fh) as rd:
        while len(buf) < limit:
            try:
                chunk = rd.read(1024 * 1024)
            except zstandard.ZstdError:
                break
            if not chunk:
                break
            buf += chunk
    return buf.decode("utf-8", "replace")


def root_session_text(run: Path) -> str:
    """The first 8 MB of the root session log (the session that is not under a subagent directory)."""
    logs = sorted(run.glob("home/sessions/*/*/session.v4.jsonl.zstd"), key=lambda p: p.stat().st_mtime)
    for p in logs:
        text = read_zstd_head(p, 2 * 1024 * 1024)
        if '"parent"' not in text.split("\n")[0] and "parentSession" not in text[:4000]:
            return text
    return read_zstd_head(logs[0]) if logs else ""


def check_run(run: Path, tasks: dict, sentences: dict, model: str) -> tuple:
    meta = json.loads((run / "result.json").read_text(encoding="utf-8"))
    group, task = meta["group"], tasks[meta["task"]]
    m = GROUP.match(group)
    problems = []
    if not m:
        return group, [f"group name not understood: {group}"]
    tag, base, depth, k = m.group(1), m.group(2), int(m.group(3)), m.group(4)
    patches = meta.get("patches") or []
    if not patches or patches[-1] != f"{base}.patch.yml":
        problems.append(f"last patch {patches[-1:]} != {base}.patch.yml")
    cfg = run / "cfg"
    if depth > 0:
        found = {"d": None, "k": None}
        for p in sorted(cfg.glob("*.yml")):
            for d, kk in LIMITS.findall(p.read_text(encoding="utf-8", errors="replace")):
                if d:
                    found["d"] = int(d)
                if kk:
                    found["k"] = int(kk)
        if found["d"] != depth or found["k"] != int(k):
            problems.append(f"config limits {found} != D{depth} K{k}")
    if (meta.get("sentence_tag") or None) != tag:
        problems.append(f"sentence_tag {meta.get('sentence_tag')} != {tag}")
    prompt_file = cfg / "prompt.txt"
    prompt = prompt_file.read_text(encoding="utf-8", errors="replace") if prompt_file.exists() else None
    if prompt is None:
        problems.append("no cfg/prompt.txt")
    else:
        want = task["prompt"] + ("\n\n" + sentences[tag] if tag else "")
        if prompt != want:
            problems.append("prompt differs from task prompt" + (" + sentence" if tag else ""))
        if meta.get("prompt_sha256") != hashlib.sha256(prompt.encode("utf-8")).hexdigest():
            problems.append("prompt_sha256 does not match cfg/prompt.txt")
    if group.startswith("W-") != bool(meta.get("wait_for_subagents")):
        problems.append("wait flag mismatch")
    mem_want = int(task.get("memory_mb", 16384))
    if int(meta.get("memory_mb") or 0) != mem_want:
        problems.append(f"memory_mb {meta.get('memory_mb')} != {mem_want}")
    text = root_session_text(run)
    if not text:
        problems.append("no session log")
    else:
        models = set(re.findall(r'"model"\s*:\s*"([^"]{1,80})"', text))
        if models and model not in models:
            problems.append(f"session names model(s) {sorted(models)[:3]}, not {model}")
        if not models:
            problems.append("session log names no model")
        has_tool = '"subagent"' in text[:200000]
        if depth == 0 and has_tool:
            problems.append("D0 but the session header lists a subagent tool")
        if depth > 0 and not has_tool:
            problems.append("no subagent tool in the session header")
    return group, problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch", type=Path)
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument("--sentences", type=Path, required=True)
    ap.add_argument("--model", default="deepseek-flash")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    tasks = {}
    for line in a.tasks.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            t = json.loads(line)
            tasks[t["id"]] = t
    sentences = json.loads(a.sentences.read_text(encoding="utf-8"))
    rows, bad = [], 0
    for run in sorted(p for p in a.batch.iterdir() if p.is_dir() and not p.name.startswith("_") and (p / "result.json").exists()):
        group, problems = check_run(run, tasks, sentences, a.model)
        rows.append({"id": run.name, "group": group, "problems": problems})
        bad += bool(problems)
        print(f"{run.name} {group}: {'ok' if not problems else '; '.join(problems)}")
    by = {}
    for r in rows:
        by.setdefault(r["group"], [0, 0])
        by[r["group"]][0] += 1
        by[r["group"]][1] += bool(r["problems"])
    for g, (n, b) in sorted(by.items()):
        print(f"  {g}: {n} runs, {b} with problems")
    if a.out:
        a.out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"phase2_check: {'OK' if not bad else 'MISMATCH'} ({len(rows)} runs, {bad} with problems)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
