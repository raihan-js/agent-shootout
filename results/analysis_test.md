## test: main comparison (n = 240 questions per architecture)

| | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| Correct (gold cited, nothing invented) | 59.6% [53.1, 65.8] (143/240) | 61.7% [55.2, 67.8] (148/240) | 65.0% [58.6, 71.0] (156/240) | 63.7% [57.3, 69.8] (153/240) |
| Precise (also nothing extra cited) | 45.0% [38.6, 51.5] (108/240) | 49.6% [43.1, 56.1] (119/240) | 54.6% [48.1, 61.0] (131/240) | 48.3% [41.9, 54.9] (116/240) |
| Answers with an invented citation | 2.9% [1.2, 5.9] (7/240) | 0.8% [0.1, 3.0] (2/240) | 2.9% [1.2, 5.9] (7/240) | 0.4% [0.0, 2.3] (1/240) |
| Invented mentions / all citation mentions | 8/495 (1.6%) | 3/418 (0.7%) | 8/404 (2.0%) | 1/490 (0.2%) |
| Answers with an unsupported quote (of answers that quote) | 86.1% [78.6, 91.7] (105/122) | 89.5% [66.9, 98.7] (17/19) | 88.2% [63.6, 98.5] (15/17) | 85.7% [78.1, 91.5] (102/119) |
| Gold article(s) cited | 60.0% [53.5, 66.2] (144/240) | 61.7% [55.2, 67.8] (148/240) | 65.0% [58.6, 71.0] (156/240) | 63.7% [57.3, 69.8] (153/240) |
| Used no tool at all | 10.8% [7.2, 15.5] (26/240) | 0.0% [0.0, 1.5] (0/240) | 0.0% [0.0, 1.5] (0/240) | 7.1% [4.2, 11.1] (17/240) |
| Not answered (budget, error) | 2.5% [0.9, 5.4] (6/240) | 1.2% [0.3, 3.6] (3/240) | 0.8% [0.1, 3.0] (2/240) | 0.8% [0.1, 3.0] (2/240) |
| Run with a failed tool call | 0.8% [0.1, 3.0] (2/240) | 9.2% [5.8, 13.5] (22/240) | 2.5% [0.9, 5.4] (6/240) | 0.8% [0.1, 3.0] (2/240) |
| Tokens per question, mean [95% CI] | 4,663 [4,118, 5,219] | 10,535 [10,101, 10,994] | 7,494 [6,958, 8,049] | 4,905 [4,366, 5,517] |
| Tokens per correct answer | 7,826 | 17,084 | 11,530 | 7,694 |
| Model calls / tool calls per question | 3.0 / 2.9 | 9.1 / 5.1 | 7.5 / 4.3 | 3.1 / 3.0 |
| Latency p50 / p95 (s, 4 questions in flight) | 14 / 31 | 40 / 70 | 31 / 75 | 16 / 38 |

Paired comparisons on `correct` (exact McNemar by question; Bonferroni threshold 0.0083 for six pairs):

| Pair | A correct | B correct | only first | only second | p | clears 0.0083 |
|---|---|---|---|---|---|---|
| react vs plan_execute | 143 | 148 | 25 | 30 | 0.59 | no |
| react vs supervisor | 143 | 156 | 18 | 31 | 0.0854 | no |
| react vs draft_verify | 143 | 153 | 6 | 16 | 0.0525 | no |
| plan_execute vs supervisor | 148 | 156 | 16 | 24 | 0.268 | no |
| plan_execute vs draft_verify | 148 | 153 | 21 | 26 | 0.56 | no |
| supervisor vs draft_verify | 156 | 153 | 22 | 19 | 0.755 | no |

Dominance (pre-registered: no detectably worse correct rate at 0.0083, and a lower mean cost with non-overlapping bootstrap intervals):

- A react dominates B plan-execute
- A react dominates C supervisor
- C supervisor dominates B plan-execute
- D draft-verify dominates B plan-execute
- D draft-verify dominates C supervisor

By type and by language (correct rate):

| | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| neighbour | 67.5% (54/80) | 57.5% (46/80) | 62.5% (50/80) | 68.8% (55/80) |
| pair | 41.2% (33/80) | 48.8% (39/80) | 48.8% (39/80) | 47.5% (38/80) |
| topic | 70.0% (56/80) | 78.8% (63/80) | 83.8% (67/80) | 75.0% (60/80) |
| en | 65.0% (78/120) | 63.3% (76/120) | 68.3% (82/120) | 65.0% (78/120) |
| ja | 54.2% (65/120) | 60.0% (72/120) | 61.7% (74/120) | 62.5% (75/120) |

What the wrong answers are:

| | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| real but wrong article | 84 | 87 | 74 | 83 |
| invented | 7 | 2 | 7 | 1 |
| no citation | 0 | 0 | 1 | 1 |
| not answered | 6 | 3 | 2 | 2 |

Where the tokens go (mean tokens per question, share):

- **A react**: react.agent 4,576 (98%); react.force 87 (2%)
- **B plan-execute**: step.agent 9,516 (90%); step.force 418 (4%); synth 397 (4%); planner 204 (2%)
- **C supervisor**: researcher.agent 6,269 (84%); supervisor 625 (8%); writer 301 (4%); researcher.force 299 (4%)
- **D draft-verify**: draft.agent 4,663 (95%); revise.agent 143 (3%); draft.force 100 (2%)

Noise floor: the same 36 questions run twice under identical settings (results/runs/dev2 vs results/runs/dev3_repeat):

| | A react | B plan-execute | C supervisor | D draft-verify |
|---|---|---|---|---|
| identical answers | 5/36 | 5/36 | 2/36 | 3/36 |
| questions that changed correctness | 4 (3 right to wrong, 1 wrong to right) | 1 (1 right to wrong, 0 wrong to right) | 2 (1 right to wrong, 1 wrong to right) | 5 (2 right to wrong, 3 wrong to right) |
| correct, run 1 / run 2 | 21 / 19 | 22 / 21 | 21 / 21 | 21 / 22 |
