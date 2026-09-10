# Worldshepherd PRIME physics closure v0.9

Status: ENGINEERING TARGET / REQUIRES CAD, FEA, AND REPRESENTATIVE HARDWARE VALIDATION

This record continues the PRIME all-domain architecture without promoting physical capability by assertion. It refines four v0.8 blockers: PSDM-4L release dynamics, AERO protected VTOL packaging, SPACE-S50-TBI heat rejection, and HADAL emergency buoyancy. Weapon employment and targeting remain outside scope.

## Claims boundary

All Worldshepherd values below are first-order design arithmetic unless separately identified as external evidence. External NASA and WHOI work is used as precedent or benchmark only. No external result is transferred directly into PRIME performance credit. A failed mass, thermal, packaging, hydrostatic, or qualification gate spawns redesign rather than relaxing the requirement.

## PSDM-4L v0.9 release and inertia screen

Reference planning model remains 1,100 kg loaded mass, approximately 2.10 m clear diameter, approximately 3.65 m axial length, four approximately 130 kg SPACE-configured PRIME payloads, and approximately 580 kg non-PRIME module mass. For first-order dynamics only, the four PRIME payload centers are screened at x = +/-0.85 m and y = +/-0.45 m around the module center; the remaining 580 kg is approximated as an axisymmetric 2.10 m diameter x 3.65 m long body. These simplifications are not CAD geometry.

The resulting rough loaded-module mass moments of inertia are Ix approximately 425 kg-m2, Iy approximately 1,179 kg-m2, and Iz approximately 1,285 kg-m2. With one geometrically opposite cross-station pair removed, the same simple model gives approximately Ix 372 kg-m2, Iy 992 kg-m2, and Iz 1,044 kg-m2. These are controller/separation screening values only.

Release sequencing is revised. Releasing both PRIME units from one fore or aft station first can shift first-order module CG by approximately 0.263 m. Releasing both units from one lateral side across the two stations can shift lateral CG by approximately 0.139 m. The preferred nominal sequence is therefore a geometrically symmetric cross-station pair: one fore/one aft and opposite lateral positions, followed by the complementary pair. Ideal simultaneous release of such a symmetric pair produces approximately zero first-order CG translation in the point-mass model. If the first member releases but its paired member fails to release, the one-unit-off transient CG excursion screens at approximately 0.129 m. Further release is then inhibited until attitude/translation state is recovered and the failed bay is dispositioned.

PSDM-4L remains BLOCKED pending actual occupied-bay CAD, structural modes, slosh/fluid effects where applicable, latch/release impulse characterization, multibody separation simulation, flexible-body dynamics, control authority, collision clearance, and representative deployment testing.

## AERO v0.9 protected-VTOL geometry trade

The AERO PUMI-H screen remains <=90 kg total pack mass with 45 kg installed energy/reserve and 45 kg non-energy hardware. Current hover design arithmetic remains approximately 182 kg gross PRIME-plus-AERO mass, >=8.0 m2 effective deployed lift area, and approximately 33.2 kW design peak propulsion input under the existing figure-of-merit, drivetrain-efficiency, and reserve assumptions.

At exactly 8.0 m2 total ideal disk area, equivalent circular propulsor trades are:

- 4 effectors: approximately 1.60 m diameter each, approximately 446 N static thrust and 8.3 kW design power each.
- 6 effectors: approximately 1.30 m diameter each, approximately 298 N and 5.53 kW each.
- 8 effectors: approximately 1.13 m diameter each, approximately 223 N and 4.15 kW each.
- 12 effectors: approximately 0.92 m diameter each, approximately 149 N and 2.77 kW each.

Disk loading is approximately 223 N/m2 for all four idealized trades because total weight and area are unchanged.

The v0.8 non-energy BOM gives only 12 kg to lift/cruise effectors and local ducts/shrouds, 6 kg to motors/inverters, and 5 kg to fold/tilt/deployment mechanisms. This implies total propulsor-related allocations of about 5.75 kg per unit for a 4-unit architecture, 3.83 kg for 6 units, 2.88 kg for 8 units, or 1.92 kg for 12 units, before allocating the remaining AERO structure, thermal, avionics, distribution, landing/docking, protection, and growth lines.

AERO-VTOL-B6 is promoted only as the leading CAD trade, not as a passing design: six approximately 1.30 m deployed effectors provide a useful compromise between unit count, packaging, redundancy, and per-effector mass allowance. Fully deep-ducted fans are not assumed to close the 12 kg effector/duct line. Short annular inlet/tip structures, partial shrouds, folding or stowing blades, wing/boom structure that also carries the propulsor loads, and rotor-guard omission where required by mass/efficiency remain active candidates. If guards are omitted, exclusion-zone, interlock, stow/fold, maintenance, and human-proximity controls become mandatory operational mitigations.

For an acoustic/structural screening band only, a 1.30 m rotor diameter corresponds to approximately 2,740 rpm at tip Mach 0.55, 2,990 rpm at Mach 0.60, and 3,240 rpm at Mach 0.65 using 340 m/s speed of sound. No rpm is frozen until blade count, solidity, section, loading, duct interaction, transition aerodynamics, noise, motor torque, and structural margins are modeled and tested.

External evidence used as research precedent:

- NASA TechPort project 154365, HPDM-30, updated 2026-08-20: targets a 30 kW integrated motor drive at 10 kW/kg continuous specific power and 93% combined efficiency. This is an external research benchmark only.
- NASA TechPort project 125317, Electric Lift Augmenting Slats: investigates distributed small electric ducted fans embedded with high-lift devices for low-speed lift augmentation and retractable installation concepts.
- NASA NTRS 20250007333: experimentally studies distributed electric ducted fan arrays at multiple placements around a wing to quantify aeropropulsive lift/control interactions.
- NASA QUEEN testing documents electrically driven ducted-fan static thrust, thermal, and acoustic characterization, reinforcing the requirement for integrated thrust/thermal/noise testing rather than motor-only credit.

AERO remains BLOCKED pending actual CAD mass closure, BEM/CFD, transition simulation, motor/inverter sourcing or demonstrator evidence, thermal closure, structural analysis, acoustic testing, fault containment, and flight control validation.

## SPACE-S50-TBI v0.9 thermal closure

SPACE-S50 retains the <=50 kg PUMI-S target and only 8 kg total thermal-hardware allocation. The previously rejected 2.4 m2 fully deployable radiator remains FAIL/BLOCKED against that allocation.

SPACE-S50-TBI retains 1.2 m2 physical deployable radiator area plus 1.2 m2 physical body-integrated/multifunctional radiator area. At emissivity 0.9 and the existing 70% system effectiveness screen, net idealized radiative flux is approximately 424 W/m2 at 330 K and 536 W/m2 at 350 K.

For the 700 W nominal rejection target at 330 K, total effective radiator area must be approximately 1.65 m2. With all 1.2 m2 deployable area effective, the 1.2 m2 body-integrated physical area therefore needs an effective exposure/utilization factor of approximately 0.38. At 350 K, a 0.60 body-area utilization factor produces approximately 1.92 m2 effective area and roughly 1.03 kW idealized rejection under the same effectiveness assumption.

The deployable 1.2 m2 portion retains a <=5 kg/m2 mass objective if approximately 2 kg of the 8 kg thermal allowance is reserved for loop interfaces, valves, plumbing, deployment hardware, and local control. Body-integrated heat-rejection surfaces receive no hidden mass credit: added coating, facesheet, heat pipe, spreader, manifold, micrometeoroid protection, or structural penalty must be allocated to either the thermal line or an explicitly multifunctional structure line.

NASA TechPort project 113167, updated 2026-01-22, reports a deployable freeze-tolerant radiator design meeting a solicitation requirement below 8 kg/m2 and describes representative-environment prototype work. This remains an external design benchmark, not PRIME hardware evidence.

The 2 kW PUMI thermal-transfer capability is NOT promoted to continuous SPACE-S50 vacuum rejection. At 330 K and 0.60 body utilization, the current screen rejects only about 0.81 kW; a 2 kW load sustained for 15 minutes would leave roughly 1.07 MJ of unrejected heat. At 350 K and the same utilization, rejection screens near 1.03 kW and the 15-minute deficit remains roughly 0.87 MJ. Therefore S50 must combine load scheduling, derating, core/pack thermal capacitance, or separately accounted transient storage. A dedicated heavier SPACE-H thermal branch remains appropriate for higher sustained loads.

SPACE-S50-TBI remains BLOCKED pending orbit/surface view factors, solar/albedo/planetary IR cases, radiator stow/deploy CAD, thermal straps/manifolds, pump power, working-fluid selection, freeze tolerance, contamination/degradation, micrometeoroid protection, mass closure, and thermal-vacuum testing.

## HADAL v0.9 emergency buoyancy correction

The v0.8 idealized -10 kg operating / +5 kg post-ballast-release trim is demoted because it gives too little emergency margin once compression, trapped/flooded volume, density variation, damage, and manufacturing tolerance are admitted.

Using the same 242 kg first-order PRIME-plus-HADAL mass ceiling and 1,025 kg/m3 seawater screen, the revised nominal operating target is approximately 5 kg apparent negative mass. This requires about 237 kg buoyancy-equivalent displacement, or approximately 231.2 L effective displacement. Releasing the existing 15 kg independent ballast allocation then moves the idealized system from -5 kg apparent to +10 kg apparent positive buoyancy before depth effects.

The new emergency gate is >=+5 kg apparent positive buoyancy at the rated depth and worst qualified temperature after measured/validated compression, flooding/trapped-volume states, density variation, ballast-release tolerances, and credible single-fault effects are applied. Under the simple 237 kg buoyancy-equivalent model, losing 5 kg buoyancy-equivalent corresponds to approximately 2.11% of the nominal displacement support. Therefore a combined depth/environment/state loss exceeding about 2.1% would consume the entire +5 kg minimum margin and force redesign, more reserve buoyancy, or a different operating trim.

Static-stability requirements are not frozen without CAD. As sensitivity only, approximately 237 kg buoyancy-equivalent produces about 2.33 kN buoyant force. At 10 degrees heel/pitch, a 25 mm, 50 mm, or 100 mm vertical separation between center of buoyancy and center of gravity produces roughly 10, 20, or 40 N-m restoring moment respectively. Actual required CB-CG separation must be derived from thruster, manipulator, tether, current, seabed-contact, and payload disturbance moments.

WHOI public engineering sources support the underlying architecture: spherical/cylindrical pressure housings for protected dry equipment; syntactic foam composed of hollow microspheres in epoxy for pressure-resistant buoyancy; pressure-balanced/oil-filled electronics where enclosed gas volume can be eliminated; and ceramic pressure/flotation approaches as historical deep-ocean challengers. These sources do not establish Worldshepherd depth qualification.

HADAL remains BLOCKED pending full displaced-volume CAD, material density/compression data, center-of-buoyancy and center-of-gravity mapping, pressure-vessel and pressure-balanced subsystem design, ballast-release reliability, trim/control simulation, drag/current cases, pressure cycling, leak/flood cases, and representative-depth testing.

## v0.9 promotion state

- PSDM-4L symmetric cross-station pair release: ENGINEERING TARGET; first-order CG improvement demonstrated mathematically; physical separation remains BLOCKED.
- PSDM-4L approximate inertia values: SIMULATED/ARITHMETIC SCREEN ONLY.
- AERO-VTOL-B6 six-effector geometry: LEADING CAD TRADE; not selected hardware and not flight-qualified.
- AERO motor/inverter external research benchmark: SUPPORTED BY EXTERNAL NASA RESEARCH; no Worldshepherd performance credit.
- SPACE-S50-TBI 0.38 body-utilization threshold for 700 W at 330 K: ARITHMETIC SCREEN; environmental validation required.
- SPACE continuous 2 kW rejection: NOT CURRENTLY CLAIMED for S50.
- HADAL -5 kg operating / +10 kg ideal post-release trim with >=+5 kg worst-depth emergency margin: ENGINEERING TARGET.
- Full-ocean-depth HADAL capability: NOT CURRENTLY CLAIMED.

Next closure sequence: parameterized CAD for PSDM-4L occupied bays and symmetric deployment paths; AERO-B6 integrated mass/geometry and BEM/CFD; SPACE-S50-TBI view-factor/thermal-network model with stow/deploy packaging; HADAL full hydrostatic CAD with depth-dependent buoyancy ledger; then PUMI/PRIME coupled FEA and representative component tests.