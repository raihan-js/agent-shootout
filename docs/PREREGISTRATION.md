# Pre-registration: what the shootout will be judged on, written before the test split is run

Written 2026-10-06. The git history timestamps this file; the report must quote this commit and list every deviation. Everything is about **synthetic questions generated from statute headings**,
**one local 9B model**, **one frozen prompt set** and **one run**. Nothing here measures legal accuracy.

## What was and was not looked at before this was written

- **Looked at:** the 36 development questions, run three times (prompts v1, prompts v2, and a repeat of v2), all four architectures each time; all prompt work is in `docs/TUNING.md`.
- **Looked at, with no agent:** the registry (article counts, deleted articles, caption uniqueness) and a retrieval statistic for the search index: for 600 sampled anchor articles the raw caption as a
  query finds the gold article in the top 5 for 98% of them when captions are indexed and 79% when only the article text is indexed (49% at rank 1, 86% in the top 10). The text-only index was chosen on this
  statistic (a caption index makes the task trivial); no architecture result influenced the choice.
- **Not looked at:** any of the 240 test questions' results.

## Inputs (pinned)

| Input | Pin |
|---|---|
| Registry | `data/registry.json.gz`, sha256 `75e3d4eb5e6b57c2...`; 11 laws, 4,778 main-provision articles from the e-Gov Law API v2 (fetched 2026-10-06; 72 deleted placeholders) |
| Test questions | `data/questions_test.json`, sha256 `c1381b02b2fa21da...`: 120 items x {ja, en} = 240; 40 items per type (topic, neighbour, pair); seed 0; articles disjoint from the dev split |
| Model | Ollama `qwen3.5:9b` (Apache-2.0, Q4_K_M GGUF, sha256 `dec52a44569a2a25...`), served by llama.cpp's server from the Ollama 0.32.15 bundle (build commit 9d77fa172), 4 parallel slots of 16,384 tokens, flash attention, q8_0 KV cache, thinking off (`scripts/serve_llm.sh`) |
| Decoding | temperature 0, seed 0, 400 output tokens per call |
| Prompts | version v2 (`src/shootout/prompts.py`, sha256 `1cc35319e0b15603...`), graphs `src/shootout/graphs.py` (sha256 `755d5f1f182a98c5...`), scoring `src/shootout/scoring.py` (sha256 `90c4b638b2847b52...`) |
| Budget | every architecture, every question: at most 24,000 tokens (prompt + completion) and 20 model calls; agent loops: A 8 iterations, B 4 per step (3 steps max), C 4 per research round (3 rounds max), D 8 for the draft and 5 per revision (2 revisions max) |

## Architectures (same tools, same base prompt, same model)

A **react**: one tool-using loop. B **plan_execute**: planner (up to 3 steps), executor loop per step, synthesizer. C **supervisor**: supervisor routes between a researcher loop and a writer.
D **draft_verify**: a draft (the A loop), a symbolic check of every citation against the registry, up to 2 revisions. D's check uses the same registry as the scoring, so its invented-citation rate is low
by construction; it cannot detect a real but wrong article, and that is part of what is being measured.

## Metrics (per architecture on the 240 test questions; exact Clopper-Pearson 95% intervals for rates)

**Primary**
1. **Correct rate:** the answer cites every gold article and cites no article that does not exist in the law (`correct` in `scoring.py`). Deleted articles count as non-existent.
2. **Cost:** mean tokens per question (prompt + completion), with a percentile bootstrap over questions; and tokens per correct answer (total tokens / number of correct answers).

**Secondary**
3. Invented-citation rate: answers with at least one invented citation, and invented mentions / all mentions.
4. Precise rate: correct and no citation beyond the gold articles and the anchor of a neighbour question (cross-references quoted from article text count as extra).
5. Not-answered rate (budget exhausted, server error, no answer), runs that used no tool, runs with a failed tool call, model calls and tool calls per question, p50 and p95 latency.
6. Share of wrong answers that cite a real but wrong article (as opposed to an invented one or none).
7. Breakdown by question type and by language; per-node token breakdown (where each design spends its tokens). Subgroups are descriptive: 40 items per type per language per architecture.
8. Unsupported quotes: quoted passages of 6+ characters that do not occur in any cited article's text.

**Paired comparisons:** every pair of architectures on `correct`, by question, exact McNemar; six pairs, so the threshold is 0.05 / 6 = 0.0083. A design is called better than another only if it clears this
threshold; otherwise the report says "no detectable difference". A design **dominates** another if it has no worse correct rate (no detectable difference) and a lower mean cost with non-overlapping bootstrap intervals.

**Noise floor:** the dev set was run twice under identical settings (`results/runs/dev2` and `results/runs/dev3_repeat`). Batched generation at temperature 0 is not exactly repeatable, so the report quotes how many
questions change correctness between the two runs, per architecture, and reads test differences against it.

## Hypotheses, stated in advance (the first three come from the dev results)

- **H1.** Correct rates are close: all four within 10 points of each other, and no pair clears the 0.0083 threshold.
- **H2.** Cost separates the designs even when accuracy does not: mean tokens per question ordered A < D < C < B, with B at least twice A. The supervisor (C) costs more than ReAct (A) without a higher correct rate.
- **H3.** Invented citations are rare (under 5% of answers for every design) and most wrong answers cite a real but wrong article (over 70% of the wrong ones), so D's verification step does not raise its correct rate above A's.
- **H4 (exploratory).** Pair questions are the hardest type for every design; plan-and-execute (B) is the most likely to help there.
- **H5.** ReAct and draft-verify still skip the tools in a minority of runs (under 25%).

## Out of scope and known limits

- Questions are generated from statute headings, so they are easier and more regular than real legal questions; English questions quote the Japanese heading. This measures grounding and lookup, not legal reasoning.
- One model, one prompt set, one run, one seed. The prompts were tuned on 36 questions with equal effort per design, but a different prompt could change the ranking; the result is about these prompts.
- Citations are attributed to the law named in the question; a model citing another law's article is scored against the question's law. Rates are per answer unless marked per mention.
- Temperature 0 with batched generation is not bit-repeatable; see the noise floor.
- No reviewer or human judgement is involved, and no language-model judge: scoring is symbolic.

## Deviations

The test run itself followed this document: one run, prompts v2, the five pinned inputs unchanged (sha256 re-checked before and after), raw records committed (`d4e4056`) before any analysis. The items below are everything that
differs from, or was added to, what was written above. No number was removed.

1. **Power loss before the test (not a deviation of the test).** The first noise-floor repeat of the dev set was cut short when the PC shut down and the model server died; it was re-run in full with identical settings and the broken attempt is
   kept (`results/runs/dev3_repeat_interrupted`, see `docs/TUNING.md`). The pre-registration commit `956b41c` predates both.
2. **Three react runs ended as `llm_error`** (HTTP 500: the model wrote tool-call arguments that were not valid JSON). They are model failures, count as "not answered" as pre-registered, and were not re-run.
3. **Metrics 3 and 8 and the dominance rule were missing from the first analysis output.** `scripts/analyze.py` computed invented mentions and unsupported quotes but did not print them, and had no dominance table; both were added after the first
   look at the test numbers. The definitions are unchanged and no earlier table value changed.
4. **Metric 8 (unsupported quotes) turned out to measure headings, not fabrication:** the question quotes a statute heading, the answer quotes it back, and a heading is a caption, not article text, so 86% of quoting answers count as
   "unsupported" for every design. The pre-registered number is reported as such and not used to rank designs. A refined version (also accepts the cited articles' captions and the question) is **post-hoc**, in `scripts/posthoc.py`.
5. **Post-hoc, not pre-registered** (`scripts/posthoc.py`, `results/posthoc_test.md`): the refined quote check, where draft-verify's lead over react comes from, pairwise disagreement versus the noise floor, failed article lookups, and whether the gold article was ever returned by a tool call (replay of the recorded calls) with a paired test on "correct and gold read".
6. **Known limitations found after the run, not fixed:** (a) `correct` is a citation check: some correct answers (about 8% to 9% for react, supervisor and draft-verify) cite a gold article that no tool call ever returned and describe it wrongly (post-hoc check 5); (b) the article tool accepts canonical ids (541, 415-2) only; spellings such as 61条の2 or 250の6 return "no such article" for articles that exist. 11 of plan-execute's 34 failed lookups and 2 of
   the supervisor's 7 were of this kind (0 for react and draft-verify). The tool is identical for all four designs and was not changed.
