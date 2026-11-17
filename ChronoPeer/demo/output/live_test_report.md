# ChronoPeer live test report

- Site: https://chronopeer.vercel.app
- Run at: 2026-11-17 11:02:13 UTC
- Result: **ALL PASSED** (30 of 30 steps passed)
- Serverless instance resets during the run: 0

| # | Step | Request | Expected | Got | Time | Result | Detail |
|---|---|---|---|---|---|---|---|
| 1 | Service is up and reports temporary storage | `GET /api/health` | 200 | 200 | 427 ms | PASS | ephemeral=True |
| 2 | Bundled demo case is present | `GET /api/cases` | 200 | 200 | 286 ms | PASS | DF-PBL-040 found |
| 3 | Investigator creates an investigation | `POST /api/cases` | 201 | 201 | 269 ms | PASS |  |
| 4 | Reviewer mode cannot create an investigation | `POST /api/cases` | 403 | 403 | 380 ms | PASS |  |
| 5 | Preview validates, hashes, flags malformed rows (stores nothing) | `POST /api/cases/2/evidence/preview` | 200 | 200 | 268 ms | PASS | 5 valid, 1 malformed, 1 unknown timezone, SHA-256 matches local |
| 6 | Nothing was stored by the preview | `GET /api/cases/2/evidence` | 200 | 200 | 268 ms | PASS | evidence list = [] |
| 7 | Import evidence (original file stored by hash) | `POST /api/cases/2/evidence` | 201 | 201 | 250 ms | PASS | valid_records = 5 |
| 8 | Importing the same file again is refused | `POST /api/cases/2/evidence` | 409 | 409 | 314 ms | PASS |  |
| 9 | Reviewer mode cannot import evidence | `POST /api/cases/2/evidence` | 403 | 403 | 302 ms | PASS |  |
| 10 | A non-CSV/JSON file is rejected | `POST /api/cases/2/evidence` | 422 | 422 | 274 ms | PASS |  |
| 11 | Integrity re-check of the stored file | `GET /api/evidence/2/verify` | 200 | 200 | 261 ms | PASS | verify result = MATCH |
| 12 | Timeline is chronological; unknown timezone is flagged and last | `GET /api/cases/2/timeline` | 200 | 200 | 251 ms | PASS | order EV001..EV004 then EV005 (unknown timezone, not converted) |
| 13 | Create an inference with three supporting events | `POST /api/cases/2/inferences` | 201 | 201 | 260 ms | PASS | status = proposed |
| 14 | An inference citing a non-existent event is refused | `POST /api/cases/2/inferences` | 422 | 422 | 268 ms | PASS |  |
| 15 | Reviewer mode cannot create an inference | `POST /api/cases/2/inferences` | 403 | 403 | 257 ms | PASS |  |
| 16 | A challenge without an alternative explanation is refused | `POST /api/inferences/10/reviews` | 422 | 422 | 269 ms | PASS |  |
| 17 | Reviewer submits a challenge with an alternative | `POST /api/inferences/10/reviews` | 201 | 201 | 262 ms | PASS |  |
| 18 | Inference is now marked challenged | `GET /api/inferences/10` | 200 | 200 | 270 ms | PASS | status = challenged |
| 19 | A duplicate review in the same round is refused | `POST /api/inferences/10/reviews` | 409 | 409 | 523 ms | PASS |  |
| 20 | Investigator mode cannot submit a review | `POST /api/inferences/10/reviews` | 403 | 403 | 270 ms | PASS |  |
| 21 | A response without a justification is refused | `POST /api/inferences/10/revisions` | 422 | 422 | 259 ms | PASS |  |
| 22 | Investigator accepts the challenge and revises | `POST /api/inferences/10/revisions` | 201 | 201 | 288 ms | PASS | status revised; original reasoning preserved |
| 23 | The same review cannot be answered twice | `POST /api/inferences/10/revisions` | 409 | 409 | 258 ms | PASS |  |
| 24 | History keeps original, challenge, response and current | `GET /api/inferences/10/history` | 200 | 200 | 259 ms | PASS | original -> challenge -> response -> current |
| 25 | Audit trail recorded every action in order | `GET /api/cases/2/audit` | 200 | 200 | 289 ms | PASS | case_created > evidence_imported > inference_created > review_submitted > revision_recorded |
| 26 | Investigator generates the PDF report | `GET /api/cases/2/report` | 200 | 200 | 324 ms | PASS | 9264 bytes, all 11 section headings present |
| 27 | Reviewer mode cannot generate the report | `GET /api/cases/2/report` | 403 | 403 | 256 ms | PASS |  |
| 28 | The audit trail cannot be deleted | `DELETE /api/cases/2/audit` | 405 | 405 | 266 ms | PASS |  |
| 29 | The bundled demo case is untouched | `GET /api/cases/1/summary` | 200 | 200 | 268 ms | PASS | demo case (events, inferences) = (25, 9) |
| 30 | Dashboard reflects both investigations | `GET /api/dashboard` | 200 | 200 | 249 ms | PASS | investigations = 2 |
