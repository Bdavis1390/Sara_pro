# General-Agent Runtime v0.2

## Purpose

Move Worldshepherd from an AGI qualification framework toward an executable candidate agent architecture.

This version targets four open blockers from the AGI Gap Ledger:

- persistent state continuity;
- causal world-model learning;
- structural transfer;
- rule-change adaptation.

It does not clear those blockers empirically until the preregistered benchmarks are actually run.

## Runtime loop

1. Maintain multiple live causal hypotheses.
2. Estimate which action is most useful instrumentally and epistemically.
3. Intervene.
4. Observe the outcome.
5. Update posterior belief over causal models.
6. Measure surprise.
7. Detect repeated model violation as possible regime change.
8. Preserve falsified history.
9. Store validated skills with evidence and authorization scope.
10. Propose structural transfer under representation shift.
11. Validate transfer in the target environment.
12. Persist explicit state and resume without losing evidence or falsifiers.

## Why causal hypotheses instead of one world model

A general agent should not prematurely collapse uncertainty.

If two rules explain current observations, both stay live until an action separates them.

Expected information gain identifies actions whose predicted outcomes differ across hypotheses.

## Persistent state

The state store serializes only explicit decision-relevant records:
- goals;
- beliefs;
- causal hypotheses;
- skill records;
- action/outcome evidence;
- falsified hypotheses;
- authorization scope.

It does not store hidden chain-of-thought.

Snapshots are fingerprinted so corruption or mutation is detectable.

## Structural transfer

The runtime separates:
- surface representation;
- structural roles;
- relations;
- dynamics.

Transfer similarity proposes a hypothesis.

Transfer is never treated as validated until target-environment evidence confirms it.

## Regime changes

General intelligence requires more than learning once.

If environmental rules change:
- surprise rises;
- repeated high-surprise events trigger a regime-change state;
- prior rules are not silently erased;
- the system records that a formerly useful causal model has failed;
- alternatives must be re-evaluated.

This directly targets catastrophic persistence of obsolete rules.

## AGI claim rule

Software support for a capability is not empirical evidence that the capability reaches human-level generality.

The path remains:

architecture
-> executable benchmark
-> held-out transfer
-> independent replication
-> human reference
-> AGI qualification.
