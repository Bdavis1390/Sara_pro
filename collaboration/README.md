# Worldshepherd Collaborator Intake v1

## Purpose

This lane turns public collaborator discovery and subsequent responses into a claims-controlled evidence process instead of an informal contact list.

A candidate may be discovered through Web3, WebP3, or another technical ecosystem, but Worldshepherd does not infer availability, consent, interest, employment status, partnership status, community membership, program acceptance, or permission to contact from public work alone.

## Evidence model

Each candidate record binds:

- stable internal candidate ID;
- display name and candidate type (`PERSON`, `TEAM`, or `ORG`);
- discovery source lane (`WEB3`, `WEBP3`, or `OTHER`);
- technical domains;
- Worldshepherd lane mapping;
- at least two distinct public evidence references;
- public contact/collaboration surfaces when present;
- observation and verification dates; and
- an optional source-resolution note.

Verification state is deliberately separate from the semantic candidate digest. A record can be re-verified without silently changing who or what the record describes.

## Candidate states

`INSUFFICIENT_PUBLIC_CANDIDATE_EVIDENCE`

The candidate lacks one or more required evidence predicates.

`EVIDENCED_CANDIDATE_FOR_HUMAN_REVIEW`

Public identity, technical work, freshness, technical-domain mapping, Worldshepherd relevance, and multi-source evidence are present. This means the candidate is worth human review only.

`EVIDENCED_CANDIDATE_FOR_OUTREACH_HUMAN_REVIEW`

The candidate is already review-ready, a public collaboration surface exists, and conflict screening has completed without a known conflict. Even this state does **not** authorize outreach.

## Response evidence states

`WS-COLLAB-RESPONSE-V1` classifies what happened after an authorized outreach action without copying private message bodies into the public repository. The semantic record keeps only an opaque source-system evidence reference, candidate binding, response class, observation time, and channel.

Supported response classes are:

- `NO_RESPONSE_YET`;
- `ROUTED_TO_PUBLIC_FORUM`;
- `COMMUNITY_CHANNEL_INVITE_AVAILABLE`;
- `PROGRAM_ELIGIBILITY_CRITERIA_RECEIVED`;
- `PAID_REVIEW_AVAILABLE`;
- `SCOPE_DISCUSSION_AVAILABLE`;
- `COLLABORATION_INTEREST_EXPRESSED`;
- `DECLINED`; and
- `UNDELIVERABLE_OR_CHANNEL_CLOSED`.

A valid response still cannot authorize spending, broaden outreach, establish teammate/employment/partnership status, establish community/program membership, or imply endorsement or technical validation.

Routing rules remain bounded:

- a public-forum referral routes only to the referred public forum;
- a community invite routes only to human channel-join review;
- program eligibility criteria route only to human eligibility-gap review;
- paid-review availability routes only to human budget/scope review; and
- an expression of collaboration interest routes only to human relationship review.

An invitation does not prove that a community account was created or joined. Program criteria do not prove eligibility, acceptance, or membership. A vendor/program response does not validate Worldshepherd software, hardware, interoperability, or deployment claims.

Private message content, quoted prices, addresses, telephone numbers, and personal notes are intentionally excluded from the response digest. The authoritative communication remains in its source system.

## Hard authority boundary

Candidate decisions hard-code:

```text
human_review_required = true
outreach_authorized = false
teammate_relationship_established = false
employment_offer_authorized = false
partnership_authorized = false
```

Response decisions additionally hard-code:

```text
budget_commitment_authorized = false
outreach_expansion_authorized = false
teammate_relationship_established = false
employment_relationship_established = false
partnership_established = false
community_membership_established = false
program_membership_established = false
technical_validation_established = false
```

The corresponding claims boundary also keeps these interpretations false:

```text
invite_implies_membership = false
eligibility_criteria_imply_acceptance = false
program_contact_implies_technical_validation = false
```

Public evidence or a reply never becomes consent, spending authority, membership, validation, or a relationship by inference.

## Web3 seed

`web3_candidate_seed_2026-09-15.json` currently captures public evidence for technically relevant people/teams working in areas such as post-quantum cryptography, Bitcoin PQ migration, Ethereum PQ interoperability, auditable cryptographic libraries, and Lean Ethereum tooling.

The seed is a research snapshot. It is not an endorsement or ranked recruiting list, and every record must be re-verified before any future outreach review.

## WebP3 resolution

The exact public term **WebP3** is currently treated as ambiguous/low relevance rather than silently equated with Web3. Current public search primarily resolves to an unrelated Python music-server project. A separate sparse business reference describes a Webp3 company working on websites/apps/Web3 products, but no attributable technical personnel were verified from sufficiently strong public evidence.

Therefore no `WEBP3` teammate candidate is promoted in the seed. The source remains open for future verification.

## Worldshepherd mapping

- **ECHO:** preserve public source provenance, response evidence references, and verification dates.
- **PRIME:** enforce evidence, freshness, conflict-screen, response classification, membership/validation boundaries, and authority boundaries.
- **SARA:** orchestrate human review, eligibility-gap review, channel-join review, budget/scope review, and any separately authorized outreach workflow.
- **OVERWATCH:** monitor stale evidence, unresolved conflicts, duplicate candidates, pending responses, invitation/application state, and source ambiguity.
- **QCRYPTO:** supplies technical fit context for cryptography/PQC candidates.

## Claims state

`IMPLEMENTED IN SOFTWARE / EXTERNAL RELATIONSHIPS AND MEMBERSHIPS NOT ESTABLISHED`
