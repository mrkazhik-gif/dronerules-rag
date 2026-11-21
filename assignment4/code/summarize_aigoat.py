# -*- coding: utf-8 -*-
"""
Results of the AIGoat extension from logs/aigoat_*.jsonl (no model calls). Test labels are used here for evaluation only.
Benign answers are rescored with the current expected thesis in benign_heldout.json, as in summarize_a4.py.

Per phase the rates are shares of the phase's own 44 requests (the monitor's 20-request window carries values over
from the previous phase, so the window maximum is not used here).

Run:  python summarize_aigoat.py     -> logs/aigoat_summary.md, logs/aigoat_summary.json
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
PHASES = ["normal", "aigoat_injection", "aigoat_stuffing", "aigoat_trust_spoof", "aigoat_flooding", "aigoat_injection_insider"]


def load(name):
    return [json.loads(l) for l in open(LOGS / f"aigoat_{name}.jsonl", encoding="utf-8") if l.strip()]


def is_attack(pid):
    return pid.startswith("aigoat-") or pid.startswith("poison-")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    req, events, canaries, store = load("requests"), load("events"), load("canaries"), load("store_checks")
    expected = {q["id"]: q["correct_re"] for q in json.loads((ROOT / "data" / "attack" / "benign_heldout.json").read_text(encoding="utf-8"))}
    for r in req:
        if r["kind"] == "benign":
            r["truth_correct"] = re.search(expected[r["qid"]], r["answer"], re.I) is not None and not r["truth_injection_followed"]
    out, md = {"phases": {}}, ["# Assignment 4 - AIGoat extension", "",
        "| Phase | Requests | Correct | False value shown | Followed injected instruction | Attack passage in unfiltered top-5 | Attack passage in model context "
        "| Suspect alert | Injection scan hit | Blocked | p95, s | Canary | Store mismatches (last) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for ph in PHASES:
        g = [r for r in req if r["phase"] == ph]
        lat = sorted(r["latency_s"] for r in g)
        can = [c for c in canaries if c["phase"] == ph]
        st = [s for s in store if s["phase"] == ph]
        n = len(g)
        s = {"requests": n, "first_step": g[0]["step"], "last_step": g[-1]["step"],
             "correct": sum(r["truth_correct"] for r in g) / n, "false_value": sum(bool(r["truth_false_value"]) for r in g),
             "injection_followed": sum(r["truth_injection_followed"] for r in g),
             "attack_in_top5": sum(any(is_attack(i) for i in r["unfiltered_ids"]) for r in g) / n,
             "attack_in_context": sum(any(is_attack(i) for i in r["context_ids"]) for r in g) / n,
             "suspect": sum(bool(r["suspects"]) for r in g) / n, "injection_scan": sum(bool(r["injection_retrieved"]) for r in g) / n,
             "blocked": sum(r["verdict"] == "blocked" for r in g) / n, "p95": lat[min(n - 1, int(0.95 * n))],
             "errors": sum(r["guard"] == "error" for r in g) / n,
             "canary": sum(c["correct"] for c in can) / len(can), "store": st[-1]["mismatches"] if st else 0}
        out["phases"][ph] = s
        md.append(f"| {ph} | {n} | {s['correct']:.0%} | {s['false_value']} | {s['injection_followed']} | {s['attack_in_top5']:.0%} | {s['attack_in_context']:.0%} "
                  f"| {s['suspect']:.0%} | {s['injection_scan']:.0%} | {s['blocked']:.0%} | {s['p95']:.1f} | {s['canary']:.0%} | {s['store']} |")

    md += ["", "## Monitor events", "", "| Step | Phase | Event | Indicator | Value | Threshold | Requests since phase start | False-value answers shown in the phase before it |",
           "|---|---|---|---|---|---|---|---|"]
    out["events"] = []
    for e in events:
        ph = out["phases"][e["phase"]]
        since = e["step"] - ph["first_step"] + 1
        shown = sum(bool(r["truth_false_value"]) for r in req if r["phase"] == e["phase"] and r["step"] <= e["step"])
        out["events"].append({**e, "since_phase_start": since, "false_shown_before": shown})
        md.append(f"| {e['step']} | {e['phase']} | {e['event']} | {e['indicator']} | {e['value']} | {e['threshold']} | {since} | {shown} |")

    false_alarms = [e for e in events if e["event"] == "fire" and e["phase"] == "normal"]
    out["false_alarm_events"] = false_alarms
    md += ["", f"Fired during the normal phase: {len(false_alarms)}"]
    t = json.loads((LOGS / "aigoat_thresholds.json").read_text(encoding="utf-8"))
    out["thresholds"] = {k: {"direction": v[0], "limit": v[1], "why": v[2], "response": v[3]} for k, v in t.items()}
    (LOGS / "aigoat_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (LOGS / "aigoat_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
