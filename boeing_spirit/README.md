# Boeing–Spirit Quality Integration Assurance (BS-QIA)

## Purpose

BS-QIA is a bounded Worldshepherd/SARA solution lane for **supplier-quality, configuration, APQP/PPAP, product/process verification, corrective-action, and shipment-readiness evidence** across a Boeing/Spirit-like aerostructures production environment.

It is deliberately **not** a claim that Worldshepherd can fix Boeing, reverse unfavorable contract economics, certify an aircraft, replace Boeing/Spirit MES/QMS/PLM/SAP systems, or achieve a 98.7% real-world problem-resolution probability today.

The current lane converts public problem signals into executable, falsifiable assurance controls and a fail-closed external-contact gate.

## Public problem signals used to derive the initial requirements

Current Boeing/Spirit Commercial quality postings in Wichita identify the following concrete work:

- APQP/PPAP execution for new product launches, work transfers, and process changes;
- Process Flow, PFMEA, Control Plan, SPC, MSA, and FAI evidence;
- supplier QMS, contract/customer/regulatory requirement compliance;
- Notifications of Escapement and 8D closure;
- validation of supplier planning against engineering requirements;
- process and product audits and RCCA closure;
- SAP/MES use in supplier product/process verification;
- BOM/build-record/configuration verification and engineering-change control;
- closure of open work before shipping and complete shipment documentation.

These are **public demand signals**, not proof that Boeing would adopt BS-QIA.

## Worldshepherd mapping

```text
Existing SAP / MES / QMS / PLM / supplier records
        |
        v
ECHO SENTINEL LINK
  source identity, timestamps, digests, provenance
        |
        v
SARA Evidence Graph
  requirement -> plan -> process -> inspection -> NCR/RCCA -> release lineage
        |
        v
PRIME SENTINEL release gates
  fail closed on missing/contradictory/expired evidence
        |
        +---------------------+
        |                     |
        v                     v
OVERWATCH                Qualification package
trend / escape /         replayable evidence,
config / APQP debt       uncertainty, exceptions
```

PRE remains upstream: it converts customer/engineering/contract deltas into controlled requirement records. BS-QIA does not infer that an undocumented requirement has been satisfied.

## Active solution modules

### 1. Supplier Requirement-to-Plan Reconciler
Compares supplier planning against controlled engineering/customer/purchase-contract requirements. Missing flow-down or revision mismatch is a release-blocking finding.

### 2. APQP/PPAP Evidence Compiler
Requires evidence for Process Flow, PFMEA, Control Plan, SPC, MSA, and FAI where applicable. It records missing evidence explicitly rather than treating absence as success.

### 3. Configuration & Build Record Guard
Checks engineering/planning/BOM revisions, unresolved open work, build-record completeness, and shipment documentation before release.

### 4. Escape / RCCA Closure Graph
Links nonconformance or Notification-of-Escapement records to containment, root cause, corrective action, effectiveness evidence, and closure approval. An open required RCCA remains visible and can block release.

### 5. Process & Product Verification Gate
Produces a machine-readable audit result for supplier process/product verification and retains the requirement/evidence lineage for replay.

### 6. Evidence-Debt & Exception Monitor
OVERWATCH can rank high-consequence records with weak, stale, contradictory, or missing evidence. Schedule pressure is not accepted as a substitute for evidence.

## Current executable scope

`quality_assurance.py` implements a zero-dependency rules engine for synthetic records. It checks:

1. source/provenance completeness;
2. requirement flow-down completeness;
3. engineering/planning/configuration revision consistency;
4. APQP evidence completeness;
5. FAI status;
6. supplier QMS approval;
7. special-process qualification;
8. calibration validity;
9. process/product audit findings;
10. escape/RCCA closure;
11. open work before shipment;
12. shipment-document completeness;
13. unauthorized schedule/production override attempts.

The synthetic fixture is for software behavior only. A perfect synthetic score does **not** promote external readiness.

## 98.7% external-contact rule

No Boeing/Spirit outreach may claim a >=98.7% chance of solving the scoped problem until `contact_gate.py` returns `GO_CONTACT` from retained external evidence.

The gate requires, at minimum:

- a narrowly defined outcome metric and scope;
- production-representative external data, not synthetic data;
- independent validation/review;
- multi-condition / stratified failure-mode coverage;
- zero unresolved safety-critical false negatives;
- a one-sided 95% exact lower confidence bound of at least 0.987 for the predeclared success metric;
- customer-representative workflow/interface validation;
- provenance/custody digest and reproducible package;
- completed security/data-rights/export-control/legal review appropriate to the pilot;
- explicit human acceptance.

For the special case of **zero failures**, at least 229 independent Bernoulli trials are needed before the one-sided 95% exact lower bound can reach 0.987. This statistical condition alone is not sufficient: representativeness, independence, stratification, and the other gates above still apply.

Until those conditions are met, the contact decision remains `NO_CONTACT` and any stated probability remains `NOT_ESTIMABLE_FROM_CURRENT_EVIDENCE`.

## Pilot shape once the evidence gate is earned

The initial external proposition should be a **bounded, non-production shadow-mode pilot**, not a claim to replace Boeing systems:

1. ingest a sanitized/export-controlled representative record set;
2. replay requirement/configuration/APQP/RCCA lineage without changing production systems;
3. compare BS-QIA findings to authoritative human/QMS disposition;
4. measure recall, false-positive burden, time-to-detect, evidence completeness, and replayability;
5. red-team revision changes, missing flow-down, expired evidence, open RCCA, and schedule-bypass attempts;
6. independently reproduce the result;
7. only then consider a controlled integration pilot.

## Claims boundary

**Current status: INTERNAL SOFTWARE / SYNTHETIC ASSURANCE PROTOTYPE.**

No Boeing or Spirit validation, supplier approval, FAA approval, AS9100/AS9102/AS9145 conformity, CMMC/NIST conformity, production integration, quality escape reduction, financial-loss reduction, certification, or aircraft airworthiness claim is made.