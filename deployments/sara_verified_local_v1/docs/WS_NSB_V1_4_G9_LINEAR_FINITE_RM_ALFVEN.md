# WS-NSB v1.4 — G9 Linear Finite-Rm Alfvén Gate

## Purpose

G9 is the first WS-NSB gate that evolves a magnetic perturbation explicitly in time and couples it back to the velocity field. It advances beyond the imposed-field quasi-static G7/G8 references while remaining deliberately narrow: a one-dimensional, periodic, linearized, incompressible resistive-viscous Alfvén reference around a uniform guide field.

This gate is designed to verify induction/backreaction numerics and energy transfer before any nonlinear or multidimensional MHD claim is considered.

## Bounded equations

The transverse magnetic perturbation is written in Alfvén-speed units. Constant density and the uniform guide-field normalization are absorbed into `v_A`:

\[
\partial_t u = v_A\,\partial_x b + \nu\,\partial_{xx}u,
\]

\[
\partial_t b = v_A\,\partial_x u + \eta\,\partial_{xx}b.
\]

The analytical gate uses equal viscosity and magnetic diffusivity,

\[
\nu=\eta=d,
\]

so the Elsässer variables diagonalize the system exactly.

For

\[
u(x,0)=\sin(kx),\qquad b(x,0)=0,
\]

the continuum reference is

\[
u(x,t)=e^{-dk^2t}\sin(kx)\cos(v_Akt),
\]

\[
b(x,t)=e^{-dk^2t}\cos(kx)\sin(v_Akt).
\]

The implementation uses second-order centered periodic differences and classical RK4. Temporal convergence is isolated by comparing against the exact semi-discrete solution using the centered-difference symbols

\[
\tilde{k}=\frac{\sin(kh)}{h},
\qquad
\tilde{k}_2^2=\frac{4\sin^2(kh/2)}{h^2}.
\]

## Verification matrix

The default spatial gate uses `N = 32, 64, 128`, `k = 2`, `v_A = 1`, and `nu = eta = 0.02`, comparing the fully discrete solution against the continuum damped Alfvén reference.

The temporal gate fixes `N = 128` and uses `dt = 0.016, 0.008, 0.004`, comparing against the exact semi-discrete reference so the RK4 order can be measured without spatial truncation dominating.

The quarter-Alfvén-period transfer case evaluates whether an initially kinetic perturbation transfers almost entirely into magnetic perturbation energy while the total energy decays consistently with the equal-diffusivity analytical envelope.

A mode-scale magnetic Reynolds proxy is recorded as

\[
Rm_k=\frac{|v_A|}{\eta k}.
\]

Control cases verify pure magnetic diffusion at `v_A = 0`, symmetry under `v_A -> -v_A`, magnetic antisymmetry under that sign reversal, and zero generated magnetic field when coupling is removed.

## Default acceptance criteria

- spatial observed order >= 1.9;
- finest spatial combined L2 error <= 1e-3;
- temporal observed order >= 3.6;
- finest temporal combined L2 error <= 1e-9;
- quarter-period magnetic energy fraction >= 0.999;
- quarter-period total-energy relative error <= 2e-4;
- diffusion-only magnetic L2 error <= 5e-5;
- sign-symmetry and zero-coupling residuals <= 1e-12;
- deterministic report digest validates.

## Claims boundary

Passing G9 supports only:

`IMPLEMENTED IN SOFTWARE — SIMULATED ONLY`

More specifically, it supports a bounded **linearized finite-Rm induction/backreaction reference** with an explicitly evolved magnetic perturbation.

It does not establish:

- a nonlinear MHD solver;
- compressible MHD;
- general 2D or 3D MHD geometry or boundary conditions;
- Hall-MHD, two-fluid, kinetic, or plasma capability;
- adaptive electromagnetic control;
- laboratory validation;
- propulsion, shielding, stealth, cloaking, or operational capability;
- reproduction or validation of any finite-time Navier-Stokes singularity construction.

A successful G9 is therefore a prerequisite for, not evidence of, a later nonlinear finite-Rm MHD capability. The next defensible primary gate is a nonlinear periodic incompressible MHD reference with separately tracked kinetic, magnetic, viscous, and resistive energy budgets and known invariant/decay controls.
