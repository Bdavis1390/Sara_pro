# Gazebo gz-sim #3977 — ParticleEmitter lifecycle source review

Upstream target: `gazebosim/gz-sim#3977`

Claims state: **SOURCE-REVIEWED / OPEN / NO MATCHING FIX PR FOUND / DESIGN AGREEMENT REQUIRED**

## Confirmed current-main behavior

`ParticleEmitterPrivate` keeps several long-lived representations of an emitter:

```text
transport Node subscription
emitterTopicMap: topic -> Entity
userCmd: Entity -> pending command
serviceMsg: cached ParticleEmitter_V response
```

`ParticleEmitter::PreUpdate()` currently:

1. scans `EachNew<ParticleEmitter, ParentEntity, Pose>`;
2. subscribes to the emitter command topic;
3. inserts `emitterTopicMap[topic] = entity`;
4. appends the emitter to the cached `serviceMsg`;
5. later drains `userCmd` into `ParticleEmitterCmd` components.

The class implements only `ISystemConfigure` and `ISystemPreUpdate`. Current main contains no corresponding removal pass and no `ISystemPostUpdate` implementation.

The ECM contract is important: `EntityComponentManager::EachRemoved` is documented to be called only from a System's `PostUpdate` callback. Therefore adding cleanup opportunistically inside the existing `PreUpdate` path would violate the documented lifecycle contract.

## Failure model

The issue demonstrates three representations that can diverge after entity removal:

```text
ECM truth:          emitter/model removed
service truth:      emitter remains in /particle_emitters response
transport truth:    old command topic remains subscribed/routable
pending-command:    stale Entity can still receive queued command state
```

This is a direct semantic-health failure: the authoritative entity graph says the object is gone while externally observable interfaces continue claiming or routing to it.

## Recommended contribution architecture

Do not patch each container independently. Introduce one emitter-owned lifecycle record or equivalent internal abstraction so addition/removal has a single ownership boundary.

A conceptual record needs to bind, at minimum:

```text
entity
command_topic
service representation identity
subscription ownership/lifetime
```

The exact transport subscription/unsubscription API must be confirmed against the gz-transport version used by current gz-sim before implementation. Do not assume that removing a topic subscription is safe if multiple logical emitters can share a topic; either forbid/handle duplicates explicitly or track the subscription ownership semantics chosen by maintainers.

## Removal phase

Add `ISystemPostUpdate` to `ParticleEmitter` and observe removed `components::ParticleEmitter` entities there.

For each removed emitter, cleanup must be coordinated under the same mutex discipline used by command routing and service state:

```text
remove topic -> entity route
remove / invalidate pending userCmd for entity
remove emitter from service representation
release/unsubscribe the owned transport callback safely
```

The callback must not be able to repopulate `userCmd` for a removed entity after cleanup. That creates a concurrency requirement between the transport callback and PostUpdate removal path, not merely a container-erasure requirement.

## Regression matrix

### A. Normal lifecycle

1. Create one particle emitter.
2. Confirm it appears exactly once in the service response.
3. Publish a command and confirm it reaches the live ECM entity.
4. Remove the emitter/model recursively.
5. Confirm the ECM entity is absent.
6. Confirm service response no longer contains it.
7. Publish on the old topic and confirm no command is routed to the deleted entity.

### B. Remove with pending command

Arrange for a command to be pending when removal is observed. After removal, no `ParticleEmitterCmd` component creation should be attempted for the deleted entity.

### C. Re-add after removal

Create a new emitter using the same logical topic after cleanup. Exactly one active route should exist and commands must target only the new entity.

### D. Multiple emitters

Remove one emitter while another remains. Service output, routes, and command delivery for the survivor must be unchanged.

### E. Repeated create/remove cycles

Run many lifecycle cycles and assert that route/service-record counts return to baseline each time. This catches silent accumulation even when functional behavior appears correct for a few cycles.

## Evidence to expose in tests

A useful test should independently observe:

```text
ECM entity count
service emitter count
active logical route count
command-delivery target
stale component-creation errors
```

Process survival alone is irrelevant to this bug class.

## Upstream-safe next step

The next contribution should be a regression test plus maintainer discussion on subscription ownership and service-message representation. Once that contract is settled, the production patch should make lifecycle ownership explicit rather than layering ad-hoc erase calls over the existing append-only structures.
