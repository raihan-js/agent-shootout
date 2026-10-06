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

## 5. Did the model read the gold article? (correct answers only; replay of the recorded tool calls)

| | correct answers where every gold article was returned by a tool call | topic | neighbour | pair | correct AND gold read, of all 240 |
|---|---|---|---|---|---|
| A react | 130/143 (90.9%) | 53/56 | 44/54 | 33/33 | 54.2% [47.6, 60.6] (130/240) |
| B plan-execute | 147/148 (99.3%) | 63/63 | 45/46 | 39/39 | 61.3% [54.8, 67.4] (147/240) |
| C supervisor | 144/156 (92.3%) | 66/67 | 39/50 | 39/39 | 60.0% [53.5, 66.2] (144/240) |
| D draft-verify | 139/153 (90.8%) | 57/60 | 44/55 | 38/38 | 57.9% [51.4, 64.2] (139/240) |

A search hit shows the start of the article text; get_article shows all of it. A pointer in a neighbouring article does not count as reading. A correct answer that never read its gold article got the number from a guess or from arithmetic (the next article after 730 is usually 731) and has not seen the text it summarises. Example: `test063-ja`, react, cites 民法 731 as the article after 730 and summarises it as a rule about the end of a duty of support; 731 is the minimum marriage age.

Paired comparison on `correct AND gold read` (exact McNemar, post-hoc, six pairs so the same 0.0083 threshold is the fair reading):

| pair | first | second | only first | only second | p |
|---|---|---|---|---|---|
| A react vs B plan-execute | 130 | 147 | 21 | 38 | 0.0363 |
| A react vs C supervisor | 130 | 144 | 22 | 36 | 0.0869 |
| A react vs D draft-verify | 130 | 139 | 6 | 15 | 0.0784 |
| B plan-execute vs C supervisor | 147 | 144 | 24 | 21 | 0.766 |
| B plan-execute vs D draft-verify | 147 | 139 | 28 | 20 | 0.312 |
| C supervisor vs D draft-verify | 144 | 139 | 29 | 24 | 0.583 |
