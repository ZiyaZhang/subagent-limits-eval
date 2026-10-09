#!/bin/bash
# Run the Opus second-judge sample of a batch EARLY, next to the GPT-5.5 first pass, instead of after it. Same sample, same
# command and same parallel as drb2-judge-gpt.sh uses (which runs Opus next to the GPT second pass anyway); when the chain
# reaches its own Opus step every file exists and it returns at once. The key comes in through the environment only.
#   B=p2-main bash opus-early.sh      (JUDGE_USER_SK in the environment)
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
cd "$P" || exit 1
source haienv py312-202505 >/dev/null 2>&1
set -u
: "${JUDGE_USER_SK:?no key}"
export JUDGE_USER_SK
B=${B:?batch}
J=judge-env/scripts
ROWS=results/master/raw/$B.csv
[ -s "$ROWS" ] || { echo "no rows file $ROWS"; exit 1; }
N=$(python - "$ROWS" <<'PY'
import csv, sys
print(sum(1 for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")) if r["task"].startswith("drb2_")))
PY
)
FIFTH=$(( (N + 4) / 5 ))
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
mkdir -p results/drb2-score/$B
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] early Opus sample of $B: $(echo "$OPUS_IDS" | tr ',' '\n' | wc -l) of $N reports, parallel ${PAR_OPUS:-4}"
python -u $J/drb2_score.py --reports results/runs/$B --rows "$ROWS" --out results/drb2-score/$B --parallel "${PAR_OPUS:-4}" --ids "$OPUS_IDS" --repeat 1
unset JUDGE_USER_SK
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] OPUS-EARLY-END $B"
