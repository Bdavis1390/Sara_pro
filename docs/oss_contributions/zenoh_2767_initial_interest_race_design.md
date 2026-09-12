# Zenoh #2767 — close the querier initial-interest race after queryable reconnect

Upstream issue: `eclipse-zenoh/zenoh#2767`
Reviewed upstream main: `646f2d1b730e584a570015a77bee9f6db08be9d1`
Claims state: **SOURCE-REVIEWED FIX HYPOTHESIS / REQUIRES MAINTAINER SEMANTICS DECISION + RUST REPRODUCTION**

## Observed failure

After a remote queryable disconnects and reconnects behind a router, a requester can declare a new querier and immediately call `get()`. The configured query timeout is 10 seconds, but the first call can complete with zero replies after only milliseconds. The router sees the querier's interest and sends the current queryable declaration plus `DeclareFinal`, yet it never receives the failing query request. A later `get()` on the same querier succeeds.

This is a semantic-liveness failure: the application receives a definitive-looking empty result while the querier's initial remote-queryable snapshot is still converging.

## Source findings

### 1. `Querier::get()` does pass the configured timeout

`zenoh/src/api/builders/querier.rs` delegates to `Session::query(...)` with `self.querier.timeout` and `Some(self.querier.id)`. The builder is therefore not silently replacing the timeout.

### 2. A newly declared remote querier becomes usable before its initial current-state interest is finalized

`SessionState::register_querier()` registers the local querier state. `Session::declare_querier_inner()` then sends:

```rust
Interest {
    id,
    mode: InterestMode::CurrentFuture,
    options: InterestOptions::KEYEXPRS + InterestOptions::QUERYABLES,
    ...
}
```

and returns `Ok(id)` without awaiting the matching `DeclareFinal` for that current-state snapshot.

That means the public `Querier` can be returned to the application while the queryable routing view associated with its initial `CurrentFuture` interest is still being populated.

### 3. The routing layer already models current-interest completion explicitly

The routing hats keep `pending_current_interests`. For a client current interest, `route_declare_final()` removes the corresponding pending interest and cancels its cleanup token. Therefore Zenoh already has a concrete protocol event that means:

> the initial current-state response stream for this interest has completed.

The missing synchronization is between that protocol completion and the API object's readiness to make routing-sensitive decisions.

### 4. An empty query route is finalized immediately

`zenoh/src/net/routing/dispatcher/queries.rs::route_query()` computes the route from the current routing table. If the resulting direction set is empty, it sends `ResponseFinal` immediately:

```text
Send final reply (no matching queryables or not master)
```

The configured query timeout is only used for pending routed queries. It is not a grace period for a routing table that is still being initialized.

That behavior is reasonable for a genuinely empty, already-synchronized route. It is problematic during the narrow initial-interest window above.

## Related evidence

- #2205 fixed a queryable-info cleanup/update case and added matching-status session-drop tests, but it does not make querier declaration wait for its initial current-state snapshot.
- #2516 reports the same user-visible class of premature zero-reply completion when queryable routing state is transiently absent. Its reporter clarified that the behavior persists even when Zenoh APIs are not called from a receive callback.

These issues do not prove a single root cause across every topology, but they strengthen the requirement that a transiently incomplete route must not be indistinguishable from a synchronized empty route.

## Fix objective

Preserve existing fast empty-route behavior **after routing state is synchronized**, while preventing an immediate false-empty result during the new querier's initial `CurrentFuture` synchronization.

Do **not** globally reinterpret `timeout` as "wait for a queryable to appear." That would alter established behavior for truly absent queryables and could add unwanted latency to every query.

## Preferred implementation direction

Track initial-interest readiness for remote queriers and make the first routing-sensitive query respect it.

A minimal conceptual state is:

```rust
QuerierState {
    ...
    initial_interest: Ready | Pending(InterestId),
}
```

The exact state should use Zenoh's existing interest/cancellation primitives rather than inventing a second protocol tracker.

### Option A — declaration awaits initial `DeclareFinal`

Make remote `declare_querier(...).await` resolve only after the initial `CurrentFuture` snapshot reaches `DeclareFinal`.

Advantages:
- simple external contract: returned querier is routing-ready;
- no special first-query path;
- matching state and query routing start from the same completed snapshot.

Risks:
- changes declaration latency and potentially the current synchronous `Wait` implementation shape;
- needs bounded failure/timeout semantics if the current-interest exchange cannot complete;
- may be too strong for applications that only want a declaration handle immediately.

### Option B — return immediately, but gate routing-sensitive `get()` until initial synchronization finishes

Keep current declaration latency, record the initial interest as pending, and have `Querier::get()` / `Session::query(..., querier_id=Some(...))` distinguish:

```text
route empty + initial sync complete  -> immediate empty final (existing behavior)
route empty + initial sync pending   -> wait/defer until DeclareFinal or bounded sync failure
route non-empty                      -> send normally
```

Advantages:
- preserves fast querier construction;
- narrows the behavior change to the race window;
- avoids globally delaying normal empty-route queries.

Risks:
- requires a safe waiter/notification path from interest completion into API session state;
- must handle querier undeclare/session close while a get is waiting;
- must not hold session/routing locks across await points.

**Recommendation:** Option B appears less disruptive, but maintainers should choose after confirming intended API semantics.

## Critical implementation constraint

Do not simply sleep/retry on an empty route. Readiness must be tied to the actual `DeclareFinal` (or the interest's bounded failure/cleanup), otherwise the race becomes timing-dependent and DDIL behavior remains nondeterministic.

The waiter should be edge-trigger safe:

1. inspect whether initial sync is already complete;
2. if pending, register/obtain a completion notifier under the same state synchronization domain;
3. release locks;
4. await completion/cancellation;
5. re-evaluate routing state before sending the query.

This avoids a lost-wakeup race between checking `Pending` and installing the waiter.

## Deterministic regression test

Build the test around the existing client → router → client/queryable topology from #2767.

Required sequence:

1. Start router and requester client.
2. Start responder client and declare a queryable on `repro/service/rpc`.
3. Confirm a baseline query succeeds.
4. Disconnect the responder and confirm routing state removes the old queryable.
5. Reconnect the responder and redeclare the same queryable.
6. On the requester, declare a **new** querier and call `get()` immediately, with no arbitrary sleep.
7. Use a test-only barrier/hook to delay delivery/processing of the initial queryable declaration or its `DeclareFinal` so the race is deterministic.
8. Assert the first `get()` does **not** complete as an immediate false empty while initial sync is pending.
9. Release the barrier; assert the request reaches the router and the queryable receives it, then assert the reply arrives.

Controls:

- with no queryable anywhere and initial sync completed, an empty route should retain the project's documented existing completion semantics;
- an already-existing querier should continue operating across ordinary queryable disappearance/reappearance according to existing routing behavior;
- `QueryTarget::BestMatching` and `QueryTarget::All` should both be exercised;
- session close / querier undeclare during pending initialization must cancel safely;
- a lost or rejected initial interest must resolve through a bounded error/cancellation path rather than hang indefinitely;
- matching listeners/status must still report the completed current snapshot correctly.

## Acceptance criteria

1. The supplied #2767 topology reproduces the baseline premature empty completion deterministically.
2. After the fix, a fresh querier cannot emit a false-empty result solely because its initial current-interest snapshot is unfinished.
3. Queries against a synchronized, genuinely empty routing table are not globally delayed by the query timeout.
4. No session/routing lock is held while awaiting interest completion.
5. Declaration/get cancellation and session shutdown remain bounded.
6. No duplicate query is emitted when synchronization completes.
7. Existing reconnect/matching tests remain green.

## Worldshepherd mapping

This is an OVERWATCH/SARA semantic-health problem: **protocol liveness and API truth must agree**. A temporary control-plane convergence window must not be reported to the caller as a durable "no responder" fact.

The reusable invariant is:

> **Do not convert incomplete control-plane knowledge into a definitive negative application result.**

## Ownership and submission boundary

As of the 2026-09-12 audit:

- #2767 is open;
- no assignee is listed;
- the issue has no ownership comments;
- no matching implementation PR was found.

Before any external submission, re-check issue/PR ownership and current Zenoh contribution/AI-assistance requirements. This artifact is a source-reviewed fix hypothesis, not a compile-tested patch or accepted upstream design.
