# WS-NSB v1.3 — G8 Independent Magnetic Replication Gate

## Purpose

G8 tests the G7 low-magnetic-Reynolds-number imposed-field magnetic operator through a numerically distinct implementation.

G7 uses a Fourier-space damping operator. G8 does **not** call that operator. Instead, it starts from analytical periodic velocity fields, applies normalized quasi-static Ohm/Lorentz relations in physical space, takes the Lorentz-force curl with second-order centered finite differences, and compares the result against the analytical mode-by-mode target.

This is an internal cross-method verification gate, not an independent external laboratory or third-party replication.

## Bounded model

The reference is strictly two-dimensional, periodic, z-invariant, homogeneous, and uses a uniform in-plane imposed field

\[
\hat{\mathbf B}=(\cos\theta,\sin\theta,0).
\]

Magnetic-field magnitude, electrical conductivity, density, and other normalization factors are absorbed into the nonnegative coupling parameter \(\Lambda\).

For velocity \(\mathbf u=(u,v,0)\), the normalized low-Rm induced current is

\[
j_z=uB_y-vB_x.
\]

The Lorentz force is

\[
\mathbf f_L
=
\Lambda j_z(-B_y,B_x,0).
\]

The vorticity tendency used by the finite-difference implementation is

\[
(\nabla\times\mathbf f_L)_z
=
\Lambda\left(
B_x\partial_x j_z+B_y\partial_y j_z
\right).
\]

For a Fourier mode with wavevector \(\mathbf k\), incompressibility gives the analytical reference

\[
\left.\partial_t\hat\omega_{\mathbf k}\right|_B
=
-\Lambda
\frac{(\mathbf k\cdot\hat{\mathbf B})^2}{|\mathbf k|^2}
\hat\omega_{\mathbf k}.
\]

The Joule/Lorentz work identity is also checked:

\[
D_J
=
\Lambda\langle j_z^2\rangle
=
-\langle\mathbf u\cdot\mathbf f_L\rangle
\ge 0.
\]

In this strict 2D in-plane-field geometry the induced current is purely z-directed and all fields are z-invariant, so \(\nabla\cdot\mathbf j=0\) follows geometrically. G8 therefore does **not** claim an electric-potential Poisson solve.

## Verification matrix

The default gate uses a three-mode analytical streamfunction field and grid sizes 32, 64, and 128. It requires factor-two refinement and verifies second-order spatial convergence of the physical-space magnetic vorticity operator.

It separately exercises:

- field parallel to the test wavevector: maximum magnetic damping;
- field perpendicular to the wavevector: magnetic null;
- x-directed imposed field with oblique wavevector;
- arbitrary continuous field angle;
- reversal \(\mathbf B\rightarrow-\mathbf B\), which must leave the Lorentz damping unchanged;
- \(\Lambda=0\), which must remove the magnetic operator and Joule dissipation;
- Joule dissipation equals negative Lorentz work.

## Default acceptance criteria

- observed spatial order >= 1.9;
- finest-grid L2 error <= 5e-3;
- finest-grid relative L2 error <= 3e-3;
- every orientation-case L2 error <= 5e-3;
- perpendicular-field magnetic sink <= 1e-12;
- field-reversal L2 difference <= 1e-12;
- zero-magnetic operator and dissipation <= 1e-12;
- Joule/work identity error <= 1e-12;
- deterministic report digest validates.

## Claims boundary

Passing G8 supports only:

`IMPLEMENTED IN SOFTWARE — SIMULATED ONLY`

Specifically, it supports a numerically distinct internal replication of the bounded G7 low-Rm imposed-field magnetic damping operator.

It does not establish:

- magnetic induction or finite-Rm MHD;
- an electric-potential/current-continuity solver for general geometries;
- general 2D or 3D magnetofluid boundary conditions;
- Hall-MHD, two-fluid, kinetic, or plasma capability;
- adaptive electromagnetic control;
- laboratory validation;
- propulsion, shielding, stealth, cloaking, or operational capability;
- reproduction or validation of any finite-time Navier-Stokes singularity construction.

The next primary scientific gate after G8 is a separately bounded finite-Rm induction test with an analytical magnetic-diffusion/Alfvén reference, not a promotion to plasma or propulsion claims.
