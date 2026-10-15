#!/usr/bin/env python3
"""Publish a Markdown report as a Feishu docx, with its figures, and give one user full access.

Steps (Feishu open API, tenant token of the lark-mcp app; the app id and secret are read from ~/.claude.json and
never printed):
  1. the Markdown without its image lines is uploaded and imported as a new docx (drive import task);
  2. the user (open_id) is added as a collaborator with full_access;
  3. for every image line `![alt](path)` in the Markdown, an image block is created in the document right before
     the block whose text starts with the caption that follows the image line, the PNG is uploaded into that block
     and the block is pointed at it.

Usage: feishu_publish.py REPORT.md --title TEXT --openid ou_xxx [--domain trtgsjkv6r.feishu.cn]
Prints the document token and URL.
"""
from __future__ import annotations

import argparse
import json
import socket
import mimetypes
import os
import re
import sys
import time
import urllib.error
import http.client
import urllib.request
import uuid
from pathlib import Path

API = "https://open.feishu.cn/open-apis"


def creds() -> tuple:
    cfg = json.loads(Path.home().joinpath(".claude.json").read_text(encoding="utf-8"))

    def find(o):
        if isinstance(o, dict):
            if "lark-mcp" in o and isinstance(o["lark-mcp"], dict) and "args" in o["lark-mcp"]:
                return o["lark-mcp"]["args"]
            for v in o.values():
                r = find(v)
                if r:
                    return r
        return None

    args = find(cfg)
    if not args:
        sys.exit("lark-mcp args not found in ~/.claude.json")
    return args[args.index("-a") + 1], args[args.index("-s") + 1]


def call(method: str, path: str, token: str | None = None, body=None, headers=None, raw: bytes | None = None) -> dict:
    h = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if headers:
        h.update(headers)
    data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
    req = urllib.request.Request(API + path, data=data, method=method, headers=h)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                out = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(2 * (attempt + 1))
                continue
            sys.exit(f"{method} {path}: HTTP {e.code} {text[:400]}")
        except (http.client.IncompleteRead, urllib.error.URLError, ConnectionError, TimeoutError, socket.timeout) as e:
            # a request that broke off: safe to repeat for a GET, for a media upload (at worst an unused file is left)
            # and for putting an uploaded image into its block (the same result twice); a repeated POST that creates
            # blocks could create them twice, so those are not repeated
            safe = method == "GET" or path.endswith("/medias/upload_all") or (method == "PATCH" and isinstance(body, dict) and "replace_image" in body)
            if safe and attempt < 4:
                time.sleep(3 * (attempt + 1))
                continue
            sys.exit(f"{method} {path}: connection problem ({type(e).__name__}: {str(e)[:200]})")
    if out.get("code") not in (0, None):
        if out.get("code") in (99991400, 1061045) and False:
            pass
        sys.exit(f"{method} {path}: code {out.get('code')} {str(out.get('msg'))[:300]}")
    return out


def multipart(fields: dict, file_field: str, filename: str, content: bytes) -> tuple:
    boundary = "----report" + uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8"))
    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
                  f"Content-Type: {ctype}\r\n\r\n").encode("utf-8") + content + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), {"Content-Type": f"multipart/form-data; boundary={boundary}"}


def upload(token: str, name: str, content: bytes, parent_type: str, parent_node: str, extra: str | None = None) -> str:
    fields = {"file_name": name, "parent_type": parent_type, "parent_node": parent_node, "size": str(len(content))}
    if extra:
        fields["extra"] = extra
    raw, h = multipart(fields, "file", name, content)
    return call("POST", "/drive/v1/medias/upload_all", token, raw=raw, headers=h)["data"]["file_token"]


def block_text(b: dict) -> str:
    for k in ("text", "heading1", "heading2", "heading3", "heading4", "bullet", "ordered", "quote"):
        if k in b:
            return "".join((e.get("text_run") or {}).get("content", "") for e in b[k].get("elements", []))
    return ""


def all_blocks(token: str, doc: str) -> list:
    out, page = [], None
    while True:
        q = "?page_size=500" + (f"&page_token={page}" if page else "")
        d = call("GET", f"/docx/v1/documents/{doc}/blocks{q}", token)["data"]
        out += d.get("items", [])
        if not d.get("has_more"):
            return out
        page = d["page_token"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", type=Path)
    ap.add_argument("--title", required=True)
    ap.add_argument("--openid", required=True)
    ap.add_argument("--domain", default="trtgsjkv6r.feishu.cn")
    ap.add_argument("--doc", help="an existing document token: skip the import and only (re)insert the images")
    a = ap.parse_args()
    md = a.report.read_text(encoding="utf-8")
    lines = md.splitlines()
    images = []  # (path, caption prefix)
    kept = []
    for i, line in enumerate(lines):
        m = re.match(r"^!\[[^\]]*\]\(([^)]+)\)\s*$", line)
        if m:
            nxt = next((x for x in lines[i + 1:] if x.strip()), "")
            images.append((a.report.parent / m.group(1), nxt.strip()[:12]))
            continue
        kept.append(line)
    body = "\n".join(kept) + "\n"
    app_id, secret = creds()
    token = call("POST", "/auth/v3/tenant_access_token/internal", body={"app_id": app_id, "app_secret": secret})["tenant_access_token"]

    doc = a.doc
    if not doc:
        ft = upload(token, "report.md", body.encode("utf-8"), "ccm_import_open", "",
                    extra=json.dumps({"obj_type": "docx", "file_extension": "md"}))
        ticket = call("POST", "/drive/v1/import_tasks", token,
                      body={"file_extension": "md", "file_token": ft, "type": "docx", "file_name": a.title,
                            "point": {"mount_type": 1, "mount_key": ""}})["data"]["ticket"]
        for _ in range(90):
            time.sleep(2)
            res = call("GET", f"/drive/v1/import_tasks/{ticket}", token)["data"]["result"]
            if res.get("job_status") == 0:
                doc = res["token"]
                break
            if res.get("job_status") not in (1, 2):
                sys.exit(f"import failed: status {res.get('job_status')} {res.get('job_error_msg')}")
        if not doc:
            sys.exit("import did not finish in 3 minutes")
        call("POST", f"/drive/v1/permissions/{doc}/members?type=docx", token,
             body={"member_type": "openid", "member_id": a.openid, "perm": "full_access"})
        print("imported; collaborator added")

    blocks = all_blocks(token, doc)
    root = next(b for b in blocks if b.get("block_type") == 1)
    for path, cap in images:
        children = next(b for b in all_blocks(token, doc) if b.get("block_type") == 1)["children"]
        by_id = {b["block_id"]: b for b in all_blocks(token, doc)}
        idx = next((n for n, c in enumerate(children) if block_text(by_id[c]).strip().startswith(cap)), None)
        if idx is None:
            print(f"caption not found for {path.name} ({cap!r}); image skipped")
            continue
        made = call("POST", f"/docx/v1/documents/{doc}/blocks/{root['block_id']}/children", token,
                    body={"index": idx, "children": [{"block_type": 27, "image": {}}]})["data"]["children"][0]
        ft = upload(token, path.name, path.read_bytes(), "docx_image", made["block_id"])
        call("PATCH", f"/docx/v1/documents/{doc}/blocks/{made['block_id']}", token, body={"replace_image": {"token": ft}})
        print(f"image {path.name} inserted before {cap!r}")
    print(f"doc {doc}\nurl https://{a.domain}/docx/{doc}")


if __name__ == "__main__":
    main()
