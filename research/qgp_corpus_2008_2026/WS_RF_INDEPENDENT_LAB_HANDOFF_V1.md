# WS-D14-RF-LAB.1.0 — independent falsification study handoff

**Classification:** public/nonproprietary measurement checklist; *not* an approved experiment, laboratory booking, procurement order or new-physics claim.

**State as of November 8, 2026 (EST):** no calibrated WorldShepherd raw RF measurement has been identified, no RF hardware/analyzer verified connected to Lenovo and no novel material effect has been demonstrated. This handoff is suitable for review by an independent RF metrologist and a scientific collaborator without transmitting proprietary implementational details.

## Primary scientific question

With a stable, terminated and calibrated low-power two-tone RF drive, does a blinded candidate coupon exhibit a repeatable complex nonlinear response that a conventional circuit/nonlinear-material model plus receiver/source artifacts cannot account for, across **independently withheld** sample, power, phase, frequency and temperature settings?

The physically conservative forward null is a calibrated nonlinear response plus artifacts, e.g.

```text
z_measured(omega_out) =
    H_path(omega_out) * z_source_spur(omega_out)
  + H_path(omega_out) * z_sample_nonlin(omega_out;
      chi2, chi3, higher_orders, geometry, temperature, drive_amplitude)
  + z_receiver_nonlin(omega_out)
  + correlated_noise_and_drift
```

This decomposition is schematic, not a derived fundamental Hamiltonian. An uncharacterized residual does not automatically imply new physics. Samples can show original engineered nonlinear properties entirely consistent with Maxwell electrodynamics.

The first- to third-order conventional products, sample/blank OFF-A-B-AB response, phase coherence, two-tone detuning, receiver-side pad experiment, sham frequencies and passive power conservation have executable source validators in the WorldShepherd research branch.

## Measurable initial predictions (conventional baseline / null)

Historical input pairs (GHz; unvalidated as material resonances):

| Pair | Tone 1 GHz | Tone 2 GHz | An expected conventional IM3 product |
|---|---:|---:|---:|
| WS-RF-001 | 3.96993 | 9.53242 | `f2 - 2*f1 = 1.59256 GHz` |
| WS-RF-002 | 0.242 | 0.953 | `2*f2 - f1 = 1.664 GHz` |
| WS-RF-003 | 0.396 | 0.993 | `2*f2 - f1 = 1.590 GHz` |

Independent pair 1 and pair 3 IM3 outputs lie **2.56 MHz** apart. If their outputs are coherently combined, an ordinary beat is predicted with period **390.625 ns**, even if the physical paths are independent and have zero material cross-coupling.

For a perturbative, source-locked IM3 component with signed tone orders `m,n`, the complex output follows `exp[i(m*phi_low+n*phi_high)]`; simple power dependence is `P_low^|m| * P_high^|n|` in weak unsaturated conditions. These predictions are also produced by nonlinear source components and receivers.

If the candidate merely exhibits these conventional scaling relations, **do not claim a new fundamental physical effect**. A sample-specific nonlinear response can still have materials-science or engineering value, subject to prior-art and IP review.

## Recommended minimum data-acquisition matrix

The following counts are acquisition-plan arithmetic, **not** statistical-power guarantees.

- For **each** of 3 paired-frequency hypotheses, complete **at least three truly independent sessions** on multiple days, with randomized sample labels and stable independent calibration.
- Within each session, acquire each of **CANDIDATE**, **BLANK**, and **KNOWN_NONLINEAR_REFERENCE** over a full 4 × 4 independent low-tone/high-tone phase cycle, using the same source state, calibrated complex-IQ reference plane and settings.
- This implies **3 × 3 × 3 × 16 = 432 complex-IQ records** across the initial three-pair phase protocol, excluding additional independent confirmations, sham settings, separate power-ramp data and reference standards.
- In a **separate, matched** subexperiment, record OFF/A/B/AB input and output channels for candidate and blank: 3 pairs × 3 sessions × 2 sample types × 4 conditions = **72 initial power-condition records**, each with nonoverlapping, calibrated or bounded reflected, transmitted, radiated, heat, stored and other power channels, plus the full input.
- In another **separate** subexperiment, perform at least 3 calibrated pad settings spanning ≥8 dB **after the sample and before the receiver**, sample vs blank, for at least three independent sessions: 3 × 3 × 2 × 3 = **54 pad-response records**; source drive and calibration state must stay fixed.
- Independently detune each tone in both frequency directions, with at least six distinct two-dimensional settings per sample type and independently verified source/reference clocks. Run sham-frequency and fixture-swap controls.
- The initial count is **not** a guarantee of 5% significance or sufficient detection power. Before booking, calculate power from measured lab noise/covariance, expected effect size and look-elsewhere family, then preregister sample size and stopping rules.

## Required artifacts per instrument and run

Raw original instrument traces, complex I/Q, calibration certificate/reference-plane details, receiver gain/linearity checks, source drive and attenuation, fixture/sensor geometries, environment and temperature, phase-reference continuity, RBW/VBW/window settings, cable swap log, unpowered and dummy-load controls, and cryptographic digests for every original file. Treat saturated and below-noise lines as **censored observations**; do not convert them to zero.

Use instrument independent receiver/VNA check and second qualified laboratory, with the sample labels and confirmatory frequency/power settings held out and signed by an independent custodian.

## Pre-release statistical gates

1. Publish or privately escrow a timestamped model with **quantitative predicted complex amplitude/phase**, parameter bounds and uncertainty covariance, plus the complete conventional baseline, before receiving independently held-out data.
2. Verify source labels, spectrometer reference planes and instrument certificate lineage; reject or quarantine runs with missing calibration, uncontrolled receiver compression, misidentified sample labels or nonclosed energy budgets.
3. Reject standard cubic and higher-order mixing, normal dispersive material response, fixture/cable modes, cross-source interference, temperature and drift alternatives before discussing a novel mechanism.
4. Use a preregistered model-comparison statistic across **all** tested bands, sample identities and settings. Independently quantify frequency/time look-elsewhere choices, systematic errors and covariance. Record **all null and negative runs**.
5. Seek blinded replication with a separate qualified team/instrument after the primary result, and obtain technical review for electromagnetic, energy and statistical consistency.
6. New **material response** ≠ new **fundamental law**. A result must discriminate a specific new physically derived theory, not merely produce a visible spur or a large fitted residual.
7. Confirm data/IP release authority before making public assertions. No unpublished source model or confidential parameter set is to be placed on the existing public Sara_pro research branch.

## Data-only analysis command map

- `rf_intermod_prior.py`: standard low-order product frequencies and cross-pair close products.
- `rf_coincidence_nulls.py`: arbitrary illustrative post-hoc coincidence baselines, **not** confirmatory p values.
- `rf_detuning_gate.py`: independently detuned two-tone peak trajectories; fixed interference vs normal mixing.
- `rf_measurement_gate.py`: OFF/A/B/AB, candidate minus blank, exact sign-flip and Holm correction on declared power readings.
- `rf_power_balance_gate.py`: passivity and apparent nonclosure; no energy-creation interpretation.
- `rf_receiver_attenuation_gate.py`: tentative -1 dB/dB upstream spur vs -3 dB/dB weak receiver IM3 control.
- `rf_phase_cycle_gate.py`: complex coherent phase response vs fixed spur for candidate, blank and standard nonlinear reference.
- `rf_four_tone_beating_baseline.py`: 2.56 MHz beat under **zero** inter-pair coupling.
- `test_*.py`: offline literature, data, simulation, control and artifact regressions. **Not hardware tests.**

Scientific metrology reference anchors:
- NIST, *System-Level Calibration of a Millimeter-Wave Vector Signal Analyzer with Uncertainties* (2025), https://www.nist.gov/publications/system-level-calibration-millimeter-wave-vector-signal-analyzer-uncertainties .
- NIST, *Quantifying Receiver Nonlinearities in VNA Measurements for the WR-15 Waveguide Band* (2022), https://www.nist.gov/publications/quantifying-receiver-nonlinearities-vna-measurements-wr-15-waveguide-band .
- NIST, *Two-Tier VNA Calibrations for Uncertainties in Laboratory-Based Over-the-Air and Channel Measurements* (2025), https://www.nist.gov/publications/two-tier-vector-network-analyzer-calibrations-uncertainties-laboratory-based-over-air .
- NIST, *NIST-Traceable Microwave Power Measurement in Waveguide Calorimeter with Correlated Uncertainties* (2019), https://www.nist.gov/publications/nist-traceable-microwave-power-measurement-waveguide-calorimeter-correlated .

**Gate as of November 8, 2026 EST: unresolved original physical prediction, no verified RF measurements, no qualified independent replication. New physics NOT demonstrated.**
