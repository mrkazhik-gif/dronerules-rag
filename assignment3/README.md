# DroneRules RAG: Assignment 3 (AISRA1301)

Continuation of the Midterm prototype: a local RAG assistant for the UAS rules of Kazakhstan, tested against knowledge corruption
(PoisonedRAG). Assignment 3 adds **output verification with abstention (M3)** and tests it, including against attackers who know how it works.

All poisoned passages are synthetic test artefacts on a local testbed. Nothing was tested on external systems.

## What changed since the Midterm

| File | Change |
|---|---|
| `code/verifier.py` | New. Extracts numbers with units (digits and Russian words) and checks them against official evidence |
| `code/rag_core.py` | New configurations `verify_abstain`, `verify_fallback`, `layered`; `safe_ask` for empty input and runtime errors |
| `code/attacks_a3.py` | New. Adaptive attacks: value in words, Latin units, real value from another item, compromised store |
| `code/run_a3.py`, `code/summarize_a3.py` | New. Experiment stages and tables |
| `data/attack/benign_heldout.json` | New. 24 held-out benign questions (16 numeric, 8 without numbers) |
| `code/rag_server.py`, `web/index.html` | Warning, check result and official passages on the page; server uses `safe_ask` |
| `configs/*layered*`, `code/run_garak.cmd`, `code/summarize_garak.py` | garak probes of the Midterm on `layered` |

Kept unchanged from the Midterm: `build_kb.py` output in `data/kb`, `poison.py`, `clarify.py`, `guard.py`, the 20 target questions.

## Configurations

| Name | Retrieval | After generation |
|---|---|---|
| `baseline` | top-5, whole knowledge base | nothing |
| `provenance` (M2) | top-5, verified store only | nothing |
| `verify_abstain` (M3a) | as baseline | blocked draft: abstain |
| `verify_fallback` (M3b) | as baseline | blocked draft: rewrite from official passages, check again, otherwise abstain |
| `layered` (M2 + M3) | verified store only | check the draft; alert if an unverified passage states a value missing from the evidence |

## Reproduce

Windows 11, Python 3.11.9, NVIDIA GPU with 8 GB (CUDA 13.0). Dependencies: `requirements.txt` (the Midterm's `garak-env`).
Models from Hugging Face: `Qwen/Qwen2.5-3B-Instruct`, `intfloat/multilingual-e5-small`.

```bash
cd code
python run_a3.py main robust heldout adaptive
python summarize_a3.py
python rag_server.py
```

With the server running, in a second window:

```bash
run_garak.cmd
python summarize_garak.py
```

Then the figure (a Python with matplotlib):

```bash
python make_figures_a3.py
```

Decoding is greedy, so answers repeat on the same hardware and library versions; latency varies. The demo page is at http://127.0.0.1:8095.

## Evidence

| Path | Content |
|---|---|
| `logs/a3_main.jsonl`, `a3_heldout.jsonl`, `a3_adaptive.jsonl`, `a3_robust.jsonl` | Every answer with draft, verdict, claims, evidence and latency |
| `logs/a3_summary.md`, `a3_summary.json` | Tables used in the report |
| `logs/a3_manual_overrides.json` | 5 scoring corrections with reasons (b12); the rule for b23 was narrowed in `benign_heldout.json` |
| `logs/_v1_digits_only/` | First run: digits-only verifier, which the value in words bypassed, and two faults of the test itself |
| `logs/_midterm_baseline/` | Midterm results used for comparison |
| `logs/garak_layered/`, `garak_layered_summary.json` | garak reports |

`value_collision` on q05 is excluded from the tables: the value "50 м" became "50 км" in the claim, so it was not a real collision. The code now skips such a case, so a fresh run has 16 questions for this attack.

## Known limits

The verifier cannot tell which official value answers the question, recognises Russian units only and does not check answers without numbers. A compromised verified store defeats every configuration. English and Kazakh questions are refused as out of scope. See Sections 6 and 9 of the report.
