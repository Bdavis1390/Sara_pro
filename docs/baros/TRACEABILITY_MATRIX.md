# BAROS G1 Requirements Traceability Matrix

Status: research-only verification artifact  
Clinical use: prohibited

| Requirement ID | Manuscript-derived function | Repository implementation | Verification | Current evidence state | Next external gate |
|---|---|---|---|---|---|
| BAROS-BIO-001 | LQ survival response | `baros/models.py::lq_survival` | `test_lq_survival_known_case` | IMPLEMENTED IN SOFTWARE; internally tested when CI passes | independent numerical reference review |
| BAROS-BIO-002 | Poisson-style TCP aggregation | `baros/models.py::poisson_tcp` | `test_poisson_tcp_known_case` | IMPLEMENTED IN SOFTWARE; internally tested when CI passes | model-selection/domain review |
| BAROS-BIO-003 | sigmoid NTCP reference | `baros/models.py::logistic_ntcp` | `test_logistic_ntcp_is_half_at_d50_and_monotonic` | IMPLEMENTED IN SOFTWARE; bounded reference only | clinically justified NTCP model/parameters |
| BAROS-PHY-001 | beamlet-weight to synthetic voxel-dose mapping | `baros/dose.py::dose_from_influence` | `test_dose_matrix_and_hard_constraint_fail_closed` | SIMULATED ONLY | independent dose-engine/TPS validation |
| BAROS-SAFE-001 | hard max-dose constraints fail closed | `baros/dose.py::hard_max_constraints` | positive/negative constraint test | IMPLEMENTED IN SOFTWARE for synthetic arrays | clinically governed constraint source + TPS verification |
| BAROS-OPT-001 | iterative constrained optimization | `baros/reference_optimizer.py::optimize_synthetic` | objective-improvement + OAR-limit test | SIMULATED ONLY | independent optimization review and broader pathological cases |
| BAROS-SAFE-002 | invalid mathematical inputs rejected | models/dose/optimizer input validation | `test_invalid_inputs_rejected` | IMPLEMENTED IN SOFTWARE | expanded fuzz/property testing |
| BAROS-IO-001 | RTSTRUCT ingestion/validation | not implemented | none | NOT CURRENTLY CLAIMED | DICOM conformance/interoperability |
| BAROS-IO-002 | RTPLAN ingestion/modification | not implemented | none | NOT CURRENTLY CLAIMED | TPS research integration |
| BAROS-IO-003 | RTDOSE ingestion/evaluation | not implemented | none | NOT CURRENTLY CLAIMED | TPS/research-dose-engine integration |
| BAROS-VAL-001 | DVH generation/comparison | not implemented | none | NOT CURRENTLY CLAIMED | independent physics reference |
| BAROS-VAL-002 | gamma analysis | not implemented | none | NOT CURRENTLY CLAIMED | qualified medical-physics validation |
| BAROS-VAL-003 | measurement/phantom QA | outside repository-only capability | none | REQUIRES LAB/PARTNER VALIDATION | medical-physics lab/clinical institution |
| BAROS-ADAPT-001 | adaptive cumulative-dose workflow | not implemented | none | NOT CURRENTLY CLAIMED | retrospective/clinical workflow validation |
| BAROS-CLIN-001 | retrospective clinical performance | no traceable controlled dataset/evidence in repo | none | NOT CURRENTLY CLAIMED | institutional retrospective protocol |
| BAROS-CLIN-002 | prospective clinical safety/effectiveness | not established | none | NOT CURRENTLY CLAIMED | prospective study/regulatory pathway |

## Promotion rule

A requirement can move only to the broadest claim state directly supported by its evidence. In particular:

- synthetic optimizer tests do not establish physical dose accuracy;
- DICOM parsing will not establish TPS interoperability until tested against the intended systems;
- TPS interoperability will not establish patient safety/effectiveness;
- peer review will not establish regulatory authorization;
- successful clinical/regulatory evidence must remain scoped to the validated intended use, version, population, and workflow.

## G1 exit criteria

G1 is complete only when:

1. every implemented mathematical component has a deterministic positive test;
2. every implemented boundary has a negative/fail-closed test;
3. independent reference values are added for each numerical model;
4. CI passes at the exact branch head;
5. the evidence bundle identifies commit, environment, commands, and outputs;
6. this matrix is updated so no manuscript capability is silently treated as implemented.
