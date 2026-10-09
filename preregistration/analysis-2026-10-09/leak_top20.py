#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The human leak look before unblinding (protocol v5.1 section 八): the highest-scoring report runs, shown blind.

`make` takes the N (20) reports with the highest GPT-5.5 total over the given batches, adds the runs the n-gram check
flagged (at most --extra, highest overlap first), shuffles them (seeded) and writes for each one an entry with:
the task's topic, the source article the task forbids (title, addresses), what the scripts found (blocked source
fetched and read / downloaded but not read / only mentioned; the benchmark's name in the logs; title, shared 12-word
passages and shared references from the n-gram check), the sites the run opened most and every address it opened on a
forbidden source's host, and the report (head, headings, last lines with the references). No group, no run id, no score.

  leak-form.md              the entries
  leak-answers-template.csv entry, verdict (没有 / 有 / 拿不准), note
  leak-key.json             SEALED: entry -> batch, run id, task, group, total, why it is in the sample
  sha256.txt
`score` reads the filled csv and the key and writes human-leak-flags.json: {run id: 1} for the entries marked 有
(master_table.py counts them as flagged, like the script's own flags), and prints the counts.

Usage (experiment directory on the dev box):
  leak_top20.py make --scores results/drb2-score-gpt --batches p2-main,p2-merge,p2-d --runs results/runs \
      --index tasks/phase2-drb2-index.json [--merge-index tasks/phase2-merge-index.json] --out results/human-check/leak [--n 20] [--extra 10]
  leak_top20.py score --answers results/human-check/leak/leak-answers.csv --key results/human-check/leak/leak-key.json --out results/human-leak-flags.json
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import random
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
HEADING = re.compile(r"^#{1,6}\s")
URL = re.compile(r"https?://[^\s\"'<>)\]]+")
YES = {"有", "yes", "y", "1", "是"}
NO = {"没有", "no", "n", "0", "否", "无"}


def host(u: str) -> str:
    try:
        h = urlparse(u if "//" in u else "//" + u).netloc.lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def opened(run_dir: Path) -> list:
    """Every address the run opened: web_fetch urls and the addresses in shell commands that fetch."""
    import run_metrics as rm
    out = []
    _, sessions = rm.load_sessions(run_dir)
    for s in sessions:
        for cid in s["call_order"]:
            call = s["calls"][cid]
            args = call["args"] if isinstance(call["args"], dict) else {}
            if call["name"] == "web_fetch":
                for key in ("url", "urls"):
                    v = args.get(key)
                    out += [v] if isinstance(v, str) else [x for x in (v or []) if isinstance(x, str)]
            elif call["name"] == "bash" and re.search(r"\b(curl|wget|requests|urlopen|httpx)\b", str(args.get("command") or "")):
                out += URL.findall(str(args.get("command")))
    return out


def cmd_make(a) -> None:
    index = json.loads(a.index.read_text(encoding="utf-8"))
    if a.merge_index and a.merge_index.exists():
        index.update(json.loads(a.merge_index.read_text(encoding="utf-8")))
    cand, ngram, script = [], {}, {}
    for b in [x for x in a.batches.split(",") if x]:
        for f in sorted((a.scores / b).glob("*.r1.json")):
            rec = json.loads(f.read_text(encoding="utf-8"))
            if rec.get("total") is not None:
                cand.append((rec["total"], b, rec["id"], rec.get("task", "")))
        g = a.scores.parent / f"analysis-{b}-ngram.csv"
        if g.exists():
            for r in csv.DictReader(open(g, encoding="utf-8")):
                ngram[r["id"]] = r
        sj = a.scores.parent / f"analysis-{b}-sources.json"
        if sj.exists():
            for r in json.loads(sj.read_text(encoding="utf-8")):
                script[r["id"]] = r
    if not cand:
        raise SystemExit("no judged report")
    cand.sort(key=lambda c: (-c[0], hashlib.sha256(c[2].encode()).hexdigest()))
    chosen = {c[2]: (c, "top score") for c in cand[:a.n]}
    flagged = sorted((c for c in cand if ngram.get(c[2], {}).get("flag") == "1" and c[2] not in chosen),
                     key=lambda c: -(int(ngram[c[2]].get("shared_shingles") or 0) + 3 * int(ngram[c[2]].get("title_mention") or 0)))
    for c in flagged[:a.extra]:
        chosen[c[2]] = (c, "n-gram flag")
    entries = list(chosen.values())
    random.Random(a.seed).shuffle(entries)
    a.out.mkdir(parents=True, exist_ok=True)
    form = ["# 解盲前的泄漏人工关", "",
            f"共 {len(entries)} 次运行：得分最高的 {min(a.n, len(cand))} 次，加上文字重合检查标出来的 {len(entries) - min(a.n, len(cand))} 次，顺序已打乱。"
            "每条只判断一件事：这份报告有没有照抄题目禁用的那篇来源文章，或者明显用了它。不显示组别、运行编号和分数。",
            "在 leak-answers-template.csv 里填 没有 / 有 / 拿不准，另存为 leak-answers.csv。", ""]
    key = {}
    for n, ((total, b, rid, task), why) in enumerate(entries, 1):
        meta = index.get(task) or {}
        blocked = meta.get("blocked") or {}
        bhosts = {host(u) for u in blocked.get("urls") or []} - {""}
        run_dir = a.runs / b / rid
        urls = opened(run_dir)
        hosts = collections.Counter(host(u) for u in urls)
        on_blocked = sorted({u[:200] for u in urls if any(h in u.lower() for h in bhosts)})  # also archive copies: the host anywhere in the address
        s, g = script.get(rid, {}), ngram.get(rid, {})
        rep = run_dir / "workspace" / "report.md"
        text = rep.read_text(encoding="utf-8", errors="replace") if rep.exists() else ""
        lines = text.splitlines()
        heads = [ln.strip() for ln in lines if HEADING.match(ln)][:40]
        key[str(n)] = {"batch": b, "id": rid, "task": task, "group": json.loads((run_dir / "result.json").read_text()).get("group") if (run_dir / "result.json").exists() else "",
                       "total": total, "why": why}
        form += [f"## 条目 {n}", "", f"**题目**：{meta.get('description', '')}（{meta.get('theme', '')}）", "",
                 f"**禁用的来源文章**：{blocked.get('title', '')}", ""] + [f"- {u}" for u in (blocked.get("urls") or [])[:6]] + ["",
                 "**脚本查到的**：读入禁用来源 %s 次；下载了没读 %s 次；只是提到 %s 次；日志里出现评测集名字 %s 次。" % (
                     s.get("n_source_calls", "未查"), s.get("n_unread", "未查"), s.get("n_mentions", "未查"), s.get("n_name_hits", "未查"))
                 + (" 文字重合：报告里%s来源文章的标题；与来源正文相同的 12 词片段 %s 条；相同的参考文献 %s 条。" % (
                     "出现了" if g.get("title_mention") == "1" else "没有出现", g.get("shared_shingles", "-"), g.get("shared_refs", "-")) if g else " 文字重合：未查。"),
                 ""]
        if g.get("example_shingle"):
            form += [f"相同片段举例：`{g['example_shingle']}`", ""]
        form += [f"**这次运行打开过 {len(urls)} 个地址，最多的站点**：" + "，".join(f"{h} {c}" for h, c in hosts.most_common(12)), ""]
        form += ["**打开过的、和禁用来源同一个站点的地址**：" + ("无" if not on_blocked else "")] + [f"- {u}" for u in on_blocked[:15]] + [""]
        form += ["**报告的各级标题**：", ""] + [f"    {h}" for h in heads] + ["", "**报告开头**：", "", "> " + text[:1500].replace("\n", "\n> "), "",
                 "**报告结尾（含参考文献）**：", "", "> " + "\n> ".join(lines[-35:]), "", "判断：[ ] 没有　[ ] 有　[ ] 拿不准　　备注：", "", "---", ""]
    (a.out / "leak-form.md").write_text("\n".join(form), encoding="utf-8")
    with open(a.out / "leak-answers-template.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["entry", "verdict", "note"])
        for n in range(1, len(entries) + 1):
            w.writerow([n, "", ""])
    (a.out / "leak-key.json").write_text(json.dumps({"SEALED": "人工关做完之前不要打开", "entries": key}, ensure_ascii=False, indent=1), encoding="utf-8")
    shas = {f: hashlib.sha256((a.out / f).read_bytes()).hexdigest() for f in ("leak-form.md", "leak-key.json")}
    (a.out / "sha256.txt").write_text("".join(f"{v}  {k}\n" for k, v in shas.items()), encoding="utf-8")
    print(f"{len(entries)} entries ({sum(1 for _, w_ in entries if w_ == 'top score')} top score, {sum(1 for _, w_ in entries if w_ != 'top score')} n-gram flag) "
          f"from {len(cand)} judged reports; form {len(chr(10).join(form))} characters; written to {a.out}")
    for k, v in shas.items():
        print(f"sha256 {k}: {v}")


def cmd_score(a) -> None:
    key = json.loads(a.key.read_text(encoding="utf-8"))["entries"]
    flags, counts, missing = {}, collections.Counter(), []
    for r in csv.DictReader(open(a.answers, encoding="utf-8-sig")):
        v = (r.get("verdict") or "").strip().lower()
        e = key.get(str(r["entry"]).strip())
        if e is None:
            continue
        if v in YES:
            flags[e["id"]] = 1
            counts["有"] += 1
        elif v in NO:
            counts["没有"] += 1
        elif v:
            counts["拿不准"] += 1
        else:
            missing.append(r["entry"])
    if missing:
        raise SystemExit(f"entries without a verdict: {missing}")
    a.out.write_text(json.dumps(flags, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"answers sha256 {hashlib.sha256(a.answers.read_bytes()).hexdigest()}")
    print(f"{sum(counts.values())} entries: " + ", ".join(f"{k} {v}" for k, v in counts.items()) + f"; {len(flags)} runs flagged by the human look -> {a.out}")
    for rid in flags:
        e = next(x for x in key.values() if x["id"] == rid)
        print(f"  flagged: {e['batch']} {rid} {e['task']} {e['group']} total {e['total']} ({e['why']})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make")
    mk.add_argument("--scores", type=Path, required=True, help="results/drb2-score-gpt (the batch folders are below it; the n-gram and source checks are looked up next to it)")
    mk.add_argument("--batches", required=True)
    mk.add_argument("--runs", type=Path, required=True)
    mk.add_argument("--index", type=Path, required=True)
    mk.add_argument("--merge-index", type=Path)
    mk.add_argument("--out", type=Path, required=True)
    mk.add_argument("--n", type=int, default=20)
    mk.add_argument("--extra", type=int, default=10)
    mk.add_argument("--seed", type=int, default=20261008)
    sc = sub.add_parser("score")
    sc.add_argument("--answers", type=Path, required=True)
    sc.add_argument("--key", type=Path, required=True)
    sc.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    (cmd_make if a.cmd == "make" else cmd_score)(a)


if __name__ == "__main__":
    main()
