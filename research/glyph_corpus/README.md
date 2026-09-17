# Worldshepherd Global Glyph & Stela Corpus

Status: ACTIVE research program  
Parent issue: #378  
Methodology: #377 Layered Systems Reasoning Protocol (LSRP)

## Mission

Build a provenance-preserving, machine-queryable corpus of glyphs, inscriptions, stelae, tablets, seals, diagrams, ritual/fraternal symbols, astronomical marks, alchemical/esoteric signs, rock art and related symbolic systems, then analyze them using LSRP.

This program deliberately separates visual similarity from historical connection, semantic identity, organizational affiliation and physical causation.

> visual resemblance != shared origin != author intent != organizational affiliation != causal mechanism != quantitative relationship != proof

## Why this exists

The current Sound/Light/Frequency screenshot showed that a literal-only reading can miss information expressed through topology, ordering, weaving, symmetry, hierarchy and cross-scale correspondence. The correction is not to accept every apparent pattern; it is to inspect each plausible layer before promoting or rejecting a hypothesis.

## Analysis stack

Every consequential artifact or glyph is evaluated through ten layers:

1. Literal observation
2. Relational/topological structure
3. Cross-domain correspondence
4. Process/causal-flow hypotheses
5. Multiscale mapping
6. Measurable counterpart
7. Systems integration
8. Testable hypothesis generation
9. Adversarial falsification
10. Evidence classification

## Core distinction

For every proposed connection, store separate evidence for:

- geometric resemblance
- semantic/function resemblance
- chronological overlap
- geographic/contact plausibility
- documented transmission
- later reuse/reinterpretation
- organizational association
- quantitative/measurable correspondence

No single field can silently stand in for the others.

## Program lanes

Initial lanes include Egyptian hieroglyphs; Mesopotamian cuneiform and seals; Maya monuments; Linear B; early Chinese/oracle-bone and historic East Asian scripts; Greek/Roman epigraphy; Scandinavian runes; South Asian symbolic/manuscript systems; alchemical and Hermetic diagrams; documented Masonic/fraternal material; historical Bavarian Illuminati primary texts; **Dee/Kelley Enochian material treated as a Renaissance comparator rather than an ancient corpus**; and modern symbolic diagrams whose older motifs require independent source tracing.

## Repository contents

- `source_registry.yaml` — provenance and access metadata for initial authoritative corpora.
- `glyph_record.schema.json` — canonical machine schema for artifact, glyph/motif, layered reasoning and cross-links.
- `current_screenshot_case.yaml` — decomposition of the present diagram into separately testable motifs/hypotheses.
- `SIMILARITY_MODEL.md` — scoring and guardrails for structural comparison without conflating resemblance and provenance.
- `ENOCHIAN_INTEGRATION.md` — historically fenced integration of Dee/Kelley manuscripts, grids, alphabet, Keys, acoustics and cross-domain hypotheses.
- `enochian_case.yaml` — machine-readable Enochian provenance, observables, falsifiers and comparison tests.
- `enochian_analysis.py` — deterministic grid/sequence statistics for coordinate-preserving transcriptions.
- `test_enochian_analysis.py` — regression tests for those helpers.

## Phase 1 acceptance gates

- 10+ authoritative corpora across 6+ domains registered.
- Canonical schema implemented.
- 100-item pilot distributed across ancient inscriptions, symbolic/ritual material and the modern screenshot.
- Current screenshot decomposed into individual motifs with separate hypotheses.
- Masonic and Bavarian Illuminati claims sourced independently.
- Enochian primary and later-reception layers remain chronologically separated.
- At least 10 cross-cultural visual matches tested for independent invention and chronology/contact failure.
- No claim promoted solely from shape similarity.

## 100-item pilot allocation

| Lane | Target |
|---|---:|
| Egyptian hieroglyph/stela material | 15 |
| Mesopotamian signs/tablets/seals | 15 |
| Maya inscriptions/monuments | 15 |
| Linear B / early alphabetic / classical epigraphy | 15 |
| Early East Asian / runic material | 10 |
| Alchemical/Hermetic diagrams | 10 |
| Documented Masonic/fraternal material | 8 |
| Dee/Kelley Enochian primary material | 7 |
| Historical Illuminati primary-source material | 3 |
| Current screenshot motifs and immediate comparators | 2 |
| **Total** | **100** |

The pilot is intentionally heterogeneous: the similarity engine must survive differences in medium, chronology, culture and semantic function instead of learning a single tradition's iconography.

## Governance

Worldshepherd doctrine remains:

`AI proposes -> human approves -> automation remains bounded -> actions and evidence are logged.`

Symbolic or cross-domain correspondence may generate a hypothesis, but only source evidence and reproducible measurement may promote technical or historical claims.