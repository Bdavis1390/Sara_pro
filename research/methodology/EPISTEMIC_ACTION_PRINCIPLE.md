# Epistemic Action Principle

## 1. Why passive reasoning is not enough

The Identifiability Ceiling shows that some questions cannot be resolved by collecting more of the same observations.

At that point a capable reasoner must ask:

**What should I observe or do next so that the possible outcomes discriminate among my remaining hypotheses?**

This is the transition from passive inference to experimental intelligence.

## 2. Expected information gain

Let H denote the current hypothesis variable.

Before action a, uncertainty is:

Entropy(H | D)

After taking a and observing outcome y:

Entropy(H | D, a, y)

Expected information gain is:

EIG(a)
=
Entropy(H | D)
-
E_y[Entropy(H | D,a,y)]

An action has high epistemic value when its possible outcomes sharply separate the live hypotheses.

## 3. Information gain is not enough

A medically dangerous experiment might be highly informative.

A destructive cybersecurity response might reveal whether a machine was compromised but destroy forensic evidence.

An intrusive intelligence collection method might carry legal/privacy costs.

Therefore Worldshepherd uses bounded epistemic utility:

U(a)
=
EIG(a)
- lambda_r Risk(a)
- lambda_c Cost(a)
- lambda_i Irreversibility(a)

subject to authorization.

## 4. Dual role of action

An action can have two distinct values.

### Instrumental value
Moves the world toward a desired task state.

### Epistemic value
Improves the world model.

Often one action has both.

Example:
A robot moves slightly around an object.
- instrumental effect: changes position;
- epistemic effect: resolves depth/occlusion ambiguity.

Example:
A scientist perturbs one gene.
- instrumental effect: changes cellular state;
- epistemic effect: distinguishes causal models.

Example:
A translator finds a new manuscript fragment.
- no physical task reward may be involved;
- but the new witness can collapse a reading equivalence class.

## 5. AGI relevance

A passive language model can answer from available context.

A general agent needs another capability:

**recognize when available evidence is insufficient, predict what new evidence candidate actions would produce, and choose the best safe discriminator.**

That is a qualitatively different competence.

It requires:
- uncertainty;
- explicit alternatives;
- forward models;
- action consequences;
- experiment design;
- cost/risk awareness;
- governance;
- belief update.

## 6. Connection to consciousness work

The consciousness path itself demonstrates this method.

Behavioral nonresponse generated multiple live explanations.

Task-based EEG/fMRI supplied discriminating evidence.

Network-targeted stimulation studies add causal perturbation.

Adversarial theory tests deliberately select predictions on which theories disagree.

Thus modern consciousness science is moving from:

observe and correlate

toward:

hypothesize, perturb, discriminate, revise.

## 7. Worldshepherd implementation doctrine

When uncertainty is materially decision-relevant:

1. enumerate live hypotheses;
2. identify observational equivalence;
3. generate candidate evidence actions;
4. predict outcomes under each hypothesis;
5. estimate information gain;
6. estimate cost/risk/irreversibility;
7. PRIME checks authorization;
8. take or recommend the safest high-value action;
9. capture result in ECHO;
10. update EBOM and claims;
11. repeat until decision threshold or irreducible uncertainty.

## 8. Strongest synthesis

The original lesson has now progressed:

surface feature
-> relationship
-> latent state
-> equivalence class
-> discriminating intervention
-> causal identification
-> revised world model.

That is a complete scientific reasoning loop.
