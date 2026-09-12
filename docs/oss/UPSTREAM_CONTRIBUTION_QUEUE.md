# Live upstream contribution queue — 2026-09-12

This queue converts the open-source screen into bounded engineering work. Priority is based on Worldshepherd fit, reproducibility, upstream usefulness, blast-radius reduction, and ability to prove improvement with tests.

## P0 — Open-RMF: isolate per-robot failures from fleet health

### Issue open-rmf/rmf_ros2#553

`add_robot()` can throw from an asynchronous participant callback when no charger is reachable. The exception can terminate the fleet adapter process even though the failure is specific to one robot.

**Worldshepherd contribution:** failure containment + semantic health reporting.

Proposed acceptance criteria:

- a robot with no reachable charger is rejected/faulted without terminating the adapter;
- healthy robots continue to register and operate;
- the caller receives a structured/catchable failure signal where practical;
- async callback boundaries do not allow recoverable per-robot exceptions to escape to `std::terminate`;
- tests include at least two robots so blast-radius isolation is proven rather than inferred;
- health output distinguishes `process_alive` from `fleet_operational`.

Suggested test matrix:

```text
robot A reachable charger, robot B unreachable charger -> adapter survives; A registered; B faulted
both reachable -> both registered
no charging waypoint exists anywhere -> deterministic error, no process abort
callback invoked after fleet weak_ptr expired -> safe return
```

### Issue open-rmf/rmf_ros2#549

Python bindings can retain the GIL during blocking RMF calls, creating a fleet-wide deadlock when worker callbacks simultaneously need Python.

**Worldshepherd contribution:** concurrency boundary audit + liveness regression test.

Acceptance criteria:

- binding calls that may block on RMF internals release the GIL;
- Python callbacks reacquire the GIL only for Python execution;
- stress test runs concurrent `replan()`/issue creation and callback traffic for a bounded interval with a watchdog;
- watchdog proves telemetry timestamps continue advancing, not merely that the process PID is alive.

## P0 — Eclipse Zenoh: semantic transport health under DDIL/reconnect stress

### Issue eclipse-zenoh/zenoh#2780

Router can remain alive with listeners present while silently ceasing to accept new sessions.

**Worldshepherd contribution:** accept-path accounting invariants + externally observable semantic readiness.

Acceptance criteria:

- `incoming`/pending-accept accounting cannot leak after cancellation, timeout, task abort, or panic;
- rejection due to `accept_pending` saturation is visible above trace-only logging;
- stress test repeatedly restarts router and rapidly connects/disconnects sessions;
- readiness probe performs an actual short connection/round trip rather than checking PID/listen socket only;
- test fails if kernel backlog grows while no application accept progress occurs.

Useful invariant:

```text
accepted_links_started - accepted_links_finished == current_incoming_counter
```

The invariant should hold after every spawned accept task completes, times out, is cancelled, or is aborted.

### Issue eclipse-zenoh/zenoh#2718

A silently dead peer can cause roughly ten seconds of forwarding interruption between otherwise healthy peers during lease-expiry teardown.

**Worldshepherd contribution:** failure-isolation benchmark.

Acceptance criteria:

- three-router minimum harness with A<->B traffic while C is blackholed without FIN;
- measure forwarding gap distribution across repeated runs;
- graceful shutdown is retained as a null/control case;
- link teardown must not hold a global/shared forwarding critical section across blocking close/flush work;
- regression threshold should be expressed in relation to normal forwarding cadence, not only an absolute wall-clock value.

## P1 — Keylime: attestation truthfulness and history

### keylime/keylime#1932

Warn when a non-empty measured-boot reference state is supplied but `accept-all` means it is not enforced.

Contribution shape:

- explicit runtime warning at policy assignment/first evaluation;
- audit field exposing effective measured-boot policy mode;
- test proving warning occurs once and does not flood per quote.

### keylime/keylime#1909

Add cumulative attestation failure history.

Contribution shape:

- persistent `total_attestation_failures` counter;
- migration + API exposure;
- invariants: success resets consecutive failures but never total failures; failed verification increments total exactly once.

### keylime/keylime#1941

Inconsistent push attestation fallback intervals can silently change cadence.

Contribution shape:

- one authoritative fallback definition;
- explicit degraded-cadence telemetry when fallback is used;
- tests for malformed/missing verifier interval response.

## P1 — Sigstore/Cosign: provenance publication failure semantics

### sigstore/cosign#5035

Define atomicity/rollback semantics across OCI artifact publication.

**Worldshepherd contribution:** phase ledger and partial-success evidence.

Candidate publication phases:

```text
VALIDATED
BLOBS_UPLOADED
ARTIFACT_MANIFEST_COMMITTED
DISCOVERY_INDEX_UPDATED
COMPLETE
```

On failure, return the original cause plus the highest durable commit point. Never imply rollback of shared content-addressed blobs unless exclusivity is proven.

### sigstore/cosign#5037

Separate source and target registry policies when `COSIGN_REPOSITORY` redirects artifacts.

**Worldshepherd contribution:** policy-domain separation tests.

Acceptance criteria:

- credentials/clients/TLS policy never cross source->target boundary implicitly;
- same canonical repository can preserve compatibility;
- same host but different repository is treated as a separate policy boundary unless explicitly configured;
- 401/403/TLS/timeout causes remain distinguishable.

## P1 — Gazebo: make simulation a qualification/evidence engine

### gazebosim/gz-sim#3891

A failed integration test can emit gigabytes of repeated logs.

Contribution shape:

- rate-limit/deduplicate repeated terminal server-error logging;
- fail test promptly when required remote model cannot be resolved;
- assert bounded log volume in the regression test.

### gazebosim/gz-sim#3881 and #3941

Flaky communications/noise tests are useful candidates for deterministic statistical test design.

Contribution shape:

- fixed/recorded seeds where deterministic behavior is required;
- statistically valid tolerances when randomness is part of the feature;
- repeated-run CI helper that records failure rate and confidence bounds.

## P2 — OpenTelemetry Semantic Conventions

See `OTEL_AUDIT_EVENT_SEMCONV_PROPOSAL.md`.

Primary objective is a narrow audit envelope that composes with domain semantic conventions rather than reproducing them.

## P2 — Open Policy Agent

See `OPA_AGENT_POLICY_ENVELOPE.md`.

Primary objective is an agent-runtime guide with a structured decision contract and explicit PDP/PEP boundary.

## P2 — Chainloop

See `CHAINLOOP_FANOUT_RESILIENCY_PROPOSAL.md`.

Primary objective is a durable, replayable, inspectable integration-delivery contract before broker-specific implementation.

## Definition of an upstream-ready Worldshepherd contribution

A contribution does not move from `CANDIDATE` to `UPSTREAM_READY` until it has:

1. a live upstream issue or maintainer-confirmed need;
2. a minimal reproducible case or explicit design gap;
3. a bounded patch surface;
4. tests that prove the claimed improvement;
5. failure/recovery semantics;
6. compatibility analysis;
7. claims labeling that distinguishes local validation from upstream acceptance;
8. no dependence on Worldshepherd-specific branding in the upstream interface unless maintainers explicitly want it.
