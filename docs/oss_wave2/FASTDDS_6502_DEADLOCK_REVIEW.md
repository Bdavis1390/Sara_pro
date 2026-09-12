# Fast DDS #6502 — timer-unregistration deadlock review

Date: 2026-09-12

Claims state: **SUPPORTED BY UPSTREAM SOURCE + THIRD-PARTY REPRODUCTION / NOT PROVEN INTERNALLY / WATCH-COLLABORATE**

Upstream issue: `eProsima/Fast-DDS#6502`

## Executive finding

This issue should no longer be treated as an unclaimed Worldshepherd fix target.

There is no matching Fast DDS pull request at the time of this review, but another contributor has already published a concrete per-timer quiescence design in the issue discussion and reports multi-platform reproduction plus substantial validation of that design. Worldshepherd should therefore avoid submitting a competing implementation unless the existing effort is abandoned or maintainers request an alternative.

The best Worldshepherd role is independent validation, invariant review, regression-test hardening, and monitoring for an upstream PR.

## Source-level mechanism

Current Fast DDS source shows two important behaviors.

### `ResourceEvent::unregister_timer()`

`unregister_timer()` acquires the event resource mutex. When called outside the service thread, it waits on `cv_manipulation_` until `allow_vector_manipulation_` becomes true. That flag is enabled only when the resource event thread finishes its timer-action pass and enters a state in which other threads may manipulate the timer collections.

The guarantee is stronger than callers actually require: a caller unregistering timer A can be forced to wait for an unrelated timer B callback to finish.

### `WriterProxy::stop()`

If a WriterProxy is `BUSY`, `stop()` deliberately calls `initial_acknack_->recreate_timer()` rather than merely cancelling it. The source comment states that the timed event may be executing and must be allowed to finish. Destruction paths also require this kind of quiescence because callbacks capture their owning objects.

Therefore, simply making timer unregistration non-blocking would be unsafe: it could allow a callback to run concurrently with owner cleanup or destruction.

## Deadlock cycle

The issue discussion includes independent captures on Fast DDS 3.6.2/macOS x86-64 and Linux/gcc 13 in addition to the original Android/aarch64 report.

The generalized cycle is:

1. Thread A holds an endpoint/discovery/writer mutex.
2. Thread A unregisters or recreates timer A and waits for the event service to reach global manipulation quiescence.
3. The event service thread is executing timer B.
4. Timer B's callback tries to acquire the endpoint/discovery/writer mutex held by Thread A.
5. Thread A cannot continue until the event service completes its action pass; the event service cannot continue until Thread A releases the mutex.

The independent reporter initially isolated lease-expiry callbacks, then demonstrated that the trigger is broader: `StatefulWriter::send_periodic_heartbeat` can close the same cycle. The defect is therefore not fundamentally a PDP lease-expiry bug; it is a global timer-quiescence coupling problem.

## Existing proposed fix from another contributor

The issue discussion proposes changing the contract from **global event-loop quiescence** to **quiescence of the specific timer being unregistered**.

The reported design:

- records the timer currently being executed;
- protects timer collections consistently with the resource mutex;
- snapshots the due prefix of active timers;
- releases the mutex while running a callback;
- revalidates snapshot entries before use;
- makes `unregister_timer(event)` wait only while that exact event is executing;
- preserves the service-thread non-waiting rule for re-entrant unregistration;
- removes the wider `allow_vector_manipulation_` / `skip_checking_active_timers_` mechanism.

The contributor reports:

- existing TimedEvent tests remain green;
- no additional ThreadSanitizer finding relative to baseline;
- an unpatched reproducer deadlocked at cycle 156, while the patched version completed 518 cycles;
- their approximately 180-test downstream suite passed.

These are third-party claims, not Worldshepherd internal validation.

## Worldshepherd improvement path

Do **not** duplicate the patch. Instead:

1. Port or reproduce the stress harness against current Fast DDS `master` without modifying production code.
2. Record lock-order and callback identity at the point of each unregister wait.
3. Verify the proposed per-timer scheme preserves these invariants:
   - an event is never destroyed while its callback is executing;
   - a recreated timer cannot race with `WriterProxy::clear()`;
   - re-entrant unregistration from the event thread does not self-deadlock;
   - a timer removed after a due-list snapshot is never dereferenced from stale storage;
   - timer ordering remains deterministic for equal/near-equal deadlines.
4. Run the current TimedEvent unit suite plus TSan where supported.
5. Add a deterministic deadlock regression test if upstream maintainers accept the design but the external patch lacks one suitable for Fast DDS CI.
6. Monitor the issue for the promised upstream PR and review that PR rather than opening a competing one.

## Contribution decision

**Classification: WATCH / COLLABORATE / INDEPENDENTLY VALIDATE.**

This remains a high-value resilience issue for Worldshepherd because it exercises failure containment and semantic liveness, but contribution priority should shift from implementation ownership to evidence quality and regression coverage.
