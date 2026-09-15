# Worldshepherd Independent Replication Protocol v1

## Purpose

Define what counts as an independent replication for the Worldshepherd AGI gate. A replication count is accepted only when independence, provenance, and result integrity are evidenced; a self-reported number is insufficient.

## Independence criteria

A replication should use a materially distinct evaluator or evaluation organization and should disclose shared infrastructure, model-provider dependencies, task-generation sources, graders, orchestration code, and personnel that could create correlated failure or contamination.

The evaluated planner/operator must not serve as its own final-state adjudicator. Planner, in-loop verifier, final evaluator, and ensemble selector identities must be recorded and role collisions disclosed. A replication that reuses the same final adjudicator without a defensible independent-control boundary should not be counted as fully independent.

## Required replication package

Each replication provides:

- replication identifier and evaluator identity;
- system identifier/version under test;
- suite and benchmark versions;
- task-set and grader hashes;
- pre-run commitment and commitment hash;
- sealed result set or controlled-access reference;
- normalized lane metrics and sample counts;
- failed trials and integrity incidents;
- contamination review;
- infrastructure/dependency disclosure;
- rerun count and rerun policy;
- human adjudication record for material disputes;
- explicit statement of which prior evaluation artifacts, prompts, tools, or personnel were shared.

## Distinctness assessment

Replication evidence is classified as one of:

- `DISTINCT`: evaluator and material execution/adjudication path are independent enough to count toward the gate;
- `PARTIALLY_SHARED`: useful corroboration but shared dependencies materially reduce independence;
- `NOT_INDEPENDENT`: evaluator/adjudication path is effectively the same and does not increase the independent replication count;
- `UNRESOLVED`: provenance is insufficient to determine independence.

Only `DISTINCT` replications count toward the configured independent-replication threshold.

## Consistency and conflict handling

Replication disagreement is evidence, not noise to discard. If a distinct evaluator produces materially different results, preserve both packages and open an integrity/measurement investigation. Promotion is blocked while a material unresolved contradiction could change the gate outcome.

A replication should not be rejected merely because it lowers the measured score. Selection of only favorable replications invalidates the evidence package.

## Benchmark leakage and contamination

Each evaluator documents how protected content was generated, stored, accessed, and separated from the evaluated system. Known exposure of holdout content, answer keys, grader targets, or equivalent leakage must be recorded and ordinarily invalidates that replication for promotion use.

## Minimum gate counts

The machine-readable gate controls the numerical requirement. The present operational framework requires multiple genuinely independent replications before promotion, with the verified state requiring a stricter replication count than the candidate state.

The numerical count never overrides an unresolved evidence-integrity failure.

## Claims boundary

Replication strengthens confidence in reproducibility; it does not by itself establish AGI, consciousness, sentience, or deployment authorization. All required capability lanes must still satisfy the configured gate.

Current classification remains `BELOW_AGI` until valid multi-lane evidence and the required distinct replications are present.
