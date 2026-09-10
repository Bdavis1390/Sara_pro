# Worldshepherd PRIME All-Domain Modular Architecture

Status: architecture definition / engineering targets / claims-controlled.

This document records the current implementation-facing architecture for the Worldshepherd PRIME all-domain program. It does not claim validated robot, aircraft, deep-sea, launch, or space hardware performance.

## Canonical nomenclature

- **WHX**: humanoids.
- **CHX**: companions/helpers.
- **PRIME**: top-tier all-domain architecture.
- **PUMI**: PRIME Universal Mission Interface.
- **PSDM-4**: four-PRIME deployment module.
- **OLV-4**: orbital launch vehicle carrying one PSDM-4.
- **PASC**: autonomous PRIME squad carrier.

## PRIME-4 deployment rule

The standard deployment module contains **four PRIME units**. One PSDM-4 / OLV-4 carries four PRIME units. A standard eight-PRIME squad uses two independent groups of four. Twelve-unit growth uses three groups of four.

The four-unit grouping is intended to persist across ground, subterranean, maritime/deep-sea, atmospheric, orbital, lunar/asteroid, industrial, rescue, scientific, and authorized government configurations.

## All-domain core and mission packs

PRIME uses a persistent standardized robot core plus detachable domain packs rather than carrying every environment system simultaneously.

- **SUBTERRA**: mines, caves, tunnels, dust/water, hazardous-environment sensing, climbing and communications.
- **SUBSPACE**: dual mining/space configuration; the same serialized PRIME core can transition from underground service to a SPACE configuration after inspection, decontamination, and qualification checks.
- **HADAL**: pressure architecture, pressure-balanced mechanisms where appropriate, protected electronics, syntactic buoyancy, thrusters, ballast, sonar, dedicated dive power, and emergency positive buoyancy.
- **AERO**: detachable atmospheric-flight structure with its own propulsion, inverters, flight energy, flight controls, and emergency recovery energy.
- **SPACE**: vacuum-compatible mobility, thermal rejection/heaters, radiation-aware avionics, particulate/dust awareness, communications, maneuvering propulsion, and protected emergency-return energy.

Space capability does not imply self-launch to orbit. Orbital insertion remains a carrier/launch-vehicle function.

## PUMI v0.3

PUMI uses a four-point torso/pelvis load frame with two upper capture nodes and two pelvic load nodes. Candidate hardpoint spacing is approximately 0.46 m laterally and 0.55 m vertically, subject to packaging and FEA. Pack loads bypass cosmetic shells and enter the primary spine/pelvic structure.

Preliminary mechanical classes:

| Class | Pack mass target | CG offset target | Working load target | Working moment target |
|---|---:|---:|---:|---:|
| PUMI-S | <= 50 kg | <= 0.25 m | 8 kN | 1.5 kN-m |
| PUMI-H | <= 100 kg | <= 0.30 m | 12 kN | 2.0 kN-m |
| PUMI-X | <= 150 kg | <= 0.35 m | 15 kN | 2.5 kN-m |

A 2.5 kN-m moment across 0.55 m produces about a 4.55 kN tension/compression couple before proof factors. Development proof loading begins at >=1.5x the applicable working envelope. Exact node, insert, laminate, fatigue, fracture, bearing, and impact behavior remains **BLOCKED pending FEA and physical test**.

## Power isolation

- **P0**: PRIME core energy.
- **P1**: mission-pack energy.
- **P2**: protected survival reserve.
- **P3**: protected emergency mobility/return reserve.

Mission packs power their own high-current propulsion loops. PUMI provides controlled service/cross-feed rather than becoming the primary flight, dive, or space-propulsion bus.

Design targets are a 120 VDC-class high-voltage service bus, 24/28 VDC-class safety/control bus, and up to 10 kW controlled bidirectional service transfer. These values require engineering validation.

## Data, safety, and custody

PUMI separates:

- **D-A**: primary high-rate mission network.
- **D-B**: independent redundant high-rate network.
- **D-S**: independent deterministic safety/health channel.

Loss or compromise of D-A must not disable pack isolation, safe-torque-off, emergency release, thermal protection, insulation-fault response, or protected-reserve commands.

Every mission pack presents a machine-readable digital passport containing identity, revision, mass properties, PUMI class, environment rating, power/reserve state, thermal limits, inspection state, structural-health state, compatibility, experimental maturity, and authorization state.

SARA handles orchestration/configuration custody; PRIME SENTINEL is the independent authorization boundary; ECHO SENTINEL LINK records provenance; OVERWATCH tracks health/operational state.

## Thermal interface

PUMI supports passive conductive heat transfer plus optional dry-break active coolant supply/return. Current active transfer target is 2 kW continuous per PRIME, with higher transients subject to thermal-mass analysis. Cooling loss must cause derating/controlled shutdown rather than an unsafe dependency.

## PSDM-4 v0.3

PSDM-4 contains four mechanically and electrically independent PRIME cassettes. Each cassette has its own launch restraint, shock/vibration isolation, service connection, health monitoring, electrical isolation, thermal conditioning, emergency service power, and deployment mechanism.

Current packaging targets:

- folded/reclined bay: approximately 2.1 m x 0.85 m x 0.65 m per PRIME;
- complete PSDM-4 envelope: approximately 2.4 m x 2.1 m x 1.7-1.9 m before launch-stage integration;
- loaded PSDM-4: approximately 1.0-1.3 tonnes.

These are CAD/FEA targets, not validated dimensions or masses.

Launch restraints are separate from PUMI and transfer launch loads into dedicated primary structural restraint points.

## Autonomous carrier / air-launch branch

PASC is an autonomous heavy airborne mission carrier sized around complete four-PRIME launch groups. Minimum squad configuration carries two independently releasable OLV-4 / PSDM-4 assemblies for eight PRIME units; growth configuration supports three groups of four.

The air-launch branch uses the high-level carrier-aircraft plus released orbital-stage pattern. Autonomous flight/payload functions remain bounded by independent safety and authorization gates. Failed launch criteria result in no release and safe return when the vehicle design and mission state permit.

## Experimental technology tracks

Every major family maintains:

1. **Baseline** control.
2. **E-Single** one-variable experimental articles.
3. **E-Mix** selected experimental combinations.
4. **E-MULTI** experimentally promoted combinations.
5. **E-X** all-experimental shadow architecture.

E-X uses experimental challengers across major technology-bearing subsystems wherever one exists, but receives no hidden credit from baseline hardware. Experimental candidates include T1200/T1100-CNT structural hybrids, CF/CNT transition zones, CF-PAEK nodes, WS-AlTi graded nodes after coupon validation, compliant/tendon/artificial-muscle distal actuation, parallel-elastic/variable-ratio joints, advanced battery chemistries, secondary structural storage, CNT conductors, structural heat spreading, self-healing composites, embedded health sensing, programmable RF surfaces, and autonomous repair/manufacturing research.

E-X must remain externally interoperable with the common PUMI contract.

## Claims-control boundaries

- No image-generated number is evidence.
- No experimental technology contributes credited performance before measured validation.
- WS-AlTi remains an IP-stage / validation-stage challenger pending modeling and physical evidence.
- Unconventional propulsion contributes zero lift, thrust, energy, or range credit until calibrated measurement and replication.
- SARA software evidence does not establish physical robot, aircraft, launch, deep-sea, or space performance.

## Government / military derivatives

Authorized government or military derivatives may reuse the same PRIME-4, PUMI, PSDM-4, carrier, and domain-pack architecture for qualified-domain transport, mobility, logistics, engineering, rescue/recovery, sensing, communications, environmental operations, platform survivability, and space-support missions. "Anywhere insertion" means physically engineered, tested, authorized, and legally permitted domains; it is not an assumption of unrestricted reach. Weapon employment and targeting are outside this architecture document.

## Immediate engineering closure

1. Run PUMI v0.3 structural/topology and laminate/insert FEA against S/H/X envelopes.
2. Freeze folded WHX-PRIME geometry and mass-property reference frames.
3. Close HADAL, AERO, SUBSPACE, and SPACE pack mass/CG/inertia against PUMI classes.
4. Close PSDM-4 launch-load paths, bay release independence, service power, and thermal budgets.
5. Continue one-variable experimental articles before E-MULTI promotion; retain E-X as a non-credit shadow configuration until evidence closes.
