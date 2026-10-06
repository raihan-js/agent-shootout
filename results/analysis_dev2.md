## dev2: main comparison (n = 36 questions per architecture)

| | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| Correct (gold cited, nothing invented) | 58.3% [40.8, 74.5] (21/36) | 61.1% [43.5, 76.9] (22/36) | 58.3% [40.8, 74.5] (21/36) | 58.3% [40.8, 74.5] (21/36) |
| Precise (also nothing extra cited) | 44.4% [27.9, 61.9] (16/36) | 41.7% [25.5, 59.2] (15/36) | 33.3% [18.6, 51.0] (12/36) | 41.7% [25.5, 59.2] (15/36) |
| Answers with an invented citation | 5.6% [0.7, 18.7] (2/36) | 0.0% [0.0, 9.7] (0/36) | 0.0% [0.0, 9.7] (0/36) | 0.0% [0.0, 9.7] (0/36) |
| Gold article(s) cited | 61.1% [43.5, 76.9] (22/36) | 61.1% [43.5, 76.9] (22/36) | 58.3% [40.8, 74.5] (21/36) | 58.3% [40.8, 74.5] (21/36) |
| Used no tool at all | 16.7% [6.4, 32.8] (6/36) | 0.0% [0.0, 9.7] (0/36) | 0.0% [0.0, 9.7] (0/36) | 16.7% [6.4, 32.8] (6/36) |
| Not answered (budget, error) | 0.0% [0.0, 9.7] (0/36) | 2.8% [0.1, 14.5] (1/36) | 2.8% [0.1, 14.5] (1/36) | 0.0% [0.0, 9.7] (0/36) |
| Run with a failed tool call | 2.8% [0.1, 14.5] (1/36) | 2.8% [0.1, 14.5] (1/36) | 5.6% [0.7, 18.7] (2/36) | 2.8% [0.1, 14.5] (1/36) |
| Tokens per question, mean [95% CI] | 3,842 [3,015, 4,947] | 10,785 [9,557, 12,154] | 7,794 [6,261, 9,467] | 4,069 [3,181, 5,212] |
| Tokens per correct answer | 6,587 | 17,649 | 13,361 | 6,976 |
| Model calls / tool calls per question | 2.6 / 2.2 | 8.9 / 5.5 | 7.6 / 4.2 | 2.8 / 2.4 |
| Latency p50 / p95 (s, 4 questions in flight) | 15 / 28 | 42 / 69 | 27 / 79 | 14 / 30 |

Paired comparisons on `correct` (exact McNemar by question; Bonferroni threshold 0.0083 for six pairs):

| Pair | A correct | B correct | only first | only second | p | clears 0.0083 |
|---|---|---|---|---|---|---|
| react vs plan_execute | 21 | 22 | 4 | 5 | 1 | no |
| react vs supervisor | 21 | 21 | 3 | 3 | 1 | no |
| react vs draft_verify | 21 | 21 | 2 | 2 | 1 | no |
| plan_execute vs supervisor | 22 | 21 | 3 | 2 | 1 | no |
| plan_execute vs draft_verify | 22 | 21 | 5 | 4 | 1 | no |
| supervisor vs draft_verify | 21 | 21 | 3 | 3 | 1 | no |

By type and by language (correct rate):

| | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| neighbour | 83.3% (10/12) | 66.7% (8/12) | 66.7% (8/12) | 91.7% (11/12) |
| pair | 33.3% (4/12) | 41.7% (5/12) | 41.7% (5/12) | 33.3% (4/12) |
| topic | 58.3% (7/12) | 75.0% (9/12) | 66.7% (8/12) | 50.0% (6/12) |
| en | 61.1% (11/18) | 61.1% (11/18) | 61.1% (11/18) | 61.1% (11/18) |
| ja | 55.6% (10/18) | 61.1% (11/18) | 55.6% (10/18) | 55.6% (10/18) |

What the wrong answers are:

| | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| real but wrong article | 13 | 13 | 14 | 15 |
| invented | 2 | 0 | 0 | 0 |
| no citation | 0 | 0 | 0 | 0 |
| not answered | 0 | 1 | 1 | 0 |

Where the tokens go (mean tokens per question, share):

- **A react**: react.agent 3,768 (98%); react.force 74 (2%)
- **B plan-execute**: step.agent 9,677 (90%); step.force 510 (5%); synth 394 (4%); planner 205 (2%)
- **C supervisor**: researcher.agent 6,492 (83%); supervisor 682 (9%); writer 326 (4%); researcher.force 295 (4%)
- **D draft-verify**: draft.agent 3,731 (92%); revise.agent 266 (7%); draft.force 72 (2%)

Noise floor: the same 36 questions run twice under identical settings (results/runs/dev2 vs results/runs/dev3_repeat):

| | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| identical answers | 5/36 | 5/36 | 2/36 | 3/36 |
| questions that changed correctness | 4 (3 right to wrong, 1 wrong to right) | 1 (1 right to wrong, 0 wrong to right) | 2 (1 right to wrong, 1 wrong to right) | 5 (2 right to wrong, 3 wrong to right) |
| correct, run 1 / run 2 | 21 / 19 | 22 / 21 | 21 / 21 | 21 / 22 |
