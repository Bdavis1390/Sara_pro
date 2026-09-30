# WS-QBENCH-MGRAPH v0.1

Bounded Worldshepherd research implementation of the **Floquet-Rabi magnetic-graph**
construction introduced by Sunkyu Yu, Xianji Piao, and Namkyoo Park in:

- *Magnetic graphs for cavity quantum electrodynamics*, **Science Advances 12**,
  eaee5566 (2026), DOI: `10.1126/sciadv.aee5566`
- arXiv: `2607.04736`

## Why this exists

The source work maps the generalized gauge-invariant quantum Rabi model onto a
semi-infinite weighted bipartite magnetic graph under Floquet boundary
conditions. A normalized magnetic-Laplacian eigenvalue, `lambda1`, is used as
a continuous graph-connectivity metric across weak, ultrastrong, and
deep-strong coupling. The paper further separates ordinary conductance from
magnetic-flux/phase frustration and reports phase frustration as the main
driver of the coupling-induced connectivity transition.

Worldshepherd is ingesting that result as a **diagnostic and falsification
layer** for WS-QBENCH / WS-QFLOQUET. This package does not claim new physics.

## Claim state

| Item | State |
|---|---|
| Source magnetic-graph/QRM result | `SUPPORTED BY LITERATURE` |
| Analytic Fock displacement matrix | `IMPLEMENTED IN SOFTWARE` |
| Finite normalized magnetic Laplacian | `IMPLEMENTED IN SOFTWARE` |
| `lambda1` sweep | `SIMULATED ONLY` |
| Thresholded random-loop proxy | `HYPOTHESIS` / diagnostic proxy |
| Exact reproduction of published figures | **NOT YET CLAIMED** |
| Hardware implication | `REQUIRES PARTNER VALIDATION` |

The source paper is prior art. Worldshepherd's contribution here is the
bounded reproducibility harness, provenance/claim controls, deterministic
tests, and planned cross-comparison with existing QBENCH/Floquet observables.

## Implemented equations

For `0 <= n,m <= Nmax`, the hopping block uses

`l_nm^(±) = <n|D(±2 i eta)|m>`

with the associated-Laguerre closed form. The finite FR adjacency is

```text
A = [ 0   K  ]
    [ K†  0  ]
```

and the normalized magnetic Laplacian is

```text
L = I - D^(-1/2) A D^(-1/2)
D_ii = sum_j |A_ij|.
```

The v0.1 primary observable is the smallest eigenvalue of `L`.

## Run

From the repository root:

```bash
python -m unittest research.ws_qbench_mgraph_v01.tests.test_magnetic_graph
python -m research.ws_qbench_mgraph_v01.benchmark --nmax 48
```

For a higher-cutoff comparison closer to the paper's figure settings:

```bash
python -m research.ws_qbench_mgraph_v01.benchmark \
  --nmax 200 \
  --loop-samples 20000 \
  --output mgraph_n200.json
```

`Nmax=200` and `20,000` loop samples reflect values explicitly reported in the
paper for selected figures, but matching those numbers alone does **not**
constitute exact reproduction.

## v0.1 validation gates

1. `D(+2 i eta) = D(-2 i eta)†` within numerical tolerance.
2. `eta -> 0` approaches identity hopping.
3. finite FR adjacency and normalized magnetic Laplacian are Hermitian.
4. magnetic-Laplacian spectrum is invariant under arbitrary local U(1) gauge
   rephasing.
5. finite-cutoff spectrum remains in the normalized-Laplacian interval
   `[0, 2]` within floating-point tolerance.
6. a bounded sample reproduces the source paper's **qualitative** rise of
   `lambda1` from weak toward ultrastrong coupling.

## Known limitations

- Finite Fock truncation makes the displacement block non-unitary near the
  cutoff. This is a numerical truncation effect.
- v0.1 does not yet recreate the paper's exact Figure 3/4 parameterization.
- The random-loop routine is a Worldshepherd **proxy**, not yet a claim of an
  exact implementation of the paper's Supplementary Note S1 sampling method.
- No hardware, gate-speed, error-correction, sensing, or commercial
  performance claim follows from this simulation.

## Next gate

v0.2 should lock the complete source parameter set, recreate the published
`lambda1(eta)` curve at `Nmax=200`, reproduce loop statistics with the exact
supplementary sampling convention, and then compare those graph observables
against WS-QBENCH state-localization/Floquet diagnostics using predeclared
correlation and ablation tests.
