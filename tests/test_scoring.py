from shootout.scoring import cited_ids, score_answer
from shootout.tools import LawTools

Q = {"law": "民法", "gold": ["5"], "anchor": []}


def test_citation_parsing_dedupes_normalises_and_keeps_text_order():
    assert cited_ids("民法第五条と第5条、Article 2-2、第二条の二") == ["5", "2-2"]
    assert cited_ids("第百二十五条の二の三と第三条") == ["125-2-3", "3"]
    assert cited_ids("Articles 5, 7 and 9-2 of the Civil Code") == ["5", "7", "9-2"]
    assert cited_ids("第５４１条") == ["541"]                       # full-width digits
    assert cited_ids("") == [] and cited_ids(None) == []


def test_a_branch_citation_is_one_citation_not_two():
    # JaCite-Bench's extract_cited_articles returns ['2-2', '2'] for this text: the phantom '2' is the prefix 第二条
    assert cited_ids("第二条の二") == ["2-2"]
    assert cited_ids("民法第四百十五条の二") == ["415-2"]


def test_correct_invented_and_missing(small_registry):
    lt = LawTools(small_registry)
    ok = score_answer(Q, "民法第五条が契約の解除を定めています。", lt)
    assert ok["correct"] and ok["gold_hit"] and not ok["invalid"] and not ok["extra"]
    invented = score_answer(Q, "民法第五条および第九十九条です。", lt)
    assert invented["invalid"] == ["99"] and invented["gold_hit"] and not invented["correct"]      # hitting gold does not excuse an invented citation
    none = score_answer(Q, "該当する条文は見つかりませんでした。", lt)
    assert none["no_citation"] and not none["gold_hit"] and none["gold_recall"] == 0
    wrong = score_answer(Q, "民法第一条です。", lt)
    assert wrong["extra"] == ["1"] and not wrong["gold_hit"]


def test_deleted_articles_count_as_invented(small_registry):
    assert score_answer(Q, "民法第三条です。", LawTools(small_registry))["invalid"] == ["3"]


def test_pair_needs_both_and_anchor_is_not_extra(small_registry):
    lt = LawTools(small_registry)
    pair = {"law": "民法", "gold": ["1", "5"], "anchor": []}
    assert score_answer(pair, "第一条と第五条", lt)["correct"] and not score_answer(pair, "第一条のみ", lt)["gold_hit"]
    assert score_answer(pair, "第一条のみ", lt)["gold_recall"] == 0.5
    nb = {"law": "民法", "gold": ["5"], "anchor": ["4"]}
    assert score_answer(nb, "第四条の次は第五条です。", lt)["extra"] == []


def test_quotes_are_checked_against_the_cited_text(small_registry):
    lt = LawTools(small_registry)
    good = score_answer(Q, "第五条は「相手方は契約の解除をすることができる」と定めます。", lt)
    bad = score_answer(Q, "第五条は「当事者は常に損害賠償を請求できる」と定めます。", lt)
    assert (good["quotes"], good["quotes_unsupported"]) == (1, 0) and (bad["quotes"], bad["quotes_unsupported"]) == (1, 1)


def test_spaced_and_bare_number_forms_are_citations():
    # found on the dev set: the model writes "民法第 740 条" and "民法709条"; a strict 第N条 pattern scored such correct answers as having no citation
    assert cited_ids("民法第 740 条は") == ["740"] and cited_ids("民法第　740　条") == ["740"]
    assert cited_ids("民法709条と民法第 415 条の 2 です") == ["709", "415-2"]
    assert cited_ids("第740条第1項") == ["740"]
    assert cited_ids("民法740条の2") == ["740-2"]


def test_no_false_positives_from_ordinary_text():
    assert cited_ids("第三者に対抗できない。条約と条例と条文。") == []
    assert cited_ids("国際条約740件") == []
    assert cited_ids("1,000条約") == []
