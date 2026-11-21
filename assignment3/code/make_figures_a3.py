# -*- coding: utf-8 -*-
"""Figure of the Assignment 3 report from logs/a3_summary.json.  Run:  python make_figures_a3.py  -> figures/fig_a3_asr.png"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "logs" / "a3_summary.json").read_text(encoding="utf-8"))
INK, MUTED, GRID, BASE, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
SERIES = [("baseline", "Baseline", "#2a78d6"), ("verify_fallback", "M3b verifier", "#eb6834"), ("layered", "Layered (M2 + M3)", "#1baf7a")]
SCENARIOS = [("naive", "Naive poisoning\n(as in the Midterm)"), ("word_numbers", "Value in Russian words"), ("latin_units", "Latin units (\"5 kg\")"),
             ("value_collision", "Real value from\nanother item"), ("store_compromise", "Verified store\ncompromised")]


def asr(scenario, cfg):
    return S["main"][f"{cfg}|5"]["asr"] if scenario == "naive" else S["adaptive"][f"{scenario}|{cfg}"]["asr"]


fig, ax = plt.subplots(figsize=(7.2, 2.75), dpi=220, facecolor=SURFACE)
ax.set_facecolor(SURFACE)
h, gap = 0.24, 0.03
for s, (cfg, name, color) in enumerate(SERIES):
    ys = [i + (s - 1) * (h + gap) for i in range(len(SCENARIOS))]
    vals = [asr(k, cfg) * 100 for k, _ in SCENARIOS]
    ax.barh(ys, vals, height=h, color=color, label=name, zorder=3)
    for y, v in zip(ys, vals):
        ax.text(v + 1.2, y, f"{v:.0f}%", va="center", ha="left", fontsize=7, color=INK)
ax.set_yticks(range(len(SCENARIOS)), [n for _, n in SCENARIOS], fontsize=7.5, color=INK)
ax.invert_yaxis()
ax.set_xlim(0, 112)
ax.set_xticks([0, 25, 50, 75, 100], ["0", "25", "50", "75", "100%"], fontsize=7, color=MUTED)
ax.set_xlabel("Attack success rate, N = 5 poisoned passages per question", fontsize=7.5, color=MUTED)
ax.xaxis.grid(True, color=GRID, lw=0.6, zorder=0)
ax.tick_params(length=0)
for side in ("top", "right", "bottom"):
    ax.spines[side].set_visible(False)
ax.spines["left"].set_color(BASE)
ax.legend(loc="upper center", bbox_to_anchor=(0.42, 1.14), ncol=3, frameon=False, fontsize=7.5, handlelength=1, labelcolor=INK)
fig.tight_layout(pad=0.4)
(ROOT / "figures").mkdir(exist_ok=True)
fig.savefig(ROOT / "figures" / "fig_a3_asr.png", facecolor=SURFACE)
print("ok")
