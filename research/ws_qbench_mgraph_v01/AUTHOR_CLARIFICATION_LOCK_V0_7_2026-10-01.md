# WS-QBENCH-MGRAPH v0.7 corresponding-author source lock — 2026-10-01

## Status

This note records a direct clarification from corresponding author Sunkyu Yu, received 2026-10-02 KST (2026-10-01 EDT), in response to the Worldshepherd reproduction query for *Magnetic graphs for cavity quantum electrodynamics*.

The clarification resolves the numerical-convention gaps G1-G3 and locates the authors' Code S1 implementation. Exact-figure reproduction remains disabled until Code S1 itself is locally acquired, hashed, and compared line-by-line against the Worldshepherd implementation.

Claim state: `SUPPORTED BY LITERATURE` + `IMPLEMENTED IN SOFTWARE` + `SIMULATED ONLY`. No hardware inference is authorized.

## Author-locked conventions

### G1 — loop connection and phase classification

- Fock cutoff for the reported pipeline: `Nmax = 200`.
- Hopping elements: closed-form Laguerre expression.
- No numerical tolerance is applied to decide whether a hopping element is zero.
- No maximum hopping-order cutoff is applied.
- A sampled loop is connected iff its full `2q`-fold product `Wq` is exactly nonzero in double-precision arithmetic.
- Nontrivial loop phase: `|Phi_q - pi| < 1e-9`.
- Trivial loop phase: `|Phi_q| < 1e-9`.

This supersedes the earlier Worldshepherd threshold-proxy convention for attempts to match Figure 4d / Supplementary Figure S1.

### G2 — Figure 4e/f Hamiltonian normalization

The corresponding author specified dimensionless units with:

- `hbar = 1`;
- `omega0 = 1`;
- `h0 = 0`;
- `h = (0, 0, 1/2) hbar*omega0`;
- `|h_parallel| = 0`;
- the transverse/perpendicular component has magnitude `1/2 hbar*omega0`;
- real transition dipole `d = (1, 0, 0)`;
- `d+ = d- = 0`;
- `A0 = (eta, 0, 0)`;
- `omega_q = omega0`;
- first 30 eigenstates are used for the Figure 4e/f localization/eigenenergy calculation.

Worldshepherd maps the author's transverse/normal coefficient to its `h_perp` parameter. That notation mapping must still be checked against Code S1 before claiming exact source reproduction.

### G3 — random-subgraph sampling

The `q` number states in each bipartition are sampled **without replacement**.

The requested source run uses `2 x 10^4` realizations with `q = 2..10, 30, 50`.

### G4 — authors' code

The corresponding author states that the complete codebase is supplied as **Supplementary Material, Code S1** with the published paper.

The Figure 4 / Supplementary Figure S1 pipeline was identified as:

1. `R003_Rabi_001_eig_Fock_data.m` — Hamiltonian, magnetic Laplacian, eigenstates;
2. `R003_Rabi_001_eig_Fock_post.m` — random subgraphs and loops;
3. `R003_Rabi_001_eig_Fock_post_plot.m` — figures.

This changes G4 from "not found" to **located but not yet locally verified**. The publisher asset could not be programmatically retrieved in the current environment, so Code S1 has not yet been hashed or line-by-line compared.

## Promotion gate

Exact Figure 3b / 4c-f / Supplementary Figure S1 reproduction remains blocked until:

1. Code S1 is acquired locally;
2. the three named MATLAB files are cryptographically hashed;
3. parameter conventions are checked directly against the code;
4. Worldshepherd runs `Nmax=200`, `2 x 10^4` realizations and the source `q` set;
5. output discrepancies are quantified rather than visually asserted away.

The prior null-control, cutoff-sensitivity, and negative-evidence results remain separate from the source-paper implementation.
