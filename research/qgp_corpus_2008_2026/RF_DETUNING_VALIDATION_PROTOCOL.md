# WS-RF-DT.1 — standard two-tone detuning / spectral-spur discrimination

Status: **ANALYSIS SOFTWARE VALIDATED WITH SYNTHETIC INPUT ONLY — NO PHYSICAL DISCOVERY**.
This procedure follows published nonlinear RF metrology practice rather than proposing a new fundamental electromagnetic law.

## Why the detuning scan is necessary

Ordinary nonlinear devices, RF receivers, signal combiners, and samples produce spectral components at integer combinations `|m f_low + n f_high|`, including difference and sum frequencies, third-order `|2 f_low - f_high|` and `|2 f_high - f_low|`, and higher-order mixing. Observing a candidate peak at a predicted nonlinear frequency does **not** establish an original material response.

For a conventional third-order product with signed coefficients `(m,n)`, independently varying the two oscillator frequencies gives source-locked derivatives `d f_spur / d f_low = m` and `d f_spur / d f_high = n` (except near a sign crossing, where the absolute-frequency branch changes). Under weak unsaturated cubic response, the output power generally scales as `P_low^|m| P_high^|n|`; receivers can show the same effect. The phase combination is `m*phi_low+n*phi_high` for phase-coherent drives. Power or phase scaling alone cannot identify its physical origin.

The public code `rf_intermod_prior.py` builds the first- through third-order frequency prior, compares all source-pair combinations, computes the energy scale, and labels close numerical coincidences as **exploratory arithmetic only**. Historical source-pair frequency values originate from operator hypotheses and are **not measured RF resonances**.

## CSV for `rf_detuning_gate.py`

Fields:

`pair_id,sample_type,detune_id,f_low_hz,f_high_hz,observed_peak_hz,frequency_uncertainty_hz,instrument_id,calibration_id,data_origin`

- Sample type: `CANDIDATE` or `BLANK`. Both use identical independent 2D oscillator-detuning schedules.
- At least six steps and three distinct settings of each input frequency. Frequency changes must span two linearly independent directions; sweeping both frequencies together is uninformative.
- Explicit evidence origin: `SYNTHETIC_TEST` or `MEASURED_UNVERIFIED`. The instrument and calibration IDs are **declared only**, not authenticated.
- The validator tests signed low-order conventional mixing candidates against the supplied observed peak frequency uncertainties, and separately fits a static external-interference line.
- Possible outputs: `CONSISTENT_WITH_STANDARD_FREQUENCY_MIXING`, `CONSISTENT_WITH_FIXED_FREQUENCY_INTERFERENCE`, `AMBIGUOUS_MIXING_OR_STATIC_LINE`, `UNMATCHED_LIMITED_CATALOG_REVIEW_REQUIRED`.
- The discovery gate **remains BLOCKED for all outputs**, including unmatched peaks. There are unmodeled higher-order nonlinearities, independent resonator poles, spectral aliases, external interference, drift and receiver distortions.

Command: `python3 rf_detuning_gate.py --csv /absolute/path/to/paired_peak_tracks.csv --out /absolute/path/to/report.json`.

Regression test: `python3 -m unittest -v test_rf_detuning_gate`.

The synthetic tests create source-locked conventional intermodulation, fixed-frequency external interference, unrelated moving features, and invalid/collinear source controls. Tests do not use actual instruments.

## Further evidence required before any physical claim

1. Pre-register all input/output bands, detector resolution, dynamic range, filter transfer functions, source stability and linewidth before looking at real traces; account for all searched frequencies, not the interesting ones only.
2. Calibrated low-power shielded/terminated RF bench with independent tone sources, full trace provenance and a *sample-vs-blank* control run under the same conditions; equipment safety and permitted emission checks.
3. Independent input power ramp with expected `P_low^2 P_high` and `P_low P_high^2` baseline slopes, phase-lock control and loss/attenuation changes to identify receiver and generator origins.
4. Record complex scattering parameters and input/reflected/transmitted/radiated/dissipated power in watts with a stated uncertainty budget. Absolute energy accounting is independent of detection significance.
5. Controlled comparisons with established nonlinear materials and circuits, thermal drift, cable/attenuator substitution, phase and humidity changes, instrument swap, negative/sham scans, and blinded replication.
6. An **original physically derived, quantitatively distinct prediction**, not retrofitting a resonance interpretation after the spectra are observed. Independent laboratory replication and expert review remain mandatory.

References:
- Keysight, *Intermodulation Distortion Measurements Using the PNA-X*, https://www.keysight.com/us/en/assets/7018-01651/application-notes/5989-7265.pdf
- NIST Stelson et al. (2022), DOI 10.1109/TMTT.2022.3155466.
- NIST Kast et al. (2025), DOI 10.1109/TMTT.2025.3597240.
- NIST Manurkar et al. (2025), DOI 10.1109/OJIM.2025.3619249.

No calibrated experimental spectra were acquired or processed in this iteration; the numerical coincidences are not discoveries.
