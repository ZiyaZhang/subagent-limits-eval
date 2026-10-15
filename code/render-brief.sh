#!/bin/bash
# Render the short report's SVG figures to PNG with headless Chrome (2x device pixels).
# Usage: bash scripts/render-brief.sh [results/analysis-brief]
set -eu
cd "$(dirname "$0")/.."
D=${1:-results/analysis-brief}
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
for svg in "$D"/*.svg; do
  f=${svg%.svg}
  read -r W H < <(/usr/bin/python3 -c "
import re,sys
m=re.search(r'viewBox=\"0 0 (\d+) (\d+)\"', open(sys.argv[1], encoding='utf-8').read()); print(m.group(1), m.group(2))" "$svg")
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 --window-size="$W,$H" \
    --default-background-color=FFFFFFFF --screenshot="$PWD/$f.png" "file://$PWD/$svg" >/dev/null 2>&1
  ls -la "$f.png" | awk '{print $5, $9}'
done
