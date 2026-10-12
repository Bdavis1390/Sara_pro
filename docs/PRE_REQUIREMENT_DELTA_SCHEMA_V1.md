# Worldshepherd Predictive Requirements Engine — Requirement Delta Schema v1

Status: IMPLEMENTED AS GOVERNANCE/SCHEMA; domain performance remains evidence-gated.

This document mirrors the executable Pydantic models in `deployments/sara_verified_local_v1/worldshepherd_sara/qualification.py`. If this document and the executable model diverge, neither side should be silently treated as canonical; the mismatch must be reconciled explicitly.

## Evidence taxonomy separation
Every `RequirementDeltaRecord` contains independent source and capability maturity fields:

- `source.source_status`
- root-level `capability_status`

Prediction, source confidence and capability maturity remain independent. Prediction never upgrades capability maturity.

### `source.source_status` executable values
- `OFFICIAL_SOURCE_VERIFIED`
- `GOVERNMENT_SECONDARY_VERIFIED`
- `PRIMARY_TECHNICAL_SOURCE`
- `THIRD_PARTY_DISCOVERY_ONLY`
- `CONFLICTING_SOURCES`
- `UNVERIFIED`

### `capability_status` executable values
Serialized records use the executable enum tokens below. Human-facing displays may render equivalent labels with spaces, but machine records must not silently substitute a different token shape.

- `PROVEN_INTERNALLY`
- `IMPLEMENTED_IN_SOFTWARE`
- `SUPPORTED_BY_LITERATURE`
- `SIMULATED_ONLY`
- `HYPOTHESIS`
- `SPECULATIVE_EXTENSION`
- `REQUIRES_LAB_VALIDATION`
- `REQUIRES_PARTNER_VALIDATION`
- `REQUIRES_LEGAL_REVIEW`
- `NOT_CURRENTLY_CLAIMED`
- `NOT_APPLICABLE`

### Demand class executable values
- `CONFIRMED_DEMAND`
- `EMERGING_DEMAND`
- `WORLDSHEPHERD_FORECAST`

### Forecast horizon executable values
- `0-90D`
- `3-12M`
- `12-24M_PLUS`

## Requirement Delta Record
The executable `RequirementDeltaRecord` is flat except for the nested `source` record.

```yaml
requirement_delta_id: PRE-RD-YYYY-NNNN  # runtime requires at least four trailing digits
demand_class: CONFIRMED_DEMAND | EMERGING_DEMAND | WORLDSHEPHERD_FORECAST
source:
  title:
  agency:
  url:
  solicitation_or_topic:
  source_status: OFFICIAL_SOURCE_VERIFIED | GOVERNMENT_SECONDARY_VERIFIED | PRIMARY_TECHNICAL_SOURCE | THIRD_PARTY_DISCOVERY_ONLY | CONFLICTING_SOURCES | UNVERIFIED
  retrieved_utc:
statement:
recurrence:
forecast_horizon: 0-90D | 3-12M | 12-24M_PLUS
affected_lanes: []
existing_capability: []
capability_status: []
missing_capability: []
experiment_or_demonstration_needed: []
partner_needed: []
evidence_target: []
likely_future_programs: []
claims_boundary: []
```

### Capture readiness
The executable `capture_ready()` method returns false when `source.source_status` is any of:

- `UNVERIFIED`
- `THIRD_PARTY_DISCOVERY_ONLY`
- `CONFLICTING_SOURCES`

A source being capture-ready does not make the associated capability proven, validated or deployable.

## Qualification Evidence Record
Canonical evidence chain:

`requirement -> test -> environment/configuration -> inputs/outputs -> metrics/uncertainty -> result -> negative evidence -> provenance -> identified-human review -> supersession state`

### Evidence scope executable values
- `SOFTWARE`
- `SIMULATION`
- `PHYSICAL`
- `ADMINISTRATIVE`

### Result executable values
- `PASS`
- `FAIL`
- `INCONCLUSIVE`

```yaml
qualification_id: WS-QE-YYYY-NNNN  # runtime requires at least four trailing digits
requirement_id:
test_id:
evidence_scope: SOFTWARE | SIMULATION | PHYSICAL | ADMINISTRATIVE
capability_status: PROVEN_INTERNALLY | IMPLEMENTED_IN_SOFTWARE | SUPPORTED_BY_LITERATURE | SIMULATED_ONLY | HYPOTHESIS | SPECULATIVE_EXTENSION | REQUIRES_LAB_VALIDATION | REQUIRES_PARTNER_VALIDATION | REQUIRES_LEGAL_REVIEW | NOT_CURRENTLY_CLAIMED | NOT_APPLICABLE
environment_digest:
configuration_digest:
inputs: []
outputs: []
metrics: []
uncertainty: []
result: PASS | FAIL | INCONCLUSIVE
rationale:
negative_evidence: []
software_commit:
executed_utc:
operator:
physical_validation_performed: false
review:
  status: UNREVIEWED | ACCEPTED | REJECTED
  reviewer:
  reviewed_utc:
supersession:
  state: CURRENT | SUPERSEDED | REVOKED
  superseded_by:
```

## Executable fail-closed behavior
The current model enforces the following directly or through the documented governance contract:

1. Missing or invalid `source.source_status` cannot be represented as a valid source record.
2. `capture_ready()` rejects `UNVERIFIED`, `THIRD_PARTY_DISCOVERY_ONLY` and `CONFLICTING_SOURCES` sources.
3. Prediction never upgrades capability maturity.
4. Generated output without source lineage is unqualified.
5. Physical performance cannot be inferred from software implementation or simulation evidence.
6. A `PHYSICAL` qualification cannot claim `PROVEN_INTERNALLY` unless `physical_validation_performed` is true; the executable validator rejects that combination.
7. Partner brochures, outreach, expressions of interest or public marketing are not partner validation.
8. Internal controls do not establish CMMC, NIST 800-171 conformity, DFARS satisfaction, government authorization, certification, clearance, CUI authorization or operational readiness.
9. Negative and anomalous evidence is retained, not discarded.
10. Superseded evidence remains addressable and auditable through the supersession record.

## Digest and bundle behavior
`canonical_digest()` serializes model data deterministically with sorted JSON keys, compact separators and `allow_nan=False`, then prefixes the SHA-256 digest with `sha256:`.

`compile_qualification_bundle()` emits:

- serialized requirement data;
- serialized evidence records;
- optional evidence graph;
- `capture_ready_source` from the executable source gate;
- the requirement claims boundary; and
- a deterministic `bundle_digest`.

These mechanics establish bounded software provenance behavior only. They do not establish the truth of an external source, physical performance, certification, partner acceptance or operational suitability.
