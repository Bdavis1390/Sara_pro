# WS-PILOT-01 — Governed Evidence & Mission-Assurance Pilot

**Status:** INTERNAL COMMERCIAL PACKAGE — REVIEW BEFORE EXTERNAL USE

## Buyer problem

High-consequence engineering and autonomy teams often need to prove, after the fact and under scrutiny:

- who authorized a decision or change;
- which exact inputs and configuration produced it;
- whether evidence was altered, duplicated, replayed, or lost;
- whether prohibited or unauthorized actions failed closed;
- what occurred during restart, recovery, or degraded conditions;
- whether a result can be reproduced and independently reviewed.

## Pilot objective

Apply Worldshepherd's governed software-assurance stack to one bounded customer workflow and produce an evidence package that makes those questions answerable without requiring the customer to adopt the entire Worldshepherd portfolio.

## In-scope capabilities

- evidence provenance and lineage;
- role and authorization separation;
- configuration / change custody;
- integrity and replay/duplicate handling;
- identified-human approval gates where required;
- discrepancy and negative-result retention;
- restart / recovery evidence;
- audit and decision traceability;
- bounded reproducibility of deterministic behavior.

## Current software basis

The current protected mainline includes SARA / PRIME SENTINEL and merged ECHO persistence/reconciliation software. This is implemented software evidence only; customer acceptance, production certification, compliance, and operational effectiveness require separate evidence.

## Explicit exclusions

Unless separately scoped and authorized, Pilot-01 does not include:

- classified, CUI, CDI, export-controlled, or customer-restricted data;
- consequential-action autonomy authority;
- physical-platform performance validation;
- CMMC, NIST SP 800-171, DFARS, RMF/ATO, or other certification claims;
- partner-specific proprietary interfaces without authoritative documentation and approval;
- transfer of enabling Worldshepherd IP beyond agreed deliverables.

## Customer inputs

Customer provides:

1. one bounded workflow or representative synthetic workflow;
2. roles / approval rules;
3. allowed and prohibited actions;
4. configuration/change events to govern;
5. expected outputs or acceptance conditions;
6. agreed failure/recovery cases;
7. approved data-classification boundary;
8. a technical counterpart able to confirm results.

## Worldshepherd deliverables

- pilot architecture and scope map;
- governed input/configuration record;
- authorization and approval evidence;
- provenance / integrity records;
- replay, malformed-input, and negative-case evidence;
- restart/recovery evidence where applicable;
- discrepancy register;
- reproducibility package for deterministic portions;
- final claims-bounded pilot report.

## Default acceptance criteria

Pilot passes only if the agreed workflow demonstrates all applicable criteria:

- exact input/configuration identity is retained;
- authorized and unauthorized actions are distinguishable;
- prohibited actions fail closed;
- replay/duplicate conditions are detected or safely handled;
- malformed/tampered evidence is not silently accepted;
- restart/recovery behavior leaves inspectable evidence;
- required human approval is retained;
- deterministic results are reproducible from frozen inputs where expected;
- discrepancies and failed cases remain visible after remediation.

## Planning commercial bands

These are internal planning bands, not claimed market transactions:

- Evaluation pilot: **$25K–$50K**
- Operational pilot: **$75K–$150K**
- Enterprise/mission pilot: **$150K–$350K+**

Final price depends on integration effort, data boundary, deployment environment, customer support burden, evidence-retention requirements, and contractual obligations.

## Suggested milestone structure

1. **M0 — scope / data / authority freeze**
2. **M1 — baseline integration**
3. **M2 — nominal workflow evidence**
4. **M3 — adversarial / failure / recovery cases**
5. **M4 — customer-observed acceptance run**
6. **M5 — final evidence package and discrepancy disposition**

## V10 commercial evidence rule

This document does not close V10-4. V10-4 closes only when a meaningful third party executes commercial terms and commits real economic consideration for the bounded capability. Outreach, meetings, interest, proposals, drafts, and verbal enthusiasm do not count as paid customer evidence.
