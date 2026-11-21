# -*- coding: utf-8 -*-
"""Figure of the AIGoat extension from logs/aigoat_*.  Run:  python make_figure_aigoat.py  -> figures/fig_a4_aigoat.png"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
S = json.loads((LOGS / "aigoat_summary.json").read_text(encoding="utf-8"))
req = [json.loads(l) for l in open(LOGS / "aigoat_requests.jsonl", encoding="utf-8") if l.strip()]
store = [json.loads(l) for l in open(LOGS / "aigoat_store_checks.jsonl", encoding="utf-8") if l.strip()]
INK, MUTED, GRID, BASE, SURFACE, BLUE, ORANGE, RED = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb", "#2a78d6", "#eb6834", "#c0392b"
LABELS = {"normal": "normal", "aigoat_injection": "LLM01-4\ninjection", "aigoat_stuffing": "LLM09-2\nstuffing", "aigoat_trust_spoof": "LLM09-3\ntrust spoof",
          "aigoat_flooding": "LLM09-4\nflooding", "aigoat_injection_insider": "LLM01-4 after\nstore compromise"}
N = len(req)

x = [r["step"] for r in req]
panels = [("Alert rate", [r["indicators"]["alert_rate"] * 100 for r in req], 10, "%", (0, 100)),
          ("Injection rate", [r["indicators"]["injection_rate"] * 100 for r in req], 0, "%", (-5, 100))]
fig, axes = plt.subplots(4, 1, figsize=(7.4, 4.3), dpi=220, sharex=True, facecolor=SURFACE, gridspec_kw={"hspace": 0.18, "height_ratios": [1, 1, 0.8, 0.55]})
for ax, (title, y, limit, unit, ylim) in zip(axes, panels):
    ax.plot(x, y, color=BLUE, lw=1.3, zorder=3)
    ax.axhline(limit, color=ORANGE, lw=1, ls="--", zorder=2)
    ax.text(N + 2, limit, f" limit {limit:g}{unit}", fontsize=6, color=MUTED, va="center")
    ax.set_ylim(*ylim); ax.set_ylabel(title, fontsize=6.5, color=INK)
ax = axes[2]
ax.step([s["step"] for s in store], [s["mismatches"] for s in store], where="post", color=BLUE, lw=1.3, zorder=3)
ax.axhline(0, color=ORANGE, lw=1, ls="--", zorder=2)
ax.text(N + 2, 0, " limit 0", fontsize=6, color=MUTED, va="center")
ax.set_ylim(-8, 75); ax.set_ylabel("Store\nmismatches", fontsize=6.5, color=INK)
ax = axes[3]
bad = [r["step"] for r in req if r["truth_false_value"]]
inj = [r["step"] for r in req if r["truth_injection_followed"] and not r["truth_false_value"]]
ax.scatter(bad, [1] * len(bad), s=7, color=RED, zorder=3, label="false value shown (also followed the instruction)")
ax.scatter(inj, [1] * len(inj), s=7, color=ORANGE, zorder=3, label="followed the instruction only")
ax.set_ylim(0.4, 1.6); ax.set_yticks([]); ax.set_ylabel("Harm\n(test label)", fontsize=6.5, color=INK)
ax.legend(fontsize=5.6, frameon=False, loc="center left", bbox_to_anchor=(0.0, 0.5), handletextpad=0.2)
ax.set_xlabel("Request number. Lines use a sliding window of 20 requests; the harm row uses test labels that the monitor does not see.", fontsize=6.5, color=MUTED)
for i, ax in enumerate(axes):
    ax.set_facecolor(SURFACE); ax.tick_params(length=0, labelsize=6, colors=MUTED)
    if i < 3:
        ax.yaxis.grid(True, color=GRID, lw=0.5)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(BASE)
    for ph, s in S["phases"].items():
        ax.axvline(s["first_step"] - 0.5, color=BASE, lw=0.5, zorder=1)
        if i == 0:
            ax.text((s["first_step"] + s["last_step"]) / 2, 104, LABELS[ph], ha="center", va="bottom", fontsize=5.8, color=INK, linespacing=0.95)
    ax.set_xlim(1, N)
fig.subplots_adjust(left=0.085, right=0.915, top=0.91, bottom=0.085)
fig.savefig(ROOT / "figures" / "fig_a4_aigoat.png", facecolor=SURFACE)
print("ok")
