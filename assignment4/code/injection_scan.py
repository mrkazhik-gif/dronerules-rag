# -*- coding: utf-8 -*-
"""
Instruction-override scanner for retrieved passages (new indicator of the AIGoat extension of Assignment 4).

The English patterns are taken from AIGoat, app/rag/injection_detector.py (AI Security Consortium, Apache License 2.0,
https://github.com/AISecurityConsortium/AIGoat). In AIGoat this check is the Level 2 control `retrieval.injection_scan`.
The Russian patterns are our translation of the same categories, because the knowledge base and the attacks are in Russian.

Here the scanner is used only as a monitoring signal: it does not filter passages, so the layered configuration is unchanged.
"""
import re

AIGOAT_PATTERNS = [
    (r"ignore\s+(?:all\s+)?(?:previous|prior|above|prior)\s+(?:instructions?|context|prompt)", "instruction override"),
    (r"disregard\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|context|documents?)", "context disregard"),
    (r"forget\s+(?:everything|all)\s+(?:you\s+)?(?:know|were\s+told)", "memory reset"),
    (r"you\s+are\s+now\s+(?:a\s+)?(?:different|new)\s+", "role confusion"),
    (r"system\s*:\s*", "system prompt injection"),
    (r"<\s*/\s*system\s*>", "delimiter injection"),
    (r"\[INST\]|\[\s*\/\s*INST\s*\]", "format injection"),
    (r"new\s+instructions?\s*:", "instruction override"),
    (r"override\s+(?:your|the)\s+", "override attempt"),
    (r"pretend\s+(?:you\s+are|to\s+be)\s+", "persona override"),
    (r"act\s+as\s+if\s+", "behavior override"),
    (r"from\s+now\s+on\s+", "behavior override"),
    (r"do\s+not\s+(?:follow|obey|use)\s+(?:your\s+)?(?:instructions?|rules?)", "rule bypass"),
]

RUSSIAN_PATTERNS = [
    (r"игнориру\w*\s+(?:вс[её]\s+|все\s+)?(?:предыдущ|прежн|вышеуказанн|предшествующ)\w*\s+(?:инструкц|указан|правил|контекст)", "instruction override"),
    (r"не\s+(?:учитывай|принимай\s+во\s+внимание)\s+(?:вс[её]\s+|все\s+)?(?:предыдущ|прежн|вышеуказанн)\w*", "context disregard"),
    (r"забудь\s+(?:вс[её]|все)", "memory reset"),
    (r"теперь\s+ты\s+", "role confusion"),
    (r"(?:системн\w+\s+(?:сообщение|инструкция)|система)\s*:", "system prompt injection"),
    (r"нов\w+\s+инструкц\w*\s*:", "instruction override"),
    (r"не\s+(?:следуй|соблюдай|выполняй|используй)\s+(?:свои\s+|своим\s+)?(?:инструкц|правил|указан)", "rule bypass"),
    (r"притворись|представь,?\s+что\s+ты", "persona override"),
    (r"веди\s+себя\s+как", "behavior override"),
    (r"с\s+этого\s+момента", "behavior override"),
    (r"(?:всегда|на\s+любой\s+вопрос\w*)\s+(?:\S+\s+){0,4}отвечай", "answer override"),
]

PATTERNS = [(re.compile(p, re.I | re.S), why) for p, why in AIGOAT_PATTERNS + RUSSIAN_PATTERNS]


def scan(text):
    """Return the categories of instruction-override phrasing found in one passage (empty list = clean)."""
    return sorted({why for rx, why in PATTERNS if rx.search(text or "")})


def scan_passages(passages):
    """Ids of passages that contain instruction-override phrasing."""
    return [p["id"] for p in passages if scan(p.get("text", ""))]


if __name__ == "__main__":       # check on the clean knowledge base: the threshold assumes 0 matches there
    import json, pathlib
    kb = pathlib.Path(__file__).resolve().parents[1] / "data" / "kb"
    docs = [json.loads(l) for f in ("official_chunks.jsonl", "community_faq.jsonl") for l in open(kb / f, encoding="utf-8") if l.strip()]
    hits = [(d["id"], scan(d["text"])) for d in docs if scan(d["text"])]
    print(len(docs), "passages,", len(hits), "with matches", hits[:10])
