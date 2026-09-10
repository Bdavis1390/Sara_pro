# WS-NSB v1.6 — G11 Independent Nonlinear MHD Replication

## Purpose

G11 provides a numerically distinct internal replication of the bounded G10 nonlinear 2D periodic incompressible resistive-MHD reference.

The G10 reference uses Fourier pseudo-spectral derivatives and dealiasing. G11 instead evolves the same vorticity/vector-potential equations with second-order centered finite differences and the Arakawa Jacobian. A Fourier transform is used only to invert the **discrete finite-difference periodic Poisson operator** required to reconstruct streamfunction from vorticity.

## Equations

The independent evolution is

```text
domega/dt = J(psi, omega) - J(a, j) + nu*laplacian_h(omega)
da/dt     = J(psi, a) + eta*laplacian_h(a)
```

with

```text
-laplacian_h(psi) = omega
B = (D_y a, -D_x a)
j = -laplacian_h(a)
```

where `J` is the Arakawa discretization of the Jacobian.

## Acceptance evidence

The default gate requires:

- decreasing finite-difference/spectral disagreement over 16/32/64 grids;
- observed cross-method convergence order >= 1.6;
- finest combined relative field disagreement <= 1%;
- nontrivial aligned Alfvénic advection and Lorentz terms that cancel to <= 1e-10;
- induction advection <= 1e-10 in the aligned state;
- velocity and magnetic divergence <= 1e-10;
- dissipative finite-difference total energy decrease;
- final finite-difference/spectral total-energy disagreement <= 1%;
- deterministic SHA-256 report verification.

## Scientific boundary

G11 is an **internal cross-method numerical replication**. It is not an independent third-party validation. It remains a 2D periodic incompressible resistive-MHD reference and does not establish compressible MHD, 3D MHD, Hall-MHD, two-fluid, kinetic, plasma, or non-periodic physical-boundary capability.

## Claims control

The report is fail-closed at `SIMULATED_ONLY` and explicitly rejects unsupported claims of laboratory validation, adaptive electromagnetic control, propulsion, shielding, stealth, cloaking, operational capability, or finite-time Navier-Stokes singularity reproduction.
