# WS-DCAR NLR -> Argonne External Validation Protocol

**Date:** 2026-09-30
**Program:** Worldshepherd Data Center Assurance & Resilience (WS-DCAR)
**Routing:** ACTIVE 3/3 — Growth & Externalization (#283)
**Controlling gate:** #525
**Implementation PR:** #524

## Objective

Advance WS-DCAR from external-surrogate interoperability to independent validation against partner-origin or partner-controlled evidence without weakening the existing claims boundary.

Sequence:

1. **NLR** — extend the existing measured-workload lineage represented by DOI `10.7799/3025227` into a controlled event bundle carrying enough provenance to evaluate an actual bounded intervention.
2. **Argonne JLSE** — apply the same evidence contract to the Data Center Flexibility Dataset project, whose planned control sweeps and QoS/power measurements are a strong fit for independent event verification.

This protocol does not treat workload power traces as utility-boundary evidence and does not infer missing authorization, clock, baseline, configuration, or meter provenance.

## Stage NLR-001 — controlled event request

Public source already integrated at surrogate level:

- NLR Data Catalog: Dataset of Generative AI Workload Power Profiles
- DOI: `10.7799/3025227`
- high-resolution measured GenAI workload power profiles
- public processed derivative already ingested by EXT-001

### Minimum useful event bundle

For one workload or bounded power-management event:

- event/request identifier;
- issued intervention and command timestamp;
- workload/job identifier;
- hardware/software configuration identity;
- synchronized node/cluster power measurements;
- higher-level PDU/facility/grid-boundary measurement when available;
- clock source and synchronization evidence;
- pre-event baseline interval or documented baseline method;
- telemetry quality flags/gaps;
- known adverse or exception condition where feasible.

Examples of bounded interventions include a GPU power-cap change, clock-frequency change, workload start/stop, concurrency change, or another partner-approved action with an explicit timestamp.

### NLR disposition rules

- If only workload/device power is available, classify the result at that measurement boundary only.
- If the issued request/authorization is absent, return `INSUFFICIENT_EVIDENCE`; do not infer intent from the trace.
- If higher-level metering is absent, do not make a utility/grid-boundary claim.
- Preserve raw-source identity, transformation history, resampling, scaling, filtering, and aggregation parameters.
- Any redaction must preserve stable pseudonymous identifiers sufficient to test configuration and meter continuity.

## Stage ANL-001 — JLSE flexibility-event validation

Target project: **Argonne JLSE Data Center Flexibility Dataset**, PI Wei Gao.

Published project scope includes sweeps of:

- GPU clock frequency;
- GPU/CPU power caps;
- batch size;
- request concurrency;

with measurements including node-level GPU/CPU/DRAM power/energy, clock, utilization, temperature, and per-request QoS such as time-to-first-token, latency, and tokens/second. The project also targets achievable power range, ramp rate, and performance-flexibility characterization.

### Proposed bounded collaboration

Argonne/JLSE retains control of the experiment. For one selected control action or sweep segment, WS-DCAR receives an evidence bundle containing:

- control/request identity and timestamp;
- authorization/experiment-ownership record;
- synchronized measurement timestamps;
- control setting before/after;
- hardware/software configuration identity;
- node/cluster power and energy telemetry;
- QoS measurements;
- telemetry quality/gap markers;
- facility/grid-boundary measurement if available;
- baseline definition;
- one adverse case or intentionally incomplete bundle where practical.

WS-DCAR independently emits one of:

- `VERIFIED`
- `VERIFIED_WITH_EXCEPTIONS`
- `INSUFFICIENT_EVIDENCE`
- `NONCOMPLIANT`

The disposition must state the measurement boundary. A node/cluster result is not promoted to a facility/grid claim without authoritative higher-level metering.

## Common evidence contract

Each external event should be representable as:

```text
source identity
  -> issued request / control action
  -> authorization / experiment authority
  -> configuration identity
  -> synchronized measurements
  -> transformation history
  -> baseline method
  -> verifier disposition
  -> immutable evidence hashes
```

### Required custody fields

- source organization;
- dataset/project identifier;
- raw file/object identity;
- cryptographic hash where available;
- acquisition timestamp/range;
- timezone/clock source;
- transformation steps in order;
- transformation parameters;
- software/tool version used for transformation;
- measurement boundary and units;
- configuration/hardware identifiers;
- redaction/pseudonymization statement;
- known limitations.

## Adversarial acceptance tests

A partner bundle is useful even when incomplete if the ground truth is known. Preferred adverse cases include:

1. missing authorization evidence;
2. stale or missing telemetry;
3. timestamp offset / clock drift;
4. configuration change during event;
5. meter/device identity substitution;
6. response-deadline miss;
7. duration shortfall;
8. decomposition mismatch;
9. baseline invalidation;
10. successful physical outcome with an invalid evidence chain.

The verifier passes the exercise only if it refuses unsupported positive claims and distinguishes evidence failure from operational noncompliance.

## Advancement criteria

### NLR-001 complete when

A partner-origin event or controlled experimental bundle is replayed with explicit provenance and the resulting disposition is independently reproducible.

### ANL-001 complete when

At least one JLSE control-sweep event is replayed with control identity, synchronized telemetry, configuration identity, QoS context, and explicit measurement-boundary limitations.

### Partner-validation gate complete when

A controlled event includes authoritative facility/grid-boundary evidence plus request provenance, authorization evidence, synchronized clocks, baseline method/uncertainty, configuration custody, and at least one adverse case.

## Claims boundary

Until the partner-validation gate is complete, the following remain `REQUIRES PARTNER VALIDATION`:

- MW-scale field accuracy;
- utility compliance;
- facility/grid demand-response performance;
- economic savings;
- reliability improvement;
- water/emissions outcomes;
- field cybersecurity performance.

External-data ingestion, deterministic transformations, provenance preservation, fail-closed evidence handling, and synthetic/adversarial verification may be claimed only to the extent demonstrated by repository tests and exact-head CI.
