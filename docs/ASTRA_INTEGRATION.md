# Worldshepherd Astra Integration

Status: DESIGN/INTEGRATION PROFILE — not production authorization
Date: 2026-09-04
Owner/authority: CRE1AWS
Orchestrator: SARA

## Purpose

Integrate OpenAI GPT-6 Astra as a bounded high-capability solver for Worldshepherd while preserving SARA as the policy, authorization, provenance, and execution authority.

Astra is not granted independent authority to perform network writes, external communications, procurement, deployment, security testing against third-party systems, or physical-control actions.

## Role separation

- **SARA**: authoritative workflow/orchestration layer; enforces authorization, claims-control, evidence capture, rollback, and operator approval.
- **GPT-6 Astra**: solver/research/review node; produces analyses, candidate designs, code, test plans, simulations, counterexamples, and evidence requests.
- **ECHO SENTINEL LINK**: provenance/telemetry record for Astra requests, outputs, tool use, evidence references, configuration, and disposition.
- **PRIME SENTINEL**: policy gate for requested actions and tool access.
- **OVERWATCH**: monitors performance, anomalies, drift, task duration, resource use, and policy events.
- **CRE1AWS**: final authority for consequential external action.

## Priority Worldshepherd uses

1. **Scientific and engineering solver**
   - multiphysics model decomposition
   - materials design and inverse design
   - metasurface/RF control synthesis
   - numerical verification and symbolic checks
   - experiment and coupon-test design
   - uncertainty quantification and disconfirming-evidence search

2. **Software engineering and verification**
   - repository-scale code review
   - test generation
   - architecture refactoring proposals
   - CI failure diagnosis
   - SBOM/provenance validation plans
   - secure configuration review

3. **Predictive Requirements Engine (PRE)**
   - requirement extraction and recurrence analysis
   - requirement-delta generation
   - gap-to-demo planning
   - partner-capability matching
   - evidence-package planning
   - bid-readiness red-team review

4. **Opportunity intelligence**
   - solicitation decomposition
   - compliance matrices
   - technical-volume review
   - partner-vs-prime analysis
   - contradiction and eligibility checks
   - probability calibration support

5. **Claims control / adversarial review**
   - attempt to falsify technical claims
   - distinguish literature support, simulation, implementation, and physical validation
   - flag unsupported extrapolation
   - identify missing measurements, standards, certifications, and legal review

## Default execution policy

Astra starts in `SOLVER_READ_ONLY` mode.

Allowed by default:
- read authorized local/project inputs
- reason over evidence
- generate candidate artifacts
- generate code patches for review
- propose simulations and test plans
- produce structured provenance and confidence records

Disallowed by default:
- network writes
- sending email/messages
- creating external accounts
- publishing
- purchases or financial transactions
- third-party security probing/exploitation
- changing production infrastructure
- changing physical-control parameters on live hardware
- bypassing SARA/PRIME authorization

Any expansion beyond read-only requires an explicit SARA authorization record and must be bounded to the named resource, action, and time window.

## Cybersecurity handling

Because Astra is a cyber-critical-capability model, Worldshepherd treats cyber work as a separate high-risk lane.

Permitted baseline:
- defensive review of Worldshepherd-owned code and configuration
- static analysis
- threat modeling
- patch recommendations
- lab-only tests against explicitly owned/authorized targets

Never inferred from general project authority:
- exploitation of third-party systems
- credential acquisition
- persistence/evasion
- autonomous scanning outside the authorized lab boundary

## Evidence contract

Every Astra task record should include:

- task_id
- timestamp_utc
- requester/authority
- model = `gpt-6-astra`
- mode
- input/evidence references
- allowed tools
- prohibited actions
- output digest
- claims-control labels
- uncertainty/confidence notes
- disconfirming evidence
- human disposition
- follow-on action

## Claims-control rules

Astra output does **not** upgrade maturity by itself.

Use existing Worldshepherd labels, including:
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

Astra may recommend an upgrade; only evidence and the existing approval workflow may perform one.

## Routing policy

Route a task to Astra when one or more of these conditions hold:
- long-horizon/multistep reasoning is the bottleneck
- repository-scale code understanding is required
- deep scientific/mathematical reasoning is required
- a result needs adversarial falsification before promotion
- PRE/opportunity analysis spans many interdependent requirements
- a complex tool workflow benefits from persistent context

Do not route routine low-risk work to Astra merely because it is available.

## First application lanes

### A. Programmable metasurface control
Use Astra to derive and test constrained control laws across RF/material/thermal states, generate null-steering and beamforming test cases, and search for instability/energy-accounting failures before hardware promotion.

### B. WS-AlTi meta-alloy
Use Astra for inverse-design studies, phase/precipitate hypothesis generation, DED process-window optimization, sensitivity studies, coupon-matrix reduction, and falsification of claimed advantages before valuation upgrades.

### C. SARA/PRE
Use Astra to produce requirement-delta records, evidence matrices, partner gaps, and readiness-horizon actions while preserving source provenance and distinction between confirmed demand, emerging demand, and Worldshepherd forecast.

### D. Repository assurance
Use Astra to review SARA changes, generate tests, and identify contradictions between implementation, docs, CI, and claimed readiness.

## Promotion gates

Astra integration is not operationally complete until:

1. model access is available to the chosen runtime/API account;
2. credentials are stored outside the repository;
3. SARA adapter is implemented;
4. request/response provenance is logged;
5. read-only tests pass;
6. timeout/cancellation/rollback behavior is verified;
7. tool allow-list enforcement is verified;
8. claims-control tagging is verified;
9. cyber-specific boundary tests pass;
10. CRE1AWS approves any mode beyond `SOLVER_READ_ONLY`.

## Non-negotiable architectural principle

**Astra proposes and solves; SARA authorizes and records; CRE1AWS controls consequential action.**
