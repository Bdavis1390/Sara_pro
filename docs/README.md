# Worldshepherd Documentation Index

This directory contains a mixture of **canonical architecture/governance documents**, **dated evidence artifacts**, **partner/opportunity screening packages**, and **research notes**. Use this index to avoid treating every file as equally authoritative.

## Canonical documents

Read these first:

1. [Worldshepherd Capability Map](WORLDSHEPHERD_CAPABILITY_MAP.md) — portfolio lanes, maturity boundaries, promotion gates.
2. [Claims and Evidence Policy](CLAIMS_AND_EVIDENCE_POLICY.md) — canonical public claim-state rules.
3. [PRE Requirement Delta Schema v1](PRE_REQUIREMENT_DELTA_SCHEMA_V1.md) — demand/evidence schema and fail-closed rules.
4. [Claims Boundary Normalization — 2026-09-01](WS_CLAIMS_BOUNDARY_NORMALIZATION_2026-09-01.md) — exporter claim-boundary behavior and prohibited false-readiness assertions.

## Requirements intelligence / PRE

- [PRE Requirement Delta Schema v1](PRE_REQUIREMENT_DELTA_SCHEMA_V1.md)
- [PRE Release 5 Ingest — 2026-08-25](PRE_RELEASE5_INGEST_2026-08-25.md)
- repository-root `PRE_RELEASE5_INGEST_WAVE2_2026-08-26.md`

PRE documents should preserve a strict separation between:

- source verification;
- forecast/demand classification;
- Worldshepherd capability maturity;
- required experiment/demonstration;
- partner need;
- evidence target.

## Claims / conformance / readiness

Known artifacts include:

- [WS Claims Boundary Normalization — 2026-09-01](WS_CLAIMS_BOUNDARY_NORMALIZATION_2026-09-01.md)
- `WS_INDUSTRY_STANDARDS_CONFORMANCE_BASELINE_2026-09-01.md`
- CI workflows under `../.github/workflows/` covering test/build, CodeQL, release attestation, rollback/recovery, operational resilience, NIST 800-171 precursor work and other evidence checks.

**Important:** internal conformance work does not itself establish government certification, authorization, accreditation, CMMC status, NIST conformity, DFARS satisfaction, or field readiness.

## Provenance / partner screening

Existing dated artifacts include:

- `WS_CI_PARTNER_SCREENING_ARTIFACT_2026-09-01.md`
- `WS_BAE_GEO_SCREENING_CLI_2026-09-01.md`
- `WS_GEO_PROV_BAE_SCREENING_BUNDLE_INDEX_2026-09-01.md`
- `WS_GEO_PROV_FULL_BLOOM_OUTPUT_2026-09-01.md`
- `WS_GEO_PROV_PRE_BAE_INTEGRATION_2026-09-01.md`

Treat these as **dated evidence/screening artifacts**, not timeless architecture specifications.

## CISNET / integration nodes

- [WS CISNET v0.1](WS_CISNET_V0_1.md)
- code/integration material under `../cisnet/`
- `../brd953_xyz_node/`
- `../flamehold_ai_node/`
- `../external_anchor_pilots/`

Each subproject should eventually gain its own local README with purpose, inputs/outputs, run instructions, maturity state, tests, and known limitations.

## Physics / research

- [Worldshepherd Prime Physics Closure v0.9](WORLDSHEPHERD_PRIME_PHYSICS_CLOSURE_V0_9.md)
- additional research notes elsewhere in the repository

Research files must be read through [CLAIMS_AND_EVIDENCE_POLICY.md](CLAIMS_AND_EVIDENCE_POLICY.md). Mathematical consistency, a proposed control law, or a simulation is not equivalent to physical validation.

## OSS contribution work

The repository also contains OSS health/contribution artifacts under `../tools/` and related documentation/patch directories. The required test/build workflow currently checks Python compilation/unit tests for the semantic-health reference work, patch structure, merge-conflict markers, and whitespace integrity.

## Document lifecycle

Use these categories in future filenames/front matter:

| Category | Meaning | Naming guidance |
|---|---|---|
| `CANONICAL` | current governing architecture/policy/specification | stable descriptive filename, version in document |
| `EVIDENCE` | test/output/provenance for a specific configuration | include date/version/commit/test ID |
| `SCREENING` | partner/opportunity/readiness analysis | include target and date |
| `RESEARCH` | hypothesis, literature synthesis, model or simulation | include maturity label |
| `ARCHIVE` | superseded but retained for traceability | move under `docs/archive/` when safe |

## Minimum front matter for new technical documents

```yaml
status: CANONICAL | EVIDENCE | SCREENING | RESEARCH | ARCHIVE
claim_state:
  - IMPLEMENTED IN SOFTWARE
owner: Worldshepherd
version: vX.Y
date: YYYY-MM-DD
supersedes: null
evidence_refs: []
limitations: []
```

## Cleanup roadmap

The current repository contains valuable material but still reflects an accumulation history. The cleanup sequence should be:

1. index existing documents;
2. identify canonical vs superseded versions;
3. add claim-state metadata;
4. move superseded material to an archive without deleting provenance;
5. add local READMEs to active subprojects;
6. consolidate runnable SARA packaging;
7. add evidence manifests that connect claims to tests and CI results.
