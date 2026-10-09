#!/bin/bash
# Extra steps of the judging stage that the chain does not run (protocol v5.1 sections 五 and 六), started by hand:
#   probe   the price of one search request, measured on 100 requests of the main batch (search_cost_probe.py)
#   pilot   the behaviour checklist on 40 runs and the classification of re-delegations on 40 units (a first look
#           at the prompts' output before the larger sample)
#   behavior    the behaviour checklist on every run of the batch (runs already annotated are skipped)
#   delegation  the classification of re-delegations on a seeded sample of N_UNITS units (0 = every unit)
# The key comes in through the environment only. Parallel stays low: the GPT-5.5 route is shared with the judging.
#   WHAT="probe pilot" bash stage6-extras.sh      (JUDGE_USER_SK in the environment)
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
cd "$P" || exit 1
source haienv py312-202505 >/dev/null 2>&1
set -u
: "${JUDGE_USER_SK:?no key}"
export JUDGE_USER_SK PYTHONDONTWRITEBYTECODE=1
J=judge-env/scripts
B=${B:-p2-main}
WHAT=${WHAT:-probe pilot}
PARA=${PARA:-2}
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
ids() {  # $1 = how many: a seeded random sample of the runs that had the delegation tools (depth limit >= 1)
  python - "results/master/raw/$B.csv" "$1" <<'PY'
import csv, random, sys
rows = [r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")) if r["task"].startswith("drb2_") and "D0" not in r["group"]]
ids = sorted(r["id"] for r in rows)
random.Random(20261008).shuffle(ids)
print(",".join(ids[:int(sys.argv[2])]))
PY
}
for w in $WHAT; do
  case "$w" in
  probe)
    log "search price probe on $B (100 requests)"
    python -u $J/search_cost_probe.py results/runs/$B --sample 100 --out results/search-cost-probe-$B.json > results/search-cost-probe-$B.txt 2>&1 \
      && log "probe: $(grep 'per request' results/search-cost-probe-$B.txt | cut -c1-200)" || log "probe FAILED (results/search-cost-probe-$B.txt)" ;;
  pilot)
    log "behaviour checklist pilot: 40 runs"
    PYTHONPATH=$P/$J python -u $J/behavior_annotate.py results/digests/$B --out results/behavior/$B --ids "$(ids 40)" --parallel "$PARA" > results/behavior-$B-pilot.txt 2>&1 \
      && log "behaviour pilot: $(tail -n 1 results/behavior-$B-pilot.txt | cut -c1-160)" || log "behaviour pilot FAILED"
    log "re-delegation classification pilot: 40 units"
    PYTHONPATH=$P/$J python -u $J/delegation_classify.py annotate results/delegation/$B --limit 40 --parallel "$PARA" > results/delegation-$B-pilot.txt 2>&1 \
      && log "delegation pilot: $(tail -n 1 results/delegation-$B-pilot.txt | cut -c1-160)" || log "delegation pilot FAILED" ;;
  behavior)
    log "behaviour checklist on every run of $B"
    PYTHONPATH=$P/$J python -u $J/behavior_annotate.py results/digests/$B --out results/behavior/$B --parallel "$PARA" > results/behavior-$B-full.txt 2>&1 \
      && log "behaviour: $(tail -n 1 results/behavior-$B-full.txt | cut -c1-160)" || log "behaviour FAILED (results/behavior-$B-full.txt)" ;;
  delegation)
    log "re-delegation classification: ${N_UNITS:-400} units (0 = all)"
    PYTHONPATH=$P/$J python -u $J/delegation_classify.py annotate results/delegation/$B --limit "${N_UNITS:-400}" --parallel "$PARA" > results/delegation-$B-sample.txt 2>&1 \
      && log "delegation: $(tail -n 1 results/delegation-$B-sample.txt | cut -c1-160)" || log "delegation FAILED (results/delegation-$B-sample.txt)" ;;
  esac
done
unset JUDGE_USER_SK
log "STAGE6-EXTRAS-END ($WHAT)"
