# WS-QBENCH-MGRAPH v0.3

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
| `lambda1`, cutoff, conductance and null sweeps | `SIMULATED ONLY` |
| Thresholded loop-connectivity convention | `HYPOTHESIS` / diagnostic proxy |
| Complete-bipartite conductance null | `HYPOTHESIS` / adversarial control |
| Delta-sign phase-topology null | `HYPOTHESIS` / adversarial control |
| Detailed sign-topology increment for tested model/settings | `PROVEN INTERNALLY — NUMERICAL CONTROL ONLY` |
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
- a complete-unweighted-bipartite null, `C_q(null) = 1 - q/(Nmax+1)`.

The conductance null showed that the reproduced near-linear `C_q(q)` trend is almost entirely explained by sampling geometry. Worldshepherd therefore does not treat raw `C_q` as an independent feature without null correction.

## v0.3 addition: phase-topology falsification

`phase_null_v03.py` asks whether the source `lambda1` can be explained by edge magnitudes and coarse hopping-order phase classes alone. Its deliberately nonphysical Delta-sign permutation null preserves, for every hopping order `Delta`:

- every edge magnitude at its original matrix location;
- the parity phase base `i**Delta`;
- hopping-block symmetry;
- the exact multiset of positive/negative Laguerre signs within that Delta band;

while randomizing only where those signs occur within the band.

An independent `Nmax=150`, 50-permutation cross-check found the source-topology `lambda1` above all 50 nulls for every tested `eta` from `0.1` through `2.0`. Descriptive source-minus-null standardized distances rose from about `0.88` at `eta=0.1` to about `12.21` at `eta=2`. These are permutation-ensemble distances, **not calibrated p-values**.

Within the tested finite numerical model, this supports the narrower conclusion that detailed sign/phase topology affects `lambda1` beyond edge magnitudes, coarse hopping-order phase parity, symmetry, and per-band sign counts. It does not establish experimental or hardware causality.

## Run

From the repository root:

```bash
python -m unittest research.ws_qbench_mgraph_v01.tests.test_magnetic_graph
python -m unittest research.ws_qbench_mgraph_v01.tests.test_validation_v02
python -m unittest research.ws_qbench_mgraph_v01.tests.test_phase_null_v03
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

The v0.2 suite adds checks for weighted conductance, node validation, the complete-bipartite null, probability closure, cutoff-reference handling, and weak-coupling diagnostics.

The v0.3 suite checks phase-null magnitude preservation, hopping symmetry, per-band sign-count preservation, seed determinism, and rejection of phase-incompatible inputs.

Evidence notes:

- `VALIDATION_V0_2_2026-10-01.md`
- `PHASE_NULL_V0_3_2026-10-01.md`
- `evidence/independent_crosscheck_v02_2026-10-01.json`
- `evidence/independent_phase_null_v03_2026-10-01.json`

Key findings:

- low Fock cutoffs become materially wrong in the deep-strong-coupling direction; the independent `eta=2` calculation has `Nmax=150` and `200` agreeing to about `4e-9`;
- the weak-coupling `lambda1 ~ 2 eta` asymptote is recovered as `eta -> 0`;
- Figure-4c-like raw conductance is closely reproduced but nearly coincides with the complete-bipartite null;
- conditional nontrivial loop phase stays near one half once enough loops form, while absolute `pConnect` is strongly sensitive to the unresolved numerical edge-zero convention;
- the detailed source sign topology produces a larger `lambda1` than Delta-sign-permuted controls that preserve magnitudes and coarse phase structure across the tested coupling range.

## Known limitations

- Finite Fock truncation makes the displacement block non-unitary near the cutoff; this is a numerical truncation effect.
- The paper's Supplementary Note S1 does not expose enough detail in the available text to lock the effective numerical zero/connection convention.
- Current loop-formation probabilities therefore remain threshold-sensitive and are not claimed as an exact Supplementary Figure S1 reproduction.
- The Delta-sign permutation is intentionally nonphysical; it is useful as a falsification control, not as an alternative physical model.
- Independent cross-checks are not repository CI; full CI/review must pass before merge.
- No hardware, gate-speed, error-correction, sensing, or commercial-performance claim follows from these simulations.

## Next falsification gate

Compare localization/regime observables under four controlled graph variants: source topology, Delta-sign-permuted topology, phase-stripped positive weights, and magnitude-preserving randomized phases. Cross-check those changes against IPR/localization and existing WS-QBENCH/QFLOQUET observables. Retain a graph observable only if it adds reproducible information beyond baseline and null controls. Preserve negative results.
