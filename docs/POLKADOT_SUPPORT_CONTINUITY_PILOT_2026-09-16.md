# Worldshepherd × Polkadot Support Continuity Pilot

**Status:** independent, unofficial pilot for public technical and community review  
**Date:** 2026-09-16  
**Live pilot:** https://worldshepherd-polkadot-support.floot.app

## Purpose

The former centralized Official Polkadot Support operation has announced that it is being wound down and has directed users toward Polkadot community channels. Worldshepherd / SARA has deployed a small independent support-continuity pilot to test whether an auditable, non-custodial community support layer can complement the existing Polkadot Forum, Discord, documentation, and governance ecosystem.

This pilot does **not** claim affiliation with, endorsement by, or replacement of Web3 Foundation, Parity Technologies, the Polkadot Community Foundation, or the former Official Polkadot Support operation.

## Implemented pilot capabilities

- persistent support-case creation
- unique `WS-DOT-*` case identifiers
- database-backed case storage
- public case-status lookup
- topic routing for wallet/transaction, staking, governance, developer, security, and general requests
- explicit anti-scam and custody boundaries
- authenticated operator access
- admin-only case queue and response controls
- controlled case-state transitions
- operator action audit events
- mobile-responsive public interface

## Non-custodial boundary

The service is designed around a hard rule: support personnel do not require or request a seed phrase, recovery phrase, mnemonic, private key, password, one-time code, or secret file. Case content is not authorization to sign transactions, move assets, control an account, or take custody of user funds.

Submissions containing apparent secret material are rejected where detected. The user-facing interface repeats the custody boundary prominently.

## Case lifecycle

Current states:

`new → triaged → in_review → waiting_user → resolved → closed`

Each operator update records an auditable event containing the case identifier, actor where available, prior status, new status, public response state, and timestamp.

## Intended ecosystem role

The pilot is not intended to become a new centralized authority. Its proposed role is a continuity and triage layer that can:

1. direct users toward authoritative Polkadot resources;
2. retain a traceable case ID for unresolved issues;
3. distinguish documentation questions from security incidents, protocol/developer questions, governance questions, and wallet/transaction problems;
4. make support actions reviewable rather than opaque;
5. preserve a strict non-custodial boundary; and
6. escalate issues to the appropriate existing community or technical venue rather than pretending to be authoritative on every topic.

## Threat model and review questions

Community review is specifically requested on the following failure modes:

- impersonation of official Polkadot support
- social-engineering attempts against users or operators
- accidental collection of secrets or excessive personal data
- malicious or misleading public reference links
- operator account compromise
- abusive or spam case creation
- unsafe advice on wallet recovery, asset transfer, staking, governance, or transaction troubleshooting
- inaccurate routing to technical/community resources
- insufficient auditability of operator actions
- privacy and retention obligations
- duplication of existing Discord, Forum, documentation, or ecosystem-support efforts

## Claims discipline

### Implemented in software / internally verified

- support intake
- persistent case IDs
- database persistence
- public case lookup
- role-protected operator APIs
- operator case queue
- case-state updates
- audit-event persistence
- production deployment

### Requires ecosystem / partner validation

- suitability for Polkadot community use
- completeness of threat controls
- interoperability with current support channels
- operator staffing model
- escalation agreements
- data-retention policy
- abuse-response process
- community-governance fit

### Not claimed

- official Polkadot status
- Web3 Foundation endorsement
- Parity Technologies endorsement
- Polkadot Community Foundation endorsement
- authority over wallets, accounts, transactions, governance decisions, or funds
- replacement of authoritative protocol documentation

## Proposed 90-day evaluation framework

Before any request for broad deployment or material funding, the pilot should be evaluated against measurable criteria such as:

- median first-response time
- median time to resolution
- percentage of cases resolved without escalation
- percentage correctly routed to authoritative resources
- repeat-contact rate
- security/scam cases safely handled
- rejected secret-bearing submissions
- unresolved-case aging
- operator action provenance completeness
- substantiated user complaints
- cost per resolved case
- evidence of duplication or conflict with existing ecosystem support

The pilot should be stopped or redesigned if it creates material custody risk, increases impersonation/scam risk, produces unreliable advice, or fails to add measurable value beyond existing community channels.

## Public-review request

We are asking the Polkadot ecosystem to challenge this pilot before any attempt at scaling it. Useful review includes:

- architecture and threat-model criticism
- identification of existing support functions this duplicates
- recommendations for authoritative escalation paths
- privacy/data-minimization requirements
- community moderation and anti-abuse requirements
- whether a Forum discussion, OpenGov pre-proposal, bounty, PCF feasibility process, or no governance action at all is the appropriate next step

No endorsement or funding is assumed by publication of this document.

## Contact

Brandon Ray Davis  
Worldshepherd / SARA  
GitHub: https://github.com/Bdavis1390
