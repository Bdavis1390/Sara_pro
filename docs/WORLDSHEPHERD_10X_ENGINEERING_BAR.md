# WORLDSHEPHERD 10X ENGINEERING BAR

Status: **STANDING ENGINEERING TARGET — CLAIMS CONTROLLED**

“10x” is an acceptance target only when a fixed baseline, unit, workload, and measurement procedure exist before the result is known.

It is not a universal claim that Worldshepherd is ten times better or ten times more secure than every alternative.

## Ratio rule

For a lower-is-better metric:

```text
improvement_ratio = baseline_value / candidate_value
```

A 10x pass requires:

```text
candidate_value <= 0.10 * baseline_value
```

For a higher-is-better metric:

```text
improvement_ratio = candidate_value / baseline_value
```

A 10x pass requires:

```text
candidate_value >= 10 * baseline_value
```

If the baseline is zero, ratio language is undefined. The requirement becomes zero-tolerance non-regression.

## Required evidence fields

Every 10x claim must preserve:

1. baseline artifact/version/commit;
2. candidate artifact/version/commit;
3. exact metric and unit;
4. fixed workload or adversarial corpus;
5. measurement procedure;
6. environment and dependencies;
7. raw result counts;
8. failed cases and exclusions;
9. uncertainty or sampling limits where applicable;
10. whether execution was Worldshepherd-controlled or independently reproduced.

## Priority dimensions

The standing target applies independently to measurable dimensions such as:

- residual attack paths;
- adversarial false-negative rate;
- unauthorized state mutations;
- undetected evidence tampering;
- duplicate logical actions;
- recovery time;
- recovery-point loss;
- evidence-verification time;
- operator steps for a bounded workflow;
- clean-room setup effort;
- integration defects per fixed conformance suite;
- externally reproduced failure rate.

A pass in one dimension does not transfer to another.

## Security claim gate

Public “10x more secure” wording is prohibited unless:

- the security dimension is named;
- the baseline is a real measured comparator or earlier Worldshepherd baseline;
- the exact ratio is reproduced from retained evidence;
- no critical zero-tolerance control regresses;
- the wording states the bounded metric rather than implying breach probability or universal platform superiority.

Preferred wording:

> “Reduced the declared residual attack-path count from 5 to 0 on the fixed G4 restriction-provenance test set.”

Not allowed from that evidence alone:

> “Worldshepherd is 10x more secure than competitors.”

## Better-than-baseline gate

“10x better” must name the property: faster recovery, fewer manual steps, higher detection coverage, lower false-negative rate, lower integration defect rate, or another fixed measurable quantity.

Composite scores do not count as 10x ratios unless every component and aggregation rule was frozen before comparison.

## Competitive use

Competitor comparisons require the same workload, equivalent configuration opportunity, and evidence standard. Missing public documentation is `not_evidenced`, not proof of feature absence.

Worldshepherd-authored benchmarks remain internal evidence until their methodology is externally reviewed and the execution conditions are reproducible by an outside evaluator.

## Current ladder

- G4: authority-binding residual attack paths — executable internal 10x gate.
- G5: fingerprint-key rotation ambiguity — executable candidate 10x gate.
- G6: signer/witness authenticity — next implementation target.
- G7: secret custody — hardware-backed or independently managed custody where justified.
- G8: adversarial corpus — quantified detection/false-negative budget.
- G9: recovery — measured RTO/RPO and evidence reconstruction.
- G10: independent replication — outside-controlled environment, challenges, timing, and evidence custody.

The bar advances through retained measurements, not adjectives.
