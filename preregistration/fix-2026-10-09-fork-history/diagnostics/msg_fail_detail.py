"""For each failed send_message of the census: what the target is in the tree (ancestor above the parent, a cousin,
a nephew...), and for ids that are no session of the run, how far the id is from the nearest real session id."""
import collections
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, "judge-env/scripts")
import run_metrics as rm  # noqa: E402

rows = json.load(open("results/analysis-p2-main-messages.json"))
fails = [r for r in rows if r["outcome"] != "delivered"]
by_run = collections.defaultdict(list)
for r in fails:
    by_run[r["run"]].append(r)


def dist(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


rel_c, near_c, ex = collections.Counter(), collections.Counter(), []
for run, rs in sorted(by_run.items()):
    _, sessions = rm.load_sessions(Path("results/runs/p2-main") / run)
    by = {s["id"]: s for s in sessions}
    ids = [str(s["id"]) for s in sessions]
    for r in rs:
        sender = next((s for s in sessions if str(s["id"]).startswith(r["sid"])), None)
        raw = r["raw_id"].replace("session-", "")
        if "another parent" in r["outcome"]:
            m = rm.norm_id(raw) if raw in by or rm.norm_id(raw) in by else None
            t = by.get(m)
            if t is None or sender is None:
                rel_c["?"] += 1
                continue
            anc, cur, up = False, sender, 0
            while cur is not None and cur["parent"] in by:
                cur = by[cur["parent"]]
                up += 1
                if cur["id"] == t["id"]:
                    anc = True
                    break
            if t["id"] == sender["id"]:
                rel_c["itself"] += 1
            elif anc:
                rel_c[f"ancestor {up} levels up (target depth {t['depth']}, sender depth {sender['depth']})"] += 1
            else:
                rel_c[f"other branch (target depth {t['depth']}, sender depth {sender['depth']}, target parent is sender's parent's sibling: "
                      f"{by.get(t['parent'], {}).get('parent') == by.get(sender['parent'], {}).get('parent')})"] += 1
        elif "unavailable" in r["outcome"]:
            d, near = min((dist(raw.lower(), i.lower()), i) for i in ids) if ids else (99, "")
            t = by.get(near)
            relation = "?"
            if t is not None and sender is not None:
                relation = ("own child" if t["parent"] == sender["id"] else "own parent" if sender["parent"] == t["id"]
                            else "itself" if t["id"] == sender["id"] else "other")
            near_c[(("0" if d == 0 else "1" if d == 1 else "2-3" if d <= 3 else "4-8" if d <= 8 else ">8"), relation)] += 1
            if len(ex) < 12:
                ex.append((run, r["group"], d, raw, near, relation))
print("belongs to another parent session:")
for k, v in rel_c.most_common():
    print(f"  {v:3d}  {k}")
print("is unavailable: edit distance of the id to the nearest real session id of the run, and what that session is to the sender")
for k, v in sorted(near_c.items()):
    print(f"  {v:3d}  distance {k[0]:4s} nearest is {k[1]}")
for e in ex:
    print("  ", e)
