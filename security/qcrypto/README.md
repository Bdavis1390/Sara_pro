# Worldshepherd QCRYPTO Risk Gate

This package implements a defensive, claims-controlled quantum-cryptography risk gate for migration planning.

## Purpose

QCRYPTO separates four quantities that are often conflated:

1. **logical width** — how many logical qubits a published complete attack requires;
2. **gate cost / depth** — how much quantum work the attack requires;
3. **architecture-specific runtime** — how long a compiled attack is estimated to take on a stated hardware/QEC architecture;
4. **exposure and migration windows** — how long a public key is available to attack and how long defenders need to migrate.

A low logical-qubit count does **not** imply a fast practical attack. A point-addition or arithmetic subroutine result does **not** imply a complete end-to-end key break. Q4 is reserved for a production-strength break demonstrated in a controlled, authorized environment.

## Threat ladder

- **Q0** — mathematical/resource issue known; no operational overlap demonstrated.
- **Q1** — materially compressed complete-attack resources; accelerated validation required.
- **Q2** — modeled complete-attack runtime overlaps the supplied public-key exposure window.
- **Q3** — Q2 plus a non-positive migration margin.
- **Q4** — production-strength break demonstrated in a controlled, authorized environment.

## September 2026 trigger

Luo et al., `arXiv:2607.13816`, present a complete Shor algorithm implementation for prime-field ECDLP requiring only **835 logical qubits** for a 256-bit curve. The construction is space-efficient but has a large gate cost: its leading Toffoli term is `919*n^3/log2(n)`, which evaluates to **1,927,282,688** at `n=256`, before the stated lower-order `O(n^2)` term.

That result therefore tightens the **width** frontier substantially while not, by itself, establishing a fast physical attack. QCRYPTO encodes that distinction explicitly.

## Safety boundary

This module does not implement Shor's algorithm, private-key recovery, wallet interaction, transaction signing, live-network probing, or attacks against third-party systems. It is a defensive resource-estimate and migration-risk classifier.

## Validation

Run:

```bash
python -m py_compile security/qcrypto/qcrypto_guard.py
python -m unittest discover -s security/qcrypto -p 'test_*.py' -v
python -m json.tool security/qcrypto/baseline_2026-09-12.json >/dev/null
```

The GitHub Actions workflow `.github/workflows/qcrypto-risk-gate.yml` enforces these checks for changes to this package.
