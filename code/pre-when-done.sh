#!/bin/bash
# Run the blind pre-step the moment the chain is DONE, so the two human forms are ready without waiting for the next
# check-in. Waits for results/phase2-chain-DONE.txt and for every judging process to end, then runs phase2-post.sh in
# mode pre. Module O starts its own runs at the same moment (phase2-o.sh); those are runs, not judging, so the two do
# not collide, and the leak look of module O is done separately once that batch is judged.
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
cd "$P" || exit 1
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
log "waiting for results/phase2-chain-DONE.txt"
until [ -f results/phase2-chain-DONE.txt ]; do
  if [ -f results/phase2-chain-FAILED.txt ]; then log "the chain FAILED: $(cat results/phase2-chain-FAILED.txt | cut -c1-200); not running the pre step"; exit 1; fi
  sleep 60
done
log "the chain is DONE; waiting for the judging processes to end"
while ps -eo args | grep -qE '[p]ython[0-9.]* -u [^ ]*drb2_score(_gpt)?(_repair)?[.]py'; do sleep 30; done
log "starting MODE=pre"
MODE=pre bash judge-env/scripts/phase2-post.sh > results/phase2-post-pre.out 2>&1
log "pre exit $?; last lines:"
tail -n 6 results/phase2-post-pre.out | cut -c1-220
log "PRE-WHEN-DONE-END"
