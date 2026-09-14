# WS-QPHONON ↔ Quantum Readiness Fabric Reconciliation

## Status

This document reconciles the WS-QPHONON L2 architecture with the pre-existing Worldshepherd Quantum Readiness Fabric (QRF) work on `agent/quantum-readiness-fabric`.

The two lanes are complementary but not interchangeable.

## What QRF can contribute now

QRF already defines provider-neutral real-QPU evidence discipline, including:

- frozen workloads before hardware execution;
- named physical-device identity;
- retained raw results;
- SHA-256 artifact custody;
- human technical review;
- repeat runs;
- independent-provider reproduction;
- explicit rejection of simulator runs as hardware evidence;
- prohibition on promoting outreach, account setup, payment, or queue entry as physical evidence.

Those controls should be reused by WS-QPHONON wherever they are platform-neutral.

## What QRF cannot establish for QPHONON

A governed run on IBM, Braket, IonQ, QSCOUT, QCUP, AQT, or another gate-model QPU does **not** establish any of the following QPHONON claims:

- coherent SiV/SnV-to-phonon exchange;
- acoustic dressed-state protection in a QPHONON device;
- phononic-cavity cooperativity;
- phonon-mediated two-node state transfer;
- a phononic entangling gate;
- Worldshepherd ownership or operation of diamond/phononic quantum hardware.

Those require hardware whose physical mechanism actually exercises the QPHONON hypothesis.

## Reuse boundary

QRF evidence may close **software/governance interoperability gates** for WS-QPHONON, including:

1. SARA experiment packaging;
2. PRIME pre-execution authorization semantics;
3. ECHO raw-result hashing and provenance;
4. immutable pre-run configuration capture;
5. human review binding;
6. repeat/reproduction workflow;
7. negative-result retention;
8. cross-provider evidence comparison.

QRF evidence may not close **phononic physics gates**.

## Two-axis maturity model

WS-QPHONON maturity is tracked on two independent axes.

### Axis A — governance/runtime maturity

- A0: design only
- A1: synthetic software exercise
- A2: governed simulator exercise
- A3: governed physical-QPU exercise on non-phononic hardware
- A4: independently reproduced governance/runtime result

### Axis B — phononic physics maturity

- B0: literature-supported concept
- B1: calibrated model reproduces external measurements
- B2: partner device characterization
- B3: Worldshepherd-governed experiment on relevant phononic hardware
- B4: reproducible holdout prediction and independent partner reproduction

L3 QPHONON capability promotion requires **B3/B4 evidence**. A3/A4 alone is insufficient.

## Recommended reuse sequence

1. Preserve the existing QRF access matrix and runbooks as the generic external-QPU evidence path.
2. Use a real QRF hardware run, when available, to test the Worldshepherd quantum evidence/provenance pipeline end to end.
3. Keep the QPHONON claims state unchanged after that run unless relevant phononic hardware is involved.
4. Reuse the proven evidence pipeline for the eventual SiV/SnV phononic partner campaign.
5. Require the QPHONON-specific L3 partner experiment before any physical-capability promotion.

## Claims rule

A stronger generic quantum-runtime result must never be silently converted into a stronger phononic-physics claim.

The canonical rule is:

`GENERIC_QUANTUM_RUNTIME_EVIDENCE != QPHONON_PHYSICAL_EVIDENCE`

This separation is mandatory even when the same SARA, PRIME, ECHO, OVERWATCH, and PRE components participate in both campaigns.
