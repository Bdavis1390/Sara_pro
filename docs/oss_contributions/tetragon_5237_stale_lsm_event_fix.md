# Cilium Tetragon #5237 — prevent stale BPF-LSM event re-emission

Upstream: `cilium/tetragon#5237`

Claims state: **SOURCE-REVIEWED FIX DESIGN / REQUIRES BPF VERIFIER AND KERNEL TESTING / COORDINATE BEFORE UPSTREAM SUBMISSION**

## Confirmed failure mechanism

The issue reports phantom `PROCESS_LSM` events from a pod that is idle after one real matching event. The emitted records preserve the old timestamp and payload but recur when unrelated processes invoke the same LSM hook.

Current source ordering in `generic_start_process_filter()` is consistent with that diagnosis:

```c
if (!policy_filter_check(config->policy_id))
    return 0;

/* later */
msg->lsm.post = false;
msg->common.flags = 0;
```

For generic LSM, `generic_lsm_actions()` later sets `e->lsm.post = postit`, while the independent LSM output program can inspect that per-CPU event state. A non-matching invocation can therefore return before the stale `post` marker is cleared.

This differs materially from the kprobe output path, which does not have the same independently attached output behavior.

## Fix objective

Guarantee that **every LSM hook invocation starts with output authorization cleared before any filter can return**.

Do not indiscriminately move union/state resets in the shared generic helper unless the memory-layout consequences for kprobe/fentry/uprobe/rawtp paths are proven. The lowest-risk direction is an LSM-specific reset placed before the shared filter path or an explicitly LSM-guarded reset in the shared helper.

Conceptual option A — LSM entry reset:

```c
__attribute__((section((MAIN)), used)) int
generic_lsm_event(struct pt_regs *ctx)
{
    struct msg_generic_kprobe *e;
    int zero = 0;

    e = map_lookup_elem(&process_call_heap, &zero);
    if (e)
        e->lsm.post = false;

    return generic_start_process_filter(ctx, (struct bpf_map_def *)&lsm_calls);
}
```

Conceptual option B — in the shared helper under `#ifdef GENERIC_LSM`, clear `msg->lsm.post` immediately after obtaining `msg` and before `policy_filter_check()` can return.

Maintainers should choose the placement that best matches verifier constraints and existing generic sensor invariants.

## Why only clearing `post` is the first patch

The demonstrated phantom-output gate is `lsm.post`. Clearing the entire event payload before filtering may increase BPF instruction cost and risks perturbing fields that other generic sensor paths expect. A minimal authorization-bit reset is easier to reason about and test.

If testing shows any path can emit without a freshly populated payload after `post=true`, expand the reset deliberately rather than preemptively zeroing the full event structure.

## Required regression tests

1. Apply a namespaced `socket_connect` LSM policy to workload A.
2. Generate one real matching connection from workload A and record one expected event.
3. Keep A idle.
4. Generate sustained unrelated `socket_connect` activity from workload B that fails A's policy filter.
5. Assert no additional event with A's original timestamp/payload is emitted.
6. Repeat on at least two CPUs to exercise per-CPU heap state.
7. Generate a second legitimate event from A and confirm normal LSM output still works.
8. Validate `Override`/enforcement action semantics are unchanged.
9. Run BPF verifier/load tests across the repository's supported kernel matrix where CI provides them.
10. Add an event-count assertion so one policy-matching invocation cannot be amplified by unrelated hook invocations.

## Relation to Tetragon #5528

#5528 reports hundreds of events for one denied `execve`. Its issue thread explicitly notes that its immutable timestamp, single PID, and node-wide activity correlation may indicate the same #5237 stale-per-CPU mechanism, while also noting differences in hook/action/version. Treat #5528 as a likely related or duplicate symptom until #5237 is resolved and retested; do not open a second overlapping implementation lane.

## Worldshepherd mapping

This is an ECHO provenance-integrity failure: an old event is emitted as if it were evidence of a new effect-producing action. The governing invariant is:

> **No telemetry event may be emitted unless the current invocation freshly authorizes and populates that event.**

The upstream fix belongs in Tetragon; Worldshepherd should consume trustworthy events rather than compensate downstream for stale kernel telemetry.

## Upstream coordination and AI-assistance boundary

The maintainer has already asked the original reporter whether they are willing to propose a fix and separately asked whether the report was AI-generated. There is still no matching implementation PR or assignee in the 2026-09-12 audit, but that conversation means Worldshepherd should **not race the reporter**.

Before any external issue comment or PR:

- re-check whether the original reporter has accepted the maintainer's invitation or opened a PR;
- read and comply with the current Cilium/Tetragon contribution and AI-assistance policies;
- disclose AI assistance exactly as the project requires;
- prefer offering the regression harness / independent verification if another contributor has taken the code fix.

## Submission boundary

This design has not been built through the Tetragon BPF toolchain and must not be labeled validated until verifier, unit/integration, and supported-kernel tests pass. Internal preparation may continue; external submission requires the ownership and policy checks above.
