# WS-QBENCH-MGRAPH v0.6 reference-relative interaction-zero scan — 2026-10-01

## Status

`SIMULATED ONLY` / independent numerical diagnostic. This scan does **not** resolve source-lock gaps G1-G4 and does not claim a physical critical point or exact reproduction of Figure 4e/f.

Define the topology effect at scale ratio `r` as

`E(r) = IPR_source(r) - IPR_null(r)`.

The paired interaction contrast used here is

`I(r; r0) = E(r) - E(r0)`

with `r0 = |h_perp|/(hbar omega0) = 0.5`.

**Correction / terminology lock:** a zero of `I(r; r0)` means `E(r) = E(r0)`. It is a **reference-relative return-to-baseline ratio**, not necessarily a zero of the topology effect itself and not an intrinsic physical boundary. The separate `TOPOLOGY_EFFECT_SCAN_V0_6_2026-10-01.md` analyzes `E(r)=0` directly.

For stochastic nulls the same null topology is evaluated at the reference and target ratios. A reported interaction zero is only a local linear interpolation between adjacent sampled ratios whose ensemble-mean `I(r; r0)` changes sign.

## Design

- reference ratio: `|h_perp|/(hbar omega0) = 0.5`;
- `eta = {0.5, 1.0, 2.0}`;
- `Nmax = {60, 80, 100}`;
- first 30 eigenstates;
- `omega0=1`, `h_parallel=h0=0`;
- 40 paired null realizations per stochastic null family;
- nulls: Delta-sign permutation and magnitude-preserving randomized phase.

## Estimated interaction-zero ratios

| eta | Nmax | Delta-sign `I=0` | randomized-phase `I=0` |
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

Cutoff summaries are descriptive, not confidence intervals:

| eta | null family | mean `I=0` ratio | min | max | cutoff spread |
|---:|---|---:|---:|---:|---:|
|0.5|Delta-sign|1.9439|1.9376|1.9535|0.0159|
|0.5|randomized phase|1.7115|1.6930|1.7221|0.0291|
|1.0|Delta-sign|2.8835|2.8426|2.9185|0.0759|
|1.0|randomized phase|2.2364|2.2195|2.2524|0.0329|
|2.0|Delta-sign|3.4948|3.4667|3.5234|0.0567|
|2.0|randomized phase|3.7481|3.6351|3.9392|0.3041|

## Interpretation

The scan demonstrates a reproducible topology × scale interaction, but it does **not** identify one null-independent critical ratio. The interaction-zero location depends on the null family and, mathematically, on the chosen reference ratio `r0`.

This distinction matters: changing `r0` vertically shifts `I(r; r0)` by the constant `-E(r0)` and can move its zero even when the underlying `E(r)` curve is unchanged. Therefore these values are useful paired-ablation diagnostics, not intrinsic phase boundaries.

## Falsification / next gate

Before promoting any scale-boundary claim, require direct analysis of `E(r)=0`, denser sampling, larger paired ensembles, `Nmax > 100`, multiple reference ratios, independent numerical implementation, and the source-locked Figure 4 normalization once G2 is resolved.
