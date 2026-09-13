# WS-CAE Cryptographic Continuity Transparency

Status: research protocol candidate. Read-only metadata only.

## Purpose

Represent the exact cryptographic authority/dependency state of a digital-asset system as a portable, content-addressed object and make that state independently auditable over time.

This layer does not define a cryptocurrency, token, consensus protocol, signature algorithm, wallet, custody system, transaction format, or registry operator.

## Objects

### Continuity manifest

`WS-CAE-CONTINUITY-MANIFEST-1`

A chain-neutral record containing subject identity/type, evidence date/version, authority model, deployment maturity, protocol commitment, PQ authorization state, consensus PQ state, crypto-agility state, recovery state, critical dependencies, and evidence references.

Canonical JSON bytes are SHA-256 addressed as `sha256:<64 hex>`.

### Continuity snapshot

`WS-CAE-CONTINUITY-SNAPSHOT-1`

A deterministic digest over a sorted set of manifest content IDs. This is useful for referring to the exact collection of states evaluated in a study or portfolio snapshot.

### Transparency tree

`WS-CAE-CONTINUITY-TRANSPARENCY-1`

An append-order Merkle tree over manifest content IDs. Leaves use SHA-256 with domain separator `0x00`; internal nodes use SHA-256 with domain separator `0x01`. Inclusion proofs bind one manifest content ID to one checkpoint root.

### Linked checkpoint

A checkpoint records tree size/root and may name the immediately preceding tree size/root. A linked checkpoint is valid only when the current content-ID sequence extends the prior sequence as an exact prefix.

### SCITT statement

`WS-CAE-SCITT-CONTINUITY-1` and `WS-CAE-SCITT-CONTINUITY-CHECKPOINT-1` serialize manifests/checkpoints into transparency-oriented statements while preserving the content ID/root. Signing and registration are external concerns.

### Witness receipts

Independent externally verifiable receipts can be evaluated under an N-of-M policy. Duplicate issuers do not increase quorum. An issuer observed presenting different roots for the same tree size is flagged for equivocation and excluded from the agreeing set.

### Proof bundle

`WS-CAE-CONTINUITY-PROOF-BUNDLE-1` binds a manifest content ID, Merkle inclusion proof, and checkpoint into one portable verification object.

## Interoperability vectors

`examples/continuity_interop_vectors.json` freezes a canonical manifest content ID, roots for tree sizes 0–5, and an uneven-tree inclusion path. Independent implementations should reproduce these bytes/digests before claiming compatibility.

## Security boundary

The protocol describes and verifies metadata. It does not access private keys, generate cryptocurrency signatures, construct or broadcast transactions, move assets, operate validators, alter consensus, or confer regulatory/certification status.

## Claims boundary

Passing these checks establishes only structural/content-addressing/transparency properties of the supplied metadata. It does not establish that the evidence is true, that a system is fully post-quantum secure, that a migration will succeed, or that any standards body has adopted WS-CAE.
