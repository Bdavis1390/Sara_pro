# WorldShepherd RF discovery program — conventional-effect exclusion, v1.2

**Evidence state:** analysis methods implemented and tested with synthetic data. **No calibrated original RF traces or new physical interaction demonstrated.** This is an experiment specification, not an authorization to radiate RF or operate unsafe hardware.

## 1. Post-hoc frequency coincidence audit

`rf_coincidence_nulls.py` evaluates conventional mixing frequencies from the three historical operator-reported unvalidated paired GHz settings, using 50,000 independently varied sets in each of three arbitrary, band-conditioned input distributions (±2%, ±10%, ±30%). The minimum observed cross-pair conventional intermodulation frequency separation is 2.56 MHz (1.59256 vs 1.59000 GHz).

The fraction of random sets with **any** cross-pair mixed product at least this close is 0.0491, 0.1004, and 0.0861, respectively. These are **not valid confirmatory p-values**: historical settings were not drawn randomly, the search/window was retrospective, and the null distributions were invented for sensitivity assessment. No evidence of actual material or inter-pair physical coupling follows.

The raw simulation report is saved as `results/rf_coincidence_nulls_results.json` and reproducibility checks are in `test_rf_coincidence_nulls.py`.

## 2. Passive energy balance — independent of spectral mixing

`rf_power_balance_gate.py` takes explicitly labeled, calibrated-or-bounded physical **watt** channels for passive test systems: input, reflected, transmitted, radiated, heat, stored, and other. It requires OFF/A/B/AB for both CANDIDATE and BLANK across three or more truly independent sessions. It checks:

`P_in - (P_reflected + P_transmitted + P_radiated + P_heat + P_stored + P_other) = residual`.

The output is a **diagonal-uncertainty preliminary** closure diagnostic. It cannot authenticate a calibration ID; channel reference planes and nonoverlapping definitions must be independently reviewed. A residual outside 3 user-supplied standard uncertainties is `NONCLOSURE_REVIEW_REQUIRED`. This does **not** establish energy creation, violate thermodynamics, or identify a new physical force; missing pump power, channel mismatch, sensor error and calibration correlations are more basic explanations.

Active/pumped devices are deliberately rejected because this simple passive model lacks the full powered-system budget. Do not silently assign an unmeasured radiation, storage or heat channel to zero.

Tests: `test_rf_power_balance_gate.py` produces a synthetic closed-budget case, a synthetic apparent excess-output case, incomplete conditions, invalid active-system usage, and false calibration. The declaration of `SYNTHETIC_TEST` is mandatory for generated test data.

## 3. Receiver-versus-upstream artifact discrimination

The **physical location** of an unwanted nonlinear spur matters. A passive, independently characterized pad inserted *after* the sample but *before* the receiver attenuates a pre-existing sample/source spur approximately **1 dB** per **1 dB** of added loss. In the weak unsaturated cubic region, an IM3 spur generated internally in the receiver from the already attenuated tones can decline approximately **3 dB** per **1 dB** of added loss.

`rf_receiver_attenuation_gate.py` compares uncorrected receiver-level measurements at 3+ distinct calibrated pad losses spanning at least 8 dB, for candidate and blank under matched source settings and calibrations in 3+ independent sessions. It rejects source-power drift inconsistent with post-sample attenuation, measured outputs within 6 dB of the noise floor, and fake synthetic calibration IDs. Raw—not display-normalized—receiver dBm readings are required.

This test can help localize nonlinear distortion, but both material and source/combiner spurs are *upstream* of the pad, and coherent upstream/receiver contributions can produce nonlinear non-integer apparent slopes. A -1 slope does not identify novel material physics; a -3 slope does not by itself prove a receiver defect.

Tests: `test_rf_receiver_attenuation_gate.py` verifies synthetic -1, -3 and mixed slopes, pad mismatch, source drift, low-SNR and false-measurement cases.

## 4. Minimum independent physical experiment

A qualified RF metrology lab should freeze a protocol **before** examining new candidate spectra:

- independent low-power, shielded and terminated oscillators, appropriate load/isolation, certified frequency reference, VNA/spectrum analyzer and power meters in calibrated reference planes;
- OFF/A/B/AB for candidate and matched blank; known conventional nonlinear reference; sham frequencies; blinded materials and randomized measurement order;
- independent two-dimensional detuning and attenuation after the device under test; raw recorded phase and complex S-parameters; receiver preamp/attenuation and intermodulation characterization; source/combiner spur baseline; oscilloscope/reference receiver cross-check;
- complete passive/active device power and thermal accounting, with covariance and systematic uncertainty; record failures and censored peaks, never select only successful frequencies;
- preregistered physical model with units, coupling parameters, predicted amplitude *and* phase (not frequencies alone), preregistered multiple testing and physical replication at a second laboratory.

Only if a specific original prediction survives these and independent replication would it be appropriate to discuss an unexplained physical effect. A newly characterized nonlinear material response can still be **new engineering/materials science within established Maxwell electrodynamics**, not automatically a new fundamental physical law.

References and normal-physics comparators:
- NIST (2022), receiver nonlinearities of VNA: https://www.nist.gov/publications/quantifying-receiver-nonlinearities-vna-measurements-wr-15-waveguide-band
- NIST (2010), correlated VNA covariance: https://www.nist.gov/publications/covariance-based-vector-network-analyzer-uncertainty-analysis-time-and-frequency-domain
- Keysight, PNA-X intermodulation source and receiver effects: https://www.keysight.com/gb/en/assets/7018-01651/application-notes/5989-7265.pdf
- NIST (2025), VNA two-tier uncertainty: https://www.nist.gov/publications/two-tier-vector-network-analyzer-calibrations-uncertainties-laboratory-based-over-air

**No physical RF experiment performed.** The scientific discovery gate remains **BLOCKED**.
