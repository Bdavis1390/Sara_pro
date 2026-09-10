# WS-NSB v1.2 — G7 Anisotropic Low-Rm Imposed-Field Reference

## Purpose

G7 is the first WS-NSB gate to place a **direction-dependent quasi-static magnetic damping operator inside the existing nonlinear 2D periodic vorticity-streamfunction solver**.

It follows G5/G6 Hartmann references. It is deliberately narrower than a full MHD solver: the applied magnetic field is imposed, magnetic Reynolds number is assumed asymptotically small, and no induction equation is solved.

## Reduced quasi-static operator

For a homogeneous imposed field aligned with the `x`/parallel direction, the normalized Fourier-space magnetic contribution is

\[
\left.\frac{d\hat\omega_{\mathbf k}}{dt}\right|_B
=-\Lambda\frac{k_\parallel^2}{|\mathbf k|^2}\hat\omega_{\mathbf k}.
\]

This captures the orientation-dependent Joule damping characteristic of the low-\(R_m\) quasi-static limit. Modes invariant along the imposed field have `k_parallel = 0` and therefore no magnetic damping in this periodic homogeneous reference. Modes whose wavevector is fully parallel to the field have the maximum normalized magnetic decay rate `Lambda`.

The full bounded G7 vorticity equation is

\[
\partial_t\omega+\mathbf u\cdot\nabla\omega
=\nu\nabla^2\omega+\mathcal L_B[\omega],
\qquad\nabla\cdot\mathbf u=0.
\]

The hydrodynamic solver, Poisson inversion, spectral derivatives and two-thirds dealiasing are inherited from the already-gated WS-NSB v0.8 G3 implementation.

## Exact single-mode reference

For a Laplacian eigenmode with wavevector `(k_parallel, k_transverse)`, nonlinear self-advection vanishes and the exact vorticity amplitude is

\[
\hat\omega(t)=\hat\omega(0)\exp[-\lambda t],
\]

where

\[
\lambda
=\nu|\mathbf k|^2
+\Lambda\frac{k_\parallel^2}{|\mathbf k|^2}.
\]

G7 exercises the orientation set

- `(0,2)` — magnetic null / flow aligned with the imposed field;
- `(1,3)` — weak magnetic damping;
- `(1,1)` — 50% orientation factor;
- `(3,1)` — strong magnetic damping;
- `(2,0)` — maximum magnetic damping.

## Magnetic kinetic-energy sink

For the normalized operator, the instantaneous Joule dissipation diagnostic is

\[
D_B
=\frac{\Lambda}{N_g^4}
\sum_{\mathbf k\ne0}
\frac{k_\parallel^2}{|\mathbf k|^2}
\frac{|\hat\omega_{\mathbf k}|^2}{|\mathbf k|^2}
\ge0.
\]

The G7 nonlinear mixed-mode run compares the same initial state with `Lambda=0` and `Lambda>0` and requires a measurable reduction in kinetic energy while preserving the periodic incompressibility/Poisson controls.

## Acceptance criteria

The default CI gate requires:

- RK2 observed temporal order at least 1.8 on the `(3,1)` exact decay case;
- finest temporal single-mode L2 error no greater than `5e-5`;
- maximum error in the inferred orientation-dependent magnetic decay rate no greater than `5e-4`;
- `k_parallel=0` magnetic dissipation no greater than `1e-12`;
- `k_transverse=0` magnetic decay equal to the full normalized damping coefficient within the decay-rate tolerance;
- zero-magnetic limit consistent with pure viscous decay;
- nonlinear mixed-mode magnetic energy reduction at least `1e-3` versus the zero-field counterpart;
- divergence and Poisson residuals no greater than `1e-10`;
- nonlinear mean-vorticity drift no greater than `1e-12`.

## Claims boundary

**Classification: `SIMULATED_ONLY`.**

G7 verifies only the bounded low-\(R_m\), homogeneous imposed-field Fourier damping operator in a periodic 2D reference solver.

It does **not** establish:

- a finite-magnetic-Reynolds-number or full MHD solver;
- a magnetic induction-equation solution;
- general 2D/3D magnetofluid boundary-condition capability;
- Hall-MHD, two-fluid, kinetic, or plasma capability;
- adaptive electromagnetic flow control;
- laboratory validation;
- finite-time Navier–Stokes singularity reproduction;
- propulsion, shielding, stealth, cloaking, or operational capability.

Those remain separate future gates.

## Evidence

Run:

```bash
ws-nsb-g7 --output ws_nsb_g7_report.json
ws-nsb-g7 --verify ws_nsb_g7_report.json
```

The report is deterministically bound with the repository `canonical_digest` mechanism and CI uploads it as `ws-nsb-v1-2-g7-report`.
