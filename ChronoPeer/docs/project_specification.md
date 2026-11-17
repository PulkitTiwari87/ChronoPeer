# Specification and traceability

Source: the ChronoPeer Software Requirements and Technical Design Document (project code DF-PBL-040, version 1.0). This page restates the requirements and shows where each one is implemented and tested. The student identity lines of the original document are intentionally not reproduced here.

## Problem and objectives

Investigators may mis-order events, overlook alternatives or conclude more than the evidence supports. ChronoPeer adds a structured peer-review step: import evidence, preserve hashes, normalise timestamps, build a timeline, separate observation from inference, record challenges and alternatives, preserve original and revised conclusions, and report.

## Functional requirements

| ID | Requirement | Implemented in | Tests |
|---|---|---|---|
| FR-01 | Investigation management (case ID, title, description, date, dataset, status) | `api/cases.py`, `models.Case` | `test_inferences`, `test_acceptance` |
| FR-02 | CSV and JSON import with record validation | `services/file_validator.py`, `evidence_parser.py` | `test_evidence` |
| FR-03 | SHA-256, original files preserved, import time, artifact ids | `services/hashing.py`, `evidence_importer.py` | `test_evidence`, `test_hashing` |
| FR-04 | Chronological timeline, flagged missing or invalid timestamps | `services/timeline_builder.py`, `timestamp_normalizer.py` | `test_timeline` |
| FR-05 | Inference with supporting events, confidence, reasoning, status | `services/inference_manager.py` | `test_inferences` |
| FR-06 | Peer challenge or agreement, alternative explanation, evidence request, confidence | `services/review_manager.py` | `test_reviews` |
| FR-07 | Accept, partly accept, reject (justified), modify, unresolved; previous versions kept | `services/revision_manager.py` | `test_revisions` |
| FR-08 | Audit history of every action | `services/audit.py`, `models.AuditLog` | `test_revisions` |
| FR-09 | PDF report with 11 sections | `services/report_generator.py` | `test_acceptance` |

## Non-functional requirements

| Requirement | How it is met |
|---|---|
| Usability | Seven focused pages; the current mode is always shown |
| Integrity | SHA-256 at import; `/verify` re-checks the stored file |
| Reliability | Row-level validation; malformed rows reported, never silently dropped |
| Reproducibility | Deterministic ordering with fixed tie-breaks (`test_timeline`) |
| Traceability | An inference cannot exist without real supporting events |
| Maintainability | Thin routers, one module per concern, modular React pages and components |
| Portability | Runs locally on Windows with a venv; no Docker, Redis or cloud database |
| Security | Filename, extension, size and content checks; hash-named storage; parameterised ORM queries |
| Auditability | Append-only audit log; revisions never overwrite history |

## Deliberate deviations from the recommended structure

- Hash routing instead of a router library (fewer dependencies).
- No separate Sidebar component: navigation is a translucent top bar.
- Added `deps.py`, `inference_manager.py`, `evidence_importer.py` and `seed_demo.py`, and a shared `ui.jsx` in the frontend.
- Extra columns listed in `database_schema.md`.
