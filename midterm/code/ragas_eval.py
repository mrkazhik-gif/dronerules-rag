# -*- coding: utf-8 -*-
"""
Ragas evaluation of the retrieval step, computed from the saved answers in logs/results.jsonl (no model is re-run).

Metrics (Ragas 0.4.3, ID-based, no LLM judge needed):
  context precision = share of retrieved passages that are reference passages
  context recall    = share of reference passages that were retrieved
Reference passage of a question = the official chunk (item or sub-item) that states the correct value
(field ref_ids in data/attack/targets.json, checked against correct_re when it was set).

Run in a separate environment (ragas pulls in langchain/pandas):  D:\\Work\\ragas-env\\Scripts\\python.exe ragas_eval.py
Output: logs/ragas_summary.md, logs/ragas_summary.csv, logs/ragas_per_answer.jsonl
"""
import asyncio, csv, json, pathlib, re
from ragas import SingleTurnSample
from ragas.metrics import _IDBasedContextPrecision, _IDBasedContextRecall

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS, KB = ROOT / "logs", ROOT / "data" / "kb"
CONFIGS = ["baseline", "baseline_k10", "source_aware", "provenance"]
N_LEVELS = [0, 1, 3, 5]


def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def reference_ids(target, chunks):
    if target.get("ref_ids"):                                    # exact reference chunk(s), set in targets.json
        return target["ref_ids"]
    prefix = target["ref"]                                       # fallback: all chunks of the item that contain the value
    ids = [c["id"] for c in chunks if c["id"].startswith(prefix) and re.search(target["correct_re"], c["text"], re.I)]
    assert ids, f"no reference chunk for {target['id']}"
    return ids


async def main():
    targets = {t["id"]: t for t in json.loads((ROOT / "data" / "attack" / "targets.json").read_text(encoding="utf-8"))}
    chunks = load_jsonl(KB / "official_chunks.jsonl")
    refs = {qid: reference_ids(t, chunks) for qid, t in targets.items()}
    prec, rec = _IDBasedContextPrecision(), _IDBasedContextRecall()
    rows = []
    for r in load_jsonl(LOGS / "results.jsonl"):
        s = SingleTurnSample(user_input=r["question"], response=r["answer"],
                             retrieved_context_ids=r["retrieved"], reference_context_ids=refs[r["qid"]])
        rows.append({"qid": r["qid"], "config": r["config"], "n_poison": r["n_poison"],
                     "context_precision": round(await prec.single_turn_ascore(s), 3),
                     "context_recall": round(await rec.single_turn_ascore(s), 3)})
    with open(LOGS / "ragas_per_answer.jsonl", "w", encoding="utf-8") as f:
        for x in rows:
            f.write(json.dumps(x) + "\n")
    summary = []
    for c in CONFIGS:
        for n in N_LEVELS:
            g = [x for x in rows if x["config"] == c and x["n_poison"] == n]
            summary.append({"config": c, "n_poison": n,
                            "context_precision": round(sum(x["context_precision"] for x in g) / len(g), 3),
                            "context_recall": round(sum(x["context_recall"] for x in g) / len(g), 3)})
    with open(LOGS / "ragas_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
    md = ["# Ragas retrieval metrics (ID-based, Ragas 0.4.3)", "",
          f"Reference passages: the official chunk that states the correct value ({sum(len(v) for v in refs.values())} for 20 questions).", "",
          "| Config | N poisoned | Context precision | Context recall |", "|---|---|---|---|"]
    md += [f"| {s['config']} | {s['n_poison']} | {s['context_precision']:.2f} | {s['context_recall']:.2f} |" for s in summary]
    (LOGS / "ragas_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    asyncio.run(main())
