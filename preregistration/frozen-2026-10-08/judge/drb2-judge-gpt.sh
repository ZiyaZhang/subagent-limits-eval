#!/bin/bash
# Phase-2 judging of a DeepResearch Bench II batch on the dev box (protocol v5.1 section 八):
#   1. GPT-5.5 (official judge) on every report of the batch, pass 1                    drb2_score_gpt.py
#   2. Opus 5.5 high on a fifth of the reports (run-id hash order), cross-vendor check   drb2_score.py --limit N
#   3. GPT-5.5 pass 2 on a tenth of the reports (self-consistency)                       drb2_score_gpt.py --repeat 2
# Refuses to start while a web batch runs (the runs' web search and the judges share the company proxy). The key
# comes in through the environment and is never written to disk. Start from the Mac:
#   security find-generic-password -s dsllm-usersk -a zhangziya -w | ssh dev-cpu-hg \
#     "cd $P; read -r K; JUDGE_USER_SK=\"\$K\" B=p2-main setsid nohup bash drb2-judge-gpt.sh > results/drb2-judge-gpt-phase2-main.out 2>&1 < /dev/null & unset K"
# The rows file is the run table of the batch (results/master/raw/<batch>.csv: id, task ...); the judge scripts read
# only id and task from it.
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
cd "$P" || exit 1
source haienv py312-202505 >/dev/null 2>&1
command -v python >/dev/null || { echo "haienv python missing"; exit 1; }
set -u
: "${JUDGE_USER_SK:?no key}"
export JUDGE_USER_SK
B=${B:?batch name}
J=judge-env/scripts
ROWS=${ROWS:-results/master/raw/$B.csv}
OG=results/drb2-score-gpt/$B
OO=results/drb2-score/$B
PAR_GPT=${PAR_GPT:-8}
PAR_OPUS=${PAR_OPUS:-4}
OPUS=${OPUS:-1}       # 0: skip the Opus pass (phase-1 re-judge)
SECOND=${SECOND:-1}   # 0: skip the GPT second pass
EFFORT=${EFFORT:-high}   # calibration 2026-10-08: medium 0.959 two-pass item agreement, high 0.978
mkdir -p "$OG" "$OO"
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
for pid in $(pgrep -f '^[^ ]*python[0-9.]* -u dsec_matrix'); do
  b=$(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null | grep -o -- '--batch [^ ]*' | cut -d' ' -f2)
  if [ -n "$b" ] && [ -f "results/runs/$b/WEB" ]; then log "web batch $b is running; not judging"; exit 1; fi
done
[ -s "$ROWS" ] || { log "no rows file $ROWS"; exit 1; }
N=$(python - "$ROWS" <<'PY'
import csv, sys
print(sum(1 for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")) if r["task"].startswith("drb2_")))
PY
)
FIFTH=$(( (N + 4) / 5 )); TENTH=$(( (N + 9) / 10 ))
log "judging $B: $N reports; GPT-5.5 pass 1 (parallel $PAR_GPT), Opus on $FIFTH, GPT-5.5 pass 2 on $TENTH; scorer $(sha256sum $J/drb2_score_gpt.py | cut -c1-12), tasks $(sha256sum judge-env/data/drb2/repo-src/tasks_and_rubrics.jsonl | cut -c1-12)"
python -u $J/drb2_score_gpt.py --reports results/runs/$B --rows "$ROWS" --out "$OG" --parallel "$PAR_GPT" --repeat 1 --effort "$EFFORT" > results/drb2-score-gpt/$B-pass1.out 2>&1
tail -n 1 results/drb2-score-gpt/$B-pass1.out
# Opus sample (protocol v5.1, change log 09:50Z): the D0 and W-D1-K8 rep-1 reports of 30 seeded-random tasks (so that the
# human check has both sides of a pair Opus-judged), topped up to a fifth of all reports in run-id hash order.
OPUS_IDS=$(python - "$ROWS" "$FIFTH" <<'PY'
import csv, hashlib, random, sys
rows = [r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")) if r["task"].startswith("drb2_")]
tasks = sorted({r["task"] for r in rows}); random.Random(20261008).shuffle(tasks)
want = []
for t in tasks[:30]:
    for g in ("D0", "W-D1-K8"):
        want += [r["id"] for r in rows if r["task"] == t and r.get("group") == g and str(r.get("rep")) == "1"]
seen = set(want)
for r in sorted(rows, key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest()):
    if len(want) >= int(sys.argv[2]): break
    if r["id"] not in seen: want.append(r["id"]); seen.add(r["id"])
print(",".join(want))
PY
)
echo "$OPUS_IDS" | tr "," "\n" > results/drb2-score/$B-opus-ids.txt
[ "$OPUS" = 1 ] && log "Opus sample: $(wc -l < results/drb2-score/$B-opus-ids.txt) reports (pairs of 30 tasks plus hash-order top-up)"
OPUS_PID=""
if [ "$OPUS" = 1 ]; then
  python -u $J/drb2_score.py --reports results/runs/$B --rows "$ROWS" --out "$OO" --parallel "$PAR_OPUS" --ids "$OPUS_IDS" --repeat 1 > results/drb2-score/$B-opus.out 2>&1 &
  OPUS_PID=$!
fi
if [ "$SECOND" = 1 ]; then
  python -u $J/drb2_score_gpt.py --reports results/runs/$B --rows "$ROWS" --out "$OG" --parallel "$PAR_GPT" --limit "$TENTH" --repeat 2 --effort "$EFFORT" > results/drb2-score-gpt/$B-pass2.out 2>&1
  tail -n 1 results/drb2-score-gpt/$B-pass2.out
fi
if [ -n "$OPUS_PID" ]; then wait $OPUS_PID; tail -n 1 results/drb2-score/$B-opus.out; fi
unset JUDGE_USER_SK
date -u +%Y-%m-%dT%H:%M:%SZ > results/drb2-score-gpt/$B-done.txt
log "$B judged"
