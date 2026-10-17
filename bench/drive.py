"""交替起独立进程跑 A/B，逐轮配对算比值；同时跑「同码对同码」当噪声底。
用法: python drive.py <tag> <rounds> <limit>
"""

import json
import statistics
import subprocess
import sys
import tempfile
import os

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
ROOT = os.path.dirname(HERE)
UP = os.path.join(ROOT, "upstream")
OP = os.path.join(ROOT, "optimized")

tag = sys.argv[1]
rounds = int(sys.argv[2])
limit = int(sys.argv[3])


def run(pkg, out):
    subprocess.run(
        [PY, os.path.join(HERE, "micro.py"), pkg, os.path.join(HERE, "words.json"), tag, str(1), str(limit), out],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    with open(out, encoding="utf-8") as fobj:
        return json.load(fobj)["rounds_ms"][0]


tmp = tempfile.mkdtemp()
fa = os.path.join(tmp, "a.json")
fb = os.path.join(tmp, "b.json")

pairs = []
noise = []
for r in range(rounds):
    if r % 2 == 0:
        a = run(UP, fa)
        b = run(OP, fb)
    else:  # 反向顺序，抵消可能的位置效应
        b = run(OP, fb)
        a = run(UP, fa)
    pairs.append((a, b))
    # 噪声底：同一份优化版代码跑两遍
    n1 = run(OP, fa)
    n2 = run(OP, fb)
    noise.append((n1, n2))
    print("round %d: upstream %8.2f ms | optimized %8.2f ms | ratio %7.2fx || noise %8.2f vs %8.2f (%5.2fx)"
          % (r, a, b, a / b, n1, n2, n1 / n2))

ratios = [a / b for a, b in pairs]
nr = [a / b for a, b in noise]
print()
print("=== tag=%s  n=%d  rounds=%d ===" % (tag, limit, rounds))
print("upstream  median %.2f ms" % statistics.median([a for a, _ in pairs]))
print("optimized median %.2f ms" % statistics.median([b for _, b in pairs]))
print("speedup   median %.2fx   min %.2fx   max %.2fx" % (statistics.median(ratios), min(ratios), max(ratios)))
print("noise floor (same code twice): median %.3fx  min %.3fx  max %.3fx"
      % (statistics.median(nr), min(nr), max(nr)))
