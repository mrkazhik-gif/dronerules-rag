# -*- coding: utf-8 -*-
"""
Loads the monitoring experiment into MLflow (local SQLite store, no cloud) after the run, so it is an offline evaluation,
not live monitoring: the system answered first (garak-env), MLflow reads the logs afterwards (mlflow-env).

  one parent run: indicators per request as metric series (step = request number), thresholds as parameters, events and tables as artifacts
  one child run per phase: its metrics and tags
  one trace per monitor event: the indicator, its value and the response

Run:  D:\\Work\\mlflow-env\\Scripts\\python.exe log_mlflow.py
View: D:\\Work\\mlflow-env\\Scripts\\mlflow.exe server --backend-store-uri sqlite:///../logs/mlflow.db --port 5000
"""
import json, os, pathlib

os.environ["MLFLOW_ENABLE_ASYNC_TRACE_LOGGING"] = "false"
import mlflow

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
DB = (LOGS / "mlflow.db").resolve()
if DB.exists():
    DB.unlink()
mlflow.set_tracking_uri("sqlite:///" + DB.as_posix())
mlflow.set_experiment("dronerules-monitoring-a4")
S = json.loads((LOGS / "a4_summary.json").read_text(encoding="utf-8"))
req = [json.loads(l) for l in open(LOGS / "a4_requests.jsonl", encoding="utf-8") if l.strip()]

with mlflow.start_run(run_name="monitoring_experiment") as parent:
    mlflow.set_tags({"config": "layered", "mode": "offline evaluation of logged run", "model": "Qwen2.5-3B-Instruct"})
    for name, t in S["thresholds"].items():
        mlflow.log_param(f"threshold.{name}", f"{t['direction']} {t['limit']}")
    for r in req:
        for k, v in r["indicators"].items():
            mlflow.log_metric(k, v, step=r["step"])
        mlflow.log_metric("latency_s", r["latency_s"], step=r["step"])
        if "store_mismatches" in r:
            mlflow.log_metric("store_mismatches", r["store_mismatches"], step=r["step"])
    for name in ("a4_summary.md", "a4_events.jsonl", "a4_thresholds.json", "a4_canaries.jsonl"):
        mlflow.log_artifact(str(LOGS / name))
    for ph, s in S["phases"].items():
        with mlflow.start_run(run_name=ph, nested=True):
            mlflow.set_tags({"phase": ph, "simulated": str(s["simulated"]).lower()})
            mlflow.log_metrics({k: float(s[k]) for k in ("correct", "false_value", "alert_rate", "block_rate", "unchecked", "p95", "errors", "store") if s[k] is not None})
            if s["canary"] is not None:
                mlflow.log_metric("canary", s["canary"])
    for e in S["events"]:
        with mlflow.start_span(name=f"{e['event']}:{e['indicator']}") as span:
            span.set_inputs({"phase": e["phase"], "step": e["step"], "indicator": e["indicator"]})
            span.set_outputs({"value": e["value"], "threshold": e["threshold"], "response": e["response"]})

# AIGoat extension (run on Colab T4, logs/aigoat_*): a second parent run in the same experiment
A = json.loads((LOGS / "aigoat_summary.json").read_text(encoding="utf-8"))
areq = [json.loads(l) for l in open(LOGS / "aigoat_requests.jsonl", encoding="utf-8") if l.strip()]
with mlflow.start_run(run_name="aigoat_extension"):
    mlflow.set_tags({"config": "layered", "mode": "offline evaluation of logged run", "model": "Qwen2.5-3B-Instruct", "hardware": "Colab Tesla T4",
                     "attacks": "adapted from AIGoat RAG labs LLM01-4, LLM09-2, LLM09-3, LLM09-4"})
    for name, t in A["thresholds"].items():
        mlflow.log_param(f"threshold.{name}", f"{t['direction']} {t['limit']}")
    for r in areq:
        for k, v in r["indicators"].items():
            mlflow.log_metric(k, v, step=r["step"])
        mlflow.log_metric("latency_s", r["latency_s"], step=r["step"])
        if "store_mismatches" in r:
            mlflow.log_metric("store_mismatches", r["store_mismatches"], step=r["step"])
    for name in ("aigoat_summary.md", "aigoat_events.jsonl", "aigoat_thresholds.json", "aigoat_canaries.jsonl"):
        mlflow.log_artifact(str(LOGS / name))
    for ph, s in A["phases"].items():
        with mlflow.start_run(run_name=ph, nested=True):
            mlflow.set_tags({"phase": ph, "simulated": "false"})
            mlflow.log_metrics({k: float(s[k]) for k in ("correct", "false_value", "injection_followed", "attack_in_top5", "attack_in_context",
                                                          "suspect", "injection_scan", "blocked", "p95", "errors", "canary", "store")})
    for e in A["events"]:
        with mlflow.start_span(name=f"aigoat {e['event']}:{e['indicator']}") as span:
            span.set_inputs({"phase": e["phase"], "step": e["step"], "indicator": e["indicator"]})
            span.set_outputs({"value": e["value"], "threshold": e["threshold"], "response": e["response"]})

client = mlflow.tracking.MlflowClient()
print("experiment", parent.info.experiment_id, "run", parent.info.run_id)
print("runs in experiment", len(client.search_runs([parent.info.experiment_id])))
print("metric points alert_rate", len(client.get_metric_history(parent.info.run_id, "alert_rate")))
print("traces", len(mlflow.search_traces(locations=[parent.info.experiment_id])))
