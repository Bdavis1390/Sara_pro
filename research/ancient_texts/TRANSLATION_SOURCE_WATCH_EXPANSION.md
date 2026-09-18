# Translation Source Watch Expansion

## DĀMOS

DĀMOS explicitly allows multiple simultaneous analyses of a linguistic unit and ranks hypotheses by probability. Its note conventions also mark sources of:
- new joins;
- new/different readings;
- corrections;
- alternative readings.

These are machine-usable re-audit triggers.

## TLA

TLA exposes an editorial state on lemma records. Current search/help pages explicitly distinguish lemma translations and editorial state, and individual records can be marked "Verification pending".

ATIP therefore treats "verification pending" as a review state, not as proof of error.

## Gāndhārī

Gandhari.org reports 3,954 documented corrections/improvements to published texts and states that changes are documented and justified in notes. The project is progressively integrating accepted text with the history of earlier readings and interpretations.

This makes Gāndhārī an unusually valuable natural experiment for translation-lineage drift.

## ORACC

ORACC provides a representation-level warning especially relevant to the original Worldshepherd lesson:
- corpus JSON contains transliteration, lemmatization and sign-level information;
- translation is not included in that text-edition JSON;
- project metadata separately records translation formats such as tr-en;
- ATF translation markup preserves supplied, uncertain, broken/restored and untranslatable material.

A pipeline that ingests only corpusjson has not ingested the complete semantic layer.

## General result

A translation-monitoring system must monitor **source-specific change signals**, not only compare English strings.
