#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""More context for the entries of the human leak look that were answered 拿不准 (2026-10-11).

The first form showed one example of the 12-word passages a report shares with its task's forbidden source article and
did not show where the article's title occurs. Twelve entries were answered 拿不准 for exactly that reason. For each of
the given entries this writes, still blind (no group, no run id, no score):
  - the shared 12-word shingles merged into whole passages, counted by where they sit in the report: inside a reference
    entry (a list item or table row with a year and a citation mark such as a DOI, a URL, "et al", a journal word) or in
    running text; every running-text passage with its context on both sides (report and source); a few of the
    reference-entry passages as examples
  - every occurrence of the forbidden article's title in the report, with the text around it and the heading it is under
The shingles are computed exactly as drb2_ngram_leak.py does (same normalisation, same body cut, same boilerplate set).
Reads the sealed key only to locate the runs; prints nothing from it.

Usage (experiment directory): leak_supplement.py --key results/human-check/leak/leak-key.json --entries 3,4,5 \\
    --runs results/runs --sources judge-env/data/drb2/sources --index tasks/phase2-drb2-index.json \\
    [--merge-index tasks/phase2-merge-index.json] --out results/human-check/leak-supplement
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import drb2_ngram_leak as ng  # noqa: E402

N = ng.N
CITE = re.compile(r"doi|https?://|www\.|et al|journal|proceedings|conference|transactions|symposium|arxiv|preprint|vol\.|pp\.|ieee|acm |springer|elsevier|wiley|press\b|"
                  r"学报|期刊|出版社|会议", re.I)
YEAR = re.compile(r"(19|20)\d{2}")
ITEM = re.compile(r"^\s*(?:\[\^?\d+\]|\(?\d{1,3}[.)、\]]|[-*•·]|\||>)")


def soft(text: str) -> str:
    """The checker's normalisation without the lower-casing, for display (same length as the lower-cased text)."""
    return re.sub(r"-\s*\n\s*", "", unicodedata.normalize("NFKC", text))


def words_with_pos(text: str) -> list:
    return [(m.group(0), m.start(), m.end()) for m in ng.WORD.finditer(text)]


def line_at(text: str, pos: int) -> tuple:
    a = text.rfind("\n", 0, pos) + 1
    b = text.find("\n", pos)
    return a, (len(text) if b < 0 else b)


def heading_before(text: str, pos: int) -> str:
    best = ""
    for m in re.finditer(r"^#{1,6}\s+(.+)$", text[:pos], re.M):
        best = m.group(1).strip()
    return best[:60]


def clip(s: str, n: int) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n] + " …"


def passages(low: str, shared: set) -> list:
    """Maximal runs of words of `low` in which every 12-word window is a shared shingle: [(char start, char end, words)]."""
    w = words_with_pos(low)
    covered = [False] * len(w)
    for i in range(len(w) - N + 1):
        if " ".join(x[0] for x in w[i:i + N]) in shared:
            for k in range(i, i + N):
                covered[k] = True
    out, i = [], 0
    while i < len(w):
        if not covered[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(w) and covered[j + 1]:
            j += 1
        out.append((w[i][1], w[j][2], j - i + 1))
        i = j + 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", type=Path, required=True)
    ap.add_argument("--entries", required=True)
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--sources", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--merge-index", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-prose", type=int, default=12)
    ap.add_argument("--max-cite", type=int, default=4)
    a = ap.parse_args()
    key = json.loads(a.key.read_text(encoding="utf-8"))
    key = key.get("entries", key)
    index = json.loads(a.index.read_text(encoding="utf-8"))
    if a.merge_index and a.merge_index.exists():
        index.update(json.loads(a.merge_index.read_text(encoding="utf-8")))
    seen, boiler = {}, set()
    for d in sorted(a.sources.glob("*/article.txt")):
        for s in ng.shingles(ng.body(ng.norm(d.read_text(encoding="utf-8", errors="ignore")))):
            if s in seen and seen[s] != d.parent.name:
                boiler.add(s)
            seen.setdefault(s, d.parent.name)
    del seen
    want = [e.strip() for e in a.entries.split(",") if e.strip()]
    form = ["# 泄漏查看·补充材料（只针对第一遍选了“拿不准”的条目）", "",
            f"共 {len(want)} 条，条目编号和第一张表相同。第一张表里只给了一个重合片段的例子、没给标题出现的位置，这里补全：",
            "", "- **重合片段**：报告和禁用来源文章共有的连续 12 个英文词以上的文字，相邻的已合并成整段。按它在报告里的位置分两类：落在**参考文献条目**里（列表项或表格行，带年份和 DOI、网址、et al、期刊名这类引用标记），还是落在**正文句子**里。正文里的每一段都给出报告和来源两边的上下文；参考文献条目里的只举几例。两篇文章引用同一篇文献，会在参考文献条目里产生重合，这不算使用了禁用来源。",
            "- **标题出现的位置**：禁用文章的标题在报告里每一次出现的前后文，和它所在的小节标题。",
            "", "仍然不显示组别、运行编号和分数。请只对这几条重新判断：这份报告有没有照抄或明显使用禁用的来源文章。", "", "---", ""]
    rows, stats = [], []
    for e in want:
        k = key[e]
        meta = index[k["task"]]
        idx = int(meta["idx"])
        run_dir = a.runs / k["batch"] / (k.get("run") or k.get("id") or k.get("run_id"))
        raw = (run_dir / "workspace" / "report.md").read_text(encoding="utf-8", errors="ignore")
        r_soft, r_low = soft(raw), ng.norm(raw)
        sf = a.sources / str(idx) / "article.txt"
        s_raw = sf.read_text(encoding="utf-8", errors="ignore") if sf.exists() else ""
        s_soft, s_low = soft(s_raw), ng.norm(s_raw)
        same_len = len(r_soft) == len(r_low) and len(s_soft) == len(s_low)
        r_show, s_show = (r_soft, s_soft) if same_len else (r_low, s_low)
        r_body, s_body = ng.body(r_low), ng.body(s_low)
        shared = (ng.shingles(r_body) & ng.shingles(s_body)) - boiler if s_low else set()
        ps = passages(r_body, shared)
        s_words = words_with_pos(s_body)
        s_first = {}
        for i in range(len(s_words) - N + 1):
            s_first.setdefault(" ".join(x[0] for x in s_words[i:i + N]), i)
        s_ref_cut = len(s_body)
        prose, cite = [], []
        for (c0, c1, nw) in ps:
            la, lb = line_at(r_body, c0)
            line = r_show[la:lb]
            is_cite = bool(YEAR.search(line)) and bool(CITE.search(line) or ITEM.match(line))
            first12 = " ".join(x[0] for x in words_with_pos(r_body[c0:c1])[:N])
            si = s_first.get(first12)
            s_ctx, s_where = "", ""
            if si is not None:
                sp = s_words[si][1]
                sa, sb = line_at(s_body, sp)
                s_ctx = clip(s_show[max(sa, sp - 160):min(sb, sp + 260)], 420)
                s_line = s_show[sa:sb]
                s_where = "来源文章的参考文献条目" if (YEAR.search(s_line) and (CITE.search(s_line) or ITEM.match(s_line))) else "来源文章的正文"
            item = {"words": nw, "report": clip(r_show[max(la, c0 - 160):min(lb, c1 + 160)], 520), "passage": clip(r_show[c0:c1], 300),
                    "heading": heading_before(r_show, c0), "source": s_ctx, "source_where": s_where}
            (cite if is_cite else prose).append(item)
        title = ng.norm(((meta.get("blocked") or {}).get("title") or ""))[:60]
        hits = [m.start() for m in re.finditer(re.escape(title), r_low)] if title else []
        form += [f"## 条目 {e}", "", f"**题目**：{clip(str(meta.get('topic') or meta.get('title') or k['task']), 120)}", "",
                 f"**禁用的来源文章**：{clip(str((meta.get('blocked') or {}).get('title') or ''), 200)}", "",
                 f"**重合片段**：12 词窗口共 {len(shared)} 个，合并成 {len(ps)} 段；其中落在报告参考文献条目里的 {len(cite)} 段，落在报告正文句子里的 {len(prose)} 段。", ""]
        if prose:
            form += [f"### 落在正文句子里的 {len(prose)} 段" + (f"（列出前 {a.max_prose} 段，按长短排）" if len(prose) > a.max_prose else ""), ""]
            for n, it in enumerate(sorted(prose, key=lambda x: -x["words"])[:a.max_prose], 1):
                form += [f"**{n}.** 连续 {it['words']} 个词相同；报告里所在小节：{it['heading'] or '（无标题）'}", "",
                         f"> 报告：{it['report']}", ">", f"> 来源（{it['source_where'] or '未定位'}）：{it['source'] or '（未定位）'}", ""]
        else:
            form += ["正文句子里没有重合片段。", ""]
        if cite:
            form += [f"### 落在参考文献条目里的 {len(cite)} 段（举 {min(a.max_cite, len(cite))} 例）", ""]
            for it in sorted(cite, key=lambda x: -x["words"])[:a.max_cite]:
                form += [f"- 连续 {it['words']} 个词；所在小节：{it['heading'] or '（无标题）'}：{it['report']}", ""]
        form += [f"**禁用文章的标题在报告里出现 {len(hits)} 次**" + ("：" if hits else "。"), ""]
        for n, h in enumerate(hits[:6], 1):
            form += [f"{n}. 所在小节：{heading_before(r_show, h) or '（无标题）'}", "", "> " + clip(r_show[max(0, h - 220):h + len(title) + 220], 560), ""]
        form += ["判断：[ ] 没有  [ ] 有  [ ] 拿不准", "", "备注：", "", "---", ""]
        rows.append(e)
        stats.append((e, len(shared), len(ps), len(prose), len(cite), len(hits)))
    a.out.mkdir(parents=True, exist_ok=True)
    text = "\n".join(form)
    text = re.sub(r"/work/[a-z0-9]{10}\b", "/work/<run>", text)
    (a.out / "leak-supplement.md").write_text(text, encoding="utf-8")
    (a.out / "leak-supplement-template.csv").write_text("entry,verdict,note\n" + "".join(f"{e},,\n" for e in rows), encoding="utf-8")
    print(f"{len(rows)} entries; form {len(text)} characters -> {a.out}")
    print("entry: shared windows, passages, in running text, in reference entries, title occurrences")
    for s in stats:
        print("  %s: %d, %d, %d, %d, %d" % s)
    print("sha256 leak-supplement.md:", hashlib.sha256(text.encode("utf-8")).hexdigest())


if __name__ == "__main__":
    main()
