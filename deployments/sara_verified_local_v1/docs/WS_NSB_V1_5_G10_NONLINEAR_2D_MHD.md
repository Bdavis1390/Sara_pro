# WS-NSB v1.5 — G10 nonlinear 2D incompressible MHD gate

## Scope

G10 advances the WS-NSB chain from the bounded linear Alfvén G9 reference to a bounded nonlinear 2D periodic incompressible resistive-MHD reference.

The state uses scalar vorticity `omega` and out-of-plane magnetic vector potential `a`:

- `u = (d_y psi, -d_x psi)` with `omega = -laplacian(psi)`
- `B = (d_y a, -d_x a)` with `j = -laplacian(a)`

The normalized equations are

```text
domega/dt = -u.grad(omega) + B.grad(j) + nu*laplacian(omega)
da/dt     = -u.grad(a)     + eta*laplacian(a)
```

All spatial derivatives are Fourier pseudo-spectral and nonlinear products are two-thirds dealiased. Time integration uses explicit midpoint RK2.

## Evidence cases

G10 requires three separate cases.

1. **Aligned Alfvénic exact case.** `a = psi` and equal viscosity/resistivity create a nonlinear state in which hydrodynamic vorticity advection and Lorentz curl are individually nonzero but cancel. The remaining evolution is exact diffusion of each Fourier mode.
2. **Mixed nonlinear dissipative case.** Independent velocity and magnetic modes exercise both induction and Lorentz backreaction. The gate checks nontrivial evolution, kinetic + magnetic energy decay, positive viscous/resistive dissipation, instantaneous energy-budget closure, divergence control, and mean-state preservation.
3. **Short ideal invariant case.** With `nu = eta = 0`, the gate checks bounded drift of total energy, cross helicity, and mean-square magnetic potential over a short integration window.

## Acceptance boundary

The default gate requires:

- aligned exact-case vorticity and magnetic-potential L2 errors <= `2e-5`;
- individually nontrivial hydrodynamic and magnetic nonlinear terms with cancellation RMS <= `1e-10`;
- velocity and magnetic divergence RMS <= `1e-10`;
- instantaneous total-energy budget residual <= `2e-8`;
- mixed nonlinear RHS RMS >= `1e-2` and a measurable dissipative total-energy decrease;
- ideal total-energy, cross-helicity, and magnetic-potential-variance relative drift <= `2e-5`;
- deterministic SHA-256 report verification.

These are bounded internal software acceptance thresholds, not universal MHD accuracy claims.

## Claims control

G10 remains `SIMULATED_ONLY`.

Passing G10 supports only the statement that the repository contains and executes a bounded 2D periodic incompressible nonlinear resistive-MHD reference with dynamically evolved magnetic induction and reciprocal Lorentz backreaction under the declared numerical tests.

It does **not** establish:

- compressible or three-dimensional MHD;
- general non-periodic boundary handling;
- Hall-MHD, two-fluid, kinetic, or plasma capability;
- adaptive electromagnetic control;
- laboratory validation;
- finite-time Navier-Stokes singularity reproduction;
- propulsion, shielding, stealth, cloaking, or operational capability.

The gate is therefore an internal numerical-physics milestone, not a physical-system validation claim.
