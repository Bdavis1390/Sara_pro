# Worldshepherd PoO Technical State Engine

## Purpose

The state engine turns already-governed PoO evidence into **candidate technical ownership states** while keeping external authority out of scope. It does not adjudicate legal title, move value, rotate credentials, or execute a transfer.

The engine binds two predecessor chains at once:

```text
PoO lineage:  PoO[n] -> PoO[n+1]
COC lineage:  COC[n] -> COC[n+1]
```

A transfer or recovery is blocked if either predecessor does not equal the active technical state.

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

## Transfer supersession

A transfer candidate additionally requires:

- governed transfer readiness;
- current asset equality;
- current claimant/current-owner equality;
- transfer predecessor equal to active PoO digest;
- recipient COC valid for the recipient and new control fingerprint; and
- recipient COC predecessor equal to the active COC digest.

The result is `TECHNICAL_STATE_SUPERSESSION_READY`, not an executed transfer. `technical_state_committed`, `legal_title_changed`, `live_value_moved`, and `external_transfer_executed` remain false.

## Recovery supersession

Recovery uses the same dual-predecessor rule but must preserve the active claimant. The replacement COC may bind a new control surface, but the state engine does not rotate the credential itself.

## Fork detection

The state engine can project technical states into the existing PoO lineage verifier. Two successor states from one active PoO create a detectable ownership-lineage fork and are not silently resolved.

## Multi-asset registry

`WS-POO-TECHNICAL-REGISTRY-V1` groups states by asset and requires every asset lineage to be internally consistent. It blocks:

- multiple genesis roots for one asset;
- duplicate technical states;
- PoO digest reuse across registry states;
- lineage forks/cycles/missing predecessors;
- malformed generations; and
- missing or ambiguous active technical tips.

A valid registry exposes one active technical PoO and claimant per asset. It explicitly reports `legal_registry_authority = false` and `legal_title_established = false`.

## Claims boundary

This layer is an internal evidence/state model only. It does not claim:

- legal ownership or custody adjudication;
- government registry authority;
- external transfer execution;
- live-value movement;
- key or credential rotation;
- external validation/certification; or
- that PoW, PoC, COC, or PoS alone proves ownership.
