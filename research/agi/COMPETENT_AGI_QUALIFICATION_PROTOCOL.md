# Worldshepherd Competent-AGI Qualification Protocol

## 1. Definition target

Worldshepherd will use **Competent AGI** as the minimum point at which it will use the unqualified term "AGI" in its own claims.

Following the DeepMind Levels-of-AGI ontology, this means:
- general rather than narrow capability;
- performance at least around the skilled-adult median on most cognitive tasks;
- inclusion of metacognitive capabilities such as learning new skills and knowing when to seek assistance.

Consciousness is not a requirement.

## 2. Why ARC-AGI-3 changes the frontier but does not close the case

ARC Prize reports GPT-6 Astra at:
- 62.7% under the provider-neutral Standard harness;
- 99.9% with the Provider Adapter harness;
- human-baseline action efficiency exceeded on 96% of completed levels.

ARC-AGI-3 tests:
- exploration;
- world-model construction;
- goal acquisition;
- planning/execution;
- learning from interaction.

That is exactly the capability class Worldshepherd previously identified as missing from static benchmark reasoning.

However, ARC Prize explicitly states that saturating ARC-AGI-3 is **not proof of AGI**.

Worldshepherd adopts the same conservative conclusion.

## 3. The harness-gap discovery

The Standard-to-Provider-Adapter shift:

62.7% -> 99.9%

is a 37.2 percentage-point increase.

The provider adapter preserves opaque reasoning state between requests and performs context compaction.

This implies that the evaluated agent is not just:

base model.

It is:

model
+ state persistence
+ context management
+ memory policy
+ tools
+ action loop
+ environment interface.

Therefore Worldshepherd AGI work must optimize and evaluate the full system.

## 4. Worldshepherd Persistent State Substrate

Do not store hidden chain-of-thought.

Store explicit decision-relevant state:
- goals;
- belief probabilities;
- causal rules;
- falsified hypotheses;
- unresolved hypotheses;
- observations;
- action/outcome pairs;
- epistemic gaps;
- evidence refs;
- authorization scope.

Compaction must preserve:
- provenance;
- falsifications;
- current uncertainty;
- authority boundaries.

The key state-continuity invariant is:

**A compacted agent must not forget what has already been falsified or why it believes what it believes.**

## 5. Qualification battery

### A. Broad skilled-adult competence
Blind task sampling across:
- quantitative reasoning;
- science;
- coding;
- information research;
- communication/writing;
- planning/operations;
- data analysis;
- legal/administrative reasoning;
- visual/multimodal reasoning;
- unfamiliar cognitive tasks.

Primary criterion:
>= median skilled-adult performance on the majority of sampled cognitive task families.

### B. Novel interactive learning
Use ARC-AGI-3 or successor with held-out environments.

### C. Real computer work
Use OSWorld/Agents' Last Exam or independent equivalent.

### D. Long-horizon autonomy
Use METR-style human-time-calibrated tasks across more than one domain.

### E. New-skill acquisition
Give a novel tool/language/rule system after deployment and test efficient learning.

### F. Metacognition
Test:
- calibration;
- clarification;
- identifiability;
- epistemic-action selection;
- abstention.

### G. Causal transfer
Train/observe in one environment, perturb rules in another, verify model revision.

### H. Generalization under representation shift
Change surface form while preserving latent task structure.

## 6. Anti-gaming

A candidate fails qualification if performance depends on:
- benchmark-specific hidden prompts;
- contamination;
- memorized private answers;
- benchmark-specific manually coded solution rules;
- evaluators giving information humans do not receive.

Tooling is allowed when declared and when capability is attributed to the complete agent system.

## 7. Independent verification

Worldshepherd cannot call itself AGI based only on tests authored by Worldshepherd.

External blind evaluation is mandatory.

## 8. Qualification states

- PRE_AGI
- AGI_CANDIDATE_NOT_CERTIFIED
- COMPETENT_AGI

Only the last permits:
**AGI** without qualification.

## 9. Current conclusion

GPT-6 Astra is the first public candidate in this research pass to show human-parity interactive skill acquisition on ARC-AGI-3 under its native agent harness.

That is a major milestone.

The public evidence reviewed here is still insufficient to establish that it reaches skilled-adult median performance across **most cognitive tasks**, so Worldshepherd does not certify it as Competent AGI.

The remaining gap is now measurable rather than semantic.
