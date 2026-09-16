# Cilium Tetragon #5237 — stale BPF-LSM event re-emission

Upstream issue: `cilium/tetragon#5237`

Current upstream fix: `cilium/tetragon#5460` — **OPEN / FIX IN REVIEW**

Claims state: **UPSTREAM FIX IN REVIEW / WORLDSHEPHERD MECHANISM ANALYSIS ALIGNED / REQUIRES UPSTREAM BPF + KERNEL VALIDATION**

## Status change

Worldshepherd originally identified the stale per-CPU LSM output state as the likely mechanism and recommended clearing output authorization before policy-filter early returns, while explicitly avoiding a race with the original reporter.

Upstream PR #5460 now implements that same class of correction: it clears stale LSM output state before policy filtering and adds a regression test designed to reproduce the same-CPU stale re-emission condition. The earlier deleted-fork PR #5388 is superseded by #5460.

This materially changes the contribution posture:

- do **not** open a competing implementation PR;
- treat #5460 as the authoritative upstream fix candidate;
- offer independent review/reproduction only if useful to maintainers;
- do not claim the bug resolved until the upstream PR is merged and its target release/integration state is known.

## Confirmed failure mechanism

The issue reports phantom `PROCESS_LSM` events from a pod that is idle after one real matching event. The emitted records preserve the old timestamp and payload but recur when unrelated processes invoke the same LSM hook.

The reviewed source ordering was consistent with that diagnosis:

```c
if (!policy_filter_check(config->policy_id))
    return 0;

/* later */
msg->lsm.post = false;
msg->common.flags = 0;
```

For generic LSM, `generic_lsm_actions()` later sets `e->lsm.post = postit`, while the independently attached LSM output program can inspect per-CPU event state. A non-matching invocation can therefore return before stale output authorization is cleared.

The core invariant remains:

> **Every LSM hook invocation must begin with output authorization/state cleared before any filter path can return.**

## Alignment with PR #5460

PR #5460 is directionally aligned with the Worldshepherd analysis because it moves the stale-state clear ahead of policy filtering rather than trying to compensate downstream for duplicate/stale telemetry.

That alignment is evidence that the mechanism analysis was useful; it is **not** evidence that Worldshepherd authored, validated, or caused the upstream patch.

The upstream implementation and tests remain authoritative.

## Independent validation targets

If Worldshepherd contributes further, the useful lane is verification rather than competing code:

1. reproduce one legitimate namespaced LSM event;
2. keep the matching workload idle;
3. generate unrelated same-hook activity that does not match the policy;
4. assert the original event/timestamp is not re-emitted;
5. exercise more than one CPU/per-CPU heap instance;
6. produce a second legitimate matching event and confirm normal output;
7. verify `Override`/enforcement semantics remain unchanged;
8. run verifier/load tests across the upstream-supported kernel matrix;
9. test the related #5528 symptom after #5460 to determine whether any user-space amplification remains.

## Relation to Tetragon #5528

#5528 reports hundreds of events for one denied `execve`. Its thread notes that immutable timestamp, single PID, and node-wide activity correlation may indicate the same #5237 stale-per-CPU mechanism, while also noting differences in hook/action/version.

Do not open a second overlapping implementation lane. Re-test #5528 after the #5237 fix is merged; only then isolate any remaining event-cache or user-space retry behavior.

## Worldshepherd mapping

This remains an ECHO provenance-integrity case: an old event is emitted as if it were evidence of a new effect-producing action.

Worldshepherd should consume trustworthy upstream events and retain the invariant:

> **No telemetry event may be emitted unless the current invocation freshly authorizes and populates that event.**

## Submission boundary

As of the latest audit, Worldshepherd should not submit a competing Tetragon #5237 fix. The active posture is **WATCH / REVIEW / INDEPENDENT VALIDATION IF REQUESTED**.

Do not promote this lane to resolved until #5460 is actually merged and, where relevant, released/backported. Do not claim upstream acceptance of Worldshepherd work from the existence of #5460.