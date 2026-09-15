# Worldshepherd — NP004 Assertion-to-Evidence Register

**Date:** 2026-09-14
**Topic:** DON26BX05-NP004
**Purpose:** Prevent proposal language from outrunning evidence.
**Rule:** Every technical assertion used in a proposal, briefing, screenshot caption, demo script, or partner discussion must resolve to a pinned artifact or to `NOT_YET_EVIDENCED`.

## Evidence classes

- **PROVEN INTERNALLY** — demonstrated by a pinned test/workflow for the exact stated software scope.
- **IMPLEMENTED IN SOFTWARE** — code exists, but the broader performance/operational claim has not been demonstrated.
- **SIMULATED ONLY** — evidence is from representative/synthetic inputs only.
- **SUPPORTED BY PUBLIC REQUIREMENT** — statement describes the published Government requirement, not Worldshepherd performance.
- **REQUIRES PARTNER VALIDATION** — depends on a non-Worldshepherd interface/system.
- **REQUIRES LAB VALIDATION** — requires measured environment/performance evidence not currently pinned.
- **NOT_YET_EVIDENCED** — do not claim as achieved.

## Pinned POC-A evidence anchor

**PR:** #187 — `Add NP004 synthetic APNT operator-awareness POC-A`
**Branch:** `worldshepherd/np004-apnt-poc-a-v0-1-20260912`
**Exact head:** `178f3da3a3ccd7ca84ac05825229c01a10cec778`
**PR state:** DRAFT / BLOCK MERGE / independent review pending
**POC claims boundary:** `SIMULATED_ONLY / SYNTHETIC APNT OPERATOR-AWARENESS DEMONSTRATOR / INFORMATIONAL DECISION AID ONLY`

### Exact-head successful workflow records

| Workflow | Run | Result |
|---|---:|---|
| WS NP004 APNT POC-A v0.1 Gate | 24 | SUCCESS |
| Required Test and Build | 108 | SUCCESS |
| SARA Verified Local v1 Gate | 2093 | SUCCESS |
| SARA Commit Closure Evidence | 1990 | SUCCESS |
| SARA TLS Private Backend Architecture | 1345 | SUCCESS |
| SARA NIST 800-171 SSP Precursor | 744 | SUCCESS |
| SARA Replacement Environment Restore | 1359 | SUCCESS |
| SARA Rollback Drill | 1367 | SUCCESS |
| SARA Operational Resilience Drill | 768 | SUCCESS |

Successful CI establishes that the exact POC-A head passed those repository workflows. It does **not** establish Navy acceptance, operational APNT performance, or Government cybersecurity authorization.

## Assertion register

| ID | Candidate assertion | Evidence anchor | Evidence class | Approved wording | Prohibited escalation |
|---|---|---|---|---|---|
| NP004-A001 | Worldshepherd has a synthetic APNT operator-awareness prototype | PR #187 exact head; `apnt_awareness.py`; fixture; tests | PROVEN INTERNALLY + SIMULATED ONLY | “A synthetic operator-awareness/replay prototype has been implemented and tested internally.” | “Operational APNT system”; “Navy validated” |
| NP004-A002 | The prototype preserves a source/alert/recommendation/operator-response trace | `apnt_awareness.py`; `test_hash_chain_links_every_audit_step`; exact-head gate | PROVEN INTERNALLY + SIMULATED ONLY | “The synthetic POC preserves a hash-linked decision trace.” | “Tamper-proof operational ledger”; “forensically certified” |
| NP004-A003 | Identical synthetic inputs produce deterministic replay output | `test_replay_is_deterministic_for_identical_inputs` | PROVEN INTERNALLY + SIMULATED ONLY | “Identical tested inputs produced deterministic replay evidence in the POC.” | General deterministic behavior under all production concurrency/inputs |
| NP004-A004 | Operator APPROVE/REJECT/DEFER remains non-actuating | `test_approved_operator_response_remains_informational_only`; `execution_attempted=false` | PROVEN INTERNALLY + SIMULATED ONLY | “Operator evaluation is recorded without execution; the POC contains no platform-command stage.” | “Human-authorized source switching”; “closed-loop recovery” |
| NP004-A005 | Invalid/non-finite evidence values fail validation | `test_non_finite_replay_evidence_is_rejected` | PROVEN INTERNALLY | “The tested data model rejects NaN/Infinity in bounded evidence fields.” | “All malformed or adversarial data is safely handled” |
| NP004-A006 | External APNT adapters can be gated on explicit authoritative mappings | `apnt_interface_contract.py`; `test_apnt_interface_contract.py` | IMPLEMENTED IN SOFTWARE | “Worldshepherd includes a fail-closed interface-contract mechanism requiring explicit field mappings and validation markers before enablement.” | “ASPN certified”; “pntOS interoperable” |
| NP004-A007 | Worldshepherd has a normalized synthetic PNT source model | `apnt_adapter.py` | IMPLEMENTED IN SOFTWARE + SIMULATED ONLY | “An internal normalized source model supports the synthetic feasibility lane.” | “Universal PNT schema” |
| NP004-A008 | Worldshepherd can derive bounded awareness states and recovery candidates | `apnt.py`; `apnt_qualification.py` | IMPLEMENTED IN SOFTWARE + SIMULATED ONLY | “A bounded demonstrator rule set derives synthetic awareness state and informational recovery candidates.” | “Navigation solution”; “autonomous anomaly classifier” |
| NP004-A009 | Synthetic qualification marks physical validity as not evaluated | `apnt_qualification.py` | PROVEN INTERNALLY for evidence semantics | “Qualification artifacts explicitly preserve the distinction between software-synthetic results and physical validation.” | Any physical/Navy system performance claim |
| NP004-A010 | Existing APNT tests intentionally preserve known blind spots | `test_apnt_nist_adversarial_gap_suite.py` | PROVEN INTERNALLY + NEGATIVE EVIDENCE | “The test suite records representative cases the current baseline intentionally does not detect, preventing silent promotion of capability.” | “Anti-spoofing capability” |
| NP004-A011 | Mission events can be ordered and replayed with evidence relationships | `mission_replay.py` | IMPLEMENTED IN SOFTWARE | “Worldshepherd includes an evidence-linked replay primitive.” | “Operational mission reconstruction validated by Navy” |
| NP004-A012 | Human acceptance records are scope-limited and do not automatically become operational-validation claims | `hmaa_human_acceptance.py` | IMPLEMENTED IN SOFTWARE | “Human acceptance custody explicitly limits what can become claimable evidence.” | “Human approval makes output operationally validated” |
| NP004-A013 | PRIME has a cryptographically verified short-lived authorization primitive | `prime_sentinel_authorization.py` | IMPLEMENTED IN SOFTWARE | Use only if relevant to general governance architecture; specify its existing narrow requalification-release scope | Do **not** present it as APNT command authorization or source-switch control |
| NP004-A014 | Worldshepherd currently meets the Government's 3–8 sources at 1–10 Hz design envelope | None | NOT_YET_EVIDENCED | “The Phase I design/benchmark will target the published 3–8 source, 1–10 Hz envelope.” | “Supports 8 sources at 10 Hz” before measurement |
| NP004-A015 | Worldshepherd currently meets sub-second end-to-end alert latency | None | NOT_YET_EVIDENCED | “Sub-second ingest-to-initial-alert latency is a Phase I measurement target.” | Any achieved sub-second latency statement |
| NP004-A016 | Worldshepherd has an ECDIS-style navigation UI | No pinned NP004 UI evidence identified in this gate | NOT_YET_EVIDENCED | “The proposed prototype will use operator-familiar navigation-style conventions and progressive disclosure.” | “ECDIS compliant/certified” |
| NP004-A017 | Worldshepherd improves operator decision speed/accuracy | No human-performance evidence | NOT_YET_EVIDENCED | “Phase I will measure surrogate-user task performance against defined scenarios.” | Any percentage or improvement claim |
| NP004-A018 | Worldshepherd is ASPN/pntOS interoperable | Stub/contract architecture only | REQUIRES PARTNER/AUTHORITATIVE INTERFACE VALIDATION | “Architecture is designed to map authoritative interfaces through explicit adapters.” | “Compatible,” “compliant,” or “integrated” without conformance evidence |
| NP004-A019 | Worldshepherd is integrated with GPNTS | None | NOT_YET_EVIDENCED | “GPNTS is the intended transition/integration target identified by the topic.” | “GPNTS integration” |
| NP004-A020 | Worldshepherd detects spoofing/jamming | Existing negative-evidence tests show blind spots | NOT_YET_EVIDENCED | “The system will support operator anomaly triage using available representative indicators; current POC does not independently detect spoofing/jamming.” | “Spoofing detector”; “jamming detector” |
| NP004-A021 | Worldshepherd runs fully air-gapped for the exact NP004 demo | Verified-local architecture exists but exact NP004 isolated demonstration evidence is not pinned here | REQUIRES LAB VALIDATION | “The architecture is designed for local isolated execution; Phase I demonstration will verify the exact NP004 package in an isolated runtime.” | “Air-gap validated NP004 deployment” before exact test |
| NP004-A022 | Worldshepherd is container-ready | Repository verified-local/container patterns exist | IMPLEMENTED IN SOFTWARE | “Existing deployment patterns are container-oriented; the NP004 package will produce pinned container evidence.” | “Iron Bank approved” |
| NP004-A023 | Worldshepherd is CMMC Level 2 compliant/certified | Repository includes NIST 800-171 precursor workflow but no award-time status verified in this register | NOT_YET_EVIDENCED / ADMIN GATE | “CMMC Level 2 (Self) award-time readiness is a mandatory capture gate to verify.” | “CMMC compliant/certified” without current official status |
| NP004-A024 | Worldshepherd has been independently code-reviewed at POC-A exact head | PR body says fresh independent review remains pending | NOT_YET_EVIDENCED | “Exact-head CI is green; independent review remains pending.” | “Review-clean”; “approved for merge” |

## Proposal sentence pattern

Use:

> **Capability + exact boundary + evidence state + next validation step.**

Example:

> “Worldshepherd has internally tested a synthetic APNT awareness/replay prototype that preserves a hash-linked source-to-operator decision trace while preventing platform execution; Phase I will extend this evidence base with representative ASPN/pntOS-conformant synthetic inputs, measured latency characterization, and an operator-facing navigation-style demonstration.”

Do not compress that sentence into a broader unsupported claim such as “Worldshepherd is an operational APNT C2 platform.”

## Evidence promotion rule

An assertion may move from `NOT_YET_EVIDENCED` or `IMPLEMENTED IN SOFTWARE` to `PROVEN INTERNALLY` only when all of the following are recorded:

1. exact commit SHA;
2. exact test/benchmark or workflow definition;
3. exact fixture/data/configuration identity and digest where applicable;
4. reproducible execution result;
5. environmental/runtime metadata needed to interpret performance;
6. negative/failure evidence;
7. claim text constrained to what the result actually measures;
8. independent review status.

External or Government claims require the corresponding partner/Government evidence and cannot be promoted by internal testing alone.
