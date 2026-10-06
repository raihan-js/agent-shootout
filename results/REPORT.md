# Agent Shootout: report

Four LangGraph designs answer the same 240 questions about Japanese statutes with the same tools, the same base prompt, the same model and the same token budget. The protocol, the inputs (with sha256) and five hypotheses were fixed in
[`docs/PREREGISTRATION.md`](../docs/PREREGISTRATION.md), committed as `956b41c` **before** the test split was run; the raw test records are commit `d4e4056`, committed before any analysis. Every number below is
from [`analysis_test.md`](analysis_test.md) / `analysis_test.json` (pre-registered analysis) or [`posthoc_test.md`](posthoc_test.md) (post-hoc, labelled as such).

**Scope, stated once.** Synthetic questions generated from statute headings; one local 9B model (qwen3.5, Q4_K_M, thinking off, temperature 0); one frozen prompt set (v2, tuned on 36 separate dev questions with equal effort per design); one run of the
test split. "Correct" means the answer cites every gold article and cites no article that does not exist in that law. It does not mean the answer is legally right. Nothing here measures legal accuracy.

## The four designs

| | Design | What it adds |
|---|---|---|
| A | **react**: one tool-using loop | nothing: the baseline |
| B | **plan_execute**: planner (up to 3 steps), an executor loop per step, a synthesiser | explicit decomposition |
| C | **supervisor**: a supervisor routes between a researcher loop and a writer (up to 3 rounds) | role separation |
| D | **draft_verify**: a draft (the A loop), a symbolic check of every citation against the registry, up to 2 revisions | verification |

Tools (`search_articles`, `get_article`, `verify_citation`) are the same for all four; every question gets at most 24,000 tokens and 20 model calls whatever the design. D's check uses the same registry as the scoring, so its
invented-citation rate is low **by construction**; it cannot detect a real but wrong article.

## Result

| 240 test questions per design | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| **Correct** | 59.6% [53.1, 65.8] (143) | 61.7% [55.2, 67.8] (148) | 65.0% [58.6, 71.0] (156) | 63.7% [57.3, 69.8] (153) |
| Precise (also nothing extra cited) | 45.0% (108) | 49.6% (119) | 54.6% (131) | 48.3% (116) |
| Answers with an invented citation | 2.9% (7) | 0.8% (2) | 2.9% (7) | 0.4% (1) |
| **Mean tokens per question** [95% bootstrap CI] | 4,663 [4,118, 5,219] | 10,535 [10,101, 10,994] | 7,494 [6,958, 8,049] | 4,905 [4,366, 5,517] |
| Tokens per correct answer | 7,826 | 17,084 | 11,530 | 7,694 |
| Model calls / tool calls per question | 3.0 / 2.9 | 9.1 / 5.1 | 7.5 / 4.3 | 3.1 / 3.0 |
| Latency p50 / p95 (s, 4 questions in flight) | 14 / 31 | 40 / 70 | 31 / 75 | 16 / 38 |
| Not answered (budget or server error) | 2.5% (6) | 1.2% (3) | 0.8% (2) | 0.8% (2) |
| Runs that used no tool | 10.8% (26) | 0% | 0% | 7.1% (17) |

**Paired comparisons on `correct`** (exact McNemar by question; pre-registered threshold 0.05 / 6 = 0.0083): no pair clears it. The smallest p is react vs draft-verify (6 questions only react, 16 only draft-verify, p = 0.0525);
react vs supervisor p = 0.085; every other pair p > 0.26. The test could only have called a pair different if it disagreed by about **6 to 9 points** (the pairs disagree on 9% to 23% of questions; with 22 disagreements a 14-question
lead is needed, with 49 to 55 a 21-question lead).

**Dominance** (pre-registered: no detectably worse correct rate and a lower mean cost with non-overlapping bootstrap intervals): react dominates plan-execute and supervisor; draft-verify dominates plan-execute and supervisor;
supervisor dominates plan-execute. React and draft-verify do not dominate each other. So the two designs that were left standing are the two cheapest, and the most expensive one (B) is dominated by all three others.

## Hypotheses, as pre-registered

| | Prediction | Outcome |
|---|---|---|
| H1 | all four within 10 points; no pair clears 0.0083 | **Held.** Spread 5.4 points (59.6% to 65.0%); smallest p 0.0525. |
| H2 | cost ordered A < D < C < B, B at least twice A; C costs more than A without a higher correct rate | **Held as stated.** 4,663 < 4,905 < 7,494 < 10,535; B/A = 2.26. C costs more than A (intervals do not overlap); its correct rate is 5.4 points higher but not detectably (p = 0.085), which is what "no higher correct rate" meant under the pre-registered rule. A 5-point gap is not excluded. |
| H3 | invented citations under 5% for every design; over 70% of wrong answers cite a real but wrong article; D's check does not raise its correct rate above A's | **Held.** Invented 0.4% to 2.9%. Real-but-wrong share of wrong answers: A 84/97 (86.6%), B 87/92 (94.6%), C 74/84 (88.1%), D 83/87 (95.4%). D (63.7%) is not detectably above A (59.6%), but see post-hoc 2: 6 of the 16 questions only D got right are ones where react invented a citation or did not answer, which is what D's check removes by design. |
| H4 | (exploratory) pair questions hardest for every design; plan-execute most likely to help there | **Half held.** Pair is the hardest type for all four (41.2%, 48.8%, 48.8%, 47.5% against 57.5% to 83.8% for the other types). Plan-execute did **not** stand out on pair: 39/80, the same as the supervisor (39/80), draft-verify 38/80, react 33/80. |
| H5 | react and draft-verify skip the tools in under 25% of runs | **Held.** 10.8% and 7.1%. |

## By type and language (descriptive: 80 questions per type, 120 per language, per design)

| correct | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| topic -> article | 70.0% | 78.8% | 83.8% | 75.0% |
| neighbour ("the article after the one on X") | 67.5% | 57.5% | 62.5% | 68.8% |
| pair (two topics) | 41.2% | 48.8% | 48.8% | 47.5% |
| English question | 65.0% | 63.3% | 68.3% | 65.0% |
| Japanese question | 54.2% | 60.0% | 61.7% | 62.5% |

Plan-execute is the weakest on neighbour questions; the supervisor is the strongest on topic questions; react has the largest Japanese-versus-English gap (10.8 points). None of these subgroup differences was tested.

## Where the cost goes

Mean tokens per question by node: react 98% in the agent loop; plan-execute 90% in the executor loops (9,516 of 10,535), 4% in the synthesiser, 2% in the planner; supervisor 84% in the researcher, 8% in the supervisor's routing calls;
draft-verify 95% in the draft, 3% in revisions. The extra tokens of B and C are tool-loop turns (more searches and article reads, each re-sending the growing context), not planning text.

## Noise floor

The 36 dev questions were run twice under identical settings (`results/runs/dev2`, `results/runs/dev3_repeat`; batched generation at temperature 0 is not exactly repeatable). Identical answer text: 5/36, 5/36, 2/36, 3/36 (A, B, C, D). Questions whose
correctness changed: 4, 1, 2 and 5 of 36 (3% to 14%). The test pairs disagree on 9% to 23% of 240 questions, so part of every disagreement is run-to-run noise, and the draft-verify versus react disagreement (9.2%, 22 questions) is
about the size of one design's own repeat noise (11% for react, 14% for draft-verify on 36 questions). The test split was run once, as pre-registered, so test-time noise was not measured.

## Post-hoc (not pre-registered; `scripts/posthoc.py`)

1. **Unsupported quotes.** The pre-registered metric counts a 「…」 passage as unsupported when it is not in a cited article's text. 86% of quoting answers fail it for every design, because the question quotes a statute heading and the answer
   quotes it back, and a heading is a caption, not article text. The metric measured headings and is not used to rank designs. Counting a quote as supported if it is in the question or in a cited article's caption: react 8/122 answers (6.6%),
   plan-execute 3/19, supervisor 0/17, draft-verify 8/119 (6.7%).
2. **Where draft-verify beats react.** Of the 16 questions only draft-verify got right, react had an invented citation in 5 and did not answer in 1; the other 10 are questions where react cited no invented article but missed a gold one. Only react
   was right on 6 (none with an invented citation in D).
3. **Failed article lookups.** React 2 of 367, draft-verify 2 of 382, supervisor 7 of 616, plan-execute 34 of 822 (4.1%). The tool accepts canonical ids (541, 415-2) only; 11 of plan-execute's failures and 2 of the supervisor's were a
   real article written another way (61条の2, 250の6, 千二十六) and answered "no such article". The tool is identical for all four designs and was not changed after the pre-registration, so this is part of what was measured, and it probably
   cost plan-execute more than the others (5 runs affected, 2 correct).
4. **"Correct" does not mean the answer was grounded.** Replaying the recorded tool calls (the tools are deterministic) shows how often every gold article was actually returned to the model, as a search hit or by `get_article`:
   react 130 of its 143 correct answers (90.9%), plan-execute 147 of 148 (99.3%), supervisor 144 of 156 (92.3%), draft-verify 139 of 153 (90.8%). The rest are almost all neighbour questions ("the article after the one on X"), where the model
   cited the anchor's number plus one without having seen the next article. Example, `test063-ja`, react: the question asks for the article after 民法 730; the answer cites 731 (right) and summarises it as a rule about ending a duty of
   support; article 731 is the minimum marriage age (婚姻適齢), and no tool call ever returned it. So about 8% to 9% of the correct answers of react, supervisor and draft-verify (13 of 143, 12 of 156, 14 of 153) cite the right number over made-up
   content, and **no metric here checks the content of an answer that cites a gold article**. On "correct AND gold read" the rates are react 54.2%, supervisor 60.0%, draft-verify 57.9%, plan-execute 61.3%; the paired tests do not clear
   0.0083 either (smallest p = 0.036, react vs plan-execute; 21 questions only react, 38 only plan-execute).

## What this does not show

- That a correct answer says something true about the article: the score checks which articles are cited, not what is written about them (post-hoc 4).

- That any design is better or worse **for legal research**: questions are generated from headings, so they are more regular than real ones, English questions quote the Japanese heading, and "correct" is a citation check, not an answer check.
- That the ranking holds for another model, another prompt set or another token budget. The prompts were tuned on 36 questions with equal effort per design; a different prompt could change the order.
- Anything about differences below 6 to 9 points. The intervals are 12 to 13 points wide.
- That draft-verify's low invented rate is an achievement: its verifier uses the scoring's own registry.

## Deviations from the pre-registration

Listed in full in `docs/PREREGISTRATION.md` ("Deviations"): a power loss during the dev repeat (re-run in full, broken attempt kept); three react runs ended in HTTP 500 from malformed tool-call JSON and count as not answered; metrics 3 and 8 and the
dominance table were added to the output after the first look at the test numbers (definitions unchanged); metric 8 turned out to measure headings; the tool-spelling limitation above.

## Reproduce

`scripts/serve_llm.sh` (llama.cpp server from the Ollama bundle, 4 slots), then `python scripts/run_test_langsmith.py --out results/runs/test --no-langsmith` and `python scripts/analyze.py results/runs/test --name test --noise results/runs/dev2 results/runs/dev3_repeat`;
`python scripts/posthoc.py results/runs/test`. Re-scoring the committed records needs no model: `python scripts/rescore_runs.py results/runs/test`. LangSmith experiments: see [`langsmith_experiments.md`](langsmith_experiments.md).
