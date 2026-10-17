"""只算索引键数量：Σ_{e1 ∈ E1(word)} (1 + len(e1))，
即优化版在 distance-2 阶段实际构造并查询的字符串个数。"""

import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

pkg_dir, words_path, tag, limit = sys.argv[1:5]
limit = int(limit)

sys.path.insert(0, pkg_dir)
from spellchecker import SpellChecker  # noqa: E402

with open(words_path, encoding="utf-8") as fobj:
    queries = json.load(fobj)

words = [w for t, w in queries if t == tag][:limit]
spell = SpellChecker()

keys = 0
ed1_total = 0
for w in words:
    e1 = spell.edit_distance_1(w)
    ed1_total += len(e1)
    for x in e1:
        keys += 1 + len(x)

print("%-10s queries=%d  |E1| total=%d  index keys=%d  (avg %.0f keys/query)"
      % (pkg_dir.split("/")[-1], len(words), ed1_total, keys, keys / len(words)))
