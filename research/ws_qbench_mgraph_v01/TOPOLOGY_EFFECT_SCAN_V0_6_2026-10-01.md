# WS-QBENCH-MGRAPH v0.6 direct topology-effect scan — 2026-10-01

## Status

`SIMULATED ONLY` / independent numerical diagnostic. This note does **not** resolve source-lock gaps G1-G4 and does not claim an experimental phase transition or exact Figure 4 reproduction.

The quantity analyzed here is the direct topology effect

`E(r) = IPR_source(r) - IPR_null(r)`

rather than the reference-relative interaction `I(r; r0)=E(r)-E(r0)`.

A zero of `E(r)` means the source and selected null have equal ensemble-mean IPR at that sampled/interpolated scale ratio. It is null-family dependent and is **not** automatically a physical critical point.

## Baseline design

- `eta = {0.5, 1.0, 2.0}`;
- `Nmax = {60, 80, 100}`;
- first 30 eigenstates;
- `omega0=1`, `h_parallel=h0=0`;
- 40 stochastic null realizations per cutoff for Delta-sign and randomized-phase controls;
- magnitude-only phase-stripped control evaluated deterministically;
- local linear interpolation only inside sampled adjacent sign-change brackets.

## Direct `E(r)=0` estimates through Nmax=100

### eta = 0.5

| Nmax | Delta-sign | randomized phase | phase stripped |
|---:|---:|---:|---:|
|60|1.9992|1.7169|2.3097|
|80|1.9767|1.7279|2.3097|
|100|1.9965|1.7234|2.3097|

All three null families show one high-scale sign change, but at materially different ratios.

### eta = 1.0

| Nmax | Delta-sign | randomized phase | phase stripped |
|---:|---:|---:|---:|
|60|2.9367|2.2037|none in sampled interval|
|80|2.8252|2.2192|none in sampled interval|
|100|2.9313|2.2135|none in sampled interval|

The two phase-sensitive controls again cross at distinct ratios. The phase-stripped topology effect remains negative over the sampled moderate/high-scale window.

### eta = 2.0 — initial Nmax<=100 result

| Nmax | Delta-sign low zero | Delta-sign high zero | randomized-phase high zero | phase-stripped zero |
|---:|---:|---:|---:|---:|
|60|1.6934|3.5779|3.6218|1.9127|
|80|1.6475|3.4962|3.6107|1.9365|
|100|1.6819|3.5014|3.7660|1.9413|

At `Nmax<=100` the Delta-sign ensemble appeared re-entrant: a low-scale positive region, a negative intermediate region, then a positive high-scale region. This was explicitly treated as a finite-model clue requiring a higher-cutoff falsification gate.

## High-cutoff falsification: eta=2, Nmax=120 and 140

That gate materially changes the interpretation.

| Nmax | Delta-sign low zero | Delta-sign high zero | randomized-phase high zero | phase-stripped zero |
|---:|---:|---:|---:|---:|
|120|1.6393|3.4763|3.6787|1.9456|
|140|~0.582 apparent*|3.5671|3.5385|1.9464|

`*` At `Nmax=140`, the low-scale Delta-sign ensemble means from `r=0.25` through `1.5` are all small compared with their ensemble dispersion. Using 40 null realizations, the mean divided by its estimated standard error remains below 1 in absolute value at every sampled low-scale point. The apparent ~0.582 interpolation is therefore **not evidence for a resolved physical or numerical zero**; it is noise-level structure and is not promoted.

The high-scale sign change, by contrast, persists at both `Nmax=120` and `140`. The Delta-sign high zero remains in the neighborhood of `r≈3.5`, and the randomized-phase high zero remains in the same broad high-scale regime, though with noticeable ensemble/cutoff variation.

## Revised interpretation

The higher-cutoff test **demotes the low-scale Delta-sign re-entrant branch**. It may be a finite-cutoff or low-signal ensemble artifact; current evidence does not resolve which. It must not be presented as a surviving re-entrant regime.

The narrower result that survives is:

1. no single topology-only localization sign rule exists across null families;
2. the phase-sensitive controls show a reproducible high-scale sign change in the tested finite model;
3. the location of that sign change remains null-family dependent;
4. the low-scale `eta=2` Delta-sign sign structure fails the current high-cutoff/significance gate and is retained as **negative evidence**;
5. the phase-stripped control behaves differently from both phase-sensitive controls, preventing a universal phase-topology claim.

## Deeper structural relation

The normalized magnetic-Laplacian observable `lambda1` removes a global positive hopping scale through degree normalization, whereas the physical Hamiltonian retains the ratio between hopping and onsite energy scales. A robust graph-level topology signal can therefore coexist with a scale-dependent and null-dependent localization response.

The evidence now supports the separation

`graph structure -> lambda1` (scale-normalized structural channel)

versus

`graph structure × energy-scale ratios -> eigenvectors/IPR` (scale-bearing physical channel),

while **rejecting** the stronger inference that every apparent low-scale IPR sign feature is structurally meaningful.

## Next falsification gate

Before promotion:

- increase `eta=2`, `Nmax>=140` null ensembles well beyond 40 realizations;
- resolve individual low-energy eigenstate behavior rather than only mean IPR;
- test multiple eigenstate windows;
- repeat the high-scale zero at `Nmax>140` where numerically practical;
- use an independent numerical implementation;
- substitute the source-paper Figure 4 normalization once G2 is source-locked.
