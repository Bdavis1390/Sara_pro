# WS-CAE Competitive Differentiation Matrix

Status date: 2026-09-13

## Purpose

This document makes the WS-CAE research position falsifiable by comparing it with the strongest adjacent public work found in the current prior-art review.

The claim under evaluation is narrow: WS-CAE is a cross-chain authority-agility conformance profile for persistent digital-asset authority during post-quantum migration. It is not a new signature scheme, wallet standard, DLT interoperability standard, or cryptographic inventory format.

## Adjacent work

| Effort | Primary strength | What it clearly covers | Gap relative to WS-CAE's narrow lane |
|---|---|---|---|
| NIST NCCoE Migration to PQC | PQC interoperability and migration practice | Algorithm interoperability, implementation compatibility, benchmarking, discovery | Does not define a cross-chain digital-asset authority-state conformance model |
| NIST CSWP 39upd1 | Crypto-agility lifecycle guidance | Replacing/adapting cryptography while preserving operations | General guidance, not blockchain authority semantics |
| IETF Crypto-Agility Manifest draft | Machine-readable posture publication | CBOM summary, readiness, migration policy, conformance declaration | Describes project cryptographic posture, not persistent account/authority semantics across chains |
| ISO/TS 23516:2026 | Broad DLT interoperability | DLT interoperability framework | Broader scope; no public evidence found of the WS-CAE PQ authority-state maturity model |
| ISO/AWI PAS 26347 | Wallet interoperability | Interoperable protocol between blockchain/DLT wallets, under development | Public project metadata does not show cross-chain PQ authority-state conformance semantics |
| Project Eleven Quantum Vault / libqc | Audited migration implementation | ERC-4337 account abstraction, Bitcoin support, crypto-agile wallet infrastructure | Implementation/reference architecture, not a protocol-neutral conformance vocabulary across unrelated account models |
| LayerQu | Independent readiness measurement | 72-chain readiness scoring, deployed-vs-announced distinctions, migration stages | Measurement framework, not an authority interoperability contract |
| Ethereum EIP-8141 | Native authority abstraction on Ethereum | Native key rotation, programmable validation, off-ramp from ECDSA | Ethereum-specific mechanism, not cross-chain conformance |
| Algorand PQ accounts/rekey | Live native PQ authorization | Native PQ accounts and stable account rekey semantics | Algorand-specific implementation |
| Sui address aliases / PQ roadmap | Stable identity and replaceable authentication | Persistent alias layer and differentiated PQ design direction | Sui-specific mechanism |

## WS-CAE differentiation

WS-CAE combines the following properties in one cross-chain authority profile:

1. persistent authority identity separated from the current authentication algorithm;
2. versioned replaceable authenticators;
3. explicit maturity distinction among roadmap, draft, testnet, and live capability;
4. explicit separation of account/vault authorization from consensus/validator PQ security;
5. policy versioning and recovery state;
6. domain/replay and evidence binding;
7. chain-adapter mapping across unrelated account architectures;
8. a common conformance vocabulary designed to permit independent implementations to reach the same classification.

The current public review did not identify another specification that combines all eight properties in the same narrow digital-asset authority role.

## Claims boundary

This matrix does not prove global novelty or superiority. It is a dated prior-art comparison. A newly discovered public specification can narrow or invalidate the differentiation claim.

No standards-body adoption, certification, production security approval, or external endorsement is claimed.
