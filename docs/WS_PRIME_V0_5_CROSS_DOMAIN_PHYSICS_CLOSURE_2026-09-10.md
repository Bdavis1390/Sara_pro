# Worldshepherd PRIME v0.5 Cross-Domain Physics Closure

Status: engineering screen / claims-controlled / not validated hardware performance.

## AERO wing-borne cruise screen

Assumptions: 182 kg gross PRIME+AERO mass, 4.8 m2 wing, rho=1.225 kg/m3, provisional CLmax=1.6, 35 m/s cruise, L/D=12, propulsive efficiency=0.80.

Results:

- first-order stall-speed screen: ~19.5 m/s
- cruise propulsion-input screen: ~6.5 kW
- baseline pack screen: 10.8 kWh
- four total VTOL minutes at 36 kW: ~2.4 kWh
- 20% pack reserve: 2.16 kWh
- remaining idealized cruise energy: ~6.24 kWh
- idealized cruise duration: ~0.96 h
- idealized range screen: ~121 km / 65 nmi

Climb, transition, wind, avionics, thermal loads, reserve policy, and drag growth will reduce actual range. This is not a promised range.

E-X shadow energy at 14.4 kWh screens near 95 nmi under the same assumptions, but receives zero baseline credit until installed-pack and integrated-flight evidence exists.

The prior eight-by-one-meter rotor arithmetic remains equivalent disk-area bookkeeping only. It does not freeze an exposed-rotor architecture. Enclosed, ducted, embedded, tilt, and other efficient VTOL concepts remain active trades, with short VTOL plus wing-borne cruise preferred.

## SPACE radiator closure

At emissivity 0.9 and 300 K, simple blackbody radiative flux is ~413 W/m2 before solar/albedo, view-factor, degradation, conduction, and packaging penalties.

Ideal radiator-area screens:

- 700 W: ~1.69 m2
- 1.2 kW: ~2.90 m2
- 2.0 kW: ~4.84 m2

Therefore the 2 kW PUMI thermal-transfer target does not imply that a SPACE pack can reject 2 kW continuously. SPACE requires deployable/distributed radiator area, acceptable higher radiator temperature, thermal storage/derating, or a combination. Exact orbital/surface thermal balance remains BLOCKED.

## HADAL buoyancy sensitivity

Generic density-only screens in 1025 kg/m3 seawater:

- 500 kg/m3 buoyancy material -> ~0.525 kg net buoyancy per liter
- 600 kg/m3 -> ~0.425 kg/L
- 700 kg/m3 -> ~0.325 kg/L

Offsetting 100 kg of negative mass would require roughly 190, 235, or 308 L respectively before pressure compression and packaging. These are not candidate-material specifications. The result reinforces distributed pressure-housing displacement, distributed buoyancy, flooded structures, controlled slightly-negative seabed buoyancy, releasable ballast, and protected emergency ascent rather than a single giant buoyancy backpack.

## SUBSPACE dual qualification

The common mining/space PRIME core must keep mine hazardous-location qualification and space vacuum/outgassing/radiation qualification as separate gates. The architecture therefore places vacuum-compatible tribology and critical sensing inside controlled/sealed joint modules while keeping mine-specific outer boots, contamination barriers, gas sensing, and hazardous-environment electrical provisions replaceable at the mission layer.

A mine-sealed joint is not automatically space-qualified; a space-qualified joint is not automatically safe in a hazardous mine atmosphere.

## OLV-4 fairing blocker

The v0.4 PSDM external screen is ~1.95 x 2.00 x 1.90 m. Carrying a 2.00 x 1.90 m face inside a circular fairing requires a circumscribed diameter of:

sqrt(2.00^2 + 1.90^2) ~= 2.76 m

before clearance, insulation, separation hardware, or fairing structure.

Therefore the current rectangular PSDM requires roughly a 2.8 m-or-larger internal circular envelope or a cross-section redesign. This is a formal compact-air-launch packaging BLOCKER.

Next branch: compare corner-nested, canted, and circularized four-cassette arrangements. The fairing requirement will not simply be enlarged until the redesign options are compared for mass, structure, access, thermal management, and deployment reliability.

## Promotion state

- AERO: first-order range/endurance screen complete; BLOCKED on CFD, propulsion, transition, acoustics, thermal, flight-control, and reserve validation.
- SPACE: first-order radiator-area screen complete; BLOCKED on full environment-specific thermal closure.
- HADAL: buoyancy sensitivity screen complete; BLOCKED on pressure/hydrostatic/material qualification.
- SUBSPACE: dual-qualification architecture defined; both mine and space certifications remain separate gates.
- PSDM/OLV: volume reduction achieved as a design screen, but circular-fairing compatibility is now a formal blocker requiring redesign.

No experimental or unconventional technology receives additional performance credit from this closure.
