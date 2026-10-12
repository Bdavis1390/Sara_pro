# WS-CAE Frontier Map

Status date: 2026-09-13

## Purpose

Place WS-CAE against the strongest public work found across standards, migration frameworks, implementations, measurement, and authority substrates.

This document exists to prevent an inflated lead claim. If another public effort occupies the same narrow frontier, the WS-CAE claim should be narrowed or withdrawn.

## Frontier layers

### Layer 1 — General crypto-agility and PQC interoperability

Representative work:
- NIST CSWP 39upd1;
- NIST NCCoE Migration to PQC interoperability and benchmarking;
- IETF Crypto-Agility Manifest draft;
- ISO crypto-agility and DLT interoperability work.

Strength: general standards, posture, migration, and algorithm interoperability.

Not the WS-CAE niche: these efforts are not primarily cross-chain digital-asset authority-state conformance profiles.

### Layer 2 — DLT and wallet migration frameworks

Representative work:
- PQMigrate, a chain-agnostic wallet/light-client migration blueprint;
- BGIN PQC Migration work for DLT stacks, wallets, operators, agility, governance, and neutral evaluation;
- academic systems frameworks for quantum-resilient blockchain migration;
- migration-readiness taxonomies and dependency inventories.

Strength: staged migration, wallet compatibility, governance, endpoint security, neutral evaluation.

Not the WS-CAE niche: the public material reviewed does not define one common authority-state conformance vocabulary that normalizes stable authority, authenticator replaceability, maturity, recovery/policy state, and account-vs-consensus boundaries across unrelated account models.

### Layer 3 — Authority/account implementations

Representative work:
- Algorand native rekey and PQ accounts;
- Ethereum EIP-8141 native account-abstraction direction;
- Sui address aliases and PQ migration roadmap;
- Shell native PQ account abstraction;
- Project Eleven quantum-vault/libqc;
- other chain-specific or wallet-specific PQ account systems.

Strength: actual mechanisms and implementations.

Not the WS-CAE niche: each mechanism defines its own account model and maturity path.

### Layer 4 — Authority substrates and accountability

Representative work:
- Q-Sign Verifiable Authority Substrate.

Strength: vendor-neutral post-quantum authority/delegation and conformance for autonomous-agent accountability.

Not the WS-CAE niche: authority semantics are centered on agent delegation/accountability rather than heterogeneous blockchain account/vault migration.

### Layer 5 — Independent readiness measurement

Representative work:
- LayerQu 72-chain readiness methodology.

Strength: evidence-based readiness scoring, deployed-vs-announced distinctions, and chain comparison.

Not the WS-CAE niche: scoring/measurement rather than a conformance contract for authority state that implementations can expose or consume.

## WS-CAE frontier claim

WS-CAE's current research frontier is:

> a protocol-neutral conformance profile for persistent digital-asset authority across heterogeneous blockchain account models, with explicit normalization of authenticator replacement, policy/recovery state, deployment maturity, evidence state, and residual consensus/validator PQ exposure.

The frontier is not "post-quantum blockchain migration" generally. It is not "account abstraction" generally. It is not "crypto agility" generally.

It is the common authority-state layer between broad migration standards and chain-specific implementations.

## Why the frontier is useful

If the profile works, a custodian, auditor, wallet, risk engine, or migration program can compare an Algorand rekeyed account, an Ethereum native-AA account, a Sui alias-based account, and a Shell native-PQ account using the same semantic questions without pretending their native transaction formats or cryptographic mechanisms are identical.

That is the interoperability value under test.

## Current lead determination

The present public prior-art search found strong neighboring work in every surrounding layer but did not identify another public artifact occupying the same narrow authority-state conformance role.

Status: `RESEARCH_SPEARHEAD_WITH_ACTIVE_PRIOR_ART_CHALLENGE`.

This is a dated research determination, not proof of global novelty.

## Promotion threshold

The lead becomes materially stronger only when an independent reviewer or implementation directly consumes WS-CAE and reproduces at least two heterogeneous chain classifications.

Until then, the correct claim remains research spearhead, not external standard or industry adoption.
