# Gazebo Sim #3979 — late removal leaves a ghost physics collider

Upstream: `gazebosim/gz-sim#3979`

Claims state: **SOURCE-REVIEWED FIX DESIGN / REQUIRES GAZEBO CONCURRENCY VALIDATION**

## Failure mode

A later-priority `Update` system can request model removal after the Physics system has already scanned `EachRemoved<Model>`. The ECM entity is physically deleted at iteration end and the removal view is cleared, so the next Physics update cannot discover the removal. The gz-physics / DART backend object survives and continues colliding even though `Server::HasEntity()` reports the model absent.

The upstream reproducer demonstrates three useful controls:

1. removal before Physics runs works;
2. removal after Physics runs leaves the backend collider active;
3. retaining the ground produces the same resting height as the failing case.

That makes this a semantic-state divergence bug, not merely an ECM visibility problem.

## Safety constraint

The issue author reports that moving the existing removal call to `PostUpdate` makes the regression pass, but the production fix must account for parallel `PostUpdate` execution and backend thread-safety. Therefore Worldshepherd should not propose an unconditional backend mutation from `PostUpdate` without proving the synchronization contract.

## Preferred correction

Use a two-phase removal path:

### Phase A — observe removal marks in `PostUpdate`

`PostUpdate` is the lifecycle phase where `EachRemoved` is guaranteed to expose removals. Snapshot the identifiers and any descendant/backend handles needed for cleanup into a Physics-owned queue. Keep this phase read/record oriented if direct physics-engine mutation is not concurrency-safe.

Conceptual shape:

```cpp
void Physics::PostUpdate(
  const UpdateInfo &,
  const EntityComponentManager &_ecm)
{
  _ecm.EachRemoved<components::Model>(
    [this](const Entity &_entity, const components::Model *)
    {
      this->dataPtr->removedModels.push_back(_entity);
      return true;
    });
}
```

The actual queue type and synchronization primitive must match Gazebo's system execution guarantees; the example is illustrative only.

### Phase B — drain before the next physics step

At the beginning of the next Physics `Update`, before stepping DART/gz-physics, drain the queued removals through the existing backend cleanup path. This guarantees no deleted collider participates in another physics step while avoiding mutation from a potentially parallel `PostUpdate` callback.

Pseudo-order:

```text
iteration N:
  Physics::Update()        -> normal step
  LaterSystem::Update()    -> requests entity removal
  Physics::PostUpdate()    -> snapshots removal
  runner                   -> clears ECM removal view

iteration N+1:
  Physics::Update()
    drain queued removals  -> backend collider removed
    step physics           -> deleted object cannot collide
```

## Required invariants

- Every model observed as removed by the ECM is eventually removed exactly once from the backend.
- A late-removed collision never participates in the next physics step.
- Duplicate/removal-of-already-gone entities is idempotent and does not crash.
- Parent removal correctly removes descendants or delegates to the existing recursive cleanup path.
- Reset/world-reload does not retain stale queued entity IDs.
- Queue access is race-free under the scheduler's actual `PostUpdate` and `Update` execution model.

## Regression matrix

1. Existing upstream late-removal reproducer — must pass.
2. PreUpdate removal — must remain passing.
3. Retained-ground control — unchanged.
4. Remove parent model with multiple collision descendants.
5. Remove multiple models in the same iteration.
6. Remove then reset before the next update.
7. Request duplicate removal / remove already-gone entity.
8. Dynamic plugin with explicit priorities proving the late-remover ordering.
9. Thread/race sanitizer path where supported by Gazebo CI.
10. Back-to-back create/remove cycles to detect stale bridge/backend entries.

## Observability

A debug/trace counter for queued and drained removals would make this class of divergence diagnosable without changing normal user-visible behavior. Any metric/logging should follow existing Gazebo conventions rather than a Worldshepherd namespace.

## Worldshepherd relevance

This is a strong semantic-health example: **control-plane state says the entity is gone while physical simulation state still behaves as if it exists**. The same assurance rule applies to robots, distributed middleware, and policy systems: health requires agreement between authoritative state and the subsystem that actually produces effects.

A future Worldshepherd Gazebo fault harness should include an invariant check comparing ECM entity state, backend collision state, and observable dynamics after lifecycle operations.

## Submission boundary

Do not present the two-phase design as upstream-tested until it has been implemented against current `gz-sim` and run through the regression matrix. No competing fix PR was found during the 2026-09-12 scan, but re-check immediately before submission.
