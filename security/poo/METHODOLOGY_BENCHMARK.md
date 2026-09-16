# Worldshepherd PoO V3 — Comparative Methodology Benchmark

**Benchmark date:** 2026-09-15  
**Status:** INTERNAL COMPARATIVE ASSURANCE BENCHMARK — NOT GLOBAL SUPERIORITY, NOT CERTIFICATION

## Why this exists

The purpose of this benchmark is to test whether Worldshepherd PoO V3 adds technical-assurance properties that are absent from narrower ownership/authentication mechanisms in common use. It is not intended to declare PoO categorically "better than humans" or superior to mature standards as a whole.

A valid comparative claim must name the exact dimensions being compared. The benchmark intentionally hard-codes `global_superiority_established = false`, `standards_compliance_established = false`, `legal_superiority_established = false`, and `external_validation_established = false`.

## Current reference baselines

The following official specifications define important pieces of today's identity, wallet-control, credential, and token-ownership landscape:

| Reference | What the source establishes | Source |
|---|---|---|
| ERC-4361 / Sign-In with Ethereum | Standard off-chain authentication for Ethereum accounts using structured signed messages, domain binding, nonces, time fields, and ERC-1271 support for contract accounts. | https://eips.ethereum.org/EIPS/eip-4361 |
| ERC-1271 | Standard signature validation method for smart-contract accounts. | https://eips.ethereum.org/EIPS/eip-1271 |
| ERC-721 | Standard non-fungible token interface including `ownerOf` and transfer events/state. | https://eips.ethereum.org/EIPS/eip-721 |
| W3C Verifiable Credentials Data Model 2.0 | W3C Recommendation for cryptographically secure, privacy-respecting, machine-verifiable issuer/holder/verifier credentials, including validity, status, evidence, and extensibility. | https://www.w3.org/TR/vc-data-model/ |
| W3C DID Core / DID 1.1 | Identifier/controller/verification-method architecture for decentralized identifiers; DID 1.1 is a 2026 Candidate Recommendation Snapshot. | https://www.w3.org/TR/did-1.1/ |
| OpenID4VP 1.0 | Final protocol for requesting and presenting credentials with nonce/session protections. | https://openid.net/specs/openid-4-verifiable-presentations-1_0.html |

These references are **complementary baselines**, not strawmen. PoO should interoperate with mature standards where appropriate instead of replacing them merely to be different.

## Two comparison baselines

The executable benchmark intentionally uses two different models.

### Narrow account-authentication baseline

This model represents a wallet/account-authentication mechanism. It is useful for asking whether PoO adds custody/provenance/state-assurance properties beyond proving control of an account.

### Generous current-practice composite upper bound

`modeled_current_practice_composite_profile()` is deliberately harder. It is **not one deployed system**. It gives current human/technical practice collective credit for capabilities available across wallet authentication, on-chain ownership state, VC/DID/OpenID credential systems, institutional custody/audit controls, concurrency controls, and authoritative legal registries.

It therefore credits current practice with:

- identity and asset binding;
- challenge/response control;
- custody evidence and custody history;
- provenance;
- freshness and revocation;
- ownership lineage/history;
- conflict detection and stale-write protection;
- durable audit evidence;
- human approval controls;
- standards interoperability;
- multiple independent implementations;
- production deployment; and
- legal recognition where authoritative systems supply it.

Under this deliberately generous model, PoO V3 does **not** dominate current practice overall. Its current modeled technical additions narrow to two constructions:

1. **exact semantic COC digest binding** — the ownership claim commits the exact Control/Custody Verification evidence object used by the state transition; and
2. **coupled ownership/custody lineage** — PoO and COC predecessor lineages must advance together as one state-transition invariant.

Those are candidate technical advantages to validate externally. They are not proof of global superiority.

## What PoO V3 adds in its current internal model

The internal implementation separately tests:

- asset and claimant binding;
- PoW, PoC (Proof of Concept), COC (Control/Custody Verification), and PoS as fail-closed independent predicates;
- challenge-response control evidence;
- exact semantic COC digest binding inside the PoO claim;
- title/provenance reference binding without declaring legal title;
- freshness and revocation;
- independent PoO and COC predecessor lineages that must advance together;
- fork/cycle/conflict detection;
- optimistic-concurrency / stale-writer rejection at the registry-candidate layer;
- durable ECHO/PRIME/SARA/OVERWATCH evidence through the native SARA outbox; and
- explicit human-approval and non-execution boundaries.

Against a narrow account-authentication model, PoO is stronger on several selected assurance dimensions. Against the generous current-practice composite, the modeled advantage is intentionally much narrower: exact COC commitment and coupled PoO/COC lineage.

That statement does **not** imply that PoO is globally superior to SIWE, ERC-1271, ERC-721, VC/DID, OpenID, institutional custody systems, legal registries, or human adjudication.

## Known areas where current practice is stronger

PoO V3 currently lacks evidence that mature systems already possess in important dimensions:

1. **standards interoperability** — no conformance profile for VC 2.0, DID 1.1, OpenID4VP, ERC-4361, ERC-1271, or ERC-721 has been demonstrated;
2. **independent implementation** — no separately developed external implementation has reproduced the protocol behavior;
3. **formal verification** — invariants are regression/model tested, not machine-proved;
4. **production deployment** — no long-duration production reliability, throughput, latency, operational-cost, or incident dataset exists;
5. **external cryptographic review** — collaborator review is being requested but has not yet been received;
6. **legal recognition** — no legal-title or government-registry authority is claimed;
7. **human factors** — usability, recovery burden, false-positive/false-negative rates, and operator error need empirical testing;
8. **economic design validation** — PoW/PoS parameters and incentives have not been proven optimal or Sybil-resistant in production; and
9. **privacy analysis** — COC and provenance references require explicit minimization/selective-disclosure design before sensitive deployments.

## Triple-check methodology

Worldshepherd treats the core methodology as internally complete only when all three primary classes pass on the same implementation state:

1. **Protocol invariants** — exhaustive fail-closed predicate testing, semantic digest mutation testing, dual-lineage/fork/replay/stale-writer tests, plus a bounded scheduler over competing transfer/recovery candidates.
2. **Native integration** — SARA audit-adapter regressions prove bounded ECHO → PRIME → SARA → OVERWATCH evidence and reject authority escalation.
3. **Comparative assurance** — a non-weighted feature-dominance check shows that the candidate is never weaker on the explicitly selected dimensions and strictly stronger on at least one.

### Additional cross-language reproducibility check

Shared vectors in `security/poo/interop/poo_v3_vectors.json` cover a linked genesis → transfer → recovery sequence across COC, PoO, transfer, and recovery digests. The Python implementation and a JavaScript reference verifier must reproduce the exact same SHA-256 values.

This can establish only:

`INTERNAL_SECOND_LANGUAGE_REPRODUCTION`

It does **not** establish an independently developed implementation because both implementations were created within the same Worldshepherd development effort.

Even after all internal layers pass, the maximum claims remain internal engineering evidence. They are still **not** external validation, production readiness, standards compliance, legal superiority, or a global "better than current human systems" conclusion.

## Current honest comparative conclusion

The methodology is designed to permit the following statement once its exact-head tests pass:

> Worldshepherd PoO V3 is internally demonstrated to add exact COC-evidence commitment and coupled ownership/custody lineage to the modeled current-practice composite, while current practice remains stronger in interoperability, independent implementation, production maturity, and legal recognition.

The methodology is specifically designed to reject the broader statement that PoO is globally better than current human systems.

## External collaborator challenge

Issue #320 is the public adversarial-review surface. External contributors are invited to:

- break COC semantic binding;
- break dual PoO/COC lineage;
- find a concurrency sequence that defeats stale-writer protection;
- independently reproduce shared vectors in another implementation; or
- map PoO/COC onto VC/DID/OpenID/SIWE/ERC-1271 primitives without duplicating mature standards.

A failing test or counterexample is considered a successful review contribution.

## Next external-validation targets

- independent cryptographic review of COC/domain separation and proof composition;
- second implementation from a separate team/language;
- standards mapping and adapter prototypes for VC/DID/OpenID and SIWE/ERC-1271;
- property-based and model-based state-machine testing;
- formal specification of lineage and compare-and-swap invariants;
- performance/failure benchmarks under concurrent writers and partial audit delivery;
- privacy/threat-model review; and
- legal/domain-specific integration only through authoritative external title systems.
