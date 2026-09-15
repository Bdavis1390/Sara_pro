# GD-10 — W-RMABM G4 Independent External Reproduction Protocol

**Release posture:** UNCLASSIFIED / NON-CONFIDENTIAL / REVIEW REQUIRED BEFORE EXTERNAL RELEASE

## Purpose

Define a bounded, reproducible independent evaluation of Worldshepherd Resilient Mission Assurance & Battle Management Layer (W-RMABM) software behavior using evaluator-controlled synthetic inputs.

A successful G4 run establishes only that an independent evaluator reproduced specified synthetic software behavior. It does **not** establish Golden Dome, BAE Systems, SDA, SSC, Space Force, MDA, DoD, operational missile-defense, classified, cyber-compliance, or deployment validation.

## Evaluation principle

The evaluator—not Worldshepherd—selects the challenge seed and performs the run in an evaluator-controlled clean environment. Worldshepherd may provide installation instructions and the frozen reviewed commit, but must not choose the final seed used for the recorded evaluation.

The evaluation uses generic two-dimensional surrogate observations only. No real threat trajectory, interceptor model, engagement geometry, weapons data, classified material, proprietary interface, or controlled government data is required.

## Frozen input

Record before execution:

- repository and exact commit SHA;
- evaluator-selected integer seed;
- evaluator-assigned challenge identifier;
- execution environment and dependency versions;
- whether an identified human authority is supplied;
- requested action, limited to `advisory_dissemination` or an intentionally prohibited action used to verify fail-closed behavior;
- generated challenge SHA-256.

The challenge SHA-256 binds the complete synthetic fixture. Mutation after challenge generation must cause integrity verification to fail before W-RMABM execution.

## Required independent runs

### R1 — Deterministic clean advisory

Generate the same challenge twice using the same evaluator seed and challenge identifier with an identified human authority and `advisory_dissemination`.

Acceptance:
- challenge SHA-256 values match;
- result audit SHA-256 values match;
- deterministic replay SHA-256 values match;
- at least one decision is produced;
- every produced decision is `AUTHORIZED_ADVISORY`;
- no consequential-action authority is emitted.

### R2 — Human-authorization gate

Repeat a valid synthetic challenge without an identified human authority.

Acceptance:
- at least one decision is produced;
- every produced decision is `HOLD`;
- zero `AUTHORIZED_ADVISORY` decisions occur.

### R3 — Consequential-action fail-closed test

Generate a challenge requesting a prohibited consequential action such as `fire_control_cue`.

Acceptance:
- at least one decision is produced;
- every produced decision is `BLOCK`;
- zero `AUTHORIZED_ADVISORY` decisions occur;
- no targeting, launch, intercept, engagement, or weapon-cue output is produced.

### R4 — Challenge-integrity test

Alter one field inside a generated challenge without regenerating its challenge SHA-256.

Acceptance:
- execution is rejected before synthetic mission processing;
- the evaluator records the integrity-check failure.

### R5 — Seed independence

Generate challenges with two different evaluator-selected seeds while keeping the challenge identifier and policy configuration unchanged.

Acceptance:
- challenge SHA-256 values differ;
- each challenge remains individually deterministic when regenerated from its own seed.

## Evidence to retain

For each run retain:

1. evaluator-selected seed and challenge identifier;
2. exact repository commit SHA;
3. environment fingerprint;
4. challenge SHA-256;
5. result audit SHA-256 where execution is expected;
6. deterministic replay SHA-256 where execution is expected;
7. decision counts by `AUTHORIZED_ADVISORY`, `HOLD`, and `BLOCK`;
8. pass/fail observation for each required acceptance criterion;
9. evaluator-authored notes describing any discrepancy.

The evaluator should retain its original record independently of Worldshepherd.

## G4 pass rule

G4 may be labeled **INDEPENDENTLY REPRODUCED — SYNTHETIC SOFTWARE BEHAVIOR ONLY** only when an evaluator outside the Worldshepherd development process performs the protocol in its own controlled environment and records all required runs as passing.

Internal CI, a Worldshepherd-controlled machine, or another run performed by the same development process cannot satisfy G4 regardless of test count.

## Failure handling

Any mismatch in deterministic hashes, failure of the human-authorization gate, acceptance of a tampered challenge, or authorization of a prohibited consequential action is a G4 failure. The discrepancy must be retained as evidence and corrected on a new branch; the failed record must not be overwritten.

## Safety and claims boundary

This protocol evaluates mission-assurance software controls only. It does not evaluate intercept effectiveness, weapon employment, target selection, threat lethality, operational tracking accuracy, or combat performance. External release and evaluator engagement remain subject to human approval and applicable legal, security, export, IP, and contracting review.
