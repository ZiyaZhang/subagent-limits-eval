#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""False-fact sensitivity of the DRB II judge (protocol v5.1 section 八, 改坏灵敏度: 20 reports each get 3
plausible-but-false facts inserted; does the judge award the rubric items they contradict?).

`make`: for each chosen report, take the info_recall rubric items that the original judgement (--scores,
<id>.r<k>.json from drb2_score_gpt.py) scored 0 (not mentioned), pick 3 of them, and insert for each one a sentence
that asserts a WRONG value for that item. The sentence is made from the rubric item by fixed rules, no model:
  number    every number in the item that is not a year is multiplied by a factor in [0.4, 0.6] or [1.5, 2.0] (chosen
            from the hash of run id and item) and rounded to the item's own decimals; small integers (<= 10) move by 2-4
  year      every four-digit year is shifted by 3-7 years (the same shift for all years of the item; backwards when the
            shift would pass 2026)
  cn_number Chinese ordinals and counts move by 2-4 (第一步 -> 第三步, 五个支柱 -> 七个支柱; a bare 一 is left alone)
  entity    the first organisation-like name (…政府 / …公司 / …大学 / …委员会 …, with its acronym in parentheses)
            becomes "另一机构"; names inside quotes and concepts such as 数字政府 do not count
  negation  the first polarity word is turned around (不包括 -> 包括, 是 -> 不是, 达到 -> 未达到, 颁布 -> 并未颁布 …)
  fallback  the assertion is followed by "——这一说法并不成立" (counted separately; exclude it if you want)
Items are ranked number > year > cn_number > entity > negation > fallback, ties by hash, and the first 3 are used; the
rubric scaffolding ("明确指出", "在对比表格中，正确填写" …) is stripped so the sentence reads as a statement. Each sentence goes
in as a paragraph of its own at a paragraph boundary near the middle of the report (never inside a code fence or a
table). The original text is never changed (checked). Writes <out>/<id>/workspace/report.md, <out>/manifest.json
(every insert: id, task, rubric_item, rule, inserted_sentence, position = character offset in the modified file,
paragraph_index) and <out>/rows.csv (id, task) for the judge.

`compare`: for each insert, did the judge's score for that rubric item go from 0 to 1 (a false credit)? Prints the
count and rate overall and per rule, the inserts that went 0 -> -1, and every other flip (items not touched) with the
per-report totals before and after.

Usage:
  judge_false_facts.py make --reports results/runs/<batch> --rows results/master/raw/<batch>.csv --n 20 \
      --scores results/drb2-score-gpt/<batch> --out results/drb2-false-facts/<batch>   [--ids a,b] [--k 3] [--rep 1]
  drb2_score_gpt.py --reports results/drb2-false-facts/<batch> --rows results/drb2-false-facts/<batch>/rows.csv \
      --out results/drb2-score-gpt/<batch>-false
  judge_false_facts.py compare --orig results/drb2-score-gpt/<batch> --modified results/drb2-score-gpt/<batch>-false \
      --manifest results/drb2-false-facts/<batch>/manifest.json [--rep 1]
Reads and writes files only; no API call.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "data/drb2/repo-src/tasks_and_rubrics.jsonl"
DIMS = ("info_recall", "analysis", "presentation")
HEADING = re.compile(r"^#{1,6}\s")
FENCE = re.compile(r"^\s*(```|~~~)")
THIS_YEAR = 2026
RULES = ("number", "year", "cn_number", "entity", "negation", "fallback")

# a number that is not glued to letters (S5000C, GPT-4), not after a Latin word (S&P 500, Infocomm 21: names),
# not an ordinal (第2套); optional thousands separators; an optional % sign is captured for the cap at 100
NUM = re.compile(r"(?<![\dA-Za-z.第])(?<![A-Za-z&] )(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?![\dA-Za-z])(\s*[%％])?")
YEAR = re.compile(r"(?<![\dA-Za-z])((?:18|19|20)\d{2})(?![\dA-Za-z])")
# a Chinese numeral as an ordinal (第一步) or a count before a classifier (五个支柱, 两部分); a bare 一 before a
# classifier (是一种模式) is an article, not a count, and is left alone
CN_DIGITS = "零一二三四五六七八九"
CN_NUM = re.compile(r"(第)?([一二三四五六七八九十两]{1,3})(?(1)|(?=(?:个|项|种|类|大|条|步|层|级|次|家|位|名|部分|部|套|款|批|轮|期|阶段|方面|要素|支柱|维度|指标|原则|要点|措施|阶段|环节)))")
# an institution: a name before a strong suffix, with an optional acronym in parentheses; the name is cut after the last
# particle or verb in it (由/在/的/包括 …) so that the subject of the sentence is not swallowed ("VIX由芝加哥期权交易所（CBOE）
# 发布"); a match inside quotes (“数字政府总体规划”, a strategy's name) or a concept (数字政府) does not count
ENTITY = re.compile(r"([一-鿿A-Za-z·& \-－]{1,14}?)(政府|委员会|研究院|研究所|大学|学院|集团|公司|银行|基金会|协会|联盟|交易所|央行|总局|管理局|监管局)"
                    r"(\s*[（(][A-Za-z&.\-\s]{2,40}[)）])?")
QUOTED = re.compile(r"“[^”]*”|‘[^’]*’|《[^》]*》|「[^」]*」")
CONCEPT = ("数字", "数字化", "电子", "智慧", "开放", "透明", "服务型", "法治", "有限", "责任", "大", "小", "新", "旧")  # 数字政府 is not an institution
PARTICLES = "由在是为和及或与对向将把从到经被如了的指出提过据按称即于让使给替同跟不括供立设布属自等各其该本足有含"
SCAFFOLD = [
    (re.compile(r"^(?:在)?[^，,。]{1,16}(?:中|里|内|下|时)[，,]\s*"), ""),  # "在对比表格中，" / "LiDAR制造商对比表中，"
    (re.compile(r"^(?:报告|文章|正文|输出)(?:中|应|必须|需要|要)?(?:明确|正确|准确|清晰地?|具体|详细)?"), ""),
    (re.compile(r"^(?:明确|正确|准确|清晰地?|具体|详细|完整)?(?:地)?(?:指出|提及|提到|说明|给出|列出|列举|填写|描述|解释|阐述|提出|引用|引述|强调|陈述|写明|注明|标明|提供|呈现|展示|回答|识别|承认|总结|归纳|分析|讨论|区分)[：:，,]?\s*"), ""),
    (re.compile(r"^(?:明确|正确)?(?:将|把)(.+?)(?:定义为|界定为)(.+)$"), r"\1是指\2"),
    (re.compile(r"^(?:明确|正确)?(?:将|把)(.+?)(?:描述为|称为|视为|归为|确定为|列为|认定为|作为|看作|当作)(.+)$"), r"\1是\2"),
    (re.compile(r"^(?:明确|正确)"), ""),
]
# (pattern, replacement): the earliest match in the sentence is turned around, the longer one at a tie. Words that are
# as often nouns as verbs in rubric items (建议, 要求, 限制, 有) are not in the list; the one-character words carry
# lookarounds so that 认为 / 作为 / 是否 / 社会 / 应用 ... are left alone.
NEGATION = [(re.compile(p), r) for p, r in [
    ("不包括", "包括"), ("不包含", "包含"), ("不属于", "属于"), ("不存在", "存在"), ("不需要", "需要"), ("不应当", "应当"),
    ("不应该", "应该"), ("并非", "正是"), ("没有", "有"), ("无法", "能够"), ("不能", "能够"), ("不会", "会"), ("不是", "是"),
    ("不应", "应"), ("是指", "并非指"), ("名称为", "名称并非"), ("全称为", "全称并非"), ("简称为", "简称并非"),
    ("定义为", "并非定义为"), ("称为", "并非称为"), ("视为", "并非视为"), ("作为", "并非作为"), ("成为", "并未成为"),
    ("分为", "并非分为"), ("列为", "并未列为"), ("转变为", "并未转变为"), ("变为", "并未变为"), ("旨在", "并非旨在"),
    ("包括", "不包括"), ("包含", "不包含"), ("涵盖", "并未涵盖"), ("属于", "不属于"), ("存在", "不存在"), ("涉及", "不涉及"),
    ("需要", "不需要"), ("应当", "不应当"), ("应该", "不应该"), ("可以", "不能"), ("能够", "无法"), ("达到", "未达到"),
    ("源于", "并非源于"), ("来自", "并非来自"), ("基于", "并非基于"), ("位于", "并非位于"), ("用于", "不用于"), ("应用于", "不应用于"),
    ("适用于", "不适用于"), ("导致", "不会导致"), ("造成", "并未造成"), ("引起", "并未引起"), ("带来", "并未带来"), ("形成", "并未形成"),
    ("提出", "并未提出"), ("提供", "并不提供"), ("颁布", "并未颁布"), ("成立", "并未成立"), ("引入", "并未引入"), ("推出", "并未推出"),
    ("采用", "并未采用"), ("实施", "并未实施"), ("启动", "并未启动"), ("制定", "并未制定"), ("设立", "并未设立"),
    ("发布", "并未发布"), ("通过", "并未通过"), ("签署", "并未签署"), ("加入", "并未加入"), ("使用", "并未使用"),
    ("采取", "并未采取"), ("建立", "并未建立"), ("出现", "并未出现"), ("获得", "并未获得"), ("实现", "并未实现"),
    ("完成", "并未完成"), ("开始", "并未开始"), ("结束", "并未结束"), ("强调", "并未强调"), ("认为", "并不认为"),
    ("表明", "并未表明"), ("显示", "并未显示"), ("发现", "并未发现"), ("证明", "并未证明"), ("支持", "并不支持"),
    ("允许", "不允许"), ("禁止", "允许"), ("鼓励", "不鼓励"), ("依赖", "不依赖"), ("具有", "不具有"), ("拥有", "并不拥有"),
    ("含有", "不含"), ("持有", "并未持有"), ("减免", "并不减免"), ("转向", "并未转向"), ("满足", "并不满足"), ("符合", "不符合"),
    ("遵循", "并未遵循"), ("遵守", "并未遵守"), ("考虑", "并未考虑"), ("纳入", "并未纳入"), ("排除", "并未排除"), ("参与", "并未参与"),
    ("覆盖", "并未覆盖"), ("审查", "并未审查"), ("评估", "并未评估"), ("批准", "并未批准"), ("负责", "不负责"), ("监督", "并未监督"),
    ("资助", "并未资助"), ("投资于", "并未投资于"), ("关注", "并未关注"), ("记录", "并未记录"), ("分离", "并未分离"),
    ("促进", "抑制"), ("抑制", "促进"), ("提高", "降低"), ("降低", "提高"), ("减少", "增加"), ("增加", "减少"),
    ("扩大", "缩小"), ("缩小", "扩大"), ("改善", "恶化"), ("加强", "削弱"), ("削弱", "加强"), ("推动", "阻碍"),
    ("增至", "降至"), ("降至", "增至"), ("增长", "下降"), ("上升", "下降"), ("下降", "上升"), ("高于", "低于"),
    ("低于", "高于"), ("超过", "不足"), ("不足", "超过"), ("最高", "最低"), ("最低", "最高"), ("最大", "最小"),
    ("最小", "最大"), ("正相关", "负相关"), ("负相关", "正相关"),
    (r"(?<![对反适响回供效相感因顺答呼报照理接策])应(?![用对急该当答有付邀允变激聘诉战力和])", "不应"),
    (r"(?<![社协学委机议基工公商教都不才将可展年晚盛员国事东峰大分总两集联业行])会(?![议员计谈晤面展馆长见合社话商务])", "不会"),
    (r"(?<![但可或只凡于即总若不并正还就而尤也便倒当真确老实莫自本如先后亦])是(?![否指非以故为])", "不是"),
    (r"(?<![认成作因以称视列定分行较最更甚极颇尤无变改转译化归评选推誉奉封立设拟订])为(?![了何止此什主准例基由目核重中代首期名标宜限])", "并非"),
]]
LEADS = ["据公开资料，", "需要补充的是，", "另据统计，", "值得注意的是，", "有资料显示，", "按照现有记录，"]


def hval(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest(), 16)


def assertion_of(item: str) -> str:
    """The rubric item without its grading scaffolding, as a plain statement ending in 。."""
    s = item.strip()
    for pat, rep in SCAFFOLD:
        s = pat.sub(rep, s, count=1)
    s = s.strip(" ，,：:")
    if s and s[-1] not in "。！？.":
        s += "。"
    return s


def change_number(tok: str, h: int, percent: bool = False) -> str:
    sep = "," in tok
    raw = tok.replace(",", "")
    dec = len(raw.split(".")[1]) if "." in raw else 0
    x = float(raw)
    if dec == 0 and x <= 10:
        y = x + 2 + h % 3
    else:
        low = (h >> 10) % 2 == 1 or (percent and x * 1.5 > 100)  # a percentage stays at or under 100
        f = (0.4 + (h % 1000) / 1000 * 0.2) if low else (1.5 + (h % 1000) / 1000 * 0.5)
        y = round(x * f, dec)
        if y == x or y <= 0:
            y = round(x * 2, dec) if x * 2 != x else x + 1
    s = f"{y:.{dec}f}"
    if sep:
        a, _, b = s.partition(".")
        s = f"{int(a):,}" + (f".{b}" if b else "")
    return s


def cn_to_int(s: str):
    if s == "两":
        return 2
    if s == "十":
        return 10
    if "十" in s:
        a, _, b = s.partition("十")
        return (CN_DIGITS.index(a) if a else 1) * 10 + (CN_DIGITS.index(b) if b else 0)
    return CN_DIGITS.index(s) if len(s) == 1 else None


def int_to_cn(n: int) -> str:
    if n < 10:
        return CN_DIGITS[n]
    if n < 20:
        return "十" + (CN_DIGITS[n - 10] if n > 10 else "")
    return CN_DIGITS[n // 10] + "十" + (CN_DIGITS[n % 10] if n % 10 else "")


def change_cn_numbers(base: str, h: int):
    """Chinese ordinals and counts moved by 2-4 (never to the same value); None when the sentence has none."""
    out, last, changed = [], 0, False
    for k, m in enumerate(CN_NUM.finditer(base)):
        n = cn_to_int(m.group(2))
        if n is None or (n == 1 and not m.group(1)):
            continue
        new = n + 2 + (h >> (k * 2)) % 3
        if new > 20:
            new = max(2, n - 2 - (h >> (k * 2)) % 3)
        out.append(base[last:m.start(2)])
        out.append(int_to_cn(new))
        last = m.end(2)
        changed = True
    out.append(base[last:])
    return "".join(out) if changed else None


def entity_span(base: str):
    """(start, end) of the first institution name in the sentence, or None when every candidate is a bare suffix, a
    concept (数字政府) or inside quotes (a title). The name is cut after the last particle or verb in it and must be
    2-8 characters (or carry an acronym in parentheses)."""
    quoted = [(m.start(), m.end()) for m in QUOTED.finditer(base)]
    for m in ENTITY.finditer(base):
        if any(q0 <= m.start() < q1 for q0, q1 in quoted):
            continue
        name = m.group(1)
        cut = max((name.rfind(c) for c in PARTICLES), default=-1)
        name = name[cut + 1:]
        if name in CONCEPT or len(name) > (24 if re.search("[A-Za-z]", name) else 8):
            continue
        if len(name) >= 2 or m.group(3):
            return m.start(1) + len(m.group(1)) - len(name), m.end()
    return None


def make_sentence(item: str, h: int) -> tuple:
    """(rule, wrong sentence) for a rubric item; the rule tells which transformation applied."""
    base = assertion_of(item)
    nums = [m for m in NUM.finditer(base) if not YEAR.fullmatch(m.group(1))]
    if nums:
        out, last = [], 0
        for k, m in enumerate(nums):
            out.append(base[last:m.start(1)])
            out.append(change_number(m.group(1), h >> (k * 3), percent=bool(m.group(2))))
            last = m.end(1)
        out.append(base[last:])
        return "number", "".join(out)
    years = list(YEAR.finditer(base))
    if years:
        shift = 3 + h % 5
        if any(int(m.group(1)) + shift > THIS_YEAR for m in years):
            shift = -shift
        out, last = [], 0
        for m in years:
            out.append(base[last:m.start(1)])
            out.append(str(int(m.group(1)) + shift))
            last = m.end(1)
        out.append(base[last:])
        return "year", "".join(out)
    cn = change_cn_numbers(base, h)
    if cn:
        return "cn_number", cn
    span = entity_span(base)
    if span:
        return "entity", base[:span[0]] + "另一机构" + base[span[1]:]
    hits = []
    for pat, r in NEGATION:
        m = pat.search(base)
        if m:
            hits.append((m.start(), -(m.end() - m.start()), m.group(0), r))
    if hits:
        pos, neg_len, p, r = min(hits)
        return "negation", base[:pos] + r + base[pos - neg_len:]
    return "fallback", base.rstrip("。") + "——这一说法并不成立。"


def blocks_of(text: str) -> list:
    """(start, end, first line) of each block: a run of non-blank lines, a fenced code block, or a heading."""
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


def middle_points(text: str, k: int) -> list:
    """k block starts nearest to the middle of the text (not the first block; not right before a heading when a
    plain paragraph boundary is as near), sorted by position."""
    blocks = blocks_of(text)
    cands = [(i, b[0]) for i, b in enumerate(blocks) if i > 0]
    if not cands:
        return [(1, len(text))]
    mid = len(text) / 2
    cands.sort(key=lambda c: (abs(c[1] - mid) + (0.02 * len(text) if HEADING.match(blocks[c[0]][2]) else 0)))
    return sorted(cands[:k], key=lambda c: c[1])


def insert_sentences(text: str, sentences: list) -> tuple:
    """Each sentence becomes its own paragraph at one of the block starts nearest the middle. Returns the modified
    text and, per sentence, (inserted paragraph, offset in the modified text, paragraph index)."""
    pts = middle_points(text, len(sentences))
    plan = sorted(zip(pts, sentences), key=lambda z: -z[0][1])  # from the back, so offsets stay valid
    mod, segs = text, []
    for (bi, off), sent in plan:
        before = mod[:off]
        lead = "" if (not before or before.endswith("\n\n")) else ("\n" if before.endswith("\n") else "\n\n")
        trail = "\n\n" if off < len(mod) else "\n"
        seg = lead + sent + trail
        mod = before + seg + mod[off:]
        segs.append((bi, seg, sent))
    check = mod
    for _, seg, _ in segs:
        check = check.replace(seg, "", 1)
    if check != text:
        raise RuntimeError("the modified text does not contain the original text unchanged")
    out = []
    for bi, seg, sent in sorted(segs, key=lambda s: s[0]):
        out.append((seg, mod.find(seg) + len(seg) - len(seg.lstrip("\n")), bi))
    return mod, out


def load_tasks(path: Path) -> dict:
    tasks = {}
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            t = json.loads(line)
            tasks[int(t["idx"])] = t
    return tasks


def pick_rows(a) -> list:
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
            else:
                sf = a.scores / f"{rid}.r{a.rep}.json"
                if not sf.exists():
                    sys.exit(f"{rid}: not in --rows and no {sf.name} under --scores; cannot tell its task")
                out.append({"id": rid, "task": json.loads(sf.read_text(encoding="utf-8"))["task"]})
        return out
    if not rows:
        sys.exit("give --ids or --rows")
    return sorted(rows, key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())


def cmd_make(a) -> None:
    rows = pick_rows(a)
    tasks = load_tasks(a.tasks)
    a.out.mkdir(parents=True, exist_ok=True)
    inserts, reports, short = [], [], []
    for r in rows:
        if not a.ids and len(reports) >= a.n:
            break
        rid = r["id"]
        f = a.reports / rid / "workspace" / "report.md"
        sf = a.scores / f"{rid}.r{a.rep}.json"
        if not f.exists() or not sf.exists():
            if a.ids:
                print(f"{rid}: missing report or judgement; skipped")
            continue
        rec = json.loads(sf.read_text(encoding="utf-8"))
        if rec.get("total") is None:
            continue
        idx = int(r["task"].rsplit("_", 1)[1])
        rubric = set(tasks[idx]["content"]["rubric"].get("info_recall") or [])
        zero = [it["rubric_item"] for it in rec["items"] if it["dim"] == "info_recall" and it["score"] == 0 and it["rubric_item"] in rubric]
        cands = []
        for item in zero:
            h = hval(rid, item)
            rule, sent = make_sentence(item, h)
            cands.append((RULES.index(rule), h, item, rule, sent))
        cands.sort()
        chosen = cands[:a.k]
        if not chosen:
            print(f"{rid}: no info_recall item scored 0; skipped")
            continue
        if len(chosen) < a.k:
            short.append(rid)
        text = f.read_text(encoding="utf-8")
        paras = [LEADS[(h >> 4) % len(LEADS)] + sent for _, h, _, _, sent in chosen]
        mod, placed = insert_sentences(text, paras)
        d = a.out / rid / "workspace"
        d.mkdir(parents=True, exist_ok=True)
        (d / "report.md").write_text(mod, encoding="utf-8")
        for (_, h, item, rule, sent), (seg, off, bi) in zip(chosen, placed):
            inserts.append({"id": rid, "task": r["task"], "rubric_item": item, "dim": "info_recall", "rule": rule,
                            "original_score": 0, "inserted_sentence": seg.strip("\n"), "position": off, "paragraph_index": bi})
        reports.append({"id": rid, "task": r["task"], "original_chars": len(text), "modified_chars": len(mod), "n_inserts": len(chosen),
                        "zero_info_recall_items": len(zero)})
        print(f"{rid} {r['task']}: {len(chosen)} inserts ({', '.join(c[3] for c in chosen)}) of {len(zero)} items scored 0")
        for c, (seg, off, bi) in zip(chosen, placed):
            print(f"    [{c[3]}] {seg.strip()}")
    if not reports:
        sys.exit("nothing modified")
    by_rule = {}
    for x in inserts:
        by_rule[x["rule"]] = by_rule.get(x["rule"], 0) + 1
    man = {"note": "false facts inserted into copies of reports for the judge sensitivity check; the originals are untouched",
           "k": a.k, "judge_rep_of_original": a.rep, "scores_dir": str(a.scores), "reports_dir": str(a.reports),
           "inserts_by_rule": by_rule, "reports": reports, "inserts": inserts}
    (a.out / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(a.out / "rows.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "task"])
        w.writeheader()
        w.writerows({"id": x["id"], "task": x["task"]} for x in reports)
    print(f"\n{len(reports)} modified reports, {len(inserts)} inserts ({', '.join(f'{k} {v}' for k, v in sorted(by_rule.items()))}) under {a.out}; "
          f"manifest.json and rows.csv written" + (f"; fewer than {a.k} eligible items in {' '.join(short)}" if short else ""))


def load_scores(d: Path, rep: int) -> dict:
    out = {}
    for p in sorted(d.glob(f"*.r{rep}.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("total") is not None:
            out[rec["id"]] = rec
    return out


def cmd_compare(a) -> None:
    man = json.loads(a.manifest.read_text(encoding="utf-8"))
    o, m = load_scores(a.orig, a.rep), load_scores(a.modified, a.rep)
    touched = {(x["id"], x["rubric_item"]) for x in man["inserts"]}
    judged, credited, minus, by_rule = 0, 0, 0, {}
    print("inserted items (original score -> score after the insert):")
    for x in man["inserts"]:
        rid = x["id"]
        if rid not in o or rid not in m:
            print(f"  {rid}: judgement missing on one side")
            continue
        so = {it["rubric_item"]: it["score"] for it in o[rid]["items"]}
        sm = {it["rubric_item"]: it["score"] for it in m[rid]["items"]}
        if x["rubric_item"] not in so or x["rubric_item"] not in sm:
            print(f"  {rid}: rubric item not in a judgement: {x['rubric_item'][:40]}")
            continue
        a0, a1 = so[x["rubric_item"]], sm[x["rubric_item"]]
        judged += 1
        r = by_rule.setdefault(x["rule"], [0, 0, 0])
        r[0] += 1
        if a1 == 1:
            credited += 1
            r[1] += 1
        if a1 == -1:
            minus += 1
            r[2] += 1
        if a0 != 0:
            print(f"  {rid}: original score was {a0}, not 0 (manifest built from another pass?)")
        print(f"  {rid} [{x['rule']:8s}] {a0} -> {a1}  {x['rubric_item'][:60]}")
    print(f"\nfalse credits: {credited} of {judged} inserted items scored 1 after the insert "
          f"({100 * credited / judged:.1f}%)" if judged else "\nno inserted item was judged on both sides")
    if minus:
        print(f"inserted items scored -1 after the insert: {minus}")
    for rule in RULES:
        if rule in by_rule:
            n, c, mm = by_rule[rule]
            print(f"  {rule:9s} {c} of {n} credited ({100 * c / n:.1f}%)" + (f", {mm} scored -1" if mm else ""))
    print("\nother items (not touched by an insert) and report totals:")
    print(f"{'id':12s} {'task':12s} {'orig':>7s} {'mod':>7s} {'diff':>7s} {'0->1':>5s} {'1->0':>5s} {'other':>5s}")
    flips, diffs, credited_pts = {}, [], []
    for rep_ in man["reports"]:
        rid = rep_["id"]
        if rid not in o or rid not in m:
            continue
        so = {it["rubric_item"]: it["score"] for it in o[rid]["items"]}
        sm = {it["rubric_item"]: it["score"] for it in m[rid]["items"]}
        f = {}
        for k in so:
            if k in sm and (rid, k) not in touched and so[k] != sm[k]:
                key = f"{so[k]}->{sm[k]}"
                f[key] = f.get(key, 0) + 1
                flips[key] = flips.get(key, 0) + 1
        diffs.append(m[rid]["total"] - o[rid]["total"])
        credited_pts.append(100 * sum(1 for k in sm if (rid, k) in touched and sm[k] == 1) / len(sm))
        other = sum(v for k, v in f.items() if k not in ("0->1", "1->0"))
        print(f"{rid:12s} {o[rid].get('task', ''):12s} {o[rid]['total']:7.2f} {m[rid]['total']:7.2f} {m[rid]['total'] - o[rid]['total']:+7.2f} "
              f"{f.get('0->1', 0):5d} {f.get('1->0', 0):5d} {other:5d}")
    if diffs:
        print(f"\nother-item flips over {len(diffs)} reports: " + (", ".join(f"{k} {v}" for k, v in sorted(flips.items())) or "none")
              + f"; mean total change {sum(diffs) / len(diffs):+.2f} pts, of which the credited inserts account for "
              f"{sum(credited_pts) / len(credited_pts):+.2f} pts")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make", help="write copies of the chosen reports with false facts inserted")
    mk.add_argument("--reports", type=Path, required=True, help="dir of runs: <id>/workspace/report.md")
    mk.add_argument("--rows", type=Path, help="CSV with id, task (drb2_zh_NNN)[, incomplete]")
    mk.add_argument("--ids", default="", help="comma-separated run ids (else --n of --rows in run-id hash order)")
    mk.add_argument("--n", type=int, default=20)
    mk.add_argument("--scores", type=Path, required=True, help="dir of the original judgements <id>.r<rep>.json")
    mk.add_argument("--tasks", type=Path, default=TASKS, help="tasks_and_rubrics.jsonl")
    mk.add_argument("--out", type=Path, required=True)
    mk.add_argument("--k", type=int, default=3, help="false facts per report")
    mk.add_argument("--rep", type=int, default=1, help="judge pass of the original judgements")
    mk.set_defaults(fn=cmd_make)
    cp = sub.add_parser("compare", help="original vs modified judgements")
    cp.add_argument("--orig", type=Path, required=True)
    cp.add_argument("--modified", type=Path, required=True)
    cp.add_argument("--manifest", type=Path, required=True, help="manifest.json of make")
    cp.add_argument("--rep", type=int, default=1, help="judge pass to read on both sides")
    cp.set_defaults(fn=cmd_compare)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
