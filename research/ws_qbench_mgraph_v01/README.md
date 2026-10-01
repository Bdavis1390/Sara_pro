# WS-QBENCH-MGRAPH v0.2

Bounded Worldshepherd research implementation of the **Floquet-Rabi magnetic-graph** construction introduced by Sunkyu Yu, Xianji Piao, and Namkyoo Park in *Magnetic graphs for cavity quantum electrodynamics*, **Science Advances 12**, eaee5566 (2026), DOI `10.1126/sciadv.aee5566`, arXiv `2607.04736`.

## Why this exists

The source work maps the generalized gauge-invariant quantum Rabi model onto a semi-infinite weighted bipartite magnetic graph under Floquet boundary conditions. A normalized magnetic-Laplacian eigenvalue, `lambda1`, is used as a graph-connectivity metric across weak, ultrastrong, and deep-strong coupling. The paper further separates ordinary conductance from magnetic-flux/phase frustration and reports phase frustration as the main driver of the coupling-induced connectivity transition.

Worldshepherd ingests the result as a **diagnostic and falsification layer** for WS-QBENCH / WS-QFLOQUET. This package does not claim new physics.

## Claim state

| Item | State |
|---|---|
| Source magnetic-graph/QRM result | `SUPPORTED BY LITERATURE` |
| Analytic Fock displacement matrix | `IMPLEMENTED IN SOFTWARE` |
| Finite normalized magnetic Laplacian | `IMPLEMENTED IN SOFTWARE` |
| `lambda1`, cutoff and conductance sweeps | `SIMULATED ONLY` |
| Thresholded loop-connectivity convention | `HYPOTHESIS` / diagnostic proxy |
| Complete-bipartite conductance null | `HYPOTHESIS` / adversarial control |
| Exact Figure 4/S1 reproduction | `NOT CURRENTLY CLAIMED` |
| Hardware implication | `REQUIRES PARTNER VALIDATION` |

The source paper is prior art. Worldshepherd's contribution here is the bounded reproducibility harness, provenance/claim controls, deterministic tests, independent numerical cross-checks, adversarial nulls, and planned cross-comparison with existing QBENCH/Floquet observables.

## Core equations

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

The primary connectivity observable is the smallest eigenvalue `lambda1`. The source derives `0 <= lambda1 <= 1`; the generic normalized-Laplacian spectrum remains within `[0,2]`.

## v0.2 additions

`validation_v02.py` adds:

- weighted random-subgraph conductance `C_q`;
- `pConnect`, `pNontrivial`, `pTrivial`, and the nontrivial fraction conditional on loop formation;
- phase-quantization residual tracking;
- Fock-cutoff convergence;
- weak-coupling comparison against `lambda1 ~ 2 eta`;
- explicit edge-threshold sensitivity;
- a complete-unweighted-bipartite null, `C_q(null) = 1 - q/(Nmax+1)`, so raw conductance is not mistaken for independent information when it is explained by sampling geometry.

The null is a Worldshepherd adversarial control, not a claim from the source paper.

## Run

From the repository root:

```bash
python -m unittest research.ws_qbench_mgraph_v01.tests.test_magnetic_graph
python -m unittest research.ws_qbench_mgraph_v01.tests.test_validation_v02
python -m research.ws_qbench_mgraph_v01.benchmark --nmax 48
```

For a higher-cutoff comparison closer to the source settings:

```bash
python -m research.ws_qbench_mgraph_v01.benchmark \
  --nmax 200 \
  --loop-samples 20000 \
  --output mgraph_n200.json
```

`Nmax=200` and `20,000` random subgraphs are values explicitly reported by the paper for selected analyses, but matching those counts alone does **not** constitute exact reproduction.

## Validation status

The v0.1 suite covers the displacement adjoint relation, weak-coupling identity limit, Hermiticity, local-U(1) spectral invariance, normalized-Laplacian bounds, qualitative `lambda1` growth, and deterministic loop output.

The v0.2 suite adds deterministic checks for weighted conductance, node validation, the complete-bipartite null, probability closure, cutoff-reference handling, and weak-coupling diagnostics.

`VALIDATION_V0_2_2026-10-01.md` records an independent NumPy/SciPy cross-check. Important findings include:

- `Nmax=32` is adequate in weak coupling but is materially wrong by `eta=2`; `Nmax=150` and `200` agree to about `4e-9` for the independent `eta=2` calculation;
- the weak-coupling `lambda1 ~ 2 eta` asymptote is recovered as `eta -> 0`;
- the Figure-4c-like conductance values for `q={2,10,30,50}` are reproduced closely;
- those conductance values also lie extremely close to the simple complete-bipartite null, so raw `C_q` must be null-corrected before Worldshepherd treats it as an independent feature;
- conditional phase frustration stays near one half once enough loops form, while the absolute loop-formation probability is strongly sensitive to the unresolved numerical edge-zero threshold.

## Known limitations

- Finite Fock truncation makes the displacement block non-unitary near the cutoff; this is a numerical truncation effect.
- The paper's Supplementary Note S1 does not expose enough detail to lock the effective numerical zero/connection convention from text alone.
- The current loop-formation probabilities therefore remain threshold-sensitive and are not claimed as an exact Supplementary Figure S1 reproduction.
- The independent cross-check is not repository CI; full CI/review must pass before merge.
- No hardware, gate-speed, error-correction, sensing, or commercial-performance claim follows from these simulations.

## Next falsification gate

Compare held-out localization/regime prediction using baseline WS-QBENCH/QFLOQUET observables against additions of `lambda1`, phase/loop observables, raw `C_q`, and null-corrected `C_q - C_q(null)`. Retain a graph observable only if it adds reproducible information beyond the baseline and null controls. Preserve negative results.
