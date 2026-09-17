# Worldshepherd Partner Use-Case Pilot

Worldshepherd is inviting technical teams, operators, evaluators, manufacturers, integrators, and research partners to bring a **real, bounded workflow** that is difficult to trust, govern, reproduce, or audit.

The objective is not a sales demo. The objective is to turn one partner-supplied use case into a reproducible assurance exercise with explicit authority boundaries, measurable pass/fail criteria, retained negative evidence, and a claims-controlled result.

## What Worldshepherd currently provides

The current SARA/PRIME/ECHO/OVERWATCH work is an implemented software foundation for governed workflow orchestration and evidence handling. Current repository capabilities include authenticated role separation, protected registry state, durable audit evidence, bounded event-outbox recovery, PRIME authorization/passport controls, restriction observability, request-size and storage safety controls, and evaluator-oriented regression/evidence workflows.

Worldshepherd does **not** claim certification, government acceptance, independent validation, customer adoption, model superiority, or operational effectiveness unless and until the corresponding evidence exists.

## Bring us one hard use case

A strong pilot candidate has all of the following:

- a concrete decision, action, or workflow that should not execute without defined authority;
- at least one meaningful failure mode, misuse case, or recovery condition;
- an observable success criterion;
- evidence that can be collected without exposing protected information;
- a partner who can judge whether the result is operationally useful.

## Pilot tracks

### 1. Governed AI / agent workflow

Examples: tool-using agents, approval-gated automation, human-in-the-loop decisions, policy-constrained workflows, sensitive action routing, or multi-agent handoffs.

Worldshepherd contribution: authority gates, bounded execution, provenance, rejection evidence, recovery tests, and evaluator-readable evidence packages.

### 2. Software assurance / adversarial evaluation

Examples: a known-fixed defect, a security-sensitive workflow, a regression surface, a release candidate, or a control that should fail closed.

Worldshepherd contribution: exact-release binding, challenge definition, negative tests, clean-environment reproduction, discrepancy retention, and regression evidence.

### 3. Supply-chain / manufacturing provenance

Examples: component identity, process-step evidence, custody changes, inspection results, software/firmware provenance, traceability handoffs, or requalification after mission/field use.

Worldshepherd contribution: signed or attributable evidence references, protected state transitions, custody/requalification logic, traceability events, and claims-controlled status reporting.

### 4. Mission / industrial operations

Examples: autonomous logistics, maritime/robotic operations, maintenance decisions, resilient communications workflows, fielded-system status, or operator authorization chains.

Worldshepherd contribution: policy/authorization separation, local evidence capture, bounded automation, degraded-mode behavior, operator-visible status, and post-event reconstruction.

## What the partner supplies

For a useful pilot, the partner should provide:

1. the workflow or decision to test;
2. the actor(s) and authority boundaries;
3. the most important failure or misuse cases;
4. the evidence the partner would need to trust the result;
5. one or more measurable acceptance criteria;
6. environmental or integration constraints;
7. what may and may not be disclosed publicly.

A sanitized or synthetic workflow is acceptable when real data is sensitive.

## What Worldshepherd returns

A completed pilot should aim to produce:

- a scoped use-case specification;
- an authority and failure-mode map;
- an executable or reproducible challenge set where feasible;
- pass/fail results with negative evidence retained;
- provenance/evidence records;
- unresolved discrepancies and known limitations;
- a claims-control classification for every material conclusion;
- a partner disposition: useful, not useful, incomplete, or requires further validation.

## Claims-control rules

Every material result is classified using Worldshepherd claims-control labels such as:

- `PROVEN INTERNALLY`
- `IMPLEMENTED IN SOFTWARE`
- `SUPPORTED BY LITERATURE`
- `SIMULATED ONLY`
- `HYPOTHESIS`
- `REQUIRES LAB VALIDATION`
- `REQUIRES PARTNER VALIDATION`
- `REQUIRES LEGAL REVIEW`
- `NOT CURRENTLY CLAIMED`

Partner criticism and failed tests are evidence and are not deleted to preserve a favorable narrative.

## Sensitive-information boundary

Do **not** put classified information, CUI, export-controlled technical data, credentials, proprietary source code, regulated personal data, protected health information, or other confidential material into a public GitHub issue.

Use a sanitized description for initial intake. Sensitive follow-on work requires an appropriate private channel and authorization boundary.

## How to submit a use case

Open a new GitHub issue using the **Partner use-case pilot** template and provide only information safe for public disclosure.

Worldshepherd will first determine whether the use case is technically bounded and measurable. Acceptance into a pilot is not a claim that the use case will succeed.

## What success means

The strongest outcome is not a testimonial. It is an externally supplied problem for which another party can inspect the assumptions, reproduce or challenge the evidence, and decide whether the Worldshepherd controls materially improve trust, accountability, or operational assurance.
