# Test plan

Run `python -m pytest` from the `ChronoPeer` folder. Each test gets a fresh app and a temporary SQLite database. Current result: **52 passed**.

## Evidence (`test_evidence.py`, `test_hashing.py`)

Valid CSV import, valid JSON import (list and `{"events": []}`), invalid file rejection (wrong extension, empty, binary, not JSON, broken JSON, not UTF-8), unsafe filenames, oversized upload (413), missing columns, malformed rows reported while valid rows import, missing timestamp kept and flagged, duplicate events skipped within and across files, same file twice is a conflict, preview stores nothing, reviewer mode cannot import, SHA-256 known vector, MATCH/MISMATCH/MISSING detection, tampering after import is detected, original bytes preserved.

## Timeline (`test_timeline.py`)

Chronological sorting (ascending and descending), identical timestamps with natural tie-break (`EV2` before `EV10`), mixed timezone offsets normalised to UTC, unknown timezone never converted and sorted after known events, assumed timezone recorded as assumed, invalid assumption rejected, missing and invalid timestamps last and flagged, the same input in two cases gives the same order, normaliser unit cases.

## Inferences (`test_inferences.py`)

Create with several supporting events, reject references to events that do not exist or belong to another case, require at least one event and a confidence of 1 to 5, status update recorded as a revision, investigator-only creation.

## Peer review (`test_reviews.py`)

Submit a challenge, a challenge requires an alternative explanation, agreement requires a justification, duplicate submission in the same round is rejected, only reviewer mode may review, every inference needs a disposition (the pending count falls to zero).

## Revisions (`test_revisions.py`)

Accept with revised reasoning while the original is preserved, reject needs a justification and changes nothing, partial acceptance and unresolved, acceptance needs revised reasoning and a review to answer, a review can be answered only once, history shows original then challenge then response, re-review after a revision, investigator-only responses, the audit log records every step and cannot be updated or deleted.

## End to end (`test_acceptance.py`)

The specification's 8 steps through the HTTP API only: import, timeline, inference, shared review interface, challenge, return to investigator mode, revise, report. Also: the PDF has all 11 section headings, reviewer mode cannot generate it, and the demo seed loads 25 events, 9 inferences and 12 revisions, verifies its evidence hash, produces a report, and does not seed twice.

## Manual checks done on the built app

Dashboard, timeline (25 points plotted), inferences, evidence table, report page, mode gating on the peer-review page, and the full revision history of an inference, against the running server. The UI has no automated tests.
