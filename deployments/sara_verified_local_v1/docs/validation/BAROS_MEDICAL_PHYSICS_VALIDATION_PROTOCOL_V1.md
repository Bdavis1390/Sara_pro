# BAROS Medical-Physics Computational Validation Protocol v1

**Artifact ID:** WS-BAROS-VAL.1.0  
**Status:** RESEARCH / NON-CLINICAL VALIDATION SPECIFICATION  
**Clinical boundary:** BAROS is not clinically validated or cleared/approved for patient-specific treatment decisions by this protocol. No patient treatment, dose prescription, optimization, or clinical deployment is authorized by this document.

## 1. Purpose

Create a rigorous non-clinical pathway for validating BAROS dose-calculation, optimization, uncertainty, and related medical-physics computation against accepted reference calculations and measurements before any clinical claim is considered.

## 2. External foundation

AAPM Medical Physics Practice Guideline 5.b addresses commissioning and QA of external-beam treatment-planning dose calculations and emphasizes validation of dose-calculation accuracy, beam modeling, and routine QA. AAPM also publishes sample IMRT/VMAT/reference datasets intended for dose-calculation validation.

These sources provide a quality-assurance framework; they do not validate BAROS.

## 3. Scope separation

Maintain separate evidence classes for:

- mathematical/unit tests;
- analytic or manufactured reference cases;
- Monte Carlo/reference-solver comparison;
- phantom measurement comparison;
- retrospective de-identified dataset evaluation;
- prospective/clinical evaluation.

Passing a lower evidence class does not authorize the next one.

## 4. Frozen software/model definition

Before each confirmatory campaign freeze:

- BAROS software commit and environment digest;
- dose engine/optimizer version;
- numerical solver and convergence settings;
- material/tissue parameter sources;
- beam/device model inputs where relevant;
- image preprocessing/resampling rules;
- coordinate system and DICOM interpretation rules;
- random seeds for stochastic calculations;
- objective/constraint definitions;
- acceptance metrics and tolerances;
- reference dataset digest.

Changing any materially relevant solver/model parameter after reviewing results creates a new campaign revision.

## 5. Stage B0 — Mathematical verification

Before comparing against clinical-style cases:

- unit tests for dimensions/units;
- conservation/normalization checks appropriate to the model;
- simple homogeneous geometry cases;
- symmetry tests where symmetry is expected;
- limiting cases;
- coordinate-transform and interpolation tests;
- deterministic repeatability or characterized stochastic variation;
- numerical convergence/sensitivity study.

A solver that cannot reproduce controlled mathematical cases cannot advance by good agreement on a complex dataset.

## 6. Stage B1 — Reference calculation comparison

Use accepted reference calculations or independently implemented reference solvers.

Requirements:

- no tuning to the final held-out cases;
- reference method/version recorded;
- point-dose and spatial-distribution differences retained;
- heterogeneity-sensitive cases included where the BAROS scope includes heterogeneous media;
- convergence and discretization effects characterized.

## 7. Stage B2 — Phantom / measurement validation

Where BAROS predicts a physically measurable dose quantity, comparison to calibrated measurement is required before a physical dose-accuracy claim.

Evidence should include:

- phantom/geometry identity;
- beam/device configuration identity;
- dosimeter/instrument calibration and traceability;
- setup/image/coordinate uncertainty;
- raw measurement files;
- environmental/setup notes;
- uncertainty budget;
- independent comparison between measured and BAROS-predicted dose.

The facility's qualified medical-physics procedures govern radiation operations. This protocol does not prescribe radiation-delivery settings.

## 8. Stage B3 — Standard/reference datasets

Use public or institution-approved datasets with explicit provenance. AAPM-provided treatment-planning validation datasets are an appropriate example source for benchmarking workflow behavior.

Maintain:

- untouched validation/test cases;
- training/development cases separately;
- preprocessing/version logs;
- DICOM object hashes;
- reference plan/calculation identity;
- failure and exclusion reasons.

## 9. Metrics

Select metrics appropriate to the BAROS intended function before unblinding results. Examples may include:

- absolute/relative dose difference at preregistered points/regions;
- spatial agreement metrics;
- gamma-style comparison where appropriate to the accepted medical-physics protocol;
- DVH-related differences for research comparison;
- optimization convergence and constraint satisfaction;
- uncertainty/calibration of predicted quantities;
- runtime/resource usage as a separate engineering metric.

Do not convert a single aggregate score into a universal accuracy claim.

## 10. Independent review

At minimum, a qualified medical physicist or appropriately credentialed domain expert must review:

- intended-use statement;
- reference cases;
- measurement methodology;
- acceptance criteria;
- limitations;
- failure cases;
- whether the test evidence supports the exact claim wording.

Domain review is evidence, not a substitute for independent physical validation.

## 11. Data governance

For any human-derived data:

- use only appropriately authorized/de-identified data;
- preserve source/consent/usage restrictions;
- prevent re-identification workflows;
- separate research identifiers from direct patient identifiers;
- maintain access/audit controls;
- do not copy clinical data into uncontrolled repositories.

## 12. Advancement gates

### Research verification

Requires mathematical verification, reference-case agreement, configuration custody, and uncertainty/sensitivity analysis.

### Internal physical validation

Requires calibrated measurement comparison where the intended claim is a physical dose prediction.

### Independent validation

Requires an independent facility/team or defensible separate chain with independent measurement/reference analysis and completed qualified domain review.

### Clinical use

Not granted by PVK. Any clinical deployment requires the applicable institutional, professional, quality, regulatory, cybersecurity, safety, and medical-device requirements.

## 13. Failure conditions

Do not advance claims if:

- agreement depends on tuning to the held-out test set;
- reference and BAROS share hidden implementation/code paths that defeat independence;
- dose discrepancies are hidden by aggregate metrics;
- image/coordinate or heterogeneity handling is not verified;
- measurement uncertainty is missing;
- clinically relevant failure cases are excluded without justification;
- qualified medical-physics review is absent for clinical-facing interpretations.

Negative or discrepant cases must remain in the evidence package.

## 14. Claim-safe wording

> BAROS is a research-stage medical-physics computational system. Its dose/optimization outputs require staged mathematical verification, reference-case comparison, calibrated physical measurement where applicable, uncertainty analysis, and qualified independent medical-physics review before any clinical-performance claim. No patient-specific clinical use is established by the present Worldshepherd evidence.

## 15. Public foundation references

- AAPM MPPG 5.b, *Commissioning and QA of treatment planning dose calculations—Megavoltage photon and electron beams*: https://aapm.org/pubs/MPPG/detail.asp?docid=246
- AAPM treatment-planning validation datasets: https://www.aapm.org/pubs/MPPG/TPS/
