"""在指定实现上跑一遍查询词表，把 candidates() 的结果写成 json。
用法: python run_queries.py <pkg_dir> <words.json> <out.json>
"""

import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

pkg_dir = sys.argv[1]
words_path = sys.argv[2]
out_path = sys.argv[3]

sys.path.insert(0, pkg_dir)

from spellchecker import SpellChecker  # noqa: E402  (import after sys.path tweak)

with open(words_path, encoding="utf-8") as fobj:
    queries = json.load(fobj)

spell = SpellChecker()

results = []
timings = {}
t_all = time.perf_counter()
for tag, word in queries:
    start = time.perf_counter()
    got = spell.candidates(word)
    elapsed = time.perf_counter() - start
    bucket = timings.setdefault(tag, [0.0, 0])
    bucket[0] += elapsed
    bucket[1] += 1
    results.append(None if got is None else sorted(got))
t_all = time.perf_counter() - t_all

with open(out_path, "w", encoding="utf-8", newline="\n") as fobj:
    json.dump({"results": results, "timings": {k: v[0] for k, v in timings.items()}}, fobj)

print("pkg:", pkg_dir)
print("total wall: %.2f s" % t_all)
for tag in sorted(timings):
    tot, cnt = timings[tag]
    print("  %-8s n=%4d  total %9.2f ms  avg %8.3f ms" % (tag, cnt, tot * 1000, tot / cnt * 1000))
