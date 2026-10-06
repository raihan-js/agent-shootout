"""The statute registry: the symbolic source of truth for every citation check, built from the e-Gov Law API v2.

Unlike the JaCite-Bench registry (article numbers and captions only) this one keeps each article's TEXT, so tools can show it and quoted passages can be
checked against it. Only the main provisions are indexed: supplementary provisions (附則) contain `Article` nodes whose numbers collide with the main text.

Attribution: 出典：e-Gov法令検索（デジタル庁）https://laws.e-gov.go.jp/ を加工して作成. Statutes are not subject to copyright in Japan (著作権法第13条).
"""
import gzip
import json
import re
import time
from pathlib import Path

API_BASE = "https://laws.e-gov.go.jp/api/2"

# The same 11 laws as JaCite-Bench: (title, e-Gov law id)
LAWS = [
    ("民法", "129AC0000000089"), ("民法施行法", "131AC0000000011"), ("刑法", "140AC0000000045"), ("商法", "132AC0000000048"),
    ("会社法", "417AC0000000086"), ("労働基準法", "322AC0000000049"), ("健康保険法", "211AC0000000070"), ("刑事訴訟法", "323AC0000000131"),
    ("国家賠償法", "322AC0000000125"), ("国家公務員法", "322AC0000000120"), ("地方自治法", "322AC0000000067"),
]
LAW_NAMES_EN = {
    "民法": "Civil Code", "民法施行法": "Civil Code Enforcement Act", "刑法": "Penal Code", "商法": "Commercial Code", "会社法": "Companies Act",
    "労働基準法": "Labor Standards Act", "健康保険法": "Health Insurance Act", "刑事訴訟法": "Code of Criminal Procedure",
    "国家賠償法": "State Redress Act", "国家公務員法": "National Public Service Act", "地方自治法": "Local Autonomy Act",
}
_SKIP_IN_TEXT = {"ArticleCaption", "ArticleTitle"}


def _strings(node, out):
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        if node.get("tag") in _SKIP_IN_TEXT:
            return
        for c in node.get("children", []):
            _strings(c, out)
    elif isinstance(node, list):
        for c in node:
            _strings(c, out)


def article_text(article):
    """Paragraphs joined by newlines, in document order; paragraph numbers and item titles are kept because they are part of how articles are cited."""
    paragraphs = []
    for child in article.get("children", []):
        if isinstance(child, dict) and child.get("tag") == "Paragraph":
            parts = []
            _strings(child, parts)
            paragraphs.append("".join(parts).strip())
    if not paragraphs:                                                   # an article without Paragraph nodes (rare)
        parts = []
        _strings(article, parts)
        paragraphs = ["".join(parts).strip()]
    return "\n".join(p for p in paragraphs if p)


def _caption(article):
    for c in article.get("children", []):
        if isinstance(c, dict) and c.get("tag") == "ArticleCaption":
            parts = []
            _strings({"children": c.get("children", [])}, parts)
            return re.sub(r"^[（(]|[）)]$", "", "".join(parts).strip())
    return ""


def _title(article):
    for c in article.get("children", []):
        if isinstance(c, dict) and c.get("tag") == "ArticleTitle":
            return "".join(x for x in c.get("children", []) if isinstance(x, str)).strip()
    return ""


def extract_articles(law_full_text):
    """Articles of the MAIN provisions only, in order: {id, title, caption, text}. `id` is e-Gov's Num with '_' as '-' ("415_2" -> "415-2")."""
    out = []

    def walk(node, in_main):
        if isinstance(node, list):
            for c in node:
                walk(c, in_main)
        elif isinstance(node, dict):
            tag = node.get("tag")
            if tag == "SupplProvision":
                return
            if tag == "Article" and in_main:
                num = (node.get("attr") or {}).get("Num", "")
                if num:
                    out.append({"id": num.replace("_", "-"), "title": _title(node), "caption": _caption(node), "text": article_text(node)})
                return
            for c in node.get("children", []):
                walk(c, in_main or tag == "MainProvision")

    walk(law_full_text, False)
    return out


def build_registry(laws=LAWS, delay=0.5, fetch=None):
    import requests
    fetch = fetch or (lambda law_id: requests.get(f"{API_BASE}/law_data/{law_id}", timeout=120).json())
    reg = {"source": "e-Gov Law API v2", "fetched": time.strftime("%Y-%m-%d"), "attribution": "出典：e-Gov法令検索（デジタル庁）https://laws.e-gov.go.jp/ を加工して作成", "laws": []}
    for title, law_id in laws:
        d = fetch(law_id)
        rev = d.get("revision_info", {})
        arts = extract_articles(d.get("law_full_text", {}))
        reg["laws"].append({"law_id": law_id, "title": rev.get("law_title", title), "revision_id": rev.get("law_revision_id", ""), "updated": rev.get("updated", ""),
                            "articles": arts})
        time.sleep(delay)
    return reg


def save(reg, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False)


def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)
