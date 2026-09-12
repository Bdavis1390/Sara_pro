# KubeEdge #7278 — isolate node health from high-volume list/watch fan-out

Upstream: `kubeedge/kubeedge#7278`

Claims state: **SOURCE-REVIEWED RESILIENCE DESIGN / REQUIRES SCALE REPRODUCTION AND BENCHMARKING**

## Reported failure chain

The issue describes a large-scale CloudCore deployment where batch Service label changes generate thousands of Service and Endpoints events. `CommonResourceEventHandler.dispatchEvents()` processes listeners serially for each GVR; fan-out then feeds CloudHub reliable delivery, whose ACK handling and success-point persistence add further serialized work and synchronous Kubernetes API calls.

Observed consequence: application/resource synchronization work can delay node-status processing long enough for Kubernetes to mark large numbers of edge nodes `NotReady`, after which reconnect activity compounds the load.

This is a **bulkhead/backpressure failure**: high-volume data-plane/control-data work is allowed to consume the scheduling and persistence capacity required for liveness-critical node health.

## Design principle

Do not solve this by simply spawning one goroutine per listener/event. Unbounded parallelism moves the failure from latency to memory, API-server pressure, and goroutine explosion.

The correction should introduce explicit bounded work classes and preserve per-resource ordering where required.

## Proposed phased contribution

### Phase 1 — measurable bounded listener fan-out

Replace serial listener iteration with a bounded worker/semaphore model per handler or shared dispatcher.

Required properties:

- maximum concurrent `sendObj` work is configurable or derived from a conservative default;
- queue depth is bounded;
- enqueue latency, queue depth, active workers, dropped/coalesced work, and send latency are observable;
- shutdown drains or cancels workers cleanly;
- ordering semantics are documented and tested.

Before parallelizing, verify whether two updates for the same resource/listener may be reordered without violating edge-cache correctness. If ordering matters, shard by a stable key (for example node + GVR + namespace/name) so different keys execute concurrently while one key stays ordered.

### Phase 2 — coalescing for state-style watch events

For resources where only the newest state matters, avoid shipping every superseded intermediate `Modified` event during a burst.

Candidate rule:

```text
pending[(listener, resource-key)] = newest resourceVersion/event
```

A worker consumes the latest pending state. This must not be used for event types or resources whose intermediate transitions are semantically required.

### Phase 3 — health/control priority bulkhead

Node heartbeat/status and reconnect-control traffic must not share an unbounded starvation domain with bulk resource fan-out.

Introduce explicit priority or separate bounded queues so health-critical traffic has reserved service capacity. The invariant is not “health always first”; it is that bulk watch propagation cannot delay node-health handling beyond the node monitor safety budget.

### Phase 4 — reduce ACK persistence amplification

The issue reports synchronous ObjectSync API operations after ACKs. Measure before changing semantics. Candidate improvements include:

- cache existing ObjectSync objects and avoid redundant GETs;
- batch or coalesce status updates by resource/version;
- use a bounded persistence worker rather than blocking the delivery loop;
- apply conflict-aware retry with cancellation;
- expose persistence backlog and age.

Any batching must preserve the reliable-sync recovery contract.

## Required benchmark/reproduction harness

Build a scale test that can vary:

- edge nodes: 20 / 40 / 100 / 200;
- watched Services/Endpoints: 100 / 500 / 2000+;
- listeners per GVR;
- label-update burst size and rate;
- CloudCore replicas;
- API-server latency;
- artificial edge-link delay/loss.

Capture at minimum:

- p50/p95/p99 event dispatch latency;
- node-status response latency;
- count/duration of Ready→NotReady transitions;
- dispatcher queue depth and oldest-item age;
- ACK queue depth/age;
- Kubernetes API request rate and latency;
- CloudCore CPU, goroutines, heap;
- per-replica connected-node distribution.

## Acceptance criteria

1. Reproduce the reported oscillation or an equivalent saturation signature on baseline code.
2. Under the same burst, no node-health deadline is missed solely because the resource fan-out queue is saturated.
3. Memory and goroutine counts remain bounded by configured capacities.
4. No resource ends with an older state than the newest delivered resourceVersion.
5. Backpressure is visible through metrics/logging rather than silent queue growth.
6. Recovery after the burst is monotonic: queue age drains and nodes do not enter a reconnect oscillation.
7. The fix does not multiply Kubernetes API write pressure beyond baseline.

## Worldshepherd mapping

This directly exercises SARA/OVERWATCH degraded-state doctrine:

- classify work by operational criticality;
- bound automation and queues;
- preserve semantic ordering;
- expose backlog age, not merely process liveness;
- reserve recovery capacity so overload in one work class cannot collapse unrelated health functions.

## Submission boundary

No matching implementation PR was found in the 2026-09-12 duplicate check. The issue's timing arithmetic is reporter-supplied and must be validated with profiling before treating each listed sub-cause as proven. Start with instrumentation + bounded fan-out benchmark, then change persistence/priority semantics only where measurements support them.
