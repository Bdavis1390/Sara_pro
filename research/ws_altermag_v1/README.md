# WS-ALTERMAG v1.0-rc0

Status: `IMPLEMENTED IN SOFTWARE` for the bounded tests that pass.

Physical status: `SIMULATED ONLY / REQUIRES LAB VALIDATION`.

This node is the first bounded implementation of the Worldshepherd Physical Compiler / Physical Decompiler contract for altermagnet research.

It begins with a deterministic synthetic benchmark, then adds a literature-reference adapter before any DFT, transport, or laboratory backend is attached.

## B000-S — synthetic truth recovery

B000-S uses a B1g-like g-wave angular basis,

`sin(theta)^3 * cos(theta) * sin(3*phi)`,

as a literature-informed symmetry reference. The hidden amplitude and relaxation parameter in the manifest are synthetic test values and are **not** experimental CrSb material constants.

The benchmark executes:

`manifest -> state -> synthetic forward model -> noisy observations -> inverse recovery -> H0/H1 discrimination -> uncertainty/identifiability -> claims gate -> provenance digest`

The alternative hypotheses are:

- H0: relaxation/background response only;
- H1: altermagnetic-like angular contribution plus relaxation.

## B000-R — bounded literature-reference adapter

B000-R encodes only explicitly reported textual observables from:

Long et al., *Nature* 656, 854-860 (2026), DOI `10.1038/s41586-026-10902-z`.

The current adapter checks:

- `B1g` / `Y_4^-3` symmetry metadata;
- nodal planes at azimuthal `phi = 0, 60, 120 deg`;
- the basal nodal plane at `theta = 90 deg`;
- internal consistency of the reported representative frequency pair `3.41 kT` and `3.82 kT`, giving `0.41 kT` splitting at the stated orientation.

This is **not yet a raw-data reproduction**. It is a versioned reference contract that keeps the software aligned with the published symmetry and selected textual observables.

## Run

From repository root:

```bash
python -m research.ws_altermag_v1.benchmark_b000
python -m research.ws_altermag_v1.reference_b000
python -m pytest -q research/ws_altermag_v1/test_end_to_end.py
```

## Claim boundary

A passing B000-S test supports only the bounded claim that the software can recover the known hidden state of its deterministic synthetic benchmark and can fail closed against physical claim promotion.

A passing B000-R test supports only that the encoded literature reference is internally consistent with the implemented analytic symmetry basis and selected reported observables.

Neither establishes:

- independent reproduction of the CrSb experiment;
- CrSb physical performance beyond the cited literature;
- experimental altermagnetic switching by Worldshepherd;
- a fabricated Worldshepherd material or device;
- laboratory validation;
- partner validation;
- production readiness.

Those remain evidence-gated by `docs/CLAIMS_AND_EVIDENCE_POLICY.md`.

## Next gate

Acquire and version the open source-data/supplementary datasets for the published CrSb quantum-oscillation experiment, then reproduce the nodal-versus-antinodal frequency behavior from the data rather than from manually encoded textual reference points. Only after that reference-data gate should a first-principles solver backend be admitted.
