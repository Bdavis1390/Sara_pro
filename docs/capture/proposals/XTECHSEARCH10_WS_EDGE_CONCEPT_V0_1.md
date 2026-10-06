# xTech|Search 10 Concept v0.1 — WS-EDGE

**Working title:** WS-EDGE — Governed Evidence-to-Decision Gateway for DDIL Operations
**Opportunity:** U.S. Army xTech|Search 10
**Official deadline verified:** 2026-10-19 17:00 ET
**Submission rule:** one submission per eligible entity
**Status:** CONCEPT / requires legal-entity and eligibility verification before submission

## 1. Army problem

Distributed formations increasingly depend on AI-enabled decision support, sensor fusion, autonomous logistics, and machine-to-machine workflows while operating under intermittent connectivity, stale data, contested networks, and rapid configuration change.

The failure mode is not only "AI made a bad prediction." A fielded workflow must also answer:

- Which data was current?
- Which source produced it?
- Was it replayed, duplicated, or stale?
- Which model or rule produced the recommendation?
- What action was authorized?
- Who approved it?
- What happened after communications degraded?
- Can the event chain be reconstructed after the fact?

## 2. Proposed product

**WS-EDGE** is a software assurance gateway that sits between data/AI/autonomy services and mission or sustainment workflows.

It provides:

1. provenance-bound event ingestion;
2. stale/replay/duplicate detection;
3. policy and human-approval gates for bounded actions;
4. deterministic event replay and mission-state reconstruction;
5. configuration and version custody;
6. degraded-connectivity operation with queued, bounded workflows;
7. machine-readable evidence packages for after-action review and rapid requalification.

WS-EDGE is not a replacement for the Army's C2, sensor, autonomy, logistics, or communications systems. It is an assurance and evidence layer that can wrap those systems through adapters.

## 3. Why this is differentiated

Most observability products answer whether software is running. WS-EDGE is designed to answer whether a decision/action chain was **authorized, evidence-supported, configuration-consistent, and reconstructable**.

The architecture combines:

- SARA — governed orchestration;
- PRIME — authorization / policy boundary;
- ECHO — provenance and evidence lineage;
- OVERWATCH — status and anomaly visibility.

The existing public repository contains implemented software, tests, CI, rollback/recovery work, and claims/evidence controls. Operational Army-system integration remains a proposed validation step rather than a current claim.

## 4. Initial Army use cases

### A. Adaptive sustainment
- maintenance decision provenance;
- distributed repair/fabrication authorization;
- inventory/logistics event lineage;
- comms-loss queueing and reconciliation;
- post-event reconstruction.

### B. C2 / Counter-C2 networks
- stale and replayed message detection;
- machine recommendation lineage;
- policy-gated workflow execution;
- degraded-state reconstruction;
- resilient command-post evidence.

### C. Autonomous systems
- human-on-the-loop authorization evidence;
- configuration custody;
- mission-state divergence detection;
- deterministic replay for incident review.

## 5. Measurable proof-of-concept

A 12–16 week proof-of-concept should integrate WS-EDGE with one synthetic or customer-provided workflow.

Predeclared metrics:

| Metric | Target for POC |
|---|---|
| Event lineage completeness | >=99% for in-scope events |
| Injected replay/duplicate detection | >=99% |
| Injected stale-data detection | >=99% under declared thresholds |
| Unauthorized action blocking | 100% for declared policy violations |
| Deterministic reconstruction | Exact reconstruction for bounded test corpus |
| Recovery after disconnect/restart | No unauthorized action and complete retained evidence |
| Added latency | measured and reported; no unsupported performance claim before test |

Targets are proposal objectives, not current field-performance claims.

## 6. Phase-1 xTech demonstration

Demonstrate:

1. nominal workflow;
2. comms loss;
3. stale sensor/update;
4. replayed event;
5. unauthorized request;
6. configuration change;
7. recovery/reconciliation;
8. machine-readable after-action evidence.

## 7. Transition

Potential transition paths include Army C2, distributed sustainment, autonomous systems, condition-based maintenance, and government digital-engineering/test environments.

The commercial counterpart is regulated or high-consequence AI/autonomy assurance where customers need evidence of what an AI-enabled workflow did and why.

## 8. Evidence boundary

Current posture:
- `IMPLEMENTED IN SOFTWARE` for specific SARA and evidence-governance behaviors tied to tests;
- `PROVEN INTERNALLY` only for bounded tested configurations;
- `REQUIRES PARTNER VALIDATION` for Army/customer system integration;
- no Army sponsorship, fielding, certification, CUI authorization, or operational performance is currently claimed.

## 9. Submission blockers

Before submission:
- verify Curious NerdworX is an eligible U.S. for-profit small business;
- verify ownership/control and <=500 employee rules;
- check prior/current/pending federal support for substantially similar technology;
- freeze one entity name and one product name;
- produce the competition-specific white paper in the required format;
- retain exact submitted version and human approval in the evidence record.
