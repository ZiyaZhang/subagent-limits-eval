#!/bin/bash
# After the fork correction of 2026-10-09 (a forked agent's log starts with a copy of its parent's history; the readers
# now leave the copy out): rebuild every file of the main batch that was computed from session logs before the fix.
# Old files are kept under results/before-fork-fix/. Only p2-main has forked agents (3 runs); the other batches have none.
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
cd "$P" || exit 1
source haienv py312-202505 >/dev/null 2>&1
export PYTHONDONTWRITEBYTECODE=1
J=judge-env/scripts
B=p2-main
RUNS3=844gcwcw22,vj1vzxympf,x677n9f24r
OLD=results/before-fork-fix
mkdir -p $OLD/digests $OLD/delegation
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
keep() { [ -e "$OLD/$(basename "$1")" ] || cp -p "$1" "$OLD/" 2>/dev/null; }

log "delegation units"
keep results/delegation/$B/units.jsonl; keep results/delegation/$B/extract-stats.txt; keep results/delegation-$B-extract.txt
python -u $J/delegation_classify.py extract results/runs/$B --out analysis-dev/delegation-forkfix/$B --jobs 32 > analysis-dev/delegation-forkfix-extract.txt 2>&1 \
  && cp -p analysis-dev/delegation-forkfix/$B/units.jsonl results/delegation/$B/units.jsonl.new && mv results/delegation/$B/units.jsonl.new results/delegation/$B/units.jsonl \
  && cp -p analysis-dev/delegation-forkfix/$B/extract-stats.txt results/delegation/$B/extract-stats.txt \
  && cp -p analysis-dev/delegation-forkfix-extract.txt results/delegation-$B-extract.txt && log "units: $(tail -n 1 analysis-dev/delegation-forkfix-extract.txt | cut -c1-200)" || log "units FAILED"

log "digests of the three runs"
for r in ${RUNS3//,/ }; do for f in results/digests/$B/$r.*; do [ -e "$OLD/digests/$(basename "$f")" ] || cp -p "$f" $OLD/digests/; done; done
python -u $J/run_digest.py results/runs/$B --ids $RUNS3 --jobs 3 > analysis-dev/digests-forkfix.txt 2>&1 && log "digests: $(tail -n 1 analysis-dev/digests-forkfix.txt | cut -c1-200)" || log "digests FAILED"

log "retry waits, tool errors, request timing"
for f in retry toolerrors reqtiming; do keep results/analysis-$B-$f.json; keep results/analysis-$B-$f.txt; done
python $J/retry_waits.py results/runs/$B --out results/analysis-$B-retry.json --jobs 16 > results/analysis-$B-retry.txt 2>&1 && log "retry: $(tail -n 1 results/analysis-$B-retry.txt | cut -c1-160)" || log "retry FAILED"
PYTHONPATH=$P/$J python $J/tool_errors.py results/runs/$B --out results/analysis-$B-toolerrors.json --jobs 16 > results/analysis-$B-toolerrors.txt 2>&1 && log "tool errors: $(tail -n 1 results/analysis-$B-toolerrors.txt | cut -c1-160)" || log "tool errors FAILED"
python -u $J/request_timing.py results/runs/$B --json results/analysis-$B-reqtiming.json > results/analysis-$B-reqtiming.txt 2>&1 && log "request timing done" || log "request timing FAILED"

log "message census and tool-error census"
keep results/analysis-$B-messages.json
[ -d $OLD/toolcensus ] || cp -rp results/analysis-$B-toolcensus $OLD/toolcensus 2>/dev/null
python -u $J/message_census.py results/runs/$B --out results/analysis-$B-messages.json --jobs 32 > analysis-dev/messages-forkfix.txt 2>&1 && log "messages: $(head -n 1 analysis-dev/messages-forkfix.txt | cut -c1-200)" || log "messages FAILED"
python -u $J/tool_error_census.py results/runs/$B --out results/analysis-$B-toolcensus --jobs 32 > analysis-dev/toolcensus-forkfix.txt 2>&1 && log "tool census: $(head -n 2 analysis-dev/toolcensus-forkfix.txt | tr '\n' ' ' | cut -c1-200)" || log "tool census FAILED"
log "FORKFIX-REGEN-END"
