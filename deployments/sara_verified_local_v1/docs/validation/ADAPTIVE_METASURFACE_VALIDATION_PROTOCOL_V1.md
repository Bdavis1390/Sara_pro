# Adaptive Metasurface Scientific-Validation Protocol v1

**Protocol ID:** `SV-META-001-P1`  
**Purpose:** determine whether a bounded Worldshepherd metasurface coupon/array produces commanded, repeatable electromagnetic phase/amplitude control and the predicted beam/null behavior.  
**Current claim boundary:** `REQUIRES_LAB_VALIDATION`. No stealth, cloaking, broadband cancellation, or aerospace-qualified performance is implied.

## 1. Freeze one bounded experiment

The first validation campaign must use **one declared operating band**, one geometry revision, one substrate/material stack, one actuator/tuning mechanism, and one measurement geometry. Do not use the full “195 nm to 9675 nm” research span as a single validation claim.

Before fabrication, freeze:

- frequency band `[f_low, f_high]`;
- polarization(s);
- incidence angle(s);
- unit-cell periodicity and geometry revision;
- material property source and uncertainty;
- command-state set;
- intended phase/amplitude response per state;
- array size and aperture geometry;
- primary far-field or scattering endpoint;
- thermal/power envelope;
- pass/fail and exclusion rules.

## 2. Hypotheses

### H0 — null
Observed phase, amplitude, resonance, beam, or null changes are explainable by measurement uncertainty, fixture motion, cable drift, calibration error, temperature drift, mutual coupling not represented in the model, or uncontrolled material variation.

### H1 — controlled boundary condition
The commanded tile/material states produce a repeatable phase/amplitude response and corresponding array-level field redistribution consistent with the preregistered electromagnetic model within the declared uncertainty budget.

## 3. Test articles

Initial internal campaign should include:

1. **reference coupon** — substrate/feed/fixture without the active metasurface function where practical;
2. **single-cell or small periodic coupon** — for resonance and unit-cell response;
3. **active small array** — for command-state and spatial field tests;
4. at least **3 independently assembled/fabricated active coupons or arrays** if manufacturing volume permits.

A power-cycle repeat of one device is not manufacturing replication.

## 4. Simulation freeze

Before hardware measurement, archive/hash:

- solver and version;
- geometry/material files;
- mesh or discretization settings;
- boundary/port conditions;
- convergence study;
- assumed material dispersion/loss;
- predicted S-parameters;
- predicted phase and amplitude for every command state;
- predicted thermal change where active loss/heating matters;
- predicted array factor/radiation or scattering pattern for the selected test geometry.

Prime-indexed modes, if retained as an indexing/decomposition device, must not be labeled quantum modes unless an independently justified quantum degree of freedom is actually modeled and measured.

## 5. Calibrated RF/microwave measurement chain

For RF/microwave validation, use a vector network analyzer or equivalent calibrated measurement system appropriate to the band.

Record:

- VNA/instrument make, model, serial, firmware/software;
- calibration-kit ID and calibration validity;
- calibration method selected for the fixture (for example SOLT, TRL, or another method justified by the laboratory);
- reference plane;
- cable/fixture configuration and movement constraints;
- source power;
- IF bandwidth / averaging / sweep settings;
- ambient/device temperature;
- raw complex S-parameter files.

Do not report only screenshots. Preserve the complex raw data.

## 6. Unit-cell / coupon measurements

For each command state and each independent coupon:

1. measure the reference/control condition;
2. measure complex `S11` and, where applicable, `S21` across the frozen band;
3. repeat after returning to the reference state;
4. repeat through at least three complete command-state cycles;
5. record temperature during the sequence;
6. repeat after a full power cycle;
7. where practical, reverse/rotate the fixture to expose systematic asymmetries.

Derived endpoints may include:

- resonance frequency;
- reflection/transmission magnitude;
- phase shift relative to reference;
- usable phase range;
- insertion/reflection loss;
- hysteresis;
- state-switch repeatability;
- temperature coefficient.

## 7. Array-level beam/null test

For a radiating or scattering array, use a measurement geometry consistent with **IEEE 149-2021** antenna-measurement principles where applicable. The lab must verify far-field/near-field criteria and range suitability for the actual aperture and frequency.

Pre-register at least two discriminating states:

- **State A:** reference/broadside or declared baseline pattern;
- **State B:** commanded steering or null state with a predicted angle and level.

Measure:

- normalized radiation/scattering pattern over the declared angular region;
- beam peak angle;
- half-power beamwidth where meaningful;
- sidelobe levels where meaningful;
- null angle and null depth for a nulling experiment;
- total/relative efficiency where the setup supports it;
- cross-polarization if relevant.

A measured reduction at one angle is not “stealth.” It is a bounded pattern/scattering observation under the tested geometry.

## 8. Thermal and coupling confounders

At minimum evaluate:

- temperature vs phase/amplitude drift;
- cable/connector movement;
- fixture repeatability;
- actuator bias/current noise;
- mutual coupling between cells;
- command timing and settling time;
- source-power dependence;
- sensor calibration;
- chamber/range background;
- polarization and alignment error.

Where the proposed mechanism relies on material tuning, measure the actual electrical/optical material response where possible rather than treating commanded voltage/current/temperature as proof that `epsilon`, `mu`, or `sigma` took the modeled value.

## 9. Internal scientific success criteria

The project may advance toward `INTERNAL_TEST` only when:

1. measured command-state phase/amplitude changes exceed combined measurement uncertainty;
2. state ordering/sign agrees with the preregistered prediction or the disagreement is explicitly recorded;
3. the effect repeats across power cycles and, where available, independently fabricated devices;
4. measured S-parameter features correlate with the frozen model within a reported error band;
5. a predicted array-level beam or null moves to the preregistered region within the uncertainty of the range;
6. thermal/fixture/cable/background controls are insufficient to explain the result;
7. raw S-parameters, pattern data, calibration records, command logs, temperature data, and analysis are hash-bound and recoverable.

No single numeric threshold is hard-coded here because the target performance must be preregistered for the selected architecture and use case before testing.

## 10. Failure/falsification conditions

A result fails the candidate model if, after measurement-system integrity is confirmed:

- command-state response is not reproducible;
- apparent phase shift disappears after calibration/fixture control;
- beam/null location does not follow command state;
- measured response is dominated by heating rather than the predicted tuning mechanism;
- the model requires post-hoc parameter changes outside preregistered uncertainty to match every dataset;
- independent coupons exhibit incompatible behavior.

Negative results remain in the PVK registry.

## 11. Advancement ladder

- **M0:** frozen model, geometry, and measurement plan.
- **M1:** calibrated unit-cell/coupon S-parameter dataset.
- **M2:** repeated command-state response across cycles/devices.
- **M3:** bounded array-level beam/null result with simulation-to-test correlation.
- **M4:** environmental repeat (temperature/orientation/vibration or EMC subset relevant to use case).
- **M5:** independent laboratory replication.
- **M6:** application-specific qualification campaign.

“Stealth,” “cloaking,” or broad-spectrum cancellation language remains blocked unless a later application-specific test defines and measures the relevant scattering metric across angle, frequency, polarization, power, and environment.

## 12. Evidence package

For every run preserve:

`device_id -> geometry/material revision -> calibration -> instrument -> command log -> environment -> raw complex data -> processed data -> model revision -> residuals -> result`

ECHO/PVK should retain SHA-256 digests for the immutable raw files and record any analysis revision separately.

## 13. External-safe statement until M3 closes

> Worldshepherd is developing a reconfigurable metasurface architecture based on established electromagnetic and tunable-material principles. Worldshepherd-specific phase/amplitude, beam-steering, nulling, or scattering performance remains under calibrated coupon/array validation.

## 14. Standards/evidence anchors

- IEEE 149-2021 — recommended practice for antenna measurements where antenna/radiation-pattern measurements are applicable.
- Instrument/vendor calibration procedures and traceable calibration artifacts appropriate to the selected VNA, fixture, frequency band, and range.

The selected laboratory must verify method applicability and current revision before claiming standards conformance.
