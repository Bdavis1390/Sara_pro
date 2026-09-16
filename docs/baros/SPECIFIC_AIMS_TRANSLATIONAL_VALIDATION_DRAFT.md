# BAROS Translational Validation — Specific Aims Draft

> Research-stage planning document. NON-CLINICAL. This document does not establish patient-care suitability, clinical safety, clinical effectiveness, physical dose accuracy, or regulatory authorization.

## Overall objective

Translate BAROS (Biologically Adaptive Radiotherapy Optimization System) from a research-stage software framework into an independently testable radiotherapy planning system with predeclared physical, workflow, and clinical-validation endpoints for one locked intended-use population.

## Central premise

BAROS should advance only if independent medical-physics and clinical investigators can reproduce its behavior, identify failure modes, measure delivered-dose agreement, and demonstrate clinically meaningful performance under a locked protocol. Repository tests and simulation are prerequisites, not substitutes, for this evidence.

## Aim 1 — Lock intended use and complete independent technical/dosimetric validation

Jointly define one indication, treatment technique, delivery platform, TPS environment, fractionation strategy, comparator, software version, endpoints, and acceptance criteria. Complete independent medical-physics commissioning using measured dose, end-to-end testing, absolute-dose checks, clinically relevant DVH/structure metrics, gamma analysis where appropriate, heterogeneity/stress cases, failure localization, interoperability testing, and regression testing.

### Aim 1 success condition

A predeclared dose-accuracy endpoint must be satisfied on independent measurements with no unresolved clinically material systematic error. Any 98.7% probability claim must use an appropriate statistical design and lower confidence bound rather than a descriptive pass percentage.

## Aim 2 — Establish retrospective and prospective shadow-mode clinical workflow performance

Evaluate BAROS against the locked standard-of-care comparator on held-out retrospective cases, followed by prospective shadow-mode use in the real planning workflow while standard care remains authoritative. Quantify plan quality, OAR constraint compliance, target coverage, robustness, planning time, intervention frequency, failure modes, and discrepancy resolution.

### Aim 2 success condition

The system must meet predeclared safety and workflow-reliability thresholds with independent adjudication and without silent clinically material failures. No interventional use is permitted under this aim.

## Aim 3 — Determine whether interventional clinical validation is scientifically and regulatorily justified

Using the Aim 1–2 evidence, obtain appropriate institutional and regulatory determinations and, only if justified, execute a controlled prospective validation study with indication-specific safety and effectiveness endpoints. Clinical effectiveness will be analyzed using a predeclared superiority, non-inferiority, or other justified comparative design; it will not be inferred from a universal 98.7% cancer-outcome target.

### Aim 3 success condition

Clinical claims may be promoted only when the relevant safety, physical dose accuracy, clinical-effectiveness, and treatment-process endpoints independently meet their prespecified criteria and all required regulatory/institutional gates are satisfied.

## Partnership model

### Industrial / BAROS engineering role
- BAROS architecture, implementation, configuration custody, reproducibility, audit/provenance, software verification, interoperability engineering, release control, and technical remediation.
- Support deployment of frozen research builds and respond to independently identified defects.
- Maintain claims control and prevent clinical inference from synthetic evidence.

### Academic medical-physics / radiation-oncology role
- Lead or co-lead intended-use selection, dosimetric protocol, independent measurements, comparator definition, retrospective/prospective study design, clinical endpoint selection, statistical analysis, adverse-event/failure adjudication, and scientific publication.
- Retain authority to report negative findings, stop validation for safety/technical reasons, and require remediation before progression.

## Translational endpoint

Successful completion would produce a reproducible evidence package suitable for deciding whether BAROS merits broader multi-site validation, regulatory submission strategy, commercialization planning, and/or further controlled clinical evaluation. It would not by itself guarantee routine patient-care authorization.