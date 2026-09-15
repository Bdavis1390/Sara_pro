# Worldshepherd QCRYPTO — Governed Evidence for Post-Quantum Migration Readiness

**Document class:** PUBLIC TECHNICAL WHITE PAGE / NON-CONFIDENTIAL  
**Publication state:** POSTABLE CANDIDATE — final GO requires the QCRYPTO White Page Publication Gate to pass on the publication revision.  
**Claims state:** PROVEN INTERNALLY for the bounded software behavior described below.  
**Validated implementation anchor:** `b65302d2e849dcad67b553378d3fce11b404f3c5`  
**Evidence artifact digest:** `sha256:15dc39ef59a8bbe10e48f858f1bb42d34c9c35adb33045b9f7635201c5df698e`

## Why this exists

Post-quantum migration is not only an algorithm-selection problem. Organizations also need to know which cryptographic dependencies exist, which evidence supports a migration decision, who authorized a plan, whether evidence was preserved across retries and failures, and whether operational claims remain inside what has actually been demonstrated.

Worldshepherd QCRYPTO applies the existing SARA / ECHO SENTINEL LINK / PRIME SENTINEL / OVERWATCH governance pattern to that problem. The current implementation is an internal control-plane and evidence-management capability. It is not a quantum computer, a key-recovery system, or a production cryptographic migration engine.

## What is demonstrated internally

The validated implementation records a bounded four-stage QCRYPTO decision chain:

1. **ECHO SENTINEL LINK** — records provenance/evidence state.
2. **PRIME SENTINEL** — records the bounded recommendation state.
3. **SARA** — records the human-governance/authorization state.
4. **OVERWATCH** — records the resulting tracking state.

Each semantic decision receives a deterministic `decision_digest`. Each concrete four-event submission receives a separate server-generated `audit_instance_id`, so two identical semantic decisions can be distinguished as separate audit instances.

The SARA→ECHO evidence bridge has been internally exercised in an isolated container deployment with retained ECHO history already present. The selected QCRYPTO instance must still reconcile as four explicit `MATCHED` records with zero `SARA_ONLY` and zero `PAYLOAD_MISMATCH` records. Unrelated retained ECHO evidence is allowed to remain `ECHO_ONLY` without weakening the selected-instance match requirement.

The same bridge has tested at-least-once recovery behavior. Replays deduplicate previously stored evidence, interrupted multi-record delivery can recover by storing only missing records, and simulated acknowledgement loss can be retried without creating duplicate semantic evidence. Synchronization bookkeeping is kept outside the canonical decision fields so retry/pending records do not inflate the original four-stage audit reconstruction.

## Evidence snapshot

For implementation anchor `b65302d2e849dcad67b553378d3fce11b404f3c5`, the exact-head validation set completed successfully, including:

- QCRYPTO Risk Gate;
- QCRYPTO ECHO Bridge Gate;
- SARA Verified Local v1 Gate;
- Required Test and Build;
- CodeQL Required Gate;
- SARA Commit Closure Evidence;
- SARA Operational Resilience Drill;
- SARA Replacement Environment Restore;
- SARA Rollback Drill;
- SARA NIST 800-171 SSP Precursor; and
- SARA TLS Private Backend Architecture.

The deployed bridge artifact records one unrelated retained ECHO event, four matched QCRYPTO records, first-delivery storage of four records, replay deduplication of four records, five total ECHO records, and a five-event checkpoint. The checkpoint algorithm in this validated configuration is **Ed25519**.

## Claims boundary

This white page does **not** claim or establish:

- production deployment;
- cryptographic migration execution;
- blockchain transaction signing or movement of value;
- live-value authorization;
- a current production-strength quantum break of any cryptocurrency or cryptographic system;
- post-quantum security of the current Ed25519 ECHO checkpoint;
- Federal compliance, certification, or authorization;
- WS-CAE conformance;
- third-party, partner, regulator, or government validation;
- physical-system qualification; or
- that a passing test suite alone proves operational adoption.

No real third-party wallet, private key, exchange, bridge, network, or fund is targeted by this work.

## Practical role

The demonstrated capability is best described as a **claims-controlled migration-readiness evidence layer**. It can support future work such as cryptographic inventory, migration-plan provenance, authorization tracking, evidence reconciliation, retry-safe audit transport, and readiness dashboards while preserving the separation between research evidence, implementation evidence, human approval, and operational execution.

## Publication note

This page is intentionally narrower than the underlying research program. Public posting is appropriate only when the repository publication gate is green and the implementation anchor and evidence digest above remain unchanged. Any later implementation revision requires its own exact-head validation before its claims can replace this anchor.
