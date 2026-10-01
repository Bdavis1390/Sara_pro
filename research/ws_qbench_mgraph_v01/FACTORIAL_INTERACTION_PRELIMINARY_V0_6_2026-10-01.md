# WS-QBENCH-MGRAPH v0.6 preliminary factorial interaction results — 2026-10-01

## Status

`SIMULATED ONLY` / independent numerical diagnostic. This note does **not** resolve source-lock gaps G1-G4 and does not claim exact reproduction of Figure 4e/f or Supplementary Figure S1.

The interaction contrast is

`I = [IPR_source(r1)-IPR_null(r1)] - [IPR_source(r0)-IPR_null(r0)]`,

with `r0 = |h_perp|/(hbar omega0) = 0.5`. Positive `I` means the source topology's IPR advantage relative to a given null becomes more positive at the target ratio. For stochastic nulls, the same null topology is evaluated at both scale ratios before the difference-in-differences contrast is formed.

Design: `eta={0.5,1,2}`, `Nmax={40,60,80}`, first 30 eigenstates, `omega0=1`, `h_parallel=h0=0`, 30 repetitions for stochastic nulls. Seeds follow `10000 + Nmax + int(eta*100) + int(target*10)`.

## Target ratio 2.0

Values are `interaction_mean (std; positive_fraction)`.

| eta | Nmax | phase stripped | Delta-sign permuted | randomized phase |
|---:|---:|---:|---:|---:|
|0.5|40|-0.008951 (0; 0.00)|+0.003804 (0.009006; 0.63)|+0.023753 (0.006165; 1.00)|
|0.5|60|-0.008930 (0; 0.00)|+0.002702 (0.009057; 0.60)|+0.025374 (0.005871; 1.00)|
|0.5|80|-0.008930 (0; 0.00)|+0.003324 (0.010160; 0.70)|+0.024959 (0.008339; 1.00)|
|1.0|40|-0.034800 (0; 0.00)|-0.015203 (0.008027; 0.03)|-0.007420 (0.007542; 0.27)|
|1.0|60|-0.033819 (0; 0.00)|-0.014831 (0.008617; 0.03)|-0.006913 (0.006897; 0.17)|
|1.0|80|-0.033778 (0; 0.00)|-0.018037 (0.008089; 0.00)|-0.006830 (0.008998; 0.17)|
|2.0|40|-0.007000 (0; 0.00)|-0.003348 (0.005392; 0.23)|-0.017227 (0.011290; 0.00)|
|2.0|60|-0.004615 (0; 0.00)|-0.008115 (0.004932; 0.07)|-0.019535 (0.013091; 0.03)|
|2.0|80|-0.003861 (0; 0.00)|-0.006323 (0.005711; 0.17)|-0.019709 (0.012846; 0.03)|

At target ratio 2, the interaction is not uniformly positive. The `eta=0.5` randomized-phase control is consistently positive, but `eta=1` and `eta=2` are predominantly negative. The Delta-sign control at `eta=0.5` remains close to zero relative to its ensemble width. This rejects a simple monotonic claim that increasing hopping scale always increases the localization contribution of source phase topology.

## Target ratio 5.0

| eta | Nmax | phase stripped | Delta-sign permuted | randomized phase |
|---:|---:|---:|---:|---:|
|0.5|40|+0.011022 (0; 1.00)|+0.047099 (0.005301; 1.00)|+0.067681 (0.002804; 1.00)|
|0.5|60|+0.010124 (0; 1.00)|+0.048071 (0.003939; 1.00)|+0.067433 (0.002562; 1.00)|
|0.5|80|+0.010102 (0; 1.00)|+0.049502 (0.005425; 1.00)|+0.067675 (0.002768; 1.00)|
|1.0|40|-0.020529 (0; 0.00)|+0.026145 (0.005990; 1.00)|+0.041435 (0.003284; 1.00)|
|1.0|60|-0.017685 (0; 0.00)|+0.025230 (0.007296; 1.00)|+0.042240 (0.002820; 1.00)|
|1.0|80|-0.019640 (0; 0.00)|+0.026743 (0.006049; 1.00)|+0.042409 (0.002578; 1.00)|
|2.0|40|-0.072009 (0; 0.00)|+0.006707 (0.012310; 0.70)|+0.014160 (0.009358; 0.97)|
|2.0|60|-0.052380 (0; 0.00)|+0.018532 (0.010403; 0.97)|+0.023049 (0.009426; 1.00)|
|2.0|80|-0.045747 (0; 0.00)|+0.021263 (0.011255; 0.97)|+0.027362 (0.008200; 1.00)|

At target ratio 5, the structured Delta-sign and randomized-phase controls show positive interaction means for all three eta values. The `eta=0.5` and `eta=1` results are comparatively stable across `Nmax=40..80`; `eta=2` remains cutoff-sensitive and is not converged. The phase-stripped control disagrees in sign at `eta=1` and `eta=2`, demonstrating that the conclusion depends materially on the null family.

## Current interpretation

The numerical surface is more consistent with a **crossover / interaction regime** than with a universal monotonic law. In particular:

1. the scale-free `lambda1` result and the scale-bearing IPR result remain logically distinct;
2. topology-scale interaction changes sign across coupling and scale ratios;
3. agreement between Delta-sign and randomized-phase controls at target ratio 5 is evidence worth following, but disagreement with the magnitude-only phase-stripped control prevents a universal claim;
4. `eta=2` requires a higher-cutoff convergence study before interpretation;
5. the authors' exact Figure 4 normalization remains required before source-paper comparison.

## Falsification gate

Do not promote a topology-scale localization claim unless the sign and magnitude of the interaction survive: higher Fock cutoffs, larger paired null ensembles, multiple reference ratios, exact source normalization once obtained, and independent reruns. Retain any null-family disagreement as negative evidence rather than averaging it away.
