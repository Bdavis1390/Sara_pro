# Worldshepherd QCRYPTO Risk Gate

This package implements a defensive, claims-controlled quantum-cryptography risk gate for migration planning.

## Purpose

QCRYPTO separates quantities that are frequently conflated:

1. **logical width** — how many logical qubits a published complete attack requires;
2. **gate cost / depth** — how much quantum work the attack requires;
3. **architecture-specific runtime** — how long a compiled attack is estimated to take on a stated hardware/QEC architecture;
4. **measured QEC overhead** — what a concrete error-correcting code has demonstrated on real hardware;
5. **hardware roadmap maturity** — what a vendor plans versus what has actually been demonstrated;
6. **exposure and migration windows** — how long a public key is available to attack and how long defenders need to migrate.

A low logical-qubit count does **not** imply a fast practical attack. A low physical/logical code-block ratio does **not** imply a complete-application physical-qubit count. A point-addition or arithmetic subroutine result does **not** imply a complete end-to-end key break. A future vendor roadmap is **not** demonstrated hardware. Q4 is reserved for a production-strength break demonstrated in a controlled, authorized environment.

## Threat ladder

- **Q0** — mathematical/resource issue known; no operational overlap demonstrated.
- **Q1** — materially compressed complete-attack resources; accelerated validation required.
- **Q2** — modeled complete-attack runtime overlaps the supplied public-key exposure window.
- **Q3** — Q2 plus a non-positive migration margin.
- **Q4** — production-strength break demonstrated in a controlled, authorized environment.

## September 2026 attack-width trigger

Luo et al., `arXiv:2607.13816`, present a complete Shor algorithm implementation for prime-field ECDLP requiring only **835 logical qubits** for a 256-bit curve. The construction is space-efficient but has a large gate cost: its leading Toffoli term is `919*n^3/log2(n)`, which evaluates to **1,927,282,688** at `n=256`, before the stated lower-order `O(n^2)` term.

That result tightens the **width** frontier substantially while not, by itself, establishing a fast physical attack. QCRYPTO encodes that distinction explicitly.

## September 2026 same-vendor roadmap collision trigger

IonQ's current public roadmap targets approximately **10,000 physical / 800 logical qubits in 2027** and **20,000 physical / 1,600 logical qubits in 2028**, with the roadmap explicitly presented as forward-looking targets.

IonQ's separate Walking Cat secp256k1 resource estimate reports an end-to-end attack envelope of approximately **19,397 physical / about 1,450 logical qubits** and **25.7 days per attempt** under its architecture assumptions.

Those numbers create a material planning signal: the vendor's **2028 target numerically overlaps the vendor's own attack envelope**. This is not evidence that the 2028 target will be achieved, that every required QEC/runtime assumption will hold, or that a production key can be broken today.

`assess_roadmap_collision()` therefore creates a separate roadmap evidence plane:

- `VENDOR_ROADMAP_TARGET` remains distinct from demonstrated hardware;
- same-architecture logical/physical overlap can trigger `SAME_ARCHITECTURE_ATTACK_ENVELOPE_COLLISION`;
- a collision can increase migration urgency to `ACCELERATE_MIGRATION_VALIDATION` or `MIGRATION_SCHEDULE_AT_RISK`;
- roadmap evidence alone can never establish Q2, Q3, Q4, or Q-day.

This fixes a common failure mode in quantum-risk analysis: treating vendor roadmaps as either meaningless marketing or as already-delivered capability. QCRYPTO records them as forward evidence that can compress the available migration schedule without upgrading capability maturity.

## September 2026 hardware-QEC trigger

Quantinuum's C4-Helix experiment, `arXiv:2609.03194`, reports a `[[20,2,6]]` code on Helios: **20 physical ions carrying two logical qubits**, repeated error correction at about `4.6e-5` error per logical qubit per cycle, and complete two-logical-qubit Clifford benchmarking at about `2.8e-4` error per logical Clifford. The encoded results outperform corresponding unencoded physical baselines without postselection.

This is substantial evidence that useful QEC overhead can be much lower than older surface-code intuition suggests on some architectures. It is **not** evidence that a complete 835-logical-qubit ECDLP attack needs only 8,350 physical ions.

`assess_qec_bridge()` therefore treats `835 × 10 = 8,350` only as a **bare code-block floor** and blocks promotion to a physical attack estimate until all of the following are supplied:

- universal non-Clifford fault-tolerant execution,
- architecture-specific compilation of the complete attack,
- justified scaling to the attack's logical width and operation count,
- and a complete fault-tolerant overhead model covering ancillas, magic-state/factory resources, routing, decoding and runtime reliability.

## Claims-control rule

Hardware progress, roadmap targets, QEC evidence and attack-algorithm progress are tracked independently and may all compress the threat frontier. Cross-paper multiplication is prohibited unless architecture compatibility and complete fault-tolerant overhead are established. Roadmap collision is a migration-planning signal, never a production-break claim.

## Safety boundary

This module does not implement Shor's algorithm, private-key recovery, wallet interaction, transaction signing, live-network probing, or attacks against third-party systems. It is a defensive resource-estimate, QEC-evidence, roadmap-collision and migration-risk classifier.

## Validation

Run:

```bash
python -m py_compile security/qcrypto/qcrypto_guard.py
python -m unittest discover -s security/qcrypto -p 'test_*.py' -v
python -m json.tool security/qcrypto/baseline_2026-09-12.json >/dev/null
```

The GitHub Actions workflow `.github/workflows/qcrypto-risk-gate.yml` enforces these checks for changes to this package.
