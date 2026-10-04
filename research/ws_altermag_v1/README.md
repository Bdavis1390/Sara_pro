# WS-ALTERMAG v1.0-rc0

Status: `IMPLEMENTED IN SOFTWARE` once repository tests pass.

Physical status: `SIMULATED ONLY / REQUIRES LAB VALIDATION`.

This node is the first bounded implementation of the Worldshepherd Physical Compiler / Physical Decompiler contract for altermagnet research.

It deliberately begins with a deterministic synthetic benchmark before any DFT, transport, or laboratory backend is attached.

## B000-S

B000-S uses a B1g-like g-wave angular basis,

`sin(theta)^3 * cos(theta) * sin(3*phi)`,

as a literature-informed symmetry reference. The hidden amplitude and relaxation parameter in the manifest are synthetic test values and are **not** experimental CrSb material constants.

The benchmark executes:

`manifest -> state -> synthetic forward model -> noisy observations -> inverse recovery -> H0/H1 discrimination -> uncertainty/identifiability -> claims gate -> provenance digest`

The alternative hypotheses are:

- H0: relaxation/background response only;
- H1: altermagnetic-like angular contribution plus relaxation.

## Run

From repository root:

```bash
python -m research.ws_altermag_v1.benchmark_b000
python -m pytest -q research/ws_altermag_v1/test_end_to_end.py
```

## Claim boundary

A passing B000-S test supports only the bounded claim that the software can recover the known hidden state of its deterministic synthetic benchmark and can fail closed against physical claim promotion.

It does **not** establish:

- CrSb physical performance;
- experimental altermagnetic switching;
- a fabricated Worldshepherd material or device;
- laboratory validation;
- partner validation;
- production readiness.

Those remain evidence-gated by `docs/CLAIMS_AND_EVIDENCE_POLICY.md`.

## Next gate

Replace the analytic forward model with a versioned reference-data adapter for the published CrSb B000 observables while preserving the exact same Compiler/Decompiler/evidence contract. Only after reference reproduction should a first-principles solver backend be admitted.
