#!/bin/bash
# Mac side: fetch the blind check forms from the dev box and build one page per form that she fills with the keyboard.
# Usage: bash scripts/phase2-forms.sh            (after MODE=pre of phase2-post.sh on the dev box)
#        bash scripts/phase2-forms.sh push       (after she exported the answers: copies them from ~/Downloads to the dev box)
set -eu
cd "$(dirname "$0")/.."
P=/weka-hg/prod/deepseek/permanent/zhangziya/private/dsec-exp
H=results/human-check
if [ "${1:-}" = push ]; then
  for pair in "answers.csv:$H/answers.csv:results/human-check/answers.csv" "leak-answers.csv:$H/leak/leak-answers.csv:results/human-check/leak/leak-answers.csv"; do
    name=${pair%%:*}; rest=${pair#*:}; loc=${rest%%:*}; rem=${rest#*:}
    src=$(ls -t "$HOME/Downloads/$name" "$HOME"/Downloads/"${name%.csv}"*.csv 2>/dev/null | head -n 1 || true)
    [ -n "$src" ] || { echo "no $name in ~/Downloads yet"; continue; }
    cp "$src" "$loc" && scp -q "$loc" "dev-cpu-hg:$P/$rem" && echo "$name: $(($(wc -l < "$loc") - 1)) rows -> $rem (from $src)"
  done
  exit 0
fi
mkdir -p $H/leak
scp -q "dev-cpu-hg:$P/results/human-check/form.md" "dev-cpu-hg:$P/results/human-check/answer-template.csv" $H/
scp -q "dev-cpu-hg:$P/results/human-check/leak/leak-form.md" "dev-cpu-hg:$P/results/human-check/leak/leak-answers-template.csv" $H/leak/
python3 scripts/label_page.py --form $H/form.md --template $H/answer-template.csv --choices 满足,不满足,拿不准 --save-as answers.csv --out $H/form.html --title "评分项判定核对（$(($(wc -l < $H/answer-template.csv) - 1)) 条）"
python3 scripts/label_page.py --form $H/leak/leak-form.md --template $H/leak/leak-answers-template.csv --choices 没有,有,拿不准 --save-as leak-answers.csv --out $H/leak/leak-form.html --title "解盲前的泄漏人工关"
echo "open: $PWD/$H/form.html and $PWD/$H/leak/leak-form.html"
