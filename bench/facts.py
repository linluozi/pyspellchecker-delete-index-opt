"""补齐报告里引用的原始数字：|E1|、二次展开耗时、以及「2-delete 索引」的规模估计。"""

import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from spellchecker import SpellChecker  # noqa: E402

spell = SpellChecker()
words = list(spell.word_frequency.dictionary)

print("=== |E1| 与 __edit_distance_alt 实测 ===")
print("%-14s %6s %8s %12s" % ("word", "len", "|E1|", "alt_ms"))
for w in ["accomodate", "maintainance", "questionaire", "recieve"]:
    e1 = spell.edit_distance_1(w)
    t0 = time.perf_counter()
    alt = spell._SpellChecker__edit_distance_alt(e1)
    dt = (time.perf_counter() - t0) * 1000
    print("%-14s %6d %6d %12.1f   (results=%d)" % (w, len(w), len(e1), dt, len(alt)))

print()
print("=== 1-delete 索引规模 ===")
pairs1 = sum(1 + len(w) for w in words)
print("entries (含重复): %d" % pairs1)

print()
print("=== 2-delete 索引规模（未采纳，仅用于说明代价）===")
pairs2 = sum(1 + len(w) + len(w) * (len(w) - 1) // 2 for w in words)
print("entries (含重复): %d" % pairs2)
print("约为 1-delete 索引的 %.1f 倍" % (pairs2 / pairs1))
