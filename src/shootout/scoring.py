"""Symbolic scoring of one answer. No language model, no judge: citations are parsed with the JaCite-Bench normaliser and resolved against the registry.

  cited          canonical ids of every article the answer cites (all attributed to the law in the question)
  invalid        cited ids that do not exist in that law (an INVENTED citation)
  gold_hit       every gold article is cited
  extra          cited articles that exist but are neither gold nor the anchor of a neighbour question ("real but off target")
  correct        gold_hit and no invalid citation          <- the primary outcome
  quotes         passages in 「…」 of 6+ characters, and how many do not occur in any cited article's text (unsupported)
"""
import re
import unicodedata

from jacite.normaliser import kanji_to_int

_NUM = r"[零一二三四五六七八九十百千\d]+"
# One left-to-right pass, so that 第二条の二 is ONE citation ("2-2"): JaCite-Bench's first extractor ran its patterns one after the other and also reported the prefix 第二条 of every
# branch citation as a second, phantom citation ("2"). Whitespace is allowed around the number (the model writes "第 740 条"), and a bare Arabic number before 条 counts ("民法709条").
_ARTICLE = re.compile(
    rf"第\s*(?P<n1>{_NUM})\s*条(?P<b1>(?:\s*の\s*{_NUM})*)"
    rf"|(?<![\d第])(?P<n2>\d{{1,4}})\s*条(?![約例])(?P<b2>(?:\s*の\s*\d+)*)"
    rf"|Articles?\s+(?P<en>\d+(?:-\d+)*(?:\s*(?:,|and|&|or)\s*\d+(?:-\d+)*)*)", re.I)
_QUOTE = re.compile(r"[「『]([^」』]{6,})[」』]")
_STRIP = re.compile(r"[\s、。，．,.・\n]+")


def _norm(s):
    return _STRIP.sub("", unicodedata.normalize("NFKC", s))


def cited_ids(answer):
    """Canonical ids of the articles an answer cites, in text order, without duplicates: 第五百四十一条 -> '541', 第二条の二 -> '2-2', Article 415-2 -> '415-2'."""
    out = []

    def add(i):
        if i and i not in out:
            out.append(i)

    for m in _ARTICLE.finditer(unicodedata.normalize("NFKC", answer or "")):
        if m.group("en"):
            for num in re.findall(r"\d+(?:-\d+)*", m.group("en")):
                add(num)
            continue
        n, b = (m.group("n1"), m.group("b1")) if m.group("n1") else (m.group("n2"), m.group("b2"))
        parts = [kanji_to_int(n)] + [kanji_to_int(x) for x in re.findall(rf"の\s*({_NUM})", b)]
        if None not in parts:
            add("-".join(str(x) for x in parts))
    return out


def score_answer(q, answer, lt):
    cited = cited_ids(answer)
    invalid = [c for c in cited if not lt.exists(q["law"], c)]
    gold, allowed = q["gold"], set(q["gold"]) | set(q.get("anchor", []))
    valid = [c for c in cited if c not in invalid]
    texts = [_norm(lt.laws[q["law"]]["articles"][lt.by_id[q["law"]][c]]["text"]) for c in valid]
    quotes = [m.group(1) for m in _QUOTE.finditer(answer or "")]
    unsupported = [x for x in quotes if not any(_norm(x) in t for t in texts)]
    gold_hit = all(g in cited for g in gold)
    return {"cited": cited, "invalid": invalid, "gold_hit": gold_hit, "gold_recall": sum(g in cited for g in gold) / len(gold),
            "extra": [c for c in valid if c not in allowed], "correct": gold_hit and not invalid, "no_citation": not cited,
            "quotes": len(quotes), "quotes_unsupported": len(unsupported)}
