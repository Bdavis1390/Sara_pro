# External Feedback → Gap Closure Ledger

Status: **candidate control** supporting issue #327.

## Purpose

Convert substantive external feedback into a durable, claims-controlled engineering and growth input.

An external statement such as “I cannot find an online presence,” “show me the evaluator package,” “this belongs in Phase II,” “you need a legal entity,” “the core technology still needs to be invented,” or “this is outside our charter” is useful only if Worldshepherd preserves the source, checks the criticism against current evidence, classifies the gap correctly, and routes it to an authoritative closure path.

The ledger prevents two opposite errors:

1. **dismissal error** — treating criticism as merely a rejection and failing to improve a real weakness;
2. **inflation error** — treating every external comment as proof that Worldshepherd should claim or build a capability it does not own.

## Gap classes

`REAL_INTERNAL_GAP`
: Worldshepherd can close the deficiency through software, documentation, process, packaging, or architecture work it legitimately owns.

`PROOF_SURFACE_GAP`
: capability/evidence may exist, but an outsider cannot inspect, reproduce, or understand it efficiently.

`POSITIONING_GAP`
: contribution, scope, maturity, or immediate ask is unclear or mismatched.

`PARTNER_GAP`
: the missing core capability belongs with a specialist partner, laboratory, prime, institution, hardware owner, or domain expert. Worldshepherd must not silently inherit that capability.

`EXTERNAL_VALIDATION_GAP`
: stronger maturity requires independent reproduction, physical measurement, qualified domain review, or another externally controlled evidence event.

`LEGAL_ENTITY_COMPLIANCE_GAP`
: the missing gate is corporate, legal, contractual, regulatory, registration, clearance, export-control, certification, or compliance evidence that software/CI cannot self-create.

`VENUE_SCOPE_MISMATCH`
: the work may be legitimate but the current standards body, solicitation, partner, or program is not the correct venue.

`NOT_A_WORLDSHEPHERD_GAP`
: the counterpart's timing, strategy, internal capability, procurement posture, or preference does not establish a Worldshepherd deficiency.

## Fail-closed classes

Open records classified as:

- `PARTNER_GAP`
- `EXTERNAL_VALIDATION_GAP`
- `LEGAL_ENTITY_COMPLIANCE_GAP`

are explicitly reported as **claim-promotion blockers** by the validator until the record is `CLOSED` with closure evidence.

This does not mean all work must stop. It means external language cannot silently cross the missing partner/validation/legal boundary.

## Record fields

Every record carries:

- stable `gap_id`;
- source organization, date, channel, opaque source reference, and source visibility;
- concise feedback summary;
- gap classification and confidence;
- `systemic_key` used to deduplicate recurring feedback across organizations;
- authoritative evidence checked before accepting the criticism;
- route issue(s);
- owner and concrete action;
- closure evidence;
- explicit claims effect;
- lifecycle status.

## Lifecycle

`INTAKE`
: feedback captured but not yet fully checked/routed.

`ROUTED`
: current evidence was checked and at least one authoritative issue/closure path was assigned.

`IN_PROGRESS`
: closure work is active.

`CLOSED`
: objective closure evidence exists. A closed record must include `closure_evidence`.

`REJECTED`
: the criticism was examined and rejected as inaccurate/inapplicable; rationale belongs in the action/claims-effect/evidence fields. Rejection does not erase the historical feedback.

`ROUTED`, `IN_PROGRESS`, and `CLOSED` records require at least one `route_issue_ref` so feedback cannot float without an owner.

## Privacy / publication rule

The public repository must **not** become a dump of private correspondence.

For real email, Slack, direct-message, partner, customer, counsel, or laboratory feedback:

- keep private source text and contact details in the authorized source system;
- use an opaque source reference in the ledger;
- paraphrase only the minimum technical/business feedback needed for routing;
- mark `source_visibility` accurately;
- do not commit email addresses, phone numbers, private message bodies, proprietary partner data, NDA material, CUI, export-controlled information, credentials, or personal data merely to prove that feedback occurred.

A public summary may state the engineering lesson without reproducing the private correspondence.

## Deduplication rule

`systemic_key` identifies recurring weaknesses across multiple sources. Examples:

- `public-credibility-front-door`
- `evaluator-ready-package`
- `bounded-contribution-and-ask`
- `independent-validation-depth`
- `legal-entity-eligibility`
- `partner-owned-core`
- `test-article-definition`
- `venue-fit`

A repeated systemic key raises priority; it does **not** manufacture additional independent validation.

Ten organizations saying “show independent validation” is strong evidence that independent validation is a market/readiness requirement. It is not ten independent validations.

## CLI

Validate and summarize a ledger:

```bash
python -m worldshepherd_sara.external_gap_ledger build/external-gap-ledger.json
```

Print JSON Schema:

```bash
python -m worldshepherd_sara.external_gap_ledger --schema
```

The summary includes:

- record count;
- canonical ledger SHA-256;
- counts by gap class;
- counts by systemic key;
- IDs of open fail-closed partner/validation/legal gaps.

Exit status is `2` when one or more fail-closed gap records remain open, otherwise `0`.

## Closure discipline

A gap closes only with evidence appropriate to the class.

Examples:

- public-presence gap → reviewed public evidence front door exists and an outsider can use it;
- evaluator-package gap → frozen package is reproducible by an independent evaluator;
- partner gap → qualified partner actually supplies/validates the missing core capability;
- legal-entity gap → authoritative entity/registration documentation exists;
- lab-validation gap → calibrated measured evidence and qualified review exist;
- positioning gap → the contribution/ask is rewritten and the counterpart can correctly identify the intended role;
- venue mismatch → work is routed to a genuinely aligned venue, not distorted to fit the original one.

## Claims boundary

The ledger records **feedback and closure state**. It is not itself proof that the external party is correct, a partner, a customer, an evaluator, an endorser, or an authority over Worldshepherd.

External feedback informs preparation. Evidence determines promotion.
