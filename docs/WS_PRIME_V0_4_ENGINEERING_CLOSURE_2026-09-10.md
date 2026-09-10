# Worldshepherd PRIME v0.4 Engineering Closure

Status: architecture-defined / engineering targets / claims-controlled.

This closure advances the PRIME all-domain architecture from PUMI/PSDM v0.3.1 into a reference geometry and mass-property screen. It does not claim validated humanoid, flight, deep-sea, launch, or space hardware performance.

## PRIME body reference frame

Coordinate origin is the pelvic structural center. +X is forward, +Y is left, +Z is up.

Preliminary PUMI aft hardpoints:

- upper left/right: (-0.10 m, +/-0.23 m, +0.32 m)
- lower left/right: (-0.08 m, +/-0.20 m, -0.23 m)

This preserves approximately 0.55 m vertical and 0.40-0.46 m lateral separation. Pack loads must enter the torso/pelvic primary structure, not cosmetic shells.

## PUMI-X proof-load screen

- working load target: 15 kN
- development proof target: 22.5 kN
- working moment target: 2.5 kN-m
- development proof moment: 3.75 kN-m
- proof-moment row couple across 0.55 m: about 6.82 kN
- symmetric per-node moment share: about 3.41 kN
- nominal per-node proof-force share: 5.625 kN
- simple worst-direction additive node screen: about 9.03 kN
- retained initial hardpoint article screen: approximately 10 kN combined-equivalent per node

Detailed multiaxial FEA and physical testing must still cover torsion, asymmetric loads, insert/bearing failure, peel, fatigue, impact, and damaged-state operation.

## WHX-PRIME packaging reference

Current design targets for packaging studies:

- standing height: 1.86 m
- shoulder width: 0.52 m
- pelvic width: 0.38 m
- torso depth: approximately 0.30 m
- bare-core folded envelope: 1.45 m x 0.74 m x 0.64 m
- SPACE-configured folded envelope: 1.60 m x 0.82 m x 0.75 m
- PSDM cassette clear envelope: approximately 1.70 m x 0.90 m x 0.82 m

These values remain CAD targets until full joint-range/clearance verification proves the folded pose.

## PSDM-4 v0.4 packaging

A two-across/two-level arrangement of four 1.70 m x 0.90 m x 0.82 m cassettes yields an initial external module target of approximately 1.95 m x 2.00 m x 1.90 m including preliminary structural/service allowances.

The prior nominal 2.4 m x 2.1 m x 1.8 m screen is about 9.07 m3. The v0.4 notional envelope is about 7.41 m3, roughly 18% lower volume. No structural mass reduction is credited from this geometric reduction until FEA closes; the loaded PSDM-4 target remains approximately 1.0-1.3 tonnes.

## Pack mass-property screens

Early rectangular-prism inertia screens use X as depth, Y as width, and Z as height.

| Class | Mass | Screen envelope X x Y x Z | Ixx | Iyy | Izz |
|---|---:|---:|---:|---:|---:|
| PUMI-S | 50 kg | 0.25 x 0.60 x 0.45 m | 2.34 | 1.10 | 1.76 kg-m2 |
| PUMI-H | 100 kg | 0.35 x 0.75 x 0.80 m | 10.02 | 6.35 | 5.71 kg-m2 |
| PUMI-X | 150 kg | 0.45 x 0.85 x 1.05 m | 22.81 | 16.31 | 11.56 kg-m2 |

These are conservative geometric screening values, not measured pack inertias. A pack that meets mass and CG limits but exceeds dynamic-inertia limits must be redesigned or reclassified.

Normal aft-mounted packs target lateral CG offset |Y| <= 0.03 m. Offsets beyond 0.05 m require explicit control/structural/fatigue analysis.

## Domain mass-budget screens

### SUBTERRA / SUBSPACE

External pack target remains <=35 kg. Mass is allocated across environmental protection, gas/environment sensing, climbing/resource tools, communications, pack energy, thermal control, and emergency support. PUMI-S remains the preferred class.

### SPACE

Local-mobility pack target remains <=50 kg for PUMI-S. First allocation screen:

- structure/interface: 6 kg
- mission energy: 12 kg
- maneuvering propulsion/propellant: 10 kg
- thermal hardware: 8 kg
- avionics/comms: 4 kg
- dust/radiation/environment protection: 4 kg
- protected survival/return reserve: 6 kg

Heavier SPACE configurations move to PUMI-H rather than expanding PUMI-S.

### AERO

PUMI-H target remains <=90 kg. First allocation screen:

- installed energy including protected reserve allocation: 45 kg
- wing/load structure: approximately 18 kg
- propulsion/inverters: approximately 15 kg
- thermal, avionics, landing/docking, wiring, growth: approximately 12 kg

The earlier eight-by-one-meter rotor calculation remains equivalent disk-area bookkeeping only; it is not a frozen exposed-rotor architecture. Enclosed, ducted, embedded, tilt, and other efficient VTOL candidates remain active trades. Short VTOL plus wing-borne cruise remains the baseline architectural preference.

### HADAL

PUMI-X dry-handling target remains <=150 kg. First allocation screen:

- pressure/buoyancy architecture: approximately 55 kg
- energy: 25 kg
- thrusters/drives: 20 kg
- structure/interface: 15 kg
- sonar/environment sensing: 10 kg
- ballast/release: 10 kg
- controls/comms/thermal interfaces: 5 kg
- growth: 10 kg

Full-ocean-depth capability remains BLOCKED pending pressure-vessel, buoyancy-material, sealing, connector, thruster, hydrostatic, stability, and representative-depth validation.

## Claims-control result

Architecture-defined in this pass: PRIME body reference frame, preliminary PUMI node coordinates, hardpoint article screen, reduced folded/cassette packaging targets, pack inertia screens, and first domain mass allocations.

Still BLOCKED: laminate/insert FEA, physical folded-pose verification, complete multiaxial PUMI tests, HADAL pressure/hydrostatic closure, AERO propulsion/aerodynamic closure, SPACE vacuum/thermal/radiation closure, and PSDM launch-vibration/shock qualification.

No experimental technology or unconventional propulsion receives new performance credit from this closure.
