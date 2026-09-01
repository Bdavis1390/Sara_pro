# Worldshepherd Geospatial Provenance PRE/BAE Integration — 2026-09-01

Status: `INTERNAL DESIGN / SIMULATED SOFTWARE EVIDENCE ONLY / REQUIRES EXTERNAL VALIDATION`

This document binds the environmental-resilience intake/design workstream into the Worldshepherd/SARA project without promoting any unvalidated capability claim.

## Integration target

`WS-GEO-PROV-001A` is a synthetic replay package for environmental/geospatial evidence handling. Its purpose is to demonstrate:

1. dataset registration and hash-based provenance;
2. baseline/comparison period tracking;
3. change-detection event representation;
4. null-control retention;
5. uncertainty labeling;
6. human-review gating;
7. BAE-facing screening overlay with explicit non-validation boundary.

It is not a restoration claim, emergency-response claim, BAE validation claim, DOE validation claim, CMMC/NIST conformity claim, or hardware field-performance claim.

## PRE records

| Record | Class | Purpose |
|---|---:|---|
| `PRE-ENVIRONMENTAL-BASELINE-018` | `EMERGING DEMAND` | Prepare for auditable geospatial baselines, uncertainty, null controls, and human-reviewed response decisions. |
| `PRE-BAE-GEOSPATIAL-PROVENANCE-019` | `WORLDSHEPHERD FORECAST` | Package geospatial/environmental state as mission-context provenance for BAE screening, not as partnership evidence. |
| `PRE-RD-2026-0020` | `EMERGING_DEMAND` | Code-level Requirement Delta identifier used by `worldshepherd_sara.geo_provenance`. |

`PRE-RD-2026-0020` is intentionally used in code to avoid collision with existing PRE compiler IDs already present in the repository.

## Worldshepherd asset mapping

| Asset | Role |
|---|---|
| SARA | Orchestrates intake, evidence records, reviewer disposition, and audit chain. |
| ECHO SENTINEL LINK | Preserves dataset, sensor, imagery, configuration, and result provenance. |
| PRIME SENTINEL | Blocks consequential escalation until policy and human-review gates pass. |
| OVERWATCH | Displays map layers, uncertainty, null controls, source status, and review state. |
| Autonomous sensing/control | Alerting and monitoring only; no unsupervised field action. |
| Software/database workflows | Stores source records, change events, evidence graphs, BAE overlays, and replay manifests. |
| DOE/national-lab pathways | Potential external validation and environmental/resilience research alignment. |
| BAE campaign | Mission-state provenance angle for distributed sensing, C5ISR, digital engineering, and resilient infrastructure. |

## BAE evidence map

| Field | Value |
|---|---|
| BAE lane | C5ISR, distributed sensing, mission engineering, digital engineering, resilient infrastructure |
| Worldshepherd asset | SARA + ECHO + PRIME + OVERWATCH |
| Current maturity | Internal software/design evidence; synthetic replay only |
| Missing validation | Independent replay, signed bundle, field-calibrated data, BAE-specific integration test, supplier-compliance evidence |
| Proposed demo | Environmental disruption scenario with degraded data, source disagreement, human review, replay manifest, and sanitized evidence bundle |
| Likely value | Shows evidence discipline for heterogeneous sensing and uncertain mission-state data |
| Strongest BAE path | RIVETS, ADAPT/ADAMS, Virtual Proving Ground-style plugfest, Mission Advantage screening |

## Acceptance gates

`BAE_SCREENING_READY_DESIGN` requires:

- `claims-boundary.md` or equivalent claims-boundary section;
- replay manifest or deterministic synthetic fixture;
- audit/event chain with source/configuration/result hashes;
- interface assumptions;
- null-control and uncertainty reporting;
- threat model;
- SBOM/build-provenance plan;
- NIST/CMMC/DFARS gap map;
- external validation route.

Blocked claims:

- `BAE_VALIDATED`
- `BAE_INTEREST_CONFIRMED`
- `CMMC_CERTIFIED`
- `NIST_800_171_CONFORMANT`
- `HARDWARE_FIELD_VALIDATED`
- `DOE_VALIDATED`
- `FIELD_RESTORATION_PERFORMANCE_PROVEN`

## Code artifact

The module `worldshepherd_sara.geo_provenance` provides:

- `EnvironmentalSourceRecord`
- `ChangeDetectionEvidence`
- `BAEGeoEvidenceOverlay`
- `build_environmental_baseline_requirement()`
- `build_geo_prov_bundle()`

The pytest file `tests/test_geo_provenance.py` verifies:

- PRE demand class and synthetic capability status;
- null-control preservation;
- BAE missing-validation map;
- SHA-256 provenance requirements;
- human-review rationale enforcement;
- rejection of false BAE validation language.

## Claims boundary

The package is designed to strengthen Worldshepherd partner-readiness discipline. It does not establish external reproduction, BAE adoption, government acceptance, operational suitability, classified access, CMMC/NIST conformity, or environmental field performance.
