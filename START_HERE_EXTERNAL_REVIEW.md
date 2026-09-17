# Worldshepherd — External Reviewer Start Here

**Purpose:** give a technical reviewer, partner, program office, standards participant, laboratory, or prospective customer a bounded path to determine what Worldshepherd is, what is executable now, what evidence exists, what is still missing, and what a useful next engagement could be.

This page is intentionally narrower than the full research portfolio.

## 60-second summary

Worldshepherd is an R&D software, assurance, evidence-provenance, and multidisciplinary engineering program centered on **SARA** and the surrounding **PRIME SENTINEL / ECHO SENTINEL LINK / OVERWATCH** architecture.

The governing operating rule is:

> **AI proposes → human approves → automation stays bounded → actions and evidence are logged.**

The public repository contains executable software, CI, reproducibility/recovery work, claims/evidence controls, opportunity/requirements tooling, research protocols, and multidisciplinary R&D artifacts.

The repository does **not** treat documents, simulations, outreach, partner interest, literature, or CI success as automatic proof of physical, clinical, operational, contractual, certified, or government-accepted capability.

## What a reviewer should inspect first

### 1. Canonical runnable SARA surface

The repository declares one canonical local SARA implementation:

- [`runtime/README.md`](runtime/README.md)
- [`deployments/sara_verified_local_v1/`](deployments/sara_verified_local_v1/)
- [`scripts/sara.sh`](scripts/sara.sh)

The public operator path includes:

```bash
bash scripts/sara.sh setup
bash scripts/sara.sh run
bash scripts/sara.sh check
bash scripts/sara.sh test
```

The bounded local service exposes health/readiness/UI surfaces plus authenticated or administrator-scoped workflow, audit, registry, and related governed functions. A successful relay operation means **local governed recording/audit** unless a separately verified integration establishes something more.

### 2. Claims and evidence controls

Read these before interpreting research or capability language:

- [`docs/CLAIMS_AND_EVIDENCE_POLICY.md`](docs/CLAIMS_AND_EVIDENCE_POLICY.md)
- [`docs/WORLDSHEPHERD_CAPABILITY_MAP.md`](docs/WORLDSHEPHERD_CAPABILITY_MAP.md)
- [`docs/operations/ACTIVE_TASKS.md`](docs/operations/ACTIVE_TASKS.md)
- [`docs/operations/FRESHNESS_POLICY.md`](docs/operations/FRESHNESS_POLICY.md)

Substantive claims should be distinguishable as one or more of:

- `PROVEN INTERNALLY`
- `IMPLEMENTED IN SOFTWARE`
- `SUPPORTED BY LITERATURE`
- `SIMULATED ONLY`
- `HYPOTHESIS`
- `SPECULATIVE EXTENSION`
- `REQUIRES LAB VALIDATION`
- `REQUIRES PARTNER VALIDATION`
- `REQUIRES LEGAL REVIEW`
- `NOT CURRENTLY CLAIMED`

If a stronger state is not supported by a named evidence artifact, do not infer it.

### 3. Evaluator handoff surface

A machine-readable evaluator handoff generator is documented at:

- [`deployments/sara_verified_local_v1/docs/EVALUATOR_HANDOFF_MANIFEST_V1.md`](deployments/sara_verified_local_v1/docs/EVALUATOR_HANDOFF_MANIFEST_V1.md)

It is designed to bind an evaluator package to an exact repository/ref/commit, code inventory, declared software and hardware assumptions, fixtures, expected-result semantics, evaluation scope/window, claims boundaries, and conflict/contract-disclosure state. Its output receives a canonical SHA-256 digest.

A handoff manifest is **not** independent validation. It is the precision layer used when a frozen candidate is handed to an evaluator. Issue **#155** remains authoritative for the frozen-release and independently controlled reproduction gate.

## Five-minute technical review path

1. Read this page and the root [`README.md`](README.md).
2. Read [`runtime/README.md`](runtime/README.md) and identify the canonical runnable SARA boundary.
3. Read [`docs/CLAIMS_AND_EVIDENCE_POLICY.md`](docs/CLAIMS_AND_EVIDENCE_POLICY.md).
4. Inspect the relevant implementation, tests, and GitHub Actions workflow instead of relying on an email, slide, or summary.
5. Inspect the evaluator-handoff manifest specification above.
6. For independent reproduction, use the frozen/evaluator-package work tracked in **#155** rather than treating moving `main` as a frozen release.
7. Record discrepancies. A useful external review may falsify, narrow, or simplify a claim; disagreement is evidence to retain.

## Core architecture — bounded roles

| Component | Bounded role | Do not infer |
|---|---|---|
| **SARA** | governed workflow/orchestration, local administration, bounded relay recording, audit-oriented execution | arbitrary autonomous action, third-party activation, or unrestricted network control |
| **PRIME SENTINEL** | policy/authorization and human-approval boundaries tied to specific implementations | universal authorization, accreditation, or authority over partner systems |
| **ECHO SENTINEL LINK** | provenance/evidence lineage and custody patterns | independent validation merely because evidence was logged |
| **OVERWATCH** | observability/common-operating-picture architecture and integration work | fielded operational C2 capability unless separately demonstrated |
| **PRE** | requirements/opportunity delta and qualification tooling | prediction as proof that a requirement, award, or capability exists |

## How the wider Worldshepherd portfolio fits

The broader projects are not treated as one monolithic maturity claim. They are routed into the common assurance stack according to evidence type:

- software/system projects can become evaluator workloads when their exact implementation and tests are frozen;
- scientific and engineering projects can become evidence-ingestion workloads when measured data, calibration, uncertainty, and provenance exist;
- partner-owned domain cores remain partner-owned while Worldshepherd contributes bounded assurance, evidence, authorization, configuration custody, or integration functions;
- unvalidated concepts remain hypotheses, simulations, or validation plans until the relevant physical/domain gate is actually closed.

This allows projects such as MBSE reconstruction, APNT/sensing, materials, RF/metasurfaces, propulsion, quantum, aerospace, BAROS, PoO/custody, supply-chain provenance, and other lanes to exercise common SARA/PRIME/ECHO/OVERWATCH machinery **without allowing breadth to inflate maturity**.

## Current external-evidence boundary

The public repository contains substantial internal engineering evidence and multiple external-evaluation plans. Those are not interchangeable with a completed independent evaluation.

Until the relevant gate is closed, do not describe Worldshepherd as:

- independently certified or generally independently validated;
- CMMC/NIST/DFARS compliant solely because controls, precursors, or mapping artifacts exist;
- government sponsored, approved, endorsed, accepted, or operationally deployed merely because work targets public government requirements;
- cleared for classified/CUI/SAP processing without the applicable authorized environment and documentary basis;
- clinically validated or appropriate for patient care;
- physically validated in a domain where only models, simulations, protocols, literature, or partner capabilities exist;
- partnered with, endorsed by, or under contract with an organization merely because outreach, a referral, a meeting, or technical discussion occurred.

External/compliance gates that software cannot close are tracked in **#27**. Corporate/IP/diligence closure is tracked in **#157**. Independent-reproduction packaging is tracked in **#155**.

## Identity and title accuracy

Public Worldshepherd material should use **Brandon Davis**, **Brandon Ray Davis**, or **Mr. Davis** as appropriate. This repository does **not** claim an earned doctoral title or doctorate credential for Brandon Ray Davis, and Worldshepherd-authored material should not apply `Dr.` unless an applicable qualified body formally confers such a title.

If an outside correspondent independently uses `Dr.`, that assumption is not evidence of a credential.

## Legal, corporate, eligibility, and contracting status

Do not infer legal-entity formation, SBIR/STTR eligibility, SAM/UEI/CAGE/DSIP status, contracting status, security clearance, export-control status, patent ownership, or regulatory authorization from repository visibility or technical activity.

The authoritative closure ledgers are **#27** and **#157**. Unknown or documentary-pending fields remain unknown/pending; they are not silently filled from founder assertion or code activity.

## Bounded engagement modes

### 1. Independent software evaluation

Evaluate a frozen SARA/PRIME/ECHO/OVERWATCH software boundary for deterministic behavior, authorization separation, audit/evidence integrity, replay/tamper handling, recovery, and reproducibility.

**Immediate need:** an evaluator-controlled environment and challenge inputs. See **#155**.

### 2. Governed Evidence & Mission-Assurance Pilot

Apply bounded provenance, authorization, configuration custody, replay/duplicate handling, human approval, recovery evidence, and discrepancy retention to one real customer workflow.

**Immediate need:** one qualified customer problem with measurable acceptance criteria. See **#156**.

### 3. Standards/community contribution

Contribute machine-readable evidence, provenance, assurance, interoperability, or evaluation artifacts where they actually fit an existing charter.

**Boundary:** a standards mailing-list discussion, community membership, or contribution is not adoption or endorsement.

### 4. Partner integration

Worldshepherd can provide an assurance/evidence/governance layer around a partner-owned domain core where the partner owns the relevant sensor, laser, PNT, RF, manufacturing, autonomy, biomedical, or other specialist capability.

**Boundary:** partner capability does not become Worldshepherd capability merely because an integration is contemplated.

### 5. Scientific/domain validation partnership

Use a qualified laboratory, domain expert, medical physicist, test facility, or engineering partner to convert a frozen model/test article into calibrated, reproducible external evidence.

**Boundary:** a lab conversation, quote, protocol, or facility capability is not a test result.

## Default external-engagement envelope

Every serious external engagement should be reducible to:

> **Worldshepherd contributes `<specific bounded capability>` to `<counterpart-owned/core system>` by `<measurable mechanism>`; it does not claim `<core technology, authority, or validation not owned>`. The immediate ask is `<one concrete next action>`.**

A useful first message identifies:

- the organization/project;
- the specific public opportunity, technical problem, or evaluation objective;
- Worldshepherd's bounded contribution;
- the evidence/artifact the recipient can inspect;
- one requested next action.

## How to challenge the work

Public technical criticism is useful. The strongest review is specific enough to become a reproducible issue:

- identify the exact claim, file, commit, test, or interface;
- state what evidence is missing or contradictory;
- provide a falsifying case or a simpler architecture where possible;
- distinguish a real technical gap from a venue, timing, procurement, or organization-fit mismatch.

External feedback is routed into the gap-closure process tracked in **#327** rather than being treated automatically as either rejection or validation.

## Contact / routing

For public technical review, use the repository's GitHub issue/PR workflow and reference the exact artifact or issue being discussed. For an existing private correspondence relationship, continue in that established thread rather than publishing private contact information or partner details into the public repository.

Private contact data, credentials, proprietary partner material, export-controlled information, CUI, and uncleared sensitive data must not be committed here.

## Licensing and public visibility

This repository is public, but **public visibility is not itself an open-source license**. Do not infer reuse rights, patent rights, data rights, third-party permissions, or contribution terms beyond the repository's actual governing documents.

---

### Reviewer decision in one sentence

If you can identify a **specific bounded capability worth testing**, use the linked implementation/evidence path and tell us exactly what fails, what is missing, or what would make the result independently credible. If the core capability belongs to your organization or another specialist, treat Worldshepherd as the assurance/integration/evidence layer until measured evidence supports something broader.
