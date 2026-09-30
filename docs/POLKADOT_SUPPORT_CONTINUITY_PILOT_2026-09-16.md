# Worldshepherd × Polkadot Support Continuity Pilot

**Status:** independent, unofficial pilot for public technical and community review  
**Date:** 2026-09-16  
**Operational update:** 2026-09-17  
**Live pilot:** https://worldshepherd-polkadot-support.floot.app

## Purpose

The former centralized Official Polkadot Support operation has announced that it is being wound down and has directed users toward Polkadot community channels. Worldshepherd / SARA has deployed a small independent support-continuity pilot to test whether an auditable, non-custodial community support layer can complement the existing Polkadot Forum, Discord, documentation, and governance ecosystem.

This pilot does **not** claim affiliation with, endorsement by, or replacement of Web3 Foundation, Parity Technologies, the Polkadot Community Foundation, or the former Official Polkadot Support operation.

## Implemented pilot capabilities

- persistent support-case creation
- unique `WS-DOT-*` case identifiers
- database-backed case storage
- private case-status access using a case ID plus a separate status access key; only a one-way hash of the access key is stored
- deterministic safety-first automatic triage
- explicit routine/elevated/urgent priority classification
- automatic high-risk security/scam escalation flags without auto-closing those cases
- topic routing for wallet/transaction, staking, governance, developer, security, and general requests
- explicit anti-scam and custody boundaries
- rejection of submissions that contain recognized secret-material indicators
- per-email and per-network-source intake rate limits
- authenticated operator access
- admin-only case queue and response controls
- controlled case-state transitions
- operator action audit events
- operator-visible automated-triage reason and next-action record
- optional Discord operations bridge using a bot account and metadata-only alerts
- mobile-responsive public interface
- machine-readable readiness endpoint at `/_api/system/readiness`

## Bounded self-operational mode

As of 2026-09-17, the core intake path can operate without continuous operator intervention. New cases are persisted, assigned a case identifier, issued a private status access key, classified by deterministic rules, given an immediate safety-bounded response, assigned a next action, and recorded in the audit trail.

The automation is deliberately bounded. It does **not** automatically resolve security-sensitive, ambiguous, or high-risk cases. Security/scam indicators are marked `urgent` and `human_required`; general unclassified requests are marked `elevated` and `human_required`. Routine staking, governance, developer, and non-risk wallet cases can receive immediate documentation-oriented guidance but remain open rather than being silently closed.

The current readiness endpoint explicitly distinguishes core automation from optional/human layers. At the time of this update, core intake, deterministic triage, secure status lookup, secret-material rejection, and abuse-rate controls are operational. Initial Worldshepherd administrator activation and the optional Discord escalation transport remain separate readiness gates and are not falsely represented as active until configured.

## Non-custodial boundary

The service is designed around a hard rule: support personnel and automated workflows do not require or request a seed phrase, recovery phrase, mnemonic, private key, password, one-time code, or secret file. Case content is not authorization to sign transactions, move assets, control an account, vote, or take custody of user funds.

Submissions containing apparent secret material are rejected where detected. The user-facing interface repeats the custody boundary prominently. Automated responses are constrained to evidence collection, authoritative documentation paths, case routing, and explicit escalation rather than asset-transfer or signing instructions.

## Case lifecycle

Current states:

`new → triaged → in_review → waiting_user → resolved → closed`

The self-operational intake currently places newly classified cases into `triaged`; it does not claim that triage equals resolution.

Each operator update records an auditable event containing the case identifier, actor where available, prior status, new status, public response state, and timestamp. Automated case creation records a distinct `case_created_auto_triaged` event.

## Status-access security

Public status lookup no longer relies on knowledge of a case ID alone. New cases receive a separate high-entropy status access key. The service stores a SHA-256 hash of that key and requires both the case ID and original key for public status retrieval. Invalid keys are rejected. The raw status key is displayed to the requester at case creation and is not retained in recoverable form by the public lookup workflow.

This is intended to reduce accidental disclosure if a case identifier is leaked or guessed. It is not claimed as a substitute for a full privacy or security audit.

## Abuse controls

The public intake path now applies bounded rate limits before creating a case: recent submissions are limited per email address and per hashed network source. Raw source IP addresses are not stored in the case record; the current implementation derives a one-way source hash for rate-control purposes.

These controls reduce basic spam/flooding risk but are not claimed to defeat distributed abuse, disposable identities, coordinated attacks, or sophisticated denial-of-service behavior. Those remain ecosystem-validation requirements.

## Intended ecosystem role

The pilot is not intended to become a new centralized authority. Its proposed role is a continuity and triage layer that can:

1. direct users toward authoritative Polkadot resources;
2. retain a traceable case ID for unresolved issues;
3. distinguish documentation questions from security incidents, protocol/developer questions, governance questions, and wallet/transaction problems;
4. make automated and human support actions reviewable rather than opaque;
5. preserve a strict non-custodial boundary; and
6. escalate issues to the appropriate existing community or technical venue rather than pretending to be authoritative on every topic.

## Threat model and review questions

Community review is specifically requested on the following failure modes:

- impersonation of official Polkadot support
- social-engineering attempts against users or operators
- accidental collection of secrets or excessive personal data
- malicious or misleading public reference links
- operator account compromise
- abuse of automated triage rules
- abusive or spam case creation
- unsafe advice on wallet recovery, asset transfer, staking, governance, or transaction troubleshooting
- inaccurate routing to technical/community resources
- insufficient auditability of automated or operator actions
- privacy and retention obligations
- duplication of existing Discord, Forum, documentation, or ecosystem-support efforts

## Claims discipline

### Implemented in software / internally verified

- support intake
- persistent case IDs
- database persistence
- hashed status-access-key lookup
- deterministic auto-triage
- urgent/high-risk escalation classification
- anti-secret rejection boundary
- intake rate limiting
- role-protected operator APIs
- operator case queue
- case-state updates
- audit-event persistence
- readiness reporting
- optional Discord bridge code path
- production deployment

### Requires ecosystem / partner validation

- suitability for Polkadot community use
- completeness of threat controls
- correctness and usefulness of automated routing rules
- interoperability with current support channels
- operator staffing model
- escalation agreements
- data-retention policy
- abuse-response process
- community-governance fit
- independent security/privacy review

### Not claimed

- official Polkadot status
- Web3 Foundation endorsement
- Parity Technologies endorsement
- Polkadot Community Foundation endorsement
- authority over wallets, accounts, transactions, governance decisions, or funds
- replacement of authoritative protocol documentation
- complete secret detection
- complete anti-abuse protection
- autonomous handling of security-sensitive cases

## Proposed 90-day evaluation framework

Before any request for broad deployment or material funding, the pilot should be evaluated against measurable criteria such as:

- median first-response time
- median time to resolution
- percentage of cases resolved without escalation
- percentage correctly routed to authoritative resources
- automated-triage false-positive and false-negative rates
- repeat-contact rate
- security/scam cases safely handled
- rejected secret-bearing submissions
- rejected abusive/rate-limited submissions
- unresolved-case aging
- operator action provenance completeness
- substantiated user complaints
- cost per resolved case
- evidence of duplication or conflict with existing ecosystem support

The pilot should be stopped or redesigned if it creates material custody risk, increases impersonation/scam risk, produces unreliable advice, misclassifies security incidents at an unacceptable rate, or fails to add measurable value beyond existing community channels.

## Public-review request

We are asking the Polkadot ecosystem to challenge this pilot before any attempt at scaling it. Useful review includes:

- architecture and threat-model criticism
- review of the deterministic triage rules and escalation boundaries
- analysis of the status-access-key design and privacy model
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
