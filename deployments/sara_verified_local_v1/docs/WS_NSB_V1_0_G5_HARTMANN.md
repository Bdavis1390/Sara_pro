# WS-NSB v1.0 — G5 Quasi-Static Hartmann-Flow Reference

## Purpose

G5 is the first Worldshepherd WS-NSB gate that introduces a magnetic body-force reference. It deliberately starts with a classical low-magnetic-Reynolds-number Hartmann channel problem instead of jumping directly from hydrodynamics to a general MHD or plasma solver.

The objective is narrow: verify that a bounded numerical source-term model reproduces the classical transverse-field velocity profile, recovers the zero-field hydrodynamic limit, and produces the expected resistive magnetic damping under a fixed pressure gradient.

## Literature basis

For low magnetic Reynolds number, the induced magnetic field can be neglected relative to the imposed field and the quasi-static approximation is applicable. Classical Hartmann flow between parallel plates under a transverse magnetic field has an analytical velocity profile governed by the Hartmann number. Published validation literature uses this problem specifically to verify magnetic source terms in MHD codes.

Representative basis used for this gate:

- classical/generalized Hartmann-flow formulation under the quasi-static approximation, including the standard hyperbolic-cosine velocity profile and recovery of Poiseuille flow in the appropriate field orientation/limit;
- published MHD code-verification literature identifying Hartmann–Poiseuille flow as an analytical benchmark for magnetohydrodynamic solvers.

## Normalized reference problem

G5 solves

\[
\frac{d^2u}{dy^2}-Ha^2u=-1,
\qquad -1\le y\le1,
\qquad u(-1)=u(1)=0.
\]

For \(Ha>0\), the exact normalized profile is

\[
u(y)=\frac{1}{Ha^2}\left[1-\frac{\cosh(Ha\,y)}{\cosh(Ha)}\right].
\]

The zero-field limit is the plane-Poiseuille profile

\[
u(y)=\frac12(1-y^2).
\]

The exact section-mean velocity under the same pressure-gradient normalization is

\[
\bar u=\frac{1}{Ha^2}\left(1-\frac{\tanh Ha}{Ha}\right),
\]

with \(\bar u\to1/3\) as \(Ha\to0\).

The numerical implementation uses a second-order centered finite-difference discretization and a direct tridiagonal solve.

## Required controls

G5 executes:

1. a Hartmann-number sweep `Ha = 0, 0.5, 1, 2, 5, 10`;
2. a factor-two spatial-refinement family at `Ha = 2` using `N = 33, 65, 129`;
3. a strict `Ha = 0` hydrodynamic-limit comparison against plane Poiseuille flow;
4. a `+Ha/-Ha` numerical symmetry control because this reduced source term depends on magnetic-field magnitude squared;
5. monotonic centerline-velocity and flow-rate checks under a fixed pressure gradient.

## Default acceptance criteria

- observed spatial order at `Ha = 2`: `>= 1.8`;
- finest-grid profile L2 error: `<= 1e-5`;
- zero-field hydrodynamic-limit L2 error: `<= 1e-12`;
- `+Ha/-Ha` profile L2 difference: `<= 1e-14`;
- maximum mean-flow relative error across the sweep: `<= 5e-4`;
- centerline and mean velocity must decrease monotonically as `Ha` increases for the fixed-pressure-gradient reference.

## Claims boundary

Passing G5 supports only the following bounded statement:

> This software numerically reproduces the declared steady 1D quasi-static Hartmann reference problem, including its zero-field hydrodynamic limit and the expected field-strength-dependent damping trend, within the declared numerical tolerances.

It does **not** establish:

- a full MHD solver;
- solution of the magnetic induction equation;
- Hall-MHD, two-fluid, kinetic, or plasma capability;
- a 2D/3D magnetofluid solver;
- adaptive electromagnetic vortex control;
- laboratory validation;
- propulsion, shielding, stealth, cloaking, or operational capability;
- reproduction, validation, or refutation of any finite-time Navier–Stokes singularity.

The evidence remains `SIMULATED_ONLY` and is SHA-256 bound.

## Next gate

After G5 passes, G6 should introduce a time-dependent quasi-static MHD test with a known energy budget and an explicit zero-field reduction to a previously validated hydrodynamic solver. Only after that should Worldshepherd test adaptive Lorentz-force control as a hypothesis rather than a built-in expected result.
