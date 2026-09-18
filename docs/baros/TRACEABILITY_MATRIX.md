# BAROS Requirements Traceability Matrix

Status: research-only verification artifact
Clinical use: prohibited

This matrix describes bounded repository behaviors only. It does **not** establish physical dose accuracy, treatment-planning-system interoperability, clinically valid biological parameters, patient safety/effectiveness, regulatory authorization, or patient-care suitability.

| Requirement ID | Function | Repository implementation | Verification | Current evidence state | Next external gate |
|---|---|---|---|---|---|
| BAROS-BIO-001 | LQ survival response | `baros/models.py::lq_survival` | known-value tests | IMPLEMENTED IN SOFTWARE | independent numerical/model review |
| BAROS-BIO-002 | Poisson-style TCP aggregation | `baros/models.py::poisson_tcp` | known-value tests | IMPLEMENTED IN SOFTWARE | model-selection/domain review |
| BAROS-BIO-003 | bounded sigmoid NTCP reference | `baros/models.py::logistic_ntcp` | monotonicity/reference tests | IMPLEMENTED IN SOFTWARE; bounded reference only | clinically justified model/parameters |
| BAROS-PHY-001 | synthetic beamlet-weight to voxel-dose mapping | `baros/dose.py::dose_from_influence` | synthetic mapping/constraint tests | SIMULATED ONLY | independent dose-engine/TPS validation |
| BAROS-SAFE-001 | fail-closed hard max-dose constraints | `baros/dose.py::hard_max_constraints` | positive/negative constraint tests | IMPLEMENTED IN SOFTWARE for numerical arrays | clinically governed constraints + TPS verification |
| BAROS-OPT-001 | deterministic constrained synthetic optimization | `baros/reference_optimizer.py::optimize_synthetic` | objective/constraint tests | SIMULATED ONLY | independent optimization review + pathological cases |
| BAROS-SAFE-002 | invalid mathematical inputs rejected | models/dose/optimizer validation | invalid-input tests | IMPLEMENTED IN SOFTWARE | expanded property/fuzz testing |
| BAROS-PIPE-001 | deterministic end-to-end research loop | `baros/pipeline.py`, `baros/cli.py` | pipeline tests + exact-run artifact | IMPLEMENTED IN SOFTWARE | independent reference fixtures |
| BAROS-IO-001 | RTSTRUCT ingestion/semantic validation | `baros/dicom_rt.py` | supported/wrong-modality/UID tests | IMPLEMENTED IN SOFTWARE for bounded objects | real-world multi-vendor conformance/interoperability |
| BAROS-IO-002 | RTPLAN ingestion/reference validation | `baros/dicom_rt.py` | RTPLAN/linkage tests | IMPLEMENTED IN SOFTWARE for bounded read/semantic validation | TPS research-interface validation |
| BAROS-IO-003 | RTDOSE numerical decoding | `baros/dicom_rt.py::decode_rtdose` | scaling/round-trip/error tests | IMPLEMENTED IN SOFTWARE; physical dose accuracy NOT CLAIMED | independent dose-engine/TPS + measurement validation |
| BAROS-IO-004 | RTSTRUCT → RTPLAN → RTDOSE reference-chain integrity | `baros/dicom_rt.py::validate_linkage` | matching/mismatched UID tests | IMPLEMENTED IN SOFTWARE | multi-vendor / real-case interoperability |
| BAROS-VAL-001 | DVH summary, Vx, Dx%, cumulative DVH | `baros/dvh.py` | exact-value, monotonicity, mask, fail-closed tests | IMPLEMENTED IN SOFTWARE for numerical arrays | independent TPS/physics reference comparison |
| BAROS-VAL-002 | gamma comparison | `baros/gamma_analysis.py` using pinned PyMedPhys | identity/error/input-validation tests | IMPLEMENTED IN SOFTWARE as research wrapper | measured-dose validation under qualified physics protocol |
| BAROS-ROB-001 | finite-scenario robustness evaluation | `baros/robustness.py` | worst-case/constraint/fail-closed tests | SIMULATED ONLY | clinically justified uncertainty model + partner validation |
| BAROS-ADAPT-001 | aligned cumulative-dose summation | `baros/adaptive.py::accumulate_aligned_dose` | alignment/mismatch/negative-dose tests | IMPLEMENTED IN SOFTWARE only for already-aligned grids | validated registration/resampling workflow |
| BAROS-GOV-001 | locked intended-use identity | `baros/clinical_governance.py::IntendedUseManifest` | digest stability/change tests | IMPLEMENTED IN SOFTWARE | partner/institution locks clinical research configuration |
| BAROS-GOV-002 | EBOM-style evidence envelope | `baros/clinical_governance.py::EvidenceEnvelope` | validation/quarantine tests | IMPLEMENTED IN SOFTWARE | partner-controlled evidence population |
| BAROS-GOV-003 | contradiction/deviation quarantine | `assess_evidence_for_gate` | contradiction/deviation negative tests | IMPLEMENTED IN SOFTWARE | external discrepancy adjudication process |
| BAROS-GOV-004 | exact-effect human gate authorization | `GateTransitionRequest`, `GateAuthorization` | mutated-effect/expiry tests | IMPLEMENTED IN SOFTWARE as bounded approval binding | institutional role/signature integration |
| BAROS-GOV-005 | durable replay/stale-state control | `SQLiteGateLedger` | replay/reopen/stale-epoch tests | IMPLEMENTED IN SOFTWARE at local SQLite boundary | external custody/witness hardening |
| BAROS-MOD-001 | local parameter identifiability | `baros/model_assurance.py::assess_local_identifiability` | full-rank/rank-deficient tests | IMPLEMENTED IN SOFTWARE | model-specific partner data and sensitivity analysis |
| BAROS-MOD-002 | validation experiment information gain | `expected_information_gain`, `rank_validation_experiments` | information/risk/authorization tests | IMPLEMENTED IN SOFTWARE as linearized research utility | partner-defined experiment models/cost/risk |
| BAROS-MOD-003 | observability-controllability hazard | `assess_observability_controllability` | low-O/high-C hazard tests | IMPLEMENTED IN SOFTWARE | clinically meaningful state/measurement definitions |
| BAROS-EVID-001 | evidence dependency graph | `baros/evidence_graph.py::EvidenceDependencyGraph` | chain/cycle/unknown dependency tests | IMPLEMENTED IN SOFTWARE | populate with external evidence lineage |
| BAROS-EVID-002 | blast-radius claim invalidation | `blast_radius`, `assess_claim` | invalid/quarantine/config-change tests | IMPLEMENTED IN SOFTWARE | link validation claims to partner artifacts/calibrations |
| BAROS-OBS-001 | synchronized expert technical readout | `baros/expert_readout.py`, `baros/expert_cli.py` | determinism, quantitative-state, governance/model/evidence-state and Markdown tests | IMPLEMENTED IN SOFTWARE; exact-head hosted verification required | external reviewer usability and evidence-ingestion evaluation |
| BAROS-VAL-003 | measurement/phantom QA | outside repository-only capability | none | REQUIRES LAB/PARTNER VALIDATION | medical-physics lab/clinical institution |
| BAROS-CLIN-001 | retrospective clinical performance | no controlled clinical dataset/evidence in repo | none | NOT CURRENTLY CLAIMED | institutional retrospective protocol |
| BAROS-CLIN-002 | prospective clinical safety/effectiveness | not established | none | NOT CURRENTLY CLAIMED | prospective study + regulatory/institutional pathway |

## Expert readout requirement

The expert readout integrates but does not promote the underlying evidence state. It must expose:

- mathematical/model assumptions;
- optimization and hard-constraint state;
- DICOM/dose/robustness summary;
- governance control state;
- model-identifiability/experiment-design capability state;
- evidence dependency/claim invalidation state;
- G0-G9 required evidence and current status;
- risk families/stop conditions;
- partner execution package;
- external blockers;
- exact source evidence and runtime provenance.

## Promotion rules

A requirement may move only to the broadest claim state directly supported by its evidence:

- numerical implementation does not establish model validity;
- an optimizer output does not establish parameter identifiability;
- synthetic dose tests do not establish physical dose accuracy;
- synthetic DICOM tests do not establish vendor/TPS interoperability or formal DICOM conformance;
- numerical DVH/gamma tests do not establish measurement-based QA;
- gamma pass rate alone is not a clinical safety endpoint;
- finite synthetic robustness scenarios do not establish clinical uncertainty coverage;
- aligned-grid summation does not establish deformable registration accuracy;
- an information-gain ranking does not authorize an experiment;
- local SQLite approval/replay controls do not substitute for institutional clinical authorization;
- a detailed expert readout does not establish external validation;
- TPS interoperability does not establish patient safety/effectiveness;
- peer review does not establish regulatory authorization;
- changed or quarantined evidence must invalidate dependent claims rather than leave stale promotion active;
- successful external evidence remains scoped to the locked intended use, version, population, modality, and workflow.

## Current exit state

BAROS now contains bounded planning/analysis functions, translational scientific-assurance controls, model-assurance utilities, dependency-aware claim invalidation, and an expert-facing observability layer designed to make the entire evidence state inspectable in one artifact.

The decisive next gate remains external: **independent numerical/model review, real TPS/vendor interoperability, measured-dose/end-to-end medical-physics validation, and held-out retrospective evaluation under partner control**.
