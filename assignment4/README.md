# DroneRules RAG: Assignment 4 (AISRA1301)

Monitoring, oversight and deployment readiness of the Assignment 3 system. No new application: the `layered` configuration is unchanged.
All poisoned passages are synthetic test artefacts on a local testbed. Nothing was tested on external systems.

## What is new

| File | Purpose |
|---|---|
| `code/monitor.py` | Indicators, thresholds, alert events, store integrity check |
| `code/run_monitoring.py` | The controlled experiment: 10 phases of 44 requests each |
| `code/summarize_a4.py` | Tables from the logs |
| `code/log_mlflow.py` | Loads the logs into MLflow (metric series, child runs, traces, artifacts) |
| `code/make_figures_a4.py` | Figures of the report |
| `code/aigoat_attacks.py` | AIGoat extension: four RAG attacks adapted from AIGoat labs LLM01-4, LLM09-2, LLM09-3, LLM09-4 |
| `code/injection_scan.py` | AIGoat extension: instruction-override scan (English patterns from AIGoat, Apache 2.0, plus a Russian translation) |
| `code/run_aigoat.py` | AIGoat extension: 6 phases of 44 requests, adds the `injection_rate` indicator |
| `code/summarize_aigoat.py`, `code/make_figure_aigoat.py` | AIGoat extension: tables and figure |

Reused code: the English patterns in `injection_scan.py` come from AIGoat, `app/rag/injection_detector.py` (AI Security Consortium, https://github.com/AISecurityConsortium/AIGoat, Apache License 2.0). The attack techniques follow AIGoat's RAG labs (lab content CC BY-NC-SA 4.0); the passages themselves are our own Russian text for the UAS rules. We did not run or test the AIGoat application.

## Reproduce

Windows 11, Python 3.11.9, NVIDIA GPU with 8 GB. Two environments are used, so MLflow cannot break the model environment.

1. The system and monitor, in the Midterm's `garak-env` (`requirements.txt`):

```bash
cd code
python run_monitoring.py
python summarize_a4.py
```

2. MLflow, in a separate environment:

```bash
python -m venv D:\Work\mlflow-env
D:\Work\mlflow-env\Scripts\python.exe -m pip install mlflow
D:\Work\mlflow-env\Scripts\python.exe log_mlflow.py
```

On our laptop Windows Smart App Control blocked the compiled SQLAlchemy modules, so SQLAlchemy was installed as pure Python (`set DISABLE_SQLALCHEMY_CEXT=1` and `pip install --force-reinstall --no-deps --no-binary sqlalchemy sqlalchemy`). This may not be needed elsewhere. `log_mlflow.py` loads both the main experiment and the AIGoat run (two parent runs in one experiment).

3. The dashboard, then http://127.0.0.1:5000 (experiment `dronerules-monitoring-a4`):

```bash
D:\Work\mlflow-env\Scripts\python.exe -m mlflow server --backend-store-uri sqlite:///../logs/mlflow.db --port 5000 --workers 1
```

On our laptop Smart App Control also blocks the `mlflow.exe` launcher, so the server is started as a Python module.

4. Figures, in a Python with matplotlib: `make_figures_a4.py`, `make_figure_aigoat.py`.

5. The AIGoat extension was run in Google Colab (Tesla T4, torch 2.14.1, transformers 5.22.1), with `code/` and `data/` unpacked to `/content/a4`:

```bash
cd code
python injection_scan.py        # check: 0 of 786 clean passages match
python run_aigoat.py            # --quick: 3 requests per phase, a smoke test only
python summarize_aigoat.py
```

The run reported in the report is the one of 12 November 2026 (`logs/aigoat_*`). We repeated it in Colab (T4) on 21 November 2026 with the same code and data; its logs are in `logs/_aigoat_rerun_2026-11-21/`. All 264 answers, the alert events, the canary answers and the store checks are identical to the first run. Only the latencies differ (p95 per phase 4.8-5.9 s instead of 4.6-6.4 s), so the report was not changed.

The executed notebook of the repeated run, with all outputs, is `evidence/aigoat_colab_run_2026-11-21.ipynb` (Tesla T4, Python 3.13.16, torch 2.14.1, transformers 5.22.1). It uploads a ZIP of `code/` and `data/`, unpacks it to `/content/a4` and runs the three commands above. The notebook of the first run was not kept.

## Phases

`normal`, `naive` (3 poisoned passages per target question), `recovery`, `stealth` (real value from another item, or Latin units), `compromise` (poison added to the manifest), `compromise_avoid_canary`, `kb_loss` (30% of official chunks removed), `latency_sim`, `errors_sim`, `normal_end`.

**`latency_sim` and `errors_sim` are simulated:** the script adds 3 s to each model call or makes every 4th call fail. They are not real incidents. The other phases use real model answers.

AIGoat extension (`run_aigoat.py`, all real model answers): `normal`, `aigoat_injection` (LLM01-4, override instruction in unverified web passages), `aigoat_stuffing` (LLM09-2, keyword stuffing), `aigoat_trust_spoof` (LLM09-3, passages labelled "official" but not in the manifest), `aigoat_flooding` (LLM09-4, naive poison plus large flood passages), `aigoat_injection_insider` (the injection passages added to the manifest).

The monitor never reads the test labels (`truth_*`); they are used only by `summarize_a4.py` and `summarize_aigoat.py`.

## Evidence

| Path | Content |
|---|---|
| `logs/a4_requests.jsonl` | Every request: answer, verdict, suspects, latency, indicators |
| `logs/a4_events.jsonl`, `a4_canaries.jsonl`, `a4_store_checks.jsonl` | Alerts, canary answers, store checks |
| `logs/a4_summary.md`, `a4_summary.json`, `a4_thresholds.json` | Tables and thresholds |
| `logs/mlflow.db`, `code/mlruns/` | MLflow store and run artifacts |
| `evidence/mlflow_metrics.jpg`, `evidence/mlflow_traces.jpg` | Dashboard screenshots, main experiment |
| `evidence/mlflow_aigoat_metrics.jpg`, `evidence/mlflow_aigoat_traces.jpg` | Dashboard screenshots, AIGoat extension (taken on 21 November 2026) |
| `logs/aigoat_*.jsonl`, `aigoat_summary.md`, `aigoat_summary.json`, `aigoat_thresholds.json`, `aigoat_run.out` | AIGoat extension: the same logs for the Colab run of 12 November 2026 |
| `logs/_aigoat_rerun_2026-11-21/` | AIGoat extension: logs of the repeated Colab run |
| `evidence/aigoat_colab_run_2026-11-21.ipynb` | AIGoat extension: executed Colab notebook of the repeated run |
| `figures/fig_a4_aigoat.png` | AIGoat extension: indicator series |
| `logs/_a3_results/` | Assignment 3 results used for the thresholds |

In `logs/mlflow.db` the operating-system account name that MLflow stores as the run user was replaced by `student`. Metrics, parameters and traces were not changed. The artifact paths in the store are local paths of our laptop.

## Known limits

MLflow loaded the logs after the run, so this is an offline evaluation. Safe mode, operators and alert delivery are a design, not implemented. The reference snapshot is on the same machine. The request log has no timestamps. See Section 9 of the report.
