#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One self-contained HTML page for filling a blind check form with the keyboard instead of editing a CSV by hand.

Works for the four forms of phase 2, which share one layout: a markdown file whose entries start with "## 条目 N", and
an answer template CSV (entry, <answer column>[, note]). The page shows one entry at a time, takes the answer with a
key (1, 2, 3 ...) or a click, moves on, keeps the progress in the browser (so it survives a reload), and exports a CSV
with exactly the template's header and entry values. It holds nothing but the form's own text: no group, no score.

  the 200 judgements   label_page.py --form results/human-check/form.md --template results/human-check/answer-template.csv \
                           --choices 满足,不满足,拿不准 --save-as answers.csv --out results/human-check/form.html
  the leak look        label_page.py --form .../leak/leak-form.md --template .../leak/leak-answers-template.csv \
                           --choices 没有,有,拿不准 --save-as leak-answers.csv --out .../leak/leak-form.html
  behaviour check      --choices 是,否,拿不准 --save-as check-answers.csv
  delegation check     --choices 原样转包,分片,收窄,新子题,复核,拿不准 --save-as check-answers.csv

No network, no external file: open the HTML in a browser.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from pathlib import Path

ENTRY = re.compile(r"^## 条目 (\d+)\s*$", re.M)
BOLD = re.compile(r"\*\*(.+?)\*\*")
CODE = re.compile(r"`([^`]+)`")
BOXES = re.compile(r"^(?:判断：)?\s*\[ \].*$")


def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = BOLD.sub(r"<b>\1</b>", s)
    return CODE.sub(r"<code>\1</code>", s)


def md_to_html(md: str) -> str:
    """The small part of markdown the forms use: paragraphs, **bold**, `code`, > quotes, - lists, 4-space code, --- rules."""
    out, mode = [], None

    def close():
        nonlocal mode
        if mode:
            out.append({"quote": "</blockquote>", "list": "</ul>", "pre": "</pre>"}[mode])
            mode = None

    for line in md.split("\n"):
        if BOXES.match(line.strip()) or line.strip() == "---":
            continue  # the tick boxes of the paper form: the page has buttons instead
        if line.startswith("> ") or line == ">":
            if mode != "quote":
                close()
                out.append("<blockquote>")
                mode = "quote"
            body = line[2:]
            out.append(f"<p>{inline(body)}</p>" if body.strip() else "")
        elif line.startswith("- "):
            if mode != "list":
                close()
                out.append("<ul>")
                mode = "list"
            out.append(f"<li>{inline(line[2:])}</li>")
        elif line.startswith("    ") and line.strip():
            if mode != "pre":
                close()
                out.append("<pre>")
                mode = "pre"
            out.append(html.escape(line[4:], quote=False))
        elif not line.strip():
            close()
        else:
            close()
            out.append(f"<p>{inline(line)}</p>")
    close()
    return "\n".join(x for x in out if x != "")


PAGE = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root { --bg:#fbfaf7; --ink:#1b1b1a; --ink2:#55534e; --line:#dedcd3; --card:#ffffff; --accent:#2a78d6; --ok:#2e8f5c; --quote:#f3f2ec; }
@media (prefers-color-scheme: dark) { :root { --bg:#161615; --ink:#ecebe6; --ink2:#a5a39b; --line:#34332f; --card:#1f1f1d; --accent:#6aa8f0; --ok:#5fc08d; --quote:#262623; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font: 17px/1.75 system-ui, -apple-system, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; }
header { position:sticky; top:0; z-index:2; background:var(--bg); border-bottom:1px solid var(--line); padding:10px 16px; }
.row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; max-width:920px; margin:0 auto; }
.bar { flex:1; min-width:120px; height:8px; background:var(--line); border-radius:4px; overflow:hidden; }
.bar > i { display:block; height:100%; width:0; background:var(--ok); }
main { max-width:920px; margin:0 auto; padding:18px 16px 150px; }
h1 { font-size:20px; margin:0 0 4px; } h2 { font-size:19px; margin:6px 0 14px; }
.small { font-size:14px; color:var(--ink2); }
blockquote { margin:10px 0; padding:10px 14px; background:var(--quote); border-left:3px solid var(--line); border-radius:4px; overflow-wrap:anywhere; }
blockquote p { margin:0 0 6px; } p { margin:10px 0; overflow-wrap:anywhere; } ul { margin:8px 0; padding-left:22px; overflow-wrap:anywhere; }
pre { background:var(--quote); padding:10px 14px; border-radius:4px; white-space:pre-wrap; overflow-wrap:anywhere; font-size:15px; }
code { background:var(--quote); padding:1px 4px; border-radius:3px; font-size:15px; overflow-wrap:anywhere; }
footer { position:fixed; bottom:0; left:0; right:0; background:var(--card); border-top:1px solid var(--line); padding:10px 16px; }
button { font:inherit; border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:8px; padding:8px 14px; cursor:pointer; }
button.choice { min-width:92px; } button.choice.on { background:var(--accent); border-color:var(--accent); color:#fff; }
button:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
kbd { font:13px ui-monospace, Menlo, monospace; border:1px solid var(--line); border-radius:4px; padding:0 5px; margin-right:6px; color:var(--ink2); background:var(--bg); }
button.choice.on kbd { color:#fff; border-color:#ffffff88; background:transparent; }
input[type=text] { font:inherit; flex:1; min-width:160px; padding:7px 10px; border:1px solid var(--line); border-radius:8px; background:var(--card); color:var(--ink); }
details { margin:0 0 12px; } summary { cursor:pointer; color:var(--ink2); }
#done { display:none; padding:14px; border:1px solid var(--ok); border-radius:8px; margin:12px 0; }
</style></head><body>
<header><div class="row"><b id="pos"></b><div class="bar"><i id="fill"></i></div><span class="small" id="left"></span>
<button id="jump">跳到下一条没答的</button><button id="export">导出 __SAVEAS__</button>
<label class="small" style="cursor:pointer">载入之前导出的文件<input type="file" id="load" accept=".csv" style="display:none"></label></div></header>
<main>
<h1>__TITLE__</h1>
<p class="small" id="warn" style="display:none;color:#c9463d">这个浏览器不让本页保存进度：答完之前不要刷新或关掉页面；中途可以随时点“导出”存一份，回来用“载入之前导出的文件”接着答。</p>
<details id="intro"><summary>说明（点开看）</summary><p><b>在这个页面上作答不用管下面提到的 csv 文件</b>：按数字键或点按钮，答完点右上角“导出”。</p>__INTRO__</details>
<div id="done"><b>全部答完了。</b>点右上角“导出 __SAVEAS__”，浏览器会把文件存到“下载”文件夹，告诉我一声即可。</div>
<h2 id="head"></h2><div id="body"></div>
</main>
<footer><div class="row" id="choices"></div>
<div class="row" style="margin-top:8px"><button id="prev">← 上一条</button><button id="next">下一条 →</button>__NOTE__
<span class="small">按数字键作答并自动到下一条；← → 翻页；答案存在这个浏览器里，刷新不丢。</span></div></footer>
<script>
const DATA = __DATA__;
const KEY = "label-" + DATA.sha;
let st = {}; try { st = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { st = {}; }
st.a = st.a || {}; st.n = st.n || {}; let i = Math.min(st.i || 0, DATA.entries.length - 1);
const $ = id => document.getElementById(id);
let canStore = true;
function save() { st.i = i; try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) { canStore = false; } $("warn").style.display = canStore ? "none" : "block"; }
function parseCsv(text) {  // the page's own export: quoted cells, doubled quotes
  const rows = []; let row = [], cell = "", q = false;
  for (let k = 0; k < text.length; k++) { const c = text[k];
    if (q) { if (c === '"') { if (text[k + 1] === '"') { cell += '"'; k++; } else q = false; } else cell += c; }
    else if (c === '"') q = true; else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; } else if (c !== "\r") cell += c; }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows; }
function loadCsv(file) { const r = new FileReader(); r.onload = () => { let n = 0;
    const known = new Set(DATA.entries.map(e => e.id));
    parseCsv(String(r.result).replace(/^\uFEFF/, "")).slice(1).forEach(row => { const id = (row[0] || "").trim(), ans = (row[DATA.answerIdx] || "").trim();
      if (known.has(id) && DATA.choices.includes(ans)) { st.a[id] = ans; n++; } if (known.has(id) && DATA.noteIdx >= 0 && row[DATA.noteIdx]) st.n[id] = row[DATA.noteIdx]; });
    alert("载入了 " + n + " 条答案"); render(); }; r.readAsText(file, "utf-8"); }
function answered() { return DATA.entries.filter(e => st.a[e.id]).length; }
function render() {
  const e = DATA.entries[i];
  $("head").textContent = "条目 " + e.id; $("body").innerHTML = e.html;
  $("pos").textContent = (i + 1) + " / " + DATA.entries.length;
  const n = answered(); $("fill").style.width = (100 * n / DATA.entries.length) + "%";
  $("left").textContent = "已答 " + n + "，还剩 " + (DATA.entries.length - n);
  $("done").style.display = n === DATA.entries.length ? "block" : "none";
  const box = $("choices"); box.innerHTML = "";
  DATA.choices.forEach((c, k) => { const b = document.createElement("button"); b.className = "choice" + (st.a[e.id] === c ? " on" : "");
    b.innerHTML = "<kbd>" + (k + 1) + "</kbd>"; b.appendChild(document.createTextNode(c)); b.onclick = () => choose(c); box.appendChild(b); });
  const note = $("note"); if (note) note.value = st.n[e.id] || "";
  window.scrollTo(0, 0); save();
}
function choose(c) { const e = DATA.entries[i]; st.a[e.id] = c; save(); if (i < DATA.entries.length - 1) { i++; } render(); }
function go(d) { i = Math.max(0, Math.min(DATA.entries.length - 1, i + d)); render(); }
function jump() { for (let k = 1; k <= DATA.entries.length; k++) { const j = (i + k) % DATA.entries.length; if (!st.a[DATA.entries[j].id]) { i = j; break; } } render(); }
function csvText() {
  const rows = [DATA.header.join(",")].concat(DATA.entries.map(e => e.row.map((v, k) => csvCell(k === DATA.answerIdx ? (st.a[e.id] || "") : (k === DATA.noteIdx ? (st.n[e.id] || "") : v))).join(",")));
  return rows.join("\n") + "\n"; }
function csvCell(s) { s = String(s == null ? "" : s); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }
function exportCsv() {
  const missing = DATA.entries.length - answered();
  if (missing && !confirm("还有 " + missing + " 条没答，仍然导出吗？")) return;
  const blob = new Blob([csvText()], {type: "text/csv;charset=utf-8"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = DATA.saveAs; document.body.appendChild(a); a.click(); a.remove();
}
$("prev").onclick = () => go(-1); $("next").onclick = () => go(1); $("jump").onclick = jump; $("export").onclick = exportCsv;
$("load").onchange = ev => { if (ev.target.files[0]) loadCsv(ev.target.files[0]); ev.target.value = ""; };
const noteEl = $("note"); if (noteEl) noteEl.oninput = () => { st.n[DATA.entries[i].id] = noteEl.value; save(); };
document.addEventListener("keydown", ev => {
  if (ev.target && ev.target.tagName === "INPUT") return;
  if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
  const k = parseInt(ev.key, 10);
  if (k >= 1 && k <= DATA.choices.length) { choose(DATA.choices[k - 1]); ev.preventDefault(); }
  else if (ev.key === "ArrowLeft") go(-1); else if (ev.key === "ArrowRight") go(1);
});
if (!answered()) $("intro").open = true;
render();
</script></body></html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--form", type=Path, required=True)
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--choices", required=True, help="comma-separated, in key order")
    ap.add_argument("--save-as", required=True, help="file name the page offers when exporting")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--answer-column", default="", help="name of the column to fill (default: the template's last column that is not 'note')")
    a = ap.parse_args()
    md = a.form.read_text(encoding="utf-8")
    rows = list(csv.reader(open(a.template, encoding="utf-8-sig")))
    header, body_rows = rows[0], [r for r in rows[1:] if r and r[0].strip()]
    ids = [r[0] for r in body_rows]
    note_idx = header.index("note") if "note" in header else -1
    answer_idx = header.index(a.answer_column) if a.answer_column else max(k for k in range(1, len(header)) if k != note_idx)
    parts = ENTRY.split(md)
    intro, bodies = parts[0], {int(parts[k]): parts[k + 1] for k in range(1, len(parts) - 1, 2)}
    missing = [i for i in ids if int(i) not in bodies]
    if missing or len(bodies) != len(ids):
        raise SystemExit(f"form and template do not match: {len(bodies)} entries in the form, {len(ids)} in the template; without a form entry: {missing[:10]}")
    title = a.title or (md.lstrip().splitlines()[0].lstrip("# ").strip() if md.lstrip().startswith("#") else a.form.stem)
    intro_md = "\n".join(intro.splitlines()[1:]) if intro.lstrip().startswith("#") else intro
    data = {"sha": hashlib.sha256(md.encode("utf-8")).hexdigest()[:16], "choices": [c for c in a.choices.split(",") if c], "header": header,
            "saveAs": a.save_as, "answerIdx": answer_idx, "noteIdx": note_idx,
            "entries": [{"id": r[0], "row": (r + [""] * len(header))[:len(header)], "html": md_to_html(bodies[int(r[0])].strip("\n"))} for r in body_rows]}
    note = '<input type="text" id="note" placeholder="备注（可不填）">' if note_idx >= 0 else ""
    page = (PAGE.replace("__TITLE__", html.escape(title)).replace("__SAVEAS__", html.escape(a.save_as)).replace("__INTRO__", md_to_html(intro_md))
            .replace("__NOTE__", note).replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    a.out.write_text(page, encoding="utf-8")
    print(f"{len(ids)} entries, choices {data['choices']}, export {a.save_as} with header {header} (answers in '{header[answer_idx]}') -> {a.out} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
