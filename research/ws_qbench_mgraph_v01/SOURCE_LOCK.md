# Source lock — WS-QBENCH-MGRAPH v0.1

## Primary source

Sunkyu Yu, Xianji Piao, Namkyoo Park,
"Magnetic graphs for cavity quantum electrodynamics,"
*Science Advances* 12, eaee5566 (2026).
DOI: `10.1126/sciadv.aee5566`
arXiv: `2607.04736`

## Source facts used by v0.1

- generalized QRM mapped to a complex bipartite graph;
- Fock-basis hopping `l_nm^(±)=<n|D(±2 i eta)|m>`;
- local gauge transformation yields a Floquet-Rabi graph;
- normalized magnetic Laplacian uses the elementwise absolute-value degree;
- the smallest Laplacian eigenvalue is used as the graph-connectivity metric;
- the paper reports `Nmax=200` for graph visualizations;
- the paper reports `2 x 10^4` random subgraphs for selected conductance/loop
  statistics;
- the reported interpretation is that coupling-dependent connectivity changes
  are driven by phase frustration rather than a changing bottleneck fraction.

## Reproduction boundary

The exact supplementary random-loop sampling and all source figure parameters
must be independently checked before Worldshepherd labels Figure 3/4 as
reproduced. Until then, the loop sampler in this package is explicitly a
diagnostic proxy.

## Falsification gates

The ingest should be rejected or revised if any of the following occur:

1. the source equations cannot be reproduced at high cutoff;
2. `lambda1(eta)` is not stable to cutoff escalation;
3. graph results disappear under numerically equivalent gauge choices;
4. claimed phase-frustration behavior is dominated by threshold choice;
5. graph observables add no predictive/explanatory information beyond existing
   QBENCH observables under held-out comparisons.

Negative results are retained as evidence.
