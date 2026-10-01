# WS-QBENCH-MGRAPH v0.6 interaction crossover scan — 2026-10-01

## Status

`SIMULATED ONLY` / independent numerical diagnostic. This scan does **not** resolve source-lock gaps G1-G4 and does not claim a physical critical point or exact reproduction of Figure 4e/f.

The paired interaction contrast is

`I(r) = [IPR_source(r)-IPR_null(r)] - [IPR_source(0.5)-IPR_null(0.5)]`.

For stochastic nulls the same null topology is evaluated at the reference and target ratios. A reported crossover is only a local linear interpolation between adjacent sampled ratios whose ensemble-mean interaction changes sign.

## Design

- reference ratio: `|h_perp|/(hbar omega0) = 0.5`;
- `eta = {0.5, 1.0, 2.0}`;
- `Nmax = {60, 80, 100}`;
- first 30 eigenstates;
- `omega0=1`, `h_parallel=h0=0`;
- 40 paired null realizations per stochastic null family;
- nulls: Delta-sign permutation and magnitude-preserving randomized phase;
- local sign-change brackets chosen from the preliminary v0.6 interaction surface.

## Estimated zero crossings

| eta | Nmax | Delta-sign crossover | randomized-phase crossover |
|---:|---:|---:|---:|
|0.5|60|1.9535|1.7221|
|0.5|80|1.9376|1.6930|
|0.5|100|1.9406|1.7193|
|1.0|60|2.9185|2.2371|
|1.0|80|2.8894|2.2195|
|1.0|100|2.8426|2.2524|
|2.0|60|3.4667|3.9392|
|2.0|80|3.4943|3.6699|
|2.0|100|3.5234|3.6351|

Cutoff summaries are descriptive, not statistical confidence intervals:

| eta | null family | mean crossover | min | max | cutoff spread |
|---:|---|---:|---:|---:|---:|
|0.5|Delta-sign|1.9439|1.9376|1.9535|0.0159|
|0.5|randomized phase|1.7115|1.6930|1.7221|0.0291|
|1.0|Delta-sign|2.8835|2.8426|2.9185|0.0759|
|1.0|randomized phase|2.2364|2.2195|2.2524|0.0329|
|2.0|Delta-sign|3.4948|3.4667|3.5234|0.0567|
|2.0|randomized phase|3.7481|3.6351|3.9392|0.3041|

## Interpretation

The scan strengthens the **crossover-regime** interpretation but rejects the stronger idea of one null-independent critical ratio.

1. `eta=0.5` shows good cutoff stability within each null family, yet the two phase-sensitive nulls place the crossover at materially different ratios (~1.71 vs ~1.94).
2. `eta=1.0` also shows internally stable but substantially separated crossover estimates (~2.24 vs ~2.88).
3. `eta=2.0` puts the two phase-sensitive crossovers closer together in the high-scale regime, but the randomized-phase estimate remains noticeably cutoff-sensitive; it is not converged enough to promote.
4. The magnitude-only phase-stripped control does not define the same boundary and remains negative through large portions of the tested high-scale regime, so a universal 'phase topology increases localization above one critical ratio' statement is not supported.
5. The increasing location of the Delta-sign crossover with eta is a useful empirical pattern, but three eta values are insufficient to claim a scaling law.

## Falsification / next gate

Do not label these interpolated zeros as phase transitions or physical critical points. Before promotion, require:

- denser target-ratio sampling around each sign change;
- larger paired ensembles with uncertainty on the ensemble mean;
- `Nmax > 100`, especially for `eta=2` randomized phase;
- multiple predeclared reference ratios instead of only `0.5`;
- source-locked Figure 4 normalization once G2 is resolved;
- an independent rerun using a numerically separate implementation.

The practical result is narrower: the topology contribution to IPR changes with the Hamiltonian scale ratio, but the location of that sign change is control-family dependent and therefore cannot yet be treated as a unique physical boundary.
