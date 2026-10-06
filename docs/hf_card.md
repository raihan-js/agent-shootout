---
license: cc-by-4.0
language:
- ja
- en
pretty_name: Agent Shootout (per-question runs of four LangGraph designs on Japanese-law questions)
tags:
- agents
- langgraph
- evaluation
- japanese
- legal
- citation-grounding
configs:
- config_name: test_runs
  data_files: test_runs_flat.jsonl
  default: true
size_categories:
- n<1K
---

# Agent Shootout: per-question runs

Four LangGraph agent designs (ReAct, plan-and-execute, supervisor, draft-verify) answered the same 240 questions about Japanese statutes with the same tools, base prompt, local model (qwen3.5 9B, Q4_K_M, temperature 0) and token budget (24,000 tokens, 20 model calls). This dataset holds every question, every answer and every score. Code, pre-registration and report: https://github.com/raihan-js/agent-shootout

**Scope.** Synthetic questions generated from statute headings (11 laws, e-Gov Law API v2, fetched 2026-10-06); one model, one prompt set, one run. `correct` means the answer cites every gold article and no article that does not exist in that law: a **citation check, not a check that the answer is right**. Scoring is symbolic; no language model judged anything. Nothing here measures legal accuracy and nothing here is legal advice.

## Files

| File | What |
|---|---|
| `test_runs_flat.jsonl` | 960 rows (4 designs x 240 test questions): question, gold, answer, status, scores, tokens, calls, latency, errors. The viewer table. |
| `runs/test/<design>.jsonl` | the same runs as written by the harness, with every model call (`calls`: node, tokens, ms) and tool call (`tools`: name, arguments, ok) |
| `runs/dev1`, `runs/dev2`, `runs/dev3_repeat` | the 36 development questions, run three times (prompts v1, v2, and a repeat of v2 for the noise floor) |
| `runs/dev3_repeat_interrupted` | the first repeat attempt, cut short by a power loss (about 40% of its records are connection errors); kept unedited, not used |
| `questions_test.json`, `questions_dev.json` | the 240 test and 36 dev questions with gold and anchor articles |
| `analysis_test.json` / `.md`, `posthoc_test.json` / `.md` | the pre-registered analysis and the labelled post-hoc checks |
| `REPORT.md`, `PREREGISTRATION.md` | the write-up and the protocol fixed before the test run |

## Columns of `test_runs_flat.jsonl`

`id`, `architecture` (react, plan_execute, supervisor, draft_verify), `type` (topic, neighbour, pair), `language` (ja, en), `law`, `question`, `gold` and `anchor` (article ids), `answer`, `status` (answered, budget_exhausted, llm_error), `correct`, `gold_hit`, `cited`, `invented` (cited ids that do not exist; deleted articles count), `extra` (real articles that are neither gold nor the anchor), `quotes` / `quotes_unsupported`, `tokens`, `tokens_in`, `tokens_out`, `llm_calls`, `tool_calls`, `tool_failures`, `latency_s` (4 questions in flight), `errors`.

## Headline (240 questions per design)

| | react | plan_execute | supervisor | draft_verify |
|---|---|---|---|---|
| correct | 59.6% | 61.7% | 65.0% | 63.7% |
| mean tokens per question | 4,663 | 10,535 | 7,494 | 4,905 |

No pair of designs differs on `correct` at the pre-registered threshold (0.0083). Read the report before quoting any number: the intervals are 12 to 13 points wide, the noise floor on 36 repeated questions was 1 to 5 flips per design, and a post-hoc replay shows about 8% to 9% of the correct answers of three designs cite a gold article that no tool call ever returned to the model.

## Limits

Heading-generated questions are more regular than real ones; English questions quote the Japanese heading; one 9B model; prompts tuned on 36 separate questions; the article tool accepts canonical ids only (`415-2`, not `415条の2`), which cost plan-and-execute most; the draft-verify design's invented-citation rate is low by construction (its check uses the scoring's registry).

## Licence and provenance

CC-BY-4.0. Statute text excerpts come from the e-Gov Law API v2 (Japanese statutes are not subject to copyright). Answers are outputs of qwen3.5 9B (Apache-2.0). Author: Raihan Sikder (raihan-js).
