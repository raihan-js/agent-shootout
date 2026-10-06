from shootout import registry, search
from shootout.tools import LawTools, make_tools, resolve_article_id


def test_extract_articles_main_only_and_branch_ids():
    tree = {"tag": "Law", "children": [{"tag": "LawBody", "children": [
        {"tag": "MainProvision", "children": [
            {"tag": "Article", "attr": {"Num": "415_2"}, "children": [
                {"tag": "ArticleCaption", "children": ["（損害賠償）"]}, {"tag": "ArticleTitle", "children": ["第四百十五条の二"]},
                {"tag": "Paragraph", "attr": {"Num": "1"}, "children": [{"tag": "ParagraphNum", "children": []},
                                                                      {"tag": "ParagraphSentence", "children": [{"tag": "Sentence", "children": ["本文一。"]}]}]},
                {"tag": "Paragraph", "attr": {"Num": "2"}, "children": [{"tag": "ParagraphNum", "children": ["２"]},
                                                                      {"tag": "ParagraphSentence", "children": [{"tag": "Sentence", "children": ["本文二。"]}]}]}]}]},
        {"tag": "SupplProvision", "children": [{"tag": "Article", "attr": {"Num": "1"}, "children": []}]}]}]}
    arts = registry.extract_articles(tree)
    assert [a["id"] for a in arts] == ["415-2"]                                  # the supplementary Article 1 is not indexed
    assert arts[0]["caption"] == "損害賠償" and arts[0]["title"] == "第四百十五条の二" and arts[0]["text"] == "本文一。\n２本文二。"


def test_real_registry_shape(real_registry):
    assert len(real_registry["laws"]) == 11 and sum(len(l["articles"]) for l in real_registry["laws"]) == 4778
    for law in real_registry["laws"]:
        ids = [a["id"] for a in law["articles"]]
        assert len(ids) == len(set(ids)), law["title"]


def test_resolver_accepts_every_printed_form():
    for ref, want in [("541", "541"), ("415-2", "415-2"), ("第五百四十一条", "541"), ("第415条の2", "415-2"), ("Article 541", "541"), ("１２", "12")]:
        assert resolve_article_id(ref) == want, ref
    assert resolve_article_id("nonsense") is None and resolve_article_id(None) is None


def test_get_verify_and_navigation_skip_deleted(small_registry):
    lt = LawTools(small_registry)
    assert "Caption: 解釈の基準" in lt.get("民法", "2") and "next article id: 2-2" in lt.get("民法", "2")
    assert "previous article id: 2-2" not in lt.get("民法", "4") and "Previous article id: 2-2; next article id: 5" in lt.get("民法", "4")   # 3 is deleted
    assert lt.get("Civil Code", "第二条の二").startswith("民法 第二条の二")           # English name, printed form
    assert lt.get("民法", "3").startswith("No such article")                       # deleted
    assert lt.verify("民法", "5").startswith("VALID") and lt.verify("民法", "99").startswith("INVALID") and lt.verify("民法", "3").startswith("INVALID")
    assert lt.get("Nope", "1").startswith("Unknown law") and "民法 (Civil Code)" in lt.get("Nope", "1")
    assert "truncated, 300 more characters" in lt.get("民法", "4")


def test_search_is_text_only_and_never_shows_captions(small_registry):
    lt = LawTools(small_registry)
    out = lt.search("債務を履行しない場合 契約の解除", "民法")
    assert out.startswith("1. 民法 第五条 (id 5):") and "契約の解除" not in out.split(":")[0]
    assert "契約の解除" not in out.replace("契約の解除をすることができる", "")      # the caption string is not rendered
    assert lt.search("設立 組織 運営", "Companies Act").startswith("1. 会社法 第一条")
    assert lt.search("zzzz qqqq", "民法") == "No matching articles."
    assert all("削除" not in l for l in lt.search("削除").splitlines())             # deleted articles are never returned


def test_caption_indexing_is_an_option(small_registry):
    on = LawTools(small_registry, index_captions=True)
    assert on.search("基本原則", "民法").startswith("1. 民法 第一条")


def test_bm25_ranks_the_matching_document_first():
    idx = search.Bm25(["契約の解除に関する規定", "婚姻の成立に関する規定", "会社の設立"])
    assert idx.top("契約解除", 3)[0][0] == 0 and idx.top("会社設立", 3)[0][0] == 2


def test_tools_are_wrapped_with_stable_names(small_registry):
    tools = make_tools(LawTools(small_registry))
    assert [t.name for t in tools] == ["search_articles", "get_article", "verify_citation"]
    assert tools[2].invoke({"law": "民法", "article": "1"}).startswith("VALID")
