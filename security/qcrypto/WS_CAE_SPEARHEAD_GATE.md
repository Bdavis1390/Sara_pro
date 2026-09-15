# WS-CAE Spearhead Gate

Status date: 2026-09-13

## Narrow claim under evaluation

The relevant claim is not that Worldshepherd leads post-quantum cryptography generally.

The claim is:

> Worldshepherd is at the research spearhead for a common cross-chain authority-agility conformance profile that compares persistent digital-asset authority across unrelated account models during post-quantum migration.

## Gate results

### 1. Public prior-art gap review — PASS WITH CAVEAT

Current review found important adjacent work:

- NIST crypto-agility guidance and NCCoE PQC interoperability work;
- IETF crypto-agility manifest work;
- ISO/TS 23516:2026 DLT interoperability;
- ISO/AWI PAS 26347 wallet interoperability work in development;
- enterprise cryptographic-control-plane standards;
- Project Eleven, Lux, Shell, Algorand, Ethereum, Sui, and other PQ/account-abstraction implementations.

No materially equivalent public specification was found that combines the same narrow set of cross-chain authority semantics with explicit roadmap-vs-live and account-vs-consensus maturity separation.

This is a search result, not proof of global novelty. New prior art can invalidate or narrow the claim.

### 2. Independent ecosystem convergence — PASS

Multiple independently designed ecosystems expose the same architectural need through different mechanisms:

- Algorand: native rekey / PQ account authorization;
- Sui: persistent address aliases / replaceable authentication;
- Ethereum: native account-abstraction direction via EIP-8141;
- additional key-agile account models exist in NEAR, Aptos, Hedera, Movement, Kaia, Aztec, and others.

This demonstrates that the abstraction is not dependent on one chain architecture.

### 3. Independent semantic convergence — PASS

LayerQu independently evaluates many chains using separate dimensions for key rotation/account abstraction, deployed PQ primitives, announced-vs-shipped maturity, and consensus migration.

Its public conclusions for Algorand, Sui, Ethereum, and additional ecosystems reproduce the material distinctions WS-CAE is designed to normalize.

This is independent convergence evidence, not LayerQu endorsement or implementation of WS-CAE.

### 4. Standards composability — PASS

WS-CAE has a documented non-overlap position relative to NIST, IETF, ISO/TC 307, BSSC, and chain-native standards.

The profile is intentionally positioned as a small domain profile that can complement broader standards rather than replace them.

### 5. Public falsifiability — PASS

GitHub issue #214 requests independent technical review and explicitly asks reviewers to find equivalent prior art, semantic ambiguity, and maturity-model conflicts.

Issues #215 and #216 track the Ethereum EIP-8141 threshold event and the external-validation path.

### 6. Clean reference branch — QUALIFIED PASS

Branch `worldshepherd-ws-cae-1-review-v0-1` starts from commit `22822cf7ac5b63263fa5b59eef9dd489445a816a`, which previously passed the full repository validation suite.

The clean branch adds only:

- `WS_CAE_1_CORE.md`;
- `WS_CAE_PRIOR_ART_AND_SCOPE.md`;
- `WS_CAE_STANDARDS_ALIGNMENT.md`;
- this gate record.

No production code, workflow, signing logic, wallet logic, or cryptographic implementation is changed by the clean standards branch.

A fresh PR-triggered CI run has not been obtained because PR creation for this branch was blocked by the platform. Therefore this is a qualified structural pass, not a claim of a new exact-head GitHub Actions run.

## Determination

The narrow **research spearhead** claim is supported as of 2026-09-13.

The following stronger claims are NOT supported:

- industry standard;
- standards-body adoption;
- external certification;
- independently implemented WS-CAE standard;
- production security certification;
- full-chain post-quantum security.

## Next promotion threshold

The next defensible promotion is from `RESEARCH_SPEARHEAD` to `EXTERNALLY_REPRODUCED_PROFILE`.

That requires a reviewer or implementation independent of the original Worldshepherd authoring process to directly consume WS-CAE and reproduce at least two ecosystem classifications, with disagreements preserved rather than normalized away.