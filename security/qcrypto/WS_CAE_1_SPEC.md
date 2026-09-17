# WS-CAE-1 — Canonical Authority Envelope

Status: **Worldshepherd Draft Specification v0.1**
Date: 2026-09-13
Scope: defensive post-quantum migration, authority abstraction, interoperability, and evidence.

## 1. Purpose

WS-CAE-1 defines a chain-neutral control contract for persistent authority whose authentication mechanisms may be replaced without changing the authority identity. It is intentionally independent of any one blockchain, wallet, custody provider, HSM, or signature algorithm.

The specification does **not** define a new cryptographic primitive, signature scheme, threshold signature, wallet, transaction format, or consensus protocol. It standardizes the control surface around existing mechanisms such as native rekeying, address aliases, programmable validators, account abstraction, custody policy engines, and future native PQ authorization.

The design goal is:

> persistent authority with replaceable cryptography, versioned policy, recoverability, evidence, and explicit claims boundaries.

This follows the crypto-agility principle that cryptographic algorithms must be replaceable while preserving secure operation. NIST CSWP 39upd1 is the primary external agility reference. NIST NCCoE's Migration to PQC project is the primary interoperability/benchmarking reference. IETF ML-DSA and SLH-DSA identifiers should be used where standardized encodings exist.

## 2. Claims boundary

Conformance with WS-CAE-1 MUST NOT be represented as any of the following unless separately demonstrated:

- post-quantum consensus;
- post-quantum validator security;
- post-quantum bridge security;
- post-quantum stablecoin or issuer administration;
- production wallet certification;
- independent security certification;
- authorization to move live value;
- proof that a cryptographically relevant quantum computer exists.

A conforming authority envelope MAY protect an account or custody authorization domain while the underlying chain remains classically authenticated elsewhere.

## 3. Terminology

**Authority ID** — stable identifier for the controlled authority domain. It survives authenticator rotation.

**Authenticator** — a cryptographic mechanism or externally managed signing identity used to satisfy an authorization policy.

**Authenticator Set** — versioned collection of authenticators eligible under a policy.

**Policy** — versioned authorization rules applied to an authority ID. Policy may express quorum or weighted approval without requiring scheme-specific threshold cryptography.

**Adapter** — chain- or custody-specific mapping from WS-CAE-1 semantics into a native mechanism such as rekeying, address aliasing, programmable validation, native account abstraction, or a custody policy engine.

**Recovery Commitment** — pre-positioned, versioned recovery reference whose operation is independently governed and testable.

**Evidence Binding** — immutable or tamper-evident reference connecting an authority change, review result, or conformance result to its evidence record.

**Replay Domain** — context binding that prevents an authorization decision from being treated as valid outside its intended chain, authority, policy version, or operation domain.

## 4. Normative envelope

A WS-CAE-1 authority record MUST contain the following logical fields. Serialization may be JSON, CBOR, protobuf, or another deterministic representation, provided the field semantics are preserved.

```text
version
  spec: "WS-CAE-1"
  profile_version: integer

authority
  authority_id: stable opaque identifier
  chain_id: chain / custody domain identifier
  adapter_class: implementation class

authentication
  authenticator_set_version: integer
  authenticators[]:
    authenticator_id
    algorithm_family
    algorithm_identifier
    status
    provider_scope

policy
  policy_version: integer
  policy_class
  explicit_human_approval_required: boolean
  minimum_independent_algorithm_families: integer
  minimum_independent_provider_scopes: integer

recovery
  recovery_version: integer
  commitment_present: boolean
  exercise_status

domain_binding
  chain_binding_present: boolean
  authority_binding_present: boolean
  policy_binding_present: boolean
  replay_domain_present: boolean

evidence
  evidence_binding_present: boolean
  review_state
  claims_state
```

An implementation MAY add fields, but MUST NOT reinterpret the semantics of required fields.

## 5. Algorithm identifiers

Where IETF or NIST identifiers exist, implementations SHOULD use standardized identifiers rather than private names. Relevant external references include:

- NIST FIPS 204 / ML-DSA;
- NIST FIPS 205 / SLH-DSA;
- RFC 9881 for ML-DSA X.509 identifiers;
- RFC 9909 for SLH-DSA X.509 identifiers;
- active IETF JOSE/COSE work for SLH-DSA and corresponding standardized serialization work.

WS-CAE-1 does not require a specific PQ algorithm. Algorithm agility is normative; algorithm choice is profile-specific.

## 6. Conformance levels

### CAE-C0 — Documented Authority

Minimum:
- stable authority identifier documented;
- adapter class documented;
- claims boundary present.

C0 is inventory only and provides no deployment-readiness claim.

### CAE-C1 — Crypto-Agile Authority

Requires C0 plus:
- replaceable authenticator mechanism;
- versioned authenticator set;
- versioned policy;
- chain/authority binding;
- explicit human approval policy.

C1 demonstrates that authority identity is no longer permanently coupled to one signing algorithm.

### CAE-C2 — Recoverable and Domain-Bound

Requires C1 plus:
- pre-positioned recovery commitment;
- replay-domain binding;
- evidence binding;
- recovery procedure documented and exercised in a non-production environment.

### CAE-C3 — Diversified High-Value Authority

Requires C2 plus:
- at least two independent cryptographic algorithm families for the high-value profile;
- provider diversity where practical;
- fail-closed behavior when the required diversity policy cannot be satisfied.

A typical profile MAY use a lattice-based operational path and a hash-based reserve path. WS-CAE-1 does not mandate those families.

### CAE-C4 — Independently Reviewed Live Adapter

Requires C3 plus:
- live chain/custody adapter support;
- independent review of the complete adapter and authorization path;
- critical review findings closed;
- monitoring/pause control demonstrated;
- recovery exercise passed against the live adapter in a non-value or explicitly bounded environment.

C4 does not itself authorize live-value execution.

### CAE-C5 — Bounded-Canary Eligible

Requires C4 plus:
- bounded-value policy defined externally;
- deployment expiry/change window defined;
- immutable evidence capture enabled;
- separate explicit human execution approval required;
- execution receipt treated as evidence, not as authorization.

C5 means **eligible for a separately authorized bounded canary**. It does not execute one.

## 7. Canonical authority intent

A WS-CAE-1 implementation SHOULD express an authorization request as an algorithm-independent intent object containing at least:

```text
spec_version
authority_id
chain_id
adapter_class
policy_version
authenticator_set_version
operation_class
intent_nonce
expiry_or_validity_window
evidence_context
```

The intent object MUST NOT depend on a single signature algorithm's native encoding. Chain-specific transaction data belongs below the adapter boundary.

The adapter MUST bind the canonical intent to the chain-native operation before authorization evidence is accepted.

## 8. Policy separation

WS-CAE-1 strongly recommends separating:

1. member/authenticator verification; and
2. authorization/quorum policy.

This allows cryptographic authenticators to rotate without redesigning the authorization policy. A native multi-crypto policy layer, programmable validator, or custody policy engine may satisfy this requirement if the separation is explicit and reviewable.

Scheme-specific threshold cryptography MAY be used but is not required for conformance.

## 9. Algorithm diversity

For CAE-C3 and above, the high-value profile MUST support at least two cryptographically independent algorithm families unless an explicit risk acceptance is recorded.

The intent is to avoid a cryptographic monoculture in which a single mathematical break invalidates both routine authorization and recovery/reserve authorization.

Independence claims MUST name the families and MUST NOT infer independence merely from different parameter sets of the same scheme.

## 10. Provider diversity

For institutional profiles, provider diversity SHOULD be used where practical. Two keys hosted by the same control plane are not automatically independent merely because they use different algorithms.

Provider diversity is an operational-resilience control, not a cryptographic proof.

## 11. Recovery

Recovery MUST be pre-positioned before the primary authenticator is considered suspect.

A CAE-C2+ recovery design MUST:
- be versioned;
- be bound to the same authority ID;
- have a separately reviewable authorization policy;
- have an exercise status;
- produce evidence when exercised;
- not silently downgrade claims about the underlying chain.

## 12. Adapter classes

The initial registry recognizes:

- `NATIVE_REKEY` — native account remains stable while authorization key changes;
- `ADDRESS_ALIAS` — persistent address resolves to replaceable authentication state;
- `PROGRAMMABLE_VALIDATOR` — smart-account or contract validator controls authentication;
- `NATIVE_ACCOUNT_ABSTRACTION` — protocol-level programmable account authentication;
- `CUSTODY_POLICY_ENGINE` — external custody/HSM policy layer controlling an authority domain;
- `PRE_PROTOCOL_VAULT` — application-layer vault protecting assets before protocol-wide PQ migration;
- `OTHER_REVIEW_REQUIRED` — extension requiring explicit documentation.

Adapter registration does not imply deployment maturity.

## 13. Chain profile semantics

A chain profile MUST separately declare:

- whether the stable-authority mechanism is live;
- whether PQ authorization is live;
- whether the policy/quorum layer is live;
- whether wallet/tooling interoperability has been validated;
- whether consensus/validator authentication is PQ;
- whether independent review exists.

Roadmap items MUST NOT be promoted to live capability.

## 14. Evidence model

Every conformance claim C1 or higher MUST include an evidence bundle containing:

- implementation identifier/version;
- profile version;
- adapter class;
- source/evidence references;
- test result summary;
- review state;
- unresolved blockers;
- claims label;
- timestamp;
- immutable/tamper-evident digest or repository reference where practical.

Worldshepherd claims-control labels remain applicable. External evidence alone does not upgrade a Worldshepherd implementation to internally proven or externally certified status.

## 15. Test-vector philosophy

WS-CAE-1 test vectors validate **control semantics**, not cryptographic primitives. They test:

- stable identity across authenticator-set changes;
- policy-version changes;
- rejection of missing recovery at C2+;
- rejection of one-family profiles at C3+;
- rejection of roadmap capability as live capability;
- preservation of the consensus-layer claims boundary;
- requirement for independent review at C4+;
- requirement for separate human execution approval at C5.

Cryptographic known-answer tests belong to the underlying standardized algorithm implementation.

## 16. Initial implementation mapping

Current public evidence supports the following broad mapping, subject to each ecosystem's own maturity claims:

- **Algorand**: live native PQ accounts and live rekey semantics support a strong `NATIVE_REKEY` adapter foundation; native multi-crypto institutional policy is roadmap work rather than assumed live capability.
- **Sui**: address aliases establish the stable-identity/key-replacement pattern; native PQ account authentication is tracked separately from the live alias substrate.
- **Ethereum**: account abstraction is live at the application layer; EIP-8141 describes a stronger native account-abstraction/key-rotation direction, while the Ethereum PQ roadmap treats execution-layer migration as incremental.

These mappings are evidence classifications, not endorsements or certifications.

## 17. Interoperability objective

The objective of WS-CAE-1 is that two independent implementations can consume the same authority profile and agree on:

- authority identity;
- adapter class;
- authenticator-set version;
- algorithm-family diversity state;
- policy version;
- recovery state;
- review state;
- conformance level;
- unresolved claims boundary.

They do not need to share the same blockchain or signing provider.

## 18. External alignment

WS-CAE-1 is intended to complement, not replace:

- NIST PQC standards;
- NIST crypto-agility guidance;
- NIST NCCoE PQC interoperability/benchmarking work;
- IETF algorithm identifier and JOSE/COSE serialization standards;
- chain-native account-abstraction and PQ migration designs.

## 19. Versioning

Breaking semantic changes require a new major specification identifier. Additive fields and new adapter registry entries may be introduced by profile-version increments if backward compatibility is maintained.

## 20. Current maturity

This document is a **Worldshepherd draft interoperability specification** and requires independent external review before it should be represented as an industry standard. Its value is the testable common control model and conformance language, not any claim of standards-body adoption.
