# Worldshepherd Claims and Evidence Policy

## Purpose

Worldshepherd covers software, systems engineering, autonomy, cyber/provenance, sensing, materials, RF, aerospace, space, energy, and other research domains. That breadth is useful only if maturity is explicit.

This document is the public-repository rule for separating **what exists**, **what has been tested**, **what is supported by external evidence**, and **what is still a hypothesis**.

## Canonical claim states

Use one or more of the following labels on substantive technical claims:

| State | Meaning |
|---|---|
| `PROVEN INTERNALLY` | Reproducible internal evidence exists for the bounded claim and configuration stated. |
| `IMPLEMENTED IN SOFTWARE` | Code/configuration implements the stated behavior; this does not establish physical-system performance. |
| `SUPPORTED BY LITERATURE` | Credible external technical literature supports the scientific/engineering basis. |
| `SIMULATED ONLY` | Evidence is currently simulation/model output, not physical demonstration. |
| `HYPOTHESIS` | Testable proposed explanation/design not yet adequately validated. |
| `SPECULATIVE EXTENSION` | Forward-looking extrapolation beyond current evidence. |
| `REQUIRES LAB VALIDATION` | Physical/laboratory evidence is required before the claim can advance. |
| `REQUIRES PARTNER VALIDATION` | External partner/integration evidence is required. |
| `REQUIRES LEGAL REVIEW` | Release, licensing, regulatory, export, contractual, or IP review is required. |
| `NOT CURRENTLY CLAIMED` | Explicitly outside the present claim boundary. |

Where a schema requires it, `NOT_APPLICABLE` may be used for fields rather than capability claims.

## Evidence chain

For qualification-grade work, prefer the chain:

`requirement → test → configuration → result → uncertainty → pass/fail → provenance → identified-human review`

Every major result should make enough of that chain visible to allow another reviewer to understand what was actually established.

## Fail-closed rules

1. **Prediction never upgrades capability maturity.** Forecast demand may justify preparation, not readiness claims.
2. **Software does not prove hardware performance.** A controller, digital twin, model, or workflow implementation cannot establish thrust, strength, RF performance, survivability, sensor accuracy, or other physical performance without appropriate evidence.
3. **Simulation is not demonstration.** Simulation results remain `SIMULATED ONLY` until validated against suitable physical or reference data.
4. **A paper is not a prototype.** Literature support establishes plausibility or prior evidence, not Worldshepherd implementation.
5. **Outreach is not partner validation.** Emails, meetings, brochures, or interest do not become `REQUIRES PARTNER VALIDATION` evidence until the partner actually evaluates the relevant claim.
6. **Internal controls are not certification.** Internal security controls do not establish CMMC certification, NIST 800-171 conformity, DFARS satisfaction, clearance, government authorization, or operational accreditation.
7. **Negative evidence is retained.** Failed tests, anomalies, contradictory literature, and uncertainty are part of the evidence record.
8. **Configuration matters.** Results apply to the configuration tested; scope expansion requires justification or new evidence.
9. **Public release is a separate gate.** Evidence may be technically valid but inappropriate for a public repository.

## Recommended claim block

Use this compact block in research documents and PRs:

```yaml
claim:
  statement: "Precisely bounded technical statement"
  status:
    - IMPLEMENTED IN SOFTWARE
    - REQUIRES PARTNER VALIDATION
  evidence:
    - "path/to/test-or-report"
  configuration: "version / commit / test setup"
  limitations:
    - "Known limitation or missing evidence"
  next_gate: "Objective pass/fail validation step"
```

## Physical-science work

For materials, propulsion, RF/metasurfaces, energy systems, sensing, and other physical domains, a credible advancement path normally includes:

1. governing physics and assumptions;
2. literature/prior-art review;
3. model/simulation with uncertainty bounds;
4. test article or coupon definition;
5. instrumentation and calibration plan;
6. predeclared pass/fail criteria;
7. independent or partner replication where material;
8. configuration-controlled evidence package.

Until those gates are satisfied, use the corresponding `SUPPORTED BY LITERATURE`, `SIMULATED ONLY`, `HYPOTHESIS`, `REQUIRES LAB VALIDATION`, or `REQUIRES PARTNER VALIDATION` states.

## Software work

For software and governance components, credible evidence may include:

- source code tied to a commit;
- unit/integration tests;
- CI results;
- interface/schema validation;
- audit/provenance output;
- permission-boundary tests;
- recovery/rollback drills;
- security scanning;
- reproducible deployment instructions.

A passing software test supports only the behavior exercised by that test.

## Relationship to existing repository policy

This document is the human-readable top-level policy. Existing artifacts such as:

- `PRE_REQUIREMENT_DELTA_SCHEMA_V1.md`
- `WS_CLAIMS_BOUNDARY_NORMALIZATION_2026-09-01.md`

remain authoritative for their specific workflows and should continue to fail closed against false-readiness claims.
