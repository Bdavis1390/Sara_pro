# WS-QBENCH-MGRAPH v0.5 next gate

Do not add another physical claim before the source-lock blockers in `SOURCE_GAPS_V0_4_2026-10-01.md` are addressed.

## Gate A — author/source-code lock

Obtain the code or explicit conventions for:

- effective zero / maximum hopping-order rule used for loop formation;
- random-subgraph duplicate policy;
- Figure 4e/f values of `h0`, `|h_parallel|`, `|h_perp|`, and `hbar omega0`.

## Gate B — exact-parameter Nmax=200 reproduction

With those parameters frozen in a machine-readable manifest:

1. rerun `lambda1(eta)`;
2. reproduce Figure 4c conductance with null-corrected residuals;
3. reproduce Figure 4d/S1 loop statistics under the source connection convention;
4. reproduce the first 30 IPR and eigenenergy curves;
5. repeat IPR under source, phase-stripped, Delta-sign, and randomized-phase controls;
6. quantify cutoff and Monte-Carlo uncertainty.

## Gate C — incremental-information decision

Promote an observable into WS-QBENCH/QFLOQUET only if it survives:

- source-parameter lock;
- cutoff convergence;
- null correction;
- phase-control ablation;
- held-out or independent rerun;
- negative-evidence retention.

Expected outcomes are allowed to be negative. A feature that fails the incremental-information gate should be removed rather than rationalized.
