# Worldshepherd Predictive Requirements Engine — Requirement Delta Schema v1

Status: IMPLEMENTED AS GOVERNANCE/SCHEMA; domain performance remains evidence-gated.

## Evidence taxonomy separation
Every record MUST contain independent `source_status` and `worldshepherd_capability_status` fields.

### source_status
- OFFICIAL_SOURCE_VERIFIED
- GOVERNMENT_SECONDARY_VERIFIED
- PRIMARY_TECHNICAL_SOURCE
- THIRD_PARTY_DISCOVERY_ONLY
- CONFLICTING_SOURCES
- UNVERIFIED

### worldshepherd_capability_status
- PROVEN INTERNALLY
- IMPLEMENTED IN SOFTWARE
- SUPPORTED BY LITERATURE
- SIMULATED ONLY
- HYPOTHESIS
- SPECULATIVE EXTENSION
- REQUIRES LAB VALIDATION
- REQUIRES PARTNER VALIDATION
- REQUIRES LEGAL REVIEW
- NOT CURRENTLY CLAIMED
- NOT_APPLICABLE

## Requirement Delta Record
```yaml
requirement_delta_id: PRE-RD-YYYY-NNNN
demand_class: CONFIRMED_DEMAND | EMERGING_DEMAND | WORLDSHEPHERD_FORECAST
source:
  title:
  agency:
  url:
  solicitation_or_topic:
  source_status:
  retrieved_utc:
requirement:
  statement:
  recurrence:
  forecast_horizon: 0-90D | 3-12M | 12-24M_PLUS
  affected_lanes: []
worldshepherd:
  existing_capability: []
  capability_status: []
  missing_capability: []
readiness:
  experiment_or_demonstration_needed: []
  partner_needed: []
  evidence_target: []
  likely_future_programs: []
claims_boundary: []
```

## Qualification Evidence Record
Canonical chain:
`requirement -> test -> configuration -> result -> uncertainty -> pass/fail -> provenance -> identified-human review`

```yaml
qualification_id: WS-QE-YYYY-NNNN
requirement_id:
test_id:
environment_digest:
configuration_digest:
inputs: []
outputs: []
metrics: []
uncertainty: []
result: PASS | FAIL | INCONCLUSIVE
rationale:
negative_evidence: []
provenance:
  software_commit:
  executed_utc:
  operator:
review:
  status: UNREVIEWED | ACCEPTED | REJECTED
  reviewer:
  reviewed_utc:
supersession:
  state: CURRENT | SUPERSEDED | REVOKED
  superseded_by:
```

## Fail-closed rules
1. Missing source status => record cannot become a capture requirement.
2. Prediction never upgrades capability maturity.
3. Generated output without source lineage is unqualified.
4. Physical performance cannot be inferred from software implementation.
5. Partner brochures/outreach are not partner validation.
6. Internal controls do not establish CMMC, NIST 800-171, government authorization, certification, clearance, or operational readiness.
7. Negative and anomalous evidence is retained, not discarded.
8. Superseded evidence remains addressable and auditable.
