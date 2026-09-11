# WS-NSB v2.1 — G16 Electrothermal Driver Gate

## Purpose

G16 advances the G15 finite-geometry electromagnetic transfer model by adding a bounded actuator-drive layer. It tests whether G12 modal commands remain reachable after coil inductance, mutual coupling, voltage saturation, current limits, command latency, temperature-dependent copper resistance, and lumped coil heating are introduced.

## Model stack

1. **G15 finite-geometry transfer map** — finite-segment circular-coil Biot-Savart field model plus solved scalar-potential conduction current.
2. **Coil circuit** — one current state per coil with an inductance matrix. Self inductance uses a thin-wire air-core circular-coil approximation. Mutual terms use the source-coil finite-segment field at the receiver center multiplied by receiver area and turns.
3. **Driver** — averaged bounded voltage source with proportional current feedback, hard current limit, and explicit command latency.
4. **Thermal state** — one lumped copper temperature per coil, Joule heating, temperature-dependent resistance, and idealized natural-convection cooling.
5. **Closed-loop plant** — realized coil currents are projected through the G15 transfer matrix into the three G12 Lorentz-force-curl modes and injected into the existing G10/G12 nonlinear MHD control plant.

## Acceptance tests

G16 requires:

- a well-conditioned coupled inductance matrix;
- bounded nominal step response with <=2% final current error and settling inside the configured limit;
- a 60 s high-current thermal dwell below the configured thermal ceiling;
- correct rejection of a deliberately fast 400 Hz current command as bandwidth-limited;
- retained closed-loop target-mode reduction after command latency and RL/thermal dynamics;
- voltage/current bounds and divergence limits preserved.

## Claims boundary

G16 is `SIMULATED_ONLY`.

The inductance model is an engineering approximation, not a measured LCR matrix or exact full Neumann-integral winding solution. The thermal model does not resolve insulation, potting, radiation, contact thermal resistance, conductor hot spots, or structure. The driver is not a switching-converter, EMI, transistor, gate-drive, or calibrated power-electronics model. No measured hardware parameters are used.

Passing G16 therefore does **not** establish laboratory adaptive electromagnetic control, plasma control, propulsion, shielding, stealth, cloaking, certification, or operational capability.

## CLI

```bash
ws-nsb-g16 --output ws_nsb_g16_report.json
ws-nsb-g16 --verify ws_nsb_g16_report.json
```

The JSON report is deterministically bound by the existing Worldshepherd canonical SHA-256 digest mechanism.
