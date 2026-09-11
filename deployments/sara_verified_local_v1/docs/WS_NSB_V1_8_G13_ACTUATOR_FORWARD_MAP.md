# WS-NSB v1.8 — G13 Actuator Forward-Map Gate

## Purpose

G13 is the bridge between the abstract three-mode Lorentz-force-curl commands validated in G12 and a bounded finite-channel actuator allocation problem.

The gate uses an eight-channel normalized periodic current-sheet surrogate. The three actuator-to-mode transfer rows are synthetic Fourier-like spatial coupling functions. They are intentionally deterministic, bounded, and full-rank so reachability, conditioning, calibration, saturation, fault handling, and closed-loop degradation can be tested before introducing a Maxwell or hardware-specific model.

## What G13 does

- maps actuator channels into the three G12 control modes;
- computes minimum-norm bounded actuator allocation;
- quantifies transfer rank and conditioning;
- measures modal tracking residual;
- tests deterministic channel-gain drift with and without calibration;
- disables one actuator and reallocates;
- detects a deliberately unreachable saturated target;
- runs the G12 feedback loop through the forward-map surrogate rather than directly injecting ideal modal commands;
- emits a deterministic SHA-256-bound evidence report.

## Scientific boundary

The transfer matrix is **synthetic**. It is not a full-wave Maxwell solution, Biot-Savart coil calculation, electrode/plasma sheath model, measured transfer function, RF aperture model, or calibrated device model.

Passing G13 therefore supports only:

`IMPLEMENTED IN SOFTWARE — SIMULATED ONLY`

It does not establish physical actuator realizability or laboratory electromagnetic control.

## Acceptance targets

The default gate requires:

- three-mode effective rank = 3;
- transfer condition number <= 3;
- nominal modal residual <= 5e-4;
- single-actuator-out residual <= 5e-3;
- calibrated gain-drift residual <= 5e-4 and lower than the uncalibrated residual;
- deliberate saturation case correctly flagged unreachable;
- forward-mapped closed loop retains >= 15% target-modal reduction;
- final target-modal result remains within 1% of the ideal G12 result;
- velocity and magnetic divergence <= 1e-10;
- all actuator commands remain within their declared hard limits.

## Next gate

G14 should replace the synthetic transfer matrix with a geometry-specific electromagnetic forward model. The preferred progression is quasi-static coil/electrode geometry first, then frequency-dependent Maxwell/full-wave modeling if the intended actuator requires it. G14 must still remain simulation-only until measured hardware transfer data are introduced.
