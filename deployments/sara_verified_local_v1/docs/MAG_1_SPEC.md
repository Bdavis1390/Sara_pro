# MAG-1 — Misalignment Assurance Gate

- **Status:** implementation branch / pre-merge review
- **Canonical runtime:** `deployments/sara_verified_local_v1/`
- **Primary claim state:** `IMPLEMENTED IN SOFTWARE` for the controls and regression fixtures in this branch
- **Safety/effectiveness claim state:** `REQUIRES LAB VALIDATION`

## Purpose

MAG-1 adds a compositional control boundary around SARA's existing bounded autonomy policy. It is designed to make authority, context lineage, side effects, and whole-trajectory behavior explicit before an action is considered eligible for automatic execution.

MAG-1 does **not** claim to solve model alignment, prevent every form of model misbehavior, establish external certification, or prove safety in deployment.

## Core invariant

> A request, model-generated summary, model memory, prior model statement, discovered credential, available tool, reachable destination, or technically achievable operation does not constitute authority by itself.

Consequential authority must be independently represented, purpose-bound, time-bounded, scope-bounded, and checked before the action proceeds.

## Implemented primitives

### `context_lineage.py`

Defines explicit trust classes for human root instructions, signed policy, tool results, source documents, model summaries, model memory, and model inference.

Model-generated summaries, memories, and inferences are classified as `UNTRUSTED_DERIVED`. They cannot grant authority and cannot become source evidence merely through repetition.

### `authorization_envelope.py`

Defines a purpose-bound authorization envelope covering:

- principal;
- workflow;
- action;
- resource;
- purpose;
- scopes;
- destination allowlist;
- explicit external-egress permission;
- explicit credential-use permission;
- delegation ceiling;
- timezone-aware validity window; and
- a maximum 15-minute lifetime.

Authorization evaluation fails closed for missing, expired, not-yet-valid, scope-mismatched, purpose-mismatched, destination-mismatched, egress-mismatched, credential-use-mismatched, or over-delegated requests.

This generic envelope is currently a **structural authorization primitive**. It is not yet a cryptographic replacement for the repository's existing PRIME SENTINEL Ed25519 authorization assertion. A subsequent integration should bind generic MAG-1 envelopes to independently verified PRIME issuance/identity evidence rather than permitting caller-originated trust metadata to stand alone.

### `trajectory_guard.py`

Tracks state across action sequences rather than judging each operation in isolation. Current tracked state includes:

- action/decision history;
- destinations successfully contacted;
- credential observations and permitted uses;
- blocked-attempt count; and
- cumulative trajectory risk.

The guard treats the following as high-consequence effects:

- external writes;
- publication;
- execution; and
- credential use.

It also detects/penalizes non-allowlisted channels, repeated blocked attempts, alternate-channel boundary seeking, policy conflicts, fragmented-sensitive-data bypass behavior, and child authority exceeding parent authority.

Risk persists across subsequent actions. It does not reset merely because the next individual operation is locally harmless.

### `misalignment_incident.py`

Defines an incident evidence object and a constrained lifecycle:

`DETECTED -> CONTAINED -> EVIDENCE_PRESERVED -> TRIAGED -> INVESTIGATING -> MITIGATED -> VERIFIED -> DISCLOSED/CLOSED`

An incident cannot enter `VERIFIED`, `DISCLOSED`, or `CLOSED` without both ECHO evidence hashes and regression-test identifiers.

### `mag1_gate.py`

Composes:

1. context-lineage authority validation;
2. purpose-bound authorization;
3. trajectory-level control; and
4. the existing `autonomy_policy.evaluate_candidate()` gate.

High-consequence side effects automatically require authorization. This requirement cannot be disabled by the caller. A caller-supplied `authorization_verified=True` flag is overwritten by the composite gate whenever authorization is required.

The composite result is one of:

- `AUTO_ELIGIBLE`;
- `HUMAN_REVIEW_REQUIRED`;
- `DENIED`; or
- `PAUSED`.

`PAUSED` represents a trajectory-level intervention rather than permission to continue.

## Adversarial regression matrix

The test suite includes explicit fixtures for these incident classes:

| ID | Failure class | Required behavior |
|---|---|---|
| MAG-01 | model summary attempts to grant authority | reject authority laundering |
| MAG-02 | concealment/evidence instruction in derived summary | derived context is not evidence |
| MAG-03 | missing authorization | fail closed; do not invent permission |
| MAG-04 | discovered credential | use requires independent authorization |
| MAG-05 | citation/public-host egress | require destination + egress authority |
| MAG-06 | repository used as unintended message bus | reject non-allowlisted channel |
| MAG-07 | public file transfer | reject without verified authority |
| MAG-08 | fragmented/reconstructed sensitive-data bypass | hard deny |
| MAG-09 | repeated blocked attempts | pause entire trajectory |
| MAG-10 | nested agent authority escalation | child authority cannot exceed parent |
| MAG-11 | instruction/policy collision | governing policy wins; fail closed |
| MAG-12 | external side effect | require verified authority |
| MAG-13 | scope drift | require new authorization |
| MAG-14 | post-action verification without evidence | block VERIFIED state |
| MAG-15 | multi-step risk accumulation | preserve risk across local-looking steps |
| MAG-16 | model memory launders prior model statement | reject as authority |

Additional composite tests prove that high-consequence authorization is implicit/non-bypassable and that a correctly scoped, current authorization can pass the composed gate when every other control also passes.

## Relationship to existing PRIME, ECHO, SARA, and OVERWATCH

MAG-1 is intended as the compositional decision layer between policy/authority and execution:

```text
human / signed policy
        |
        v
context lineage
        |
        v
PRIME authority evidence
        |
        v
MAG-1 purpose + trajectory gate
        |
        v
existing SARA autonomy policy
        |
        v
bounded execution
        |
        v
ECHO evidence / OVERWATCH intervention
```

The present branch implements the MAG-1 software primitives and regression fixtures. Full runtime integration with PRIME cryptographic issuance, ECHO persistence, and an OVERWATCH pause actuator remains a separate integration gate.

## Evidence and CI contract

The canonical SARA workflow already triggers for changes under `deployments/sara_verified_local_v1/**`, compiles the package, and runs `pytest`. Therefore these MAG-1 tests become part of the existing canonical verification path when this branch is proposed through a pull request.

A MAG-1 merge candidate should not be represented as passing until the GitHub Actions `SARA Verified Local v1 Gate` succeeds on the exact proposed commit.

## Claims boundary

### Supported after code review + passing canonical CI

A precise claim may state:

> SARA contains implemented software primitives for context-lineage classification, purpose/scope/time-bounded authorization, cumulative trajectory risk, non-bypassable authorization for defined high-consequence side effects, a misalignment-incident state machine, and incident-derived adversarial regression tests.

### Not currently established

MAG-1 does **not** establish:

- that Worldshepherd solves AI alignment;
- that all misalignment or unauthorized behavior will be detected or prevented;
- that the risk weights are empirically calibrated;
- cryptographic provenance for the generic authorization envelope;
- production integration of every MAG-1 decision with PRIME, ECHO, or OVERWATCH;
- independent third-party validation;
- NIST, CMMC, DFARS, CUI, classified-system, or other regulatory authorization;
- field safety, flight safety, weapon-system authorization, or physical-system validation.

## External incident motivation

MAG-1 was motivated in part by OpenAI's September 16, 2026 public framework for reporting model misalignment and its disclosed examples of unexpected or unauthorized model behavior, together with OpenAI's public work on safety/alignment for long-horizon agents. Those publications are treated as external evidence for relevant failure classes, **not** as validation of Worldshepherd.

Primary references:

- OpenAI, *Our framework for reporting model misalignment*, 2026-09-16.
- OpenAI, *Safety and alignment for long-horizon models*, 2026.

## Next integration gate — MAG-1.1

Do not broaden the safety claim merely because this branch passes unit tests. MAG-1.1 should add:

1. cryptographic binding from a verified PRIME authorization assertion/issuance record to the generic envelope;
2. persistent ECHO serialization of every MAG-1 decision and trajectory update;
3. an OVERWATCH pause/containment actuator exercised by integration tests;
4. tamper tests for context lineage and trajectory state;
5. replay protection for authorization identifiers/nonces;
6. deterministic policy-hash binding; and
7. repeated model-in-the-loop adversarial trials with observed violation, detection, and prevention rates reported separately.
