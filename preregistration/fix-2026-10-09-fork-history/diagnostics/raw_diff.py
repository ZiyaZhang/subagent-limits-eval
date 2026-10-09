"""Compare the run table before and after the fork fix: which rows and which columns changed."""
import collections
import csv
import sys

old_dir, new_dir, b = sys.argv[1], sys.argv[2], sys.argv[3]
for suffix, key in ((".csv", "id"), (".agents.csv", None), (".spawn_calls.csv", None)):
    old = list(csv.DictReader(open(f"{old_dir}/{b}{suffix}", encoding="utf-8")))
    new = list(csv.DictReader(open(f"{new_dir}/{b}{suffix}", encoding="utf-8")))
    print(f"{b}{suffix}: rows {len(old)} -> {len(new)}; columns equal: {list(old[0]) == list(new[0])}")
    if key:
        o = {r[key]: r for r in old}
        n = {r[key]: r for r in new}
        changed = [k for k in o if o[k] != n.get(k)]
        print("  ids only in one:", set(o) ^ set(n), "| changed rows:", len(changed), sorted(changed))
        cols = collections.Counter(c for k in changed for c in o[k] if o[k][c] != n[k][c])
        print("  columns changed (rows):", dict(cols.most_common(60)))
        for k in sorted(changed):
            show = ["group", "task"] + [c for c in ("cost_cny_peak", "search_aux", "agents", "spawned", "spawn_ok", "tool_calls", "web_search", "web_fetch", "peak_alive", "t_answer_s") if c in o[k]]
            print("  ", k, {c: (o[k][c], n[k][c]) if o[k][c] != n[k][c] else o[k][c] for c in show})
    else:
        idc = "id" if "id" in old[0] else ("run" if "run" in old[0] else list(old[0])[1])
        co = collections.Counter(r[idc] for r in old)
        cn = collections.Counter(r[idc] for r in new)
        diff = {k: (co[k], cn[k]) for k in set(co) | set(cn) if co[k] != cn[k]}
        print("  per-run row counts that changed:", diff)
        same = sum(1 for k in co if co[k] == cn[k])
        oo = collections.defaultdict(list)
        nn = collections.defaultdict(list)
        for r in old:
            oo[r[idc]].append(tuple(r.values()))
        for r in new:
            nn[r[idc]].append(tuple(r.values()))
        other = [k for k in oo if sorted(oo[k]) != sorted(nn.get(k, []))]
        print("  runs whose rows changed in any way:", sorted(other))
