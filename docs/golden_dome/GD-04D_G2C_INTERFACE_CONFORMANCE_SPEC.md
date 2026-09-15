# GD-04D — W-RMABM G2C Vendor-Neutral Interface Conformance Specification

**Status:** INTERNAL G2 INCREMENT / SYNTHETIC ONLY / NO PROPRIETARY INTERFACES

## Objective
Demonstrate that W-RMABM can place heterogeneous synthetic records behind a common provenance and policy boundary without assuming or reverse-engineering any government or vendor interface.

## Synthetic interface families
Two intentionally fictional schemas are used:
- `synthetic_alpha` version `1.0`
- `synthetic_beta` version `2026.1`

They encode the same minimal abstract information using different field structures: source/event identity, timestamp, two-dimensional synthetic coordinates, confidence, payload bytes, and claimed SHA-256.

These schema names and structures are Worldshepherd test fixtures only. They do not model BAE Systems, Space Development Agency, Space Systems Command, Rocket Lab, Amazon, Lockheed Martin, Northrop Grumman, York Space Systems, or any other real organization’s proprietary interface.

## Conformance boundary
Before a record can enter the synthetic mission-assurance pipeline, the adapter must:
1. recognize an explicitly supported fictional schema/version;
2. decode the source payload;
3. recompute and verify its SHA-256;
4. validate and normalize required fields;
5. preserve source identity;
6. reject duplicate normalized observation identifiers;
7. emit a standard `ProvenancedObservation` object.

The resulting observations can then use the already bounded W-RMABM quality, provenance, human-authorization, replay, and advisory-only controls.

## G2C acceptance criteria
- Alpha and Beta records representing compatible synthetic observations normalize into the common model and can satisfy the existing two-source advisory policy.
- Unsupported schema versions are rejected.
- Payload tampering is rejected before normalization.
- Duplicate observation identities across schema families are rejected.
- Batch normalization order is deterministic.
- No operational targeting, fire-control, weapon-cueing, launch, interceptor, or engagement functionality is introduced.

## Files
- `deployments/sara_verified_local_v1/worldshepherd_sara/rmabm_interfaces.py`
- `deployments/sara_verified_local_v1/tests/test_rmabm_interfaces.py`

## External-validation path
A G4 evaluator could replace either fictional adapter with an evaluator-approved, unclassified surrogate schema while retaining the common governance core. That substitution—not this synthetic adapter test—would provide evidence of real interface compatibility.

## Claims boundary
Passing this test supports only the claim that Worldshepherd can normalize and provenance-check two heterogeneous fictional schemas under internal CI. It does not establish compatibility with any actual Space Force, SDA, BAE, Rocket Lab, or other operational interface.
