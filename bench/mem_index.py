"""量索引的构建耗时与常驻内存增量。
用法: python mem_index.py <variant>   variant = none | list | str
每个 variant 独立进程跑，避免互相污染 RSS。
"""

import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import psutil  # noqa: E402

variant = sys.argv[1] if len(sys.argv) > 1 else "none"

from spellchecker import SpellChecker  # noqa: E402

proc = psutil.Process(os.getpid())
spell = SpellChecker()
words = list(spell.word_frequency.dictionary)
base = proc.memory_info().rss / (1024 * 1024)
print("variant = %s, dictionary words = %d" % (variant, len(words)))
print("rss after dictionary load: %.1f MB" % base)

if variant != "none":
    t0 = time.perf_counter()
    idx = {}
    get = idx.get
    if variant == "list":
        for w in words:
            b = get(w)
            if b is None:
                idx[w] = [w]
            else:
                b.append(w)
            for i in range(len(w)):
                k = w[:i] + w[i + 1 :]
                b = get(k)
                if b is None:
                    idx[k] = [w]
                else:
                    b.append(w)
    else:
        for w in words:
            b = get(w)
            if b is None:
                idx[w] = w
            elif type(b) is str:
                idx[w] = [b, w]
            else:
                b.append(w)
            for i in range(len(w)):
                k = w[:i] + w[i + 1 :]
                b = get(k)
                if b is None:
                    idx[k] = w
                elif type(b) is str:
                    idx[k] = [b, w]
                else:
                    b.append(w)
    build = time.perf_counter() - t0
    after = proc.memory_info().rss / (1024 * 1024)
    print("build: %.2f s" % build)
    print("entries: %d" % len(idx))
    print("rss after index: %.1f MB  (delta +%.1f MB)" % (after, after - base))
