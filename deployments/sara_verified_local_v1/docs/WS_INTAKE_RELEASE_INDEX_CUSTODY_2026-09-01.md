# WS Intake Release-Index Custody — 2026-09-01

## Purpose

This record wires the previously merged intake-minimum standard into the SARA CI evidence chain.

The goal is to make `intake-minimum-standard-evidence` a first-class workflow artifact and to link it into `sara-release-evidence-index` with artifact metadata, local file digests, counts, routing status, review status, and an explicit claims boundary.

## Added custody path

```text
fixtures/intake_minimum_standard.json
→ ws-intake-minimum-ledger
→ intake_minimum_ci/
→ intake-minimum-standard-evidence artifact
→ ws-release-index
→ ws-release-index-link-intake
→ sara-release-evidence-index artifact
```

## New CLI

```text
ws-release-index-link-intake
```

The linker updates an existing `release-index.json` by adding:

- `artifacts.intake_minimum_standard_evidence`
- `local_evidence.intake_minimum_summary_path`
- `local_evidence.intake_minimum_summary_sha256`
- `local_evidence.intake_minimum_ledger_path`
- `local_evidence.intake_minimum_ledger_sha256`
- `local_evidence.intake_minimum_ledger_digest`
- `local_evidence.intake_minimum_evidence_status`
- `local_evidence.intake_minimum_intake_count`
- `local_evidence.intake_minimum_pending_human_review_count`
- `local_evidence.intake_minimum_reviewed_action_required_count`
- `local_evidence.intake_minimum_not_material_count`
- `local_evidence.intake_minimum_review_counts`
- `local_evidence.intake_minimum_routing_counts`
- `local_evidence.intake_minimum_input_files`

It then recomputes `release_index_digest`.

## CI additions

The SARA Verified Local v1 Gate now validates the new CLI, builds the intake-minimum evidence from the fixture, verifies the artifact directory with `scripts/verify_intake_minimum_artifact.sh`, uploads `intake-minimum-standard-evidence`, and links that artifact into the release evidence index.

## Operating rule

Every new intake can be captured as a raw signal, but it cannot promote readiness, probability, remediation, compliance, partner posture, or operational posture unless it passes the intake-minimum ledger requirements and receives downstream evidence or routing.

## Claims boundary

This custody step records CI evidence and intake-governance traceability only. It does not establish source truth, opportunity eligibility, award probability, partner validation, supplier approval, certification, CMMC/NIST/DFARS conformity, classified access, DOE validation, external reproduction, field performance, hardware performance, export-control clearance, software supply-chain completeness, absence of vulnerabilities, advisory-feed completeness, vulnerability scan pass, vulnerability remediation, human-review completion, exploitability analysis, license legal review, SLSA compliance, or operational authority.
