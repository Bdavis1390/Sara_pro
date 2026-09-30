# Corpus-Wide Translation Continuation Plan

## Objective

Continue every translation-related lane under ATIP while preserving differences among:
- witness;
- transcription;
- transliteration;
- lexical analysis;
- grammar;
- translation;
- interpretation;
- reception history.

## New finding: translation data can be structurally separated from text data

ORACC is a concrete example.

Its corpus JSON carries transliteration, lemmatization and sign-level structure, while translation is not included in that text-edition JSON. Project metadata separately identifies texts with translation formats such as `tr-en`, and the translation itself uses dedicated ATF structures.

This is a direct application of the Representation-Loss Budget:

**machine-readable source != semantically complete source**

unless the representation contract is known.

## TEI interoperability

The TEI critical-apparatus model already distinguishes:
- lemma;
- alternate readings;
- witnesses;
- editorial responsibility;
- certainty.

ATIP maps these to the Translation Lineage Graph rather than selecting one reading and discarding the apparatus.

## Continuous audit pipeline

1. ingest witness/source metadata;
2. fingerprint each source layer;
3. preserve apparatus and alternatives;
4. pin every derived layer to exact upstream fingerprints;
5. compare upstream changes;
6. mark dependent translations STALE_PENDING_REAUDIT;
7. run named-entity/number/date/lexical consistency checks;
8. preserve supplied/restored/uncertain/untranslatable markers;
9. compare independent translations where rights permit;
10. escalate material disagreements to specialist review;
11. publish negative results and stable translations as well as errors.

## Corpus-specific rule

A source is not called "translation-ready" merely because:
- text exists;
- transliteration exists;
- a lemma dictionary exists;
- OCR exists;
- another website provides an English paraphrase.

The matrix in `translation_source_matrix.yaml` explicitly states the audit mode for each registered source.

## Output

Every audited translation should eventually have:
- exact witness refs;
- source/edition version;
- upstream fingerprints;
- alignment spans;
- uncertainty vector;
- difference classes T0-T8;
- stale/current state;
- specialist-review state;
- supersession links;
- EBOM/EIX dependency refs.
