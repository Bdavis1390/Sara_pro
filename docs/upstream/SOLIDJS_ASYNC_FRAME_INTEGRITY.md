# SolidJS upstream contribution lane — Async Frame Integrity

**Status:** CANDIDATE / UNVERIFIED LOCALLY  
**Upstream target:** `solidjs/solid:next`  
**Prepared:** 2026-09-14

## Objective

Contribute test-only coverage that exercises interactions among already-ruled SolidJS async semantics rather than proposing new semantics.

The target cross-rule cases are:

1. **A29 × pending probes** — multiple tracked computations begin reading a live transaction's staged value at different points in the same held transaction. They must join the hold while `isPending` remains observable and non-participating.
2. **A30 × stale async landing** — a held memo switches dependencies; both the old committed dependency and the new staged dependency change before replacement commit; no intermediate frame may mix those worlds.
3. **A29 × A30** — a late conditional reader begins consuming a dependency-switched memo while the replacement frame is held; it must not publish staged state into the mainline frame.

## Why this is worth upstreaming

SolidJS already pins A29 and A30 individually. The next useful step is **cross-rule integrity coverage**. A runtime change can satisfy each rule in isolation while failing when staged reads, dependency switching, stale flights, probes, and multiple late readers interleave.

This lane applies the Worldshepherd evidence discipline in a generic upstream form:

`observable invariant -> deterministic schedule -> exact replay trace -> regression gate`

No Worldshepherd-specific runtime dependency or branding is proposed for SolidJS itself.

## Candidate upstream file

`packages/signals/tests/async-frame-integrity.test.ts`

## Candidate PR title

`test(signals): cover async frame integrity across staged-read and committed-dependency rules`

## Candidate PR body

Test-only coverage for interactions among existing ruled semantics.

It adds deterministic interleaving cases for:

- A29 + `isPending`: multiple computations begin reading a staged signal at different points in the same held transaction. They must join the hold, while the pending probe remains observable.
- A30 + stale async landing: a held memo switches from one dependency to another, then both the old committed dependency and the new staged dependency change before the replacement frame lands.
- A29 + A30 together: a late reader begins consuming a dependency-switched memo while the replacement frame is held.

No new semantic rule is proposed. The intent is to make frame-integrity regressions easier to catch when changes touch read visibility, dependency trimming, transition entry, or stale-flight handling.

The harness follows the deterministic manual-clock/settle pattern already used in the signals async regression tests so each failure reduces to an exact sequence of observable frames.

## Verification gate

Before upstream submission, run against the current `next` branch:

```bash
pnpm vitest packages/signals/tests/async-frame-integrity.test.ts
pnpm vitest packages/signals/tests/held-conditional-memo.test.ts
pnpm vitest packages/signals/tests/latest-isPending-consistency.test.ts
```

Then run the SolidJS package/monorepo gates required by maintainers.

## Claims control

Until those commands execute successfully on a real SolidJS checkout, this remains **UNVERIFIED LOCALLY**. It is an upstream-ready candidate design and test artifact, not a claim of a passing patch.
