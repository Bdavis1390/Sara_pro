# GD-04B — W-RMABM G2 Synthetic Fault Campaign

**Status:** G2 INTERNAL TEST ARTIFACT / SYNTHETIC ONLY / EXTERNAL VALIDATION REQUIRED

## Purpose
Extend the frozen G1 mission-assurance demonstration with reproducible fault injection focused on data quality, provenance/lineage integrity, human authorization, and policy-boundary behavior.

This campaign does not add missile-intercept, weapon-target pairing, launch, engagement, or fire-control functionality.

## Seeded campaign
The first campaign uses an explicit random seed so the same fixture and seed produce the same fault plan and result set. Initial faults are:

1. observation delay sufficient to test stale-source handling;
2. confidence reduction;
3. observation/source loss;
4. duplicated observation identifier to test lineage rejection;
5. removal of identified human authority;
6. attempted prohibited fire-control action to verify policy blocking.

## Acceptance criteria
- Same fixture + same seed produces an identical fault plan.
- Same fixture + same seed produces identical result records and audit hashes where runs are accepted.
- Duplicate observation IDs are rejected before synthetic fusion.
- No fault variant can transform a prohibited consequential action into `AUTHORIZED_ADVISORY`.
- Missing human authority yields zero authorized advisory releases.
- A delayed source that exceeds the staleness threshold remains traceable in the result.
- Every accepted run remains inside `AUTHORIZED_ADVISORY`, `HOLD`, or `BLOCK` decision states.

## Initial implementation
- `deployments/sara_verified_local_v1/worldshepherd_sara/rmabm_faults.py`
- `deployments/sara_verified_local_v1/tests/test_rmabm_faults.py`

## Next G2 increments
After the initial campaign passes clean CI, extend with:
- seeded packet/event duplication and reordering;
- source disagreement and clock-skew fixtures;
- provenance-tamper verification using bound source bytes/manifests rather than digest-format checks alone;
- scale/latency/throughput measurements;
- policy-ablation negative controls;
- provenance-enabled versus provenance-disabled overhead/traceability comparison;
- independently runnable evidence bundle.

## Claims boundary
A successful G2 campaign is evidence of deterministic software behavior under synthetic faults only. It is not evidence of operational missile-warning/tracking performance, classified-environment suitability, BAE/SDA/SSC integration, government acceptance, or regulatory/cyber certification.
