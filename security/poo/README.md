# Worldshepherd Proof of Ownership (PoO) v1

## Purpose

PoO is a claims-controlled ownership-attestation protocol that composes independent evidence instead of treating any one consensus primitive as ownership.

### The proof and verification legs

- **PoW — Proof of Work:** claim-specific bounded work tied to the asset and claim. This adds freshness/cost and makes cheap claim flooding harder. It does **not** prove ownership by itself.
- **PoC — Proof of Concept:** a bounded demonstration that the claimed ownership mechanism for the asset actually works and can be independently checked. It does **not** prove current control or legal ownership by itself.
- **COC — Control/Custody Verification:** verifies that the claimant currently controls or holds custody over the asset-bound authority or custody surface. It is a separate mandatory predicate and is not PoC.
- **PoS — Proof of Stake:** bonded/slashable value or other accountable stake tied to the claim. This creates economic consequence for fraudulent assertions. It does **not** prove ownership by itself.

PoO also requires title/provenance binding, asset fingerprint binding, claimant identity binding, freshness, and a non-revoked state.

## Core rule

PoO uses fail-closed AND semantics, not a weighted score:

```text
PoO_valid =
    asset_fingerprint_bound
    AND claimant_identity_bound
    AND title_or_provenance_bound
    AND PoW_verified
    AND PoC_concept_verified
    AND COC_verified
    AND PoS_bond_verified
    AND freshness_verified
    AND not_revoked
```

A claimant cannot compensate for missing Proof of Concept, COC, or provenance by adding more work or stake.

## Why COC is separate from PoC

Proof of Concept answers: **does the claimed ownership mechanism work as demonstrated?**

COC answers: **does this claimant currently control or hold custody over the asset-bound authority?**

Those are different questions. A successful PoC cannot establish present control/custody, and a valid COC cannot establish that the broader ownership mechanism itself has been demonstrated or validated.

## Why title/provenance is separate

PoW, PoC, COC, and PoS provide computational, demonstrative, control/custody, and economic evidence. They cannot manufacture legal title. A valid PoO therefore means **technical ownership attestation under the supplied evidence**, not a court judgment, government registry entry, or statutory title determination.

Even when an external title reference has been verified, Worldshepherd reports only:

`TECHNICAL_ATTESTATION_WITH_EXTERNAL_TITLE_REFERENCE`

and keeps `legal_ownership_established = false`.

## Semantic commitment

The deterministic ownership digest commits to:

```text
schema
asset_id
claimant_id
title_reference
control_key_fingerprint
work_reference
concept_reference
stake_reference
issued_at
expires_at
previous_poo_digest
```

Evidence-verification booleans are deliberately excluded from the semantic digest. This allows evidence state to be re-evaluated without changing the underlying ownership-claim identity.

## Governed transfer and supersession

A transfer never edits or erases the prior PoO. It prepares a **new PoO candidate** whose `previous_poo_digest` points to the prior attestation.

Base transfer evidence is fail-closed:

```text
Base_transfer_ready =
    prior_PoO_valid
    AND asset_continuity_verified
    AND current_owner_authorized
    AND recipient_identity_bound
    AND recipient_PoC_concept_verified
    AND recipient_COC_verified
    AND recipient_PoW_verified
    AND recipient_PoS_bond_verified
    AND title_or_provenance_transition_bound
    AND freshness_verified
    AND no_active_dispute
    AND transfer_not_revoked
    AND human_approval_verified
```

But base readiness is not enough. `security/poo/governance_guard.py` binds transfer readiness to the technical ownership lineage:

```text
Governed_transfer_ready =
    Base_transfer_ready
    AND lineage_internally_consistent
    AND prior_poo_digest == active_tip_digest
    AND current_owner_id == active_tip_claimant_id
    AND transfer.asset_id == active_tip.asset_id
```

Therefore a transfer with perfect PoW/PoC/COC/PoS evidence is still blocked if it references a stale predecessor, arrives while the lineage is forked/cyclic/structurally invalid, or names a current owner who is not the claimant on the single active technical tip.

Only the combined state reports:

`TRANSFER_READY_WITH_LINEAGE_GUARD`

The system still hard-codes:

```text
transfer_executed = false
live_value_authorized = false
legal_title_changed = false
conflict_winner_selected = false
lineage_auto_resolved = false
```

## Recovery and disputes

Recovery is a separate **same-owner** path for lost control, compromised control, custody failure, or a technical record correction. It is not an alternate transfer mechanism and cannot silently change the claimant.

Base recovery evidence is fail-closed:

```text
Base_recovery_ready =
    prior_PoO_valid
    AND asset_continuity_verified
    AND claimant_continuity_verified
    AND claimant_identity_reverified
    AND title_or_provenance_reverified
    AND compromise_or_loss_evidence_bound
    AND recovery_PoW_verified
    AND recovery_PoC_concept_verified
    AND alternate_COC_verified
    AND recovery_PoS_bond_verified
    AND multisource_or_quorum_verified
    AND freshness_verified
    AND recovery_not_revoked
    AND human_approval_verified
    AND (NOT active_dispute OR dispute_resolution_verified)
```

Allowed v1 recovery reasons are:

- `LOST_CONTROL`
- `COMPROMISED_CONTROL`
- `CUSTODY_FAILURE`
- `TECHNICAL_RECORD_CORRECTION`

`OWNER_CHANGE` is intentionally not a recovery reason; ownership change belongs in the governed transfer lane.

Recovery readiness is also bound to the lineage:

```text
Governed_recovery_ready =
    Base_recovery_ready
    AND lineage_internally_consistent
    AND prior_poo_digest == active_tip_digest
    AND claimant_id == active_tip_claimant_id
    AND recovery.asset_id == active_tip.asset_id
```

Only the combined state reports:

`RECOVERY_READY_WITH_LINEAGE_GUARD`

and the system still hard-codes:

```text
ownership_restored = false
control_rotated = false
transfer_executed = false
live_value_authorized = false
legal_title_changed = false
conflict_winner_selected = false
lineage_auto_resolved = false
```

An active dispute blocks recovery unless `dispute_resolution_verified` is explicitly present.

## Lineage and double-transfer protection

`security/poo/lineage_guard.py` treats ownership history as a single technical lineage per asset. It does not choose a legal owner; it checks structural integrity of the PoO chain.

A valid lineage requires:

- exactly one genesis PoO;
- genesis event type `CLAIM`;
- unique PoO digests;
- one non-empty `asset_id` across the lineage;
- every predecessor to exist;
- no successor from a revoked parent;
- no cycles;
- no parent with more than one successor;
- every record with a successor to be marked superseded;
- a terminal record not to be marked superseded; and
- exactly one active technical tip.

Two successors referencing the same prior PoO are therefore not two equally acceptable ownership records. They produce:

`LINEAGE_REVIEW_REQUIRED`

with `forked ownership lineage detected`.

Only a structurally consistent chain reports:

`LINEAGE_INTERNALLY_CONSISTENT`

and even then `legal_title_established = false`.

## Governed lineage dispute state

`security/poo/audit_projection.py` projects lineage integrity through the same Worldshepherd control plane as claim, transfer, and recovery evidence.

A healthy lineage produces:

```text
ECHO_POO_LINEAGE_ACCEPTED
PRIME_POO_LINEAGE_ELIGIBLE
SARA_POO_LINEAGE_MONITORABLE
OVERWATCH_POO_LINEAGE_HEALTHY
```

A fork, cycle, missing predecessor, invalid technical PoO, multiple active tips, or other structural lineage failure produces:

```text
ECHO_POO_LINEAGE_CONFLICT_CUSTODIED
PRIME_POO_LINEAGE_BLOCKED
SARA_POO_LINEAGE_DISPUTE_BLOCK
OVERWATCH_POO_LINEAGE_CONFLICT_ACTIVE
```

The projection records `lineage_checked`, `lineage_valid`, `fork_detected`, `cycle_detected`, the active-tip digest when valid, issue count, and conflict class (`NONE`, `FORK`, `CYCLE`, `STRUCTURAL`, or `MULTIPLE`). It always keeps:

```text
conflict_winner_selected = false
lineage_auto_resolved = false
```

Worldshepherd therefore records and blocks a conflicting lineage without deciding which claimant has legal title.

## Native SARA governance audit path

Claim, transfer-readiness, recovery-readiness, and lineage-integrity decisions are projected through:

`WS-POO-GOVERNANCE-DECISION-V2`

The native SARA adapter emits four bounded governance events under:

`WS-POO-SARA-AUDIT-EVENT-V2`

```text
poo_echo_state
poo_prime_state
poo_sara_state
poo_overwatch_state
```

They use SARA's existing durable event outbox and canonical `AuditRecord` path with at-least-once delivery semantics. One server-generated PoO audit-instance ID ties the four stage events together.

The SARA boundary enforces these additional invariants:

- `TRANSFER_READINESS` requires `lineage_checked = true`;
- `RECOVERY_READINESS` requires `lineage_checked = true`;
- a ready transfer/recovery requires `lineage_valid = true`;
- a ready transfer/recovery requires `previous_poo_digest == active_tip_digest`;
- invalid lineage cannot expose an active technical tip;
- valid lineage must have zero issues and conflict type `NONE`;
- lineage-integrity events cannot grant ownership/transfer/recovery readiness;
- blocked lineage states remain auditable; and
- no audit projection may assert automatic conflict resolution or select a winner.

The adapter rejects any projection that attempts to set any of these true:

```text
ownership_changed
transfer_executed
live_value_authorized
legal_title_established
legal_title_transferred
control_rotated
conflict_winner_selected
lineage_auto_resolved
```

This audit path records governed evidence; it does not create an ownership-changing transaction engine.

## Worldshepherd mapping

- **ECHO:** stores provenance, claim events, evidence hashes, revocations, PoC/COC evidence, prior/new PoO lineage, disputes, recovery evidence, transfer evidence, lineage-conflict evidence, and audit lineage.
- **PRIME:** enforces ownership policy, required predicates, PoC acceptance criteria, COC rules, stake rules, asset-class rules, revocation policy, transfer/recovery policy, active-lineage requirements, and dispute policy.
- **SARA:** orchestrates bounded claim, transfer, recovery, lineage-dispute, and review workflows with required human approvals and durable audit custody.
- **OVERWATCH:** monitors expiration, revocation, stale COC evidence, bond state, conflicts, duplicate claims, lineage forks/cycles/stale-tip references, recovery state, and unresolved disputes.
- **QCRYPTO:** supplies crypto-agility and hybrid/PQ migration policy for signatures, COC challenges, transfer authorization, and recovery evidence.

## Asset classes

PoO can be adapted to:

- digital assets and software/IP;
- physical equipment with serial/secure-element/PUF/manufacturer provenance;
- datasets and model artifacts;
- licenses/entitlements;
- custody positions;
- tokenized representations of off-chain assets.

For off-chain regulated or titled property, PoO remains an evidence layer and must defer to the relevant authoritative registry or legal process.

## Threat model

| Attack | PoW | PoC | COC | PoS | Title/provenance | Lineage control | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| cheap Sybil claims | helps | neutral | helps | helps | neutral | neutral | harder |
| broken/fake ownership mechanism | neutral | detects failed concept | neutral | neutral | neutral | neutral | blocked |
| stolen key | weak | may still pass | may pass until revoked | neutral | helps | active-tip/recovery checks | recovery/revocation required |
| wealthy false claimant | weak | insufficient alone | blocks without COC | insufficient alone | blocks without provenance | active-tip claimant check | fail closed |
| compute-rich false claimant | insufficient alone | insufficient alone | blocks without COC | neutral | blocks without provenance | active-tip check | fail closed |
| replayed old claim | neutral | stale PoC can fail policy | freshness/COC check | neutral | lineage helps | stale-tip rejection | blocked |
| registry/provenance conflict | neutral | neutral | neutral | neutral | detects conflict | dispute state | human/policy resolution |
| unauthorized transfer | neutral | neutral | recipient COC insufficient | neutral | transition blocked | active-tip/current-owner binding | blocked |
| double-transfer/conflicting lineage | neutral | neutral | neutral | neutral | lineage fork check | fork quarantine | blocked/review required |
| cyclic/missing-parent lineage | neutral | neutral | neutral | neutral | lineage integrity | structural quarantine | blocked/review required |
| compromised current key recovery | fresh work required | recovery mechanism demonstrated | alternate COC required | fresh bond required | reverified | same active-tip claimant required | governed recovery only |
| disputed recovery | insufficient | insufficient | insufficient | insufficient | dispute resolution required | lineage remains blocked | blocked until resolved |

## Claims boundary

PoO v1 does **not** claim:

- legal title adjudication;
- government registry authority;
- automatic conflict-winner selection;
- automatic lineage conflict resolution;
- automatic transfer execution;
- automatic credential/key rotation;
- automatic prior-control revocation;
- live-value movement authority;
- external validation or certification;
- that PoW, PoC, COC, or PoS alone proves ownership.

## Validation record

The PoO V2 core branch is validated separately from this lineage-governance increment so that each proof point has an immutable SHA. This branch adds active-tip binding, conflict quarantine, Governance Decision V2, SARA Audit Event V2, and lineage-governed transfer/recovery readiness.

Current lineage-governance status: **IMPLEMENTED IN SOFTWARE / EXACT-HEAD VALIDATION PENDING**.
