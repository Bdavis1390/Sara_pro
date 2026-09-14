# WS-NSB v1.5.1 — G10 nonlinear 2D incompressible MHD gate

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

## v1.5.1 numerical-defect remediation

Issue #245 identified that the original ideal-case `dt = 2.5e-4` configuration produced cross-helicity relative drift above the predeclared `2e-5` invariant limit while the other G10 gates remained healthy. The acceptance threshold is not relaxed.

v1.5.1 changes only the ideal-invariant temporal evidence path:

- preserves the original coarse `dt = 2.5e-4` run as regression evidence;
- adds `dt = 1.25e-4` and `dt = 6.25e-5` refinement runs at the same grid and `final_time = 0.01`;
- records the actual effective `dt`, step count, and all three invariant drifts for each run in the hash-bound report;
- uses `dt = 1.25e-4` as the acceptance configuration;
- requires regression coverage to demonstrate that the original coarse run remains above the unchanged threshold, refinement reduces the maximum observed invariant drift, and the `1.25e-4` run satisfies the original `2e-5` limit.

For `final_time = 0.01`, the requested refinement sequence corresponds to 40, 80, and 160 steps respectively. CI remains the acceptance oracle for the measured drift values; this document does not predeclare a passing numerical result.

## Acceptance boundary

The default gate requires:

- aligned exact-case vorticity and magnetic-potential L2 errors <= `2e-5`;
- individually nontrivial hydrodynamic and magnetic nonlinear terms with cancellation RMS <= `1e-10`;
- velocity and magnetic divergence RMS <= `1e-10`;
- instantaneous total-energy budget residual <= `2e-8`;
- mixed nonlinear RHS RMS >= `1e-2` and a measurable dissipative total-energy decrease;
- ideal total-energy, cross-helicity, and magnetic-potential-variance relative drift <= `2e-5` at the v1.5.1 acceptance step size;
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
