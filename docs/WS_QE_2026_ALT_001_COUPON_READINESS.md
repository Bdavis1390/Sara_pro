# WS-QE-2026-ALT-001 — Al–Ti Coupon Readiness Package

Status: PRE-PHYSICAL QUALIFICATION / NO MATERIAL-PERFORMANCE CLAIM

Parent intake: `WS-RI-2026-0904-W3`

Baseline branch: `worldshepherd/alti-coupon-readiness-v1-20260908`

## Purpose

Translate the WS–AlTi M1-MSZ-Prime platform thesis into a falsifiable coupon campaign without promoting IP-stage positioning into a physical-material claim.

This package does **not** establish alloy performance, additive-manufacturing process qualification, patentability, freedom to operate, partner validation, or commercial valuation.

## Core hypothesis

A deliberately commanded Al–Ti composition/process gradient can be fabricated reproducibly and produce a spatially resolved composition/microstructure/property response that is measurably different from fixed-composition and non-graded controls.

A gradient that appears incidentally is not sufficient. The campaign must demonstrate:

`commanded spatial state -> measured composition/process state -> measured phase/microstructure -> measured property response -> repeatability`

## Failure modes to target explicitly

The campaign must treat the following as expected disconfirming mechanisms rather than anomalies to omit:

1. brittle Ti–Al intermetallic formation;
2. interfacial or bulk cracking;
3. residual-stress accumulation;
4. aluminum volatilization / composition drift;
5. porosity, lack-of-fusion, or delamination;
6. local chemistry outside commanded tolerance;
7. microstructure/property non-monotonicity;
8. process-history dependence and hysteresis;
9. thermal-cycle instability;
10. fracture initiation from defects not visible in one inspection modality.

## Coupon set

Minimum controlled campaign:

- **C0 — process blank:** substrate/process baseline with no intended gradient;
- **C1 — fixed Al-rich composition:** constant-composition control;
- **C2 — fixed Ti-rich composition:** constant-composition control;
- **C3 — monotonic Al->Ti gradient:** commanded spatial gradient;
- **C4 — monotonic Ti->Al gradient:** reverse-gradient control;
- **C5 — stepped gradient:** discrete composition zones to test command fidelity;
- **C6 — repeat of C3:** independent repeatability coupon using frozen nominal recipe.

If fabrication constraints require a smaller first pass, retain C0, C1, C2, C3, and C6.

## Required pre-build records

Before manufacturing, freeze and hash:

- material lot/provenance;
- feedstock chemistry certificates if available;
- machine identifier and configuration;
- deposition/process parameter table;
- intended spatial composition map;
- intended scan/deposition path;
- substrate preparation;
- environmental state available to the operator;
- calibration state;
- operator and approval record;
- software/model version used to generate the recipe.

ECHO should preserve the immutable configuration digest and the command-to-position mapping. PRIME should prevent a coupon from being labeled `PHYSICALLY VALIDATED` solely because a build completed.

## Minimum measurements

### Geometry and defect state

- dimensional inspection;
- visual/macroscopic defect record;
- density/porosity estimate where practical;
- crack/delamination map;
- cross-sectional microscopy.

### Chemistry and phase

Preferred minimum set:

- SEM/EDS spatial chemistry mapping;
- XRD phase identification;
- EBSD where available for phase/orientation/grain mapping;
- oxygen/contaminant measurement when feasible;
- local chemistry checks at predefined spatial stations.

### Residual stress / thermal state

- residual-stress measurement where facility capability permits;
- thermal history from process telemetry when available;
- post-build thermal-cycle or aging check for selected coupons.

### Properties

At minimum choose property measurements that can be spatially registered to the commanded gradient:

- microhardness/hardness traverse;
- tensile tests where coupon geometry permits;
- fracture-surface analysis for failed tensile/fatigue specimens;
- fatigue testing only after basic coupon integrity is established;
- thermal/electrical measurements only if they are part of the intended platform claim.

## Registration requirement

All measurements must be registered to a common coupon coordinate system so the evidence chain can support:

`commanded position -> process history -> measured chemistry -> phase/microstructure -> property`

Do not infer causality from unregistered, aggregate-only measurements.

## Primary metrics

- spatial composition error versus commanded profile;
- gradient repeatability across C3/C6;
- phase fraction / phase-presence map;
- crack density or defect burden;
- porosity fraction where measurable;
- residual-stress distribution where measurable;
- property-map correlation with commanded/measured composition;
- between-coupon variance;
- fraction of spatial stations inside predefined chemistry/process tolerance.

## Advancement gates

### G0 — recipe/model readiness

Pass only when the intended composition/process map, controls, instrumentation plan, and configuration-custody records are frozen.

### G1 — manufacturability

Pass only if the gradient coupon can be built without uncontrolled catastrophic failure and with complete provenance. This is not a material-performance pass.

### G2 — command fidelity

Pass only if measured spatial chemistry tracks the intended profile within a predeclared tolerance and the repeated coupon shows comparable behavior.

### G3 — structure/property linkage

Pass only if independently measured phase/microstructure/property changes can be registered to the measured composition/process variation and distinguish the gradient coupon from fixed-composition controls.

### G4 — robustness

Pass only after repeatability, defect sensitivity, thermal stability, and at least one independent or partner-controlled measurement campaign support the bounded claim.

## Claims boundary

Until G2 closes, allowed wording is limited to:

- `WS–AlTi M1-MSZ-Prime platform thesis`;
- `candidate programmable deposited Al–Ti material architecture`;
- `coupon validation in preparation`.

After G2 but before G3, allowed wording may include:

- `repeatably commanded and measured spatial composition gradient`.

The word **programmable** in a material-performance sense requires G3 evidence: intentionally commanded spatial variation, measured repeatable composition/microstructure, and a measured property response linked to that variation.

Do not claim:

- superior strength, fatigue, thermal, electrical, aerospace, armor, propulsion, or structural performance;
- qualification to any manufacturing/material standard;
- patentability or freedom to operate;
- independent validation;
- commercial valuation established by market evidence;
- partner adoption or production readiness,

unless separate evidence closes those claims.

## Evidence ladder

`source thesis -> governed repo intake -> coupon plan -> frozen build configuration -> manufactured coupon -> chemistry/phase/defect evidence -> property map -> repeat build -> external blind measurement -> independent replication`

Negative coupons, cracking, chemistry drift, non-monotonic properties, and failed repeatability are valid evidence and must remain in the qualification record.

## Immediate next action

Do not manufacture yet unless the legal/IP boundary, fabrication route, feedstock, machine/process family, and measurement access are known. The next low-cost action is to populate a frozen coupon matrix with the intended composition stations and process variables, then run prior-art/process-window modeling before committing material and machine time.
