# Semantic Information, Viability, and the AGI Grounding Bridge

## 1. The game-changing connection

Kolchinsky and Wolpert formalized a distinction that maps directly onto the original layered-systems lesson.

Shannon information measures statistical dependence.

It does not tell us which correlations **matter** to the system.

Their proposal defines semantic information as information about the environment that is causally necessary for the system to maintain its existence/viability.

That can be tested counterfactually:

1. measure the system with its actual information channel;
2. scramble or remove the system-environment correlation;
3. hold the remaining dynamics appropriately fixed;
4. measure the change in viability.

If destroying a correlation does not affect viability, the information may be statistically present but not semantically useful under the chosen viability definition.

## 2. Why this matches the original lesson

The initial image lesson was:

**Do not isolate a symbol from the relational structure that gives it function.**

The physical-agent analogue is:

**Do not isolate information from the causal system in which it has consequences.**

Thus:

correlation != meaning

just as:

shape resemblance != historical transmission.

Meaning resides partly in **what the information enables the system to do**.

## 3. Thermodynamic bridge

Autonomous living agents are far-from-equilibrium systems.

They must continually exchange energy/matter with their surroundings to preserve an organized state.

The 2026 non-equilibrium consciousness result adds an important but separate observation: consciousness-related states are associated with stronger non-equilibrium dynamical signatures than anesthesia/unresponsive conditions in the tested datasets.

These lines of work should not be collapsed into one theorem.

Together they motivate a testable systems model:

environment information
-> internal organized dynamics
-> action
-> altered energy/matter flow
-> maintained viability
-> feedback.

## 4. Empowerment and semantic information are complementary

Empowerment asks:

**How much control does the agent have over future states?**

Semantic information asks:

**Which information about the environment is causally necessary for maintaining viability?**

A general agent needs both.

High empowerment with poor semantic grounding can be dangerous:
- it can control many futures;
- while failing to know which observations matter.

High semantic information with zero empowerment can describe a system that knows relevant facts but cannot act.

The useful regime is:

bounded semantic grounding + calibrated empowerment + governance.

## 5. The AGI relevance

Current large language models are exceptionally strong statistical models of symbolic relationships.

But general agency requires more than predicting symbol sequences.

A robust agent must learn:
- which observations are causally relevant;
- which uncertainty should trigger information-seeking;
- which actions change the world;
- which state changes threaten or satisfy the authorized task;
- which evidence supports current beliefs;
- which changes invalidate those beliefs.

This is where the original lesson becomes a stepping stone toward more general intelligence.

It replaces:

"recognize patterns"

with:

"model relationships, intervene, observe consequences, preserve viability constraints, and update causal beliefs."

## 6. Important safety distinction

A biological organism has evolved self-maintenance drives.

An artificial system should not automatically receive unconstrained self-preservation as a goal.

Worldshepherd therefore defines a bounded analogue:

### Governed viability envelope

The states the system is authorized to maintain, for example:
- evidence integrity;
- user-defined mission constraints;
- resource ceilings;
- legal/safety constraints;
- valid authorization;
- calibration thresholds;
- secure operating state.

The system must remain shutdown-able and subordinate to human authority.

## 7. Governed Semantic Information

For an information channel Z and bounded viability measure V:

GSI(Z) = V(actual information) - V(counterfactually scrambled Z)

Interpretation:

How much does this information contribute to maintaining the authorized operating envelope?

Examples:

### Provenance
Scramble source-version data.

If stale conclusions are no longer invalidated, provenance carries high GSI for epistemic viability.

### Uncertainty
Remove uncertainty estimates.

If the agent begins acting confidently on insufficient evidence, uncertainty carries high GSI.

### API version
Scramble API/schema version.

If software actions fail or become unsafe, version information carries GSI.

### Robot state
Remove obstacle/depth information.

If the robot leaves its safe operating envelope, that sensor information carries GSI.

## 8. Counterfactual requirement

Correlation is insufficient.

For every candidate information variable:
- remove it;
- scramble it;
- delay it;
- substitute a matched distractor;
- measure impact.

This directly implements the user's lesson:

**the function of information is revealed by its relationships and effects, not just its appearance.**

## 9. A candidate bounded-general-agency loop

observe
-> relational world model
-> semantic relevance estimate
-> uncertainty
-> epistemic action if needed
-> policy
-> authorized action
-> environmental consequence
-> feedback
-> model update
-> viability/evidence audit.

This is not a definition of consciousness or AGI.

It is a testable architecture for grounded, bounded agency.
