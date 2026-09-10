# WS-NSB v1.1 — G6 Transient Quasi-Static Hartmann Reference

## Purpose

G6 adds the first **time-dependent magnetic energy-budget gate** to the Worldshepherd Navier–Stokes Benchmark (WS-NSB) ladder.

It follows the G5 steady quasi-static Hartmann reference and intentionally remains one-dimensional and reduced. The point is to verify the temporal treatment of the imposed-field magnetic damping term before any 2D/3D MHD, induction equation, plasma model, or adaptive electromagnetic controller is admitted into the primary validation chain.

## Governing reference

The normalized problem is

\[
\frac{\partial u}{\partial t}
=
\frac{\partial^2u}{\partial y^2}
-Ha^2u+1,
\qquad -1\le y\le1,
\]

with

\[
u(-1,t)=u(1,t)=0,\qquad u(y,0)=0.
\]

The forcing term is a fixed unit pressure-gradient normalization. The reduced electromagnetic contribution is the linear sink \(-Ha^2u\).

The code uses Crank–Nicolson time integration and second-order centered finite differences in space.

## Exact transient reference

With \(x=(y+1)/2\), the constant forcing has the Dirichlet sine expansion

\[
1=\sum_{n\ {\rm odd}}\frac{4}{n\pi}\sin(n\pi x).
\]

Therefore

\[
u(y,t)
=
\sum_{n\ {\rm odd}}
\frac{4}{n\pi}
\frac{1-e^{-\lambda_n t}}{\lambda_n}
\sin\left(\frac{n\pi(y+1)}{2}\right),
\]

where

\[
\lambda_n=\left(\frac{n\pi}{2}\right)^2+Ha^2.
\]

This supplies an independent analytical transient profile for error and convergence measurement.

## Energy budget

For the normalized reference,

\[
E(t)=\frac12\int_{-1}^{1}u^2\,dy
\]

obeys

\[
\frac{dE}{dt}
=
\underbrace{\int u\,dy}_{P_{\rm forcing}}
-
\underbrace{\int (\partial_yu)^2dy}_{D_\nu}
-
\underbrace{Ha^2\int u^2dy}_{D_{\rm EM}}.
\]

The Crank–Nicolson implementation records the forcing work, viscous dissipation, electromagnetic dissipation, and the absolute closure residual. This is the central G6 addition: the magnetic term must appear as a positive energy sink for nonzero \(Ha\), while the \(Ha=0\) control must produce zero electromagnetic dissipation.

## Acceptance criteria

The default gate requires:

- spatial order at least 1.8 on grids 33/65/129 at \(Ha=2\);
- temporal order at least 1.8 using \(\Delta t=0.08,0.04,0.02\);
- finest spatial transient-profile L2 error no greater than \(10^{-5}\);
- finest temporal L2 error no greater than \(5\times10^{-5}\);
- cumulative discrete energy-budget closure residual no greater than \(10^{-10}\);
- zero-field electromagnetic sink no greater than \(10^{-14}\);
- positive electromagnetic dissipation for every nonzero-Hartmann sweep case;
- exact +Ha/-Ha symmetry to within \(10^{-14}\) for this \(Ha^2\) reduced model;
- monotonic centerline and mean-flow reduction as Hartmann number increases;
- long-time consistency with the G5 steady analytical Hartmann profile to within \(10^{-5}\) L2.

## Claims boundary

**Classification: `SIMULATED_ONLY`.**

A G6 pass establishes only that the repository's bounded transient **1D quasi-static Hartmann reference** meets its declared analytical, convergence, energy-budget, sign-control, and steady-limit checks.

It does **not** establish:

- a full MHD solver;
- induction-equation capability;
- 2D or 3D magnetofluid capability;
- Hall-MHD, two-fluid, kinetic, or plasma capability;
- adaptive electromagnetic flow control;
- laboratory validation;
- finite-time Navier–Stokes singularity reproduction;
- propulsion, shielding, stealth, cloaking, or operational capability.

Those remain separate future gates.

## Evidence

Run:

```bash
ws-nsb-g6 --output ws_nsb_g6_report.json
ws-nsb-g6 --verify ws_nsb_g6_report.json
```

The report is deterministically bound through the repository `canonical_digest` mechanism. CI uploads the report as the `ws-nsb-v1-1-g6-report` artifact.
