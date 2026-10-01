# WS-QBENCH-MGRAPH v0.6 direct topology-effect scan — 2026-10-01

## Status

`SIMULATED ONLY` / independent numerical diagnostic. This note does **not** resolve source-lock gaps G1-G4 and does not claim an experimental phase transition or exact Figure 4 reproduction.

The quantity analyzed here is the direct topology effect

`E(r) = IPR_source(r) - IPR_null(r)`

rather than the reference-relative interaction `I(r; r0)=E(r)-E(r0)`.

A zero of `E(r)` means the source and selected null have equal ensemble-mean IPR at that sampled/interpolated scale ratio. It is still null-family dependent and is **not** automatically a physical critical point.

## Design

- `eta = {0.5, 1.0, 2.0}`;
- `Nmax = {60, 80, 100}`;
- first 30 eigenstates;
- `omega0=1`, `h_parallel=h0=0`;
- 40 paired stochastic null realizations per cutoff for Delta-sign and randomized-phase controls;
- magnitude-only phase-stripped control evaluated deterministically;
- local linear interpolation only inside sampled adjacent sign-change brackets.

## Direct `E(r)=0` estimates

### eta = 0.5

| Nmax | Delta-sign | randomized phase | phase stripped |
|---:|---:|---:|---:|
|60|1.9992|1.7169|2.3097|
|80|1.9767|1.7279|2.3097|
|100|1.9965|1.7234|2.3097|

All three null families show one high-scale sign change, but at materially different ratios. The phase-stripped result is essentially cutoff-stable over this range, while the two phase-sensitive controls disagree with it and with each other.

### eta = 1.0

| Nmax | Delta-sign | randomized phase | phase stripped |
|---:|---:|---:|---:|
|60|2.9367|2.2037|none in sampled interval|
|80|2.8252|2.2192|none in sampled interval|
|100|2.9313|2.2135|none in sampled interval|

The two phase-sensitive controls again cross at distinct ratios. The phase-stripped topology effect remains negative over the sampled moderate/high-scale window, so there is no null-independent sign boundary.

### eta = 2.0

| Nmax | Delta-sign low zero | Delta-sign high zero | randomized-phase high zero | phase-stripped zero |
|---:|---:|---:|---:|---:|
|60|1.6934|3.5779|3.6218|1.9127|
|80|1.6475|3.4962|3.6107|1.9365|
|100|1.6819|3.5014|3.7660|1.9413|

This is the most informative case. The Delta-sign control is **re-entrant** within the tested finite model: `E(r)` is positive at low scale, becomes negative at intermediate scale, and becomes positive again at high scale. The magnitude-only phase-stripped control crosses in the opposite direction near `r≈1.93` and remains negative through the tested high-scale region. The randomized-phase control is negative through low/intermediate scale and crosses positive only in the high-scale regime.

## Interpretation

The direct-effect scan sharpens the v0.6 picture:

1. There is no single topology-only localization sign rule.
2. The null family changes both the location and, for `eta=2`, the **number** of sign changes.
3. The `eta=2` Delta-sign re-entrant pattern is a stronger structural clue than the earlier reference-relative interaction zero because it is defined directly on `E(r)`.
4. The high-scale Delta-sign zero at `eta=2` is comparatively stable from `Nmax=80` to `100` (~3.50), while the randomized-phase high zero remains more cutoff-sensitive (~3.61 to ~3.77).
5. The data therefore support a finite-model **multi-regime topology/scale competition**, not a universal monotonic law and not yet a physical phase-transition claim.

## Deeper structural relation

The normalized magnetic-Laplacian observable `lambda1` removes a global positive hopping scale through degree normalization, whereas the physical Hamiltonian retains the ratio between hopping and onsite energy scales. The direct IPR effect can therefore pass through multiple sign regimes even while the graph-level topology diagnostic remains robust.

The emerging separation is:

`graph structure -> lambda1` (scale-normalized structural channel)

versus

`graph structure × energy-scale ratios -> eigenvectors/IPR` (scale-bearing physical channel).

The `eta=2` re-entrant result is consistent with competition between those channels; it is not proof of the underlying mechanism.

## Next falsification gate

Before promotion:

- reproduce the re-entrant `eta=2` pattern at `Nmax > 100`;
- increase stochastic null ensembles substantially;
- resolve individual low-energy eigenstate behavior rather than only mean IPR;
- test whether the sign changes persist under different eigenstate windows;
- rerun using a numerically independent implementation;
- substitute the source-paper Figure 4 normalization once G2 is source-locked.
