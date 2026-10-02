# WS-QBENCH-MGRAPH v0.8 — author-aligned Figure 4e/f candidate cross-check

## Status

`SIMULATED ONLY`. The corresponding-author normalization is now locked, but the Worldshepherd mapping of the author's transverse/normal Hamiltonian coefficient to `h_perp` remains gated on direct Code S1 inspection. This is therefore a **candidate source-aligned cross-check**, not an exact Figure 4e/f reproduction claim.

The public manuscript states that Figure 4e/f plots the first 30 eigenstates and uses IPR to quantify localization. The authors describe increasing phase frustration as producing localization and spectral degeneracies.

## Locked candidate setup

- `Nmax = 200`
- `hbar = omega0 = 1`
- `h0 = 0`
- `h_parallel = 0`
- mapped `h_perp = 0.5`
- first 30 eigenstates
- independent cross-check: SciPy associated-Laguerre construction + NumPy Hermitian eigensolver

The independent displacement matrix agrees with the repository recurrence to `<= 3.5e-15` at `Nmax=20` for `eta={0.1,0.5,1,2}`.

## Aggregate first-30-state IPR

| eta | mean IPR | median IPR | min IPR | max IPR |
|---:|---:|---:|---:|---:|
|0.10|0.288347|0.282577|0.254104|0.497537|
|0.25|0.396943|0.412338|0.273380|0.485774|
|0.50|0.445268|0.451266|0.347023|0.480560|
|0.75|0.460734|0.464878|0.421635|0.486967|
|1.00|0.469543|0.473740|0.430674|0.489858|
|1.25|0.475704|0.478791|0.443482|0.491339|
|1.50|0.480376|0.482838|0.457896|0.495351|
|2.00|0.486284|0.487513|0.468233|0.498766|
|2.50|0.490169|0.489799|0.473830|0.499538|
|3.00|0.493172|0.495681|0.478250|0.499788|

From `eta=0.1` upward, the aggregate IPR rises toward roughly one-half. That is qualitatively consistent with the manuscript's reported localization trend, but visual/qualitative agreement is not an exact-figure validation.

## Spectral compression diagnostic

For the same first 30 states, the minimum adjacent gap changes from approximately `1.997e-1` at `eta=0.1` to `3.53e-4` at `eta=2` and `1.57e-8` at `eta=3`. At `eta=3`, five adjacent gaps are below `1e-3`.

These thresholds are descriptive diagnostics only; they are not promoted as a degeneracy criterion.

## Cutoff control

The mean-IPR result is effectively unchanged from `Nmax=80` through `200` for `eta<=2`. At `eta=3`, the mean-IPR spread across that range is about `6.96e-6`, while the upper energy of the first-30-state window shifts by about `7.41e-4`. Thus the localization summary is well behaved, but the high-coupling energy window retains visible finite-cutoff sensitivity.

## Gate

Do not promote this to exact Figure 4e/f reproduction until:

1. Code S1 is acquired and cryptographically hashed;
2. the `h_perp` notation mapping is confirmed line-by-line;
3. the exact eta grid and plotting conventions are extracted from the MATLAB source;
4. state-resolved energies/IPRs are compared numerically, not only visually.
