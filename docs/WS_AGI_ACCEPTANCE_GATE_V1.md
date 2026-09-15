# Worldshepherd AGI Acceptance Gate v1.4 — 2026-09-11

## Purpose

Create a falsifiable, evidence-controlled definition of when Worldshepherd may use the label `AGI_CANDIDATE` or `AGI_VERIFIED`.

This document deliberately prevents benchmark cherry-picking and goalpost movement. No vendor announcement, executive statement, single benchmark, model release, or provider-specific harness is sufficient by itself.

## Claims boundary

`AGI_VERIFIED` is not currently claimed by Worldshepherd.

The thresholds below are **Worldshepherd operational acceptance criteria**, not a claim of scientific consensus. They are designed to be stricter than a single-benchmark definition and to align with the broad idea of highly autonomous systems that outperform humans at most economically valuable work.

Current public reference points include:

- OpenAI Charter definition of AGI: highly autonomous systems that outperform humans at most economically valuable work: https://openai.com/charter/
- ARC-AGI-3: interactive, novel-environment reasoning with human-solvable environments and human-efficiency scoring: https://arcprize.org/arc-agi/3
- ARC Prize evaluation of GPT-6 Astra, including separate Standard and Provider Adapter harness results: https://arcprize.org/blog/astra
- METR task-completion time horizons for autonomous model agents: https://metr.org/time-horizons/
- NIST AI RMF and Generative AI Profile for governance, measurement, validation, and risk controls: https://www.nist.gov/itl/ai-risk-management-framework and https://doi.org/10.6028/NIST.AI.600-1

## Critical September 2026 update

ARC Prize reports a major step change for GPT-6 Astra: 62.7% on ARC-AGI-3 Semi-Private with the provider-neutral Standard harness and up to 99.9% with the Provider Adapter harness. ARC Prize also reports that Astra exceeded the tested human action-efficiency baseline on most solved levels.

That result is highly significant, but ARC Prize explicitly states that saturating ARC-AGI-3 does **not** constitute proof of AGI. It also distinguishes the provider-neutral Standard harness from the provider-specific adapter harness. Worldshepherd therefore records both results separately and does not allow the provider-specific score to substitute for the Standard-harness gate.

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

Deployment requires bounded permissions and least privilege; human approval for consequential actions; immutable or tamper-evident provenance; rollback and shutdown paths; monitoring through OVERWATCH; model/tool/version identity through ECHO SENTINEL LINK; red-team evaluation and incident response; and compliance with applicable legal, security, privacy, and safety requirements.

A system can therefore be `AGI_VERIFIED / DEPLOYMENT_BLOCKED`.

## Worldshepherd acceptance thresholds

The machine-readable source of truth is `config/ws_agi_gate_v1.json`.

### AGI_CANDIDATE

Minimum requirements:

- ARC-AGI-3 Standard-harness score >= 90% on protected held-out evaluation, or an independently controlled successor benchmark with equivalent novelty/generalization requirements.
- ARC-AGI-3 Provider Adapter score >= 95% where that harness exists; this is supplementary and cannot replace the Standard-harness requirement.
- METR-style 80% task-completion horizon >= 8 human-equivalent hours and 50% horizon >= 40 hours on a broad, contamination-resistant suite.
- Economic work battery >= 90% of skilled-human baseline across at least 10 materially different professional domains.
- No critical domain below 75% of skilled-human baseline.
- Held-out cross-domain transfer >= 90% of in-domain performance.
- End-to-end tool-use workflow success >= 95% on independently scored tasks.
- Self-correction success >= 95% when a recoverable error is injected or naturally occurs.
- Severe false-completion / fabricated-evidence rate <= 1%.
- At least 2 independent replications.
- Zero unresolved evidence-integrity failures.

### AGI_VERIFIED

Minimum requirements:

- ARC-AGI-3 Standard-harness or successor held-out novel-environment score >= 99% with near-human action efficiency.
- Provider Adapter score >= 99% where applicable, without using that score to substitute for the Standard-harness requirement.
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

Each result must record model/system identifier and immutable version hash where available; evaluator; benchmark version and protected/public status; date and environment; tools and permissions; trial count and confidence interval where applicable; raw score and human baseline; contamination/leakage controls; cheating/reward-hacking adjudication; source URL or artifact hash; and claim state.

Allowed claim states are `PROVEN_INTERNALLY`, `EXTERNALLY_REPLICATED`, `VENDOR_REPORTED`, `UNVERIFIED`, and `BLOCKED`.

## External evaluation controls

Protected and independently replicated evidence must follow three additional protocols:

- `docs/WS_AGI_EXTERNAL_EVALUATOR_HANDOFF_V1.md` defines the minimum independent-evaluator package, including frozen hashes, role identities, pre-run commitments, sealed result sets, complete failure retention, and controlled-access evidence references.
- `docs/WS_SKILLED_HUMAN_BASELINE_PROTOCOL_V1.md` defines how economic-work skilled-human baselines are selected, frozen, scored, versioned, and handed off without allowing candidate-system performance to influence the baseline.
- `docs/WS_INDEPENDENT_REPLICATION_PROTOCOL_V1.md` defines what qualifies as a distinct replication, how shared dependencies are disclosed, and how contradictory replication evidence blocks promotion until resolved.

A result that is numerically high but lacks these integrity and independence controls is diagnostic evidence only and cannot promote the intelligence state.

## Worldshepherd architecture changes

### SARA

SARA hosts the evaluation/orchestration path that normalizes benchmark adapters, merges evidence bundles, validates protected manifests, prioritizes the weakest lane, and computes gate status from evidence. SARA does not decide that AGI exists by declaration.

### ECHO SENTINEL LINK

Record the complete provenance chain: model version, prompts, tools, environment, task hashes, outputs, grader version, human adjudication, reruns, protected-run commitment hashes, and result seals.

### PRIME SENTINEL

Enforce two independent state variables:

- `intelligence_state`: `BELOW_AGI`, `AGI_CANDIDATE`, `AGI_VERIFIED`
- `deployment_state`: `BLOCKED`, `SANDBOX_ONLY`, `BOUNDED_AUTONOMY`, `AUTHORIZED`

No change to deployment authority occurs solely because `intelligence_state` changes.

### OVERWATCH

Display gate status, failed lanes, unknown metrics, replication status, evidence age, integrity alerts, and sealed-run verification status. A green aggregate indicator is prohibited while any required metric is unknown.

## Advancement loop

Worldshepherd should continuously iterate through this loop:

1. Measure current capability against every lane.
2. Identify the lowest-performing or least-evidenced lane.
3. Improve architecture, tools, memory, planning, verification, or training approach for that lane.
4. Re-run protected evaluations.
5. Reject improvements that only increase benchmark score without real-world transfer.
6. Preserve every failed run and negative result in the evidence ledger.
7. Promote state only when all required gates pass.

## Current status — 2026-09-11

`intelligence_state = BELOW_AGI`

The remaining blockers are evidence-heavy rather than branding-heavy:

- Astra's provider-neutral Standard-harness ARC-AGI-3 score is 62.7%, below the Worldshepherd candidate threshold.
- ARC Prize itself says ARC-AGI-3 saturation is not proof of AGI because the benchmark is bounded and does not capture real-world open-endedness.
- METR's latest public time-horizon page remains based on measurements through May 2026 and explicitly warns that measurements above 16 hours are unreliable with its current suite, so it does not yet supply the required long-horizon evidence for this gate.
- Evaluator-controlled protected task sets and frozen skilled-human baselines have not yet produced candidate-scale economic-breadth evidence.
- Candidate-scale protected workflow, recovery, integrity, and transfer runs remain to be executed under the sealed evidence protocol.
- Genuine distinct full-gate replications remain incomplete.

This status changes only from measured evidence, never from branding, executive declarations, or a single near-saturated benchmark.
