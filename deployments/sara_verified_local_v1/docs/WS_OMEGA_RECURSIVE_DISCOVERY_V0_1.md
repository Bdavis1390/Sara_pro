# WS-OMEGA Recursive Discovery v0.1

## Purpose

WS-OMEGA is the governed recursive-discovery layer for Worldshepherd SARA. It operationalizes the CRE1AWS directive to search with effectively non-terminal breadth, depth, and recursion while preserving finite compute, reproducibility, claims control, and human authorization.

The implementation does **not** claim literal mathematical infinity. Instead it implements:

- no terminal global search depth;
- bounded work in each execution cycle;
- persistent frontier and overflow backlog;
- recursive generation of new observations, hypotheses, contradictions, negative-space questions, experiments, partner candidates, opportunities, standards gaps, prior-art checks, and risks;
- canonical state and report digests;
- explicit routes into existing Worldshepherd controls;
- fail-closed claim promotion and external execution.

## Existing Worldshepherd integration

WS-OMEGA is intentionally a thin layer over existing SARA functions rather than a parallel assurance system.

| WS-OMEGA node | Existing route |
| --- | --- |
| domain | ECHO, SARA-ADE, SARA-COVERAGE |
| observation | ECHO, SARA-ADE, PVK |
| hypothesis | SARA-ADE, PVK, RED-TEAM, PRIME |
| contradiction | SARA-CONTRADICTION, PVK, RED-TEAM, PRIME |
| negative-space observation | SARA-ADE, SARA-CONTRADICTION, PVK |
| experiment | SARA-ADE, PVK, ECHO, PRIME |
| partner | PARTNER-SCREENING, PRE, ECHO |
| opportunity | PRE, PARTNER-SCREENING, ECHO |
| standard | PRE, ECHO, PRIME-TEVV |
| prior art | PRE, SARA-CONTRADICTION, PRIME |
| risk | PRIME, OVERWATCH, RED-TEAM |

PVK is treated as the controlled physics/scientific-validation branch while it remains under its existing draft/host-validation governance. WS-OMEGA does not elevate PVK or any domain campaign maturity.

## Recursive state machine

```text
INGEST / SEED
    |
    v
PRIORITIZED FRONTIER
    |
    +--> EVIDENCE / CONTRADICTION / NEGATIVE-SPACE CHECKS
    |
    +--> HYPOTHESIS / EXPERIMENT / OPPORTUNITY / PARTNER GENERATION
    |
    v
BOUNDED CYCLE
    |
    +--> ACTIVE FRONTIER
    +--> OVERFLOW BACKLOG
    +--> EXPLORED LINEAGE
    |
    v
CANONICAL STATE DIGEST
    |
    v
NEXT CYCLE
```

There is deliberately no terminal global-depth field. A resource boundary is applied per cycle, not to the overall lineage.

## Governance invariants

The following are hard-coded fail-closed invariants:

1. `claim_promotion_allowed=false` for every discovery node.
2. `physical_validation_claimed=false` for every discovery node.
3. `external_execution_performed=false` for every discovery node.
4. `allow_claim_promotion=false` in the recursive policy.
5. `allow_external_execution=false` in the recursive policy.
6. negative evidence must be retained.
7. human review remains required for any later promotion outside WS-OMEGA.
8. a cycle report explicitly records that literal physical infinity is **not** claimed.

The engine may identify a candidate action or route, but existing SARA/PRIME authorization remains the gate for consequential execution.

## Priority behavior

The frontier scorer deliberately values:

- source quality and confidence;
- falsifiability;
- cross-domain relevance;
- contradictions and negative-space observations;
- experiments and prior-art checks.

This prevents the recursion loop from becoming a novelty-only idea generator. A high-value contradiction may outrank a speculative new hypothesis.

## Persistence and resumability

`RecursiveDiscoveryState` preserves:

- cycle index;
- active frontier;
- overflow backlog;
- explored node IDs;
- prior-state digest.

No branch is silently discarded solely because the active frontier is full; overflow moves to the backlog.

## Command-line interface

Initialize from a seed file:

```bash
ws-omega-recursion init \
  --seeds fixtures/omega_discovery_seeds_v1.json \
  --out var/omega/state.json
```

Advance one governed cycle with externally generated proposals:

```bash
ws-omega-recursion cycle \
  --state var/omega/state.json \
  --proposals var/omega/proposals.json \
  --out-state var/omega/state.next.json \
  --out-report var/omega/cycle-report.json
```

Verify state and report custody:

```bash
ws-omega-recursion verify \
  --state var/omega/state.next.json \
  --report var/omega/cycle-report.json
```

The CLI performs no web collection, messaging, physical actuation, purchasing, proposal submission, or claim promotion. External collectors can supply candidate proposals, but WS-OMEGA only validates, routes, ranks, and preserves them.

## Claims boundary

Current implementation classification: **IMPLEMENTED IN SOFTWARE candidate pending protected CI on the exact branch head**.

It does not establish:

- autonomous scientific discovery in the physical world;
- new physics;
- physical validation of any Worldshepherd technology;
- infinite computation;
- continuous operation on a physical Worldshepherd host;
- external collection capability;
- partner engagement;
- opportunity eligibility or award probability;
- authority to execute external or consequential actions.

Actual-host persistence, scheduler integration, external-source adapters, and any promotion workflow remain separate evidence gates.
