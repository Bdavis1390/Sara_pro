# BAROS Clinical 98.7% Evidence Gate

Status: **EXTERNAL VALIDATION REQUIRED**

Patient-care use remains prohibited until the applicable institutional, clinical, quality-system, and regulatory gates are satisfied.

## Purpose

This gate defines what evidence would be required before BAROS may be described as having at least a 98.7% probability of being clinically safe, dose-accurate, clinically effective, and capable of successful treatment use.

The four claims are evaluated independently. They may not be averaged together, and a strong result in one domain may not compensate for weak or missing evidence in another.

A repository-only simulation, software test suite, manuscript, peer review, clinician opinion, synthetic gamma analysis, or synthetic reliability study cannot clear this gate.

## Intended-use lock comes first

No 98.7% clinical probability is meaningful without a fixed intended use. Before enrollment or clinical validation, BAROS must lock at minimum:

- disease site(s) and clinical indication;
- stage/risk group and inclusion/exclusion criteria;
- treatment modality and delivery platform(s);
- fractionation/regimen classes;
- target/OAR definitions and clinical planning protocol;
- comparator workflow and TPS;
- BAROS software/version/configuration;
- acceptable human-review intervention;
- primary and secondary endpoints;
- safety-event definitions;
- follow-up interval;
- statistical analysis plan and missing-data rules.

Any material expansion of intended use requires new evidence rather than extrapolation.

## Probability rule

A claim may be stated as `>= 98.7%` only when its predeclared statistical analysis supports that lower bound for the specific intended use.

For a simple binary endpoint with zero observed failures, an exact one-sided binomial lower confidence bound may be used. At a 99.9% one-sided confidence level, at least **528 independent zero-failure observations** are required before the exact lower confidence bound can exceed 98.7%.

This zero-failure calculation is appropriate only for genuinely binary, independently adjudicated events. It must not be misapplied to continuous dose error, tumor control, toxicity severity, survival, or composite endpoints.

## C1 — Clinical safety >= 98.7%

### Claim definition

Within the locked intended use, the probability that BAROS contributes **no device-attributable serious treatment-planning or treatment-delivery safety failure** must have a predeclared lower confidence/credible bound >= 98.7%.

### Safety failures include, at minimum

- wrong-patient/wrong-study association attributable to BAROS;
- incorrect coordinate/frame interpretation;
- clinically material structure, prescription, beam, or dose corruption;
- hard OAR constraint bypass;
- silent optimizer failure or unsafe fallback;
- incorrect cumulative-dose handling;
- clinically material DICOM/TPS interoperability error;
- clinically material dose discrepancy not detected by required QA;
- software/cybersecurity failure that can affect treatment output;
- BAROS-attributable treatment delay or interruption meeting the protocol's serious-event definition;
- any serious adverse device effect adjudicated as related or possibly related to BAROS.

### Required evidence

1. Formal risk analysis and traceability under the applicable medical-device QMS.
2. Hazard controls verified at software/system level.
3. Independent medical-physics review of safety architecture.
4. Prospective event capture with independent adjudication.
5. A predeclared safety endpoint whose lower probability bound clears 98.7%.
6. No unresolved safety signal in subgroup, site, version, or failure-mode analysis.

A zero-event study may use an exact binomial bound only if the endpoint is genuinely binary and the denominator consists of independent clinically relevant uses.

## C2 — Dose accuracy >= 98.7%

### Claim definition

For the locked delivery systems, beam models, techniques, and clinical geometries, BAROS-associated plans must meet the commissioned physical-dose accuracy requirements with a lower probability bound >= 98.7% **and** must satisfy all required absolute tolerance/action limits.

### Required physical validation layers

- commissioning against measured beam data;
- water-tank/point-dose measurements across field sizes, depths, off-axis positions, modifiers, and clinically relevant heterogeneities;
- IMRT/VMAT commissioning appropriate to the intended techniques;
- anthropomorphic/end-to-end testing;
- independent dose calculation where appropriate;
- patient-specific measurement-based QA for the validation cohort;
- dose/DVH comparison on clinically important targets and OARs;
- failure-localization analysis rather than reliance on a single gamma percentage;
- longitudinal constancy and software-upgrade regression testing.

AAPM MPPG 5.b/TG-218-style criteria are treated as baseline clinical-physics references, not as proof by citation. The actual BAROS configuration must be measured.

### Statistical requirement

The protocol must define a clinically meaningful binary dose-accuracy success unit (for example, an independently measured plan meeting every predeclared absolute and spatial criterion). The lower probability bound for that unit must exceed 98.7%.

In addition, all continuous dose-error metrics must meet their predeclared numerical tolerances. A high pass probability may not hide a systematic bias that violates an absolute tolerance.

## C3 — Clinical effectiveness >= 98.7%

### Claim definition

BAROS must demonstrate clinically meaningful benefit or non-inferiority for its intended treatment-planning function in the target clinical population.

Because effectiveness is not a single universal Bernoulli variable, this claim must be indication-specific.

### Required endpoints may include

- protocol-compliant target coverage;
- OAR sparing;
- physician/medical-physics clinical acceptability;
- replanning frequency;
- treatment-plan deliverability;
- clinically relevant acute/late toxicity;
- local control/progression endpoints when BAROS is claimed to influence them;
- quality-of-life or patient-relevant functional outcomes when applicable.

### Comparative design

The prospective protocol must compare BAROS against an appropriate standard-of-care planning workflow using a predeclared superiority or non-inferiority hypothesis. The analysis must account for site, technique, operator, institution, and relevant patient covariates.

A BAROS clinical-effectiveness claim of >=98.7% requires either:

- a predeclared posterior probability >=98.7% that the clinically meaningful effectiveness criterion is met; or
- a frequentist design whose confidence interval establishes the predeclared effect/non-inferiority criterion with an equivalent level of evidentiary strength.

The exact effect size, non-inferiority margin, and sample size cannot be fixed until the disease site, comparator, endpoint, baseline event rate, and acceptable clinical margin are defined.

## C4 — Successful treatment use >= 98.7%

### Claim definition

For the locked intended use, a `successful treatment use` means that the BAROS-assisted plan:

1. is generated without a BAROS-attributable safety failure;
2. passes all clinical planning constraints;
3. passes independent physics/delivery QA;
4. is accepted by the authorized clinical team;
5. is delivered as intended without a BAROS-attributable treatment failure; and
6. meets the protocol-defined treatment-process endpoint.

The lower probability bound for successful treatment use must exceed 98.7%.

This endpoint does **not** mean a 98.7% probability of cancer cure, survival, or freedom from toxicity. Disease outcome claims require indication-specific clinical endpoints and follow-up under C3.

## Required validation sequence

### Phase A — Preclinical/bench lock

Must complete before human-use validation:

- software verification and requirements traceability;
- DICOM/TPS interoperability on intended systems;
- independent numerical/model validation;
- complete physical/dosimetric commissioning;
- anthropomorphic end-to-end testing;
- cybersecurity/risk controls;
- failure-injection and fail-safe testing;
- independent medical-physics sign-off on the validation protocol.

### Phase B — Retrospective silent study

BAROS runs on prior/de-identified cases without influencing care.

Required:

- locked cohort/protocol;
- blinded or independently adjudicated comparator analysis;
- site-specific performance and failure analysis;
- subgroup and out-of-distribution analysis;
- no retrospective tuning on the final held-out validation cohort.

### Phase C — Prospective silent/shadow study

BAROS runs prospectively while standard care remains authoritative.

Required:

- prospective data capture;
- real workflow/interoperability timing;
- safety/failure detection;
- independent adjudication of whether BAROS recommendations would have been clinically acceptable;
- confirmation that retrospective performance survives prospective workflow conditions.

### Phase D — Controlled interventional study

Only after institutional and regulatory authorization appropriate to the risk determination.

Required:

- IRB-approved protocol;
- IDE/FDA authorization when required;
- informed consent when required;
- predefined stopping rules;
- data safety monitoring appropriate to risk;
- prospective comparison with standard care;
- independent endpoint adjudication;
- final locked statistical analysis.

### Phase E — Multi-site replication

Before a broad clinical claim:

- independent institutions;
- different planners/physicists;
- representative hardware/TPS configurations within intended use;
- independently reproduced dose and workflow evidence;
- predeclared pooled and site-specific analyses;
- no site may be hidden by an aggregate average if its safety/accuracy gate fails.

## 98.7% release rule

BAROS may be described as meeting the 98.7% clinical gate only when **all four** of these are true for the same locked intended use and software version:

- `C1 SAFETY >= 98.7%` — supported by prospective clinical safety evidence;
- `C2 DOSE ACCURACY >= 98.7%` — supported by independent physical measurements and clinical physics validation;
- `C3 CLINICAL EFFECTIVENESS >= 98.7% evidentiary threshold` — supported by an indication-specific comparative clinical study;
- `C4 SUCCESSFUL TREATMENT USE >= 98.7%` — supported by prospective treatment-process evidence.

If any one claim is below threshold, uncertain, unmeasured, or lacks external evidence, the combined clinical 98.7% claim is prohibited.

## Regulatory/quality-system boundary

The final regulatory classification/pathway is not predetermined by this document. It must be established from the locked intended use and current FDA interaction.

Clinical investigations must follow applicable human-subject, IRB, IDE, informed-consent, monitoring, record, and reporting requirements. Significant-risk device studies require FDA IDE approval and IRB approval before initiation.

BAROS development intended for clinical deployment must operate under the applicable FDA Quality Management System Regulation and associated software, risk-management, cybersecurity, design/development, verification, validation, and change-control requirements.

## Current state

At creation of this document:

- BAROS has bounded repository-level research-software evidence;
- BAROS does **not** yet possess the external measured-dose, prospective clinical, interventional, or regulatory evidence required to make any of the four clinical 98.7% claims;
- therefore the current combined clinical 98.7% claim state is **NOT ESTABLISHED**.

The correct next milestone is not another synthetic probability calculation. It is acquisition of external medical-physics and clinical evidence under a locked protocol.
