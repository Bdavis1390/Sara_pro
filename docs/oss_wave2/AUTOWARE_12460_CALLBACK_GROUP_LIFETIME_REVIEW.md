# Autoware Universe #12460 — GoalPlanner callback-group lifetime review

Date: 2026-09-12

Claims state: **SOURCE-SUPPORTED LIFETIME MISMATCH / THIRD-PARTY WORKAROUND VALIDATION / ROOT CAUSE REQUIRES WORLDSHEPHERD REPRODUCTION**

Upstream issue: `autowarefoundation/autoware_universe#12460`

## Executive finding

Issue #12460 is a high-value, currently unassigned Worldshepherd contribution candidate.

The reported failure is a process-aborting `rclcpp::exceptions::RCLError` while the multithreaded executor is rebuilding/waiting on guard conditions after planning-goal churn. The reporter attributes the crash to callback groups owned by a short-lived `GoalPlannerModule`: a new planning goal can destroy and recreate the module while the executor still has weak references to callback-group state.

Current Autoware Universe source still creates the lane-parking and freespace-parking callback groups inside each `GoalPlannerModule` instance. The manager creates fresh `GoalPlannerModule` instances from a longer-lived node. This establishes a real lifetime mismatch worth testing even though Worldshepherd has not yet reproduced the exact crash on current master.

The reporter's workaround makes the callback groups static so they survive module recreation. They report using that fix across releases, with nightly testing and fleet log monitoring, and no recurrence since applying it. That is meaningful third-party operational evidence but not a sufficient reason to adopt process-global statics upstream.

## Current Autoware source ownership

On current source reviewed for this record:

- `GoalPlannerModule` has instance-owned `rclcpp::CallbackGroup::SharedPtr` members for lane and freespace parking;
- the constructor calls `node.create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive)` for each module instance;
- timers are created against those groups;
- the destructor cancels the timers;
- `GoalPlannerModuleManager::createNewSceneModuleInstance()` returns a new `std::unique_ptr<GoalPlannerModule>` from the manager's longer-lived `node_`.

This means callback-group lifetime follows scene-module lifetime even though the executor/node in which those groups participate survives across scene-module replacement.

## Corroborating rclcpp ownership evidence

Current rclcpp source intentionally uses weak callback-group ownership across the executor/node machinery:

- `NodeBase` stores non-default callback groups as `std::vector<rclcpp::CallbackGroup::WeakPtr>`;
- executor collection APIs expose `std::vector<rclcpp::CallbackGroup::WeakPtr>`;
- executor entity records associate entities with callback groups through weak pointers;
- memory-strategy/executor maps likewise use weak callback-group and weak node references.

This makes application-side lifetime ownership material: creating a callback group does not imply that the executor will keep it alive indefinitely.

There is also a long-standing rclcpp issue, #726, reporting an `invalid guard condition` / wait-set crash when executor-visible node ownership is allowed to expire. That issue is not proof that Autoware #12460 has exactly the same root cause, but the failure family and weak-ownership design materially strengthen the lifetime hypothesis.

This changes the first reproduction goal from merely "make the planner crash" to a more precise question:

> Does the failing Autoware run contain an expired callback-group weak reference or an entity/guard-condition whose owner has been destroyed while the executor is assembling or using its wait set?

Instrumentation should answer that directly.

## Why the static workaround is not the preferred upstream design

A static callback-group pointer extends lifetime and reportedly suppresses the crash, but it broadens ownership too far.

Potential problems with a process-global static include:

- the first node constructing the static group implicitly owns it;
- multiple behavior-planner nodes in one process may unintentionally share a callback group;
- lifecycle/testing teardown can retain state across otherwise independent node instances;
- ownership becomes implicit and difficult to reason about.

The better design is to bind callback-group lifetime to an explicit owner that already survives scene-module recreation.

## Preferred structural fix: manager-owned callback groups

`GoalPlannerModuleManager` is a natural candidate because it survives individual `GoalPlannerModule` instances and already owns/accesses the node used to construct them.

Proposed direction:

1. Create the lane-parking callback group once at manager initialization or lazily on first module creation.
2. Create the freespace-parking callback group once when that feature is enabled.
3. Store both groups as manager members.
4. Pass the shared callback-group handles into each new `GoalPlannerModule`.
5. Keep timers instance-owned so a module can cancel/destroy its work while the callback-group execution context remains valid for the node/executor lifetime.
6. Do not use global statics.

An alternative long-lived node-owned registry would also be acceptable if maintainers prefer callback-group ownership outside the module manager.

## Regression and instrumentation strategy

The issue already contains a useful planning-goal abuse runner. The contribution should preserve the reproducer instead of treating it as disposable debugging code.

A robust regression campaign should:

- launch the planning simulator/component container;
- establish initial pose;
- repeatedly publish valid planning goals with randomized short intervals;
- constrain CPU resources to widen the race window;
- watch `behavior_path_planner` and its component container for disappearance/abort;
- repeat module destruction/recreation many times;
- record the number of module generations and callback-group addresses/IDs;
- log callback-group creation/destruction and whether executor weak references lock successfully during the failure window where practical;
- fail on any `failed to add guard condition to wait set` error or executor process death;
- run long enough to cover the historically rare operational failure, with a shorter deterministic stress mode for CI if possible.

The harness should become a retained test artifact so future ROS 2/Autoware changes do not silently reintroduce the lifetime bug.

## Additional correctness questions before patching

Before changing ownership, verify:

- whether the callback groups can safely be reused by successive timers after prior timers are cancelled;
- whether any timer callback can still be active when `GoalPlannerModule` destruction begins;
- whether module-owned references captured by callback lambdas remain valid through cancellation/destruction;
- whether the executor prunes expired callback groups before constructing every wait set in the affected ROS 2 version;
- whether a surviving entity can retain a guard condition after its callback-group owner expires;
- whether current supported ROS 2 distributions differ in weak callback-group cleanup behavior;
- whether multiple GoalPlannerModule instances can coexist and therefore require more than one lane/freespace execution lane.

If simultaneous instances are valid, manager ownership may need a stable pool keyed by module identity rather than exactly one group per function.

## Pass criteria

A candidate fix is not considered proven merely because the process stays alive once.

Minimum evidence:

- pre-fix stress reproduces the guard-condition failure or demonstrates expired callback-group state;
- instrumentation ties the failure to an ownership/lifetime transition rather than merely correlating with goal publication;
- post-fix run completes the same stress budget without executor abort;
- repeated module teardown/recreation leaves no accumulating callback groups/timers;
- ThreadSanitizer or equivalent race checks show no new issue where feasible;
- normal parking planning behavior remains functional;
- multi-node/component-container behavior does not cross-couple callback groups;
- CI regression retains the abuse/lifecycle scenario.

## Worldshepherd contribution decision

**Classification: P0 / REPRODUCTION + LIFETIME-OWNERSHIP FIX CANDIDATE.**

Internal screening score: **96/100** after corroborating rclcpp weak-ownership evidence.

Worldshepherd should first turn the existing abuse runner into a reproducible current-master test with callback-group lifetime instrumentation. If the lifetime hypothesis is confirmed, propose explicit manager/node-lifetime callback-group ownership rather than the global-static workaround. Until reproduction succeeds, the exact root cause remains a hypothesis even though current source, rclcpp ownership semantics, and third-party operational evidence strongly support the lifetime direction.
