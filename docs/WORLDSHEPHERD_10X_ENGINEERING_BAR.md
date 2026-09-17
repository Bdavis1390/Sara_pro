# WORLDSHEPHERD 10X ENGINEERING BAR

Status: **STANDING ENGINEERING TARGET — CLAIMS CONTROLLED**

“10x” is valid only when a baseline, metric, unit, workload, and measurement procedure are fixed before the candidate result is known.

It is not a universal statement that Worldshepherd is ten times better or ten times more secure than every competing system.

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

When the baseline is zero, ratio language is undefined. The control becomes zero-tolerance non-regression.

## Mandatory evidence fields

Every 10x claim must retain:

1. baseline artifact/version/commit;
2. candidate artifact/version/commit;
3. exact metric and unit;
4. fixed workload/adversarial corpus;
5. measurement procedure;
6. environment/dependencies;
7. raw result counts;
8. failures and exclusions;
9. uncertainty/sampling limitations where relevant;
10. whether execution was Worldshepherd-controlled or independently reproduced.

## Independent dimensions

The target may be applied separately to:

- residual attack paths;
- adversarial false-negative rate;
- unauthorized state mutations;
- undetected evidence tampering;
- duplicate logical actions;
- recovery time;
- recovery-point loss;
- evidence verification time;
- operator steps;
- clean-room setup effort;
- conformance defects;
- externally reproduced failure rate.

A pass in one dimension does not transfer to another.

## Competitive comparison rule

Competitor comparisons require the same workload, equivalent configuration opportunity, and equivalent evidence standard.

Missing public documentation is `not_evidenced`, not proof that a competitor lacks a feature.

Worldshepherd-authored benchmarks remain internal evidence until methodology and execution are independently reviewable.

## Public wording

Prefer:

> “Reduced the declared residual attack-path count from 5 to 0 on the fixed G4 test set.”

or:

> “Reduced G6 unsigned-authenticity residual classes from 4 to 0 on the fixed witness-verification test set.”

Do not infer from those results alone:

> “Worldshepherd is 10x more secure than every competitor.”

## Current ladder

- G4 — application authority binding.
- G5 — fingerprint-key epoch provenance.
- G6 — signed ECHO witness verification.
- G7 — signer/secret custody and rollback resistance.
- G8 — quantified adversarial corpus and false-negative budget.
- G9 — measured recovery RTO/RPO and evidence reconstruction.
- G10 — independent external replication.

The bar advances through retained measurements, not adjectives.
