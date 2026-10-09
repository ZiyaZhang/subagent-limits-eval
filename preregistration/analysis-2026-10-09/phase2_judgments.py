#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The judgments table of phase 2 and the agreement between judges (protocol v5.1 sections 八 and 十).

judgments.csv: one row per report and rubric item: batch, run id, task, dimension, item (hash and text), the verdict
of GPT-5.5 pass 1, GPT-5.5 pass 2 (a tenth of the reports), Opus (a fifth), the head of GPT-5.5's cited evidence, and
whether the GPT call was marked anomalous. Verdicts are 1 (satisfied), 0 (not), -1 (satisfied only through a blocked
source). The human verdicts of the blind check are joined by human_check_sample.py score, not here.

agreement.md: Cohen's kappa and the agreement on contested items (at least one side says 1) for GPT pass 1 against
pass 2 and for GPT pass 1 against Opus, overall, per dimension and per batch; the report totals of the two judges
(mean, mean signed difference, mean absolute difference, Pearson r). Raw agreement is printed for the record only:
the protocol reports kappa and contested-item agreement.

The script never reads the run table: its output says nothing about cells, so it can be run before unblinding.

Usage: phase2_judgments.py --gpt results/drb2-score-gpt --opus results/drb2-score --batches p2-main,p2-merge,p2-d,p2-o --out results/analysis-phase2-judge
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics as st
from pathlib import Path

DIMS = ("info_recall", "analysis", "presentation")
DIM_ZH = {"info_recall": "信息召回", "analysis": "分析", "presentation": "呈现"}


def kappa(pairs: list):
    n = len(pairs)
    if not n:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    cats = {a for a, _ in pairs} | {b for _, b in pairs}
    pe = sum((sum(1 for a, _ in pairs if a == c) / n) * (sum(1 for _, b in pairs if b == c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else None


def read(path: Path):
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return rec if rec.get("items") else None


def stats(pairs: list) -> dict:
    """pairs: (a, b) verdicts of the same item by two judgements."""
    n = len(pairs)
    contested = [(a, b) for a, b in pairs if a == 1 or b == 1]
    return {"n": n, "raw": sum(a == b for a, b in pairs) / n if n else None, "kappa": kappa(pairs),
            "contested_n": len(contested), "contested": sum(a == b for a, b in contested) / len(contested) if contested else None}


def fmt(x, nd=3) -> str:
    return "-" if x is None else f"{x:.{nd}f}"


def pearson(x: list, y: list):
    if len(x) < 3:
        return None
    mx, my = st.mean(x), st.mean(y)
    sxx, syy = sum((a - mx) ** 2 for a in x), sum((b - my) ** 2 for b in y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gpt", type=Path, required=True)
    ap.add_argument("--opus", type=Path, required=True)
    ap.add_argument("--batches", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rows, per_batch = [], {}
    pair_r2, pair_op = {}, {}       # (batch, dim) -> [(gpt1, other)]
    tot_r2, tot_op = [], []         # (gpt1 total, other total)
    for b in [x for x in a.batches.split(",") if x]:
        n = {"reports": 0, "no_score": 0, "r2": 0, "opus": 0, "anomalous": 0, "items": 0}
        for f in sorted((a.gpt / b).glob("*.r1.json")):
            rid = f.name[:-len(".r1.json")]
            g1 = read(f)
            if g1 is None:
                n["no_score"] += 1
                continue
            n["reports"] += 1
            g2, op = read(a.gpt / b / f"{rid}.r2.json"), read(a.opus / b / f"{rid}.r1.json")
            anomalous = int(bool((g1.get("llm") or {}).get("anomalous")))
            n["anomalous"] += anomalous
            i2 = {it["rubric_item"]: it["score"] for it in (g2 or {}).get("items") or []}
            io = {it["rubric_item"]: it["score"] for it in (op or {}).get("items") or []}
            n["r2"] += bool(g2)
            n["opus"] += bool(op)
            if g2 and g2.get("total") is not None and g1.get("total") is not None:
                tot_r2.append((g1["total"], g2["total"]))
            if op and op.get("total") is not None and g1.get("total") is not None:
                tot_op.append((g1["total"], op["total"]))
            for it in g1["items"]:
                key = it["rubric_item"]
                n["items"] += 1
                rows.append({"batch": b, "id": rid, "task": g1.get("task", ""), "dim": it.get("dim", ""),
                             "item": hashlib.sha1(key.encode("utf-8")).hexdigest()[:10], "gpt_r1": it["score"], "gpt_r2": i2.get(key, ""),
                             "opus_r1": io.get(key, ""), "gpt_anomalous": anomalous, "gpt_evidence_head": (it.get("evidence") or "")[:160].replace("\n", " "),
                             "item_text": key.replace("\n", " ")})
                if key in i2:
                    pair_r2.setdefault((b, it.get("dim", "")), []).append((it["score"], i2[key]))
                if key in io:
                    pair_op.setdefault((b, it.get("dim", "")), []).append((it["score"], io[key]))
        per_batch[b] = n
    if not rows:
        raise SystemExit("no judged report found")
    with open(a.out / "judgments.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    md = ["# 判分一致性（第二阶段，脚本生成，不含任何格别信息）", "", "| 批 | 判了分的报告 | 没出分 | 评分项 | GPT-5.5 第二遍 | Opus | GPT 用量异常 |", "|---|---|---|---|---|---|---|"]
    for b, n in per_batch.items():
        md.append(f"| {b} | {n['reports']} | {n['no_score']} | {n['items']} | {n['r2']} | {n['opus']} | {n['anomalous']} |")
    share = lambda v: sum(1 for r in rows if r["gpt_r1"] == v) / len(rows)  # noqa: E731
    md += ["", f"GPT-5.5 第一遍的判定分布：满足 {100 * share(1):.1f}%，不满足 {100 * share(0):.1f}%，只靠禁用来源才满足 {100 * share(-1):.2f}%。", ""]
    for title, pairs, tots in (("GPT-5.5 两遍之间（自身一致）", pair_r2, tot_r2), ("GPT-5.5 第一遍对 Opus（跨厂商）", pair_op, tot_op)):
        md += [f"## {title}", "", "| 范围 | 评分项 | kappa | 有争议条目上的一致率（条数） | 原始一致率（只作记录） |", "|---|---|---|---|---|"]
        every = [p for v in pairs.values() for p in v]
        if not every:
            md += ["| 全部 | 0 | - | - | - |", ""]
            continue
        s = stats(every)
        md.append(f"| 全部 | {s['n']} | {fmt(s['kappa'])} | {fmt(s['contested'])}（{s['contested_n']}） | {fmt(s['raw'])} |")
        for d in DIMS:
            sel = [p for (b, dd), v in pairs.items() if dd == d for p in v]
            if sel:
                s = stats(sel)
                md.append(f"| {DIM_ZH[d]} | {s['n']} | {fmt(s['kappa'])} | {fmt(s['contested'])}（{s['contested_n']}） | {fmt(s['raw'])} |")
        for b in per_batch:
            sel = [p for (bb, _), v in pairs.items() if bb == b for p in v]
            if sel:
                s = stats(sel)
                md.append(f"| 批 {b} | {s['n']} | {fmt(s['kappa'])} | {fmt(s['contested'])}（{s['contested_n']}） | {fmt(s['raw'])} |")
        if tots:
            x, y = [t[0] for t in tots], [t[1] for t in tots]
            d = [q - p for p, q in tots]
            md += ["", f"报告总分（{len(tots)} 份）：GPT-5.5 第一遍均值 {st.mean(x):.1f}，另一方均值 {st.mean(y):.1f}；另一方减 GPT 第一遍 {st.mean(d):+.2f} 分，"
                   f"差的绝对值均值 {st.mean(abs(v) for v in d):.2f} 分，相关系数 {fmt(pearson(x, y), 3)}。", ""]
    (a.out / "agreement.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"\nwritten: {a.out / 'judgments.csv'} ({len(rows)} rows), {a.out / 'agreement.md'}")


if __name__ == "__main__":
    main()
