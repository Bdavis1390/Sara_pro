# BAROS Closed-Loop Biological Operating Doctrine

Status: IMPLEMENTED AS BOUNDED RESEARCH CONTROL LOGIC
Clinical use: PROHIBITED

## The defining BAROS operating model

BAROS is not intended to behave like a static one-pass treatment-plan optimizer.

Its defining research loop is:

measure -> qualify -> re-optimize/propose -> independently recalculate -> validate -> human review -> continue/adapt

The crucial property is that a new biological or anatomical measurement does not automatically become a new treatment plan. BAROS first asks whether the measurement is sufficiently trustworthy, identifiable, geometrically coherent, in-distribution, and within the uncertainty limits locked for the intended use.

If that qualification fails, the correct BAROS behavior is refusal to adapt.

The bounded control states are:

- NO_ADAPTATION — no predeclared trigger has fired; preserve the last governed plan identity;
- PROPOSE_REOPTIMIZATION — a trigger fired and the measured state qualified; BAROS may generate a research candidate but the prior plan remains authoritative;
- HOLD_LAST_VALID — a trigger fired but the new state is not qualified; preserve the last valid plan;
- FALLBACK_STANDARD — the state is not qualified and no last-valid adaptive plan exists; preserve the declared standard plan.

No state grants patient-care authority.

## Biological state

The current bounded state representation makes the intended closed-loop variables explicit:

- voxelwise alpha;
- voxelwise beta;
- hypoxia index;
- resistance index;
- uncertainty;
- anatomy change;
- motion;
- measurement quality;
- geometry qualification;
- model-identifiability status;
- out-of-distribution status.

These are a research state schema, not a claim that every listed variable is currently measurable, clinically valid, or suitable for treatment adaptation.

## Trigger-governed adaptation

Adaptation is event-driven rather than automatic at every phase.

Current bounded trigger families include:

- change in hypoxia state;
- change in resistance state;
- change in uncertainty;
- anatomical change;
- motion;
- explicit authorized/manual force.

Thresholds belong to the locked intended-use configuration. They must not be silently learned or changed during a validation campaign.

## Qualification before optimization

A trigger is necessary but not sufficient.

The measured state is rejected for adaptation when any locked qualification condition fails, including:

- geometry is not qualified;
- model state is not identifiable;
- the observation is out of distribution;
- measurement quality is below threshold;
- uncertainty exceeds the permitted bound.

This separates detection of change from permission to adapt.

## Phase-coupled optimization

BAROS was conceived as spatially and temporally coordinated, not as a collection of independent per-fraction optimizations.

The bounded phase-coupling utility therefore accepts caller-supplied per-phase loss values and adds two explicit research penalties:

1. uncertainty penalty;
2. temporal control-discontinuity penalty.

For phase losses L_k, uncertainties q_k, and control vectors u_k, the bounded score is:

J = sum_k L_k + lambda_u sum_k q_k + lambda_t sum_(k>0) ||u_k - u_(k-1)||^2

This is not presented as a clinically validated objective. It encodes the architectural requirement that BAROS account for uncertainty and temporal continuity rather than optimizing each phase as if neighboring phases were unrelated.

## Authority separation

Even after PROPOSE_REOPTIMIZATION, BAROS does not authorize use of the candidate.

The required sequence remains:

1. generate bounded BAROS candidate;
2. independently recalculate through the locked TPS or approved research dose engine;
3. run protocol-defined dosimetric/deliverability checks;
4. obtain qualified human review/authorization;
5. preserve the last-valid or standard plan until all required external gates pass.

This authority separation is fundamental to BAROS, not a temporary implementation limitation.

## Degraded-mode behavior

The intended controller is deliberately asymmetric:

- good evidence can permit a proposal;
- weak evidence cannot force adaptation;
- conflicting evidence is quarantined;
- failure preserves or falls back to a known governed state.

This is the BAROS version of graceful degradation.

## Why this matters scientifically

Biological adaptation is uniquely vulnerable to false precision. A numerical optimizer can always return a number even when the underlying biological state is uncertain, non-identifiable, moving, or poorly observed.

BAROS therefore treats uncertainty, observability, identifiability, geometry, provenance, and human authority as control variables and gates, not after-the-fact documentation.

## External validation implications

A partner study should test not just plan quality but whether the closed loop behaves correctly:

- trigger sensitivity/specificity;
- false adaptation rate;
- missed adaptation rate;
- correct refusal rate;
- incorrect refusal rate;
- time from observation to qualified proposal;
- frequency and cause of hold-last-valid;
- frequency and cause of standard-plan fallback;
- discordance between BAROS state qualification and expert adjudication;
- stability of phase-coupled control;
- dependence on biological-model uncertainty;
- effect of stale, noisy, inconsistent, or contradictory observations.

The clinical scientific question is therefore broader than "does the optimizer produce a better plan?" It is also "does the adaptive controller know when it has enough evidence to propose change, and when it should refuse?"
