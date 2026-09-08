# TIDELENS / Specular MIST Sensing Validation Protocol v1

**Artifact ID:** WS-TIDELENS-VAL.1.0  
**Status:** PREREGISTRATION / HARDWARE-AND-DATA VALIDATION SPECIFICATION  
**Claim boundary:** Radar and electromagnetic sensing are established physics. Worldshepherd-specific detection, classification, localization, RCS inference, clutter rejection, or low-observable performance must be demonstrated on calibrated measured data and cannot be inferred from simulation alone.

## 1. Purpose

Create a reproducible path from synthetic/simulated sensing work to calibrated measured evidence for TIDELENS / Specular MIST.

The campaign separates four questions:

1. Is the sensor calibrated and stable?
2. Is the measured target/background dataset trustworthy and geometrically defined?
3. Does the signal-processing/inference method perform on held-out measured data?
4. Does performance persist across geometry, clutter, environment, hardware state, and time?

## 2. External foundation

NIST radar-cross-section metrology demonstrates that calibration, background separation, drift, dynamic range, geometry, and measurement uncertainty can materially change inferred target scattering. Newer NIST close-range work also shows that conventional far-field RCS assumptions can fail when targets are only partially illuminated.

These references establish measurement constraints, not Worldshepherd sensor performance.

## 3. Frozen campaign definition

Before collection, freeze:

- sensor hardware/firmware/software configuration digest;
- waveform/frequency/bandwidth/polarization definitions;
- antenna/aperture geometry and coordinate frame;
- target classes and ground-truth definitions;
- range/angle/environment matrix;
- calibration artifacts and procedures;
- background/clutter conditions;
- train/validation/test split policy;
- detection, localization, identification, and false-alarm metrics;
- preregistered operating thresholds;
- data-retention and provenance plan.

A threshold tuned after viewing the held-out test set creates an exploratory result and requires a new untouched test set for confirmation.

## 4. Calibration and measurement assurance

For each collection session record:

- calibration-target identity and accepted reference model/value;
- background/no-target measurement;
- gain/phase/time/frequency calibration state as applicable;
- system dynamic range and noise floor;
- drift over the collection interval;
- target and sensor coordinates/orientation;
- environmental conditions;
- hardware/software version and configuration digest.

Where RCS is inferred, record whether far-field assumptions are valid. If not, use an explicitly appropriate effective/near-field measurement model rather than labeling the value intrinsic far-field RCS.

## 5. Dataset classes

Maintain explicit separation between:

- synthetic/simulated data;
- benchtop/lab measured data;
- controlled range measured data;
- field measured data;
- independent external data.

Never aggregate these into one performance metric without stratifying by source class.

## 6. Ground truth

Ground truth must be independently established to the degree needed for each claimed metric:

- target presence/absence;
- target class/identity;
- target pose and orientation;
- position/range/velocity where used;
- environment/clutter state;
- occlusion state;
- acquisition timestamp.

Uncertain ground truth must be labeled and excluded from metrics that require exact truth unless the uncertainty is modeled explicitly.

## 7. Core test matrix

At minimum include:

1. empty/background condition;
2. calibration target(s);
3. target present at multiple ranges/angles;
4. target absent with confounding clutter;
5. known hard negatives that resemble target signatures;
6. orientation/polarization changes where relevant;
7. repeated collection on a different session/day;
8. perturbations in hardware/environment that are part of the intended operating envelope.

For low-observable or weak-target claims, preserve both raw complex data and background measurements; background subtraction cannot be the only retained artifact.

## 8. Metrics

Report detection and classification separately.

### Detection

- probability of detection versus operating point;
- false-alarm probability/rate;
- precision/recall where appropriate;
- ROC/PR curves when threshold selection matters;
- detection performance versus range/SNR/geometry/clutter.

### Localization / tracking

- position/range/angle/velocity error distributions;
- track continuity;
- missed/false track rates;
- latency.

### Classification / identification

- confusion matrix;
- per-class sensitivity/specificity or equivalent metrics;
- calibration of confidence scores;
- performance on untouched held-out measured data.

### RCS/scattering inference

- calibration uncertainty;
- background subtraction method;
- drift and dynamic-range effects;
- measurement geometry;
- near/far-field applicability.

## 9. Model and algorithm controls

- freeze algorithm version and training data digest;
- record every preprocessing transform;
- prevent train/test leakage by target instance, session, location, or time where leakage could inflate performance;
- preserve a simple physics/statistical baseline;
- compare new algorithm performance against that baseline;
- perform ablations to identify which inputs/features drive gains;
- report degraded-state behavior rather than only nominal best case.

## 10. Advancement gates

### Internal-test

Requires:

- calibrated measured dataset;
- raw-data SHA-256 digests;
- complete calibration/background records;
- independently established ground truth;
- held-out measured evaluation;
- uncertainty and failure-mode analysis;
- ECHO-grade provenance.

### Independent replication

Requires a separate sensor/session/facility or other defensible independent chain and a test set not used to tune the originating model.

## 11. Failure conditions

Do not advance claims if:

- measured gains disappear without background leakage or target-specific shortcuts;
- held-out field performance collapses relative to synthetic/lab data;
- calibration/drift uncertainty is of the same order as the claimed RCS/scattering effect;
- near-field measurements are represented as intrinsic far-field RCS without a valid transformation/model;
- ground-truth uncertainty dominates the claimed metric;
- false-alarm statistics are omitted.

Negative results must remain in the campaign record.

## 12. Claim-safe wording

> TIDELENS / Specular MIST uses established radar/electromagnetic sensing principles, but Worldshepherd-specific detection, classification, localization, and scattering-performance claims require calibrated measured datasets, ground truth, background and uncertainty control, held-out evaluation, and replication.

## 13. Public foundation references

- NIST TN 1522, *Phase Dependence in Radar Cross Section Measurements*: https://www.nist.gov/publications/phase-dependence-radar-cross-section-measurements
- NIST, *Radar Cross Section Calibration Errors and Uncertainties*: https://www.nist.gov/publications/radar-cross-section-calibration-errors-and-uncertainties
- NIST, *Effective Radar Cross Section in Close-Range Joint Communication and Sensing Applications*: https://www.nist.gov/publications/effective-radar-cross-section-close-range-joint-communication-and-sensing-applications
