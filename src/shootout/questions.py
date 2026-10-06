"""Question generator: rule-based, deterministic, no language model. Every question has a gold set of articles known from the registry and NEVER names an article
number (JaCite-Bench's did, which makes retrieval trivial), so the agent has to find the article.

Types (each item is asked in Japanese and in English, so the language comparison is paired):
  topic     which article deals with 「caption」?                                          gold: that article
  neighbour which article comes right after the one on 「caption」?  (needs search + navigation)   gold: the next article in the law
  pair      which articles deal with 「caption A」 and 「caption B」?                      gold: both articles (same law)
Eligible anchor articles: not deleted, a caption that is unique across the whole registry, text of 30 to 600 characters. English questions quote the Japanese
caption (there is no automatic translation); that is part of the task, not a bug.
"""
import random

from jacite.normaliser import extract_cited_articles

from .registry import LAW_NAMES_EN

TYPES = ("topic", "neighbour", "pair")

JA = {
    "topic": "{law}のうち、「{a}」について定めている条文はどれですか。条文番号を挙げて、その内容を要約してください。",
    "neighbour": "{law}で、「{a}」について定めている条文の直後に置かれている条文はどれですか。その条文番号を挙げて、内容を要約してください。",
    "pair": "{law}で、「{a}」と「{b}」についてそれぞれ定めている条文はどれですか。条文番号を挙げて、内容を要約してください。",
}
EN = {
    "topic": "Which article of the {law} deals with 「{a}」? Cite the article number and summarize what it provides.",
    "neighbour": "In the {law}, which article comes immediately after the one on 「{a}」? Cite its number and summarize what it provides.",
    "pair": "Which articles of the {law} deal with 「{a}」 and 「{b}」? Cite the article numbers and summarize what each provides.",
}


def is_deleted(article):
    return article["text"].strip().startswith("削除") or ":" in article["id"]


def eligible(registry):
    """[(law_dict, index_in_law)] of articles that can anchor a question."""
    counts = {}
    for law in registry["laws"]:
        for a in law["articles"]:
            if a["caption"] and not is_deleted(a):
                counts[a["caption"]] = counts.get(a["caption"], 0) + 1
    out = []
    for law in registry["laws"]:
        arts = law["articles"]
        for i, a in enumerate(arts):
            if is_deleted(a) or not a["caption"] or counts[a["caption"]] != 1 or len(a["caption"]) < 3 or not (30 <= len(a["text"]) <= 600):
                continue
            out.append((law, i))
    return out


def _next_index(law, i):
    for j in range(i + 1, len(law["articles"])):
        if not is_deleted(law["articles"][j]):
            return j
    return None


def make_items(registry, n_per_type, seed, exclude=frozenset()):
    """n_per_type items of each type. `exclude` is a set of (law_id, article_id) already used (dev vs test must be disjoint). Returns (items, used)."""
    rng = random.Random(seed)
    pool = [(law, i) for law, i in eligible(registry) if (law["law_id"], law["articles"][i]["id"]) not in exclude]
    rng.shuffle(pool)
    used = set(exclude)
    items = []

    def take(pred=lambda law, i: True):
        for k, (law, i) in enumerate(pool):
            key = (law["law_id"], law["articles"][i]["id"])
            if key in used or not pred(law, i):
                continue
            pool.pop(k)
            used.add(key)
            return law, i
        raise ValueError("not enough eligible articles")

    def mark(law, j):
        used.add((law["law_id"], law["articles"][j]["id"]))

    for t in TYPES:
        for n in range(n_per_type):
            if t == "topic":
                law, i = take()
                items.append({"type": t, "law": law["title"], "law_id": law["law_id"], "captions": [law["articles"][i]["caption"]], "gold": [law["articles"][i]["id"]], "anchor": []})
            elif t == "neighbour":
                law, i = take(lambda law, i: _next_index(law, i) is not None)
                j = _next_index(law, i)
                mark(law, j)                                                       # the neighbour is gold: keep it out of every other item and split
                items.append({"type": t, "law": law["title"], "law_id": law["law_id"], "captions": [law["articles"][i]["caption"]], "gold": [law["articles"][j]["id"]],
                              "anchor": [law["articles"][i]["id"]]})
            else:
                law, i = take()
                k_pool = [(k, (l2, i2)) for k, (l2, i2) in enumerate(pool) if l2["law_id"] == law["law_id"] and (l2["law_id"], l2["articles"][i2]["id"]) not in used
                          and abs(i2 - i) > 1]
                if not k_pool:
                    used.discard((law["law_id"], law["articles"][i]["id"]))
                    law, i = take()
                    k_pool = [(k, (l2, i2)) for k, (l2, i2) in enumerate(pool) if l2["law_id"] == law["law_id"] and (l2["law_id"], l2["articles"][i2]["id"]) not in used
                              and abs(i2 - i) > 1]
                _, (law2, i2) = k_pool[0]
                used.add((law2["law_id"], law2["articles"][i2]["id"]))
                items.append({"type": t, "law": law["title"], "law_id": law["law_id"], "captions": [law["articles"][i]["caption"], law2["articles"][i2]["caption"]],
                              "gold": [law["articles"][i]["id"], law2["articles"][i2]["id"]], "anchor": []})
    return items, used


def render(items, prefix):
    """Two questions per item (ja, en) with stable ids."""
    out = []
    for n, it in enumerate(items):
        caps = {"a": it["captions"][0], "b": it["captions"][1] if len(it["captions"]) > 1 else ""}
        for lang, tmpl, law_name in (("ja", JA, it["law"]), ("en", EN, LAW_NAMES_EN.get(it["law"], it["law"]))):
            q = tmpl[it["type"]].format(law=law_name, **caps)
            assert not extract_cited_articles(q), f"question names an article: {q}"
            out.append({"id": f"{prefix}{n:03d}-{lang}", "item_id": f"{prefix}{n:03d}", "language": lang, "type": it["type"], "law": it["law"], "law_id": it["law_id"],
                        "question": q, "gold": it["gold"], "anchor": it["anchor"]})
    return out


def build(registry, dev_per_type=6, test_per_type=40, seed=0):
    """Dev and test questions, disjoint in every article they touch."""
    dev_items, used = make_items(registry, dev_per_type, seed)
    test_items, _ = make_items(registry, test_per_type, seed + 1, exclude=frozenset(used))
    return render(dev_items, "dev"), render(test_items, "test")
