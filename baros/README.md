# BAROS bounded research reference

BAROS (Biologically Adaptive Radiotherapy Optimization System) is implemented here as a **research-stage, non-clinical radiotherapy planning/validation framework**.

**NON-CLINICAL. NOT FOR PATIENT CARE OR TREATMENT PLANNING.**

## Claims state

- **IMPLEMENTED IN SOFTWARE**: only for the bounded functions present in this repository.
- **PROVEN INTERNALLY**: only where pinned hosted tests/CI and exact-run evidence pass.
- **SIMULATED ONLY**: for synthetic optimization, finite synthetic robustness, and synthetic reliability behavior.
- **REQUIRES LAB/PARTNER VALIDATION**: physical dose, deliverability, TPS/vendor interoperability, measurement QA, and clinical workflow evidence.
- **NOT CURRENTLY CLAIMED**: clinical benefit, patient safety/effectiveness, regulatory authorization, routine treatment use, or treatment-success probability.

## Current executable scope

The bounded implementation includes:

- linear-quadratic surviving fraction;
- Poisson-form TCP reference calculation;
- bounded sigmoid NTCP reference calculation;
- synthetic beamlet-by-voxel dose-influence calculation;
- fail-closed maximum-dose constraints;
- deterministic constrained synthetic optimization;
- deterministic end-to-end synthetic research pipeline and evidence/provenance capture;
- bounded DICOM-RT read/semantic/reference-chain checks for RTSTRUCT, RTPLAN, and RTDOSE;
- RTDOSE numerical decoding and tested round trips;
- numerical DVH summaries, Vx, Dx%, and empirical cumulative DVH;
- gamma-index comparison delegated to pinned PyMedPhys;
- finite-scenario synthetic robustness evaluation;
- cumulative physical-dose summation only for grids proven to share the same frame/geometry;
- a predeclared synthetic reliability gate that is explicitly barred from clinical interpretation.

No module in this repository independently establishes clinical dose calculation, commissioned dose accuracy, treatment-machine deliverability, deformable registration accuracy, multi-vendor TPS interoperability, patient safety/effectiveness, or regulatory authorization.

## Hosted verification baseline

At pinned BAROS PR #306 parent head `f00a68ed7aa073ada7b03c4a24d0e8b4a6a36b7d`:

- **42 BAROS tests passed** on the GitHub-hosted runner (2 warnings);
- the exact-run synthetic evidence bundle was generated;
- the bounded reliability gate executed **1,000 synthetic cases with 1,000 successes and 0 failures** and asserted a one-sided 99.9% lower confidence bound above 0.993 and above the 0.987 research-software target;
- BAROS verification, Required Test and Build, Repository Freshness, CodeQL, Commit Closure, NIST 800-171 precursor, and Operational Resilience workflows all succeeded.

This is software/research evidence only. Any later commit requires a fresh run before being treated as verified.

## Run locally

```bash
python -m pip install -r baros/requirements.txt
PYTHONPATH=. python -m pytest -q tests/test_baros_*.py
PYTHONPATH=. python -m baros.cli --commit-sha LOCAL --output baros-evidence.json
```

## Next decisive validation gates

1. Freeze one intended use: indication, treatment technique, delivery platform, TPS environment, fractionation, comparator, version, endpoints, and acceptance criteria.
2. Complete independent numerical/model review and external reference fixtures.
3. Validate real-world DICOM/TPS interoperability against the locked partner environment.
4. Perform qualified medical-physics commissioning and end-to-end measured-dose testing, including absolute dose, spatial distribution, DVH/structure metrics, failure localization, repeatability, and gamma where appropriate.
5. Perform held-out retrospective comparison using governed partner-controlled cases and predeclared metrics.
6. Consider prospective shadow-mode workflow evaluation only after the preceding gates pass.
7. Treat any later interventional or patient-care study as a separate institutional/regulatory decision.

See:

- `docs/baros/TRACEABILITY_MATRIX.md`
- `docs/baros/BAROS_IMPLEMENTATION_AND_VALIDATION_GATE.md`
- `docs/baros/EXTERNAL_CLINICAL_VALIDATION_PROTOCOL.md`
- `docs/baros/SPECIFIC_AIMS_TRANSLATIONAL_VALIDATION_DRAFT.md`
