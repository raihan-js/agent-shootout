import pytest

from shootout import metrics


def rec(i, correct=True, invalid=(), tokens=1000, status="answered", extra=(), quotes=0, unsupported=0, tool_failures=0):
    return {"id": i, "type": "topic", "language": "ja", "status": status,
            "score": {"correct": correct, "gold_hit": correct, "invalid": list(invalid), "cited": ["1"] + list(invalid), "no_citation": False, "extra": list(extra),
                      "quotes": quotes, "quotes_unsupported": unsupported},
            "run": {"tokens": tokens, "llm_calls": 3, "tool_calls": 2, "latency_s": 5.0, "tool_failures": tool_failures}}


def test_rate_intervals_at_the_edges():
    r = metrics.rate([False] * 50)
    assert (r["k"], r["n"], r["lo"]) == (0, 50, 0.0) and 0.05 < r["hi"] < 0.08
    assert metrics.rate([True] * 10)["hi"] == 1.0 and metrics.rate([])["rate"] is None


def test_summary_counts_and_cost():
    s = metrics.summarise([rec("a"), rec("b", correct=False, invalid=["99"]), rec("c", status="budget_exhausted", correct=False, tokens=3000)])
    assert s["correct"]["k"] == 1 and s["invented"]["k"] == 1 and s["invented_mentions"] == {"k": 1, "n": 4} and s["not_answered"]["k"] == 1
    assert s["tokens"]["mean"] == pytest.approx(5000 / 3) and s["tokens_per_correct"] == 5000 and s["statuses"] == {"answered": 2, "budget_exhausted": 1}


def test_unsupported_quote_rate_only_counts_answers_with_quotes():
    s = metrics.summarise([rec("a"), rec("b", quotes=2, unsupported=1), rec("c", quotes=1, unsupported=0)])
    assert (s["unsupported_quote"]["k"], s["unsupported_quote"]["n"]) == (1, 2)


def test_paired_mcnemar():
    a = [rec(str(i), correct=True) for i in range(10)]
    b = [rec(str(i), correct=False) for i in range(10)]
    p = metrics.paired(a, b, lambda r: r["score"]["correct"])
    assert (p["only_a"], p["only_b"]) == (10, 0) and p["p"] == pytest.approx(2 * 0.5 ** 10)
    assert metrics.paired(a, a, lambda r: r["score"]["correct"])["p"] == 1.0
