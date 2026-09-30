# Phase-Gated Global State Switching

## 1. A new temporal scale for the consciousness model

Park et al. 2026 report that whole-brain directional information flow alternates between two dominant modes on an approximately 200 ms timescale.

### Top-down mode
Anterior regions lead posterior regions in phase.

Associated simultaneous fMRI activity emphasizes higher-order cognitive networks.

### Bottom-up mode
Posterior regions lead anterior regions.

Associated simultaneous fMRI activity emphasizes sensory networks.

The switching is most prominent in wakefulness and progressively diminishes with anesthesia.

This suggests that conscious wakefulness is not characterized by one fixed direction of information flow.

It is characterized by **rapidly reconfigurable directional exchange**.

## 2. Why this changes the frequency model

A power spectrum can tell us how much activity exists at various frequencies.

It does not by itself tell us:
- who leads whom;
- which direction information is propagating;
- which global state the brain currently occupies;
- when a perturbation is delivered relative to that state.

Relative phase adds directional structure.

Thus two brains can have similar spectral power while differing substantially in phase organization and directional flow.

## 3. Whole-brain stimulation modeling supplies the control side

Benitez Stulz et al. 2026 simulate perturbations in connectome-based whole-brain oscillatory models.

Their key result is not just phase dependence at the stimulated node.

The global functional-connectivity state changes the effective phase-response curve.

The same pulse can:
- produce a limited local/network deformation;
- or trigger switching to another global connectivity state.

Machine-learning prediction improved by up to 40% when global functional-connectivity information was included.

## 4. New state representation

A consciousness-control state vector should therefore include:

X(t) = {
  spectral_power,
  phase,
  directional_flow,
  connectivity_state,
  criticality,
  non_equilibrium_state,
  anatomy,
  behavior
}

A perturbation becomes:

U(t) = {
  modality,
  target,
  timing,
  waveform,
  phase_alignment,
  amplitude,
  duration
}

and transition:

X(t+dt) = F(X(t), U(t)).

## 5. Transition windows

The key hypothesis is:

P(desired transition | same U) changes with X(t).

Therefore a fixed intervention schedule throws away information.

A state-aware system would instead estimate **transition windows**.

These are moments when the current network state makes a desired switch more probable.

## 6. Why the ~200 ms observation is important

If the relevant global modes change on a sub-second timescale, then:
- minute-scale or session-average biomarkers may hide actionable dynamics;
- a parameter tuned at one moment may be mistimed a fraction of a second later;
- closed-loop latency becomes a scientific variable;
- stimulation timing may matter independently of stimulation frequency.

## 7. Falsification

The phase-gated hypothesis would weaken if:
- RPA dynamics fail independent replication;
- the wakefulness/anesthesia association does not generalize;
- phase/network-state knowledge fails to improve prospective stimulation prediction;
- phase-timed stimulation performs no better than timing-matched random controls.

## 8. Claim boundary

Supported:
- sub-second directional-flow alternations are reported in human EEG and differ with conscious state;
- simultaneous EEG-fMRI links modes to distinct functional systems;
- computational whole-brain stimulation responses depend on phase and network state.

Hypothesis:
- phase/network-state-targeted stimulation can improve consciousness-restoration efficacy.

Not established:
- 200 ms is a universal "frequency of consciousness";
- these transitions alone are sufficient for subjective experience;
- phase-aware stimulation is currently an established treatment.
