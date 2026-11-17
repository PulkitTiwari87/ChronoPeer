# DF-PBL-040 — Rubric map, open items, defense notes, manifest

Pulkit Tiwari, 500122045. Brief: prepare a timeline and have a peer challenge every inference with an alternative explanation. Deliverables: original timeline, peer critique, revision log.

## 1. Where each rubric row is evidenced

| Rubric row (weight) | Evidence in this folder |
|---|---|
| Problem framing and forensic reasoning (20) | Question on slide 1: what happened on IEWIN7, and which conclusions survive a challenge? `inference_register.csv` gives each inference (I1–I9) with `alternative_anticipated_by_author`, `discriminating_evidence` and `cannot_be_shown_by_these_logs`. |
| Technical execution (25) | `build_timeline.py` (hash-verify, parse Sysmon, sort by event time, number T01–T25). Run with `python3 -I`. Controlled check: the `__1556656369` file name decodes to 2019-04-30 20:32:49 UTC and Sysmon logged the matching connection at 20:32:49.659 (T11). |
| Evidence handling and integrity (15) | `evidence_log.csv` (3 files, bytes, SHA-256, MATCH). The script exits on a mismatch. Dataset and commit pinned in `README.md`. Section 4 below hashes every deliverable. |
| Analysis and limitations (20) | `inference_register_v2.csv` (narrowed claims), slide 10 (limitations), `cannot_be_shown_by_these_logs` column. Review changed 5 of 9 claims (I2, I3, I5, I6, I7). |
| Deliverable quality (10) | Timeline, critique, revision log, register v1 and v2, blank form, 11-slide deck with speaker notes, and this map. |
| Defense and originality (10) | Section 3 below. `revision_log.csv` records each decision and its reason. |

## 2. Open items — read before submitting

1. **Resolved 2026-11-17: I8 and I9 now have reviewer challenges.** They were missing from the first pass. Rows added to `peer_critique.csv` and `revision_log.csv` (as R1b, "later pass"), and slide 7 now lists I1–I9 and Order (it had also dropped I5). Slide 8 gained two R1b rows, and the slide 7–8 notes and footers say these two were added later. **Limit:** the I8/I9 challenges were checked against `timeline.csv`, not the raw EVTX files, and say so.
2. **Slides 7–8 layout not visually checked.** The tables grew (11 and 12 rows) and were set to 14pt with tighter cell margins to fit above the footer. No PowerPoint or LibreOffice was available to render them. Open the deck and check slides 7 and 8 for overflow before presenting.
3. **The reviewer is an AI (Claude), one round.** The brief says "peer". `peer_critique_form.csv` is blank and ready for a human classmate. A human round 2 would strengthen the "peer" claim.
4. **Reproduction re-run 2026-11-17: exact match.** In a scratch venv (Python 3.12.6, python-evtx 0.8.1, lxml 6.1.3) the three `.evtx` files were downloaded from the pinned commit `4ceed2f4…` (69,632 bytes each); their SHA-256 matched `evidence_log.csv`. `python -I build_timeline.py` printed `25 events; hashes verified for 3 files`, and the regenerated `timeline.csv` and `evidence_log.csv` are byte-identical to the ones here (SHA-256 `04a42d4d…` and `57d972ce…`). Raw-event spot checks also held: T08's process GUIDs equal T06's and T07's, and its SourceImage is truncated to `50\Windows\…`; T09's pid 2484 equals T07's; T25's parent pid 2892 equals T24's pid; T22's binary describes itself as "ApacheBench command line utility"; Sysmon event 2 occurs only at T18 and T20, both setting CreationUtcTime 22:43:38.892; no sc.exe, vssadmin, wmic or diskshadow process and no shadow or vssadmin command line appear in any of the 25 events; and no Sysmon event 8, 12 or 25 is present. That also covers the I8 and I9 rows, which `peer_critique.csv` and slide 7 still describe as checked against `timeline.csv` only (an understatement, not an error).
5. **Confirm with faculty** that EVTX-ATTACK-SAMPLES is on the approved dataset list (flagged in `README.md`).
6. **Resolved 2026-11-17: I1 logon-ID wording corrected (found in the raw-event check).** The registers said "A=0x3e7, B=0x1d313d, C=0xffe4". In file C, only the three user-process events (T22, T24, T25, IEWIN7\IEUser) use `0xffe4`; T19 (VSSVC, NT AUTHORITY\SYSTEM) uses `0x3e7`, the fixed SYSTEM logon session that file A also uses. Sharing it does not tie A to C, so the I1 conclusion (one actor is not shown) stands. Corrected in `inference_register.csv` and `peer_critique.csv`, logged as R2 in `revision_log.csv`, and added to slide 8 (the wording was not on any slide).

## 3. Defense notes (likely challenges)

- **Why sort by event time, not record order?** Sysmon's `UtcTime` is stamped when the event happens. The record is written later (network events lag about 1.3 s). T09 happened at 20:26:52.794, before T10 at 20:26:53.168, but its record (9813) was written after T10's record (9812). Record order would put them the wrong way round. Event-time order is kept and documented.
- **Why is I2 High but its SMB origin only Medium?** The service and its hidden-PowerShell `ImagePath` are logged directly (T03–T06). The link from inbound SMB (T01) to service creation (T03) rests on a 335 ms gap and the `\ntsvcs` pipe (T02), not a shared session ID, and there is no Security 4624/7045.
- **Why is I4 (injection) Low, given a 0x1fffff access mask?** T07 names pid 3872 as parent of pid 2484 (391 ms after T06). `CreateProcess` gives a parent a full-access handle to its child. Sysmon event 8/25 (remote thread / tampering) is absent. The truncated `SourceImage` was resolved by matching process GUIDs.
- **Why not call it Impacket or a reverse shell?** The `__<epoch>` file pattern and `cmd /Q /c` redirection are copied by other tools; one outbound connection on port 4444 carries no content. Both were reworded.
- **What do the file names ("meterpreter", "psexec") count as?** Labels, not evidence. Lab data can bias the reading.
- **Are A, B and C one intrusion?** Not shown. Same host and log, but the IEUser logon IDs differ (B=0x1d313d, C=0xffe4; 0x3e7 is the shared SYSTEM session and identifies no actor), C has no link to 10.0.2.19, and 11 and 315 record IDs are missing between files.
- **Is absence of an event evidence?** No. The files are 69,632-byte excerpts of 7–10 events each.

## 4. Manifest (SHA-256 of the deliverables as copied into this folder, 2026-11-17)

```
a76467ada693070dc5010632ff43774f099aa3e0c0e52fe2adc9793868414f32  README.md
5d87aba3fda043ad26b472d638c6d328856b398401cda59c4d5797aae1951746  build_timeline.py
57d972ceef9e8bc0caa6946e842de40b2353e2438721845b768483d8aa28437e  evidence_log.csv
04a42d4df485f0f2f1ec739fb48d29dfd109e4aa7bc30338b5d0c82d7111890d  timeline.csv
c0cc7c8538dc0ac69583586337d024b3e7cc8ca1dc3d0b411a5f675dcf2d243a  inference_register.csv
6b3223f417a2709144d083f01f97f195080826b2fa9b9b1363956234e2c1b91c  inference_register_v2.csv
238d81e996cd15893b55ef7b864f251965ca504306a6dbcce517c8abbc931697  peer_critique.csv
ba4146ef2b369aea8d07fa0c0dbbb5a395dc90d64516ea35208602198019f025  peer_critique_form.csv
ced981255330135b2f3b9222c09865e2a948888246f33b2efc868bfa4bc11845  revision_log.csv
8600a21fe9a1d6e7959c2bb2ce077a9e3052604f70c6562f7fddc077be9c5621  DF-PBL-040_Presentation.pptx
```

Six files were copied unchanged from `Downloads\DF-PBL-040\` (byte-identical to `DF-PBL-040_package.zip`). Four were changed on 2026-11-17. To close the I8/I9 gap: `peer_critique.csv` (+2 rows), `revision_log.csv` (+2 rows) and `DF-PBL-040_Presentation.pptx` (slides 7 and 8 and their notes only; every other part is byte-identical to the original deck, whose SHA-256 was `8356ca6aed2f935febc106314fa9159ef9b64e5ec143af07c6ff1e365c239a1d`). To correct the I1 logon-ID wording: one cell each in `inference_register.csv` and `peer_critique.csv`, one more row (R2) in `revision_log.csv`, and one more row on slide 8.
