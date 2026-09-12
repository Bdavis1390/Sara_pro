# Worldshepherd OSS opportunity wave 2 — 2026-09-12

This queue extends the open-source screen into adjacent autonomy, DDS/ROS 2, policy, workload-identity, simulation, RF/DSP, flight-controller, and edge-infrastructure projects.

Claims state: **OPPORTUNITY SCREEN / NOT UPSTREAM OWNED / NOT UPSTREAM ACCEPTED**.

Candidates are promoted only after checking the live upstream issue, current source where practical, and looking for an existing fix PR or contributor claim. Items already being fixed or credibly owned are classified as `WATCH/COLLABORATE` rather than duplicated.

## P0 — currently unclaimed or bounded contribution candidates

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

Source review found that naïvely compressing/counting pending events is unsafe because `ReadyEntity` IDs participate in cross-group ordering. First gate: maintainer agreement on saturation/drop semantics before changing the public API.

### Autoware Universe #12460 — GoalPlanner callback-group lifetime crash

Status: **OPEN / UNASSIGNED / NO MATCHING FIX PR FOUND**  
Internal screening score: **95/100**

Repeated planning-goal churn can abort the `behavior_path_planner` component container with an rclcpp guard-condition/wait-set error. Current source still creates lane/freespace callback groups inside each short-lived `GoalPlannerModule`, while the longer-lived manager repeatedly creates new module instances from the same node.

The reporter's static callback-group workaround is reportedly used operationally across releases with nightly/fleet monitoring and no recurrence, but a process-global static is broader than necessary.

Worldshepherd contribution shape:

- retain/adapt the supplied planning-goal abuse runner as a permanent regression harness;
- reproduce on current Autoware/ROS 2 under CPU-constrained stress;
- verify the callback-group lifetime hypothesis;
- prefer manager- or node-lifetime callback-group ownership over process-global statics;
- test repeated module destruction/recreation, multi-node isolation, and executor survival.

Claims state: **SOURCE-SUPPORTED LIFETIME MISMATCH / THIRD-PARTY WORKAROUND VALIDATION / ROOT CAUSE REQUIRES WORLDshepherd REPRODUCTION**.

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

A source-reviewed patch draft is included in this branch. It remains **REQUIRES UPSTREAM TESTING/MAINTAINER REVIEW**.

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

### Gazebo Sim #3979 — physics collider survives late entity removal

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Internal screening score: **91/100**

Source review indicates removal processing currently occurs in an update phase even though removed-component traversal is documented for `PostUpdate`. The cleanup path also requires entity hierarchy information, making a simple deferred entity-ID queue potentially insufficient.

Worldshepherd contribution shape:

- deterministic create/remove/recreate physics regression;
- preserve enough hierarchy/component evidence until post-update removal processing;
- prove collision state disappears with the removed entity;
- verify no ghost colliders or stale physics handles remain.

### GNU Radio #8195 — low-normalized-frequency Signal Source error

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Internal screening score: **90/100**

Source review points to fixed-point NCO phase-increment quantization as the leading mechanism. At 1 Hz / 100 MS/s the ideal fixed increment is approximately 42.94967296, while the current conversion yields 42, predicting approximately 0.9778887 Hz or about -2.211% error before other effects.

Worldshepherd contribution shape:

- add low-normalized-frequency regression coverage;
- characterize error versus requested frequency/sample rate;
- establish the compatibility/accuracy contract with maintainers before changing oscillator representation or rounding behavior;
- avoid claiming the mechanism as fully proven until measured against the running block.

## P1 — promoted validation / hardware-evidence lane

### ArduPilot #34365 — STM32H7 type2 I2C kernel-clock/timing mismatch

Status: **OPEN / NO ACTUAL FIX PR FOUND / SOURCE DESIGN ALREADY DISCUSSED**  
Internal screening score: **90/100**

The type2 STM32H7 configuration can select PCLK1 for I2C1/2/3/5 while ArduPilot uses hardcoded H7 `TIMINGR` constants derived for roughly 32 MHz. The issue derives roughly 415 kHz counter timing for a requested 100 kHz bus on SPRacingH7RF and a direct SCLDEL mismatch of roughly 61.5 ns versus a 250 ns standard-mode setup requirement.

PR #34349 explicitly treats this as a separate issue and does not fix it.

Worldshepherd contribution shape:

- compile-time invariant tying hardcoded timing assumptions to the actual selected kernel clock;
- timing-calculation regression across H7 type2 variants;
- review/fix the corresponding ChibiOS `I2C1235SEL` selector logic as close to upstream as possible;
- hardware scope/logic-analyzer evidence on SPRacingH7RF I2C2 before flight-critical qualification.

Claims state: **SUPPORTED BY SOURCE/COUNTER DERIVATION / REQUIRES LAB VALIDATION**. Do not convert the counter-only frequency estimate into a measured-bus claim.

### ROS 2 rclpy #1720 — intermittent service-response timeout

Status: **OPEN / NO MATCHING FIX PR FOUND**  
Internal screening score: **88/100**

Repeated sequential Humble service calls intermittently produce `service_send_response` timeout warnings while the system later recovers.

Worldshepherd action: **REPRODUCTION FIRST**. Record request sequence, client lifetime, RMW implementation, response-send return state, DDS state, and recovery. Root cause may be below rclpy, so repository ownership should follow the evidence rather than assumption.

## WATCH / COLLABORATE — do not duplicate

### Fast DDS #6502 — ResourceEvent timer-unregistration deadlock

Status: **OPEN / NO UPSTREAM PR YET / CREDIBLE THIRD-PARTY PATCH DESIGN PRESENT**.

A second contributor independently reproduced the deadlock across Fast DDS 3.6.2 on macOS/x86-64 and Linux in addition to the original Android/aarch64 report. Their follow-up generalizes the fault: any timer callback requiring a mutex held by a thread unregistering another timer can close the cycle.

They also published a concrete per-timer quiescence design and report unit-suite, TSan-baseline, reproducer, and downstream-suite validation. Worldshepherd should independently reproduce/review invariants and contribute regression evidence rather than open a competing implementation.

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

### KubeEdge resilience cluster

Status: **MULTIPLE ACTIVE FIX PRS / WATCH FOR DESIGN LESSONS**.

Recent high-fit KubeEdge issues are largely occupied: certificate-rotation reconnect deadlock (#7142/#7143), retry-timer cleanup (#7202), false-success CSI response (#7186), local-cache false ACK/divergence (#7070), node-delete sync GC (#7027), and webhook CA/certificate rotation (#7220) all have active fix PRs. EdgeCore certificate bootstrap panic #7165 is open but assigned to its reporter. Do not duplicate these lanes.

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

**Active Task A — Autonomy & Resilience OSS:** rclcpp #3213, Autoware #12460, rclpy #1720, plus existing Open-RMF/Zenoh/PX4 lanes. Fast DDS #6502 moves to WATCH/COLLABORATE because a credible implementation design already exists in the issue.

**Active Task B — Trust, Governance & Evidence OSS:** Kyverno #17542, SPIRE #7236/#7111, plus OpenTelemetry/Keylime/Witness/Sigstore/Chainloop/OPA. Gatekeeper and the occupied KubeEdge fixes remain WATCH.

**Active Task C — Simulation / Physical-AI Frontier OSS:** Gazebo #3979/#3977, GNU Radio #8195, ArduPilot #34365, plus continuing Autoware/Gazebo/RF/fault-injection and edge-middleware scans. ArduPilot #34365 remains lab-gated; its timing claims do not advance beyond source/counter derivation until hardware waveforms exist.

## Promotion rule

Move an item from `CANDIDATE` to `PATCH DRAFT` only after source-level root-cause review, a fresh duplicate/ownership check, a reproducible failing test or explicit design gap, bounded patch surface, compatibility analysis, and explicit pass/fail evidence criteria.

If another contributor already has a credible implementation in an issue but no PR, classify the lane as `WATCH/COLLABORATE` rather than exploiting the absence of a PR to claim ownership.
