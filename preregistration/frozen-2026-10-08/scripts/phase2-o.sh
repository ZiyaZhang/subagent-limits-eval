#!/bin/bash
# Module O (orchestration contrast, exploratory; protocol change log 2026-10-08T14:10Z): on the g40 tasks, the main agent
# gets the role sentence "po" (split and merge only, no searching itself) at D1-K8, against a fresh default D1-K8 run
# in the same batch (80 runs). Runs after the whole chain is done (a web batch must not overlap judging), then judges
# the batch (GPT-5.5 pass 1, Opus fifth, GPT-5.5 second pass on a tenth). Start from the Mac like the chain:
#   ... DSEC_KEY="\$K" setsid nohup bash phase2-o.sh > results/phase2-o.out 2>&1 < /dev/null & ...
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
cd "$P" || exit 1
source haienv py312-202505 >/dev/null 2>&1
set -u
KEY="${DSEC_KEY:?no key}"; unset DSEC_KEY
export PYTHONPATH=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-py/1.21.2
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a results/phase2-o.log; }
log "phase2-o waiting for the chain (results/phase2-chain-DONE.txt)"
until [ -f results/phase2-chain-DONE.txt ]; do sleep 120; done
while pgrep -f '^[^ ]*python[0-9.]* -u [^ ]*(drb2_score|drb2_score_gpt)[.]py' >/dev/null; do sleep 60; done
log "chain done; starting module O"
rm -f results/phase2-p2-o-done.txt
DSEC_KEY="$KEY" MODE=o bash phase2-run.v3.sh > results/p2-o.out 2>&1
[ -f results/phase2-p2-o-done.txt ] || { log "p2-o did not finish (results/p2-o.out)"; exit 1; }
JUDGE_USER_SK="$KEY" B=p2-o bash drb2-judge-gpt.sh > results/drb2-judge-gpt-p2-o.out 2>&1
unset KEY
date -u +%Y-%m-%dT%H:%M:%SZ > results/phase2-o-DONE.txt
log "module O done and judged"
