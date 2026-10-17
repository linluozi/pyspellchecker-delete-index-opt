"""逐条比对两份实现的 candidates() 结果，并汇总耗时。"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))

with open(f"{HERE}/words.json", encoding="utf-8") as fobj:
    queries = json.load(fobj)
with open(f"{HERE}/res_upstream.json", encoding="utf-8") as fobj:
    up = json.load(fobj)
with open(f"{HERE}/res_optimized.json", encoding="utf-8") as fobj:
    op = json.load(fobj)

assert len(queries) == len(up["results"]) == len(op["results"]), "长度不一致"

tags = {}
mismatch_examples = []
for (tag, word), a, b in zip(queries, up["results"], op["results"]):
    rec = tags.setdefault(tag, {"n": 0, "same": 0, "both_none": 0, "diff": 0})
    rec["n"] += 1
    if a == b:
        rec["same"] += 1
        if a is None:
            rec["both_none"] += 1
    else:
        rec["diff"] += 1
        if len(mismatch_examples) < 15:
            only_a = sorted(set(a or []) - set(b or []))
            only_b = sorted(set(b or []) - set(a or []))
            mismatch_examples.append((tag, word, only_a[:5], only_b[:5]))

print("%-8s %6s %8s %10s %8s" % ("tag", "n", "identical", "both_none", "diff"))
tot = {"n": 0, "same": 0, "diff": 0}
for tag in sorted(tags):
    r = tags[tag]
    tot["n"] += r["n"]
    tot["same"] += r["same"]
    tot["diff"] += r["diff"]
    print("%-8s %6d %8d %10d %8d" % (tag, r["n"], r["same"], r["both_none"], r["diff"]))
print("%-8s %6d %8d %10s %8d" % ("TOTAL", tot["n"], tot["same"], "-", tot["diff"]))

if mismatch_examples:
    print("\n不一致样例:")
    for tag, word, oa, ob in mismatch_examples:
        print("  [%s] %-16s upstream-only=%s  optimized-only=%s" % (tag, word, oa, ob))

print("\n=== 耗时（同一批查询，各自独立进程，单轮） ===")
print("%-8s %12s %12s %10s" % ("tag", "upstream", "optimized", "speedup"))
for tag in sorted(tags):
    n = tags[tag]["n"]
    tu = up["timings"][tag]
    to = op["timings"][tag]
    print("%-8s %9.1f ms %9.1f ms %9.1fx" % (tag, tu * 1000, to * 1000, (tu / to) if to else float("inf")))
tu = sum(up["timings"].values())
to = sum(op["timings"].values())
print("%-8s %9.1f ms %9.1f ms %9.1fx" % ("TOTAL", tu * 1000, to * 1000, tu / to))
