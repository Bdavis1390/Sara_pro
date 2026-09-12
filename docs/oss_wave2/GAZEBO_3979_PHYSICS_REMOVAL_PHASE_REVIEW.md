# Gazebo gz-sim #3979 — Physics removal-phase source review

Upstream target: `gazebosim/gz-sim#3979`

Claims state: **SOURCE-REVIEWED / OPEN / NO MATCHING FIX PR FOUND / REQUIRES CONCURRENCY DESIGN REVIEW**

## Confirmed current-main phase ordering

`Physics` currently implements:

```text
ISystemConfigure
ISystemConfigurePriority
ISystemReset
ISystemUpdate
```

It does not implement `ISystemPostUpdate`.

Inside `Physics::Update()` current main executes:

```text
CreatePhysicsEntities
UpdatePhysics
Step
ChangedLinks
UpdateSim
RemovePhysicsEntities
```

Therefore `RemovePhysicsEntities()` runs before any later-priority `Update` system has had a chance to request removal.

The ECM API explicitly documents `EachRemoved` as a PostUpdate-only operation. Current `RemovePhysicsEntities()` consumes `EachRemoved` state despite being called from `Update`.

## Why the ghost collider is structurally possible

If a later `Update` system requests deletion after Physics has completed its removal scan:

```text
Physics Update:       no removal observed
later Update system:  requests removal
PostUpdate/end step:  ECM removal information is available/then cleared
next Physics Update:  ECM entity already gone; prior removal view no longer available
physics backend:      old model/collider mapping remains
```

The user-visible result is an ECM model that is gone while the physics engine continues simulating its collision object.

## Important implementation constraint

A deferred cleanup cannot assume that storing only the removed model's `Entity` ID is sufficient.

The existing `RemovePhysicsEntities()` model path uses ECM hierarchy queries while processing the removed model, including child links/collisions/joints, before erasing physics-side mappings. Once the ECM physically deletes that hierarchy, those relationships may no longer be recoverable from the parent entity ID alone.

Any phase-correct redesign therefore needs either:

1. enough hierarchy/cleanup information snapshotted during PostUpdate, while the removal view is valid; or
2. a physics-side ownership map rich enough to remove descendants without consulting already-deleted ECM hierarchy.

The second option may be architecturally cleaner but is a larger change.

## Recommended minimal direction

### PostUpdate: observe and snapshot

Add `ISystemPostUpdate` and, during PostUpdate, consume the documented `EachRemoved` view. Build a bounded pending-cleanup record containing exactly the identifiers needed to remove:

```text
model physics object / map entry
child link map entries
child collision map entries
child joint map entries
related top-level-model bookkeeping
relevant detachable-joint bookkeeping if applicable
```

Do not mutate a physics backend from PostUpdate until thread-safety/phase guarantees are verified. PostUpdate systems may execute under different concurrency expectations than the existing Physics Update path.

### Next Update, before physics stepping: drain cleanup

At the beginning of the next safe Physics `Update`, drain the snapshotted cleanup queue before `UpdatePhysics()` and before `Step()`.

Target ordering:

```text
Create/registration reconciliation as required
DRAIN REMOVALS CAPTURED LAST POSTUPDATE
UpdatePhysics
Step
UpdateSim
...
```

This ensures a collider marked for removal in iteration N cannot participate in the physics step for iteration N+1.

The exact placement relative to `CreatePhysicsEntities` needs a re-add/same-ID lifecycle test; do not assume create-before-remove or remove-before-create semantics without that test.

## Alternative direction

Move backend removal directly into `PostUpdate` only if Gazebo's system-execution contract and the selected physics backends guarantee that those mutations are safe there. The issue reporter observed this as a diagnostic fix, but that is not enough evidence to make it the production design.

## Regression matrix

### A. Early removal control

Removal requested in PreUpdate. Existing behavior should remain correct: backend collider gone before the next step.

### B. Late Update removal — primary regression

A system with later Update priority requests model removal after Physics runs. Assert:

```text
ECM says model absent
next physics step does not collide with removed geometry
physics-side entity maps no longer contain model/children
```

### C. Nested model removal

Remove a model with nested links, joints, and collisions. Assert all relevant physics-side mappings are cleaned without leaving descendants.

### D. Detachable joints

Exercise a removed model participating in detachable-joint bookkeeping. Preserve the existing required cleanup ordering.

### E. Remove and recreate

Remove and recreate equivalent geometry across adjacent iterations. Ensure pending cleanup cannot delete the newly created backend object or leave duplicate mappings.

### F. Many create/remove cycles

Track map sizes and collision behavior over repeated cycles to detect resource leaks or stale mappings.

## Evidence requirement

The regression must prove both representations converge:

```text
ECM entity truth == physics backend/map truth
```

Checking only `Server::HasEntity()` is insufficient because #3979 demonstrates that ECM truth can already be correct while the backend is stale.

## Upstream-safe next step

Submit the reproduction/regression first or discuss the snapshot record with maintainers before a production patch. The root phase mismatch is source-confirmed, but the safe mutation phase and minimum snapshot data still require upstream concurrency review.
