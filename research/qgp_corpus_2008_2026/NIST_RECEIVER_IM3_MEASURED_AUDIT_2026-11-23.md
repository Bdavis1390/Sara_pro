# WorldShepherd external nonlinear RF measurement audit — NIST MDS2-2628

**Execution:** November 23, 2026, America/New_York  
**Evidence classification:** independently collected **NIST** IQ receiver measurements; reanalyzed by WorldShepherd software. **No WorldShepherd physical experiment, new materials response, or new fundamental physics demonstrated.**

## Primary source and prior art

- NIST [public data collection 10.18434/mds2-2628](https://data.nist.gov/od/id/mds2-2628), *Measurements of IP3 and P1dB for Spectrum Monitoring with Software Defined Radios (Public Release of Data)*, 2022.
- McNulty, Gu, Kuester and Nayeri, [EuCAP 2022 paper](https://www.nist.gov/publications/measurements-ip3-and-p1db-spectrum-monitoring-software-defined-radios), DOI 10.23919/EuCAP53622.2022.9769373. The publication **already reports departures from the ideal 3 dB/dB IMD3 slope**; this fact and its interpretation are not novel WorldShepherd research.
- The data collection is public under the [NIST open license](https://www.nist.gov/open/license).

## Storage-preserving acquisition

The full publicly downloadable IMD3 ZIP archives are approximately 773 MB (SDR0) and 976 MB (SDR1). NIST supports HTTPS byte ranges; a read-only archive indexer retrieved just the necessary ZIP central directories and JSON experiment metadata without storing either full archive on Lenovo.

| Source archive | Entries | On-server archive size |
|---|---:|---:|
| `imd3 sdr0.zip` | 50 | 772,741,579 bytes |
| `imd3 sdr1.zip` | 69 | 975,535,369 bytes |

Individual `2f1-f2/test_N.bin` signals were streamed and fully decompressed for ZIP-member CRC verification and independent uncompressed SHA-256. Files were not persistently extracted; the first 524,288 complex float32 samples of each capture were analyzed in memory at the reported 5 MHz sample rate, giving 9.5367 Hz spectral-bin resolution. The full source archive SHA-256 hashes have **not** been verified because the archives were not entirely downloaded. Therefore, provenance assertions apply to the fetched NIST URL, selected individual member CRCs and SHA-256 digests, not a verified full ZIP.

The known two-tone source frequencies are approximately **1.702500 GHz** and **2.702499878 GHz**. The conventional expected third-order product `2 f1 - f2` is **702.500122 MHz**. The reported receiver center was **701.500 MHz**, so the expected baseband offset is approximately **1.000122 MHz**.

## Measured signal response (selected NIST captures)

FFT search: Hann-windowed complex ADC samples; candidate peak selected over ±15 kHz around the source-predicted beat. Reported amplitude is `20 log10(|FFT peak| / sum(window))`, a **relative ADC amplitude in dB, NOT calibrated RF output dBm**. A neighboring median single-bin FFT amplitude defines an exploratory SNR proxy. The search-window *maximum* itself has a look-elsewhere bias; it cannot be called a detected signal without a matching noise comparison.

Selected NIST IQ capture results:

| Per-tone nominal power (dBm) | SDR0 relative peak (dB) | SDR0 SNR proxy (dB) | SDR1 relative peak (dB) | SDR1 SNR proxy (dB) |
|---|---:|---:|---:|---:|
| -20 | -114.29 | 11.48 | — | — |
| -16 | -115.09 | 10.64 | -97.44 | 21.89 |
| -12 | -103.36 | 22.39 | -85.44 | 33.62 |
| -9 | -93.50 | 32.25 | -76.52 | 42.42 |
| -7 | -86.62 | 39.08 | -70.45 | 48.48 |

The source also supplies a 50 Ω terminated receiver test. The maximum among many searched bins is already **11.61 dB** above the local single-bin noise proxy for SDR0 and **10.41 dB** for SDR1. The apparent low-power SDR0 peaks are therefore not accepted as robust IM3 detections.

**Retrospective diagnostic only:** an explicit filter requires at least 6 dB above that receiver's observed terminated-control *maximum*, plus a peak staying within 250 Hz of the stronger-capture frequency anchor (which is itself selected after inspecting the candidate captures). SDR0 qualifies the -12, -9 and -7 dBm settings; SDR1 qualifies -16, -12, -9, -7 dBm.

| Receiver | Accepted points | IM3 amplitude slope, dB/dB | Residual RMS |
|---|---:|---:|---:|
| SDR0 | 3 | **3.34445** | 0.0838 dB |
| SDR1 | 4 | **2.99628** | 0.0312 dB |

These are *descriptive*, post-selected relative slopes with very few points. They are compatible with known cubic receiver intermodulation behavior and cannot be interpreted as statistically significant deviations from a fundamental cubic law. The SDRs are different instruments, not replications of an original WorldShepherd physical sample.

High-power detected baseband peaks are close to 1.0015 MHz rather than the approximately 1.000122 MHz source-calculated IF. That ~1.4 kHz offset can arise from oscillator/reference clock offset or acquisition settings; source timing synchronization was not independently measured here. Such offsets must not be treated as an anomalous resonance.

## What was independently tested?

- HTTPS Range ZIP index metadata for both NIST SDRs.
- Full decompression with ZIP-member CRC32 verification and locally computed SHA-256 for selected IQ captures; *not* complete archive download/hash.
- Complex IQ FFT estimation with bounded memory; explicit frequency-bin resolution.
- A matched 50 Ω terminated-control search-window maximum, illustrating why unrestricted spectral peak hunting creates false detections.
- Basic relative amplitude-versus-input response, fit after a documented retrospective low-SNR exclusion.

The five NIST-IQ parser/spectral tests and five noise-quality filter tests pass. The complete WorldShepherd research regression suite is **86/86 PASS**. These are software tests, not 86 original physical experiments.

## WorldShepherd discovery gate

**Current result:** a real NIST-established nonlinear receiver artifact baseline has been independently reproduced at selected conditions. This strengthens the conventional-physics null against which any future WorldShepherd sample effect must be tested.

**Still missing:** source-isolated and receiver-isolated two-tone measurements of a real WorldShepherd test article; prospective predictions of calibrated complex IM3 amplitude, phase and drive dependence; independent fixture/cable controls and full error covariance; matched sample/blank and a known nonlinear reference; a held-out experiment and a second-laboratory replication. Ordinary device nonlinearity, including receiver-dependent slope deviations, does **not** constitute new fundamental physics.

The previous TERRAMETA measured linear S2P dataset and this NIST measured two-tone IQ dataset answer different questions. They cannot be combined into a claim of *the same hardware* exhibiting a new physical mechanism. Continue treating QGP transport as a separate scientific domain.

## Scripts and derived artifacts

- `nist_range_zip_metadata.py`, `nist_im3_iq_selected_analysis.py`: bounded NIST source inspection and selected IQ streaming/relative FFT analysis.
- `nist_im3_quality_gate.py`: retrospective control-maximum, frequency-stability and power-slope reporting.
- `test_nist_im3_iq.py`, `test_nist_im3_quality_gate.py`: five synthetic tests each including optional local NIST-derived summaries.
- `results/nist_imd3_sdr0_index.json`, `results/nist_imd3_sdr1_index.json`: source archive index and public measurement metadata.
- `results/sdr0_selected_im3_real_iq.json`, `results/sdr1_selected_im3_real_iq.json`: per-capture member digests, relative spectral estimates.
- `results/receiver_pair_crosscheck.json`: complete quality-filter disclosure and conventional model comparison.

**Scientific claim status: NO ORIGINAL NEW PHYSICS DEMONSTRATED.**
