# Worldshepherd Capture Engine v1.1

Status: IMPLEMENTED AS GOVERNANCE / ROUTING / READINESS ARCHITECTURE

Date: 2026-09-12

## Purpose

Convert external opportunities into reusable Worldshepherd capability development instead of isolated proposal work.

Operating chain:

`discover -> verify -> score -> route -> evidence-gap -> build/test -> package -> human approval -> submit/partner -> transition -> reuse`

## Core rule

Opportunity facts and Worldshepherd capability claims remain independent.

No solicitation language, award value, partner brochure, market demand, or predictive signal may upgrade Worldshepherd maturity. Physical performance requires physical evidence. Security/compliance/clearance status must be independently verified.

## Capture tiers

- TIER 0: unusually high-value/high-leverage; automatic escalation.
- TIER 1: high-fit actionable opportunity with manageable gaps.
- TIER 2: useful but material maturation/teaming required.
- TIER 3: strategic preparation/future demand.
- TIER 4: remote/speculative; monitor only.

## Routing

Every opportunity must resolve to one state:

- PRIME — Worldshepherd can credibly lead if eligibility/evidence pass.
- PARTNER — pursue through a qualified partner where hardware, domain, clearance, certification, production, or test evidence is missing.
- PREPARE — build reusable evidence before the opportunity becomes directly actionable.
- NO_BID — consciously decline while preserving the reason.

## Scoring

100-point scale:

- Technical fit: 20
- Evidence maturity: 15
- Eligibility: 15
- Team probability: 10
- Gap-to-demo: 10
- Award value: 10
- Strategic value: 10
- Follow-on potential: 5
- Deadline feasibility: 5

Tier is not mechanically determined by score alone; acquisition-channel leverage, recurring ordering access, or exceptional transition pathways can independently justify Tier 0.

## Productization architecture

### SARA
Governed workflow/orchestration. Converts requirements and evidence into controlled processes.

### PRIME
Authorization, policy, claims-control, decision gates, and human approval.

### ECHO
Telemetry, evidence lineage, provenance, configuration custody, and event records.

### OVERWATCH
Operational picture, health/status, decision support, alerts, and risk presentation.

### PRE
Requirement deltas, recurring demand extraction, forecast horizons, readiness backlog, and future-program mapping.

### Qualification Accelerator
Canonical chain:

`requirement -> test -> configuration -> result -> uncertainty -> pass/fail -> provenance -> identified-human review`

### Supply-Chain Illumination
Multi-tier supplier/component/software/material lineage, risk, alternate-source qualification, mitigation tracking, and corrective-action closure.

### Digital-Twin Assurance
Configuration-custodied digital twins, CBM+, explainability, model-evidence linkage, uncertainty, and sustainment decisions.

### DDIL Mission Mesh
Degraded-state orchestration, bounded autonomy, resilient mission-data workflows, recoverability, and evidence preservation.

## Cross-program readiness backlog

These upgrades are reusable across Army, Navy, Air/Space Force, MDA, SDA, DIU, CDAO, DOE and prime-partner routes:

1. NIST 800-171 / CMMC gap assessment (status must remain unclaimed until verified).
2. SBOM and software provenance.
3. MOSA/open-API adapter pack.
4. DDIL degraded-state test harness.
5. Digital-twin evidence adapter.
6. PNT/APNT adapter.
7. Sensor-fusion provenance adapter.
8. Signer-ready decision-package generator.
9. Partner / clearance / certification gate registry.
10. Qualification evidence store.

## Current Tier-0 convergence

The current live market is converging on several repeated requirements:

- governed agentic AI with human control;
- signer-ready auditable decisions;
- digital engineering / SysML / MBSE interoperability;
- provenance and traceability;
- edge and DDIL operation;
- MOSA/open interfaces;
- sensor/data fusion with confidence;
- resilient PNT and C2;
- digital twins / CBM+;
- supply-chain visibility and qualification;
- rapid commercial/prototype acquisition paths.

This convergence means Worldshepherd should not create separate architectures for each opportunity. The same evidence-gated core should be adapted through mission-specific interface packs.

## Immediate mission packs

### Decision Intelligence Pack
Target: Army Agentic-AI, Tradewinds, acquisition decision support.

Deliverables:
- schema-driven decision object;
- evidence/assumption graph;
- bounded agent workflow;
- human signer gate;
- reproducibility manifest;
- decision refresh when evidence changes.

### Space / PNT Mission Pack
Target: SDA STEC, GPS/PNT opportunities, MDA concepts.

Deliverables:
- PNT/APNT adapter;
- telemetry provenance;
- degraded-mode state machine;
- confidence and uncertainty representation;
- battle-management/C2 interface abstraction;
- simulation-first validation.

### Maritime Sustainment Pack
Target: NAVAIR CBM+, ONR/NAVSEA/NAVWAR routes.

Deliverables:
- digital-twin evidence adapter;
- condition-monitoring ingestion;
- explainable diagnostics/prognostics;
- DDIL synchronization;
- configuration custody;
- maintenance decision package.

### Multi-INT / Sensor Fusion Pack
Target: DIU Space Threat, distributed sensing, RF/spectrum, maritime awareness.

Deliverables:
- multi-source ingest adapters;
- source confidence and provenance;
- entity/track fusion abstraction;
- contradictory-evidence handling;
- operator-facing uncertainty;
- machine-to-machine API.

## Fail-closed capture rules

1. Missing authoritative source -> cannot be Tier 0 based on opportunity facts alone.
2. Missing eligibility evidence -> PRIME remains conditional.
3. Missing physical validation -> physical capability remains unclaimed.
4. Missing clearance/certification -> route to PARTNER or PREPARE.
5. Direct-to-Phase-II -> feasibility evidence must be audited before PRIME routing.
6. Prediction -> preparation only; never capability maturity.
7. Negative evidence is retained and can lower capture score.
8. External submission, outreach, signature, spending, paid membership, compliance certification, and binding commitments require identified-human authorization.

## Repository integration

Machine-readable policy: `config/worldshepherd_capture_engine_v1_1.json`

Seed Tier-0 ledger: `config/worldshepherd_tier0_seed_2026-09-12.json`

Existing PRE Requirement Delta schema remains authoritative for requirement-level evidence separation. Capture Engine records should reference PRE Requirement Delta IDs whenever a live opportunity creates or confirms a reusable requirement.

## Advancement criterion

An opportunity only counts as advancing Worldshepherd if at least one of these improves:

- verified capability evidence;
- reusable software module;
- interface/adaptor coverage;
- compliance/readiness evidence;
- test harness quality;
- qualified partner access;
- acquisition-channel access;
- transition evidence;
- validated market/customer requirement.

Proposal volume by itself is not advancement.
