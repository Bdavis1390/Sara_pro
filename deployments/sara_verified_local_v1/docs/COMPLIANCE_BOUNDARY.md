# Worldshepherd SARA / PRE Compliance Boundary

## Status vocabulary

This project distinguishes **internal software conformance** from **external compliance, certification, eligibility, or operational validation**.

A green CI run means the repository's bounded software/test/deployment gate passed for the tested commit. It does not mean any external framework has been certified.

## Internally testable and currently gateable

The repository can directly test and retain evidence for:

- Python compilation and unit/API tests;
- deterministic frozen-fixture qualification behavior;
- claims-boundary assertions;
- local ECHO-style digest verification;
- local configuration and registry custody behavior;
- fail-closed evidence rules;
- Docker Compose syntax and ephemeral local deployment;
- local health/readiness/self-test behavior;
- bounded authorization/policy logic;
- synthetic DDIL fault and reconciliation behavior;
- internal software provenance records;
- machine-readable readiness and PRE horizon records.

These are software conformance claims only unless a specific evidence package establishes more.

## External gates that cannot be self-certified by this repository

| Gate | Current default status | Evidence required to close |
|---|---|---|
| CMMC | NOT CERTIFIED / UNVERIFIED | Applicable CMMC assessment/certificate or authoritative program evidence |
| NIST SP 800-171 organizational conformity | UNVERIFIED | scoped system boundary, SSP, control implementation evidence, assessment results and required POA&M/SPR S evidence |
| SPRS | UNVERIFIED | authoritative SPRS assessment/score evidence when applicable |
| SAM / UEI / CAGE | UNVERIFIED in software | authoritative entity records |
| SBIR/STTR eligibility | UNVERIFIED | formation, ownership/control, size, registry, PI and solicitation-specific documentary evidence |
| ITAR/EAR | REQUIRES LEGAL/EXPORT REVIEW | export classification, access/control analysis and required registrations/authorizations |
| FOCI / foreign influence constraints | UNVERIFIED / REQUIRES REVIEW | ownership/control/influence analysis under applicable solicitation/security rules |
| Security clearance / facility clearance | NOT CLAIMED | authoritative personnel/facility clearance evidence |
| Government ATO / RMF authorization | NOT CLAIMED | customer-authorized RMF package and authorization decision |
| Government interoperability certification | NOT CLAIMED | designated authority/test-facility conformance evidence |
| Physical hardware performance | NOT CLAIMED unless separate evidence exists | controlled physical test with configuration, instrumentation, calibration and retained results |
| Operational effectiveness | NOT CLAIMED | representative operational evaluation with agreed metrics and customer/independent evidence |
| Qualified aerospace/material process | NOT CLAIMED | coupon/process qualification, repeatability, standards/certification evidence and appropriate authority acceptance |

## Claims-control rule

Do not use `PASS`, `green`, `verified`, `qualified`, `compliant`, or similar language without naming the scope. Preferred forms are:

- `INTERNALLY TESTED SOFTWARE BEHAVIOR: PASS`
- `CI/LOCAL DEPLOYMENT GATE: PASS`
- `SYNTHETIC QUALIFICATION FIXTURE: PASS`
- `EXTERNAL CMMC STATUS: UNVERIFIED`
- `PHYSICAL PERFORMANCE: REQUIRES LAB/PARTNER VALIDATION`

## Release usability gate

A commit may be called **internally usable** when all of the following hold for that commit:

1. required GitHub Actions gate is green;
2. `pytest` passes;
3. full-bloom qualification compiler exits zero;
4. required qualification outputs are generated;
5. ECHO-style custody verification is all true;
6. Docker Compose validates;
7. ephemeral deployment verifier passes;
8. documented CLI/quick-start path matches the tested path;
9. no known high-severity unresolved defect invalidates the tested scope.

This is an internal engineering release criterion only. External contractual or regulatory compliance remains governed by the applicable authority and evidence package.
