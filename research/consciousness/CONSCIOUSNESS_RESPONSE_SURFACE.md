# Consciousness Response Surface

## Core result

The newest evidence argues against a one-dimensional consciousness-control model.

A naive model is:

C = f(total activation)

or:

C = f(one frequency).

The data increasingly require:

C_next = F(
  C_current,
  anatomy,
  pathology,
  target,
  stimulation modality,
  field geometry,
  carrier frequency,
  envelope/burst structure,
  amplitude,
  duration,
  phase,
  network response,
  prior treatment history
)

This is a **response surface** rather than a scalar dose-response curve.

## The paradoxical-reset clue

The Monti et al. 2026 preprint is particularly informative.

Behavioral responsiveness improved after thalamic focused ultrasound while:
- glucose metabolism decreased in thalamus and widespread cortex;
- EEG became slower by the selected delta/beta metric;
- stronger frontal slowing predicted larger behavioral gains.

That directly contradicts a simplistic rule:

more energy / faster activity -> more consciousness.

It is compatible with a different mechanism:

**a perturbation may improve the system by knocking it out of a pathological attractor and allowing reorganization.**

This is a hypothesis, not a proven mechanism.

## Dynamical interpretation

Let x(t) be the latent brain-network state.

Let u(t) be the intervention.

Then:

dx/dt = F(x, u, anatomy, pathology)

and observable consciousness-related behavior is:

y(t) = H(x).

A stimulation input can move the state:

x_0 -> x_1

even if some gross energy observable decreases.

What matters is whether x_1 lands closer to a viable conscious-network regime.

## Attractor formulation

Pathological unconsciousness may involve stable or metastable dynamical regimes.

The therapeutic goal is not necessarily:

maximize activity.

It may be:

**apply the smallest safe perturbation that moves the system across a basin boundary into a more adaptive attractor.**

Potential mechanisms:
- reset;
- disinhibition;
- network decoupling followed by reintegration;
- thalamocortical gating changes;
- altered basal-ganglia/thalamic control;
- frequency-specific recruitment.

## Frequency-specific evidence

Simultaneous EEG-fNIRS during multifrequency SCS shows that 5 Hz and 70 Hz can produce different neurovascular/network signatures.

That means frequency is not merely a magnitude label.

It selects different dynamical pathways.

## Time matters

Longitudinal SCS evidence further shows that early and intermediate network changes can differ in their relationship to later recovery.

Therefore the response surface has memory:

x(t+1) = F(x(t), u(t), history).

A static one-shot model is inadequate.

## Personalized closed-loop implication

A future controller should estimate:

1. current state;
2. likely controllable directions;
3. safe perturbation set;
4. immediate response;
5. longer-horizon trend;
6. uncertainty.

Then choose the next perturbation.

Conceptually:

u* = argmax_u E[
  clinical_gain
  - safety_cost
  - uncertainty_penalty
  | current_state
]

subject to clinician authorization and device constraints.

## Relation to the user's original lesson

The user's original "alter our frequencies -> alter the world" insight becomes physically precise here:

**altering a dynamical variable changes a coupled system only through the full relational structure of the system.**

The effect of frequency depends on:
- what is oscillating;
- where;
- with what phase/amplitude;
- through which pathway;
- in what baseline state;
- with what feedback.

## AGI analogy

The same control principle matters for artificial agents.

A general agent should not apply a fixed action because it was globally successful.

It should model:

state -> action -> transition -> new state

and learn a response surface.

That is the difference between:
- rule execution;
- state-aware causal control.

## Safety boundary

This file is research architecture only.

It must not be used to generate unsupervised human neurostimulation protocols.
