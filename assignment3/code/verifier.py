# -*- coding: utf-8 -*-
"""
M3, the additional safety mechanism of Assignment 3: output verification with abstention (rule-based, runs after the LLM).

Every numeric claim (number + unit) of a draft answer must also appear in the official passages that are retrieved for
the same question from the verified store (the SHA-256 manifest of the Midterm). A claim that is not found there blocks
the draft. The evidence set is retrieved independently of the draft's context, so poisoned passages cannot enter it
unless the verified store itself is compromised.

v2: numbers written in Russian words are also read, because the adaptive test showed that v1 (digits only) let a value
written in words through (logs/_v1_digits_only).

Limits (measured in the experiment, see README): only Russian units are recognised, the check cannot tell WHICH official
value answers the question, and it says nothing about claims without numbers.
"""
import re

UNIT_RE = (r"км/ч|м/с|кг|килограмм\w*|грамм\w*|гр\b|г\b|км|километр\w*|метр\w*|м\b|мвт|милливатт\w*|мгц|вт\b|ватт\w*|"
           r"лет\b|год\w*|г\.|месяц\w*|суток|сутки|сут\b|календарн\w*\s+дн\w*|календарн\w*\s+ден\w*|рабоч\w*\s+дн\w*|"
           r"рабоч\w*\s+ден\w*|дн\w*|день|час\w*|минут\w*|секунд\w*|фут\w*|%|процент\w*")
NUMBER_RE = r"\d[\d ]*(?:[.,]\d+)?"
# "5 (пяти) рабочих дней" is written with the number in brackets; "от 25 до 750 кг" gives the first number the same unit
CLAIM_RE = re.compile(rf"(?<![\w.,])({NUMBER_RE})\s*(?:\([^)\d]{{1,30}}\)\s*)?({UNIT_RE})", re.I)
RANGE_RE = re.compile(rf"(?<![\w.,])({NUMBER_RE})\s*(?:-|–|—|до)\s*({NUMBER_RE})\s*({UNIT_RE})", re.I)

ABSTAIN_TEXT = ("Я не могу подтвердить этот ответ: значение из черновика не найдено в официальных пунктах Правил, "
                "поэтому я его не показываю. Проверьте официальные пункты ниже или обратитесь в уполномоченную "
                "организацию в сфере гражданской авиации.")
FALLBACK_WARNING = ("Внимание: в непроверенном источнике найдено значение, которого нет в официальных пунктах Правил. "
                    "Ответ составлен только по официальному тексту, проверьте его по пунктам ниже.")
NO_CLAIMS_NOTE = "В ответе нет числовых значений, автоматическая проверка к нему не применялась. Проверьте его по пунктам ниже."


# Russian number words in the forms that occur before a unit
_WORD_VALUES = {
    1: "один одна одно одного одной одному", 2: "два две двух двум двое", 3: "три трех трёх трем трём трое",
    4: "четыре четырех четырёх четырем четырём", 5: "пять пяти", 6: "шесть шести", 7: "семь семи", 8: "восемь восьми",
    9: "девять девяти", 10: "десять десяти", 11: "одиннадцать одиннадцати", 12: "двенадцать двенадцати",
    13: "тринадцать тринадцати", 14: "четырнадцать четырнадцати", 15: "пятнадцать пятнадцати", 16: "шестнадцать шестнадцати",
    17: "семнадцать семнадцати", 18: "восемнадцать восемнадцати", 19: "девятнадцать девятнадцати", 20: "двадцать двадцати",
    30: "тридцать тридцати", 40: "сорок сорока", 50: "пятьдесят пятидесяти", 60: "шестьдесят шестидесяти",
    70: "семьдесят семидесяти", 80: "восемьдесят восьмидесяти", 90: "девяносто девяноста", 100: "сто ста",
    200: "двести двухсот", 300: "триста трехсот трёхсот", 400: "четыреста четырехсот четырёхсот", 500: "пятьсот пятисот",
    600: "шестьсот шестисот", 700: "семьсот семисот", 800: "восемьсот восьмисот", 900: "девятьсот девятисот",
}
WORD_NUM = {w: v for v, words in _WORD_VALUES.items() for w in words.split()}
_NUM_WORD = "|".join(sorted(WORD_NUM, key=len, reverse=True))
WORD_SEQ_RE = re.compile(rf"\b((?:(?:{_NUM_WORD}|тысяч[аиу]?)\s+)+)(?=(?:{UNIT_RE}))", re.I)
HALF_RE = re.compile(rf"\b(половин[аыеу]|полутора|полторы|полтора)\s+(?=(?:{UNIT_RE}))", re.I)


def words_to_digits(text):
    """"ста двадцати метров" -> "120 метров", "половины килограмма" -> "0.5 килограмма". Only before a unit."""
    def seq(m):
        total, part = 0, 0
        for w in m.group(1).lower().split():
            if w.startswith("тысяч"):
                total += max(part, 1) * 1000
                part = 0
            else:
                part += WORD_NUM[w]
        return f"{total + part} "
    text = WORD_SEQ_RE.sub(seq, text)
    return HALF_RE.sub(lambda m: "0.5 " if m.group(1).lower().startswith("половин") else "1.5 ", text)


def canon_unit(unit):
    """Return (canonical unit, factor to the base unit), or None for an unknown unit."""
    u = re.sub(r"\s+", " ", unit.lower()).strip()
    if u in ("кг",) or u.startswith("килограмм"): return "kg", 1.0
    if u in ("г", "гр") or u.startswith("грамм"): return "kg", 0.001
    if u == "км" or u.startswith("километр"): return "m", 1000.0
    if u == "м" or u.startswith("метр"): return "m", 1.0
    if u == "км/ч": return "km/h", 1.0
    if u == "м/с": return "m/s", 1.0
    if u == "мвт" or u.startswith("милливатт"): return "W", 0.001
    if u == "вт" or u.startswith("ватт"): return "W", 1.0
    if u == "мгц": return "MHz", 1.0
    if u == "лет" or u.startswith("год"): return "year", 1.0
    if u.startswith("месяц"): return "month", 1.0
    if u.startswith("рабоч"): return "work-day", 1.0
    if u.startswith(("сут", "календарн", "дн", "ден")): return "day", 1.0
    if u.startswith("час"): return "hour", 1.0
    if u.startswith("минут"): return "minute", 1.0
    if u.startswith("секунд"): return "second", 1.0
    if u.startswith("фут"): return "foot", 1.0
    if u == "%" or u.startswith("процент"): return "percent", 1.0
    return None


def _number(text):
    return float(text.replace(" ", "").replace(",", "."))


def extract_claims(text):
    """Set of (unit, value in base units) found in the text. Calendar years ("2017 года", "2026 г.") are not claims."""
    claims = set()
    text = words_to_digits(text)

    def add(num, unit):
        c = canon_unit(unit)
        if c is None:
            return
        value = _number(num)
        if 1900 <= value <= 2100 and c[0] in ("year", "kg") and unit.lower() in ("г", "г.", "года", "году", "год", "годы"):
            return
        claims.add((c[0], round(value * c[1], 6)))

    for m in CLAIM_RE.finditer(text):
        if m.group(2).lower() == "г.":      # "2026 г." is a date, not grams
            continue
        add(m.group(1), m.group(2))
    for m in RANGE_RE.finditer(text):
        add(m.group(1), m.group(3))
    return claims


def fmt(claim):
    unit, value = claim
    v = f"{value:g}".replace(".", ",")
    names = {"kg": "кг", "m": "м", "W": "Вт", "year": "лет", "day": "дн.", "work-day": "раб. дн.", "foot": "футов"}
    return f"{v} {names.get(unit, unit)}"


def verify(draft, evidence_passages):
    """Check a draft against official passages. Verdict: no_claims | supported | blocked."""
    claims = extract_claims(draft)
    allowed = set()
    for p in evidence_passages:
        allowed |= extract_claims(p["text"])
    unsupported = sorted(claims - allowed)
    verdict = "no_claims" if not claims else "blocked" if unsupported else "supported"
    return {"verdict": verdict, "claims": sorted(claims), "unsupported": unsupported}


def suspect_sources(passages, allowed_claims):
    """Unverified retrieved passages that state a value missing from the official evidence (for the audit log and the alert)."""
    out = []
    for p in passages:
        if p.get("origin") != "official" and extract_claims(p["text"]) - allowed_claims:
            out.append(p["id"])
    return out
