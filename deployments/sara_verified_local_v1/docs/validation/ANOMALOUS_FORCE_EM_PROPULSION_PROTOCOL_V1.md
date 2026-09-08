# Worldshepherd Anomalous-Force / EM Propulsion Validation Protocol v1

**Artifact ID:** WS-AFEM-VAL.1.0  
**Status:** PREREGISTRATION / FALSIFICATION-FIRST TEST SPECIFICATION  
**Physics boundary:** Any interpretation implying thrust without identified expelled momentum, photon momentum, interaction with an external field/environment, or another quantitatively closed momentum exchange remains a P4/Beyond-Standard-Model hypothesis in Worldshepherd unless and until independent evidence establishes otherwise.

## 1. Purpose

Provide a rigorous path for testing resonant electromagnetic, electrostatic, electrogravitic, cavity, dielectric, superconducting, or related anomalous-force concepts without converting balance deflection into a propulsion claim prematurely.

The first experimental question is deliberately narrow:

> Does a reproducible residual force remain after all known force-transfer paths and measurement artefacts have been bounded below the residual, and does that residual survive independent replication?

A positive balance reading is not by itself evidence of reactionless propulsion or new physics.

## 2. External foundation and disconfirming evidence

Established baseline physics includes electromagnetic momentum transfer and radiation pressure. For ideal one-way electromagnetic radiation,

`F_photon = P / c`

with `c = 299792458 m/s`.

Published high-accuracy EMDrive testing by Tajmar, Neunzig, and Weikert used an improved thrust balance, battery-powered onboard electronics to reduce feedthrough interactions, thermal/magnetic controls, multiple resonances, and null configurations. Their tested EMDrive configurations produced no anomalous thrust above the photon-thrust scale and demonstrated how thermal, mechanical, magnetic, and feedthrough effects can create false positives.

That result constrains the tested EMDrive family and measurement claims. It does not logically rule out every conceivable anomalous-force hypothesis. Worldshepherd therefore treats it as a **minimum experimental-control baseline**, not as permission either to claim or categorically dismiss every future concept without testing.

## 3. Pre-registration

Before unblinded force data are acquired, freeze:

- article ID, geometry, materials, configuration digest, and mass properties;
- operating principle as a testable statement, not a marketing description;
- drive frequency/voltage/current/power/state ranges;
- predicted force magnitude, direction, scaling law, transient behavior, and uncertainty;
- declared momentum-transfer hypothesis;
- photon-thrust baseline for every powered condition;
- force-sensor/balance architecture and expected resolution;
- calibration method and force standard;
- vacuum/atmospheric condition;
- thermal, magnetic, electrostatic, vibration, acoustic, gas-flow, cable/feedthrough, center-of-mass, and RF-leakage controls;
- null, reversal, dummy-load, off-resonance, and sham conditions;
- statistical decision rule and stopping rule;
- raw-data/custody plan.

If the predicted signal or analysis rule is changed after viewing unblinded data, the changed test is a new exploratory campaign and cannot be represented as a preregistered confirmation.

## 4. Minimum measurement system

Use a facility and apparatus appropriate to the voltage, RF, vacuum, stored-energy, thermal, magnetic, electrostatic, and mechanical hazards. Facility SOPs govern operation.

The measurement system should provide:

- calibrated force/torque sensitivity below the smallest claim being tested;
- independent displacement or force readout where practical;
- synchronized electrical power/current/voltage data;
- temperature sensing on article, amplifier/power electronics, balance, and nearby structural points;
- magnetic-field monitoring where current or magnetic materials are present;
- chamber pressure and gas/environment monitoring;
- vibration/seismic monitoring adequate to identify correlated disturbances;
- RF leakage/field characterization appropriate to frequency and power;
- UTC or documented monotonic timing with provenance.

## 5. Mandatory control classes

A maturity claim is blocked until every applicable class is tested or explicitly justified as not applicable.

### 5.1 Force calibration

- pre-run calibration across the expected force range;
- post-run calibration to detect drift;
- multiple calibration amplitudes rather than one-point calibration where feasible;
- calibration residuals retained in raw evidence;
- force standard traceability recorded.

### 5.2 Thermal / center-of-mass

- characterize warm-up and cooldown transients;
- record temperature at enough locations to test correlation with apparent force;
- test a thermal dummy or equivalent non-propulsive heating condition where practical;
- quantify center-of-mass shift and mounting stress susceptibility;
- do not subtract thermal drift with a flexible fitted model unless that model was preregistered or independently validated on controls.

### 5.3 Electrical feedthrough / cable forces

- characterize cable stiffness, flexure, and current-dependent force;
- prefer onboard/battery power for high-sensitivity anomalous-force tests when technically appropriate, because it reduces conductive feedthrough pathways;
- if feedthroughs remain, execute powered dummy-load controls with equivalent current/power routing.

### 5.4 Magnetic coupling

- map relevant static/background magnetic field;
- identify high-current loops, ferromagnetic components, damping magnets, and chamber structures;
- reverse current or orientation where meaningful to distinguish magnetic-force signatures;
- measure or bound force from known magnetic coupling below the claimed residual.

### 5.5 Electrostatic coupling

- monitor high-voltage state and nearby conductive surfaces;
- test grounding/shielding/configuration changes that should alter electrostatic force but not the hypothesized propulsion effect;
- inspect charge accumulation and leakage paths;
- quantify electrostatic attraction/repulsion where applicable.

### 5.6 Gas / ion / corona / outgassing

- distinguish atmospheric and vacuum behavior;
- monitor chamber pressure during power cycles;
- check for corona, ion wind, leakage current, ablation, evaporation, or outgassing that can carry momentum;
- retain mass-change evidence if material loss is plausible.

### 5.7 Mechanical / vibration / acoustic

- record structural vibration and impulsive events;
- test pump, fan, relay, actuator, and switching artefacts;
- characterize resonance of the balance/support structure;
- reject signals phase-locked to known mechanical disturbances unless the coupling path is quantitatively closed.

### 5.8 RF leakage / ordinary photon momentum

- estimate total radiated/leaked RF power and directional asymmetry;
- calculate the corresponding photon-force scale;
- treat any result at or below the unresolved photon-momentum budget as compatible with ordinary electromagnetic momentum transfer.

## 6. Required test matrix

The first confirmatory campaign must include, randomized or blinded where practical:

1. power off / baseline;
2. powered dummy load;
3. article on-resonance or target state;
4. article off-resonance / non-target state;
5. orientation reversed by 180 degrees around the measurement-relevant axis where safe and mechanically valid;
6. orientation perpendicular to the measurement axis or another geometric null where meaningful;
7. repeated warm-up/cooldown cycles;
8. at least two independently assembled or re-mounted sessions.

The configuration order should not simply progress from low to high power if that creates a confounded thermal time trend.

## 7. Decision variables

Record and report:

- signed force or torque with uncertainty;
- input electrical power with a declared boundary;
- `F / P`;
- photon-force ratio:

`R_photon = F_measured * c / P`

- correlation with temperature, magnetic field, pressure, vibration, current, and timing;
- signal reversal consistency under article reversal;
- control/null distributions;
- between-session repeatability.

A value `R_photon > 1` is not proof of anomalous propulsion. It only shows the measured force exceeds the ideal one-way photon-force value for the declared power boundary; all other momentum-transfer and artefact paths still have to be bounded.

## 8. Falsification gates

### Gate AF-0 — Instrument competence

The stand resolves known calibration forces in the target range with a documented uncertainty budget. Failure blocks all subsequent physical claims.

### Gate AF-1 — Null/control separation

The target configuration must separate from preregistered dummy/off/null distributions. Failure classifies the result as `NULL_OR_UNRESOLVED`.

### Gate AF-2 — Directionality

The signal must reverse or transform according to the preregistered physical prediction when the article orientation/configuration is reversed, while control artefacts do not mimic the same transformation.

### Gate AF-3 — Confounder closure

Thermal, magnetic, electrostatic, gas-flow, RF/photon, cable/feedthrough, center-of-mass, vibration, and calibration effects must each be measured or conservatively bounded below the residual claimed as unexplained.

### Gate AF-4 — Scaling law

The residual must follow a preregistered scaling law with power/frequency/field/configuration more closely than competing artefact models.

### Gate AF-5 — Internal replication

The effect survives at least two independent setup/re-mount sessions and is not dependent on one analysis choice.

### Gate AF-6 — Instrument independence

A materially different force readout, balance architecture, or independent instrumentation reproduces the bounded effect.

### Gate AF-7 — External replication

An external team/facility reproduces the effect from a frozen protocol/configuration with its own calibration and raw-data chain.

Only after AF-7 and governance review can a P4 record be considered for Worldshepherd `independently_replicated`; even then, `new_physics_confirmed` remains false until a coherent physical interpretation survives broader experimental constraints.

## 9. Evidence handling

Every physical-test candidate record requires ECHO-grade provenance:

- source manifest digest;
- article/configuration digest;
- acquisition UTC/time reference;
- calibration IDs;
- raw-data SHA-256 digests;
- environment/coordinate-frame metadata;
- custody events;
- preregistered prediction IDs;
- explicit confounder states;
- replication state.

External packages should use `ws-lab-evidence-package-1`. SARA package acceptance is structural only and cannot promote maturity.

## 10. Interpretation ladder

Use the most conservative applicable label:

- `NO_SIGNAL`: target is statistically consistent with controls/nulls;
- `ARTEFACT_IDENTIFIED`: apparent force is explained by a measured coupling path;
- `UNRESOLVED_RESIDUAL`: residual remains but one or more confounders are not closed;
- `ANOMALY_CANDIDATE`: preregistered residual survives internal controls and replication but not external independent replication;
- `INDEPENDENT_REPLICATION_REQUIRED`: high-quality internal evidence merits external reproduction;
- `INDEPENDENTLY_REPLICATED_BOUNDED_EFFECT`: external reproduction exists for a precisely bounded configuration; physical interpretation still requires separate review.

Do not use `reactionless propulsion`, `electrogravitic propulsion confirmed`, `gravity control`, `propellantless breakthrough`, or equivalent external wording merely because a balance deflection is observed.

## 11. Claim-safe output

Current Worldshepherd wording:

> Resonant electromagnetic and electrostatic systems can produce ordinary radiation-pressure, field-coupling, thermal, mechanical, plasma, and environmental forces. Worldshepherd anomalous-force concepts remain hypotheses until a residual survives calibrated nulls, quantified confounders, repeated internal tests, instrument-independent measurement, and external replication.

## 12. Public foundation / disconfirming reference

- Tajmar, Neunzig, Weikert, *High-accuracy thrust measurements of the EMDrive and elimination of false-positive effects*, CEAS Space Journal 14, 31–44 (2022): https://link.springer.com/article/10.1007/s12567-021-00385-1
- NASA NTRS, *Recommended Practices in Thrust Measurements*: https://ntrs.nasa.gov/citations/20150008062
