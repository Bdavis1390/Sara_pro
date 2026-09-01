# Worldshepherd / SARA Standards Control Matrix — 2026-09-01

## Purpose

This patch advances the industry-standards baseline from a list of target standards into a per-control, evidence-gated matrix.

The governing rule remains:

> A control is not marked **MET** or **EXCEEDED** until mapped implementation evidence exists, the assessment method is defined, the latest check passes, the claims boundary is attached, gaps or exceptions are dispositioned, and formal or external assessment evidence is attached when required.

## Added artifact

```text
 deployments/sara_verified_local_v1/standards_control_matrix.json
```

The matrix records:

- `control_id`
- `standard_id`
- domain
- control objective
- owner role
- reviewer role
- current status
- readiness level
- required evidence objects
- implementation evidence IDs
- assessment method
- latest check result
- gap / exception disposition
- claims-boundary reference
- next action

## Current matrix coverage

The matrix currently maps all 14 baseline standards/frameworks:

| Standard ID | Control intent |
|---|---|
| `NIST_CSF_2_0` | Cybersecurity governance and risk evidence. |
| `NIST_SSDF_800_218` | Secure software development lifecycle evidence. |
| `NIST_800_171_R3` | CUI safeguarding readiness without CUI claim. |
| `NIST_800_171A_R3` | CUI assessment-method readiness. |
| `NIST_800_172_R3` | Enhanced CUI / high-value defense readiness tracking. |
| `DOD_CMMC_32_CFR_170` | CMMC applicability and assessment-route separation. |
| `NIST_800_161_R1_UPD1` | Cybersecurity supply-chain risk management. |
| `SLSA_1_2` | Build provenance and artifact custody readiness. |
| `OPENSSF_SCORECARD` | Repository security hygiene tracking. |
| `OWASP_ASVS_5` | Application/API security verification. |
| `CYCLONEDX_1_6_PLUS` | SBOM/BOM generation and validation route. |
| `SPDX_3` | SBOM interoperability route. |
| `OPENVEX` | Vulnerability affectedness decision discipline. |
| `NIST_AI_RMF_1_0` | AI workflow governance and evaluation boundaries. |

## Current posture

```text
records: 14
TARGET_DEFINED: 7
GAP_IDENTIFIED: 3
PARTIAL_INTERNAL_EVIDENCE: 4
MET: 0
EXCEEDED: 0
FORMALLY_ASSESSED: 0
```

The highest currently claimable state remains selected internal CI/evidence-custody evidence only. No formal standards conformance or certification claim is made.

## CI guard added

```text
 deployments/sara_verified_local_v1/tests/test_standards_control_matrix.py
```

The guard verifies:

1. Matrix schema and baseline linkage.
2. Every baseline standard has at least one mapped control record.
3. Required fields are present on every control.
4. Status values are from the approved status set.
5. `MET` or `EXCEEDED` require evidence IDs, passing checks, claim boundaries, gap disposition, and formal/external assessment reference when required.
6. External-claim statuses require reviewer/assessor posture and evidence IDs.
7. Summary status counts match actual records.
8. Formal readiness, certification, partner validation, and field/hardware claims remain blocked unless evidence exists.

## Claims boundary

This matrix records standards mapping, evidence targets, readiness posture, and gating rules only. It does **not** establish certification, accreditation, CMMC conformity, NIST SP 800-171 implementation, DFARS satisfaction, FedRAMP authorization, ISO certification, SOC 2 attestation, BAE validation, DOE validation, supplier approval, export-control clearance, classified access, external reproduction, hardware performance, field performance, or operational authority.

## Next controls to build

1. SBOM generation and retention in CI.
2. Dependency vulnerability scan and vulnerability disposition record.
3. Secrets scan gate.
4. SSDF crosswalk.
5. CUI boundary decision record and SSP skeleton.
6. CMMC applicability decision record.
7. ASVS endpoint/API checklist.
8. AI RMF workflow-risk register.
9. Independent-review handoff package.
