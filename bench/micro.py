"""单进程微基准：对某一类查询重复计时若干轮。
用法: python micro.py <pkg_dir> <words.json> <tag> <rounds> <limit> <out.json>
"""

import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

pkg_dir, words_path, tag, rounds, limit, out_path = sys.argv[1:7]
rounds = int(rounds)
limit = int(limit)

sys.path.insert(0, pkg_dir)
from spellchecker import SpellChecker  # noqa: E402

with open(words_path, encoding="utf-8") as fobj:
    queries = json.load(fobj)

words = [w for t, w in queries if t == tag][:limit]

spell = SpellChecker()

# 预热：优化版会在第一次 distance-2 查询时构建索引，这一轮不计入
for w in words:
    spell.candidates(w)

samples = []
for _ in range(rounds):
    start = time.perf_counter()
    for w in words:
        spell.candidates(w)
    samples.append((time.perf_counter() - start) * 1000.0)

with open(out_path, "w", encoding="utf-8", newline="\n") as fobj:
    json.dump({"pkg": pkg_dir, "tag": tag, "n": len(words), "rounds_ms": samples}, fobj)

print("%-9s %-7s n=%d rounds=%d  median %.2f ms  min %.2f ms  max %.2f ms" % (
    pkg_dir.split("/")[-1], tag, len(words), rounds,
    sorted(samples)[rounds // 2], min(samples), max(samples),
))
