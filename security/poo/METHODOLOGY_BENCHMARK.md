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
| W3C Verifiable Credentials Data Model 2.0 | W3C Recommendation for cryptographically secure, privacy-respecting, machine-verifiable issuer/holder/verifier credentials. | https://www.w3.org/TR/vc-data-model/ |
| W3C DID Core / DID 1.1 | Identifier/controller/verification-method architecture for decentralized identifiers; DID 1.1 is a 2026 Candidate Recommendation Snapshot. | https://www.w3.org/TR/did-1.1/ |
| OpenID4VP 1.0 | Final protocol for requesting and presenting credentials. | https://openid.net/specs/openid-4-verifiable-presentations-1_0-final.html |

These references are **complementary baselines**, not strawmen. PoO should interoperate with mature standards where appropriate instead of replacing them merely to be different.

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

On a **selected set consisting of custody evidence, exact COC binding, provenance binding, dual lineage, conflict detection, stale-writer protection, durable audit provenance, and explicit human approval**, the current PoO V3 model can be described as stronger than a modeled single-wallet authentication baseline when all relevant tests pass.

That statement does **not** imply that PoO is globally superior to SIWE, ERC-1271, ERC-721, VC/DID, OpenID, institutional custody systems, legal registries, or human adjudication.

## Known areas where PoO V3 is not yet stronger

PoO V3 currently lacks evidence for:

1. **standards interoperability** — no conformance profile for VC 2.0, DID 1.1, OpenID4VP, ERC-4361, ERC-1271, or ERC-721 has been demonstrated;
2. **independent implementation** — no separately developed second implementation has reproduced the protocol behavior;
3. **formal verification** — invariants are regression-tested, not machine-proved;
4. **production deployment** — no long-duration production reliability, throughput, latency, operational-cost, or incident dataset exists;
5. **external cryptographic review** — collaborator review is being requested but has not yet been received;
6. **legal recognition** — no legal-title or government-registry authority is claimed;
7. **human factors** — usability, recovery burden, false-positive/false-negative rates, and operator error need empirical testing;
8. **economic design validation** — PoW/PoS parameters and incentives have not been proven optimal or Sybil-resistant in production;
9. **privacy analysis** — COC and provenance references require explicit minimization/selective-disclosure design before sensitive deployments.

## Triple-check methodology

Worldshepherd treats the methodology as internally complete only when all three layers pass on the same implementation state:

1. **Protocol invariants** — exhaustive fail-closed predicate testing, semantic digest mutation testing, lineage/fork/replay/stale-writer tests.
2. **Native integration** — SARA audit-adapter regressions prove bounded ECHO → PRIME → SARA → OVERWATCH evidence and reject authority escalation.
3. **Comparative assurance** — a non-weighted feature-dominance check shows that the candidate is never weaker on the explicitly selected dimensions and strictly stronger on at least one.

Even after all three pass, the maximum internal label is:

`INTERNAL_TRIPLE_CHECK_COMPLETE`

It is still **not** external validation, production readiness, standards compliance, legal superiority, or a global "better than current human systems" conclusion.

## Next external-validation targets

- independent cryptographic review of COC/domain separation and proof composition;
- second implementation from a separate team/language;
- standards mapping and adapter prototypes for VC/DID/OpenID and SIWE/ERC-1271;
- property-based and model-based state-machine testing;
- formal specification of lineage and compare-and-swap invariants;
- performance/failure benchmarks under concurrent writers and partial audit delivery;
- privacy/threat-model review; and
- legal/domain-specific integration only through authoritative external title systems.
