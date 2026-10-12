# Worldshepherd EM Intelligence Control Plane

Status: IMPLEMENTATION DESIGN / no physical capability claim

## Objective
Provide a governed software layer between electromagnetic intent, simulation/inference, authorization and eventual programmable hardware.

## Core flow
1. Intent: target sensing/control objective arrives.
2. SARA: proposes candidate operating state, sparse tones or future geometry.
3. Evidence resolver: retrieves validated envelopes, D4/D5 metrics, convergence status and applicable model version.
4. Surrogate/inverse model: may rank or propose candidates only.
5. Palace/full-wave validator: required for any new design claim before promotion.
6. PRIME: checks authorization, evidence class, safe-state constraints and whether the action is inside a validated envelope.
7. Hardware adapter: future bounded command to LOW_C/HIGH_C/SAFE_OPEN or later multi-bit state.
8. ECHO: records request, model version, evidence references, command, observed response and hashes.
9. OVERWATCH: displays state, confidence, drift, warnings and validation status.

## Required software objects
### EMIntent
- objective
- frequency band or sparse tones
- polarization
- angle/context estimate
- desired state/function
- latency/power constraints

### EMCandidate
- candidate state/design ID
- predicted TE/TM complex response
- predicted latent coordinates
- model/source version
- uncertainty / refinement status
- allowed evidence label

### EMPolicyDecision
- authorized: true/false
- validated envelope ID
- safe fallback
- unresolved gates
- rationale code

### EMObservation
- timestamp
- device/coupon ID
- state command
- TE/TM complex observations
- angle/polarization estimate
- sparse-tone set or full sweep
- latent coordinates
- numerical or measurement uncertainty
- provenance hashes

## Operating modes
### Audit/calibration
Full spectral sweep and maximum evidence retention.

### Operational sparse-tone
Small deterministic tone set selected only after D5/full-spectrum validation.

### Safe/degraded
SAFE_OPEN or future explicitly validated fallback when confidence is insufficient.

### Design exploration
Surrogate/inverse-design proposals are sandboxed and cannot directly actuate hardware or create validated claims.

## Confidence doctrine
No single scalar confidence should hide unresolved physics.
Track separate components:
- convergence confidence
- model-discrepancy status
- measurement uncertainty
- state observability
- angle observability
- polarization observability
- out-of-manifold distance
- hardware repeatability

## Worldshepherd-specific opportunity
Use functional channel separation:
- TE: reference / angle / health witness candidate
- TM: programmable / sensitive candidate
- TE-TM differential: self-referenced inference candidate

This separation is evidence-derived from current diagnostics but remains subject to fine-mesh and hardware validation.

## Safety and claims control
- no automatic promotion from surrogate output;
- no hidden parameter tuning;
- no hardware command outside PRIME authorization;
- no replacement of failed runs with retries unless preregistered;
- preserve numerical warnings and anomalous measurements;
- unknown/out-of-manifold states fail closed to the validated safe mode.

## Implementation sequence
1. define schemas and enums;
2. ingest sealed UC06 evidence metadata;
3. implement read-only D4/D5 metrics endpoint;
4. add PRIME policy for evidence-class gating;
5. add ECHO event schema for EM intent/candidate/decision/observation;
6. add OVERWATCH panels;
7. add surrogate sandbox after validator APIs exist;
8. add hardware adapter only after physical validation.

## Claims boundary
This document specifies software/governance architecture. It does not establish hardware self-sensing, autonomous beamforming, sparse-tone sufficiency, physical anomaly detection, or experimental validation.
