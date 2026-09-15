# WS-CAE proposal for BGIN Block 15 PQC migration work

Date: 2026-09-13
Status: public discussion candidate; not endorsed by BGIN, NIST, IETF, any chain, or any standards body.

## Proposed contribution

WS-CAE is a read-only, machine-readable authority/dependency profile for digital-asset systems. It separates deployment maturity, protocol commitment, asset authorization, consensus state, and critical dependencies instead of collapsing them into a single “quantum-ready” label.

The proposed Block 15 contribution is a neutral interoperability/testbed exercise, not a request to adopt a new cryptographic primitive.

## Why this matches the BGIN PQC Migration agenda

BGIN’s PQC Migration project focuses on crypto-agility, staged rollout, deployment gaps, neutral evaluation, and testbed coordination for DLT stacks, wallets, and operators. WS-CAE is designed to provide a common evidence vocabulary for those exact migration states.

## Public evidence already available

1. Named four-chain snapshot: Algorand, Bitcoin, Ethereum, Sui.
2. Chain Patch and Crypto System Patch schemas.
3. Weakest-critical-dependency portfolio model.
4. Upstream-valid exports to CycloneDX 1.7, SPDX 3.0.1, SARIF 2.1.0, CloudEvents 1.0, and OCSF 1.8.
5. Live GitHub Code Scanning ingestion/readback proof.
6. Keyless Sigstore provenance proof with transparency-log inclusion.
7. RFC 9943 / SCITT cross-implementation vector validation in CI.
8. Public falsification and independent-reproduction issues.

## New continuity evaluation layer

WS-CAE now also implements a chain-neutral cryptographic-continuity model intended to sit beneath any BGIN/NEDO prize-specific scoring rubric rather than replace it.

The model uses the invariant **stable subject identity, immutable state identity**. A digital-asset system can retain its stable subject identifier while moving through content-addressed states as algorithms, authenticators, recovery mechanisms, governance commitments, or critical dependencies change.

Implemented elements include:

- content-addressed continuity manifests;
- explicit content-addressed state transitions;
- lineage/fork detection;
- fail-closed resolution to one current state;
- append-order Merkle transparency roots and inclusion proofs;
- linked checkpoints for append-only history;
- independent witness threshold/equivocation policy;
- SCITT-oriented manifest and checkpoint statements;
- portable proof bundles;
- frozen cross-implementation test vectors;
- `standards/WS_CAE_SCITT_CONTINUITY_PROFILE_00.md`, an RFC-style research candidate for standards discussion.

This layer intentionally defines no competition weights, winners, algorithms, consensus mechanism, token, or registry operator.

## Proposed neutral evaluation exercise

Ask independent participants to select at least three different digital-asset models, populate WS-CAE profiles only from primary evidence, and compare results across:

- authorization model;
- implementation maturity;
- governance/protocol commitment;
- PQ authorization state;
- consensus PQ boundary;
- issuer/bridge/custody/wallet/recovery dependencies where applicable;
- ability to preserve stable subject identity across a cryptographic migration;
- reproducibility of manifest content IDs and transparency proofs.

Success does not mean “all profiles agree.” Success means disagreements are explicit, source-backed, and machine-comparable.

## Suggested Block 15 deliverable

A small public matrix plus continuity-vector exercise showing where existing DLT PQ migration work can already be normalized and where the vocabulary fails. Any failures should become change requests rather than being hidden.

## Relevant public artifacts

- PR #221: standalone WS-CAE implementation
- Issue #223: all-crypto dependency challenge
- Issue #224: CycloneDX/CBOM interoperability challenge
- Issue #225: multi-standard ingestion challenge
- Issue #226: operational ingestion + Sigstore verification challenge
- Issue #227: named four-chain market snapshot
- Issue #228: Treasury/G7 policy-market comparison
- Issue #229: consolidated public evidence release
- `ws_cae/CONTINUITY_TRANSPARENCY.md`: continuity/transparency protocol candidate
- `standards/WS_CAE_SCITT_CONTINUITY_PROFILE_00.md`: SCITT application-profile candidate

## Claims boundary

WS-CAE is a research/interoperability candidate. It is not a standard, certification, regulatory requirement, chain endorsement, proof of Q-day, competition acceptance, or proof that any cryptocurrency is fully post-quantum secure.

## Requested feedback

The strongest useful feedback would be:

1. an existing public specification that already fills this exact cross-chain authority/dependency/continuity role;
2. a DLT architecture WS-CAE cannot represent without distortion;
3. evidence that a field or maturity distinction is incorrectly modeled;
4. an independent reproduction of the frozen continuity vectors;
5. guidance on whether this belongs as a BGIN migration-playbook profile, neutral testbed input, CBOM companion profile, SCITT application profile, or another existing standards vehicle.
