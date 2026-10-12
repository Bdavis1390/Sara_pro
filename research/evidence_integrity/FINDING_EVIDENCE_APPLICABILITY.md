# Finding: Evidence changes require applicability, not just invalidation

## Problem

EBOM correctly propagates an upstream evidence change through its material dependency graph. But treating every descendant as permanently invalid is too coarse.

A source can be:
- corrected,
- revised,
- retracted,
- superseded,
- given a new safety warning,
- newly designated as actively exploited,
- or assigned corrected metadata.

Only some downstream claims may actually depend on the changed portion.

## Existing standards already expose the missing pieces

### W3C PROV

PROV explicitly models revision and invalidation. It gives us a standard vocabulary for "this entity was revised" or "this entity ceased to be valid/usable."

### Crossmark

Crossref's Crossmark service communicates the current status of scholarly content, including corrections, retractions, and updates. It is designed specifically so that a reader can discover changes even after the publication was downloaded.

### PubMed/NLM

NLM creates explicit links between retraction notices and the original publication.

### SPDX VEX

VEX separates "a vulnerability exists" from "this product is actually affected." That distinction is the exact missing mechanism for evidence dependencies.

## Synthesis

The scalable pattern is:

1. **detect source-state change**;
2. **propagate potential impact** through EBOM;
3. **quarantine descendants**;
4. **assess applicability claim by claim**;
5. **release NOT_AFFECTED branches with evidence**;
6. **recompute/review AFFECTED branches**;
7. **record REVALIDATED or WITHDRAWN outcome**.

This avoids both major failure modes:

- silent stale knowledge;
- indiscriminate invalidation of still-correct knowledge.

## General rule

A change event tells us that a source changed.

An EBOM tells us what might depend on it.

An EIX assessment tells us **which dependent claims actually need to change**.

That three-layer architecture is the minimum viable structure for continuous evidence validity at scale.
