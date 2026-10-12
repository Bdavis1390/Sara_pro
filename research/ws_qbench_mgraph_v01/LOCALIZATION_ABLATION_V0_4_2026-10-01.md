# WS-QBENCH-MGRAPH v0.4 — parameterized localization ablation

## Why this gate was necessary

The source paper links nontrivial loop phases to destructive interference, localization, and spectral degeneracy. It evaluates localization through the inverse participation ratio (IPR) of the first 30 eigenstates of the physical Coulomb-gauge Hamiltonian `H_C`.

The v0.3 phase-topology null found a clear numerical separation in the graph-connectivity metric `lambda1`: the source sign topology produced larger `lambda1` than Delta-sign permutations preserving edge magnitudes and coarse hopping-order phase classes. That is a useful graph-level result, but it does **not** automatically prove an equally strong localization effect in the physical Hamiltonian.

The accessible source text defines the Hamiltonian scale factors but does not expose enough information to lock the exact Figure 4e/f numerical normalization, especially `|h_perp|/(hbar omega0)`. v0.4 therefore turns that unknown into an explicit sensitivity axis rather than guessing it.

## Implemented Hamiltonian

`localization_ablation_v04.py` implements the finite block Hamiltonian corresponding to Eq. (3)/End Matter E1, in units with `hbar=1`:

```text
H = [ B + h_parallel I    h_perp K       ]
    [ h_perp K^dagger    B - h_parallel I ]

B_nn = n omega0 + h0
K_nm = <n|D(+2 i eta)|m>.
```

It computes `IPR = sum_v |psi_v|^4` for the lowest-energy eigenstates and compares four variants:

1. source phase topology;
2. phase-stripped positive weights `|K|`;
3. Delta-sign-permuted topology from v0.3;
4. magnitude-preserving independently randomized phases.

The last three are adversarial controls, not physical alternative models.

## Independent sensitivity sweep

A separate NumPy/SciPy implementation using `scipy.special.eval_genlaguerre` was run independently of the repository recurrence with:

- `Nmax=80`;
- `omega0=1`;
- `h_parallel=0`;
- `h0=0`;
- first 30 eigenstates;
- 20 realizations for each stochastic null;
- `eta={0.5,1.0,2.0}`;
- `h_perp/omega0={0.25,0.5,1,2,5}`.

The full table is in `evidence/independent_localization_ablation_v04_2026-10-01.json`.

### Selected results: source mean IPR minus Delta-sign-null mean IPR

| eta | h_perp/omega0=0.25 | 0.5 | 1 | 2 | 5 |
|---:|---:|---:|---:|---:|---:|
| 0.5 | -0.000134 | -0.000994 | -0.021815 | +0.001457 | +0.045675 |
| 1.0 | -0.000023 | -0.000211 | -0.004251 | -0.013848 | +0.026577 |
| 2.0 | +0.000012 | -0.000026 | +0.000335 | -0.007689 | +0.017947 |

Positive values mean the source topology is more localized by this summary statistic; negative values mean the Delta-sign-permuted control is more localized.

## Negative result that must be preserved

The incremental localization effect of the detailed source phase topology is **not normalization-independent** in this sensitivity sweep. At small-to-moderate `h_perp/omega0`, the source topology is often indistinguishable from, or slightly less localized than, the Delta-sign null. At the largest tested ratio (`5`), the source topology becomes more localized than the Delta-sign ensemble for all three tested `eta` values.

This is important because it narrows the v0.3 interpretation:

- v0.3 supports an incremental role for detailed phase/sign topology in `lambda1` within the tested graph model;
- v0.4 shows that translating that graph-level separation into an IPR-localization separation depends strongly on the Hamiltonian scale ratio;
- therefore `lambda1` separation alone is insufficient to claim a universal localization mechanism independent of physical normalization.

That is a useful falsification result, not a failure of the program.

## Source consistency

The source paper states that stronger phase frustration is associated with localization and plots IPR for the first 30 eigenstates. The present v0.4 sweep does not dispute that source result because we have not yet locked the exact Figure 4e/f Hamiltonian normalization. The appropriate conclusion is narrower: **parameter lock is mandatory before comparing the Worldshepherd IPR curve to the published panel.**

## Claim state

- finite Hamiltonian/IPR code: `IMPLEMENTED IN SOFTWARE`;
- independent scale sweep: `SIMULATED ONLY`;
- normalization sensitivity: `PROVEN INTERNALLY — NUMERICAL CONTROL ONLY` for the tested settings;
- exact Figure 4e/f reproduction: `NOT CURRENTLY CLAIMED`;
- general physical localization claim: `REQUIRES LAB / PARTNER VALIDATION`.

## Next gate

1. obtain or reconstruct the exact Figure 4e/f normalization from author code or explicit author clarification;
2. rerun at `Nmax=200` with the locked physical parameters;
3. compare the first 30 source-topology IPR/eigenenergy curves to the published panel;
4. repeat the same locked setting under phase-stripped, Delta-sign, and randomized-phase nulls;
5. report effect size with cutoff convergence and negative evidence retained.

Until that gate closes, no exact localization-reproduction claim should enter external-facing Worldshepherd materials.
