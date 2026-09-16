# BAROS G1 bounded research reference

This directory is the first executable repository slice for the Biologically Adaptive Radiotherapy Optimization System (BAROS).

## Status

- `IMPLEMENTED IN SOFTWARE`: only for the bounded mathematical/synthetic functions present here.
- `PROVEN INTERNALLY`: only after the corresponding pinned tests/CI pass.
- `SIMULATED ONLY`: for synthetic optimization behavior.
- `NOT CURRENTLY CLAIMED`: physical/dosimetric validity, DICOM-RT interoperability, TPS integration, retrospective clinical benefit, prospective clinical benefit, regulatory authorization, or patient-care readiness.

**NON-CLINICAL. NOT FOR PATIENT CARE OR TREATMENT PLANNING.**

## Current executable scope

- linear-quadratic surviving fraction;
- Poisson-form TCP reference calculation;
- bounded sigmoid NTCP reference calculation;
- synthetic beamlet-by-voxel dose-influence calculation;
- fail-closed maximum-dose constraints;
- deterministic projected/backtracking synthetic optimizer that reduces a tumor-survival surrogate while preserving configured synthetic OAR limits.

These functions provide numerical building blocks for G1 verification. They do not compute clinical dose and do not emit RTPLAN/RTDOSE.

## Run

```bash
PYTHONPATH=. python -m pytest -q tests/test_baros_reference.py
```

## Next required implementation gates

1. Requirements/traceability completion for every manuscript function.
2. Independent numerical reference fixtures and expanded property testing.
3. Synthetic end-to-end research pipeline and immutable evidence bundle.
4. DICOM-RT read/validate/write layer with safe failure behavior.
5. Research TPS/dose-engine adapter boundary.
6. DVH/gamma/robustness modules verified against independent references.
7. External medical-physics and clinical validation under the gates in `docs/baros/BAROS_IMPLEMENTATION_AND_VALIDATION_GATE.md`.
