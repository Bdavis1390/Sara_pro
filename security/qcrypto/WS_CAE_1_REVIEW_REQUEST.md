# WS-CAE-1 Independent Review Request

Worldshepherd is requesting independent technical review of **WS-CAE-1 — Canonical Authority Envelope**, a draft interoperability specification for crypto-agile and post-quantum account/custody migration.

## What we are asking reviewers to test

1. Is the separation between stable authority identity and replaceable authentication technically coherent across different chains?
2. Are authenticator-set versioning and authorization-policy versioning sufficiently distinct?
3. Does the adapter model map cleanly to native rekeying, address aliases, programmable validators, and native account abstraction?
4. Does the recovery model preserve the same authority identity without silently weakening the claims boundary?
5. Is the algorithm-diversity requirement meaningful without requiring scheme-specific threshold cryptography?
6. Are chain/domain/replay bindings described strongly enough for independent implementations to agree on semantics?
7. Does the conformance ladder prevent roadmap features from being represented as live capability?
8. Does it clearly separate account/vault PQ readiness from consensus/validator PQ readiness?
9. Can a custody provider or HSM policy engine implement the same authority semantics as a blockchain adapter?
10. What minimum evidence should be required before CAE-C4 or CAE-C5 is considered credible?

## What this draft does not claim

WS-CAE-1 is not currently an IETF, NIST, ISO, IEEE, chain-foundation, or other external standard. It does not introduce a new signature algorithm and does not certify any blockchain as quantum safe.

The current Worldshepherd claims state is:

- IMPLEMENTED IN SOFTWARE
- SUPPORTED BY LITERATURE
- DRAFT SPECIFICATION
- REQUIRES INDEPENDENT REVIEW
- REQUIRES PARTNER VALIDATION

## Requested reviewer backgrounds

Useful review can come from:

- blockchain protocol/account-abstraction engineering;
- wallet or custody architecture;
- HSM/KMS integration;
- NIST/IETF PQC implementation;
- cryptographic protocol review;
- security architecture and recovery engineering;
- interoperability/conformance testing.

## Artifacts

- `WS_CAE_1_SPEC.md`
- `WS_CAE_1_CONFORMANCE_MATRIX.md`
- `ws_cae_1_evidence_profile_2026-09-13.json`
- `canonical_authority_envelope.py`
- existing QCRYPTO regression suite

Reviewers are specifically encouraged to identify contradictions, missing controls, unverifiable assumptions, ambiguous terminology, and cases where two independent implementations could interpret the specification differently.
