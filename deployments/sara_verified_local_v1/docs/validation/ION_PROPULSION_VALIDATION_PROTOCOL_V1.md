# Worldshepherd Ion Propulsion Validation Protocol v1

**Artifact ID:** WS-ION-VAL.1.0  
**Status:** PREREGISTRATION / LAB-EXECUTION SPECIFICATION  
**Claim boundary:** This protocol does not claim that a Worldshepherd-specific ion thruster has been fabricated, tested, qualified, or flight-proven. Established ion-propulsion physics and external flight heritage are foundation evidence only.

## 1. Purpose

Establish a reproducible, transportable validation path for any Worldshepherd gridded-ion or related electrostatic electric-propulsion article. The first objective is not maximum performance. It is to determine whether a specific article produces directly measured thrust and electrical/propellant performance consistent with independently measured inputs, uncertainty, and established electric-propulsion physics.

## 2. External foundation

Use the following as foundation references, not Worldshepherd-specific evidence:

- NASA, *State of the Art of Small Spacecraft Technology — In-Space Propulsion*: gridded-ion systems ionize propellant and accelerate ions through electrostatic grids; published systems span sub-mN to hundreds-of-mN regimes depending on scale.
- NASA/NTRS, *Recommended Practices in Thrust Measurements* (2015): pendulum thrust stands, calibration, error sources, data processing, and uncertainty analysis for micro-N to mN electric-propulsion measurements.
- NASA/NTRS, *Recommended Practices for the Experimental Characterization of Gridded Ion Engines* (2025): transportable characterization methods including perveance, neutralizer behavior, discharge losses, back-streaming limit, and ion transparency.
- NASA NEXT reference performance is an external benchmark only. Published NEXT demonstrations include approximately 0.5–6.9 kW operation, 26–236 mN thrust, and maximum specific impulse around 4190 s. No Worldshepherd article inherits those values.

## 3. Validation questions

A Worldshepherd article may advance only by answering, with measured evidence:

1. Does direct calibrated thrust exceed the stand's blank/null distribution with a preregistered significance criterion?
2. Does thrust scale consistently with beam/acceleration conditions and propellant flow within the tested operating envelope?
3. Are thrust, beam current, beam voltage, mass flow, input power, and plume observables mutually consistent within uncertainty?
4. Does the article remain stable across repeated runs and at least two independently prepared operating sessions?
5. Are facility/background effects small enough that the measured performance is transportable to another facility?

## 4. Minimum facility requirements

Testing requires a facility qualified for the article's voltage, stored energy, vacuum, propellant, RF, thermal, and plasma hazards. The detailed operating procedure belongs to the approved facility SOP and is not defined here.

Minimum measurement capabilities:

- vacuum pressure measurement with calibration/provenance;
- calibrated direct thrust stand suitable for the expected force range;
- time-synchronized electrical measurements for relevant voltage/current channels;
- traceable propellant mass-flow measurement;
- article and facility temperature monitoring;
- data acquisition with UTC or documented monotonic time reference;
- plume/current diagnostics appropriate to the article class when available;
- remote shutdown/interlocks per facility policy.

## 5. Pre-registration package

Freeze before powered testing:

- article ID and configuration digest;
- geometry/configuration drawing revision;
- propellant identity and lot/source;
- power-processing configuration;
- predicted operating points and expected force range;
- predicted thrust-to-power and specific-impulse ranges, with model source;
- stand calibration plan;
- null/blank plan;
- facility-background characterization plan;
- pass/fail criteria;
- known failure modes;
- raw-data naming and hash/custody plan.

Changing a configuration after pre-registration creates a new configuration digest and new test series.

## 6. Required measurements

At each accepted operating point, record at minimum:

- thrust and thrust-stand calibration state;
- chamber pressure and relevant background pressure trend;
- propellant mass flow;
- beam/accelerating potential(s) and relevant current(s);
- total article electrical input power and measurement boundary;
- neutralizer/cathode measurements when applicable;
- article and thrust-stand temperature channels;
- acquisition timestamps;
- all trip/fault events;
- operator and facility identifiers.

Recommended gridded-ion characterization, where applicable:

- perveance/current-voltage behavior;
- neutralizer operating envelope;
- discharge losses;
- electron back-streaming limit;
- ion transparency;
- plume divergence or beam-current distribution.

## 7. Thrust-stand controls

The thrust result is invalid for maturity promotion unless all applicable controls are executed:

- pre-test calibration with traceable force or equivalent calibration method;
- post-test calibration to quantify drift;
- powered-null or electrical dummy-load control where practical;
- zero-thrust/propellant-off baseline;
- thermal-drift characterization;
- cable/flexure/feedthrough influence characterization;
- magnetic/electrostatic coupling review;
- chamber pumping/background-pressure review;
- vibration/seismic/background-force review;
- orientation or reversal control when physically meaningful and safe.

Record calibration residuals and use them in the uncertainty budget.

## 8. Derived quantities

Use SI units and record equation/source IDs.

### 8.1 Thrust-to-power

`T/P = measured_thrust_N / measured_input_power_W`

The power boundary must be declared. Thruster-only and system/PPU input power must not be silently mixed.

### 8.2 Specific impulse

For a conventional propellant-expelling article:

`Isp = T / (m_dot * g0)`

where `g0 = 9.80665 m/s^2` and `m_dot` is the propellant mass flow crossing the declared propulsion-system boundary.

### 8.3 Efficiency

Use only an efficiency definition appropriate to the article class and state the exact boundary/equation. Do not compare thruster efficiency to system efficiency without the power-processing boundary.

## 9. Uncertainty and acceptance

The report must include a combined uncertainty budget covering at least:

- force calibration and stand noise/drift;
- mass-flow uncertainty;
- voltage/current/power uncertainty;
- timing alignment;
- pressure/facility effects;
- repeatability;
- data-reduction/model uncertainty where derived quantities are reported.

### Internal-test gate

A Worldshepherd article may be considered for `internal_test` only when:

- the physical article and configuration are uniquely identified;
- raw data and calibration records are SHA-256 bound;
- ECHO-grade provenance fields are complete;
- direct thrust is distinguishable from null/control behavior under the preregistered criterion;
- the uncertainty interval and all failed/off-nominal runs are retained;
- no unexplained force is used to inflate conventional performance claims;
- PVK review accepts the evidence package.

### Independent-replication gate

Requires a separate facility/operator or otherwise defensible independent chain, a newly executed calibration chain, and no hidden use of the originating analysis output as the independent result.

## 10. Failure criteria

The campaign does **not** validate article performance if any of the following remains unresolved:

- thrust signal disappears under calibration/null/reversal control;
- stand drift is comparable to the claimed signal without adequate correction evidence;
- chamber pressure/facility interactions dominate the result;
- electrical or propellant boundaries are incomplete;
- raw/native data are unavailable;
- calibration status is unknown or expired for required channels;
- independent rerun cannot reproduce the bounded effect where replication is claimed.

A null result is a valid technical result and should narrow the design space rather than be discarded.

## 11. Evidence package

Return evidence using `ws-lab-evidence-package-1` plus the corresponding `ws-physics-record-1` candidate record. Minimum file roles:

- raw thrust time series;
- calibration files;
- raw electrical channels;
- mass-flow data;
- pressure/environment data;
- method/SOP references and deviations;
- processed result tables;
- uncertainty analysis;
- test report.

SARA structural acceptance of the package does not itself promote maturity.

## 12. Claim-safe output

Before Worldshepherd-specific physical testing:

> Ion propulsion is an established propulsion class. Worldshepherd-specific ion-thruster performance remains unvalidated until a physical article is tested with calibrated thrust, power, flow, facility-background, uncertainty, and provenance controls.

After a successful internal campaign, wording must remain limited to the tested article/configuration and operating envelope until independent replication and qualification gates close.

## 13. Public foundation references

- NASA Small Spacecraft Systems Virtual Institute, *4.0 In-Space Propulsion*: https://www.nasa.gov/smallsat-institute/sst-soa/in-space_propulsion/
- NASA NTRS, *Recommended Practices in Thrust Measurements*: https://ntrs.nasa.gov/citations/20150008062
- NASA NTRS, *Recommended Practices for the Experimental Characterization of Gridded Ion Engines*: https://ntrs.nasa.gov/citations/20250002123
- NASA/NEXT reference performance: https://discovery.larc.nasa.gov/pdf_files/01-NEXT-SBenson-2.pdf
