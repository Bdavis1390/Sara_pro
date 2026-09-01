# WS Claims Boundary Normalization — 2026-09-01

## Purpose

Normalize partner-screening claim-boundary acceptance so PRE qualification bundles can be exported directly when they already include explicit non-claim language.

## Change

The `ws-partner-screening` exporter now accepts explicit non-claim markers such as:

- `does not`
- `do not`
- `not`
- `no`
- `without`
- `unless`
- `never`

This covers early PRE bundle wording such as `No physical APNT, shipboard, sensor-accuracy, or Navy operator-performance claim` without requiring a synthetic matrix-only sentence.

## Verification

The matrix test now exports native PRE full-bloom bundles directly for:

- APNT
- DDIL campaign
- mission replay
- sensor fusion
- RF discrepancy
- CBM+ / digital twin
- manufacturing lineage
- edge benchmark
- DDIL partition / rejoin

The focused unit test pins acceptance of `No ... claim` language.

## Preserved restrictions

This normalization does not weaken the screening boundary. The exporter still rejects prohibited assertions including partner validation, BAE validation, supplier approval, CMMC certification, NIST conformity, DFARS satisfaction, classified access, DOE validation, field validation, and similar false-readiness claims.

Current maturity remains:

`INTERNAL SOFTWARE EVIDENCE / SCREENING PACKAGE EXPORT / REQUIRES EXTERNAL VALIDATION`
