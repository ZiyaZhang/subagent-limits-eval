#!/usr/bin/env python3
"""Merge tasks for module G's "four independent single-agent reports, then one merge" control (protocol v5.1 section 四).

Inputs: the D0 reports of the main batch for the g40 tasks, repeats 1-4 (rep 1 is module A's D0 run, reps 2-4 are
module G's extra D0 runs). Per task one merge task: workspace inputs/report-1.md ... report-4.md; prompt = the task's
own prompt (benchmark prompt + output paragraph + blocked-source paragraph, unchanged) followed by one paragraph that
asks for a merged report.md, the same paragraph as phase 1's office merge control with four inputs. The merge run gets
no delegation tools (group D0) and may use the web only to verify.

Run in the experiment directory on the dev box after the main batch:
  python judge-env/scripts/build_merge_tasks_drb2.py --batch p2-main
Writes tasks/ws/phase2-merge/<id>.tar.gz, tasks/phase2-merge-tasks.jsonl, tasks/phase2-merge-index.json (the base task's
idx and blocked list, so the judge and the leak check map the merge run to the base task) and tasks/cells-phase2-merge.json.
Merge task ids are drb2_m4_<idx> (the judge reads the idx from the last underscore field).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path

ROOT = Path.cwd()
PARA = ("inputs/ 目录里有 4 份已经写好的报告（report-1.md、report-2.md、report-3.md、report-4.md），是分别独立完成的，题目和上面相同。"
        "请把它们合并成一份：有来源的事实都保留，重复的只写一次；几份说法不一致的地方重新核实后再写，核实不了的写“待核验”；"
        "不用重新做一遍调研，只在需要核实时再去查；结构仍按上面的要求，输出到 report.md。")


def tar_bytes(members: list) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as tf:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(data))
    return raw.getvalue()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", default="p2-main")
    ap.add_argument("--tasks", type=Path, default=Path("tasks/phase2-drb2-tasks.jsonl"))
    ap.add_argument("--index", type=Path, default=Path("tasks/phase2-drb2-index.json"))
    ap.add_argument("--reps", default="1,2,3,4")
    a = ap.parse_args()
    reps = [int(x) for x in a.reps.split(",")]
    tasks = {}
    for line in a.tasks.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            t = json.loads(line)
            tasks[t["id"]] = t
    index = json.loads(a.index.read_text(encoding="utf-8"))
    g40 = [tid for tid, v in index.items() if "g40" in v["sets"]]
    manifest = {}
    for line in (ROOT / "results/runs" / a.batch / "manifest.jsonl").read_text(encoding="utf-8").split("\n"):
        if line.strip():
            r = json.loads(line)
            manifest[(r["task"], r["group"], r["rep"])] = r
    ws_dir = ROOT / "tasks/ws/phase2-merge"
    ws_dir.mkdir(parents=True, exist_ok=True)
    out, cells, merge_index, missing = [], [], {}, []
    for tid in sorted(g40):
        members, sources = [], []
        for n, rep in enumerate(reps, 1):
            r = manifest.get((tid, "D0", rep))
            f = ROOT / "results/runs" / a.batch / r["id"] / "workspace/report.md" if r else None
            if not r or not f.exists() or f.stat().st_size < 2000:
                missing.append((tid, rep, r["id"] if r else None))
                break
            data = f.read_bytes()
            members.append((f"inputs/report-{n}.md", data))
            sources.append({"rep": rep, "id": r["id"], "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        if len(members) != len(reps):
            continue
        idx = index[tid]["idx"]
        mid = f"drb2_m4_{idx:03d}"
        blob = tar_bytes(members)
        (ws_dir / f"{mid}.tar.gz").write_bytes(blob)
        base = tasks[tid]
        out.append({"id": mid, "type": "research-report-merge", "prompt": base["prompt"] + "\n\n" + PARA, "deliverable": "report.md",
                    "min_bytes": 2000, "web": True, "timeout_s": base.get("timeout_s", 5400), "block_hosts": base.get("block_hosts", []),
                    "workspace_tar": f"tasks/ws/phase2-merge/{mid}.tar.gz"})
        cells.append([mid, "D0", 1])
        merge_index[mid] = {**{k: index[tid][k] for k in ("idx", "theme", "description", "license", "blocked", "rubric_items")},
                            "base_task": tid, "inputs": sources, "workspace_sha256": hashlib.sha256(blob).hexdigest()}
    (ROOT / "tasks/phase2-merge-tasks.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in out), encoding="utf-8")
    (ROOT / "tasks/phase2-merge-index.json").write_text(json.dumps(merge_index, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "tasks/cells-phase2-merge.json").write_text(json.dumps(cells), encoding="utf-8")
    print(f"{len(out)} merge tasks from {len(g40)} g40 tasks; missing inputs: {missing}")
    print(f"tasks file sha256 {hashlib.sha256((ROOT / 'tasks/phase2-merge-tasks.jsonl').read_bytes()).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
