# WS-QBENCH-MGRAPH v0.6 — topology × energy-scale interaction gate

## Why this gate exists

v0.3 found that the source detailed sign/phase topology changes the normalized magnetic-Laplacian `lambda1` relative to magnitude-preserving Delta-sign permutation controls. v0.4 then found that the source-minus-null IPR difference changes sign and magnitude as `|h_perp|/(hbar omega0)` is varied.

These results are not logically inconsistent. For a positive global adjacency rescaling `A -> c A`, the degree matrix rescales as `D -> c D`, so the normalized magnetic Laplacian

`L = I - D^(-1/2) A D^(-1/2)`

is invariant to `c`. By contrast, the physical Hamiltonian contains onsite and hopping energy scales separately, so its eigenvectors and IPR depend on ratios such as `|h_perp|/(hbar omega0)`.

v0.6 therefore tests a narrower statement: **does the localization effect of detailed phase topology interact with the physical hopping/onsite scale ratio?**

## Predeclared contrast

For one source topology `S`, one null topology `N`, a reference scale ratio `r0`, and a target ratio `r1`, define

`Delta(r) = IPR_S(r) - IPR_N(r)`

and the paired interaction contrast

`I(r1,r0) = Delta(r1) - Delta(r0)`.

Equivalently,

`I = [IPR_S(r1)-IPR_N(r1)] - [IPR_S(r0)-IPR_N(r0)]`.

Under an additive/no-interaction model, `I = 0`. Positive `I` means the source topology's IPR advantage relative to that null becomes more positive at the target scale. Negative `I` means it becomes less positive or more negative.

For stochastic nulls, **the same null topology is evaluated at both scale ratios** before computing `I`. This paired design removes between-null topology variation from the scale contrast and is stronger than comparing two independently sampled null ensembles.

## Null families

1. `phase_stripped`: deterministic magnitude-only positive hopping;
2. `delta_sign_permuted`: preserves every edge magnitude in place, coarse hopping-order phase parity, symmetry, and per-band sign counts while permuting detailed sign placement;
3. `randomized_phase`: preserves every edge magnitude while replacing phases with independent random phases; deliberately nonphysical.

## Claims boundary

- interaction harness: `IMPLEMENTED IN SOFTWARE`;
- any numerical interaction sweep: `SIMULATED ONLY`;
- null families: `HYPOTHESIS / ADVERSARIAL CONTROL`;
- exact source Figure 4e/f reproduction: `NOT CURRENTLY CLAIMED`;
- hardware/experimental implication: `REQUIRES PARTNER VALIDATION`.

The source paper does not claim this Worldshepherd difference-in-differences analysis. It is an adversarial extension designed to separate scale-free graph structure from scale-bearing localization physics.

## Source-lock compatibility

G1-G4 from `SOURCE_LOCK_V0_5.json` remain authoritative. v0.6 does not resolve or bypass them. Until G2 is source-locked, ratio sweeps are sensitivity analyses only. When G2 is resolved, its published ratio becomes a predeclared target point inside the same interaction harness rather than requiring a new metric.

## Falsification rule

The topology-scale interaction hypothesis is not retained merely because some contrasts are nonzero. It should survive:

- Fock-cutoff convergence;
- repeated null ensembles;
- multiple reasonable reference ratios;
- sign/magnitude stability in the source-locked physical regime once G2 is resolved;
- comparison against phase-stripped and fully randomized-phase controls;
- negative-evidence retention.

If the interaction vanishes under convergence or is confined to arbitrary normalization choices, the stronger interpretation is rejected.
