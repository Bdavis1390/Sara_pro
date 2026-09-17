# WS-QX 0.1 Architecture — Requirements-to-Evidence Compiler

WS-QX operationalizes Worldshepherd claims control as a reusable qualification pipeline.

PRE -> Requirement Delta -> Qualification Profile -> SARA Experiment -> ECHO Evidence -> PRIME Claim Decision -> OVERWATCH Readiness State -> Capture/Transition Evidence Package

## Separation of responsibilities

PRE predicts and records demand but cannot upgrade maturity.
SARA executes only authorized bounded workflows.
ECHO preserves source/evidence provenance.
PRIME applies claim-promotion rules.
OVERWATCH reports current state and gaps.

## Promotion principle

Requirements specify what evidence is needed. They are not evidence themselves.

A qualification profile specifies measurements, baselines, mandatory dimensions, safety controls, and promotion prerequisites. Passing software tests proves the software behavior tested; it does not prove physical performance. A physical experiment proves only the bounded configuration and conditions actually measured. External replication is separately recorded.

## Opportunity reuse

A solicitation should map to existing qualification profiles wherever possible. Missing requirements create Requirement Delta Records rather than one-off unsupported claims. This permits evidence to accumulate before future solicitations while preserving program-specific eligibility and performance gates.

## Initial profile family

EVIDENCE-01: common evidence envelope.
LAB-INTEROP-01: device/protocol interoperability.
SEMCAP-01: mission-aware semantic communications.
DDIL-01: degraded communications.
MOSA-EDGE-01: modular edge/payload integration.
AUTONOMY-01: perception/reasoning/safe execution.
AIRFRAME-QUAL-01: physical UAS subsystem qualification.

WS-QX does not make these profiles equivalent; it makes their evidence custody interoperable.
