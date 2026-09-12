# Worldshepherd QCRYPTO Independent Review Protocol

## Purpose

This protocol gives an external reviewer a bounded way to evaluate the quality of the Worldshepherd QCRYPTO research-engineering process without requiring trust in biography, promotional claims, or unpublished capability assertions.

The review target is the methodology: provenance, evidence separation, claims control, reproducibility, and migration-readiness reasoning.

## Review questions

A reviewer should determine whether the repository:

1. Separates published research, measured hardware results, standards guidance, vendor roadmaps, operational migration evidence, and internal software validation.
2. Preserves source provenance and does not relabel third-party findings as Worldshepherd discoveries.
3. Prevents forward-looking or partial evidence from being promoted into claims of present operational capability.
4. Distinguishes implementation evidence from certification, endorsement, independent validation, adoption, or field deployment.
5. Treats post-quantum migration as a systems problem involving inventory, cryptographic agility, compatibility, governance, and recovery rather than a single-algorithm substitution.
6. Produces reproducible test results at an exact repository commit.
7. States limitations and excluded claims clearly enough that a third party can challenge them.

## Reproduction procedure

Checkout the exact review commit, inspect the QCRYPTO evidence and claims-control files, and run the repository's QCRYPTO Risk Gate or its equivalent local test commands. Record the commit SHA, test outcome, environment, and any discrepancies.

The reviewer should fail the review if source categories are conflated, unsupported claims are promoted, the test suite does not reproduce, or the documentation implies external endorsement that has not occurred.

## Evidence axes

The strongest process warrant requires evidence across independent axes rather than repeated citations from one source family:

- peer-reviewed scientific analysis;
- measured quantum-hardware or error-correction evidence;
- authoritative standards or migration guidance;
- operational post-quantum deployment evidence;
- reproducible internal claims-control software.

No one axis substitutes for the others.

## Claims boundary

A successful review can support statements such as:

- the analysis is grounded in cited external literature and primary sources;
- the claims-control logic is implemented in software;
- the tested repository behavior is internally reproducible;
- the migration analysis reflects standards guidance and real deployment evidence;
- the engineering process is suitable for further external technical review.

A successful review does not by itself establish original authorship of external scientific findings, third-party certification, endorsement, adoption, possession of advanced quantum hardware, or independent validation unless the reviewer explicitly performs and documents such validation.

## Attributable review receipt

Use `review_receipt_template.json` to record the reviewer identity or organization, exact commit, environment, date, pass/fail results, discrepancies, supported claims, excluded claims, and an attributable review record. `independent_review_guard.py` defines the conservative classification rule for that receipt.

An incomplete, anonymous, unattributed, or partially failed receipt must not be represented as independent validation. A complete receipt may support the narrower label `INDEPENDENTLY REPRODUCED — METHODOLOGY/SOFTWARE BEHAVIOR ONLY`; certification, endorsement, adoption, scientific originality, and external validation of broader Worldshepherd capability remain separate claims requiring separate evidence.

## Reviewer output

A useful independent review should publish:

- reviewer identity or organization;
- exact commit reviewed;
- reproduction environment;
- pass/fail by review question;
- discrepancies or objections;
- claims the reviewer believes are supported;
- claims the reviewer believes must remain excluded;
- date and signed or attributable review record.

## Current internal status

Worldshepherd may describe the QCRYPTO implementation as internally reproducible only when the exact branch head has a successful validation run. External validation begins only when an independent reviewer reproduces the work and records that result.
