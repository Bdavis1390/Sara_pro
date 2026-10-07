# WS-QPHONON-MULTIMODE-003 — v0.3

**Evidence:** `IMPLEMENTED IN SOFTWARE / SIMULATED ONLY / SUPPORTED BY LITERATURE`.

This extension adds a vacuum-preserving multimode phonon bus, low-occupation finite-temperature Lindblad terms, propagation delay/phase utilities, and sender-to-receiver single-qubit channel fidelity. It is intentionally separate from any claim of fabricated hardware or source-paper figure reproduction.

## Source-bounded inputs

Myronov et al., *APL Quantum* **3**, 026115 (2026), DOI `10.1063/5.0332643`, states order-of-magnitude QPL ranges including phonon frequencies of 10–50 GHz, estimated spin–phonon coupling of 0.1–10 MHz, quality factors of about 1e4–1e6, and spin T2* of about 1–10 us. The paper also describes cs-Ge QW thicknesses around 10–30 nm, GHz phonon wavelengths around 100–500 nm, and expected coherent propagation from tens of micrometers to centimeters subject to material/fabrication limits.

Those ranges are **literature context, not Worldshepherd measurements**. The v0.3 demonstration uses a 25 GHz central mode and 1 MHz central coupling because they lie inside the stated ranges. Side-mode spacings/couplings, temperature, propagation distance, and representative group velocity are benchmark assumptions and are labeled as such in the output.

## Thermal boundary

The Hilbert space contains vacuum plus at most one excitation. Bosonic thermal upward/downward jumps are therefore only a low-occupation approximation. By default the model fails closed when any mode has `nbar > 0.05`; higher-temperature work requires a larger Fock-space implementation rather than silently extending this approximation.

## Channel metric

Pure-dephasing inputs are expressed as coherence-decay rates in s^-1; the benchmark maps the illustrative 5 us T2* surrogate to `gamma_phi=1/T2*`.

The model preserves vacuum/excitation coherence, allowing arbitrary input qubit states `alpha|0> + beta|1_A>`. It reports a six-cardinal-state average receiver fidelity. Both raw fidelity and a best deterministic receiver `Z`-phase-corrected fidelity are reported; the phase correction is not hidden as an optimization advantage.

## Reproduce

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run_v03.py
```

## Still not claimed

No COMSOL reconstruction, measured spectral density, calibrated group velocity, thermal multi-phonon dynamics, partner result, fabricated device, quantum advantage, error-corrected logical operation, or source-paper numerical reproduction is currently claimed.
