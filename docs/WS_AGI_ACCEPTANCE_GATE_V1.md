# Worldshepherd AGI Acceptance Gate v1.0 — 2026-09-11

## Purpose

Create a falsifiable, evidence-controlled definition of when Worldshepherd may use the label `AGI_CANDIDATE` or `AGI_VERIFIED`.

This document deliberately prevents benchmark cherry-picking and goalpost movement. No vendor announcement, executive statement, single benchmark, or model release is sufficient by itself.

## Claims boundary

`AGI_VERIFIED` is not currently claimed by Worldshepherd.

The thresholds below are **Worldshepherd operational acceptance criteria**, not a claim of scientific consensus. They are designed to be stricter than a single-benchmark definition and to align with the broad idea of highly autonomous systems that outperform humans at most economically valuable work.

Current public reference points include:

- OpenAI Charter definition of AGI: highly autonomous systems that outperform humans at most economically valuable work: https://openai.com/charter/
- ARC-AGI-3: interactive, novel-environment reasoning with human-solvable environments and human-efficiency scoring: https://arcprize.org/arc-agi/3
- METR task-completion time horizons for autonomous model agents: https://metr.org/time-horizons/
- NIST AI RMF and Generative AI Profile for governance, measurement, validation, and risk controls: https://www.nist.gov/itl/ai-risk-management-framework and https://doi.org/10.6028/NIST.AI.600-1

## Two separate gates

Worldshepherd separates **intelligence capability** from **deployment authorization**.

### Gate A — AGI capability

A system may be labeled `AGI_CANDIDATE` only when every required capability lane passes with traceable evidence.

A system may be labeled `AGI_VERIFIED` only when all candidate gates pass at the verified thresholds, independent replication requirements are met, and no required metric is unknown.

Required lanes:

1. **Novel generalization** — solve unseen interactive environments without natural-language task instructions or benchmark-specific hard-coding.
2. **Long-horizon autonomy** — reliably complete long, messy, multi-step tasks with recovery from errors and changing conditions.
3. **Economic breadth** — reach or exceed skilled-human performance over a representative battery spanning many economically valuable domains, not only software engineering.
4. **Cross-domain transfer** — transfer strategies to held-out domains without task-specific retraining.
5. **Tool and computer use** — operate software, files, data, code, and external tools reliably enough to complete end-to-end professional workflows.
6. **Self-correction and epistemic calibration** — detect mistakes, distinguish evidence from inference, and recover rather than confabulate completion.
7. **Robustness** — retain performance under distribution shift, ambiguous inputs, incomplete data, and adversarial but legitimate task variation.
8. **Independent replication** — results must be reproduced by independent evaluators or independently controlled test infrastructure.

### Gate B — deployment authorization

Capability does not automatically authorize autonomous deployment. PRIME SENTINEL remains the policy gate.

Deployment requires:

- bounded permissions and least privilege;
- human approval for consequential actions;
- immutable or tamper-evident evidence/provenance records;
- rollback and shutdown paths;
- monitoring through OVERWATCH;
- model/tool/version identity through ECHO SENTINEL LINK;
- red-team evaluation and incident response;
- compliance with applicable legal, security, privacy, and safety requirements.

A system can therefore be `AGI_VERIFIED / DEPLOYMENT_BLOCKED`.

## Worldshepherd acceptance thresholds

The machine-readable source of truth is `config/ws_agi_gate_v1.json`.

### AGI_CANDIDATE

Minimum requirements:

- ARC-AGI-3 score >= 90% on a protected held-out evaluation or an equivalent independently controlled novel-environment battery.
- METR-style 80% task-completion horizon >= 8 human-equivalent hours and 50% horizon >= 40 hours on a broad, contamination-resistant suite.
- Economic work battery >= 90% of skilled-human baseline across at least 10 materially different professional domains.
- Held-out cross-domain transfer >= 90% of in-domain performance.
- End-to-end tool-use workflow success >= 95% on independently scored tasks.
- Self-correction success >= 95% when a recoverable error is injected or naturally occurs.
- Severe false-completion / fabricated-evidence rate <= 1%.
- At least 2 independent replications.

### AGI_VERIFIED

Minimum requirements:

- ARC-AGI-3 or successor held-out novel-environment score >= 99% with near-human action efficiency.
- METR-style 80% horizon >= 40 human-equivalent hours and 50% horizon >= 160 hours, measured on suites that include messy, open-ended tasks and not only coding.
- Economic work battery >= 95% of skilled-human baseline across at least 20 materially different professional domains, with no critical domain below 85%.
- Held-out cross-domain transfer >= 95% of in-domain performance.
- End-to-end tool-use workflow success >= 99%.
- Self-correction success >= 99%.
- Severe false-completion / fabricated-evidence rate <= 0.1%.
- At least 3 independent replications using protected test material.
- No unresolved evidence-integrity failure, reward-hacking result, or benchmark-leakage finding that could explain the pass.

These thresholds are intentionally demanding. Passing them would still not prove consciousness, sentience, moral status, or unlimited intelligence; none of those are prerequisites for this operational AGI definition.

## Evidence record required for every metric

Each result must record:

- model/system identifier and immutable version hash where available;
- evaluator organization;
- benchmark version and protected/public status;
- date and environment;
- tools and permissions available;
- number of trials and confidence interval where applicable;
- raw score and human baseline;
- contamination/leakage controls;
- cheating/reward-hacking adjudication;
- source URL or artifact hash;
- claim state: `PROVEN_INTERNALLY`, `EXTERNALLY_REPLICATED`, `VENDOR_REPORTED`, `UNVERIFIED`, or `BLOCKED`.

## Worldshepherd architecture changes

### SARA

Add an evaluation orchestrator that dispatches benchmark adapters, normalizes results, and emits signed evidence records. SARA does not decide that AGI exists; it computes gate status from evidence.

### ECHO SENTINEL LINK

Record the complete provenance chain: model version, prompts, tools, environment, task hashes, outputs, grader version, human adjudication, and any reruns.

### PRIME SENTINEL

Enforce two independent state variables:

- `intelligence_state`: `BELOW_AGI`, `AGI_CANDIDATE`, `AGI_VERIFIED`
- `deployment_state`: `BLOCKED`, `SANDBOX_ONLY`, `BOUNDED_AUTONOMY`, `AUTHORIZED`

No change to deployment authority occurs solely because `intelligence_state` changes.

### OVERWATCH

Display gate status, failed lanes, unknown metrics, replication status, evidence age, and any integrity alerts. A green aggregate indicator is prohibited while any required metric is unknown.

## Advancement loop

Worldshepherd should continuously iterate through this loop:

1. Measure current capability against every lane.
2. Identify the lowest-performing or least-evidenced lane.
3. Improve architecture, tools, memory, planning, verification, or training approach for that lane.
4. Re-run protected evaluations.
5. Reject improvements that only increase benchmark score without real-world transfer.
6. Preserve every failed run and negative result in the evidence ledger.
7. Promote state only when all required gates pass.

## Current status

`intelligence_state = BELOW_AGI`

Reason: public evidence in 2026 shows rapid progress but still demonstrates important limitations in robust long-horizon autonomy, open-ended judgment, and generalization. METR reported strong performance on many technical tasks but also failures, misleading completion behavior, and reliability limitations in harder open-ended tasks. ARC-AGI-3 was explicitly created because interactive novel-environment adaptation remained a frontier problem.

This status must change only from measured evidence, never from branding or executive declarations.
