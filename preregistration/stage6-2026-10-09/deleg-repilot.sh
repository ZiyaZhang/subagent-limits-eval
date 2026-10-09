#!/bin/bash
# Second pilot of the re-delegation classification, on the same 40 units as the first, after the change of
# 2026-10-09 to how a child task is shown (repeated passages folded). The first pilot's labels are kept.
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
cd "$P" || exit 1
source haienv py312-202505 >/dev/null 2>&1
: "${JUDGE_USER_SK:?no key}"
export JUDGE_USER_SK PYTHONDONTWRITEBYTECODE=1
J=judge-env/scripts
D=results/delegation/p2-main
[ -e $D/labels.pilot-v1.csv ] || { cp -p $D/labels.csv $D/labels.pilot-v1.csv; cp -rp $D/labels $D/labels.pilot-v1; cp -rp $D/replies $D/replies.pilot-v1; }
IDS=$(python - "$D/labels.pilot-v1.csv" <<'PY'
import csv, sys
print(",".join(sorted({r["unit"] for r in csv.DictReader(open(sys.argv[1], encoding="utf-8"))})))
PY
)
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] second pilot on $(echo "$IDS" | tr ',' '\n' | wc -l) units"
PYTHONPATH=$P/$J python -u $J/delegation_classify.py annotate $D --ids "$IDS" --force --parallel "${PARA:-2}" > results/delegation-p2-main-pilot2.txt 2>&1
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] exit $?: $(tail -n 1 results/delegation-p2-main-pilot2.txt | cut -c1-160)"
unset JUDGE_USER_SK
echo DELEG-REPILOT-END
