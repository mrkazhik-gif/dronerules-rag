# -*- coding: utf-8 -*-
"""
Results of the monitoring experiment from logs/a4_*.jsonl (no model calls). Test labels are used here for evaluation only.
Benign answers are rescored with the current expected thesis in benign_heldout.json.

Run:  python summarize_a4.py     -> logs/a4_summary.md, logs/a4_summary.json
"""
import json, pathlib, re, sys
from monitor import THRESHOLDS

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
PHASES = ["normal", "naive", "recovery", "stealth", "compromise", "compromise_avoid_canary", "kb_loss", "latency_sim", "errors_sim", "normal_end"]
SIMULATED = {"latency_sim", "errors_sim"}
INDICATORS = ["alert_rate", "block_rate", "unchecked_rate", "latency_p95", "error_rate"]


def load(name):
    return [json.loads(l) for l in open(LOGS / f"a4_{name}.jsonl", encoding="utf-8") if l.strip()]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    req, events, canaries, store = load("requests"), load("events"), load("canaries"), load("store_checks")
    expected = {q["id"]: q["correct_re"] for q in json.loads((ROOT / "data" / "attack" / "benign_heldout.json").read_text(encoding="utf-8"))}
    for r in req:
        if r["kind"] == "benign":
            r["truth_correct"] = re.search(expected[r["qid"]], r["answer"], re.I) is not None
    out, md = {"phases": {}}, ["# Assignment 4 - monitoring experiment", "",
        "| Phase | Requests | Correct | Answers with false value | Alert rate | Block rate | Unchecked | Latency p95, s | Errors | Canary | Store mismatches (last) |",
        "|---|---|---|---|---|---|---|---|---|---|---|"]
    for ph in PHASES:
        g = [r for r in req if r["phase"] == ph]
        if not g:
            continue
        lat = sorted(r["latency_s"] for r in g)
        can = [c for c in canaries if c["phase"] == ph]
        st = [s for s in store if s["phase"] == ph]
        s = {"requests": len(g), "first_step": g[0]["step"], "last_step": g[-1]["step"], "correct": sum(r["truth_correct"] for r in g) / len(g),
             "false_value": sum(r["truth_false_value"] for r in g), "alert_rate": sum(bool(r["suspects"]) for r in g) / len(g),
             "block_rate": sum(r["verdict"] == "blocked" for r in g) / len(g), "unchecked": sum(r["verdict"] == "no_claims" for r in g) / len(g),
             "p95": lat[min(len(lat) - 1, int(0.95 * len(lat)))], "errors": sum(r["guard"] == "error" for r in g) / len(g),
             "canary": sum(c["correct"] for c in can) / len(can) if can else None, "store": st[-1]["mismatches"] if st else 0, "simulated": ph in SIMULATED}
        out["phases"][ph] = s
        name = ph + (" (SIMULATED)" if ph in SIMULATED else "")
        md.append(f"| {name} | {s['requests']} | {s['correct']:.0%} | {s['false_value']} | {s['alert_rate']:.0%} | {s['block_rate']:.0%} | {s['unchecked']:.0%} | {s['p95']:.1f} | {s['errors']:.0%} | {s['canary']:.0%} | {s['store']} |")

    md += ["", "## Monitor events", "", "| Step | Phase | Event | Indicator | Value | Threshold | Requests since phase start | False-value answers shown in the phase before it |", "|---|---|---|---|---|---|---|---|"]
    out["events"] = []
    for e in events:
        ph = out["phases"][e["phase"]]
        since = e["step"] - ph["first_step"] + 1
        shown = sum(r["truth_false_value"] for r in req if r["phase"] == e["phase"] and r["step"] <= e["step"])
        out["events"].append({**e, "since_phase_start": since, "false_shown_before": shown})
        md.append(f"| {e['step']} | {e['phase']} | {e['event']} | {e['indicator']} | {e['value']} | {e['threshold']} | {since} | {shown} |")

    false_alarms = [e for e in events if e["event"] == "fire" and e["phase"] in ("normal", "recovery", "normal_end")]
    out["false_alarm_events"] = false_alarms
    md += ["", f"Fired during phases without an injected fault: {len(false_alarms)}"] + [f"- step {e['step']} {e['phase']}: {e['indicator']} = {e['value']}" for e in false_alarms]
    out["thresholds"] = {k: {"direction": v[0], "limit": v[1], "why": v[2], "response": v[3]} for k, v in THRESHOLDS.items()}
    (LOGS / "a4_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (LOGS / "a4_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
