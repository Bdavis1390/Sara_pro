# HELIOS-LINK Power-Beaming Validation Protocol v1

**Artifact ID:** WS-HELIOS-VAL.1.0  
**Status:** PREREGISTRATION / BOUNDED LAB VALIDATION SPECIFICATION  
**Claim boundary:** Wireless power transfer by microwave, RF, optical, or laser means is established physics and has been externally demonstrated. No Worldshepherd-specific HELIOS-LINK range, efficiency, pointing, safety, atmospheric, or operational performance is established by that foundation.

## 1. Purpose

Validate one bounded HELIOS-LINK transmitter–propagation–receiver configuration as an energy-transfer system with complete power accounting, geometry, beam profile, pointing, thermal response, and safety evidence.

The first campaign should answer:

1. How much electrical input power enters the declared transmitter boundary?
2. How much radiated/optical power leaves the transmitter aperture?
3. What field/beam distribution exists at the receiver plane?
4. How much usable electrical power leaves the receiver boundary?
5. How do efficiency, pointing error, range, atmospheric/environmental condition, alignment, and thermal state interact?

## 2. External foundation

Foundation references include NASA wireless-power-transmission work and power-beaming demonstrations. NASA has documented microwave and laser WPT development and a laser-powered model-aircraft demonstration. These establish feasibility of electromagnetic power transfer, not HELIOS-LINK performance.

## 3. Freeze the test article and link

Before acquisition, freeze:

- transmitter ID/configuration digest;
- frequency/wavelength and modulation state;
- source electrical input boundary;
- transmitter aperture/optics/antenna geometry;
- receiver aperture and conversion architecture;
- transmitter–receiver separation and coordinate frames;
- expected beam waist/pattern or antenna gain pattern;
- predicted link budget;
- expected end-to-end efficiency;
- alignment/pointing method;
- thermal limits;
- applicable RF/laser/electrical safety classification and facility approval;
- pass/fail and uncertainty criteria.

Any change to aperture, optics, antenna, frequency, power electronics, receiver, range, or geometry creates a new configuration digest.

## 4. Measurement boundaries

Measure separately where possible:

- source electrical input power;
- transmitter conversion efficiency;
- radiated/optical power at or near the transmit aperture;
- propagation/link loss;
- received incident power;
- receiver conversion efficiency;
- delivered electrical load power.

Do not collapse these into one number without retaining the intermediate boundaries.

## 5. Minimum instrumentation

Use calibrated instrumentation appropriate to the chosen band and power level:

- electrical power instrumentation;
- optical/RF power sensor(s);
- beam/pattern or field-strength mapping capability;
- receiver output power/load instrumentation;
- distance and alignment metrology;
- thermal telemetry on source, aperture, receiver, and load;
- environment records where propagation can be affected;
- synchronized acquisition with UTC/time-reference provenance.

Testing must occur under an approved facility safety procedure. This protocol does not authorize hazardous RF, laser, high-voltage, thermal, or flight operations.

## 6. Test sequence

### Stage H0 — Instrument and safety readiness

- calibration evidence present;
- safety boundary approved;
- interlocks/shutdown verified under facility procedure;
- dark/off baseline acquired.

### Stage H1 — Component efficiency

Measure transmitter and receiver independently where practical. Record conversion efficiencies versus bounded input levels and thermal state.

### Stage H2 — Static link

At a short, controlled range:

- acquire input/radiated/received/output power;
- map beam/field profile around the nominal receiver location;
- measure pointing offset sensitivity;
- repeat at multiple input levels within the safe validated range.

### Stage H3 — Range sweep

Repeat over preregistered distances while preserving geometry and measurement boundary definitions.

### Stage H4 — Perturbation tests

Where applicable and safe, test sensitivity to:

- small pointing offsets;
- receiver angular misalignment;
- transmitter/receiver thermal state;
- atmospheric or environmental changes;
- polarization mismatch for RF systems;
- controlled obstruction or multipath condition.

### Stage H5 — Repeatability

Repeat the accepted configuration on at least two independently prepared sessions.

## 7. Derived quantities

### End-to-end efficiency

`eta_e2e = P_load_out / P_source_in`

### Propagation/capture efficiency

`eta_link = P_incident_receiver / P_radiated_aperture`

### Receiver efficiency

`eta_rx = P_load_out / P_incident_receiver`

### Pointing sensitivity

Report power loss versus angular/linear offset, not only a best-case aligned value.

Every derived quantity must carry an uncertainty statement and exact measurement boundary.

## 8. Required controls

- transmitter off / dark baseline;
- receiver electronics self-consumption accounted separately;
- background optical/RF environment characterized;
- detector linearity checked over the measurement range;
- thermal drift characterized;
- geometry and distance independently recorded;
- beam spill/sidelobe or off-axis energy measured sufficiently to support safety and energy accounting;
- no efficiency above unity may be reported without first closing every measurement boundary and calibration error.

## 9. Advancement gates

### Internal-test gate

Requires:

- raw calibrated source/transmitter/receiver/load data;
- source and configuration digests;
- beam/field profile evidence;
- geometry/pointing records;
- thermal/environment records;
- uncertainty budget;
- repeated session;
- ECHO-grade provenance.

### Independent-replication gate

Requires a separate operator/facility or defensible independent chain with independent calibration and no reuse of hidden correction parameters from the originating analysis.

## 10. Claim-safe wording

Before Worldshepherd-specific measurement:

> Wireless power transmission is established and has been demonstrated externally using microwave and laser methods. HELIOS-LINK-specific efficiency, range, beam-control, thermal, safety, and operational performance remain unvalidated until measured on a frozen configuration with complete power and uncertainty accounting.

## 11. Public foundation references

- NASA NTRS, *Wireless Power Transmission (WPT) Technology — Past and Now*: https://ntrs.nasa.gov/citations/20230000093
- NASA, *Power Beaming Flight Demonstration*: https://www.nasa.gov/image-article/power-beaming-flight-demonstration-5/
