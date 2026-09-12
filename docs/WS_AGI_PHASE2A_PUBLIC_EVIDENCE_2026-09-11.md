# Worldshepherd AGI Phase 2A — Public Evidence Matrix

Date: 2026-09-11

## Claims boundary

This document records public evidence relevant to the Worldshepherd AGI acceptance gate. It does not claim that AGI has been reached. Vendor-reported results remain vendor-reported unless an independent evaluator reproduced them under documented conditions.

## Novel generalization

ARC Prize reports GPT-6 Astra on ARC-AGI-3 Semi-Private at:

- 62.7% with the provider-neutral Standard harness (max reasoning).
- 99.9% with the Provider Adapter harness (high reasoning).
- Fewer actions than the tested median-human baseline on 96% of levels in the Provider Adapter evaluation.

ARC Prize explicitly states that saturating ARC-AGI-3 is not proof of AGI and describes the benchmark as bounded, deterministic, and not representative of open-ended real-world complexity.

Sources:
- https://arcprize.org/blog/astra
- https://arcprize.org/results/openai-gpt-6-astra
- https://arcprize.org/policy

Worldshepherd gate effect: Standard and Provider Adapter results remain separate. The Standard result is below the current candidate threshold. Provider-specific context management cannot substitute for the Standard-harness requirement.

## Computer use and professional work

OpenAI's GPT-6 Astra release page reports:

- Agents' Last Exam: 59.3%.
- OSWorld 2.0 offline subset: 72.6%.
- ScreenSpot-Pro: 92.7%.
- AutomationBench: 41.4%.
- BenchCAD: 95.9%.
- BrowseComp: 91.5%.
- Internal Design Tasks: 50.0%.
- Internal Data Science Tasks: 40.9%.
- Terminal-Bench 4.0: 57.9%.
- GPQA Diamond: 96.0%.

Source:
- https://openai.com/index/gpt-6-astra/

These results are strong but heterogeneous. They are not a substitute for the Worldshepherd protected economic-work battery because they use different task definitions, grading methods, baselines, and in some cases internal vendor-controlled evaluations. They are recorded as capability evidence, not as proof that the economic-breadth gate has passed.

## Example end-to-end professional workflow evidence

OpenAI reports that Legora used Astra to review 41 documents in a financial-statement tie-out workflow, finding 4 of 4 planted errors and improving 40% against Legora's benchmark while keeping final judgment with legal professionals.

Source:
- https://openai.com/index/legora-financial-statement-review-with-astra/

Claim state: VENDOR_REPORTED / CUSTOMER_CASE_STUDY. Useful for task-design inspiration, not sufficient for AGI gate promotion.

## Long-horizon autonomy

METR's public time-horizon page was last updated 2026-05-08. It states that its Time Horizon 1.1 suite is primarily software engineering, machine learning, and security-related work and that measurements above 16 hours are unreliable with the current task suite.

METR's February-March 2026 frontier-risk report gives a public-frontier reference of approximately 12 hours at 50% success and approximately 1.5 hours at 80% success, with wide uncertainty, while also warning about suite saturation at the frontier.

Sources:
- https://metr.org/time-horizons/
- https://metr.org/blog/2026-05-19-frontier-risk-report/

Worldshepherd gate effect: out-of-range extrapolations are retained for analysis but blocked from satisfying the gate unless a suitable measurement suite supports them.

## Current Worldshepherd evidence conclusion

Current public evidence supports a large frontier-model capability jump but does not establish the complete Worldshepherd AGI acceptance package. The largest unresolved evidence gaps are:

1. Provider-neutral novel generalization at the configured candidate threshold.
2. Broad long-horizon autonomy on suites capable of reliably measuring beyond 16 hours.
3. A protected, contamination-resistant 10-domain/20-domain professional-work battery against skilled-human baselines.
4. Held-out cross-domain transfer.
5. End-to-end workflow reliability with independent final-state verification.
6. Self-correction and low false-completion rates measured on protected trials.
7. Multiple independent replications across the complete gate rather than isolated benchmarks.

Current classification remains `BELOW_AGI` until all required evidence-gated metrics pass.
