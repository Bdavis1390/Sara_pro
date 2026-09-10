# Worldshepherd PRIME v0.6 — PSDM-4 Circularization and PUMI Hardpoint Closure

Status: engineering screen / architecture target / claims-controlled.

This closure attacks the v0.5 OLV-4 circular-fairing packaging blocker without enlarging the PRIME body or silently relaxing PUMI/PSDM constraints.

## 1. PSDM-4 circularization trade

Current SPACE-equipped PRIME launch-fold envelope target: 1.60 m axial x 0.82 m x 0.75 m cross-section. Four raw folded-body cross-sections therefore occupy approximately 2.46 m^2 before cassette walls, service gaps, primary structure, thermal routing, deployment mechanisms, and clearance.

A circular section provides the following first-order area screen:

- 2.45 m clear internal diameter: about 4.71 m^2; folded-body occupancy about 52.2%.
- 2.55 m clear internal diameter: about 5.11 m^2; folded-body occupancy about 48.2%.
- 2.65 m clear internal diameter: about 5.52 m^2; folded-body occupancy about 44.6%.

Area alone does not prove geometric fit. It shows that the v0.5 problem is primarily rectangular-cassette inefficiency rather than raw PRIME cross-sectional area.

The v0.6 geometry branch therefore uses three gates:

1. PSDM-4C-FALLBACK: <= 2.65 m clear internal diameter using conservative cassette packaging.
2. PSDM-4C-OBJECTIVE: <= 2.55 m clear internal diameter using conformal/canted four-petal cassettes and a central service spine.
3. PSDM-4C-STRETCH: <= 2.45 m clear internal diameter if full CAD, deployment clearances, structural paths, and service routing close.

No cassette or PSDM mass reduction is credited from circularization until CAD and FEA demonstrate it.

## 2. Four-petal architecture

The preferred v0.6 topology places four independent conformal cassettes around a central service/structure spine. Each cassette remains independently restrained, powered, monitored, conditioned, and deployable. The shape may taper or clip unused corner volume around the folded robot rather than preserving the old full rectangular cassette section.

The central spine carries common PSDM structure, service power distribution, thermal manifolds where used, timing/data backbone, and launch-vehicle interface loads. It must not create a common release single point of failure: each bay retains an independent final deployment release path.

## 3. PUMI-X hardpoint screen

Existing PUMI-X development proof targets remain 22.5 kN resultant working-direction proof load and 3.75 kN-m proof moment based on the 1.5x development screen.

At the current 0.55 m upper-to-pelvic hardpoint separation, the 3.75 kN-m proof moment produces an approximately 6.82 kN upper/lower force couple. A simple worst-direction distribution with 22.5 kN axial proof load shared across four nodes gives approximately 5.63 kN/node axial contribution. If moment-couple load is shared by the two nodes in the loaded upper or lower pair, it adds approximately 3.41 kN/node, producing about 9.03 kN at the most highly loaded node before local secondary effects.

The existing 10 kN/node initial article proof target therefore remains a useful first screen, but it is not yet a final requirement. Detailed FEA must add local eccentricity, latch preload, bearing, peel, torsion, impact, manufacturing tolerance, thermal strain, and fatigue.

A candidate mechanical article may use a replaceable metallic bearing/pin cartridge isolated from the composite primary structure through a CF-PAEK or equivalent transition collar. A 14 mm pin carrying 10 kN in ideal double shear would see only about 32.5 MPa nominal shear; a 10 mm-thick local bearing stack at the same load would screen at about 71 MPa nominal bearing stress. These calculations show that local composite transfer, insert pullout, peel, fatigue, and damage tolerance are more likely to govern than ideal pin shear. Material allowables are not assigned until coupon/subcomponent evidence exists.

Baseline hardpoint cartridge: qualified aerospace titanium candidate.
Experimental challengers: lighter hybrid composite/metal cartridge and WS-AlTi graded-node article only after its own coupon/joint gates pass.

## 4. Required v0.6 structural load cases

PUMI/PSDM FEA and subsequent test articles must include, at minimum: +X/-X, +Y/-Y, +Z/-Z; roll/pitch/yaw moments; combined load+moment; latch preload; pack CG tolerance; dynamic step/stumble loading; AERO thrust/reaction loads; HADAL drag/buoyancy loads; launch restraint interaction; wet/salt exposure; vacuum/thermal-cycle exposure for SPACE; damaged-laminate and one-latch-degraded cases.

Launch restraint remains separate from PUMI. PSDM cassettes carry launch acceleration/vibration into dedicated PRIME restraint nodes rather than forcing PUMI alone to be a rocket restraint.

## 5. OLV-4 packaging decision

The v0.5 rectangular PSDM cross-section requiring roughly 2.76 m circular diameter remains a failed layout, not a passed requirement. OLV-4 integration is now gated on PSDM-4C CAD proving one of the <=2.65/2.55/2.45 m internal-diameter configurations with all four occupied bays, service routing, thermal hardware, deployment clearance, tolerances, and launch restraint structure represented.

OLV-4 propulsion/staging design is outside this architecture record. OLV-4 remains a partner/launch-vehicle development program carrying one PSDM-4 with four PRIME units.

## 6. Status after v0.6

- PRIME-4 grouping: ARCHITECTURE LOCKED.
- Four PRIME per PSDM-4 / OLV-4: ARCHITECTURE LOCKED.
- PSDM-4C four-petal circularization: ENGINEERING TARGET.
- 2.65 m clear-ID fallback: TARGET — requires CAD.
- 2.55 m clear-ID objective: TARGET — requires CAD.
- 2.45 m clear-ID stretch: TARGET — requires CAD.
- 10 kN/node PUMI article proof screen: RETAINED DEVELOPMENT SCREEN.
- titanium/CF-PAEK hardpoint cartridge: BASELINE DESIGN CANDIDATE.
- WS-AlTi hardpoint credit: BLOCKED pending material/joint evidence.
- OLV-4 packaging: BLOCKED until circularized CAD closes.
- PSDM mass savings from circularization: NOT CURRENTLY CLAIMED.

Next closure: parameterized CAD of the four-petal section, node-level laminate/insert FEA, and a PSDM mass/inertia update using actual geometry rather than bounding boxes.
