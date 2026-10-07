# WS-QPHONON-ZENO-TOY-001 — Worldshepherd research benchmark v0.1

**Evidence class:** `IMPLEMENTED IN SOFTWARE / SIMULATED ONLY`.

A transparent four-state single-excitation toy model that compares coherent
phonon-mediated qubit transfer, acoustic-mode loss, pure dephasing and
Zeno-like inhibition of transfer. It is a standalone **research prototype**;
no quantum hardware, germanium material specimen, continuum waveguide, and
cosmological scalar field are simulated or validated here.

## Physics model

Basis: `|A>`, `|P>` (one shared phonon), `|B>`, `|loss>` (absorbing state).
With `ℏ=1`, coherent couplings `g_A`, `g_B` link A–P–B, and optional
site/phonon detunings describe frequency selectivity. The Lindblad
operators are `sqrt(kappa)|loss><P|` (phonon damping) and
`sqrt(gamma_j)|j><j|` (site-local pure dephasing).

The initial state is `|A><A|`. We report **unconditional** populations
including the loss state. Because these are Lindblad equations, density
matrix trace is preserved even while excitation is irreversibly deposited
in `|loss>`.

The testable expectation at the ideal transfer time `t = π/(sqrt(2)*g)`:
with equal couplings, zero detuning and no noise, `P(B)=1`. High dephasing
or high phonon loss inhibits transfer at that fixed observation time.
Extreme loss can increase retained `P(A)` while reducing `P(B)`—a
Zeno-like effect, **not** improved quantum-computing fidelity.

A sweep uses an exponential amplitude attenuation heuristic
`g_B/g_A = exp(-d/(2 L))`. This is NOT measured or derived from the
Ge/Si phononic paper, and no device-specific lengths/frequencies are fitted.
Phases are included; in this chain without a closed path the phase is
unobservable in site-population probabilities. Do not claim a phase-control
advantage from this phase parameter alone.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run_benchmark.py
```

Files created: `results/benchmark_results.json`, `results/provenance_manifest.json`,
`plots/noise_sweep.png`, `plots/detuning_sweep.png`.

## Research provenance and claims boundaries

Source inspiration (NOT numeric reproduction):

* Myronov et al., *Quantum phononic links for on-chip long-range coupling of
  hole spin qubits in compressively strained germanium on silicon*,
  *APL Quantum* 3, 026115 (2026), DOI: https://doi.org/10.1063/5.0332643.
* Christie et al., *Cosmic Lockdown: When Decoherence Saves the Universe from
  Tunneling*, 2026, https://arxiv.org/abs/2512.14204. This paper treats
  inflationary field theory, not on-chip acoustics. The present model only
  illustrates an analogous open-system mechanism.

Existing project integration boundary:

* WS-QBENCH v0.3 remains source-locked separately: the unresolved NcFT sign
  and reference conventions remain OPEN and are not overwritten by this toy.
* WS-QPHONON reconstructed provenance remains `RECONSTRUCTED`; this new
  standalone module is marked `NEW_WORK`, not `RECOVERED_SOURCE`.
* ECHO can ingest `provenance_manifest.json` and retain hashes of
  parameters, code and numerical artifacts. This repository does not claim
  that a SARA/PRIME authorization workflow has executed.

## Next independent gates

1. Specify and reproduce an actual Ge/Si phononic dispersion/coupling
   figure from the primary paper and its input dimensions/elastic constants.
2. Include spatially propagating phonon modes, spectral densities,
   temperatures, retardation and correlated loss beyond this 4-state toy.
3. Calibrate rates with *measured* partner data and record uncertainty.
4. Benchmark spectral selectivity and network transfer against no-bus and
   direct-exchange classical/control baselines.
5. Validate convergence with extended phonon-Fock cutoffs when multi-phonon
   physics is introduced; present single-excitation model has no cutoff sweep.
6. Require human sign-off before any physical deployment or claims upgrade.
