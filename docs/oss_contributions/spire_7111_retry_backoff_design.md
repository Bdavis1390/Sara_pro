# SPIRE #7111 — decouple agent API retry backoff from reconciliation cadence

Upstream issue: `spiffe/spire#7111`

Current upstream implementation: `spiffe/spire#7286` — **OPEN / MERGEABLE / FIX IN REVIEW**

Claims state: **UPSTREAM FIX IN REVIEW / WORLDSHEPHERD DESIGN ALIGNED / DO NOT DUPLICATE**

## Status change

Worldshepherd previously source-reviewed #7111 and proposed separating normal `SyncInterval` from transient synchronization retry policy while preserving legacy defaults.

Upstream PR #7286 now implements that lane directly. It is open, non-draft, mergeable, and has maintainer reviewers requested. Worldshepherd should therefore stop implementation work and track/review the upstream fix.

## Confirmed problem

SPIRE derives synchronize retry timing from the reconciliation interval:

- normal `SyncInterval` controls steady-state synchronization cadence;
- retry backoff also starts from that cadence;
- the retry ceiling is bounded by `min(8m, 48 * SyncInterval)`.

With the normal 5-second sync interval this can allow roughly a four-minute retry ceiling after transient synchronization failures. Normal operating cadence and degraded-state recovery policy are separate control concerns and should be independently configurable.

## How PR #7286 addresses it

The upstream PR adds an experimental `sync_retry_backoff` configuration block with optional fields:

```hcl
agent {
  experimental {
    sync_retry_backoff {
      initial_interval = "1s"
      max_interval = "30s"
      backoff_multiplier = 2
      jitter = 0.1
    }
  }
}
```

Important properties from the PR description:

- unset fields preserve current behavior;
- configured durations must be positive;
- max must not be less than initial;
- multiplier must be at least 1;
- jitter must be in `[0, 1)`;
- existing backoff plumbing is reused rather than replaced;
- the current default multiplier is preserved at 1.5 when unset;
- attestation and manager-init loops remain outside this change.

This is broader than the initial Worldshepherd sketch, which focused primarily on independent initial/max intervals. The upstream version appropriately exposes multiplier and jitter as part of one coherent retry policy.

## Upstream test coverage claimed by #7286

The PR reports:

- unit tests for backoff multiplier and randomization options;
- fake-clock manager tests for defaults, ceilings, configured backoff, and partial configuration fallback;
- CLI config parsing and validation cases;
- `go test` for agent/CLI packages;
- `go vet` and lint execution.

These are **upstream author claims** until independently reproduced; Worldshepherd should not restate them as its own validation.

## Worldshepherd review targets

If contributing review/validation rather than code, focus on invariants:

1. no configuration -> byte-for-behavior compatibility with the legacy retry sequence;
2. successful synchronization resets retry state and returns to normal reconciliation cadence;
3. configured max is never exceeded;
4. jitter cannot create zero/negative effective delay;
5. partial configuration inherits the documented legacy value for every omitted field;
6. a large `sync_interval` can coexist with fast bounded transient retry when configured;
7. no change leaks into attestation or manager-init backoff loops;
8. observability still makes degraded retry state distinguishable from healthy steady-state synchronization.

## Worldshepherd mapping

This remains a SARA/OVERWATCH assurance-plane case:

```text
steady_state_cadence != degraded_state_retry_policy
```

A live process waiting minutes after a transient control-plane failure is semantically degraded even if PID/liveness checks remain green.

## Submission boundary

Do not submit a competing SPIRE #7111 implementation while PR #7286 is active. Current posture is **WATCH / REVIEW / INDEPENDENT VALIDATION IF REQUESTED**.

Do not mark #7111 resolved until #7286 is merged and the relevant release/integration state is known.
