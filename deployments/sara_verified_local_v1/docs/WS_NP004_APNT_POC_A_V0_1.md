# WS NP004 APNT POC-A v0.1

**Status:** DRAFT / SIMULATED_ONLY / SYNTHETIC OPERATOR-AWARENESS DEMONSTRATOR / BLOCK MERGE  
**Date:** 2026-09-12

## Purpose

This implementation demonstrates a bounded Worldshepherd layer above synthetic navigation-integrity events. It does not implement a PNT estimator, spoofing detector, pntOS/ASPN/GPNTS integration, vehicle navigation controller, or Navy display.

The demonstrator covers the six scenario states selected for POC-A:

1. nominal GPS;
2. degraded accuracy/integrity;
3. spoofing suspicion;
4. primary/alternate source disagreement;
5. alternate-source recovery;
6. restored trust.

## Input contract

Each synthetic `APNTEvent` carries:

- source;
- sequence and timestamp;
- bounded Cartesian state estimate;
- confidence;
- integrity indicator;
- anomaly/reason codes;
- optional upstream recovery candidate.

Worldshepherd treats these values as upstream evidence. It does not claim to validate the underlying navigation physics or estimator.

## Worldshepherd outputs

For every event the demonstrator emits:

- a concise awareness alert;
- evidence references;
- an optional bounded recovery recommendation;
- explicit operator APPROVE / REJECT / DEFER custody;
- a resulting action state;
- hash-linked source -> alert -> recommendation -> operator-decision -> simulated-action audit steps;
- deterministic replay digest.

No recommendation is executable when an explicit approval is absent. Missing operator input resolves to `DEFERRED`.

An approved candidate may only reach `SIMULATED_APPLIED`, which is explicitly a synthetic state transition. No PNT hardware, navigation estimator, platform controller, external API, or vehicle command is executed.

## Acceptance gates

The v0.1 focused regression suite requires:

- all six synthetic states ingested and alerted;
- four expected recovery recommendations;
- final synthetic state `RESTORED`;
- complete hash-linked trace;
- identical digest when the same event set is supplied in reverse input order but has the same sequence/timestamps;
- no simulated action without explicit operator approval;
- rejected action remains non-executable;
- duplicate event sequence fails closed;
- decision referencing an unknown event fails closed.

## Claims boundary

Before exact-head focused CI succeeds:

**IMPLEMENTED IN SOFTWARE — DRAFT / VALIDATION PENDING**

After successful focused CI, maximum permitted claim:

**PROVEN INTERNALLY FOR THE SYNTHETIC POC-A V0.1 REPLAY/AUTHORIZATION SCOPE**

Not currently claimed:

- actual Assured PNT performance;
- spoofing detection accuracy;
- pntOS, ASPN, GPNTS, GPS or alternate-sensor integration;
- Navy UI/display compliance;
- platform command or recovery execution;
- sub-second alerting or any specific latency threshold;
- operational cybersecurity/compliance;
- partner, Navy or government validation.

## Next gates

1. Exact-head focused CI and evidence artifact.
2. Latency instrumentation for ingest-to-alert p50/p95/p99 using synthetic workloads.
3. ECHO evidence-graph adapter tying event/recommendation/operator decision/result.
4. Qualified PNT partner supplies real schema and integrity-estimator semantics.
5. Validate display/event mapping against actual Navy/user conventions.
6. Only then evaluate read-only partner integration; command execution remains separately governed.
