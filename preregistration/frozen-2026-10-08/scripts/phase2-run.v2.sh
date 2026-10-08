#!/bin/bash
# Phase 2 batches on the dev box, v2 (phase2-experiment-protocol-2026-10-08.md v5.1). One MODE per invocation:
#   smoke / smoke-d / smoke-f   pilots (never scored)
#   calib      4 calibration tasks x the four sentence groups x 2 (never scored; spawn and search counts are read)
#   main       modules A, B, C, H, G on all tasks: one batch, block = task x repeat (runner --block-by task)
#   merge      module G's four-report merge runs (tasks built by build_merge_tasks_drb2.py after main)
#   d          module D, v4-pro (extra patch v4pro.patch.yml, 120-minute limit)
#   smoke-f64  one large-coding run in a 64 GB container (decides the memory of module F)
#   f          module F, code tasks (not on the web; may run while judging runs); CODE_TASKS picks the task file
# Batch names are p2-* (phase2-smoke was used on 2026-10-03 by the new-task screening). A web batch leaves the marker
# results/runs/<batch>/WEB so that the judge launcher can refuse to start while it runs.
# After the runs: the run table (judge-env/scripts/run_table.py) and, for web batches, the leak check (drb2_sources.py).
# Start from the Mac (or from phase2-chain.sh):
#   security find-generic-password -s dsllm-usersk -a zhangziya -w | ssh dev-cpu-hg \
#     "cd $P; read -r K; DSEC_KEY=\"\$K\" MODE=smoke setsid nohup bash phase2-run.v2.sh > results/p2-smoke.out 2>&1 < /dev/null & unset K"
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
cd "$P" || exit 1
source haienv py312-202505 >/dev/null 2>&1
command -v python >/dev/null || { echo "haienv python missing"; exit 1; }
set -u
export PYTHONPATH=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-py/1.21.2
KEY="${DSEC_KEY:?no key}"
unset DSEC_KEY
J=judge-env/scripts
MODE=${MODE:-smoke}
SEED=${SEED:-20261008}
WEB=1
TASKS=tasks/phase2-drb2-tasks.jsonl
INDEX=tasks/phase2-drb2-index.json
PROBE=deepseek-flash
case "$MODE" in
  smoke)     B=p2-smoke;     CELLS=tasks/cells-phase2-smoke.json;     PAR=${PAR:-8} ;;
  smoke-d)   B=p2-smoke-d;   CELLS=tasks/cells-phase2-smoke-d.json;   PAR=${PAR:-5};  TASKS=tasks/phase2-drb2-tasks-v4pro.jsonl; PROBE=deepseek-v4-pro ;;
  calib)     B=p2-calib;     CELLS=tasks/cells-phase2-calib.json;     PAR=${PAR:-32} ;;
  main)      B=p2-main;      CELLS=tasks/cells-phase2-main.json;      PAR=${PAR:-26} ;;
  merge)     B=p2-merge;     CELLS=tasks/cells-phase2-merge.json;     PAR=${PAR:-20}; TASKS=tasks/phase2-merge-tasks.jsonl; INDEX=tasks/phase2-merge-index.json ;;
  d)         B=p2-d;         CELLS=tasks/cells-phase2-d.json;         PAR=${PAR:-20}; TASKS=tasks/phase2-drb2-tasks-v4pro.jsonl; PROBE=deepseek-v4-pro ;;
  f)         B=p2-f;         CELLS=tasks/cells-phase2-f.json;         PAR=${PAR:-12}; TASKS=${CODE_TASKS:-tasks/phase2-code-tasks.jsonl}; WEB=0 ;;
  smoke-f)   B=p2-smoke-f;   CELLS=tasks/cells-phase2-smoke-f.json;   PAR=${PAR:-3};  TASKS=tasks/phase2-code-tasks.jsonl; WEB=0 ;;
  smoke-f64) B=p2-smoke-f64; CELLS=tasks/cells-phase2-smoke-f64.json; PAR=1;          TASKS=tasks/phase2-code-tasks-64g.jsonl; WEB=0 ;;
  *) echo "unknown MODE $MODE"; exit 1 ;;
esac
[ -s "$CELLS" ] && [ -s "$TASKS" ] && [ -s tasks/phase2-sentences.json ] && [ -s patches/dsh-wait/index.js ] || { echo "a cell, task, sentence or patch file is missing ($CELLS, $TASKS)"; exit 1; }
LOG=results/phase2-$B.log
mkdir -p results/master/raw "results/runs/$B"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG"; }
if [ "$WEB" = 1 ] && pgrep -f '^[^ ]*python[0-9.]* -u [^ ]*(judge_facts|ws_score|drb2_score|drb2_score_gpt)[.]py' >/dev/null; then log "judging is running; a web batch must not start"; exit 1; fi
if pgrep -f '^[^ ]*python[0-9.]* -u dsec_matrix' >/dev/null; then log "another DSec batch is running"; exit 1; fi
[ "$WEB" = 1 ] && touch "results/runs/$B/WEB"
matrix() { DSEC_USER_SK="$KEY" python -u dsec_matrix_v6.py --tasks "$TASKS" --patches patches --out results/runs \
             --batch "$B" --cells "$CELLS" --seed "$SEED" --parallel "$PAR" --block-by task \
             --sentences tasks/phase2-sentences.json --probe-model "$PROBE"; }
log "$B start (pid $$); mode $MODE; cells $CELLS ($(python -c "import json;print(len(json.load(open('$CELLS'))))") runs); tasks $(sha256sum "$TASKS" | cut -c1-16); sentences $(sha256sum tasks/phase2-sentences.json | cut -c1-16); runner $(sha256sum dsec_matrix_v6.py | cut -c1-16); parallel $PAR"
matrix && matrix || { log "batch failed"; rm -f "results/runs/$B/WEB"; exit 1; }
unset KEY
rm -f "results/runs/$B/WEB"
log "runs done"
python $J/run_table.py "results/runs/$B" --out results/master/raw > "results/master/raw/$B.extract.txt" 2>&1 && log "run table written: results/master/raw/$B.csv" || log "run table FAILED (see results/master/raw/$B.extract.txt)"
if [ "$WEB" = 1 ]; then
  python $J/drb2_sources.py "results/runs/$B" --index "$INDEX" --out "results/analysis-$B-sources.json" > "results/analysis-$B-sources.txt" 2>&1 && log "leak check: $(tail -n 1 "results/analysis-$B-sources.txt")" || log "leak check FAILED"
fi
date -u +%Y-%m-%dT%H:%M:%SZ > "results/phase2-$B-done.txt"
log "$B finished"
