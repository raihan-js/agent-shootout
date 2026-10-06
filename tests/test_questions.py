from collections import Counter

from jacite.normaliser import extract_cited_articles

from shootout import questions


def test_no_question_names_an_article_and_every_gold_exists(real_registry):
    dev, test = questions.build(real_registry)
    ids = {(l["title"], a["id"]) for l in real_registry["laws"] for a in l["articles"]}
    for q in dev + test:
        assert extract_cited_articles(q["question"]) == []
        assert q["gold"] and all((q["law"], g) in ids for g in q["gold"])
        assert len(q["question"]) > 20


def test_sizes_types_languages_and_pairing(real_registry):
    dev, test = questions.build(real_registry)
    assert (len(dev), len(test)) == (36, 240)
    assert dict(Counter(q["type"] for q in test)) == {"topic": 80, "neighbour": 80, "pair": 80}
    assert dict(Counter(q["language"] for q in test)) == {"ja": 120, "en": 120}
    by_item = {}
    for q in test:
        by_item.setdefault(q["item_id"], []).append(q)
    assert all(len(v) == 2 and v[0]["gold"] == v[1]["gold"] and {x["language"] for x in v} == {"ja", "en"} for v in by_item.values())


def test_dev_and_test_touch_disjoint_articles(real_registry):
    dev, test = questions.build(real_registry)
    touched = lambda qs: {(q["law_id"], a) for q in qs for a in q["gold"] + q["anchor"]}
    assert not touched(dev) & touched(test)


def test_gold_semantics(real_registry):
    _, test = questions.build(real_registry)
    law = {l["title"]: l for l in real_registry["laws"]}
    for q in test:
        if q["language"] != "ja":
            continue
        arts = {a["id"]: i for i, a in enumerate(law[q["law"]]["articles"])}
        if q["type"] == "neighbour":                                              # gold is the nearest non-deleted article after the anchor
            i = arts[q["anchor"][0]]
            nxt = next(a for a in law[q["law"]]["articles"][i + 1:] if not questions.is_deleted(a))
            assert q["gold"] == [nxt["id"]]
        if q["type"] == "pair":
            assert len(set(q["gold"])) == 2 and abs(arts[q["gold"][0]] - arts[q["gold"][1]]) > 1


def test_generation_is_deterministic(real_registry):
    assert questions.build(real_registry) == questions.build(real_registry)
