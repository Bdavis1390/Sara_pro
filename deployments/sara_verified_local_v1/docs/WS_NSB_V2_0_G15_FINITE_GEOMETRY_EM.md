# WS-NSB v2.0 G15 — Finite-Geometry Quasi-Static EM Gate

## Purpose

G15 advances the G14 geometry-specific electromagnetic reference in two independent ways:

1. the eight circular control coils are integrated as finite segmented current loops using the Biot-Savart law instead of point magnetic dipoles; and
2. the conductive-medium current density is derived from a solved scalar electric potential instead of being prescribed directly.

The resulting Lorentz-force-curl fields are projected into the same three G12 feedback modes and used to drive the previously validated nonlinear MHD control plant.

## Reference problem

The reference domain is a 0.10 m square conductive region with uniform conductivity 3.4×10^6 S/m. Full-width ideal electrodes impose 14.7059 mV across the y direction, corresponding analytically to approximately 5×10^5 A/m² for the uniform-conductivity reference. Side walls are electrically insulating.

Eight 200-turn circular coils of 10 mm radius surround the region on a 70 mm radius ring, 25 mm from the control plane. Each loop is discretized into 96 line segments. The current limit remains 3.5 A per coil.

## Independent verification elements

G15 verifies the segmented loop calculation against the exact on-axis circular-loop field

`Bz = mu0*N*I*R^2 / (2*(R^2+z^2)^(3/2))`

at segment counts 24, 48 and 96. It also records the Laplace-solve residual, mean conduction current, current uniformity and numerical current-divergence diagnostic.

The finite-geometry transfer matrix is compared with the G14 dipole transfer as a model-delta diagnostic, but agreement with G14 is not itself an acceptance requirement because G15 intentionally increases physical fidelity.

## Acceptance intent

The default gate requires:

- 96-segment on-axis loop-field relative error <= 5e-4 with approximately second-order segment refinement,
- mean conduction-current relative error <= 2e-4 and relative current nonuniformity <= 2e-3,
- full three-mode transfer rank and condition number <= 10,
- nominal modal allocation residual <= 1e-3 with no current saturation,
- all single-coil-out cases retaining rank three with worst residual <= 1e-2,
- at least 12% reduction in targeted modal energy in the G12 closed-loop test,
- finite-geometry closed-loop result within 5% of the ideal G12 result,
- bounded coil current and divergence <= 1e-10.

## Claims boundary

G15 remains `SIMULATED_ONLY`. The finite-segment line integral does not model conductor cross-section, skin/proximity effects, mutual inductance, driver electronics, ferromagnetic materials, or full-wave propagation. The electric solve assumes uniform scalar conductivity, ideal full-width electrodes and no contact impedance, Hall term, electrode polarization, fluid-motion-induced electric field, or plasma sheath.

Passing G15 therefore does not establish laboratory adaptive electromagnetic control, plasma control, propulsion, shielding, stealth, cloaking or operational capability. Those require later geometry, thermal, materials and bench validation gates.
