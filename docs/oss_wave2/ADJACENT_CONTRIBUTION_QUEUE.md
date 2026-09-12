# Worldshepherd OSS opportunity wave 2 — 2026-09-12

This queue extends the open-source scan into adjacent autonomy, DDS/ROS 2, policy, and workload-identity infrastructure.

Claims state: **OPPORTUNITY SCREEN / NOT UPSTREAM OWNED / NOT UPSTREAM ACCEPTED**.

A candidate is promoted only after checking for a current upstream issue and searching for an existing fix PR. If another contributor already has a credible fix in flight, Worldshepherd records the item as `WATCH` instead of duplicating it.

## Priority model

Screening scores are internal prioritization estimates, not objective project ratings. They combine Worldshepherd capability fit, bounded patch surface, reproducibility, testability without expensive hardware, upstream leverage, and duplicate risk.

## P0 — unclaimed contribution candidates

### 1. ROS 2 rclcpp #3213 — bounded event queues / backpressure

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Screening score: **96/100**

`EventsCBGExecutor` can accumulate ready-but-unserviced events without bound when producers outrun execution. The upstream issue explicitly asks for a `max_events` policy and raises the core policy question: warn, reject new events, or remove old events.

Worldshepherd fit:

- bounded automation and bounded failure;
- semantic health instead of process-only health;
- queue saturation telemetry;
- degraded-state policy;
- deterministic fault/stress tests.

Recommended contribution sequence:

1. Write an executor stress test that drives a timer faster than one callback group can service it.
2. Measure queue depth and memory growth on the current implementation.
3. Define a policy enum/contract rather than hard-code one behavior:
   - `WARN_ONLY`
   - `DROP_NEWEST`
   - `DROP_OLDEST`
   - possibly `REJECT/ERROR` where API semantics permit.
4. Add saturation counters and a high-water mark that can be observed without inspecting process RSS.
5. Preserve existing unbounded behavior by default unless maintainers choose a breaking/default change.

Upstream-ready gate: maintainer agreement on drop semantics + deterministic queue-depth regression.

### 2. eProsima Fast DDS #6502 — liveliness/timer deadlock

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Screening score: **95/100**

The issue reports a deadlock between `ResourceEvent::unregister_timer()` and `PDP::check_remote_participant_liveliness()` with concrete thread stacks.

Worldshepherd fit:

- deadlock/failure-isolation analysis;
- lock-order invariants;
- liveliness semantics;
- watchdog-based regression where PID liveness is insufficient.

Recommended contribution sequence:

1. Reduce the reported two-thread stack cycle into a lock-order graph.
2. Identify whether timer unregister can be deferred or performed outside the participant/liveliness critical section.
3. Build a stress reproducer around participant discovery/removal and timer recreation.
4. Pass criterion must require discovery/liveliness progress, not only process survival.
5. Add a timeout/watchdog that emits the two last known lock-state transitions when progress stops.

Claims boundary: **ROOT-CAUSE ANALYSIS CANDIDATE / NO FIX CLAIMED** until the lock cycle is reproduced against current upstream.

### 3. Open Policy Agent Gatekeeper #4776 — operation-to-capability wiring tests

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Screening score: **94/100**

Gatekeeper has no focused table-driven test proving that each independently selectable `--operation` value creates exactly the controller dependencies it needs. The issue lists concrete contradictory paths around `status`, `generate`, mutation, and feature-disabled configurations.

Worldshepherd fit:

- PRIME-style explicit capability authorization;
- configuration truth;
- dependency minimization;
- deterministic policy/control-plane tests.

Recommended contribution:

- extract or expose a pure operation-to-capability plan used by production setup;
- table-test every isolated operation and representative combinations;
- assert required dependencies are non-null;
- assert disabled capabilities are not constructed;
- prove at least one test fails when a production guard is reverted.

This is a particularly attractive first contribution because it improves governance correctness without modifying admission-policy semantics.

### 4. Kyverno #17542 — distinguish `skip` from vacuous `pass`

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Screening score: **93/100**

A CEL `.all()` over an empty filtered set evaluates true, causing resources with no applicable nested objects to be reported as `pass`. Operators therefore cannot distinguish "validated and passed" from "nothing matched."

Worldshepherd fit:

- policy-result truthfulness;
- explicit `ALLOW/DENY/ESCALATE/NOT_APPLICABLE` semantics;
- audit provenance;
- avoiding false-green dashboards.

Recommended contribution shape:

1. Define an explicit applicability result before changing API surface.
2. Prototype/report semantics for `PASS`, `FAIL`, and `SKIP/NOT_APPLICABLE`.
3. Test nested-list filtering where the applicable set is empty, partially populated, and fully populated.
4. Preserve Kubernetes CEL truth semantics; the reporting layer should carry applicability rather than pretending CEL itself changed.

This should begin as a design/test contribution because the best API shape may require maintainer agreement.

### 5. SPIFFE/SPIRE #7236 — health cache freshness

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Screening score: **93/100**

SPIRE's shared health cache can serve a result up to one minute old after initial readiness. A short database blip can therefore leave every server reporting unhealthy for a full minute, potentially removing an otherwise recovered cluster from a load balancer.

Worldshepherd fit:

- semantic health;
- recovery-state observability;
- stale-evidence detection;
- degraded-state hysteresis.

Recommended contribution:

- separate check cadence from endpoint request cadence;
- shorten recovery detection after failure without creating a hot polling loop;
- expose `last_checked_at`, result age, and possibly last transition time;
- test transient failure, sustained failure, and recovery;
- avoid synchronized polling across HA replicas by preserving/adding jitter.

A robust design should distinguish `UNHEALTHY` from `HEALTH_STATE_STALE` rather than silently returning old truth.

### 6. SPIFFE/SPIRE #7111 — configurable API retry backoff

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Screening score: **91/100**

The agent's API retry delay is coupled to its sync interval and can become roughly four minutes with the default 5-second sync interval after transient API failures.

Worldshepherd fit:

- DDIL/reconnect resilience;
- bounded exponential backoff;
- recovery telemetry;
- separation of steady-state reconciliation cadence from failure-retry policy.

Recommended contribution:

- independent retry-backoff configuration with bounded min/max;
- jitter to avoid herd behavior;
- explicit attempt/backoff telemetry;
- compatibility default preserving current behavior unless maintainers choose otherwise;
- tests proving transient recovery does not wait for the full reconciliation-derived delay.

### 7. ROS 2 rclpy #1720 — intermittent service response timeout

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Screening score: **88/100**

Under repeated sequential service calls on Humble, `service_send_response` intermittently times out even though the process subsequently recovers and later calls succeed.

Worldshepherd fit:

- request/response semantic health;
- intermittent failure reproduction;
- provenance-rich timeout classification.

Recommended next action is **reproduction first**, not a patch: create a deterministic load harness that records request sequence, client lifetime, RMW implementation, response-send return code, and recovery behavior. Root cause may sit below rclpy, so ownership should follow evidence.

## Compatibility/watch inputs — do not duplicate

### Kyverno #17463 / PR #17469

Status: **ACTIVE FIX PR FOUND — WATCH**.

A concurrent map read/write in webhook expression caching already has a focused fix using a snapshot under the read lock plus a race regression test. Worldshepherd should watch review/CI and learn from the test pattern rather than open a competing implementation.

### Kyverno #17452 / PR #17543

Status: **ACTIVE FIX PR FOUND — WATCH**.

The no-op trigger update that can delete synchronized generated resources already has a fix PR comparing `object` and `oldObject` and a regression test. Do not duplicate.

### Kyverno #17088 / PR #17119

Status: **ACTIVE FIX PR FOUND — WATCH**.

The false `READY=false` state after VAP generation already has a patch that heals stale `WebhookConfigured` status. This is highly relevant to Worldshepherd's semantic-health model, but the contribution lane is occupied.

### Cilium Tetragon #5614 / PR #5621

Status: **ACTIVE FIX PR FOUND — WATCH**.

The truncated `MSG_OP_DATA` unsigned-size underflow/OOM path has an active patch with lower-bound validation and regression tests. Do not race it; monitor acceptance and reuse its failure-containment test pattern.

### Falco #3979 and falcosecurity/plugins #1499

Status: **CLOSED UPSTREAM — EVIDENCE/LESSON ONLY**.

Both the stale runtime-socket problem and CRI event re-subscription problem have been closed. Their important reusable lesson is that process/HTTP health can remain green while container enrichment is functionally dead.

### Eclipse Cyclone DDS #2440

Status: **CLOSED UPSTREAM — DO NOT DUPLICATE**.

The empty/element-free QoS profile null dereference is already completed upstream. Retain as a configuration-validation pattern, not a contribution target.

### OpenTelemetry Semantic Conventions PR #4102

Status: **OPEN PR BY ANOTHER CONTRIBUTOR — COMPATIBILITY WATCH**.

The PR proposes common handling for unbounded attributes and `*_ref` reference attributes. Worldshepherd audit/provenance schemas should watch this closely so evidence references and free-form explanations align with upstream semantics if/when they are accepted. Do not treat the proposed conventions as stable yet.

## Consolidation into the three Worldshepherd active tasks

### Active Task A — Autonomy & Resilience OSS

- ROS 2 rclcpp #3213
- Fast DDS #6502
- rclpy #1720
- existing Open-RMF / Zenoh / PX4 / Gazebo lanes

### Active Task B — Trust, Governance & Evidence OSS

- Gatekeeper #4776
- Kyverno #17542
- SPIRE #7236 and #7111
- existing OpenTelemetry / Keylime / Witness / Sigstore / Chainloop / OPA lanes

### Active Task C — Simulation / Physical-AI Frontier OSS

No new Wave-2 item is promoted into this task yet. Continue scanning Gazebo, Autoware, GNU Radio, ArduPilot, simulator fault-injection frameworks, and edge middleware; only promote when a concrete non-duplicated issue has a bounded contribution path.

## Promotion rule

A Wave-2 item becomes `PATCH DRAFT` only after:

1. source-level root-cause review;
2. confirmation that no existing upstream PR already owns the fix;
3. a minimal reproducer or a deterministic failing test;
4. a bounded patch surface;
5. compatibility analysis;
6. explicit pass/fail evidence criteria;
7. claims-state labeling.
