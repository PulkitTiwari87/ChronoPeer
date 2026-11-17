# Limitations

From the specification:

1. Timeline accuracy depends on the quality of the source artifacts.
2. Different system clocks may introduce discrepancies.
3. Timestamp interpretation is hard when timezone information is missing; such events are marked, not converted.
4. CSV and JSON imports depend on correct extraction by an external forensic tool.
5. The application does not perform disk acquisition or low-level analysis.
6. Peer review reduces unsupported reasoning but does not guarantee correct conclusions.
7. The application does not determine intent or establish guilt.
8. The shared review mode does not provide strong identity authentication.

Specific to this implementation:

- **Modes are not authentication.** Anyone can send `X-Role: reviewer`. Reviewer names are self-declared.
- **SHA-256 is not authenticity.** It shows a stored file matches its recorded digest, not that the original was genuine or that custody was unbroken.
- **The demo case has an AI reviewer.** Its critiques were written by Claude and checked against the raw events; there is no human peer in the demo data. A human second round is the obvious next step.
- **The demo evidence is excerpts.** Seven to ten events per file, with 11 and 315 record ids missing between files. Absence of an event is not evidence of absence.
- **Seeded timestamps are seeding time.** The dates of the original review activity are not reproduced in the audit trail.
- **Free hosting is ephemeral.** On a free web service the disk is wiped when the service restarts or idles out, so data you add is lost and the demo case is re-seeded. Use a local run, or a host with a persistent disk, for real work.
- **One process, SQLite.** Suitable for a demonstration and light use; not a multi-user production deployment.
- **PDF fonts.** The report uses built-in fonts, so characters outside Western European text print as `?`.
- **The UI has no automated tests.**
