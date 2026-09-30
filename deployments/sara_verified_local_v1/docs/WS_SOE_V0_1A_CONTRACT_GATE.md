# WS-SOE v0.1A Contract Gate

## Scope

WS-SOE v0.1A is a software-only contract gate for a harmless in-memory demonstration action. It separates five canonical records so authorization, execution, observation, evidence, and conformance can be recomputed independently:

1. `Intent`
2. `Decision`
3. `Observation`
4. `EvidenceReceipt`
5. `ConformanceAssessment`

The reference action is `demo.counter.increment` against `demo.counter`, with the first positive trace fixed at **41 → 42**.

## v0.1A invariants

- Canonical serialization is UTF-8 JSON with sorted object keys, compact separators, explicit UTC timestamp normalization, finite numeric values only, and SHA-256 binding.
- An `ALLOW` decision binds the exact canonical hash of one intent. Mutation after authorization invalidates that binding.
- Intent validity is bounded by `issued_at <= execution_time < expires_at`.
- The demo executor accepts exactly `demo.counter.increment`, target `demo.counter`, and `{"delta": 1}`.
- A successfully consumed intent hash cannot execute again in the same executor instance.
- An evidence receipt binds both the intent digest and observation digest. Ordered receipts bind their predecessor by digest.
- Evidence-chain corruption is a `CONFLICT`, not a match.
- Missing authorization, observation, required evidence, or an unsupported conformance rule is `UNKNOWN`, not compliant.
- Old-but-otherwise-valid observations are `STALE`, not a match.
- Observed execution outside authorization is a `VIOLATION`.
- An authorized action with a bound but incorrect outcome is a `DEVIATION`.
- `MATCH`, `DEVIATION`, `VIOLATION`, `UNKNOWN`, `STALE`, and `CONFLICT` are independent enum states. No boolean "compliant" fallback exists.

## Evidence derivation

For a valid trace, each stage can be recomputed without trusting a downstream summary:

- authorization: recompute `sha256(canonical(Intent))` and compare with `Decision.intent_hash`;
- execution observation: recompute the intent hash and compare with `Observation.intent_hash` plus exact action/target;
- evidence: recompute `sha256(canonical(Observation))`, verify `EvidenceReceipt.observation_hash`, and verify predecessor linkage;
- conformance: recompute the supplied contract hashes and derive the state from the explicit rule set.

`ConformanceAssessment` records the independent decision, observation, and evidence digests used for that assessment.

## Adversarial acceptance tests

The v0.1A tests include exact-intent mutation, replay, target substitution, expiry-boundary execution, stale observation, evidence-chain corruption, an explicit `UNKNOWN != MATCH` guard, and positive `41 → 42` conformance. They also exercise distinct `DEVIATION` and `VIOLATION` outcomes and assert that all six states remain present.

## Claims boundary

What this gate can demonstrate when its tests pass:

- deterministic software serialization and digest binding for the five v0.1A contracts;
- fail-closed exact-intent and expiry checks in the demo executor;
- in-process replay rejection for already-consumed intent hashes;
- digest-linked software evidence receipts;
- non-collapsing six-state conformance classification for the bounded demo rule.

What v0.1A does **not** claim:

- production hardening or distributed replay protection;
- digital signatures, PKI, HSM, TPM, Secure Boot, remote attestation, or hardware roots of trust;
- certification, accreditation, CMMC/NIST compliance, or any legal/compliance status;
- fleet-scale behavior, persistence guarantees, Byzantine consensus, or cross-host ordering;
- safety approval for consequential autonomy, weapons, vehicles, medical systems, or other real-world actuation;
- physical validation of any Worldshepherd research claim.

Those are later validation gates, not implied by a passing v0.1A software test suite.
