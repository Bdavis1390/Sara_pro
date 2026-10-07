# Worldshepherd WS-QPHONON-ZENO-TOY-002 — v0.2 research extension

**Classification: IMPLEMENTED IN SOFTWARE / SIMULATED ONLY.**

## What this is

A *phenomenological* four-state Lindblad simulation of a single-excitation shared phonon bus, with two distinct environmental mechanisms and coherent pulse sequencing. This is a frozen standalone successor to the v0.1 toy baseline. It does **not** numerically reproduce either paper, is **not** a model of a fabricated semiconductor chip, and does **not** demonstrate quantum advantage, error correction, an entangling gate, or hardware readiness.

Source context (neither replicated):

* Myronov et al., *Quantum phononic links for on-chip long-range coupling of hole spin qubits in compressively strained germanium on silicon*, APL Quantum 3, 026115 (2026), DOI [10.1063/5.0332643](https://doi.org/10.1063/5.0332643).
* Christie et al., *Cosmic Lockdown: When Decoherence Saves the Universe from Tunneling*, arXiv:[2512.14204](https://arxiv.org/abs/2512.14204). Its inflaton-field dynamics are **not** implemented.

## Mechanisms distinguished

1. **Absorptive mode loss:** `L = sqrt(kappa) |sink><P|` removes the excitation. This is not the same thing as repeated measurement of a qubit.
2. **Nonselective sender-site monitoring:** `L = sqrt(gamma_A) |A><A|` dephases the site occupation and inhibits escape at large `gamma_A` (Zeno-like).
3. **Coherent population trapping / adiabatic passage (CTAP/STIRAP-like):** `g_B(t)` pulses before `g_A(t)`, enabling an approximate dark state `|D> ∝ g_B|A> − g_A|B>`. The protocol can reduce shared-mode occupation at long durations, but is sensitive to duration and detuning.

The Hamiltonian and all rates are **dimensionless** with hbar=1. A coupling of 1 does not mean a measured 1 GHz device or any specific lithographic length. There are no thermal phonons, multiple propagation modes, dispersion, or correlated non-Markovian noise. Spatial attenuation from v0.1 is only an uncalibrated heuristic and is not used to estimate distances here.

## Reproduce

```sh
cd research/qphonon_zeno/v0_2
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run_protocol.py
```

Local artifact runs can also be invoked in the standalone extracted `WS-QPHONON-ZENO-v0.2` directory. Results and provenance hashes appear in `results/`, and three plots in `plots/`. Test results must be preserved separately from benchmark-run success.

## Fair comparisons

The static reference has `g_A=g_B=1` and starts in `|A>`. For each pulse duration `T`, report static receiver population both at time `T` and the **best value at any earlier time** in `[0,T]`. The pulse has bounded peak `g=1` per arm but **does not** have the same total integrated control power/energy as the constant-coupling case. Pulse sequencing can win in some lossy parameter regimes *only by using substantially longer duration*. No speedup claim is warranted.

All final probabilities are **unconditional**: lost excitations are not discarded or postselected. A single-excitation population transfer is **not** sufficient to establish faithful transfer of arbitrary qubit amplitudes and phases.

## Bounded validation gate

- 25 unit tests including inherited v0.1 physics tests, independent solver cross-check, Lindblad trace/positivity, integrated dissipation, monitoring-only/no-loss, solver-tolerance convergence, detuning sensitivity, and explicit NaN/Inf fail-closed regressions.
- Fail-closed run health checks first reject non-finite metrics, then enforce `max|trace−1| <= 1e-8`, minimum sampled eigenvalue `>= −1e-8`, and phonon-integrated loss consistency `<= 5e-4`; JSON serialization also rejects NaN/Inf.
- New-source and output SHA-256 hashes, Python/numeric-library versions, and wall-clock generation timestamp are recorded.
- Full source-paper reproductions, device parameter calibration, two-qubit gate fidelity, and partner/laboratory validation remain **NOT CURRENTLY CLAIMED**.

## Next scientific gate

A defensible follow-on would require an actual waveguide spectral density or measured/finite-element phonon mode coupling, calibrated scattering and coherence rates, propagation delay, thermal occupancy, and a logical qubit process-fidelity metric. Until then these sweeps are hypotheses for controller design, not engineering performance forecasts.
