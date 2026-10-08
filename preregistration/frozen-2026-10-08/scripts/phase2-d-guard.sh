#!/bin/bash
# Kill switch for module D (v4-pro): after the v4-pro smoke (p2-smoke-d) finishes, if two or more of its five cells
# gave up after three attempts, write results/runs/p2-d/STOP so that the chain's D batch starts and stops at once
# (the runner starts no attempt when STOP exists), and leave a note. Otherwise do nothing. Runs in the background.
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
cd "$P" || exit 1
until [ -f results/phase2-p2-smoke-d-done.txt ]; do sleep 60; done
gave_up=$(wc -l < results/runs/p2-smoke-d/failures.jsonl 2>/dev/null || echo 0)
retries=$(python3 -c "import json;print(json.load(open('results/runs/p2-smoke-d/progress.json'))['infra_retries'])" 2>/dev/null || echo "?")
mkdir -p results/runs/p2-d
if [ "${gave_up:-0}" -ge 2 ]; then
  touch results/runs/p2-d/STOP
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) D skipped: v4-pro smoke had $gave_up of 5 cells give up after 3 attempts ($retries infra retries); STOP written to results/runs/p2-d" | tee results/phase2-d-guard.txt
else
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) D allowed: v4-pro smoke had $gave_up cells give up ($retries infra retries)" | tee results/phase2-d-guard.txt
fi
