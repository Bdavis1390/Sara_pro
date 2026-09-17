# Worldshepherd QCRYPTO Risk Gate

This package implements defensive, claims-controlled quantum-cryptography migration planning and readiness controls.

## Purpose

QCRYPTO keeps threat evidence, migration readiness, custody controls, account/vault protection, recovery, and pilot promotion as separate evidence planes. It prevents roadmap, prototype, account-layer, custody-layer, or pilot evidence from being promoted into claims of full blockchain quantum safety.

## Threat and migration controls

The package separates logical attack width, gate/depth cost, architecture-specific runtime, measured QEC overhead, hardware roadmap maturity, platform/manufacturing maturity, classical decoding capacity, public-key exposure, protocol migration windows, custody readiness, sector coordination, and industrialization pressure.

A low logical-qubit count does not imply a fast practical attack. A future vendor roadmap is not demonstrated hardware. A fabricated prototype is not attack-scale hardware. Account-layer PQ protection is not consensus-layer PQ protection. Commercial PQ signing availability is not Worldshepherd integration until exercised.

## Defensive solution layers

### Pre-Protocol PQ Vault

`preprotocol_pq_vault.py` tracks whether value can be placed under a native or application-layer PQ authorization path before full protocol migration completes, while preserving relay, recovery, audit, and consensus limitations.

### Quantum Continuity Envelope

`quantum_continuity_envelope.py` virtualizes authorization so stable authority identity, replaceable authenticators, quorum policy, algorithm diversity, and recovery can evolve independently. It explicitly keeps base-layer consensus outside the protection boundary unless separately validated.

### Institution-Grade High-Value Pilot

`high_value_pilot.py` defines a staged readiness ladder:

`HVP_DESIGN_OR_INTEGRATION -> HVP_DRY_RUN_READY -> HVP_TESTNET_READY -> HVP_BOUNDED_CANARY_READY_PENDING_HUMAN_AUTHORIZATION -> HVP_BOUNDED_CANARY_READY`

The pilot requires dual-family PQ signing capability, stable authority identity, replaceable authenticators, separated quorum authorization, recovery, evidence logging, independent review, and a bounded-value policy. A live-value canary can never be inferred from technical readiness; explicit human authorization is a separate gate.

`HIGH_VALUE_PILOT_RUNBOOK.md` defines the governance sequence from evidence qualification through zero-value dry run, non-production integration, recovery campaign, independent review, and bounded-canary proposal.

## Claims boundary

QCRYPTO does not sign transactions, access wallets, recover keys, move assets, authorize live-value deployment, or claim full-chain quantum safety. Any eventual live-value canary remains subject to explicit human approval, independent review, bounded scope, and chain-specific controls.
