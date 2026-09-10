# Worldshepherd PRIME v0.7 — Domain-Pack and Air-Launch Closure

Status: engineering screen / architecture target / claims-controlled.

This pass continues the v0.6 packaging branch and advances AERO, SPACE, HADAL, SUBSPACE, PSDM-4, and OLV-4 together. No physical capability is promoted by calculation alone.

## 1. PSDM-4 geometry: compact versus slender

The current SPACE-configured folded PRIME cross-section target is 0.82 m x 0.75 m. If four such envelopes are arranged as a 2x2 body grid around a 0.10 m central utility/service cross, the raw grid is approximately 1.74 m x 1.60 m and its circumscribed diagonal is approximately 2.364 m.

That produces a useful radial-corner-clearance screen:

- 2.45 m clear circular diameter: about 43 mm radial margin beyond the raw grid corner.
- 2.55 m: about 93 mm.
- 2.65 m: about 143 mm.

Therefore the 2.45 m PSDM-4C stretch objective is now considered a low-margin geometry that likely requires conformal/canted cassettes and highly efficient structural/service routing. The 2.55 m objective remains the preferred compact target. The 2.65 m fallback remains the lower-risk compact envelope. Actual fit remains BLOCKED until CAD represents cassette walls, shock isolation, wiring/fluid routing, deployment motion, tolerances, thermal hardware, and launch restraints.

### PSDM-4L slender air-launch branch

A new air-launch-optimized arrangement uses two PRIME units side-by-side per longitudinal station and two stations in tandem. With a 0.10 m center gap, one two-PRIME station has a 1.74 m x 0.75 m raw cross-section and a 1.895 m circumscribed diagonal. Allowing approximately 0.10 m radial packaging margin screens at about 2.10 m clear diameter. Two 1.60 m folded PRIME lengths plus inter-station and end structure screen at about 3.6-3.7 m axial length.

This does not prove a launch vehicle. It establishes a better geometry trade:

- PSDM-4C: compact/fat, target about 2.55 m clear diameter, short axial package; preferred for vertical launch or larger cargo spacecraft when diameter is available.
- PSDM-4L: slender, target about 2.10 m clear diameter and 3.6-3.7 m axial length; preferred early air-launch trade because it reduces frontal diameter at the cost of bending, structural length, fore/aft CG migration, and deployment sequencing complexity.
- PSDM-4S: single-file four-PRIME concept can screen near 1.3-1.4 m diameter but roughly 7 m length; retained as a remote trade only because length/bending penalties are severe.

The air-launch branch now treats PSDM-4L as the leading packaging candidate while preserving PSDM-4C as the common compact module architecture.

## 2. AERO power-area trade

At the current 182 kg PRIME-plus-AERO gross screen, sea-level momentum-theory bookkeeping with figure of merit 0.70, drivetrain efficiency 0.88, and 20% peak reserve produces approximately:

- 6.28 m2 effective disk area: 37.5 kW design-power screen.
- 8.0 m2: 33.2 kW.
- 10.0 m2: 29.7 kW.

Four total VTOL minutes at those power levels consume approximately 2.50, 2.21, and 1.98 kWh respectively before other loads.

The baseline AERO trade objective is therefore moved toward >=8 m2 effective deployed lift area if it can close inside the <=90 kg PUMI-H pack mass. This is not a frozen eight-open-rotor layout. Worldshepherd continues to prioritize enclosed, ducted, partially shrouded, embedded, folding, or otherwise protected propulsion where mass and efficiency close. Exposed/open rotors remain a fallback trade rather than the default.

The current AERO mass allocation gives approximately 15 kg to propulsion/inverter hardware. A 33.2 kW peak screen across 15 kg corresponds to about 2.2 kW/kg at that subsystem allocation. This is a design requirement, not a claim. NASA's 2026 TechPort record for the HPDM-30 targets 10 kW/kg continuous for a 30 kW integrated motor drive; NASA also reports a 250 kW converter at 10.6 kW/kg. These external benchmarks indicate that the electric machine/inverter alone need not dominate AERO mass, but fans/rotors, ducts, tilt mechanisms, bearings, cooling, structure, acoustic treatment, and fault containment still must close inside the remaining mass.

The non-energy AERO hardware remains capped at approximately 45 kg unless the mission-energy requirement is independently reclosed. The battery cannot be silently reduced merely to rescue an overweight propulsion structure.

## 3. SPACE thermal architecture

NASA's 2026 small-spacecraft thermal state-of-the-art explicitly treats deployable radiators as a means of increasing radiating area when body area is insufficient, and NASA TechPort includes deployable/freeze-tolerant radiator development. Worldshepherd therefore promotes a deployable radiator from optional trade to baseline SPACE architecture requirement for sustained higher-power operation.

A first v0.7 target is approximately 2.4 m2 total deployable radiator area, implemented as two or more independently survivable panels or equivalent distributed surfaces. Using emissivity 0.9 and an intentionally conservative 70% effective-rejection screen:

- at 330 K, 2.4 m2 screens near 1.02 kW heat rejection;
- at 350 K, 2.4 m2 screens near 1.29 kW.

This supports the existing 700 W nominal local SPACE thermal target with mathematical margin, but does not make the 2 kW PUMI thermal-transfer capability a continuous SPACE heat-rejection rating.

If a 2 kW transient persists for 15 minutes while the radiator rejects only about 1.29 kW, the thermal buffer must absorb roughly 642 kJ (0.178 kWh) before other losses. SPACE therefore requires a combination of deployable radiator area, thermal storage, load scheduling, power derating, and/or higher-temperature heat rejection. Exact orbital view factors, solar/albedo inputs, surface environment, coatings, coolant temperatures, and radiator deployment reliability remain BLOCKED pending mission-specific thermal analysis.

## 4. HADAL pressure architecture

WHOI deep-ocean practice supports the hybrid architecture already selected by Worldshepherd: spherical/cylindrical pressure housings for sensitive dry equipment, syntactic foam or pressure-tolerant flotation for buoyancy, and oil-filled/pressure-balanced components where enclosed gas volume can be eliminated. WHOI's DEEPSEA CHALLENGER description also documents multiple battery buses and oil-equalized battery packaging; WHOI's Nereus work used hollow ceramic flotation spheres and ceramic pressure-resistant housings to reduce dependence on heavier titanium systems.

Worldshepherd therefore freezes three HADAL physical strategies for baseline trade studies:

1. pressure-balanced/flooded or oil-filled subsystems wherever the component can tolerate ambient pressure;
2. minimized pressure vessels for components that truly require a dry controlled enclosure;
3. distributed buoyancy using qualified syntactic and/or ceramic flotation architecture rather than one giant backpack.

HADAL-BUOY-E1 becomes a one-variable experimental article comparing ceramic-sphere distributed flotation against the baseline qualified syntactic-flotation solution for mass, volume, impact tolerance, inspectability, repairability, and repeated pressure-cycle behavior. No material receives full-ocean-depth credit until representative pressure testing closes.

Emergency positive buoyancy remains mechanically available through independently releasable ballast and protected reserve control rather than requiring sustained thruster power for ascent.

## 5. SUBSPACE transition gate

The same serialized PRIME core may transition between mining and SPACE configurations only through a controlled requalification state. The transition record must include decontamination/cleaning, mechanical and NDT inspection where required, connector/insulation checks, seal and lubricant condition, battery health, structural-health review, mission-pack removal/install provenance, and the applicable vacuum/outgassing/environment acceptance tests. Mine hazardous-location qualification and SPACE qualification remain independent evidence states.

## 6. Experimental distribution

The v0.7 experimental matrix adds:

- AERO-E-SINGLE-PWR: high-specific-power integrated electric drive challenger.
- AERO-E-SINGLE-LIFT: protected/ducted/folding high-disk-area propulsion challenger.
- SPACE-E-SINGLE-THERM: deployable composite/advanced radiator challenger.
- HADAL-E-SINGLE-BUOY: ceramic distributed flotation challenger.
- PSDM-E-SINGLE-MAT: lightweight multifunctional central-spine challenger.
- PUMI-E-SINGLE-NODE: WS-AlTi graded-node challenger only after material/joint gates.

E-Mix and E-X may combine these only while preserving separate evidence accounting; experimental success does not automatically promote baseline capability.

## 7. External evidence intake and operational use

Evidence class: SUPPORTED BY EXTERNAL GOVERNMENT/LAB OR OCEANOGRAPHIC SOURCE, not Worldshepherd hardware evidence.

- NASA TechPort, HPDM-30, updated 2026-08-20: 30 kW integrated motor-drive project targeting 10 kW/kg continuous. Operational use: AERO experimental motor/inverter benchmark and validation target.
- NASA Electric Aircraft Propulsion Power Converters, current 2026 page: 250 kW converter reported at 10.6 kW/kg and 99.3% efficiency. Operational use: inverter benchmark; no direct PRIME credit.
- NASA 2026 Small Spacecraft Thermal Systems state of the art: deployable radiators increase available heat-rejection surface. Operational use: SPACE baseline deployable-radiator requirement.
- NASA TechPort deployable/freeze-tolerant radiator projects, updated 2026: operational use as SPACE thermal technology benchmark and freeze/deployment failure-mode input.
- WHOI, How do ocean robots take the pressure?: spherical/cylindrical housings and syntactic foam. Operational use: HADAL baseline architecture.
- WHOI DEEPSEA CHALLENGER: structural syntactic foam plus pressure-equalized/oil-immersed batteries and redundant battery buses. Operational use: HADAL power/pressure architecture benchmark.
- WHOI Nereus: hollow ceramic flotation spheres and ceramic pressure-resistant housings. Operational use: HADAL-BUOY-E1 challenger definition.

## 8. Promotion state after v0.7

- PSDM-4C 2.55 m compact objective: PLAUSIBLE BY AREA/MARGIN SCREEN, still BLOCKED pending CAD.
- PSDM-4L ~2.10 m slender air-launch objective: NEW LEADING AIR-LAUNCH PACKAGING TRADE, still BLOCKED pending CAD/loads.
- AERO >=8 m2 effective lift-area objective: ENGINEERING TARGET.
- AERO non-energy hardware <=45 kg: HARD MASS GATE pending detailed BOM.
- SPACE deployable radiator ~2.4 m2: BASELINE ENGINEERING TARGET.
- SPACE continuous 2 kW rejection: NOT CLAIMED.
- HADAL hybrid pressure/buoyancy architecture: SUPPORTED BY EXTERNAL PRACTICE, Worldshepherd hardware still BLOCKED.
- SUBSPACE dual-environment transition/requalification: ARCHITECTURE DEFINED.

Next closure: parameterized CAD for PSDM-4C versus PSDM-4L, detailed AERO non-energy BOM, SPACE radiator stow/deploy mass and thermal loop, and HADAL dry-volume/pressure/buoyancy accounting.
