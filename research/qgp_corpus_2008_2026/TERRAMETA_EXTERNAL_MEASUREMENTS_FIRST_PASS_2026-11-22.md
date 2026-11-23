# WorldShepherd: first real published RF-data reduction — TERRAMETA memristors

**Report date:** 2026-11-22 (America/New_York)  
**Evidence:** Independent *external* calibrated-source measurements, not WorldShepherd laboratory measurements or novel physics.  
**Dataset:** Lucci & Pessoa, TERRAMETA, [Zenodo 10.5281/zenodo.20186567](https://zenodo.org/records/20186567), released 2026-05-14.  
**Repository rights:** Zenodo's machine-readable rights/license metadata did not provide a clear reuse license at verification. **Do not put the raw files or full numerical curves on the public GitHub branch.**

## Acquisition and source integrity

The study reports passive linear two-port S-parameters from an LRRM-calibrated Anritsu VectorStar ME7838G at 25 °C for two memristive devices in High Resistance State (HRS) and Low Resistance State (LRS). The source dataset comprises **12 Touchstone .S2P files**: 3 THRU standards/reference structures plus 9 memristor-state traces (device 1: 2 HRS/2 LRS; device 2: 1 HRS/4 LRS).

- **12/12 publisher MD5 hashes independently verified**, with local SHA-256 digests recorded.
- **1,664,424 raw bytes** downloaded to Lenovo only; data not mirrored to public GitHub.
- Every file contains **800** Touchstone records in the format `# Hz S RI R 50`. The frequency grid spans 70 kHz–160 GHz at approximately **200.250225 MHz** increments.
- Some files round printed frequencies to whole hertz; differences up to 0.5 Hz between grid text are treated as source-file formatting, not physically distinct frequency grids.

Source files are original third-party measurements according to Zenodo. WorldShepherd has not independently authenticated calibration certificates or measured those devices.

## Measured response near historical WorldShepherd GHz frequencies

Median state-wise S21 comparisons at the *interpolated* target frequencies:

| Device | Target frequency | Median LRS minus median HRS S21 (dB) |
|---|---:|---:|
| MEMR_1 | 3.96993 GHz | +2.617 |
| MEMR_1 | 9.53242 GHz | +0.293 |
| MEMR_2 | 3.96993 GHz | +8.959 |
| MEMR_2 | 9.53242 GHz | +3.814 |

The numbers are descriptive state contrasts, NOT confidence intervals. The states correspond to different switching histories/resistances, not independent instrument uncertainty replicates. Complex S21 was interpolated linearly; interpolation error and phase sensitivity have not been calibrated. Low and high state transmission differences are expected ordinary reconfigurable microwave-device behavior.

**Critical frequency-resolution limit:** The known ordinary-mixing products at 1.59000 and 1.59256 GHz differ by **2.56 MHz**, while this measured data grid is **~78.2 times coarser**. No distinct 2.56 MHz spectral structure or two-tone mixing can be inferred from this dataset; there are no measured IM3 products, IQ phase-cycling runs or instrument power ramps.

## Passive-system sanity check

A passive linear two-port ideally satisfies the singular-value bound `max_sv(S)<=1` when reference planes, power-wave normalization and calibration are correct.

Across this source dataset, 11 of 12 traces exceed the preliminary `1.02` singular-value threshold at high frequencies. Importantly, the **same flags occur in both fabricated-substrate THRU reference files**. None of the 12 crosses that threshold below 80 GHz; above 120 GHz all on-substrate traces, including THRUs, cross it.

A shared fixture/reference-plane or calibration-chain limitation is a plausible explanation. The deviations are **NOT evidence of energy creation**, and their cause is not proved without lab error budgets and reference-plane reconstruction.

## Conventional two-port model challenge: series versus shunt topology

For a zero-length ideal matched two-port with a lumped series impedance Z, the exact identity is `S11 + S21 = 1`; for a lumped shunt admittance Y, it is `S21 - S11 = 1`. Subtracting the corresponding identities of each of the two on-substrate THRU controls gives a **reference-differenced comparison**, not an exact cascade deembedding.

Across all nine memristor-state files below 10 GHz, the series-topology median residual versus the two THRU references is approximately **0.0024–0.0038**, compared with **0.089–1.665** for the shunt-topology median residual. All nine states are closer to the ordinary series-element relationship by this descriptive metric.

This is a physically constrained *conventional* baseline, not a novel-material claim. It needs fixture S-parameter deembedding, calibration uncertainty, and device-model review before extracting quantitative RLC values.

## WorldShepherd scientific gates

- **Established:** A real independently collected RF dataset is now locally ingested with provenance hashes; broad state-dependent switching and a conventional series-impedance baseline are verified descriptively.
- **Not established:** An original measured WorldShepherd sample, GHz-frequency mixing, 2.56 MHz doublet, characteristic-mode currents of a reconfigurable *aperture*, a unique nonlinear mechanism, a new law of physics, or calibrated uncertainty.
- **MOSAIC-RF next:** Obtain/produce two different antenna switch configurations satisfying the SAME radiation objective; test whether modal features improve held-out nonlinear-distortion predictions beyond local-device voltage/current and ordinary series-impedance/device harmonic-balance models.
- **Independent lab next:** WRCNC pilot should specify calibrated low-power two-tone sample vs blank, resolution finer than any tested narrow feature, phase-coherent source controls, receiver IM3 exclusions, full power and calibration covariance, and separate external replication.
- **Evidence rules:** Do not call checksum validation independent experiment, report passive apparent gain as energy production, or infer nonlinear intermodulation from single-tone S-parameters.

## Reproducibility

Public source scripts **without raw external data**:

- `fetch_terrameta_measured_rf.py` — retrieves publisher files, enforces size/host limits, checks source MD5 and records SHA-256.
- `analyze_terrameta_measured_rf.py` — strict Touchstone parsing, complex target interpolation, state contrasts, passivity and reciprocity flags.
- `rf_series_shunt_baseline.py` — two-reference conventional topology test.
- `test_terrameta_measured_rf.py`, `test_rf_series_shunt_baseline.py` — synthetic parser/physics controls plus optional external measured-data checks.

End-to-end connected Lenovo suite: **76/76 offline tests passed** (the additional 12 tests include measured-data integrity checks; they are not 12 new hardware experiments). The publisher's raw dataset and full derived local output remain on the Lenovo, excluded from this public research repository pending rights review.

**Conclusive scientific state: NO NEW PHYSICS DEMONSTRATED.** The tested observations are broadly compatible with standard linear microwave two-port behavior and known reconfigurable-device switching.
