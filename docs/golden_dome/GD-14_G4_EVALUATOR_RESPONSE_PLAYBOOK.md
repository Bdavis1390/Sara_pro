# GD-14 — G4 Evaluator Response Playbook

**Posture:** INTERNAL CAPTURE / CLAIMS-CONTROLLED

## Purpose
Provide one consistent decision path for replies to W-RMABM independent-evaluation outreach. This document does not authorize release of source code, controlled information, legal acceptance, payment, or government submission.

## Current state
- G4-prep branch: `golden-dome-rmabm-g4prep`
- Draft PR: #116
- Evidence state: internally verified synthetic software only.
- G4 status: **PREPARED / OUTREACH SENT — NOT INDEPENDENTLY REPRODUCED**.
- First-wave evaluator outreach sent: Aerospace Commercial Programs; Georgia Tech Research Institute (GTRI).
- Second-wave evaluator drafts staged, unsent: Virginia Tech NSI/Hume; CMU SEI; MITRE NSEC.

## Reply classification and action

### R0 — Automated acknowledgment
Examples: ticket receipt, generic auto-response.

Action: record only. Do not advance relationship or G4 state.

### R1 — Human routing / correct-contact referral
Examples: named lab, contracts office, technical lead, intake form.

Action: verify route; prepare a minimal non-confidential reply. No bundle transmission unless the receiving route is confirmed and release review is complete.

### R2 — Scoping / technical-question response
Examples: asks what is being evaluated, environment requirements, expected duration, evaluator role.

Action: answer using GD-10/GD-11/GD-13 claims-controlled material only. Do not disclose enabling IP, CUI, classified information, proprietary interfaces, real operational data, or weapon/engagement logic.

### R3 — Request for evaluation materials
Action: perform release review of the allowlisted external bundle; verify exact recipient and purpose; generate/verify manifest hashes; provide only the minimum required artifacts after human release approval. Source code is not automatically releasable merely because documentation is allowlisted.

### R4 — NDA / legal terms / IP terms / data-rights terms
Action: stop and surface to CRE1AWS. Do not sign, click-accept, or send strategic IP under unreviewed terms.

### R5 — Pricing / statement of work / procurement mechanism
Action: obtain scope, deliverables, price, schedule, ownership/data-rights terms, evaluator independence statement, and payment mechanism. Surface for CRE1AWS approval before commitment.

### R6 — Sponsor / clearance / CUI / classified requirement
Action: stop unclassified G4 path unless evaluator offers a fully unclassified surrogate route. Do not submit CUI/classified material or claim access/clearance.

### R7 — Evaluation accepted
Required before scheduling:
1. evaluator is outside Worldshepherd development;
2. evaluator-controlled environment;
3. evaluator selects challenge seed;
4. frozen commit and challenge digest recorded;
5. positive and fail-closed tests included;
6. evaluator owns the scorecard record;
7. result can be reported at least as pass/fail with enough provenance to establish independence.

Relationship state may advance to **CONTROLLED EVALUATION AGREED** only after these conditions and any commercial/legal terms are authorized. G4 itself is still not achieved.

### R8 — Independent run completed
G4 can advance only if the outside evaluator records all mandatory GD-11 assertions as passing against the frozen protocol. Allowed claim:

**INDEPENDENTLY REPRODUCED — SYNTHETIC SOFTWARE BEHAVIOR ONLY**

This does not establish operational missile-warning/tracking performance, fire-control suitability, Golden Dome acceptance, Space Force acceptance, BAE integration, certification, CMMC/NIST compliance, classified readiness, or deployment.

### R9 — Rejection / no-fit
Record reason. Distinguish technical rejection from business-model, sponsor, funding, charter, conflict-of-interest, security, or routing constraints. Use the reason to update evaluator ranking rather than treating it as technical falsification unless the evaluator actually tested the frozen benchmark.

## Second-wave trigger
Do not mass-send. Second-wave outreach is appropriate when:
- a first-wave route rejects or cannot accept privately initiated evaluation;
- first-wave routing produces no substantive response after a reasonable business interval; or
- CRE1AWS explicitly directs broader parallel evaluation.

## Hard boundaries
- No real threat trajectories or engagement geometry.
- No targeting, interceptor guidance, fire-control, launch, or weapon-cueing logic.
- No CUI/classified/protected partner data.
- No claim of external validation before evaluator-owned reproduction evidence exists.
- No automatic NDA, legal, pricing, or payment acceptance.
