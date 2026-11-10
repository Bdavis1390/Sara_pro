# WorldShepherd Scientific Evidence: BTO Photonics and Chiral Perovskite Spin Cascade
Date: 2026-11-10 | Umbrella: #282 Science & Validation | Status: literature review + synthetic-only numerical benchmark.

## Peer-reviewed sources
- Kang et al., *Broadband Optical Characterization of Tetragonal Barium Titanate by Mueller-Matrix Spectroscopic Ellipsometry*, **ACS Photonics**, 2026-10-20, https://doi.org/10.1021/acsphotonics.6c01514 . Reports orientation-sensitive complex optical constants for tetragonal BTO in 190 nm–40 μm and extinction coefficients ~1e-5 in the measured 2–10 μm transparency range. Claim: **SUPPORTED BY LITERATURE**.
- Qiu et al., *Perovskite chiral multiple quantum wells with extended spin lifetime via efficient spin cascade*, **Nature Photonics**, 2026-10-15, https://doi.org/10.1038/s41566-026-02027-6 . Reports room-temperature polarization persistence near 5 ns, luminescence dissymmetry up to 0.014 and transport spin polarization >80%. Publisher lists source XLSX for Figs 2/4/5. Claim: **SUPPORTED BY LITERATURE**.

## Physical scope and limitations
- BTO's optical tensor is not measured RF/GHz permittivity; cannot infer GHz resonance directly.
- Chiral quantum-well **spin-polarization lifetime** is not equivalent to a verified qubit T2 coherence time or a quantum memory.
- Different materials and distinct mechanisms do not establish their cross-coupling or WorldShepherd's unpublished proposals.
- No source XLSX or ACS original numeric optical tensor was imported into the benchmark on this date.

## Controlled synthetic benchmark
The standalone WorldShepherd Phase II local package implements a simple Beer–Lambert BTO attenuation calculation, rotated dielectric tensors, and a four-stage classical polarization-population kinetic model:
`dP_i/dt = -(gamma_i+k_i)P_i + eta_(i-1) k_(i-1) P_(i-1)`.
Rates are **arbitrary illustrative**, not fitted paper parameters: gamma=[5, 2, 0.5, 0.2] ns^-1, k=[20,20,20] ns^-1, eta=[0.96,0.96,0.96].
- First 1/e crossing: no-transfer=0.200 ns; cascade=2.807 ns (**SIMULATED ONLY**).
- Illustrative bulk BTO attenuation at 5 µm, kappa=1e-5, L=1 mm: alpha=25.1327 m^-1, ~0.109 dB, excluding scattering and waveguide overlap.
- Seven unit tests passed for this bounded implementation (**IMPLEMENTED IN SOFTWARE**). These tests do not validate physical measurements.

## Science & Validation next gates
1. Obtain article source files with recorded URLs, license, SHA256, figure mapping, axis definitions, uncertainties and immutable custody record.
2. Fit measured BTO axis-resolved n,k including orientation, passivity, causality and uncertainty, against measured optical observables. Do not extrapolate to microwave parameters.
3. Fit source-data polarization dynamics with one-/multi-exponential, sequential-rate, and instrument-response-convolved models. Check background, pump conditions, achiral and reversed-layer-order controls, hold-out residuals and uncertainty intervals.
4. Preregister new cross-domain experiments: optical and electrical controls, heating, geometry, calibrated measurement floor, randomization, negative controls and independent lab replication. State: **HYPOTHESIS / REQUIRES LAB VALIDATION**.
5. Disclose no proprietary frequency predictions, private system designs, partner/custody records or secrets through public GitHub.

This review follows [WorldShepherd's claim and evidence policy](../CLAIMS_AND_EVIDENCE_POLICY.md): papers are not prototypes; synthetic simulations are not experimental proof.