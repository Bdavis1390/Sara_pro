# BAROS Translational Validation — Expert Specific Aims Draft

> Research-stage planning document. NON-CLINICAL. This document does not establish patient-care suitability, clinical safety, clinical effectiveness, commissioned physical dose accuracy, TPS interoperability, or regulatory authorization.

## Overall objective

Translate BAROS (Biologically Adaptive Radiotherapy Optimization System) from a reproducibly verified research-software and translational-assurance framework into an independently testable radiotherapy optimization/decision-support system for one locked intended use, with explicit numerical, interoperability, dosimetric, workflow, human-factors and clinical-validation endpoints.

## Technical starting point

BAROS already contains bounded executable capability for:

- linear-quadratic survival, Poisson-form TCP and bounded sigmoid NTCP reference calculations;
- deterministic constrained synthetic optimization with hard max-dose rejection;
- RTSTRUCT/RTPLAN/RTDOSE semantic/reference-chain validation;
- RTDOSE scaling and strict geometry extraction;
- numerical DVH summary, Vx, Dx% and empirical cumulative DVH;
- gamma-index comparison through a pinned independent PyMedPhys implementation;
- finite-scenario robustness evaluation;
- cumulative dose summation only for proven-aligned grids;
- commit/configuration/input/runtime provenance and evidence hashing;
- bounded synthetic reliability testing;
- SHA-256 locked intended-use manifests;
- EBOM-style evidence envelopes including raw/analysis hashes, custody, uncertainty, deviations, contradictions and reviewer role;
- G0-G9 evidence requirements, exact-effect human authorization and durable monotonic epoch/replay protection;
- local model-identifiability analysis using sensitivity-matrix SVD;
- expected-information-gain experiment ranking with explicit cost/risk/irreversibility penalties and authorization boundaries;
- observability-versus-controllability hazard detection;
- trigger-governed closed-loop biological adaptation using measure -> qualify -> propose/re-optimize -> external recalculation/validation;
- safe degraded modes that hold the last valid plan or fall back to the declared standard plan rather than force adaptation from weak evidence;
- phase-coupled temporal-control scoring with explicit uncertainty and control-discontinuity penalties;
- dependency-aware evidence/model/configuration/claim graphs with quarantine propagation and blast-radius invalidation;
- synchronized JSON/Markdown expert readouts exposing assumptions, metrics, hard-constraint margins, governance state, model-assurance state, risk families, G0-G9 readiness and external blockers.

These capabilities remain research-only until the corresponding independent external gates are passed.

## Central hypothesis

For a narrowly defined radiotherapy indication and workflow, a trigger-governed biologically adaptive controller can update its internal state over treatment, but should propose replanning only when new observations are sufficiently qualified. The controller can be integrated as an external, auditable layer while preserving hard dosimetric constraints, independently commissioned final-dose calculation, qualified medical-physics QA, traceable evidence custody and human clinical authority.

The hypothesis will be rejected or narrowed if independent measurements, interoperability testing, model-identifiability analysis, held-out workflow evidence or human-factors evaluation reveal systematic error, unsafe failure modes, unmanageable uncertainty, insufficient observability, stale-claim risk or unacceptable workflow burden.

## Aim 1 — Lock intended use and independently validate the numerical, model and interoperability boundary

Jointly freeze:

- disease site / indication and stage/risk group;
- modality, delivery technique and machine class;
- TPS and version;
- fractionation/regimen class;
- target/OAR definitions and naming conventions;
- comparator planning workflow;
- BAROS commit/configuration;
- biological model/parameter sources and allowable uncertainty;
- biological/anatomical measurements allowed to drive adaptation;
- adaptation-trigger thresholds;
- state-qualification thresholds and out-of-distribution rules;
- temporal phase definition and phase-coupling weights;
- hold-last-valid and standard-plan fallback rules;
- permitted human overrides;
- primary/secondary endpoints;
- failure taxonomy, stopping rules and statistical analysis plan.

### Aim 1 work packages

1. Verify LQ/TCP/NTCP calculations against independent analytical/reference implementations.
2. Review model selection, parameter provenance, sensitivity, local identifiability, uncertainty and applicability; prohibit biological inputs that cannot be justified for the locked use.
3. Define measurable/observable state variables and refusal criteria for low-observability/high-control or out-of-distribution conditions.
4. Validate the closed-loop decision boundary itself: measure -> trigger assessment -> state qualification -> proposal/refusal, including false-trigger, missed-trigger, correct-refusal and incorrect-refusal cases.
5. Test phase-coupled temporal-control behavior under stable, changing, noisy and contradictory biological-state sequences.
6. Exercise real governed RTSTRUCT/RTPLAN/RTDOSE objects and vendor/TPS edge cases.
7. Verify UID/reference integrity, frame/coordinate semantics, dose-grid interpretation, scaling, unsupported-plan detection and failure behavior.
8. Verify that any BAROS research proposal is recalculated by the partner TPS or approved independent dose engine rather than treating BAROS surrogate dose as authoritative.
9. Execute malformed-input, stale-data, configuration/version-mismatch and partial-workflow failure injection.
10. Conduct formative expert-usability review of the BAROS readout: model assumptions, trigger reasons, qualification blockers, identifiability, constraints, provenance, disagreement and fail-closed states must be rapidly interpretable.
11. Populate the intended-use manifest and initial evidence dependency graph so later changes expose their claim blast radius.

### Aim 1 success condition

All material numerical, model, identifiability, geometry, reference-chain, data-integrity and interoperability discrepancies are resolved or retained as explicit failures under predeclared criteria. No silent clinically material failure is permitted. The partner can reproduce the exact software/evidence state from pinned artifacts, and unresolved contradictions or material deviations block promotion.

## Aim 2 — Establish physical dosimetric, deliverability and end-to-end performance under qualified medical-physics control

The partner QMP will control the measurement design, instruments, calibration, source data, custody, uncertainty analysis and acceptance criteria.

### Aim 2 work packages

Evaluate, as applicable to the locked technique:

- static reference fields;
- clinically relevant field sizes/depths and off-axis conditions;
- heterogeneous media;
- representative IMRT/VMAT cases;
- high-gradient target/OAR configurations;
- anthropomorphic end-to-end cases;
- independent point-dose measurement;
- planar/volumetric measurement;
- independent dose calculation;
- target/OAR DVH agreement;
- spatial dose-distribution agreement and localized discrepancy analysis;
- machine deliverability/complexity;
- repeated-run/release regression;
- failure localization and root-cause classification.

Every external run will be represented as a partner-controlled evidence envelope that binds the locked intended use, BAROS commit, protocol, configuration, raw/analysis artifacts, environment, custody, uncertainty, deviations, contradictions and reviewer role.

Gamma analysis may be included using institutionally appropriate criteria, but gamma pass rate will not substitute for absolute dose, clinically relevant DVH/structure metrics, localized error analysis or deliverability assessment.

### Aim 2 success condition

The locked BAROS/TPS/machine configuration satisfies institutionally predeclared absolute-dose, spatial, structural/DVH, deliverability, repeatability and end-to-end criteria with no unresolved systematic bias, coordinate error, stale-data hazard, hard-constraint bypass or clinically material silent failure. Contradictory evidence is quarantined rather than averaged away.

## Aim 3 — Establish held-out retrospective performance and prospective shadow-mode workflow feasibility

After Aims 1-2 pass, evaluate BAROS on partner-controlled governed cases without treatment authority.

### Aim 3A — Retrospective held-out validation

Use a cohort not used for final tuning. Predeclare:

- inclusion/exclusion;
- missing-data handling;
- comparator;
- target coverage and OAR/DVH metrics;
- robustness;
- deliverability;
- physician and physicist acceptability;
- trigger sensitivity/specificity against expert-adjudicated adaptation need;
- false-adaptation and missed-adaptation rate;
- correct-refusal and incorrect-refusal rate;
- hold-last-valid and standard-plan fallback frequency/reason;
- phase-coupled temporal stability;
- failure/fallback rate;
- BAROS-versus-standard disagreement;
- unsupported/out-of-distribution rate;
- workflow time and intervention burden;
- subgroup/failure analyses.

Evidence dependencies will be explicit so changed source data, calibrations, model parameters, TPS versions or BAROS configurations identify all affected downstream claims.

### Aim 3B — Prospective shadow mode

If justified by prior evidence and institutional review, run BAROS alongside the real workflow while standard care remains authoritative.

Measure:

- real-time DICOM/TPS/data-integrity failures;
- plan-generation success/failure;
- safety-control activation;
- adaptation-trigger events and whether the measured state qualified;
- PROPOSE_REOPTIMIZATION / HOLD_LAST_VALID / FALLBACK_STANDARD decisions;
- operator interaction and critical-use errors;
- workflow latency;
- prospective dose/constraint agreement;
- correct refusals, incorrect refusals and incorrect acceptances;
- disagreement resolution and override behavior;
- authorization/version mismatch and evidence-drift events.

### Aim 3 success condition

Generate an independently adjudicated evidence package sufficient to determine whether an interventional study is scientifically justified, what indication-specific safety/effectiveness hypothesis should be tested, and what FDA/IRB pathway applies. No interventional use is inferred merely from shadow-mode success.

## Innovation

The proposed innovation is not a claim that any single radiobiological equation is novel. The system-level innovation is the attempt to combine:

- explicitly identified biological objective terms;
- hard non-tradeable constraints;
- strict DICOM/geometry/data-integrity checks;
- model identifiability and observability scrutiny;
- trigger-governed measure/qualify/adapt/refuse control;
- phase-coupled temporal coordination instead of independent per-fraction optimization;
- hold-last-valid and standard-plan fallback under degraded evidence;
- independently recalculated final dose;
- robustness/failure analysis;
- evidence envelopes and dependency-aware claim invalidation;
- exact-effect human authorization and replay/stale-state control;
- human authority and fail-closed controls;
- expert-readable state, assumption, risk and evidence reporting;

into one falsifiable translational workflow whose claims can be promoted only as each corresponding evidence gate is actually passed.

## Partnership model

### BAROS engineering

- architecture, code, configuration custody and release control;
- model implementation and parameter provenance;
- deterministic verification and regression;
- DICOM/TPS interface engineering;
- model-assurance and experiment-design tooling;
- evidence/provenance, dependency graph and expert-readout generation;
- defect remediation;
- claims control.

### Academic medical physics / radiation oncology

- intended-use selection;
- independent numerical/model and identifiability review;
- TPS/machine/interface access and interoperability evaluation;
- commissioning and measurements;
- comparator selection;
- retrospective/prospective protocol design;
- endpoint/statistical design;
- human-factors input;
- failure/adverse-event adjudication;
- evidence custody and independent publication, including negative findings.

## Translational endpoint

The project succeeds if it produces a locked, independently characterized BAROS configuration with reproducible technical evidence, real-system interoperability evidence, measured-dose/end-to-end evidence, explicit model-assurance evidence and clinically relevant silent-workflow evidence sufficient to support a scientifically defensible go/no-go decision for interventional study and regulatory engagement.

It does not succeed merely because internal tests, synthetic optimization, governance controls or software reliability metrics are favorable.
