#!/usr/bin/env python3
"""Run DSH headless over tasks x groups x repeats on DSec, one container per attempt (experiment-plan-dsec-v2.md).

v6 (2026-10-08, phase 2; phase2-experiment-protocol-2026-10-08.md): a cell may carry its repeat index ([task, group, rep]);
--block-by task orders the jobs so that every cell of one task and repeat runs consecutively (block = task x repeat,
repeat-major, tasks and cells shuffled with the seed); a P<tag>- group prefix (after W-/T-, before E-/N-) appends
the sentence --sentences FILE.json[tag] to the prompt; a task may set memory_mb and cpu_cores, and the container TTL
follows the task's time limit; the endpoint probe (--probe-model) records the model id the endpoint reports into
every run's result.json (model_probe). Everything else is v5.
v6.1 (2026-10-08T21:00Z): the read-back copies only small files from the workspace / stage tmp / fake home (session logs
always), lists the rest (.ws-listing, .stage-listing, .ctmp-listing) and no longer copies the container's /tmp.

Runs on the HG dev box:
  source haienv py312-202505
  security find-generic-password -s dsllm-usersk -a zhangziya -w | ssh dev-cpu-hg \
    'cd <dir> && PYTHONPATH=<libdsec 1.21.2> python -u dsec_matrix.py --batch NAME --tasks ... --groups ... ...'
The user_sk arrives on stdin (one line) and lives only in this process.

Per attempt (random 10-character id, stage /work/<id>):
  container  IMAGE + ENV_LAYER + WS_LAYER, 4 cores / 16 GB, TTL 7200 s; network by task: web tasks
             {"lan": True, "lan/mirror": False, "www": True}, others {"lan": True, "lan/mirror": False, "www": False}.
  stage      home/ (DSH_HOME) fakehome/ (HOME) tmp/ (TMPDIR) workspace/ cfg/ bin/ (blocked-bin), owner exp. The
             workspace is a copy of /opt/ws/<template> (empty for office tasks); .ws-before / .ws-after hold
             sha256 lists of its files.
  config     cfg/<n>.yml = base.patch.yml, extra patches, <group>.patch.yml (E-<G> = G's patches + the encourage
             sentence after "\\n\\n"; N-<G> = G's patches + the no-review sentence after "\\n\\n"; prefixes in the
             order W-, E-, N-). cfg/ becomes 000 after DSH's first event (at most 60 s); DSH reads --patch at
             startup only.
  wait arm   W-<G> (or W-E-<G>) = G with the one-shot runner kept alive until every subagent has finished
             (supplementary experiment 2026-10-03): the container's @deepseek-ai/dsh-headless/lib/index.js, whose
             sha256 must be HEADLESS_ORIG_SHA, is replaced by <patches>/dsh-wait/index.js (scripts/make_wait_patch.py)
             and DSH_EXP_WAIT_SUBAGENTS=1 is set. Groups without W- run the unmodified layer.
  told arm   T-<G> (v5, 2026-10-07; after W-, before E- and N-) = G with the limit on simultaneously active subagents
             written into the description of the delegation tools: the container's
             @deepseek-ai/dsh-tool-subagent/lib/index.js, whose sha256 must be TOOL_SUBAGENT_ORIG_SHA, is replaced by
             <patches>/dsh-told/index.js (scripts/make_told_patch.py), and DSH_EXP_LIMIT_NOTE carries the sentence
             (--told, with {k} replaced by maxActiveSubagents of G's patch file). Groups without T- run the unmodified
             module and do not get the variable.
  time limit a task's "timeout_s" replaces the 3600 s limit for that task (control tasks with a stated limit).
  blocked    a task's "block_hosts" (v4, 2026-10-05): host names that root appends to the container's /etc/hosts as
             0.0.0.0 / :: before DSH starts, so neither web_fetch nor curl can open them. Used for the WideSearch
             tasks, whose gold tables are public (HuggingFace, GitHub and repositories that copy them); one pilot
             run found and copied such a table.
  workspace  a task's "workspace_tar" (a .tar.gz path relative to this script) is written into the container and
             unpacked into the workspace instead of copying a /opt/ws template (small control-task workspaces).
  key        DEEPSEEK_API_KEY (DataTask key) [+ HIGH_FIVE_API_KEY for web tasks] go into <stage>/.k with write_file
             (mode 600, owner exp); the launch sources it and deletes it before exec'ing DSH. No command line or log
             holds a key; exceptions from the write_file call are reported by type only.
  launch     runuser -u exp -- env -i <env> bash -c 'cd workspace; . ../.k; rm ../.k;
             exec timeout -s TERM -k 30 3600 node bin.js --profile headless --patch ... --json PROMPT'
  after      exit status and times as output markers (libdsec's return_code reads `exit 0` as None), exp's leftover
             processes (then killed), memory.events / memory.peak, the container's /tmp as ctmp/ (a full listing, but only files under 1 MB);
             the stage (workspace: only new or changed files) is read back as a tarball and unpacked into
             <out>/<batch>/<id>/.
Classification as run_matrix_v2: crash5063, fatal load failure and our timeout are results; a DSH provider error in
INFRA_CODES / HTTP_5xx, or no assistant message in the root session, is an infrastructure failure and the cell is
retried (at most 3 attempts per cell and invocation); so are container / copy / read-back failures. Every attempt
that is not the cell's result is kept in <batch>/_failed/<id>/.

Order: randomized complete blocks: for repeat r, every cell once, shuffled with random.Random(seed * 1000 + r);
jobs are handed to --parallel workers in that order. Finished cells (manifest.jsonl) are skipped on restart.
A file STOP in the batch directory stops new attempts; endpoints down for 2 h pause the batch (PAUSED.json, exit 3).
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import io
import json
import os
import random
import re
import secrets
import shlex
import string
import sys
import tarfile
import time
from pathlib import Path

IMAGE = "registry.high-flyer.cn/swe/ubuntu:24.04"
ENV_LAYER = "/artifacts/zhangziya/dsh-020rc2-env-v1.img"
WS_LAYER = "/artifacts/zhangziya/ws-v1.img"
NODE = "/opt/node/bin/node"
DSH_BIN = "/opt/dsh-runtime/node_modules/@deepseek-ai/dsh/lib/bin.js"
HEADLESS_JS = "/opt/dsh-runtime/node_modules/@deepseek-ai/dsh-headless/lib/index.js"
HEADLESS_ORIG_SHA = "31a4caa307b6a3bc0133e01d765c9449ff808725058639e32ebf0d020524e267"
WAIT_PATCH = "dsh-wait/index.js"  # under --patches
TOOL_SUBAGENT_JS = "/opt/dsh-runtime/node_modules/@deepseek-ai/dsh-tool-subagent/lib/index.js"
TOOL_SUBAGENT_ORIG_SHA = "26a1e804aab4c6f9cb53a670c63b817fc8d9409569e6d68eda6fda33b966a840"
TOLD_PATCH = "dsh-told/index.js"  # under --patches
DEFAULT_TOLD = ("At most {k} subagents in total can be active at the same time (started and not yet finished). "
                "A call made while {k} are active is rejected: wait for an existing subagent to finish, "
                "or complete the work with the current agents.")
LIMIT_IN_PATCH = re.compile(r"^\s*maxActiveSubagents:\s*(\d+)\s*$", re.M)
PATH_TAIL = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
MODEL_BASE_URL = "https://api-internal.deepseek.com/anthropic"
SEARCH_MODELS_URL = "https://proxy.high-five-ai.xyz:8443/v1/models"
DEFAULT_ENCOURAGE = "独立的子任务尽量交给 subagent 并行做。"
DEFAULT_NOREVIEW = "文件都写完以后，不要再另开子代理去复核、验证或补测试；需要检查就自己检查。"
NET_WEB = {"lan": True, "lan/mirror": False, "www": True}
NET_CODE = {"lan": True, "lan/mirror": False, "www": False}
CPU, MEM_MB, TTL_S = 4, 16384, 7200
COLLECT_FILE_MAX, COLLECT_TOTAL_MAX = 2 * 1024 * 1024, 64 * 1024 * 1024  # v6.1 read-back caps (bytes)
TIMEOUT_S = 3600
KILL_GRACE_S = 30
CFG_LOCK_AFTER_S = 60
MAX_ATTEMPTS = 3
PROBE_WAIT_S = 60
PROBE_LIMIT_S = 7200
ID_CHARS = string.ascii_lowercase + string.digits

INFRA_CODES = frozenset({"TRANSPORT", "TIMEOUT", "SERVER", "RATE_LIMIT", "EMPTY_RESPONSE", "STREAM_CLOSED",
                         "MALFORMED_RESPONSE", "AUTH", "QUOTA", "ACCOUNT_QUOTA", "MISSING_CREDENTIAL",
                         "INVALID_CREDENTIAL", "REQUEST_EXTENSION"})
DSH_ERROR = re.compile(r"dsh: ([A-Z0-9_]+):")
HTTP_5XX = re.compile(r"HTTP_5[0-9][0-9]")
NO_ASSISTANT = "NO_ASSISTANT_MESSAGE"
FATAL_LOAD = "fatal load failure"
CRASH5063 = "cannot read inbox state"
MARKER = re.compile(r"__RC__=(\d+) __T0__=([\d.]+) __T1__=([\d.]+) __KEYLEFT__=(\d)")

HERE = Path(__file__).resolve().parent


class InfraError(Exception):
    """A failure of DSec, the copy-in/out or the endpoints, not of the agent."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def new_id() -> str:
    return "".join(secrets.choice(ID_CHARS) for _ in range(10))


# ------------------------------------------------------------------ tasks and jobs

def load_tasks(path: Path) -> dict:
    tasks = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if not line.strip():
            continue
        t = json.loads(line)
        if not isinstance(t.get("id"), str) or not isinstance(t.get("prompt"), str) or not t["prompt"].strip():
            raise SystemExit(f"{path}:{n}: task needs id and prompt")
        if t["id"] in tasks:
            raise SystemExit(f"{path}:{n}: duplicate id {t['id']}")
        t["_line"] = line
        tasks[t["id"]] = t
    return tasks


def deliverable_spec(task: dict):
    d = task.get("deliverable")
    if d is None:
        return None
    if isinstance(d, str):
        return {"kind": "file", "name": d, "min_bytes": int(task.get("min_bytes", 2000))}
    if d.get("kind", "file") == "file":
        return {"kind": "file", "name": d["name"], "min_bytes": int(d.get("min_bytes", 2000))}
    return {"kind": "changed_files", "files": list(d["files"])}


SENTENCE_PREFIX = re.compile(r"P([a-z0-9]+)-")


def group_flags(group: str) -> tuple:
    """(base group, encourage, wait, noreview, told, sentence tag): W-, T-, P<tag>-, E-, N- prefixes in this order,
    e.g. W-T-Pb8-E-N-D1-K8."""
    wait = group.startswith("W-")
    rest = group[2:] if wait else group
    told = rest.startswith("T-")
    rest = rest[2:] if told else rest
    m = SENTENCE_PREFIX.match(rest)
    tag = m.group(1) if m else None
    rest = rest[m.end():] if m else rest
    encourage = rest.startswith("E-")
    rest = rest[2:] if encourage else rest
    noreview = rest.startswith("N-")
    return (rest[2:] if noreview else rest), encourage, wait, noreview, told, tag


def group_patches(task: dict, group: str) -> tuple:
    base, encourage = group_flags(group)[:2]
    return ["base.patch.yml", *task.get("extra_patches", []), f"{base}.patch.yml"], encourage


def build_jobs(cells: list, rep_start: int, repeats: int, seed: int, block_by: str = "none") -> list:
    """[(order, block_pos, task_id, group, rep)]. A 2-tuple cell runs once per repeat rep_start..rep_start+repeats-1;
    a 3-tuple cell (task, group, rep) runs in that repeat only. Repeat-major: the cells of repeat r are shuffled with
    random.Random(seed * 1000 + r); with block_by == "task" the tasks are shuffled and each task's cells are kept
    together (block = task x repeat). The order is the same in every invocation."""
    per_rep = {}
    for c in cells:
        if len(c) == 3:
            per_rep.setdefault(int(c[2]), []).append((c[0], c[1]))
        else:
            for r in range(rep_start, rep_start + repeats):
                per_rep.setdefault(r, []).append((c[0], c[1]))
    jobs, start = [], 0
    for r in sorted(per_rep):
        rng = random.Random(seed * 1000 + r)
        block = list(per_rep[r])
        if block_by == "task":
            order_of_tasks = sorted({t for t, _ in block})
            rng.shuffle(order_of_tasks)
            ordered = []
            for t in order_of_tasks:
                mine = [c for c in block if c[0] == t]
                rng.shuffle(mine)
                ordered += mine
            block = ordered
        else:
            rng.shuffle(block)
        jobs += [(start + pos, pos, t, g, r) for pos, (t, g) in enumerate(block)]
        start += len(block)
    return jobs


# ------------------------------------------------------------------ logs and classification

def read_log_lines(path: Path) -> list:
    try:
        if path.name.endswith(".zstd"):
            import zstandard
            chunks = []
            with open(path, "rb") as fh:
                reader = zstandard.ZstdDecompressor().stream_reader(fh, read_across_frames=True)
                try:
                    while True:
                        chunk = reader.read(1 << 20)
                        if not chunk:
                            break
                        chunks.append(chunk)
                except zstandard.ZstdError:
                    pass
            data = b"".join(chunks)
        else:
            data = path.read_bytes()
        return [line.decode("utf-8", errors="replace") for line in data.split(b"\n") if line.strip()]
    except (OSError, ImportError):
        return []


def root_assistant_messages(sessions: Path) -> int:
    try:
        paths = sorted(set(sessions.rglob("session*.jsonl")) | set(sessions.rglob("session*.jsonl.zstd")))
    except OSError:
        return 0
    total = 0
    for path in paths:
        lines = read_log_lines(path)
        try:
            header = json.loads(lines[0]) if lines else None
        except ValueError:
            continue
        if not isinstance(header, dict) or header.get("type", "session") != "session":
            continue
        if header.get("parentSession") or header.get("delegationDepth", 0) != 0:
            continue
        for line in lines[1:]:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and event.get("type") == "assistant/message":
                total += 1
    return total


def classify(stderr: str, root_assistant: int, timed_out: bool) -> dict:
    crash = CRASH5063 in stderr
    fatal = FATAL_LOAD in stderr
    infra = None
    for code in DSH_ERROR.findall(stderr):
        if code in INFRA_CODES or HTTP_5XX.fullmatch(code):
            infra = code
            break
    if infra is None and root_assistant == 0:
        infra = NO_ASSISTANT
    retry = infra is not None and not timed_out and not crash and not (fatal and root_assistant > 0)
    return {"crash5063": crash, "fatal_load_failure": fatal, "infra_signal": infra, "retry": retry}


def sha_list(path: Path) -> dict:
    out = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").split("\n"):
            if len(line) > 66 and line[64:66] == "  ":
                out[line[66:].removeprefix("./")] = line[:64]
    except OSError:
        pass
    return out


def check_deliverable(spec, run_dir: Path):
    if spec is None:
        return None
    if spec["kind"] == "file":
        f = run_dir / "workspace" / spec["name"]
        exists = f.is_file()
        size = f.stat().st_size if exists else 0
        return {"kind": "file", "name": spec["name"], "min_bytes": spec["min_bytes"], "exists": exists, "bytes": size,
                "ok": exists and size >= spec["min_bytes"]}
    before, after = sha_list(run_dir / ".ws-before"), sha_list(run_dir / ".ws-after")
    changed = {name: before.get(name) != after.get(name) for name in spec["files"]}
    return {"kind": "changed_files", "changed": sum(changed.values()), "files": changed}


def memory_events(run_dir: Path) -> dict:
    out = {}
    try:
        for line in (run_dir / ".memory.events").read_text().split("\n"):
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                out[parts[0]] = int(parts[1])
    except OSError:
        pass
    try:
        out["peak_bytes"] = int((run_dir / ".memory.peak").read_text().strip())
    except (OSError, ValueError):
        pass
    return out


def leftovers(run_dir: Path) -> dict:
    names = []
    try:
        for line in (run_dir / ".leftover").read_text(errors="replace").split("\n"):
            parts = line.split(None, 2)
            if len(parts) == 3:
                names.append(parts[2][:120])
    except OSError:
        pass
    return {"count": len(names), "names": names[:20]}


# ------------------------------------------------------------------ probes (from the dev box)

def probe(user_sk: str, web: bool, model: str = "deepseek-flash") -> tuple:
    """(error or None, the model id the endpoint reports or None)."""
    import httpx
    model_id = None
    try:
        r = httpx.post(f"{MODEL_BASE_URL}/v1/messages", timeout=30, trust_env=False,
                       headers={"x-api-key": f"sk-internal-datatask-zhangziya-{user_sk}", "anthropic-version": "2023-06-01",
                                "content-type": "application/json"},
                       json={"model": model, "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]})
        if r.status_code != 200:
            return f"model http {r.status_code}", None
        try:
            model_id = r.json().get("model")
        except ValueError:
            model_id = None
        if web:
            r = httpx.get(SEARCH_MODELS_URL, timeout=30, trust_env=False, headers={"authorization": f"Bearer {user_sk}"})
            if r.status_code != 200:
                return f"search proxy http {r.status_code}", model_id
    except Exception as e:  # noqa: BLE001 - the request carries the key; report the type only
        return f"probe {type(e).__name__}", None
    return None, model_id


# ------------------------------------------------------------------ the batch

class Batch:
    def __init__(self, args, tasks: dict, jobs: list, user_sk: str):
        self.args, self.tasks, self.jobs, self.user_sk = args, tasks, jobs, user_sk
        self.dir = Path(args.out) / args.batch
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "_failed").mkdir(exist_ok=True)
        self.patch_dir = Path(args.patches)
        self.log_path = self.dir / "run.log"
        self.done = self.read_manifest()
        self.lock = asyncio.Lock()
        self.running = 0
        self.finished = 0
        self.infra_retries = 0
        self.paused = None
        self.probe_down_since = None
        self.client = None
        self.model_probe = None
        self.sentences = json.loads(Path(args.sentences).read_text(encoding="utf-8")) if args.sentences else {}

    def log(self, line: str) -> None:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%SZ")
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(f"[{stamp}] {line}\n")
        print(f"[{stamp}] {line}", flush=True)

    def read_manifest(self) -> set:
        done = set()
        p = self.dir / "manifest.jsonl"
        if p.exists():
            for line in p.read_text(encoding="utf-8").split("\n"):
                if line.strip():
                    try:
                        r = json.loads(line)
                        done.add((r["task"], r["group"], r["rep"]))
                    except (ValueError, KeyError):
                        pass
        return done

    def write_progress(self, state: str) -> None:
        write_json(self.dir / "progress.json", {
            "batch": self.args.batch, "total": len(self.jobs), "done": len(self.done), "running": self.running,
            "infra_retries": self.infra_retries, "state": state, "updated_utc": utc_now()})

    async def wait_ready(self, web: bool) -> bool:
        while True:
            err, model_id = await asyncio.to_thread(probe, self.user_sk, web, self.args.probe_model)
            if err is None:
                self.probe_down_since = None
                if model_id and model_id != self.model_probe:
                    self.log(f"endpoint reports model {model_id}")
                    self.model_probe = model_id
                return True
            now = time.time()
            self.probe_down_since = self.probe_down_since or now
            self.log(f"endpoint not ready: {err}; waiting")
            if now - self.probe_down_since > self.args.probe_limit:
                self.paused = {"reason": f"endpoints down {self.args.probe_limit} s", "last": err, "at": utc_now()}
                write_json(self.dir / "PAUSED.json", self.paused)
                return False
            await asyncio.sleep(PROBE_WAIT_S)

    async def attempt(self, task: dict, group: str, rep: int, order: int, pos: int, attempt_no: int) -> dict:
        from libdsec import DSecContainerRunArgs, DSecMountPoint
        rid = new_id()
        S = f"/work/{rid}"
        patches, encourage = group_patches(task, group)
        wait, noreview, told, tag = group_flags(group)[2:]
        note = None
        if told:
            found = LIMIT_IN_PATCH.findall((self.patch_dir / patches[-1]).read_text(encoding="utf-8"))
            if len(found) != 1:
                raise RuntimeError(f"{patches[-1]}: maxActiveSubagents found {len(found)} times")
            note = self.args.told.replace("{k}", found[0])
        limit = int(task.get("timeout_s", TIMEOUT_S))
        cpu, mem_mb = int(task.get("cpu_cores", CPU)), int(task.get("memory_mb", MEM_MB))
        ttl = max(TTL_S, limit + 1800)
        sentence = self.sentences[tag] if tag else None
        prompt = (task["prompt"] + ("\n\n" + sentence if sentence else "") + ("\n\n" + self.args.encourage if encourage else "")
                  + ("\n\n" + self.args.noreview if noreview else ""))
        web = bool(task.get("web"))
        net = NET_WEB if web else NET_CODE
        tmpl = task.get("workspace_template")
        permission = task.get("permission", "workspace-write")
        layers = [ENV_LAYER, WS_LAYER, *task.get("extra_layers", [])]
        meta = {"id": rid, "task": task["id"], "group": group, "rep": rep, "order": order, "block_pos": pos,
                "attempt": attempt_no, "runner": "dsec_matrix_v6.1", "platform": "dsec", "parallel": self.args.parallel,
                "shuffle": self.args.seed, "timeout_s": float(limit), "image": IMAGE, "layers": layers,
                "wait_for_subagents": wait, "told_limit": told, "limit_note": note,
                "cpu_cores": cpu, "memory_mb": mem_mb, "ttl_s": ttl, "network_rules": net, "patches": patches, "web": web,
                "model_probe": self.model_probe, "sentence_tag": tag,
                "sentence_sha256": sha256_bytes(sentence.encode("utf-8")) if sentence else None,
                "patch_sha256": {p: sha256_bytes((self.patch_dir / p).read_bytes()) for p in patches},
                "prompt_sha256": sha256_bytes(prompt.encode("utf-8")), "task_sha256": sha256_bytes(task["_line"].encode("utf-8")),
                "encourage_sha256": sha256_bytes(self.args.encourage.encode("utf-8")) if encourage else None,
                "noreview_sha256": sha256_bytes(self.args.noreview.encode("utf-8")) if noreview else None,
                "permission": permission, "cwd": f"{S}/workspace", "stage": S, "workspace_template": tmpl,
                "workspace_tar": task.get("workspace_tar"), "blocked_hosts": list(task.get("block_hosts") or [])}
        env = {"USER": "exp", "LOGNAME": "exp", "SHELL": "/bin/bash", "LANG": "C.UTF-8", "TERM": "dumb",
               "DSH_PERMISSION_MODE": permission, "DEEPSEEK_BASE_URL": MODEL_BASE_URL, "NODE_USE_SYSTEM_CA": "1",
               "HOME": f"{S}/fakehome", "TMPDIR": f"{S}/tmp", "PATH": f"{S}/bin:{PATH_TAIL}", "DSH_HOME": f"{S}/home"}
        if wait:
            env["DSH_EXP_WAIT_SUBAGENTS"] = "1"
        if told:
            env["DSH_EXP_LIMIT_NOTE"] = note
        meta["env_public"] = dict(env)
        meta["env_names"] = sorted([*env, "DEEPSEEK_API_KEY", *(["HIGH_FIVE_API_KEY"] if web else [])])
        c = None
        t_create = time.time()
        try:
            try:
                c = await self.client.run_container(DSecContainerRunArgs(
                    container_image=IMAGE, cpu_cores_limit=cpu, memory_limit_mb=mem_mb,
                    ttl_running_pause=ttl, ttl_running_stop=ttl, ttl_paused_stop=ttl,
                    mount_points=[DSecMountPoint(kind="layer", host_relative_path=p) for p in layers],
                    network_rules=net), timeout=600)
            except Exception as e:  # noqa: BLE001
                raise InfraError(f"run_container {type(e).__name__}: {str(e)[:200]}") from None
            meta["container_id"] = c.id
            meta["container_seconds"] = round(time.time() - t_create, 1)
            copy_ws = f"cp -a /opt/ws/{shlex.quote(tmpl)}/. {S}/workspace/" if tmpl else ":"
            ws_tar = task.get("workspace_tar")
            if ws_tar:
                blob = (HERE / ws_tar).read_bytes()
                meta["workspace_tar_sha256"] = sha256_bytes(blob)
                await c.run_shell(f"mkdir -p {S}", timeout=60)
                await c.write_file(blob, f"{S}/.ws.tar.gz")
                copy_ws = f"tar -xzf {S}/.ws.tar.gz -C {S}/workspace --no-same-owner && rm -f {S}/.ws.tar.gz"
            prep = (f"mkdir -p {S}/home {S}/fakehome {S}/tmp {S}/workspace {S}/cfg {S}/bin && "
                    f"cp /opt/exp/blocked-bin/* {S}/bin/ && chmod 755 {S}/bin/* && {copy_ws} && chown -R exp:exp {S} && chmod 700 {S} && "
                    f"(cd {S}/workspace && find . -type f -print0 | sort -z | xargs -0 -r sha256sum > {S}/.ws-before) && "
                    f"echo __PREP_OK__ $(ls -A /tmp | wc -l)")
            r = await c.run_shell(prep, timeout=900)
            if "__PREP_OK__" not in (r.output or ""):
                raise InfraError(f"prep failed: {(r.output or '')[-300:]}")
            meta["tmp_entries_at_start"] = int((r.output or "").split("__PREP_OK__")[-1].strip() or 0)
            if meta["blocked_hosts"]:
                lines = "".join(f"0.0.0.0 {h}\n:: {h}\n" for h in meta["blocked_hosts"])
                await c.write_file(lines.encode("utf-8"), f"{S}/.hosts-block")
                r = await c.run_shell(f"cat {S}/.hosts-block >> /etc/hosts && rm -f {S}/.hosts-block && "
                                      f"echo __HOSTS_OK__ $(grep -c '^0.0.0.0 ' /etc/hosts) $(getent hosts {shlex.quote(meta['blocked_hosts'][0])} | head -1)",
                                      timeout=60)
                tail = (r.output or "").split("__HOSTS_OK__")[-1].split()   # count, then getent's address (:: or 0.0.0.0) and name
                if "__HOSTS_OK__" not in (r.output or "") or len(tail) < 2 or int(tail[0]) < len(meta["blocked_hosts"]) or tail[1] not in ("::", "0.0.0.0"):
                    raise InfraError(f"blocking hosts failed: {(r.output or '')[-200:]}")
            r = await c.run_shell(f"sha256sum {HEADLESS_JS} | cut -c1-64", timeout=60)
            if HEADLESS_ORIG_SHA not in (r.output or ""):
                raise InfraError(f"headless entry is not the expected file: {(r.output or '')[-100:]}")
            if wait:
                patched = (self.patch_dir / WAIT_PATCH).read_bytes()
                await c.write_file(patched, HEADLESS_JS)
                r = await c.run_shell(f"chmod 644 {HEADLESS_JS} && sha256sum {HEADLESS_JS} | cut -c1-64", timeout=60)
                meta["headless_patch_sha256"] = sha256_bytes(patched)
                if meta["headless_patch_sha256"] not in (r.output or ""):
                    raise InfraError("the patched headless entry did not land")
            if told:
                r = await c.run_shell(f"sha256sum {TOOL_SUBAGENT_JS} | cut -c1-64", timeout=60)
                if TOOL_SUBAGENT_ORIG_SHA not in (r.output or ""):
                    raise InfraError(f"the delegation-tool module is not the expected file: {(r.output or '')[-100:]}")
                patched = (self.patch_dir / TOLD_PATCH).read_bytes()
                await c.write_file(patched, TOOL_SUBAGENT_JS)
                r = await c.run_shell(f"chmod 644 {TOOL_SUBAGENT_JS} && sha256sum {TOOL_SUBAGENT_JS} | cut -c1-64", timeout=60)
                meta["told_patch_sha256"] = sha256_bytes(patched)
                if meta["told_patch_sha256"] not in (r.output or ""):
                    raise InfraError("the patched delegation-tool module did not land")
            for i, name in enumerate(patches):
                await c.write_file((self.patch_dir / name).read_bytes(), f"{S}/cfg/{i}.yml")  # libdsec: content, dest
            keys = f"DEEPSEEK_API_KEY=sk-internal-datatask-zhangziya-{self.user_sk}\n"
            if web:
                keys += f"HIGH_FIVE_API_KEY={self.user_sk}\n"
            try:
                await c.write_file(keys.encode("utf-8"), f"{S}/.k")
            except Exception as e:  # noqa: BLE001 - the call arguments carry the key
                raise InfraError(f"write_file(.k) {type(e).__name__}") from None
            r = await c.run_shell(f"chown -R exp:exp {S}/cfg {S}/.k && chmod 600 {S}/.k && chmod 644 {S}/cfg/*.yml && echo __KEY_OK__",
                                  timeout=120)
            if "__KEY_OK__" not in (r.output or ""):
                raise InfraError("key/cfg permissions failed")
            argv = [NODE, DSH_BIN, "--profile", "headless"]
            for i in range(len(patches)):
                argv += ["--patch", f"{S}/cfg/{i}.yml"]
            argv += ["--json"]
            # The task text goes in through standard input, not the command line: a subagent's `pkill -f <word>`
            # matched the DSH process itself when the prompt (which named pytest) was in its arguments.
            await c.write_file(prompt.encode("utf-8"), f"{S}/cfg/prompt.txt")
            await c.run_shell(f"chown exp:exp {S}/cfg/prompt.txt && chmod 644 {S}/cfg/prompt.txt", timeout=60)
            inner = (f"cd {S}/workspace && set -a && . {S}/.k && set +a && rm -f {S}/.k && "
                     f"exec timeout -s TERM -k {KILL_GRACE_S} {limit} {shlex.join(argv)} < {S}/cfg/prompt.txt > {S}/events.jsonl 2> {S}/stderr.log")
            env_str = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
            # The patch files are locked once the session has started, so the agent cannot read the limits.
            # A task may switch that off (lock_cfg false) when the running process has to re-read them.
            lock = f"chmod 000 {S}/cfg" if task.get("lock_cfg", True) else ":"
            meta["cfg_locked"] = bool(task.get("lock_cfg", True))
            launch = (f"touch {S}/.start; "
                      f"( i=0; while [ $i -lt {CFG_LOCK_AFTER_S * 2} ]; do [ -s {S}/events.jsonl ] && break; sleep 0.5; i=$((i+1)); done; "
                      f"{lock} ) & W=$!; "
                      f"T0=$(date +%s.%N); runuser -u exp -- env -i {env_str} bash -c {shlex.quote(inner)}; RC=$?; T1=$(date +%s.%N); "
                      f"kill $W 2>/dev/null; wait $W 2>/dev/null; chmod 700 {S}/cfg; "
                      f"if [ -e {S}/.k ]; then KL=1; rm -f {S}/.k; else KL=0; fi; "
                      f"ps -u exp -o pid=,etimes=,args= > {S}/.leftover 2>/dev/null; pkill -TERM -u exp 2>/dev/null; sleep 2; "
                      f"pkill -KILL -u exp 2>/dev/null; "
                      f"cat /sys/fs/cgroup/memory.events > {S}/.memory.events 2>/dev/null; "
                      f"cat /sys/fs/cgroup/memory.peak > {S}/.memory.peak 2>/dev/null; "
                      f"echo \"__RC__=$RC __T0__=$T0 __T1__=$T1 __KEYLEFT__=$KL\"")
            meta["started_utc"] = utc_now()
            try:
                r = await c.run_shell(launch, timeout=limit + KILL_GRACE_S + 600)
            except Exception as e:  # noqa: BLE001
                raise InfraError(f"launch run_shell {type(e).__name__}: {str(e)[:160]}") from None
            meta["ended_utc"] = utc_now()
            m = MARKER.search(r.output or "")
            if not m:
                raise InfraError(f"no exit marker: {(r.output or '')[-300:]}")
            rc, t0, t1, keyleft = int(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4) == "1"
            meta.update({"exit": rc, "seconds": round(t1 - t0, 1), "key_file_left": keyleft})
            pc = task.get("post_check")
            if pc:
                meta["post_check"] = await self.post_check(c, S, pc, patches, env)
            # v6.1 (2026-10-08T21:00Z): the read-back used to copy the whole stage; runs that save hundreds of pages
            # made 0.3-1.2 GB stages and the copy took 20-30 min per run. Now: every session log (home/) is kept; from
            # the workspace only changed files up to COLLECT_FILE_MAX each and COLLECT_TOTAL_MAX in all (the deliverable
            # first, then small files first); the stage tmp and the fake home only files under COLLECT_FILE_MAX; the
            # container's /tmp is listed, not copied. Library folders the model installs (.venv, site-packages,
            # node_modules ...) are listed but never copied. .ws-listing (sha256, size, path) records every changed
            # workspace file, copied or not, so saved pages can still be counted.
            deliverable_name = (task.get("deliverable") or {}).get("name", "") if isinstance(task.get("deliverable"), dict) else (task.get("deliverable") or "")
            collect = (f"(cd {S}/workspace && find . -type f -print0 | sort -z | xargs -0 -r sha256sum > {S}/.ws-after); "
                       f"find /tmp -mindepth 1 -printf '%y\\t%s\\t%p\\n' > {S}/.ctmp-listing 2>/dev/null; "
                       f"find {S} -mindepth 1 -printf '%y\\t%s\\t%P\\n' > {S}/.stage-listing 2>/dev/null; "
                       f"python3 - {S} {shlex.quote(str(deliverable_name))} {COLLECT_FILE_MAX} {COLLECT_TOTAL_MAX} <<'PY'\n"
                       "import os, sys\nS, deliv, fmax, tmax = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])\n"
                       "def load(p):\n    d = {}\n    for line in open(p, encoding='utf-8', errors='replace'):\n"
                       "        line = line.rstrip('\\n')\n        if len(line) > 66: d[line[66:]] = line[:64]\n    return d\n"
                       "b, a = load(S + '/.ws-before'), load(S + '/.ws-after')\n"
                       "rid = S.rsplit('/', 1)[1]\n"
                       "changed = [k for k, v in a.items() if b.get(k) != v]\n"
                       "def size(k):\n    try: return os.path.getsize(S + '/workspace/' + k[2:])\n    except OSError: return 0\n"
                       "with open(S + '/.ws-listing', 'w') as fh:\n    for k in changed: fh.write(a[k] + '\\t' + str(size(k)) + '\\t' + k[2:] + '\\n')\n"
                       "LIB = ('/.venv/', '/venv/', 'site-packages', 'node_modules', '__pycache__', '/.git/', 'dist-info', '/.cache/')\n"
                       "def lib(k):\n    s = '/' + k[2:]\n    return any(x in s for x in LIB)\n"
                       "order = sorted((k for k in changed if not lib(k)), key=lambda k: (0 if (deliv and k[2:] == deliv) else 1, size(k)))\n"
                       "total = 0\n"
                       "with open(S + '/.ws-collect', 'w') as fh:\n"
                       "    for k in order:\n        s = size(k)\n        if k[2:] != deliv and (s > fmax or total + s > tmax): continue\n"
                       "        total += s\n        fh.write(rid + '/workspace/' + k[2:] + '\\n')\n"
                       "with open(S + '/.ws-deleted', 'w') as fh:\n    fh.write('\\n'.join(k for k in b if k not in a))\n"
                       "PY\n"
                       f"cd /work && find {rid} -type f ! -path '{rid}/workspace/*' ! -path '{rid}/ctmp/*' "
                       f"\\( -path '{rid}/home/*' -o -size -{COLLECT_FILE_MAX // 1024 + 1}k \\) -print0 | tar --null -T - -cf /work/{rid}.tar && "
                       f"{{ [ ! -s {S}/.ws-collect ] || tar -rf /work/{rid}.tar -T {S}/.ws-collect; }} && gzip -1 /work/{rid}.tar && "
                       f"echo __PACK_OK__ $(stat -c %s /work/{rid}.tar.gz)")
            r = await c.run_shell(collect, timeout=1200)
            if "__PACK_OK__" not in (r.output or ""):
                raise InfraError(f"pack failed: {(r.output or '')[-300:]}")
            try:
                data = await c.read_file(f"/work/{rid}.tar.gz")
            except Exception as e:  # noqa: BLE001
                raise InfraError(f"read_file {type(e).__name__}: {str(e)[:160]}") from None
            data = bytes(data)
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                tf.extractall(self.dir, filter="data")
            meta["stage_tar_bytes"] = len(data)
            run_dir = self.dir / rid
            if self.user_sk.encode() in data or any(self.user_sk.encode() in p.read_bytes()
                                                   for p in run_dir.rglob("*") if p.is_file() and p.stat().st_size < 50_000_000):
                meta["key_in_stage"] = True  # recorded; the stage is scrubbed below
                for p in run_dir.rglob("*"):
                    if p.is_file():
                        b = p.read_bytes()
                        if self.user_sk.encode() in b:
                            p.write_bytes(b.replace(self.user_sk.encode(), b"<user_sk>"))
            else:
                meta["key_in_stage"] = False
        finally:
            if c is not None:
                try:
                    await c.stop()
                except Exception as e:  # noqa: BLE001
                    self.log(f"{rid}: stop failed {type(e).__name__}")
        run_dir = self.dir / rid
        stderr = (run_dir / "stderr.log").read_text(encoding="utf-8", errors="replace") if (run_dir / "stderr.log").exists() else ""
        ra = root_assistant_messages(run_dir / "home" / "sessions")
        timed_out = meta["exit"] == 124 or (meta["exit"] == 137 and meta["seconds"] >= limit - 5)
        cls = classify(stderr, ra, timed_out)
        mem = memory_events(run_dir)
        meta.update({"timeout": timed_out, "root_assistant_messages": ra, **{k: cls[k] for k in ("crash5063", "fatal_load_failure", "infra_signal")},
                     "retry": cls["retry"], "oom_kill": mem.get("oom_kill", 0) > 0, "memory": mem,
                     "leftover_processes": leftovers(run_dir), "deliverable": check_deliverable(deliverable_spec(task), run_dir)})
        return meta

    async def post_check(self, c, S: str, pc: dict, patches: list, env: dict) -> dict:
        """After the run, with every agent process gone, start the profile again in the same DSH home.
        boots: for each entry, the one-shot runner is switched off and a checker plugin is inserted; it runs the
          hidden cases through the tool registry (no model call), writes check/<name>/out.json and exits. An entry
          may add one more patch (for example a config override of the plugin under test).
        session_prompt: one ordinary one-shot session with this prompt (one small model request), events in
          check/session/events.jsonl; the grader compares what the plugin reported with that session's log.
        The case files enter the container only now."""
        pc_dir = HERE / pc["dir"]
        limit = int(pc.get("timeout_s", 120))
        env_str = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items() if k not in ("DSH_EXP_WAIT_SUBAGENTS", "DSH_EXP_LIMIT_NOTE"))
        base_argv = [NODE, DSH_BIN, "--profile", "headless"]
        for i in range(len(patches)):
            base_argv += ["--patch", f"{S}/cfg/{i}.yml"]
        out = {"boots": {}, "files_sha256": {}}
        try:
            await c.run_shell(f"mkdir -p {S}/check && cp {S}/home/profiles/headless/package.json {S}/check/profile-package.json 2>/dev/null; "
                              f"ls -la {S}/home/profiles/headless/node_modules/@local/ > {S}/check/profile-links.txt 2>&1; true", timeout=60)
            checker = (pc_dir / "index.js").read_bytes()
            out["files_sha256"]["index.js"] = sha256_bytes(checker)
            await c.write_file(checker, f"{S}/check/index.js")
            for boot in pc.get("boots", []):
                name = boot["name"]
                D = f"{S}/check/{name}"
                cases = (pc_dir / boot["cases"]).read_bytes()
                out["files_sha256"][boot["cases"]] = sha256_bytes(cases)
                await c.run_shell(f"mkdir -p {D}", timeout=60)
                await c.write_file(cases, f"{D}/cases.json")
                patch = ("- id: headless-runner\n  disabled: true\n- insert:\n    - id: exp-checker\n"
                         f"      name: '{S}/check/index.js'\n      config:\n        cases: '{D}/cases.json'\n"
                         f"        out: '{D}/out.json'\n        waitMs: {int(pc.get('wait_ms', 8000))}\n")
                await c.write_file(patch.encode("utf-8"), f"{D}/checker.patch.yml")
                argv = list(base_argv)
                if boot.get("patch"):
                    extra = (pc_dir / boot["patch"]).read_bytes()
                    out["files_sha256"][boot["patch"]] = sha256_bytes(extra)
                    await c.write_file(extra, f"{D}/extra.patch.yml")
                    argv += ["--patch", f"{D}/extra.patch.yml"]
                argv += ["--patch", f"{D}/checker.patch.yml", "noop"]
                inner = f"cd {S}/workspace && exec timeout -s KILL {limit} {shlex.join(argv)} > {D}/stdout.log 2> {D}/stderr.log"
                r = await c.run_shell(f"chown -R exp:exp {S}/check; runuser -u exp -- env -i {env_str} bash -c {shlex.quote(inner)}; RC=$?; "
                                      f"pkill -KILL -u exp 2>/dev/null; "
                                      f"echo \"__CHECK_RC__=$RC __OUT__=$(stat -c %s {D}/out.json 2>/dev/null || echo 0)\"", timeout=limit + 120)
                mm = re.search(r"__CHECK_RC__=(-?\d+) __OUT__=(\d+)", r.output or "")
                out["boots"][name] = {"exit": int(mm.group(1)), "out_bytes": int(mm.group(2))} if mm else {"error": (r.output or "")[-200:]}
            prompt = pc.get("session_prompt")
            if prompt:
                D = f"{S}/check/session"
                s_limit = int(pc.get("session_timeout_s", 300))
                await c.run_shell(f"mkdir -p {D} && chown -R exp:exp {S}/check && "
                                  f"(ls -d {S}/home/sessions/*/* 2>/dev/null | sort > {D}/.before; true)", timeout=60)
                try:
                    await c.write_file(f"DEEPSEEK_API_KEY=sk-internal-datatask-zhangziya-{self.user_sk}\n".encode("utf-8"), f"{S}/.k")
                except Exception as e:  # noqa: BLE001 - the call arguments carry the key
                    raise InfraError(f"write_file(.k) {type(e).__name__}") from None
                argv = [*base_argv, "--json"]
                await c.write_file(prompt.encode("utf-8"), f"{D}/prompt.txt")
                inner = (f"cd {S}/workspace && set -a && . {S}/.k && set +a && rm -f {S}/.k && "
                         f"exec timeout -s TERM -k {KILL_GRACE_S} {s_limit} {shlex.join(argv)} < {D}/prompt.txt > {D}/events.jsonl 2> {D}/stderr.log")
                r = await c.run_shell(f"chown exp:exp {S}/.k {D}/prompt.txt && chmod 600 {S}/.k; runuser -u exp -- env -i {env_str} bash -c {shlex.quote(inner)}; RC=$?; "
                                      f"rm -f {S}/.k; pkill -KILL -u exp 2>/dev/null; echo \"__CHECK_RC__=$RC __OUT__=$(stat -c %s {D}/events.jsonl 2>/dev/null || echo 0)\"",
                                      timeout=s_limit + KILL_GRACE_S + 120)
                mm = re.search(r"__CHECK_RC__=(-?\d+) __OUT__=(\d+)", r.output or "")
                out["session"] = {"exit": int(mm.group(1)), "events_bytes": int(mm.group(2))} if mm else {"error": (r.output or "")[-200:]}
                # The check session's log moves out of home/sessions, so the run's own metrics never count it.
                r = await c.run_shell(f"mkdir -p {D}/sessions; ls -d {S}/home/sessions/*/* 2>/dev/null | sort > {D}/.after; "
                                      f"comm -13 {D}/.before {D}/.after | while read -r d; do mv \"$d\" {D}/sessions/; done; "
                                      f"ls {D}/sessions | wc -l", timeout=120)
                out["session"]["moved_sessions"] = int((r.output or "0").strip().split()[-1]) if (r.output or "").strip() else 0
            out["ran"] = True
        except InfraError:
            raise
        except Exception as e:  # noqa: BLE001 - a failed check is recorded, the run itself stays valid
            out.update({"ran": False, "error": f"{type(e).__name__}: {str(e)[:160]}"})
        return out

    async def run_cell(self, job) -> None:
        order, pos, tid, group, rep = job
        task = self.tasks[tid]
        failed = []
        for attempt_no in range(1, MAX_ATTEMPTS + 1):
            if self.paused or (self.dir / "STOP").exists():
                return
            if not await self.wait_ready(bool(task.get("web"))):
                return
            try:
                meta = await self.attempt(task, group, rep, order, pos, attempt_no)
            except InfraError as e:
                self.infra_retries += 1
                self.log(f"{tid} {group} r{rep} attempt {attempt_no}: infrastructure failure: {e}")
                failed.append({"attempt": attempt_no, "error": str(e)[:300], "at": utc_now()})
                await asyncio.sleep(10 * attempt_no)
                continue
            rid = meta["id"]
            if meta["retry"]:
                self.infra_retries += 1
                self.log(f"{tid} {group} r{rep} attempt {attempt_no} ({rid}): infra signal {meta['infra_signal']}"
                         + ("; retrying" if attempt_no < MAX_ATTEMPTS else "; no attempts left"))
                dest = self.dir / "_failed" / rid
                os.replace(self.dir / rid, dest)
                write_json(dest / "attempt.json", meta)
                failed.append({"attempt": attempt_no, "id": rid, "infra_signal": meta["infra_signal"]})
                continue
            meta["attempts"] = attempt_no
            meta["failed_attempts"] = failed
            meta["failed_attempt_ids"] = [f["id"] for f in failed if "id" in f]
            write_json(self.dir / rid / "result.json", meta)
            line = {k: meta.get(k) for k in ("task", "group", "rep", "id", "order", "attempts", "exit", "seconds", "timeout",
                                              "crash5063", "fatal_load_failure", "infra_signal", "oom_kill", "key_file_left")}

            line["deliverable_ok"] = (meta["deliverable"] or {}).get("ok", (meta["deliverable"] or {}).get("changed"))
            async with self.lock:
                with open(self.dir / "manifest.jsonl", "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(line, ensure_ascii=False) + "\n")
                self.done.add((tid, group, rep))
            self.log(f"{tid} {group} r{rep} order={order} id={rid} exit={meta['exit']} {meta['seconds']}s attempts={attempt_no}"
                     + (" TIMEOUT" if meta["timeout"] else "") + (" crash5063" if meta["crash5063"] else "")
                     + (" OOM" if meta["oom_kill"] else "") + (" KEYFILE-LEFT" if meta["key_file_left"] else "")
                     + (" KEY-IN-STAGE" if meta.get("key_in_stage") else ""))
            return
        with open(self.dir / "failures.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"task": tid, "group": group, "rep": rep, "order": order, "attempts": failed}, ensure_ascii=False) + "\n")
        self.log(f"{tid} {group} r{rep}: gave up after {MAX_ATTEMPTS} attempts")

    async def worker(self, queue: asyncio.Queue) -> None:
        while True:
            try:
                job = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            if self.paused or (self.dir / "STOP").exists():
                return
            self.running += 1
            self.write_progress("running")
            try:
                await self.run_cell(job)
            except Exception as e:  # noqa: BLE001 - one cell's bug must not stop the batch
                self.log(f"{job[2]} {job[3]} r{job[4]}: runner error {type(e).__name__}: {str(e)[:300]}")
            finally:
                self.running -= 1
                self.write_progress("running")

    async def run(self) -> int:
        from libdsec import DSecClient
        todo = [j for j in self.jobs if (j[2], j[3], j[4]) not in self.done]
        write_json(self.dir / "batch.json", {
            "batch": self.args.batch, "started_utc": utc_now(), "tasks": sorted({j[2] for j in self.jobs}),
            "cells": sorted({(j[2], j[3]) for j in self.jobs}), "repeats": [self.args.rep_start, self.args.repeats],
            "seed": self.args.seed, "parallel": self.args.parallel, "image": IMAGE, "layers": [ENV_LAYER, WS_LAYER],
            "task_options": {t: {k: self.tasks[t].get(k) for k in ("permission", "extra_layers", "extra_patches", "post_check", "lock_cfg") if self.tasks[t].get(k) is not None}
                             for t in sorted({j[2] for j in self.jobs})},
            "cpu_cores": CPU, "memory_mb": MEM_MB, "timeout_s": TIMEOUT_S, "net_web": NET_WEB, "net_code": NET_CODE,
            "encourage": self.args.encourage, "noreview": self.args.noreview, "told": self.args.told,
            "sentences": self.sentences, "probe_model": self.args.probe_model, "block_by": self.args.block_by,
            "runner_sha256": sha256_bytes(Path(__file__).read_bytes())})
        self.log(f"batch {self.args.batch}: {len(self.jobs)} jobs, {len(todo)} to run, parallel {self.args.parallel}")
        self.client = DSecClient()
        await self.client.open()
        queue = asyncio.Queue()
        for j in todo:
            queue.put_nowait(j)
        self.write_progress("running")
        try:
            await asyncio.gather(*(self.worker(queue) for _ in range(self.args.parallel)))
        finally:
            await self.client.close()
        state = "paused" if self.paused else "stopped" if (self.dir / "STOP").exists() else "done"
        self.write_progress(state)
        self.log(f"batch {self.args.batch} {state}: {len(self.done)} of {len(self.jobs)} cells recorded")
        return 3 if self.paused else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", required=True)
    ap.add_argument("--tasks", required=True, type=Path)
    ap.add_argument("--only", help="comma-separated task ids")
    ap.add_argument("--groups", help="comma-separated groups for every selected task")
    ap.add_argument("--cells", type=Path, help="JSON list of [task, group] pairs instead of --only/--groups")
    ap.add_argument("--repeats", type=int, default=1, help="repeats for 2-tuple cells; 3-tuple cells carry their own")
    ap.add_argument("--rep-start", type=int, default=1)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--parallel", type=int, required=True)
    ap.add_argument("--patches", default=str(HERE / "patches"))
    ap.add_argument("--out", default=str(HERE / "results" / "runs"))
    ap.add_argument("--encourage", default=DEFAULT_ENCOURAGE)
    ap.add_argument("--noreview", default=DEFAULT_NOREVIEW, help="sentence appended for N- groups")
    ap.add_argument("--told", default=DEFAULT_TOLD, help="sentence appended to the delegation tools' description for T- groups; {k} = the limit")
    ap.add_argument("--probe-limit", type=int, default=PROBE_LIMIT_S)
    ap.add_argument("--block-by", choices=("none", "task"), default="none", help="task: every cell of a task and repeat runs consecutively")
    ap.add_argument("--sentences", type=Path, help="JSON {tag: sentence} for P<tag>- groups")
    ap.add_argument("--probe-model", default="deepseek-flash", help="model the endpoint probe asks for (deepseek-v4-pro for module D)")
    ap.add_argument("--plan-only", action="store_true", help="print the job order and exit (no key, no container)")
    args = ap.parse_args()
    tasks = load_tasks(args.tasks)
    if args.cells:
        cells = [tuple(x) for x in json.loads(args.cells.read_text(encoding="utf-8"))]
    else:
        ids = [s for s in (args.only or "").split(",") if s] or list(tasks)
        groups = [g for g in (args.groups or "").split(",") if g]
        cells = [(t, g) for t in ids for g in groups]
    if any(len(c) not in (2, 3) for c in cells):
        raise SystemExit("a cell is [task, group] or [task, group, rep]")
    sentences = json.loads(args.sentences.read_text(encoding="utf-8")) if args.sentences else {}
    for t, g in sorted({(c[0], c[1]) for c in cells}):
        if t not in tasks:
            raise SystemExit(f"unknown task {t}")
        tag = group_flags(g)[5]
        if tag and tag not in sentences:
            raise SystemExit(f"{g}: no sentence for tag {tag} in --sentences")
        for p in group_patches(tasks[t], g)[0]:
            if not (Path(args.patches) / p).is_file():
                raise SystemExit(f"missing patch {p}")
        if group_flags(g)[2] and not (Path(args.patches) / WAIT_PATCH).is_file():
            raise SystemExit(f"missing {WAIT_PATCH} (scripts/make_wait_patch.py)")
        if group_flags(g)[4]:
            if not (Path(args.patches) / TOLD_PATCH).is_file():
                raise SystemExit(f"missing {TOLD_PATCH} (scripts/make_told_patch.py)")
            if "{k}" not in args.told:
                raise SystemExit("--told needs {k}")
            if len(LIMIT_IN_PATCH.findall((Path(args.patches) / group_patches(tasks[t], g)[0][-1]).read_text(encoding="utf-8"))) != 1:
                raise SystemExit(f"{g}: its patch file does not set maxActiveSubagents exactly once")
        pc = tasks[t].get("post_check")
        if pc:
            need = ["index.js", *[b["cases"] for b in pc.get("boots", [])], *[b["patch"] for b in pc.get("boots", []) if b.get("patch")]]
            lost = [n for n in need if not (HERE / pc["dir"] / n).is_file()]
            if lost:
                raise SystemExit(f"missing post_check files for {t}: {lost}")
        if tasks[t].get("permission", "workspace-write") not in ("workspace-write", "danger-full-access"):
            raise SystemExit(f"unknown permission for {t}")
    # Background runs get the key in DSEC_USER_SK (set from a shell variable, never a file) and drop it at once;
    # foreground runs read it from stdin.
    jobs = build_jobs(cells, args.rep_start, args.repeats, args.seed, args.block_by)
    if args.plan_only:
        for order, pos, t, g, r in jobs:
            print(order, pos, t, g, r)
        print(f"{len(jobs)} jobs, {len({j[2] for j in jobs})} tasks, {len({(j[2], j[3]) for j in jobs})} cells")
        return 0
    user_sk = os.environ.pop("DSEC_USER_SK", "").strip() or sys.stdin.readline().strip()
    if not user_sk:
        raise SystemExit("no user_sk (DSEC_USER_SK or stdin)")
    return asyncio.run(Batch(args, tasks, jobs, user_sk).run())


if __name__ == "__main__":
    sys.exit(main())
