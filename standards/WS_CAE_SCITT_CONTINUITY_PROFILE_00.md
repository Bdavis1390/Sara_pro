# WS-CAE Cryptographic Continuity Statement Profile for SCITT — Candidate -00

Status: research contribution candidate. Not an IETF Internet-Draft and not adopted by BGIN, NIST, IETF, or any other standards body.

## Abstract

This document describes a candidate SCITT application profile for statements about the cryptographic continuity of digital-asset systems. It defines a content-addressed manifest for the current authority, migration, recovery, dependency, and evidence state of a stable subject, together with state transitions, transparency checkpoints, and portable verification bundles.

The profile does not define cryptographic algorithms, cryptocurrency transactions, consensus, custody, wallets, or a Transparency Service. It is intended to be carried by existing SCITT mechanisms.

## 1. Problem statement

Digital-asset systems may retain economic or operational identity while replacing authenticators, signature algorithms, recovery mechanisms, validators, bridges, custodians, or other cryptographic dependencies. Project-specific prose makes these transitions difficult to compare and audit across heterogeneous systems.

The profile separates:

1. stable subject identity;
2. immutable content-addressed state identity;
3. explicit state transitions;
4. append-only transparency checkpoints;
5. external receipts/witnesses.

## 2. Requirements language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, NOT RECOMMENDED, MAY, and OPTIONAL are to be interpreted as described in BCP 14 when, and only when, they appear in all capitals.

## 3. Continuity manifest

A conforming manifest MUST identify a stable subject and MUST include sufficient fields to distinguish the current cryptographic state from the stable subject identity.

The reference profile currently carries:

- `subject_id`;
- `subject_type`;
- `version`;
- `as_of`;
- `authority_model`;
- `implementation_maturity`;
- `protocol_commitment_state`;
- `pq_authorization_state`;
- `consensus_pq_state`;
- `crypto_agility_state`;
- `recovery_state`;
- `dependencies`;
- `evidence`.

A manifest MUST fail validation if the subject identifier is empty, the subject type is outside the supported vocabulary, or no evidence reference is supplied.

Evidence references MUST use HTTPS in the current reference implementation. A valid manifest does not establish that an evidence claim is true; evidence truth remains an external review responsibility.

## 4. Content identity

The reference implementation serializes the manifest as UTF-8 JSON with object keys sorted lexicographically, no insignificant whitespace, and unescaped non-ASCII characters. The resulting bytes are hashed with SHA-256 and represented as:

`sha256:<64 lowercase hexadecimal characters>`

The content ID identifies the exact state, not the stable subject.

Independent implementations SHOULD reproduce the frozen interoperability vectors before claiming compatibility.

## 5. State transitions

A continuity transition MUST link two different content IDs belonging to the same stable subject.

A transition carries:

- stable `subject_id`;
- `previous_content_id`;
- `new_content_id`;
- transition reason;
- effective time;
- optional evidence references.

The current reason vocabulary includes algorithm migration, authority rotation, dependency change, recovery change, governance change, evidence update, and an explicit extension category.

A no-op transition or transition between different stable subjects MUST be rejected.

## 6. Lineage and resolution

A lineage starts from a declared genesis content ID.

A resolver MUST fail closed when it detects:

- multiple subject identifiers in one lineage;
- two successors from the same prior state unless the application explicitly defines fork handling;
- multiple predecessors for one state;
- states unreachable from genesis;
- a cycle to genesis;
- zero or multiple terminal states;
- an unavailable or invalid terminal manifest;
- mismatch between the terminal manifest content ID and lineage tip.

The WS-CAE reference resolver accepts only a single terminal state.

## 7. Transparency tree

The reference transparency structure is an append-order Merkle tree over content IDs.

Leaf hash:

`SHA-256(0x00 || ASCII(content_id))`

Internal node hash:

`SHA-256(0x01 || left_hash || right_hash)`

The empty-tree hash is `SHA-256("")`.

The tree split rule uses the largest power of two strictly smaller than the current non-trivial tree size. Inclusion proofs MUST reproduce the declared checkpoint root.

## 8. Linked checkpoints

A checkpoint contains tree size and root hash. A later checkpoint MAY also name a prior tree size and root.

When prior content IDs are available, the current sequence MUST extend the prior sequence as an exact prefix before the reference implementation accepts the linked checkpoint.

This -00 candidate deliberately uses explicit prefix verification rather than claiming a compact logarithmic consistency-proof scheme.

## 9. Witness receipts and equivocation

Applications MAY require multiple independently verified receipts for the same checkpoint.

Duplicate issuer identities MUST NOT increase an N-of-M witness threshold.

If one issuer is observed presenting different root hashes for the same tree size, that issuer MUST be flagged for equivocation and its receipts MUST NOT count toward the agreeing set in the reference policy.

Cryptographic verification of receipts is external to this metadata policy and is expected to use the selected SCITT/Transparency Service or other accepted attestation mechanism.

## 10. SCITT statement mapping

The reference media type is currently:

`application/vnd.ws-cae.cryptographic-continuity+json`

This is a research/vendor media type and is not asserted to be IANA registered.

`WS-CAE-SCITT-CONTINUITY-1` preserves:

- issuer;
- observation time;
- stable subject identifier/type;
- manifest content ID;
- state version/date;
- continuity claims;
- dependencies;
- evidence references.

`WS-CAE-SCITT-CONTINUITY-CHECKPOINT-1` carries a continuity transparency checkpoint and optional predecessor metadata.

Signing, registration, receipt production, and Transparency Service policy remain SCITT-layer concerns and are not redefined here.

## 11. Proof bundle

`WS-CAE-CONTINUITY-PROOF-BUNDLE-1` binds one content ID to:

- a Merkle inclusion proof;
- tree size/index;
- checkpoint root;
- optional predecessor checkpoint metadata.

A verifier MUST reject a bundle when the content ID, proof root/tree size, or checkpoint do not match.

## 12. Interoperability vectors

The repository publishes `ws_cae/examples/continuity_interop_vectors.json` containing:

- one canonical manifest content ID;
- roots for tree sizes 0 through 5;
- an inclusion path for a non-power-of-two tree.

These vectors are intended as cross-implementation reproduction targets.

## 13. Security considerations

The profile makes metadata tampering and inconsistent histories easier to detect; it does not establish the truth of source evidence.

A malicious issuer can make false claims. Transparency increases accountability but does not make an issuer honest.

A malicious or compromised Transparency Service can be a source of equivocation risk; independent receipts, checkpoint comparison, and external auditing SHOULD be used according to application risk.

The profile carries URLs and descriptive evidence and may reveal dependency relationships. Deployments SHOULD evaluate confidentiality and data-minimization requirements before publication.

The profile MUST NOT be treated as proof that a digital asset is post-quantum secure, compliant, certified, or safe for live-value operations.

## 14. Privacy considerations

Subjects SHOULD use organizational/system identifiers rather than personal identifiers unless a specific application requires otherwise. Evidence references SHOULD avoid personal data that is not necessary for the stated assurance purpose.

## 15. IANA considerations

This -00 research candidate requests no IANA action.

## 16. Open questions for standards review

1. Should the continuity manifest be a distinct SCITT application profile or an application-layer statement with no additional SCITT profile semantics?
2. Which SCITT header/claim structures should carry the stable subject identifier, content ID, and media type?
3. Should compact consistency proofs be defined here or delegated entirely to the selected SCITT Verifiable Data Structure?
4. How should digital-asset dependency vocabularies align with existing CBOM/SBOM and DLT standards rather than duplicate them?
5. What evidence-minimization guidance is needed for public-chain, custody, bridge, issuer, and wallet use cases?
6. Which parts belong in BGIN/NIST application guidance instead of an IETF profile?

## 17. Reference implementation

Public review surface:

https://github.com/Bdavis1390/Sara_pro/pull/221

The implementation is research-stage and maintains a no-transaction/no-wallet/no-custody execution boundary.
