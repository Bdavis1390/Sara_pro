# WS-CAE Prior Art and Defensible Scope

Status: research comparison for WS-CAE-1 Core
Date: 2026-09-13

## Claim discipline

WS-CAE does not claim to be the first crypto-agility framework, the first post-quantum wallet design, the first post-quantum account-abstraction design, or the first cross-chain post-quantum project.

The narrower research claim under evaluation is:

> WS-CAE is a candidate common conformance vocabulary for describing persistent digital-asset authority across different chain-native account/rekey/account-abstraction mechanisms while keeping account-level post-quantum readiness distinct from consensus-level readiness.

This claim remains subject to external review and contradiction.

## Adjacent standards and frameworks

### NIST crypto agility

NIST CSWP 39upd1 defines crypto agility across protocols, applications, software, hardware, firmware, and infrastructure. WS-CAE applies that principle to digital-asset authority semantics rather than replacing NIST guidance.

### NIST NCCoE Migration to PQC

The NCCoE project explicitly emphasizes interoperability and benchmarking. WS-CAE is aligned with that objective but is not a NIST project or NIST-endorsed profile.

### IETF Crypto-Agility Manifest

The 2026 Internet-Draft for a crypto-agility manifest defines a discoverable JSON summary of cryptographic posture. It addresses posture publication rather than cross-chain account-authority semantics. WS-CAE should reuse or complement standardized posture fields where appropriate instead of duplicating them.

### Cryptographic Control Plane Standard

The CCP Standard defines an enterprise cryptographic control-plane architecture and maturity model. It is broader than blockchain account authority and is important adjacent prior art. WS-CAE should avoid duplicating its enterprise governance role.

## Adjacent blockchain implementations

### Algorand

Algorand exposes a scheme-agnostic post-quantum signature envelope and native rekey semantics. Public documentation describes cryptographic agility and a roadmap toward generic multi-cryptography policy over independently verifiable signatures.

WS-CAE mapping: `NATIVE_REKEY`.

### Ethereum

Ethereum's post-quantum roadmap uses account abstraction for gradual execution-layer migration. EIP-8141 has been scheduled for Hegota inclusion and separates account behavior from permanent ECDSA key identity.

WS-CAE mapping: `NATIVE_ACCOUNT_ABSTRACTION` once activated; until then, scheduled capability remains distinct from live capability.

### Sui

Sui's address-alias architecture preserves address identity while authentication evolves, and its PQ direction uses distinct algorithm families for different authority roles.

WS-CAE mapping: `ADDRESS_ALIAS`.

### Project Eleven

Project Eleven publishes audited reference work for crypto-agile account abstraction and multi-chain PQ migration. This is strong adjacent implementation prior art. It demonstrates practical migration infrastructure rather than a chain-neutral authority conformance vocabulary.

WS-CAE mapping: implementation/reference substrate, not a competing standards-body claim.

### Lux

Lux publishes an ERC-4337-derived account-abstraction standard with PQ verification integration. It is another important implementation profile and should be included in interoperability testing.

WS-CAE mapping: `PROGRAMMABLE_VALIDATOR` / account-abstraction profile.

### Shell Chain

Shell documents native account abstraction, stable identity across key rotation, and built-in PQ validation. These claims should be independently verified before being promoted beyond self-described implementation status.

WS-CAE mapping: `NATIVE_ACCOUNT_ABSTRACTION` candidate profile.

### Other cross-chain PQ projects

Projects proposing PQ wallets, bridges, L2s, or migration labs are relevant prior art and should be tracked. Cross-chain scope alone does not establish equivalent authority-conformance semantics.

## Defensible gap

Based on the sources reviewed as of 2026-09-13, the specific gap WS-CAE targets is not "post-quantum blockchain" generally. It is the lack of a common, evidence-oriented vocabulary that lets independent reviewers compare unrelated authority mechanisms on the same axes:

- stable authority identity;
- authenticator replacement and versioning;
- authorization-policy versioning;
- recovery state;
- domain/replay separation;
- evidence/review state;
- implementation maturity;
- separate account-level and consensus-level PQ claims.

If an existing standard or project is found to provide this same cross-chain semantic/conformance role, WS-CAE should either align with it or narrow its scope further.

## Spearhead gate

Worldshepherd should only describe WS-CAE as a leading or spearhead effort in this narrow niche when all of the following are true:

1. a current prior-art review finds no materially equivalent cross-chain authority-conformance specification;
2. at least two independently designed blockchain account architectures map into the model without special-case semantic changes;
3. the mapping preserves roadmap-vs-live and account-vs-consensus distinctions;
4. the reference branch passes repository quality gates;
5. an external reviewer or independent implementation can reproduce at least two profile classifications.

Items 1-4 can be demonstrated internally with public evidence. Item 5 requires evidence independent of the original Worldshepherd authoring process and must not be self-certified.