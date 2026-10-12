# WS-LAB-INTEROP-01 G1 — Synthetic Interoperability Baseline

Status: IMPLEMENTATION UNDER REVIEW / SIMULATED_ONLY

This current-main implementation supersedes the stale-base prototype path for qualification purposes.

## Scope

Two deterministic device profiles exercise command, semantic, and evidence interoperability with F1–F10 fault injection:

1. interface version drift
2. dropped telemetry
3. stale state
4. malformed command
5. sensor disagreement
6. device offline
7. unit mismatch
8. timestamp reorder
9. replay
10. partial execution plus communications loss

Overall maturity is limited by the weakest dimension:

`I_overall = min(I_C, I_S, I_E)`

## Claims boundary

Passing G1 means only that the exact synthetic harness demonstrates its declared fail-closed and evidence-reconstruction behavior.

It does not establish physical-device integration, OPC UA LADS conformance, SiLA 2 conformance, production security, certification, partner validation, or external blind replication.
