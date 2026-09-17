# Representation-Loss Budget

## Why this exists

Layered reasoning fails if the system applies it only after the evidence has already been flattened.

A caption, summary, translation, dashboard, aggregate, API wrapper or alert may be useful, but each is a transformation of a richer source.

For a purely derived representation R = T(E), the data-processing principle gives the core warning:

**A downstream representation cannot recreate source information that its transformation discarded.**

External annotation can add new information, but that information comes from another evidence source and must carry its own provenance.

## Mandatory pre-analysis question

Before using any transformed evidence:

> What information-bearing layers were lost, approximated, or externally added when this representation was created?

## Operational statuses

- PRESERVED
- APPROXIMATED
- DISCARDED
- ADDED_EXTERNAL
- UNKNOWN

## Claim gating

If a conclusion requires a DISCARDED layer:
- return to the source, or
- cap the claim.

If it requires an APPROXIMATED layer:
- preserve uncertainty.

If an ADDED_EXTERNAL layer is used:
- require an independent evidence reference.

## Importance

This turns the original image lesson into a general guardrail against:
- summary bias;
- translation flattening;
- dashboard overconfidence;
- alert-as-incident errors;
- aggregate-as-causation errors;
- documentation-as-runtime errors;
- metadata-as-object errors.

It also makes LSRP compositional: every processing step can declare what it preserved and what it destroyed.
