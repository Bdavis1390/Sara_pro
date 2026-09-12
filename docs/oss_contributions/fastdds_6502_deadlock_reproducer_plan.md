# Fast DDS #6502 — deterministic lease-expiry / timer-quiescence deadlock reproducer

Upstream: `eProsima/Fast-DDS#6502`

Claims state: **SOURCE-REVIEWED TEST CONTRIBUTION / REQUIRES FAST-DDS BUILD AND TSAN EXECUTION**

## Why contribute a reproducer before a lock rewrite

The issue contains two independent captures of the same wait cycle across Android/aarch64, macOS/x86-64, and Linux. A second reporter narrowed the trigger to **remote participant lease expiry overlapping endpoint teardown** and explicitly documented why seemingly easy changes to `ResourceEvent::unregister_timer()` are unsafe:

- `WriterProxy::stop()` intentionally uses blocking `recreate_timer()` when a timed event is BUSY;
- `TimedEvent::~TimedEvent()` must ensure the callback is quiescent before deleting callback-owned state;
- making unregister/cancel simply non-blocking can turn a deadlock into use-after-free.

The repository's existing `test/unittest/rtps/resources/timedevent/TimedEventTests.cpp` already encodes that blocking-cancel/recreate behavior as a synchronization guarantee, including a TSAN-oriented test. Therefore the safest first contribution is a deterministic regression harness that captures the cross-subsystem lock cycle without weakening timer lifetime semantics.

## Reported lock cycle

One thread tears down an endpoint while holding an endpoint/history mutex and blocks in:

```text
... WriterProxy::stop / TimedEvent::~TimedEvent
  -> ResourceEvent::unregister_timer
  -> wait for in-flight timer callback to quiesce
```

The ResourceEvent thread is inside a participant lease-expiry callback and attempts to remove remote endpoints, eventually waiting for an endpoint mutex held by the teardown thread:

```text
ResourceEvent::do_timer_actions
  -> lease callback
  -> PDP::check_remote_participant_liveliness / remove_remote_participant
  -> actions_on_remote_participant_removed
  -> removeRemoteEndpoints
  -> endpoint mutex
```

That is a circular wait: teardown owes callback quiescence while the callback owes an endpoint lock held by teardown.

## Contribution target

Add a regression/integration test that forces the overlap predictably enough for CI and can later validate any candidate lock-order fix.

### Test topology

- Main test process owns two DomainParticipants on the same domain.
- It repeatedly creates and deletes a writer/reader pair to exercise endpoint teardown.
- One or more helper peer processes join with a short advertised participant lease (for example 2–3 seconds).
- The helper peer is terminated without clean RTPS disposal so the main participants remove it by **lease expiry**, not by normal dispose traffic.
- Repeat the endpoint create/delete cycle across the expected expiry window.

### Deterministic synchronization

Do **not** merge a production `sleep_for()` like the reporter used to widen the race.

Preferred test-only mechanisms, in order:

1. Existing test hooks/friends around ResourceEvent or PDP if available.
2. A test-only synchronization barrier/callback compiled only into the test target.
3. A narrowly scoped injectable hook that pauses the lease callback immediately before endpoint removal while the teardown thread reaches the blocking unregister path.

The test should prove the exact cycle with barriers rather than depend on scheduler luck.

## Required assertions

Baseline/failing-mode harness should establish:

1. Lease-expiry callback has started on the ResourceEvent thread.
2. Endpoint teardown has entered the timer-unregister/quiescence path.
3. The lease-expiry callback attempts endpoint removal while teardown owns the conflicting endpoint lock.
4. The operation fails to complete inside a conservative deadline on vulnerable code.

After a future fix:

5. Both operations complete without forcing cancellation.
6. No timer callback runs after its owning object is destroyed.
7. Remote participant and endpoint state are fully removed.
8. A fresh participant/endpoint can be created afterward, proving no poisoned ResourceEvent state remains.

## Test matrix

- intraprocess delivery FULL / OFF;
- `recreate_timer()` path and `TimedEvent` destructor path;
- clean remote dispose control — should not reproduce the lease-expiry cycle;
- forced lease expiry — should exercise the target path;
- repeated 100+ cycles after fix;
- TSAN where supported;
- ASAN/UBSAN where supported;
- Linux default CI first, with macOS as a useful secondary reproducer if project CI capacity permits.

## Candidate fix constraints

The reproducer should be merged or reviewable independently of the final fix. Any final implementation must preserve these invariants:

- unregister/destructor returns only when callback lifetime is safe;
- ResourceEvent callback path must not wait on an endpoint mutex while another thread holding that mutex waits for ResourceEvent quiescence;
- no endpoint cleanup may be silently skipped merely to avoid the lock;
- participant lease expiry remains timely and idempotent.

This points toward **breaking the callback-side lock cycle** (for example staged removal, snapshot-then-act, or deferring mutex-taking endpoint cleanup to a context that does not own the ResourceEvent callback) rather than weakening timer quiescence. The exact architecture must be selected by Fast DDS maintainers after the harness identifies the minimal lock boundary.

## Worldshepherd mapping

This is a classic failure-containment and semantic-health case: all processes may remain alive while forward progress is permanently lost. OVERWATCH should distinguish liveness from progress, but the underlying lock-order bug belongs upstream in Fast DDS.

## Submission boundary

No matching fix PR or assignee was found in the 2026-09-12 thread-level audit. The independent reporter explicitly offered to test candidate fixes against their reproducer. This document does **not** claim a correct lock rewrite; it proposes the deterministic evidence harness needed before one can be justified.
