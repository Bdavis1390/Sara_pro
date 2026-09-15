# WS-CAE-1 Core — Cross-Chain Authority Agility Profile

Status: Worldshepherd research draft v0.1
Date: 2026-09-13

## Purpose

WS-CAE-1 Core defines a chain-neutral way to describe crypto-agile account and custody authority without defining a new cryptographic primitive or consensus protocol.

The model is intentionally narrow. It focuses on the control semantics shared by systems that keep an authority identity stable while changing the authentication mechanism beneath it.

## Required semantics

A conforming profile documents:

- a stable authority identifier;
- an adapter class describing the native mechanism;
- a versioned authenticator set;
- a versioned authorization policy;
- recovery state;
- chain or domain binding;
- replay-domain separation;
- evidence or review state;
- a separate statement of consensus or validator post-quantum status.

## Adapter classes

Initial adapter classes are:

- `NATIVE_REKEY`;
- `ADDRESS_ALIAS`;
- `PROGRAMMABLE_VALIDATOR`;
- `NATIVE_ACCOUNT_ABSTRACTION`;
- `CUSTODY_POLICY_ENGINE`;
- `PRE_PROTOCOL_VAULT`;
- `OTHER_REVIEW_REQUIRED`.

An adapter-class label describes mechanism only. It does not imply production maturity, independent review, or post-quantum consensus.

## Maturity labels

Profiles use four non-overlapping maturity labels:

- `DOCUMENTED` — mechanism and evidence are described;
- `IMPLEMENTED` — a relevant mechanism exists in software or protocol implementation;
- `LIVE` — the claimed authority mechanism is active in the referenced production environment;
- `INDEPENDENTLY_REVIEWED` — an external review has examined the claimed path.

Roadmap items must not be classified as live.

## Cross-chain mapping objective

Two independent implementations should be able to inspect the same public evidence and agree on:

- whether authority identity is stable;
- whether authenticators are replaceable;
- whether policy is separately versioned;
- whether recovery is represented;
- whether replay/domain separation is present;
- whether the mechanism is documented, implemented, live, or independently reviewed;
- whether account-level post-quantum capability is being incorrectly promoted into a consensus-level claim.

## Initial ecosystem profiles

Current public evidence supports these architectural mappings:

- Algorand: `NATIVE_REKEY`; live native PQ account authorization exists, while broader multi-cryptography policy remains a separate maturity question.
- Sui: `ADDRESS_ALIAS`; stable address aliases establish authority continuity while PQ account authentication is tracked separately.
- Ethereum: `NATIVE_ACCOUNT_ABSTRACTION`; EIP-8141 is scheduled for inclusion and is treated as roadmap/scheduled capability until activated.

These are evidence mappings, not endorsements or certifications.

## Relationship to adjacent work

WS-CAE-1 Core complements rather than replaces:

- NIST post-quantum standards and crypto-agility guidance;
- NIST NCCoE interoperability and benchmarking work;
- IETF cryptographic identifier and crypto-agility manifest work;
- enterprise cryptographic-control-plane standards;
- chain-native account-abstraction and post-quantum migration mechanisms.

Its narrower target is cross-chain digital-asset authority semantics.

## Claims boundary

Conformance with this draft does not establish:

- post-quantum consensus;
- post-quantum validator or bridge security;
- standards-body adoption;
- external certification;
- authorization to move live value;
- proof that a cryptographically relevant quantum computer exists.

## Review target

WS-CAE-1 Core should be considered mature enough for a stronger claim only after an implementation or reviewer independent of the original authoring process reproduces the same classification for at least two ecosystems and records disagreements publicly.