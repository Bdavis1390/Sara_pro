# BAROS Requirements Traceability Matrix

Status: research-only verification artifact  
Clinical use: prohibited

This matrix describes only the bounded repository behaviors exercised by BAROS tests. It does **not** establish physical dose accuracy, treatment-planning-system interoperability, clinical safety/effectiveness, regulatory authorization, or patient-care suitability.

| Requirement ID | Function | Repository implementation | Verification | Current evidence state | Next external gate |
|---|---|---|---|---|---|
| BAROS-BIO-001 | LQ survival response | `baros/models.py::lq_survival` | known-value tests | IMPLEMENTED IN SOFTWARE; hosted CI verified | independent numerical/model review |
| BAROS-BIO-002 | Poisson-style TCP aggregation | `baros/models.py::poisson_tcp` | known-value tests | IMPLEMENTED IN SOFTWARE; hosted CI verified | model-selection/domain review |
| BAROS-BIO-003 | bounded sigmoid NTCP reference | `baros/models.py::logistic_ntcp` | monotonicity/reference tests | IMPLEMENTED IN SOFTWARE; bounded reference only | clinically justified model/parameters |
| BAROS-PHY-001 | synthetic beamlet-weight to voxel-dose mapping | `baros/dose.py::dose_from_influence` | synthetic mapping/constraint tests | SIMULATED ONLY; hosted CI verified | independent dose-engine/TPS validation |
| BAROS-SAFE-001 | fail-closed hard max-dose constraints | `baros/dose.py::hard_max_constraints` | positive/negative constraint tests | IMPLEMENTED IN SOFTWARE for numerical arrays | clinically governed constraints + TPS verification |
| BAROS-OPT-001 | deterministic constrained synthetic optimization | `baros/reference_optimizer.py::optimize_synthetic` | objective/constraint tests | SIMULATED ONLY; hosted CI verified | independent optimization review + pathological cases |
| BAROS-SAFE-002 | invalid mathematical inputs rejected | models/dose/optimizer validation | invalid-input tests | IMPLEMENTED IN SOFTWARE | expanded property/fuzz testing |
| BAROS-PIPE-001 | deterministic end-to-end research loop | `baros/pipeline.py`, `baros/cli.py` | pipeline tests + exact-run artifact | PROVEN INTERNALLY for bounded synthetic workflow | independent reference fixtures |
| BAROS-IO-001 | RTSTRUCT ingestion/semantic validation | `baros/dicom_rt.py` | supported/wrong-modality/UID tests | IMPLEMENTED IN SOFTWARE for bounded synthetic objects | real-world multi-vendor conformance/interoperability |
| BAROS-IO-002 | RTPLAN ingestion/reference validation | `baros/dicom_rt.py` | synthetic RTPLAN/linkage tests | IMPLEMENTED IN SOFTWARE for bounded read/semantic validation; no clinical plan generation claimed | TPS research-interface validation |
| BAROS-IO-003 | RTDOSE numerical decoding | `baros/dicom_rt.py::decode_rtdose` | scaling/round-trip/error tests | IMPLEMENTED IN SOFTWARE for bounded numerical decoding; physical dose accuracy NOT CLAIMED | independent dose-engine/TPS + measurement validation |
| BAROS-IO-004 | RTSTRUCT → RTPLAN → RTDOSE reference-chain integrity | `baros/dicom_rt.py::validate_linkage` | matching/mismatched UID tests | IMPLEMENTED IN SOFTWARE for tested synthetic objects | multi-vendor / real-case interoperability |
| BAROS-VAL-001 | DVH summary, Vx, Dx%, cumulative DVH | `baros/dvh.py` | exact-value, monotonicity, mask, fail-closed tests | IMPLEMENTED IN SOFTWARE for numerical arrays; hosted CI verified | independent TPS/medical-physics reference comparison |
| BAROS-VAL-002 | gamma comparison | `baros/gamma_analysis.py` using pinned PyMedPhys | identity/error/input-validation tests | IMPLEMENTED IN SOFTWARE as research comparison wrapper; hosted CI verified | measured-dose validation under qualified physics protocol |
| BAROS-ROB-001 | finite-scenario robustness evaluation | `baros/robustness.py` | worst-case/constraint/fail-closed tests | SIMULATED ONLY; hosted CI verified | clinically justified uncertainty model + partner validation |
| BAROS-ADAPT-001 | aligned cumulative-dose summation | `baros/adaptive.py::accumulate_aligned_dose` | alignment/mismatch/negative-dose tests | IMPLEMENTED IN SOFTWARE only for already-aligned grids; hosted CI verified | validated registration/resampling workflow + retrospective validation |
| BAROS-VAL-003 | measurement/phantom QA | outside repository-only capability | none | REQUIRES LAB/PARTNER VALIDATION | medical-physics lab/clinical institution |
| BAROS-CLIN-001 | retrospective clinical performance | no controlled clinical dataset/evidence in repo | none | NOT CURRENTLY CLAIMED | institutional retrospective protocol |
| BAROS-CLIN-002 | prospective clinical safety/effectiveness | not established | none | NOT CURRENTLY CLAIMED | prospective study + regulatory/institutional pathway |

## Verified repository baseline

At BAROS PR #306 parent verification head `f00a68ed7aa073ada7b03c4a24d0e8b4a6a36b7d`:

- `BAROS bounded research verification` completed successfully on GitHub-hosted runners.
- All BAROS tests completed: **42 passed, 2 warnings**.
- The workflow generated the exact-run synthetic evidence bundle.
- The predeclared bounded synthetic reliability gate ran **1,000 cases with 1,000 successes and 0 failures**, with the one-sided 99.9% lower confidence bound asserted above 0.993 and above the 0.987 target.
- `Required Test and Build`, `Repository Freshness Gate`, `CodeQL Required Gate`, `SARA Commit Closure Evidence`, `SARA NIST 800-171 SSP Precursor`, and `SARA Operational Resilience Drill` also completed successfully.

That evidence supports only the bounded software/research claims above. The 1,000-case result is a **synthetic research-software acceptance result**, not a clinical-probability, treatment-success, patient-safety, or physical-dose claim.

Any commit after that pinned baseline requires a fresh hosted run before its broader repository state is treated as verified.

## Promotion rules

A requirement may move only to the broadest claim state directly supported by its evidence:

- synthetic optimizer tests do not establish physical dose accuracy;
- synthetic DICOM round trips do not establish vendor/TPS interoperability or formal DICOM conformance;
- numerical DVH/gamma tests do not establish measurement-based QA;
- gamma pass rate alone is not a clinical safety endpoint;
- finite synthetic robustness scenarios do not establish clinical uncertainty coverage;
- aligned-grid summation does not establish deformable registration accuracy;
- TPS interoperability does not establish patient safety/effectiveness;
- peer review does not establish regulatory authorization;
- successful external evidence remains scoped to the validated intended use, version, population, modality, and workflow.

## Current exit state

The repository now contains a materially broader bounded implementation than the original G1 slice, including research-only DICOM semantics, DVH utilities, independent-library gamma comparison, finite-scenario robustness, aligned-dose accumulation, provenance/reliability tooling, and a deterministic synthetic pipeline.

The next decisive BAROS gate is no longer “write more synthetic code.” It is to freeze one intended-use configuration and obtain **independent numerical review, real TPS/vendor interoperability evidence, measured-dose/end-to-end medical-physics validation, and held-out retrospective evaluation** under partner control.
