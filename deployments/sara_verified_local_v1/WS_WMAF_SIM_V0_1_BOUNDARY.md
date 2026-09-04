# WS-WMAF-SIM v0.1 — Mobility Assurance Composition Boundary

## Purpose

WS-WMAF-SIM v0.1 composes existing Worldshepherd/SARA APNT normalization, bounded autonomy-policy evaluation, and canonical evidence-digest primitives into a synthetic/replay mobility-assurance assessment path.

It is intentionally a thin composition layer. It does not introduce a second autonomy stack, a vehicle-control system, or a vendor-specific integration framework.

## Implemented scope

The v0.1 software path can:

- accept a synthetic/replay mobility event using `WS-WMAF-EVENT-V0.1`;
- normalize a synthetic PNT source through the existing `SyntheticPntAdapter`;
- identify bounded risk conditions for PNT degradation, contradictory vehicle state, unauthorized software version, telemetry loss/staleness, and invalid telemetry age;
- evaluate an optional action candidate through the existing Worldshepherd autonomy policy;
- classify the assessment as `OBSERVE`, `FLAG`, `ESCALATE`, or `DENY`;
- retain `execution_performed=false` for every assessment; and
- bind the complete assessment inputs, disposition, and claims boundary to a canonical SHA-256 digest.

## Default policy boundary

The default WMAF-SIM policy allows only policy evaluation for the non-actuating action types:

- `record_evidence`
- `raise_alert`

It explicitly denies:

- `vehicle_control`
- `steering`
- `braking`
- `throttle`
- `route_override`
- `actuation`

An `AUTO_ELIGIBLE` policy result does not execute an action and does not confer external authority.

## Validation boundary

Current claimable state for WMAF-SIM v0.1 is limited to software/simulation evidence after tests pass.

This increment does **not** establish:

- physical or field validation;
- roadworthiness or functional-safety compliance;
- ISO 26262 conformity or certification;
- ISO/SAE 21434 conformity or certification;
- UNECE R155/R156 conformity;
- ISO 3691-4 conformity;
- ASPN, pntOS, GPNTS, or government-interface implementation;
- production CAN, CAN-FD, Automotive Ethernet, ROS 2, DDS, or proprietary vehicle-bus integration;
- NXP, Aeva, Hyster-Yale, NVIDIA, Mobileye, Toyota, Qualcomm, DENSO, Infineon, Ambarella, Wabtec, RoboSense, or other partner/vendor integration;
- partner interest, endorsement, adoption, validation, or supplier approval;
- autonomous steering, braking, throttle, routing, flight, weapons, or other actuation;
- operational authority.

## Audit-derived architecture decision

The repository already contains APNT adapters/contracts, autonomy policy, sensor-fusion evidence, HMAA assurance/attestation, evidence stores, PRE qualification, and partner-screening machinery. WMAF therefore reuses those primitives rather than duplicating them.

Vendor-specific adapters must remain separate future increments and require authoritative interface definitions, lawful access, test fixtures, and partner or lab validation before any integration claim is promoted.

## Next evidence gate

WMAF-SIM v0.1 is eligible for promotion only after:

1. repository tests covering nominal and fault cases pass;
2. protected SARA CI passes on the proposed revision;
3. CodeQL/security checks pass where configured;
4. the diff is reviewed for absence of network/write/control paths;
5. claims-boundary language remains intact; and
6. human review approves merge.

After that gate, the next technical increment should be a replay-oriented generic mobility adapter or authoritative partner-specific fixture—not a live vehicle-control integration.
