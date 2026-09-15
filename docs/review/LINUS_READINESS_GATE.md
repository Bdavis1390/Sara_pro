# Linus / senior systems reviewer readiness gate

Status is binary: **HOLD** or **READY_FOR_ONE_REVIEW_REQUEST**.

This gate does not predict whether Linus Torvalds, the Linux Foundation, AAIF, or any other reviewer will respond. It controls whether Worldshepherd has earned the right to make one concise criticism-first request without wasting the reviewer's time.

## Gate A — exact artifact

- [ ] Record the exact PR #279 head commit in the outbound review note.
- [ ] All required checks are green on that exact commit.
- [ ] No uncommitted/local-only fix is described as part of the review target.
- [ ] The review packet links to the narrow SARA implementation rather than requiring the broader research tree.

Any failure => **HOLD**.

## Gate B — clean-room reproduction

From a fresh clone and ordinary documented prerequisites, an evaluator can:

- [ ] check out the exact review commit;
- [ ] create the environment and install the review package using the documented commands;
- [ ] run the package test suite successfully;
- [ ] compile the package;
- [ ] render the Docker Compose configuration using test-only placeholder configuration;
- [ ] identify the supported local-only/single-writer topology without hidden operator knowledge.

The reproducer must record OS, architecture, runtime versions, exact commit, command transcript, failures, and deviations.

Any undocumented intervention required to obtain a pass => **HOLD** until documented or removed.

## Gate C — hostile trust-boundary review

The review packet must preserve known limitations and demonstrate negative cases for the stated boundary:

- [ ] relay credentials do not become administrator authority through the supported HTTP/API surface;
- [ ] protected registry/state cannot be mutated through the generic write path;
- [ ] missing/invalid authorization fails closed where authorization is required;
- [ ] replay, identity/environment misbinding, and signing-key replacement are tested or explicitly bounded;
- [ ] recorded PRIME authorization is bound to exact signing-key material, not only a reusable key ID;
- [ ] malformed/corrupt durable state is not silently converted into successful authorization;
- [ ] the local relay/record path is not described as arbitrary external command execution;
- [ ] JSONL/application logs are not described as immutable/tamper-proof;
- [ ] current persistence semantics are not described as multi-writer/distributed safe.

A discovered defect does not automatically make the project unreviewable. An **undisclosed or hand-waved** defect does.

## Gate D — maintainability and simplification

Before external review, Worldshepherd must be willing to delete its own abstractions.

- [ ] Reviewer questions explicitly invite replacement by existing policy/evidence/observability standards.
- [ ] SARA/PRIME/ECHO/OVERWATCH names are treated as implementation labels, not proof of architectural necessity.
- [ ] No component is protected from criticism because it is strategically important to the broader Worldshepherd narrative.
- [ ] The review can conclude "this should be much smaller" or "use an existing project" and still count as success.

## Gate E — claims and legal/IP language

- [ ] README and review documents distinguish internal software evidence from external validation/certification.
- [ ] No physical, scientific, government, customer, partner, or compliance claim is inferred from CI.
- [ ] No Linus/Linux Foundation/AAIF review, endorsement, adoption, partnership, or interest is claimed before it actually exists.
- [ ] Public inspectability is not called open-source licensing while the license decision remains unresolved.
- [ ] The outbound request contains no confidential, controlled, CUI, classified, export-controlled, partner-proprietary, credential, or secret material.

## Gate F — outreach discipline

Only after A-E pass:

- [ ] Send **one** short request for technical criticism.
- [ ] Link the exact reviewer entry point and exact commit/PR.
- [ ] Ask for falsification/simplification, not endorsement.
- [ ] Do not lead with funding, valuation, defense pipeline, speculative science, or partnership economics.
- [ ] Do not send repeated unsolicited follow-ups.
- [ ] If substantive criticism arrives, route every technical finding to ACTIVE 1/3 (#281), retain the negative evidence, patch if justified, and rerun before making any stronger claim.

## Partnership threshold

A partnership/upstream-contribution discussion belongs to ACTIVE 3/3 (#283) **only after** an external reviewer independently indicates that at least one component solves a legitimate systems problem or could usefully integrate with an existing ecosystem.

No response, a rejection, or a recommendation to delete/replace the architecture is not a failed outreach operation. It is evidence about product/architecture fit.

## Decision record

```text
review_commit: <exact SHA>
required_checks: PASS | FAIL | PENDING
clean_room_reproduction: PASS | FAIL | PENDING
hostile_review_disposition: PASS | FAIL | PENDING
claims_legal_boundary: PASS | FAIL | PENDING
outreach_decision: HOLD | READY_FOR_ONE_REVIEW_REQUEST
reviewer_contacted: NO | YES
external_review_received: NO | YES
partnership_discussion_authorized: NO | YES
```

Default values are `PENDING`, `HOLD`, `NO`, `NO`, `NO`.

The gate may only move to `READY_FOR_ONE_REVIEW_REQUEST` from objective evidence tied to the exact outbound review commit.