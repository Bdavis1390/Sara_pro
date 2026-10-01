# WS-QBENCH-MGRAPH v0.4 review handoff

## Reviewer orientation

Start with:

1. `README.md`
2. `CLAIMS_MATRIX_V0_4_2026-10-01.md`
3. `VALIDATION_V0_2_2026-10-01.md`
4. `PHASE_NULL_V0_3_2026-10-01.md`
5. `LOCALIZATION_ABLATION_V0_4_2026-10-01.md`
6. `SOURCE_GAPS_V0_4_2026-10-01.md`
7. `EXTERNAL_REVIEW_CHECKLIST_V0_4.md`

Then inspect implementation in `magnetic_graph.py`, `validation_v02.py`, `phase_null_v03.py`, and `localization_ablation_v04.py` together with their test modules.

## Most important result

The work now contains both a positive and a negative adversarial finding:

- **Positive:** detailed source sign topology changes the magnetic-Laplacian connectivity metric `lambda1` beyond edge magnitudes/coarse phase classes in the tested finite model.
- **Negative:** the corresponding incremental IPR-localization effect is not invariant to the physical Hamiltonian scale ratio `h_perp/omega0`; its sign changes across the current sensitivity sweep.

Both must survive review together. Removing the negative result would materially misrepresent the evidence state.

## Blocked exact-reproduction claims

Do not approve wording that says Figure 4e/f or Supplementary Figure S1 has been exactly reproduced. The source-lock gaps remain explicit and an author-query draft is prepared.

## Merge recommendation boundary

Technical merge readiness requires exact-head CI, resolved comments, and consistency with the claims matrix. Scientific claim promotion beyond the current labels requires the v0.5 source-lock gate. These are separate decisions.
