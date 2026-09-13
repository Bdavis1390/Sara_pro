# WS-CAE-1 Conformance & Interoperability Matrix

Status: Draft v0.1

This matrix turns the WS-CAE-1 specification into a review checklist. It is descriptive and does not authorize signing, wallet access, or asset movement.

## Conformance levels

| Level | Minimum evidence |
|---|---|
| CAE-C0 | Stable authority identifier, adapter class, explicit claims boundary |
| CAE-C1 | C0 + replaceable authenticator, versioned authenticator set, versioned policy, chain/authority binding, human approval policy |
| CAE-C2 | C1 + pre-positioned recovery, replay-domain binding, evidence binding, recovery exercise in a non-production environment |
| CAE-C3 | C2 + at least two independent cryptographic algorithm families for the high-value profile, plus fail-closed diversity policy |
| CAE-C4 | C3 + live adapter support, independent review, critical findings closed, monitoring/pause demonstration, adapter recovery exercise |
| CAE-C5 | C4 + externally defined bounded-canary policy, deployment expiry/change window, immutable evidence capture, separate execution approval |

## Mandatory claims boundary

Every conformance statement must separately disclose whether the following are demonstrated:

| Domain | Separate claim required? |
|---|---|
| Account / vault authorization | Yes |
| Consensus / validator authentication | Yes |
| Bridge authorization | Yes |
| Stablecoin / issuer administration | Yes |
| Custody / HSM integration | Yes |
| Wallet interoperability | Yes |
| Independent external review | Yes |
| Live-value execution authorization | Yes |

No WS-CAE-1 level automatically upgrades another row.

## Initial ecosystem adapter mapping

### Algorand

Public evidence supports a strong `NATIVE_REKEY` foundation:

- native Falcon account support is live;
- account rekey semantics preserve account identity while changing authorization;
- PQ institutional/multi-crypto policy is tracked separately from current account-layer deployment;
- consensus PQ work remains a separate roadmap item.

Review target: determine which WS-CAE-1 controls can be satisfied today using native account/rekey capabilities and which require the planned multi-crypto policy layer.

### Sui

Public evidence supports an `ADDRESS_ALIAS` agility foundation:

- address aliases preserve account identity while authentication evolves;
- the PQ design uses ML-DSA for native-account direction and SLH-DSA for high-value vault diversity;
- native PQ account authentication must be classified separately by actual deployment state.

Review target: map alias state, validator/authenticator versioning, and vault diversity into the canonical authority model without promoting roadmap state to production state.

### Ethereum

Public evidence supports `PROGRAMMABLE_VALIDATOR` today and a stronger `NATIVE_ACCOUNT_ABSTRACTION` direction:

- account abstraction permits programmable authorization at the application layer;
- Ethereum's PQ roadmap explicitly treats signature agility as a gradual migration mechanism;
- EIP-8141 describes protocol-native key rotation / account abstraction direction;
- PQ signature precompiles and consensus migration remain distinct milestones.

Review target: establish one WS-CAE-1 authority profile that can survive movement from ERC-4337-style application-layer control to future native account abstraction without changing the authority identity semantics.

## Interoperability questions for independent reviewers

1. Can two implementations derive the same authority ID semantics without sharing the same chain?
2. Can both implementations distinguish authenticator-set version from policy version?
3. Can an authenticator rotate without changing the authority identifier?
4. Can recovery be exercised without silently weakening the claims boundary?
5. Can a policy require independent algorithm families without requiring one scheme-specific threshold signature?
6. Can a roadmap-only chain feature remain explicitly non-live in the profile?
7. Can evidence be bound to a profile version in a tamper-evident way?
8. Can the adapter preserve chain/domain separation so authorization evidence is not portable across unintended domains?
9. Can external reviewers reproduce the declared conformance level from the evidence bundle alone?
10. Can the system represent `account authorization is PQ` while `consensus is not PQ` without ambiguity?

## External standards alignment checklist

- NIST FIPS 204 identifiers used for ML-DSA where applicable.
- NIST FIPS 205 identifiers used for SLH-DSA where applicable.
- RFC 9881 used for ML-DSA X.509 identifier conventions where X.509 is relevant.
- RFC 9909 used for SLH-DSA X.509 identifier conventions where X.509 is relevant.
- JOSE/COSE serialization should follow IETF standards/drafts rather than private encodings when available.
- Crypto-agility controls should be assessed against NIST CSWP 39upd1 principles.
- Interoperability methodology should be compatible with the NCCoE PQC migration project's interoperability-and-benchmarking philosophy.

## Worldshepherd maturity rule

`SPECIFICATION PUBLISHED INTERNALLY` is not the same as `INDUSTRY STANDARD`.

The current defensible state is:

**IMPLEMENTED IN SOFTWARE / DRAFT SPECIFICATION / REQUIRES INDEPENDENT REVIEW / REQUIRES PARTNER VALIDATION**

External adoption, standards-body consideration, or independent implementation must be evidenced before stronger claims are made.
