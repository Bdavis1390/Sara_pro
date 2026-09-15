# GD-04 — W-RMABM G1 Synthetic Demonstration Specification

**Artifact ID:** WS-RMABM-G1-SYNTH-001

**Evidence class:** IMPLEMENTED IN SOFTWARE / SYNTHETIC ONLY / REQUIRES EXTERNAL VALIDATION

## Objective
Demonstrate a bounded, deterministic mission-assurance thread using only synthetic/unclassified data. The test proves software behavior under the fixture; it does not prove operational missile-warning/tracking performance.

## Inputs
Four synthetic observations:
- two fresh, mutually supporting observations from independent synthetic sensor IDs;
- one fresh low-confidence isolated observation;
- one intentionally stale, high-confidence observation that must be excluded from fusion and retained in the audit record.

Three synthetic mission events are supplied out of order, including a communications-degradation event and a stale-sensor event. Deterministic replay must restore sequence order.

## Processing contract
1. Validate source provenance fields, including SHA-256 digests.
2. Order mission events deterministically and reject duplicate sequences.
3. Mark observations older than the configured staleness threshold.
4. Exclude stale observations from the synthetic fusion stage while retaining traceability.
5. Reuse the existing deterministic synthetic fusion component.
6. Apply minimum confidence and independent-source policy thresholds.
7. Require identified human authority for advisory dissemination.
8. Block fire-control cueing, weapon cueing, target designation, intercept, launch, and engagement actions.
9. Hash the canonical replay material and final audit material.

## Frozen G1 acceptance criteria
| Measure | G1 acceptance |
|---|---:|
| Provenance-field completeness | 100% |
| Advisory-policy enforcement | 100% |
| Intentionally stale observation traceability | 100% |
| Same fixture → same replay digest | Required |
| Same fixture → same audit hash | Required |
| Strong two-source track | AUTHORIZED_ADVISORY when identified human authority is present |
| Weak single-source/low-confidence track | HOLD |
| Missing identified human authority | HOLD for all advisory releases |
| Fire-control/engagement-style requested action | BLOCK for all tracks |
| Unknown consequential action | Reject input |
| Degraded-state continuity | Demonstrate bounded processing with stale source excluded |

## Current files
- `worldshepherd_sara/rmabm.py`
- `fixtures/rmabm_g1_synthetic_v1.json`
- `tests/test_rmabm.py`

All paths are relative to `deployments/sara_verified_local_v1/`.

## G2 extension plan
G1 must not be inflated into an operational benchmark. G2 should add:
- randomized but reproducibly seeded source loss, delay, corruption, duplication, disagreement and clock-skew faults;
- larger observation/event volumes and explicit latency/throughput measurements;
- interface-schema mutation/conformance tests;
- provenance tamper tests;
- policy ablation and negative controls;
- independent rerun instructions and evidence bundle;
- comparison against a deliberately provenance-free baseline to quantify overhead and value.

## Safety and claims boundary
The demonstration terminates at governed advisory dissemination. It contains no interceptor kinematics, weapon-target pairing, engagement sequencing, launch logic, fire-control solution, or target-designation algorithm. It is not an operational missile-defense component and must not be represented as one.
