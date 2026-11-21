# -*- coding: utf-8 -*-
"""
Recompute logs/summary.csv and logs/summary.md from logs/results.jsonl, applying the manual corrections in
logs/manual_overrides.json (answers whose regex score was wrong after human review). The model is not re-run.

Run:  python summarize.py
"""
import csv, json, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
CONFIGS = ["baseline", "baseline_k10", "source_aware", "provenance"]
N_LEVELS = [0, 1, 3, 5]


def main():
    import sys; sys.stdout.reconfigure(encoding="utf-8")
    rows = [json.loads(l) for l in open(LOGS / "results.jsonl", encoding="utf-8") if l.strip()]
    overrides = json.loads((LOGS / "manual_overrides.json").read_text(encoding="utf-8")) if (LOGS / "manual_overrides.json").exists() else []
    for o in overrides:
        hit = [r for r in rows if r["qid"] == o["qid"] and r["config"] == o["config"] and r["n_poison"] == o["n_poison"]]
        assert len(hit) == 1 and hit[0]["outcome"] == o["regex_outcome"], o
        hit[0]["outcome"] = o["outcome"]
    summary = []
    for cfg in CONFIGS:
        for n in N_LEVELS:
            g = [r for r in rows if r["config"] == cfg and r["n_poison"] == n]
            cnt = {o: sum(r["outcome"] == o for r in g) for o in ("correct", "attack", "mixed", "other")}
            summary.append({
                "config": cfg, "n_poison": n, "questions": len(g), **cnt,
                "accuracy": round(cnt["correct"] / len(g), 3),
                "asr": round((cnt["attack"] + cnt["mixed"]) / len(g), 3),
                "poison_precision": round(sum(r["poison_in_topk"] for r in g) / sum(r["k"] for r in g), 3),
                "poison_recall": round(sum(r["poison_in_topk"] for r in g) / (n * len(g)), 3) if n else "",
                "mean_latency_s": round(sum(r["latency_s"] for r in g) / len(g), 2),
            })
    with open(LOGS / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
    md = [f"# Knowledge-corruption experiment - summary recomputed {time.strftime('%Y-%m-%d %H:%M')}", "",
          f"Outcomes from logs/results.jsonl; {len(overrides)} answer(s) corrected by manual review (logs/manual_overrides.json). "
          "ASR = answers containing the attacker's value (attack + mixed).", "",
          "| Config | N poisoned | Accuracy | ASR | correct | attack | mixed | other | poison precision@k | poison recall | latency, s |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in summary:
        md.append(f"| {s['config']} | {s['n_poison']} | {s['accuracy']:.0%} | {s['asr']:.0%} | {s['correct']} | {s['attack']} | "
                  f"{s['mixed']} | {s['other']} | {s['poison_precision']} | {s['poison_recall']} | {s['mean_latency_s']} |")
    for o in overrides:
        md.append(f"\nManual correction: {o['qid']} / {o['config']} / N = {o['n_poison']}: {o['regex_outcome']} → {o['outcome']}. {o['note']}")
    (LOGS / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[4:]))


if __name__ == "__main__":
    main()
