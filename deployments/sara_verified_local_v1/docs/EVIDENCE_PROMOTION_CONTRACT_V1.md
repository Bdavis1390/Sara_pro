# Worldshepherd EPC / AST v1.0

Status: **IMPLEMENTED IN SOFTWARE on this branch / NOT YET PROMOTED TO MAIN**

This package introduces the first executable Worldshepherd Evidence Promotion Contract (EPC) and Authenticated State Transition (AST) primitive.

## Control loop

PRIME authorizes the proposed action. SARA performs the bounded transformation. ECHO binds evidence and custody. OVERWATCH evaluates evidence and contradictions. EPC maps evidence scope to permitted claims. AST is the immutable transition record connecting those layers.

## Decisions

The evaluator emits exactly one of:

- `PROMOTE` — all current promotion requirements are satisfied.
- `HOLD` — evidence is valid but insufficient for promotion.
- `DENY` — authorization, verification, or claim-scope rules fail.
- `REVIEW` — material contradiction requires reconciliation.
- `DEMOTE` — critical contradictory evidence invalidates an existing promoted state.

## Fail-closed rules

Promotion is blocked when a requested claim exceeds evidence scope, authority is absent, provenance is incomplete, the environment is missing, measurements are incomplete, reproduction class is insufficient, or a required human gate is not approved.

A successful test output by itself is not promotion evidence.

## Reproduction classes

- R0: same execution context
- R1: independent process
- R2: independent internal operator/machine
- R3: independent organization
- R4: independent implementation
- R5: multiple independent organizations

R0-R2 must never be described as independent external reproduction.

## Claim dependency DAG

The in-memory ClaimGraph records evidence-to-claim and claim-to-claim dependencies. Revoking or invalidating evidence recursively suspends dependent claims rather than rewriting history.

## Conformance fixtures

`tests/fixtures/evidence_contract/conformance.json` freezes first-pass contracts for:

1. NeedleGuard v1.8 isolated Windows replay
2. Q-VCP v0.7 circuit-level fault bridge
3. WS-10X baseline freeze
4. WSMiner evidence-state progression

The fixture file is a claims-control contract, not evidence that those gates have passed.

## Claim boundary

The presence of these files establishes only that EPC/AST mechanics are implemented and unit-tested once CI passes on the exact branch SHA. It does not establish independent reproduction, external validation, standards compliance, government acceptance, operational deployment, commercial adoption, WS-10X, hardware FTQC, or WSMiner revenue.
