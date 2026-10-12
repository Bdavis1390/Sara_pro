# Translation Verification Protocol

## Principle

A translation is a hypothesis constrained by a witness, language model, lexicon, grammar, textual tradition and editorial choices.

ATIP does not ask merely "Is this translation accepted?" It asks:

1. Which witness is being translated?
2. Is the transcription current?
3. Are any signs/letters uncertain?
4. Is text supplied because the witness is damaged?
5. Are competing witnesses materially different?
6. Are the lexical and grammatical analyses unique?
7. Which English concepts are supplied for readability?
8. Has the underlying reading changed in a newer edition?
9. Does a current critical translation incorporate evidence unavailable to older translations?
10. Does the translation preserve semantic roles even when wording differs?

## Audit procedure

1. Pin the exact witness and current critical transcription.
2. Record edition/version date.
3. Compare older/current transcriptions.
4. Align source tokens to translation spans.
5. Mark uncertain, restored and illegible source material.
6. Record lexical/morphological alternatives.
7. Compare at least two independent translations where available.
8. Separate stylistic smoothing from semantic change.
9. Search editorial history/new joins/new photographs/new fragment evidence.
10. Assign difference classes T0–T8.
11. Preserve every disagreement.
12. Escalate material T2–T7 cases for specialist review.

## No universal "correctness score"

A single score hides the important distinction between:
- a stylistic paraphrase,
- a lexical dispute,
- a damaged witness,
- a superseded reading,
- and unsupported interpretive expansion.

Report the vector instead.

## Continuous mode

Every canonical translation record should retain:
- source edition/version;
- last-audited date;
- superseded-by link;
- unresolved flags;
- external-review status.

If the upstream corpus changes, affected ATIP translations become STALE_PENDING_REAUDIT.
