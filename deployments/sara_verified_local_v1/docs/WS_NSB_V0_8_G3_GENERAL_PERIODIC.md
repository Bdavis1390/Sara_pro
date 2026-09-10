# WS-NSB v0.8 — G3 Mode-General Periodic Incompressible Solver

## Purpose

G3 replaces the Taylor-Green-specific velocity reconstruction used by G2 with a mode-general 2D periodic vorticity-streamfunction solver. It is a numerical verification gate, not a physical capability claim.

## Formulation

The solver advances

\[
\partial_t\omega + \mathbf{u}\cdot\nabla\omega = \nu\nabla^2\omega
\]

on a periodic \([0,2\pi)^2\) domain. Velocity is reconstructed from

\[
-\nabla^2\psi = \omega,\qquad
u_x = \partial_y\psi,\qquad
u_y = -\partial_x\psi.
\]

The implementation uses a pure-Python radix-2 FFT, Fourier Poisson inversion and derivatives, pseudo-spectral nonlinear advection, two-thirds dealiasing, and explicit midpoint RK2 time stepping.

## Required evidence

The default benchmark executes three independent checks:

1. **Multimode manufactured Poisson reconstruction** using several Fourier modes not restricted to Taylor-Green structure.
2. **Taylor-Green regression** at three factor-two timesteps to verify second-order temporal convergence.
3. **Nonlinear mixed-mode evolution** to prove the solver is exercising nonzero advection rather than only a cancelling manufactured mode.

The nonlinear case must preserve mean vorticity to tolerance, remain divergence-free to tolerance, maintain a small Poisson residual, evolve by a nontrivial amount, and show nonincreasing kinetic energy and enstrophy for positive viscosity.

## Default acceptance criteria

- manufactured Poisson/velocity/residual errors: `<= 1e-10`
- divergence RMS: `<= 1e-10`
- Taylor-Green temporal order: `>= 1.8`
- finest Taylor-Green vorticity L2 error: `<= 1e-6`
- mean-vorticity drift: `<= 1e-12`
- nonlinear advection RMS: `>= 1e-2`
- nonlinear state-change RMS: `>= 1e-3`
- kinetic energy and enstrophy: nonincreasing for the dissipative reference runs

## Claims boundary

Passing G3 supports only the statement that this exact software implements a bounded, mode-general **2D periodic** incompressible vorticity-streamfunction solver on radix-2 grids and passes the declared numerical checks.

It does **not** establish:

- a 3D solver;
- a general-purpose CFD solver;
- non-periodic boundary support;
- reproduction, validation, or refutation of a finite-time Navier-Stokes singularity;
- MHD or plasma physics;
- laboratory validation;
- propulsion, shielding, stealth, cloaking, or operational capability.

The report is fail-closed at `SIMULATED_ONLY` and SHA-256 binds its serialized evidence.

## Next gate

G4 should add a second numerically independent hydrodynamic formulation (for example, a finite-difference/finite-volume projection or independent Poisson discretization) and compare nontrivial periodic cases before any MHD coupling is promoted into the main validation chain.
