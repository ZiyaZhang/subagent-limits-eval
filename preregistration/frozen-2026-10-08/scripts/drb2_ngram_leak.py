#!/usr/bin/env python3
"""Did a report copy from its task's blocked source article? (protocol v5.1 section 八, the leak check she approved)

The source articles are mostly English papers (data/drb2/sources/<idx>/article.txt, drb2_fetch_sources.py); the reports
are Chinese, so translated copying is not caught here (the fetch-based check drb2_sources.py and the human look at the
top-scoring runs cover that side). What this script measures, per report:
  title     the blocked article's title (first 60 chars, normalised) appears in the report           (flag: mention)
  shingles  12-word English shingles shared between the BODIES of report and source (the text before each one's
            reference list; shared citations are legitimate), word-level, normalised (NFKC, lower, hyphen-newline joined,
            punctuation stripped), minus shingles found in two or more source articles (boilerplate)         (flag: >= 3)
  dois      DOIs / URLs in the report that also occur in the source's text (its reference list)      (flag: >= 5)
  numbers   share of the report's distinct numeric tokens (>= 3 digits, or decimals) that occur in the source
            (descriptive: a good report legitimately shares numbers with the source)
A run is flagged when any flag condition holds; the flags are reported per cell and the flagged runs are listed for
the human leak check. Nothing is removed by this script alone.

Usage: drb2_ngram_leak.py --reports results/runs/<batch> --sources data/drb2/sources --index tasks/phase2-drb2-index.json
                          --out results/analysis-<batch>-ngram.csv [--merge-index tasks/phase2-merge-index.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

WORD = re.compile(r"[a-z][a-z'-]+")
DOI = re.compile(r"10\.\d{4,9}/[^\s\"'<>)\]]+", re.I)
URL = re.compile(r"https?://[^\s\"'<>)\]]+", re.I)
NUMBER = re.compile(r"(?<![\d.])(\d{3,}(?:\.\d+)?|\d+\.\d+)(?![\d.])")
N = 12


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"-\s*\n\s*", "", text)
    return text.lower()


REF_HEAD = re.compile(r"^\s*(?:#+\s*)?(?:\d+[.、]?\s*)?(?:references?|bibliography|reference list|参考文献|参考资料|引用文献|引用来源|资料来源|数据来源|参考链接)\s*[:：]?\s*$", re.I | re.M)


def body(text: str) -> str:
    """The text before its reference list (the last reference heading in the second half of the text)."""
    cut = None
    for m in REF_HEAD.finditer(text):
        if m.start() > len(text) * 0.4:
            cut = m.start()
    return text[:cut] if cut else text


def shingles(text: str) -> set:
    words = WORD.findall(text)
    return {" ".join(words[i:i + N]) for i in range(len(words) - N + 1)}


def refs(text: str) -> set:
    out = {m.group(0).rstrip(".,;") for m in DOI.finditer(text)}
    out |= {m.group(0).rstrip(".,;") for m in URL.finditer(text)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reports", type=Path, required=True)
    ap.add_argument("--sources", type=Path, required=True)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--merge-index", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    index = json.loads(a.index.read_text(encoding="utf-8"))
    if a.merge_index and a.merge_index.exists():
        index.update(json.loads(a.merge_index.read_text(encoding="utf-8")))
    cache = {}
    # boilerplate: shingles that occur in two or more different source articles (licence notices, standard phrases)
    seen, boiler = {}, set()
    for d in sorted(a.sources.glob("*/article.txt")):
        for s in shingles(body(norm(d.read_text(encoding="utf-8", errors="ignore")))):
            if s in seen and seen[s] != d.parent.name:
                boiler.add(s)
            seen.setdefault(s, d.parent.name)
    del seen

    def source(idx: int):
        if idx not in cache:
            f = a.sources / str(idx) / "article.txt"
            text = norm(f.read_text(encoding="utf-8", errors="ignore")) if f.exists() else ""
            cache[idx] = (text, shingles(body(text)), refs(text), set(NUMBER.findall(text)))
        return cache[idx]
    rows = []
    for rp in sorted(a.reports.glob("*/result.json")):
        res = json.loads(rp.read_text(encoding="utf-8"))
        meta = index.get(res["task"])
        f = rp.parent / "workspace" / "report.md"
        if not meta or not f.exists():
            continue
        idx = int(meta["idx"])
        stext, sshing, srefs, snums = source(idx)
        rtext = norm(f.read_text(encoding="utf-8", errors="ignore"))
        title = norm(((meta.get("blocked") or {}).get("title") or ""))[:60]
        title_hit = bool(title) and title in rtext
        shared = (shingles(body(rtext)) & sshing) - boiler if stext else set()
        rrefs = refs(rtext)
        shared_refs = {r for r in rrefs if r in srefs} if stext else set()
        rnums = set(NUMBER.findall(rtext))
        num_share = (len(rnums & snums) / len(rnums)) if (rnums and stext) else None
        flag = title_hit or len(shared) >= 3 or len(shared_refs) >= 5
        rows.append({"id": res["id"], "task": res["task"], "group": res["group"], "rep": res["rep"], "idx": idx,
                     "source_chars": len(stext), "title_mention": int(title_hit), "shared_shingles": len(shared),
                     "shared_refs": len(shared_refs), "report_refs": len(rrefs), "number_share": round(num_share, 3) if num_share is not None else "",
                     "flag": int(flag), "example_shingle": next(iter(shared), "")[:120]})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["id"])
        w.writeheader()
        w.writerows(rows)
    by = {}
    for r in rows:
        by.setdefault(r["group"], [0, 0])
        by[r["group"]][0] += 1
        by[r["group"]][1] += r["flag"]
    for g, (n, k) in sorted(by.items()):
        print(f"{g}: {n} reports, {k} flagged")
    print(f"{len(rows)} reports; flagged {sum(r['flag'] for r in rows)}; no source text for {sum(1 for r in rows if not r['source_chars'])} -> {a.out}")
    for r in rows:
        if r["flag"]:
            print(f"  FLAG {r['id']} {r['task']} {r['group']}: title {r['title_mention']}, shingles {r['shared_shingles']}, refs {r['shared_refs']}")


if __name__ == "__main__":
    main()
