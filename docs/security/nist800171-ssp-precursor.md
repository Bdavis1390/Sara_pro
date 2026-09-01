# SARA NIST SP 800-171 Rev. 3 SSP Precursor

Status: INTERNAL ENGINEERING PRECURSOR / NOT AN ASSESSMENT

## Purpose

Establish a machine-checked starting point for a future scoped system security plan by documenting the current SARA verified-local system boundary, interfaces, data classes, exclusions, and the status of evidence available across all 17 NIST SP 800-171 Rev. 3 requirement families.

## Current CUI posture

The current reference architecture is not authorized to process CUI and does not claim to do so. Synthetic/test data, internal engineering metadata, and engineering evidence are the only data classes currently represented as active. Any future CUI scope must be established contractually and technically before the boundary can be promoted beyond this precursor.

## Evidence-map semantics

`INTERNAL_EVIDENCE_PARTIAL` means bounded internal technical evidence exists but is insufficient to establish requirement satisfaction. `PROCEDURAL_ONLY` means an internal procedure or planning precursor exists without enough implementation evidence. `EXTERNAL_EVIDENCE_REQUIRED` means authoritative organizational, personnel, physical, contractual, customer, assessor, or other evidence outside software CI is required. `UNVERIFIED` means no adequate evidence has yet been established.

The family-level map is intentionally not a control-by-control assessment. Organization-defined parameters remain subject to contractual and organization assignment. Requirement `03.15.02` is retained as the system-security-plan planning reference for this precursor.

## Fail-closed rules

The CI validator requires all 17 families exactly once, valid boundary components and interface references, explicit CUI non-authorization, evidence/gap ownership for every family, repository-resolvable evidence references, explicit ODP status, and claims-control language. It rejects unsupported statements that claim NIST SP 800-171 compliance, CMMC certification, full implementation, or CUI authorization.

## Promotion prerequisites

Promotion toward an actual SSP or assessment package requires at minimum a contract/program-specific CUI determination, finalized system boundary, authorized organizational roles, assigned ODP values, requirement-level implementation statements, objective evidence, exception/POA&M handling as applicable, and the appropriate assessment/authorization process. SPRS, CMMC, RMF/ATO, customer acceptance, or other external status must be evidenced independently and never inferred from this CI gate.

## Claims boundary

Passing `SARA NIST 800-171 SSP Precursor` means only that the precursor is structurally complete and internally evidence-linked under its declared non-CUI scope. It does not constitute an approved SSP, NIST SP 800-171A assessment, SPRS score, CMMC certification, ATO, customer authorization, or permission to process CUI.
