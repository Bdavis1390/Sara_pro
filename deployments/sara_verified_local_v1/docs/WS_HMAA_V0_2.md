# WS-HMAA v0.2 — Synthetic SIL Scenario Runner

Status: IMPLEMENTED IN SOFTWARE / SYNTHETIC VALIDATION ONLY

## Increment objective

WS-HMAA v0.2 adds an executable software-in-the-loop scenario runner on top of the v0.1 assurance core. It exercises nominal autonomy observations, link degradation, reconnection, evidence-integrity failure, and policy-service failure without commanding an aircraft or importing proprietary vehicle/autonomy software.

## Added behavior

`hmaa_simulation.py` accepts typed scenario steps and converts them into the same hash-chained HMAA evidence model introduced in v0.1. Each step receives an assurance disposition:

- `ALLOW` — no assurance exception detected;
- `WARN` — degraded link or duplicate condition requiring attention;
- `REVIEW` — integrity or chronology exception requiring human review;
- `INDETERMINATE` — assurance/policy service unavailable; approval is never inferred.

The runner then verifies the complete evidence chain before emitting a scenario result.

## First scenario fixture

`fixtures/hmaa_link_loss_scenario.json` contains seven synthetic events:

1. nominal aircraft entity update;
2. task enters progress;
3. healthy entity-stream heartbeat;
4. degraded/missed-link heartbeat condition;
5. stream reconnect attempt;
6. evidence-object checksum failure;
7. policy-service outage.

Expected assurance distribution:

- 4 `ALLOW`
- 1 `WARN`
- 1 `REVIEW`
- 1 `INDETERMINATE`

## Acceptance criteria

Automated tests require that:

- the seven-event chain verifies end to end;
- the degraded heartbeat is surfaced as `WARN`;
- reconnection is recorded as a separate provenance event;
- checksum failure is escalated to `REVIEW`;
- policy-service failure remains `INDETERMINATE`;
- an empty SIL scenario is rejected.

## Claims boundary

This increment is evidence that the Worldshepherd assurance logic can execute against synthetic autonomy-like event sequences. It is not evidence of production integration with Anduril Lattice, Hermeus Quarterhorse, any government mission system, or any flight-control stack.

The next validation tier requires an authorized Lattice Sandbox or equivalent controlled interoperability environment. Until then, the appropriate claims labels remain `IMPLEMENTED IN SOFTWARE` and `SIMULATED ONLY`.

## Next increment

WS-HMAA v0.3 should add replay-safe deduplication, clock-skew-aware chronology validation, persistent evidence storage using SARA's secured data-directory conventions, and read-only assurance status/evidence endpoints. A live Lattice client should remain a separate adapter package so the assurance core stays testable without external credentials or proprietary dependencies.
