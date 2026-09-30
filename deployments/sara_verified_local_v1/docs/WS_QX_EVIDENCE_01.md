# WS-QX / EVIDENCE-01 — Qualification Evidence Contract

Status: IMPLEMENTED IN SOFTWARE (contract); NOT PHYSICALLY VALIDATED

## Purpose

WS-QX converts requirements into claims-controlled qualification evidence. It is deliberately domain-neutral: semantic edge communications, DDIL, laboratory interoperability, robotics/HIL, materials experiments, UAS subsystems, and partner validation can share the same evidence envelope without sharing unsupported maturity claims.

## Governing invariant

> Claim promotion MUST NOT exceed evidence actually observed.

A workflow cannot promote a capability merely because a target threshold, proposal requirement, simulation, or expected disposition exists. Promotion is derived from recorded evidence and an explicit qualification profile.

## Core evidence envelope

Each qualification run SHOULD bind at minimum:

- qualification_id and qualification_version
- experiment_id and run_id
- claim_state_before and requested_claim_state_after
- hardware identities, where physical hardware is involved
- software commit and model/configuration digests
- calibration identifiers, where measurements require calibration
- operator/authorization record
- test-manifest digest
- raw and normalized evidence references
- injected faults and expected/observed dispositions
- uncertainty budget
- independent pass/fail dimensions
- physical_io_observed
- required human safety-control verification
- run_complete
- evidence digest and optional parent-evidence digest
- external replication reference, if any

## Evidence ladder

1. SOURCE THESIS
2. GOVERNED REPO INTAKE
3. CURRENT IMPLEMENTATION / MODEL
4. INTERNAL REPRODUCIBLE TEST
5. CONTROLLED SIMULATION / BENCH
6. PHYSICAL COUPON / HARDWARE
7. EXTERNAL BLIND TEST
8. INDEPENDENT REPLICATION

Evidence at one level does not automatically imply any higher level.

## Evidence vector

Qualification SHOULD preserve at least three independent axes:

- E_P — physical-performance evidence
- E_A — assurance / TEVV evidence
- E_R — replication / external evidence

These axes MUST NOT be collapsed into a single readiness number when doing so could conceal a weak or absent evidence dimension.

## Fail-closed aggregation

Domain profiles MAY define independent qualification dimensions Q_i. Where all dimensions are mandatory, system qualification is bounded by the weakest mandatory dimension rather than an arithmetic average.

## Physical-evidence interlock

A physical-validation claim MUST remain false unless the profile's required physical evidence is present. Software CI success, simulations, emulation, a populated manifest, a physical-readiness assessment, or a planned experiment are not physical validation.

## External-validation interlock

External or independent validation MUST remain false unless the evidence record identifies the external test/replication artifact and its provenance.

## Standards boundary

Alignment to a standard, profile, paper, solicitation, or test methodology is not certification or conformance unless the applicable conformance process has actually been completed and evidenced.

## Module responsibilities

- SARA: orchestrates governed qualification workflows.
- ECHO SENTINEL LINK: preserves evidence/provenance.
- PRIME SENTINEL: evaluates authorization and claim-promotion policy.
- OVERWATCH: exposes qualification/readiness state without silently promoting it.
- PRE: maps recurring/emerging requirements into qualification profiles and evidence gaps.

## Initial profiles

- WS-LAB-INTEROP-01 — device/protocol interoperability and pre-physical HIL readiness.
- WS-SEMCAP-01 — mission-aware semantic edge communications.
- WS-DDIL-01 — degraded/disrupted/intermittent/limited communications behavior.
- WS-MOSA-EDGE-01 — modular payload/autonomy integration.
- WS-AUTONOMY-01 — perception/reasoning/safe-execution qualification.
- WS-AIRFRAME-QUAL-01 — physical UAS subsystem qualification.

## WS-SEMCAP-01 measurement extension

A semantic-communications profile SHOULD retain independently:

- baseline transmitted bits
- semantic transmitted bits
- mission utility under baseline
- mission utility under semantic transmission
- sensor-to-packet latency
- measured power on identified hardware
- missed critical events
- false semantic selections
- receiver reconstruction fidelity
- link state / bandwidth regime
- provenance completeness

Data reduction is computed against an explicitly identified baseline and MUST NOT be presented alone as mission success. High reduction with unacceptable mission-utility loss fails the qualification profile.

## Claims state for this document

This document defines a governed software/evidence architecture. It does not claim physical validation, external validation, certification, standards conformance, DV019 qualification, UAS flight validation, or partner validation.
