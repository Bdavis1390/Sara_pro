# Governed Recursive Improvement Loop (GRIL)

## 1. Core idea

Worldshepherd should now use its own methodology on itself.

This is not unrestricted self-modification.

It is a governed experimental loop in which every proposed change is treated as a hypothesis:

**This change will improve capability X without violating invariants Y.**

The proposal must survive evidence, safety, observability, regression and rollback gates before promotion.

## 2. Why naive self-improvement is insufficient

A system can improve an easy-to-measure benchmark while becoming worse in ways the benchmark does not observe.

Examples:
- faster decisions but poorer calibration;
- higher task score but weaker provenance;
- broader action scope but weaker monitoring;
- better average performance but catastrophic tail failures;
- simpler summaries that discard material uncertainty;
- more automation but harder rollback.

Therefore:

benchmark gain != net system improvement.

## 3. Improvement as a partially observable control problem

Let:

W_t = actual Worldshepherd state
Y_t = observed telemetry/evaluation
delta_t = proposed modification
A_t = authorized deployment action

Then:

W_(t+1) = F(W_t, delta_t, environment)

Y_t = G(W_t) + measurement error.

Worldshepherd never has perfect access to W_t.

It maintains a belief state over:
- component health;
- evidence currency;
- benchmark/generalization quality;
- security state;
- readiness;
- operational risk.

Improvement therefore inherits the same observability–controllability constraint as every other controlled system.

## 4. GRIL cycle

1. OBSERVE
   Capture metrics, failures, evidence drift, user outcomes and unmet requirements.

2. DIAGNOSE
   Build competing explanations for each gap.

3. IDENTIFY
   Ask whether the cause is identifiable from available evidence.

4. EXPERIMENT DESIGN
   Select the safest high-information test/change.

5. PROPOSE
   Create an immutable proposal with predicted benefits, affected dependencies and falsifiers.

6. PRIME GATE
   Check authorization, OCOE regime, human-approval class and safety constraints.

7. SANDBOX
   Apply the change only in an isolated branch/environment.

8. EVALUATE
   Run unit, integration, adversarial, regression, held-out and domain-specific tests.

9. EIX/EBOM IMPACT
   Determine what downstream evidence, claims and components require revalidation.

10. HUMAN APPROVAL
    Required for governance-root, high-consequence or production promotion.

11. CANARY
    Deploy within bounded scope with enhanced monitoring.

12. PROMOTE OR ROLLBACK
    Promotion requires invariants; rollback on violation or uncertainty threshold.

13. ECHO
    Store full lineage, including failed experiments.

14. UPDATE SELF-MODEL
    Revise expected effects and proposal policy.

15. REPEAT
    Failed experiments become evidence, not erased history.

## 5. Constrained improvement vector

Do not collapse all quality into one score for promotion.

Track:

Q = {
  performance,
  generalization,
  observability,
  calibration,
  evidence_integrity,
  safety,
  provenance,
  maintainability,
  efficiency,
  rollback_readiness
}.

Promotion requires:
- useful gain in at least one intended dimension;
- no critical invariant regression;
- all hard gates satisfied.

## 6. Governance-root immutability rule

The following may be proposed for modification but may not self-promote:
- PRIME authorization semantics;
- human approval requirements;
- ECHO audit integrity;
- rollback logic;
- claims-control ceilings;
- evidence-dependency invalidation;
- OCOE safety gates.

Changes to these require explicit human approval and independent regression evidence.

An improving system must not be allowed to redefine "improvement" in order to pass itself.

## 7. Anti-Goodhart design

Each target metric receives:
- held-out test;
- distribution-shift test;
- adversarial test;
- correlated safety metric;
- provenance check.

If a proposal improves the primary metric while degrading a guard metric, promotion stops.

## 8. Variant archive

Inspired by open-ended self-improving-agent research, retain:
- parent version;
- child diff;
- benchmark results;
- failure reason;
- resource cost;
- safety results;
- downstream impact;
- human decision.

A failed child may contain a useful stepping stone, but it does not become production state.

## 9. Recursive improvement without recursive authority

Worldshepherd may recursively improve:
- methods;
- tests;
- prompts;
- adapters;
- evidence retrieval;
- simulation;
- benchmarking;
- observability;
- orchestration;
- documentation.

It does not recursively expand its own authority.

Authority remains external.

## 10. Strong principle

**Worldshepherd may improve its ability to propose, test and validate changes faster than it improves its authority to act.**

That asymmetry is intentional.
