# WS-ICD-001 — Worldshepherd Integrated Test Interface Contract

Status: DRAFT BASELINE

## Purpose

WS-ICD-001 defines the common interface boundary for WS-ITX-01 and later Worldshepherd physical-system experiments. It allows propulsion, FIELD-SKIN, materials, sensing, power, control, solver, and SARA evidence components to evolve independently without inventing incompatible data or evidence conventions.

## Interface families

- `I_P` — power: voltage, current, frequency/phase where applicable, energy, limits, isolation domain.
- `I_D` — data: timestamps, sensor identity, units, sample rate, calibration identity, uncertainty source.
- `I_M` — mechanical: mass, center of gravity, mount datum, coordinate transform, predicted force/torque vector.
- `I_C` — control: requested wrench/field objective, actuator limits, interlocks, health state, fault state.
- `I_E` — evidence: experiment identity, configuration digests, software commit, material batches, calibration IDs, raw-data digest, uncertainty model, hypotheses, result class, review state.

## Coordinate-frame rule

Every test article shall declare a module frame `M` and a balance/reference frame `B`. Force and torque results shall be transformed using the recorded `B<-M` transformation rather than informal directional labels.

## Power rule

Logic/sensor, RF, propulsion/high-voltage, and auxiliary power domains shall be separately measurable. Switching transients and energy input must be time-aligned with force, thermal, magnetic, vibration, and other relevant sensor channels.

## Evidence rule

No test result is promoted by existence alone. Each record must preserve whether its content is `MEASURED`, `CALCULATED`, `LITERATURE`, `SIMULATED`, `HYPOTHESIS`, `NULL_CONTROL`, or `ARTIFACT` evidence. Corrections use append-only supersession rather than overwrite.

## Propulsion outer contract

Every propulsion module shall expose, where applicable:

`[Fx, Fy, Fz, Tx, Ty, Tz, Pin, Puseful, mdot, Qthermal, EMI, health, uncertainty, validity_domain]`

A module may expose additional mechanism-specific state, but AEROSHEPHERD and ITX orchestration consume the common outer contract.

## FIELD-SKIN maturity boundary

- `FS-1`: environmental sensing.
- `FS-2`: verified field manipulation within declared frequency/geometry/power limits.
- `FS-3`: propulsion, flow-control, or energy-management contribution. FS-3 requires separate physical validation and may not be inferred from FS-1/FS-2 success.

## Safety/control hierarchy

1. `L0` hardware interlocks — non-bypassable by AI.
2. `L1` deterministic local control.
3. `L2` constrained optimization/allocation.
4. `L3` AI/learning recommendations and bounded residual correction.

AI output alone is never sufficient authority to exceed a validated hardware, thermal, power, or evidence boundary.

## Glob/DOE boundary

The established `PA`, `PB`, and `PC` permutations may select deterministic experiment ordering, withheld conditions, and admissible parameter indexes. They do not define physical constants or establish causal physical relationships.

## ITX01 minimum acceptance sequence

1. mechanical datum verification;
2. power-isolation characterization;
3. clock synchronization check;
4. pre-calibration;
5. zero/drift characterization;
6. powered null;
7. active reference propulsion article;
8. polarity/orientation reversal where physically meaningful;
9. FIELD-SKIN sensing operation;
10. thermal/electrical/environmental correlation;
11. solver discrepancy calculation;
12. SARA evidence ingestion;
13. bounded fault injection;
14. post-calibration;
15. one withheld/blind prediction condition.

## Claim boundary

WS-ICD-001 specifies interfaces and evidence handling. It does not itself validate WS-AlTi material properties, FIELD-SKIN propulsion effects, anomalous propulsion, or any other physical hypothesis.
