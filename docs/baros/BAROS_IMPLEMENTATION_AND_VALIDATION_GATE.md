# BAROS Implementation and Medical Validation Gate

Status: ACTIVE VALIDATION SPECIFICATION
Scope: Biologically Adaptive Radiotherapy Optimization System (BAROS)
Patient-care use: **PROHIBITED until all applicable clinical/regulatory gates are satisfied**

## Purpose

This document defines what must be true before Worldshepherd may claim that BAROS is implemented, reproducible, scientifically supported, clinically validated, or suitable for patient-care use.

It exists to prevent a manuscript, simulation, code artifact, internal test, peer review, or planning-system interface from being misrepresented as broader evidence than it actually provides.

## Critical boundary: peer review is not medical-device validation

Peer review is an important external scientific-scrutiny gate. It can establish that methods, assumptions, analyses, limitations, and reported evidence have been examined by qualified independent reviewers.

Peer review **does not by itself establish**:

- software correctness;
- DICOM-RT interoperability;
- treatment-plan deliverability;
- physical dose accuracy;
- patient-specific QA performance;
- clinical safety or effectiveness;
- generalization to the intended patient population;
- regulatory authorization;
- suitability for patient care.

Accordingly:

> **Peer review separates unreviewed research from externally scrutinized science. It does not separate an unvalidated medical technology from a validated one.**

For BAROS, a medical-validation claim requires objective evidence across software verification, analytical/technical validation, physical/dosimetric validation, clinical validation, human factors/risk management, and the applicable regulatory pathway.

## Current BAROS claim state at gate creation

At creation of this gate, the canonical `main` branch does not contain an indexed executable BAROS/radiotherapy/DVH implementation. The BAROS manuscript therefore remains a research specification and validation roadmap rather than evidence that the full technology executes from the repository.

Current permitted claim states:

- `SUPPORTED BY LITERATURE` for individual methods where an explicit source supports them;
- `HYPOTHESIS` for proposed BAROS-specific mechanisms not independently demonstrated;
- `SIMULATED ONLY` only where a traceable, reproducible simulation artifact actually exists;
- `NOT CURRENTLY CLAIMED` for clinical benefit, patient-care suitability, regulatory status, or physical performance not backed by evidence.

A manuscript statement such as an observed gamma pass rate, TCP/NTCP improvement, clinical-QA pass, retrospective result, or multi-site result is **not accepted as evidence** unless the repository or controlled evidence store contains the underlying dataset identity, configuration, executable method, output artifacts, statistical analysis, and provenance sufficient for independent reproduction.

## Intended BAROS research architecture

The implementation target derived from the BAROS manuscript is:

1. DICOM-RT ingestion and validation (`RTSTRUCT`, `RTPLAN`, `RTDOSE`);
2. imaging/feature input normalization;
3. biological parameter mapping (for example alpha/beta, hypoxia, proliferation/repair proxies) with explicit uncertainty;
4. TCP/NTCP and related model evaluation;
5. constrained optimization of plan parameters or research fluence representation;
6. hard OAR, protocol, and machine/deliverability constraints;
7. TPS/research-dose-engine adapter boundary;
8. final-dose recalculation outside the BAROS surrogate path;
9. DVH, dose-difference, gamma, constraint, and robustness evaluation;
10. adaptive/cumulative-dose state handling;
11. audit/provenance, versioning, fail-closed behavior, and human approval;
12. reproducible reports suitable for independent scientific review.

BAROS must remain an external research optimization layer. No repository code may bypass clinical TPS dose recalculation, patient-specific QA, or authorized human review.

## Definition of "works from the repository"

The phrase **works from the repository** may be used only for a bounded research configuration when all of the following are true:

- a clean checkout at a pinned commit installs from documented dependencies;
- a single documented command or workflow runs the complete research pipeline end-to-end;
- all required test fixtures are public, synthetic, de-identified and legally usable, or are referenced through an approved controlled-data process;
- all unit, integration, numerical-regression, negative-path, security, and provenance tests pass;
- outputs are deterministic within predeclared tolerances;
- hard constraints fail closed;
- unsupported inputs and malformed DICOM are rejected safely;
- no clinical result is inferred from synthetic-only evidence;
- the resulting evidence bundle records code SHA, configuration, inputs, model versions, outputs, metrics, failures, and environment.

This definition supports `IMPLEMENTED IN SOFTWARE` or `PROVEN INTERNALLY` for the tested research configuration. It does **not** support a claim of clinical validation.

## Mandatory validation gates

### G0 — Requirements and traceability

Pass criteria:

- every BAROS requirement has a stable ID;
- each requirement maps to code, tests, evidence, and risk controls;
- intended use and non-intended use are explicit;
- clinical claims are absent unless separately validated.

Maximum promotion if passed: architecture is traceable; no medical-performance promotion.

### G1 — Deterministic component verification

Required coverage includes:

- biological model calculations;
- TCP/NTCP calculations;
- uncertainty propagation;
- optimizer objective/gradient behavior;
- hard-constraint enforcement;
- DVH metrics;
- gamma implementation against known reference cases if implemented locally;
- audit/provenance serialization.

Pass criteria:

- unit/property/regression tests pass at pinned commit;
- independent numerical reference fixtures agree within predeclared tolerance;
- pathological and boundary inputs are covered.

Maximum promotion if passed: `IMPLEMENTED IN SOFTWARE` for tested components.

### G2 — End-to-end research pipeline

Pass criteria:

- synthetic/de-identified imaging and DICOM fixtures traverse the full pipeline;
- plan proposal -> external/research dose calculation -> evaluation -> bounded update loop is reproducible;
- every state transition is logged;
- invalid inputs, missing structures, invalid geometry, impossible constraints, and dose-engine failures terminate safely.

Maximum promotion if passed: `PROVEN INTERNALLY` for the bounded research workflow.

### G3 — Numerical and model validation

Pass criteria:

- LQ/TCP/NTCP/model outputs match independent reference implementations or analytically checkable cases;
- sensitivity and uncertainty analyses are predeclared and reproducible;
- model-identifiability and calibration limits are documented;
- no imaging-derived biological parameter is treated as measured truth without evidence.

Maximum promotion if passed: `PROVEN INTERNALLY` + applicable `SUPPORTED BY LITERATURE` for specific models.

### G4 — DICOM-RT interoperability and conformance

Pass criteria:

- validated parsing/writing of the intended DICOM-RT objects;
- round-trip tests preserve required semantics;
- transfer-syntax, UID, coordinate-frame, contour, plan, and dose-grid edge cases are covered;
- malformed or ambiguous records fail closed;
- vendor-specific behavior is documented and tested where accessible.

Maximum promotion if passed: internal interoperability evidence only.

### G5 — External TPS/research-dose-engine integration

Pass criteria:

- BAROS-generated research plan changes are imported by the target TPS or approved research interface;
- the independent dose engine recalculates dose without relying on BAROS's surrogate result;
- dose-grid, coordinate, structure, beam/control-point, and constraint semantics are preserved;
- failures and unsupported plan constructs are handled safely.

Maximum promotion if passed: `REQUIRES PARTNER VALIDATION` may be cleared only for the tested integration if the partner/institution provides documented evidence.

### G6 — Physical/dosimetric verification

Pass criteria must be predeclared by qualified medical-physics collaborators and may include:

- independent dose comparison;
- gamma analysis using context-appropriate criteria;
- DVH and clinical-constraint agreement;
- phantom or measurement-based QA;
- machine-deliverability/complexity checks;
- setup and model-uncertainty robustness.

Repository simulation cannot clear this gate by itself.

Maximum promotion if passed: physical/dosimetric validation for the tested configuration only.

### G7 — Retrospective clinical validation

Requires appropriate institutional oversight, data governance, expert protocol design, and de-identified/controlled clinical data.

Pass criteria:

- pre-specified protocol, endpoints, baseline comparators, exclusion criteria, and statistical analysis plan;
- held-out or independently sourced evaluation data;
- clinically relevant failure analysis and subgroup performance;
- transparent negative/null findings;
- no use for treatment decisions during research-only evaluation.

Maximum promotion if passed: retrospective clinical evidence; not routine patient-care authorization.

### G8 — Independent replication and peer review

Pass criteria:

- qualified external investigators can reproduce the bounded method and evidence;
- manuscript methods match the executable implementation;
- reported metrics are traceable to immutable evidence bundles;
- limitations and negative evidence are disclosed;
- independent peer review is completed for the claims being published.

Maximum promotion if passed: externally scrutinized and independently reproduced evidence for the bounded claims.

**G8 still does not, by itself, authorize clinical use.**

### G9 — Prospective clinical/regulatory readiness

Before patient-care deployment, complete the applicable pathway for the intended use and jurisdiction. This includes, as applicable:

- prospective clinical evidence;
- risk management and benefit-risk analysis;
- human factors/usability validation;
- cybersecurity lifecycle controls;
- quality-system controls;
- software lifecycle and change-control documentation;
- regulatory interaction/submission/authorization;
- site acceptance, commissioning, and post-market/performance monitoring.

Only this stage can support a claim that BAROS is ready for the authorized clinical use, and only within that authorization's scope.

## Claims-control rule for manuscript results

Until traceable evidence exists, convert result-style wording to one of these forms:

- `VALIDATION TARGET:` for an intended acceptance threshold;
- `SYNTHETIC RESULT:` for reproducible synthetic data generated by an identified script/commit;
- `MODEL-PREDICTED RESULT:` for a model estimate without clinical observation;
- `RETROSPECTIVE RESULT:` only with a traceable retrospective dataset/protocol and analysis;
- `EXTERNALLY REPLICATED:` only after independent reproduction;
- `CLINICALLY VALIDATED:` only when the defined clinical-validation evidence supports the intended use.

Examples that currently require evidence before being presented as established results include manuscript statements about 97-99% gamma pass rates, statistically significant TCP improvement, NTCP reduction, all plans passing clinical QA, multi-site consistency, and superiority to standard TPS optimization.

## Repository acceptance artifacts required before G2 is declared

Expected minimum tree:

```text
baros/
  README.md
  pyproject.toml or integrated project packaging
  src/baros/
    io/
    biology/
    models/
    optimization/
    constraints/
    adapters/
    validation/
    provenance/
    cli.py
  tests/
    unit/
    integration/
    regression/
    negative/
    fixtures/
  evidence/
    README.md
  docs/
    INTENDED_USE.md
    REQUIREMENTS.md
    TRACEABILITY_MATRIX.md
    RISK_REGISTER.md
    VALIDATION_PROTOCOL.md
```

Exact layout may vary, but equivalent functionality, traceability, and test coverage are mandatory.

## Evidence-bundle schema

Every BAROS evidence-producing run must capture at minimum:

- repository and commit SHA;
- branch/tag/release;
- build/dependency lock identifier;
- operating environment;
- input dataset/fixture IDs and provenance;
- model/parameter versions;
- intended-use test configuration;
- random seeds where applicable;
- test and analysis commands;
- pass/fail criteria declared before result review;
- output hashes;
- metrics and confidence intervals where applicable;
- warnings/failures/exclusions;
- reviewer identity/role for controlled external validation;
- claim-state promotion permitted by that run.

## External standards/regulatory baseline

As of 2026, BAROS planning should be aligned with the current FDA device-software documentation framework, the FDA Quality Management System Regulation (QMSR) effective 2026-02-02, applicable software lifecycle/risk-management/cybersecurity expectations, and the IMDRF SaMD clinical-evaluation model distinguishing valid clinical association, analytical/technical validation, and clinical validation.

The exact regulatory classification/pathway is **not predetermined by this repository** and must be confirmed against the final intended use and current FDA feedback before any submission strategy is represented as settled.

## Release rule

No BAROS branch may be labeled or described as clinically validated, treatment ready, production medical software, FDA approved/cleared/authorized, or suitable for patient care solely because:

- tests pass;
- CI is green;
- a manuscript is complete;
- the manuscript is peer reviewed;
- simulated gamma/DVH/TCP/NTCP metrics pass;
- the software interoperates with a TPS;
- a clinician or physicist expresses interest.

The broadest permitted claim must always be the narrowest claim fully supported by traceable evidence.
