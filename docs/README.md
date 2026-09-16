# Worldshepherd Documentation Index

This directory contains a mixture of **canonical architecture/governance documents**, **dated evidence artifacts**, **partner/opportunity screening packages**, and **research notes**. Use this index to avoid treating every file as equally authoritative.

## Canonical documents

Read these first:

1. [Canonical SARA Runtime entry point](../runtime/README.md) — supported repository-level path to the runnable SARA / SSPADAWANZZ local service.
2. [ADR-0001 — Canonical SARA Runtime Location](adr/0001-canonical-sara-runtime.md) — authoritative decision for where the runnable implementation lives and how it is exposed.
3. [Worldshepherd Capability Map](WORLDSHEPHERD_CAPABILITY_MAP.md) — portfolio lanes, maturity boundaries, promotion gates.
4. [Claims and Evidence Policy](CLAIMS_AND_EVIDENCE_POLICY.md) — canonical public claim-state rules.
5. [Active Tasks](operations/ACTIVE_TASKS.md) — the three top-level operating umbrellas and anti-inflation rules.
6. [Repository Freshness Policy](operations/FRESHNESS_POLICY.md) — lifecycle, staleness, reconciliation, supersession and safe-deletion rules.
7. [Latest Repository Freshness Audit — 2026-09-15](operations/FRESHNESS_AUDIT_2026-09-15.md) — dated branch/PR/source-of-truth audit evidence.
8. [PRE Requirement Delta Schema v1](PRE_REQUIREMENT_DELTA_SCHEMA_V1.md) — demand/evidence schema and fail-closed rules.
9. [Claims Boundary Normalization — 2026-09-01](WS_CLAIMS_BOUNDARY_NORMALIZATION_2026-09-01.md) — exporter claim-boundary behavior and prohibited false-readiness assertions.

## Canonical SARA runtime / operator path

The current runnable local implementation is:

```text
../deployments/sara_verified_local_v1/
```

Repository-root operator commands are exposed through:

```text
../scripts/sara.sh
```

Start from a fresh clone with:

```bash
bash scripts/sara.sh setup
bash scripts/sara.sh run
```

The dedicated implementation gate is:

```text
../.github/workflows/sara-verified-local-v1.yml
```

Current historical-to-main reconciliation is retained in:

```text
../deployments/sara_verified_local_v1/docs/WS_QE_2026_ADM_001.md
```

That evidence explicitly distinguishes current local relay-recording behavior from historical external-integration wording. Do not generalize `recorded_local_only` into a third-party delivery or execution claim.

## Repository operations and freshness

The operating source of truth is:

- [Active Tasks](operations/ACTIVE_TASKS.md) — #281 Platform & Assurance, #282 Science & Validation, #283 Growth & Externalization;
- [Freshness Policy](operations/FRESHNESS_POLICY.md) — `CURRENT_CANONICAL`, `ACTIVE`, `DATED_EVIDENCE`, `RECONCILE_REQUIRED`, `SUPERSEDED`, `ARCHIVE`, and `SAFE_DELETE_AFTER_VERIFY`;
- [Freshness Audit — 2026-09-15](operations/FRESHNESS_AUDIT_2026-09-15.md) — dated evidence about branch/PR accumulation and current reconciliation priorities;
- `../tools/repository_freshness.py` — fail-closed static source-of-truth checker;
- `../.github/workflows/repository-freshness.yml` — scheduled/on-change freshness CI gate.

**Age alone is never a deletion criterion.** Preserve unique code, evidence, negative results, source corrections and decision history. Reconcile useful stale-base work forward; archive or delete only after supersession/containment is proven.

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

Time-sensitive opportunity facts require authoritative re-verification before external use; a dated opportunity artifact remains historical evidence even after its facts change.

## Claims / conformance / readiness

Known artifacts include:

- [WS Claims Boundary Normalization — 2026-09-01](WS_CLAIMS_BOUNDARY_NORMALIZATION_2026-09-01.md)
- `WS_INDUSTRY_STANDARDS_CONFORMANCE_BASELINE_2026-09-01.md`
- CI workflows under `../.github/workflows/` covering test/build, CodeQL, SARA Verified Local, release attestation, rollback/recovery, operational resilience, NIST 800-171 precursor work and other evidence checks.

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

Each remaining active subproject should gain its own local README with purpose, inputs/outputs, run instructions, maturity state, tests, and known limitations.

## Physics / research

- [Worldshepherd Prime Physics Closure v0.9](WORLDSHEPHERD_PRIME_PHYSICS_CLOSURE_V0_9.md)
- additional research notes elsewhere in the repository

Research files must be read through [CLAIMS_AND_EVIDENCE_POLICY.md](CLAIMS_AND_EVIDENCE_POLICY.md). Mathematical consistency, a proposed control law, or a simulation is not equivalent to physical validation.

A dated scientific artifact is not automatically stale. Preserve its original assumptions/results and issue a new superseding artifact when later evidence changes interpretation.

## OSS contribution work

The repository also contains OSS health/contribution artifacts under `../tools/` and related documentation/patch directories. The required test/build workflow checks Python compilation/unit tests for the semantic-health reference work, patch structure, merge-conflict markers, and whitespace integrity.

## Architecture Decision Records

ADRs capture repository-level decisions whose reversal should be explicit and reviewable.

- [ADR-0001 — Canonical SARA Runtime Location](adr/0001-canonical-sara-runtime.md)

Future major interface, repository-split, security-boundary and evidence-custody decisions should receive their own ADR rather than living only in chat or README prose.

## Document lifecycle

Use these categories in future filenames/front matter:

| Category | Meaning | Naming guidance |
|---|---|---|
| `CANONICAL` | current governing architecture/policy/specification | stable descriptive filename, version in document |
| `EVIDENCE` | test/output/provenance for a specific configuration | include date/version/commit/test ID |
| `SCREENING` | partner/opportunity/readiness analysis | include target and date |
| `RESEARCH` | hypothesis, literature synthesis, model or simulation | include maturity label |
| `ARCHIVE` | superseded but retained for traceability | move under `docs/archive/` when safe |

Operational lifecycle state is separately governed by [FRESHNESS_POLICY.md](operations/FRESHNESS_POLICY.md).

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

The repository still reflects an accumulation history, but the canonical SARA runtime and freshness doctrine are now explicit. Continue in this order:

1. reconcile active useful branches against current `main`;
2. classify old PRs/branches rather than bulk-close by age;
3. identify canonical vs superseded document versions;
4. add claim-state/lifecycle metadata where ambiguity remains;
5. move genuinely superseded material to archive without deleting provenance;
6. remove duplicate branches only after comparison proves no unique work is lost;
7. add local READMEs to remaining active subprojects;
8. attach evidence manifests to major capability claims;
9. keep CI/action/dependency runtimes on maintained upstream versions through reviewable, gated migrations;
10. record major repository/interface decisions as ADRs.
