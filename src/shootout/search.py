"""BM25 full-text search over the registry (own implementation: 4.8k short documents, no dependency).

Tokens: character bigrams for kana and kanji runs (no morphological dictionary needed), lower-cased words for ASCII. The default index covers the article TEXT only, the way a
statute full-text search does; captions are shown only when an article is opened (see `LawTools`). Whether captions are indexed is a documented design choice
(`index_captions`), made on a retrieval statistic that involves no agent (docs/PREREGISTRATION.md).
"""
import math
import re
import unicodedata
from collections import Counter, defaultdict

_RUN = re.compile(r"[぀-ヿ㐀-鿿]+|[a-z0-9]+")


def tokenize(s):
    toks = []
    for m in _RUN.finditer(unicodedata.normalize("NFKC", s).lower()):
        w = m.group(0)
        if "぀" <= w[0] <= "鿿":
            toks += [w[i:i + 2] for i in range(len(w) - 1)] if len(w) > 1 else [w]
        else:
            toks.append(w)
    return toks


class Bm25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(tokenize(d)) for d in docs]
        self.len = [sum(c.values()) for c in self.tf]
        self.avg = sum(self.len) / max(len(docs), 1)
        self.post = defaultdict(list)
        for i, c in enumerate(self.tf):
            for t, n in c.items():
                self.post[t].append((i, n))
        self.N = len(docs)

    def top(self, query, k=5, allowed=None):
        scores = defaultdict(float)
        for t in set(tokenize(query)):
            plist = self.post.get(t)
            if not plist:
                continue
            idf = math.log(1 + (self.N - len(plist) + 0.5) / (len(plist) + 0.5))
            for i, n in plist:
                if allowed is not None and i not in allowed:
                    continue
                scores[i] += idf * n * (self.k1 + 1) / (n + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
        return sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:k]
