# Architecture

## Layers

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React, Tailwind CSS (Vite build), Plotly for the timeline chart | Dashboard, evidence upload, timeline, inferences, peer review, revisions, report download |
| Backend | Python, FastAPI, Pydantic | Upload validation, parsing, hashing, timestamp normalisation, timeline, inferences, reviews, revisions, audit, PDF |
| Database | SQLite via SQLAlchemy | Cases, evidence, events, inferences, reviews, revisions, audit |

One process serves both: the API under `/api` and the built UI at `/`. Routing in the UI is hash-based, so no server rewrite rules are needed and the same bundle works behind any host.

## Data flow

Evidence file → upload → **validation** (name, extension, size, UTF-8, shape) → **SHA-256** → **parse** (pandas; malformed rows reported) → **timestamp normalisation** → timeline events → inference (must cite real events) → **peer review** (agree or challenge) → **investigator revision** → **PDF report**. Every step appends to the audit log.

Route handlers only parse the request, call a service, commit and serialise. Business rules live in `backend/services/`.

## Modes (spec 4.3)

Two modes share one investigation. The caller states its mode in `X-Role` (`investigator` or `reviewer`) and name in `X-Actor`; `deps.py` enforces the mode per endpoint:

- Investigator: create cases, import evidence, create inferences, respond to challenges, generate the report.
- Peer reviewer: submit reviews. Everyone can read.

This is separation of duties plus attribution. It is **not authentication** and cannot prove identity (spec 13.8).

## Timeline ordering (deterministic)

Events are grouped, then sorted:

1. UTC time known or assumed, by UTC time.
2. Timezone unknown, by the wall-clock value in the original string (so events from one clock still order among themselves). The value is never converted with the machine's timezone.
3. Missing or invalid timestamp, last.

Ties break on a natural sort of the artifact id (`EV2` before `EV10`), then import order, then database id. The same input therefore always gives the same order.

## Revisions and history

`inferences` always holds the current state and also the original explanation, reasoning and confidence, which are never edited. Each response adds a `revisions` row snapshotting previous and new reasoning, confidence and status plus the justification, so the original conclusion, the challenge, the response and the revised conclusion are all readable. A review can be answered once. Reviews are unique per reviewer and round (round = number of revisions so far), which blocks duplicate submissions yet allows re-review after a revision.

## Audit

`audit_logs` is append-only: the application exposes no update or delete endpoint, and ORM listeners raise on update or delete.

## Deployment shape

A single Python web process with a SQLite file and an upload folder. That fits one long-lived instance (local Windows, or a single free web service) and does **not** fit serverless platforms where the filesystem is per-request. On a free host the disk is ephemeral, so the demo case is re-seeded when the database is empty (`CHRONOPEER_SEED_DEMO=1`).
