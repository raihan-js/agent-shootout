# I Pre-Registered a Four-Way LangGraph Shootout. Plan-and-Execute Cost 2.3x and Bought Nothing I Could Detect

*Four agent designs, the same 240 questions about Japanese statutes, the same local 9B model and the same token budget. The cheapest designs were as accurate as the expensive ones, and my own scoring turned out to be weaker than I thought.*

---

![Agent Shootout results](https://raw.githubusercontent.com/raihan-js/agent-shootout/HEAD/images/agent-shootout.png)

> Scope note: everything here is measured on **synthetic questions** generated from statute headings (11 Japanese laws, 4,778 articles from the e-Gov Law API), with **one local model** (qwen3.5 9B, Q4_K_M, temperature 0), **one prompt set** and **one run** of the test split. "Correct" means the answer cites every gold article and no article that does not exist. It is a citation check, not a check that the answer is right. This says nothing about legal accuracy and is not legal advice.

## What I built

Everyone has an opinion on whether an agent needs a planner, a supervisor or a verifier. I wanted a number, so I built four designs in LangGraph and held everything else fixed: the same three tools (`search_articles`, `get_article`, `verify_citation`), the same base prompt, the same model, and the same budget of 24,000 tokens and 20 model calls per question.

- **A, ReAct:** one model-and-tools loop.
- **B, plan-and-execute:** a planner writes up to three steps, an executor loop runs each, a synthesiser writes the answer.
- **C, supervisor:** a supervisor routes between a researcher loop and a writer.
- **D, draft-verify:** a draft (the ReAct loop), then a symbolic check of every citation against the registry, then up to two revisions.

The questions do not name the article ("which article comes right after the one on X?"), so search matters. There are three types (topic, neighbour, pair), asked in Japanese and English, 120 items and 240 questions in all. Scoring is symbolic, with no language-model judge anywhere: a citation extractor, an existence check against the registry, and gold articles known from the registry.

## I wrote down how I would judge it first

Before running the test split I committed a pre-registration: the inputs with their hashes, the metrics, the paired test (exact McNemar by question, with a threshold of 0.05 / 6 = 0.0083 for six pairs), and five hypotheses. The prompts were tuned on 36 separate dev questions, with the same number of rounds for every design and no change made for one design only. I also ran the dev set twice under identical settings to measure the noise floor: the same design on the same 36 questions changed correctness on 1 to 5 of them, and gave identical answer text on only 2 to 5.

The first draft of that repeat was destroyed by a power cut: the model server died and 14 to 16 questions per design were written as instant connection errors. I kept the broken run, re-ran the repeat in full, and re-checked the hashes of every pinned file before touching the test split.

## The result

| 240 questions per design | ReAct | Plan-execute | Supervisor | Draft-verify |
|---|---|---|---|---|
| **Correct** | 59.6% [53.1, 65.8] | 61.7% [55.2, 67.8] | 65.0% [58.6, 71.0] | 63.7% [57.3, 69.8] |
| **Mean tokens per question** | 4,663 | 10,535 | 7,494 | 4,905 |
| Tokens per correct answer | 7,826 | 17,084 | 11,530 | 7,694 |
| Latency p50 (s) | 14 | 40 | 31 | 16 |

No pair of designs clears the threshold on correctness; the smallest p is 0.0525. Cost does separate them: plain ReAct and draft-verify each have a lower mean cost than plan-and-execute and the supervisor, with non-overlapping bootstrap intervals, and no detectably worse accuracy. Plan-and-execute is dominated by all three of the others. The extra tokens are tool-loop turns (more searches and article reads, each re-sending the growing context), not planning text: 90% of its tokens are in the executor loops.

Four of the five hypotheses held as written (all four within 10 points, cost ordered A < D < C < B with B at least twice A, invented citations under 5%, ReAct and draft-verify skipping the tools in under 25% of runs). One half-held: I expected plan-and-execute to help on pair questions, the hardest type for every design, and it did not stand out (39 of 80, the same as the supervisor).

That is also a statement about power. With the designs disagreeing on 9% to 23% of questions, a pair needed a gap of about 6 to 9 points to be called different. A real five-point lead for the supervisor (p = 0.085) is neither shown nor ruled out.

## The part that looked like a win

Draft-verify was ahead of ReAct by 10 questions (16 only it got right, 6 only ReAct). That looks like verification paying off. I checked: in 5 of those 16, ReAct had an invented citation, and in 1 it did not answer. Removing an invented citation is exactly what the verifier does, using the same registry the scoring uses, so its low invented rate (0.4%) is a property of the setup, not an achievement. The remaining 10 are questions where ReAct cited real articles and missed a gold one, which the verifier cannot see. Neither design is distinguishable from the other, and their disagreement (22 of 240 questions) is about the size of one design's own run-to-run noise.

## "Correct" is a citation check

The first record I printed from the flat results table was this. The question asked for the article after 民法 730; ReAct answered 731, which is right, and said it covers the end of a duty of support. Article 731 is the minimum marriage age. The model had only seen article 730 in its search results and guessed the next number.

Because the tools are deterministic, I replayed every recorded tool call and asked whether each gold article was ever actually returned to the model. For 91% to 99% of the correct answers it was. For the rest (13 of ReAct's 143, 12 of the supervisor's 156, 14 of draft-verify's 153, and 1 of plan-and-execute's 148) it was not: the right number, over made-up content. No metric in this study checks what an answer says about an article it cites correctly. On "correct and the gold article was read" the paired tests still clear nothing (smallest p = 0.036), so the conclusions stand, but the number I am most careful about is the one that says "correct".

## Things that went wrong

- **A scoring bug that looked like a model result.** The first dev scores used a pattern that needed `第740条`; the model writes `第 740 条` and `民法709条`. 28 answers scored as "no citation". Fixed with tests; the stored runs were re-scored from their text.
- **A bug in my earlier project's extractor,** found while writing this scoring: the prefix of every branch citation (第二条の二) counted as a second, phantom citation. I re-scored all 1,800 published responses of that project and corrected its numbers.
- **A metric that measured headings.** The pre-registered "unsupported quote" rate is 86% to 90% for every design, because answers quote the statute heading from the question and a heading is a caption, not article text. I report it and do not use it.
- **A picky tool.** `get_article` accepts `415-2` but not `415条の2` or `250の6`, and says "no such article" for articles that exist. 11 of plan-and-execute's 34 failed lookups were of this kind. The tool was identical for all four designs and I did not change it after the pre-registration.

## What this does not show

- That any design is better for real legal research. The questions are regular, English questions quote the Japanese heading, and "correct" is a citation check.
- That the order holds for another model, another prompt set or another budget. I tuned prompts on 36 questions with equal effort per design; different prompts could reorder them.
- Anything about differences under 6 to 9 points.

The code, the pre-registration, the report, the post-hoc analysis (labelled as such) and every per-question record are public: [github.com/raihan-js/agent-shootout](https://github.com/raihan-js/agent-shootout) and the [Hugging Face dataset](https://huggingface.co/datasets/raihan-js/agent-shootout).
