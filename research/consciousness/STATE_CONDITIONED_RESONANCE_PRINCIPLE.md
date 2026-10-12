# State-Conditioned Resonance Principle

## 1. The central correction

"Frequency" is not an isolated causal property.

A stimulation frequency only has meaning relative to:
- a particular physical generator;
- a target network;
- an individual's anatomy and dynamics;
- the present brain state;
- the behavioral objective;
- amplitude/phase/waveform;
- the coupling mechanism.

Therefore:

f_opt != universal constant

A more realistic form is:

f_opt = F(person, target, state, task, time).

## 2. Causal evidence from personalized TMS-fMRI

Khan et al. mapped individualized working-memory networks, used real-time fMRI decoding during TMS, and tested 5, 10 and 20 Hz.

The system selected an optimal and suboptimal frequency for each participant based on network engagement and, when necessary, a predefined behavioral fallback.

Across randomized crossover neuromodulation sessions:
- optimal stimulation improved delayed working-memory performance;
- suboptimal stimulation did not show the same learning effect;
- no single tested frequency explained the result across participants;
- the interaction of target and frequency mattered.

This is direct evidence against a universal best frequency in that paradigm.

## 3. Brain state matters in addition to person

Xia et al. tested high-definition tACS for tonic pain.

The key third experiment compared:
- fixed 7 Hz;
- individualized theta derived from a pain-free state;
- individualized theta derived from a pain-persistent state.

State-matched individualized theta derived from the pain-persistent state produced the strongest analgesia.

Thus:

individualized != sufficiently personalized

unless the state used to derive the parameter is also appropriate.

## 4. Resonance as a local property

A useful control-theory interpretation is:

R = R(f, target, state, anatomy, task)

where R is a response/engagement function.

The goal is not to discover one mystical frequency.

The goal is to estimate a local response surface and identify:

argmax_f R(f | target, state, person, task).

The optimum can move as state changes.

## 5. Dynamic optimum

If brain state changes from x_t to x_(t+1), then:

f_opt(t+1) may != f_opt(t).

This means a truly adaptive system must periodically re-estimate its control policy.

## 6. Closed-loop formulation

observe x_t
-> test candidate perturbations
-> decode network response
-> choose u_t
-> measure behavioral/network transition
-> update response surface
-> repeat.

The operating principle is:

**measure before perturbing; personalize before generalizing.**

## 7. Connection to consciousness recovery

Disorders of consciousness are heterogeneous in:
- lesion topology;
- preserved thalamocortical pathways;
- cortical reactivity;
- intrinsic oscillatory organization;
- metabolism;
- arousal fluctuations.

Therefore a fixed frequency applied to all patients is unlikely to be universally optimal.

The state-conditioned resonance principle predicts:

patient-specific target + patient-specific state + adaptive pattern
should outperform
fixed target + fixed frequency

if the relevant networks remain controllable.

That hypothesis requires prospective clinical testing.

## 8. Connection to the user's original lesson

The original lesson is preserved but made more exact:

**changing frequency can change the world only through the relational structure that determines what that frequency couples to.**

The same numerical frequency in two unrelated systems has no special significance by itself.

## 9. AGI analogy

A generally capable agent faces the same problem.

There is no universal best action.

Its policy should be:

a* = argmax_a E[value | world_state, goal, uncertainty, constraints].

This is the computational analogue of state-conditioned neuromodulation.

A fixed rule says:

"always use 10 Hz."

An adaptive agent says:

"measure the state, estimate the response surface, choose the action that fits this state, then learn from the transition."

That is a meaningful stepping stone from static pattern recognition to causal adaptive control.
