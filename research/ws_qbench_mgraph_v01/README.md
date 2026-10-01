# WS-QBENCH-MGRAPH v0.4

Bounded Worldshepherd research implementation of the **Floquet-Rabi magnetic-graph** construction introduced by Sunkyu Yu, Xianji Piao, and Namkyoo Park in *Magnetic graphs for cavity quantum electrodynamics*, **Science Advances 12**, eaee5566 (2026), DOI `10.1126/sciadv.aee5566`, arXiv `2607.04736`.

## Why this exists

The source work maps the generalized gauge-invariant quantum Rabi model onto a semi-infinite weighted bipartite magnetic graph under Floquet boundary conditions. A normalized magnetic-Laplacian eigenvalue, `lambda1`, is used as a graph-connectivity metric across weak, ultrastrong, and deep-strong coupling. The paper further separates ordinary conductance from magnetic-flux/phase frustration and links frustration to localization.

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
| Detailed sign-topology increment in `lambda1` for tested settings | `PROVEN INTERNALLY — NUMERICAL CONTROL ONLY` |
| Parameterized Hamiltonian/IPR ablation | `IMPLEMENTED IN SOFTWARE` + `SIMULATED ONLY` |
| Exact Figure 4e/f or Supplementary Figure S1 reproduction | `NOT CURRENTLY CLAIMED` |
| Hardware implication | `REQUIRES PARTNER VALIDATION` |

The source paper is prior art. Worldshepherd's contribution here is the bounded reproducibility harness, provenance/claim controls, deterministic tests, independent numerical cross-checks, adversarial nulls, and negative-evidence retention.

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

## v0.2: conductance and loop controls

`validation_v02.py` adds weighted random-subgraph conductance `C_q`, loop probabilities and phase diagnostics, Fock-cutoff convergence, weak-coupling checks, edge-threshold sensitivity, and the complete-unweighted-bipartite null

`C_q(null) = 1 - q/(Nmax+1)`.

The adversarial result is important: the reproduced near-linear `C_q(q)` trend lies extremely close to this simple sampling-geometry null. Raw `C_q` is therefore not treated as independent Worldshepherd evidence without null correction.

## v0.3: phase-topology falsification

`phase_null_v03.py` tests whether `lambda1` is explained by edge magnitudes and coarse hopping-order phase classes alone. Its deliberately nonphysical Delta-sign permutation null preserves, for every hopping order `Delta`, every edge magnitude in place, the parity phase base `i**Delta`, hopping-block symmetry, and the exact positive/negative sign multiset, while randomizing sign placement within the band.

An independent `Nmax=150`, 50-permutation cross-check found source-topology `lambda1` above all 50 nulls for every tested `eta` from `0.1` through `2.0`. Descriptive standardized separations rose from about `0.88` at `eta=0.1` to about `12.21` at `eta=2`; these are **not calibrated p-values**.

Within the tested finite model, this supports the narrow conclusion that detailed sign/phase topology affects `lambda1` beyond magnitudes and coarse phase parity. It does not establish experimental causality.

## v0.4: physical-Hamiltonian localization ablation

`localization_ablation_v04.py` implements the finite Eq. (3)/End Matter E1 Hamiltonian with all scale ratios explicit:

```text
H = [ B + h_parallel I    h_perp K        ]
    [ h_perp K†           B - h_parallel I ]
B_nn = n omega0 + h0
```

It evaluates IPR for the lowest-energy states under four controlled variants:

1. source topology;
2. phase-stripped positive weights;
3. Delta-sign-permuted topology;
4. magnitude-preserving randomized phases.

Because the accessible source text does not lock the exact Figure 4e/f value of `|h_perp|/(hbar omega0)`, v0.4 sweeps that ratio rather than silently assuming one.

The independent `Nmax=80` sensitivity sweep found that the source-minus-Delta-null IPR difference changes sign and magnitude across the tested `h_perp/omega0` range. At `h_perp/omega0=5`, the source topology is more localized than the Delta-sign ensemble for `eta={0.5,1,2}`; at several smaller ratios it is indistinguishable from or less localized than that null. This negative evidence narrows the v0.3 result: `lambda1` phase-topology separation does **not** by itself prove a normalization-independent IPR advantage.

## Run

From the repository root:

```bash
python -m unittest research.ws_qbench_mgraph_v01.tests.test_magnetic_graph
python -m unittest research.ws_qbench_mgraph_v01.tests.test_validation_v02
python -m unittest research.ws_qbench_mgraph_v01.tests.test_phase_null_v03
python -m unittest research.ws_qbench_mgraph_v01.tests.test_localization_ablation_v04
python -m research.ws_qbench_mgraph_v01.benchmark --nmax 48
```

For a higher-cutoff connectivity comparison closer to source settings:

```bash
python -m research.ws_qbench_mgraph_v01.benchmark \
  --nmax 200 \
  --loop-samples 20000 \
  --output mgraph_n200.json
```

`Nmax=200` and `20,000` random subgraphs are explicitly reported by the source for selected analyses, but matching those counts alone does **not** constitute exact reproduction.

## Evidence and source-lock documents

- `VALIDATION_V0_2_2026-10-01.md`
- `PHASE_NULL_V0_3_2026-10-01.md`
- `LOCALIZATION_ABLATION_V0_4_2026-10-01.md`
- `SOURCE_GAPS_V0_4_2026-10-01.md`
- `evidence/independent_crosscheck_v02_2026-10-01.json`
- `evidence/independent_phase_null_v03_2026-10-01.json`
- `evidence/independent_localization_ablation_v04_2026-10-01.json`

## Known limitations

- Finite Fock truncation makes the displacement block non-unitary near the cutoff; this is numerical truncation.
- The accessible Supplementary Note S1 text does not lock the effective numerical zero/connection convention, so absolute loop-formation probabilities remain threshold-sensitive.
- The exact Figure 4e/f Hamiltonian normalization is not yet source-locked, so v0.4 is a sensitivity study rather than a figure reproduction.
- Delta-sign and fully randomized-phase controls are intentionally nonphysical falsification nulls.
- Independent cross-checks are not repository CI; full CI/review must pass before merge.
- No hardware, gate-speed, error-correction, sensing, or commercial-performance claim follows from these simulations.

## Next gate

Obtain the authors' source conventions/code for the loop connection rule and Figure 4e/f normalization, then run an `Nmax=200` locked-parameter reproduction of the first 30 IPR/eigenenergy curves. Repeat the locked physical setting under the three phase controls. Retain negative evidence and only promote observables that add reproducible information beyond baseline and nulls.
