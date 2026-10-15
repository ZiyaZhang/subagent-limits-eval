#!/usr/bin/env python3
"""Replace the BODY of an existing Feishu docx with a Markdown report and keep the document's own appendix.

For a page somebody else wrote, where the tail (from a given heading on) has to stay exactly as it is.
Order of the steps: everything that adds comes first, everything that removes comes last, so a failure in the
middle leaves the old content in place (plus the part already copied, which the script reports).

  1. BODY.md (without its image lines) is imported as a temporary docx; its block tree is copied to the START of the
     target, in batches of whole top-level blocks;
  2. the target's old top-level blocks from the start up to (not including) the kept heading are deleted;
  3. the images of BODY.md are uploaded and placed before their caption lines;
  4. the headings inside the kept tail are raised by --raise levels (a new heading with the same text is created at
     the same place, then the old one is removed; no other block of the tail is touched);
  5. EXTRA.md (optional) is imported and inserted inside the tail, before the heading named by --extra-before;
  6. the section named by --drop-section (a heading of the kept tail and what follows it up to the next heading of
     the same or a higher level) is removed: for a section of the tail that the new body now carries itself;
  7. the temporary documents are deleted; the kept blocks are compared with their state before the run.

Usage: feishu_replace_body.py BODY.md --doc TOKEN --keep-from 附录 [--raise 1] [--extra EXTRA.md --extra-before 题目]
                              [--drop-section 方法补充] [--dry-run]
--dry-run stops after reading the target and the Markdown: it prints what would be deleted and kept.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import feishu_publish as fp  # noqa: E402
import feishu_update as fu  # noqa: E402

HEAD = {3: "heading1", 4: "heading2", 5: "heading3", 6: "heading4", 7: "heading5", 8: "heading6"}


def htext(b: dict) -> str:
    k = HEAD.get(b["block_type"])
    return "".join((e.get("text_run") or {}).get("content", "") for e in b[k]["elements"]).strip() if k else ""


def import_md(token: str, text: str, name: str) -> str:
    ft = fp.upload(token, "report.md", text.encode("utf-8"), "ccm_import_open", "", extra=json.dumps({"obj_type": "docx", "file_extension": "md"}))
    ticket = fp.call("POST", "/drive/v1/import_tasks", token, body={"file_extension": "md", "file_token": ft, "type": "docx", "file_name": name,
                                                                     "point": {"mount_type": 1, "mount_key": ""}})["data"]["ticket"]
    for _ in range(120):
        time.sleep(2)
        res = fp.call("GET", f"/drive/v1/import_tasks/{ticket}", token)["data"]["result"]
        if res.get("job_status") == 0:
            return res["token"]
        if res.get("job_status") not in (1, 2):
            sys.exit(f"import failed: status {res.get('job_status')} {res.get('job_error_msg')}")
    sys.exit("import did not finish in 4 minutes")


def copy_tree(token: str, temp: str, doc: str, root_id: str, index: int) -> int:
    """Copy the temporary document's whole tree into the target before top-level position `index`; returns how many
    top-level blocks were added."""
    src = fp.all_blocks(token, temp)
    by = {b["block_id"]: b for b in src}
    top = next(b for b in src if b["block_type"] == 1)["children"]
    cleaned = {bid: fu.clean(b, by) for bid, b in by.items() if b["block_type"] != 1}  # raises before any change on an unknown type
    batches, cur, size = [], [], 0
    for bid in top:
        n = len(fu.subtree(by, bid))
        if n > fu.BATCH + 100:
            sys.exit(f"one top-level block has {n} blocks; too large for one request")
        if cur and size + n > fu.BATCH:
            batches.append(cur)
            cur, size = [], 0
        cur.append(bid)
        size += n
    if cur:
        batches.append(cur)
    added = 0
    for i, batch in enumerate(batches):
        desc = [cleaned[x["block_id"]] for bid in batch for x in fu.subtree(by, bid)]
        try:
            fp.call("POST", f"/docx/v1/documents/{doc}/blocks/{root_id}/descendant?document_revision_id=-1", token,
                    body={"index": index + added, "children_id": batch, "descendants": desc})
        except SystemExit as e:
            sys.exit(f"copy failed at batch {i + 1}/{len(batches)} ({e}); nothing was deleted; {added} new top-level blocks sit at index {index}")
        added += len(batch)
        print(f"  batch {i + 1}/{len(batches)}: {len(batch)} top-level, {len(desc)} blocks")
        time.sleep(0.5)
    return added


def digest(b: dict) -> str:
    return hashlib.sha1(json.dumps({k: v for k, v in b.items() if k != "comment_ids"}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def tree_ids(by: dict, ids: list) -> list:
    out, stack = [], list(ids)
    while stack:
        x = stack.pop()
        out.append(x)
        stack += by[x].get("children") or []
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("body", type=Path)
    ap.add_argument("--doc", required=True)
    ap.add_argument("--keep-from", required=True, help="text of the top-level heading where the kept tail starts")
    ap.add_argument("--start-at", help="text of the top-level heading where the part to replace starts; what stands before it is kept as it is")
    ap.add_argument("--raise", dest="lift", type=int, default=0, help="raise the headings of the kept tail by this many levels")
    ap.add_argument("--extra", type=Path)
    ap.add_argument("--extra-before", help="text of the heading in the kept tail before which EXTRA.md is inserted")
    ap.add_argument("--drop-section", help="text of a heading in the kept tail: that section is removed from the tail")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    lines = a.body.read_text(encoding="utf-8").splitlines()
    images, kept = [], []
    for i, line in enumerate(lines):
        m = re.match(r"^!\[[^\]]*\]\(([^)]+)\)\s*$", line)
        if m:
            nxt = next((x for x in lines[i + 1:] if x.strip()), "")
            images.append((a.body.parent / m.group(1), nxt.strip()[:12]))
            continue
        kept.append(line)
    for path, _ in images:
        if not path.exists():
            sys.exit(f"missing image {path}")
    app_id, secret = fp.creds()
    token = fp.call("POST", "/auth/v3/tenant_access_token/internal", body={"app_id": app_id, "app_secret": secret})["tenant_access_token"]

    before = fp.all_blocks(token, a.doc)
    by0 = {b["block_id"]: b for b in before}
    root = next(b for b in before if b["block_type"] == 1)
    kids0 = list(root.get("children") or [])
    k = next((i for i, c in enumerate(kids0) if htext(by0[c]) == a.keep_from), None)
    if k is None:
        sys.exit(f"no top-level heading with the text {a.keep_from!r}; nothing was changed")
    h = 0
    if a.start_at:
        h = next((i for i, c in enumerate(kids0) if htext(by0[c]) == a.start_at), None)
        if h is None or h >= k:
            sys.exit(f"no top-level heading {a.start_at!r} before {a.keep_from!r}; nothing was changed")
    head = kids0[:h]
    tail = kids0[k:]
    tail_heads = [c for c in tail if by0[c]["block_type"] in HEAD]
    drop = []
    if a.drop_section:
        d0 = next((i for i, c in enumerate(tail) if htext(by0[c]) == a.drop_section), None)
        if d0 is None or d0 == 0:
            sys.exit(f"no heading {a.drop_section!r} inside the kept tail (after its first heading); nothing was changed")
        level = by0[tail[d0]]["block_type"]
        d1 = next((i for i in range(d0 + 1, len(tail)) if by0[tail[i]]["block_type"] in HEAD and by0[tail[i]]["block_type"] <= level), len(tail))
        drop = tail[d0:d1]
        print(f"section to drop from the tail: {len(drop)} top-level blocks:")
        for c in drop:
            print("   ", by0[c]["block_type"], repr(fp.block_text(by0[c])[:70]))
    drop_tree = set(tree_ids(by0, drop))
    kept_ids = tree_ids(by0, head) + [x for x in tree_ids(by0, tail) if x not in drop_tree and not (a.lift and x in tail_heads)]
    kept_digest = {x: digest(by0[x]) for x in kept_ids}
    if a.lift and any(by0[c]["block_type"] - a.lift < 3 for c in tail_heads):
        sys.exit("a heading of the kept tail cannot be raised that far; nothing was changed")
    caps = [cap for _, cap in images]
    clash = [cap for cap in caps if any(fp.block_text(by0[c]).strip().startswith(cap) for c in tail + head)]
    if clash:
        sys.exit(f"captions {clash} also start a block of the kept parts; nothing was changed")
    print(f"target: {len(before)} blocks, {len(kids0)} top-level; kept head = top-level 0..{h - 1} ({len(tree_ids(by0, head))} blocks); body to replace = top-level {h}..{k - 1}; kept tail = {len(tail)} top-level blocks "
          f"({len(tree_ids(by0, tail))} blocks, headings: {[htext(by0[c]) for c in tail_heads]})")
    print(f"new body: {len(kept)} lines, {len(images)} images")
    if a.dry_run:
        return

    # 1. new body in front of everything
    temp = import_md(token, "\n".join(kept) + "\n", "tmp-body")
    added = copy_tree(token, temp, a.doc, root["block_id"], h)
    print(f"1. new body copied: {added} top-level blocks at position {h}")
    # 2. remove the old body (it now sits right after the new one)
    if k - h:
        fp.call("DELETE", f"/docx/v1/documents/{a.doc}/blocks/{root['block_id']}/children/batch_delete?document_revision_id=-1", token,
                body={"start_index": h + added, "end_index": added + k})
        print(f"2. old body removed: {k - h} top-level blocks")
        time.sleep(0.5)
    # 3. images
    for path, cap in images:
        blocks = fp.all_blocks(token, a.doc)
        by_t = {b["block_id"]: b for b in blocks}
        children = next(b for b in blocks if b["block_type"] == 1)["children"]
        idx = next((n for n, c in enumerate(children) if fp.block_text(by_t[c]).strip().startswith(cap)), None)
        if idx is None:
            print(f"   caption not found for {path.name} ({cap!r}); image skipped")
            continue
        made = fp.call("POST", f"/docx/v1/documents/{a.doc}/blocks/{root['block_id']}/children", token,
                       body={"index": idx, "children": [{"block_type": 27, "image": {}}]})["data"]["children"][0]
        ftok = fp.upload(token, path.name, path.read_bytes(), "docx_image", made["block_id"])
        fp.call("PATCH", f"/docx/v1/documents/{a.doc}/blocks/{made['block_id']}", token, body={"replace_image": {"token": ftok}})
        time.sleep(0.4)
    print(f"3. {len(images)} images placed")
    # 4. raise the headings of the kept tail
    if a.lift:
        for old in tail_heads:
            children = next(b for b in fp.all_blocks(token, a.doc) if b["block_type"] == 1)["children"]
            i = children.index(old)
            b = by0[old]
            key_old, t_new = HEAD[b["block_type"]], b["block_type"] - a.lift
            content = {"elements": b[key_old]["elements"], "style": {"align": (b[key_old].get("style") or {}).get("align", 1)}}
            fp.call("POST", f"/docx/v1/documents/{a.doc}/blocks/{root['block_id']}/children", token,
                    body={"index": i, "children": [{"block_type": t_new, HEAD[t_new]: content}]})
            fp.call("DELETE", f"/docx/v1/documents/{a.doc}/blocks/{root['block_id']}/children/batch_delete?document_revision_id=-1", token,
                    body={"start_index": i + 1, "end_index": i + 2})
            time.sleep(0.4)
        print(f"4. {len(tail_heads)} headings of the kept tail raised by {a.lift}")
    # 5. extra section inside the tail
    temp2 = None
    if a.extra:
        blocks = fp.all_blocks(token, a.doc)
        by_t = {b["block_id"]: b for b in blocks}
        children = next(b for b in blocks if b["block_type"] == 1)["children"]
        start = next(n for n, c in enumerate(children) if htext(by_t[c]) == a.keep_from)
        at = next((n for n, c in enumerate(children) if n > start and htext(by_t[c]) == a.extra_before), None) if a.extra_before else len(children)
        if at is None:
            sys.exit(f"heading {a.extra_before!r} not found in the kept tail; the extra section was not inserted (everything else is done)")
        temp2 = import_md(token, a.extra.read_text(encoding="utf-8"), "tmp-extra")
        n2 = copy_tree(token, temp2, a.doc, root["block_id"], at)
        print(f"5. extra section inserted: {n2} top-level blocks before {a.extra_before!r}")
    # 6. drop a section of the tail that the new body carries itself
    if drop:
        children = next(b for b in fp.all_blocks(token, a.doc) if b["block_type"] == 1)["children"]
        i0 = children.index(drop[0])
        if children[i0:i0 + len(drop)] != drop:
            sys.exit("the section to drop is not where it was; it was left in place (everything else is done)")
        fp.call("DELETE", f"/docx/v1/documents/{a.doc}/blocks/{root['block_id']}/children/batch_delete?document_revision_id=-1", token,
                body={"start_index": i0, "end_index": i0 + len(drop)})
        print(f"6. section {a.drop_section!r} removed from the tail: {len(drop)} top-level blocks")
        time.sleep(0.5)
    # 7. clean up and compare
    for t in (temp, temp2):
        if t:
            try:
                fp.call("DELETE", f"/drive/v1/files/{t}?type=docx", token)
            except SystemExit as e:
                print(f"   temporary document {t} not deleted ({str(e)[:100]}); it is not shared with anyone")
    after = fp.all_blocks(token, a.doc)
    by1 = {b["block_id"]: b for b in after}
    missing = [x for x in kept_digest if x not in by1]
    changed = [x for x in kept_digest if x in by1 and digest(by1[x]) != kept_digest[x]]
    top1 = next(b for b in after if b["block_type"] == 1)["children"]
    print(f"7. target now has {len(after)} blocks, {len(top1)} top-level; kept blocks: {len(kept_digest)} checked, {len(missing)} missing, {len(changed)} changed")
    if missing or changed:
        sys.exit("some kept blocks differ from before: look at them before doing anything else")


if __name__ == "__main__":
    main()
