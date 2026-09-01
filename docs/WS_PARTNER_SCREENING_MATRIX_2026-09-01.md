# Worldshepherd Partner Screening Matrix — 2026-09-01

## Purpose

This record extends the generic `ws-partner-screening` export path beyond the initial GEO bundle. It adds CI coverage proving that major PRE full-bloom qualification bundles can be converted into sanitized partner-screening packages under the same evidence and claims-boundary controls.

## Covered PRE lanes

The matrix covers the following generated full-bloom bundles:

- `apnt_qualification_bundle.json`
- `ddil_qualification_bundle.json`
- `mission_qualification_bundle.json`
- `fusion_qualification_bundle.json`
- `rf_qualification_bundle.json`
- `cbm_qualification_bundle.json`
- `manufacturing_qualification_bundle.json`
- `edge_qualification_bundle.json`
- `ddil_rejoin_qualification_bundle.json`

Each bundle is exported through both partner presets:

- `BAE_SYSTEMS`
- `GENERIC_PRIME`

## Required preservation checks

For every lane and partner preset, the matrix requires preservation of:

- source bundle digest linkage;
- requirement delta ID;
- test ID;
- evidence scope;
- capability status;
- PASS result;
- partner evidence overlay;
- partner-screening claim boundary;
- artifact digests for every emitted file.

## Claims boundary

This matrix does not upgrade capability maturity. It only verifies that each lane can be transformed into a sanitized partner-screening package.

It does **not** claim:

- partner interest;
- partner endorsement;
- partner adoption;
- BAE validation;
- supplier approval;
- CMMC conformity;
- NIST SP 800-171 implementation;
- DFARS satisfaction;
- CUI/CDI handling authorization;
- classified access;
- DOE validation;
- field performance;
- hardware performance;
- operational authority.

Current maturity remains:

`INTERNAL SOFTWARE EVIDENCE / SCREENING PACKAGE EXPORT / REQUIRES EXTERNAL VALIDATION`

## BAE campaign relevance

This adds a practical BAE-readiness improvement: the screening package path is no longer a GEO-only prototype. APNT, DDIL, mission replay, sensor fusion, RF discrepancy, CBM+/digital twin, manufacturing lineage and edge benchmark evidence can now be checked against the same package-export controls.

That strengthens screening discipline and partner-readiness packaging. It does not establish any BAE relationship or validation.
