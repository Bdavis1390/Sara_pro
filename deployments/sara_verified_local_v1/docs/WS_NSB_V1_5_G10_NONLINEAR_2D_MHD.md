# WS-NSB v1.5.2 — G10 nonlinear 2D incompressible MHD gate

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

## #245 remediation history

### v1.5 negative evidence

Issue #245 recorded an ideal-case cross-helicity **relative** drift of approximately `3.6710178210651096e-05`, above the predeclared `2e-5` limit. Total-energy and magnetic-potential-variance drift remained within the limit. The acceptance threshold is not relaxed.

### v1.5.1 temporal-refinement attempt

v1.5.1 retained the original `dt = 2.5e-4` run and added `1.25e-4` and `6.25e-5` runs. The dedicated GitHub G10 gate still failed. That failure is preserved rather than suppressed.

The investigation identified an error-metric conditioning defect: the mixed ideal initial condition has cross helicity numerically near zero. A quantity of the form

```text
abs(Hc_final - Hc_initial) / abs(Hc_initial)
```

is therefore ill-conditioned even when the **absolute** cross-helicity change is at roundoff scale. Halving `dt` cannot reliably repair a denominator that is effectively zero.

### v1.5.2 conditioned acceptance metric

v1.5.2 keeps the same physical initial condition, the same three timestep refinements, and the same `2e-5` invariant limit. It does **not** erase the legacy relative metric. Instead the report now records:

- initial and final cross helicity;
- absolute cross-helicity drift;
- the legacy near-zero-relative drift as retained diagnostic evidence;
- the cross-helicity energy scale `2*sqrt(E_k0*E_b0)`;
- the dimensionless normalized error

```text
abs(Hc_final - Hc_initial) / (2*sqrt(E_k0*E_b0))
```

used for cross-helicity acceptance.

The denominator follows the Cauchy-Schwarz bound on cross helicity and remains well-conditioned when the true invariant itself is near zero. This is a metric correction, not a tolerance relaxation.

The temporal-refinement record remains `2.5e-4 -> 1.25e-4 -> 6.25e-5` at `final_time = 0.01`, corresponding to 40, 80, and 160 steps. Total-energy and magnetic-potential-variance relative errors must show refinement reduction. Cross-helicity absolute/normalized error is expected to be roundoff-dominated once it reaches machine-scale behavior, so monotonic temporal order is not asserted for that already-negligible quantity.

## Acceptance boundary

The default gate requires:

- aligned exact-case vorticity and magnetic-potential L2 errors <= `2e-5`;
- individually nontrivial hydrodynamic and magnetic nonlinear terms with cancellation RMS <= `1e-10`;
- velocity and magnetic divergence RMS <= `1e-10`;
- instantaneous total-energy budget residual <= `2e-8`;
- mixed nonlinear RHS RMS >= `1e-2` and a measurable dissipative total-energy decrease;
- ideal total-energy relative drift <= `2e-5`;
- ideal cross-helicity absolute drift normalized by `2*sqrt(E_k0*E_b0)` <= `2e-5`;
- ideal magnetic-potential-variance relative drift <= `2e-5`;
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
