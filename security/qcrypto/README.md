# Worldshepherd QCRYPTO Risk Gate

This package implements defensive, claims-controlled quantum-cryptography migration planning and readiness controls.

## Purpose

QCRYPTO keeps threat evidence, migration readiness, custody controls, account/vault protection, recovery, and pilot promotion as separate evidence planes. It prevents roadmap, prototype, account-layer, custody-layer, or pilot evidence from being promoted into claims of full blockchain quantum safety.

## Threat and migration controls

The package separates logical attack width, gate/depth cost, architecture-specific runtime, measured QEC overhead, hardware roadmap maturity, platform/manufacturing maturity, classical decoding capacity, public-key exposure, protocol migration windows, custody readiness, sector coordination, and industrialization pressure.

A low logical-qubit count does not imply a fast practical attack. A future vendor roadmap is not demonstrated hardware. A fabricated prototype is not attack-scale hardware. Account-layer PQ protection is not consensus-layer PQ protection. Commercial PQ signing availability is not Worldshepherd integration until exercised.

## Federal PQC migration control plane

The Federal-alignment modules convert public migration requirements into internal Worldshepherd planning controls without asserting Federal compliance, certification, authorization, procurement qualification, or government approval.

`federal_pqc_control_map.py` maps public migration functions to SARA, ECHO, PRIME, and OVERWATCH responsibilities and evidence targets.

`federal_pqc_readiness.py` enforces the evidence sequence:

`UNMAPPED -> DESIGN_MAPPING -> IMPLEMENTED_IN_SOFTWARE -> PROVEN_INTERNALLY -> INDEPENDENTLY_REPRODUCED`

A later state cannot be awarded when prerequisite evidence is absent.

`cbom_inventory.py` provides an evidence-custodied cryptographic inventory model and conservative internal priority bands. Missing provenance produces `INCOMPLETE_EVIDENCE` rather than a migration recommendation.

`federal_pqc_control_plane.py` carries a validated CBOM record through the governed path:

`ECHO provenance -> PRIME recommendation -> SARA human-approval gate -> OVERWATCH tracking`

The control plane never performs migration. Human approval authorizes a bounded plan only; `migration_executed` remains false by construction.

The same module exposes the data-only `WS-QCRYPTO-CONTROL-DECISION-V1` audit projection. The projection carries explicit negative authority and claims flags: migration execution, execution authority, live-value authorization, Federal compliance, and WS-CAE-1 conformance all remain false at the persistence boundary.

`deployments/sara_verified_local_v1/worldshepherd_sara/qcrypto_audit_adapter.py` is the native SARA persistence bridge. It validates the QCRYPTO projection, converts the ECHO/PRIME/SARA/OVERWATCH states into four governed audit events, and queues them through SARA's existing durable event outbox. Delivery therefore inherits the existing `AuditRecord` and at-least-once evidence semantics rather than introducing a second audit schema. The adapter rejects any projection that attempts to assert migration execution, execution authority, live-value authorization, Federal compliance, or WS-CAE-1 conformance.

`federal_pqc_pilot_bridge.py` converts the internal migration priority into a target WS-CAE-1 profile and safe pilot entry stage. It recommends C1/C2/C3 targets but does not self-award WS-CAE-1 conformance. Even with human approval, the bridge advances no further than `H1_ZERO_VALUE_DRY_RUN`; live-value authorization remains false.

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

QCRYPTO does not sign transactions, access wallets, recover keys, move assets, authorize live-value deployment, or claim full-chain quantum safety. Federal requirement mapping is internal engineering alignment only and does not establish Federal compliance. SARA audit persistence records governance evidence only and does not confer execution authority. WS-CAE-1 target recommendations are not conformance findings. Any eventual live-value canary remains subject to explicit human approval, independent review, bounded scope, and chain-specific controls.
