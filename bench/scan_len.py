"""扫描：不同输入词长下，原版与优化版回答一次 distance-2 查询的耗时。

每档取固定数量、由真实词典词施加 2 次编辑生成的错词（种子固定）。
每档两侧交替、各跑 R 轮，取「逐轮比值中位数」与「每档最小值」。
输出 bench/scan_len.json。
"""

import json
import os
import random
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UP = os.path.join(ROOT, "upstream")
OP = os.path.join(ROOT, "optimized")

PER_LEN = 6
ROUNDS = 3
MIN_LEN = 3
MAX_LEN = 14

ALPHA = "abcdefghijklmnopqrstuvwxyz"


def load(pkg_dir, tag):
    for key in [k for k in sys.modules if k == "spellchecker" or k.startswith("spellchecker.")]:
        del sys.modules[key]
    sys.path.insert(0, pkg_dir)
    import spellchecker as mod  # noqa: PLC0415

    sys.path.remove(pkg_dir)
    return mod.SpellChecker


UpSpellChecker = load(UP, "up")
OpSpellChecker = load(OP, "op")

up = UpSpellChecker()
op = OpSpellChecker()

# 按长度分桶取真实词
buckets = {}
for w in up.word_frequency.dictionary:
    if w.isascii() and w.isalpha() and MIN_LEN <= len(w) <= MAX_LEN:
        buckets.setdefault(len(w), []).append(w)

rnd = random.Random(20261018)


def one_edit(w):
    kind = rnd.randint(0, 3)
    if len(w) <= 1:
        kind = 2
    if kind == 0:
        i = rnd.randrange(len(w))
        return w[:i] + w[i + 1 :]
    if kind == 1:
        i = rnd.randrange(len(w) - 1)
        return w[:i] + w[i + 1] + w[i] + w[i + 2 :]
    if kind == 2:
        i = rnd.randrange(len(w))
        return w[:i] + rnd.choice(ALPHA) + w[i + 1 :]
    i = rnd.randrange(len(w) + 1)
    return w[:i] + rnd.choice(ALPHA) + w[i:]


queries = []
for n in range(MIN_LEN, MAX_LEN + 1):
    pool = buckets.get(n, [])
    if not pool:
        continue
    for _ in range(PER_LEN):
        base = rnd.choice(pool)
        typo = one_edit(one_edit(base))
        # 必须是「没有 1-编辑候选」的纯 distance-2 场景，否则原版会提前返回
        if up.known(list(up.edit_distance_1(typo))):
            continue
        queries.append(typo)

print("queries:", len(queries))


def bench(checker, words, rounds):
    # 预热（优化版会在第一轮建索引，不计入）
    for w in words:
        checker.candidates(w)
    samples = []
    for _ in range(rounds):
        start = time.perf_counter()
        for w in words:
            checker.candidates(w)
        samples.append(time.perf_counter() - start)
    return samples


def median(xs):
    ys = sorted(xs)
    return ys[len(ys) // 2]


rows = []
for n in range(MIN_LEN, MAX_LEN + 1):
    ws = [q for q in queries if len(q) == n]
    if not ws:
        continue
    a = bench(up, ws, ROUNDS)
    b = bench(op, ws, ROUNDS)
    ma, mb = median(a), median(b)
    rows.append(
        {
            "len": n,
            "n_queries": len(ws),
            "upstream_median_ms": ma * 1000,
            "optimized_median_ms": mb * 1000,
            "speedup_median": ma / mb,
            "upstream_min_ms": min(a) * 1000,
            "optimized_min_ms": min(b) * 1000,
            "speedup_min": min(a) / min(b),
        }
    )
    print(
        "len=%2d n=%d  upstream %9.2f ms  optimized %8.3f ms  -> %7.1fx"
        % (n, len(ws), ma * 1000, mb * 1000, ma / mb)
    )

with open(os.path.join(HERE, "scan_len.json"), "w", encoding="utf-8", newline="\n") as fobj:
    json.dump(rows, fobj, indent=2)
print("wrote", os.path.join(HERE, "scan_len.json"))
