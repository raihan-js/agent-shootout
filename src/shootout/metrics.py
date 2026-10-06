"""Aggregate metrics over run records. Rates carry exact Clopper-Pearson 95% intervals; costs are means with a percentile bootstrap over questions; comparisons between
architectures are paired by question (exact McNemar for yes/no outcomes)."""
from collections import Counter

import numpy as np
from scipy.stats import beta, binomtest


def rate(flags):
    flags = [bool(f) for f in flags]
    n, k = len(flags), sum(flags)
    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return {"k": k, "n": n, "rate": k / n if n else None, "lo": lo if n else None, "hi": hi if n else None}


def mean_ci(values, n_boot=2000, seed=0):
    v = np.asarray(values, dtype=float)
    if not len(v):
        return {"mean": None, "lo": None, "hi": None}
    means = v[np.random.default_rng(seed).integers(0, len(v), size=(n_boot, len(v)))].mean(axis=1)
    return {"mean": float(v.mean()), "lo": float(np.quantile(means, 0.025)), "hi": float(np.quantile(means, 0.975))}


def fmt(r):
    return "-" if r["rate"] is None else f"{100 * r['rate']:.1f}% [{100 * r['lo']:.1f}, {100 * r['hi']:.1f}] ({r['k']}/{r['n']})"


def summarise(recs):
    correct = [r["score"]["correct"] for r in recs]
    tokens = [r["run"]["tokens"] for r in recs]
    n_correct = sum(bool(c) for c in correct)
    return {
        "n": len(recs),
        "correct": rate(correct),
        "gold_hit": rate([r["score"]["gold_hit"] for r in recs]),
        "invented": rate([bool(r["score"]["invalid"]) for r in recs]),                       # answers containing at least one invented citation
        "invented_mentions": {"k": sum(len(r["score"]["invalid"]) for r in recs), "n": sum(len(r["score"]["cited"]) for r in recs)},
        "no_citation": rate([r["score"]["no_citation"] for r in recs]),
        "precise": rate([r["score"]["correct"] and not r["score"]["extra"] for r in recs]),               # correct AND nothing cited beyond gold / anchor
        "extra_citation": rate([bool(r["score"]["extra"]) for r in recs]),
        "no_tool_runs": rate([r["run"]["tool_calls"] == 0 for r in recs]),                                 # answered without opening or searching anything
        "unsupported_quote": rate([r["score"]["quotes_unsupported"] > 0 for r in recs if r["score"]["quotes"]]),
        "not_answered": rate([r["status"] != "answered" for r in recs]),
        "tool_failure_runs": rate([r["run"]["tool_failures"] > 0 for r in recs]),
        "tokens": mean_ci(tokens), "llm_calls": mean_ci([r["run"]["llm_calls"] for r in recs]), "tool_calls": mean_ci([r["run"]["tool_calls"] for r in recs]),
        "latency_s": mean_ci([r["run"]["latency_s"] for r in recs]),
        "latency_p50": float(np.median([r["run"]["latency_s"] for r in recs])) if recs else None,
        "latency_p95": float(np.quantile([r["run"]["latency_s"] for r in recs], 0.95)) if recs else None,
        "tokens_per_correct": (sum(tokens) / n_correct) if n_correct else None,
        "statuses": dict(Counter(r["status"] for r in recs)),
    }


def paired(recs_a, recs_b, flag):
    """Exact McNemar on a yes/no outcome per question: counts of questions where only A / only B has the outcome."""
    a, b = {r["id"]: bool(flag(r)) for r in recs_a}, {r["id"]: bool(flag(r)) for r in recs_b}
    ids = sorted(set(a) & set(b))
    only_a, only_b = sum(a[i] and not b[i] for i in ids), sum(b[i] and not a[i] for i in ids)
    d = only_a + only_b
    return {"n": len(ids), "a": sum(a[i] for i in ids), "b": sum(b[i] for i in ids), "only_a": only_a, "only_b": only_b, "p": binomtest(min(only_a, only_b), d, 0.5).pvalue if d else 1.0}


def by(recs, key):
    groups = {}
    for r in recs:
        groups.setdefault(r[key], []).append(r)
    return {k: summarise(v) for k, v in sorted(groups.items())}
