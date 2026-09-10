# WS-NSB v0.7 — G2 Manufactured Incompressible Integrator

## Purpose

WS-NSB v0.7 advances the benchmark from G0/G1 instrumentation to an actual bounded PDE time integration. It integrates the two-dimensional periodic incompressible Navier-Stokes vorticity equation against the Taylor-Green manufactured solution.

This gate is intended to establish that Worldshepherd can execute and independently verify spatial and temporal convergence on a known incompressible reference problem. It is not a singularity benchmark.

## Numerical formulation

The solver advances

`d(omega)/dt + u d(omega)/dx + v d(omega)/dy = nu Laplacian(omega)`

on `[0, 2*pi)^2` with periodic boundaries.

The Taylor-Green reference is

`u = A(t) sin(x) cos(y)`

`v = -A(t) cos(x) sin(y)`

`omega = 2 A(t) sin(x) sin(y)`

with

`A(t) = exp(-2 nu t)`.

Spatial derivatives use second-order centered finite differences. Time integration uses explicit midpoint RK2. Velocity reconstruction is deliberately specialized to the Taylor-Green manufactured mode by projecting the numerical vorticity back onto that mode.

## G2 verification

The default campaign performs two independent refinement studies:

- Spatial refinement: `N = 12, 24, 48` at a fixed small timestep.
- Temporal refinement: `dt = 0.04, 0.02, 0.01` at fixed grid size, with temporal order estimated from pairwise numerical-solution differences so the common spatial error cancels.

The acceptance contract requires:

- observed spatial order >= 1.8,
- observed temporal order >= 1.8,
- RMS velocity divergence <= 1e-12,
- kinetic-energy relative error <= 1%,
- enstrophy relative error <= 1%,
- monotonic kinetic-energy and enstrophy dissipation for positive viscosity.

These are Worldshepherd engineering acceptance thresholds for this benchmark, not mathematical constants.

## Evidence and claims boundary

A passing G2 report remains `SIMULATED_ONLY`.

A passing G2 report establishes only that this bounded manufactured reference problem was numerically integrated and that the declared convergence and diagnostic gates passed.

It does **not** establish:

- a general-purpose CFD solver,
- reproduction, validation, or refutation of a finite-time Navier-Stokes singularity,
- three-dimensional singular behavior,
- MHD or plasma physics,
- laboratory validation,
- propulsion, shielding, stealth, cloaking, or operational capability.

The Pydantic report model fails closed if any of those unsupported promotions are asserted.

## Next gate

G3 should add a genuinely general periodic incompressible solver with a pressure projection or streamfunction/Poisson inversion that is not restricted to the Taylor-Green mode. Only after that baseline is independently converged should electromagnetic coupling enter a later MHD gate.
