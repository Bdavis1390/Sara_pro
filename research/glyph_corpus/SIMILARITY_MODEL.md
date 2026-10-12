# Glyph Similarity Model — structural match without provenance collapse

The corpus must not produce a single seductive "similarity score" that silently turns resemblance into history. It therefore computes separate evidence axes and enforces claim ceilings.

## Evidence axes

### A. Structural Match (SM)

Measures what can be seen without assigning meaning:

- primitive geometry
- topology / crossings / containment / branching
- orientation and handedness
- relative order / hierarchy
- repetition counts
- proportions and measured ratios
- co-occurring motifs

Recommended normalized form:

`SM = 0.15*G + 0.25*T + 0.15*O + 0.10*H + 0.10*C + 0.10*R + 0.15*CO`

where:

- `G` geometry
- `T` topology
- `O` order/hierarchy
- `H` handedness/orientation
- `C` count agreement
- `R` measured ratio agreement
- `CO` co-occurrence/context pattern

Topology is weighted above primitive geometry because circles, triangles, lines and crescents are independently common.

### B. Historical Connection Support (HCS)

Measures whether a visual parallel can plausibly reflect transmission/shared tradition:

- chronology compatibility
- geographic/contact plausibility
- documented borrowing or transmission
- semantic/function match
- source independence/quality
- intermediate forms in an evolutionary chain

No structural score may substitute for HCS.

### C. Quantitative Encoding Support (QES)

Used only when someone claims that geometry encodes physical, astronomical or biological quantities:

- measurements reproducible across source copies
- units/definitions specified before fitting
- ratio selected before looking at target constants
- error bounds reported
- comparison against random and alternative constants
- out-of-sample replication on another artifact/copy

Post-hoc numerical fitting is not quantitative evidence.

### D. Organizational Association Support (OAS)

For Freemasonry, Bavarian Illuminati or any other organization, score separately:

- object explicitly catalogued to organization
- organization-issued or member-used artifact
- primary-text documentation of symbol
- curatorial/scholarly attribution
- merely appears in later popular culture

A symbol common to religion, state iconography, alchemy and Freemasonry is not organization-specific merely because Masons also used it.

## Claim ceilings

| Available evidence | Maximum permissible statement |
|---|---|
| High SM only | "strong visual/structural correspondence" |
| High SM + semantic match | "structural and semantic parallel" |
| + chronology/contact plausibility | "possible historical relationship" |
| + documented intermediate/transmission evidence | "supported historical transmission" |
| explicit primary/curatorial organization link | "documented organizational association" |
| reproducible measurement + preregistered model + controls | "supported quantitative correspondence" |

Never jump directly from high SM to shared origin, secret transmission, physical causation or organizational authorship.

## Common-motif down-weighting

Use inverse-corpus-frequency weighting. A circle, straight line, cross, square, crescent or triangle has little discriminative power in isolation. Compound topology has more value.

Conceptually:

`weight(motif) = log((N + 1) / (frequency(motif) + 1))`

This suppresses "both contain a triangle" matches and rewards rarer combinations such as:

- two alternating curves around an axis
- fixed crossing count
- fixed lower-to-upper station order
- unusual co-occurrence with named text

## Order-aware comparison

If a diagram has `n` ordered stations, test the observed order score against shuffled versions of the same motifs. This distinguishes "same inventory" from "same relational program."

Required output:

- observed order score
- permutation null distribution
- empirical p-value
- effect size
- number of tested comparisons

When scanning many artifacts, correct for multiple testing (for example Benjamini-Hochberg false-discovery-rate control). A one-in-a-thousand coincidence is unsurprising after millions of comparisons.

## Chronology and contact gate

For proposed transmission A -> B:

1. A must plausibly predate the relevant form of B.
2. A and B need a credible path of contact/transmission or documented intermediary.
3. Later copies must not be used as evidence for ancient transmission unless their dependence is known.
4. Modern syncretic sources are excluded from training when testing ancient-to-ancient origin hypotheses.

If chronology fails, transmission support is zero even when SM is high.

## Independent-invention control

Every cross-cultural match must be compared against the probability that the motif arose independently from:

- simple geometry
- human/animal anatomy
- common celestial observations
- weaving/knotting/architecture
- tool constraints
- writing ergonomics
- symmetry preference
- repeated counting/calendrical needs

The simpler and more functional the shape, the stronger this alternative explanation becomes.

## Negative controls

Each research wave must contain:

1. shuffled motif orders
2. geometrically similar but semantically unrelated artifacts
3. same-culture artifacts from unrelated functions
4. same-period artifacts from unrelated regions
5. modern decorative material

A method that "discovers" deep connections in all controls is rejected as non-discriminating.

## Source-independence rule

Ten websites repeating one nineteenth-century drawing are one source lineage, not ten confirmations. Track citation ancestry and duplicate imagery. Independent confirmation requires genuinely independent observations, artifacts or scholarship.

## Special rule: current Sound/Light/Frequency diagram

Test at least four competing models in parallel:

- **TANTRIC MODEL:** chakra/tattva + ida/pingala/sushumna lineage.
- **WESTERN ESOTERIC MODEL:** Masonic/Hermetic/alchemical motif reuse.
- **MODERN SYNTHESIS MODEL:** deliberate twentieth-century combination of several traditions.
- **QUANTITATIVE MODEL:** geometry/count/spacing encodes non-trivial physical or astronomical ratios.

No model wins by having the most evocative story. It wins only by making predictions that survive source chronology, topology, quantitative measurement and negative controls.

## First falsification campaign

For the 100-item pilot:

- identify at least 10 high-SM cross-cultural matches;
- subject each to chronology/contact, semantic and independent-invention tests;
- require at least 3 negative controls per candidate;
- record rejected matches permanently;
- publish both retained and rejected hypotheses.

The objective is not maximum number of connections. The objective is a system that can distinguish a meaningful connection from a compelling coincidence.
