# Worldshepherd Proof of Ownership (PoO) v1

## Purpose

PoO is a claims-controlled ownership-attestation protocol that composes independent evidence instead of treating any one consensus primitive as ownership.

### The three proof legs

- **PoW — Proof of Work:** claim-specific bounded work tied to the asset and claim. This adds freshness/cost and makes cheap claim flooding harder. It does **not** prove ownership by itself.
- **PoC — Proof of Concept:** a bounded demonstration that the claimed ownership mechanism for the asset actually works and can be independently checked. A PoC might demonstrate that an asset-binding method, custody handoff, secure-element challenge, registry integration, or other ownership mechanism performs as claimed. It does **not** prove current control or legal ownership by itself.
- **PoS — Proof of Stake:** bonded/slashable value or other accountable stake tied to the claim. This creates economic consequence for fraudulent assertions. It does **not** prove ownership by itself.

PoO separately requires **control/custody verification**. That predicate establishes that the claimant currently controls the asset-bound authority or custody surface. It is intentionally not called PoC.

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
    AND control_or_custody_verified
    AND PoS_bond_verified
    AND freshness_verified
    AND not_revoked
```

A claimant cannot compensate for missing proof-of-concept, control/custody, or provenance by adding more work or stake.

## Why control/custody is separate from PoC

Proof of Concept answers: **does the claimed ownership mechanism work as demonstrated?**

Control/custody verification answers: **does this claimant currently control the asset-bound authority?**

Those are different questions. A successful PoC cannot establish that the present claimant controls the asset, and a valid control proof cannot establish that the broader ownership mechanism has been demonstrated or validated.

## Why the title/provenance predicate is separate

PoW, PoC, control/custody, and PoS provide computational, demonstrative, control, and economic evidence. They cannot manufacture legal title. A valid PoO therefore means **technical ownership attestation under the supplied evidence**, not a court judgment, government registry entry, or statutory title determination.

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

Evidence-verification booleans are deliberately excluded from the semantic digest. This allows the evidence state to be re-evaluated without changing the underlying ownership claim identity.

## Governed transfer and supersession

A transfer never edits or erases the prior PoO. It prepares a **new PoO candidate** whose `previous_poo_digest` points to the prior attestation.

Transfer readiness is also fail-closed:

```text
Transfer_ready =
    prior_PoO_valid
    AND asset_continuity_verified
    AND current_owner_authorized
    AND recipient_identity_bound
    AND recipient_PoC_concept_verified
    AND recipient_control_or_custody_verified
    AND recipient_PoW_verified
    AND recipient_PoS_bond_verified
    AND title_or_provenance_transition_bound
    AND freshness_verified
    AND no_active_dispute
    AND transfer_not_revoked
    AND human_approval_verified
```

When every predicate passes, Worldshepherd reports only:

`READY_FOR_GOVERNED_SUPERSESSION`

This means the evidence package is internally ready to produce the next technical PoO candidate. It does **not** mean a transfer has executed, funds/value moved, legal title changed, or a government/third-party registry accepted the transition.

The transfer guard hard-codes:

```text
transfer_executed = false
live_value_authorized = false
legal_title_transferred = false
```

The derived recipient candidate must itself pass the ordinary PoO evaluator, and its `previous_poo_digest` must match the prior ownership record. A disputed, stale, revoked, unauthorized, or incomplete transfer cannot derive the next PoO candidate.

## Disputes and recovery

An active ownership dispute blocks ordinary supersession even when PoW, PoC, control/custody, and PoS evidence otherwise pass. Recovery or exceptional title correction should therefore be modeled as a separate, explicitly governed process with stronger provenance, human review, and ECHO evidence custody rather than as a hidden bypass in the transfer evaluator.

## Worldshepherd mapping

- **ECHO:** stores provenance, claim events, evidence hashes, revocations, PoC evidence, prior/new PoO lineage, disputes, and transfer evidence.
- **PRIME:** enforces ownership policy, required predicates, PoC acceptance criteria, control/custody rules, stake rules, asset-class rules, revocation policy, and dispute policy.
- **SARA:** orchestrates bounded claim/transfer workflows and required human approvals.
- **OVERWATCH:** monitors expiration, revocation, stale control proofs, bond state, conflicts, duplicate claims, and unresolved disputes.
- **QCRYPTO:** supplies crypto-agility and hybrid/PQ migration policy for signatures, control challenges, and transfer authorization evidence.

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

| Attack | PoW | PoC | Control/custody | PoS | Title/provenance | Result |
|---|---:|---:|---:|---:|---:|---|
| cheap Sybil claims | helps | neutral | helps | helps | neutral | harder |
| broken/fake ownership mechanism | neutral | detects failed concept | neutral | neutral | neutral | blocked |
| stolen key | weak | may still pass | may pass until revoked | neutral | helps | revocation/recovery required |
| wealthy false claimant | weak | insufficient alone | blocks without control | insufficient alone | blocks without provenance | fail closed |
| compute-rich false claimant | insufficient alone | insufficient alone | blocks without control | neutral | blocks without provenance | fail closed |
| replayed old claim | neutral | stale PoC can fail policy | freshness/control check | neutral | lineage helps | rejected when stale/revoked |
| registry/provenance conflict | neutral | neutral | neutral | neutral | detects conflict | human/policy resolution |
| unauthorized transfer | neutral | neutral | recipient proof insufficient | neutral | transition blocked | current-owner authorization required |
| double-transfer/conflicting lineage | neutral | neutral | neutral | neutral | lineage/dispute check | blocked pending resolution |

## Claims boundary

PoO v1 does **not** claim:

- legal title adjudication;
- government registry authority;
- automatic transfer execution;
- live-value movement authority;
- external validation or certification;
- that PoW, PoC, control/custody, or PoS alone proves ownership.

Validation record:

- Ownership-attestation core with **PoC = Proof of Concept**: **PROVEN INTERNALLY — protocol logic only** at `4aa948fb98ff3f97bc2acc724326a2c984f31b51`.
- Governed transfer/supersession extension: **IMPLEMENTED IN SOFTWARE / exact-head validation pending** until the transfer regressions pass on the current branch head.
