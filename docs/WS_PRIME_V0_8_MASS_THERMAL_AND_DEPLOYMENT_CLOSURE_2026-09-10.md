# Worldshepherd PRIME v0.8 — Mass, Thermal, and Deployment Closure

Status: engineering screen / architecture target / claims-controlled.

This pass advances the v0.7 PSDM-4L, AERO, SPACE, HADAL, and SUBSPACE branches while preserving the four-PRIME module, PUMI classes, independent reserves, and evidence boundaries. No physical capability is promoted by calculation alone.

## 1. PSDM-4L first mass and CG closure

The air-launch-optimized PSDM-4L remains a two-station module, with two folded PRIME units per longitudinal station. The v0.8 nominal loaded mass screen is 1,100 kg, bounded by the existing 1.0–1.3 tonne program envelope.

Nominal planning breakdown:

- four SPACE-configured PRIME units: 520 kg total, using 130 kg/unit as the midpoint of the existing 120–140 kg launch-planning band;
- four conformal cassettes and local launch restraints: 100 kg;
- longitudinal/central primary structure and outer module structure: 150 kg;
- power and thermal service hardware: 70 kg;
- four independent deployment/release systems: 60 kg;
- avionics, timing, communications, and bay health electronics: 25 kg;
- PSDM protected contingency energy: 25 kg;
- common wiring/fluid/connectors: 30 kg;
- structural/integration growth reserve: 120 kg.

Total: 1,100 kg planning mass. This is a target allocation, not achieved mass. Hard loaded-mass ceiling remains 1,300 kg pending structural and launch-environment analysis. No circularization or slender-packaging mass savings are credited yet.

For first CG bookkeeping, place the two occupied longitudinal stations symmetrically about the module center. If the four-PRIME payload is 520 kg, each station carries approximately 260 kg. If the non-PRIME module mass is approximately 580 kg and remains near the module center, releasing one complete two-PRIME station while the opposite station remains roughly 0.85 m from center would shift the remaining module CG by approximately 0.26 m. Therefore PSDM-4L strongly favors paired 2+2 deployment sequencing or active attitude/trim compensation. Individual 1+1+1+1 deployment remains permitted only after the actual mass-property model demonstrates bounded CG and inertia migration.

PSDM-4L v0.8 goals:
- clear circular diameter target: <=2.10 m;
- axial length target: 3.6–3.7 m;
- nominal loaded mass target: <=1.10 tonnes;
- hard planning ceiling: 1.30 tonnes;
- post-paired-release axial CG shift target: <=0.30 m before active compensation.

PSDM-4C remains the lower-CG-migration compact alternative where launch diameter is available.

## 2. AERO non-energy BOM gate

AERO retains the <=90 kg PUMI-H pack target with 45 kg reserved for installed energy and protected reserves. The remaining 45 kg becomes a hard, line-item non-energy mass gate rather than a broad allowance.

v0.8 non-energy target allocation:

- lift/cruise effectors, fan/rotor structures, and local ducts/shrouds: 12.0 kg;
- electric motors and inverters: 6.0 kg;
- wing and primary load structure: 10.0 kg;
- fold/tilt/deployment mechanisms: 5.0 kg;
- thermal hardware: 3.0 kg;
- avionics, flight control, and sensors: 2.0 kg;
- power distribution/harness/contactors: 2.0 kg;
- landing/docking interfaces: 2.0 kg;
- acoustic/fault-containment shells and local protection: 1.5 kg;
- growth reserve: 1.5 kg.

Total: 45.0 kg target.

At the current 8 m2 effective-lift-area / 33.2 kW peak design-power screen, a 6 kg motor/inverter allocation corresponds to approximately 5.53 kW/kg at that combined allocation. NASA's HPDM-30 2026 project target of 10 kW/kg continuous for the integrated motor drive shows this is not obviously outside advanced electric-machine research targets, but it does not validate the complete AERO propulsion system. The 12 kg lift-effector/duct allocation is now the highest-risk mass line because large protected/ducted lift area can rapidly consume structural mass.

The next AERO article must therefore close the physical lift-area geometry and mass simultaneously. Candidate layouts include larger folding/partially shrouded effectors and distributed protected fans. The equivalent disk-area calculation does not dictate a rotor count or diameter. Open unprotected rotors remain fallback only where other architectures fail the mass/efficiency gate and operational safety can be controlled.

AERO remains BLOCKED until every non-energy BOM line has a candidate part/geometry, mass estimate with source or CAD basis, thermal path, failure mode, and growth allowance.

## 3. SPACE-S50 thermal mass failure and redesign

The existing SPACE-S50 PUMI-S branch reserves only 8 kg for thermal hardware. The v0.7 2.4 m2 deployable-radiator concept does not close that allocation using a current NASA low-temperature deployable-radiator benchmark: NASA TechPort project 113167 reports an integrated deployable radiator design meeting a solicitation mass requirement below 8 kg/m2. At 2.4 m2, that benchmark permits as much as 19.2 kg of radiator before pumps, plumbing, structure, valves, or thermal interfaces. Therefore a fully deployable 2.4 m2 radiator is FAIL/BLOCKED for the present SPACE-S50 8 kg thermal budget.

The redesign branches are:

### SPACE-S50-TBI — body-integrated plus deployable radiator

Target approximately 1.2 m2 of effective body/multifunctional radiating surface plus approximately 1.2 m2 deployable supplemental radiator. To retain the 8 kg total thermal allocation while reserving about 2 kg for loop/interface/valves/actuation, the deployable 1.2 m2 portion must target <=5 kg/m2, or equivalent mass must be eliminated through multifunctional structure. This is an engineering target, not a current qualified baseline.

The full 2.4 m2 effective area remains subject to view factor and attitude. Body area cannot be credited unless mission thermal analysis shows that it actually views cold space sufficiently and is not defeated by solar/albedo/surface loading.

### SPACE-H70-THERM — heavier thermal configuration

A separate PUMI-H branch may increase thermal-system allocation rather than weakening SPACE-S50. This branch is for higher sustained heat loads and can use a larger/heavier deployable radiator architecture. It must carry its own revised pack mass, CG, inertia, energy, and mobility closure and does not promote the S50 branch.

NASA also reports advanced high-temperature radiator research with lower areal-mass targets, including <3 kg/m2 concepts around 500–600 K. Those conditions are not directly transferable to a 330–350 K PRIME thermal loop; they are retained only as experimental-material/architecture evidence.

## 4. HADAL trim and emergency-buoyancy accounting

Use the current 92 kg PRIME core plus the 150 kg maximum dry-handling HADAL pack for a 242 kg first-order system mass. In 1025 kg/m3 seawater, a system intentionally trimmed to 10 kg apparent negative mass requires approximately 226.3 L total effective displacement. A 15 kg change in carried ballast changes apparent buoyancy by 15 kg-equivalent without requiring powered thrust.

The v0.8 emergency trim rule is therefore:

- nominal seabed operating target: approximately 10 kg apparent negative mass, subject to stability and traction needs;
- independently releasable ballast allocation target: 15 kg including ballast/release system as a design branch;
- after full ballast release, first-order target becomes approximately +5 kg apparent positive buoyancy, assuming no material compression/flooding/state change;
- emergency ascent must not depend on continuous thruster operation.

To keep the HADAL pack at <=150 kg, the prior mass allocation is rebalanced for this branch: 55 kg pressure/buoyancy architecture, 25 kg energy, 20 kg thrusters/drives, 15 kg structure/interface, 10 kg sonar/environment sensing, 15 kg ballast/release, 5 kg controls/comms/thermal interfaces, and 5 kg growth. Total remains 150 kg.

These hydrostatic values are bookkeeping only. Exact displaced volume, compressibility, syntactic/ceramic flotation behavior, trapped/flooded volumes, center of buoyancy, center of gravity, metacentric stability, hydrodynamic drag, sediment interaction, and pressure cycling remain BLOCKED pending CAD and representative testing.

## 5. SUBSPACE qualification custody

The v0.7 mine-to-space transition gate is retained. v0.8 adds a configuration-custody rule: after any hazardous mine or deep-environment mission, the serialized PRIME core enters a QUARANTINED_FOR_REQUALIFICATION state in SARA until decontamination, inspection, electrical integrity, seals/tribology, battery health, structural health, and target-environment acceptance records are complete. A new SPACE pack alone cannot clear this state.

ECHO SENTINEL LINK must preserve the before/after inspection evidence, and PRIME SENTINEL must reject mission-pack activation for a target environment whose independent qualification state is not valid.

## 6. Experimental articles created by this failure-driven pass

- SPACE-E-SINGLE-RAD: <=5 kg/m2 class low-temperature deployable radiator challenger for the S50 branch, without claiming achievement.
- SPACE-E-SINGLE-MULTITHERM: multifunctional structural/radiating skin challenger intended to reduce dedicated radiator mass.
- AERO-E-SINGLE-EFFECTOR: protected high-area lift effector evaluated against the 12 kg effector mass gate.
- PSDM-E-SINGLE-SPINE: lightweight slender central-spine challenger against the baseline PSDM-4L structure.
- HADAL-E-SINGLE-TRIM: pressure-cycle-qualified lightweight ballast/release architecture; emergency release remains mechanically independent and safety-gated.

## 7. v0.8 promotion state

- PSDM-4L <=2.10 m x 3.6–3.7 m: retained as leading air-launch packaging TARGET.
- PSDM-4L nominal 1.10 t / hard 1.30 t loaded mass: TARGET, no mass savings claimed.
- PSDM-4L paired-release CG migration: first-order ~0.26 m screen; actual inertia model required.
- AERO 45 kg non-energy BOM: CLOSED ARITHMETICALLY, NOT ENGINEERING-CLOSED; lift-effector mass is highest-risk line.
- SPACE-S50 all-deployable 2.4 m2 radiator: FAIL/BLOCKED against 8 kg thermal allocation using current external benchmark.
- SPACE-S50-TBI integrated+deployable thermal branch: REDESIGN TARGET.
- SPACE-H70-THERM: PARALLEL HEAVIER CONFIGURATION TARGET.
- HADAL -10 kg operating / +5 kg post-ballast-release buoyancy branch: HYDROSTATIC TARGET, representative testing required.
- SUBSPACE post-hazard QUARANTINED_FOR_REQUALIFICATION state: ARCHITECTURE DEFINED.

Next closure: candidate geometry/part sourcing for the AERO non-energy BOM; SPACE-S50 body-radiator view-factor and radiator mass model; PSDM-4L actual inertia tensor and structural load-case schema; HADAL body/pack displaced-volume ledger; and integration of the new quarantine state into machine-readable SARA configuration custody.
