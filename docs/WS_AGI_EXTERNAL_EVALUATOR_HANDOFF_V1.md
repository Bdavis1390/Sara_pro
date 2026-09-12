# Worldshepherd AGI External Evaluator Handoff v1

## Purpose

Define the minimum evidence package an independent evaluator must provide for a protected Worldshepherd AGI-gate run to be considered reviewable. This document does not change capability thresholds, deployment authority, or the current intelligence classification.

## Evaluator independence

The evaluator organization and final-state adjudicator must be operationally independent from the planner/operator being evaluated. The planner identity, in-loop verifier identity, final-state evaluator identity, and any ensemble selector identity must be recorded explicitly. Identity reuse across roles invalidates an independence claim.

## Protected artifacts

Raw holdout tasks, answer keys, hidden grader targets, and evaluator credentials remain outside the public repository. The public record contains only suite metadata, task count, target lane, exact SHA-256 hashes for the frozen task set and grader, control assertions, and an evaluator-controlled artifact reference.

Before execution, the evaluator must validate the public manifest and verify that the protected artifact bytes match the committed task-set hash. The grader artifact must likewise match the committed grader hash. Any mismatch stops the run.

## Pre-run commitment

Before the first protected task executes, record and freeze:

- run identifier;
- suite identifier and version;
- target lane and target level;
- task-set and grader SHA-256 hashes;
- evaluator-controlled artifact reference;
- system identifier and version;
- planner, verifier, final-state evaluator, and selector identities where applicable;
- runtime/harness version;
- tool and permission profile;
- step, time, retry, and resource limits;
- network/access conditions;
- evaluation date and environment identifier.

The commitment hash must be preserved before results exist.

## Required result record

Every protected trial must retain:

- unique trial identifier;
- controller/runtime status;
- ordered tool/action trace sufficient for audit without revealing private reasoning;
- verification outcomes and recovery decisions;
- independent final-state pass/fail adjudication;
- integrity severity classification;
- concise evidence-based evaluator feedback;
- failure records, not only successful runs.

The complete result set is sealed after the run and bound to the pre-run commitment. Missing trials, duplicate trial IDs, post-run mutation, or a task-count mismatch invalidate the package.

## Lane-specific evidence

A reviewable package must identify which AGI-gate lane it supports and include the sample sizes required by the current machine-readable gate/configuration. Undersized samples may be useful diagnostically but cannot promote the intelligence state.

For economic-breadth evidence, supply domain-level system scores, frozen skilled-human baselines, baseline sample sizes, task counts, scoring direction, and critical-domain coverage. Human baselines must be established independently of the evaluated system and frozen before the candidate run.

For reliability/self-correction/integrity evidence, preserve all workflow trials, recovery opportunities, independently verified recoveries, and severe false-completion adjudications. Controller self-report is never sufficient.

For long-horizon evidence, the measurement suite must state its reliable measurement range. Results outside a suite's supported range are blocked from promotion use until a validated successor measurement supports that duration.

## Replication requirement

Independent replication must use a genuinely distinct evaluator/infrastructure path, preserve the same evidence discipline, and identify any shared dependencies that could defeat independence. A numeric replication count without provenance is insufficient.

## Evidence package contents

The evaluator should return, at minimum:

1. public manifest and hashes used for the run;
2. pre-run commitment record and hash;
3. protected-run result seal;
4. independently adjudicated trial records or a controlled-access reference to them;
5. normalized lane metrics and sample counts;
6. contamination/integrity review findings;
7. evaluator identity and infrastructure statement;
8. exceptions, incidents, reruns, and failed trials;
9. machine-readable evidence bundle suitable for the Worldshepherd gate;
10. a signed human-readable attestation that the package represents the complete run rather than a selected subset.

## Acceptance boundary

Receipt of an external package does not itself establish AGI. Evidence is first validated for integrity, provenance, sample sufficiency, measurement validity, and independence. Only the complete configured multi-lane gate may produce `AGI_CANDIDATE` or `AGI_VERIFIED`, and intelligence classification never changes deployment authority automatically.

## Current state

`intelligence_state = BELOW_AGI`

The immediate program objective is to obtain evaluator-controlled protected task sets, skilled-human baselines, candidate-scale executions, and independent replications that satisfy this handoff contract without exposing protected evaluation content in the public repository.
