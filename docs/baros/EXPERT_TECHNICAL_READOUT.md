# BAROS Expert Technical Readout Specification

Status: ACTIVE RESEARCH-SOFTWARE SPECIFICATION
Patient-care use: PROHIBITED

## Purpose

BAROS provides an expert-facing readout layer so a medical physicist, radiation oncologist, software reviewer, statistician, modeler, human-factors specialist, regulatory reviewer, or external research partner can inspect the exact bounded state of the system without reconstructing it from source code and scattered test artifacts.

The readout has two synchronized forms:

1. machine-readable JSON for audit, comparison, archival, automated review and evidence ingestion;
2. human-readable Markdown for rapid expert inspection.

Both are generated from the same deterministic bounded-reference execution.

## Required readout domains

Every readout exposes:

- BAROS name, schema, mode and exact commit SHA;
- explicit patient-care prohibition, partner-validation readiness and patient-care readiness;
- research question;
- model registry with equations, parameter names and assumption boundaries;
- optimizer class, objective, convergence state, iterations and objective change;
- bounded dose vector plus target/OAR summaries;
- every hard-constraint limit, observed value, margin and pass/fail state;
- synthetic TCP/NTCP values with clinical-interpretation prohibition;
- finite-scenario robustness results and worst case;
- translational-governance capability state;
- model-identifiability / information-gain / observability-controllability capability state;
- evidence-dependency / quarantine / blast-radius capability state;
- capability/evidence matrix;
- G0-G9 readiness state and gate-specific required evidence kinds;
- risk families and explicit stop conditions;
- safety invariants;
- partner execution package;
- external blockers;
- source evidence digest, case digest and runtime/dependency provenance;
- canonical SHA-256 digest of the complete readout.

## Design principle: maximum visibility, minimum inference

The report intentionally places assumptions, blockers and non-claims beside favorable numerical output.

Examples:

- an improving synthetic biological objective may not imply clinical benefit;
- a passing hard constraint may not imply machine deliverability;
- a DICOM semantic pass may not imply commercial TPS interoperability;
- a gamma result may not substitute for absolute dose or localized error analysis;
- aligned-grid dose summation may not imply registration accuracy;
- an identifiability algorithm does not establish that the clinical model is identifiable until the clinical sensitivity problem is populated;
- an information-gain ranking does not authorize an experiment;
- local gate/replay controls do not substitute for institutional authorization;
- synthetic reliability may not be interpreted as a patient-safety probability;
- changed or quarantined evidence must invalidate downstream claims.

## Expert usability goal

The expert reader should be able to answer, without opening source code:

1. What equations/models are active?
2. Which model parameters are clinically justified versus still research placeholders?
3. What did the bounded optimizer actually do?
4. What constraints were active and how close were they to failure?
5. What DICOM/geometry assumptions were enforced?
6. Which robustness scenarios were evaluated?
7. Which governance controls exist and which partner-controlled elements are still absent?
8. Has model identifiability actually been established for the intended use?
9. Which evidence or calibration changes would invalidate downstream claims?
10. Which G0-G9 gates are internal, partial, or externally open?
11. What failure modes force refusal, quarantine or stop?
12. What exactly must the partner do next?
13. Which exact commit/environment produced the report?
14. Can the report be independently identified and reproduced?

## Invocation

```bash
PYTHONPATH=. python -m baros.expert_cli \
  --commit-sha "$(git rev-parse HEAD)" \
  --json-output baros-expert-readout.json \
  --markdown-output baros-expert-readout.md
```

## Evidence boundary

The expert readout is an observability, governance and evidence-integration feature. It improves usability, reviewability and falsifiability. It does not promote BAROS beyond the evidence represented in the underlying modules and external validation record.
