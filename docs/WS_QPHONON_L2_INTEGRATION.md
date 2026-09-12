# WS-QPHONON L2 Architecture Integration

**Status:** L2 architecture integration only  
**Physical capability claim:** none  
**Promotion rule:** develop aggressively, validate independently, integrate as a claimed capability only when substantial evidence crosses the L3 gate.

## Purpose

WS-QPHONON provides a governed Worldshepherd interface for quantum-phononics research. It does not represent a Worldshepherd-owned quantum computer, phononic quantum network, coherent spin-phonon swap, or fault-tolerant quantum capability.

The L2 architecture connects the existing Worldshepherd governance stack to a future partner laboratory or simulator:

- **SARA** — experiment orchestration and policy routing.
- **PRIME** — posterior-risk and operating-envelope authorization.
- **ECHO** — raw-data, model, decision, waveform, result, and claims provenance.
- **OVERWATCH** — drift, thermal state, resonance, coherence, and model-discrepancy monitoring.
- **PRE** — recurring quantum requirements, opportunity readiness, and partner/funding alignment.

## Claims boundary

Worldshepherd may currently claim that it has specified and integrated a governed quantum-experiment architecture into the repository.

Worldshepherd must not claim that it has experimentally demonstrated:

- coherent SiV/SnV-to-phonon state swapping;
- phonon-mediated two-node transfer;
- a phononic two-qubit gate;
- a fault-tolerant phononic quantum network;
- a Worldshepherd quantum processor.

Those remain external, simulated, proposed, or unvalidated depending on the specific item.

## Governed state vector

The minimum registered state is:

```text
Theta = {
  g1, g2,
  kappa_m,
  gamma_eff,
  T1, T2,
  detuning,
  device_temperature,
  thermal_occupation,
  acoustic_drive,
  orbital_leakage_probability,
  transducer_response
}
```

`gamma_eff` and `kappa_m` are intentionally separate. An observed spin-response linewidth must not be silently relabeled as the intrinsic mechanical loss rate.

## PRIME authorization model

A coherent-transfer experiment is not authorized merely because point estimates look favorable. PRIME uses uncertainty-aware gates.

Initial screen:

```text
P(constraint violation | evidence) < 0.01
C_T2 >= 1
T_device <= 0.125 K
parameter-confidence gates = PASS
model holdout validation = PASS
claims state permits the experiment
```

Preferred thermal operating point is at or below 0.100 K.

Stretch values such as `C_T2 >= 10`, transfer fidelity `>= 0.90`, and development fidelity `>= 0.99` are engineering targets, not current capability claims.

## Bayesian identification rule

A transfer trace alone is insufficient to identify the device. Parameter identification should combine orthogonal measurements including:

1. mechanical ringdown or linewidth;
2. exchange/Purcell versus detuning;
3. Ramsey;
4. echo or noise spectroscopy;
5. T1;
6. sideband or calibrated thermometry;
7. acoustic Rabi sweep;
8. power-versus-temperature sweep;
9. out-of-manifold leakage spectroscopy.

The inference layer must retain explicit **model discrepancy** so an unexplained feature is not forced into a convenient change in `g`, `kappa_m`, or `T2`.

## Candidate control policies

The architecture may compare multiple control policies without claiming any has been experimentally validated on Worldshepherd hardware:

- FAST_SWAP;
- STIRAP_DARK;
- STA/CD;
- leakage-aware Pontryagin control;
- energy-aware shortcut-to-adiabaticity control.

Policy selection is permitted only inside a validated operating envelope.

## ECHO quantum evidence record

Every governed experiment should preserve at minimum:

```text
raw_data_hash
model_version
prior
posterior
experiment_proposed
expected_information_gain
prime_decision
control_waveform_or_parameters
environmental_state
measurement_result
model_discrepancy
claims_state
```

A result is not promoted merely because the measurement agrees with a fitted model. Holdout prediction is required.

## OVERWATCH behavior

Fast state:

- detuning;
- device temperature;
- T2;
- acoustic-drive efficiency.

Slow state:

- g1/g2;
- intrinsic mechanical loss;
- transducer response;
- orbital-leakage model.

If state leaves the validated envelope, OVERWATCH returns the system to **CHARACTERIZE**. Blind compensation is prohibited.

## PRE integration

PRE tracks this lane as **EMERGING DEMAND**, including:

- autonomous calibration;
- heterogeneous quantum interconnects;
- cryogenic control;
- quantum networking;
- AI-assisted experiment design;
- scientific provenance;
- fault/drift detection;
- human-authorized autonomy.

Prediction informs preparation only and never upgrades maturity.

## L3 promotion gate

WS-QPHONON becomes a Worldshepherd **capability** only after all of the following are satisfied:

1. real external quantum hardware is used;
2. the Worldshepherd control/governance layer participates in the experiment;
3. a reproducible physical result is observed;
4. a holdout prediction succeeds;
5. uncertainty bounds are reported;
6. complete ECHO provenance is preserved;
7. an independent human or partner can reproduce the result.

Until then, the lane remains **architecture/R&D**, not hardware capability.

## Immediate implementation tasks

- validate `config/ws_qphonon_l2_v0_1.json` automatically;
- create the QPHONON registry adapter contract;
- add the PRIME posterior-risk check interface;
- add ECHO quantum-evidence schema support;
- add OVERWATCH drift-state hooks;
- validate the stack with synthetic traces;
- identify an external laboratory partner for the L3 experiment.
