# Worldshepherd QCRYPTO Risk Gate

This package implements a defensive, claims-controlled quantum-cryptography risk gate for migration planning.

## Purpose

QCRYPTO separates quantities that are frequently conflated:

1. **logical width** — how many logical qubits a published complete attack requires;
2. **gate cost / depth** — how much quantum work the attack requires;
3. **architecture-specific runtime** — how long a compiled attack is estimated to take on a stated hardware/QEC architecture;
4. **measured QEC overhead** — what a concrete error-correcting code has demonstrated on real hardware;
5. **hardware roadmap maturity** — what a vendor plans versus what has actually been demonstrated;
6. **platform/manufacturing maturity** — whether relevant hardware has moved into fabricated prototypes and productization;
7. **classical real-time decoding capacity** — whether the classical QEC control plane can plausibly keep pace with many logical qubits;
8. **protocol mitigation maturity** — whether a proposed defense is only a specification, an executable draft, production software, or consensus-active;
9. **exposure and migration windows** — how long defenders have to complete migration.

A low logical-qubit count does **not** imply a fast practical attack. A future vendor roadmap is **not** demonstrated hardware. A fabricated prototype is **not** target-scale capability. A proposed decoder is **not** an integrated system. A draft mitigation specification is **not** consensus deployment.

## Threat ladder

- **Q0** — mathematical/resource issue known; no operational overlap demonstrated.
- **Q1** — materially compressed complete-attack resources; accelerated validation required.
- **Q2** — modeled complete-attack runtime overlaps the supplied exposure window.
- **Q3** — Q2 plus a non-positive migration margin.
- **Q4** — production-strength break demonstrated in a controlled, authorized environment.

## September 2026 attack-width trigger

Luo et al., `arXiv:2607.13816`, present a complete ECDLP construction requiring only **835 logical qubits** for a 256-bit prime-field curve, but with a very high gate cost. QCRYPTO therefore tracks width and runtime separately.

## Same-vendor roadmap collision

IonQ's public roadmap targets approximately **10,000 physical / 800 logical qubits in 2027** and **20,000 physical / 1,600 logical qubits in 2028**. Its separate Walking Cat secp256k1 resource estimate is approximately **19,397 physical / 1,457 logical qubits** with a modeled runtime of **25.7 days per attempt** under its stated assumptions.

`assess_roadmap_collision()` records this as a migration-planning signal. Roadmap evidence alone cannot establish Q2-Q4.

## Full-stack convergence

`assess_full_stack_convergence()` separately tracks published resource estimates, future hardware targets, demonstrated platform/manufacturing progress, demonstrated QEC components, and classical decoder-capacity evidence. A multi-plane convergence signal can accelerate migration validation but cannot be promoted into a demonstrated production break.

## Bitcoin mitigation dependency gate

`bitcoin_mitigation_readiness.py` adds a separate defensive readiness plane for public Bitcoin post-quantum mitigation work. It distinguishes:

- specification-only work;
- executable draft/reference implementation;
- production implementation;
- consensus activation;
- rescue dependencies;
- legacy-signature sunset dependencies; and
- a deployable mitigation stack.

The machine-readable file `bitcoin_mitigation_stack_2026-09-12.json` currently records three public components: SHRINCS for PQ-authorization research, DropKick for legacy rescue research, and BIP-361 for legacy-signature sunset policy. Their present classification is `DEPENDENCY_COMPLETE_RESEARCH_STACK`, **not deployed PQ protection**.

The hard rule is that a reference implementation cannot become `DEPLOYABLE_MITIGATION_STACK` without the required production and consensus-activation evidence. Rescue and sunset mechanisms that require PQ authorization remain dependency-blocked until such authorization is active.

## Claims-control rule

Hardware progress, roadmaps, QEC evidence, decoder capacity, platform maturity, attack-resource estimates, and mitigation proposals are tracked independently. Cross-source arithmetic and proposal maturity must not be promoted into operational claims without the required evidence.

## Safety boundary

These modules do not implement private-key recovery, wallet access, transaction signing, live-network probing, or attacks against third-party systems. They are defensive evidence, readiness, and migration-risk classifiers.

## Validation

Run:

```bash
python -m py_compile security/qcrypto/qcrypto_guard.py
python -m py_compile security/qcrypto/bitcoin_mitigation_readiness.py
python -m unittest discover -s security/qcrypto -p 'test_*.py' -v
python -m json.tool security/qcrypto/baseline_2026-09-12.json >/dev/null
python -m json.tool security/qcrypto/evidence_register_2026-09-12.json >/dev/null
python -m json.tool security/qcrypto/bitcoin_mitigation_stack_2026-09-12.json >/dev/null
```

The GitHub Actions workflow `.github/workflows/qcrypto-risk-gate.yml` enforces the package checks for changes to this package.
