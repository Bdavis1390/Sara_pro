# Finding: Canonical transliteration can be a compatibility layer, not a unique phonological reconstruction

## Result

The translation audit uncovered a cross-corpus design hazard that becomes serious at scale:

> A respected digital corpus may intentionally retain a traditional transliteration for pragmatic reasons even while documenting live scholarly alternatives.

This is not an error by the corpus. It is a compatibility/editorial choice. It becomes a computational error only when downstream systems mistake that display form for a uniquely established ancient pronunciation or root.

## Verified Egyptian examples

### Pyramid

TLA lemma 71780 translates the word as "pyramid" and currently displays `mr`. Its commentary records published arguments for `mḥr`, a published defense of traditional `mr`, and states that TLA keeps `mr` for pragmatic reasons.

The lemma has 92 occurrences in the current corpus.

### Head

TLA lemma 170860 translates `tp` as "head; beginning (of a region)" and records 1,208 occurrences. Its commentary records published arguments for `dp` in Earlier and Late Egyptian, possible earlier `ḏp > dp`, a defense of traditional `tp`, and again states that TLA retains `tp` for pragmatic reasons.

### Osiris

TLA lemma 49461 has 3,124 occurrences. Its commentary records proposals including `(W)sr(.w)` and J. P. Allen's `Js-jr(j)`, while explicitly retaining traditional `Wsjr` for pragmatic reasons.

## Substantial implication

A single-field data model:

`transliteration = "mr"`

silently collapses at least four different things:

1. corpus display convention;
2. scholarly reading hypothesis;
3. phonological reconstruction;
4. lexical/root identity.

Those cannot be treated as equivalent.

At ATIP scale this would contaminate:

- cross-language string matching;
- cognate detection;
- etymology mining;
- sound-symbol comparisons;
- acrostic/numerological analysis;
- name matching;
- reconstruction of ritual pronunciation;
- claimed transmission pathways.

Because high-frequency conventional spellings dominate search and statistical models, the error can amplify rather than average away.

## ATIP correction

ATIP now models a **reading lattice**:

`display_transliteration -> {candidate reading hypotheses}`

with each hypothesis carrying status, evidence, confidence, and provenance.

A surface-string match can generate a candidate, but cannot establish a phonological match, cognacy, root identity, or historical transmission.

## New invariant

`canonical transliteration != uniquely established pronunciation`

and therefore:

`string match != phonological match != cognate != transmission`.

This finding upgrades translation verification into **representation verification**: before asking whether an English translation is right, the system must also ask whether the intermediary transliteration itself is a convention, a reconstruction, or a disputed reading.
