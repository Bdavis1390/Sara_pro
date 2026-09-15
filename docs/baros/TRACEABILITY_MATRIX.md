# BAROS Requirements Traceability Matrix

Status: research-only verification artifact
Clinical use: prohibited

| Requirement ID | Manuscript-derived function | Repository implementation | Verification | Current evidence state | Next external gate |
|---|---|---|---|---|---|
| BAROS-BIO-001 | LQ survival response | `baros/models.py::lq_survival` | `test_lq_survival_known_case` | IMPLEMENTED IN SOFTWARE; hosted CI verified | independent numerical reference review |
| BAROS-BIO-002 | Poisson-style TCP aggregation | `baros/models.py::poisson_tcp` | `test_poisson_tcp_known_case` | IMPLEMENTED IN SOFTWARE; hosted CI verified | model-selection/domain review |
| BAROS-BIO-003 | sigmoid NTCP reference | `baros/models.py::logistic_ntcp` | `test_logistic_ntcp_is_half_at_d50_and_monotonic` | IMPLEMENTED IN SOFTWARE; bounded reference only | clinically justified NTCP model/parameters |
| BAROS-PHY-001 | beamlet-weight to synthetic voxel-dose mapping | `baros/dose.py::dose_from_influence` | `test_dose_matrix_and_hard_constraint_fail_closed` | SIMULATED ONLY; hosted CI verified | independent dose-engine/TPS validation |
| BAROS-SAFE-001 | hard max-dose constraints fail closed | `baros/dose.py::hard_max_constraints` | positive/negative constraint tests | IMPLEMENTED IN SOFTWARE for synthetic arrays | clinically governed constraint source + TPS verification |
| BAROS-OPT-001 | iterative constrained optimization | `baros/reference_optimizer.py::optimize_synthetic` | objective-improvement + OAR-limit test | SIMULATED ONLY; hosted CI verified | independent optimization review and broader pathological cases |
| BAROS-SAFE-002 | invalid mathematical inputs rejected | models/dose/optimizer input validation | `test_invalid_inputs_rejected` | IMPLEMENTED IN SOFTWARE | expanded fuzz/property testing |
| BAROS-PIPE-001 | deterministic end-to-end synthetic research loop | `baros/pipeline.py`, `baros/cli.py` | `tests/test_baros_pipeline.py` + exact-run evidence artifact | PROVEN INTERNALLY for bounded synthetic workflow | expand to independently referenced models and governed fixtures |
| BAROS-IO-001 | RTSTRUCT ingestion/validation | `baros/dicom_rt.py::validate_rt_dataset`, `read_validated_rt` | synthetic supported-object, wrong-modality, UID/linkage tests | IMPLEMENTED IN SOFTWARE for bounded synthetic semantic validation; hosted CI verified | real-world DICOM/vendor/TPS conformance and interoperability |
| BAROS-IO-002 | RTPLAN ingestion/reference validation | `baros/dicom_rt.py::validate_rt_dataset`, `validate_linkage` | synthetic RTPLAN and cross-object linkage tests | IMPLEMENTED IN SOFTWARE for bounded read/semantic validation; no clinical plan generation claimed | TPS research-interface validation with qualified partner |
| BAROS-IO-003 | RTDOSE ingestion/evaluation | `baros/dicom_rt.py::decode_rtdose`, `read_validated_rt` | scaling, disk round-trip, missing-scaling, relative-dose tests | IMPLEMENTED IN SOFTWARE for bounded numerical decoding; physical dose accuracy NOT CLAIMED | independent dose-engine/TPS and dosimetric validation |
| BAROS-IO-004 | RTSTRUCT -> RTPLAN -> RTDOSE reference-chain integrity | `baros/dicom_rt.py::validate_linkage` | matching and mismatched SOPInstanceUID tests | IMPLEMENTED IN SOFTWARE for tested synthetic objects | multi-vendor / real-case interoperability |
| BAROS-VAL-001 | DVH generation/comparison | not implemented | none | NOT CURRENTLY CLAIMED | independent physics reference |
| BAROS-VAL-002 | gamma analysis | not implemented | none | NOT CURRENTLY CLAIMED | independent reference + qualified medical-physics validation |
| BAROS-VAL-003 | measurement/phantom QA | outside repository-only capability | none | REQUIRES LAB/PARTNER VALIDATION | medical-physics lab/clinical institution |
| BAROS-ADAPT-001 | adaptive cumulative-dose workflow | not implemented | none | NOT CURRENTLY CLAIMED | retrospective/clinical workflow validation |
| BAROS-CLIN-001 | retrospective clinical performance | no traceable controlled dataset/evidence in repo | none | NOT CURRENTLY CLAIMED | institutional retrospective protocol |
| BAROS-CLIN-002 | prospective clinical safety/effectiveness | not established | none | NOT CURRENTLY CLAIMED | prospective study/regulatory pathway |

## Verified repository state

At PR #306 head `e49391e08fb2870e4ae19acfcee9d21f8303e3b5`, GitHub-hosted `BAROS bounded research verification` passed 15/15 tests from a clean runner and produced an exact-run synthetic evidence artifact. The repository-wide Required Test and Build, CodeQL Required Gate, Repository Freshness Gate, SARA Commit Closure Evidence, SARA NIST 800-171 SSP Precursor, and SARA Operational Resilience Drill also passed.

This verifies the bounded software behaviors exercised by those tests. It does not establish DICOM conformance certification, TPS interoperability, physical-dose correctness, clinical effectiveness, regulatory authorization, or patient-care suitability.

## Promotion rule

A requirement can move only to the broadest claim state directly supported by its evidence. In particular:

- synthetic optimizer tests do not establish physical dose accuracy;
- synthetic DICOM round trips do not establish vendor/TPS interoperability or formal DICOM conformance;
- DICOM parsing will not establish TPS interoperability until tested against the intended systems;
- TPS interoperability will not establish patient safety/effectiveness;
- peer review will not establish regulatory authorization;
- successful clinical/regulatory evidence must remain scoped to the validated intended use, version, population, and workflow.

## G1-G2 bounded exit state

The currently implemented G1-G2 subset is internally reproducible at the pinned hosted run. Full G1/G2 for the manuscript as a whole remains open until every required component in the intended BAROS research architecture is implemented and traceable.

The next repository-verifiable targets are DVH metrics, numerical-reference expansion, robustness/uncertainty handling, and additional research-only DICOM/TPS interface checks. External G5-G9 evidence cannot be substituted by repository tests.
