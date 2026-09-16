# Worldshepherd Operating Model

## Purpose

This repository is the durable system of record for Worldshepherd software, governance, evidence, opportunity preparation, engineering validation, and operational continuity. Slack is a coordination surface; GitHub is where durable technical and governance state should be anchored.

## Control doctrine

`AI proposes → human approves → automation remains bounded → actions and evidence are logged.`

Authority model:

- **CRE1AWS** — creator / architect / human approval authority.
- **SSPADAWANZZ** — admin-operator / bounded execution.
- **SARA** — governed workflow orchestration.
- **PRIME SENTINEL** — policy and authorization.
- **ECHO SENTINEL LINK** — telemetry, provenance, and evidence lineage.
- **OVERWATCH** — observability and common operating picture.
- **PRE** — Predictive Requirements Engine for recurring/emerging demand and reusable-readiness preparation.

## Claims-control states

Use one or more on consequential technical or commercial claims:

- `PROVEN INTERNALLY`
- `IMPLEMENTED IN SOFTWARE`
- `SUPPORTED BY LITERATURE`
- `SIMULATED ONLY`
- `HYPOTHESIS`
- `SPECULATIVE EXTENSION`
- `REQUIRES LAB VALIDATION`
- `REQUIRES PARTNER VALIDATION`
- `REQUIRES LEGAL REVIEW`
- `NOT CURRENTLY CLAIMED`

Conversation ideas, simulations, news, outreach, historical assertions, political interest, or partner interest do not become verified physical capability without reproducible evidence.

## Portfolio lanes

| Lane | Repository purpose |
|---|---|
| COMMAND | architecture, doctrine, priorities, approvals, cross-lane decisions |
| OPPORTUNITY / PRE | solicitations, requirement deltas, capture, reusable readiness |
| TEAMING | partner diligence, division of labor, validation partners, commitment gates |
| OUTREACH | external communications state and unresolved follow-up |
| SARA | SARA/PRIME/ECHO/OVERWATCH implementation, integration, tests, deployment |
| EVIDENCE | test plans, results, provenance, promotion/demotion decisions |
| AI GOVERNANCE | NIST/OCSF/trustworthy-AI work, evaluation, agent governance |
| AUTONOMY / ROBOTICS | drones, humanoids, companion systems, maritime/ground/air autonomy |
| RF / SPECTRUM | radar, RF, antennas, metasurfaces, distributed sensing, spectrum |
| MATERIALS / MFG | Al–Ti work, DED/AM, electric-machine materials, qualification |
| PROPULSION / SPACE | propulsion, plasma, energy, space systems and environmental survivability |
| CYBER / PQC | defensive cyber, identity, provenance, SBOM, PQC migration |
| RESEARCH WATCH | external technical developments and disconfirming evidence |
| COMMERCIALIZATION | productization, licensing, valuation, manufacturing transition, revenue |

## Work-item standard

Use this shape for consequential issues and project records:

`[LANE][P0-P3][STATUS] Title`

Record:

1. Owner
2. Evidence class
3. Decision gate
4. Source / provenance
5. Next action
6. Due date if applicable
7. External dependency if applicable
8. Completion evidence

Priority:

- `P0` — deadline / failure risk
- `P1` — high-value active
- `P2` — important, non-urgent
- `P3` — backlog

Lifecycle:

`INBOX → TRIAGE → ACTIVE → WAITING EXTERNAL / NEEDS APPROVAL / BLOCKED → VALIDATED → COMPLETED → ARCHIVED`

Decision gates:

`CRE1AWS APPROVAL` · `SSPADAWANZZ EXECUTION` · `EXTERNAL RESPONSE` · `EVIDENCE VALIDATION` · `LEGAL REVIEW` · `NO GATE`

## Technical readiness ladder

Physical concepts advance only through measurable gates:

`requirements → analytical model → simulation → bench/coupon → subsystem → integrated demonstration → independent/partner validation → qualification/production transition`

A failure remains a failure until corrected and rerun. Partner performance remains partner performance unless Worldshepherd independently reproduces or integrates and validates it.

## Repository operating rule

Every Slack thread, external message, or research note that changes technical readiness, opportunity posture, partner state, architecture, or public claims should resolve to a durable GitHub artifact: issue, PR, test record, evidence package, or canonical document.

GitHub should remain usable if Slack is unavailable.