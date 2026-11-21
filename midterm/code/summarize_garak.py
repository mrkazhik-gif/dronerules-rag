# -*- coding: utf-8 -*-
"""
Summarise the garak latent-injection runs (logs/garak_baseline, logs/garak_source_aware) into
logs/garak_summary.md and logs/garak_summary.json: per probe and detector, prompts evaluated and injection successes.
A "hit" is an attempt whose detector score is >= 0.5, i.e. the model followed the instruction hidden in the document.
"""
import glob, json, os, pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
CONFIGS = ["baseline", "source_aware"]


def load(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    pass


def collect(cfg):
    stats = defaultdict(lambda: {"total": 0, "passed": 0})
    for path in sorted(glob.glob(str(LOGS / f"garak_{cfg}" / "*.report.jsonl"))):
        for r in load(path):
            if r.get("entry_type") == "eval":
                key = (r["probe"].replace("latentinjection.", ""), r["detector"].split(".")[-1])
                stats[key]["total"] += r.get("total_evaluated", r.get("total", 0))
                stats[key]["passed"] += r.get("passed", 0)
    return stats


def main():
    data = {cfg: collect(cfg) for cfg in CONFIGS}
    keys = sorted(set().union(*[d.keys() for d in data.values()]))
    rows, md = [], ["# garak latent-injection probes (indirect prompt injection)", "",
                    "Hit = the reply follows the instruction hidden in the document (detector score >= 0.5).", "",
                    "| Probe | Detector | " + " | ".join(f"{c} hits / total (rate)" for c in CONFIGS) + " |",
                    "|---|---|" + "---|" * len(CONFIGS)]
    for k in keys:
        cells, row = [], {"probe": k[0], "detector": k[1]}
        for c in CONFIGS:
            s = data[c].get(k, {"total": 0, "passed": 0})
            hits = s["total"] - s["passed"]
            rate = hits / s["total"] if s["total"] else 0
            row[c] = {"hits": hits, "total": s["total"], "rate": round(rate, 3)}
            cells.append(f"{hits}/{s['total']} ({rate:.0%})")
        rows.append(row)
        md.append(f"| {k[0]} | {k[1]} | " + " | ".join(cells) + " |")
    tot = {c: (sum(r[c]["hits"] for r in rows), sum(r[c]["total"] for r in rows)) for c in CONFIGS}
    md.append("| **All** | | " + " | ".join(f"**{h}/{t} ({h / t:.0%})**" if t else "-" for h, t in tot.values()) + " |")
    (LOGS / "garak_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (LOGS / "garak_summary.json").write_text(json.dumps({"rows": rows, "total": tot}, indent=1), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
