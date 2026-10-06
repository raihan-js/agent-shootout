# Tuning log (development split only)

Prompts and settings were adjusted on the **36 development questions** (18 items x ja/en, 6 per type; articles disjoint from the test split). The test split was not run until the pre-registration was committed.
Protocol: one shared base prompt for all four architectures, and the same number of revision rounds for each design; a change had to be motivated by a failure seen in the dev records, and no
change was made for one architecture only. Everything below is on n = 36 per architecture, so the intervals are wide (about +/- 16 points) and these tables guide prompt work, they do not rank designs.

## Round 1: prompts v1 (`docs/prompts_v1.py.txt`)

| | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| correct | 15/36 (41.7%) | 19/36 (52.8%) | 21/36 (58.3%) | 16/36 (44.4%) |
| correct, Japanese / English | 22.2% / 61.1% | 50.0% / 55.6% | 50.0% / 66.7% | 27.8% / 61.1% |
| runs that used no tool | 41.7% (83% of the Japanese ones) | 0% | 0% | 38.9% |
| tokens per question (mean) | 3,348 | 11,109 | 8,092 | 3,634 |

Observations that drove round 2: ReAct and draft-verify often answered **from memory without calling a tool** (and cited the wrong article); the structured designs always used tools. 15 to 19 of every
design's wrong answers were a real but wrong article, not an invented one.

**A scoring bug found here, not a model result.** The first dev scores were computed with a citation pattern that needed `第740条` contiguous; the model writes `第 740 条` (spaces) and `民法709条`
(no 第). 28 plan-execute and supervisor records scored as "no citation" although they cited correctly. The extractor now accepts both forms (tests in `tests/test_scoring.py`); the stored runs were
re-scored from their answer text (`scripts/rescore_runs.py`), no model was re-run. The table above is the re-scored one.

## Round 2: prompts v2 (the current `src/shootout/prompts.py`)

One change to the shared base prompt: "ALWAYS use the tools before answering, even if you think you know the article: article numbers recalled from memory are often wrong. Never cite an article you have
not opened with get_article", plus "if the question is about two topics, find each of them separately" and "if no candidate matches, search again with different words". Planner, supervisor, synthesizer,
writer and revise prompts are unchanged from v1.

| | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| correct | 21/36 (58.3%) | 22/36 (61.1%) | 21/36 (58.3%) | 21/36 (58.3%) |
| correct, Japanese / English | 55.6% / 61.1% | 61.1% / 61.1% | 55.6% / 61.1% | 55.6% / 61.1% |
| runs that used no tool | 16.7% | 0% | 0% | 16.7% |
| answers with an invented citation | 2 | 0 | 0 | 0 |
| tokens per question (mean) | 3,842 | 10,785 | 7,794 | 4,069 |
| budget exhausted (24k tokens) | 0 | 1 | 1 | 0 |

Prompts are frozen at v2. A repeat of the dev set under identical settings (`results/runs/dev3_repeat`) measures the run-to-run noise floor.

**The first repeat attempt was cut short by a power loss** (the PC shut down mid-run): 14 to 16 questions per design had been written as `llm_error` (connection refused, about 5 ms each) after the model server died. That partial run is kept
unedited in `results/runs/dev3_repeat_interrupted` and is not used for anything. The repeat was re-run in full from scratch after the server was restarted with the same script and settings. No prompt, graph or scoring file changed
(sha256 of all five pinned inputs re-checked against `docs/PREREGISTRATION.md` after the restart: all match).

## Settings that were fixed before any run and not tuned

Search index over article text only (captions not indexed; chosen on a retrieval statistic that involves no agent: raw caption query recall@5 is 0.98 with captions indexed and 0.79 without, see the
pre-registration); tool output cut at 900 characters; temperature 0, seed 0, 400 output tokens per call, thinking off; budget 24,000 tokens and 20 calls per question for every design.
