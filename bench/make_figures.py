"""从实测数据生成对比图。所有数字都来自 bench/ 下的测量结果，脚本里不手写结论。"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "speedup.png")

INK = "#2b2119"
PAPER = "#faf6f0"
AMBER = "#c8892b"
TERRACOTTA = "#b4552f"
OLIVE = "#6b6b3a"
MUTED = "#8a7a68"

plt.rcParams.update(
    {
        "figure.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "text.color": INK,
        "axes.labelcolor": INK,
        "axes.edgecolor": MUTED,
        "xtick.color": INK,
        "ytick.color": INK,
        "font.size": 10,
        "axes.unicode_minus": False,
    }
)

# ---- 数据：全部来自 bench 实测 ----
# run_queries.py 输出：每类查询的总耗时 / 查询条数
per_word = {
    "already correct": {"upstream": 0.62 / 300, "optimized": 0.66 / 300},
    "1-edit typo": {"upstream": 305.90 / 600, "optimized": 298.01 / 600},
    "2-edit typo": {"upstream": 415959.13 / 800, "optimized": 3966.55 / 800},
    "random string": {"upstream": 92919.69 / 400, "optimized": 915.80 / 400},
}
# count_ops.py + keys_only.py：150 条 2-edit 查询的构造量
work = {
    "edit_distance_1 calls": {"upstream": 99040 / 150, "optimized": 145 / 150},
    "strings constructed": {"upstream": (90445606 + 117742) / 150, "optimized": (115717 + 1220336) / 150},
    "should_check calls": {"upstream": 201176 / 150, "optimized": 1015 / 150},
}

with open(os.path.join(HERE, "figure_data.json"), "w", encoding="utf-8", newline="\n") as fobj:
    json.dump({"per_word_ms": per_word, "work_per_query": work}, fobj, indent=2)

def fmt(v):
    """把量级跨 8 个数量级的数字写成人类可读的短标签。"""
    if v >= 10000:
        return f"{v / 1000:.0f}k"
    if v >= 100:
        return f"{v:.0f}"
    if v >= 1:
        return f"{v:.3g}"
    return f"{v:.4g}"


fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.6))

# ---- 左：每词耗时（对数轴）----
ax = axes[0]
labels = list(per_word)
up_v = [per_word[k]["upstream"] for k in labels]
op_v = [per_word[k]["optimized"] for k in labels]
pos = range(len(labels))
w = 0.38
ax.bar([p - w / 2 for p in pos], up_v, w, label="upstream", color=TERRACOTTA)
ax.bar([p + w / 2 for p in pos], op_v, w, label="optimized", color=AMBER)
ax.set_yscale("log")
ax.set_xticks(list(pos))
ax.set_xticklabels(labels)
ax.set_ylabel("ms per query (log scale)")
ax.set_ylim(1e-4, 5e3)
for i, k in enumerate(labels):
    close = abs(up_v[i] - op_v[i]) / max(up_v[i], op_v[i]) < 0.2
    ax.text(i - w / 2, up_v[i] * (4.5 if close else 1.6), fmt(up_v[i]), ha="center", va="bottom", fontsize=8, color=INK)
    ax.text(i + w / 2, op_v[i] * 1.6, fmt(op_v[i]), ha="center", va="bottom", fontsize=8, color=INK)
    if per_word[k]["upstream"] / per_word[k]["optimized"] > 1.5:
        ax.text(i, 2.4e3, f"{per_word[k]['upstream'] / per_word[k]['optimized']:.0f}x", ha="center", fontsize=9, color=OLIVE)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
ax.set_title("Wall clock per query", color=INK)

# ---- 右：每查询的构造量（对数轴）----
ax = axes[1]
labels = list(work)
up_v = [work[k]["upstream"] for k in labels]
op_v = [work[k]["optimized"] for k in labels]
pos = range(len(labels))
ax.bar([p - w / 2 for p in pos], up_v, w, label="upstream", color=TERRACOTTA)
ax.bar([p + w / 2 for p in pos], op_v, w, label="optimized", color=AMBER)
ax.set_yscale("log")
ax.set_xticks(list(pos))
ax.set_xticklabels([x.replace(" ", "\n") for x in labels], fontsize=8)
ax.set_ylabel("operations per query (log scale)")
ax.set_ylim(0.5, 5e6)
for i, k in enumerate(labels):
    ax.text(i - w / 2, up_v[i] * 1.6, fmt(up_v[i]), ha="center", va="bottom", fontsize=8, color=INK)
    ax.text(i + w / 2, op_v[i] * 1.6, fmt(op_v[i]), ha="center", va="bottom", fontsize=8, color=INK)
    ax.text(i, 3.2e6, f"{up_v[i] / op_v[i]:.0f}x", ha="center", fontsize=9, color=OLIVE)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
ax.set_title("Deterministic work counters", color=INK)

fig.suptitle("pyspellchecker: delete-variant index vs. quadratic re-expansion", color=INK, y=0.98)
fig.tight_layout(rect=(0.01, 0.02, 1, 0.9))
fig.savefig(OUT, dpi=150)
print("wrote", OUT)

# =====================================================================
# 第二张：随输入词长变化的耗时曲线（对数轴；颜色 + 标记双编码）
# =====================================================================
with open(os.path.join(HERE, "scan_len.json"), encoding="utf-8") as fobj:
    scan = json.load(fobj)

lens = [r["len"] for r in scan]
up_w = [r["upstream_median_ms"] / r["n_queries"] for r in scan]
op_w = [r["optimized_median_ms"] / r["n_queries"] for r in scan]

fig2, ax = plt.subplots(figsize=(8.6, 4.5))
ax.plot(lens, up_w, "-o", color=TERRACOTTA, markersize=6, linewidth=2, label="upstream")
ax.plot(lens, op_w, "-s", color=OLIVE, markersize=6, linewidth=2, label="optimized")
ax.set_yscale("log")
ax.set_xlabel("input word length (characters)")
ax.set_ylabel("ms per query (log scale)")
ax.set_title("Cost per distance-2 query vs. word length", color=INK)
ax.grid(True, which="major", linestyle=":", linewidth=0.6, color=MUTED, alpha=0.5)
ax.set_ylim(5e-2, 6e3)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False)
fig2.tight_layout(rect=(0.01, 0.02, 1, 0.94))
fig2.savefig(os.path.join(HERE, "scaling.png"), dpi=150)
print("wrote", os.path.join(HERE, "scaling.png"))
