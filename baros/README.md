# BAROS bounded research reference

BAROS (Biologically Adaptive Radiotherapy Optimization System) is implemented here as a **research-stage, non-clinical radiotherapy planning, validation, and translational-assurance framework**.

**NON-CLINICAL. NOT FOR PATIENT CARE OR TREATMENT PLANNING.**

## Claims state

- **IMPLEMENTED IN SOFTWARE**: only for bounded functions present in this repository.
- **PROVEN INTERNALLY**: only where pinned hosted tests/CI and exact-run evidence pass.
- **SIMULATED ONLY**: for synthetic optimization, finite synthetic robustness, synthetic reliability, and model/experiment-design examples.
- **REQUIRES LAB/PARTNER VALIDATION**: physical dose, deliverability, TPS/vendor interoperability, measurement QA, model calibration, and clinical workflow evidence.
- **NOT CURRENTLY CLAIMED**: clinical benefit, patient safety/effectiveness, regulatory authorization, routine treatment use, or treatment-success probability.

## Executable research scope

### Radiobiology and optimization

- linear-quadratic surviving fraction;
- Poisson-form TCP reference calculation;
- bounded sigmoid NTCP reference calculation;
- synthetic beamlet-by-voxel dose-influence calculation;
- fail-closed maximum-dose constraints;
- deterministic constrained synthetic optimization.

### DICOM-RT and dosimetric analysis

- bounded RTSTRUCT/RTPLAN/RTDOSE semantic and reference-chain checks;
- strict RTDOSE geometry extraction and absolute-Gy numerical decoding;
- numerical DVH summary, Vx, Dx%, and empirical cumulative DVH;
- gamma-index comparison delegated to pinned PyMedPhys;
- finite-scenario robustness evaluation;
- aligned-dose summation only when frame/shape/origin/spacing/orientation agree.

### Reproducibility and evidence

- deterministic end-to-end synthetic research pipeline;
- commit/configuration/input/output/runtime provenance;
- dependency version and environment fingerprints;
- predeclared synthetic reliability gate;
- evidence hashes and claim-state boundaries.

### Translational governance

- SHA-256 locked intended-use manifests;
- evidence-envelope / Evidence Bill of Materials representation;
- contradiction and protocol-deviation quarantine;
- G0-G9 gate-specific minimum evidence requirements;
- external-evidence and independent-review requirements for partner gates;
- exact-effect human authorization bound to commit, evidence, intended use, gate, environment, nonce, and expiry;
- durable SQLite monotonic-epoch and one-use authorization ledger;
- replay, stale-state, evidence-substitution, commit-substitution, and gate-skipping rejection.

### Model and experimental-design assurance

- local identifiability analysis using sensitivity-matrix SVD;
- rank, nullity, singular values, condition number, and weak-parameter directions;
- linearized Gaussian expected-information-gain calculation;
- authorized validation-experiment ranking with cost/risk/irreversibility penalties;
- explicit blocking of unauthorized experiment selection;
- observability-versus-controllability assessment with low-observability/high-control hazard detection.

### Evidence dependency and invalidation

- directed evidence/assumption/model/configuration/claim dependency graph;
- transitive claim eligibility checks;
- quarantine propagation;
- blast-radius calculation when evidence, models, calibrations, or configuration change;
- cycle and missing-dependency rejection.

No module in this repository independently establishes clinical dose calculation, commissioned dose accuracy, clinically valid biological parameters, treatment-machine deliverability, deformable registration accuracy, multi-vendor TPS interoperability, patient safety/effectiveness, or regulatory authorization.

## Verification

BAROS verification runs all `tests/test_baros_*.py` in a pinned Python environment and generates exact-run synthetic evidence and reliability artifacts.

A historical verified baseline before the translational-assurance expansion had 42 BAROS tests passing and 1,000/1,000 bounded synthetic reliability cases with zero observed failures. New commits must obtain their own hosted verification before their expanded scope is treated as verified.

## Run locally

```bash
python -m pip install -r baros/requirements.txt
PYTHONPATH=. python -m pytest -q tests/test_baros_*.py
PYTHONPATH=. python -m baros.cli --commit-sha LOCAL --output baros-evidence.json
```

## Next decisive external gates

1. Freeze one intended use and evidence protocol with the partner institution.
2. Independently verify numerical/model behavior and parameter identifiability.
3. Choose validation experiments by predeclared scientific value while preserving authorization and risk boundaries.
4. Validate real-world DICOM/TPS interoperability against the locked partner environment.
5. Perform qualified medical-physics commissioning and end-to-end measured-dose testing.
6. Compile partner-controlled evidence envelopes with raw artifacts, uncertainty, deviations, contradictions, and review.
7. Perform held-out retrospective comparison using governed partner-controlled cases.
8. Consider prospective shadow-mode workflow evaluation only after the preceding gates pass.
9. Treat any interventional or patient-care study as a separate institutional/regulatory decision.

See:

- `docs/baros/TRACEABILITY_MATRIX.md`
- `docs/baros/BAROS_IMPLEMENTATION_AND_VALIDATION_GATE.md`
- `docs/baros/EXTERNAL_CLINICAL_VALIDATION_PROTOCOL.md`
- `docs/baros/TRANSLATIONAL_GOVERNANCE_AND_SCIENTIFIC_ASSURANCE_V2.md`
- `docs/baros/SPECIFIC_AIMS_TRANSLATIONAL_VALIDATION_DRAFT.md`
