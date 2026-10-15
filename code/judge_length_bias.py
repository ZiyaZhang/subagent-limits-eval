#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Length-bias check of the DRB II judge (protocol v5.1 section 八: 20 reports each get 30% irrelevant-but-true text
added and are judged again; does the pass rate move?).

`make` writes a padded copy of each chosen report under <out>/<run id>/workspace/report.md, so that drb2_score_gpt.py
can judge the copies with --reports <out> --rows <out>/manifest.csv (manifest.csv has id and task). The filler is a
bank of generic Chinese paragraphs (how a research report is organised, how sources were handled, reading guidance,
a restatement of the scope that names only the report's own title) that assert no fact about the subject and so
can satisfy no rubric item; it is cut into 5 chunks inserted at 5 evenly spaced section boundaries (before a heading;
paragraph boundaries when the report has too few headings; never inside a code fence or a table). The original
text is never changed: the script checks that removing the inserted chunks gives the original back, byte for byte.
Filler length = 30% of the original character count (the manifest records the exact ratio). The chunk order is
seeded by the run id, so two reports do not get the same text in the same order.

`compare` reads the judgements of the originals and of the padded copies (<dir>/<run id>.r<k>.json as written by
drb2_score_gpt.py or drb2_score.py) and prints: per report total before / after, the mean difference with a
paired-t 95% interval, and the item flips (0->1, 1->0, flips involving -1) overall and per dimension.

Usage:
  judge_length_bias.py make --reports results/runs/<batch> --rows results/master/raw/<batch>.csv --n 20 \
      --out results/drb2-length-bias/<batch>            [--ids a,b,...] [--share 0.30] [--points 5]
  drb2_score_gpt.py --reports results/drb2-length-bias/<batch> --rows results/drb2-length-bias/<batch>/manifest.csv \
      --out results/drb2-score-gpt/<batch>-padded
  judge_length_bias.py compare --orig results/drb2-score-gpt/<batch> --padded results/drb2-score-gpt/<batch>-padded \
      [--manifest results/drb2-length-bias/<batch>/manifest.csv] [--rep 1]
Reads and writes files only; no API call.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics as st
import sys
from pathlib import Path

DIMS = ("info_recall", "analysis", "presentation")
HEADING = re.compile(r"^#{1,6}\s")
FENCE = re.compile(r"^\s*(```|~~~)")

# Generic sentences: nothing here states a fact about any subject. {topic} is the report's own title (its first
# heading), so the text sounds like it belongs to the report without saying anything a rubric item could ask for.
BANK = [
    "本报告的撰写遵循先界定范围、再梳理材料、最后归纳结论的顺序，各节之间的先后关系以题目给定的结构为准。",
    "在整理材料时，本报告区分了一手来源与二手转述，对转述内容尽量回到原始出处核对，无法核对的表述在正文中不作为依据。",
    "围绕《{topic}》这一主题，本报告将讨论限定在题目要求的对象与时间范围之内，不向题目未要求的方向扩展。",
    "为便于阅读，各节开头先说明本节要回答的问题，节末对要点作简短小结，读者可按需跳读。",
    "研究报告通常由背景、方法、发现、讨论与结论几部分构成，本报告的编排也大体沿用这一惯例，并按题目的编号要求细分子节。",
    "需要说明的是，同一指标在不同来源中可能采用不同的统计口径，本报告在引用时尽量注明口径，避免把口径不同的数字直接相减或相比。",
    "本报告在引用数据时优先采用官方统计或原始文献中的表述，对二手整理的数字只作参考，不单独作为结论依据。",
    "关于材料的时效，本报告以题目限定的时间范围为准；超出该范围的进展只在必要处简要提及，不展开分析。",
    "各节的篇幅并不代表其重要性，篇幅较长的部分多是因为需要逐项回应题目列出的具体要求。",
    "本报告中的表格用于汇总正文已经说明的内容，表格本身不引入正文未曾出现的新信息。",
    "在术语使用上，本报告沿用题目和主要来源中的既有名称，不另起新译名，首次出现时给出原文或说明。",
    "就《{topic}》而言，题目所要求的各项内容已按原有编号在相应小节中逐一回应，未作合并或省略。",
    "阅读时请注意，本报告的归纳与比较是在题目给定框架内进行的，并不意味着对框架之外的其他分析路径有所评价。",
    "本报告的材料整理过程包括三步：先按题目的要求列出需要回答的问题清单，再逐项检索与核对，最后把核对后的内容组织成文。",
    "对于来源之间存在分歧的问题，本报告在正文中并列给出各方说法并注明出处，不替读者作取舍。",
    "本节内容与前后各节相互衔接，前文已经说明的定义和口径在此不再重复，读者可回看相应小节。",
    "为避免遗漏，本报告在定稿前按题目的要求逐条对照检查了一遍，确认每项要求都有对应的段落回应。",
    "研究报告的结论部分通常只概括正文已经论证的内容，不再引入新的材料，本报告亦遵循这一做法。",
    "关于引用格式，本报告在正文中给出来源名称，便于读者按名称回溯；同一来源多次引用时沿用同一名称。",
    "本报告不对题目范围之外的政策取向或投资选择提出建议，所有讨论都限定在题目要求的分析范围内。",
    "在组织材料时，本报告把描述性内容与分析性内容分开编排，先交代情况，再作比较与讨论。",
    "《{topic}》涉及的材料来源较为分散，本报告在归纳时尽量保留原始表述，对合并后的说法注明是本报告的归纳。",
    "阅读本报告的各节时，建议先看节首的问题说明，再看正文的分项回应，最后看节末小结，这样更容易把握各节的要点。",
    "本报告的结构以题目要求为纲：题目分几部分，本报告就分几部分；题目在某部分列出几点，本报告就在该部分回应几点。",
    "凡正文中标注“待核实”的内容，表示本报告未能找到可靠出处，读者在引用时请自行核对。",
    "本报告中出现的比较与排序，均以正文已经列出的材料为依据，没有列出的项目不参与比较。",
    "在写作上，本报告尽量用完整的句子陈述事实，用表格汇总对比，用小结归纳要点，避免只列关键词而不作说明。",
    "本报告的各项内容按题目规定的顺序排列，个别小节为叙述连贯略作调整时，在小节标题中保留了题目的原编号。",
    "就本报告的方法而言，它属于基于公开材料的文献整理与比较，不包含实地调研或访谈，相关结论的适用范围以此为限。",
    "本报告在定稿时统一了数字格式与单位写法，正文中同一指标的单位在各处保持一致。",
]
MIN_SENT = min(len(s) for s in BANK)


def blocks_of(text: str) -> list:
    """Split a markdown text into blocks: (start offset, end offset, first line). A block is a run of non-blank
    lines, a whole fenced code block, or a heading line; blank lines separate blocks. Offsets index `text`."""
    out, pos, cur_start, in_fence, first = [], 0, None, False, ""
    for line in text.splitlines(keepends=True):
        bare = line.rstrip("\r\n")
        if in_fence:
            if FENCE.match(bare):
                in_fence = False
            pos += len(line)
            continue
        if FENCE.match(bare):
            if cur_start is not None:
                out.append((cur_start, pos, first))
            cur_start, first, in_fence = pos, bare, True
            pos += len(line)
            continue
        if not bare.strip():
            if cur_start is not None:
                out.append((cur_start, pos, first))
                cur_start = None
        elif HEADING.match(bare):
            if cur_start is not None:
                out.append((cur_start, pos, first))
            cur_start, first = pos, bare
        elif cur_start is None:
            cur_start, first = pos, bare
        pos += len(line)
    if cur_start is not None:
        out.append((cur_start, pos, first))
    return out


def insertion_points(text: str, n: int) -> list:
    """n block starts, evenly spaced over the text: section boundaries (block starts that are headings, except the
    first block) when there are enough of them, else all block starts except the first."""
    blocks = blocks_of(text)
    heads = [b[0] for b in blocks[1:] if HEADING.match(b[2])]
    cands = heads if len(heads) >= n else [b[0] for b in blocks[1:]]
    if not cands:
        return [len(text)]
    chosen = []
    for k in range(1, n + 1):
        target = len(text) * k / (n + 1)
        free = [c for c in cands if c not in chosen]
        if not free:
            break
        chosen.append(min(free, key=lambda c: abs(c - target)))
    return sorted(chosen)


def filler_text(budget: int, seed: str, topic: str) -> str:
    """Generic paragraphs of about `budget` characters, sentences taken from BANK in a seeded cyclic order."""
    h = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)
    start = h % len(BANK)
    order = BANK[start:] + BANK[:start]
    sents, used = [], 0
    i = 0
    if budget < MIN_SENT // 2:  # a chunk too small for half a sentence gets nothing (tiny reports only)
        return ""
    while used < budget:
        s = order[i % len(order)].format(topic=topic)
        if used + len(s) > budget and sents:
            # the last sentence: the one from the bank that best fits the remaining budget
            rest = budget - used
            best = min((t.format(topic=topic) for t in BANK), key=lambda t: abs(len(t) - rest))
            if abs(len(best) - rest) < rest:
                sents.append(best)
                used += len(best)
            break
        sents.append(s)
        used += len(s)
        i += 1
    paras, per = [], 3 + (h >> 8) % 2
    for j in range(0, len(sents), per):
        paras.append("".join(sents[j:j + per]))
    return "\n\n".join(paras)


def pad_report(text: str, share: float, points: int, seed: str) -> tuple:
    """The padded text and the inserted chunks. Chunks go in at `points` evenly spaced block starts."""
    m = re.search(r"^#\s+(.+?)\s*$", text, re.M)
    topic = m.group(1).strip("*# ") if m else "本题"
    offs = insertion_points(text, points)
    budget = int(round(len(text) * share))
    chunks = []
    for k, off in enumerate(offs):
        b = budget // len(offs) + (1 if k < budget % len(offs) else 0)
        chunk = filler_text(b, f"{seed}:{k}", topic)
        if chunk:
            chunks.append((off, chunk))
    offs = [off for off, _ in chunks]
    out, last, inserted = [], 0, []
    for off, chunk in chunks:
        out.append(text[last:off])
        before = "".join(out)
        lead = "" if (not before or before.endswith("\n\n")) else ("\n" if before.endswith("\n") else "\n\n")
        trail = "\n\n" if off < len(text) else "\n"
        seg = lead + chunk + trail
        out.append(seg)
        inserted.append(seg)
        last = off
    out.append(text[last:])
    padded = "".join(out)
    check = padded
    for seg in inserted:
        check = check.replace(seg, "", 1)
    if check != text:
        raise RuntimeError("the padded text does not contain the original text unchanged")
    return padded, chunks, offs


def pick_rows(a) -> list:
    """The reports to pad: id and task from --rows (hash order, --n of them) or --ids (task from --rows or the run's
    result.json)."""
    rows = []
    if a.rows:
        rows = [{"id": r["id"], "task": r["task"]} for r in csv.DictReader(open(a.rows, encoding="utf-8"))
                if r["task"].startswith("drb2_") and r.get("incomplete") != "1"]
    want = [x for x in a.ids.split(",") if x]
    if want:
        by = {r["id"]: r for r in rows}
        out = []
        for rid in want:
            if rid in by:
                out.append(by[rid])
                continue
            rj = a.reports / rid / "result.json"
            if rj.exists():
                out.append({"id": rid, "task": json.loads(rj.read_text(encoding="utf-8")).get("task", "")})
            else:
                sys.exit(f"{rid}: not in --rows and no result.json under --reports; cannot tell its task")
        return out
    if not rows:
        sys.exit("give --ids or --rows")
    rows = sorted(rows, key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())
    out = []
    for r in rows:
        if (a.reports / r["id"] / "workspace" / "report.md").exists():
            out.append(r)
        if len(out) >= a.n:
            break
    return out


def cmd_make(a) -> None:
    rows = pick_rows(a)
    a.out.mkdir(parents=True, exist_ok=True)
    man = []
    for r in rows:
        f = a.reports / r["id"] / "workspace" / "report.md"
        if not f.exists():
            print(f"{r['id']}: no report.md; skipped")
            continue
        text = f.read_text(encoding="utf-8")
        padded, chunks, offs = pad_report(text, a.share, a.points, r["id"])
        d = a.out / r["id"] / "workspace"
        d.mkdir(parents=True, exist_ok=True)
        (d / "report.md").write_text(padded, encoding="utf-8")
        filler = sum(len(c) for _, c in chunks)
        man.append({"id": r["id"], "task": r["task"], "original_chars": len(text), "padded_chars": len(padded),
                    "filler_chars": filler, "ratio": round(len(padded) / len(text), 4), "points": len(offs),
                    "insert_offsets": " ".join(str(o) for o in offs)})
        print(f"{r['id']} {r['task']} {len(text)} -> {len(padded)} chars (x{len(padded) / len(text):.3f}), {len(offs)} insert points")
    if not man:
        sys.exit("nothing padded")
    with open(a.out / "manifest.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(man[0].keys()))
        w.writeheader()
        w.writerows(man)
    print(f"{len(man)} padded reports under {a.out}; manifest {a.out / 'manifest.csv'} (use it as --rows for the judge)")


def load_scores(d: Path, rep: int) -> dict:
    out = {}
    for p in sorted(d.glob(f"*.r{rep}.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("total") is not None:
            out[rec["id"]] = rec
    return out


def t_quantile(df: int, conf: float = 0.95) -> float:
    try:
        from scipy import stats as sps
        return float(sps.t.ppf(0.5 + conf / 2, df))
    except ImportError:
        from statistics import NormalDist
        return NormalDist().inv_cdf(0.5 + conf / 2)


def paired_line(diffs: list, label: str, unit: str = "") -> None:
    n = len(diffs)
    if n < 2:
        print(f"{label}: n={n}, no interval")
        return
    m, sd = st.mean(diffs), st.stdev(diffs)
    q = t_quantile(n - 1)
    half = q * sd / math.sqrt(n)
    print(f"{label}: n={n} mean {m:+.2f}{unit} [{m - half:+.2f}, {m + half:+.2f}] (paired t 95%), sd {sd:.2f}, "
          f"up {sum(1 for d in diffs if d > 0)} / same {sum(1 for d in diffs if d == 0)} / down {sum(1 for d in diffs if d < 0)}")


def flip_key(x: int, y: int) -> str:
    if x == y:
        return "same"
    if x == 0 and y == 1:
        return "0->1"
    if x == 1 and y == 0:
        return "1->0"
    return f"{x}->{y}"


def cmd_compare(a) -> None:
    o, p = load_scores(a.orig, a.rep), load_scores(a.padded, a.rep)
    ids = sorted(set(o) & set(p))
    if a.manifest and a.manifest.exists():
        man = [r["id"] for r in csv.DictReader(open(a.manifest, encoding="utf-8"))]
        missing = [x for x in man if x not in o or x not in p]
        ids = [x for x in man if x in o and x in p]
        if missing:
            print(f"{len(missing)} manifest ids without both judgements: {' '.join(missing)}")
    if not ids:
        sys.exit("no report has both judgements")
    print(f"{'id':12s} {'task':12s} {'orig':>7s} {'padded':>7s} {'diff':>7s} {'0->1':>5s} {'1->0':>5s} {'other':>5s}  {'chars orig->padded'}")
    diffs, dim_diffs, flips, dim_flips = [], {d: [] for d in DIMS}, {}, {d: {} for d in DIMS}
    for rid in ids:
        x, y = o[rid], p[rid]
        ix = {it["rubric_item"]: it for it in x["items"]}
        iy = {it["rubric_item"]: it for it in y["items"]}
        keys = [k for k in ix if k in iy]
        f = {}
        for k in keys:
            fk = flip_key(ix[k]["score"], iy[k]["score"])
            f[fk] = f.get(fk, 0) + 1
            flips[fk] = flips.get(fk, 0) + 1
            dd = dim_flips[ix[k]["dim"]]
            dd[fk] = dd.get(fk, 0) + 1
        diffs.append(y["total"] - x["total"])
        for d in DIMS:
            sx, sy = (x["dims"].get(d) or {}).get("score"), (y["dims"].get(d) or {}).get("score")
            if sx is not None and sy is not None:
                dim_diffs[d].append(sy - sx)
        other = sum(v for k, v in f.items() if k not in ("same", "0->1", "1->0"))
        print(f"{rid:12s} {x.get('task', ''):12s} {x['total']:7.2f} {y['total']:7.2f} {y['total'] - x['total']:+7.2f} "
              f"{f.get('0->1', 0):5d} {f.get('1->0', 0):5d} {other:5d}  {x.get('chars')}->{y.get('chars')}")
    print()
    paired_line(diffs, "total (padded - original)", " pts")
    for d in DIMS:
        paired_line(dim_diffs[d], f"  {d}", " pts")
    n_items = sum(flips.values())
    print(f"\nitem flips over {n_items} judged items: " + ", ".join(f"{k} {v}" for k, v in sorted(flips.items(), key=lambda kv: -kv[1])))
    for d in DIMS:
        dd = dim_flips[d]
        tot = sum(dd.values())
        if tot:
            print(f"  {d:13s} n={tot:5d}  0->1 {dd.get('0->1', 0)} ({100 * dd.get('0->1', 0) / tot:.1f}%)  1->0 {dd.get('1->0', 0)} "
                  f"({100 * dd.get('1->0', 0) / tot:.1f}%)  other {sum(v for k, v in dd.items() if k not in ('same', '0->1', '1->0'))}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make", help="write padded copies of the chosen reports")
    m.add_argument("--reports", type=Path, required=True, help="dir of runs: <id>/workspace/report.md")
    m.add_argument("--rows", type=Path, help="CSV with id, task (drb2_zh_NNN)[, incomplete]")
    m.add_argument("--ids", default="", help="comma-separated run ids (else --n of --rows in run-id hash order)")
    m.add_argument("--n", type=int, default=20)
    m.add_argument("--out", type=Path, required=True)
    m.add_argument("--share", type=float, default=0.30, help="filler as a share of the original characters")
    m.add_argument("--points", type=int, default=5, help="insertion points per report")
    m.set_defaults(fn=cmd_make)
    c = sub.add_parser("compare", help="original vs padded judgements")
    c.add_argument("--orig", type=Path, required=True, help="dir of <id>.r<k>.json for the originals")
    c.add_argument("--padded", type=Path, required=True, help="dir of <id>.r<k>.json for the padded copies")
    c.add_argument("--manifest", type=Path, help="manifest.csv of make: restricts and orders the reports")
    c.add_argument("--rep", type=int, default=1, help="judge pass to read (.r<rep>.json)")
    c.set_defaults(fn=cmd_compare)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
