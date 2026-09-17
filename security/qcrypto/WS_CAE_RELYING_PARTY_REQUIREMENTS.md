# WS-CAE Relying-Party Requirements

Status: optional procurement/due-diligence language for a research profile.

This document gives custodians, exchanges, wallets, treasuries, auditors, insurers, and risk teams a neutral way to request authority-agility information without prescribing a chain's cryptography or implementation.

## Minimal due-diligence request

A relying party may request that a supported blockchain, wallet platform, custody stack, or digital-asset service provide:

1. a current WS-CAE authority profile conforming to `ws_cae_profile.schema.json`;
2. public or inspectable evidence supporting each asserted maturity and authority state;
3. an explicit distinction between account/vault authorization and consensus/validator cryptography;
4. a change process for updating the profile when maturity changes;
5. documented deviations where a requested field cannot yet be established.

A relying party may then evaluate that profile using its own consumer policy conforming to `ws_cae_policy.schema.json`.

## Recommended requirement wording

> The supplier or ecosystem should provide a machine-readable authority-agility profile that identifies authentication replaceability, deployment maturity, post-quantum authorization state, policy and recovery documentation, replay/domain binding, evidence state, and residual consensus/validator exposure. WS-CAE-1 is accepted as one profile format. Equivalent evidence may be supplied where WS-CAE is not used. Nonconformance should be reported as a documented gap rather than silently normalized.

This wording intentionally accepts equivalent evidence so WS-CAE is useful as an interoperability profile rather than a lock-in mechanism.

## Policy examples

The repository provides two examples:

- `ws_cae_interop_minimum_policy.json` — a broad authority-agility interoperability gate suitable for integration and migration programs;
- `ws_cae_institutional_pq_policy.json` — a stricter example requiring mainnet PQ account authorization while explicitly allowing consensus state to remain separately assessed.

These are examples, not universal security requirements. Every relying party remains responsible for its own risk appetite and legal/compliance obligations.

## Why this changes chain incentives

If multiple relying parties accept the same profile format, a chain can answer one common authority-agility questionnaire instead of maintaining institution-specific mappings.

The result is useful even when a chain does not yet meet a relying party's policy: a precise fail result tells the chain which documented capability or maturity state is blocking that consumer, while leaving the chain free to decide whether and when to address it.

## Claims boundary

WS-CAE conformance does not constitute certification, regulatory compliance, security approval, standards-body endorsement, or authorization to custody or move assets. The profile is a structured evidence and interoperability mechanism.
