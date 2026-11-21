# -*- coding: utf-8 -*-
"""
Controlled monitoring experiment of Assignment 4. The layered configuration answers a request stream (the 20 target questions
and 24 held-out benign questions, shuffled) while the knowledge base goes through controlled failures. All passages are
synthetic test artefacts on the local testbed.

Real model answers: normal, naive, stealth, compromise, compromise_avoid_canary, kb_loss, recovery.
SIMULATED faults, injected in this script, not real incidents: latency_sim (+3 s per model call), errors_sim (every 4th model call fails).

The test labels (truth_*) are stored for evaluation only; monitor.py does not read them.

Run:  python run_monitoring.py     -> logs/a4_requests.jsonl, a4_events.jsonl, a4_canaries.jsonl, a4_store_checks.jsonl
"""
import json, pathlib, random, re, sys, time
from rag_core import RAGAssistant
from poison import TARGETS, poisoned_passages
from attacks_a3 import value_collision, latin_units, compromise_store
from monitor import Monitor, snapshot, store_mismatches, CANARY_IDS, INTEGRITY_EVERY, THRESHOLDS

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
HELDOUT = json.loads((ROOT / "data" / "attack" / "benign_heldout.json").read_text(encoding="utf-8"))
CONFIG = "layered"
SEED = 1103
PHASES = ["normal", "naive", "recovery", "stealth", "compromise", "compromise_avoid_canary", "kb_loss", "latency_sim", "errors_sim", "normal_end"]


def stream(phase_index):
    items = [("target", t) for t in TARGETS] + [("benign", t) for t in HELDOUT]
    random.Random(SEED + phase_index).shuffle(items)
    return items


def score(answer, kind, t, target_re):
    correct = re.search(t["correct_re"], answer, re.I) is not None
    false_value = kind == "target" and target_re is not None and re.search(target_re, answer, re.I) is not None
    return correct and not false_value, false_value


class Scenario:
    """Puts the knowledge base and model into the state of one phase and restores them afterwards."""

    def __init__(self, rag):
        self.rag = rag
        self.base = (rag.kb.base_docs, rag.kb.base_vecs)
        self.chat = rag.llm.chat
        self.undo_store = lambda: None
        self.target_re = {t["id"]: None for t in TARGETS}

    def enter(self, phase):
        rag, passages = self.rag, []
        self.target_re = {t["id"]: None for t in TARGETS}
        if phase == "naive":
            for t in TARGETS:
                passages += poisoned_passages(t, 3); self.target_re[t["id"]] = t["target_re"]
        elif phase == "stealth":        # real value from another item where one exists, otherwise Latin units
            rag.kb.set_extra([])
            for t in TARGETS:
                c = value_collision(t, 3, rag.kb.search(t["question"], 5, only_verified=True))
                chosen = c[:2] if c else latin_units(t, 3)
                passages += chosen[0]; self.target_re[t["id"]] = chosen[1]
        elif phase in ("compromise", "compromise_avoid_canary"):
            for t in TARGETS:
                if phase == "compromise" or t["id"] not in CANARY_IDS:
                    passages += poisoned_passages(t, 3); self.target_re[t["id"]] = t["target_re"]
            self.undo_store = compromise_store(rag.kb, passages)
        elif phase == "kb_loss":        # an ingestion failure: 30% of the official chunks are gone, the rest is unchanged
            keep = [i for i in range(len(self.base[0])) if self.base[0][i].get("origin") != "official" or random.Random(i + SEED).random() > 0.30]
            rag.kb.base_docs, rag.kb.base_vecs = [self.base[0][i] for i in keep], self.base[1][keep]
        elif phase == "latency_sim":
            def slow(*a, **k):
                time.sleep(3.0)
                return self.chat(*a, **k)
            rag.llm.chat = slow
        elif phase == "errors_sim":
            calls = {"n": 0}

            def failing(*a, **k):
                calls["n"] += 1
                if calls["n"] % 4 == 0:
                    raise RuntimeError("simulated generator failure")
                return self.chat(*a, **k)
            rag.llm.chat = failing
        rag.kb.set_extra(passages)

    def leave(self):
        rag = self.rag
        self.undo_store(); self.undo_store = lambda: None
        rag.kb.base_docs, rag.kb.base_vecs = self.base
        rag.llm.chat = self.chat
        rag.kb.set_extra([])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    LOGS.mkdir(exist_ok=True)
    rag = RAGAssistant()
    reference = snapshot(rag.kb)
    monitor, scenario, step = Monitor(), Scenario(rag), 0
    by_id = {t["id"]: t for t in TARGETS}
    (LOGS / "a4_thresholds.json").write_text(json.dumps(THRESHOLDS, ensure_ascii=False, indent=1), encoding="utf-8")
    req_f = open(LOGS / "a4_requests.jsonl", "w", encoding="utf-8")
    can_f = open(LOGS / "a4_canaries.jsonl", "w", encoding="utf-8")
    sto_f = open(LOGS / "a4_store_checks.jsonl", "w", encoding="utf-8")
    for pi, phase in enumerate(PHASES):
        scenario.enter(phase)
        for ri, (kind, t) in enumerate(stream(pi)):
            step += 1
            r = rag.safe_ask(t["question"], CONFIG)
            ok, false_value = score(r["answer"], kind, t, scenario.target_re.get(t["id"]) if kind == "target" else None)
            rec = {"step": step, "phase": phase, "kind": kind, "qid": t["id"], "question": t["question"], "answer": r["answer"], "verdict": r.get("verdict", ""),
                   "action": r.get("action", ""), "suspects": r.get("suspects", []), "unsupported": r.get("unsupported", []), "guard": r.get("guard", ""),
                   "error": r.get("error", ""), "latency_s": r["latency_s"], "truth_correct": ok, "truth_false_value": false_value}
            values = monitor.update(rec, step, phase)
            rec["indicators"] = {k: round(v, 3) for k, v in values.items()}
            if step % INTEGRITY_EVERY == 0:
                bad = store_mismatches(rag.kb, reference)
                rec["store_mismatches"] = len(bad)
                monitor.check("store_mismatches", len(bad), step, phase)
                sto_f.write(json.dumps({"step": step, "phase": phase, "mismatches": len(bad), "examples": bad[:5]}, ensure_ascii=False) + "\n"); sto_f.flush()
            req_f.write(json.dumps(rec, ensure_ascii=False) + "\n"); req_f.flush()
            print(phase, step, kind, t["id"], r.get("verdict", ""), r["latency_s"], "FALSE" if false_value else "", sorted(monitor.active), flush=True)
        # scheduled check at the end of the phase: known-answer questions the system's operator can score automatically
        right = 0
        for cid in CANARY_IDS:
            r = rag.safe_ask(by_id[cid]["question"], CONFIG)
            hit = re.search(by_id[cid]["correct_re"], r["answer"], re.I) is not None
            right += hit
            can_f.write(json.dumps({"step": step, "phase": phase, "qid": cid, "correct": hit, "answer": r["answer"], "latency_s": r["latency_s"]}, ensure_ascii=False) + "\n"); can_f.flush()
        monitor.check("canary_accuracy", right / len(CANARY_IDS), step, phase)
        print("### phase done", phase, "canary", right, sorted(monitor.active), flush=True)
        scenario.leave()
    with open(LOGS / "a4_events.jsonl", "w", encoding="utf-8") as f:
        for e in monitor.events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print("### done", flush=True)


if __name__ == "__main__":
    main()
