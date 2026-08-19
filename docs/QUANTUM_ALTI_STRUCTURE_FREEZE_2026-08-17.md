# Worldshepherd QRF — WS-AlTi Physical Structure Freeze Specification

**Date:** 2026-08-17  
**Active gate:** `WS-ALTI-EXT-01`  
**Precondition:** `WS-ALTI-P0-PHYSICAL-STRUCTURE-FROZEN`  
**Current mission evidence stage:** `concept`  
**Current score:** `15/100`  
**Target:** `97/100`

## Purpose

Convert WS-AlTi from a composition/process/IP-stage concept into a reproducible electronic-structure benchmark without inventing atomic coordinates, phase occupancy, or a Hamiltonian from nominal alloy percentages.

A nominal composition such as Al-Ti-Mg-Sc-Zr is **not** a periodic structure. A structure-freeze package must identify actual atomic positions, lattice, ordering, phase/model scope, provenance and immutable digests before downstream DFT, active-space reduction, VQE or resource estimation can be treated as WS-AlTi materials evidence.

The existing Worldshepherd alloy package remains IP/design-stage. This gate deliberately separates that design intent from atomistic evidence.

## Literature-grounded benchmark family

The following phases/models are suitable **candidate references** for building a benchmark family. They are not automatically the final WS-AlTi deposited microstructure.

### A. Aluminum host reference

A periodic fcc-Al host structure establishes the matrix reference for formation/interface/segregation comparisons. The exact structure artifact and provenance must still be frozen and hashed.

### B. L1_2 Al3Sc precipitate reference

Al3Sc is a well-established L1_2 precipitate reference in first-principles studies of Al-Sc and Al-Sc-Zr systems. Use a peer-reviewed or database structure artifact with retained provenance rather than reconstructing coordinates from prose alone.

### C. Al3Zr reference family

Retain phase identity explicitly. Literature distinguishes metastable L1_2-type Al3Zr precipitation behavior from the thermodynamically stable ordered Al3Zr structure. Do not collapse distinct polymorphs into one generic `Al3Zr` label.

For an L1_2 Al3Zr benchmark, one published first-principles surface study identifies the Cu3Au-type cubic structure as `Pm-3m`, with Al on 3c sites and Zr on 1a; that information is useful for cross-checking a retrieved structure but is not a substitute for retaining the actual structure file and source metadata.

### D. Sc-sublattice Ti/Zr substitution models

Published first-principles work on quasi-binary L1_2 `Al3(Sc1-xMx)` reports Ti and Zr preference for substitution on the Sc sublattice and uses special quasirandom structures for disordered quasi-binary models. A separate study evaluated explicit L1_2 `Al3Sc1-xMx` supercells including Zr and Ti substitutions.

Therefore a later WS-AlTi benchmark family may include:

- ordered low-concentration Ti-on-Sc substitution fixture,
- ordered low-concentration Zr-on-Sc substitution fixture,
- combined Sc/Zr/Ti sublattice model,
- SQS model when disorder rather than ordered substitution is the intended physical question.

Each member must be independently frozen; `Ti/Zr substitute on Sc sites` is a modeling rule, not an atomic structure file.

### E. Mg handling

Do **not** place Mg into a site by assumption. Mg may influence matrix/precipitate/interface energetics, segregation or other microstructural behavior, but the WS-AlTi electronic-structure benchmark should only include Mg after a specific physical question and source-supported site/interface model are frozen.

## Required structure-freeze record

`worldshepherd_sara.quantum_alti_structure.PeriodicStructureFreezeRecord` requires:

- `project_id=WS-ALTI`
- concrete `structure_id`
- exact composition of the modeled cell
- phase/model label
- actual structure format: CIF, POSCAR or structured JSON
- SHA-256 of the actual structure file
- source type and source reference
- SHA-256 of retained source/provenance metadata
- 3D periodicity
- space group or explicit low-symmetry label
- six lattice parameters
- atom count
- species counts that sum exactly to atom count
- SHA-256 of a canonical site/species ordering representation
- modeling scope
- `generated_from_composition_only=false`

The validator rejects a manifest without the actual structure file, rejects placeholder values, rejects mismatched file digests, rejects inconsistent site counts, and rejects composition-only coordinate generation.

## Preferred provenance routes

### Route 1 — Materials Project / computed database

Where an appropriate phase exists, retrieve the structure by a verified material identifier using the official Materials Project API or web export. Preserve:

- material ID,
- exported CIF/POSCAR/JSON,
- retrieval date,
- database/provenance fields,
- whether the structure is computed or linked to an external experimental database,
- the exact exported artifact SHA-256.

Do not invent a Materials Project ID. If the desired ordered/SQS substitution model does not exist as a suitable database entry, use another provenance route.

### Route 2 — Peer-reviewed publication supplemental structure

If a paper provides a structure file/supercell definition, retain the exact supplemental artifact, DOI, model definition and digest. If only prose or a figure is available, treat it as design guidance and reconstruct the structure only as a **Worldshepherd-generated model** with an explicit derivation record; do not relabel it as a publisher-supplied structure.

### Route 3 — Worldshepherd-generated structure

A generated model is permitted only when the derivation is reproducible and physically scoped. Retain:

- parent structure digest,
- transformation/substitution algorithm and version,
- random/SQS seed where applicable,
- exact substitutions and site indices,
- cell expansion matrix,
- pre-relaxation structure,
- post-relaxation structure as a distinct artifact,
- software and version,
- every structure digest.

A Worldshepherd-generated model must never be described as experimental structure evidence.

## Reference-computation gate

After the structure is frozen, a classical reference computation must bind to the exact `structure_digest`.

The reference record requires at least:

- electronic-structure code and version,
- method,
- exchange-correlation functional,
- basis/pseudopotential/PAW definition,
- k-point definition,
- spin treatment,
- energy and force convergence thresholds,
- input digest,
- output digest,
- total energy,
- reference kind,
- source/provenance reference.

A later Hamiltonian/active-space artifact must likewise identify which frozen structure and classical calculation produced it.

## Suggested initial benchmark sequence

The recommended sequence is intentionally incremental:

1. **ALTI-STR-A0:** fcc-Al host reference.
2. **ALTI-STR-SC1:** L1_2-Al3Sc reference.
3. **ALTI-STR-ZR1:** L1_2-Al3Zr metastable/reference precipitate model, if that is the chosen precipitation question.
4. **ALTI-STR-ZR-STABLE:** stable Al3Zr polymorph reference when thermodynamic phase competition is in scope.
5. **ALTI-STR-SCTI:** source-supported Ti-on-Sc substitution model.
6. **ALTI-STR-SCZR:** source-supported Zr-on-Sc substitution model.
7. **ALTI-STR-SCTIZR:** combined Sc/Ti/Zr sublattice model or SQS only after the compositional/modeling question is explicitly frozen.
8. **ALTI-STR-MG-*:** Mg-bearing matrix/interface/precipitate models only after a site/segregation hypothesis is specified and sourced.

This family allows Worldshepherd to compare phase/substitution physics without pretending that one tiny periodic cell is the entire spatially graded DED alloy.

## Gate closure rule

`WS-ALTI-EXT-01` must remain open until at least one physically scoped periodic structure is:

1. retained as a real file,
2. provenance-controlled,
3. structurally validated,
4. bound to a reproducible Hamiltonian/reference workflow,
5. identified as a benchmark scope rather than the whole deposited alloy.

A literature citation alone does not close the gate. A composition table does not close the gate. A hand-written Hamiltonian not derived from a frozen structure does not close the gate.

## Current external technical references

- Materials Project structure/API examples: https://docs.materialsproject.org/downloading-data/using-the-api/examples
- Materials Project provenance/API documentation: https://docs.materialsproject.org/downloading-data/using-the-api/getting-started
- Materials Project structure export FAQ: https://docs.materialsproject.org/frequently-asked-questions
- H. Zhang and S. Wang, `The structural stabilities of Al3(Sc1-xMx) by first-principles calculations`, Computational Materials Science 50 (2011) 2162-2166, DOI: 10.1016/j.commatsci.2011.02.024
- `The Effect of Alloying Elements on the Structural Stability, and Mechanical and Electronic Properties of Al3Sc: A First-Principles Study`, Materials 12 (2019) 1539, DOI: 10.3390/ma12091539
- `Electronic and structural properties of low-index L12-Al3Zr surfaces by first-principle calculations`, CALPHAD 66 (2019) 101645, DOI: 10.1016/j.calphad.2019.101645
- `First-principles study on the nucleation and growth mechanisms of Al3Sc and Al3Zr precipitates in aluminum alloys`, Journal of Alloys and Compounds 1077 (2026) 189548, DOI: 10.1016/j.jallcom.2026.189548

Re-verify current database/API behavior before retrieval. Peer-reviewed structures and computed database entries may represent idealized phases rather than the actual additively manufactured microstructure.

## Claims control

This specification closes a **software/governance ambiguity**, not the materials evidence gap. WS-AlTi remains `concept / 15` until actual structure/reference evidence is retained and technically reviewed. A later quantum calculation may supplement electronic-structure analysis; it cannot replace coupon production, microscopy/diffraction, mechanical testing or manufacturing validation.
