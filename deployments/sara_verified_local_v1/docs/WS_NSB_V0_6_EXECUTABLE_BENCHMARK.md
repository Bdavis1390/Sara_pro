# WS-NSB v0.6 — Executable G0/G1 Instrumentation Benchmark

## Purpose

WS-NSB v0.6 is a deterministic, evidence-governed software benchmark for two precursor gates:

- **G0_INSTRUMENTATION** — verify second-order central-difference curl/divergence instrumentation against manufactured analytic fields.
- **G1_SCALING** — verify that the benchmark's log-slope instrumentation recovers explicitly supplied asymptotic power laws.

It is intentionally **not** a Navier–Stokes time integrator, an MHD solver, a plasma solver, or a physical experiment.

## Claims boundary

A passing v0.6 report supports only the statement that the implemented diagnostic operators and synthetic scaling instrumentation behave as specified for this benchmark.

It does **not** establish any of the following:

- finite-time Navier–Stokes blowup reproduction;
- correctness or independent acceptance of any external mathematical proof;
- magnetic or electromagnetic vortex stabilization;
- MHD or plasma control capability;
- laboratory validation;
- propulsion, shielding, stealth, or cloaking effects;
- operational capability.

The report model therefore fails closed if any such flag is promoted, and its capability status is fixed to `SIMULATED_ONLY`.

## Manufactured G0 fields

The velocity field is the unit ABC Beltrami flow

```text
u = (sin(z) + cos(y),
     sin(x) + cos(z),
     sin(y) + cos(x))
```

which satisfies analytically

```text
div(u) = 0
curl(u) = u
```

The magnetic test field is

```text
B = (sin(y), sin(z), sin(x))
```

with `div(B) = 0`.

A separate field

```text
F = (sin(x), sin(y), sin(z))
```

has exact divergence

```text
div(F) = cos(x) + cos(y) + cos(z)
```

and is used to measure divergence-operator error rather than relying only on zero-divergence cancellation.

The normalized manufactured current proxy is the analytic curl of B,

```text
J = (-cos(z), -cos(x), -cos(y))
```

and the benchmark evaluates the curl of the Lorentz proxy `J x B` only as an instrumentation diagnostic. It is not an MHD solution.

## G0 acceptance

The default resolutions are `8,16,32`. For successive grid refinements the benchmark estimates

```text
p = log(error_coarse / error_fine) / log(h_coarse / h_fine)
```

for both curl/vorticity error and known-divergence error.

G0 passes only if every observed order lies in the provisional second-order acceptance band

```text
1.8 <= p <= 2.2
```

This is an engineering test tolerance, not a physical constant.

## G1 scaling instrumentation

For `tau = 1 - t` and default `h = 0.005`, v0.6 synthesizes exact power-law data for the declared exponents

```text
radial length      ~ tau^(1/2)
axial length       ~ tau^(1/2 - h)
peak velocity      ~ tau^(-1/2 - h)
core energy        ~ tau^(1/2 - 3h)
angular Reynolds   ~ tau^(-h)
```

The benchmark then independently re-estimates each exponent with log-linear regression. G1 passes when the maximum absolute slope error is at most `1e-10`.

This gate validates the **measurement pipeline for declared scaling laws**. Because the same declared laws generate the synthetic values, a G1 pass is not evidence that a PDE solution exhibits those laws.

## Cancellation conditioning and verification escalation

The module exposes the scalar diagnostic

```text
kappa = sum(abs(F_i)) / (abs(sum(F_i)) + epsilon)
```

with provisional escalation policy:

```text
kappa < 10        -> NORMAL
10 <= kappa < 100 -> REFINE_TIMESTEP
100 <= kappa < 1000 -> REFINE_TIMESTEP_AND_MESH
kappa >= 1000     -> REQUIRE_INDEPENDENT_SOLVER
```

The scalar form is a precursor policy primitive. A future PDE implementation should extend it to normed vector/tensor residuals with uncertainty propagation.

## Control outcome classifier

A separate helper classifies a positive baseline stretching metric and a controlled value as:

- `SUPPRESSION`
- `NEUTRAL`
- `AMPLIFICATION`
- `REDIRECTION`

The default neutral band is 5 percent. This classifier does not itself perform control or establish electromagnetic authority.

## Running

From `deployments/sara_verified_local_v1` after installation:

```bash
ws-nsb-benchmark
```

Write a hash-bound report:

```bash
ws-nsb-benchmark --output artifacts/ws_nsb_v0_6.json
```

Verify a previously generated report:

```bash
ws-nsb-benchmark --verify artifacts/ws_nsb_v0_6.json
```

Alternative resolutions and h exponent:

```bash
ws-nsb-benchmark --resolutions 8,12,16 --h-exponent 0.005
```

## Evidence custody

Every generated report includes a canonical SHA-256 digest computed with the existing Worldshepherd qualification utility. Tampering with a report after generation causes verification failure.

## Next gate

The next implementation stage is **WS-NSB v0.7 / G2**, which should add an actual incompressible PDE time-integration benchmark plus grid/time-step convergence. That stage must remain separate from any claim of singularity reproduction. MHD coupling belongs to a later gate after the hydrodynamic solver is independently validated.
