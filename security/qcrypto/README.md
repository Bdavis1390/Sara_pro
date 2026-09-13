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
8. **exposure and migration windows** — how long a public key is available to attack and how long defenders need to migrate.

A low logical-qubit count does **not** imply a fast practical attack. A low physical/logical code-block ratio does **not** imply a complete-application physical-qubit count. A point-addition or arithmetic subroutine result does **not** imply a complete end-to-end key break. A future vendor roadmap is **not** demonstrated hardware. A fabricated prototype is **not** attack-scale hardware. A proposed FPGA/ASIC decoder is **not** an integrated cryptanalytic control plane. Q4 is reserved for a production-strength break demonstrated in a controlled, authorized environment.

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

IonQ's separate Walking Cat secp256k1 resource estimate reports an end-to-end attack envelope of approximately **19,397 physical / 1,457 logical qubits** and **25.7 days per attempt** under its architecture assumptions.

Those numbers create a material planning signal: the vendor's **2028 target numerically overlaps the vendor's own attack envelope**. This is not evidence that the 2028 target will be achieved, that every required QEC/runtime assumption will hold, or that a production key can be broken today.

`assess_roadmap_collision()` therefore creates a separate roadmap evidence plane:

- `VENDOR_ROADMAP_TARGET` remains distinct from demonstrated hardware;
- same-architecture logical/physical overlap can trigger `SAME_ARCHITECTURE_ATTACK_ENVELOPE_COLLISION`;
- a collision can increase migration urgency to `ACCELERATE_MIGRATION_VALIDATION` or `MIGRATION_SCHEDULE_AT_RISK`;
- roadmap evidence alone can never establish Q2, Q3, Q4, or Q-day.

## September 2026 full-stack convergence trigger

The roadmap collision is no longer the only planning signal.

IonQ reports that **Superion 256 integrated QPUs have been fabricated at SkyWater, ions have been trapped in prototype systems, orders are open, and customer deliveries are planned for 2027**. IonQ also reports breakeven qLDPC QEC on a Tempo engineering system and describes it as validating key Walking Cat elements on hardware.

Separately, `arXiv:2605.03180` proposes a generalized qLDPC classical predecoder that processes over 90% of decoding workload, reports up to 3,963x decoder-utilization reduction, and describes designs supporting about **1,200 bivariate-bicycle logical qubits on one FPGA** or **36,000-360,000 logical qubits on a cryogenic ASIC**.

That decoder result is **not** demonstrated as the exact Walking Cat decoder. Its code compatibility, physical implementation at stated capacity, timing, and attack-specific integration remain unproven. However, it means the classical decoder should no longer be modeled as an immutable scaling barrier.

`assess_full_stack_convergence()` therefore tracks five planes together:

1. complete attack-resource estimate;
2. same-architecture future hardware target;
3. demonstrated prototype/manufacturing progress;
4. demonstrated QEC components on related hardware;
5. classical decoder capacity evidence.

When all five move in the same direction, QCRYPTO emits `MULTI_PLANE_CONVERGENCE_SIGNAL`. That signal can accelerate migration validation but **cannot** establish Q2/Q3/Q4 or a practical break.

Current blocking gaps include:

- the 20,000-qubit target has not been demonstrated;
- Superion 256 is only a 256-qubit prototype/product platform, not attack scale;
- proposed qLDPC decoder capacity has not been demonstrated as the Walking Cat decoder;
- exact QEC-code compatibility is unproven;
- attack-specific decoder integration is absent;
- full non-Clifford factory, routing, runtime-reliability, and integrated-system scaling remain to be demonstrated.

## Independent multi-vendor fault-tolerance signal

Quantinuum's C4-Helix work provides independent trapped-ion QEC evidence, and separate peer-reviewed trapped-ion work has demonstrated fault-tolerant universal logical operations at small scale. These sources do **not** get multiplied into IonQ's physical-resource estimate. They are retained only as independent evidence that several fault-tolerant primitives are becoming engineering demonstrations rather than purely theoretical proposals.

## Bitcoin mitigation dependency gate

`bitcoin_mitigation_readiness.py` tracks the maturity and dependency ordering of public Bitcoin post-quantum mitigation work. It distinguishes specification-only work, executable drafts, production implementations, consensus activation, rescue dependencies, legacy-signature sunset dependencies, and a deployable mitigation stack.

The machine-readable file `bitcoin_mitigation_stack_2026-09-12.json` currently records SHRINCS, DropKick, and BIP-361. The present classification is `DEPENDENCY_COMPLETE_RESEARCH_STACK`, not deployed post-quantum protection. Rescue and sunset mechanisms that require a PQ authorization/output mechanism remain dependency-blocked until such a mechanism is active.

## Claims-control rule

Hardware progress, roadmap targets, QEC evidence, classical decoder capacity, platform maturity, attack-algorithm progress, and mitigation proposals are tracked independently. Cross-paper multiplication is prohibited unless architecture compatibility and complete fault-tolerant overhead are established. Roadmap or convergence evidence is a migration-planning signal, never a production-break claim.

## Safety boundary

This package does not implement Shor's algorithm, private-key recovery, wallet interaction, transaction signing, live-network probing, or attacks against third-party systems. It is a defensive resource-estimate, evidence, readiness, and migration-risk classifier.

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
