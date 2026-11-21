# DroneRules RAG

Code, data and logs for the article **“One Poisoned Passage Is Enough: Attacking, Defending and Monitoring a RAG Assistant for Kazakhstan's Drone Rules”** by Daulet Kazhigul and Aslan Zhunzhumenov (2026).

Article: *the link will be added after publication.*

> **Warning.** The files in `*/data/attack/` and many answers in `*/logs/` contain **deliberately false statements about flight rules**. They are synthetic test material for a security experiment. Do not use anything in this repository as guidance for flying. The only valid source is the official text of the rules on [adilet.zan.kz](https://adilet.zan.kz).

## What this is

A small local question-answering assistant (RAG) for the *Rules for the Use of Unmanned Aircraft Systems in the Airspace of the Republic of Kazakhstan* (Order No. 706, current edition), with questions and answers in Russian:

- knowledge base: 778 chunks of the official text and 8 community notes;
- retriever: `intfloat/multilingual-e5-small`, top-5;
- generator: `Qwen/Qwen2.5-3B-Instruct`, greedy decoding;
- hardware: one laptop with an 8 GB GPU.

We attacked the knowledge base of this assistant (the PoisonedRAG method of Zou et al., USENIX Security 2025), added defences, and then tested what simple monitoring can and cannot detect.

## Repository layout

The project was done in three stages. Each folder is a self-contained snapshot of one stage with its own `code/`, `data/`, `logs/` and `README.md`.

| Folder | Stage | Content |
|---|---|---|
| `midterm/` | 1. Attack and first defences | The prototype, the poisoning attack, top-10 retrieval, source-aware prompt (M1), provenance filter (M2), garak probes, Ragas metrics |
| `assignment3/` | 2. Output verification | Numeric verifier with abstention (M3), layered configuration (M2 + M3), four adaptive attacks, 24 held-out questions |
| `assignment4/` | 3. Monitoring and oversight | Eight indicators with thresholds, 440 monitored requests, MLflow store, four attack techniques adapted from the AIGoat labs (264 requests) |

The same knowledge base (`data/kb`, `data/source`) and the same 20 target questions (`data/attack/targets.json`) are repeated in every stage, so that each stage can be run on its own.

## Main results

Stage 1, 20 questions, share of answers with the attacker's value (ASR). Source: `midterm/logs/summary.md`.

| Configuration | Correct, clean base | ASR, 1 poisoned passage | ASR, 3 | ASR, 5 |
|---|---|---|---|---|
| Baseline (top-5) | 95% | 80% | 95% | 100% |
| Top-10 retrieval | 90% | 65% | 100% | 100% |
| M1 source-aware prompt | 90% | 20% | 65% | 100% |
| M2 provenance filter | 90% | 0% | 0% | 0% |

Stage 2. Source: `assignment3/logs/a3_summary.md`.

- The verifier blocked every answer with a false value in the main experiment (55 of 55, one false alarm in 25 clean cases).
- A real value taken from another item of the rules passed the verifier in 100% of cases (16 questions).
- When the attacker can write to the verified store, every configuration gives the false value in 100% of cases.
- On 24 held-out questions without any attack the assistant was correct in 67–71% of cases.

Stage 3. Sources: `assignment4/logs/a4_summary.md`, `assignment4/logs/aigoat_summary.md`.

- The store integrity check detected a compromised store at request 4 of the phase; the canary questions detected it only at the end of the phase, after 14 answers with a false value.
- A simulated slowdown of 3 s per request was not detected, and about 20% of wrong answers without any attack were invisible to every indicator.
- Passages that only claim to be official (trust-tier spoofing) raised no alert, although the provenance filter kept them out of the model context.
- Decision: **no-go** for use by pilots; the assistant is not safe as the only source of a flight limit.

## How to reproduce

Each stage has its own `README.md` with the commands. In short: Python 3.11, an NVIDIA GPU with 8 GB, the packages from `requirements.txt`; the models are downloaded from Hugging Face on first use. The AIGoat extension of stage 3 was run in Google Colab (T4); the executed notebook is in `assignment4/evidence/`.

Notes:

- The commands in the stage READMEs and the `report_dir` in `*/configs/run_*.yaml` use paths of our laptop (`D:\Work\...`). Change them to your own.
- Decoding is greedy, so answers repeat on the same hardware and library versions. Latency varies.

## What was changed for publication

The folders are the materials submitted for the course, with these changes:

- the scripts that built the course reports and slides were left out;
- the HTML renderings of the garak reports were left out (the `.report.jsonl` and `.hitlog.jsonl` files are kept);
- the operating-system account name was replaced by `student` in five garak console logs and in `assignment4/logs/mlflow.db`;
- one demo screenshot (`assignment3/evidence/student_demo_2026-10-31/poisoned_baseline_120m.png`) was cropped to remove a desktop notification.

No answer, metric or log record was changed.

## Data and third-party material

- The text of the rules is a public legal act of the Republic of Kazakhstan, taken from the public API of adilet.zan.kz on 22 October 2026 (`*/data/source/`).
- All poisoned passages are our own synthetic text. They were used only in our local system and were never published as real guidance.
- The English patterns in `assignment4/code/injection_scan.py` come from [AIGoat](https://github.com/AISecurityConsortium/AIGoat) (AI Security Consortium, Apache License 2.0). The attack techniques of the AIGoat extension follow the AIGoat RAG labs; the passages are our own.
- No personal or company data is used.

## AI use

An AI coding assistant (Claude, Anthropic, used through Claude Code) generated most of the source code, ran the scripted experiments on the first author's computer, proposed the mitigations and indicators, and drafted this README. The authors set the task and the domain, provided the legal source and found that its first version was outdated, ran the demonstrations and the Colab run, reviewed the results and the manual corrections, made the deployment decision, and are responsible for the content.

## Context

The project was made for the course “AI Security and Risk Analysis” (AISRA1301), Master's programme AI+X, 2026.
