# SPIRE #7111 — decouple agent API retry backoff from reconciliation cadence

Upstream: `spiffe/spire#7111`

Claims state: **SOURCE-REVIEWED DESIGN / REQUIRES UPSTREAM TESTING AND MAINTAINER API SELECTION**

## Problem confirmed in current source

The agent manager currently derives the synchronize retry ceiling from the reconciliation interval:

- `SyncInterval` is the normal synchronization cadence.
- `synchronizeMaxIntervalMultiple = 48`.
- `synchronizeMaxInterval = 8 * time.Minute`.
- the manager computes `min(8m, 48 * SyncInterval)` and constructs the synchronize backoff using `SyncInterval` as its base interval.

With the default 5-second sync interval this permits roughly a four-minute retry ceiling after transient upstream/API errors. This couples two distinct control loops: steady-state reconciliation frequency and failure-recovery retry policy.

## Contribution objective

Separate **normal reconcile cadence** from **transient-failure retry cadence** without changing default behavior unexpectedly for existing deployments.

The preferred shape is an explicit retry policy that can be tuned independently while preserving the existing backoff implementation and clock injection used by tests.

Candidate manager configuration fields:

```go
// SyncRetryInitialInterval controls the initial retry delay after a failed
// synchronize attempt. Zero preserves the legacy behavior and uses SyncInterval.
SyncRetryInitialInterval time.Duration

// SyncRetryMaxInterval caps the synchronize retry delay. Zero preserves the
// legacy computed ceiling min(8m, 48*SyncInterval).
SyncRetryMaxInterval time.Duration
```

The zero-value compatibility rule is deliberate. Existing configs should behave identically unless the new knobs are configured.

## Proposed manager construction

Conceptually:

```go
retryInitial := m.c.SyncRetryInitialInterval
if retryInitial == 0 {
    retryInitial = m.c.SyncInterval
}

retryMax := m.c.SyncRetryMaxInterval
if retryMax == 0 {
    retryMax = min(synchronizeMaxInterval,
        synchronizeMaxIntervalMultiple*m.c.SyncInterval)
}

// Reject or clamp an invalid max below initial during config validation rather
// than silently constructing a nonsensical backoff policy.
m.synchronizeBackoff = backoff.NewBackoff(
    m.clk,
    retryInitial,
    backoff.WithMaxInterval(retryMax),
)
```

No change is proposed to `svidSyncBackoff` or size-limited backoff behavior unless maintainers explicitly want those exposed separately.

## HCL surface

`cmd/spire-agent/cli/run/run.go` already exposes `experimental.sync_interval` and parses it into the agent configuration. A low-risk first upstream version can keep the new settings in the same experimental block:

```hcl
agent {
  experimental {
    sync_interval = "5s"
    sync_retry_initial_interval = "1s"
    sync_retry_max_interval = "30s"
  }
}
```

Candidate raw fields:

```go
SyncRetryInitialInterval string `hcl:"sync_retry_initial_interval"`
SyncRetryMaxInterval     string `hcl:"sync_retry_max_interval"`
```

Parsing should use `time.ParseDuration`, reject non-positive configured values, and reject `max < initial`.

## Required tests

1. **Legacy compatibility** — with both new values zero/unset, verify the existing 5-second base and computed max behavior remain unchanged.
2. **Independent retry base** — `SyncInterval=5s`, retry initial `1s`, retry max `30s`; first failure waits according to the retry policy rather than five seconds.
3. **Ceiling** — repeated failures never exceed the configured retry max.
4. **Recovery** — a successful synchronization resets the retry sequence and steady-state reconciliation returns to `SyncInterval`.
5. **Large sync interval** — a large reconciliation interval no longer forces an excessively large transient retry when explicit retry settings are supplied.
6. **Validation** — reject zero/negative explicit durations and `max < initial`.
7. **Fake-clock deterministic test** — use the existing injected clock/backoff test structure; do not add wall-clock sleeps.
8. **No retry storm regression** — repeated failure still uses exponential backoff/jitter semantics already provided by the backoff package rather than a tight fixed retry loop.

## Observability recommendation

If the current telemetry surface does not expose retry state, add or reuse metrics/log fields for:

- synchronize attempt result;
- current retry interval;
- consecutive synchronize failures;
- successful recovery/reset.

This should be implemented using existing SPIRE telemetry conventions rather than a Worldshepherd-specific namespace.

## Worldshepherd relevance

This issue directly matches the Worldshepherd assurance-plane principle that **normal operating cadence, degraded-state recovery, and semantic health must be modeled independently**. A process that remains alive while waiting several minutes after a transient control-plane failure may be operationally degraded even though ordinary liveness checks stay green.

Worldshepherd should contribute the smallest upstream-compatible retry-policy change and a deterministic fake-clock regression suite; SARA/ECHO can then consume the resulting retry/recovery telemetry without embedding SPIRE-specific recovery logic.

## Submission boundary

Do not claim upstream acceptance. Before submission:

- verify current `main` has no competing PR for #7111;
- inspect maintainers' preference for experimental versus stable configuration placement;
- run manager and CLI config test suites;
- update `doc/spire_agent.md` if the configuration surface is accepted;
- preserve backward-compatible zero-value behavior unless maintainers request a default change.
