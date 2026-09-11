# WS-NSB v1.9 G14 — Geometry-Specific EM Forward Map

## Purpose

G14 replaces the synthetic G13 transfer matrix with a bounded geometry-specific quasi-static electromagnetic forward model. Eight circular coils are represented by magnetic dipoles at fixed locations around a 0.10 m square control region. A prescribed uniform in-plane conduction-current density interacts with the resulting out-of-plane magnetic field, producing an in-plane Lorentz force whose curl is projected onto the three G12 control modes.

## Reference geometry

- 16×16 control grid over a 0.10 m square domain
- reference velocity: 0.03 m/s
- reference density: 6400 kg/m³
- imposed conduction-current density: 5×10^5 A/m² in the y direction
- eight coils on a 0.070 m radius ring
- coil radius: 0.010 m
- 200 turns per coil
- standoff: 0.025 m
- angular offset: 22.5°
- conductor cross section: 1.0 mm²
- current limit: 3.5 A per coil

The magnetic model uses the point-dipole moment

`m = N I π r²`

and the analytic dipole field/gradient at the control plane. For prescribed in-plane current density `J=(Jx,Jy,0)` and `B=(0,0,Bz)`, the vorticity-source term is derived from

`curl(J×B)_z / rho = -(Jx dBz/dx + Jy dBz/dy)/rho`.

The resulting physical source is nondimensionalized by `U_ref²/L_ref²` and projected onto the G12 modal basis.

## Required cases

G14 executes:

1. nominal geometry allocation and modal reachability,
2. a +1 mm coil-standoff model mismatch followed by recalibration,
3. all eight possible single-coil-out cases and worst-case reporting,
4. a deliberately unreachable 3× command for saturation detection,
5. the G12 closed-loop controller through the geometry-derived transfer matrix.

The report also records approximate coil resistance, copper mass, Joule power, and magnetic-field magnitude for the nominal command.

## Acceptance intent

The default gate requires full three-mode rank, condition number ≤ 8 for the nominal geometry, nominal and recalibrated modal residual ≤ 5×10^-4, worst single-coil-out residual ≤ 5×10^-3, explicit saturation detection for the unreachable command, at least 15% closed-loop target-mode reduction, geometry-map performance within 2% of the ideal G12 result, bounded coil current, and velocity/magnetic divergence ≤ 1×10^-10.

## Claims boundary

This remains `SIMULATED_ONLY` evidence. The coil field is a magnetic-dipole approximation, not exact finite-wire Biot-Savart integration and not a full-wave Maxwell solution. Mutual inductance, ferromagnetic material, eddy-current redistribution, measured conductivity, electrode/contact physics, thermal rise, mechanical packaging, driver electronics, and laboratory calibration are not represented.

Passing G14 therefore does **not** establish hardware adaptive electromagnetic control, plasma control, propulsion, shielding, stealth, cloaking, or operational capability. It establishes only that this bounded geometry-specific reference model has a usable simulated control subspace under the declared assumptions.
