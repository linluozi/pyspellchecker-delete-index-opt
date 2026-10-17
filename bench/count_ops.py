"""确定性指标：不靠秒表，直接数「为了回答一次候选查询，总共构造了多少个中间字符串」。
用法: python count_ops.py <pkg_dir> <words.json> <tag> <limit>
"""

import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

pkg_dir, words_path, tag, limit = sys.argv[1:5]
limit = int(limit)

sys.path.insert(0, pkg_dir)
from spellchecker import SpellChecker  # noqa: E402

STATS = {"ed1_calls": 0, "ed1_strings": 0, "should_check_calls": 0, "known_calls": 0}

_orig_ed1 = SpellChecker.edit_distance_1
_orig_should = SpellChecker._check_if_should_check
_orig_known = SpellChecker.known


def ed1(self, word):
    res = _orig_ed1(self, word)
    STATS["ed1_calls"] += 1
    STATS["ed1_strings"] += len(res)
    return res


def should_check(self, word):
    STATS["should_check_calls"] += 1
    return _orig_should(self, word)


def known(self, words):
    STATS["known_calls"] += 1
    return _orig_known(self, words)


SpellChecker.edit_distance_1 = ed1
SpellChecker._check_if_should_check = should_check
SpellChecker.known = known

with open(words_path, encoding="utf-8") as fobj:
    queries = json.load(fobj)

words = [w for t, w in queries if t == tag][:limit]

spell = SpellChecker()
for w in words:
    spell.candidates(w)

# 第二遍：只算「索引键」数量 = Σ_{e1 ∈ E1(word)} (1 + len(e1))，
# 这是优化版实际做的字符串构造次数（不经过 edit_distance_1，所以上面统计不到）。
keys = 0
for w in words:
    for e1 in spell.edit_distance_1(w):
        keys += 1 + len(e1)
if pkg_dir.endswith("optimized"):
    print("index keys built         : %10d" % keys)
else:
    print("(若改用索引法，需构造键   : %10d)" % keys)

print("pkg            : %s" % pkg_dir.split("/")[-1])
print("queries        : %d (%s)" % (len(words), tag))
print("edit_distance_1 calls   : %10d" % STATS["ed1_calls"])
print("strings constructed     : %10d" % STATS["ed1_strings"])
print("_check_if_should_check  : %10d" % STATS["should_check_calls"])
print("known() calls           : %10d" % STATS["known_calls"])
