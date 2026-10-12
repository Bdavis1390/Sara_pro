# WS-QBENCH-MGRAPH v0.5 source-lock gate — 2026-10-01

## Purpose

v0.5 converts the unresolved reproduction assumptions from prose into a machine-readable, fail-closed source lock. It does not add a new physics claim. It prevents exact Figure 4 / Supplementary Figure S1 reproduction language from being enabled while source conventions remain unresolved.

Primary source: S. Yu, X. Piao, N. Park, *Magnetic graphs for cavity quantum electrodynamics*, Science Advances 12, eaee5566 (2026), DOI `10.1126/sciadv.aee5566`, arXiv `2607.04736`.

## Current source state

A fresh public search on 2026-10-01 located the published article, arXiv preprint, and the SNU laboratory publication pages, but did not identify public source code for this paper. The paper text states that the codes used in the study are available from the corresponding authors upon request.

Accordingly, the following remain unresolved and blocking:

1. **G1** — numerical zero / connected-loop convention for Figure 4d and Supplementary Figure S1;
2. **G2** — exact Figure 4e/f Hamiltonian normalization and energy units;
3. **G3** — random-subgraph duplicate / rejection convention;
4. **G4** — author source code or a minimal reproduction script.

## Fail-closed behavior

`SOURCE_LOCK_V0_5.json` is integrity-bound with SHA-256. `source_lock_v05.py` rejects:

- an altered lock whose digest was not recomputed and reviewed;
- missing required gaps;
- `exact_figure_reproduction_allowed=true` while any G1-G4 blocker is not `locked`;
- any `hardware_inference_allowed=true` state within this research gate.

`authorize_exact_figure_reproduction()` remains blocked until all four source gaps are explicitly marked `locked` in a reviewed lock revision.

## Local validation

Before commit, the isolated v0.5 unit suite passed **6/6** tests. These tests validate the digest, gap enumeration, premature exact-reproduction rejection, hardware-inference rejection, and the all-gaps-locked transition path.

This local test is implementation evidence only. Repository CI on the committed head remains authoritative for merge readiness.

## Claims ceiling

- `lambda1`: independent numerical cross-check;
- conductance: `SIMULATED ONLY`, always accompanied by the complete-bipartite null;
- loop formation / `pConnect`: threshold-sensitive, **not exact reproduction**;
- Figure 4e/f IPR: parameterized ablation only until G2 is locked;
- Supplementary Figure S1: `NOT CURRENTLY CLAIMED`;
- hardware effect: `REQUIRES PARTNER VALIDATION` and not inferred from these simulations.

## Next gate

Do not increase model complexity merely to fill missing source conventions. Resolve G1-G4 from author-provided code or explicit parameter clarification, update the source-lock manifest with provenance, rerun exact-head CI, and only then attempt a claim-state transition for Figure 4/S1 reproduction.
