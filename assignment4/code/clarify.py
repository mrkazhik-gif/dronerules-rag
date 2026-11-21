# -*- coding: utf-8 -*-
"""
Clarification layer of the DroneRules assistant (rule-based, no LLM).

The UAS rules often give different values under different conditions (controlled vs uncontrolled airspace, with or
without an operator certificate, day vs night, VLOS vs BVLOS, flat vs mountain terrain). If the OFFICIAL passages that
the retriever found mention such a condition, but the user's question does not say which case applies, the assistant
adds one short clarifying question after its answer.

The clarifying questions contain no numbers, so they never change how an answer is scored in the experiment.
"""
import re

# A rule fires only if (1) the question is about the topic where the condition changes the value, (2) every variant of
# the condition appears in the retrieved OFFICIAL passages, and (3) the question does not already say which case applies.
# (topic of the question, variants that must all be in the passages, words that mean "already specified", question)
RULES = [
    (r"высот", [r"контролируем"], r"контролируем|диспетчерск",
     "В каком воздушном пространстве вы планируете полет — контролируемом или неконтролируемом?"),
    (r"масс|вес|кг", [r"сертификат\w* оператора", r"кг"], r"сертификат",
     "Есть ли у вас сертификат оператора БАС, и какой категории?"),
    (r"(?<!прямой )видимост|облак|погод|метео", [r"Горная", r"Равнинная"], r"горн|равнин|холмист|водн",
     "Над какой местностью будет полет — равнинной, холмистой или горной?"),
    (r"(?<!прямой )видимост|облак|погод|метео", [r"BVLOS", r"VLOS"], r"VLOS|прямой видимост",
     "Полет в пределах прямой видимости (VLOS) или за ее пределами (BVLOS)?"),
    (r"можно ли|разрешен|когда", [r"ночью|сумерк"], r"ноч|сумерк|дн[её]м|дневн|светл",
     "Полет будет выполняться днем или ночью?"),
]
MAX_QUESTIONS = 1


def clarifying_questions(question, passages):
    """Return up to MAX_QUESTIONS clarifying questions for this question and its retrieved passages."""
    official = " ".join(p["text"] for p in passages if p.get("origin") == "official")
    out = []
    for topic, variants, specified, ask in RULES:
        if (re.search(topic, question, re.I) and all(re.search(v, official, re.I) for v in variants)
                and not re.search(specified, question, re.I)):
            out.append(ask)
        if len(out) == MAX_QUESTIONS:
            break
    return out
