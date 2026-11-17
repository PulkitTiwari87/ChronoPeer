# Dataset documentation

## Source

sbousseaden/EVTX-ATTACK-SAMPLES (licence GPL-3.0), commit `4ceed2f4706daf601c212a8f91c113dd85349a2c`. Public lab recordings of simulated attack techniques. Three Sysmon `.evtx` files from host IEWIN7, 2019-04-30:

| Label | File | SHA-256 |
|---|---|---|
| A | `Lateral Movement/LM_sysmon_psexec_smb_meterpreter.evtx` | `18ffdda9c24e593d6b1414b6e05c7f7a5dbffb8588a387c165431b61ab52d76f` |
| B | `Lateral Movement/LM_wmiexec_impacket_sysmon_whoami.evtx` | `21b8852b2b386f4d3f6f0c8a7304de8e628bb43cfa23888ab317b95b784ffe59` |
| C | `Execution/Exec_sysmon_meterpreter_reversetcp_msipackage.evtx` | `328ec1b4b6c531af991a2de2221900ec93db1853f7446f61c7e3c9bf9bf052e3` |

Each file is 69,632 bytes and holds only 7 to 10 events, so they are excerpts, not complete logs. File names such as "meterpreter" and "psexec" are labels, not evidence. **Confirm with faculty that this dataset is on the approved list.** The raw `.evtx` files are not committed to this repository.

## Extraction process

1. `build_timeline.py` (in the parent project) verifies the three hashes, parses the Sysmon events with python-evtx and lxml, sorts by Sysmon's event time, and writes `timeline.csv` (25 events) and `evidence_log.csv`. It was re-run against the pinned commit and reproduced both files byte for byte.
2. `datasets/make_sysmon_export.py` converts `timeline.csv` into ChronoPeer's import format, `datasets/sample_exports/sysmon_iewin7_export.csv`: `timestamp, event_type, description, source, artifact_id`. Sysmon's `UtcTime` is UTC by definition, so `Z` is appended and the timezone is **known**. `artifact_id` is the file label plus the Sysmon record id (for example `A-9811`), and each description is prefixed with its timeline label (`[T01]`).

The other files in `datasets/sample_exports/source/` are the project's original registers, critiques and revision log, copied unchanged.

## How the demo case is built

`backend/services/seed_demo.py` runs only when the database is empty and `CHRONOPEER_SEED_DEMO=1`. It imports the export through the normal importer, creates the nine inferences (I1 to I9) with the normal service, submits the critiques as reviews, and replays the revision log as revisions. Nothing is typed in by hand. Mappings made, and why:

- **Confidence** text to a 1 to 5 number: the lowest named level (see `methodology.md`).
- **Reviewer confidence**: not recorded in the source, so it is left empty rather than invented.
- **Alternative explanation**: the original critique records the challenge and the evidence that would distinguish, but not a separate alternative. That field is filled from the register's anticipated alternative, and the text says so.
- **Reviewer**: "Claude (AI reviewer)". The demo has no human peer, and the report states this.
- **"Order" row** (event time versus record order): a method question, not an inference. It is recorded in the case description.
- **Revision log** rows R0, R1, R1b and R2 become 12 revisions (the R0 row covers two inferences). Responses map as Upheld = accepted, Partly upheld = partially accepted, Answered = rejected (claim retained), author checks = modified.
- **Timestamps** of seeded actions are the time of seeding, not the dates in the original files.

## Limits

Excerpts only (11 record ids are missing between files A and B, 315 between B and C). Sysmon only: no Security log, so no record of which account authenticated, and no packet capture.
