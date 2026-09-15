# Worldshepherd Physical AI Interface Contract v0.1

Status: **IMPLEMENTED IN SOFTWARE — E1 UNIT-CONTRACT LEVEL ONLY**

This document defines the first bounded Physical AI interface layer for Worldshepherd SARA. It does not claim physical robot validation, flight validation, RF performance, materials qualification, or operational deployment.

## 1. Purpose

The contract provides a common governance and evidence boundary for heterogeneous physical systems while leaving flight control, motor control, robot servo control, PLC logic, and OEM safety loops inside their native controllers.

Reference stack:

```text
Physical machine
  -> native controller / OEM runtime
  -> transport adapter (ROS 2 / PX4 / RMF / OPC UA / future adapters)
  -> Worldshepherd Physical AI contract
  -> PRIME policy decision
  -> SARA orchestration
  -> ECHO evidence
  -> OVERWATCH observability
```

## 2. Asset identity

Every physical asset receives a stable Worldshepherd URI:

```text
ws://physical-ai/<fleet_id>/<asset_id>
```

The asset record binds:

- asset ID
- fleet ID
- asset class
- hardware revision
- software revision
- configuration digest

## 3. Action envelope

A physical action request carries at minimum:

- asset ID
- mission ID
- action ID
- action type
- confidence
- requested authority
- reversibility
- battery state
- telemetry age
- degraded-state status
- model digest
- configuration digest
- optional observation/evidence-parent digests

No AI or planner output should be treated as actuator authority merely because it produced a candidate action.

## 4. PRIME-style decision states

The software contract exposes six dispositions:

- `ALLOW`
- `ALLOW_WITH_LIMITS`
- `DEFER`
- `HUMAN_APPROVAL`
- `DENY`
- `SAFE_HOLD`

The initial evaluator is intentionally conservative. Missing custody evidence, stale telemetry, low confidence, excessive authority, or non-reversible automatic actions cannot silently pass.

## 5. Degraded-state model

The first state machine is:

```text
NORMAL -> DEGRADED -> SAFE_HOLD -> RECOVERY -> NORMAL
   \          \           \          \
    +----------+-----------+-----------+-> EMERGENCY_STOP
```

`EMERGENCY_STOP` is modeled as absorbing at this contract layer. Clearing a real emergency stop must be handled by an explicitly designed physical safety procedure and must not be inferred from software state alone.

## 6. Evidence manifest

For each authorization decision, the contract can create an evidence manifest containing:

- mission ID
- asset ID
- action ID
- UTC timestamp
- policy ID
- decision
- configuration digest
- model digest
- observation digest
- evidence parent
- optional action/result digests

This is the bridge into ECHO SENTINEL LINK provenance and future machine-passport work.

## 7. E1 conformance set

The initial unit-contract tests are labeled PA-001 through PA-012:

| Test | Unit-contract behavior |
|---|---|
| PA-001 | Valid bounded action is allowed |
| PA-002 | Explicitly denied action is rejected |
| PA-003 | Stale telemetry defers execution |
| PA-004 | Low battery enters safe hold |
| PA-005 | Missing model digest defers execution |
| PA-006 | Missing configuration digest defers execution |
| PA-007 | Bounded local action can proceed with limits in degraded mode |
| PA-008 | Unbounded degraded action enters safe hold |
| PA-009 | Human-approval action is not automatically executed |
| PA-010 | Emergency-stop state denies actions |
| PA-011 | Recovery-state execution remains limited |
| PA-012 | Degraded-state transitions obey bounded transition rules |

These are **E1 unit tests**, not simulation, SIL, HIL, or physical-system evidence.

## 8. Evidence ladder

Worldshepherd Physical AI evidence is tracked as:

- E0 — architecture only
- E1 — unit test
- E2 — software simulation
- E3 — software in the loop
- E4 — hardware in the loop
- E5 — controlled physical test
- E6 — operational partner demonstration

A capability must not inherit a higher evidence level from adjacent software, simulations, publications, or partner systems.

## 9. Adapter boundaries

Planned adapters:

- `WS-ROS` — ROS 2 semantic bridge
- `WS-PX4` — high-level PX4 mission/governance bridge
- `WS-RMF` — fleet-task/governance bridge
- `WS-OPCUA` — industrial robot/factory semantic bridge
- `WS-EMSKIN` — adaptive RF/metasurface control/evidence bridge

Native real-time stabilization and safety-critical servo loops remain below the Worldshepherd governance layer unless separately validated for a specific platform.

## 10. Next gate

The next engineering gate is E2/E3:

1. expose the contract through bounded SARA API endpoints;
2. add a simulated UGV adapter;
3. connect fault injection for telemetry staleness, battery depletion, navigation degradation, and network loss;
4. persist authorization and transition evidence through the existing durable audit/evidence path;
5. run PA-001..PA-012 in CI and then expand them into SIL scenarios.

Only after those pass should the contract be connected to PX4, RMF, OPC UA, or physical hardware.
