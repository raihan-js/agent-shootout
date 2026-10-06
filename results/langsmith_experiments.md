# LangSmith experiments (test split, run once, 2026-10-06)

Dataset `shootout-test-240-v1` (240 examples: inputs = id, question, law; reference outputs = gold articles, anchor, type, language). One experiment per design; the target function wrote the same record to
`results/runs/test/<design>.jsonl` as it ran, so the JSONL is exactly what LangSmith saw. Evaluators (rule-based, no model): `correct`, `invented`, `gold_hit`, `tokens`; summary evaluators: correct rate, invented rate and gold-hit rate with exact 95% intervals.
Metadata on each experiment: architecture, git commit (`a87241a`), prompts `v2`, model, pointer to the pre-registration.

| Design | Experiment |
|---|---|
| react | `shootout-react-ba2510ac` |
| plan_execute | `shootout-plan_execute-9c577e80` |
| supervisor | `shootout-supervisor-52e18936` |
| draft_verify | `shootout-draft_verify-801ae106` |

The workspace is private, so these names are for the owner's reference; the same per-question data is in this repository (`results/runs/test/`) and in the Hugging Face dataset. The numbers in `analysis_test.md` are computed from the JSONL, not read back from LangSmith.
