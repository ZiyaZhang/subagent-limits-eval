#!/usr/bin/env python3
"""Small, additive edits of a Feishu docx through the open API (tenant token of the lark-mcp app; never printed).

Inserts: new blocks under a parent at an index, new images with captions, new table rows. Every write first checks
that the anchor block still sits where the plan says (by block id), so a page that changed in between is not touched.
Existing text is changed in two ways only, both checked against the text the caller expects: Doc.correct() strikes
a phrase through (it stays readable) and puts the corrected wording right after it; Doc.rewrite() replaces a block's
text. Doc.delete(), Doc.replace_image() and the table-row calls change structure; each one names the block by id and
verifies the neighbours before and after. The caller keeps the record of what was there (see wiki_apply.py).

Library use (see scripts/wiki_apply.py):
    d = Doc(token)                              # reads the block tree
    d.insert(parent_id, index, [blocks])        # blocks from text()/bullet()/ordered()/heading()/table()
    d.insert_image(parent_id, index, path, caption)
    d.add_table_rows(table_id, [[cell, ...], ...])
    d.correct(block_id, expected_text, [(phrase, new_markup), ...])   # strike phrase, add new_markup after it
Inline markup of the text helpers: **bold**; everything else is literal.
"""
from __future__ import annotations

import copy
import re
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import feishu_publish as fp  # noqa: E402

KEY = {2: "text", 7: "heading5", 12: "bullet", 13: "ordered"}
STYLE_KEYS = ("bold", "italic", "strikethrough", "underline", "inline_code", "text_color", "background_color", "link")


def plain(elements: list) -> str:
    return "".join(e["text_run"]["content"] for e in elements)


def struck(elements: list, edits: list) -> list:
    """Elements of a text block with each (phrase, new_markup) of `edits` applied: the phrase keeps its place and
    style and gets a strike-through; new_markup (**bold** allowed, may be empty) follows it in the phrase's style
    without the strike and without bold. Every phrase must occur exactly once. Only plain text runs are handled."""
    els = []
    for e in elements:
        if set(e) != {"text_run"}:
            raise ValueError(f"not a plain text run: {list(e)}")
        st = e["text_run"].get("text_element_style") or {}
        if set(st) - set(STYLE_KEYS):
            raise ValueError(f"style keys this helper would lose: {sorted(set(st) - set(STYLE_KEYS))}")
        els.append({"text_run": {"content": e["text_run"]["content"], "text_element_style": copy.deepcopy(st)}})
    for phrase, new in edits:
        full = plain(els)
        if full.count(phrase) != 1:
            raise ValueError(f"phrase occurs {full.count(phrase)} times: {phrase!r}")
        a = full.index(phrase)
        b = a + len(phrase)
        out, pos, added = [], 0, False
        for e in els:
            c, st = e["text_run"]["content"], e["text_run"]["text_element_style"]
            lo, hi = pos, pos + len(c)
            pos = hi
            if hi <= a or lo >= b:
                out.append(e)
                continue
            if st.get("strikethrough"):
                raise ValueError(f"already struck: {phrase!r}")
            cut = [(c[:max(a - lo, 0)], False), (c[max(a - lo, 0):min(b, hi) - lo], True), (c[min(b, hi) - lo:], False)]
            for part, strike in cut:
                if part:
                    out.append({"text_run": {"content": part, "text_element_style": dict(st, strikethrough=True) if strike else dict(st)}})
                if strike and hi >= b and new and not added:
                    base = {k: v for k, v in st.items() if k not in ("strikethrough", "bold", "link")}
                    for r in runs(new):
                        r["text_run"]["text_element_style"] = dict(base, bold=r["text_run"]["text_element_style"]["bold"])
                        out.append(r)
                    added = True
        els = out
    return els


def runs(markup: str, color: int | None = None) -> list:
    out = []
    for i, part in enumerate(re.split(r"\*\*(.+?)\*\*", markup)):
        if not part:
            continue
        style = {"bold": i % 2 == 1}
        if color:
            style["text_color"] = color
        out.append({"text_run": {"content": part, "text_element_style": style}})
    return out


def para(block_type: int, markup: str, color: int | None = None, bold_all: bool = False) -> dict:
    els = runs(markup, color)
    if bold_all:
        for e in els:
            e["text_run"]["text_element_style"]["bold"] = True
    return {"block_type": block_type, KEY[block_type]: {"elements": els, "style": {}}}


def text(markup: str, color: int | None = None) -> dict:
    return para(2, markup, color)


def bullet(markup: str) -> dict:
    return para(12, markup)


def ordered(markup: str) -> dict:
    b = para(13, markup)
    b["ordered"]["style"] = {"sequence": "auto"}
    return b


def heading5(markup: str, bold: bool = False) -> dict:
    return para(7, markup, bold_all=bold)


class Doc:
    def __init__(self, doc: str):
        self.doc = doc
        app_id, secret = fp.creds()
        self.token = fp.call("POST", "/auth/v3/tenant_access_token/internal", body={"app_id": app_id, "app_secret": secret})["tenant_access_token"]
        self.reload()

    def reload(self) -> None:
        self.blocks = fp.all_blocks(self.token, self.doc)
        self.by = {b["block_id"]: b for b in self.blocks}
        self.root = next(b for b in self.blocks if b["block_type"] == 1)

    def children(self, parent: str) -> list:
        return list(self.by[parent].get("children") or [])

    def expect(self, parent: str, index: int, before: str | None, after: str | None) -> None:
        """The new blocks go to `index` under `parent`: the block now at index-1 must be `before`, the one at index `after`."""
        self.reload()
        ch = self.children(parent)
        got_before = ch[index - 1] if index > 0 else None
        got_after = ch[index] if index < len(ch) else None
        if before is not None and got_before != before:
            sys.exit(f"anchor moved: block before index {index} is {got_before}, expected {before}; nothing written")
        if after is not None and got_after != after:
            sys.exit(f"anchor moved: block at index {index} is {got_after}, expected {after}; nothing written")

    def insert(self, parent: str, index: int, blocks: list) -> list:
        made = fp.call("POST", f"/docx/v1/documents/{self.doc}/blocks/{parent}/children?document_revision_id=-1", self.token,
                       body={"index": index, "children": blocks})["data"]["children"]
        time.sleep(0.4)
        return [m["block_id"] for m in made]

    def insert_image(self, parent: str, index: int, path: Path, caption: str) -> str:
        bid = self.insert(parent, index, [{"block_type": 27, "image": {}}])[0]
        ftok = fp.upload(self.token, path.name, path.read_bytes(), "docx_image", bid)
        fp.call("PATCH", f"/docx/v1/documents/{self.doc}/blocks/{bid}?document_revision_id=-1", self.token,
                body={"replace_image": {"token": ftok, "align": 2, "caption": {"content": caption}}})
        time.sleep(0.4)
        return bid

    def insert_table(self, parent: str, index: int, rows: list, widths: list, header_bold: bool = False) -> str:
        """rows: list of rows of markup strings. Built with the nested-block request so the cells arrive filled."""
        nr, nc = len(rows), len(rows[0])
        tid = "t" + uuid.uuid4().hex[:8]
        desc, cells = [], []
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                cid, xid = f"c{r}_{c}_{tid}", f"x{r}_{c}_{tid}"
                p = text(cell)
                if r == 0 and header_bold:
                    for e in p["text"]["elements"]:
                        e["text_run"]["text_element_style"]["bold"] = True
                p["block_id"], p["children"] = xid, []
                desc.append({"block_id": cid, "block_type": 32, "table_cell": {}, "children": [xid]})
                desc.append(p)
                cells.append(cid)
        table = {"block_id": tid, "block_type": 31, "children": cells,
                 "table": {"property": {"row_size": nr, "column_size": nc, "column_width": widths}}}
        res = fp.call("POST", f"/docx/v1/documents/{self.doc}/blocks/{parent}/descendant?document_revision_id=-1", self.token,
                      body={"index": index, "children_id": [tid], "descendants": [table] + desc})
        time.sleep(0.4)
        rel = (res.get("data") or {}).get("block_id_relations") or []
        return next((x["block_id"] for x in rel if x.get("temporary_block_id") == tid), "")

    def correct(self, block: str, expected: str, edits: list, dry_run: bool = False) -> dict:
        """Strike phrases of an existing text block and put the corrected wording after each (see struck()). The block
        must read exactly `expected` now. Returns {"before": elements, "after": elements} for the record."""
        self.reload()
        b = self.by[block]
        key = next(k for k in ("text", "bullet", "ordered", "heading1", "heading2", "heading3", "heading4", "heading5", "heading6") if k in b)
        before = b[key]["elements"]
        if plain(before) != expected:
            sys.exit(f"block {block} no longer reads as expected; nothing written\n  now:      {plain(before)!r}\n  expected: {expected!r}")
        after = struck(before, edits)
        if not dry_run:
            fp.call("PATCH", f"/docx/v1/documents/{self.doc}/blocks/{block}?document_revision_id=-1", self.token,
                    body={"update_text_elements": {"elements": after}})
            time.sleep(0.4)
        return {"before": before, "after": after}

    def rewrite(self, block: str, expected: str, elements: list, dry_run: bool = False) -> dict:
        """Replace the text of a block that reads exactly `expected` now. Returns {"before", "after"} elements."""
        self.reload()
        b = self.by[block]
        key = next(k for k in ("text", "bullet", "ordered", "heading1", "heading2", "heading3", "heading4", "heading5", "heading6") if k in b)
        before = b[key]["elements"]
        if plain(before) != expected:
            sys.exit(f"block {block} no longer reads as expected; nothing written\n  now:      {plain(before)!r}\n  expected: {expected!r}")
        if not dry_run:
            fp.call("PATCH", f"/docx/v1/documents/{self.doc}/blocks/{block}?document_revision_id=-1", self.token,
                    body={"update_text_elements": {"elements": elements}})
            time.sleep(0.4)
        return {"before": before, "after": elements}

    def delete(self, parent: str, block: str) -> None:
        """Remove one child of `parent`. The API deletes by position, so the position is looked up right before the
        call and the result is checked: exactly this block is gone and its neighbours are where they were."""
        self.reload()
        ch = self.children(parent)
        i = ch.index(block)
        fp.call("DELETE", f"/docx/v1/documents/{self.doc}/blocks/{parent}/children/batch_delete?document_revision_id=-1", self.token,
                body={"start_index": i, "end_index": i + 1})
        time.sleep(0.5)
        self.reload()
        now = self.children(parent)
        if now != ch[:i] + ch[i + 1:]:
            sys.exit(f"after deleting {block} the children of {parent} are not the old list minus that block; stop and look")

    def replace_image(self, block: str, path: Path, caption: str | None = None) -> dict:
        """Put another picture into an existing image block (same block id and place). Returns the old token and caption."""
        self.reload()
        old = self.by[block]["image"]
        ftok = fp.upload(self.token, path.name, path.read_bytes(), "docx_image", block)
        body = {"replace_image": {"token": ftok}}
        if caption is not None:
            body["replace_image"]["caption"] = {"content": caption}
        fp.call("PATCH", f"/docx/v1/documents/{self.doc}/blocks/{block}?document_revision_id=-1", self.token, body=body)
        time.sleep(0.4)
        return {"old_token": old.get("token"), "old_caption": (old.get("caption") or {}).get("content"), "new_token": ftok}

    def insert_table_row(self, table: str, row_index: int, cells: list) -> None:
        """Insert one row at row_index (0-based, -1 = end) and fill it (None = leave the cell empty)."""
        fp.call("PATCH", f"/docx/v1/documents/{self.doc}/blocks/{table}?document_revision_id=-1", self.token,
                body={"insert_table_row": {"row_index": row_index}})
        time.sleep(0.4)
        self.reload()
        t = self.by[table]
        nc = t["table"]["property"]["column_size"]
        nr = t["table"]["property"]["row_size"]
        r = row_index if row_index >= 0 else nr - 1
        for cid, cell in zip(t["children"][r * nc:(r + 1) * nc], cells):
            if cell is None:
                continue
            kids = self.children(cid)
            if kids and not fp.block_text(self.by[kids[0]]).strip():
                fp.call("PATCH", f"/docx/v1/documents/{self.doc}/blocks/{kids[0]}?document_revision_id=-1", self.token,
                        body={"update_text_elements": {"elements": runs(cell)}})
            else:
                self.insert(cid, len(kids), [text(cell)])
            time.sleep(0.3)

    def delete_table_rows(self, table: str, start: int, end: int) -> None:
        """Delete rows start..end-1 (0-based) of a table."""
        fp.call("PATCH", f"/docx/v1/documents/{self.doc}/blocks/{table}?document_revision_id=-1", self.token,
                body={"delete_table_rows": {"row_start_index": start, "row_end_index": end}})
        time.sleep(0.4)

    def add_table_rows(self, table: str, rows: list) -> None:
        """Append rows to an existing table and fill the first len(row) cells of each new row."""
        for row in rows:
            fp.call("PATCH", f"/docx/v1/documents/{self.doc}/blocks/{table}?document_revision_id=-1", self.token,
                    body={"insert_table_row": {"row_index": -1}})
            time.sleep(0.4)
            self.reload()
            t = self.by[table]
            nc = t["table"]["property"]["column_size"]
            last = t["children"][-nc:]
            for cid, cell in zip(last, row):
                if cell is None:
                    continue
                kids = self.children(cid)
                if kids and not fp.block_text(self.by[kids[0]]).strip():
                    fp.call("PATCH", f"/docx/v1/documents/{self.doc}/blocks/{kids[0]}?document_revision_id=-1", self.token,
                            body={"update_text_elements": {"elements": runs(cell)}})
                else:
                    self.insert(cid, len(kids), [text(cell)])
                time.sleep(0.3)
