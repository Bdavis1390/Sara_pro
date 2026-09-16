# Worldshepherd External Correspondence Claims Lint v1

Status: **candidate control on a stacked review branch**. This document and implementation do not alter the evidence state of any Worldshepherd capability.

## Purpose

Extend the existing PVK claims-linter behavior to outbound emails, capability briefs, partner notes, proposal fragments, public profile copy, and other externally released text.

The control exists because historical correspondence can outlive the context in which it was written. A serious evaluator, partner, program office, counsel, or laboratory should not have to guess which external statements are current, evidence-backed, superseded, or only aspirational.

## Governing rule

The external linter is a **release check, not an evidence generator**. Passing it means only that no configured representation-risk rule blocked the supplied text. It does not prove the text true, validate a technology, establish legal status, confer a credential, create a partnership, establish compliance, or authorize release.

Human review remains mandatory for material external claims.

## Reuse of existing control

`claims_linter_external.py` calls the existing `lint_physics_claim()` implementation first and preserves its deterministic INFO/WARN/BLOCK findings and denial-aware behavior. It adds external-correspondence rules rather than implementing a second maturity engine.

Unqualified `MATURITY-01` and `MED-01` warnings are elevated to `BLOCK` for external release when no bounded evidence context has reduced them to informational status.

## Additional external rules

### EXT-CLASS-01 — classification / handling authority
Blocks positive use of classification, CUI, SAP, or similar government handling language when used as an external representation without an authorized basis. Explicit denial/limiting language remains informational.

Worldshepherd must not self-apply government classification markings or imply classification authority.

### EXT-GOV-01 — government sponsorship / authorization / office or program association
Blocks configured language that can reasonably imply official government sponsorship, approval, authorization, endorsement, office, or program association.

Naming a public solicitation, agency, standard, or target customer is not itself a relationship and should be written that way.

### EXT-REL-01 — partnership / endorsement / award / contract / customer status
Blocks positive relationship-status language unless it is supported outside the linter by documentary evidence. Outreach, referral, interest, application, evaluation, and teaming discussion must not be promoted into partnership or customer status.

### EXT-COMPLY-01 — regulated compliance / certification
Blocks configured positive CMMC, NIST SP 800-171, and DFARS compliance/certification language. Internal controls, CI, an SSP precursor, or readiness work do not establish an external certification or contractual compliance conclusion by themselves.

### EXT-TITLE-01 — identity / credential integrity
Blocks `Dr. Brandon Davis`, `Dr. Brandon Ray Davis`, or an attributed doctoral credential in Worldshepherd-authored identity text. Brandon Ray Davis does not currently claim an earned doctoral title or doctorate credential. `Brandon Davis`, `Brandon Ray Davis`, or `Mr. Davis` is appropriate unless an applicable qualified body formally confers a title.

If an external correspondent uses `Dr.`, a future reply may courteously correct the record without treating the correspondent's assumption as a credential.

## Deterministic evidence output

Every lint run produces `ws-external-claims-lint-1` JSON containing:

- SHA-256 of the exact UTF-8 input;
- `blocked` boolean;
- INFO/WARN/BLOCK counts;
- ordered findings with rule ID, matched text, message, and safe-replacement guidance where applicable.

This allows an outbound artifact to retain evidence of exactly which text was checked and which linter version produced the result.

## CLI

From the verified-local deployment environment:

```bash
python -m worldshepherd_sara.claims_linter_external draft.md
```

or:

```bash
cat draft.md | python -m worldshepherd_sara.claims_linter_external -
```

Exit codes:

- `0`: no BLOCK and no WARN findings;
- `1`: no BLOCK findings, but one or more WARN findings require review;
- `2`: one or more BLOCK findings; do not release without resolving the claim/evidence problem.

## What the linter cannot decide

The linter cannot independently determine:

- whether a contract, award, partnership, legal entity, clearance, certification, patent right, credential, or customer relationship exists;
- whether a physical, clinical, operational, cybersecurity, or scientific claim is actually valid;
- whether release is permitted by law, contract, NDA, export control, classification authority, privacy rules, or data rights;
- whether a named third party agrees with Worldshepherd's characterization.

Those questions remain documentary/legal/domain gates and must fail closed when unresolved.

## Claims-boundary examples

Preferred:

> Worldshepherd implements bounded workflow, authorization, and evidence-provenance software. Independent external validation remains required for partner-owned physical capability.

Preferred:

> We are evaluating fit with the public NIST program and do not claim NIST endorsement, certification, or partnership.

Blocked pending evidence review:

> Worldshepherd is an official government-approved program.

Blocked pending evidence review:

> Worldshepherd is in partnership with NIST and is CMMC Level 2 certified.

Blocked identity form:

> Dr. Brandon Ray Davis, Founder

## Relationship to the retrospective audit

Issue #331 governs retrospective external-claims integrity. This linter is one preventive control arising from that audit. Historical artifacts remain preserved; passing current text through the linter does not erase, rewrite, or retroactively validate prior correspondence.
