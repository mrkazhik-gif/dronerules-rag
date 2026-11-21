# -*- coding: utf-8 -*-
"""
Local web server for the DroneRules RAG assistant (prototype + garak target). One model is loaded once.

  GET  /                          web page (web/index.html): ask a question, pick a configuration and a knowledge base
  GET  /api/questions             the 20 test questions (for the example buttons on the page)
  POST /api/ask                   {"question", "config", "kb": "clean" | "poisoned"} -> answer + retrieved passages
  POST /generate/<config>         {"prompt"} -> {"response"}   plain chat endpoint for NVIDIA garak (no retrieval)

"poisoned" knowledge base = clean base + 3 poisoned passages for each of the 20 test questions (60 passages).
Every request is appended to logs/server_requests.jsonl.

Run:  python rag_server.py            then open http://127.0.0.1:8095
"""
import argparse, json, pathlib, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from rag_core import RAGAssistant, CONFIGS
from poison import TARGETS, poisoned_passages

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "web" / "index.html"
LOG = ROOT / "logs" / "server_requests.jsonl"
DEMO_POISON_N = 3


class Handler(BaseHTTPRequestHandler):
    rag = None
    lock = threading.Lock()      # one GPU model -> answer one request at a time
    kb_state = "clean"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _log(self, rec):
        LOG.parent.mkdir(exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), **rec}, ensure_ascii=False) + "\n")

    def _set_kb(self, state):
        if state != Handler.kb_state:
            extra = [p for t in TARGETS for p in poisoned_passages(t, DEMO_POISON_N)] if state == "poisoned" else []
            self.rag.kb.set_extra(extra)
            Handler.kb_state = state

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/questions":
            return self._json(200, [{"id": t["id"], "question": t["question"], "correct": t["correct"],
                                     "section": t["section"]} for t in TARGETS])
        self._json(404, {"error": "not found"})

    def do_POST(self):
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
        except Exception as e:
            return self._json(400, {"error": str(e)})
        if self.path == "/api/ask":
            question, config, kb = str(req.get("question", "")).strip(), req.get("config", "baseline"), req.get("kb", "clean")
            if config not in CONFIGS or kb not in ("clean", "poisoned"):
                return self._json(400, {"error": "need config in %s, kb clean|poisoned" % CONFIGS})
            with self.lock:
                self._set_kb(kb)
                r = self.rag.safe_ask(question, config)
            self._log({"endpoint": "ask", "kb": kb, "config": config, "question": question, "answer": r["answer"], "clarification": r["clarification"], "note": r["note"], "guard": r["guard"],
                       "retrieved": [p["id"] for p in r["passages"]], "latency_s": r["latency_s"]})
            return self._json(200, {**r, "kb": kb})
        if self.path.startswith("/generate/"):
            config = self.path.rsplit("/", 1)[-1]
            if config not in CONFIGS:
                return self._json(404, {"error": f"unknown config {config}"})
            prompt = str(req.get("prompt", ""))
            t0 = time.time()
            with self.lock:
                reply = self.rag.generate(prompt, config)
            self._log({"endpoint": "generate", "config": config, "prompt": prompt, "reply": reply,
                       "latency_s": round(time.time() - t0, 2)})
            return self._json(200, {"response": reply})
        self._json(404, {"error": "not found"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8095)
    a = ap.parse_args()
    Handler.rag = RAGAssistant()
    print(f"[server] DroneRules RAG ready: http://127.0.0.1:{a.port}  (garak: /generate/<config>)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
