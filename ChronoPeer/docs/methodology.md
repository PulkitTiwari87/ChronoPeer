# Methodology

The investigation method the application enforces, in order.

1. **Preserve and verify.** Hash each evidence file, store the original bytes untouched, and re-check on demand. A match shows the file equals the recorded digest, nothing more.
2. **Build the timeline first, with no interpretation.** Events are ordered by the time the source logged, not by record order. In the demo data a network event (record 9813) happened before a registry event (record 9812) but was written after it, so record order would be wrong.
3. **Separate observation from inference.** Events are observations. An inference is a claim with an explanation, reasoning, a confidence (1 to 5) and at least one supporting event.
4. **Challenge every inference.** A reviewer must give an explicit disposition. A challenge needs an alternative explanation and may request the evidence that would tell the two apart. Agreement also needs a justification.
5. **Respond and revise without erasing.** The investigator accepts, partly accepts, rejects (with justification), modifies or marks the inference unresolved. The original conclusion and every intermediate state stay on record.
6. **Report.** The report shows the original timeline and inferences, every critique and alternative, the revised view, the revision history, the limitations and the conclusion.

## Timestamps

- `Z` or an explicit offset: **known**, converted to UTC.
- No timezone, and the investigator chose an assumption at import: **assumed**, converted and labelled as such.
- No timezone and no assumption: **unknown**. No UTC value is stored and the machine's local timezone is never used.
- Empty or unparseable: **missing** or **invalid**; the event is kept, flagged and placed last.

## Confidence

Investigator confidence is 1 (barely supported) to 5 (directly shown). For the demo data, the source registers used words with qualifiers, such as "Medium (host/log); Low (actor)". These are mapped to the **lowest** named level: Rejected = 1, Low = 2, Medium = 3, High = 4. The original wording is kept inside the reasoning text.

## Status vocabulary

`proposed` (new), `challenged` (a reviewer disagreed), `agreed`, `revised` (changed after review), `retained` (challenge rejected, conclusion kept), `unresolved`, `withdrawn` (the claim was dropped as unsupported).

## "Awaiting review"

An inference is awaiting review when no review exists in its current round. The round increases with each revision, so a revised conclusion goes back to the reviewer; this is why the demo case shows eight inferences awaiting a second round.
