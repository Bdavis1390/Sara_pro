# WS-QBENCH-MGRAPH v0.4 source-lock gaps — 2026-10-01

## Purpose

The v0.1-v0.3 work has reached the point where additional numerical sophistication would risk false precision unless several source conventions are locked. This document records those gaps before any claim of exact Figure 4/Supplementary Figure S1 reproduction.

Primary source: S. Yu, X. Piao, N. Park, *Magnetic graphs for cavity quantum electrodynamics*, Science Advances 12, eaee5566 (2026), DOI `10.1126/sciadv.aee5566`, arXiv `2607.04736`.

## Gaps that matter

### G1 — Effective zero / connected-loop convention

End Matter I states that a loop is disconnected when any constituent weight is zero. Supplementary Note S1 defines `pConnect`, `pNontrivial`, and `pTrivial`, but the accessible text does not specify a numerical tolerance, hopping-order truncation rule, or underflow convention for treating very small nonzero displacement-matrix elements as absent.

This is not cosmetic. In the independent v0.2 sensitivity sweep, changing `rel_edge_threshold` from `1e-2` to `1e-8` materially changed `pConnect`, while the conditional nontrivial fraction remained near one half.

**Required lock:** exact code or explicit tolerance/truncation convention used to generate Supplementary Figure S1 and Figure 4d.

### G2 — Figure 4e/f Hamiltonian normalization

The source defines the physical Fock-space Hamiltonian through Eq. (3)/End Matter E1 with onsite terms `n hbar omega0 + h0 +/- |h_parallel|` and off-diagonal hopping amplitude `|h_perp| l_nm^(+/-)`. Figure 4e/f then evaluates the first 30 eigenstates of `H_C` using IPR and eigenenergy.

The accessible figure legend does not state the numerical values/normalization for `h0`, `|h_parallel|`, and especially `|h_perp|/(hbar omega0)` used for those panels.

**Required lock:** exact Figure 4e/f parameter values and energy units.

### G3 — Random-subgraph duplicate policy

The paper describes uniform sampling of number states over `{0,...,Nmax}` while also describing a `2q`-node subgraph. The natural implementation is sampling without replacement within each bipartition, which is what v0.2 uses, but an explicit duplicate/rejection convention is not visible in the accessible text.

**Required lock:** whether number states are drawn without replacement, drawn with replacement and rejected on collision, or handled another way.

### G4 — Published source code

The paper states that code is available from the corresponding authors upon request. No public repository was identified during the current ingest.

**Required lock:** obtain the source code or an author-supplied minimal reproduction script for Figures 3b, 4c-f, and Supplementary Figure S1.

## Interim engineering rule

Until G1-G4 are resolved:

- `lambda1` reproduction may be described as an independent numerical cross-check because it is insensitive to G1-G3;
- raw conductance results remain `SIMULATED ONLY` and must be reported with the complete-bipartite null;
- loop-formation probabilities remain threshold-sensitive and **not exact reproduction**;
- Figure 4e/f IPR/eigenenergy recreation remains **parameterized only**, not source-locked;
- no hardware or experimental performance inference is permitted.

## Next implementation step that does not require guessing

A parameterized Hamiltonian/IPR ablation harness may be implemented with all physical scale ratios explicit in its input. It must not ship with a claim that its defaults reproduce Figure 4e/f. The harness should sweep `|h_perp|/(hbar omega0)` and `|h_parallel|/(hbar omega0)` and compare source topology against controlled phase nulls. This turns the missing source normalization into a sensitivity axis rather than an undocumented assumption.
