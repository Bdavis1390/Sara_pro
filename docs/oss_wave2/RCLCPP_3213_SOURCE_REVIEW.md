# ROS 2 rclcpp #3213 — bounded EventsCBGExecutor queue source review

Upstream target: `ros2/rclcpp#3213`

Claims state: **SOURCE-REVIEWED DESIGN CONSTRAINT / NO FIX CLAIMED / REQUIRES UPSTREAM DESIGN AGREEMENT**

## What the current source actually does

`FirstInFirstOutCallbackGroupHandle` owns a per-callback-group:

```cpp
std::deque<ReadyEntity> ready_entities;
```

For subscriptions, clients, services, waitables, and callback events, each readiness notification receives a count and materializes one `ReadyEntity` per ready instance:

```cpp
for (size_t i = 0; i < nr_msg; i++) {
  ready_entities.emplace_back(...);
}
```

That loop runs under the callback group's `ready_mutex` through `add_ready_entity()`.

This confirms the reported memory-growth mechanism: if readiness is produced faster than the callback group can consume it, executor-side `ReadyEntity` objects can accumulate without a local bound.

## Critical constraint: `ReadyEntity` is not just a pointer

Every `ReadyEntity` constructor assigns a global event ID:

```cpp
id(GlobalEventIdProvider::get_next_id())
```

The scheduler exposes a `get_next_ready_entity(max_id)` path and compares the front event's ID against `max_id` when coordinating work across callback groups.

Therefore a seemingly simple optimization such as:

```text
one weak_ptr + pending_count
```

is **not automatically semantics-preserving**. If many individual events are collapsed into one counter, the implementation must still preserve whatever ordering guarantees the global event IDs provide across callback groups. A single count does not retain the interleaving of IDs with events produced concurrently by other groups.

This is the main reason Worldshepherd should not submit a naive counter-compression patch yet.

## Upstream discussion constraints

The current issue discussion adds two further constraints:

1. maintainers/users prefer the policy to be configurable rather than guessing application intent;
2. simply dropping executor events can be unsafe and may create other leaks or semantic loss because readiness may correspond to work retained below the executor.

One upstream proposal is to stop materializing more queue objects after a threshold while retaining a deferred count and later re-materializing work. The global-ID behavior above means that proposal needs an explicit ordering analysis before implementation.

## Recommended first contribution

### Phase 1 — deterministic evidence, no semantic change

Add a focused test/benchmark for `FirstInFirstOutCallbackGroupHandle` that:

- generates readiness faster than a callback group consumes it;
- records the materialized queue depth / high-water mark;
- covers subscriptions, services/clients, waitables, and timers separately;
- demonstrates which entity types can produce multiple ready instances;
- runs both mutually-exclusive and reentrant callback groups;
- exercises the `max_id` scheduler path so later solutions cannot accidentally break cross-group ordering.

If a public queue-depth accessor is undesirable, keep the instrumentation test-only/friend-scoped.

### Phase 2 — choose a representation contract with maintainers

Before changing production behavior, answer these questions explicitly:

1. Is the bound per callback group, per entity, or executor-wide?
2. Must individual ready events retain their current global event IDs?
3. Can multiple events from one readiness notification be represented as a batch without changing scheduling semantics?
4. How should `KEEP_ALL` QoS interact with executor-side bounds?
5. What is the special rule for waitables, where a DDS history limit may not exist?
6. Is saturation allowed to reject/drop work, or must it only bound the representation while preserving all pending work?

## Candidate design directions

### A. Warning/high-water instrumentation only

Lowest compatibility risk, but does **not** solve unbounded memory. Useful as a first PR if maintainers want operational visibility before choosing semantics.

### B. Bounded materialization with deferred accounting

Potentially preserves underlying work without dropping it, but requires a representation that preserves the existing global ordering contract. A bare counter is insufficient until proven otherwise.

### C. QoS-derived per-entity limits

Attractive for subscriptions/clients/services where lower layers already have resource/history limits, but can become RMW/vendor-specific and does not solve waitables uniformly.

### D. Hard executor policy (`DROP_*` / reject)

Easy to bound memory but highest semantic risk. Upstream discussion already raises concerns that dropping executor events can strand work elsewhere. Do not make this the default contribution without explicit maintainer direction.

## Regression properties for any eventual fix

Any accepted implementation should prove:

```text
materialized_ready_entities <= configured/derived bound
no deadlock under concurrent readiness + execution
no lost scheduler wakeup when a callback group transitions idle -> ready
no callback-group starvation introduced
max_id ordering behavior remains valid
expired entities still drain safely
mutually-exclusive groups never execute concurrently
reentrant groups continue exposing additional ready work correctly
```

The test should also distinguish **executor queue boundedness** from DDS/resource boundedness; solving only one layer must not be described as solving the entire memory-growth problem.

## Recommended Worldshepherd status

Keep `rclcpp#3213` at **P0 / SOURCE REVIEW COMPLETE / DESIGN-AGREEMENT REQUIRED**. The next upstream-safe deliverable is a deterministic queue-growth regression/benchmark, not a speculative production patch.
