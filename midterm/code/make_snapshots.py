# -*- coding: utf-8 -*-
"""
Screenshots of the web demo for the report and slides. Needs the running rag_server.py (port 8095) and Google Chrome.
Asks the server the same question in several settings, embeds each real response into a copy of web/index.html
and renders it with headless Chrome:  figures/demo_<name>.png (+ figures/demo_answers.json for the slides)
"""
import json, pathlib, subprocess, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEMO_QID = "q03"                                     # also the default question of the web page
QUESTION = next(t for t in json.loads((ROOT / "data" / "attack" / "targets.json").read_text(encoding="utf-8")) if t["id"] == DEMO_QID)["question"]
SHOTS = [("clean_baseline", "clean", "baseline"), ("poisoned_baseline", "poisoned", "baseline"),
         ("poisoned_source_aware", "poisoned", "source_aware"), ("poisoned_provenance", "poisoned", "provenance")]


def ask(kb, config):
    body = json.dumps({"question": QUESTION, "kb": kb, "config": config}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:8095/api/ask", body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=600).read().decode("utf-8"))


def main():
    FIG.mkdir(exist_ok=True)
    page = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    answers = {"qid": DEMO_QID}
    for name, kb, config in SHOTS:
        d = ask(kb, config)
        answers[name] = d["answer"]
        d["question"] = QUESTION
        snap = page.replace("<script>\nconst $", "<script>window.SNAPSHOT = " + json.dumps(d, ensure_ascii=False) + ";</script>\n<script>\nconst $", 1)
        html = FIG / f"demo_{name}.html"
        html.write_text(snap, encoding="utf-8")
        png = FIG / f"demo_{name}.png"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1000,1250",
                        f"--screenshot={png}", html.as_uri()], check=True, capture_output=True, timeout=120)
        html.unlink()
        print(name, "->", d["answer"][:90])
    (FIG / "demo_answers.json").write_text(json.dumps(answers, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
