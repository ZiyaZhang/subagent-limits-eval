"""One streamed Messages call for the judges (judge.py, judge_code.py), through the company proxy.

Uses the anthropic SDK when it is installed (the Mac) and plain httpx otherwise (the HG dev box has no anthropic
package; the request and the parsed reply are the same). A reply with no text and no stop_reason (the proxy
returned nothing, as on 10/2 when three calls came back empty after ~1811 s) raises EmptyReply, which is in
TRANSIENT, so callers retry it instead of writing it as a result.

The key: JUDGE_USER_SK from the environment (the HG runs pass it in at start, it is never written to disk), else the
macOS keychain item dsllm-usersk. HTTP(S)_PROXY variables are ignored (trust_env=False): the proxy host is internal.
"""
from __future__ import annotations

import json
import os
import subprocess
from types import SimpleNamespace


PROXY_HOST = "proxy.high-five-ai.xyz"
# JUDGE_PROXY_ADDR pins the proxy's address (TLS still checks the name); unset = plain DNS. 10/3: the HG dev box
# resolves the name to 172.21.31.244 and the Mac to 10.2.201.57; both end a request that has sent nothing for 600 s
# (Opus buffers its whole thinking block), so the pin did not help and is off by default.
PROXY_ADDR = os.environ.get("JUDGE_PROXY_ADDR", "").strip()


def _pin_proxy_addr() -> None:
    import socket
    if not PROXY_ADDR or getattr(socket.getaddrinfo, "judge_pin", None):
        return
    orig = socket.getaddrinfo

    def getaddrinfo(host, port, *args, **kwargs):
        return orig(PROXY_ADDR if host == PROXY_HOST else host, port, *args, **kwargs)
    getaddrinfo.judge_pin = PROXY_ADDR
    socket.getaddrinfo = getaddrinfo


_pin_proxy_addr()


class EmptyReply(Exception):
    """The proxy answered without any text and without a stop_reason."""


def _transient() -> tuple:
    import httpx
    errs = [EmptyReply, httpx.RemoteProtocolError, httpx.ReadError, httpx.ReadTimeout, httpx.ConnectError,
            httpx.ConnectTimeout, httpx.WriteError, httpx.PoolTimeout]
    try:
        import anthropic
        errs += [anthropic.APIConnectionError, anthropic.APITimeoutError, anthropic.InternalServerError]
    except ImportError:
        pass
    return tuple(errs)


TRANSIENT = _transient()


class HTTPStatusError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:200]}")
        self.status = status


def user_sk() -> str:
    key = os.environ.get("JUDGE_USER_SK", "").strip()
    if key:
        return key
    return subprocess.run(["security", "find-generic-password", "-a", "zhangziya", "-s", "dsllm-usersk", "-w"],
                          check=True, capture_output=True, text=True).stdout.strip()


READ_TIMEOUT_S = 1800  # between two received bytes; long max-effort thinking may stream nothing for many minutes


def _check(msg) -> None:
    text = "".join(getattr(b, "text", "") or "" for b in msg.content if getattr(b, "type", "") == "text")
    if not text.strip() and msg.stop_reason is None:
        raise EmptyReply(f"empty reply (no text, no stop_reason) {json.dumps(getattr(msg, 'diag', {}))}")


def _user_content(user, user_tail):
    """The user turn: plain text, or (when a tail is given) the text as a cached block followed by the tail."""
    if not user_tail:
        return user
    return [{"type": "text", "text": user, "cache_control": {"type": "ephemeral"}}, {"type": "text", "text": user_tail}]


def _sdk(base_url, token, model, system, user, effort, max_tokens, timeout, user_tail=None):
    import anthropic
    import httpx
    client = anthropic.Anthropic(base_url=base_url, auth_token=token, api_key=None, max_retries=3, timeout=timeout,
                                 http_client=httpx.Client(trust_env=False, timeout=timeout))
    with client.messages.stream(
        model=model, max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": _user_content(user, user_tail)}],
        extra_body={"thinking": {"type": "adaptive"}, "output_config": {"effort": effort}},
    ) as stream:
        msg = stream.get_final_message()
    usage = msg.usage.model_dump() if hasattr(msg.usage, "model_dump") else dict(msg.usage)
    return SimpleNamespace(content=[SimpleNamespace(type=getattr(b, "type", ""), text=getattr(b, "text", ""))
                                    for b in msg.content], usage=usage, stop_reason=msg.stop_reason)


def _httpx(base_url, token, model, system, user, effort, max_tokens, timeout, user_tail=None):
    import httpx
    body = {"model": model, "max_tokens": max_tokens, "stream": True,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": _user_content(user, user_tail)}],
            "thinking": {"type": "adaptive"}, "output_config": {"effort": effort}}
    headers = {"authorization": f"Bearer {token}", "anthropic-version": "2023-06-01", "content-type": "application/json"}
    import collections
    import time as _time
    blocks, usage, stop = {}, {}, None
    kinds, t0, last = collections.Counter(), _time.time(), None
    with httpx.Client(trust_env=False, timeout=httpx.Timeout(connect=60, read=READ_TIMEOUT_S, write=120, pool=60)) as client:
        with client.stream("POST", base_url.rstrip("/") + "/messages", headers=headers, json=body) as r:
            if r.status_code != 200:
                text = r.read().decode("utf-8", "replace")
                if r.status_code >= 500 or r.status_code == 429:
                    raise httpx.RemoteProtocolError(f"HTTP {r.status_code}: {text[:200]}")
                raise HTTPStatusError(r.status_code, text)
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    d = json.loads(line[5:])
                except ValueError:
                    continue
                t = d.get("type")
                kinds[t if t != "content_block_delta" else "delta:" + str((d.get("delta") or {}).get("type"))] += 1
                last = _time.time()
                if t == "message_start":
                    usage.update((d.get("message") or {}).get("usage") or {})
                elif t == "content_block_start":
                    cb = d.get("content_block") or {}
                    blocks[d.get("index", len(blocks))] = {"type": cb.get("type", ""), "text": cb.get("text", "") or ""}
                elif t == "content_block_delta":
                    delta = d.get("delta") or {}
                    b = blocks.setdefault(d.get("index", 0), {"type": "text", "text": ""})
                    if delta.get("type") == "text_delta":
                        b["text"] += delta.get("text", "")
                elif t == "message_delta":
                    stop = (d.get("delta") or {}).get("stop_reason", stop)
                    for k, v in (d.get("usage") or {}).items():
                        usage[k] = v
                elif t == "error":
                    raise httpx.RemoteProtocolError(f"stream error: {json.dumps(d.get('error'))[:200]}")
    content = [SimpleNamespace(type=b["type"], text=b["text"]) for _, b in sorted(blocks.items())]
    diag = {"elapsed_s": round(_time.time() - t0, 1), "last_event_s": round(last - t0, 1) if last else None,
            "events": dict(kinds), "usage": {k: usage.get(k) for k in ("input_tokens", "output_tokens")}}
    return SimpleNamespace(content=content, usage=usage, stop_reason=stop, diag=diag)


def stream_message(*, base_url: str, model: str, system: str, user: str, effort: str, max_tokens: int = 128000,
                   timeout: float = 1800, token: str | None = None, user_tail: str | None = None):
    token = token or user_sk()
    use_sdk = os.environ.get("JUDGE_CLIENT", "") != "httpx"  # httpx: no hidden SDK retries, and the stream diagnostics
    if use_sdk:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            use_sdk = False
    if use_sdk:
        msg = _sdk(base_url, token, model, system, user, effort, max_tokens, timeout, user_tail)
    else:
        msg = _httpx(base_url, token, model, system, user, effort, max_tokens, timeout, user_tail)
    _check(msg)
    return msg
