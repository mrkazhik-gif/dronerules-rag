# -*- coding: utf-8 -*-
"""
Build the knowledge base of the DroneRules RAG assistant from the CURRENT edition of the Kazakhstan UAS rules.

Input : data/source/kz_uav_rules_current.txt - «Правила использования беспилотных авиационных систем в воздушном
        пространстве Республики Казахстан», approved by Order No. 706 of 31.12.2020 (reg. No. 22031) in the edition of
        Order No. 340 of 12.05.2023 with the changes of Order No. 15 of 09.01.2024. Text taken on 22.10.2026 from the
        public API of adilet.zan.kz (is_actual = true; see kz_uav_rules_current_meta.json and the original HTML).
        data/kb/community_faq.jsonl - short plain-language notes (correct, but NOT an official source)
Output: data/kb/official_chunks.jsonl - one record per chunk: id, source, origin="official", text
        data/kb/manifest.json          - SHA-256 of every official chunk (used by the provenance filter)

Chunking (v2, 22.10.2026):
  * an item without sub-items ("7.", "20-1.") is one chunk, split at MAX_WORDS if it is long;
  * an item with numbered sub-items ("1)", "2)", ...) gets one chunk for its lead sentence and one chunk per sub-item;
    every sub-item chunk starts with the lead sentence, so that "50 m in controlled airspace" and "200 m in
    uncontrolled airspace" end up in different chunks but keep their context;
  * the tables of annex 1 (classification) and annex 2 (meteorological minima) are rebuilt row by row into sentences,
    because a flattened table ("300 (1000) 300 (1000) 2000 5000 ...") loses its column headers.
The text is not changed apart from this restructuring. Amendment notes ("Сноска ...") are dropped. The other annexes
are forms and training programmes and are skipped.

Run:  python build_kb.py
"""
import json, hashlib, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC, KB = ROOT / "data" / "source", ROOT / "data" / "kb"
TXT = SRC / "kz_uav_rules_current.txt"
MAX_WORDS = 160
LEAD_WORDS = 40                                       # how much of the lead sentence is repeated in sub-item chunks
SHORT = "Правила использования БАС РК"
ITEM = re.compile(r"^(\d{1,3}(?:-\d)?)\.\s")          # "7. К операциям ...", "20-1. ..."
SUBITEM = re.compile(r"^(\d{1,2})\)\s")               # "1) максимальная взлетная масса ..."
ANNEX = re.compile(r"^Приложение (\d+(?:-\d)?)\b")
ANNEX_HEAD = ("к Правилам", "беспилотных авиационных", "систем в воздушном", "Республики Казахстан")


def words(text):
    return " ".join(text.split())


def split_long(prefix, lines):
    """Group lines into chunks of <= MAX_WORDS words, starting a new chunk at a line boundary."""
    out, cur = [], []
    for ln in lines:
        if cur and len(" ".join(cur + [ln]).split()) > MAX_WORDS:
            out.append(cur); cur = []
        cur.append(ln)
    if cur:
        out.append(cur)
    return [f"{prefix} " + words(" ".join(c)) for c in out]


def item_chunks(n, lines):
    """Records for one numbered item: whole item, or lead + one chunk per sub-item."""
    prefix = f"{SHORT}, пункт {n}."
    lead, subs, cur = [], [], None
    for ln in lines:
        m = SUBITEM.match(ln)
        if m:
            cur = [m.group(1), [ln]]; subs.append(cur)
        elif cur is None:
            lead.append(ln)
        else:
            cur[1].append(ln)                      # unnumbered continuation lines stay with their sub-item
    base = {"source": f"{SHORT}, п. {n}", "origin": "official"}
    if len(subs) < 2:
        return [{**base, "id": f"kz-p{n}_{i}", "text": t} for i, t in enumerate(split_long(prefix, lines))]
    lead_text = words(" ".join(lead))
    lead_short = " ".join(lead_text.split()[:LEAD_WORDS]) + (" …" if len(lead_text.split()) > LEAD_WORDS else "")
    recs = [{**base, "id": f"kz-p{n}_0", "text": f"{prefix} {lead_text}"}]
    for k, body in subs:
        for i, t in enumerate(split_long(f"{SHORT}, пункт {n}, подпункт {k}). {lead_short}", body)):
            recs.append({**base, "id": f"kz-p{n}_s{k}" + (f"_{i}" if i else ""), "text": t,
                         "source": f"{SHORT}, п. {n} пп. {k})"})
    return recs


def annex1_rows(lines):
    """Annex 1: classification tables (type of construction, MTOM categories) -> one sentence per row."""
    text_before, rows, i = [], [], 0
    while i < len(lines) and lines[i] != "Тип конструкции":
        text_before.append(lines[i]); i += 1
    i += 2                                                    # skip header "Тип конструкции", "Классификатор"
    types = []
    while not lines[i].startswith("3)"):
        types.append(f"{lines[i]} — классификатор {lines[i + 1]}"); i += 2
    rows.append("Классификация по типу конструкции: " + "; ".join(types) + ".")
    i += 4                                                    # "3) по максимальной...", header of three cells
    while i + 2 < len(lines) + 1 and i < len(lines):
        cat, rng, code = lines[i:i + 3]
        rows.append(f"Классификация по максимальной взлетной массе (МТОМ): категория «{cat}» — весовой диапазон {rng}, "
                    f"классификатор МТОМ {code}.")
        i += 3
    return [words(" ".join(text_before))] + rows


def annex2_rows(lines):
    """Annex 2: table of meteorological minima -> one sentence per terrain row."""
    title = lines[0]
    i = lines.index("Вид полета") + 5                          # skip the 4 sub-headers VLOS / BVLOS / VLOS / BVLOS
    rows, note = [], ""
    while i < len(lines):
        if lines[i].startswith("Примечание"):
            note = words(" ".join(lines[i:])); break
        terrain, cb_vlos, cb_bvlos, vis_vlos, vis_bvlos = lines[i:i + 5]
        rows.append(f"{title}. Местность: {terrain}. Полеты VLOS: высота нижней границы облаков (ВНГО) над наивысшей точкой "
                    f"рельефа не менее {cb_vlos.replace('(', 'м (').replace(')', ' футов)')}, видимость не менее {vis_vlos} м. "
                    f"Полеты BVLOS: ВНГО не менее {cb_bvlos.replace('(', 'м (').replace(')', ' футов)')}, "
                    f"видимость не менее {vis_bvlos} м.")
        i += 5
    return rows + ([note] if note else [])


def main():
    lines = [l.strip() for l in TXT.read_text(encoding="utf-8").split("\n") if l.strip() and not l.startswith("NOTE")]
    start = next(i for i, l in enumerate(lines) if l.startswith("Глава 1."))
    items, order, annexes, cur, annex = {}, [], {}, None, None
    for ln in lines[start:]:
        m = ANNEX.match(ln)
        if m:
            annex = m.group(1); annexes.setdefault(annex, []); continue
        if annex:
            if not ln.startswith(ANNEX_HEAD):
                annexes[annex].append(ln)
            continue
        if ln.startswith("Глава ") or ln.startswith("Параграф "):
            cur = None; continue
        m = ITEM.match(ln)
        if m and m.group(1) not in items:
            cur = m.group(1); items[cur] = [ln]; order.append(cur)
        elif cur is not None:
            items[cur].append(ln)
    records = []
    for n in order:
        records += item_chunks(n, items[n])
    for a, rows in (("1", annex1_rows(annexes["1"])), ("2", annex2_rows(annexes["2"]))):
        for i, row in enumerate(rows):
            records.append({"id": f"kz-a{a}_{i}", "source": f"{SHORT}, приложение {a}", "origin": "official",
                            "text": f"{SHORT}, приложение {a}. {row}"})

    KB.mkdir(parents=True, exist_ok=True)
    with open(KB / "official_chunks.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # The manifest is written at ingestion time from the official text only. Later the provenance filter accepts a
    # chunk only if its id is listed here AND its text still has the same hash.
    manifest = {r["id"]: hashlib.sha256(r["text"].encode("utf-8")).hexdigest() for r in records}
    (KB / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    n_words = sum(len(r["text"].split()) for r in records)
    print(f"items: {len(order)}  official chunks: {len(records)}  words: {n_words}  -> {KB}")


if __name__ == "__main__":
    main()
