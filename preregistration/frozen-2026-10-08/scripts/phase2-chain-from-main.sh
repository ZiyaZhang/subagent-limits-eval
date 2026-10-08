#!/bin/bash
# RESTART variant of phase2-chain.sh: starts at stage 3 (main) and runs stages 3-8 unchanged; the runner skips cells
# already in results/runs/<batch>/manifest.jsonl, so a batch that stopped half-way resumes. PAR=<n> sets the main batch's
# parallel (default: the gate's decision in results/phase2-gate.txt). Start like phase2-chain.sh:
#   ... DSEC_KEY="\$K" PAR=26 setsid nohup bash phase2-chain-from-main.sh > results/phase2-chain-from-main.out 2>&1 < /dev/null & ...
# The whole second phase on the dev box in one go (protocol v5.1, timeline section 十一), started once from the Mac:
#   security find-generic-password -s dsllm-usersk -a zhangziya -w | ssh dev-cpu-hg \
#     "cd $P; read -r K; DSEC_KEY=\"\$K\" setsid nohup bash phase2-chain.sh > results/phase2-chain.out 2>&1 < /dev/null & unset K"
# Stages (results/phase2-chain.stage holds the current one; results/phase2-chain-FAILED.txt the reason when it stops):
#   0 wait     the web smoke p2-smoke (already running) finishes
#   1 pilots   p2-smoke-d (v4-pro, 5 runs); p2-calib (32 runs at parallel 32 = the load test)
#   2 gates    phase2_check.py on the three pilots; phase2_gate.py (sentence targets, load -> parallel for main)
#   3 main     p2-main (1,784 runs, block = task x repeat)
#   4 merge    build_merge_tasks_drb2.py from p2-main's D0 reports; p2-merge (40 runs)
#   5 d        p2-d (v4-pro, 180 runs)
#   6 judge+f  judging of p2-main, p2-merge, p2-d and the phase-1 re-judge (background), while module F runs:
#              p2-smoke-f64 decides 64 vs 32 GB for the large coding task, then p2-f, then the graders
#   7 checks   judge length bias and false facts (about 40 judge calls each); the blind human-check sample
#   8 done     results/phase2-chain-DONE.txt
# The key lives only in this process's environment. Every batch goes through phase2-run.v2.sh (one batch at a time;
# a web batch never while judging runs); judging and module F overlap by design (F does not use the web).
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
cd "$P" || exit 1
source haienv py312-202505 >/dev/null 2>&1
command -v python >/dev/null || { echo "haienv python missing"; exit 1; }
set -u
KEY="${DSEC_KEY:?no key}"
unset DSEC_KEY
export PYTHONPATH=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-py/1.21.2
J=judge-env/scripts
L=results/phase2-chain.log
rm -f results/phase2-chain-FAILED.txt results/phase2-chain-DONE.txt
PAR=${PAR:-$(grep "^PAR=" results/phase2-gate.txt | tail -n 1 | cut -d= -f2)}
[ -n "$PAR" ] || { echo "no PAR"; exit 1; }
log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$L"; }
stage() { echo "$1" > results/phase2-chain.stage; log "== stage $1"; }
fail() { log "FAILED at stage $(cat results/phase2-chain.stage): $*"; echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) stage $(cat results/phase2-chain.stage): $*" > results/phase2-chain-FAILED.txt; exit 1; }
run() {  # run <mode> [parallel] [CODE_TASKS]: one batch through phase2-run.v2.sh; returns 0 when its done marker exists
  local mode=$1 par=${2:-} ct=${3:-}
  local b
  case "$mode" in smoke-d) b=p2-smoke-d;; calib) b=p2-calib;; main) b=p2-main;; merge) b=p2-merge;; d) b=p2-d;; f) b=p2-f;; smoke-f64) b=p2-smoke-f64;; *) b=p2-$mode;; esac
  rm -f "results/phase2-$b-done.txt"
  if [ -n "$par" ] && [ -n "$ct" ]; then DSEC_KEY="$KEY" MODE="$mode" PAR="$par" CODE_TASKS="$ct" bash phase2-run.v2.sh > "results/$b.out" 2>&1
  elif [ -n "$par" ]; then DSEC_KEY="$KEY" MODE="$mode" PAR="$par" bash phase2-run.v2.sh > "results/$b.out" 2>&1
  elif [ -n "$ct" ]; then DSEC_KEY="$KEY" MODE="$mode" CODE_TASKS="$ct" bash phase2-run.v2.sh > "results/$b.out" 2>&1
  else DSEC_KEY="$KEY" MODE="$mode" bash phase2-run.v2.sh > "results/$b.out" 2>&1; fi
  [ -f "results/phase2-$b-done.txt" ]
}

log "phase2-chain-from-main start (pid $$); parallel $PAR; runner $(sha256sum dsec_matrix_v6.py | cut -c1-16); sentences $(sha256sum tasks/phase2-sentences.json | cut -c1-16)"
stage 3-main
run main "$PAR" || fail "p2-main did not finish (see results/p2-main.out)"
log "p2-main: $(tail -n 1 results/runs/p2-main/run.log)"

stage 4-merge
python $J/build_merge_tasks_drb2.py --batch p2-main > results/phase2-merge-build.txt 2>&1 || fail "merge tasks (results/phase2-merge-build.txt)"
tail -n 2 results/phase2-merge-build.txt | tee -a "$L"
run merge || fail "p2-merge did not finish (see results/p2-merge.out)"

stage 5-d
run d || fail "p2-d did not finish (see results/p2-d.out)"

stage 6-judge-and-f
( JUDGE_USER_SK="$KEY" bash -c '
    for b in p2-main p2-merge p2-d; do B=$b bash drb2-judge-gpt.sh; done
    for b in drb2-h1 drb2-kd drb2-k4; do B=$b ROWS=results/analysis-$b/rows-all.csv OPUS=0 SECOND=0 bash drb2-judge-gpt.sh; done
    echo JUDGE-CHAIN-END' ) > results/phase2-judge-chain.out 2>&1 &
JPID=$!
log "judging started in the background (pid $JPID)"
CODE_TASKS=tasks/phase2-code-tasks.jsonl
if run smoke-f64 1 && python - <<'PY'
import json
line = [json.loads(l) for l in open("results/runs/p2-smoke-f64/manifest.jsonl") if l.strip()]
ok = len(line) == 1 and line[0].get("exit") is not None and not line[0].get("infra_signal")
raise SystemExit(0 if ok else 1)
PY
then CODE_TASKS=tasks/phase2-code-tasks-64g.jsonl; log "64 GB container works for the large coding task; module F uses it"
else log "64 GB test failed or did not finish; module F keeps 32 GB"; fi
run f "" "$CODE_TASKS" || fail "p2-f did not finish (see results/p2-f.out)"
TK=judge-env/_private/toolkit-xl
python -u $J/dsec_grade_proj.py --task toolkit-xl --template judge-env/data/proj/toolkit-xl-build/template --reference $TK/reference --tests $TK/tests --out results/grade/p2-f results/runs/p2-f > results/phase2-grade-xl.txt 2>&1 && log "xl graded: $(tail -n 1 results/phase2-grade-xl.txt)" || log "xl grading FAILED (results/phase2-grade-xl.txt)"
python -u $J/dsec_grade_px.py --env judge-env --task pw-exercises-free --template judge-env/data/code-templates/pwide-python --archive judge-env/_private/pwide-python-full-tests.tar.gz --out results/grade/p2-f-free results/runs/p2-f > results/phase2-grade-free.txt 2>&1 && log "free24 graded: $(grep -E 'graded|reference_all_pass' results/phase2-grade-free.txt | tail -n 2 | tr '\n' ' ')" || log "free24 grading FAILED (results/phase2-grade-free.txt)"
python - > results/grade/p2-f-chain.jsonl 2> results/phase2-grade-chain.err <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, "judge-env/scripts")
import build_chain
for rp in sorted(Path("results/runs/p2-f").glob("*/result.json")):
    res = json.loads(rp.read_text())
    if res.get("task") != "n1-chain16":
        continue
    build_chain.NAME = "chain16"
    try:
        sc = build_chain.score(rp.parent / "workspace")
    except Exception as e:  # noqa: BLE001
        sc = {"error": f"{type(e).__name__}: {e}"}
    print(json.dumps({"id": res["id"], "task": res["task"], "group": res["group"], "rep": res["rep"], **sc}, ensure_ascii=False))
PY
log "chain16 scored: $(wc -l < results/grade/p2-f-chain.jsonl) runs"
wait $JPID
log "judging finished: $(tail -n 1 results/phase2-judge-chain.out)"

stage 7-checks
python $J/judge_length_bias.py make --reports results/runs/p2-main --rows results/master/raw/p2-main.csv --n 20 --out results/sens-length > results/sens-length.out 2>&1 || log "length-bias make FAILED"
JUDGE_USER_SK="$KEY" python -u $J/drb2_score_gpt.py --reports results/sens-length --rows results/sens-length/manifest.csv --out results/drb2-score-gpt/sens-length --parallel 8 >> results/sens-length.out 2>&1
python $J/judge_length_bias.py compare --orig results/drb2-score-gpt/p2-main --padded results/drb2-score-gpt/sens-length --manifest results/sens-length/manifest.csv > results/sens-length-compare.txt 2>&1 && log "length bias: $(head -n 3 results/sens-length-compare.txt | tr '\n' ' ')"
python $J/judge_false_facts.py make --reports results/runs/p2-main --rows results/master/raw/p2-main.csv --n 20 --scores results/drb2-score-gpt/p2-main --tasks judge-env/data/drb2/repo-src/tasks_and_rubrics.jsonl --out results/sens-false > results/sens-false.out 2>&1 || log "false-facts make FAILED"
JUDGE_USER_SK="$KEY" python -u $J/drb2_score_gpt.py --reports results/sens-false --rows results/sens-false/rows.csv --out results/drb2-score-gpt/sens-false --parallel 8 >> results/sens-false.out 2>&1
python $J/judge_false_facts.py compare --orig results/drb2-score-gpt/p2-main --modified results/drb2-score-gpt/sens-false --manifest results/sens-false/manifest.json > results/sens-false-compare.txt 2>&1 && log "false facts: $(head -n 3 results/sens-false-compare.txt | tr '\n' ' ')"
python $J/human_check_sample.py make --gpt results/drb2-score-gpt/p2-main --opus results/drb2-score/p2-main --runs results/master/raw/p2-main.csv --reports results/runs/p2-main --out results/human-check --seed 20261008 > results/human-check.out 2>&1 && log "human-check sample: $(tail -n 3 results/human-check.out | tr '\n' ' ')" || log "human-check sample FAILED (results/human-check.out)"
unset KEY

stage 8-done
date -u +%Y-%m-%dT%H:%M:%SZ > results/phase2-chain-DONE.txt
log "phase2-chain done"
