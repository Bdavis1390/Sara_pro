# BAROS External Clinical Validation Protocol

Status: PARTNER / IRB / REGULATORY EXECUTION REQUIRED

This protocol operationalizes `CLINICAL_98_7_EVIDENCE_GATE.md`. It is a planning artifact, not evidence that BAROS is clinically validated.

## 1. Objective

Generate the external evidence required to evaluate four independent claims for one locked BAROS intended use:

1. clinical safety;
2. physical/dosimetric accuracy;
3. clinical effectiveness;
4. successful treatment-process use.

Each claim must independently satisfy its predeclared acceptance criterion. No composite average may be used to mask a failing component.

## 2. Intended-use definition package

Before any validation data are collected, freeze:

- disease site / indication;
- stage or risk group;
- modality (e.g. external-beam photon treatment only unless expanded);
- delivery technique(s);
- treatment machine class(es);
- TPS and version;
- BAROS version / commit / configuration;
- fractionation classes;
- planning protocol;
- structure and prescription conventions;
- comparator workflow;
- operator qualifications;
- permitted human overrides;
- primary and secondary endpoints;
- safety-event taxonomy;
- follow-up duration;
- statistical analysis plan.

The frozen intended-use package receives a unique validation identifier. Evidence from a different configuration cannot be silently pooled.

## 3. Stage A — Independent physical/dosimetric validation

Owner: qualified medical physicist / partner institution.

BAROS must not influence patient care during this stage.

### Required test classes

- static reference fields;
- clinically relevant field sizes and depths;
- off-axis conditions;
- heterogeneous media;
- representative IMRT/VMAT cases if in intended use;
- clinically relevant high-gradient OAR scenarios;
- anthropomorphic end-to-end cases;
- independent point-dose measurements;
- planar or volumetric dose measurements;
- independent dose calculation where available;
- DICOM/TPS round-trip checks on intended systems;
- failure injection and malformed-input cases;
- software-upgrade/regression repeatability.

### Baseline physics criteria

Use current institutional commissioning criteria, AAPM MPPG 5.b, TG-218 where applicable, and any stricter technique-specific requirements selected by the partner QMP.

For IMRT/VMAT pretreatment QA, TG-218-style 3%/2 mm global gamma with a 10% threshold and >95% tolerance is a baseline reference, but gamma alone is insufficient. Absolute dose, clinically important DVH/structure metrics, spatial failure localization, and end-to-end measurements must also pass.

### 98.7% dose-accuracy probability unit

Before testing, define one independent `dose_accuracy_case` as a complete measured case that meets **all** predeclared absolute, spatial, structural, and deliverability criteria.

For a zero-failure exact-binomial gate:

- 95% one-sided confidence: at least 229/229 passing cases;
- 97.5% one-sided confidence: at least 282/282 passing cases;
- 99% one-sided confidence: at least 352/352 passing cases;
- 99.9% one-sided confidence: at least 528/528 passing cases.

These are statistical lower-bound requirements only. All mandatory absolute tolerances must still be satisfied.

Any systematic bias, clinically significant localized discrepancy, or serious failure blocks the claim even if the aggregate probability calculation would otherwise pass.

## 4. Stage B — Retrospective silent clinical validation

BAROS processes historical cases without affecting care.

### Cohort rules

- predeclared inclusion/exclusion criteria;
- consecutive or otherwise defensibly sampled cases;
- held-out validation cohort not used for model or parameter tuning;
- partner-controlled source data and governance;
- documented missing-data handling;
- representation of clinically important subgroups;
- no post-hoc removal of difficult cases except by predeclared exclusion rule.

### Comparative endpoints

At minimum:

- target coverage;
- OAR constraints and DVH metrics;
- plan deliverability;
- physician acceptability;
- medical-physics acceptability;
- planning failures / fallback frequency;
- clinically material BAROS-versus-standard disagreements;
- workflow time and intervention burden;
- out-of-distribution / unsupported-case rate.

BAROS remains investigational. Retrospective plan superiority does not establish patient benefit.

## 5. Stage C — Prospective shadow-mode validation

BAROS runs prospectively but cannot control treatment decisions.

Standard clinical planning remains authoritative.

### Required observations

- real-time DICOM/TPS interoperability;
- case intake and data-integrity errors;
- operator interaction and usability failures;
- BAROS plan generation success;
- silent safety-control activation;
- clinician / QMP acceptability before seeing standard-plan outcome where feasible;
- elapsed workflow time;
- prospective dose and constraint agreement;
- cases BAROS correctly refuses;
- cases BAROS incorrectly accepts;
- cases BAROS incorrectly refuses.

### Clinical safety binary endpoint

Define a `safe_use` as a prospective case with no adjudicated BAROS-attributable serious safety failure.

If the protocol uses a zero-failure exact-binomial claim at 99.9% one-sided confidence, at least 528 independent safe uses with zero failures are required to establish a lower bound above 98.7%.

This denominator must consist of real prospectively processed clinical cases, not repeated simulations of the same case.

## 6. Stage D — Regulatory / IRB determination before interventional use

Before BAROS can influence patient treatment:

- obtain institutional IRB determination / approval;
- determine device-study risk status;
- obtain FDA IDE approval if required for a significant-risk study;
- finalize informed consent requirements;
- establish monitoring, adverse-event reporting, records, and stopping rules;
- establish investigational labeling and version control;
- lock the clinical protocol and statistical analysis plan.

No interventional human-use phase begins solely because the prior stages pass.

## 7. Stage E — Controlled prospective interventional study

BAROS may influence treatment only under the authorized protocol.

### Safety endpoint

Predefine device-attributable serious safety failures and an independent adjudication process.

For a direct >=98.7% binary safety claim, the lower confidence/credible bound for `safe_use` must exceed 98.7%.

### Successful-treatment-process endpoint

A `successful_treatment_use` requires all of the following:

- no BAROS-attributable serious safety failure;
- protocol-compliant plan;
- independent physics QA pass;
- authorized clinical acceptance;
- intended treatment delivery without BAROS-attributable failure;
- no protocol-defined serious BAROS process failure.

A direct >=98.7% claim requires the lower probability bound for this endpoint to exceed 98.7%.

This is a treatment-process endpoint, not a cancer-cure probability.

## 8. Clinical-effectiveness endpoint

Clinical effectiveness must be indication-specific.

BAROS must be compared with a standard-of-care workflow using a predeclared superiority or non-inferiority design.

The primary effectiveness endpoint must be patient-relevant or clinically meaningful for the intended use. Possible components, selected by clinical investigators, include:

- target coverage / protocol compliance;
- clinically meaningful OAR sparing;
- toxicity endpoints;
- treatment interruption;
- local control or progression endpoint where scientifically justified;
- patient-reported outcome or functional endpoint when appropriate.

The trial may claim the requested 98.7% evidentiary threshold only if the locked statistical analysis shows at least 98.7% posterior probability that the clinical criterion is satisfied, or a prospectively accepted frequentist criterion of comparable evidentiary strength.

A numerical sample size cannot be responsibly specified until the partner investigators fix:

- indication;
- baseline event rate;
- endpoint distribution;
- clinically acceptable non-inferiority margin or superiority effect;
- allocation ratio;
- expected attrition / missingness;
- multiplicity plan;
- desired type-I error / power or Bayesian prior model.

## 9. Multi-site replication

A broad clinical claim requires replication beyond one institution when the intended use spans multiple clinical environments.

Record for each site:

- TPS / machine versions;
- commissioning configuration;
- QMP sign-off;
- planner / physician experience;
- case mix;
- safety events;
- dose-accuracy results;
- clinical-effectiveness endpoint;
- successful-treatment-use endpoint.

A pooled result cannot hide a site whose predefined safety or dose-accuracy gate fails.

## 10. Evidence bundle per case

Each external validation case must preserve:

- validation protocol/version;
- BAROS commit/release/configuration;
- site and system identifiers under approved governance;
- source-data provenance;
- comparator plan identifier;
- plan parameters / constraints;
- measured dose artifacts where applicable;
- independent calculation artifacts where applicable;
- DVH and gamma reports;
- adjudication results;
- deviations and overrides;
- adverse/safety events;
- physician / QMP disposition;
- analysis inclusion/exclusion reason;
- cryptographic hashes where feasible.

## 11. Stopping / failure rules

Immediately suspend claim promotion when any of the following occurs:

- serious BAROS-attributable patient safety event;
- clinically material silent dose corruption;
- hard constraint bypass;
- systematic DICOM/TPS coordinate error;
- systematic measured-dose bias outside commissioned tolerance;
- unresolved cybersecurity event with treatment impact;
- evidence of clinically important subgroup degradation;
- protocol/data-integrity failure invalidating the statistical analysis.

## 12. Final release criterion

BAROS is not allowed to state that it has >=98.7% probability of being clinically safe, clinically effective, dose-accurate, and capable of successful treatment use until the **same locked intended use and version** has evidence supporting all four clinical claims and the applicable regulatory/institutional conditions are satisfied.

Until then, the proper claim is:

`REQUIRES EXTERNAL MEDICAL-PHYSICS / CLINICAL / REGULATORY VALIDATION`.
