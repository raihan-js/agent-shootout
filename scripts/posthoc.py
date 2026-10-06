#!/usr/bin/env python3
"""POST-HOC checks on the test run, written after the pre-registered analysis had been read. Nothing here was pre-registered; every number is labelled as post-hoc in the report.

  posthoc.py results/runs/test           writes results/posthoc_test.json and .md

1. Refined quote check: pre-registered metric 8 counts a 「…」 passage as unsupported when it is not in a cited article's text; most such passages are statute HEADINGS (the question quotes
   the heading and the answer quotes it back), so here a quote also counts as supported if it occurs in the question or in a cited article's caption.
2. Why draft-verify is ahead of react by 10 questions: how many of the questions where only D is correct are ones where react had an invented citation (what D's verifier removes by design).
3. Discordance versus the dev noise floor: share of questions on which two designs disagree about `correct`.
4. Failed article lookups: how many failures were a real article written in a form the tool does not accept (e.g. 61条の2, 250の6), per design, and how often a run with such a failure was correct.
5. Grounding of the correct answers: the tools are deterministic, so the recorded calls are replayed against the registry and a gold article counts as READ if some call returned its own entry (a
   search hit with its snippet, or get_article on it). A pointer in another article ("next article id: 731") does not count: the model then knows the number but has not seen the text.
"""
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from shootout import registry, runner  # noqa: E402
from shootout.graphs import ARCHITECTURES  # noqa: E402
from shootout.metrics import paired, rate  # noqa: E402
from shootout.scoring import _QUOTE, _norm, cited_ids  # noqa: E402
from shootout.tools import LawTools  # noqa: E402

LABEL = {"react": "A react", "plan_execute": "B plan-execute", "supervisor": "C supervisor", "draft_verify": "D draft-verify"}
KANJI = r"[零一二三四五六七八九十百千]+"


def equivalent_forms(article):
    """Other spellings of the same article number a person would call equivalent: 61条の2 / 250の6 / 千二十六."""
    out = {article.replace("の", "-").replace("条-", "-").replace("条", "").replace("第", "").replace(" ", "")}
    if re.fullmatch(rf"{KANJI}(の{KANJI}|の\d+)*", article):
        out.update(cited_ids("第" + article + "条"))
    return out


def main():
    d = Path(sys.argv[1])
    runs = runner.load_runs(d, ARCHITECTURES)
    qmap = {q["id"]: q for q in json.loads((ROOT / "data/questions_test.json").read_text())}
    lt = LawTools(registry.load(ROOT / "data/registry.json.gz"))
    res, md = {}, ["# Post-hoc checks on the test run (not pre-registered)", ""]

    # 1 refined quote check
    res["refined_quotes"], rows = {}, []
    for arch, recs in runs.items():
        flags, quoters = [], 0
        for r in recs:
            quotes = _QUOTE.findall(r["answer"])
            if not quotes:
                continue
            quoters += 1
            arts = lt.laws[r["law"]]["articles"]
            valid = [c for c in r["score"]["cited"] if c not in r["score"]["invalid"]]
            pool = [_norm(arts[lt.by_id[r["law"]][c]]["text"]) for c in valid] + [_norm(arts[lt.by_id[r["law"]][c]]["caption"] or "") for c in valid] + [_norm(qmap[r["id"]]["question"])]
            flags.append(any(not any(_norm(x) in p for p in pool if p) for x in quotes))
        res["refined_quotes"][arch] = rate(flags)
        v = res["refined_quotes"][arch]
        rows.append(f"| {LABEL[arch]} | {v['k']}/{v['n']} ({100 * v['rate']:.1f}%) [{100 * v['lo']:.1f}, {100 * v['hi']:.1f}] |")
    md += ["## 1. Answers with a quote that is in none of: the cited articles' text, their captions, the question", "", "| | answers with such a quote / answers that quote |", "|---|---|", *rows, ""]

    # 2 D vs A mechanism
    A, D = {r["id"]: r for r in runs["react"]}, {r["id"]: r for r in runs["draft_verify"]}
    only_d = [i for i in A if D[i]["score"]["correct"] and not A[i]["score"]["correct"]]
    only_a = [i for i in A if A[i]["score"]["correct"] and not D[i]["score"]["correct"]]
    res["d_vs_a"] = {"only_d": len(only_d), "only_d_a_invented": sum(bool(A[i]["score"]["invalid"]) for i in only_d), "only_d_a_not_answered": sum(A[i]["status"] != "answered" for i in only_d),
                     "only_a": len(only_a), "only_a_d_invented": sum(bool(D[i]["score"]["invalid"]) for i in only_a)}
    v = res["d_vs_a"]
    md += ["## 2. Where draft-verify beats react", "",
           f"Questions where only D is correct: {v['only_d']}; in {v['only_d_a_invented']} of them react's answer had an invented citation and in {v['only_d_a_not_answered']} react did not answer (budget or server error). "
           f"Questions where only A is correct: {v['only_a']} ({v['only_a_d_invented']} with an invented citation in D). The other {v['only_d'] - v['only_d_a_invented'] - v['only_d_a_not_answered']} questions where only D is correct are ones where "
           "react answered with no invented citation but missed a gold article.", ""]

    # 3 discordance vs noise
    res["discordance"], rows = {}, []
    for p, q in itertools.combinations(runs, 2):
        v = paired(runs[p], runs[q], lambda r: r["score"]["correct"])
        res["discordance"][f"{p} vs {q}"] = (v["only_a"] + v["only_b"]) / v["n"]
        rows.append(f"| {LABEL[p]} vs {LABEL[q]} | {v['only_a'] + v['only_b']}/{v['n']} ({100 * (v['only_a'] + v['only_b']) / v['n']:.1f}%) |")
    md += ["## 3. Share of questions on which two designs disagree about `correct` (test, n = 240)", "", "| pair | disagree |", "|---|---|", *rows, "",
           "For scale, the same design run twice on the 36 dev questions changed correctness on 4 (react), 1 (plan-execute), 2 (supervisor) and 5 (draft-verify) of 36 (3 to 14%); see the pre-registered noise-floor table.", ""]

    # 4 failed lookups
    res["lookups"], rows = {}, []
    for arch, recs in runs.items():
        calls = failed = fmt = 0
        fmt_runs, fmt_correct = set(), 0
        for r in recs:
            for t in r["tools"]:
                if t["name"] not in ("get_article", "verify_citation"):
                    continue
                calls += 1
                if not t["ok"]:
                    failed += 1
                    if any(lt.exists(t["args"]["law"], x) for x in equivalent_forms(t["args"]["article"])):
                        fmt += 1
                        if r["id"] not in fmt_runs:
                            fmt_runs.add(r["id"])
                            fmt_correct += bool(r["score"]["correct"])
        res["lookups"][arch] = {"calls": calls, "failed": failed, "failed_real_article_other_spelling": fmt, "runs_with_such_failure": len(fmt_runs), "of_which_correct": fmt_correct}
        rows.append(f"| {LABEL[arch]} | {calls} | {failed} ({100 * failed / calls:.1f}%) | {fmt} | {len(fmt_runs)} ({fmt_correct} correct) |")
    md += ["## 4. Failed article lookups (get_article / verify_citation)", "", "| | lookups | failed | failed although the article exists under another spelling | runs with such a failure |", "|---|---|---|---|---|", *rows, "",
           "The tool accepts canonical ids (541, 415-2); a model that writes 61条の2 or 250の6 is told the article does not exist. The tool is the same for every design and was not changed after the pre-registration.", ""]


    # 5 grounding of correct answers (replay of the recorded tool calls)
    def read_ids(r):
        law, got = r["law"], set()
        for t in r["tools"]:
            a = t["args"]
            if t["name"] == "search_articles":
                out = lt.search(a.get("query", ""), a.get("law", ""), a.get("top_k", 5))
                for line in out.splitlines():
                    m = re.search(r"\d+\. (\S+) .*?\(id ([^)]+)\)", line)
                    if m and m.group(1) == law:
                        got.add(m.group(2))
            elif t["name"] == "get_article" and t["ok"] and lt.law_title(a.get("law", "")) == law:
                m = re.match(r"\S+ .*?\(id ([^)]+)\)", lt.get(a["law"], a["article"]))
                if m:
                    got.add(m.group(1))
        return got

    res["grounding"], rows = {}, []
    for arch, recs in runs.items():
        corr = [r for r in recs if r["score"]["correct"]]
        grounded = [r for r in corr if set(r["gold"]) <= read_ids(r)]
        by_type = {ty: (sum(set(r["gold"]) <= read_ids(r) for r in corr if r["type"] == ty), sum(r["type"] == ty for r in corr)) for ty in ("topic", "neighbour", "pair")}
        res["grounding"][arch] = {"correct": len(corr), "gold_read": len(grounded), "grounded_correct_rate_of_all": rate([r["score"]["correct"] and set(r["gold"]) <= read_ids(r) for r in recs]), "by_type": by_type}
        g = res["grounding"][arch]["grounded_correct_rate_of_all"]
        rows.append(f"| {LABEL[arch]} | {len(grounded)}/{len(corr)} ({100 * len(grounded) / len(corr):.1f}%) | " + " | ".join(f"{a}/{b}" for a, b in by_type.values()) +
                    f" | {100 * g['rate']:.1f}% [{100 * g['lo']:.1f}, {100 * g['hi']:.1f}] ({g['k']}/{g['n']}) |")
    flag = {a: {r["id"]: bool(r["score"]["correct"] and set(r["gold"]) <= read_ids(r)) for r in recs} for a, recs in runs.items()}
    res["grounding_paired"], prow = {}, []
    for p, q in itertools.combinations(runs, 2):
        ra = [dict(r, score={**r["score"], "correct": flag[p][r["id"]]}) for r in runs[p]]
        rb = [dict(r, score={**r["score"], "correct": flag[q][r["id"]]}) for r in runs[q]]
        v = paired(ra, rb, lambda r: r["score"]["correct"])
        res["grounding_paired"][f"{p} vs {q}"] = v
        prow.append(f"| {LABEL[p]} vs {LABEL[q]} | {v['a']} | {v['b']} | {v['only_a']} | {v['only_b']} | {v['p']:.3g} |")
    md += ["## 5. Did the model read the gold article? (correct answers only; replay of the recorded tool calls)", "",
           "| | correct answers where every gold article was returned by a tool call | topic | neighbour | pair | correct AND gold read, of all 240 |", "|---|---|---|---|---|---|", *rows, "",
           "A search hit shows the start of the article text; get_article shows all of it. A pointer in a neighbouring article does not count as reading. A correct answer that never read its gold article got the number from a guess or from arithmetic "
           "(the next article after 730 is usually 731) and has not seen the text it summarises. Example: `test063-ja`, react, cites 民法 731 as the article after 730 and summarises it as a rule about the end of a duty of support; 731 is the minimum marriage age.", "",
           "Paired comparison on `correct AND gold read` (exact McNemar, post-hoc, six pairs so the same 0.0083 threshold is the fair reading):", "",
           "| pair | first | second | only first | only second | p |", "|---|---|---|---|---|---|", *prow, ""]

    (ROOT / "results/posthoc_test.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "results/posthoc_test.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
