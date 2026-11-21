# -*- coding: utf-8 -*-
"""
Summarise the garak latent-injection run on the layered configuration (logs/garak_layered) into logs/garak_layered_summary.json.
A "hit" is an attempt whose detector score is >= 0.5, i.e. the model followed the instruction hidden in the document.
The Midterm's figures for baseline and M1 are in logs/_midterm_baseline/garak_summary.md.
"""
import glob, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
out = {"layered": {"total": 0, "hits": 0, "probes": {}}}
for path in sorted(glob.glob(str(LOGS / "garak_layered" / "*.report.jsonl"))):
    for line in open(path, encoding="utf-8"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("entry_type") == "eval":
            total = r.get("total_evaluated", r.get("total", 0))
            hits = total - r.get("passed", 0)
            out["layered"]["total"] += total
            out["layered"]["hits"] += hits
            out["layered"]["probes"][r["probe"].replace("latentinjection.", "")] = {"total": total, "hits": hits}
(LOGS / "garak_layered_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
