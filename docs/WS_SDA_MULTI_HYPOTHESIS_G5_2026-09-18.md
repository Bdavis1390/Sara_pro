# WS-SDA G5 — Provenance-Aware Multi-Hypothesis Reference Fusion

Status: **IMPLEMENTED IN SOFTWARE ON STACKED BRANCH — CI NOT YET EXECUTED**
Date: 2026-09-18
Branch: `feature/ws-sda-multi-hypothesis-g5-20260918`
Parent stack: G1/G2 -> G4A canonical envelope V2

## 1. Purpose

G5 addresses a specific failure mode in ordinary fusion pipelines: incompatible
measurements can disappear inside one averaged state.

The Worldshepherd G5 reference profile instead keeps mutually incompatible evidence
visible as separate hypotheses. It operates only on the non-lossy canonical
state-vector envelope produced by the G4A work.

## 2. Preconditions

Every observation must have:

- one explicit object identity and center identity shared by the set;
- an identical raw epoch and time-system label;
- one common state reference frame;
- a complete covariance;
- a covariance reference frame identical to the state frame;
- strictly positive diagonal fusion variances;
- unique observation identity.

The profile is deliberately bounded to at most 12 observations. It does not
propagate states between epochs or transform frames.

## 3. Pairwise compatibility

For six state components, pairwise disagreement is measured as:

```text
score = sum_i (x_i - y_i)^2 / (var_x_i + var_y_i)
```

The configured threshold is explicit and evidence-visible. The score is a reference
statistical compatibility metric, not a probability of truth and not an operational
track-quality certification.

## 4. Alternative hypothesis construction

G5 builds a compatibility graph and enumerates **maximal pairwise-compatible
cliques**. Each maximal clique becomes one candidate hypothesis.

This matters for ambiguous bridge cases. If A is compatible with B and B is
compatible with C, but A conflicts with C, G5 retains two overlapping alternatives:

```text
H1 = {A, B}
H2 = {B, C}
```

It does not force all three into one state and does not silently discard B.

Within each compatible clique, state fusion uses diagonal inverse-variance weights.
Source confidence, source reputation, vendor identity, or operator preference do not
silently alter the physical fusion weights.

## 5. Human/policy boundary

If more than one maximal hypothesis remains:

- `requires_resolution = true`;
- `automatic_winner_selected = false`.

The reference layer does not choose an operational winner, issue a maneuver
decision, generate targeting data, or authorize a consequential action.

PRIME/SARA policy and identified human authority remain downstream gates.

## 6. Evidence graph

Every hypothesis is connected to:

- every supporting canonical observation;
- every observation excluded by incompatibility.

This preserves both positive and negative evidence for ECHO/OVERWATCH/replay work.

## 7. Negative gates

The executable candidate rejects:

- different object identities;
- different center identities;
- different epochs/time systems;
- different state frames;
- covariance/state frame mismatch;
- missing covariance;
- zero/non-positive fusion variance;
- duplicate observation IDs;
- input sets above the bounded observation count;
- invalid/non-positive compatibility thresholds.

## 8. Claims boundary

A passing G5 reference suite establishes deterministic software behavior for
same-object, same-epoch, same-frame, covariance-bearing synthetic/reference state
evidence.

It does **not** establish:

- operational orbit determination;
- propagation between epochs;
- unknown-object association;
- maneuver detection;
- conjunction assessment;
- battle-management effectiveness;
- targeting or weapon-cue generation;
- customer/government acceptance;
- independent validation.

## 9. Next gate

After exact-head CI:

1. integrate G5 hypothesis evidence with ECHO persistence and mission replay;
2. add degraded-source exclusion as an explicit policy state rather than a hidden
   fusion weight;
3. add G6 PRIME releaseability/action-digest/human-authorization binding around any
   downstream dissemination;
4. test the ambiguity and failure corpus under G8 without upgrading claims.
