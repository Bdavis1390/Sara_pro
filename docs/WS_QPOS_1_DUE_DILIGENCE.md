# WS-QPOS-1 — Post-Quantum Proof-of-Stake Preservation Due Diligence

Status: **BOUNDED PRESERVATION PROOF IMPLEMENTED; EXACT-HEAD CI REQUIRED FOR PROMOTION**

This document defines the Worldshepherd due-diligence basis for preserving proof-of-stake while replacing quantum-vulnerable validator authentication. It distinguishes what can be machine-proved in the Worldshepherd model from what remains an external cryptographic, protocol, implementation, or deployment assumption.

## 1. External technical baseline

### Ethereum proof-of-stake invariants

Ethereum's current public documentation describes finality as stake-weighted: two-thirds of total staked ether voting for checkpoint progression is required for justification/finality, and slashing is part of the crypto-economic safety model.

Official source:
- Ethereum, Gasper: https://ethereum.org/developers/docs/consensus-mechanisms/pos/gasper/
- Ethereum, Proof-of-stake: https://ethereum.org/developers/docs/consensus-mechanisms/pos/

WS-QPOS-1 therefore treats validator economic identity and stake weight as protected state that credential migration must not alter.

### Ethereum post-quantum consensus direction

The Ethereum Foundation Protocol cluster states a target of quantum resistance across execution, consensus, and data by December 2029. The remaining consensus work includes post-quantum attestations required for full economic finality. The official PQ roadmap describes a PQ key registry, post-quantum attestations, leanXMSS, leanVM, and longer-term full PQ consensus.

Official sources:
- EF Protocol priorities, 2026-09-07: https://blog.ethereum.org/2026/09/07/protocol-priorities
- Ethereum quantum-resistance roadmap: https://ethereum.org/roadmap/security/quantum-resistance/
- Ethereum Post-Quantum program: https://pq.ethereum.org/

### Aggregation and decentralization constraint

Draft EIP-8292 specifies a post-quantum attestation-aggregator role because hash-based signatures do not aggregate like BLS. Its design explicitly seeks to keep ordinary validators light while assigning expensive proof generation to opt-in higher-specification aggregators.

Official source:
- EIP-8292, Post-Quantum Attestation Aggregators: https://eips.ethereum.org/EIPS/eip-8292

WS-QPOS-1 therefore treats aggregator eligibility as operational metadata that must not change validator stake weight.

### NIST post-quantum and crypto-agility baseline

NIST finalized FIPS 204 (ML-DSA) and FIPS 205 (SLH-DSA) for post-quantum digital signatures. NIST's crypto-agility guidance defines crypto agility around replacing/adapting cryptographic algorithms while preserving security and ongoing operations.

Official sources:
- FIPS 204: https://csrc.nist.gov/pubs/fips/204/final
- FIPS 205: https://csrc.nist.gov/pubs/fips/205/final
- NIST CSWP 39, Considerations for Achieving Crypto Agility: https://csrc.nist.gov/News/2025/considerations-for-achieving-crypto-agility
- NIST Migration to PQC: https://www.nccoe.nist.gov/applied-cryptography/migration-to-pqc

## 2. Worldshepherd preservation theorem — bounded model

WS-QPOS-1 models a validator as two separated planes:

**Protected economic plane**
- persistent validator ID;
- stake;
- effective balance / consensus weight;
- withdrawal owner;
- slashed state;
- slashing history.

**Replaceable authentication plane**
- classical credential;
- PQ credential;
- PQ scheme identifier;
- authentication mode;
- aggregator eligibility.

Allowed migration sequence:

`CLASSICAL -> PQ_REGISTERED -> HYBRID_REQUIRED -> PQ_PRIMARY -> CLASSICAL_DISABLED`

Emergency mode is allowed only after a PQ credential exists.

The machine-checked preservation obligation is:

`economic_projection(before) == economic_projection(after)`

for every allowed credential transition in the finite proof domain.

## 3. Properties the model is designed to prove

1. Validator identity is invariant under credential migration.
2. Stake and effective balance are invariant under credential migration.
3. Withdrawal ownership is invariant under credential migration.
4. Slashed state and slashing history are invariant under credential migration.
5. Aggregator-role assignment cannot alter modeled consensus weight.
6. The stake-weighted supermajority threshold is invariant when credentials change.
7. Hybrid classical+PQ evidence cannot double-count one validator's stake when vote weight is keyed by validator identity.
8. Classical authentication is rejected after classical sunset.
9. Invalid migration-order transitions fail closed.
10. Migration readiness is measured by effective stake, not validator count.
11. Duplicate validator IDs and duplicate PQ credentials fail registry validation in the model.

## 4. What the proof does not prove

A WS-QPOS-1 PASS does **not** prove:
- that ML-DSA, SLH-DSA, leanXMSS, leanVM, a SNARK/STARK, or any other primitive is mathematically secure in production;
- that a particular Ethereum client or other blockchain client implements the model correctly;
- that consensus liveness, networking, timing, aggregation throughput, or mainnet interoperability are production-qualified;
- that a migration ceremony remains safe after classical credential compromise;
- that any deployed validator, wallet, staking service, exchange, bridge, or custody system is post-quantum secure;
- regulatory compliance, certification, external validation, or mainnet approval.

The proof is conditional on the selected PQ authentication/aggregation stack being secure and correctly implemented.

## 5. Proof implementation

- Model: `security/qcrypto/qpos_preservation.py`
- Regression suite: `tests/test_qcrypto_qpos_preservation.py`
- Proof runner: `scripts/qcrypto_qpos_proof.py`
- CI: `.github/workflows/qcrypto-qpos-proof.yml`

The proof runner emits schema `WS-QPOS-1-PRESERVATION-PROOF-V1`, an evidence SHA-256, test-case counts, assumptions, proven properties, and excluded claims.

The strongest warranted claim after an exact-head CI PASS is:

> **PROVEN INTERNALLY — bounded model proof that the defined WS-QPOS-1 credential-migration transitions preserve modeled proof-of-stake economic identity, stake weight, withdrawal ownership, slashing history, and stake-weighted threshold semantics under the stated assumptions.**

That claim is intentionally narrower than “production post-quantum proof-of-stake is proven.”

## 6. Remaining due-diligence gates after bounded proof

To advance beyond bounded model proof toward production-grade post-quantum consensus evidence, separate evidence is required for:

1. concrete PQ validator signature scheme selection and cryptographic review;
2. stateful-signature lifecycle safety if leanXMSS/XMSS-derived schemes are used;
3. aggregation/proof-system soundness and verifier implementation;
4. validator-key registry and recovery ceremony under compromised-classical-key scenarios;
5. networking and bandwidth benchmarks at realistic validator counts;
6. home-validator hardware accessibility and decentralization impact;
7. aggregator censorship/failure recovery and incentive analysis;
8. full slashing/finality semantics against the production consensus specification;
9. client interoperability across independent implementations;
10. fault-injection, restart, rollback, fork-transition, and long-duration testnet evidence;
11. independent third-party reproduction.

Until those are completed, WS-QPOS-1 remains a preservation proof of the migration state model, not proof of a production PQ blockchain.
