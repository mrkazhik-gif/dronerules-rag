# -*- coding: utf-8 -*-
"""
Tables of Assignment 3 from logs/a3_*.jsonl (the model is not re-run). Manual corrections after human review are in
logs/a3_manual_overrides.json. ASR = shown answers that contain the attacker's value (attack + mixed).

Run:  python summarize_a3.py      -> logs/a3_summary.md, logs/a3_summary.json
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
CONFIGS = ["baseline", "provenance", "verify_abstain", "verify_fallback", "layered"]
N_LEVELS = [0, 1, 3, 5]
ATTACKS = ["word_numbers", "latin_units", "value_collision", "store_compromise"]


def load(stage):
    path = LOGS / f"a3_{stage}.jsonl"
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()] if path.exists() else []


def apply_overrides(rows):
    path = LOGS / "a3_manual_overrides.json"
    overrides = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    for o in overrides:
        hit = [r for r in rows if all(r.get(k) == o[k] for k in ("stage", "qid", "config", "n_poison")) and r.get("attack", "") == o.get("attack", "")]
        assert len(hit) == 1 and hit[0]["outcome"] == o["regex_outcome"], o
        hit[0]["outcome"] = o["outcome"]
    return overrides


def rates(g):
    n = len(g)
    c = {o: sum(r["outcome"] == o for r in g) for o in ("correct", "attack", "mixed", "other", "abstain")}
    return {"n": n, **c, "accuracy": c["correct"] / n, "asr": (c["attack"] + c["mixed"]) / n, "abstain_rate": c["abstain"] / n,
            "latency": sum(r["latency_s"] for r in g) / n}


def detection(rows):
    """Positive = the draft contains the attacker's value. Detected = the verifier blocked the draft."""
    tp = sum(r["draft_outcome"] in ("attack", "mixed") and r["verdict"] == "blocked" for r in rows)
    fn = sum(r["draft_outcome"] in ("attack", "mixed") and r["verdict"] != "blocked" for r in rows)
    fp = sum(r["draft_outcome"] not in ("attack", "mixed") and r["verdict"] == "blocked" for r in rows)
    tn = sum(r["draft_outcome"] not in ("attack", "mixed") and r["verdict"] != "blocked" for r in rows)
    p = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "precision": p, "recall": rec, "f1": 2 * p * rec / (p + rec) if p + rec else 0.0,
            "fpr": fp / (fp + tn) if fp + tn else 0.0}


def replay(rows):
    """Replay the verdict for other evidence sizes m from the logged evidence. No model calls."""
    out = []
    for m in (1, 3, 5, 10, 20):
        pos = blocked_pos = neg = blocked_neg = 0
        for r in rows:
            allowed = {tuple(c) for e in r["evidence_ranked"][:m] for c in e["claims"]}
            blocked = bool({tuple(c) for c in r["claims"]} - allowed)
            if r["draft_outcome"] in ("attack", "mixed"):
                pos += 1; blocked_pos += blocked
            else:
                neg += 1; blocked_neg += blocked
        out.append({"m": m, "recall": blocked_pos / pos if pos else 0.0, "fpr": blocked_neg / neg if neg else 0.0, "pos": pos, "neg": neg})
    return out


def pct(x):
    return f"{x:.0%}"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    main_rows, held, adaptive, robust = load("main"), load("heldout"), load("adaptive"), load("robust")
    # held-out answers are rescored from the log with the current expected thesis (no model call)
    expected = {q["id"]: q["correct_re"] for q in json.loads((ROOT / "data" / "attack" / "benign_heldout.json").read_text(encoding="utf-8"))}
    for r in held:
        if r["action"] != "abstain":
            r["outcome"] = "correct" if re.search(expected[r["qid"]], r["answer"], re.I) else "other"
    # q05 is not a real collision: the value "50 м" became "50 км" in the claim, so it was not in the evidence (fixed in attacks_a3.py)
    adaptive = [r for r in adaptive if not (r["attack"] == "value_collision" and r["qid"] == "q05")]
    overrides = apply_overrides(main_rows + held + adaptive)
    md, js = ["# Assignment 3 - results", ""], {}

    md += ["## Main experiment (20 Midterm questions)", "", "| Config | N | Correct | ASR | Abstain | Other | Mean latency, s |", "|---|---|---|---|---|---|---|"]
    js["main"] = {}
    for cfg in CONFIGS:
        for n in N_LEVELS:
            g = [r for r in main_rows if r["config"] == cfg and r["n_poison"] == n]
            if not g:
                continue
            s = rates(g); js["main"][f"{cfg}|{n}"] = s
            md.append(f"| {cfg} | {n} | {pct(s['accuracy'])} | {pct(s['asr'])} | {pct(s['abstain_rate'])} | {s['other']} | {s['latency']:.2f} |")

    verify_rows = [r for r in main_rows if r["config"] == "verify_abstain"]
    if verify_rows:
        d = detection(verify_rows); js["detection_main"] = d
        md += ["", "## Verifier as a detector (main, all N, verify_abstain)", "", json.dumps(d), "", "### Evidence size replay", "",
               "| m | Recall | FPR |", "|---|---|---|"]
        js["replay_main"] = replay(verify_rows)
        md += [f"| {x['m']} | {pct(x['recall'])} | {pct(x['fpr'])} |" for x in js["replay_main"]]

    alert = [r for r in main_rows if r["config"] == "layered"]
    if alert:
        md += ["", "## Operator alert (layered: unverified passage with a value missing from the official evidence)", "", "| N | Questions with alert |", "|---|---|"]
        js["alert"] = {}
        for n in N_LEVELS:
            g = [r for r in alert if r["n_poison"] == n]
            js["alert"][n] = sum(bool(r["suspects"]) for r in g) / len(g)
            md.append(f"| {n} | {pct(js['alert'][n])} |")

    md += ["", "## Held-out benign questions (24, clean KB)", "", "| Config | Kind | Correct | Abstain | Mean latency, s |", "|---|---|---|---|---|"]
    js["heldout"] = {}
    for cfg in CONFIGS:
        for kind in ("numeric", "text", "all"):
            g = [r for r in held if r["config"] == cfg and (kind == "all" or r["kind"] == kind)]
            if not g:
                continue
            s = rates(g); js["heldout"][f"{cfg}|{kind}"] = s
            md.append(f"| {cfg} | {kind} ({s['n']}) | {pct(s['accuracy'])} | {pct(s['abstain_rate'])} | {s['latency']:.2f} |")

    md += ["", "## Adaptive attacks (N = 5)", "", "| Attack | Config | Questions | Draft has false value | Shown ASR | Correct | Abstain |", "|---|---|---|---|---|---|---|"]
    js["adaptive"] = {}
    for attack in ATTACKS:
        for cfg in CONFIGS:
            g = [r for r in adaptive if r["attack"] == attack and r["config"] == cfg]
            if not g:
                continue
            s = rates(g); s["draft_attack"] = sum(r["draft_outcome"] in ("attack", "mixed") for r in g) / len(g)
            js["adaptive"][f"{attack}|{cfg}"] = s
            md.append(f"| {attack} | {cfg} | {s['n']} | {pct(s['draft_attack'])} | {pct(s['asr'])} | {pct(s['accuracy'])} | {pct(s['abstain_rate'])} |")

    md += ["", "## Unexpected inputs (verify_fallback)", "", "| Case | Guard | Action | Error | Latency, s | Answer |", "|---|---|---|---|---|---|"]
    for r in robust:
        md.append(f"| {r['case']} | {r['guard']} | {r['action']} | {r['error']} | {r['latency_s']} | {r['answer'][:90]} |")
    js["robust"] = {"cases": len(robust), "errors": sum(bool(r["error"]) for r in robust), "max_latency": max((r["latency_s"] for r in robust), default=0)}
    for o in overrides:
        md.append(f"\nManual correction: {o['stage']} / {o['qid']} / {o['config']} / N = {o['n_poison']} {o.get('attack', '')}: {o['regex_outcome']} -> {o['outcome']}. {o['note']}")
    (LOGS / "a3_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (LOGS / "a3_summary.json").write_text(json.dumps(js, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
