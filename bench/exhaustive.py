"""穷举等价性验证。

在一个小词典上，把「字母表上长度 0..7 的所有字符串」全部喂给两份实现，
逐条比对 candidates()。同时支持 --poison 故意破坏优化版，验证本比对能抓到问题。

用法: python exhaustive.py [--poison] [--alpha abcd] [--maxlen 7] [--case-sensitive] [--distance 2]
"""

import itertools
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(BASE, "upstream")
OP = os.path.join(BASE, "optimized")

alpha = "abcd"
maxlen = 7
poison = "--poison" in sys.argv
case_sensitive = "--case-sensitive" in sys.argv
distance = 2


def opt(name, default):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


alpha = opt("--alpha", alpha)
maxlen = int(opt("--maxlen", str(maxlen)))
distance = int(opt("--distance", str(distance)))


def load(pkg_dir, tag):
    for key in [k for k in sys.modules if k == "spellchecker" or k.startswith("spellchecker.")]:
        del sys.modules[key]
    sys.path.insert(0, pkg_dir)
    import spellchecker as mod  # noqa: PLC0415

    sys.path.remove(pkg_dir)
    return mod.SpellChecker, mod


UpSpellChecker, up_mod = load(UP, "up")
OpSpellChecker, op_mod = load(OP, "op")

# 词典：字母表内、长度 1..6 的一批词，覆盖各种编辑关系
DICT_WORDS = ["a", "ab", "abc", "abcd", "bcd", "cdab", "badc", "dcba", "abcdabcd", "aaaa", "bbbb", "abab", "dabc"]
if "--numeric" in sys.argv:
    # 混入数字/标点形态的词，逼出 _check_if_should_check 的过滤分支
    DICT_WORDS = DICT_WORDS + ["1", "12", "a1", "nan", "inf", "3.5", "!", "-"]
if case_sensitive:
    DICT_WORDS = DICT_WORDS + ["ABC", "Abc"]

print("alphabet      :", alpha)
print("max length    :", maxlen)
print("dictionary    :", DICT_WORDS)
print("case_sensitive:", case_sensitive, " distance:", distance, " poison:", poison)

up = UpSpellChecker(language=None, case_sensitive=case_sensitive, distance=distance)
up.word_frequency.load_words(DICT_WORDS)
op = OpSpellChecker(language=None, case_sensitive=case_sensitive, distance=distance)
op.word_frequency.load_words(DICT_WORDS)

if poison:
    # 故意去掉「一步编辑」校验：索引桶里的词会被无条件收下
    def always_true(left, right):  # noqa: ARG001
        return True

    OpSpellChecker._SpellChecker__is_within_one_edit = staticmethod(always_true)

strings = []
for n in range(0, maxlen + 1):
    for tup in itertools.product(alpha, repeat=n):
        strings.append("".join(tup))
print("queries       :", len(strings))

same = 0
diff = 0
examples = []
for s in strings:
    a = up.candidates(s)
    b = op.candidates(s)
    a = None if a is None else sorted(a)
    b = None if b is None else sorted(b)
    if a == b:
        same += 1
    else:
        diff += 1
        if len(examples) < 12:
            oa = sorted(set(a or []) - set(b or []))
            ob = sorted(set(b or []) - set(a or []))
            examples.append((s, oa[:4], ob[:4]))

print()
print("identical: %d / %d" % (same, len(strings)))
print("different: %d" % diff)
for s, oa, ob in examples:
    print("   %-10s upstream-only=%-24s optimized-only=%s" % (repr(s), oa, ob))
sys.exit(0 if diff == 0 else 1)
