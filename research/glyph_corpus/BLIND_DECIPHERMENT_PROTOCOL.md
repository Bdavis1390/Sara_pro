# Blind Decipherment / Translation Benchmark Protocol

Status: ACTIVE calibration method under #378 / #377

## Purpose

Test Worldshepherd's ability to infer structure and meaning from symbolic or partially understood corpora **before** consulting extant translations, then compare the independent reconstruction against manuscript glosses, scholarly dictionaries, and later translations.

The goal is not to manufacture novelty. The goal is to measure where independent reasoning agrees, diverges, overfits, or discovers genuine textual problems.

## Honesty rule

A case is scored `BLIND` only when the comparison translation was not viewed before the reconstruction was frozen.

If a translation was already seen during provenance research, the case is marked `RETROSPECTIVE_CALIBRATION` and cannot be presented as an independent decipherment success.

## Workflow

1. Freeze source witness and exact transcription variant.
2. Hide all full-sentence translations for the target passage.
3. Permit only:
   - source-image/manuscript evidence,
   - lexicon entries derived from other passages,
   - internal recurrence statistics,
   - morphology inferred from other occurrences,
   - grammar hypotheses learned from training passages,
   - chronology/provenance metadata.
4. Produce a literal reconstruction first, preserving uncertainty.
5. Freeze reconstruction + confidence + alternative parses.
6. Reveal comparison translations.
7. Align at token, phrase, clause, and semantic-role levels.
8. Classify every difference:
   - manuscript/transcription variant,
   - segmentation variant,
   - lexical disagreement,
   - grammatical disagreement,
   - poetic/editorial expansion,
   - later doctrinal reinterpretation,
   - unresolved.
9. Record whether the difference improves or degrades explanatory consistency across the whole corpus.
10. Never back-edit the frozen prediction; create a new revision.

## Metrics

Do not use a single accuracy score. Report a vector:

- lexical matches / conflicts
- semantic-role matches / conflicts
- word-order preservation
- unsupported inserted concepts
- untranslated residue
- manuscript-variant sensitivity
- cross-call consistency
- uncertainty calibration

## Enochian-specific controls

- Treat Dee/Kelley manuscript witnesses as primary historical evidence.
- Distinguish Dee's English 'sense' from a literal one-to-one gloss.
- Preserve spelling variants such as `lansh/lonsh`, `calz/kalz`, and segmentation variants such as `vorsg/vors g`.
- Flag lacunae and later reconstructions.
- Compare Dee/Kelley -> Ashmole/Casaubon -> Golden Dawn -> Crowley -> James/Laycock -> modern reinterpretations as separate provenance layers.
- No supernatural-origin inference is permitted from translation quality alone.

## First calibration

Key/Call 1 is `RETROSPECTIVE_CALIBRATION` because published English renderings had already been consulted during provenance work. It is used to validate the diff taxonomy and expose manuscript/editorial drift.

The first genuinely blind benchmark must use a passage whose full English rendering has not been exposed to the model in the active research session.