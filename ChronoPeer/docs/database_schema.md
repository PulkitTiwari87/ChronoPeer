# Database schema

SQLite, accessed through SQLAlchemy with foreign keys enforced. The seven specified tables plus `audit_logs`. Columns marked **+** are additions to the specification, made so the functional requirements can be met.

## cases
`id`, **`case_code`** (optional unique label such as DF-PBL-040), `title`, `description`, `dataset_name`, **`investigation_date`**, `status`, **`conclusion`** (printed as report section 11), `created_at`.

## evidence
`id`, `case_id`, `filename` (original), `file_path` (stored as `storage/<case_id>/<sha256>.<ext>`), `sha256`, `file_type`, `imported_at`, `record_count`. Unique `(case_id, sha256)`.

## timeline_events
`id`, `case_id`, `evidence_id`, `event_time_original` (exactly as imported), `event_time_utc` (null unless the timezone is known or assumed), `timezone_status` (`known`, `assumed`, `unknown`, `invalid`, `missing`), `event_type`, **`source_label`** (the `source` column), `description`, `artifact_reference`, **`import_order`** (tie-break).

## inferences
`id`, `case_id`, `title`, **`explanation`** (FR-05 asks for explanation and reasoning separately), `reasoning`, `confidence` (1 to 5), `status` (`proposed`, `challenged`, `agreed`, `revised`, `retained`, `unresolved`, `withdrawn`), **`original_explanation`**, **`original_reasoning`**, **`original_confidence`** (written once, never edited), `created_at`, `updated_at`.

## inference_events
Junction `(inference_id, event_id)`. Every inference must have at least one row, and only events of the same case are accepted.

## peer_reviews
`id`, `inference_id`, `reviewer_name`, `decision` (`agree`, `challenge`), `critique` (justification, required for both), `alternative_explanation` (required for a challenge), `additional_evidence`, `confidence` (1 to 5, nullable: the demo data records none), **`round`**. Unique `(inference_id, reviewer_name, round)`.

## revisions
`id`, `inference_id`, `peer_review_id` (nullable), **`response`** (`accepted`, `partially_accepted`, `rejected`, `modified`, `unresolved`), **`previous_explanation`**, **`revised_explanation`**, `previous_reasoning`, `revised_reasoning`, **`previous_confidence`**, **`new_confidence`**, `previous_status`, `new_status`, `change_reason` (required), **`actor_name`**, `created_at`.

## audit_logs
`id`, `case_id`, `actor_role`, `actor_name`, `action_type`, `record_id`, `description`, `created_at`. Append-only.

## Timestamps
All stored as naive UTC `DATETIME`; the API returns ISO 8601 with a `Z` suffix. `event_time_original` is text and is never rewritten.
