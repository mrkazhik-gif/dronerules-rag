# -*- coding: utf-8 -*-
"""Figures of the Assignment 4 report from logs/a4_*.  Run:  python make_figures_a4.py  -> figures/fig_a4_timeline.png, fig_a4_oversight.png"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
S = json.loads((LOGS / "a4_summary.json").read_text(encoding="utf-8"))
req = [json.loads(l) for l in open(LOGS / "a4_requests.jsonl", encoding="utf-8") if l.strip()]
store = [json.loads(l) for l in open(LOGS / "a4_store_checks.jsonl", encoding="utf-8") if l.strip()]
INK, MUTED, GRID, BASE, SURFACE, BLUE, ORANGE, AQUA = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb", "#2a78d6", "#eb6834", "#1baf7a"
LABELS = {"normal": "normal", "naive": "naive\npoison", "recovery": "recov.", "stealth": "stealth", "compromise": "store\ncompr.", "compromise_avoid_canary": "compr.\navoid", "kb_loss": "30%\nloss",
          "latency_sim": "+3 s\nSIM", "errors_sim": "errors\nSIM", "normal_end": "normal"}


def timeline():
    x = [r["step"] for r in req]
    panels = [("Alert rate", [r["indicators"]["alert_rate"] * 100 for r in req], 10, "%", (0, 100)),
              ("Latency p95, s", [r["indicators"]["latency_p95"] for r in req], 9.7, " s", (0, 16)),
              ("Error rate", [r["indicators"]["error_rate"] * 100 for r in req], 5, "%", (0, 40))]
    fig, axes = plt.subplots(4, 1, figsize=(7.4, 4.5), dpi=220, sharex=True, facecolor=SURFACE, gridspec_kw={"hspace": 0.16})
    for ax, (title, y, limit, unit, ylim) in zip(axes, panels):
        ax.plot(x, y, color=BLUE, lw=1.3, zorder=3)
        ax.axhline(limit, color=ORANGE, lw=1, ls="--", zorder=2)
        ax.text(442, limit, f" limit {limit:g}{unit}", fontsize=6, color=MUTED, va="center")
        ax.set_ylim(*ylim); ax.set_ylabel(title, fontsize=6.5, color=INK)
    ax = axes[3]
    ax.step([s["step"] for s in store], [s["mismatches"] for s in store], where="post", color=BLUE, lw=1.3, zorder=3)
    ax.axhline(0, color=ORANGE, lw=1, ls="--", zorder=2)
    ax.text(442, 0, " limit 0", fontsize=6, color=MUTED, va="center")
    ax.set_ylim(-10, 270); ax.set_ylabel("Store mismatches", fontsize=6.5, color=INK)
    ax.set_xlabel("Request number. SIM = simulated fault. Lines use a sliding window of 20 requests, so they react and recover with a delay.", fontsize=6.5, color=MUTED)
    for i, ax in enumerate(axes):
        ax.set_facecolor(SURFACE); ax.tick_params(length=0, labelsize=6, colors=MUTED); ax.yaxis.grid(True, color=GRID, lw=0.5)
        for side in ("top", "right", "bottom"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color(BASE)
        for ph, s in S["phases"].items():
            ax.axvline(s["first_step"] - 0.5, color=BASE, lw=0.5, zorder=1)
            if i == 0:
                ax.text((s["first_step"] + s["last_step"]) / 2, 104, LABELS[ph], ha="center", va="bottom", fontsize=5.8, color=INK, linespacing=0.95)
        ax.set_xlim(1, 440)
    fig.subplots_adjust(left=0.085, right=0.915, top=0.92, bottom=0.085)
    fig.savefig(ROOT / "figures" / "fig_a4_timeline.png", facecolor=SURFACE)


def oversight():
    fig, ax = plt.subplots(figsize=(7.4, 3.25), dpi=220, facecolor=SURFACE)
    ax.set_xlim(0, 100); ax.set_ylim(0, 48); ax.axis("off")
    STYLE = {"auto": ("#e8eefb", BLUE), "human": ("#fdeadf", ORANGE), "input": ("#f2f1ec", BASE)}

    def box(x, y, w, h, text, kind):
        fill, edge = STYLE[kind]
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.9", fc=fill, ec=edge, lw=1.3 if kind == "human" else 0.9))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=6.1, color=INK, linespacing=1.12)

    def arrow(a, b, label=None, pos=None, color=MUTED, ls="-"):
        ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=color, lw=0.9, ls=ls, shrinkA=0, shrinkB=0, mutation_scale=7))
        if label:
            ax.text(pos[0], pos[1], label, fontsize=5.6, color=MUTED, ha="center", va="center", backgroundcolor=SURFACE)

    box(1, 34, 12, 9, "User\nquestion", "input")
    box(18, 34, 15, 9, "Input guard\nM2: verified\nretrieval", "auto")
    box(38, 34, 14, 9, "Generator\nQwen 3B", "auto")
    box(57, 34, 15, 9, "M3 check of\nnumbers against\nofficial text", "auto")
    box(77, 34, 21, 9, "Answer with official\nitems and warnings\n(advice only)", "auto")
    arrow((13.4, 38.5), (17.6, 38.5)); arrow((33.4, 38.5), (37.6, 38.5)); arrow((52.4, 38.5), (56.6, 38.5)); arrow((72.4, 38.5), (76.6, 38.5))
    box(57, 21, 15, 7.5, "Blocked:\nabstain automatically", "auto")
    arrow((64.5, 33.6), (64.5, 29))

    box(1, 19, 22, 9, "Audit log\nevery answer, verdict, evidence", "auto")
    arrow((25, 33.6), (14, 28.6), "logged", (16.5, 31.2))
    box(28, 19, 24, 9, "Monitor\nsliding-window indicators,\nstore integrity, canaries", "auto")
    arrow((23.4, 23.5), (27.6, 23.5))
    box(28, 5, 24, 8.5, "Threshold exceeded:\nalert raised automatically", "auto")
    arrow((40, 18.6), (40, 14))
    box(57, 5, 20, 8.5, "Store or canary failure:\nautomatic safe mode;\nother alerts pass through", "auto")
    arrow((52.4, 9.2), (56.6, 9.2))
    box(81, 5, 17, 8.5, "HUMAN: operator\nreviews the alert,\nescalates incident", "human")
    arrow((77.4, 9.2), (80.6, 9.2))
    box(77, 21, 21, 7.5, "HUMAN AUTHORISATION\nchange store or manifest, lift safe\nmode, approve deployment", "human")
    arrow((89.5, 13.9), (89.5, 20.6), color=ORANGE)
    ax.text(50, 46.6, "Blue: automated. Orange: requires a person. The assistant has no tools and cannot act on external systems.", ha="center", fontsize=6.6, color=INK)
    ax.text(50, 1.3, "Safe mode, named operators and alert delivery are a design for deployment, not implemented in the prototype. The monitor ran inside the test script.", ha="center", fontsize=5.8, color=MUTED)
    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
    fig.savefig(ROOT / "figures" / "fig_a4_oversight.png", facecolor=SURFACE)


timeline(); oversight(); print("ok")
