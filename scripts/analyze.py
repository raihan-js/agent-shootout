#!/usr/bin/env python3
"""All tables of the report from the run records. Pre-registered analysis (docs/PREREGISTRATION.md); writes results/analysis_<name>.json and .md.

  analyze.py results/runs/test --name test [--noise results/runs/dev2 results/runs/dev3_repeat]
"""
import argparse
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from shootout import metrics, runner  # noqa: E402
from shootout.graphs import ARCHITECTURES  # noqa: E402

LABEL = {"react": "A react", "plan_execute": "B plan-execute", "supervisor": "C supervisor", "draft_verify": "D draft-verify"}
correct = lambda r: r["score"]["correct"]


def wrong_kind(r):
    s = r["score"]
    if r["status"] != "answered":
        return "not answered"
    return "no citation" if s["no_citation"] else "invented" if s["invalid"] else "real but wrong article"


def noise(dirs):
    a, b = (runner.load_runs(d, ARCHITECTURES) for d in dirs)
    out = {}
    for arch in ARCHITECTURES:
        A, B = {r["id"]: r for r in a[arch]}, {r["id"]: r for r in b[arch]}
        ids = sorted(set(A) & set(B))
        rw = sum(correct(A[i]) and not correct(B[i]) for i in ids)
        wr = sum(correct(B[i]) and not correct(A[i]) for i in ids)
        same_answer = sum(A[i]["answer"] == B[i]["answer"] for i in ids)
        out[arch] = {"n": len(ids), "right_to_wrong": rw, "wrong_to_right": wr, "changed": rw + wr, "identical_answers": same_answer,
                     "correct_run1": sum(correct(A[i]) for i in ids), "correct_run2": sum(correct(B[i]) for i in ids),
                     "tokens_run1": sum(A[i]["run"]["tokens"] for i in ids) / len(ids), "tokens_run2": sum(B[i]["run"]["tokens"] for i in ids) / len(ids)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--name", required=True)
    ap.add_argument("--noise", nargs=2)
    a = ap.parse_args()
    runs = runner.load_runs(a.dir, ARCHITECTURES)
    archs = [x for x in ARCHITECTURES if x in runs]
    res = {"name": a.name, "n": {x: len(runs[x]) for x in archs}, "summary": {x: metrics.summarise(runs[x]) for x in archs}}
    res["by_type"] = {x: metrics.by(runs[x], "type") for x in archs}
    res["by_language"] = {x: metrics.by(runs[x], "language") for x in archs}
    res["paired_correct"] = {f"{p} vs {q}": metrics.paired(runs[p], runs[q], correct) for p, q in itertools.combinations(archs, 2)}
    res["paired_invented"] = {f"{p} vs {q}": metrics.paired(runs[p], runs[q], lambda r: bool(r["score"]["invalid"])) for p, q in itertools.combinations(archs, 2)}
    res["wrong_kinds"] = {x: dict(Counter(wrong_kind(r) for r in runs[x] if not correct(r))) for x in archs}
    node_tokens = {}
    for x in archs:
        t = defaultdict(int)
        for r in runs[x]:
            for c in r["calls"]:
                t[c["node"]] += c["in"] + c["out"]
        tot = sum(t.values())
        node_tokens[x] = {k: {"tokens_per_question": v / len(runs[x]), "share": v / tot} for k, v in sorted(t.items(), key=lambda kv: -kv[1])}
    res["node_tokens"] = node_tokens
    if a.noise:
        res["noise_floor"] = noise(a.noise)
    Path(ROOT / f"results/analysis_{a.name}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")

    S, md = res["summary"], []
    md += [f"## {a.name}: main comparison (n = {max(res['n'].values())} questions per architecture)", "",
           "| | " + " | ".join(LABEL[x] for x in archs) + " |", "|---|" + "---|" * len(archs)]
    rows = [("Correct (gold cited, nothing invented)", lambda s: metrics.fmt(s["correct"])), ("Precise (also nothing extra cited)", lambda s: metrics.fmt(s["precise"])),
            ("Answers with an invented citation", lambda s: metrics.fmt(s["invented"])),
            ("Invented mentions / all citation mentions", lambda s: f"{s['invented_mentions']['k']}/{s['invented_mentions']['n']} ({100 * s['invented_mentions']['k'] / max(1, s['invented_mentions']['n']):.1f}%)"),
            ("Answers with an unsupported quote (of answers that quote)", lambda s: metrics.fmt(s["unsupported_quote"])),
            ("Gold article(s) cited", lambda s: metrics.fmt(s["gold_hit"])),
            ("Used no tool at all", lambda s: metrics.fmt(s["no_tool_runs"])), ("Not answered (budget, error)", lambda s: metrics.fmt(s["not_answered"])),
            ("Run with a failed tool call", lambda s: metrics.fmt(s["tool_failure_runs"])),
            ("Tokens per question, mean [95% CI]", lambda s: f"{s['tokens']['mean']:,.0f} [{s['tokens']['lo']:,.0f}, {s['tokens']['hi']:,.0f}]"),
            ("Tokens per correct answer", lambda s: f"{s['tokens_per_correct']:,.0f}" if s["tokens_per_correct"] else "-"),
            ("Model calls / tool calls per question", lambda s: f"{s['llm_calls']['mean']:.1f} / {s['tool_calls']['mean']:.1f}"),
            ("Latency p50 / p95 (s, 4 questions in flight)", lambda s: f"{s['latency_p50']:.0f} / {s['latency_p95']:.0f}")]
    for label, f in rows:
        md.append(f"| {label} | " + " | ".join(f(S[x]) for x in archs) + " |")
    md += ["", "Paired comparisons on `correct` (exact McNemar by question; Bonferroni threshold 0.0083 for six pairs):", "", "| Pair | A correct | B correct | only first | only second | p | clears 0.0083 |", "|---|---|---|---|---|---|---|"]
    for k, v in res["paired_correct"].items():
        md.append(f"| {k} | {v['a']} | {v['b']} | {v['only_a']} | {v['only_b']} | {v['p']:.3g} | {'yes' if v['p'] < 0.0083 else 'no'} |")
    # pre-registered dominance rule: P dominates Q if Q is not detectably better on `correct` (pair p >= 0.0083, or P ahead) AND P's mean tokens are lower with non-overlapping bootstrap intervals
    dom = []
    for p in archs:
        for q in archs:
            if p == q:
                continue
            key = f"{p} vs {q}" if f"{p} vs {q}" in res["paired_correct"] else f"{q} vs {p}"
            v = res["paired_correct"][key]
            q_detectably_better = v["p"] < 0.0083 and (v["b"] > v["a"] if key == f"{p} vs {q}" else v["a"] > v["b"])
            cheaper = S[p]["tokens"]["hi"] < S[q]["tokens"]["lo"]
            if cheaper and not q_detectably_better:
                dom.append((p, q))
    res["dominance"] = [f"{p} dominates {q}" for p, q in dom]
    Path(ROOT / f"results/analysis_{a.name}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    md += ["", "Dominance (pre-registered: no detectably worse correct rate at 0.0083, and a lower mean cost with non-overlapping bootstrap intervals):", ""]
    md += [f"- {LABEL[p]} dominates {LABEL[q]}" for p, q in dom] or ["- none"]
    md += ["", "By type and by language (correct rate):", "", "| | " + " | ".join(LABEL[x] for x in archs) + " |", "|---|" + "---|" * len(archs)]
    for key, grp in (("type", res["by_type"]), ("language", res["by_language"])):
        for g in sorted({k for x in archs for k in grp[x]}):
            md.append(f"| {g} | " + " | ".join(f"{100 * grp[x][g]['correct']['rate']:.1f}% ({grp[x][g]['correct']['k']}/{grp[x][g]['correct']['n']})" for x in archs) + " |")
    md += ["", "What the wrong answers are:", "", "| | " + " | ".join(LABEL[x] for x in archs) + " |", "|---|" + "---|" * len(archs)]
    for kind in ("real but wrong article", "invented", "no citation", "not answered"):
        md.append(f"| {kind} | " + " | ".join(str(res["wrong_kinds"][x].get(kind, 0)) for x in archs) + " |")
    md += ["", "Where the tokens go (mean tokens per question, share):", ""]
    for x in archs:
        md.append(f"- **{LABEL[x]}**: " + "; ".join(f"{k} {v['tokens_per_question']:,.0f} ({100 * v['share']:.0f}%)" for k, v in node_tokens[x].items()))
    if a.noise:
        md += ["", f"Noise floor: the same {res['noise_floor'][archs[0]]['n']} questions run twice under identical settings ({a.noise[0]} vs {a.noise[1]}):", "",
               "| | " + " | ".join(LABEL[x] for x in archs) + " |", "|---|" + "---|" * len(archs),
               "| identical answers | " + " | ".join(f"{res['noise_floor'][x]['identical_answers']}/{res['noise_floor'][x]['n']}" for x in archs) + " |",
               "| questions that changed correctness | " + " | ".join(f"{res['noise_floor'][x]['changed']} ({res['noise_floor'][x]['right_to_wrong']} right to wrong, {res['noise_floor'][x]['wrong_to_right']} wrong to right)" for x in archs) + " |",
               "| correct, run 1 / run 2 | " + " | ".join(f"{res['noise_floor'][x]['correct_run1']} / {res['noise_floor'][x]['correct_run2']}" for x in archs) + " |"]
    Path(ROOT / f"results/analysis_{a.name}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
