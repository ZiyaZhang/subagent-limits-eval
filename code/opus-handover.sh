#!/bin/bash
# Hand the Opus sample of p2-main over to the chain. opus-early.sh started the sample next to the GPT-5.5 first pass; it is
# slower than expected and will not be through when the first pass ends. The chain then starts its own Opus step on the
# same ids, and drb2_score.py skips a report only once its result file exists, so two processes walking the same list
# would judge every remaining report twice, eight at a time. This waits for the chain's Opus log to appear and stops the
# early run at that moment; the chain's process judges whatever is left. Touches nothing of the chain.
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
cd "$P" || exit 1
OUT=results/drb2-score/p2-main-opus.out
DIR=results/drb2-score/p2-main
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
log "waiting for $OUT (the chain's Opus step) or for the early run to end; $(ls $DIR | wc -l) result files now"
while :; do
  if ! ps -eo args | grep -q '[b]ash opus-early.sh'; then
    log "the early run ended by itself with $(ls $DIR | wc -l) result files: nothing to hand over"
    break
  fi
  if [ -e "$OUT" ]; then
    n=$(ls $DIR | wc -l)
    for pid in $(ps -eo pid,args | grep '[b]ash opus-early.sh' | awk '{print $1}'); do
      kids=$(ps -o pid= --ppid "$pid")
      kill "$pid" 2>/dev/null  # the launcher first, so that it does not go on once its scorer is gone
      for k in $kids; do kill "$k" 2>/dev/null; done
    done
    sleep 3
    log "the chain's Opus step started: early run stopped at $n result files; still alive: $(ps -eo args | grep -c '[o]pus-early.sh')"
    bad=0
    for f in $DIR/*.json; do python3 -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8'))" "$f" 2>/dev/null || { bad=$((bad + 1)); log "NOT VALID JSON: $f"; }; done
    log "result files that do not parse: $bad"
    break
  fi
  sleep 5
done
log "OPUS-HANDOVER-END"
