# Worldshepherd PoO Technical State Engine

## Purpose

The state engine turns already-governed PoO evidence into **candidate technical ownership states** while keeping external authority out of scope. It does not adjudicate legal title, move value, rotate credentials, write the durable registry, or execute a transfer.

The current architecture deliberately separates five different statements that must never be conflated:

```text
1. evidence ready
2. local technical-state candidate ready
3. full state-lineage governed candidate ready
4. optimistic-concurrency registry commit candidate ready
5. durable registry commit / external ownership change
```

This repository implements and audits stages 1–4. Stage 5 remains a separate human-governed action and is never asserted by these guards.

## Dual technical lineage

The engine binds two predecessor chains at once:

```text
PoO lineage:  PoO[n] -> PoO[n+1]
COC lineage:  COC[n] -> COC[n+1]
```

`WS-POO-STATE-LINEAGE-V1` additionally verifies generation continuity. A state history is therefore valid only when the PoO lineage, COC lineage, and generation sequence all remain internally consistent.

## First-class COC

`security/poo/coc_guard.py` defines `WS-POO-COC-V1`.

A COC evidence object binds:

- asset identity;
- claimant identity;
- control-surface/key fingerprint;
- custody evidence reference;
- point-of-custody reference;
- challenge-response reference;
- observation/expiry times; and
- previous COC digest.

COC validity is fail-closed across asset binding, claimant binding, current control/custody, challenge response, custody-chain continuity, freshness, and revocation state.

A valid COC means only `TECHNICAL_COC_ATTESTATION`. It never sets legal custody or legal title.

## Technical ownership state

`WS-POO-TECHNICAL-STATE-V1` records:

```text
asset_id
claimant_id
active_poo_digest
active_coc_digest
control_key_fingerprint
title_reference
generation
source_event_type
previous_poo_digest
previous_coc_digest
```

Every candidate state hard-codes external authority boundaries to false.

## Bootstrap

A technical genesis state requires:

1. a valid genesis PoO with no `previous_poo_digest`;
2. a valid COC for the same asset, claimant, and control fingerprint; and
3. a genesis COC with no `previous_coc_digest`.

If any binding disagrees, no candidate technical state is produced.

## Local transfer/recovery candidates

A transfer candidate requires base transfer readiness plus:

- current asset equality;
- current claimant/current-owner equality;
- transfer predecessor equal to the active PoO digest;
- recipient COC valid for the recipient and new control fingerprint; and
- recipient COC predecessor equal to the active COC digest.

Recovery uses the same dual-predecessor rule but preserves the active claimant. A replacement COC may bind a new control surface, but the state engine does not rotate the credential itself.

A successful local result means only `TECHNICAL_STATE_SUPERSESSION_READY`. It is not yet evidence that the historical state set is globally coherent.

## Full state-lineage governance

`security/poo/state_governance_guard.py` defines:

`WS-POO-STATE-GOVERNANCE-V1`

Before a transfer/recovery candidate is promoted into the governed path, the entire supplied state history is evaluated by `evaluate_state_lineage`.

A governed candidate requires:

```text
base PoW/PoC/COC/PoS evidence ready
AND PoO lineage valid
AND COC lineage valid
AND generation continuity valid
AND exactly one active technical PoO tip
AND local transition binds to that active state
```

This means otherwise-perfect transfer/recovery evidence is still blocked when any of these conditions is detected:

- forked PoO lineage;
- cyclic/missing PoO predecessor;
- broken COC predecessor;
- duplicate/reused COC state;
- generation gap or duplicate generation;
- stale PoO predecessor;
- stale COC predecessor;
- current-owner/claimant mismatch; or
- unresolved/ambiguous active technical tip.

Only a clean transfer path reports:

`STATE_TRANSFER_READY_WITH_LINEAGE_GUARD`

and only a clean recovery path reports:

`STATE_RECOVERY_READY_WITH_LINEAGE_GUARD`.

The governance decision still hard-codes:

```text
technical_state_committed = false
conflict_winner_selected = false
lineage_auto_resolved = false
legal_title_changed = false
live_value_moved = false
external_transfer_executed = false
```

A fork is therefore quarantined; Worldshepherd does not pick a claimant as the legal winner.

## Multi-asset technical registry

`WS-POO-TECHNICAL-REGISTRY-V1` groups states by asset and requires every asset lineage to be internally consistent. It blocks:

- multiple genesis roots for one asset;
- duplicate technical states;
- PoO digest reuse across registry states;
- lineage forks/cycles/missing predecessors;
- malformed generations; and
- missing or ambiguous active technical tips.

A valid registry exposes one active technical PoO and claimant per asset. It explicitly reports `legal_registry_authority = false` and `legal_title_established = false`.

## Optimistic-concurrency commit guard

`security/poo/commit_guard.py` defines:

`WS-POO-REGISTRY-COMMIT-V1`

The guard uses compare-and-swap semantics. A caller supplies the registry digest it evaluated. Before producing a candidate mutation the guard rechecks:

- the expected digest still equals the current registry digest;
- the transition is still a valid candidate;
- the current registry remains internally consistent;
- the predecessor remains the active PoO tip;
- the predecessor remains the active COC tip;
- generation advances by exactly one;
- the candidate is not a replay/duplicate; and
- the proposed post-commit registry remains internally consistent.

A stale registry snapshot therefore fails instead of being silently rebased.

## Full registry-commit governance

`security/poo/registry_governance_guard.py` defines:

`WS-POO-REGISTRY-GOVERNANCE-V1`

This guard composes the full state-lineage decision with the optimistic-concurrency commit guard:

```text
Registry_commit_candidate_ready =
    lineage_governed_state_transition_ready
    AND state_lineage_valid
    AND expected_registry_digest == current_registry_digest
    AND commit_guard_ready
    AND post_candidate_registry_valid
```

Only that combined state reports:

`REGISTRY_COMMIT_READY_WITH_FULL_GOVERNANCE`.

If another actor changes the registry after evaluation, the state becomes:

`REGISTRY_COMMIT_BLOCKED_STALE_SNAPSHOT`.

The resulting object is still only a **commit candidate**. It hard-codes:

```text
technical_registry_committed = false
durable_registry_write_authorized = false
conflict_winner_selected = false
lineage_auto_resolved = false
legal_title_changed = false
live_value_moved = false
external_transfer_executed = false
```

## Governance Decision V3 audit path

`security/poo/audit_projection.py` now emits:

`WS-POO-GOVERNANCE-DECISION-V3`

and SARA records it as:

`WS-POO-SARA-AUDIT-EVENT-V3`.

The existing claim, COC, transfer, recovery, local state-transition, and registry-health operations remain available. V3 adds:

- `STATE_LINEAGE_INTEGRITY`
- `GOVERNED_STATE_TRANSITION`
- `REGISTRY_COMMIT_READINESS`

The V3 projection records:

- whether state lineage was checked;
- full state-lineage validity;
- PoO-lineage validity;
- COC-lineage validity;
- generation validity;
- fork/cycle flags;
- active technical PoO tip when valid;
- lineage issue count;
- registry commit readiness;
- optimistic-concurrency check/match;
- expected/current/candidate registry digests; and
- candidate technical-state digest.

The native SARA adapter rejects contradictory combinations. In particular:

- valid lineage cannot report issues, forks, or cycles;
- invalid lineage cannot expose an active technical tip;
- a governed ready transition must reference the active PoO tip;
- a ready registry commit requires valid state lineage;
- a ready registry commit requires the expected/current registry digests to match;
- a ready registry commit requires candidate registry/state digests; and
- no audit record can grant durable-write, ownership-change, live-value, legal-title, winner-selection, or automatic-resolution authority.

## Worldshepherd control-plane interpretation

For a conflict or stale snapshot:

- **ECHO** custodizes the evidence and conflicting hashes;
- **PRIME** blocks promotion/commit readiness;
- **SARA** holds the workflow for human review/re-evaluation;
- **OVERWATCH** exposes the lineage conflict or stale-snapshot alert.

The modules identify technical inconsistency; they do not adjudicate legal title.

## Claims boundary

This layer is an internal evidence/state model only. It does not claim:

- legal ownership or custody adjudication;
- government registry authority;
- durable registry write authority;
- automatic conflict-winner selection;
- automatic lineage resolution;
- external transfer execution;
- live-value movement;
- key or credential rotation;
- external validation/certification; or
- that PoW, PoC, COC, or PoS alone proves ownership.
