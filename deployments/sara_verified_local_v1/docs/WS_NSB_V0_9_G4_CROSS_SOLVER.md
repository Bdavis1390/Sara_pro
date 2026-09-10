# WS-NSB v0.9 — G4 Numerically Distinct Cross-Solver Gate

## Purpose

G4 adds a second hydrodynamic discretization before any MHD coupling is admitted into the primary validation chain. The goal is to determine whether a nontrivial periodic flow result survives a materially different numerical formulation.

This is **internal numerical replication**, not external independent replication.

## Formulation

The G4 solver advances the 2D periodic incompressible vorticity equation with:

- a periodic SOR solution of the five-point finite-difference Poisson equation;
- second-order centered velocity, vorticity-gradient, divergence, and Laplacian operators;
- explicit midpoint RK2 time integration.

The comparison reference is the WS-NSB v0.8 G3 Fourier pseudo-spectral solver. G4 does not reuse the G3 Poisson or derivative operators.

## Evidence sequence

### Manufactured spatial-convergence family

The finite-difference streamfunction solver is tested on grids `8, 16, 32` against a continuous multimode manufactured field. Streamfunction and both reconstructed velocity components must show at least 1.8 observed order under factor-two refinement.

### Nonlinear cross-solver case

G3 and G4 integrate the same mixed-mode, positive-viscosity periodic vorticity field from the same initial state, timestep, and final time. The comparison records:

- L2 and relative RMS final-state disagreement;
- actual state change from the initial field;
- mean-vorticity drift;
- divergence and Poisson residual;
- kinetic-energy and enstrophy monotonicity.

## Default acceptance criteria

- minimum manufactured spatial order: `>= 1.8`
- Poisson residual RMS: `<= 1e-9`
- divergence RMS: `<= 1e-10`
- G4 finite-difference vs G3 spectral final-state relative RMS: `<= 0.005`
- mean-vorticity drift: `<= 1e-12`
- nonlinear state change: `>= 0.01`
- kinetic energy and enstrophy: nonincreasing in the positive-viscosity reference case

## Claims boundary

Passing G4 supports only a bounded software claim: two numerically distinct **internal** 2D periodic incompressible formulations agree within the declared tolerance on the specified reference case, and the finite-difference formulation demonstrates its declared spatial convergence.

It does not establish:

- external independent replication or peer review;
- a 3D or general-purpose CFD solver;
- non-periodic boundary support;
- reproduction, validation, or refutation of a finite-time Navier-Stokes singularity;
- MHD or plasma physics;
- laboratory validation;
- propulsion, shielding, stealth, cloaking, or operational capability.

The report remains fail-closed at `SIMULATED_ONLY` and is SHA-256 bound.

## Next gate

Only after G4 passes should a separate G5 introduce a bounded quasi-static MHD reference problem. G5 should first reproduce known Lorentz-force damping and a zero-field hydrodynamic limit before any adaptive electromagnetic-control hypothesis is tested.
