# WorldShepherd — falsifiable new-physics evidence gate (public, non-enabling)

**Version:** WS-NP-GATE.1.0 — 2026-11-08
**Status:** Reproducibility gate prepared; **no independent new-physics result established**.

## Evidence ladder

| Gate | Meaning | Current state |
| --- | --- | --- |
| G0: Source integrity | Traceable external source, hashes, license | PASS: STAR 2025 (5) and STAR 2026 (26) HEPData tables |
| G1: Published-result consistency | Independent data-readback/arithmetic/model cross-check | PARTIAL PASS: published STAR ratios and photonuclear slope check; full original detector analysis not available |
| G2: Distinct original prediction | Explicit preregistered model, conservation equations, parameter priors, quantitative novel prediction not fitted to evaluation data | NOT SATISFIED |
| G3: Held-out tests | Raw independently sourced experiment, calibration, experimental blinding, baseline model comparison and uncertainty/correction budget | NOT SATISFIED |
| G4: Independent replication | Separate qualified instrument/site/team, independent raw data, source code and author-signed provenance | NOT SATISFIED |
| G5: Scientific and release review | Independent specialist review, theory consistency, publication and authorized external release | NOT SATISFIED |

## Verified published benchmarks (not our discovery)
- STAR 2026 baryon-transport CC0 data DOI 10.17182/hepdata.154708: 26/26 exact table bytes and hashes mirrored into this research branch.
- Figure 4 scaled baryon/charge ratio values in centrality order 0–10%, 10–20%, 20–40%, 40–60%, 60–80%: 1.839, 1.740, 1.540, 1.331, 1.147.
- UrQMD reference calculated from STAR authors' published source archive: 0.726596, 0.689124, 0.660145, 0.5822795, 0.567359.
- Comparison is directionally consistent with STAR's **already published** model tension. Correlated systematic uncertainties and model error are not fully specified, so diagnostic chi-square values must not be presented as independent discovery significances.
- Independent approximate fit to 12 STAR derived net-proton rapidity bins: alpha = 1.057638 ± 0.150847 under declared covariance assumptions; STAR Table Figure 3 says 1.0402 ± 0.22. Bootstrap sigma ~0.150768 for 3000 fixed-seed draws. This is a computational verification, not a new QCD law.

## Required original, prospective tests

**QCD lane:** Freeze a new physical model with a *different prediction* for baryon-number and electric-charge transport across independent collision systems. Compare against representative modern baseline models with explicit nuisance terms and full covariance. Hold back an independent publication or future dataset before fitting and report both successes and failures. If every observation used to select/fix the model was already read, it cannot be called blinded confirmation.

**Electromagnetic/materials lane:** Use a preregistered, calibrated two-tone sample-versus-blank protocol. Record raw complex S-parameters, amplitude, phase, temperature, input/reflected/transmitted/radiated/dissipated power in SI units. Controls: dark/unpowered, each tone alone, both tones, blank fixture, reference nonlinear standard, randomized sham frequencies, blinded sample labels, independent instrument calibration, and independent repeat. Define a spectral *double-difference in watts*, not dBm:
D_sample(f) = P_AB,s(f) - P_A,s(f) - P_B,s(f) + P_off,s(f),
D_control(f) analogously; test D_sample - D_control against a calibrated conventional nonlinear mixing/circuit/material model. Nonzero mixing alone is **not** new physics.

Novelty tests require conservation-law consistency, uncertainty budgets, look-elsewhere correction, appropriate statistical threshold and qualified independent replication. A novel material response may remain consistent with standard Maxwell/QED physics; it should not be called a new fundamental interaction automatically.

## No unsupported cross-scale inference

GHz photon energies and the QCD thermal scale differ by many orders of magnitude. Established electromagnetic coupling to charged quarks in a heavy-ion plasma is not direct evidence that low-power RF drives QCD deconfinement or gluon-junction changes. A cross-scale proposal requires a concrete coupling Hamiltonian or effective action, consistent energy and scale accounting, and an independently measurable observable.

## Security / governance
Do not publish unpublished hardware implementation details, operator raw measurements, confidential parameter sets, or external draft IP before CRE1AWS release review. Detailed preregistration stays off this public code branch. This branch contains public data, reproducibility scripts, source hashes and openly described evidentiary criteria only.

No changes to production SARA, the original Palace 54-case solver, or the three existing scheduled tasks. No automated monitoring, filing, or external scientific claim authorized.

**Verdict as of November 8, 2026: G0 PASS; G1 PARTIAL PASS; G2–G5 OPEN.**
