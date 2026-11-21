# -*- coding: utf-8 -*-
"""
Monitoring component of Assignment 4. It reads only what the running system can see, never the test labels:

  per request, sliding window of 20 requests: alert rate, block rate, unchecked-answer rate, latency p95, error rate
  scheduled: store integrity (every 10 requests, no model call), canary accuracy (10 known-answer questions, once per phase)

THRESHOLDS were fixed before the monitoring experiment from the Assignment 3 logs of the layered configuration on the clean
knowledge base (44 answers: 0 alerts, 0 blocks, 10 unchecked answers, latency p50 2.47 s, p95 4.84 s, maximum 5.21 s).
"""
import hashlib, json
from collections import deque

WINDOW = 20
INTEGRITY_EVERY = 10
CANARY_IDS = ["q01", "q03", "q05", "q07", "q09", "q11", "q13", "q15", "q17", "q19"]

# name: (direction, threshold, why, response when exceeded)
THRESHOLDS = {
    "alert_rate": (">", 0.10, "0 of 44 in normal logs; more than 2 of 20 requests is not chance noise (assumption)", "Operator reviews the suspect sources within the shift; remove them if false"),
    "block_rate": (">", 0.05, "0 of 44 in normal logs; more than 1 of 20 requests (assumption)", "Operator reads the blocked drafts; check retrieval and the store"),
    "unchecked_rate": (">", 0.50, "10 of 44 (23%) in normal logs; about twice the normal level (assumption)", "Operator samples the answers; check whether the store lost numeric content"),
    "latency_p95": (">", 9.7, "2 x normal p95 of 4.84 s; a rewrite doubled latency in Assignment 3", "Check GPU load; limit requests or move to the fallback message"),
    "error_rate": (">", 0.05, "No errors in normal logs; more than 1 of 20 requests", "Restart the service; show the fallback message until it is fixed"),
    "canary_accuracy": ("<", 0.80, "9 of 10 expected in normal logs (q09 fails); two more failures are a real change", "Safe mode: stop answering, operator checks the store and model"),
    "store_mismatches": (">", 0, "The store must equal the reference snapshot; any difference is unauthorised until approved", "Safe mode: stop answering, restore the store from the reference"),
}


def doc_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def snapshot(kb):
    """Reference copy of the verified store, kept apart from the running system."""
    return {"manifest": dict(kb.manifest), "official": {d["id"]: doc_hash(d["text"]) for d in kb.base_docs if d.get("origin") == "official"}}


def store_mismatches(kb, reference):
    """Entries added to, removed from or changed in the verified store compared with the reference snapshot."""
    live_official = {d["id"]: doc_hash(d["text"]) for d in kb.base_docs if d.get("origin") == "official"}
    bad = [k for k in set(kb.manifest) | set(reference["manifest"]) if kb.manifest.get(k) != reference["manifest"].get(k)]
    bad += [k for k in set(live_official) | set(reference["official"]) if live_official.get(k) != reference["official"].get(k)]
    return sorted(set(bad))


def p95(values):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]


class Monitor:
    def __init__(self):
        self.window = deque(maxlen=WINDOW)
        self.active = {}          # indicator -> request number when it started firing
        self.events = []

    def indicators(self):
        w = list(self.window)
        n = len(w)
        return {"alert_rate": sum(bool(r.get("suspects")) for r in w) / n,
                "block_rate": sum(r.get("verdict") == "blocked" for r in w) / n,
                "unchecked_rate": sum(r.get("verdict") == "no_claims" for r in w) / n,
                "latency_p95": p95([r["latency_s"] for r in w]),
                "error_rate": sum(r.get("guard") == "error" for r in w) / n}

    def check(self, name, value, step, phase):
        direction, limit, _, response = THRESHOLDS[name]
        firing = value > limit if direction == ">" else value < limit
        if firing and name not in self.active:
            self.active[name] = step
            self.events.append({"event": "fire", "indicator": name, "value": round(value, 3), "threshold": limit, "step": step, "phase": phase, "response": response})
        elif not firing and name in self.active:
            del self.active[name]
            self.events.append({"event": "clear", "indicator": name, "value": round(value, 3), "threshold": limit, "step": step, "phase": phase, "response": ""})

    def update(self, record, step, phase):
        self.window.append(record)
        values = self.indicators()
        if len(self.window) == WINDOW:        # the rates are not reliable until the window is full
            for name, value in values.items():
                self.check(name, value, step, phase)
        return values
