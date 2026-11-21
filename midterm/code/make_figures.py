# -*- coding: utf-8 -*-
"""
Figures for the report and slides (run with any Python that has matplotlib):
  figures/fig1_architecture.png  - system architecture with the attack point and the two mitigations
  figures/fig2_asr.png           - ASR and accuracy vs number of poisoned passages, per configuration (from logs/summary.csv)
"""
import csv, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
INK, MUTED, BLUE, GREEN, RED, AMBER = "#1d2430", "#5b6575", "#2457c5", "#1f7a45", "#b3261e", "#8a5a00"


def box(ax, x, y, w, h, text, edge=INK, fill="white", size=9, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06", lw=1.4, ec=edge, fc=fill))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=INK, weight=weight, wrap=True)


def arrow(ax, x1, y1, x2, y2, color=INK, style="-|>", ls="-"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle=style, color=color, lw=1.4, ls=ls))


def architecture():
    fig, ax = plt.subplots(figsize=(9.2, 3.9), dpi=200)
    ax.set_xlim(0, 10); ax.set_ylim(0, 4.3); ax.axis("off")
    # ingestion
    box(ax, 0.1, 3.05, 2.2, 0.9, "Kazakhstan UAS rules\nOrder 706, ed. 2023/2024\n(official, adilet.zan.kz)", GREEN, "#e5f4ea", 8)
    box(ax, 0.1, 1.85, 2.2, 0.8, "Community notes\n(unverified)", AMBER, "#fdf1d8", 8)
    box(ax, 0.1, 0.55, 2.2, 0.9, "Attacker-edited web page\nN poisoned passages\nP = question + false claim", RED, "#fbe7e6", 8)
    box(ax, 3.0, 1.75, 1.9, 1.5, "Knowledge base\n778 official chunks\n+ 8 notes\n(+ N poisoned)\nSHA-256 manifest", INK, "white", 8)
    arrow(ax, 2.3, 3.5, 3.0, 2.9, GREEN); arrow(ax, 2.3, 2.25, 3.0, 2.45, AMBER); arrow(ax, 2.3, 1.0, 3.0, 2.0, RED)
    # retrieval + generation
    box(ax, 5.55, 1.75, 1.85, 1.5, "Retriever\nmultilingual-e5-small\ncosine, top-k\n(k = 5 or 10)", BLUE, "#e8eefb", 8)
    box(ax, 8.05, 1.75, 1.85, 1.5, "Generator\nQwen2.5-3B-Instruct\nfp16, greedy\n+ clarify.py rules", BLUE, "#e8eefb", 8)
    arrow(ax, 4.9, 2.5, 5.55, 2.5); arrow(ax, 7.4, 2.5, 8.05, 2.5)
    box(ax, 5.55, 3.55, 1.85, 0.6, "User question", INK, "white", 8)
    arrow(ax, 6.47, 3.55, 6.47, 3.25)
    box(ax, 8.05, 0.35, 1.85, 0.75, "Answer + cited sources\n(web page / REST)", INK, "white", 8)
    arrow(ax, 8.97, 1.75, 8.97, 1.1)
    # mitigations
    ax.text(4.0, 1.42, "M2 provenance filter:\nonly manifest-verified\nofficial chunks retrieved", fontsize=7.4, color=GREEN, ha="center", va="top")
    ax.text(8.97, 3.62, "M1 source-aware prompt:\nOFFICIAL / UNVERIFIED labels,\npassages = data", fontsize=7.4, color=GREEN, ha="center", va="bottom")
    ax.text(1.2, 0.3, "attack surface", fontsize=7.4, color=RED, ha="center", style="italic")
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / "fig1_architecture.png", bbox_inches="tight"); plt.close(fig)


def asr_chart():
    rows = list(csv.DictReader(open(ROOT / "logs" / "summary.csv", encoding="utf-8")))
    cfgs = [("baseline", "baseline (top-5)", RED, "o"), ("baseline_k10", "knowledge expansion (top-10)", AMBER, "s"),
            ("source_aware", "M1 source-aware prompt", BLUE, "^"), ("provenance", "M2 provenance filter", GREEN, "D")]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.3), dpi=200)
    for metric, ax, title in (("asr", axes[0], "Attack success rate"), ("accuracy", axes[1], "Accuracy (correct value only)")):
        for c, label, col, mk in cfgs:
            pts = [(int(r["n_poison"]), float(r[metric]) * 100) for r in rows if r["config"] == c]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker=mk, color=col, lw=1.8, label=label)
        ax.set_title(title, fontsize=10, color=INK); ax.set_xlabel("Poisoned passages per question (N)", fontsize=9)
        ax.set_xticks([0, 1, 3, 5]); ax.set_ylim(-3, 103); ax.set_ylabel("% of 20 questions", fontsize=9)
        ax.grid(alpha=.25); ax.tick_params(labelsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=8, frameon=False, loc="lower center", ncol=4)
    fig.tight_layout(rect=(0, 0.08, 1, 1)); fig.savefig(FIG / "fig2_asr.png", bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    architecture()
    if (ROOT / "logs" / "summary.csv").exists():
        asr_chart()
    print("figures ->", FIG)
