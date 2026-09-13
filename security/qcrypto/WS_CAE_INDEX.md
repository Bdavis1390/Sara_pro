# WS-CAE Review Index

Status date: 2026-09-13

WS-CAE is a Worldshepherd research profile for comparing persistent digital-asset authority across heterogeneous blockchain account models during crypto-agile and post-quantum migration.

## Current determination

`RESEARCH_SPEARHEAD_WITH_ACTIVE_PRIOR_ART_CHALLENGE` in the narrow cross-chain authority-agility conformance lane.

This is not a claim of industry-standard status, standards-body adoption, external certification, production security certification, or full-chain post-quantum security.

## Start here

1. `WS_CAE_1_CORE.md` — compact profile definition and core semantics.
2. `ws_cae_reference_conformance.py` — executable reference-profile classifier; performs no signing, key generation, transaction construction, or asset movement.
3. `test_ws_cae_reference_conformance.py` — reference regression tests for Algorand MAINNET PQ authority and Ethereum EIP-8141 DEVNET authority abstraction, plus fail-closed maturity/evidence tests.
4. `ws_cae_reference_profiles_2026-09-13.json` — evidence-bound Algorand and Ethereum reference profiles.
5. `WS_CAE_MULTI_CHAIN_PROFILE_MATRIX.md` — same vocabulary applied to Algorand, Ethereum, Sui, and Shell.
6. `WS_CAE_FRONTIER_MAP.md` — strongest neighboring work grouped by standards, migration frameworks, implementations, authority substrates, and readiness measurement.
7. `WS_CAE_COMPETITIVE_DIFFERENTIATION.md` — comparison against NIST, IETF, ISO, Project Eleven, Q-Sign, LayerQu, and chain-native implementations.
8. `WS_CAE_DIFFERENTIATION_SCORECARD.md` — feature-by-feature scope comparison using `NOT IDENTIFIED` rather than unsupported absence claims.
9. `WS_CAE_PRIOR_ART_AND_SCOPE.md` — prior-art boundary and novelty caveats.
10. `WS_CAE_STANDARDS_ALIGNMENT.md` — non-overlap and composability with NIST/IETF/ISO work.
11. `WS_CAE_TWO_CHAIN_REPRODUCIBILITY_CHALLENGE.md` — independent reproduction challenge.
12. `WS_CAE_SPEARHEAD_GATE.md` — evidence gate and current claims state.

## New concrete threshold

Ethereum EIP-8141 is now backed by active client implementation work and released devnet fixtures. WS-CAE therefore has two materially different evidence-backed reference classes:

- Algorand: `MAINNET` native rekey plus native Falcon-1024 PQ account authorization;
- Ethereum: `DEVNET` native account-abstraction implementation with replaceable validation, but no claim that a PQ signature scheme or Hegota is already live on mainnet.

The reference classifier is designed to preserve exactly that distinction and to keep account-level authority results separate from consensus-level PQ claims.

## Public falsification surfaces

- GitHub PR #218: clean research review and CI surface.
- GitHub issue #214: independent technical review and prior-art challenge.
- GitHub issue #215: Ethereum EIP-8141 threshold event and maturity tracking.
- GitHub issue #216: external-validation track.
- GitHub issue #217: two-chain independent reproducibility challenge.

## Narrow differentiation thesis

The adjacent ecosystem already contains strong work in:

- PQC algorithm interoperability;
- crypto-agility guidance;
- machine-readable crypto posture;
- DLT/wallet interoperability;
- chain-agnostic wallet and light-client migration blueprints;
- international DLT PQ migration coordination;
- PQ authority substrates;
- multi-chain wallet implementations;
- independent chain readiness scoring;
- native account abstraction and rekey mechanisms;
- academic blockchain migration/governance frameworks.

WS-CAE does not claim ownership of those ingredients. Its proposed contribution is the common authority-state vocabulary across unrelated digital-asset account models, including explicit separation of:

- authority identity from authenticator;
- `ROADMAP`, `DRAFT`, `DEVNET`, `TESTNET`, and `MAINNET` maturity;
- account/vault PQ authorization from consensus/validator PQ security;
- cryptographic algorithm state from policy/recovery/evidence state.

The current public review has found strong neighboring work around this lane but has not yet identified an artifact that fills the same narrow role across heterogeneous blockchain account models.

## Promotion path

Current: `RESEARCH_SPEARHEAD_WITH_ACTIVE_PRIOR_ART_CHALLENGE`

Next: `EXTERNALLY_REPRODUCED_PROFILE`

Required evidence for promotion:

- an independent reviewer or implementation directly consumes the public WS-CAE material;
- at least two heterogeneous ecosystems are classified;
- disagreements are preserved;
- maturity and consensus boundaries are not collapsed;
- the result is public or independently inspectable.

Only after that should stronger standardization or deployment claims be considered.
