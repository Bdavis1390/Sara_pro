# Worldshepherd Collaborator Intake v1

## Purpose

This lane turns public collaborator discovery into a claims-controlled evidence process instead of an informal contact list.

A candidate may be discovered through Web3, WebP3, or another technical ecosystem, but Worldshepherd does not infer availability, consent, interest, employment status, partnership status, or permission to contact from public work alone.

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

## Hard authority boundary

Every decision hard-codes:

```text
human_review_required = true
outreach_authorized = false
teammate_relationship_established = false
employment_offer_authorized = false
partnership_authorized = false
```

Public evidence never becomes consent or a relationship by inference.

## Web3 seed

`web3_candidate_seed_2026-09-15.json` currently captures public evidence for technically relevant people/teams working in areas such as post-quantum cryptography, Bitcoin PQ migration, Ethereum PQ interoperability, auditable crypto libraries, and Lean Ethereum tooling.

The seed is a research snapshot. It is not an endorsement or ranked recruiting list, and every record must be re-verified before any future outreach review.

## WebP3 resolution

The exact public term **WebP3** is currently treated as ambiguous/low relevance rather than silently equated with Web3. Current public search primarily resolves to an unrelated Python music-server project. A separate sparse business reference describes a Webp3 company working on websites/apps/Web3 products, but no attributable technical personnel were verified from sufficiently strong public evidence.

Therefore no `WEBP3` teammate candidate is promoted in the seed. The source remains open for future verification.

## Worldshepherd mapping

- **ECHO:** preserve public source provenance and verification dates.
- **PRIME:** enforce evidence, freshness, conflict-screen, and authority boundaries.
- **SARA:** orchestrate human review and any separately authorized outreach workflow.
- **OVERWATCH:** monitor stale evidence, unresolved conflicts, duplicate candidates, and source ambiguity.
- **QCRYPTO:** supplies technical fit context for cryptography/PQC candidates.

## Claims state

`IMPLEMENTED IN SOFTWARE / EXTERNAL RELATIONSHIPS NOT ESTABLISHED`
