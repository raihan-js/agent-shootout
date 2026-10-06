"""The three tools every architecture gets, identical in all four: search_articles, get_article, verify_citation.

`LawTools` is plain Python over the registry (testable without any framework); `make_tools` wraps it as LangChain tools. Tool outputs are plain strings, deliberately short
(an article is cut at MAX_CHARS) so that a prompt stays far below the model's context window. Search results show the law, the article and the start of its text, NOT the caption:
the caption appears when an article is opened, as in a full-text search over statutes.
"""
import re
import unicodedata

from jacite.normaliser import normalise_article_ref
from langchain_core.tools import tool

from .questions import is_deleted
from .registry import LAW_NAMES_EN
from .search import Bm25

MAX_CHARS = 900
SNIPPET = 70


def resolve_article_id(ref):
    """'541', '415-2', '第五百四十一条', '第415条の2', 'Article 541' -> canonical id, or None."""
    if not isinstance(ref, str):
        return None
    s = unicodedata.normalize("NFKC", ref).strip()
    if re.fullmatch(r"\d+(-\d+)*", s):
        return s
    return normalise_article_ref(s)


class LawTools:
    def __init__(self, registry, index_captions=False):
        self.reg = registry
        self.laws = {l["title"]: l for l in registry["laws"]}
        self.alias = {**{t: t for t in self.laws}, **{en.lower(): t for t, en in LAW_NAMES_EN.items() if t in self.laws}}
        self.by_id = {t: {a["id"]: i for i, a in enumerate(l["articles"])} for t, l in self.laws.items()}
        self.flat = [(t, i) for t, l in self.laws.items() for i in range(len(l["articles"]))]
        self.flat_pos = {k: n for n, k in enumerate(self.flat)}
        self.index = Bm25([(self.laws[t]["articles"][i]["caption"] + " " if index_captions else "") + self.laws[t]["articles"][i]["text"] for t, i in self.flat])
        self.law_rows = {t: {n for n, (t2, _) in enumerate(self.flat) if t2 == t} for t in self.laws}

    # -- helpers -----------------------------------------------------------------
    def law_title(self, name):
        return self.alias.get(unicodedata.normalize("NFKC", name or "").strip().lower()) or self.alias.get((name or "").strip())

    def exists(self, law, article):
        t = self.law_title(law)
        aid = resolve_article_id(article)
        if t is None or aid is None or aid not in self.by_id[t]:
            return False
        return not is_deleted(self.laws[t]["articles"][self.by_id[t][aid]])

    def neighbours(self, title, i):
        arts = self.laws[title]["articles"]
        prev = next((arts[j]["id"] for j in range(i - 1, -1, -1) if not is_deleted(arts[j])), None)
        nxt = next((arts[j]["id"] for j in range(i + 1, len(arts)) if not is_deleted(arts[j])), None)
        return prev, nxt

    def _unknown_law(self, law):
        return f"Unknown law {law!r}. Available laws: " + ", ".join(f"{t} ({LAW_NAMES_EN.get(t, t)})" for t in self.laws)

    # -- the three tools ---------------------------------------------------------
    def search(self, query, law="", top_k=5):
        title = None
        if law:
            title = self.law_title(law)
            if title is None:
                return self._unknown_law(law)
        top_k = max(1, min(int(top_k or 5), 8))
        hits = self.index.top(query, top_k * 3 if title is None else top_k, allowed=self.law_rows[title] if title else None)
        lines = []
        for n, _ in hits:
            t, i = self.flat[n]
            a = self.laws[t]["articles"][i]
            if is_deleted(a):
                continue
            lines.append(f"{t} {a['title']} (id {a['id']}): {a['text'][:SNIPPET].replace(chr(10), ' ')}…")
            if len(lines) >= top_k:
                break
        return "\n".join(f"{n + 1}. {l}" for n, l in enumerate(lines)) if lines else "No matching articles."

    def get(self, law, article):
        title = self.law_title(law)
        if title is None:
            return self._unknown_law(law)
        aid = resolve_article_id(article)
        if aid is None or aid not in self.by_id[title] or is_deleted(self.laws[title]["articles"][self.by_id[title][aid]]):
            return f"No such article: {title} has no article {article!r}."
        i = self.by_id[title][aid]
        a = self.laws[title]["articles"][i]
        text = a["text"] if len(a["text"]) <= MAX_CHARS else a["text"][:MAX_CHARS] + f"…[truncated, {len(a['text']) - MAX_CHARS} more characters]"
        prev, nxt = self.neighbours(title, i)
        return f"{title} {a['title']} (id {a['id']})\nCaption: {a['caption'] or '(none)'}\nText: {text}\nPrevious article id: {prev}; next article id: {nxt}"

    def verify(self, law, article):
        title = self.law_title(law)
        if title is None:
            return self._unknown_law(law)
        return f"VALID: {title} article {article} exists." if self.exists(law, article) else f"INVALID: {title} has no article {article!r}."


def make_tools(lt):
    @tool
    def search_articles(query: str, law: str = "", top_k: int = 5) -> str:
        """Full-text search over Japanese statute articles. `query` is words describing the content of an article; `law` optionally restricts the search to one law
        (Japanese title or English name, e.g. 民法 or Civil Code). Returns up to top_k matches as 'law article-title (id N): start of the text'. The caption of an article is
        not searched: open an article with get_article to read it."""
        return lt.search(query, law, top_k)

    @tool
    def get_article(law: str, article: str) -> str:
        """Read one article: its caption, its text (long texts are cut) and the ids of the previous and next article. `article` is the article number as printed in the
        search results (e.g. 541 or 415-2)."""
        return lt.get(law, article)

    @tool
    def verify_citation(law: str, article: str) -> str:
        """Check that an article exists in a law. Returns VALID or INVALID. Use it before citing an article you have not opened."""
        return lt.verify(law, article)

    return [search_articles, get_article, verify_citation]
