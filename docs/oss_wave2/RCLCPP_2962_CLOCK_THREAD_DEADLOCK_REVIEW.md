# ROS 2 rclcpp #2962 — TimeSource clock-thread teardown deadlock review

Date: 2026-09-12

Claims state: **SOURCE-REVIEWED REPRODUCTION CANDIDATE / ROOT CAUSE NOT PROVEN INTERNALLY / NOT UPSTREAM ACCEPTED**

Upstream issue: `ros2/rclcpp#2962`

## Executive finding

Issue #2962 is a strong Worldshepherd autonomy/resilience contribution candidate because the ROS 2 client-library working group has explicitly asked for additional independent reproduction, the failure is timing-sensitive, and the affected code path is narrow enough to instrument without redesigning the executor prematurely.

The reported symptom is an intermittent teardown deadlock in `TimeSource::NodeState::destroy_clock_sub()` while waiting for `clock_executor_thread_` to join. The reporter reproduced the failure on multiple clean Rolling workspaces and found it substantially easier to trigger on constrained hardware. Another maintainer could not reproduce it in 100 runs on a higher-core system, and the original reporter later reported 10,000 clean runs on a more powerful build server. This strongly suggests a scheduling/race window, but does not establish a root cause by itself.

No matching open fix PR was found during this review.

## Current source path

Current `rclcpp/src/rclcpp/time_source.cpp` reviewed for this record shows:

- `TimeSource::NodeState::detachNode()` calls `destroy_clock_sub()` first, with an explicit comment that this must happen before other teardown so the executor cannot invoke callbacks while state is being cleaned up.
- `create_clock_sub()` acquires `clock_sub_lock_`, creates a mutually-exclusive callback group, creates a private `SingleThreadedExecutor`, and starts a thread which adds the callback group and spins the executor.
- `destroy_clock_sub()` acquires `clock_sub_lock_`, then, if the clock executor thread is joinable:
  1. calls `clock_executor_->cancel()`;
  2. waits in `clock_executor_thread_.join()`;
  3. removes the callback group from the executor;
  4. resets the clock subscription.

The code is intentionally trying to provide teardown quiescence. A proposed fix therefore must preserve the invariant that no clock callback can race with destruction of the node/time-source state.

## What is known versus not known

Known from source and the issue:

- the hang is observed while teardown waits for the dedicated clock executor thread;
- reproduction frequency is sensitive to hardware/load/scheduling;
- the dedicated clock thread, callback group, executor, and subscription all participate in the same lifecycle transition;
- the working group wants independent reproduction.

Not yet proven:

- which exact lock, wait-set operation, guard condition, or callback keeps the executor thread from exiting;
- whether `clock_sub_lock_` participates directly in the deadlock cycle;
- whether the regression originates in rclcpp, rcl, the executor implementation, or an interaction introduced by a specific Rolling change;
- whether the same defect exists in current Jazzy or other supported distributions.

Worldshepherd should avoid naming a lock-order root cause until a timeout capture shows both sides of the cycle.

## Reproduction campaign

The first useful contribution is a deterministic or at least high-probability reproducer with evidence capture.

### Environment matrix

Run the existing failing tests under at least:

- current Rolling from source;
- the Rolling commit range around the report if current main no longer reproduces;
- current Jazzy as a negative/control comparison;
- Fast DDS RMW first, matching the report, then one alternate RMW if the failure is reproduced.

Capture kernel, CPU model, CPU count, ROS/RMW SHAs, compiler/build flags, and container/VM limits.

### Increase the scheduling window deliberately

Prefer controlled constraints over artificial sleeps in production code:

- pin the test process to 1–2 CPUs with CPU affinity;
- reduce container/cgroup CPU quota;
- run a competing CPU load on the same assigned CPUs;
- repeat `test_node` and `test_time_source` with a per-run watchdog;
- vary executor/thread CPU affinity to determine whether same-core contention materially changes failure probability.

Record attempts-to-failure and teardown latency distribution, not just pass/fail.

### Capture on watchdog timeout

On each hang, collect:

- `gdb`/debugger `thread apply all bt` equivalent;
- the thread blocked in `clock_executor_thread_.join()`;
- the clock executor thread stack;
- ownership/wait state for `clock_sub_lock_` and relevant executor/wait-set locks where observable;
- whether `cancel()` was observed by the executor;
- whether the clock callback group is still registered;
- current node/context shutdown state.

The evidence artifact should identify the exact resource each blocked thread needs.

## Instrumentation plan

Add test-only or debug logging around:

- entering/leaving `create_clock_sub()`;
- callback-group creation and address/identity;
- clock executor thread start and completion of `add_callback_group()`;
- entry into `spin()` and exit from `spin()`;
- entry into `destroy_clock_sub()`;
- before/after `cancel()`;
- before/after `join()`;
- before/after `remove_callback_group()`;
- callback start/end where safe.

Use monotonic timestamps and thread IDs so the order can be reconstructed without relying on wall-clock logging.

## Deterministic-test direction

If stack captures show a reproducible ordering dependency, replace brute-force stress with synchronization barriers in a dedicated test.

A good regression test should force the teardown thread to reach the vulnerable point while the clock executor thread is in the exact conflicting state, then release the barrier and prove teardown completes within a bounded time.

Do not merge a timing-only `sleep()` regression if a barrier/latch can encode the state transition directly.

## Candidate fix classes — only after reproduction

Depending on evidence, likely solution classes include:

1. change teardown ordering so executor cancellation/quiescence occurs without holding a lock needed by the clock thread;
2. detach/remove the callback group at a different lifecycle point while retaining strong ownership until executor exit;
3. make the clock executor thread observe cancellation before entering a wait state that teardown cannot break;
4. repair a lower-level guard-condition/wait-set lifecycle race if stacks show the dedicated thread is stuck below rclcpp.

These are hypotheses, not proposed patches yet.

Any fix must preserve:

- no callback after teardown begins destroying dependent state;
- deterministic executor-thread termination;
- no use-after-free of callback-group/subscription/node interfaces;
- no leaked clock executor thread;
- normal `/clock` behavior and simulated-time transitions.

## Worldshepherd pass criteria

Promote this issue from `REPRODUCTION CANDIDATE` to `PATCH DRAFT` only after:

- current or pinned-source reproduction exists;
- at least one hang has complete thread stacks;
- the blocking resource cycle is identified;
- a regression test fails pre-fix and passes post-fix;
- the fix is exercised under constrained and unconstrained scheduling;
- the relevant `rclcpp` test suites remain green;
- sanitizer/thread-race checks show no new failure where practical.

## Contribution decision

**Classification: P0 / INDEPENDENT REPRODUCTION + ROOT-CAUSE EVIDENCE CANDIDATE.**

Internal screening score: **94/100**.

This is a particularly good Worldshepherd contribution because upstream explicitly needs independent reproduction and because the evidence-generation work is useful even if the eventual fix belongs below `rclcpp`. The immediate deliverable should be a reproducible hang package and thread-state evidence, not an unverified lock-order patch.
