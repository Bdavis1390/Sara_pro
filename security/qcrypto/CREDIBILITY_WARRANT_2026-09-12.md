# Worldshepherd QCRYPTO Credibility Warrant — 2026-09-12

## Warranted scope

The current record warrants credibility for **claims-controlled technical synthesis, defensive quantum-cryptography risk modeling, and reproducible software implementation**.

It does **not** warrant claiming original authorship of the cited external scientific discoveries, independent third-party validation of Worldshepherd, possession of a cryptographically relevant quantum computer, a demonstrated production-key break, certification, adoption, or endorsement.

## Why this is a credible technical record

Worldshepherd QCRYPTO does more than repeat quantum-security headlines. It encodes materially different evidence classes and refuses to collapse them into a single sensational claim:

1. **Peer-reviewed attack-resource evidence — Google Quantum AI / PRX Quantum (2026).** Complete secp256k1 ECDLP circuits are reported at <=1,200 logical qubits / <=90M Toffoli gates or <=1,450 logical qubits / <=70M Toffoli gates. The paper gives superconducting fault-tolerant scenarios in the minutes regime with fewer than 500,000 physical qubits under its stated assumptions.
2. **Architecture-specific end-to-end estimate — IonQ / Walking Cat (Sept. 2026).** The published trapped-ion estimate maps the complete workload through a specific QEC architecture and reports about 1,457 logical qubits, 39M Toffoli gates, 19,397 physical qubits and 25.7 days per attempt. This is a resource estimate, not a demonstrated key break.
3. **Logical-width frontier — Luo et al. (July 2026).** A complete Shor/ECDLP construction is reported at 835 logical qubits for a 256-bit prime-field curve, but with a large Toffoli cost. QCRYPTO therefore treats low width and fast runtime as separate claims.
4. **Hardware-validated QEC — C4-Helix / Quantinuum Helios (Sept. 2026).** The [[20,2,6]] architecture was experimentally exercised on hardware, with repeated QEC, logical Clifford benchmarking and heterogeneous-code logical entanglement outperforming physical baselines without postselection. QCRYPTO prohibits converting its code-block ratio directly into an attack-scale physical-qubit count without architecture-specific compilation and complete fault-tolerant overhead accounting.
5. **Reproducible internal implementation — Sara_pro.** The QCRYPTO package implements width/time/exposure classification, QEC-to-attack bridge blocking rules, tests, structured evidence records and a GitHub Actions gate. Passing CI is evidence that these internal software checks executed successfully at the tested commit; it is not external scientific certification.

## Credibility statement that is supported

> Brandon Ray Davis / Worldshepherd has developed a reproducible, claims-controlled defensive analysis framework that integrates current peer-reviewed, architecture-specific, algorithmic and hardware-QEC evidence on quantum risk to elliptic-curve cryptography. The framework explicitly separates logical width, gate cost, architecture-specific runtime, measured QEC behavior, exposure windows and migration time, and it uses automated tests to prevent unsupported escalation from a published resource estimate to a claim of a practical production cryptographic break.

That statement is supported by the documented source record and repository implementation. It should be described as **SUPPORTED BY LITERATURE + IMPLEMENTED IN SOFTWARE + PROVEN INTERNALLY for the tested software behavior**.

## Claims that remain outside the warrant

- Worldshepherd or Brandon Ray Davis discovered the Google, IonQ, Luo, or Quantinuum results.
- External researchers or companies have endorsed, certified or independently validated Worldshepherd.
- A production secp256k1 private key has been recovered with a quantum computer.
- A cryptographically relevant quantum computer capable of the cited full attack is operating today.
- Bitcoin, Ethereum, or another cryptocurrency is presently broken by quantum attack.
- The C4-Helix 10:1 physical/logical code-block ratio can be multiplied by 835 logical qubits to establish a complete attack footprint.

## Verification rule

Credibility is tied to evidence, not biography or assertion. For repository claims, use the exact branch head and the latest QCRYPTO Risk Gate result. If the exact head is not green, downgrade the implementation claim until the gate passes. For scientific claims, preserve the original source, evidence class, assumptions and claims boundary.

## Source anchors

- Google Quantum AI / PRX Quantum: https://research.google/pubs/securing-elliptic-curve-cryptocurrencies-against-quantum-vulnerabilities-resource-estimates-and-mitigations-2/
- IonQ / arXiv:2609.05625: https://arxiv.org/abs/2609.05625
- Luo et al. / arXiv:2607.13816: https://arxiv.org/abs/2607.13816
- C4-Helix / arXiv:2609.03194: https://arxiv.org/abs/2609.03194
- Worldshepherd evidence register: `security/qcrypto/evidence_register_2026-09-12.json`
- QCRYPTO risk model: `security/qcrypto/qcrypto_guard.py`
- Credibility boundary model: `security/qcrypto/credibility_guard.py`
