# WS-QBENCH-MGRAPH v0.4 external review checklist

Before moving PR #523 out of draft, a reviewer should be able to answer **yes** to each applicable item.

## Reproduction core

- [ ] Displacement-matrix convention matches the cited source equation.
- [ ] Adjoint/Hermiticity and local-gauge invariance tests pass.
- [ ] `lambda1` is stable at the declared cutoff for every quantitative claim.
- [ ] Weak-coupling asymptote is checked independently.

## Conductance / loop evidence

- [ ] Raw `C_q` is reported beside the complete-bipartite null.
- [ ] No quasi-one-dimensional interpretation is adopted solely from the raw q trend.
- [ ] Edge-zero/connection threshold is explicit wherever `pConnect` is reported.
- [ ] Threshold sensitivity is shown rather than hidden.
- [ ] `pNontrivial + pTrivial = pConnect` holds for reported ensembles.

## Phase-topology controls

- [ ] Delta-sign null preserves magnitudes, phase-parity class, symmetry and sign counts as documented.
- [ ] Standardized permutation distances are not described as calibrated p-values.
- [ ] Nonphysical nulls are clearly labeled as falsification controls.

## Physical-Hamiltonian / localization evidence

- [ ] `omega0`, `h_perp`, `h_parallel`, `h0`, cutoff and eigenstate count are explicit.
- [ ] Figure 4e/f is not called reproduced before source normalization is locked.
- [ ] The v0.4 negative result—IPR increment depends on `h_perp/omega0`—is retained.
- [ ] Graph-level `lambda1` separation is not silently promoted into a universal localization claim.

## Claims control

- [ ] `CLAIMS_MATRIX_V0_4_2026-10-01.md` is respected.
- [ ] Hardware/QEC/sensing/gate-speed performance is not inferred from simulation.
- [ ] Independent cross-check evidence is distinguished from repository CI.
- [ ] Source prior art is distinguished from Worldshepherd controls and implementation.

## Merge boundary

- [ ] Required Test and Build succeeds on the exact head.
- [ ] CodeQL succeeds on the exact head.
- [ ] NIST precursor, commit-closure evidence and resilience workflows succeed on the exact head.
- [ ] Any review comments are resolved.
- [ ] Human approval is explicit before merge.
