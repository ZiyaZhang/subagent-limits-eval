#!/usr/bin/env python3
"""Replace the whole content of an existing Feishu docx with a Markdown report, keeping the document's URL.

Steps (tenant token of the lark-mcp app, read from ~/.claude.json and never printed):
  1. the Markdown without its image lines is imported as a temporary docx (same import as feishu_publish.py);
  2. the temporary document's block tree is copied to the END of the target document, in batches of whole top-level
     blocks (nested-block API, at most 900 blocks per request);
  3. only after every batch succeeded, the target's old top-level blocks are deleted;
  4. the images are uploaded and placed before their caption lines (same rule as feishu_publish.py);
  5. the temporary document is deleted.
If step 2 fails the target still holds its old content, followed by the part that was copied; the script says so.

With --insert-at N the Markdown is inserted before the target's N-th top-level block instead (nothing is deleted and
images are not handled): a way to add a notice to a published document.

Usage: feishu_update.py REPORT.md --doc TARGET_TOKEN [--keep-temp] [--insert-at N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import feishu_publish as fp  # noqa: E402

TEXT_KEYS = {2: "text", 3: "heading1", 4: "heading2", 5: "heading3", 6: "heading4", 7: "heading5", 8: "heading6", 12: "bullet",
             13: "ordered", 14: "code", 15: "quote", 17: "todo"}
BATCH = 900


def text_px(s: str) -> int:
    """Rough rendered width of a cell text: a CJK character about 15 px, anything else about 8 px."""
    return sum(15 if ord(c) > 0x2E7F else 8 for c in s)


def column_widths(b: dict, by: dict) -> list:
    """Column widths that fit the cell texts: each column as wide as its longest cell, between 72 and 320 px; when the
    table is narrower than the page (730 px) the spare width goes to the columns that were capped."""
    rows_, cols = b["table"]["property"]["row_size"], b["table"]["property"]["column_size"]
    need = [72] * cols
    for i, cid in enumerate(b.get("children") or []):
        txt = max((fp.block_text(by[c]) for c in by[cid].get("children") or []), key=len, default="")
        need[i % cols] = max(need[i % cols], text_px(txt) + 26)
    w = [min(n, 320) for n in need]
    spare = 730 - sum(w)
    short = [n - x for n, x in zip(need, w)]
    if spare > 0 and sum(short) > 0:
        w = [x + min(sh, int(spare * sh / sum(short))) for x, sh in zip(w, short)]
    return w


def clean(b: dict, by: dict) -> dict:
    """A block as the nested-block API accepts it: id, type, children and its own content, without read-only fields."""
    t = b["block_type"]
    out = {"block_id": b["block_id"], "block_type": t, "children": list(b.get("children") or [])}
    if t in TEXT_KEYS:
        out[TEXT_KEYS[t]] = b[TEXT_KEYS[t]]
    elif t == 31:
        prop = {k: v for k, v in b["table"]["property"].items() if k in ("row_size", "column_size", "header_row")}
        prop["column_width"] = column_widths(b, by)
        out["table"] = {"property": prop}
    elif t == 32:
        out["table_cell"] = {}
    elif t == 34:
        out["quote_container"] = {}
    elif t == 22:
        out["divider"] = {}
    else:
        raise SystemExit(f"block type {t} is not handled; nothing was changed yet" )
    return out


def subtree(by: dict, bid: str) -> list:
    out = [by[bid]]
    for c in by[bid].get("children") or []:
        out += subtree(by, c)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", type=Path)
    ap.add_argument("--doc", required=True)
    ap.add_argument("--keep-temp", action="store_true")
    ap.add_argument("--insert-at", type=int, help="insert before this top-level index; keep the old content")
    ap.add_argument("--domain", default="trtgsjkv6r.feishu.cn")
    a = ap.parse_args()
    lines = a.report.read_text(encoding="utf-8").splitlines()
    images, kept = [], []
    for i, line in enumerate(lines):
        m = re.match(r"^!\[[^\]]*\]\(([^)]+)\)\s*$", line)
        if m:
            nxt = next((x for x in lines[i + 1:] if x.strip()), "")
            images.append((a.report.parent / m.group(1), nxt.strip()[:12]))
            continue
        kept.append(line)
    for path, _ in images:
        if not path.exists():
            sys.exit(f"missing image {path}")
    app_id, secret = fp.creds()
    token = fp.call("POST", "/auth/v3/tenant_access_token/internal", body={"app_id": app_id, "app_secret": secret})["tenant_access_token"]

    # 1. import as a temporary document
    ft = fp.upload(token, "report.md", ("\n".join(kept) + "\n").encode("utf-8"), "ccm_import_open", "",
                   extra=json.dumps({"obj_type": "docx", "file_extension": "md"}))
    ticket = fp.call("POST", "/drive/v1/import_tasks", token,
                     body={"file_extension": "md", "file_token": ft, "type": "docx", "file_name": "tmp-" + a.report.stem,
                           "point": {"mount_type": 1, "mount_key": ""}})["data"]["ticket"]
    temp = None
    for _ in range(120):
        time.sleep(2)
        res = fp.call("GET", f"/drive/v1/import_tasks/{ticket}", token)["data"]["result"]
        if res.get("job_status") == 0:
            temp = res["token"]
            break
        if res.get("job_status") not in (1, 2):
            sys.exit(f"import failed: status {res.get('job_status')} {res.get('job_error_msg')}")
    if not temp:
        sys.exit("import did not finish in 4 minutes")
    src = fp.all_blocks(token, temp)
    by = {b["block_id"]: b for b in src}
    top = next(b for b in src if b["block_type"] == 1)["children"]
    print(f"temporary document {temp}: {len(src)} blocks, {len(top)} top-level")
    cleaned = {bid: clean(b, by) for bid, b in by.items() if b["block_type"] != 1}   # raises before any change on an unknown type

    # 2. copy to the end of the target
    root = next(b for b in fp.all_blocks(token, a.doc) if b["block_type"] == 1)
    old_n = len(root.get("children") or [])
    batches, cur, size = [], [], 0
    for bid in top:
        n = len(subtree(by, bid))
        if n > BATCH + 100:
            sys.exit(f"one top-level block has {n} blocks; too large for one request")
        if cur and size + n > BATCH:
            batches.append(cur)
            cur, size = [], 0
        cur.append(bid)
        size += n
    if cur:
        batches.append(cur)
    index = old_n if a.insert_at is None else min(a.insert_at, old_n)
    start_index = index
    for i, batch in enumerate(batches):
        desc = [cleaned[x["block_id"]] for bid in batch for x in subtree(by, bid)]
        try:
            fp.call("POST", f"/docx/v1/documents/{a.doc}/blocks/{root['block_id']}/descendant?document_revision_id=-1", token,
                    body={"index": index, "children_id": batch, "descendants": desc})
        except SystemExit as e:
            sys.exit(f"copy failed at batch {i + 1}/{len(batches)} ({e}); the target keeps its old content plus {index - start_index} new top-level blocks at index {start_index}")
        index += len(batch)
        print(f"batch {i + 1}/{len(batches)}: {len(batch)} top-level, {len(desc)} blocks")
        time.sleep(0.5)

    # 3. delete the old content
    if a.insert_at is not None:
        images = []
        print(f"inserted {index - start_index} top-level blocks at index {start_index}; old content kept")
    elif old_n:
        fp.call("DELETE", f"/docx/v1/documents/{a.doc}/blocks/{root['block_id']}/children/batch_delete?document_revision_id=-1", token,
                body={"start_index": 0, "end_index": old_n})
        print(f"deleted {old_n} old top-level blocks")
        time.sleep(0.5)

    # 4. images
    for path, cap in images:
        blocks = fp.all_blocks(token, a.doc)
        by_t = {b["block_id"]: b for b in blocks}
        children = next(b for b in blocks if b["block_type"] == 1)["children"]
        idx = next((n for n, c in enumerate(children) if fp.block_text(by_t[c]).strip().startswith(cap)), None)
        if idx is None:
            print(f"caption not found for {path.name} ({cap!r}); image skipped")
            continue
        made = fp.call("POST", f"/docx/v1/documents/{a.doc}/blocks/{root['block_id']}/children", token,
                       body={"index": idx, "children": [{"block_type": 27, "image": {}}]})["data"]["children"][0]
        ftok = fp.upload(token, path.name, path.read_bytes(), "docx_image", made["block_id"])
        fp.call("PATCH", f"/docx/v1/documents/{a.doc}/blocks/{made['block_id']}", token, body={"replace_image": {"token": ftok}})
        print(f"image {path.name} placed before {cap!r}")
        time.sleep(0.4)

    # 5. remove the temporary document
    if not a.keep_temp:
        try:
            fp.call("DELETE", f"/drive/v1/files/{temp}?type=docx", token)
            print("temporary document deleted")
        except SystemExit as e:
            print(f"temporary document {temp} not deleted ({str(e)[:120]}); it is not shared with anyone")
    final = fp.all_blocks(token, a.doc)
    print(f"target now has {len(final)} blocks\nurl https://{a.domain}/docx/{a.doc}")


if __name__ == "__main__":
    main()
