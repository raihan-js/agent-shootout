# Post-hoc checks on the test run (not pre-registered)

## 1. Answers with a quote that is in none of: the cited articles' text, their captions, the question

| | answers with such a quote / answers that quote |
|---|---|
| A react | 8/122 (6.6%) [2.9, 12.5] |
| B plan-execute | 3/19 (15.8%) [3.4, 39.6] |
| C supervisor | 0/17 (0.0%) [0.0, 19.5] |
| D draft-verify | 8/119 (6.7%) [2.9, 12.8] |

## 2. Where draft-verify beats react

Questions where only D is correct: 16; in 5 of them react's answer had an invented citation and in 1 react did not answer (budget or server error). Questions where only A is correct: 6 (0 with an invented citation in D). The other 10 questions where only D is correct are ones where react answered with no invented citation but missed a gold article.

## 3. Share of questions on which two designs disagree about `correct` (test, n = 240)

| pair | disagree |
|---|---|
| A react vs B plan-execute | 55/240 (22.9%) |
| A react vs C supervisor | 49/240 (20.4%) |
| A react vs D draft-verify | 22/240 (9.2%) |
| B plan-execute vs C supervisor | 40/240 (16.7%) |
| B plan-execute vs D draft-verify | 47/240 (19.6%) |
| C supervisor vs D draft-verify | 41/240 (17.1%) |

For scale, the same design run twice on the 36 dev questions changed correctness on 4 (react), 1 (plan-execute), 2 (supervisor) and 5 (draft-verify) of 36 (3 to 14%); see the pre-registered noise-floor table.

## 4. Failed article lookups (get_article / verify_citation)

| | lookups | failed | failed although the article exists under another spelling | runs with such a failure |
|---|---|---|---|---|
| A react | 367 | 2 (0.5%) | 0 | 0 (0 correct) |
| B plan-execute | 822 | 34 (4.1%) | 11 | 5 (2 correct) |
| C supervisor | 616 | 7 (1.1%) | 2 | 1 (0 correct) |
| D draft-verify | 382 | 2 (0.5%) | 0 | 0 (0 correct) |

The tool accepts canonical ids (541, 415-2); a model that writes 61条の2 or 250の6 is told the article does not exist. The tool is the same for every design and was not changed after the pre-registration.
