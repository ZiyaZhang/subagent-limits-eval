"""How much the copied history of forked agents inflates the per-run numbers.

A subagent started with subagent_fork has a session log that begins with a copy of its parent's history (header
isSeeded, the copy ends at the first session/end-seed event). run_metrics.parse_session reads the whole log, so the
copied assistant messages (token usage), tool calls and search requests are counted once more for every fork.
For each run: cost, search requests and tool calls as counted now, and with the copied part left out.

Usage: fork_inflation.py BATCH_DIR... --out FILE.json [--jobs 24]
"""
import argparse
import collections
import concurrent.futures as cf
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, "judge-env/scripts")


def one(run_dir: str):
    import run_metrics as rm
    from delegation_stats import cost_cny
    d = Path(run_dir)
    try:
        res = json.loads((d / "result.json").read_text(encoding="utf-8"))
        logs, _ = rm.load_sessions(d)
    except Exception as exc:  # noqa: BLE001
        return {"run": d.name, "batch": d.parent.name, "error": type(exc).__name__}
    now, own = collections.Counter(), collections.Counter()
    calls_now, calls_own, aux_now, aux_own, forks, copied_events = 0, 0, 0, 0, 0, 0
    web_now, web_own = collections.Counter(), collections.Counter()
    for log in logs:
        h = log["header"]
        if h is None:
            continue
        ev = log["events"]
        cut = 0
        if h.get("isSeeded"):
            forks += 1
            cut = next((i for i, e in enumerate(ev) if e.get("type") == "session/end-seed"), 0)
            copied_events += cut
        for i, e in enumerate(ev):
            t = e.get("type")
            data = e.get("data") if isinstance(e.get("data"), dict) else {}
            mine = i >= cut
            if t == "assistant/message":
                for k, v in (data.get("usage") or {}).items():
                    if isinstance(v, (int, float)) and k != "totalTokens":
                        now[k] += v
                        if mine:
                            own[k] += v
            elif t == "tool/call":
                calls_now += 1
                calls_own += mine
                if data.get("name") in ("web_search", "web_fetch"):
                    web_now[data.get("name")] += 1
                    web_own[data.get("name")] += mine
            elif t == "web/deepseek-search-llm-request":
                aux_now += 1
                aux_own += mine
    return {"run": res.get("id") or d.name, "batch": d.parent.name, "group": res.get("group"), "task": res.get("task"), "forks": forks,
            "copied_events": copied_events, "cost_now": round(cost_cny(now), 4), "cost_own": round(cost_cny(own), 4),
            "calls_now": calls_now, "calls_own": calls_own, "aux_now": aux_now, "aux_own": aux_own,
            "search_now": web_now["web_search"], "search_own": web_own["web_search"], "fetch_now": web_now["web_fetch"], "fetch_own": web_own["web_fetch"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batches", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=24)
    a = ap.parse_args()
    runs = sorted(str(p.parent) for b in a.batches for p in b.glob("*/result.json") if not p.parent.name.startswith("_"))
    with cf.ProcessPoolExecutor(max_workers=a.jobs) as ex:
        rows = list(ex.map(one, runs, chunksize=4))
    a.out.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    ok = [r for r in rows if "error" not in r]
    print(f"{len(rows)} runs read, {len(rows) - len(ok)} unreadable")
    per = collections.defaultdict(list)
    for r in ok:
        per[r["batch"]].append(r)
    print(f"{'batch':22s} {'runs':>5s} {'with fork':>9s} {'cost now':>10s} {'cost own':>10s} {'over %':>7s} {'search over %':>13s} {'fetch over %':>12s} {'worst run over %':>16s}")
    for b, rs in sorted(per.items()):
        f = [r for r in rs if r["forks"]]
        cn, co = sum(r["cost_now"] for r in rs), sum(r["cost_own"] for r in rs)
        sn, so = sum(r["search_now"] for r in rs), sum(r["search_own"] for r in rs)
        fn, fo = sum(r["fetch_now"] for r in rs), sum(r["fetch_own"] for r in rs)
        worst = max(((r["cost_now"] / r["cost_own"] - 1) * 100 for r in rs if r["cost_own"] > 0), default=0)
        pct = lambda x, y: f"{(x / y - 1) * 100:6.2f}" if y else "     -"
        print(f"{b:22s} {len(rs):5d} {len(f):9d} {cn:10.1f} {co:10.1f} {pct(cn, co):>7s} {pct(sn, so):>13s} {pct(fn, fo):>12s} {worst:16.1f}")


if __name__ == "__main__":
    main()
