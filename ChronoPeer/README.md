# ChronoPeer

A lightweight digital-forensics application that rebuilds an incident **timeline** from imported evidence, records the **inferences** an investigator draws from it, and puts every inference through **peer challenge** with an alternative explanation. Every revision keeps the original reasoning, the challenge and the response, and the whole case ends in a **PDF report**.

Project code DF-PBL-040 (Digital Forensics, project-based learning).

## What it does

1. Import a normalised **CSV or JSON** evidence file. It is hashed (SHA-256), stored untouched, validated, and parsed.
2. Build a deterministic, chronological **timeline**. Unknown timezones are flagged, never silently converted.
3. Record **inferences**, each linked to at least one real event.
4. Switch to **Peer reviewer** mode: agree or challenge every inference, with a justification and (for a challenge) an alternative explanation.
5. Switch back to **Investigator** mode: accept, partly accept, reject (with justification), modify or mark unresolved. Previous versions are kept.
6. Generate the **PDF report** (11 sections) and read the append-only **audit trail**.

The bundled demo case is the project's real Sysmon analysis (host IEWIN7, 2019-04-30): 25 events, 9 inferences, their critiques and the revision log, all loaded through the same import and review pipeline as any other case.

## Run it locally (Windows)

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn backend.main:create_app --factory --port 8000
```

Open http://127.0.0.1:8000. The built UI is in `frontend/dist`, so Node is only needed to change the interface:

```bash
cd frontend
npm install
npm run build      # writes frontend/dist (committed on purpose)
npm run dev        # Vite dev server on :5173, proxying /api to :8000
```

Settings come from environment variables (see `.env.example`): `CHRONOPEER_DB`, `CHRONOPEER_STORAGE`, `CHRONOPEER_REPORTS`, `CHRONOPEER_MAX_UPLOAD_BYTES`, and `CHRONOPEER_SEED_DEMO=1` to load the demo case when the database is empty.

## Tests

```bash
.venv\Scripts\python.exe -m pytest
```

52 tests cover every mandatory area of the specification (evidence, timeline, inferences, peer review, revisions) plus the 8-step acceptance run, the PDF sections, the audit log and the demo seed. See `docs/test_plan.md`.

## Roles

There is no login. The **mode** (Investigator or Peer reviewer) and a self-declared name are sent as `X-Role` and `X-Actor` headers, and each endpoint enforces its mode. This separates duties and records who acted; it does not authenticate anyone (see `docs/limitations.md`).

## API summary (all under `/api`)

| Area | Endpoints |
|---|---|
| Cases | `GET/POST /cases`, `GET/PATCH /cases/{id}`, `/cases/{id}/summary`, `/cases/{id}/audit`, `/dashboard` |
| Evidence | `POST /cases/{id}/evidence/preview`, `POST /cases/{id}/evidence`, `GET /cases/{id}/evidence`, `GET /evidence/{id}/verify` |
| Timeline | `GET /cases/{id}/timeline?order=asc\|desc` |
| Inferences | `POST/GET /cases/{id}/inferences`, `GET /inferences/{id}`, `PATCH /inferences/{id}/status`, `GET /inferences/{id}/history` |
| Reviews | `POST/GET /inferences/{id}/reviews` (reviewer mode to post) |
| Revisions | `POST/GET /inferences/{id}/revisions`, `GET /cases/{id}/revisions` |
| Report | `GET /cases/{id}/report` (PDF) |

Interactive docs: `/docs`.

## Layout

```
backend/      FastAPI app: api/ (routers), services/ (logic), models.py, tests/
frontend/     React + Tailwind (Vite); src/pages, src/components, src/services/api.js
datasets/     sample_exports/ (demo evidence + the source CSVs it is derived from)
docs/         specification traceability, architecture, schema, methodology, dataset, tests, limitations
reports/      generated PDFs (git-ignored)
instance/     SQLite database (git-ignored)
```

## Citations and AI assistance

- Dataset: sbousseaden/EVTX-ATTACK-SAMPLES (GPL-3.0), commit 4ceed2f. Educational lab data. Confirm with faculty that it is on the approved list.
- Tools: Python 3, FastAPI, SQLAlchemy, Pydantic, pandas, ReportLab, pytest, React, Tailwind CSS, Vite, Plotly.
- AI assistance: this application, its tests and documentation were written with Claude. The demo case's review rounds were performed by Claude acting as a reviewer; that is recorded in the data and the report.
