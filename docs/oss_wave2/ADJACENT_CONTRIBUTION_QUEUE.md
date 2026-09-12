# Worldshepherd OSS opportunity wave 2 — 2026-09-12

This queue extends the open-source screen into adjacent autonomy, DDS/ROS 2, policy, and workload-identity infrastructure.

Claims state: **OPPORTUNITY SCREEN / NOT UPSTREAM OWNED / NOT UPSTREAM ACCEPTED**.

Candidates are promoted only after checking the live upstream issue and looking for an existing fix PR or contributor claim. Items already being fixed are classified as `WATCH` rather than duplicated.

## P0 — currently unclaimed candidates

### ROS 2 rclcpp #3213 — bounded executor event queues

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Internal screening score: **96/100**

`EventsCBGExecutor` may grow its ready-event queue without bound when producers outrun callback execution. Upstream explicitly asks for a `max_events` policy and for the behavior at saturation to be designed.

Worldshepherd contribution shape:

- deterministic saturation reproducer;
- queue high-water mark and saturation evidence;
- explicit policy contract (`WARN_ONLY`, `DROP_NEWEST`, `DROP_OLDEST`, or maintainer-selected equivalent);
- compatibility-preserving default;
- tests showing bounded queue behavior without hiding semantic degradation.

First gate: maintainer agreement on saturation/drop semantics before changing the public API.

### eProsima Fast DDS #6502 — liveliness/timer deadlock

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Internal screening score: **95/100**

The issue provides thread stacks for a deadlock between `ResourceEvent::unregister_timer()` and `PDP::check_remote_participant_liveliness()`.

Worldshepherd contribution shape:

- convert the stacks into a lock-order graph;
- build a participant discovery/removal and timer-recreation stress test;
- identify the smallest critical-section reduction or deferral that breaks the cycle;
- use discovery/liveliness progress as the pass criterion instead of process survival.

Claims state remains **ROOT-CAUSE ANALYSIS CANDIDATE** until reproduced against current upstream.

### Kyverno #17542 — distinguish not-applicable from pass

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Internal screening score: **93/100**

CEL `.all()` over an empty filtered set evaluates true, so a resource with no applicable nested items can be reported as passing. That makes `not evaluated` indistinguishable from `evaluated and compliant`.

Worldshepherd contribution shape:

- define reporting semantics for `PASS`, `FAIL`, and `SKIP/NOT_APPLICABLE`;
- preserve standard CEL truth semantics;
- test empty, partially applicable, and fully applicable nested collections;
- bind the reporting state to audit evidence so false-green dashboards are impossible.

This should start as a design/test contribution because API shape requires maintainer agreement.

### SPIFFE/SPIRE #7236 — health-cache freshness

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Internal screening score: **93/100**

SPIRE's shared health cache may serve a health result up to roughly one minute old after initial readiness. A brief shared-database outage can therefore leave HA replicas marked unhealthy long after recovery.

Worldshepherd contribution shape:

- shorter recovery-detection cadence without hot polling;
- preserve/add jitter so replicas do not synchronize their checks;
- expose result age / last check / last state transition where appropriate;
- test transient failure, sustained failure, and recovery;
- distinguish stale health evidence from a freshly measured unhealthy result.

### SPIFFE/SPIRE #7111 — independent retry/backoff policy

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Internal screening score: **91/100**

Agent API retry backoff is coupled to the reconciliation sync interval and can become very long after a transient API/network failure.

Worldshepherd contribution shape:

- independently configurable bounded min/max backoff;
- jitter to prevent herd behavior;
- explicit retry/backoff telemetry;
- backward-compatible defaults;
- tests demonstrating quick recovery from transient failures without changing steady-state sync cadence.

### ROS 2 rclpy #1720 — intermittent service-response timeout

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Internal screening score: **88/100**

Repeated sequential Humble service calls intermittently produce `service_send_response` timeout warnings while the system later recovers.

Worldshepherd action: **REPRODUCTION FIRST**. Record request sequence, client lifetime, RMW implementation, response-send return state, DDS state, and recovery. Root cause may be below rclpy, so repository ownership should follow the evidence rather than assumption.

## High-value watch lanes — do not duplicate

### Gatekeeper #4776 / PR #4813

Status: **ACTIVE FIX PR — WATCH**.

The issue is already owned by PR #4813, which extracts an operation-to-capability `Plan` and table-driven tests. The issue discussion also identifies overlap with PR #4784 in `main.go` and `pkg/operations`. Worldshepherd should watch the abstraction decision and reuse the governance/testing pattern, not submit a competing rewire.

### Kyverno #17463 / PR #17469

Status: **ACTIVE FIX PR — WATCH**.

The expression-cache concurrent map race already has a focused snapshot-under-lock fix and race regression test.

### Kyverno #17452 / PR #17543

Status: **ACTIVE FIX PR — WATCH**.

The destructive no-op trigger update already has a patch comparing `object` with `oldObject` and regression coverage.

### Kyverno #17088 / PR #17119

Status: **ACTIVE FIX PR — WATCH**.

The false `READY=false` state for VAP-backed policies already has a status-healing patch. This is directly relevant to semantic-health truth but the contribution lane is occupied.

### Cilium Tetragon #5614 / PR #5621

Status: **ACTIVE FIX PR — WATCH**.

The malformed `MSG_OP_DATA` unsigned-size underflow/OOM issue already has bounds validation and userspace regression tests in flight.

### Falco #3979 and falcosecurity/plugins #1499

Status: **CLOSED UPSTREAM — LESSON ONLY**.

These issues demonstrate a reusable Worldshepherd principle: a process and `/healthz` endpoint can remain green while runtime metadata enrichment is dead after a dependency restart.

### Eclipse Cyclone DDS #2440

Status: **CLOSED UPSTREAM — DO NOT DUPLICATE**.

The empty/element-free QoS provider null-dereference lane is completed upstream.

### OpenTelemetry Semantic Conventions PR #4102

Status: **OPEN PR BY ANOTHER CONTRIBUTOR — COMPATIBILITY WATCH**.

The PR proposes common rules for unbounded attributes and `*_ref` reference attributes. Worldshepherd provenance/audit schemas should align if the proposal is accepted, but must not treat it as stable semantics yet.

## Additional scan candidates requiring deeper source review

These are not yet promoted to P0 because duplicate/root-cause review is incomplete:

- SPIRE #7234 — agent heap retention associated with OIDC-provider JWKS fetches; reproduce before attributing cause.
- SPIRE #7146 — opt-in federation behavior when a referenced bundle is missing; strong failure-isolation relevance but wider data-model/operator-UX implications.
- SPIRE #5624 — alternative event-cache reconciliation algorithm; high provenance/state-convergence relevance but large architectural scope.
- SPIRE #7233 — proposed KMIP-backed KeyManager/UpstreamAuthority; strategically relevant to custody but requires careful cryptographic/plugin review and should not be treated as a quick contribution.

## Consolidation into the three Worldshepherd active tasks

**Active Task A — Autonomy & Resilience OSS:** rclcpp #3213, Fast DDS #6502, rclpy #1720, plus existing Open-RMF/Zenoh/PX4/Gazebo lanes.

**Active Task B — Trust, Governance & Evidence OSS:** Kyverno #17542, SPIRE #7236/#7111, plus OpenTelemetry/Keylime/Witness/Sigstore/Chainloop/OPA. Gatekeeper #4776 stays WATCH because PR #4813 owns the active implementation.

**Active Task C — Simulation / Physical-AI Frontier OSS:** continue scanning Gazebo, Autoware, GNU Radio, ArduPilot, fault-injection frameworks, and edge middleware; no new Wave-2 candidate is promoted here until a concrete, non-duplicated issue has a bounded patch path.

## Promotion rule

Move an item from `CANDIDATE` to `PATCH DRAFT` only after source-level root-cause review, a fresh duplicate check, a reproducible failing test or explicit design gap, bounded patch surface, compatibility analysis, and explicit pass/fail evidence criteria.
