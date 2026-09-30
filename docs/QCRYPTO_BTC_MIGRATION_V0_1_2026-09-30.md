# Worldshepherd QCRYPTO — Bitcoin Migration Baseline v0.1

Status: **IMPLEMENTED IN SOFTWARE — exact-head repository CI and external validation pending**
Date: 2026-09-30
Program: Worldshepherd / QCRYPTO
Runtime target: SARA / PRIME SENTINEL / ECHO SENTINEL LINK / OVERWATCH
Branch: `feature/qcrypto-btc-migration-v0-1`

## 1. Purpose

This baseline converts Bitcoin post-quantum migration from a headline-level risk claim into an evidence-bounded engineering workflow.

It does **not** claim that a cryptographically relevant quantum computer (CRQC) currently exists, that Bitcoin theft is imminent, that a Bitcoin post-quantum output type has been adopted, or that Worldshepherd presently provides post-quantum protection for Bitcoin.

The implementation separates five questions that must not be collapsed into one score:

```text
on-chain public-key visibility
!= unspent-value exposure
!= key/address reuse
!= existence of a CRQC
!= existence/adoption of a Bitcoin-compatible PQ migration path
```

## 2. Current external evidence

### 2.1 Bitcoin BIP 361

The canonical Bitcoin BIPs repository lists **BIP 361, Post Quantum Migration and Legacy Signature Sunset**, as **Draft**, assigned 2026-02-11. The proposal explicitly depends on a future post-quantum signature/output BIP and describes staged migration followed by legacy-signature restrictions/sunset. Draft status is not Bitcoin consensus or deployment.

Authoritative source:
- https://github.com/bitcoin/bips/blob/master/bip-0361.mediawiki

Mirror:
- https://bitcoin.org/bip/361/

### 2.2 NIST PQC baseline

NIST states that its first finalized PQC standards are ready for implementation and that migration planning should begin now. NIST also records the July 2026 withdrawal of HAWK from its additional-signature process after a mathematical vulnerability was reported. That event is a concrete reason to design QCRYPTO for **algorithm agility**, not for permanent binding to one candidate.

Sources:
- https://www.nist.gov/pqc
- https://pages.nist.gov/nccoe-migration-post-quantum-cryptography/
- https://www.nist.gov/news-events/news/2026/05/nine-candidates-advance-third-round-additional-digital-signatures-pqc

NIST standards are not automatically Bitcoin script/signature mechanisms. Bitcoin integration remains a separate consensus, implementation, interoperability, wallet, custody, and deployment problem.

## 3. Implemented v0.1 software

`deployments/sara_verified_local_v1/worldshepherd_sara/qcrypto_btc_migration.py` implements:

1. a strict Bitcoin output/key-exposure evidence record;
2. explicit treatment of P2PK, P2TR and bare multisig as outputs with public-key material observable on chain;
3. separate handling of P2PKH/P2WPKH hash-committed outputs whose public key is not yet observed in the supplied evidence;
4. separate handling of P2SH/P2WSH where the hash alone does not establish the hidden script/key structure;
5. explicit reuse handling for a revealed key that also controls other unspent outputs;
6. deterministic migration-priority assignment without predicting CRQC arrival;
7. fail-closed classification for unknown or insufficient output evidence;
8. domain-separated canonical serialization and SHA-256 evidence digesting;
9. a bounded migration-state model requiring human approval beyond inventory;
10. test evidence before `HYBRID_TESTED` or later states;
11. rollback-drill evidence before `MIGRATION_READY` or later states;
12. target-output declaration before `MIGRATED` or later states;
13. external validation before `LEGACY_SUNSET_ELIGIBLE`;
14. prohibition on marking legacy signatures disabled before the final gated state.

The state labels are **governance claims**, not proof that a Bitcoin-compatible hybrid/PQ signature scheme already exists.

## 4. Exposure taxonomy

| Class | Meaning | v0.1 treatment |
|---|---|---|
| `PUBLIC_KEY_ON_CHAIN` | public-key material is already observable in the evidence | highest migration-planning priority when unspent value remains or the same key controls other unspent outputs |
| `HASH_COMMITTED_KEY_NOT_OBSERVED` | P2PKH/P2WPKH hash commitment with no observed public key in the supplied evidence | preserve custody and plan migration; do not describe the hash commitment as permanent PQ protection |
| `SCRIPT_HASH_NOT_OBSERVED` | P2SH/P2WSH without revealed script/key evidence | inventory hidden script/key dependencies before assigning a stronger claim |
| `SPENT_OUTPUT_KEY_EXPOSURE_RELEVANT_ONLY_IF_REUSED` | key is visible but the referenced output is spent | investigate reuse before assigning remaining-funds exposure |
| `INDETERMINATE` | evidence is incomplete or output type is unknown | fail closed to manual review |

`P0/P1/P2` in the implementation are **migration-planning priorities only**. They are not theft probabilities, time-to-break predictions, or market-risk scores.

## 5. Test baseline

`deployments/sara_verified_local_v1/tests/test_qcrypto_btc_migration.py` covers:

- P2TR/P2PK/bare-multisig exposed-key semantics;
- P2PKH/P2WPKH hash-commitment separation;
- P2SH/P2WSH script-hash separation;
- revealed-key override for a hash-based output form;
- spent-output vs reused-key distinction;
- semantic contradiction rejection;
- unknown-output fail-closed behavior;
- stable/mutation-sensitive canonical digests;
- human-approval gate;
- test-evidence gate;
- rollback-drill gate;
- external-validation gate;
- legacy-sunset gate.

The reference module and tests were exercised in an isolated pytest environment with **19 passing tests** before commit. Repository CI on the exact branch head remains the authoritative gate.

## 6. Worldshepherd integration

### SARA

SARA owns orchestration only. It may inventory and route migration work but may not assert quantum capability or Bitcoin consensus state from an internal heuristic.

### PRIME SENTINEL

PRIME owns transition authorization. A migration state above `INVENTORIED` requires a human approval identifier. Future release authorization should bind:

```text
inventory digest
+ migration-policy revision
+ target output/signature type
+ wallet/build identity
+ test evidence digest
+ rollback evidence digest
+ human approval
```

A changed target, evidence set, wallet build or policy revision must invalidate the prior release decision.

### ECHO SENTINEL LINK

ECHO should preserve:

- original chain/script evidence reference;
- exposure record digest;
- classification result;
- transformation/version history;
- wallet/hardware context;
- migration decision lineage;
- later reclassification when new chain evidence appears.

No classification overwrite should erase the earlier evidence state.

### OVERWATCH

OVERWATCH should display separately:

- key visibility;
- unspent status;
- reuse status;
- migration state;
- evidence freshness;
- external Bitcoin PQ adoption state;
- CRQC assumption (`NO_CRQC_ASSUMED_PRESENT` in v0.1).

These must not be collapsed into a single red/yellow/green quantum-risk light.

## 7. Next gates

### G1 — exact-head CI

Run the full repository test matrix on the feature branch and retain the commit/workflow evidence.

### G2 — fixture-based chain parser

Add deterministic Bitcoin script fixtures for P2PK, P2PKH, P2SH, P2WPKH, P2WSH, P2TR and bare multisig. The parser must derive output type and public-key visibility rather than accepting caller assertions blindly.

### G3 — key-reuse reconciliation

Model one logical key controlling multiple outputs and prove that exposure observed in one historical spend propagates only to outputs proven to share that key.

### G4 — migration simulator

Add a non-broadcasting simulator that models wallet/output migration, fee/size effects, rollback and failure modes. No live mainnet signing or fund movement belongs in this gate.

### G5 — algorithm-agility registry

Add a QCRYPTO primitive registry with lifecycle states such as `CANDIDATE`, `STANDARDIZED`, `RESTRICTED`, `WITHDRAWN`, `DEPRECATED`. The HAWK withdrawal is the initial adversarial fixture demonstrating why algorithm status must be updatable without rewriting provenance.

### G6 — Bitcoin PQ interoperability gate

When a concrete Bitcoin PQ output/signature proposal has a stable specification and reference implementation, add authoritative fixtures and compatibility tests. Until then, `target_output_type` remains descriptive only and no Bitcoin PQ protection claim is permitted.

### G7 — external validation

Independent wallet/Bitcoin/PQC review is required before `LEGACY_SUNSET_ELIGIBLE` can represent anything beyond a local software state.

## 8. Claims block

```yaml
claim:
  statement: >-
    Worldshepherd QCRYPTO v0.1 implements a strict, evidence-bounded Bitcoin
    public-key exposure classifier, deterministic evidence digest, and human-gated
    migration-state model.
  status:
    - IMPLEMENTED_IN_SOFTWARE
  evidence:
    - deployments/sara_verified_local_v1/worldshepherd_sara/qcrypto_btc_migration.py
    - deployments/sara_verified_local_v1/tests/test_qcrypto_btc_migration.py
  limitations:
    - "No claim that a CRQC exists today."
    - "No Bitcoin post-quantum output/signature type is implemented by this module."
    - "No wallet keys, seed phrases, private keys or live funds are ingested."
    - "No mainnet transaction creation, signing or broadcast is performed."
    - "BIP 361 is Draft and depends on a future PQ signature/output proposal."
    - "NIST PQC algorithms are not automatically Bitcoin consensus mechanisms."
  next_gate: >-
    Exact-head repository CI, then fixture-derived script classification and
    key-reuse reconciliation before any migration-simulator claim.
```
