# Worldshepherd Skilled-Human Baseline Protocol v1

## Purpose

Define how skilled-human reference scores are established for the protected economic-work battery. The baseline exists to make the system-to-human comparison reproducible and resistant to cherry-picking. It does not alter the AGI gate or current intelligence classification.

## Baseline panel

Each evaluated domain must use a predeclared skilled-human panel appropriate to the domain. Panelists should have relevant professional experience or equivalent demonstrated competence. The panel-selection rule, inclusion criteria, exclusions, and sample size must be frozen before candidate-system scoring begins.

The current machine-readable battery requires at least five human observations per domain for candidate-level evaluation and at least ten for verified-level evaluation. Higher sample sizes are preferred when feasible.

## Task identity

Human and system scores must refer to the same frozen task set, scoring rubric, task weights, allowed reference materials, time/resource constraints, and output format unless a difference is explicitly documented and justified. The exact task set and grader/rubric are represented by cryptographic hashes in the protected evaluation record.

## Measurement record

For each domain, preserve at minimum:

- domain identifier;
- task-set hash and grader/rubric hash;
- panel-selection criteria;
- anonymized participant identifiers;
- participant count;
- task count;
- per-task or auditable aggregate scores;
- score direction (`higher_is_better` or `lower_is_better`);
- permitted tools and reference materials;
- time/resource limits;
- exclusions and missing-data handling;
- arithmetic used to derive the frozen domain baseline;
- baseline freeze timestamp/version.

## Independence controls

The evaluated system must not select which human results are retained. Baseline exclusions must follow predeclared rules and be logged. System outputs may not be used to revise answer keys, grading rubrics, panel composition, or the frozen baseline for the same evaluation run.

When expert adjudication is required, the adjudicator must not be the evaluated planner. Material scoring disputes should be preserved in the evidence record rather than silently overwritten.

## Statistical reporting

Report the central baseline statistic used by the economic-work adapter and enough dispersion information to understand uncertainty, such as standard deviation, interquartile range, bootstrap interval, or another predeclared method appropriate to the score distribution. Small-panel uncertainty must be stated explicitly.

A domain ratio above 100% means the system exceeded the frozen central skilled-human reference on that scoring rule; it does not mean the system exceeds every skilled human or establishes AGI.

## Critical domains

Critical-domain baselines receive the same protections as all other domains and must not be substituted with easier neighboring tasks after seeing candidate performance. Missing or invalid critical-domain baselines invalidate the critical-domain floor for promotion use.

## Versioning and reruns

A baseline version is immutable once used for a protected candidate run. If tasks, rubric, panel-selection rules, or material scoring procedures change, issue a new baseline version and new hashes. Reruns must disclose whether the human baseline was reused unchanged or recollected.

## Evidence handoff

The independent evaluator returns the frozen baseline version and controlled-access evidence needed to audit it, plus the domain-level `human_baseline_score` and `human_baseline_n` fields consumed by the economic-work adapter. Protected participant information does not belong in the public repository.

## Claims boundary

A strong human-relative score is one lane of the Worldshepherd gate. It cannot compensate for failures in novel generalization, long-horizon autonomy, held-out transfer, tool/workflow reliability, self-correction, evidence integrity, or independent replication.

Current classification remains `BELOW_AGI` until the complete configured gate is satisfied with valid evidence.
