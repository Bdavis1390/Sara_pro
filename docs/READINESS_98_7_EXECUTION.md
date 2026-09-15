# Worldshepherd 98.7% Readiness Execution Doctrine

**Program target:** >=98.7% **internal/partner readiness** for every registered Worldshepherd workstream.

**Claims boundary:** this target is not physical validation, TRL, flight qualification, clinical validation, RF authorization, propulsion validation, regulatory approval, certification, operational adoption, or independent replication. Those states advance only from their own evidence.

## 1. Why the target is split

Worldshepherd uses three separate axes:

1. **Internal/partner readiness** — requirements, models, assumptions, uncertainty, hazards, provenance, baselines, test plans, facilities/interfaces, claims controls, and reproducibility packages are complete enough to execute a lawful validation engagement.
2. **Evidence maturity** — architecture -> simulated -> implemented software -> internal test -> partner test -> independently replicated -> qualified/certified.
3. **Deployment authority** — project-specific authorization, qualification, certification, operator/facility readiness, and lawful use.

A workstream may reach 98.7% on axis 1 while remaining low on axes 2 and 3. This is expected for research programs and is required to prevent readiness inflation.

## 2. Machine-scored readiness gates

Each workstream is scored across ten equally weighted gates:

- requirements and bounded use case;
- explicit models / engineering basis;
- assumptions, uncertainty, and limitations;
- hazards and regulatory dependencies;
- data provenance and custody;
- simulation / baseline evidence;
- test plan and acceptance criteria;
- partner / facility interface;
- claims and release controls;
- reproducibility and evidence package.

The registry is `readiness/portfolio.v1.json`. The validator is `deployments/sara_verified_local_v1/scripts/validate_portfolio_readiness.py`.

Status factors are intentionally conservative:

- VERIFIED / COMPLETE = 1.00
- DOCUMENTED = 0.90
- PARTIAL = 0.60
- PLANNED = 0.35
- MISSING = 0.00

The 98.7 target therefore cannot be reached with a large collection of partially completed gates. Nearly every gate must close with retained evidence.

## 3. Cross-project execution order

### Priority A — common stack

Close these first because every research program inherits them:

1. SARA release / recovery evidence and CRE1AWS acceptance.
2. OVERWATCH/ECHO registered-source, calibration, timing, stale-source, contradiction, and provenance demonstrations.
3. PRE outcome calibration and freshness metrics.
4. Claims / release-gate enforcement integrated with the readiness registry.
5. Evidence-package generator that emits requirement -> model -> configuration -> run -> evidence -> review -> release lineage.

### Priority B — energy first

Energy is the first physical-domain readiness package because it can reuse public Sandia tools, synthetic models, and HIL without requiring hazardous high-voltage or destructive testing in the initial stage.

`WS-ENERGY` closure sequence:

1. Freeze the PyMDT/MDT candidate schema and Windows x64 execution node.
2. Run a baseline MDT microgrid design set.
3. Export candidate configurations into the Worldshepherd stress harness.
4. Apply complete-chain accounting inherited from the X10/X40/X400 work: conversion losses, thermal auxiliaries, controls, protection, storage auxiliaries, containment/BOS, and resource/fuel constraints.
5. Run distributed node failure, sensor, stale-data, communication, storage-derating, renewable-shortfall, topology-mismatch, and compound-fault campaigns.
6. Add Applied Resonance condition-state inputs only for components with physically meaningful diagnostic observables.
7. Preserve Pareto dimensions rather than hiding tradeoffs in a single marketing score.
8. Advance to HIL only after the synthetic campaign is reproducible and the fault/acceptance envelope is frozen.
9. Seek external laboratory review/test after the internal evidence package is complete.

### Priority C — materials

`WS-ALTI` closure sequence:

1. Freeze composition/process hypotheses and IP-safe external boundary.
2. Complete CALPHAD or equivalent phase-risk review.
3. Freeze feed/process/thermal history schema.
4. Produce coupon matrix and three-copy repeatability design.
5. Define SEM/EDS-WDS/XRD/EBSD/CT/mechanical/thermal acceptance criteria before fabrication.
6. Identify qualified DED and characterization facilities.
7. Fabricate only after hazards, ownership/IP, process controls, and evidence custody are accepted.
8. Correlate predicted phases/properties to measured results without upgrading failed predictions.

### Priority D — metasurfaces / RF

`WS-MS` closure sequence:

1. Freeze operating band and target function.
2. Preserve the existing hashed DOE campaigns and failed candidates.
3. Run the leading S11/S17-family candidate through an external 3-D electromagnetic solver.
4. Freeze coupon geometry/tolerances before fabrication.
5. Execute calibrated VNA measurement with uncertainty budget.
6. Perform simulation-to-measurement residual analysis.
7. Repeat across articles and environment before any stronger performance claim.

### Priority E — Applied Resonance

`RESONANCE` closure sequence:

1. Split structural, acoustic, fluid, EM, thermal, and control-system hypotheses.
2. Build conventional baselines first.
3. Use blind fault cases and known-good controls.
4. Require at least five repeats per bounded diagnostic case where meaningful.
5. Advance diagnostic applications such as rotating equipment, cooling loops, joints, cable/pressure-line health, and heat-exchanger condition monitoring.
6. Keep nonconventional propulsion/energy interpretations quarantined until closed energy/momentum accounting and independent replication exist.

### Priority F — sensing / mission assurance

`TIDELENS` closure sequence:

1. Freeze radar/sensor assumptions and synthetic declaration.
2. Add recorded-data replay.
3. Measure association/classification/latency/uncertainty against ground truth.
4. Build an HIL adapter.
5. Identify qualification partner and controlled field-test path.

### Priority G — aviation and lift

`AEROSHEPHERD` and `LIFT-X10-X40-X400` closure sequence:

1. Keep complete mass-energy-range closure mandatory.
2. Preserve boundary failures as stop conditions.
3. Close component dyno / thermal / durability evidence before vehicle integration.
4. Close structural coupon -> joint -> subassembly evidence before full-load claims.
5. Use subscale / HIL progression before flight.
6. Keep 10:1, 40:1, 400:1, 4,000-nmi and 1,000x values as requirements/research envelopes until complete-system evidence exists.

### Priority H — HELIOS-LINK

1. Freeze bounded link budget.
2. Quantify aperture, divergence, pointing, conversion, thermal, interruption, and reserve sensitivity.
3. Conduct only authorized low-power bench work initially.
4. Require calibrated end-to-end efficiency and safe interruption behavior before range scaling.

### Priority I — BAROS

1. Freeze research-only claims.
2. Obtain qualified medical-physics review.
3. Separate dose transport, dose-engine validation, biological-state estimation, optimization, and clinical outcome claims.
4. Build governed retrospective validation only with lawful data access and institutional controls.
5. No clinical-effectiveness or patient-use claim without appropriate study and regulatory evidence.

### Priority J — ion/electric propulsion

1. Close propellant, mass-flow, ionization, acceleration, neutralization, power-processing, thermal, erosion, plume, charging, thrust, and mission budgets.
2. Use conventional electric-propulsion baselines.
3. Require calibrated thrust measurement and endurance evidence before performance promotion.
4. Keep all reactionless or unexplained-thrust interpretations in speculative quarantine unless conventional causes close and independent replication succeeds.

### Priority K — laboratory / Boone

1. No experiment is selected around assumed equipment.
2. Inventory identity, ownership, disposition authority, condition, calibration, utilities, hazards, and restrictions first.
3. Match verified equipment capability to bounded experiments second.

### Priority L — Stegriage

1. Consolidate the scanner.
2. Build known-clean and known-embedded fixtures.
3. Measure false-positive / false-negative rates.
4. Preserve hashes and reproducible extraction paths.
5. Never infer physical spectroscopy from ordinary RGB data without calibrated acquisition.

### Priority M — revenue / partnerships

1. Keep revenue, strategic partnership, and technical-validation states separate.
2. Close one fully documented Evidence-to-Execution engagement from intake to acceptance.
3. Preserve response/outcome evidence for conversion calibration.
4. For Meissner, maintain the candidate-to-device evidence pilot as partner-ready without implying access to proprietary compositions or validated superconductor results.

## 4. Promotion rule

A readiness gate changes state only when evidence changes state.

Examples:

- `planned -> documented`: a bounded plan with assumptions, owner, acceptance criteria, hazards, and evidence outputs exists.
- `documented -> complete`: the package is internally complete and reviewable.
- `complete -> verified`: the defined check/test/review is executed and retained.

A document being longer, an infographic being prettier, or a simulation count increasing does not automatically change a gate.

## 5. 98.7 completion rule

A workstream is >=98.7% internally/partner ready only when the machine-generated report says so. If an externally dependent gate is still required, it remains in `open_external_gates` even after the internal package reaches target.

For regulated/physical projects, deployment maturity remains bounded by the evidence-maturity cap and the project-specific release authority.
