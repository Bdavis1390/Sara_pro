# WS Intake Minimum Standard — 2026-09-01

## Purpose

This document defines the minimum evidence posture for every new Worldshepherd/SARA intake.

The intent is simple: a new intake should never enter the active pipeline as a loose assertion. It must arrive with source custody, review status, routing status, and a claims boundary before it can influence PRE, partner-screening, release evidence, outreach, opportunity scoring, or standards-readiness claims.

## Scope

This applies to at least the following intake classes:

- User directives
- Gmail/email signals
- Opportunity intelligence records
- PRE Requirement Delta Records
- Research/source references
- Software SBOM evidence
- Vulnerability/advisory evidence
- Human-review triage decisions
- Partner-screening packages
- Release evidence indexes
- Operational/recovery evidence
- Future standards-control or remediation evidence

## New CLI

```bash
ws-intake-minimum-ledger \
  --intake-file intakes.json \
  --out intake_minimum_ci \
  --repository "$GITHUB_REPOSITORY" \
  --commit-sha "$GITHUB_SHA" \
  --operator "github-actions" \
  --executed-utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

The command writes:

- `intake-minimum-ledger.json`
- `intake-minimum-summary.json`

## Required fields

Every intake record must include:

```json
{
  "intake_id": "WS-INTAKE-YYYY-MM-DD-NNN",
  "intake_type": "USER_DIRECTIVE",
  "source_system": "chatgpt_conversation",
  "source_locator": "conversation:<stable-reference>",
  "source_retrieved_utc": "2026-09-01T18:25:00Z",
  "source_sha256": "sha256:<64 hex chars>",
  "evidence_status": "RAW_INTAKE_UNSIGNED",
  "maturity_label": "RAW_INTAKE",
  "human_review_status": "PENDING_HUMAN_REVIEW",
  "routing_status": "ROUTED_TO_BACKLOG",
  "downstream_route": "Describe the next governed route.",
  "claims_boundary": "This intake does not establish validation, compliance, remediation, award probability, partner interest, or operational authority."
}
```

## Minimum controls

The ledger validates and records these controls per intake:

| Control | Required posture |
|---|---|
| Source custody | Source system, locator, retrieval timestamp, and SHA-256 digest recorded |
| Source hash | `source_sha256` must be a SHA-256 digest |
| Claims boundary | Explicit non-claim language required |
| Human-review status | Must be one of the bounded review states |
| Routing status | Must be one of the bounded routing states |
| Downstream route/evidence | Either a downstream route or downstream artifact evidence is required |
| False-claim guard | Prohibited readiness assertions are rejected |

## Bounded review states

Allowed `human_review_status` values:

- `PENDING_HUMAN_REVIEW`
- `HUMAN_REVIEW_NOT_REQUIRED`
- `REVIEWED_ACCEPTED_RISK`
- `REVIEWED_ACTION_REQUIRED`
- `REVIEWED_NOT_APPLICABLE`
- `DEFERRED`

Reviewed states require `review_rationale`.

## Bounded routing states

Allowed `routing_status` values:

- `PENDING_ROUTE`
- `ROUTED_TO_PRE`
- `ROUTED_TO_TRIAGE`
- `ROUTED_TO_PARTNER_SCREENING`
- `ROUTED_TO_RELEASE_INDEX`
- `ROUTED_TO_BACKLOG`
- `NOT_MATERIAL`

## Prohibited readiness assertions

The ledger rejects explicit marker claims such as:

- `BAE_VALIDATED`
- `BAE_CERTIFIED`
- `BAE_APPROVED`
- `PARTNER_VALIDATED`
- `SUPPLIER_APPROVED`
- `CMMC_CERTIFIED`
- `NIST_800_171_CONFORMANT`
- `DFARS_SATISFIED`
- `FEDRAMP_AUTHORIZED`
- `ISO_CERTIFIED`
- `SOC2_ATTESTED`
- `CLASSIFIED_ACCESS_GRANTED`
- `DOE_VALIDATED`
- `FIELD_VALIDATED`
- `HARDWARE_VALIDATED`
- `VULNERABILITY_REMEDIATED`
- `SECURE_BY_DESIGN_VALIDATED`
- `OPERATIONAL_AUTHORITY_GRANTED`

A later evidence package can support stronger claims only if a separate validated evidence path exists. This intake ledger never upgrades maturity by itself.

## Claims boundary

This standard records intake governance and custody only. It does **not** establish source truth, partner validation, supplier approval, certification, CMMC/NIST/DFARS conformity, classified access, DOE validation, external reproduction, field performance, hardware performance, export-control clearance, software supply-chain completeness, absence of vulnerabilities, advisory-feed completeness, vulnerability scan pass, vulnerability remediation, human-review completion, exploitability analysis, license legal review, SLSA compliance, opportunity eligibility, award probability, or operational authority.

## Operating rule

Every new intake should be represented by an intake record before it is used to change:

1. PRE demand posture
2. Opportunity ranking
3. Partner-screening priority
4. Outreach content
5. Standards-control status
6. Security/remediation status
7. Release evidence index posture

The first safe default for any new signal is:

```text
maturity_label: RAW_INTAKE
human_review_status: PENDING_HUMAN_REVIEW
routing_status: PENDING_ROUTE or ROUTED_TO_BACKLOG
claims_boundary: explicit non-claim language
```

Promotion requires separate evidence, not intake existence.
