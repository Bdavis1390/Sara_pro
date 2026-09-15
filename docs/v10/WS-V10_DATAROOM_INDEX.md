# WS-V10 — Diligence Data-Room Index

**Status:** INTERNAL DILIGENCE STRUCTURE

This index points to authoritative evidence. It should not duplicate sensitive records unnecessarily or convert unverified statements into facts.

## 1. Corporate / entity / ownership

Required authoritative records:

- legal entity formation/status record;
- ownership/control record;
- authorized signatory record;
- business address/contact record;
- applicable tax/business registration references kept in controlled storage.

**Current V10 state:** OPEN / documentary evidence not yet established in the connected evidence set.

## 2. IP assignments / licenses / OSS

Required:

- founder/contributor/contractor IP assignments;
- repository/code ownership chain;
- material inbound licenses;
- OSS dependency/license inventory;
- restrictions/obligations register.

**Current V10 state:** OPEN.

## 3. Invention / patent / trade-secret register

Required by technology family:

- invention title / family;
- inventor/contributor attribution;
- earliest dated evidence;
- current claims state;
- public disclosure status;
- patent candidate / filed / issued status with authoritative filing evidence;
- trade-secret candidate status and access/custody rule;
- export/publication-review flag where applicable.

Never describe a candidate as filed or issued without authoritative evidence.

## 4. Software architecture / release identities

Authoritative references should include:

- protected `main` release identities;
- SARA / PRIME SENTINEL architecture;
- ECHO persistence/reconciliation architecture;
- exact evaluator source baselines;
- deployment manifests and dependency/environment references.

## 5. Internal engineering evidence

Keep separate from external validation:

- protected CI results;
- CodeQL/security scan results;
- unit/API/integration tests;
- recovery/rollback/restore evidence;
- exact-head commit identities;
- discrepancy and failed-run records.

## 6. Independent external evaluation

Required evidence when obtained:

- evaluating organization;
- evaluator-controlled environment record;
- exact tested SHA;
- evaluator-selected inputs/challenges where applicable;
- artifact hashes;
- scorecard;
- discrepancy register;
- evaluator-owned original record / attestation.

Internal CI must never be filed here as independent reproduction.

## 7. Claims-control / maturity register

Use the established Worldshepherd labels and retain the evidence basis for each promotion:

- PROVEN INTERNALLY
- IMPLEMENTED IN SOFTWARE
- SUPPORTED BY LITERATURE
- SIMULATED ONLY
- HYPOTHESIS
- SPECULATIVE EXTENSION
- REQUIRES LAB VALIDATION
- REQUIRES PARTNER VALIDATION
- REQUIRES LEGAL REVIEW
- NOT CURRENTLY CLAIMED

## 8. Security / compliance / external-gate register

Reference issue #27 and authoritative customer/contract requirements. Separate:

- implemented internal controls;
- scoped compliance preparation;
- external assessment evidence;
- certification/authorization evidence;
- unresolved gaps.

Never infer CMMC, NIST SP 800-171, DFARS, RMF/ATO, clearance, CUI authorization, or other status from CI alone.

## 9. Commercial evidence ledger

Each opportunity/contact should occupy one objective state:

1. identified;
2. contacted;
3. human response;
4. technically qualified;
5. commercial discussion;
6. proposal/SOW issued;
7. terms executed;
8. payment/economic consideration committed;
9. delivery underway;
10. delivered/accepted;
11. repeat/expansion.

Do not count contacted, replied, or proposed work as revenue/backlog.

## 10. Customer / contract records

When they exist:

- NDA / data-rights agreement;
- proposal / SOW;
- executed contract / PO;
- acceptance criteria;
- invoice/payment evidence;
- customer acceptance / discrepancy record.

## 11. Physical R&D evidence

Separate by lane and artifact identity. For each physical artifact retain:

- frozen requirements/hypothesis;
- design/model version;
- fabrication/build provenance;
- calibrated raw measurements;
- uncertainty/error treatment;
- repeatability/retests;
- negative/anomalous evidence;
- simulation-vs-measurement comparison;
- independent/partner-controlled review where obtained.

## 12. Partner / lab validation

Outreach and willingness to discuss are not validation. Retain only objective evidence of:

- agreed test scope;
- partner-controlled or independent execution;
- device/sample identity;
- calibration/measurement method;
- raw or attributable result evidence;
- partner-authored disposition.

## 13. Known risks / blockers / negative evidence

Maintain a first-class register of:

- failed tests;
- unresolved CI/security findings;
- external gate failures;
- rejected hypotheses;
- legal/compliance uncertainty;
- customer objections;
- partner declines;
- fabrication/test failures;
- schedule/cost constraints.

Negative evidence must not be deleted after remediation.

## 14. Valuation bridge

Maintain separately:

- current risk-adjusted internal planning value;
- evidence supporting each asset class;
- explicit overlap/double-counting adjustments;
- execution / validation / concentration discounts;
- milestone-triggered scenarios;
- statement that internal planning value is not an external appraisal.

## V10 pass boundary

This data-room structure supports V10-5 only when the referenced authoritative records are actually present and navigable. The index itself does not close missing corporate, IP, external-validation, paid-customer, or physical-evidence gates.
