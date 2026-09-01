# WS-GEO-PROV full-bloom output gate — 2026-09-01

Status: `INTEGRATION_TARGET / CI_REQUIRED`

This document records the second integration step for the Worldshepherd environmental/geospatial provenance lane. The prior PR made `worldshepherd_sara.geo_provenance` code-addressable. This step wires that module into the PRE full-bloom evidence compiler so the CI evidence build emits a concrete qualification bundle.

## Output artifact

`ws-pre-bloom` now emits:

```text
geo_prov_qualification_bundle.json
```

The bundle is added to:

- `qualification_index.json` under `bundle_digests.geo_prov`
- ECHO evidence custody storage
- custody verification
- the capability readiness ledger input set
- `bloom_extensions` as `geo_provenance_replay_bundle`

## Claims boundary

This output remains bounded to:

```text
INTERNAL SOFTWARE EVIDENCE / SIMULATED REPLAY / REQUIRES EXTERNAL VALIDATION
```

It does not claim:

- land-restoration performance
- emergency-response authority
- BAE validation, approval, endorsement, certification, or adoption
- DOE validation
- CMMC/NIST conformity
- hardware/platform performance
- external reproduction
- classified access or supplier approval

## PRE record

Primary generated requirement:

```text
PRE-RD-2026-0020 — environmental baseline and geospatial provenance readiness
```

Generated test:

```text
WS-GEO-PROV-001A
```

Generated evidence status:

```text
Evidence scope: SIMULATION
Capability status: SIMULATED_ONLY
Negative evidence retained: field validation / external reproduction / BAE validation NOT_PERFORMED
```

## BAE readiness value

The output supports a BAE-screening-safe proposition only:

> Worldshepherd can package heterogeneous geospatial/environmental evidence as a replayable, claims-controlled mission-context provenance bundle.

The strongest BAE pathway remains RIVETS / ADAPT-ADAMS / Virtual Proving Ground-style plugfest / Mission Advantage screening, subject to independent validation and supplier-readiness work.

## CI verification target

The full gate must pass before this step is treated as merged evidence infrastructure:

- pinned dependency installation
- operations policy validation
- package compile
- unit/API tests
- PRE full-bloom evidence compilation
- deployment verifier
- destructive backup/restore
- operational snapshot
- observable release identity
