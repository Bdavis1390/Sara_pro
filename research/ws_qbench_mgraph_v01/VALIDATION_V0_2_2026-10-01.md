# WS-QBENCH-MGRAPH v0.2 validation note — 2026-10-01

## Scope

This note extends the v0.1 magnetic-graph ingest with adversarial controls around three source-paper claims:

1. the smallest normalized magnetic-Laplacian eigenvalue `lambda1` is stable under a sufficiently large Fock cutoff;
2. ensemble-averaged random-subgraph conductance `C_q` is nearly independent of coupling strength `eta`;
3. approximately half of *formed* loops carry the nontrivial phase while loop-formation probability grows with coupling.

Primary source: S. Yu, X. Piao, N. Park, **Magnetic graphs for cavity quantum electrodynamics**, *Science Advances* 12, eaee5566 (2026), DOI `10.1126/sciadv.aee5566`, arXiv `2607.04736`.

The source uses `Nmax = 200` for the finite Fock cutoff and reports `2e4` random subgraphs for the Figure 4 conductance/loop ensemble. Supplementary Note S1 defines `pConnect`, `pNontrivial`, and `pTrivial`, but does not specify a numerical threshold for deciding when a very small nonzero hopping amplitude is treated as disconnected. That unresolved convention is kept explicit here rather than hidden.

## Independent numerical cross-check

A separate Python/NumPy/SciPy implementation using `scipy.special.eval_genlaguerre` was run independently of the repository's custom Laguerre recurrence. The resulting evidence is stored in `evidence/independent_crosscheck_v02_2026-10-01.json`.

This is an **independent numerical cross-check**, not a repository-CI artifact and not an experimental validation.

### Cutoff convergence

`lambda1` values from the independent implementation:

| eta | Nmax=32 | 64 | 100 | 150 | 200 |
|---:|---:|---:|---:|---:|---:|
| 0.01 | 0.0196894155 | 0.0196894155 | 0.0196894155 | 0.0196894155 | 0.0196894155 |
| 0.10 | 0.1734319960 | 0.1734319960 | 0.1734319960 | 0.1734319960 | 0.1734319960 |
| 0.50 | 0.5373150285 | 0.5373150285 | 0.5373150285 | 0.5373150285 | 0.5373150285 |
| 1.00 | 0.6974934655 | 0.7045032239 | 0.7045032239 | 0.7045032239 | 0.7045032239 |
| 1.50 | 0.7092060667 | 0.7722033764 | 0.7805778885 | 0.7805778892 | 0.7805778892 |
| 2.00 | 0.7021286948 | 0.7816100301 | 0.8137473643 | 0.8238661736 | 0.8238661779 |

The important result is negative as well as positive: low cutoffs are harmless at weak coupling but become materially wrong in the DSC direction. At `eta=2`, the `Nmax=32` error relative to `Nmax=200` is about `0.12174`, `Nmax=64` is about `0.04226`, and `Nmax=100` is about `0.01012`. `Nmax=150` and `Nmax=200` agree to about `4.3e-9` in this implementation.

Therefore v0.2 must not use a low cutoff to make DSC quantitative claims.

### Weak-coupling asymptote

At `Nmax=200`, the independent implementation gives:

| eta | lambda1 | 2 eta | relative deviation |
|---:|---:|---:|---:|
| 0.001 | 0.0019968352 | 0.002 | 0.158% |
| 0.005 | 0.0099215451 | 0.010 | 0.785% |
| 0.010 | 0.0196894155 | 0.020 | 1.553% |
| 0.020 | 0.0387823877 | 0.040 | 3.044% |

This is consistent with the source-paper weak-coupling relation `lambda1 ~ 2 eta` as `eta -> 0`.

## Conductance reproduction and new null control

At `eta=1`, `Nmax=200`, and 10,000 uniformly sampled subgraphs, the independent implementation gives:

| q | observed mean C_q | complete-bipartite null `1-q/201` | excess |
|---:|---:|---:|---:|
| 2 | 0.9901856 | 0.9900498 | +1.36e-4 |
| 10 | 0.9502897 | 0.9502488 | +4.09e-5 |
| 30 | 0.8507697 | 0.8507463 | +2.34e-5 |
| 50 | 0.7511951 | 0.7512438 | -4.87e-5 |

These values reproduce the qualitative Figure 4c pattern extremely closely: `C_q` is nearly coupling-independent and decreases almost linearly with q.

However, v0.2 adds an adversarial control that the source paper did not use: an unweighted complete bipartite graph with `d=Nmax+1` nodes per partition has exactly

`C_q(null) = 1 - q/d`.

The observed values above sit within roughly `1.4e-4` of that simple combinatorial null. This does **not** invalidate the paper's magnetic-graph construction or its phase-frustration result. It does mean that the near-linear q-dependence of `C_q` alone is not sufficient evidence for a specifically quantum or quasi-one-dimensional mechanism. Any Worldshepherd use of `C_q` must therefore report the excess over this null, not just the raw conductance.

## Loop formation: result and unresolved convention

With `Nmax=200`, `2e4` samples, and the current explicit Worldshepherd threshold `|edge| > 1e-3 max|K|`:

- q=2: `pConnect` rises from `0.00025` at `eta=0.1` to `0.5687` at `eta=3.0`;
- q=10: `pConnect` rises from effectively zero at weak coupling to `0.05465` at `eta=3.0`;
- once enough loops are formed, the nontrivial fraction is consistently near one half.

At `eta=3`, changing the relative edge threshold from `1e-2` to `1e-8` moves q=2 `pConnect` from `0.4893` to `0.7042`, and q=10 from `0.0302` to `0.1802`. The conditional nontrivial fraction remains near `0.5` across the same threshold sweep.

Therefore:

- the **phase split** is comparatively robust;
- the **absolute loop-formation probability** is strongly threshold-dependent;
- Supplementary Figure S1 is **not yet reproduced** because the paper's effective numerical zero/connection convention is not fully specified in the text available to us.

## v0.2 implementation gates

`validation_v02.py` now adds:

- paper-aligned weighted subgraph conductance;
- `pConnect`, `pNontrivial`, `pTrivial`, and conditional nontrivial fraction;
- phase-quantization residual tracking;
- Fock-cutoff convergence analysis;
- weak-coupling asymptote diagnostics;
- edge-threshold sensitivity analysis;
- a complete-bipartite conductance null control and `C_q - C_q(null)` residual.

A separate six-test unit suite checks deterministic mathematics and interface behavior. The test file was syntax/logic checked in an isolated local harness using mocks for the v0.1 physics functions. Full repository CI remains required before merge.

## Claims state

- source magnetic-graph result: `SUPPORTED BY LITERATURE`;
- v0.1/v0.2 implementation: `IMPLEMENTED IN SOFTWARE`;
- repository and independent numerical values: `SIMULATED ONLY`;
- conductance null interpretation: `HYPOTHESIS / ADVERSARIAL CONTROL`;
- exact Figure 4/S1 reproduction: `NOT CURRENTLY CLAIMED`;
- hardware, gate-speed, sensing, QEC, or commercial performance: `REQUIRES PARTNER VALIDATION` and is not inferred here.

## Next falsification gate

Before accepting magnetic-graph observables as useful additions to WS-QBENCH/QFLOQUET, compare held-out predictive performance for localization/regime labels using:

1. baseline state observables only;
2. baseline + `lambda1`;
3. baseline + loop phase/strength observables;
4. baseline + raw `C_q`;
5. baseline + null-corrected `C_q - (1-q/(Nmax+1))`.

If raw `C_q` adds no information after the null correction, it should not be retained as an independent Worldshepherd feature. Negative results are evidence and must be preserved.
