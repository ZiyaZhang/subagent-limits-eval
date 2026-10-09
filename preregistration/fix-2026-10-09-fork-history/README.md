# Correction of 2026-10-09: the log of a forked agent starts with a copy of its parent's history

Found at 2026-10-09T17:00Z, while reports were being judged and before any judgement was joined to a table.

**What was wrong.** An agent started with `subagent_fork` after its parent has completed a turn gets a session log
that begins with a copy of the parent's events (same call ids and times; header `isSeeded: true`), closed by a
`session/end-seed` event. The readers took the whole log as the agent's own, so the parent's tokens, tool calls,
search requests, spawn calls and messages were counted once more for every such fork.

**Scope.** All 28 batches of phase 1 (3,009 runs) and the four phase-2 batches (2,120 runs) were scanned
(`diagnostics/fork_inflation.py`). Logs with a copy exist in 3 runs of `p2-main` only (844gcwcw22, vj1vzxympf,
x677n9f24r; 9 forks; cells "split in 8" with K = 4, 8, 6). Their model cost had been over-counted by 22%, 40% and
52%; the batch total by 0.08%. No run of phase 1, `p2-merge`, `p2-d` or `p2-f` is affected.

**The fix.** For a seeded log only the events from the first `session/end-seed` on are read.
`diagnostics/fork_check.py` confirms for each of the 9 forks that every call id before the marker is in the parent's
log and none after it is.

| File | Change |
|---|---|
| `run_metrics.py` | `read_log` leaves the copy out and reports its length as `inherited` (all scripts that use `load_sessions` follow) |
| `delegation_stats.py` | `read_session`, same rule |
| `retry_waits.py`, `request_timing.py` | same rule in their own readers |
| `test_run_metrics.py` | one new test (forked log, resumed log, fork cut off during the copy); 47 tests pass |
| `forkfix-regen.sh` | rebuilds the files of `p2-main` that had been computed from logs; the old files are kept under `results/before-fork-fix/` |

**Check.** The rebuilt run table of `p2-main` differs from the old one in exactly these 3 rows (token, tool-call,
search-request and spawn-call columns); the other 1,781 rows are identical (`diagnostics/raw_diff.py`).
Delegation units went from 3,030 to 3,021: the 9 removed ones were the forks' copies of the root's spawn calls.

**Also seen** (`diagnostics/fork_kinds.py`, `fork_prompts.py`; odd-behaviors-log.md item 8): 69 of the 78 forks
started in `p2-main` received no parent context at all, because the fork provider copies completed turns only and
the root is usually still in its first turn.
