# Worldshepherd Ancient Text Intelligence Program (ATIP) v0.1

## Evidence-Calibrated Symbolic Intelligence for Ancient Texts, Glyphs, and Translation Verification

**Status:** Public methods and research note
**Version:** 0.1
**Date:** 2026-09-17
**Repository:** Bdavis1390/Sara_pro
**Program issues:** #377, #378, #381, #429, #432

## Abstract

The Ancient Text Intelligence Program (ATIP) is a provenance-first computational framework for analyzing ancient texts, inscriptions, glyph systems, symbolic diagrams, and translation lineages without collapsing visual resemblance, textual structure, historical transmission, semantic interpretation, and physical causation into a single claim.

ATIP was developed from a methodological observation: important information can reside not only in isolated symbols but also in ordering, topology, spatial relationship, repetition, hierarchy, crossings, layout, provenance, and cross-witness variation. The program operationalizes that observation as a falsifiable research architecture.

The framework combines:

- witness-preserving ingestion;
- diplomatic and normalized transcription layers;
- typed evidence graphs;
- information-theoretic sequence diagnostics;
- topology-aware comparison;
- translation-version auditing;
- blind/retrospective benchmark separation;
- known-deciphered positive controls;
- undeciphered negative controls;
- deterministic synthetic nulls;
- false-discovery safeguards;
- explicit claim ceilings;
- specialist-review gates.

ATIP is **not** presented as a universal decipherment engine. Its success criterion is discrimination: recover structure when evidence supports it, preserve uncertainty when the record is ambiguous, detect stale or witness-dependent translations, and refuse polished semantic output when a script remains undeciphered.

## 1. Research question

ATIP tests a general hypothesis:

> Relational, topological, positional, provenance, and multimodal context can carry recoverable information beyond isolated symbol identity.

This is evaluated through controlled ablations and held-out benchmarks rather than by selecting compelling examples after interpretation.

For progressively richer analytical representations:

M0 = symbol identity

M1 = M0 + position

M2 = M1 + neighbor relations

M3 = M2 + topology

M4 = M3 + sequence

M5 = M4 + witness/material/historical context.

The program asks whether held-out restoration, classification, segmentation, or structural prediction improves as these layers are added.

## 2. Evidence ladder

ATIP separates operations that are often conflated:

raw witness
-> diplomatic transcription
-> normalized transcription
-> transliteration
-> segmentation
-> morphology/syntax
-> translation
-> interpretation
-> cross-text hypothesis
-> measurement
-> falsification
-> specialist review
-> claim state.

Each transition requires new evidence. Later analytical layers do not overwrite earlier source layers.

## 3. Non-conflation invariants

The program enforces the following distinctions:

visual resemblance != shared origin

statistical structure != language

language-likeness != decipherment

decipherment != translation

translation != interpretation

shared motif != organizational affiliation

numerical similarity != physical coupling.

Typed graph edges and claim ceilings make these distinctions machine-checkable.

## 4. Corpus architecture

ATIP is federated rather than centralized. Ancient-text resources differ in licensing, authority, data model, image rights, and editorial practice. The system therefore keeps source identity and rights state attached to each ingested layer.

Current or planned source families include:

- Mesopotamian cuneiform;
- Egyptian hieroglyphic, hieratic, and Demotic material;
- Northwest Semitic inscriptions and manuscripts;
- Linear A, Linear B, Cypro-Minoan, and related Aegean scripts;
- Greek and Roman epigraphy and papyri;
- Iranian and Central Asian traditions;
- South Asian inscriptions and manuscripts;
- early East Asian inscriptions and texts;
- Maya and other Mesoamerican writing;
- African and Arabian epigraphic corpora;
- runic, ogham, Iberian, and related European corpora;
- ancient apocalyptic/manuscript traditions including 1 Enoch;
- early-modern Enochian as a historically bounded control corpus.

Undeciphered corpora are retained explicitly as negative controls.

## 5. Epistemic classes

Every benchmark target belongs to one of four classes:

1. **KNOWN_DECIPHERED** — positive controls.
2. **PARTIALLY_CONSTRAINED** — incomplete grammar, disputed readings, damaged witnesses, or inherited glosses.
3. **UNDECIPHERED** — structure analysis permitted; running translation prohibited absent validated decipherment.
4. **SYNTHETIC_NULL** — shuffled, Markov-preserving, layout-preserving, or adversarial controls.

A good system must behave differently on each class.

## 6. Contamination accounting

Large language models may have encountered public historical materials during pretraining. ATIP therefore does not equate session-blind performance with proof of first exposure.

Current contamination classes are:

- **C0_SESSION_BLIND** — target comparator not exposed in the active benchmark.
- **C1_PARTIAL_LEXICON** — non-target lexical evidence allowed.
- **C2_RETROSPECTIVE** — target translation or close paraphrase already seen.
- **C3_EDITORIAL_DEPENDENT** — reconstruction materially depends on inherited glosses.
- **C4_UNKNOWN** — exposure cannot be bounded.

A C0 result is described as session-blind, not "never seen before."

## 7. Statistical diagnostics

The baseline harness currently implements deterministic, interpretable diagnostics including:

- token counts;
- type counts;
- unigram entropy;
- first-order conditional entropy;
- n-gram frequencies;
- repeated subsequences;
- positional profiles;
- exact-count shuffled surrogates;
- first-order Markov surrogates.

For symbol sequence X:

H(X) = -sum_i p_i log2(p_i)

and H(X_t | X_(t-1)) are used as descriptive measures of sequence uncertainty.

These measures do not produce semantic claims by themselves.

## 8. Symbolic Information Graph

ATIP represents evidence with typed nodes and edges.

Example nodes:

- Artifact
- Witness
- Glyph
- Token
- Phrase
- Translation
- Gloss
- Measurement
- Person
- Organization
- Place
- Hypothesis
- Experiment
- ClaimState

Example edges:

- CONTAINS
- ADJACENT_TO
- ABOVE
- CROSSES
- VARIANT_OF
- COPIED_FROM
- TRANSLATED_AS
- GLOSSED_AS
- RESEMBLES
- DOCUMENTED_BY
- POSSIBLE_TRANSMISSION
- MEASURED_AS
- SUPPORTED_BY
- CONTRADICTED_BY
- FALSIFIED_BY

A RESEMBLES edge cannot silently become COPIED_FROM, TRANSLATED_AS, or SUPPORTED_BY.

## 9. Translation Verification Program

ATIP treats translation as a versioned, witness-dependent analytical product rather than a timeless endpoint.

The translation audit tracks:

- exact source witness;
- transcription version;
- lexical alignment;
- grammatical analysis;
- supplied concepts;
- omitted material;
- damaged/restored material;
- competing witnesses;
- superseded readings;
- edition date;
- semantic-role preservation.

Difference classes:

- **T0_STABLE**
- **T1_STYLE**
- **T2_LEXICAL**
- **T3_GRAMMATICAL**
- **T4_WITNESS**
- **T5_RESTORATION**
- **T6_SUPERSEDED**
- **T7_INTERPOLATION**
- **T8_UNRESOLVED**

A smooth English rendering is not treated as verified merely because it is old, famous, or widely reproduced.

## 10. Current translation-audit findings

The first source-level scan indicates a recurring systemic issue: uncertainty encoded in scholarly editions is often lost when texts are quoted as plain English.

Examples under active audit include:

- Linear B records with multiple analyses or readings affected by fragment joins;
- Egyptian texts whose lemma/transliteration state is versioned in modern corpora;
- cuneiform translations containing restored, supplied, uncertain, or untranslatable material;
- papyri whose transcriptions have changed through editorial revision;
- Gāndhārī texts with documented reading corrections;
- 1 Enoch passages dependent on Aramaic, Greek, and Ethiopic witness differences;
- Maya readings subject to ongoing epigraphic revision;
- Dee/Kelley Enochian passages with manuscript, segmentation, gloss, and later ritual-layer drift.

This does **not** imply that ancient-text scholarship is broadly wrong. It demonstrates that translation confidence should be traceable to current witness-level evidence.

## 11. Enochian calibration

Dee/Kelley Enochian is retained as an early-modern calibration corpus, not reclassified as ancient writing.

Its usefulness comes from the survival of manuscript witnesses, character systems, ordered Calls/Keys, table/grid structures, English senses/glosses, later editorial traditions, and later ritual pronunciation systems.

This makes it a useful environment for testing how manuscript evidence, inherited meaning, later normalization, and modern reinterpretation diverge.

## 12. Undeciphered-script guardrail

For an undeciphered control with no validated decipherment, the software claim ceiling is:

**STRUCTURE_ONLY_NO_TRANSLATION**

and attempts to produce a running semantic translation are blocked at the harness layer.

This is a deliberate hallucination test.

## 13. First benchmark cycle

ATIP-CYCLE-0001 is pre-registered with four lanes:

- Linear B retrospective known-script calibration;
- session-blind Enochian holdout;
- Linear A negative control;
- deterministic synthetic nulls.

Reporting includes inventory recovery, entropy and conditional entropy, repeated n-grams, positional regularity, segmentation hypotheses, semantic-role alignment where permitted, unsupported insertions, unresolved residue, null-model performance, contamination class, and claim ceiling.

## 14. Rights and provenance

The program separates rights decisions for metadata, transcription, translation, and images/media.

Publicly viewable content is not assumed reusable. Unclear rights fail closed to reference-only mode.

Diplomatic transcription remains immutable. Normalization, restoration, translation, and interpretation are derivative layers.

## 15. Adversarial controls

The program includes red-team cases intended to create convincing false discoveries:

- random geometric diagrams;
- shuffled historical motifs;
- synthetic ancient-looking inscriptions;
- intentionally planted numerical ratios;
- mislabeled provenance;
- cherry-picked glosses;
- transformed duplicate images.

Success means recognizing real structural similarity while refusing unsupported provenance, semantics, or causation.

## 16. Claim promotion

ATIP uses an evidence ladder rather than rhetorical confidence.

Examples:

- resemblance alone -> hypothesis / structural correspondence;
- repeated statistically nonrandom structure -> internal support only;
- translation -> requires validated script/language evidence and witness attribution;
- transmission -> requires chronology/contact/documentary evidence;
- physical encoding -> requires preregistration, measurement, null controls, and replication;
- extraordinary provenance -> requires independent primary/curatorial evidence.

## 17. What is implemented now

Current repository implementation includes:

- glyph/stela corpus schema;
- topology-aware similarity model;
- Enochian provenance and analysis lane;
- blind/retrospective decipherment protocol;
- translation-difference utilities;
- ATIP canonical ancient-text schema;
- rights-aware source adapter contract;
- deterministic sequence/null diagnostics;
- evidence graph constraints;
- benchmark manifest schema;
- pre-registered first benchmark cycle;
- translation verification engine and audit queue;
- source federation and rights policy.

## 18. What is not yet established

ATIP v0.1 does **not** claim:

- a new decipherment of Linear A, Indus, or other undeciphered scripts;
- supernatural provenance for Enochian;
- universal ancient-symbol transmission;
- a hidden physical constant encoded in the original screenshot;
- validated biological meaning for symbolic helix/weave forms;
- proof that existing scholarly translations are broadly incorrect;
- corpus-scale superiority over established specialist methods.

Those are empirical questions, not conclusions.

## 19. Near-term validation gates

The next publishable empirical milestones are:

1. execute ATIP-CYCLE-0001;
2. freeze predictions before comparator reveal;
3. publish failures as well as successes;
4. complete a 1,000-record provenance-complete pilot;
5. run topology/context ablations;
6. complete targeted translation re-audits;
7. seek epigrapher/linguist review of any novel reading;
8. version and release reproducible benchmark data where rights permit.

## 20. Reproducibility principle

The central publication requirement is:

> A surprising result must be reconstructable from its witness, source version, allowed evidence, frozen prediction, null model, comparator, difference vector, and claim ceiling.

If that chain cannot be reconstructed, ATIP does not treat the result as a defensible discovery.

## 21. Conclusion

ATIP reframes symbolic and ancient-text analysis as an evidence-management problem as much as a pattern-recognition problem.

The program is designed to discover more relationships **while making it harder to promote weak relationships into strong claims**.

Its operating objective is not "find a hidden meaning in everything." It is to expose plausible informational layers, quantify what can be quantified, preserve provenance, compare against nulls and alternatives, and make uncertainty difficult to hide.
