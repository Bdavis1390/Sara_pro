# WS-CAE Standards Alignment Map

Status: research alignment note
Date: 2026-09-13

## Position

WS-CAE is not intended to replace general cryptographic, DLT interoperability, wallet interoperability, or custody standards. Its narrow purpose is to provide a common authority-agility profile for post-quantum migration across different blockchain account models.

## NIST

### CSWP 39upd1 — Crypto Agility

Alignment: WS-CAE applies the general requirement to replace cryptography while preserving operation to digital-asset authority identity and authentication.

Boundary: NIST guidance is broader and authoritative; WS-CAE is a domain profile only.

### NCCoE Migration to PQC

Alignment: the NCCoE interoperability and benchmarking work establishes the value of common, reproducible migration semantics across implementations.

Boundary: WS-CAE is not a NIST project and no NIST review or endorsement is claimed.

## IETF

### Crypto-Agility Manifest Internet-Draft

Alignment: machine-readable cryptographic posture is complementary to WS-CAE authority-state evidence.

Boundary: the manifest describes published cryptographic posture; WS-CAE focuses on persistent digital-asset authority, authenticator replacement, policy state, recovery state, and account-vs-consensus maturity.

### PQ signature identifiers and serialization

Alignment: WS-CAE should reference standardized algorithm identifiers where available rather than inventing private cryptographic names.

Boundary: WS-CAE does not define signature encodings or cryptographic primitives.

## ISO/TC 307

### ISO/TS 23516:2026 — DLT Interoperability Framework

Alignment: WS-CAE can be treated as a security/authority profile within broader DLT interoperability work. ISO/TS 23516 defines transport, syntactic, semantic-data, behavioural, and policy facets across DLT systems.

Boundary: WS-CAE does not claim to replace or supersede ISO/TS 23516.

### ISO/AWI PAS 26347 — Interoperable Protocol Between Digital Wallets Based on Blockchain and DLT

Status: under development at stage 20.00 as of 2026-09-13.

Alignment opportunity: compare future public PAS 26347 wallet semantics with WS-CAE stable-authority, authenticator-version, policy-version, recovery, and evidence concepts.

Boundary: no claim is made that PAS 26347 currently contains, adopts, or conflicts with WS-CAE semantics; public project metadata does not expose enough technical content to support such a claim.

### ISO/TR 23576:2020 — Security Management of Digital Asset Custodians

Alignment: custody key-management and security-control concepts are relevant to the external-custody adapter class.

Boundary: the report predates finalized PQ standards and does not establish WS-CAE post-quantum semantics.

## Blockchain Security Standards Council

BSSC publishes blockchain key-management and general security standards. WS-CAE should treat these as adjacent operational-security controls rather than duplicate key-management requirements.

## Current contribution opportunity

The strongest defensible standards contribution is not a new signature scheme or a competing DLT interoperability framework. It is a profile answering this narrower question:

> How can independent chains, wallets, custodians, and reviewers describe the state of a persistent digital-asset authority when its authenticators and authorization policies evolve during post-quantum migration?

A useful WS-CAE contribution should therefore remain small, evidence-oriented, and composable with NIST, IETF, ISO/TC 307, and chain-native standards.

## Promotion criteria

Before describing WS-CAE as an externally validated standard profile, Worldshepherd still requires direct independent review or implementation of the WS-CAE profile itself. Until then, the defensible state is a leading research/profile candidate in a narrow cross-chain authority-agility niche.