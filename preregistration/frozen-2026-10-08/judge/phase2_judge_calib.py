#!/usr/bin/env python3
"""GPT-5.5 judge calibration (protocol v5.1 section 八): two passes over 12 phase-1 reports.

Reads <gpt dir>/<id>.r1.json and .r2.json (drb2_score_gpt.py) and, when present, the phase-1 Opus judgements
<opus dir>/<id>.r1.json (drb2_score.py) of the same reports. Prints:
  - per report: total r1, total r2, |diff|, items, item agreement r1 vs r2, Opus total
  - item-level agreement between the two GPT passes: raw agreement, Cohen's kappa, agreement on items where at least one
    pass says 1 (the contested side), and the same between GPT r1 and Opus r1
  - time per call (median, p90) and tokens per call
The acceptance rule written before the data: item agreement between the two GPT passes >= 0.97 (phase 1 Opus: 0.969-0.988).

Usage: phase2_judge_calib.py --gpt results/drb2-score-gpt/calib-h1 [--opus results/drb2-score/drb2-h1]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path


def kappa(pairs: list) -> float | None:
    n = len(pairs)
    if not n:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    cats = {a for a, _ in pairs} | {b for _, b in pairs}
    pe = sum((sum(1 for a, _ in pairs if a == c) / n) * (sum(1 for _, b in pairs if b == c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else None


def items_of(rec: dict) -> dict:
    return {it["rubric_item"]: it["score"] for it in rec.get("items") or []}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gpt", type=Path, required=True)
    ap.add_argument("--opus", type=Path)
    a = ap.parse_args()
    r1 = {p.name[:-8]: json.loads(p.read_text(encoding="utf-8")) for p in a.gpt.glob("*.r1.json")}
    r2 = {p.name[:-8]: json.loads(p.read_text(encoding="utf-8")) for p in a.gpt.glob("*.r2.json")}
    pairs_gg, pairs_go, secs, toks = [], [], [], []
    print(f"{'id':12s} {'task':12s} {'r1':>6s} {'r2':>6s} {'|d|':>5s} {'items':>5s} {'agree':>6s} {'opus':>6s}")
    for rid, rec in sorted(r1.items()):
        if rec.get("total") is None:
            print(f"{rid:12s} {rec.get('task', ''):12s} no score ({rec.get('note')})")
            continue
        i1 = items_of(rec)
        for c in rec["llm"].get("detail") or []:
            secs.append(c["seconds"])
            toks.append((c["usage"].get("input_tokens") or 0, c["usage"].get("output_tokens") or 0, c["usage"].get("reasoning_tokens") or 0))
        other = r2.get(rid)
        agree = ""
        if other and other.get("total") is not None:
            i2 = items_of(other)
            pp = [(i1[k], i2[k]) for k in i1 if k in i2]
            pairs_gg += pp
            agree = f"{sum(1 for x, y in pp if x == y) / len(pp):.3f}" if pp else ""
            for c in other["llm"].get("detail") or []:
                secs.append(c["seconds"])
        opus = ""
        if a.opus:
            po = a.opus / f"{rid}.r1.json"
            if po.exists():
                orec = json.loads(po.read_text(encoding="utf-8"))
                if orec.get("total") is not None:
                    io = items_of(orec)
                    pairs_go += [(i1[k], io[k]) for k in i1 if k in io]
                    opus = f"{orec['total']:.1f}"
        d = f"{abs(rec['total'] - other['total']):.1f}" if other and other.get("total") is not None else ""
        print(f"{rid:12s} {rec['task']:12s} {rec['total']:6.1f} {(other or {}).get('total', float('nan')):6.1f} {d:>5s} {len(i1):5d} {agree:>6s} {opus:>6s}")
    for name, pairs in (("GPT r1 vs GPT r2", pairs_gg), ("GPT r1 vs Opus r1 (phase 1)", pairs_go)):
        if not pairs:
            continue
        n = len(pairs)
        raw = sum(1 for x, y in pairs if x == y) / n
        contested = [(x, y) for x, y in pairs if x == 1 or y == 1]
        craw = sum(1 for x, y in contested if x == y) / len(contested) if contested else None
        print(f"\n{name}: {n} items, raw agreement {raw:.3f}, kappa {kappa(pairs):.3f}, agreement where either says 1: {craw and round(craw, 3)} ({len(contested)} items)")
        if name.startswith("GPT r1 vs GPT"):
            print(f"  acceptance (>= 0.97 raw agreement): {'PASS' if raw >= 0.97 else 'FAIL'}")
    if secs:
        s = sorted(secs)
        print(f"\ncalls: {len(s)}, seconds per call median {s[len(s) // 2]:.0f}, p90 {s[int(0.9 * len(s)) - 1]:.0f}, max {s[-1]:.0f}")
    if toks:
        print(f"tokens per call: input median {st.median(t[0] for t in toks):.0f}, output median {st.median(t[1] for t in toks):.0f}, reasoning median {st.median(t[2] for t in toks):.0f}")
    totals = [rec["total"] for rec in r1.values() if rec.get("total") is not None]
    if totals:
        print(f"GPT r1 totals: mean {st.mean(totals):.1f}, min {min(totals):.1f}, max {max(totals):.1f}")


if __name__ == "__main__":
    main()
