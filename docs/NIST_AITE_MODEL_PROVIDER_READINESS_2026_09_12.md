# Worldshepherd — NIST AITE model-provider readiness assessment

**Original assessment:** 2026-09-12  
**Updated:** 2026-09-14  
**Relationship state:** AITE COMMUNITY MEMBER  
**Model-provider state:** NOT READY / NOT ENROLLED / NOT SUBMITTED / NO AITE RESULT

## 1. Purpose

Assess whether a bounded Worldshepherd model implementation can legitimately enter NIST AITE without treating the broader Worldshepherd/SARA governance stack as the scored model and without promoting a task-specific result into a system-wide claim.

## 2. Public-source record

Public AITE information used for this assessment was checked on 2026-09-14 against:

- NIST AITE Overview & Road Map v1.0: https://ai-challenges.nist.gov/pub/22
- NIST AITE FAQ: https://ai-challenges.nist.gov/aite_faq
- NIST AITE program page: https://ai-challenges.nist.gov/aite
- NIST launch announcement dated 2026-07-27: https://www.nist.gov/news-events/news/2026/07/announcing-nists-artificial-intelligence-technology-evaluation-aite

The public roadmap describes Phase 1 as accepting only a very limited number of additional models and application tests. It states that models are tested first-come, first-served as capacity permits and that early application-test selection considers anticipated integration ease and impact. The public materials also describe AITE as a sequestered blind-data evaluation environment and state that results are public and task-scoped, with NIST disclaiming endorsement.

These are time-sensitive program facts. Recheck the current NIST materials before any submission decision.

## 3. Current relationship state

NIST has acknowledged Worldshepherd's inquiry, registered the interest, and indicated that participation-process information will follow. The contact address has been added to the AITE Community. An implementation-focused community inquiry was sent on 2026-09-14.

Community membership and registered interest do not establish model-provider enrollment, model acceptance, application-test acceptance, submission, independent validation, certification, endorsement, or an AITE score.

## 4. What AITE would evaluate

The working assumption is that AITE evaluates the submitted model implementation/API required by the selected task. SARA, PRIME SENTINEL, ECHO SENTINEL LINK, OVERWATCH, approval gates, provenance infrastructure, and other governance components remain outside the scored artifact unless NIST's actual task specification explicitly includes them.

Those components may still support internal version control, approvals, evidence custody, and post-result claims control.

## 5. Current readiness state

`AITE_MODEL_PROVIDER_STATE = NOT_READY`

Open requirements:

1. **Participation terms:** current Participation Agreement has not yet been reviewed or accepted.
2. **Exact interface:** the current model-provider API/submission protocol has not yet been obtained and implemented.
3. **Task compatibility:** no specific Worldshepherd-associated model has yet been demonstrated compatible with an active AITE task.
4. **Provider-side handling duties:** unresolved pending NIST's current agreement and handling instructions. NIST's public description of how it protects received submissions does not, by itself, establish the submitter's exact obligations.
5. **Public-result authorization:** no model submission has been authorized and no publication-risk approval has been recorded.
6. **Submitting identity:** the legal submitting identity must be accurate at the time of any submission.
7. **External result:** none exists. Internal CI, public benchmarks, synthetic fixtures, or repository artifacts are not AITE results.

## 6. Requirements inquiry versus submission readiness

The initial requirements inquiry is allowed precisely because some authoritative participation materials are not yet available to Worldshepherd. Obtaining those materials is **not** a prerequisite to asking NIST for them.

The requirements below are gates for later **participation/submission readiness**, not for a non-proprietary information request.

## 7. Bounded adapter architecture

If the official requirements support participation, implement a dedicated `AITE_MODEL_ADAPTER` with:

- one fixed model/version identity;
- the exact NIST request/response schema for the selected task;
- a reproducible dependency/configuration manifest;
- bounded runtime/resource policy;
- no access to protected evaluation answers;
- no training, self-modification, external retrieval, persistence, or cross-trial state unless the official specification permits it;
- version freeze before submission;
- local validation using only permitted public/synthetic fixtures;
- an evidence manifest that cannot be confused with a NIST-generated result.

Preparation defaults above must yield to the official AITE specification when received.

## 8. Submission-readiness gates

### Requirements gate

- [ ] current Participation Agreement reviewed;
- [ ] official model-provider API/submission protocol obtained;
- [ ] selected task evaluation criteria obtained;
- [ ] provider-side handling instructions reviewed.

### Technical-fit gate

- [ ] one active task matches a model that can lawfully be submitted;
- [ ] official schema implemented;
- [ ] local validator passes permitted fixtures;
- [ ] dependency/runtime package is reproducible;
- [ ] fixed model/version frozen.

### Administrative gate

- [ ] submitting identity confirmed;
- [ ] publication implications accepted;
- [ ] applicable security/data-handling path approved;
- [ ] explicit submission authorization recorded.

### Claims-control gate

- [ ] no endorsement language;
- [ ] no system-wide inference from a task-scoped score;
- [ ] no internal benchmark described as AITE evidence;
- [ ] uncertainty, dataset, task, model/version, and metric limits preserved in external statements.

## 9. Application-test/data-provider lane

Because the public roadmap emphasizes integration ease and impact in early phases, any Worldshepherd-originated test concept should be a compact measurement problem rather than a broad system demonstration.

Issue #267 records one internal candidate: Bounded Authorization Decision Evaluation (BADE). It is preparation only and has not been proposed to, accepted by, reviewed by, or scored by NIST.

## 10. Result-ingestion rule

Any eventual AITE result enters the Worldshepherd evidence system as one externally generated, task-scoped measurement record. It must not automatically establish general intelligence, system-wide operational readiness, certification, standards conformity, deployment authorization, scientific consensus, or performance on unrelated tasks.

## External-safe status statement

> Worldshepherd is a member of the NIST AITE Community and NIST has registered its interest in possible participation. Worldshepherd has not enrolled or submitted a model, has no AITE result, and does not represent internal evaluation artifacts as NIST validation, certification, endorsement, or system-wide performance evidence.
