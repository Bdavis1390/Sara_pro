# Worldshepherd PRIME Cross-Domain Closure

Status: engineering target / mathematical screening / requires validation.

This addendum advances PUMI v0.3 into cross-domain mass, load, energy, buoyancy, and carrier packaging screens. It does not promote any physical capability beyond the claims state supported by evidence.

## Environmental load rule

PUMI qualification depends on environmental loads as well as attached pack mass. The interface load model must combine inertial force from mass/CG, aerodynamic or hydrodynamic force at the pack center of pressure, pack-generated reaction torque, and transient contact/impact loads. Meeting the pack-mass limit alone is insufficient.

For PUMI-X, the 2.5 kN-m working moment becomes 3.75 kN-m at the current 1.5x development proof factor. Across the candidate 0.55 m vertical hardpoint spacing this produces an approximately 6.82 kN tension/compression couple. Combined with the 15 kN working / 22.5 kN proof load envelope, initial hardpoint articles should screen at approximately 10 kN combined-equivalent proof load before detailed vector load cases and FEA refine the requirement.

## Preliminary pack-class mapping

| Pack | Preliminary class | Mass target | Key unresolved load |
|---|---|---:|---|
| SUBTERRA / SUBSPACE | PUMI-S | <= 35 kg target | impacts, climbing, hazardous-environment constraints |
| SPACE local mobility | PUMI-S / H | <= 50 kg S target; heavier H allowed | maneuvering reactions, thermal equipment |
| AERO | PUMI-H | <= 90 kg target | rotor/wing loads, vibration, landing transients |
| HADAL | PUMI-X | <= 150 kg dry-handling target | buoyancy, drag, hydrostatic stability, pressure architecture |

A pack that fails its assigned class is redesigned first. PUMI classes are not enlarged solely to rescue an overweight or over-load pack.

## AERO first-order closure

Using the current 92 kg PRIME-core target plus a 90 kg AERO pack produces a 182 kg gross design screen.

Eight 1.0 m diameter lift rotors provide approximately 6.28 m^2 total disk area. At sea-level density, ideal induced hover power screens at approximately 19.2 kW. Applying the current preliminary figure-of-merit/drivetrain screen yields roughly 30 kW propulsion input before reserve; adding a provisional 20 percent peak reserve pushes the design-power screen toward approximately 36 kW.

These are mathematical targets only. Aerodynamic interference, motor/inverter efficiency, thermal behavior, acoustic limits, control authority, gust response, rotor safety, structure, and flight test remain unresolved.

A 45 kg qualified-pack energy allocation at 240 Wh/kg usable would provide approximately 10.8 kWh. Four total minutes at a 36 kW peak screen consumes approximately 2.4 kWh; ten minutes consumes approximately 6.0 kWh before cruise, reserves, and conversion losses. The baseline architecture therefore remains **short VTOL plus wing-borne cruise**, not sustained multirotor hover.

An E-X shadow energy pack at 320 Wh/kg usable would provide approximately 14.4 kWh at the same 45 kg mass, but the additional 3.6 kWh receives no baseline credit until an installed pack demonstrates it.

## HADAL first-order closure

HADAL should not attempt to obtain all buoyancy from a single backpack. A 200 kg robot-plus-pack system requires approximately 195 L of total effective displaced seawater volume merely to balance weight at 1025 kg/m^3, before stability or reserve buoyancy is considered.

The working architecture therefore favors distributed pressure-tolerant volume/buoyancy across the body and pack, slightly negative seabed operating buoyancy, independently releasable ballast, and protected positive-buoyancy ascent capability. Exact syntactic-foam volume, pressure-vessel mass, flooded volume, drag, metacentric/stability behavior, and center-of-buoyancy location remain BLOCKED pending a complete hydrostatic CAD model.

## PSDM-4 / OLV-4 payload closure

The current 1.0-1.3 tonne loaded PSDM-4 target implies that each OLV-4 should be treated as at least a **1.5 tonne orbital-payload-class planning requirement** after adapter and growth margin. This is a separate launch-vehicle/partner development problem and is substantially beyond small air-launched satellite systems.

PASC must carry two independent OLV-4 / PSDM-4 assemblies for the standard eight-PRIME squad.

For the two-vehicle carrier, tandem or otherwise centerline-dominant launch stations are preferred for early trade studies because a single release produces less lateral roll asymmetry than widely separated left/right payloads. Fore/aft CG migration, aeroelasticity, flutter, structural loads, separation aerodynamics, and return-with-payload behavior remain mandatory analyses before carrier geometry is frozen.

## Closure status

- **PUMI-S/H/X three-class architecture:** retained.
- **SUBTERRA/SUBSPACE:** PUMI-S target; engineering development.
- **SPACE:** PUMI-S/H depending mobility and thermal equipment; engineering development.
- **AERO:** PUMI-H; BLOCKED on full propulsion/energy/aerodynamic closure.
- **HADAL:** PUMI-X; BLOCKED on hydrostatic/pressure closure.
- **PSDM-4:** four independent bays retained.
- **OLV-4:** one four-PRIME orbital insertion module retained.
- **PASC:** two independent four-PRIME launch groups minimum; autonomous-carrier development remains a separate major program.
- **E-X:** parallel non-credit shadow design; no experimental performance transfers into baseline until validated.
