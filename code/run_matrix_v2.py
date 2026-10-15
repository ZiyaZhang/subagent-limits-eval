#!/usr/bin/env python3
"""Run DSH headless over tasks x groups x repeats, one run at a time, each run isolated.

Replaces run_matrix.py for new batches, so that the experimental group is the only thing that differs
between cells (code-stage-plan-draft.md, section 7.2):

- Every attempt gets a random 10-character id and runs in <stage-root>/<id>/ with its own home/ (DSH_HOME),
  workspace/, tmp/ (TMPDIR), fakehome/ (HOME), bin/ (first on PATH: a copy of runtime/blocked-bin, whose
  placeholders shadow other agents' CLIs and package runners) and cfg/ (the patches, copied without their
  comments). So the paths DSH and the agent see, and DSH's command line, name neither the task, the group nor
  the project folder. Afterwards the directory moves to BATCH_DIR/<id>, and BATCH_DIR/manifest.jsonl maps
  (task, group, rep) to the id.
- The child environment is built from a whitelist. Proxy variables and NODE_USE_SYSTEM_CA are copied when set,
  so runs take the same network path as earlier ones.
- DSH starts in its own session. The wall-clock timeout sends SIGTERM to its process group and SIGKILL 10 s
  later. DSH exits 0 on SIGTERM, so only "timeout" in result.json marks a timeout, never "exit". After every
  attempt, processes still working in the stage directory are ended; new top-level entries of /private/tmp are
  moved into the attempt's tmp-leftovers/ (entries still open, sockets, other users' entries and protected
  names stay, listed in tmp_new_kept); and whatever the attempt left in the stage root itself (writable for the
  agent, like all of /private/tmp) is moved into its stage-root-leftovers/.
- Only infrastructure failures are retried (a DSH provider error code in stderr, or a root session without a
  single assistant message), each time with a new id, at most 3 attempts per cell in one invocation. Failed
  attempts are kept in BATCH_DIR/_failed/. Our wall-clock timeout, the inbox-state crash (crash5063), another
  unhandled DSH error after the model answered, any other exit and a missing or short deliverable are results
  and are never retried.
- Before each attempt a readiness probe (curl, through the proxy DSH would use) checks the model endpoint, and
  the search proxy when the task uses the web. The batch pauses (writes BATCH_DIR/PAUSED.json and exits with
  code 3) when the endpoints stay down for 2 hours, a cell fails 3 times in a row, workspace preparation fails,
  or DSH or a workspace template changes during the batch. Run the same command again to resume.
- BATCH_DIR/batch.json records the conditions when the batch starts (tasks, groups, seed, timeout, encourage
  text, permission, patches, DSH, templates, runner, public environment). A later invocation that differs in
  any of them refuses to start; only --repeats and --rep-start may change. To run under new conditions, start
  a new batch directory.
- --lock paths (answer keys, judgments, earlier runs, ...) are chmod 000 for the whole batch. Their modes are
  saved in BATCH_DIR/locks.json first, so the next start undoes the locks of a runner killed with SIGKILL before
  it reads anything (the task file and patches/ may be lock paths; scripts/, if locked, has to be chmod-ed back by
  hand first, since python must read this file). BATCH_DIR itself is 000 except while a finished run is moved in.

Task file (JSONL), one task per line:
  {"id": "o1", "type": "office", "prompt": "...", "files": {"a.txt": "..."}, "deliverable": "report.md"}
  {"id": "c1", "prompt": "...", "workspace_from": "/abs/dir", "extra_patches": ["noweb.patch.yml"],
   "deliverable": {"kind": "changed_files", "files": ["src/x.py"]}}
"deliverable" is a file name (with an optional task-level "min_bytes", default 2000), {"kind": "file",
"name": ..., "min_bytes": ...} or {"kind": "changed_files", "files": [...]}. "web" defaults to true, and
to false when extra_patches has noweb.patch.yml; only web tasks get HIGH_FIVE_API_KEY and the search probe.
A workspace must not hold a .env (DSH would load it into its environment).

Groups: G runs the patches base.patch.yml, then the task's extra_patches, then G.patch.yml. E-G runs
exactly G's patches with "\\n\\n" + --encourage appended to the prompt. Nothing else differs.

Usage:
  run_matrix_v2.py --tasks tasks.jsonl --groups D0,D1-K8,E-D2-K4 --repeats 5 --shuffle SEED --out BATCH_DIR
                   [--rep-start 1] [--only id,...] [--timeout 3600] [--lock PATH ...]
                   [--stage-root /private/tmp/dshx] [--permission workspace-write] [--dry-run]
  run_matrix_v2.py @ARGS_FILE   (the same arguments, one per line, e.g. @<(printf '%s\\n' ...): every run can
                                 list the runner's command line, so this keeps the seed and groups off it)

Order: randomized complete blocks, as in run_matrix.py: every repeat runs each task x group once, shuffled
with seed SEED*1000 + rep, so stopping after any repeat leaves all groups with the same number of runs.
"order" in result.json is the cell's position in the whole batch, (rep - 1) x block size + block_pos.

Exit codes: 0 done; 1 unexpected error (traceback; DSH stopped, locks restored); 2 bad arguments, task file,
paths or changed conditions; 3 paused (see BATCH_DIR/PAUSED.json); 130/143/129 stopped by SIGINT/SIGTERM/SIGHUP
(DSH stopped, locks restored, the attempt kept in BATCH_DIR/_interrupted/, the cell runs again on resume).
One runner at a time per --stage-root and per --out.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import errno
import fcntl
import hashlib
import ipaddress
import json
import os
import pwd
import random
import re
import secrets
import shutil
import signal
import stat
import string
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = Path(__file__).resolve()
PATCHES = ROOT / "patches"
RUNTIME = ROOT / "runtime"
BLOCKED_BIN = RUNTIME / "blocked-bin"
NODE_MODULES = RUNTIME / "node_modules"
DSH_PACKAGE = NODE_MODULES / "@deepseek-ai" / "dsh"
DSH_BIN = DSH_PACKAGE / "lib" / "bin.js"
DSH_LOCKFILE = RUNTIME / "package-lock.json"
NODE = "/Users/ziya/.nvm/versions/node/v22.22.1/bin/node"
FAKE_DSH = ROOT / "scripts" / "fake_dsh.py"  # stands in for DSH under --dry-run
PYTHON = "/usr/bin/python3"
CURL = "/usr/bin/curl"
LSOF = "/usr/sbin/lsof"
PS = "/bin/ps"
# DSH's workspace-write sandbox lets the agent write (and chmod) anywhere under /tmp, so nothing there is safe.
PRIVATE_TMP = Path("/private/tmp")

# Same endpoints as run_matrix.py: the internal DeepSeek endpoint (Messages protocol) and the company
# search proxy that base.patch.yml points web-search-deepseek at.
MODEL_BASE_URL = "https://api-internal.deepseek.com/anthropic"
SEARCH_MODELS_URL = "https://proxy.high-five-ai.xyz:8443/v1/models"
DEFAULT_ENCOURAGE = "独立的子任务尽量交给 subagent 并行做。"
NOWEB_PATCH = "noweb.patch.yml"
DRY_RUN_USER_SK = "dummy-user-sk"
CHILD_PATH_TAIL = "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"  # PATH after the attempt's own bin/

MAX_ATTEMPTS = 3       # per cell and invocation; only infrastructure failures use up attempts
TERM_GRACE_S = 10      # wall-clock timeout: SIGTERM to the process group, SIGKILL after this
CFG_LOCK_AFTER_S = 60  # lock cfg/ after this many seconds even if DSH has printed nothing yet
LEFTOVER_GRACE_S = 5   # leftover processes: SIGTERM, SIGKILL after this
ABORT_GRACE_S = 0.5    # the same, for an attempt that is being discarded (stop signal, error)
PROBE_TIMEOUT_S = 20   # a readiness request must answer within this
PROBE_WAIT_S = 60      # between readiness checks (--probe-wait changes it in tests only)
PROBE_LIMIT_S = 7200   # pause when the endpoints stay down this long (--probe-limit, tests only)

# DSH prints a provider failure as "dsh: CODE: message". These codes (and HTTP_5xx) mean the endpoint or the
# network failed, not the agent. TIMEOUT here is DSH's request timeout, not our wall clock.
INFRA_CODES = frozenset({"TRANSPORT", "TIMEOUT", "SERVER", "RATE_LIMIT", "EMPTY_RESPONSE", "STREAM_CLOSED",
                         "MALFORMED_RESPONSE", "AUTH", "QUOTA", "ACCOUNT_QUOTA", "MISSING_CREDENTIAL",
                         "INVALID_CREDENTIAL", "REQUEST_EXTENSION"})
DSH_ERROR = re.compile(r"dsh: ([A-Z0-9_]+):")
HTTP_5XX = re.compile(r"HTTP_5[0-9][0-9]")
NO_ASSISTANT = "NO_ASSISTANT_MESSAGE"  # infra signal when the root session has no assistant/message event
# DSH labels every unhandled promise rejection "fatal load failure" (dsh-app-boot installFailLoud). The DSH
# 0.2.0-rc.2 crash in the subagent registry (stage1 o1-singapore-trip D2-K2 r3) is the one that also says
# "cannot read inbox state": that is crash5063, a result. Any other unhandled rejection is a result once the
# model has answered, and an infrastructure failure (no assistant message) before that.
FATAL_LOAD = "fatal load failure"
CRASH5063 = "cannot read inbox state"

# New top-level /private/tmp entries with these name prefixes are other programs' (or the runner's own) and are
# never moved; they are listed in tmp_new_kept.
TMP_PROTECTED = ("claude", "com.apple", "com.openai", "tmux", "dshx", "launch", "powerlog", "node-compile-cache",
                 "codex", "chatgpt", "codemat", "cc-socks", "chrome", "playwright", "puppeteer", "vscode",
                 "cursor", "friday", "lark", "kimi", "msedge", ".")
# Never protected: DSH's instruction loader walks up from the workspace to the first .git and loads these from
# every directory on the way, so one left above the workspace would reach later prompts.
DSH_INSTRUCTION_NAMES = frozenset({".git", "agents.md", "claude.md", "agents.local.md", "claude.local.md"})
PROXY_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy",
              "no_proxy")
PASS_THROUGH = PROXY_VARS + ("NODE_USE_SYSTEM_CA",)  # copied into the child environment when set
# A patch that inserts a plugin by relative path resolves it beside the patch file; per-attempt copies would
# move it, so such patches are refused.
RELATIVE_INSERT = re.compile(rb"(?m)^\s*(-\s*)?name:\s*['\"]?\.{1,2}/")
ID_CHARS = string.ascii_lowercase + string.digits
ID_RE = re.compile(r"[a-z0-9]{10}")
STAGE_MARKER = ".stage"     # in every attempt's stage dir, so a later runner knows an unfinished one
STAGE_LOCK = ".lock"        # in the stage root: one runner per stage root; its content marks the root as ours
STAGE_LOCK_TAG = "7f3a9c1e5b2d\n"  # opaque on purpose: every run can read the stage root
LOCK_RECORD = "locks.json"  # BATCH_DIR: the lock paths' modes while they are 000
CONDITIONS = "batch.json"   # BATCH_DIR: the conditions the batch started with
MANIFEST_KEYS = ("task", "group", "rep", "id", "order", "attempts", "exit", "seconds", "timeout", "crash5063",
                 "started_utc", "ended_utc", "dry_run")


def log(line: str) -> None:
    """One line per event on stdout (never into a file: the batch dir and the lock paths are locked). A stdout
    that went away (the terminal closed) never stops the batch or its cleanup."""
    try:
        print(line, flush=True)
    except OSError:
        with contextlib.suppress(OSError):
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())


def fail(message: str) -> None:
    """A setup error (arguments, task file, paths, changed conditions): the message on stderr, exit code 2."""
    print(f"run_matrix_v2: {message}", file=sys.stderr, flush=True)
    sys.exit(2)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path) -> str | None:
    """sha256 of a file's content, None when it does not exist."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except FileNotFoundError:
        return None
    return h.hexdigest()


def read_text(path: Path) -> str:
    """A text file, "" when it is missing or unreadable (the agent can write and chmod in the stage dir, which
    holds stderr.log)."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def keychain(service: str) -> str:
    return subprocess.run(["security", "find-generic-password", "-a", "zhangziya", "-s", service, "-w"],
                          check=True, capture_output=True, text=True).stdout.strip()


def dsh_version() -> str:
    try:
        return json.loads((DSH_PACKAGE / "package.json").read_text())["version"]
    except (OSError, ValueError, KeyError):
        return "0.2.0-rc.2"


def write_json(path: Path, obj) -> None:
    """Write via a temporary file and rename, so a reader never sees half a file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def move_path(src: Path, dst: Path) -> None:
    """os.rename (the stage root and the batch dir are on the same volume); shutil.move across volumes."""
    try:
        os.rename(src, dst)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        shutil.move(str(src), str(dst))


# ---------------------------------------------------------------- tasks, groups and order

class TaskError(Exception):
    pass


def safe_relpath(name) -> bool:
    """A workspace-relative path that cannot escape the workspace."""
    return isinstance(name, str) and bool(name) and not Path(name).is_absolute() and ".." not in Path(name).parts


def deliverable_spec(task: dict) -> dict | None:
    """The task's deliverable in one shape: {"kind": "file", "name", "min_bytes"} or {"kind": "changed_files",
    "files"}; None when the task names none."""
    d = task.get("deliverable")
    if d is None:
        return None
    if isinstance(d, str):
        return {"kind": "file", "name": d, "min_bytes": int(task.get("min_bytes", 2000))}
    if isinstance(d, dict) and d.get("kind", "file") == "file" and isinstance(d.get("name"), str):
        return {"kind": "file", "name": d["name"], "min_bytes": int(d.get("min_bytes", task.get("min_bytes", 2000)))}
    if isinstance(d, dict) and d.get("kind") == "changed_files" and isinstance(d.get("files"), list):
        return {"kind": "changed_files", "files": list(d["files"])}
    raise TaskError('deliverable must be a file name, {"kind": "file", "name": ...} or '
                    '{"kind": "changed_files", "files": [...]}')


def task_web(task: dict) -> bool:
    """Whether the task uses the web tools: "web" if given, else false exactly when noweb.patch.yml is applied."""
    return task.get("web", NOWEB_PATCH not in task.get("extra_patches", []))


def check_task(task: dict, where: str) -> None:
    """Everything a selected task must satisfy before the batch starts; raises TaskError."""
    if not isinstance(task.get("prompt"), str) or not task["prompt"].strip():
        raise TaskError(f"{where}: missing prompt")
    files, source = task.get("files"), task.get("workspace_from")
    if files is not None and source is not None:
        raise TaskError(f"{where}: give files or workspace_from, not both")
    if files is not None:
        if not (isinstance(files, dict) and all(safe_relpath(k) and isinstance(v, str) for k, v in files.items())):
            raise TaskError(f"{where}: files must map relative paths to text")
        names = [Path(k).as_posix() for k in files]
        clash = sorted(a for a in names for b in names if b.startswith(a + "/"))
        if clash:
            raise TaskError(f"{where}: files has both a file and a directory named {clash[0]}")
        if ".env" in names:
            raise TaskError(f"{where}: files must not hold a .env (DSH loads the workspace's .env)")
    if source is not None:
        if not Path(source).is_dir():
            raise TaskError(f"{where}: workspace_from {source} is not a directory")
        if os.path.lexists(Path(source, ".env")):
            raise TaskError(f"{where}: workspace_from {source} holds a .env (DSH would load it into its environment)")
    extra = task.get("extra_patches", [])
    if not isinstance(extra, list) or not all(isinstance(x, str) and x and "/" not in x for x in extra):
        raise TaskError(f"{where}: extra_patches must be a list of file names in patches/")
    if "web" in task and not isinstance(task["web"], bool):
        raise TaskError(f"{where}: web must be true or false")
    if task.get("web") is True and NOWEB_PATCH in extra:
        raise TaskError(f"{where}: web is true but extra_patches has {NOWEB_PATCH}")
    try:
        spec = deliverable_spec(task)
    except (TaskError, ValueError, TypeError) as exc:
        raise TaskError(f"{where}: {exc}")
    names = [] if spec is None else [spec["name"]] if spec["kind"] == "file" else spec["files"]
    if not all(safe_relpath(x) for x in names):
        raise TaskError(f"{where}: deliverable names must be relative paths inside the workspace")


def load_tasks(path: Path, only: str | None) -> list:
    """Read the task file (it is read into memory before anything is locked) and check the selected tasks.
    Every line must be JSON with a unique id; the other checks apply to the tasks --only selects, so a task whose
    template does not exist yet does not stop the others. Returns [(task, line)], where line is the task's JSON
    line as written (task_sha256 is computed over it)."""
    rows, seen = [], set()
    # split("\n"), not splitlines(): a JSON string may hold U+2028, which splitlines() would split on.
    for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        line = line.rstrip("\r")
        if not line.strip():
            continue
        try:
            task = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TaskError(f"{path}:{n}: not JSON ({exc})")
        tid = task.get("id") if isinstance(task, dict) else None
        if not isinstance(tid, str) or not tid:
            raise TaskError(f"{path}:{n}: missing id")
        if tid in seen:
            raise TaskError(f"{path}:{n} ({tid}): duplicate id")
        seen.add(tid)
        rows.append((n, task, line))
    if only:
        keep = {s.strip() for s in only.split(",") if s.strip()}
        unknown = sorted(keep - seen)
        if unknown:
            raise TaskError(f"--only names unknown task ids: {', '.join(unknown)}")
        rows = [r for r in rows if r[1]["id"] in keep]
    if not rows:
        raise TaskError("no tasks selected")
    for n, task, _ in rows:
        check_task(task, f"{path}:{n} ({task['id']})")
    return [(task, line) for _, task, line in rows]


def group_patches(task: dict, group: str) -> tuple:
    """(patch file names in order, whether the prompt gets the encourage suffix). E-G uses G's patches."""
    encourage = group.startswith("E-")
    base = group[2:] if encourage else group
    return ["base.patch.yml", *task.get("extra_patches", []), f"{base}.patch.yml"], encourage


def build_jobs(entries: list, groups: list, rep_start: int, repeats: int, shuffle: int | None) -> list:
    """Randomized complete blocks, exactly as run_matrix.py: each repeat r is every (task, group) once, shuffled
    with random.Random(SEED*1000 + r). Returns [(order, block_pos, task, line, group, rep)] in run order, where
    order = (r - 1) * block size + block_pos is the cell's position in the whole batch, so it is the same whichever
    invocation (--rep-start) runs the cell."""
    size = len(entries) * len(groups)
    jobs = []
    for r in range(rep_start, rep_start + repeats):
        block = [(task, line, g, r) for task, line in entries for g in groups]
        if shuffle is not None:
            random.Random(shuffle * 1000 + r).shuffle(block)
        jobs += [((r - 1) * size + pos, pos, *job) for pos, job in enumerate(block)]
    return jobs


def read_jsonl(path: Path, what: str) -> list:
    """The records of a JSONL file (none when it is missing); unreadable lines are skipped with a warning."""
    recs = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            try:
                recs.append(json.loads(line))
            except ValueError:
                log(f"warning: unreadable {what} line skipped: {line[:120]}")
    return recs


def read_manifest(path: Path) -> dict:
    """(task, group, rep) -> manifest record for every cell already recorded in the batch."""
    done = {}
    for rec in read_jsonl(path, "manifest"):
        try:
            done[(rec["task"], rec["group"], rec["rep"])] = rec
        except (KeyError, TypeError):
            log(f"warning: manifest record without task/group/rep skipped: {rec}")
    return done


def read_failures(path: Path) -> dict:
    """(task, group, rep) -> [{"id", "code"}] of the infrastructure failures in failures.jsonl, oldest first, so a
    cell resumed after a pause counts the attempts that earlier invocations made."""
    prior = {}
    for rec in read_jsonl(path, "failures"):
        with contextlib.suppress(KeyError, TypeError):
            prior.setdefault((rec["task"], rec["group"], rec["rep"]), []).append({"id": rec["id"],
                                                                                  "code": rec.get("code")})
    return prior


# ---------------------------------------------------------------- workspace, patches and deliverable

def prepare_workspace(task: dict, workspace: Path) -> None:
    """Fill workspace/ before the clock starts: an APFS clone of workspace_from (instant; it shares blocks with
    the template until a file changes), or the task's files."""
    if task.get("workspace_from"):
        source = str(Path(task["workspace_from"]))  # Path() drops a trailing slash, which would make cp copy the contents
        if sys.platform == "darwin":
            subprocess.run(["/bin/cp", "-cR", source, str(workspace)], check=True, capture_output=True)
        else:
            shutil.copytree(source, workspace, symlinks=True)
    else:
        workspace.mkdir()
        for name, content in (task.get("files") or {}).items():
            target = workspace / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")


def tree_sha256(top: Path) -> str:
    """sha256 over a directory tree, entry by entry in sorted order: the relative path and kind, a file's content
    and executable bit, a symlink's target. Raises OSError when something cannot be read."""
    def raise_error(exc):
        raise exc

    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(top, onerror=raise_error):
        dirnames.sort()
        for name in sorted(dirnames + filenames):
            path = os.path.join(dirpath, name)
            st = os.lstat(path)
            if stat.S_ISLNK(st.st_mode):
                entry = "l\0" + os.readlink(path)
            elif stat.S_ISDIR(st.st_mode):
                entry = "d"
            elif stat.S_ISREG(st.st_mode):
                entry = f"f\0{'x' if st.st_mode & stat.S_IXUSR else '-'}\0{file_sha256(path)}"
            else:
                entry = "o"
            h.update(f"{os.path.relpath(path, top)}\0{entry}\n".encode("utf-8", "surrogateescape"))
    return h.hexdigest()


def strip_comment_lines(data: bytes) -> bytes:
    """A patch without its full-line comments, which describe the experiment ("Applied to every group", "Depth 0:
    ..."). Only lines with '#' in the first column are dropped: YAML ignores them, and a '#' line inside an
    indented block scalar is kept."""
    return b"\n".join(line for line in data.split(b"\n") if not line.startswith(b"#"))


def file_hashes(workspace: Path, names: list) -> dict:
    """name -> sha256 of the file's content, None when it does not exist, "unreadable" when it cannot be read."""
    out = {}
    for name in names:
        f = workspace / name
        try:
            out[name] = file_sha256(f) if f.is_file() else None
        except OSError:
            out[name] = "unreadable"
    return out


def check_deliverable(spec: dict | None, workspace: Path, before: dict | None) -> dict | None:
    """kind file: {kind, name, min_bytes, exists, bytes, ok}. kind changed_files: {kind, changed, files}, where
    files maps each listed file to whether its content differs from the prepared workspace (created and deleted
    count as changed) and changed counts the true ones. A missing deliverable is a result, never retried."""
    if spec is None:
        return None
    if spec["kind"] == "file":
        f = workspace / spec["name"]
        try:
            exists = f.is_file()
            size = f.stat().st_size if exists else 0
        except OSError:  # e.g. the agent made its workspace unreadable
            exists, size = False, 0
        return {"kind": "file", "name": spec["name"], "min_bytes": spec["min_bytes"], "exists": exists,
                "bytes": size, "ok": exists and size >= spec["min_bytes"]}
    after = file_hashes(workspace, spec["files"])
    changed = {name: after[name] != before[name] for name in spec["files"]}
    return {"kind": "changed_files", "changed": sum(changed.values()), "files": changed}


# ---------------------------------------------------------------- processes

def signal_group(pgid: int, sig: int) -> None:
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError):
        pass


def group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def stop_group(proc: subprocess.Popen, grace: float) -> None:
    """SIGTERM to the process group DSH leads; SIGKILL to whatever is left after `grace` seconds."""
    signal_group(proc.pid, signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline and (proc.poll() is None or group_alive(proc.pid)):
        time.sleep(0.1)
    signal_group(proc.pid, signal.SIGKILL)
    proc.wait()


def cwd_table() -> list:
    """(pid, cwd) of every process lsof can see, from `lsof -a -d cwd -Fpn` (lines p<pid>, f<fd>, n<path>)."""
    out = subprocess.run([LSOF, "-w", "-a", "-d", "cwd", "-Fpn"], capture_output=True, text=True,
                         errors="replace").stdout
    rows, pid = [], None
    for line in out.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            pid = int(line[1:])
        elif line.startswith("n") and pid is not None:
            rows.append((pid, line[1:]))
    return rows


def command_names(pids) -> dict:
    """pid -> short command name; processes that are already gone are left out."""
    if not pids:
        return {}
    out = subprocess.run([PS, "-o", "pid=,comm=", "-p", ",".join(map(str, sorted(pids)))],
                         capture_output=True, text=True, errors="replace").stdout
    names = {}
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if parts and parts[0].isdigit():
            names[int(parts[0])] = os.path.basename(parts[1].strip()) if len(parts) > 1 else "?"
    return names


def leftover_processes(stage: Path, pgid: int | None) -> dict:
    """pid -> short name of processes an attempt left behind: cwd inside the stage dir (lsof), still in DSH's
    process group, or carrying the stage's TMPDIR / DSH_HOME in their environment (ps -E). On macOS DSH starts
    every tool command detached (a session and process group of its own), so a background job that changed
    directory is found only through its environment, and ps -E shows no environment for Apple platform binaries
    (/bin/sh, /bin/bash, /bin/sleep, /usr/bin/perl, ...): such a job is missed, while node and the Command Line
    Tools python3 are found."""
    root = str(stage)
    found = {pid for pid, cwd in cwd_table() if cwd == root or cwd.startswith(root + "/")}
    markers = (f"TMPDIR={root}/tmp", f"DSH_HOME={root}/home")
    out = subprocess.run([PS, "-ww", "-E", "-U", str(os.getuid()), "-o", "pid=,pgid=,command="],
                         capture_output=True, text=True, errors="replace").stdout
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 2 or not (parts[0].isdigit() and parts[1].isdigit()):
            continue
        command = parts[2] if len(parts) > 2 else ""
        if (pgid is not None and int(parts[1]) == pgid) or any(m in command for m in markers):
            found.add(int(parts[0]))
    found -= {0, 1, os.getpid()}
    return command_names(found)


def end_leftovers(stage: Path, pgid: int | None, grace: float = LEFTOVER_GRACE_S) -> dict:
    """End the attempt's leftover processes: SIGTERM, SIGKILL after `grace` seconds; a second scan catches anything
    they started meanwhile. Returns {"count", "names"} (one name per process)."""
    seen = {}
    for _ in range(2):
        procs = {pid: name for pid, name in leftover_processes(stage, pgid).items() if pid not in seen}
        if not procs:
            break
        seen.update(procs)
        for pid in procs:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline and any(alive(pid) for pid in procs):
            time.sleep(0.1)
        for pid in procs:
            if alive(pid):
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.kill(pid, signal.SIGKILL)
        deadline = time.monotonic() + 1  # let killed processes close their files before /private/tmp is swept
        while time.monotonic() < deadline and any(alive(pid) for pid in procs):
            time.sleep(0.05)
    return {"count": len(seen), "names": sorted(seen.values())}


# ---------------------------------------------------------------- /private/tmp and the stage root

def tmp_snapshot(root: Path) -> dict:
    """name -> (inode, mtime_ns, owner uid) for every top-level entry of root."""
    snap = {}
    for name in os.listdir(root):
        try:
            st = os.lstat(root / name)
        except FileNotFoundError:
            continue
        snap[name] = (st.st_ino, st.st_mtime_ns, st.st_uid)
    return snap


def in_use(path: Path) -> bool:
    """Whether a live process has the entry (or, for a directory, anything below it) open (lsof)."""
    target = ["+D", str(path)] if path.is_dir() and not path.is_symlink() else ["--", str(path)]
    out = subprocess.run([LSOF, "-w", "-t", *target], capture_output=True, text=True, errors="replace").stdout
    return bool(out.strip())


def tmp_keep_reason(path: Path, owner: int) -> str | None:
    """Why a new top-level /private/tmp entry stays where it is, or None to move it. Called after the attempt's
    processes are gone, so an entry still open belongs to another program."""
    name = path.name.lower()
    if owner != os.getuid():
        return "other owner"
    if name.startswith(TMP_PROTECTED) and name not in DSH_INSTRUCTION_NAMES:
        return "protected name"
    st = os.lstat(path)
    if stat.S_ISSOCK(st.st_mode):
        return "socket"
    if stat.S_ISFIFO(st.st_mode):
        return "fifo"
    if not stat.S_ISLNK(st.st_mode) and in_use(path):
        return "in use"
    return None


def run_log_text(stage: Path) -> str:
    """Everything the attempt logged (DSH's stdout events, its stderr and its session logs), used to tell which new
    /private/tmp entries the attempt made."""
    parts = [read_text(stage / "events.jsonl"), read_text(stage / "stderr.log")]
    sessions = stage / "home" / "sessions"
    if sessions.is_dir():
        for f in sorted(sessions.rglob("session*.jsonl*")):
            parts.extend(read_log_lines(f))
    return "\n".join(parts)


# A shell, printf or Python variable inside a file name the attempt built in a loop: h_$k.html, ${H[$k]}.json,
# out_{name}.txt, page%s.html.
_VAR = r"(?:\$\{?[A-Za-z_]\w*(?:\[[^\]\s]*\])?\}?|\{[A-Za-z_][\w.]*\}|%[sd])"
_TEMPLATE = re.compile(r"[\w.\-/]*" + _VAR + r"(?:[\w.\-]|" + _VAR + r")*")
_CONCAT = re.compile(r"""['"]([\w.\-/]+)['"]\s*\+\s*[A-Za-z_]\w*\s*\+\s*['"]([\w.\-]+)['"]""")


def name_templates(text: str, rooted: bool) -> list:
    """Regexes for file names the logs build from variables. A template counts when it sits under /tmp, or anywhere
    once a command changed into /tmp (rooted). Each must keep at least two literal characters."""
    out = []
    for m in _TEMPLATE.finditer(text):
        token = m.group(0)
        under = "/tmp/" in token
        if not (under or rooted):
            continue
        last = token.rsplit("/", 1)[-1]
        parts = re.split(_VAR, last)
        if sum(len(x) for x in parts) < 2:
            continue
        out.append(re.compile(".+".join(re.escape(x) for x in parts)))
    if rooted:
        for m in _CONCAT.finditer(text):
            head, tail = m.group(1).rsplit("/", 1)[-1], m.group(2)
            if len(head) + len(tail) >= 2:
                out.append(re.compile(re.escape(head) + ".+" + re.escape(tail)))
    return out


def tmp_referenced(text: str, root: Path):
    """A predicate: whether the attempt's logs name a top-level entry of root, by absolute path, by bare name once one
    of its commands changed into root, or through a file-name template it filled in a loop. Other programs create
    entries there too while a run is going; an entry nothing in the attempt names is theirs and stays put."""
    roots = {str(root), "/tmp", "/private/tmp"}
    cd_into = any(f"cd {r}" in text for r in roots)
    templates = name_templates(text, cd_into)

    def referenced(name: str) -> bool:
        if any(f"{r}/{name}" in text for r in roots):
            return True
        if cd_into and len(name) >= 2 and re.search(rf"(?<![\w.-]){re.escape(name)}(?![\w-])", text):
            return True
        return any(t.fullmatch(name) for t in templates)
    return referenced


def sweep_tmp(root: Path, before: dict, dest: Path, keep=frozenset(), referenced=None) -> tuple:
    """Move top-level entries of root that appeared since `before` (a new name, or an old name with a new inode)
    into dest, unless the attempt's logs never name them (`referenced`, when given) or tmp_keep_reason() keeps them;
    list pre-existing entries whose mtime changed. Names in `keep` (the runner's own stage root and batch dir) are
    skipped. Returns (moved names, modified names, {kept name: reason})."""
    moved, modified, kept = [], [], {}
    for name, (ino, mtime, owner) in sorted(tmp_snapshot(root).items()):
        if name in keep:
            continue
        old = before.get(name)
        if old is not None and old[0] == ino:
            if old[1] != mtime:
                modified.append(name)
            continue
        if referenced is not None and not referenced(name):
            kept[name] = "not named in this attempt's logs"
            continue
        try:
            reason = tmp_keep_reason(root / name, owner)
        except FileNotFoundError:
            continue  # gone meanwhile
        if reason:
            kept[name] = reason
            continue
        try:
            dest.mkdir(exist_ok=True)
            move_path(root / name, dest / name)
            moved.append(name)
        except OSError as exc:
            kept[name] = f"could not move: {exc.strerror or exc}"
            log(f"warning: could not move {root / name}: {exc}")
    return moved, modified, kept


def top_level_name(path: Path, root: Path) -> str | None:
    """The first component of path below root, or None when path is not inside root."""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return None
    return parts[0] if parts else None


def root_markers(start: Path) -> list:
    """.git entries in start and its ancestors. DSH's instruction loader walks up from the workspace to the first
    .git and loads AGENTS.md / CLAUDE.md from every directory between it and the workspace, so a .git above the
    workspace would put files from outside the attempt into the prompt."""
    return [str(p / ".git") for p in (start, *start.parents) if os.path.lexists(p / ".git")]


def runner_owned(name: str, dry_run: bool) -> bool:
    """The runner's own files in the stage root (everything else there is collected)."""
    return name == STAGE_LOCK or (dry_run and name.startswith("fake_dsh_state."))


def stage_root_entries(stage_root: Path, dry_run: bool) -> list:
    return sorted(n for n in os.listdir(stage_root) if not runner_owned(n, dry_run))


def orphan_stages(stage_root: Path, dry_run: bool) -> list:
    """Stage dirs of attempts that never finished (their runner was killed): an id with the stage marker."""
    return [stage_root / n for n in stage_root_entries(stage_root, dry_run)
            if ID_RE.fullmatch(n) and os.path.isfile(stage_root / n / STAGE_MARKER)]


# ---------------------------------------------------------------- session logs and classification

def read_log_lines(path: Path) -> list:
    """Lines of a session log (.jsonl or .jsonl.zstd), like delegation_stats.read_lines but tolerant: a log cut
    short (DSH killed mid-write) gives the lines that decode, and an unreadable one gives []. Split on "\\n" only:
    JSON.stringify leaves U+2028 / U+2029 inside strings, which str.splitlines() would split on."""
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
                    pass  # keep what decoded before the damage
            data = b"".join(chunks)
        else:
            data = path.read_bytes()
        return [line.decode("utf-8", errors="replace") for line in data.split(b"\n") if line.strip()]
    except (OSError, ImportError):
        return []


def root_assistant_messages(sessions: Path) -> int:
    """assistant/message events in the root session: the session.v4.jsonl(.zstd) logs under DSH_HOME/sessions
    whose header has no parentSession and delegationDepth 0. No session files at all (or none readable) counts as
    zero."""
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


def infra_code_of(stderr: str, root_assistant: int) -> str | None:
    """The infrastructure-failure signal of an attempt, or None: the first DSH provider error code in stderr that
    is in INFRA_CODES or HTTP_5xx, else NO_ASSISTANT_MESSAGE when the root session never got an answer."""
    for code in DSH_ERROR.findall(stderr):
        if code in INFRA_CODES or HTTP_5XX.fullmatch(code):
            return code
    if root_assistant == 0:
        return NO_ASSISTANT
    return None


def classify(stderr: str, root_assistant: int, timed_out: bool) -> dict:
    """crash5063, fatal_load_failure, infra_signal (what infra_code_of found) and retry. An infrastructure signal
    means a retry unless something that is a result explains the attempt: our wall-clock timeout, crash5063, or an
    unhandled DSH error after the model answered."""
    crash = CRASH5063 in stderr
    fatal = FATAL_LOAD in stderr
    infra = infra_code_of(stderr, root_assistant)
    retry = infra is not None and not timed_out and not crash and not (fatal and root_assistant > 0)
    return {"crash5063": crash, "fatal_load_failure": fatal, "infra_signal": infra, "retry": retry}


# ---------------------------------------------------------------- readiness probe

def _env_value(env: dict, lower: str) -> str | None:
    """DSH's readEnv: the lowercase name first, then the uppercase one; a blank value counts as unset."""
    for name in (lower, lower.upper()):
        value = (env.get(name) or "").strip()
        if value:
            return value
    return None


def _proxy_slot(value: str | None) -> tuple:
    """("absent" | "rejected" | "accepted", url), as DSH's acceptProxyUrl: only a parseable http:// or https://
    URL is accepted, and a rejected one keeps its scheme direct."""
    if value is None:
        return "absent", None
    try:
        parts = urllib.parse.urlsplit(value)
    except ValueError:
        return "rejected", None
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return "rejected", None
    return "accepted", value


def _first_proxy(own: tuple, *fallbacks) -> str | None:
    kind, value = own
    if kind == "accepted":
        return value
    if kind == "rejected":
        return None
    return next((v for v in fallbacks if v is not None), None)


def _is_loopback(host: str) -> bool:
    host = host.strip("[]").rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_loopback or ip.is_unspecified


def _split_host_port(entry: str) -> tuple:
    if entry.startswith("["):
        close = entry.find("]")
        if close != -1:
            rest = entry[close + 1:]
            return (entry[1:close], rest[1:]) if rest.startswith(":") else (entry[1:close], None)
    colon = entry.find(":")
    if colon != -1 and entry.find(":", colon + 1) == -1:
        return entry[:colon], entry[colon + 1:]
    return entry, None


def _bypasses(no_proxy: str | None, host: str, port: str) -> bool:
    """DSH's bypassesProxy: an entry matches its host and every subdomain (a leading "." or "*." is the same), may
    carry a :port, and "*" matches everything."""
    for raw in re.split(r"[,\s]+", no_proxy or ""):
        entry = raw.strip().lower()
        if not entry:
            continue
        if entry == "*":
            return True
        entry_host, entry_port = _split_host_port(entry)
        if entry_port is not None and entry_port != port:
            continue
        candidate = re.sub(r"^\*?\.", "", entry_host)
        candidate = candidate[:-1] if candidate.endswith(".") else candidate
        if candidate and (host == candidate or host.endswith("." + candidate)):
            return True
    return False


def dsh_proxy_for(url: str, env: dict) -> str | None:
    """The proxy DSH would send `url` through under `env`, or None for a direct connection (dsh-http-proxy:
    resolveProxyPolicy and proxyForUrl). A scheme's own variable wins (lowercase first), then ALL_PROXY, then, for
    https only, the http proxy; loopback hosts and NO_PROXY entries go direct."""
    all_proxy = _first_proxy(_proxy_slot(_env_value(env, "all_proxy")))
    http = _first_proxy(_proxy_slot(_env_value(env, "http_proxy")), all_proxy)
    https = _first_proxy(_proxy_slot(_env_value(env, "https_proxy")), all_proxy, http)
    parts = urllib.parse.urlsplit(url)
    proxy = https if parts.scheme == "https" else http if parts.scheme == "http" else None
    host = (parts.hostname or "").rstrip(".").lower()
    if proxy is None or _is_loopback(host):
        return None
    port = str(parts.port) if parts.port else ("443" if parts.scheme == "https" else "80")
    return None if _bypasses(_env_value(env, "no_proxy"), host, port) else proxy


def _curl_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def curl_command(target: dict, proxy: str | None) -> tuple:
    """(argv, config) for one readiness request. curl reads the URL, headers, body and proxy from its config on
    stdin, so no key appears on a command line. -q first: no ~/.curlrc. No --location: a redirect is not a pass
    (DSH does not follow redirects either)."""
    config = [f"url = {_curl_quote(target['url'])}"]
    config += [f"header = {_curl_quote(f'{k}: {v}')}" for k, v in target["headers"].items()]
    if target["body"] is not None:
        config.append(f"data-raw = {_curl_quote(target['body'].decode('utf-8'))}")
    config.append(f"proxy = {_curl_quote(proxy)}" if proxy else 'noproxy = "*"')
    argv = [CURL, "-q", "--silent", "--show-error", "--output", "/dev/null", "--write-out", "%{http_code}",
            "--max-time", str(PROBE_TIMEOUT_S), "--config", "-"]
    return argv, "\n".join(config) + "\n"


def probe(target: dict, env: dict) -> str | None:
    """One readiness request, routed the way DSH would route it (dsh_proxy_for over the child environment); None
    when it passes, else a short error (status or curl's message, never a body). curl rather than urllib: the
    system Python's LibreSSL 2.8.3 has no TLS 1.3, which DSH (Node 22) and curl (LibreSSL 3.3) both speak."""
    argv, config = curl_command(target, dsh_proxy_for(target["url"], env))
    try:
        p = subprocess.run(argv, input=config, capture_output=True, text=True, errors="replace",
                           env={"PATH": "/usr/bin:/bin"}, timeout=PROBE_TIMEOUT_S + 10)
    except subprocess.TimeoutExpired:
        return f"{target['url']} no answer within {PROBE_TIMEOUT_S}s"
    status = p.stdout.strip()
    if p.returncode != 0:
        detail = (p.stderr.strip().splitlines() or [f"curl exit {p.returncode}"])[-1]
        return f"{target['url']} {detail}"
    if status == "200" or (target["need"] == "2xx" and re.fullmatch(r"2[0-9][0-9]", status)):
        return None
    return f"{target['url']} HTTP {status}"


# ---------------------------------------------------------------- environment and conditions

def base_env(permission: str, base_url: str = MODEL_BASE_URL) -> dict:
    """The part of the child environment that every attempt of the batch shares. Proxy variables and
    NODE_USE_SYSTEM_CA (which earlier runs inherited) are copied when set: the same network path and trust store."""
    user = pwd.getpwuid(os.getuid())
    env = {
        "USER": os.environ.get("USER") or user.pw_name,
        "LOGNAME": os.environ.get("LOGNAME") or user.pw_name,
        "SHELL": "/bin/bash",
        "LANG": os.environ.get("LANG") or "en_US.UTF-8",
        "TERM": "dumb",
        "PYTHONUSERBASE": f"{user.pw_dir}/Library/Python/3.9",  # so `python3 -m pytest` works with HOME moved
        "DSH_PERMISSION_MODE": permission,
        "DEEPSEEK_BASE_URL": base_url,
    }
    for name in PASS_THROUGH:
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def strip_credentials(value: str) -> str:
    """A proxy URL without user:password@ (for batch.json and result.json)."""
    try:
        parts = urllib.parse.urlsplit(value)
    except ValueError:
        return value
    if "@" not in parts.netloc:
        return value
    return urllib.parse.urlunsplit(parts._replace(netloc=parts.netloc.rsplit("@", 1)[1]))


def public_env(env: dict) -> dict:
    return {k: strip_credentials(v) if k in PROXY_VARS else v for k, v in env.items()}


def attempt_env(base: dict, stage: Path, task: dict, user_sk: str, fake: dict | None = None,
                model_key: str | None = None) -> dict:
    """One attempt's child environment, from scratch: base_env() plus the stage paths and the keys; nothing else
    is inherited. Only the stage paths and (by task, not by group) HIGH_FIVE_API_KEY vary between runs. `fake`
    (dry runs only) adds the FAKE_DSH_* variables the test double reads. `model_key` (--model-key-keychain)
    replaces the internal personal key, e.g. a personal key for the official API."""
    env = dict(base)
    env.update({
        "HOME": str(stage / "fakehome"),
        "TMPDIR": str(stage / "tmp"),
        "PATH": f"{stage / 'bin'}:{CHILD_PATH_TAIL}",
        "DSH_HOME": str(stage / "home"),
        # Model calls: internal DeepSeek endpoint, Messages protocol, personal key (or --model-key-keychain).
        "DEEPSEEK_API_KEY": model_key or f"sk-internal-personal-zhangziya-{user_sk}",
    })
    if task_web(task):
        env["HIGH_FIVE_API_KEY"] = user_sk  # web search through the company proxy (base.patch.yml)
    if fake is not None:
        env.update(fake)
    return env


def dsh_argv(dry_run: bool, patch_files: list, prompt: str) -> list:
    """DSH's command line (the fake's under --dry-run). It names only the attempt's own cfg/ copies."""
    argv = [PYTHON, str(FAKE_DSH)] if dry_run else [NODE, str(DSH_BIN)]
    argv += ["--profile", "headless"]
    for path in patch_files:
        argv += ["--patch", str(path)]
    return argv + ["--json", prompt]


def runtime_fingerprint() -> dict:
    """What identifies the DSH that runs, taken when the batch starts and again before every attempt (the batch
    pauses when it changed, e.g. after another session ran npm in runtime/): DSH's version, sha256 of bin.js and of
    runtime/package-lock.json, and a fingerprint (path, size, mtime) of every file under runtime/node_modules and
    of the node binary. DSH writes nothing under node_modules while it runs (checked after the pilot and stage1)."""
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(NODE_MODULES):
        dirnames.sort()
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            with contextlib.suppress(FileNotFoundError):
                st = os.lstat(path)
                h.update(f"{os.path.relpath(path, NODE_MODULES)}\0{st.st_size}\0{st.st_mtime_ns}\n"
                         .encode("utf-8", "surrogateescape"))
    try:
        st = os.stat(NODE)
        h.update(f"node\0{st.st_size}\0{st.st_mtime_ns}\n".encode())
    except OSError:
        h.update(b"node\0missing\n")
    return {"dsh_version": dsh_version(), "dsh_bin_sha256": file_sha256(DSH_BIN),
            "dsh_lock_sha256": file_sha256(DSH_LOCKFILE), "runtime_tree_sha256": h.hexdigest()}


def batch_conditions(args, entries: list, groups: list, patch_sha: dict, runtime: dict, workspace_sha: dict,
                     env_public: dict) -> dict:
    """What batch.json records: everything that must not change while the batch runs, across invocations."""
    encourage = args.encourage if any(g.startswith("E-") for g in groups) else None
    return {
        "runner": "run_matrix_v2", "runner_sha256": file_sha256(RUNNER), "dry_run": args.dry_run,
        # In file order: the order of tasks and groups decides each block before it is shuffled.
        "tasks": [[task["id"], sha256_bytes(line.encode("utf-8"))] for task, line in entries],
        "groups": list(groups), "shuffle": args.shuffle, "timeout_s": args.timeout,
        "encourage": encourage, "permission": args.permission,
        "stage_root": str(args.stage_root), "tmp_root": str(args.tmp_root),
        "probe": {"model_url": args.probe_url_model, "search_url": args.probe_url_search,
                  "wait_s": args.probe_wait, "limit_s": args.probe_limit},
        "patch_sha256": dict(patch_sha), **runtime, "workspace_sha256": dict(workspace_sha),
        "env_public": env_public,
    }


def conditions_diff(old: dict, new: dict) -> list:
    """The keys in which two batch.json dicts differ, readable (for a dict value, the sub-keys that differ)."""
    new = json.loads(json.dumps(new))

    def short(value) -> str:
        text = json.dumps(value, ensure_ascii=False)
        return text if len(text) <= 80 else text[:77] + "..."

    diffs = []
    for key in sorted(set(old) | set(new)):
        a, b = old.get(key), new.get(key)
        if a == b:
            continue
        if isinstance(a, dict) and isinstance(b, dict):
            subs = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            diffs.append(f"{key} ({', '.join(subs)})")
        else:
            diffs.append(f"{key}: {short(a)} -> {short(b)}")
    return diffs


# ---------------------------------------------------------------- locks and signals

class Locks:
    """chmod 000 on the --lock paths for the whole batch. The original modes go to BATCH_DIR/locks.json before the
    first chmod, so a runner killed with SIGKILL is undone by the next start (restore_recorded_locks). restore()
    puts the modes back and is safe to call more than once. Deeper paths are locked first and restored last, so
    nested lock paths work."""

    def __init__(self, paths: list, record: Path):
        self.paths = sorted(set(paths), key=lambda p: len(p.parts), reverse=True)
        self.record = record
        self.saved = []

    def lock(self) -> None:
        if not self.paths:
            return
        modes = [(path, stat.S_IMODE(os.stat(path).st_mode)) for path in self.paths]
        write_json(self.record, {str(p): m for p, m in modes})
        for path, mode in modes:
            self.saved.append((path, mode))
            os.chmod(path, 0)
        log("locked (mode 000) for the batch: " + ", ".join(f"{p} (was {m:o})" for p, m in modes))

    def restore(self) -> None:
        while self.saved:
            path, mode = self.saved.pop()
            try:
                os.chmod(path, mode)
            except OSError as exc:
                log(f"warning: could not restore mode {mode:o} on {path}: {exc}")
        try:
            self.record.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            log(f"warning: could not remove {self.record}: {exc}")


def restore_recorded_locks(record: Path) -> None:
    """Undo the locks of a runner that was killed before it restored them: the modes in BATCH_DIR/locks.json,
    shallower paths first, then the record goes."""
    if not record.exists():
        return
    try:
        saved = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail(f"{record} is unreadable ({exc}); restore the modes of the lock paths by hand, then delete it")
    for path, mode in sorted(saved.items(), key=lambda item: len(Path(item[0]).parts)):
        try:
            os.chmod(path, int(mode))
        except FileNotFoundError:
            log(f"warning: {path} (in {record.name}) no longer exists")
            continue
        except OSError as exc:
            fail(f"could not restore mode {int(mode):o} on {path} ({exc}); {record} is kept: fix it, then run again")
        log(f"restored mode {int(mode):o} on {path} (left locked by a runner that was killed)")
    record.unlink()


class Paused(Exception):
    """Stop the batch with exit code 3; info goes into BATCH_DIR/PAUSED.json."""

    def __init__(self, info: dict):
        super().__init__(info.get("reason"))
        self.info = info


STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)  # SIGHUP: the terminal running the batch closed
# The first stop signal and whether it may still raise Interrupted (set to False once cleanup has begun).
STOP = {"signum": None, "armed": True}


class Interrupted(BaseException):
    """Raised by the STOP_SIGNALS handler. A BaseException, so no `except Exception` swallows it."""

    def __init__(self, signum: int):
        super().__init__(signum)
        self.signum = signum


def on_signal(signum, frame):
    """The first stop signal ends the batch: while the batch runs it raises Interrupted wherever the main thread
    is. Every later stop signal is dropped, and none raises once cleanup has begun, so a second signal can never
    cut the cleanup short (signal.signal() and pthread_sigmask() run pending handlers, so it would otherwise
    raise inside the cleanup itself)."""
    if STOP["signum"] is not None:
        return
    STOP["signum"] = signum
    if STOP["armed"]:
        raise Interrupted(signum)


@contextlib.contextmanager
def signals_deferred():
    """Hold STOP_SIGNALS while a finished attempt is moved in and its records are written, so the step is never
    cut in half; a signal that arrives meanwhile is handled right after. (Never wrap process starts in this: a
    child inherits the blocked mask.)"""
    old = signal.pthread_sigmask(signal.SIG_BLOCK, set(STOP_SIGNALS))
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old)


# ---------------------------------------------------------------- the batch

class Attempt:
    """The attempt in progress, so that an interrupt or an error can clean it up."""

    def __init__(self, run_id: str, stage: Path):
        self.id, self.stage = run_id, stage
        self.proc = None        # the DSH process once launched
        self.tmp_before = None  # /private/tmp snapshot taken just before launch
        self.swept = False


class Batch:
    def __init__(self, args, user_sk: str, known_ids: set, tmp_keep: set, patch_bytes: dict, env: dict,
                 conditions: dict, prior: dict, model_key: str | None = None):
        self.args = args
        self.out: Path = args.out
        self.user_sk = user_sk
        self.model_key = model_key
        self.known_ids = known_ids
        self.tmp_keep = tmp_keep
        self.patch_bytes = patch_bytes  # name -> content, read when the batch started
        self.patch_sha = {name: sha256_bytes(data) for name, data in patch_bytes.items()}
        self.env = env                  # base_env(): shared by every attempt
        self.conditions = conditions    # what batch.json holds
        self.prior = prior              # (task, group, rep) -> failures recorded by earlier invocations
        self.locks = Locks(args.lock, args.out / LOCK_RECORD)
        self.active: Attempt | None = None
        self.running = False  # while True, BATCH_DIR returns to 000 after each batch_open()
        # The fake's per-cell plan position, per batch dir (a later dry run in the same stage root starts afresh).
        self.fake_state = args.stage_root / f"fake_dsh_state.{sha256_bytes(str(args.out).encode())[:12]}.json"

    # -- batch dir and records

    @contextlib.contextmanager
    def batch_open(self):
        """BATCH_DIR is 000 while runs go; it opens (700) only to move an attempt in and write records."""
        os.chmod(self.out, 0o700)
        try:
            yield
        finally:
            os.chmod(self.out, 0o000 if self.running else 0o700)

    def redact(self, text: str) -> str:
        if self.model_key:
            text = text.replace(self.model_key, "<model_key>")
        return text.replace(self.user_sk, "<user_sk>") if self.user_sk else text

    def record(self, result: dict) -> None:
        """Move the finished attempt into BATCH_DIR/<id>, write its result.json and append the manifest."""
        act = self.active
        with signals_deferred(), self.batch_open():
            dest = self.out / act.id
            move_path(act.stage, dest)
            write_json(dest / "result.json", result)
            with open(self.out / "manifest.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({k: result[k] for k in MANIFEST_KEYS}, ensure_ascii=False) + "\n")
            self.active = None
            self.done = getattr(self, "done", 0) + 1
            self.write_progress("running")
            line = (f"{result['task']} {result['group']} r{result['rep']} order={result['order']} id={result['id']} "
                    f"exit={result['exit']} seconds={result['seconds']} attempts={result['attempts']}")
            log(line + (" timeout" if result["timeout"] else "") + (" crash5063" if result["crash5063"] else "")
                + (" fatal" if result["fatal_load_failure"] and not result["crash5063"] else ""))

    def write_progress(self, state: str) -> None:
        """A neutral progress file outside every locked path, so the batch can be watched while BATCH_DIR and the
        log are locked: counts, a time and the state, never a task, group, order or id. Real runs write it to
        <EXP>/logs/<batch>.progress.json; dry runs (tests) write BATCH_DIR/progress.json, which is open whenever
        this is called."""
        folder, name = (self.out, "progress.json") if self.args.dry_run else (ROOT / "logs", f"{self.out.name}.progress.json")
        try:
            folder.mkdir(exist_ok=True)
            tmp = folder / f".{name}.tmp"
            tmp.write_text(json.dumps({"batch": self.out.name, "done": getattr(self, "done", 0), "total": getattr(self, "total", 0),
                                       "updated_utc": utc_now(), "state": state}) + "\n", encoding="utf-8")
            os.replace(tmp, folder / name)
        except OSError as exc:
            log(f"warning: could not write the progress file: {exc}")

    def file_failure(self, result: dict) -> dict:
        """Keep an infrastructure-failed attempt in BATCH_DIR/_failed/<id> and log it to failures.jsonl."""
        act = self.active
        stderr = self.redact(read_text(act.stage / "stderr.log"))
        rec = {"task": result["task"], "group": result["group"], "rep": result["rep"], "attempt": result["attempts"],
               "id": act.id, "code": result["infra_code"], "exit": result["exit"], "seconds": result["seconds"],
               "started_utc": result["started_utc"], "stderr_tail": stderr[-400:]}
        with signals_deferred(), self.batch_open():
            failed = self.out / "_failed"
            failed.mkdir(exist_ok=True)
            move_path(act.stage, failed / act.id)
            write_json(failed / act.id / "attempt.json", result)  # not result.json: no summary script picks it up
            with open(self.out / "failures.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.active = None
            # Only order and id here (task, group and rep are in failures.jsonl): this line names the cell that
            # runs next, and the log should never say which cell is running.
            log(f"order={result['order']} id={rec['id']} attempt {rec['attempt']} infrastructure failure "
                f"code={rec['code']} exit={rec['exit']} seconds={rec['seconds']}")
        return rec

    def write_paused(self, info: dict) -> None:
        with self.batch_open():
            write_json(self.out / "PAUSED.json", info)

    # -- one attempt

    def new_id(self) -> str:
        while True:
            run_id = "".join(secrets.choice(ID_CHARS) for _ in range(10))
            if run_id not in self.known_ids and not os.path.lexists(self.args.stage_root / run_id):
                self.known_ids.add(run_id)
                return run_id

    def pause_info(self, reason: str, task: dict, group: str, rep: int, **extra) -> dict:
        return {"reason": reason, "task": task["id"], "group": group, "rep": rep, **extra, "time": utc_now()}

    def prepare_stage(self, stage: Path, task: dict, patches: list) -> tuple:
        """The attempt's directory, before the clock starts: the stage marker, home/, tmp/, fakehome/, bin/ (the
        placeholders, copied so that PATH names nothing and an edit of them ends with the run), cfg/ (the patches)
        and workspace/. Returns (patch files, workspace)."""
        stage.mkdir()
        (stage / STAGE_MARKER).write_bytes(b"")
        for sub in ("home", "tmp", "fakehome"):
            (stage / sub).mkdir()
        shutil.copytree(BLOCKED_BIN, stage / "bin")
        cfg = stage / "cfg"
        cfg.mkdir()
        patch_files = []
        for i, name in enumerate(patches, 1):
            # From the bytes read when the batch started and without comments: DSH's command line, which every
            # process can list, then names neither the group nor the project, and an edit of patches/ during the
            # batch changes nothing. DSH reads its --patch files once, at startup.
            path = cfg / f"{i}.yml"
            path.write_bytes(strip_comment_lines(self.patch_bytes[name]))
            patch_files.append(path)
        workspace = stage / "workspace"
        prepare_workspace(task, workspace)
        return patch_files, workspace

    def check_unchanged(self, stage: Path, task: dict, group: str, rep: int) -> None:
        """Pause before launch when DSH changed since the batch started, or a .git above the workspace would make
        DSH load instructions from outside the attempt."""
        now = runtime_fingerprint()
        changed = sorted(k for k, v in now.items() if v != self.conditions.get(k))
        if changed:
            raise Paused(self.pause_info(f"DSH changed since the batch started ({', '.join(changed)})", task, group,
                                         rep, was={k: self.conditions.get(k) for k in changed},
                                         now={k: now[k] for k in changed}))
        markers = root_markers(stage)
        if markers:
            raise Paused(self.pause_info(f"a .git above the workspace would add instructions to the prompt: "
                                         f"{', '.join(markers)}", task, group, rep))

    def build_env(self, stage: Path, task: dict, line: str, group: str) -> dict:
        fake = None
        if self.args.dry_run:  # the fake needs its plan, the task and the group; never set in real runs
            fake = {k: v for k, v in os.environ.items() if k.startswith("FAKE_DSH_")}
            fake.update(FAKE_DSH_TASK=line, FAKE_DSH_GROUP=group, FAKE_DSH_STATE=str(self.fake_state))
        return attempt_env(self.env, stage, task, self.user_sk, fake, self.model_key)

    def probe_targets(self, task: dict, env: dict) -> list:
        """Real runs probe the model endpoint, plus the search proxy for web tasks. --dry-run probes nothing unless
        a --probe-url-* override is given (tests point those at a localhost server)."""
        dry = self.args.dry_run
        model = self.args.probe_url_model or (None if dry else env["DEEPSEEK_BASE_URL"] + "/v1/messages")
        search = self.args.probe_url_search or (None if dry else SEARCH_MODELS_URL)
        targets = []
        if model:
            body = {"model": "deepseek-flash", "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]}
            targets.append({"url": model, "method": "POST", "need": "2xx", "body": json.dumps(body).encode(),
                            "headers": {"x-api-key": env["DEEPSEEK_API_KEY"], "anthropic-version": "2023-06-01",
                                        "content-type": "application/json"}})
        if search and task_web(task):
            targets.append({"url": search, "method": "GET", "need": "200", "body": None,
                            "headers": {"Authorization": f"Bearer {self.user_sk}"}})
        return targets

    def wait_ready(self, task: dict, env: dict, label: str, group: str, rep: int) -> None:
        """Hold the attempt until the endpoints answer, so a VPN drop delays runs instead of failing them. Checks
        every --probe-wait seconds (60); after --probe-limit (2 hours) the batch pauses. The log lines carry only
        the attempt's order and id, never the cell."""
        targets = self.probe_targets(task, env)
        if not targets:
            return
        t0, waited = time.monotonic(), False
        while True:
            errors = [err for err in (probe(t, env) for t in targets) if err]
            if not errors:
                if waited:
                    log(f"{label}: endpoints ready after {time.monotonic() - t0:.0f}s")
                return
            last = self.redact("; ".join(errors))
            if time.monotonic() - t0 >= self.args.probe_limit:
                raise Paused(self.pause_info(f"endpoints not ready for {self.args.probe_limit:g}s", task, group, rep,
                                             last_error=last, label=label))
            log(f"{label}: waiting for endpoints ({last}); next check in {self.args.probe_wait:g}s")
            waited = True
            time.sleep(self.args.probe_wait)

    def launch(self, argv: list, stage: Path, env: dict) -> tuple:
        """Run DSH in its own session with the wall-clock limit. seconds runs from launch to exit (workspace
        preparation and probes are not included)."""
        act = self.active
        started = utc_now()
        with open(stage / "events.jsonl", "wb") as out, open(stage / "stderr.log", "wb") as err:
            t0 = time.monotonic()
            act.proc = subprocess.Popen(argv, cwd=stage / "workspace", env=env, stdin=subprocess.DEVNULL,
                                        stdout=out, stderr=err, start_new_session=True)
            timed_out = False
            # cfg/ holds this attempt's patches, which name its limits. DSH reads them while it boots, before it
            # prints its first event; from then on cfg/ is mode 000, so `ls ..` shows the folder but nothing in
            # it can be read. Restored when DSH exits (and after the attempt, in case of an interrupt).
            cfg, cfg_locked = stage / "cfg", False
            deadline = t0 + self.args.timeout
            while True:
                if not cfg_locked and ((stage / "events.jsonl").stat().st_size > 0
                                       or time.monotonic() - t0 > CFG_LOCK_AFTER_S):
                    with contextlib.suppress(OSError):
                        os.chmod(cfg, 0o000)
                    cfg_locked = True
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    stop_group(act.proc, TERM_GRACE_S)
                    break
                try:
                    act.proc.wait(timeout=min(remaining, 5.0 if cfg_locked else 0.2))
                    break
                except subprocess.TimeoutExpired:
                    continue
            seconds = round(time.monotonic() - t0, 1)
            with contextlib.suppress(OSError):
                os.chmod(cfg, 0o700)
        return act.proc.returncode, seconds, timed_out, started, utc_now()

    def sweep_stage_root(self, stage: Path) -> dict:
        """Move whatever the attempt left in the stage root itself (writable for the agent, as all of /private/tmp
        is) into its stage-root-leftovers/, so no later attempt can read it. Returns {"count", "names"}."""
        moved = []
        for name in stage_root_entries(self.args.stage_root, self.args.dry_run):
            if name == stage.name:
                continue
            dest = stage / "stage-root-leftovers"
            try:
                dest.mkdir(exist_ok=True)
                move_path(self.args.stage_root / name, dest / name)
                moved.append(name)
            except OSError as exc:
                log(f"warning: could not move {self.args.stage_root / name}: {exc}")
        return {"count": len(moved), "names": moved}

    def attempt(self, order: int, block_pos: int, task: dict, line: str, group: str, rep: int,
                attempt_no: int) -> tuple:
        """One isolated attempt at a cell. Returns (result, retry): retry is true for an infrastructure failure
        (never for our timeout, crash5063 or an unhandled DSH error after the model answered)."""
        run_id = self.new_id()
        stage = self.args.stage_root / run_id
        self.active = act = Attempt(run_id, stage)
        label = f"order={order} id={run_id}"
        patches, suffix = group_patches(task, group)
        try:
            patch_files, workspace = self.prepare_stage(stage, task, patches)
            workspace_sha = tree_sha256(workspace)
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = ""
            if isinstance(exc, subprocess.CalledProcessError):  # cp's own message
                detail = exc.stderr.decode(errors="replace").strip()
            raise Paused(self.pause_info(f"workspace preparation failed: {exc} {detail}".strip(), task, group, rep))
        expected = self.conditions["workspace_sha256"].get(task["id"])
        if expected is not None and workspace_sha != expected:
            raise Paused(self.pause_info("the workspace_from template changed since the batch started", task, group,
                                         rep, was=expected, now=workspace_sha))
        self.check_unchanged(stage, task, group, rep)
        spec = deliverable_spec(task)
        before = file_hashes(workspace, spec["files"]) if spec and spec["kind"] == "changed_files" else None
        prompt = task["prompt"] + ("\n\n" + self.args.encourage if suffix else "")
        env = self.build_env(stage, task, line, group)
        self.wait_ready(task, env, label, group, rep)
        argv = dsh_argv(self.args.dry_run, patch_files, prompt)

        act.tmp_before = tmp_snapshot(self.args.tmp_root)
        code, seconds, timed_out, started, ended = self.launch(argv, stage, env)
        leftovers = end_leftovers(stage, act.proc.pid)
        for path in (self.args.stage_root, stage, stage / "cfg"):  # the agent may have chmod-ed them (under /tmp)
            with contextlib.suppress(OSError):
                os.chmod(path, 0o700)
        moved, modified, kept = sweep_tmp(self.args.tmp_root, act.tmp_before, stage / "tmp-leftovers",
                                          self.tmp_keep, tmp_referenced(run_log_text(stage), self.args.tmp_root))
        root_left = self.sweep_stage_root(stage)
        act.swept = True

        stderr = read_text(stage / "stderr.log")
        n_root = root_assistant_messages(stage / "home" / "sessions")
        verdict = classify(stderr, n_root, timed_out)
        c = self.conditions
        result = {
            "id": run_id, "task": task["id"], "type": task.get("type"), "group": group, "rep": rep, "order": order,
            "block_pos": block_pos, "attempts": attempt_no, "exit": code, "seconds": seconds,
            "started_utc": started, "ended_utc": ended, "timeout": timed_out, "crash5063": verdict["crash5063"],
            "fatal_load_failure": verdict["fatal_load_failure"],
            # null on every recorded result: a retried attempt's code goes to failures.jsonl and its attempt.json.
            # infra_signal is what the check found even when a result (timeout, crash) explains it.
            "infra_code": verdict["infra_signal"] if verdict["retry"] else None,
            "infra_signal": verdict["infra_signal"], "root_assistant_messages": n_root,
            "prompt_sha256": sha256_bytes(prompt.encode("utf-8")), "suffix": suffix,
            "encourage_sha256": sha256_bytes(self.args.encourage.encode("utf-8")) if c["encourage"] else None,
            "patches": patches, "patch_sha256": {name: self.patch_sha[name] for name in patches},
            "task_sha256": sha256_bytes(line.encode("utf-8")), "workspace_sha256": workspace_sha,
            "cwd": str(workspace), "web": task_web(task), "runner": "run_matrix_v2",
            "runner_sha256": c["runner_sha256"], "dsh": c["dsh_version"], "dsh_bin_sha256": c["dsh_bin_sha256"],
            "runtime_tree_sha256": c["runtime_tree_sha256"], "parallel": 1, "dry_run": self.args.dry_run,
            "timeout_s": self.args.timeout, "permission": self.args.permission, "shuffle": self.args.shuffle,
            "env_names": sorted(env), "env_public": c["env_public"],
            "leftover_processes": leftovers, "tmp_leftovers": {"count": len(moved), "names": moved},
            "tmp_new_kept": {"count": len(kept), "names": sorted(kept), "reasons": kept},
            "tmp_modified": modified, "stage_root_leftovers": root_left,
            "deliverable": check_deliverable(spec, workspace, before),
        }
        return result, verdict["retry"]

    def run_cell(self, order: int, block_pos: int, task: dict, line: str, group: str, rep: int) -> None:
        """Up to MAX_ATTEMPTS attempts; each infrastructure failure is kept in _failed/ and the cell runs again
        with a new id (the next attempt probes the endpoints first). Three in a row pause the batch. Attempts that
        earlier invocations made at this cell (it paused there) count in "attempts" and "failed_attempt_ids"."""
        earlier = self.prior.get((task["id"], group, rep), [])
        failed = []
        for n in range(1, MAX_ATTEMPTS + 1):
            result, retry = self.attempt(order, block_pos, task, line, group, rep, len(earlier) + n)
            if not retry:
                result["failed_attempt_ids"] = [f["id"] for f in earlier + failed]
                self.record(result)
                return
            failed.append(self.file_failure(result))
        every = earlier + failed
        raise Paused(self.pause_info(f"{MAX_ATTEMPTS} infrastructure failures in a row", task, group, rep,
                                     attempts=len(every), codes=[f["code"] for f in every],
                                     ids=[f["id"] for f in every]))

    # -- the whole batch

    def run(self, todo: list) -> int:
        """Run the remaining cells in order, then clean up whichever way the batch ended (finish())."""
        for sig in STOP_SIGNALS:
            signal.signal(sig, on_signal)
        self.cells = len(todo)
        outcome = None
        try:
            try:
                self.running = True
                self.locks.lock()
                os.chmod(self.out, 0o000)
                for job in todo:
                    self.run_cell(*job)
            except BaseException as exc:  # Paused, Interrupted or an error
                outcome = exc
            STOP["armed"] = False  # from here on a stop signal is only noted: cleanup runs to the end
        except Interrupted as exc:
            # The first stop signal arrived while the batch was ending another way (between the exception and the
            # line above). It is the only Interrupted there can be, so nothing interrupts this handler.
            STOP["armed"] = False
            if outcome is None:
                outcome = exc.__context__ if isinstance(exc.__context__, Exception) else exc
        code = self.finish(outcome)
        self.write_progress({0: "done", 3: "paused", 130: "interrupted"}.get(code, f"stopped (exit {code})"))
        return code

    def finish(self, outcome) -> int:
        """Clean up after the batch ends: stop DSH at once (an interrupted attempt is discarded, so it gets no
        grace), restore BATCH_DIR and the lock paths first (a supervisor may follow its SIGTERM with SIGKILL a few
        seconds later), then end the attempt's leftovers, sweep and keep its stage in _interrupted/. An attempt
        paused before launch holds only its prepared workspace, which is removed."""
        act, self.active = self.active, None
        launched = act is not None and act.proc is not None
        if launched and act.proc.poll() is None:
            stop_group(act.proc, 0)
        self.running = False
        try:
            os.chmod(self.out, 0o700)
        except OSError as exc:
            log(f"warning: could not reopen {self.out}: {exc}")
        self.locks.restore()
        if act is not None:
            try:
                if isinstance(outcome, Paused) and not launched:
                    shutil.rmtree(act.stage, ignore_errors=True)
                else:
                    self.keep_interrupted(act)
            except Exception as exc:  # never lose the original outcome over the cleanup
                log(f"warning: cleanup of attempt {act.id} failed: {exc!r}")
        if STOP["signum"] is not None and not isinstance(outcome, Interrupted):
            log(f"signal {STOP['signum']} arrived during cleanup; cleanup finished")
        if isinstance(outcome, Paused):
            try:
                self.write_paused(outcome.info)
            except OSError as exc:
                log(f"warning: could not write PAUSED.json: {exc}; pause info: {json.dumps(outcome.info)}")
            log(f"paused {utc_now()}: {outcome.info['reason']}; see {self.out / 'PAUSED.json'}")
            return 3
        if isinstance(outcome, Interrupted):
            log(f"stopped by signal {outcome.signum} {utc_now()}; locks restored")
            return 128 + outcome.signum
        if outcome is not None:
            log(f"error {utc_now()}: {outcome!r}; locks restored")
            raise outcome
        log(f"done {utc_now()}: {self.cells} cells recorded -> {self.out}")
        return 0

    def keep_interrupted(self, act: Attempt) -> None:
        """The stopped attempt's leftovers ended (also found by cwd and environment, in case DSH had started but
        act.proc was not set yet), /private/tmp and the stage root swept, and its stage kept in _interrupted/<id>.
        No result is recorded, so the cell runs again on resume."""
        if not act.stage.exists():
            return
        end_leftovers(act.stage, act.proc.pid if act.proc else None, ABORT_GRACE_S)
        if act.tmp_before is not None and not act.swept:
            sweep_tmp(self.args.tmp_root, act.tmp_before, act.stage / "tmp-leftovers", self.tmp_keep,
                      tmp_referenced(run_log_text(act.stage), self.args.tmp_root))
            self.sweep_stage_root(act.stage)
        with self.batch_open():
            dest = self.out / "_interrupted"
            dest.mkdir(exist_ok=True)
            move_path(act.stage, dest / act.id)
        log(f"attempt {act.id} stopped; kept in {self.out / '_interrupted' / act.id}")


# ---------------------------------------------------------------- setup

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     fromfile_prefix_chars="@")
    parser.add_argument("--tasks", type=Path, required=True, help="task file (JSONL)")
    parser.add_argument("--groups", required=True, help="comma-separated groups; E-G = G's patches + encourage suffix")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--rep-start", type=int, default=1, help="number of the first repeat (to add repeats to a set)")
    parser.add_argument("--shuffle", type=int, help="shuffle each repeat's block with seed SEED*1000 + rep")
    parser.add_argument("--out", type=Path, required=True, help="batch directory")
    parser.add_argument("--timeout", type=float, default=3600.0, help="wall-clock limit per run, seconds")
    parser.add_argument("--only", help="comma-separated task ids")
    parser.add_argument("--parallel", type=int, default=1, help="must be 1")
    parser.add_argument("--encourage", default=DEFAULT_ENCOURAGE, help="text appended to the prompt in E- groups")
    parser.add_argument("--lock", type=Path, action="append", default=[],
                        help="path to chmod 000 for the whole batch (repeatable)")
    parser.add_argument("--stage-root", type=Path, default=Path("/private/tmp/dshx"))
    parser.add_argument("--permission", default="workspace-write", help="DSH_PERMISSION_MODE")
    parser.add_argument("--model-base-url", default=MODEL_BASE_URL, help="DEEPSEEK_BASE_URL (default: the internal endpoint)")
    parser.add_argument("--model-key-keychain", help="Keychain service whose value is used as DEEPSEEK_API_KEY as is "
                        "(deepseek-personal: the official API); default: the internal personal key from dsllm-usersk")
    parser.add_argument("--dry-run", action="store_true",
                        help="run scripts/fake_dsh.py instead of DSH, with dummy keys; no probe unless --probe-url-*")
    # Test-only options (refused without --dry-run).
    parser.add_argument("--probe-url-model", help="readiness probe URL instead of <DEEPSEEK_BASE_URL>/v1/messages")
    parser.add_argument("--probe-url-search", help="readiness probe URL instead of the search proxy's /v1/models")
    parser.add_argument("--probe-wait", type=float, default=PROBE_WAIT_S, help="seconds between readiness checks")
    parser.add_argument("--probe-limit", type=float, default=PROBE_LIMIT_S,
                        help="pause after the endpoints stay down this long")
    parser.add_argument("--tmp-root", type=Path, default=PRIVATE_TMP,
                        help="directory whose new top-level entries are moved after each run (tests use a scratch dir)")
    args = parser.parse_args(argv)
    if args.parallel != 1:
        parser.error("--parallel must be 1: runs that overlap share the endpoints and slow each other down")
    if args.repeats < 1 or args.rep_start < 1 or args.timeout <= 0 or args.probe_wait < 0 or args.probe_limit < 0:
        parser.error("--repeats, --rep-start and --timeout must be positive, --probe-wait and --probe-limit not "
                     "negative")
    test_only = [flag for flag, used in (("--probe-url-model", args.probe_url_model is not None),
                                         ("--probe-url-search", args.probe_url_search is not None),
                                         ("--probe-wait", args.probe_wait != PROBE_WAIT_S),
                                         ("--probe-limit", args.probe_limit != PROBE_LIMIT_S),
                                         ("--tmp-root", args.tmp_root != PRIVATE_TMP)) if used]
    if test_only and not args.dry_run:
        # A real run would send the keys to a --probe-url-* target, or change the probe and the /tmp sweep unseen.
        parser.error(f"{', '.join(test_only)} only with --dry-run (tests)")
    if any(g.strip().startswith("E-") for g in args.groups.split(",")) and not args.encourage.strip():
        parser.error("--encourage must not be empty when an E- group runs")
    return args


def inside(path: Path, other: Path) -> bool:
    """Whether path is other or lies below it (both resolved)."""
    return path == other or other in path.parents


def path_problems(args, entries: list) -> list:
    """Why --out, --stage-root or a --lock path cannot be used; checked before anything is touched."""
    problems = []
    if inside(args.stage_root, args.out) or inside(args.out, args.stage_root):
        problems.append("--stage-root and --out must not contain each other")
    if not args.dry_run and inside(args.out, PRIVATE_TMP):
        problems.append(f"--out {args.out} is under /private/tmp, where every run can chmod it and read it")
    home = pwd.getpwuid(os.getuid()).pw_dir
    # What runs (or the runner between runs) need. Real runs need nothing in scripts/ or patches/ once they have
    # started (the runner is loaded and the patches are in memory), so those can be locked; dry runs need the fake.
    needed = [RUNTIME, args.stage_root, args.out, args.tmp_root, Path(NODE).resolve().parent.parent,
              Path(home, "Library", "Python", "3.9")]
    needed += [Path(t["workspace_from"]).resolve() for t, _ in entries if t.get("workspace_from")]
    if args.dry_run:
        needed.append(FAKE_DSH)
    for path in args.lock:
        if not os.path.lexists(path):
            problems.append(f"lock path does not exist: {path}")
            continue
        hidden = sorted({str(n) for n in needed if inside(n, path) or inside(path, n)})
        if hidden:
            problems.append(f"lock path {path} would hide what runs need: {', '.join(hidden)}")
        if not args.dry_run and inside(path, PRIVATE_TMP):
            problems.append(f"lock path {path} is under /private/tmp, where every run can chmod it back")
    return problems


def open_stage_root(root: Path):
    """Create or reopen the stage root and hold its lock for the life of the process: one runner per stage root
    (the lock is released when the process ends, however it ends). A directory that holds anything but this
    runner's files is refused, since everything else in it is collected (a mistaken --stage-root /private/tmp
    must not touch other programs' files)."""
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = root / STAGE_LOCK
    try:
        entries = set(os.listdir(root))
    except PermissionError:
        if os.stat(root).st_uid != os.getuid():
            fail(f"--stage-root {root} cannot be read")
        os.chmod(root, 0o700)  # an agent chmod-ed it (it is under /tmp) and its runner was killed before undoing it
        entries = set(os.listdir(root))
    tagged = STAGE_LOCK in entries and read_text(lock_path) == STAGE_LOCK_TAG
    if entries - {STAGE_LOCK} and not tagged:
        fail(f"--stage-root {root} is not empty and was not made by run_matrix_v2; give a new or empty directory")
    handle = open(lock_path, "a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fail(f"another run_matrix_v2 is using {root}")
    if not tagged:
        handle.seek(0)
        handle.truncate()
        handle.write(STAGE_LOCK_TAG)
        handle.flush()
    return handle


def lock_batch_dir(out: Path):
    """Hold a lock beside BATCH_DIR (outside it, so it works while BATCH_DIR is 000): one runner per batch dir,
    whatever its stage root. A second runner would otherwise reopen the live batch dir and its lock paths."""
    out.parent.mkdir(parents=True, exist_ok=True)
    handle = open(out.parent / f".{out.name}.lock", "a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fail(f"another run_matrix_v2 is using {out}")
    return handle


def killed_runner_left(out: Path) -> bool:
    """Whether a runner was killed (SIGKILL, power loss) before it restored its locks: BATCH_DIR is still 000, or
    BATCH_DIR/locks.json is still there."""
    try:
        return stat.S_IMODE(os.stat(out).st_mode) == 0 or os.path.lexists(out / LOCK_RECORD)
    except FileNotFoundError:
        return False


def main() -> None:
    args = parse_args()
    args.out = args.out.resolve()
    args.stage_root = args.stage_root.resolve()
    args.tmp_root = args.tmp_root.resolve()
    args.lock = list(dict.fromkeys(p.resolve() for p in args.lock))
    if inside(args.stage_root, args.out) or inside(args.out, args.stage_root):
        fail("--stage-root and --out must not contain each other")

    # A runner killed with SIGKILL leaves BATCH_DIR and its lock paths at 000, and those may include the task file
    # and patches/. Undo that before reading anything: take the runner locks (refused while that runner still
    # lives), end its orphaned DSH (before BATCH_DIR opens), then restore the modes recorded in locks.json.
    # (scripts/ cannot be undone this way: python must read the runner first. After a SIGKILL or a power loss with
    # scripts/ locked, chmod it back by hand; this start restores the rest.)
    held, ended = None, {}
    if killed_runner_left(args.out):
        held = (open_stage_root(args.stage_root), lock_batch_dir(args.out))
        ended = {p.name: end_leftovers(p, None) for p in orphan_stages(args.stage_root, args.dry_run)}
        os.chmod(args.out, 0o700)
        restore_recorded_locks(args.out / LOCK_RECORD)

    try:
        entries = load_tasks(args.tasks, args.only)  # into memory before anything is locked
    except (OSError, TaskError) as exc:
        fail(str(exc))
    groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    if not groups or len(set(groups)) != len(groups) or "E-" in groups:
        fail("--groups must list distinct group names")
    names = sorted({n for task, _ in entries for g in groups for n in group_patches(task, g)[0]})
    missing = [n for n in names if not os.path.isfile(PATCHES / n)]
    if missing:
        fail(f"missing (or unreadable) patch files in {PATCHES}: {', '.join(missing)}")
    try:
        patch_bytes = {n: (PATCHES / n).read_bytes() for n in names}  # every attempt uses these bytes
    except OSError as exc:
        fail(f"cannot read a patch: {exc}")
    relative = [n for n, data in patch_bytes.items() if RELATIVE_INSERT.search(data)]
    if relative:
        fail(f"patches that insert a plugin by relative path cannot be copied per attempt: {', '.join(relative)}")
    if not args.dry_run and not (Path(NODE).exists() and DSH_BIN.exists()):
        fail(f"DSH not found ({NODE}, {DSH_BIN})")
    try:
        import zstandard  # noqa: F401  (DSH writes compressed session logs; without it every run would look failed)
    except ImportError:
        fail("the zstandard module is required to read DSH session logs")

    if not args.tmp_root.is_dir():
        fail(f"--tmp-root {args.tmp_root} is not a directory")
    problems = path_problems(args, entries)
    if problems:
        fail("; ".join(problems))
    markers = root_markers(args.stage_root.parent)  # the stage root's own entries are collected below
    if markers:
        fail(f"a .git above the stage root would add instructions to every prompt: {', '.join(markers)}")
    runtime = runtime_fingerprint()
    try:
        workspace_sha = {t["id"]: tree_sha256(Path(t["workspace_from"])) for t, _ in entries if t.get("workspace_from")}
    except OSError as exc:
        fail(f"cannot read a workspace_from template: {exc}")
    env = base_env(args.permission, args.model_base_url)
    conditions = batch_conditions(args, entries, groups, {n: sha256_bytes(b) for n, b in patch_bytes.items()},
                                  runtime, workspace_sha, public_env(env))

    # The stage root first (one runner per stage root), then the batch dir (one runner per batch dir); both are held
    # until the process ends. Every stage dir found then belongs to an attempt that never finished: its processes
    # are ended before BATCH_DIR opens.
    held = held or (open_stage_root(args.stage_root), lock_batch_dir(args.out))
    orphans = orphan_stages(args.stage_root, args.dry_run)
    for orphan in orphans:
        if orphan.name not in ended:
            ended[orphan.name] = end_leftovers(orphan, None)

    # The batch dir: open it (a runner killed with SIGKILL leaves it at 000, and its lock paths at 000 with their
    # modes in locks.json), then read what is done.
    args.out.mkdir(exist_ok=True)
    os.chmod(args.out, 0o700)
    restore_recorded_locks(args.out / LOCK_RECORD)
    for path in args.lock:
        try:
            locked = stat.S_IMODE(os.stat(path).st_mode) == 0
        except OSError:
            locked = True
        if locked:
            fail(f"lock path {path} has mode 000 (or cannot be reached) and no record of its mode: restore it by "
                 f"hand, or resume the batch that locked it (its BATCH_DIR/{LOCK_RECORD} has the modes)")
    known_ids = set()
    for sub in ("", "_failed", "_interrupted", "_orphaned"):
        if (args.out / sub).is_dir():
            known_ids.update(p.name for p in (args.out / sub).iterdir())
    stray = [n for n in stage_root_entries(args.stage_root, args.dry_run) if args.stage_root / n not in orphans]
    if orphans or stray:
        (args.out / "_orphaned").mkdir(exist_ok=True)
    for orphan in orphans:
        move_path(orphan, args.out / "_orphaned" / orphan.name)
        known_ids.add(orphan.name)
        log(f"unfinished attempt {orphan.name} from an earlier runner moved to _orphaned/ "
            f"({ended[orphan.name]['count']} leftover processes ended)")
    if stray:  # left in the stage root by an attempt whose runner was killed before it swept
        dest = args.out / "_orphaned" / f"stage-root-{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}"
        dest.mkdir(exist_ok=True)
        for name in stray:
            move_path(args.stage_root / name, dest / name)
        log(f"{len(stray)} entries left in the stage root moved to _orphaned/{dest.name}/")

    done = read_manifest(args.out / "manifest.jsonl")
    record = args.out / CONDITIONS
    if record.exists():
        try:
            old = json.loads(record.read_text(encoding="utf-8"))
        except ValueError as exc:
            fail(f"{record} is unreadable ({exc})")
        diffs = conditions_diff(old, conditions)
        if diffs:
            fail(f"conditions differ from those the batch started with ({record}): {'; '.join(diffs)}. Only "
                 f"--repeats and --rep-start may change; start a new --out to run under new conditions")
    elif done:
        fail(f"{args.out} has results but no {CONDITIONS} (started by an older runner); use a new --out")
    else:
        write_json(record, conditions)
    mixed = sorted({str(rec.get("dry_run", False)) for rec in done.values()} - {str(args.dry_run)})
    if mixed:
        fail(f"{args.out} holds results with dry_run={', '.join(mixed)}; dry and real runs never share a batch")
    prior = read_failures(args.out / "failures.jsonl")
    jobs = build_jobs(entries, groups, args.rep_start, args.repeats, args.shuffle)
    todo = [j for j in jobs if (j[2]["id"], j[4], j[5]) not in done]
    paused = args.out / "PAUSED.json"
    if paused.exists():
        old = paused.with_name(f"PAUSED.{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}.json")
        paused.rename(old)
        log(f"previous pause record moved to {old.name}")
    tmp_keep = {top_level_name(p, args.tmp_root) for p in (args.stage_root, args.out)} - {None}

    if args.dry_run:
        user_sk = DRY_RUN_USER_SK
    else:
        try:
            user_sk = keychain("dsllm-usersk")
        except (OSError, subprocess.CalledProcessError):
            user_sk = ""
        if not user_sk:
            fail("could not read dsllm-usersk from the Keychain")
    model_key = None
    if args.model_key_keychain and not args.dry_run:
        try:
            model_key = keychain(args.model_key_keychain)
        except (OSError, subprocess.CalledProcessError):
            model_key = ""
        if not model_key:
            fail(f"could not read {args.model_key_keychain} from the Keychain")

    log(f"start {utc_now()}: {len(jobs)} cells = {len(entries)} tasks x {len(groups)} groups x {args.repeats} "
        f"repeats; {len(jobs) - len(todo)} already in the manifest, {len(todo)} to run, one at a time"
        f"{' [dry-run]' if args.dry_run else ''} -> {args.out}")
    if not todo:
        return
    batch = Batch(args, user_sk, known_ids, tmp_keep, patch_bytes, env, conditions, prior, model_key)
    batch.total, batch.done = len(jobs), len(jobs) - len(todo)
    batch.write_progress("starting")
    sys.exit(batch.run(todo))


if __name__ == "__main__":
    main()
