# Worldshepherd — NIST AI RMF Evidence Alignment Baseline — 2026-09-13

Status: INTERNAL ALIGNMENT MAP / NOT CERTIFICATION / NOT CONFORMITY CLAIM

## Purpose
Map Worldshepherd governance and evidence controls to the NIST AI Risk Management Framework functions as an engineering checklist. This document does not assert NIST certification, regulatory compliance, government authorization, or external validation.

NIST reference posture as of 2026-09-13:
- AI RMF 1.0 remains the current published framework while revision work is underway.
- NIST AI 600-1 provides the Generative AI Profile.
- NIST is developing a Trustworthy AI in Critical Infrastructure Profile.

## GOVERN
Worldshepherd controls:
- CRE1AWS human authority and explicit approval boundaries.
- PRIME policy and authorization layer.
- Claims-control taxonomy separating internal implementation, simulation, hypothesis, lab validation, partner validation, legal review, and external evidence.
- Auditability and configuration custody.

Evidence required:
- policy version and digest;
- actor/role identity;
- authorization decision;
- approval record;
- configuration digest;
- exception record;
- supersession history.

Gap status:
- external governance assessment: NOT PERFORMED;
- regulatory mapping by use case: REQUIRES LEGAL/COMPLIANCE REVIEW.

## MAP
Worldshepherd controls:
- PRE Requirement Delta Records.
- explicit demand classes: CONFIRMED DEMAND, EMERGING DEMAND, WORLDSHEPHERD FORECAST.
- system/context decomposition by lane, stakeholder, environment, dependency, and evidence target.
- claims boundary attached to each requirement record.

Evidence required:
- source lineage;
- intended use and prohibited use;
- affected stakeholders;
- operating environment assumptions;
- dependency inventory;
- foreseeable misuse/failure modes;
- external partner and validation dependencies.

Gap status:
- use-case-specific hazard analyses: PARTIAL / MUST BE COMPLETED PER DEPLOYMENT.

## MEASURE
Worldshepherd controls:
- Qualification Evidence Record chain:
  requirement -> test -> configuration -> result -> uncertainty -> pass/fail -> provenance -> identified-human review.
- negative/anomalous evidence retention.
- benchmark ledger concept for AI accuracy, calibration, tool use, robustness, memory, long-horizon execution, and software-engineering pass rate.

Minimum evidence required for every promoted capability:
- test identifier;
- environment/configuration digest;
- dataset or input lineage;
- metrics and thresholds;
- uncertainty/error bars where applicable;
- negative evidence;
- reproducibility information;
- software commit;
- human review decision.

Gap status:
- canonical benchmark suite: IN DEVELOPMENT;
- independent external evaluation: NOT YET ESTABLISHED.

## MANAGE
Worldshepherd controls:
- SARA governed workflows and audit records.
- PRIME authorization boundaries.
- ECHO provenance and telemetry lineage.
- OVERWATCH observability/common operating picture.
- fail-closed evidence promotion and explicit supersession states.

Required response controls:
- rollback path;
- bounded automation limits;
- stop/abort condition;
- escalation path to identified human authority;
- incident/evidence preservation;
- versioned mitigation record;
- post-event review.

Gap status:
- organization-wide incident-response exercise tied to AI failures: REQUIRED;
- external red-team/independent assurance: REQUIRED FOR HIGH-CRITICALITY CLAIMS.

## Cross-cutting Worldshepherd rule
Internal implementation is evidence of implementation only. It is not evidence of external safety, certification, operational suitability, regulatory compliance, government authorization, or physical-world performance.

## Immediate engineering work
1. Add machine-readable AI risk/benchmark fields to PRE records.
2. Bind every SARA workflow execution to software/configuration/source digests.
3. Establish benchmark suites for grounding accuracy, calibration, adversarial robustness, tool reliability, long-horizon completion, and memory consistency.
4. Add explicit stop/rollback/escalation evidence to automation workflows.
5. Create a recurring external-assurance ledger for legal review, independent testing, partner validation, and security/compliance review.
6. Re-baseline this document whenever NIST publishes a revised AI RMF or finalized Critical Infrastructure Profile.
