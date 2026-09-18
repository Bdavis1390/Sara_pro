# WS-SDA G6 — PRIME-Signed Analytic Release Authorization

Status: **IMPLEMENTED IN SOFTWARE ON STACKED BRANCH — CI NOT YET EXECUTED**
Date: 2026-09-18
Branch: `feature/ws-sda-release-authz-g6-20260918`
Parent stack: G1/G2 -> G4A -> G5

## 1. Objective

G6 closes the authorization gap between an internally produced hypothesis/evidence
package and its bounded dissemination.

The authorization is for one action only:

`DISSEMINATE_ANALYTIC_EVIDENCE`

It is not an actuation, targeting, weapon-employment, or operational-track-selection
authorization.

## 2. Signed semantics

The PRIME Ed25519 signature binds:

- authorization ID;
- exact hypothesis-set digest;
- exact payload digest;
- exact policy-revision digest;
- destination;
- sorted releasability tags;
- identified human approval ID;
- identified human approver;
- issuance and expiration time;
- nonce;
- signing-key ID.

Maximum lifetime is five minutes.

## 3. Verification-to-use binding

After signature verification, the release candidate is checked again immediately
before consumption.

Any mutation of:

- payload;
- hypothesis set;
- policy revision;
- destination;
- releasability tags

fails closed.

This explicitly addresses the verification/execution TOCTOU gap.

## 4. Replay/consumption state

`consume_sda_release_authorization` prepares a one-time receipt and consumption
registry patch keyed by authorization ID.

The function is deliberately documented as transaction-dependent: cross-process
exactly-once semantics are only claimed when this check-and-write executes inside
SARA's durable serialized registry transaction. A plain Python dict call is not
misrepresented as a distributed lock.

## 5. Human authority

The assertion schema requires non-empty `human_approval_id` and
`human_approver`.

AI/software may prepare the candidate evidence. G6 does not infer approval from the
existence of a hypothesis, high confidence, source count, policy match, or PRIME
signature alone.

## 6. Negative gates

The test candidate rejects:

- signature tampering of authority-relevant fields;
- payload mutation after verification;
- hypothesis-set mutation;
- policy-revision mutation;
- destination mutation;
- releasability mutation;
- expired authorization;
- excessive future issuance;
- revoked signing key;
- authorization reuse;
- use after expiration even if verification occurred earlier;
- overlong authorization lifetime;
- missing human approval identity;
- unsorted/duplicate release tags.

## 7. Claims boundary

A passing G6 reference suite establishes software-level signed authorization binding
and one-time consumption behavior within the SARA transaction boundary.

It does not establish:

- external delivery or recipient acceptance;
- correctness of an operational orbit/track;
- targeting;
- weapon cueing;
- autonomous consequential release;
- HSM/KMS production key custody;
- independent approval;
- customer/government authorization or accreditation.

## 8. Next gates

1. wire the consumption patch through the durable SARA transaction and ECHO event
   path;
2. bind the receipt into mission replay/DDIL reconciliation;
3. exercise disconnect/rejoin behavior under G7;
4. freeze the G8 adversarial corpus around G1-G7;
5. preserve human authority at every consequential release boundary.
