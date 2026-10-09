#!/bin/bash
# Mac side of the phase-2 results: fetch what phase2-post.sh wrote on the dev box, draw the figures, render them.
# Usage: bash scripts/phase2-pull-figs.sh [analysis-phase2 | analysis-phase2-blind]
set -eu
cd "$(dirname "$0")/.."
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
A=${1:-analysis-phase2}
M=master-p2; [ "$A" = analysis-phase2-blind ] && M=master-p2-blind
mkdir -p "results/$A" "results/$M"
scp -q "dev-cpu-hg:$P/results/$A/*" "results/$A/"
scp -q "dev-cpu-hg:$P/results/$M/runs.csv" "dev-cpu-hg:$P/results/$M/columns.md" "results/$M/" 2>/dev/null || true
for f in phase2-post.log; do scp -q "dev-cpu-hg:$P/results/$f" "results/$A/" 2>/dev/null || true; done
scp -q "dev-cpu-hg:$P/results/analysis-p2-*-balance.md" "results/$A/" 2>/dev/null || true
[ "$A" = analysis-phase2 ] && scp -q -r "dev-cpu-hg:$P/results/analysis-phase2-judge" results/ 2>/dev/null || true
python3 scripts/phase2_figures.py --in "results/$A"
bash scripts/render-brief.sh "results/$A/figs"
ls "results/$A"
