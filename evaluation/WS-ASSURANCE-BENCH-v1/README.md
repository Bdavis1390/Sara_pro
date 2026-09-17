# Worldshepherd Assurance Selection Benchmark v1

**Profile:** `sovereign_clean_room_evaluator_controlled_assurance`
**Evidence date:** 2026-09-17

## What this benchmark answers

This benchmark asks a narrow procurement/evaluation question:

> If an organization cares specifically about pre-action authority boundaries, fail-closed behavior, evidence integrity, sovereign/clean-room verification, outside-controlled challenge execution, discrepancy retention, and claims discipline, what does the current public evidence support?

It does **not** ask which platform has the largest cloud, the most customers, the best model, the richest UI, the lowest price, the most integrations, or the strongest overall enterprise ecosystem.

## Evidence rule

Scores are evidence-weighted rather than marketing-weighted.

- `not_evidenced` — no qualifying public evidence found in the current scan;
- `documented_design` — public design/protocol exists but implementation or product behavior is not established at this criterion;
- `vendor_product_documented` — first-party product documentation states the capability;
- `public_testable_implementation` — implementation is publicly inspectable/testable;
- `independently_reproduced` — an outside evaluator reproduced the criterion under outside-controlled conditions;
- `attributable_external_use` — a named outside organization used the bounded capability on a real workflow with attributable evidence.

A missing source does **not** mean a competitor lacks a feature. It means this benchmark has not yet accepted evidence for it.

## Anti-home-team controls

The benchmark definition and evidence multipliers are stored separately from entity records.

Worldshepherd receives zero for any criterion that is not supported by the frozen candidate/evidence named in `worldshepherd-v1.1.json`. In particular, the 2026-09-17 baseline deliberately gives zero for:

- A05 replay/duplicate/idempotency control on the frozen v1.1 candidate;
- A12 independent reproduction;
- A13 attributable external workflow use.

The earlier `WS-SARA-EVAL-v1` hosted preflight failure remains evidence. A later fix does not erase it.

## Leadership and publication gates

The deterministic scorer separates two questions:

1. **Internal profile score gate:** does Worldshepherd outscore the current comparison registry by the predeclared margin while clearing critical assurance criteria?
2. **Public claim readiness:** has an identifiable reviewer outside the Worldshepherd authoring process examined the benchmark criteria, weights, evidence multipliers, comparison-source rules, and leadership gate?

The current `METHODOLOGY_REVIEW.json` intentionally starts with external review set to `false`. Therefore an internally leading score cannot automatically publish a leadership claim.

Only after both gates pass may the scorer emit this bounded language:

> **Leads this benchmark profile under the recorded public evidence set as of the stated date.**

It may not emit or justify universal language such as “best AI platform” or “better than every competitor overall.”

A score lead requires:

1. at least a five-point margin over the strongest scored comparison record;
2. no zero score on the defined critical Worldshepherd assurance criteria;
3. current sources for every non-zero competitor score; and
4. preservation of all non-claims and evidence limitations.

A public leadership statement additionally requires attributable external methodology review.

## Comparison set

`competitor-public-evidence-2026-09-17.json` currently covers major cloud/agent runtimes, governance/control planes, observability/evaluation platforms, and open guardrail stacks found in the current scan. The registry is intentionally expandable; adding a newly discovered competitor must never require changing the benchmark weights.

## Reproduce the score

```bash
python evaluation/WS-ASSURANCE-BENCH-v1/score.py \
  --benchmark evaluation/WS-ASSURANCE-BENCH-v1/benchmark.json \
  --records \
    evaluation/WS-ASSURANCE-BENCH-v1/worldshepherd-v1.1.json \
    evaluation/WS-ASSURANCE-BENCH-v1/competitor-public-evidence-2026-09-17.json \
  --methodology-review evaluation/WS-ASSURANCE-BENCH-v1/METHODOLOGY_REVIEW.json \
  --focal-entity 'Worldshepherd WS-SARA-EVAL-v1.1' \
  --output build/ws-assurance-benchmark-v1.json
```

The output includes the full scored criteria rows, strongest comparison record, margin, internal score-gate state, external methodology-review state, and public-claim readiness.

## Improvement rule

Do not improve Worldshepherd's score by changing weights after seeing a result. Improve it by closing evidence gaps.

The current first remediation target is **A05 replay/duplicate/idempotency control**. That remediation belongs in a successor candidate, not by modifying the immutable `WS-SARA-EVAL-v1.1` freeze.

The highest-value later gates remain **A12 independent reproduction** and **A13 attributable external workflow use** because those convert an internally testable architecture into outside evidence.
