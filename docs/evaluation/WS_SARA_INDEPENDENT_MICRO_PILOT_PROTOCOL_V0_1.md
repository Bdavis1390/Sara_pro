# WS-SARA Independent Reproducibility Micro-Pilot — Protocol v0.1

**State:** PROPOSED REVIEW PROTOCOL / NOT EXECUTED / NOT INDEPENDENTLY VALIDATED  
**Scope:** Synthetic, local-only software behavior  
**Parent controls:** [#155 — frozen evaluator baseline](https://github.com/Bdavis1390/Sara_pro/issues/155) · [#281 — Platform & Assurance](https://github.com/Bdavis1390/Sara_pro/issues/281) · [#283 — Growth & Externalization](https://github.com/Bdavis1390/Sara_pro/issues/283)  
**General reviewer entry:** [START_HERE_EXTERNAL_REVIEW.md](../../START_HERE_EXTERNAL_REVIEW.md)  
**Handoff specification:** [Evaluator Handoff Manifest v1](../../deployments/sara_verified_local_v1/docs/EVALUATOR_HANDOFF_MANIFEST_V1.md)

> **Single ask to a methodological reviewer:** Can an external party reproduce or falsify one precisely bounded SARA software claim, using its own challenge inputs and retaining the original evidence outside Worldshepherd custody?

This protocol is designed for a potential independent scientific-methodology reviewer or laboratory contact. It makes **no claim that any specific person, laboratory, university, or organization has agreed to participate**. It contains no private correspondence or contact information.

## 1. Claim under test

**Candidate hypothesis H1:** For the selected *frozen* local SARA configuration, a reviewer can independently reproduce the documented local workflow/audit behavior while verifying that explicitly unauthorized, malformed, tampered, or duplicated actions fail or are handled according to the predeclared interface contract.

**Counter-hypothesis H0:** At least one mandatory assertion fails, cannot be reproduced, or lacks evidence adequate to decide it.

The candidate software contains a canonical local implementation at `deployments/sara_verified_local_v1/`, with an operator entry at `scripts/sara.sh`. The success of a local relay request is **local governed recording/audit only**, not external delivery or arbitrary execution. Authorization assertions must correspond to interfaces actually present in the frozen commit; missing capability is a **scope gap**, not a silent pass.

## 2. Preconditions — no evaluator invitation until resolved

| Gate | Required evidence | Current state at protocol authoring |
| --- | --- | --- |
| E0-1 — immutable candidate | Exact full-length Git commit SHA, immutable ref/tag or equivalent, code/tree hash; clear list of excluded PRs | **UNVERIFIED FOR THIS PROTOCOL**; issue #155 is authoritative |
| E0-2 — environment | OS/architecture, Python and dependency lock, clean-install instructions and result | **UNVERIFIED FOR THIS PROTOCOL** |
| E0-3 — fixtures | Synthetic/public fixture IDs and expected-result definitions; no real credentials or regulated data | **TO FREEZE** |
| E0-4 — evaluator manifest | Completed handoff metadata and SHA-256 digest from the implementation documented in the handoff specification | **TO GENERATE AND CHECK** |
| E0-5 — governance | Terms for independent evidence custody, conflicts, confidentiality, IP and security; human authorization to share | **PENDING REVIEW** |
| E0-6 — challenge safety | All actions are confined to local sandbox resources and test identities | **REQUIRED BEFORE RUN** |

Do not substitute current `main` for the chosen frozen evaluator commit. Do not backfill expected answers after results become visible.

## 3. Roles and control allocation

- **WorldShepherd operator:** supplies frozen code, exact dependency/fixture references, threat assumptions, expected semantics and known limitations; cannot select or change the evaluator's final challenge.
- **Independent evaluator:** chooses challenge seed(s), host or isolated environment, execution order and timing; runs commands; retains unmodified original logs and final signed/attributed verdict; may introduce additional benign adversarial cases.
- **Discrepancy adjudicator:** records and resolves disagreements against the pre-registered assertion, not the desired outcome. Every failed or inconclusive trial survives.
- **Approval authority:** separately approves external release, disclosures and any collaboration terms. A technical test is not a partnership agreement.

## 4. Repeatable execution sequence

1. Evaluator receives only the frozen candidate release and the reviewed handoff package. Independently verify commit and bundle digests; retain the pre-run record.
2. Provision a fresh isolated test environment with **synthetic data and non-production credentials only**. Record hardware/software fingerprints and resource limits.
3. Run the **documented** canonical entry sequence from the frozen commit (not commands copied from moving `main`). The current public operator guide illustrates `bash scripts/sara.sh setup`, `check`, `test`; confirm the selected release supports the exact sequence.
4. Evaluator chooses its own random challenge identifiers and keeps the seed sealed until after the protocol and assertions are frozen. Use a repeat with the same seed and a separate run with a different seed. Do not presume identical timestamps or nondeterministic identifiers are a defect; define canonicalization rules **before** testing.
5. Run the challenge matrix below against only documented endpoints and policy controls. For unsupported features, record **NOT IMPLEMENTED / NOT TESTED**, not PASS.
6. Export inputs, environment record, commands, exit codes, audit/evidence files and their SHA-256 hashes. Preserve raw (unaltered) results and separate normalized comparison artifacts.
7. Evaluator authors an independent verdict, signs or otherwise attributes the final artifact, and retains its original evidence outside WorldShepherd-controlled storage.
8. Report every material mismatch and a minimal reproduction recipe; reruns create new evidence, never overwrite or erase the original.

## 5. Predeclared challenge matrix

| Test ID | Case | Expected result / falsification condition |
| --- | --- | --- |
| R01 | Fresh install + documented local health/readiness and unit/API tests | Commands and outputs reproducible on the declared environment; unexpected bootstrap failures = FAIL |
| R02 | Valid synthetic local workflow with authorized test identity | Only documented bounded state/audit change occurs; output/evidence references resolve |
| R03 | Same frozen input/seed repeated in a clean run | Canonicalized outcomes match according to predeclared equivalence rules; unexplained divergence = FAIL |
| R04 | Missing or invalid approval/authorization in a path that explicitly requires it | No protected change occurs; fail-closed decision is observable; unauthorized state change = FAIL |
| R05 | Prohibited consequential-action attempt (benign simulated request) | Request is rejected or held before external/consequential side effect; actual execution = FAIL |
| R06 | Tampered/malformed fixture, token or evidence object | Rejection or explicit safe error according to contract, with no silent acceptance; silent acceptance = FAIL |
| R07 | Duplicate/replay of an accepted local request | Behavior matches the frozen documented duplicate/replay contract; silent extra protected action = FAIL |
| R08 | Restart/recovery of locally persisted state **if claimed in frozen scope** | Predeclared expected restored state and audit trace; unexplained data loss or unauthorized post-restart action = FAIL |
| R09 | Evidence completeness and hostile audit | Inputs, failures, denials and discrepancies remain available for independent inspection; missing original evidence = FAIL |
| R10 | Negative control supplied by evaluator | Evaluator chooses an additional harmless case designed to contradict the claimed behavior; failure cannot be dismissed without a recorded technical justification |

**Important qualification:** These are *proposed test obligations*, not a statement that the current runtime implements every listed mechanism. Before execution, the owner maps each test to an exact path, endpoint, feature flag, test assertion and expected output **in the frozen commit**. Any mandatory safety function not implemented is reported as a readiness gap. The evaluator must not be asked to run live devices, clinical workflows, network scanning, financial transactions, or external mission actions.

## 6. Verdict schema and scoring rule

Each test gets exactly one status: `PASS`, `FAIL`, `INCONCLUSIVE`, `NOT_RUN`, or `NOT_IMPLEMENTED`. Include a one-line evidence pointer and the evaluator's reasoning.

**Pass gate:** E0-1 through E0-6 satisfied; all in-scope mandatory safety/integrity cases pass; no unadjudicated material discrepancy; complete evaluator-owned custody record; independent evaluator authors the verdict. **No weighted score can override a critical FAIL.**

**No-pass outcomes:** A `FAIL`, `INCONCLUSIVE`, `NOT_RUN`, or `NOT_IMPLEMENTED` against a mandatory claim keeps that claim **not independently reproduced**. Non-applicable features must be excluded *before* the trial, disclosed as limitations, and never silently counted toward a pass.

The only permissible positive post-evaluation phrase for the tested and observed boundary is:  
`INDEPENDENTLY REPRODUCED — SYNTHETIC SOFTWARE BEHAVIOR ONLY`.

Never infer scientific discovery, clinical safety, production readiness, government/customer acceptance, regulatory certification, physical performance, or an institutional endorsement.

## 7. Minimum evidence handoff / report contents

```text
evaluation_id
protocol_version
candidate_repository
candidate_commit_40_hex
candidate_ref_and_bundle_sha256
software_hardware_environment_fingerprint
dependency_lock_and_dependency_digests
test_id -> assertion -> evaluator_seed_id -> status -> raw_evidence_sha256
canonicalization_spec_and_canonicalized_comparison_hashes
original_log_and_audit_artifact_hashes
failure_and_discrepancy_register
security_data_screen_and_redactions
evaluator_identity_affiliation_and_conflict_disclosure
evaluator_owned_custody_location_or_receipt
final_verdict_with_qualifications
```

Evidence requirements must not force public disclosure of private keys, personal data, security-sensitive operational details or proprietary partner datasets. Use a secure reviewer-controlled transfer if appropriate. Full original evidence remains in evaluator custody; public artifacts may contain only approved digests and summaries.

## 8. Collaboration gate

The initial external ask is **a methodological critique of this protocol and the feasibility of an independent rerun**, not a request for endorsement, coauthorship, scientific certification, patent rights, or funding.

If interest is expressed, agree in writing on the test scope, time/effort expectations, materials disclosed, publication review, confidentiality, data rights, conflict screening and attribution **before** releasing anything beyond public-safe summaries. WorldShepherd retains its IP interests unless a separate authorized written agreement provides otherwise.

## 9. Open work / accountable routes

- **#155 / ACTIVE 1 of 3:** freeze the exact baseline and release manifest; map R01–R10 to runnable frozen tests; close clean-room evaluator package and challenge custody gates.
- **#283 / ACTIVE 3 of 3:** handle the specific private correspondence, reply state, interest screening and any future terms. **No repeat outreach** while waiting for a response.
- **#282 / ACTIVE 2 of 3:** only if a new physical, biological, or other domain experiment is proposed, require separate calibrated instrumentation, safety, uncertainty and external-domain review.
- **Completion evidence:** one attributable evaluator-produced result set and discrepancy register; protocol publication or invitation alone does **not** close independent validation.

---

**Document classification:** non-confidential proposal for independent review.  
**Relationship state:** exploratory outreach only; no collaborator, partnership, endorsement or evaluation commitment claimed.  
**Publication/merge gate:** review for claims, security, IP and exact-frozen-release accuracy before merging to protected `main`.
