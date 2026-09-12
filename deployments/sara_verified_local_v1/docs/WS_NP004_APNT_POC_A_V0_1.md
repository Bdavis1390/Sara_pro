# WS NP004 APNT POC-A v0.1

**Status:** DRAFT / SIMULATED_ONLY / SYNTHETIC OPERATOR-AWARENESS DEMONSTRATOR / INFORMATIONAL DECISION AID ONLY / BLOCK MERGE
**Date:** 2026-09-12

## Purpose

This implementation demonstrates a bounded Worldshepherd layer above synthetic navigation-integrity events. It does not implement a PNT estimator, spoofing detector, pntOS/ASPN/GPNTS integration, vehicle navigation controller, Navy display, or action-routing path.

The demonstrator covers the six scenario states selected for POC-A:

1. nominal GPS;
2. degraded accuracy/integrity;
3. spoofing suspicion;
4. primary/alternate source disagreement;
5. alternate-source recovery;
6. restored trust.

## Current NAVWAR Phase-I boundary

The public NP004 Q&A states that Phase I should remain limited to informational decision aids. Accordingly, POC-A records whether a synthetic operator judges a recommendation appropriate, inappropriate, or deferred for evaluation purposes, but it cannot route, apply, or execute that recommendation.

The same Q&A establishes additional design targets for later POC increments: local/air-gapped execution; an API-first modular architecture; approximately 3–8 simultaneous APNT sources at roughly 1–10 Hz; sub-second ingest-to-initial-alert/recommendation behavior; deeper evidence available through progressive disclosure; representative synthetic data; and surrogate-user evaluation rather than promised Fleet-operator access. These are external requirements/targets, not measured Worldshepherd performance.

## Input contract

Each synthetic `APNTEvent` carries:

- source;
- sequence and timestamp;
- bounded Cartesian state estimate;
- confidence;
- integrity indicator;
- anomaly/reason codes;
- optional upstream informational recovery candidate.

Worldshepherd treats these values as upstream evidence. It does not claim to validate the underlying navigation physics or estimator.

## Worldshepherd outputs

For every event the demonstrator emits:

- a concise awareness alert;
- evidence references;
- an optional bounded informational recovery recommendation;
- an optional operator APPROVE / REJECT / DEFER evaluation response;
- a resulting evaluation state only;
- hash-linked source -> alert -> recommendation -> operator-response audit steps;
- deterministic replay digest;
- an explicit `execution_attempted=false` invariant.

An `APPROVED` state means only that the synthetic operator judged the displayed recommendation appropriate in the evaluation fixture. It never means an action was routed or applied. The module contains no simulated-action stage, PNT hardware interface, navigation-estimator control, external action API, or vehicle command path.

## Acceptance gates

The v0.1 focused regression suite requires:

- all six synthetic states ingested and alerted;
- four expected informational recommendations;
- final synthetic state `RESTORED`;
- complete hash-linked trace;
- identical digest when the same event set is supplied in reverse input order but has the same sequence/timestamps;
- `execution_attempted` remains false;
- no `SIMULATED_ACTION` stage exists in the evidence trace;
- operator APPROVE / REJECT / DEFER responses remain evaluation records only;
- duplicate event sequence fails closed;
- response referencing an unknown event fails closed;
- response must bind to the exact recommendation identifier.

## Claims boundary

Before exact-head focused CI succeeds:

**IMPLEMENTED IN SOFTWARE — DRAFT / VALIDATION PENDING**

After successful focused CI, maximum permitted claim:

**PROVEN INTERNALLY FOR THE SYNTHETIC POC-A V0.1 INFORMATIONAL-AWARENESS / REPLAY SCOPE**

Not currently claimed:

- actual Assured PNT performance;
- spoofing detection accuracy;
- pntOS, ASPN, GPNTS, GPS or alternate-sensor integration;
- Navy UI/display compliance;
- platform command, recovery execution, or action routing;
- 3–8 source throughput at 1–10 Hz;
- sub-second alerting or any other latency threshold;
- air-gapped deployment validation;
- operator-performance improvement;
- operational cybersecurity/compliance;
- partner, Navy or government validation.

## Next gates

1. Exact-head focused CI and evidence artifact for the informational-only boundary.
2. Add synthetic workload instrumentation for 3–8 sources at 1–10 Hz and measure ingest-to-initial-alert p50/p95/p99 without promoting the result beyond the tested environment.
3. Add progressive-disclosure evidence views that separate the initial alert from supporting rationale/evidence.
4. Validate containerized local/air-gapped execution on the APNT-specific demonstrator.
5. Add ECHO evidence-graph mapping for event -> alert -> informational recommendation -> operator evaluation response.
6. Qualified PNT partner supplies authoritative schema and integrity-estimator semantics for later read-only mapping.
7. Validate display/event mapping against applicable Navy/user conventions.
8. Keep command/action execution outside the Phase-I POC unless a later authoritative requirement explicitly changes that boundary and a separately reviewed authorization architecture is approved.
