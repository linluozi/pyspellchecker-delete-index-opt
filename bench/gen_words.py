"""生成确定性的查询词表：正确词 / 1 编辑错词 / 2 编辑错词 / 随机串。
种子固定，保证两份实现跑的是同一批输入。"""

import json
import random
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from spellchecker import SpellChecker  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "words.json"

spell = SpellChecker()
words = sorted(w for w in spell.word_frequency.dictionary if w.isascii() and w.isalpha() and 3 <= len(w) <= 12)
rnd = random.Random(20261018)

ALPHA = "abcdefghijklmnopqrstuvwxyz"


def one_edit(w):
    kind = rnd.randint(0, 3)
    if len(w) <= 1:
        kind = 2
    if kind == 0:  # delete
        i = rnd.randrange(len(w))
        return w[:i] + w[i + 1 :]
    if kind == 1:  # transpose
        i = rnd.randrange(len(w) - 1)
        return w[:i] + w[i + 1] + w[i] + w[i + 2 :]
    if kind == 2:  # replace
        i = rnd.randrange(len(w))
        return w[:i] + rnd.choice(ALPHA) + w[i + 1 :]
    i = rnd.randrange(len(w) + 1)  # insert
    return w[:i] + rnd.choice(ALPHA) + w[i:]


def edits(w, n):
    for _ in range(n):
        w = one_edit(w)
    return w


sample = [rnd.choice(words) for _ in range(7000)]
correct = sample[:300]
d1 = [edits(w, 1) for w in sample[300:900]]
d2 = [edits(w, 2) for w in sample[900:1700]]
junk = ["".join(rnd.choice(ALPHA) for _ in range(rnd.randint(2, 10))) for _ in range(400)]

queries = []
for tag, group in (("correct", correct), ("dist1", d1), ("dist2", d2), ("junk", junk)):
    for w in group:
        queries.append([tag, w])

with open(OUT, "w", encoding="utf-8", newline="\n") as fobj:
    json.dump(queries, fobj)

print("words:", len(words))
print("queries:", len(queries))
for tag in ("correct", "dist1", "dist2", "junk"):
    print("  ", tag, sum(1 for t, _ in queries if t == tag))
