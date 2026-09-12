# WS-RI Checkpoint and Bounded Feedback Increment v0.1

## Purpose

This increment extends Worldshepherd Recursive Improvement in two bounded directions:

1. checkpoint the WS-RI lifecycle ledger into ECHO provenance custody and verify later inclusion in an ECHO signed checkpoint;
2. run finite, resumable ECHO-to-WS-RI feedback cycles without granting claim-promotion, deployment, external-execution, or physical-actuation authority.

It reuses the existing WS-RI lifecycle, ECHO semantic event store, and ECHO signed checkpoint chain rather than creating a parallel trust system.

## Ledger custody

`ImprovementLedger` persists lifecycle records in SQLite. Each entry chains to the prior global record and the prior record for the same improvement ID. The ledger enforces allowed lifecycle transitions, deduplicates exact proposal replay, and recomputes proposal and record digests during chain verification.

This is application-level custody evidence. It is not by itself evidence of immutable/WORM retention, external anchoring, third-party attestation, certification, or deployment authority.

## Operational evidence bridge

Ordinary ECHO traffic does not become an improvement proposal. An accepted audit event must carry an explicit `_ws_improvement_signal` object before `operational_improvement.py` will translate it.

The adapter preserves ECHO event identity and semantic digest, defaults unspecified capability maturity to `NOT_CURRENTLY_CLAIMED`, leaves target maturity unset, and emits only `PROPOSED` records. An `OVERWATCH` source label remains a producer-contract label and is not proof of a separately validated runtime.

## Ledger checkpoint into ECHO

`build_ledger_checkpoint()` requires a non-empty, verifying WS-RI ledger and records the current record count, head sequence, head record digest, state counts, timestamp, claims boundary, and canonical checkpoint digest.

`build_ledger_checkpoint_event()` wraps the checkpoint in an ECHO-valid audit event using the existing stable outbox ID and `AT_LEAST_ONCE` delivery contract. The event deliberately does not contain `_ws_improvement_signal`, preventing the custody checkpoint from becoming its own new improvement candidate.

`ingest_ledger_checkpoint_into_echo()` establishes ECHO provenance custody only. `verify_signed_echo_membership()` first invokes the existing ECHO checkpoint verifier with a trusted key fingerprint and then requires exact event-ID and semantic-digest membership. Only that latter state is treated as locally signed ECHO inclusion.

## Bounded feedback cycle

`run_operational_feedback_cycle()` is a finite, resumable collector. Default bounds are 64 ECHO events scanned per cycle and 32 improvement proposals handled per cycle.

The policy model fails closed if claim promotion, deployment, or external execution is enabled. Ordinary events advance the cursor without creating proposals. Explicit signals are translated to `PROPOSED` records and appended or deduplicated in the WS-RI ledger. If the proposal budget is reached, the cursor stops before the deferred signal so the next cycle can process it.

The module is not a background daemon. Repeated execution requires an existing authorized scheduler or operator.

## Claims boundary

The resulting software path is:

```text
ECHO accepted events
  -> bounded feedback cycle
  -> explicit WS-RI proposal
  -> lifecycle ledger
  -> qualification / human + PRIME review
  -> governed state transition
  -> ledger checkpoint
  -> ECHO provenance event
  -> verified signed ECHO checkpoint
```

No step in this increment authorizes automatic claim elevation, merge, deployment, partner contact, purchasing, proposal submission, physical actuation, or other consequential external execution.
