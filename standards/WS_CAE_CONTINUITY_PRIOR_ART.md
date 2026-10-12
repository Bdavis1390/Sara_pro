# WS-CAE continuity prior-art and convergence note

Date: 2026-09-13
Status: research note; no novelty or standards-adoption claim.

## Purpose

Position the WS-CAE cryptographic-continuity work relative to existing public standards and current Internet-Drafts so it complements rather than duplicates them.

## IETF SCITT — RFC 9943

RFC 9943 defines a general architecture for making signed statements transparent through Verifiable Data Structures and Transparency Services. It provides the appropriate transparency/notarization layer for heterogeneous signed content and explicitly addresses append-only history, receipts, auditability, and accountability.

WS-CAE should therefore not define a competing general Transparency Service. Its continuity manifest/checkpoint objects are candidate application-layer statements that can be carried by SCITT.

Reference: https://www.rfc-editor.org/rfc/rfc9943.html

## Crypto-Agility Manifest Internet-Draft

`draft-acosta-crypto-agility-manifest` proposes a discoverable public cryptographic-posture document at `/.well-known/crypto-agility.json`, including readiness summary, CBOM summary, migration policy, and optional attestation linkage.

This is an individual Internet-Draft / work in progress, not an IETF standard.

WS-CAE should not invent a competing well-known discovery URI while that work exists. A cleaner convergence path is:

`/.well-known/crypto-agility.json` (discovery / public posture)
→ linked continuity/attestation resource
→ WS-CAE continuity state + lineage semantics
→ SCITT Transparency Service / receipts where assurance is required.

References:
- https://datatracker.ietf.org/doc/draft-acosta-crypto-agility-manifest/
- https://datatracker.ietf.org/doc/html/draft-acosta-crypto-agility-manifest-01

## CycloneDX CBOM

CycloneDX CBOM provides cryptographic inventory and relationships. WS-CAE already exports digital-asset dependency state into CycloneDX rather than replacing CBOM.

The distinction is:
- CBOM: what cryptographic assets/dependencies exist;
- public crypto-agility manifest: discoverable public posture summary;
- WS-CAE continuity: which stable digital-asset subject is in which immutable authority/migration/dependency state, how it transitioned, and whether its lineage is unambiguous;
- SCITT: how signed statements about those states become transparent and receipted.

Reference: https://cyclonedx.org/capabilities/cbom/

## W3C DID / stable identifiers

Decentralized Identifiers already demonstrate the general pattern of a stable identifier whose verification methods can change over time. WS-CAE does not claim invention of stable-identity/key-rotation concepts.

The narrower digital-asset continuity question is whether heterogeneous chains/assets/custody/bridge/issuer systems can publish machine-comparable authority, migration, dependency, recovery, and consensus state while preserving immutable evidence history.

Reference: https://www.w3.org/TR/did-core/

## Current defensible differentiation

The current research niche is therefore not:
- first crypto-agility mechanism;
- first stable identifier/key rotation model;
- first cryptographic inventory;
- first transparency log;
- first SCITT profile;
- first blockchain PQ migration effort.

The narrower candidate contribution is the composition of:
1. digital-asset-specific authority/dependency/PQ migration semantics;
2. stable subject identity separated from immutable state identity;
3. content-addressed migration lineage with fork detection and fail-closed resolution;
4. weakest-critical-dependency system semantics;
5. deterministic transparency/inclusion/checkpoint artifacts;
6. SCITT-oriented statement mapping;
7. cross-language frozen vectors;
8. bridges into CBOM/SBOM/SecOps ecosystems.

No global novelty claim is made. Equivalent or superior prior art should replace or reshape this design rather than be ignored.
