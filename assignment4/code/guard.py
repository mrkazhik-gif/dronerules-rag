# -*- coding: utf-8 -*-
"""
Input guard of the DroneRules assistant (rule-based, runs before the LLM).

1. Keyboard layout: a question typed with the English layout ("crf;b rfr nt,z pjden") is converted to the Russian
   layout ("скажи как тебя зовут") and the user is told so.
2. Out of scope: if the question has no word from the domain AND the best retrieved passage is only weakly similar,
   the LLM is not called. Without this check the model wrote a fluent mix of unrelated items (a hallucination).
The 20 test questions of the experiment all contain domain words, so the guard never changes their answers.
"""
import re

EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`"
RU = "йцукенгшщзхъфывапролджэячсмитьбюё"
TO_RU = {ord(e): r for e, r in zip(EN, RU)}
TO_RU.update({ord(e.upper()): r.upper() for e, r in zip(EN, RU) if e.isalpha()})


def vowel_share(text, vowels):
    letters = [c for c in text.lower() if c.isalpha()]
    return sum(c in vowels for c in letters) / max(1, len(letters))

DOMAIN = re.compile(r"бвс|бас|бпла|дрон|беспилот|квадрокоптер|коптер|лет[ао]|полет|полёт|высот|масс|вес\b|кг\b|сертификат|"
                    r"разрешен|аэродром|воздушн|оператор|пилот|учет|учёт|регистрац|идентификац|remote ?id|vlos|bvlos|"
                    r"зон[аыу]|ноч|видимост|облак|погод|метео|правил|категори|штраф|запрет|границ", re.I)
MIN_SCORE = 0.85               # below this the best passage is only loosely related (test questions: 0.845-0.935)
OUT_OF_SCOPE = ("Я — DroneRules Assistant и отвечаю только на вопросы о Правилах использования беспилотных авиационных "
                "систем в воздушном пространстве РК (приказ № 706). В правилах я не нашел ничего по этому вопросу. "
                "Переформулируйте, пожалуйста, вопрос о полетах, разрешениях, сертификатах или требованиях к БАС.")


def fix_layout(question):
    """Return (question, note). Converts text typed in the English layout when the Russian reading looks like words."""
    if re.search(r"[а-яё]", question, re.I) or len(re.findall(r"[a-z]", question, re.I)) < 3:
        return question, ""
    converted = question.translate(TO_RU)
    # English text has many vowels (a e i o u); Russian typed in the English layout has few, but many after conversion
    if vowel_share(question, "aeiouy") < 0.25 and vowel_share(converted, "аеёиоуыэюя") >= 0.3:
        return converted, f"Вопрос был набран в английской раскладке, я прочитал его как: «{converted}»."
    return question, ""


def out_of_scope(question, best_score):
    return not DOMAIN.search(question) and best_score < MIN_SCORE
