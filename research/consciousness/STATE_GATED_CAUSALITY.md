# State-Gated Causality

## 1. The important shift

A repeated intervention can generate variable outcomes even when nominal parameters are identical.

The default interpretation is often:

response = intervention + noise.

The 2026 Rabuffo et al. result supports a stronger model:

response = F(intervention, hidden_pre_state) + residual_noise.

This distinction matters because hidden-state variability is potentially measurable and controllable.

## 2. Large-scale evidence

Rabuffo et al. used more than 10,000 single-pulse intracranial stimulations across approximately 320 sessions in 36 epilepsy patients with simultaneous SEEG and high-density EEG.

Pre-stimulus metrics included:
- signal dynamics;
- synchronization;
- functional connectivity;
- complexity.

Whole-brain state measures outperformed purely local ones.

Mean within-session explained variance was:
- 17.6% in SEEG;
- 7.1% in hd-EEG.

Some sessions reached:
- 85.0% SEEG;
- 71.8% hd-EEG.

Most importantly, the authors report prospective closed-loop state selection that reduced response variability.

## 3. Why this is stronger than correlation

Retrospective prediction alone says:

state predicts outcome.

Prospective state-conditioned triggering asks:

if we wait for/select a favorable state before stimulating, does the response distribution change?

That is a control intervention on the timing policy.

So the experiment moves closer to:

state -> gate stimulation -> altered response statistics.

## 4. Effective-intervention identity

Worldshepherd should treat an intervention as:

I_eff = {
  physical_stimulus,
  anatomical_target,
  pre_stimulus_state,
  timing,
  phase,
  control_policy
}

Two trials with identical pulse parameters are not necessarily equivalent interventions if pre-state differs.

## 5. Adaptive intensity convergence

Heiss et al. 2026 independently implemented real-time EEG-dependent TMS intensity adaptation.

They combined:
- 24 Hz phase targeting;
- rising/falling oscillatory flank;
- motor-cortex oscillatory power;
- intensity adaptation between 100% and 120% resting motor threshold.

The largest reported MEP increase was about 31% in the rising-flank inverse-adaptation condition.

This supports the feasibility of online state-contingent control.

## 6. Consciousness program consequence

A consciousness-restoration experiment that does not model pre-state may mix together:
- responsive windows;
- refractory windows;
- different directional-flow modes;
- different network-connectivity states.

That can inflate variance and hide real causal effects.

The next-generation design should therefore compare:

M0: fixed protocol
M1: fixed protocol + state measurement
M2: state-gated timing
M3: state-gated timing + adaptive amplitude
M4: full state/phase/network closed loop

## 7. The deeper systems principle

Variability is not synonymous with randomness.

Before labeling residual behavior stochastic:

1. increase state observability;
2. model latent variables;
3. test prospective gating;
4. measure variance reduction;
5. only then estimate irreducible noise.

This is useful far beyond neuroscience.

## 8. AGI connection

A general agent should distinguish:

epistemic uncertainty:
"I do not know the state"

from:

aleatoric uncertainty:
"the process is intrinsically stochastic."

If measuring an additional state variable makes the outcome predictable, the uncertainty was epistemic.

That difference directly affects:
- action selection;
- exploration;
- confidence;
- safety;
- causal learning.

Worldshepherd should therefore include **latent-state search before stochasticity attribution** as a general reasoning rule.
