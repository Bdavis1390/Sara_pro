# WS Human-Review Advisory Triage Ledger — 2026-09-01

## Purpose

`ws-human-triage-ledger` turns vulnerability/advisory evidence into a bounded human-review ledger for SARA Verified Local v1.

It consumes the CI-generated `vulnerability-advisory-report.json` and `vulnerability-evidence-summary.json` produced by `ws-vulnerability-evidence`, then emits:

- `human-triage-ledger.json`
- `human-triage-summary.json`

The ledger records review decisions, reviewer identity, rationale, optional evidence references, and digest-bound source vulnerability evidence.

## Schema

The emitted schema is:

```text
WS-VULNERABILITY-HUMAN-TRIAGE-LEDGER-V1
```

The evidence status is:

```text
INTERNAL_REVIEW_LEDGER_UNSIGNED
```

## Decision states

The ledger allows only these human-supplied decisions:

- `ACCEPTED_RISK`
- `PATCH_REQUIRED`
- `NOT_APPLICABLE`
- `DEFERRED`

If a matched advisory from the vulnerability evidence has no review input, it remains:

```text
PENDING_HUMAN_REVIEW
```

If the vulnerability evidence contains no advisory records, the ledger summary records:

```text
NO_ADVISORY_RECORDS
```

## Review input format

Optional review input is local JSON:

```json
{
  "reviews": [
    {
      "advisory_id": "CVE-2099-0001",
      "decision": "PATCH_REQUIRED",
      "reviewer": "CRE1AWS",
      "rationale": "Matched component requires an explicit patch plan and evidence bundle before closure.",
      "reviewed_utc": "2026-09-01T18:10:00Z",
      "evidence_refs": ["vulnerability-advisory-report.json#CVE-2099-0001"]
    }
  ]
}
```

Review input must reference advisory IDs already present in the vulnerability report. Unknown advisory IDs, duplicate reviews, missing rationale, missing reviewer, or disallowed decisions are rejected.

## CI integration

The SARA Verified Local v1 workflow now:

1. Builds dependency-freeze evidence.
2. Builds SBOM evidence.
3. Builds vulnerability/advisory evidence.
4. Builds human-review triage ledger evidence.
5. Uploads `human-triage-ledger-evidence`.
6. Links the uploaded artifact into `sara-release-evidence-index`.

The release index records:

- human triage artifact ID/digest/URL
- human triage summary digest
- human triage ledger digest
- review input status
- overall ledger status
- record counts
- pending review count
- patch-required count
- accepted-risk count
- deferred count
- source input-file digests

## Claims boundary

This ledger records internal review decisions only.

It does **not** establish absence of vulnerabilities, advisory-feed completeness, vulnerability scan pass, remediation completion, exploitability analysis, secure-by-design status, license legal review, SLSA compliance, CMMC conformity, NIST SP 800-171 implementation, DFARS satisfaction, FedRAMP authorization, ISO certification, SOC 2 attestation, supplier approval, partner validation, external reproduction, field performance, hardware performance, classified access, or operational authority.

## Standards effect

This increment improves standards-control readiness by adding a repeatable review ledger and release-custody surface.

It does not promote a control to `MET` or `EXCEEDED`. Formal promotion remains blocked until there is independently reviewed evidence for advisory feed provenance, remediation evidence, exploitability or non-applicability rationale, policy/control mapping, and accountable approval.
