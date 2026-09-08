# WS-AlTi Coupon Scientific-Validation Protocol v1

**Protocol ID:** `SV-WSALTI-001-P1`  
**Purpose:** establish whether a Worldshepherd candidate deposition/material state produces a repeatable, spatially resolved composition–microstructure–property relationship.  
**Current claim boundary:** `REQUIRES_LAB_VALIDATION`. This protocol is for internal scientific validation, not aerospace qualification or certification.

## 1. Governing question

Can the candidate WS-AlTi / M1-MSZ-Prime process produce an intended material state or zoning pattern that is measurable above uncertainty, repeatable across independently manufactured builds, and associated with reproducible microstructural/property changes relative to a declared baseline?

### H0 — null
Any observed spatial or between-condition difference is explained by ordinary build variability, measurement uncertainty, sampling location, porosity/defects, or uncontrolled process variation.

### H1 — candidate mechanism
A preregistered change in candidate material/process state produces a repeatable composition and/or microstructure change and an associated property response at the intended location.

No claim of a superior alloy, aerospace suitability, fatigue life, corrosion resistance, or programmable zoning is allowed from a single build or a single measurement modality.

## 2. Preregistration freeze

Before manufacturing, create a signed/hash-bound campaign record containing:

- candidate material/process IDs without exposing protected formulation details in public records;
- declared baseline/control material and process;
- feedstock/powder/wire lot IDs and certificates where available;
- build machine, firmware/software, calibration/maintenance state;
- geometry revision and specimen extraction map;
- intended zoning locations or homogeneous control locations;
- primary endpoint(s), secondary endpoint(s), exclusion rules, and failure conditions;
- statistical analysis plan;
- planned sample count and allowed stopping rule.

Changing any frozen item creates a new protocol revision rather than overwriting the original.

## 3. Pilot specimen matrix

For the first internal-validation campaign, target at least:

- **3 independently manufactured builds** per baseline/candidate condition;
- **3 tensile specimens per build per selected orientation** when material volume permits;
- metallographic/composition sections from each independent build at the same preregistered spatial locations;
- a hardness map with enough valid indents per zone to report mean, standard deviation, and spatial gradient without relying on a single indent.

These are internal pilot minima, not qualification sample counts. A qualified statistician/materials laboratory may require larger counts based on measured variance and desired power.

## 4. Measurement chain

### 4.1 Bulk and local chemistry

Use a calibrated method appropriate to the specimen and target elements. Where applicable, ASTM **E1251-25** provides a current method for aluminum/alloy analysis by spark atomic-emission spectrometry. For spatial zoning, add a calibrated local method such as SEM-EDS/WDS, micro-XRF, EPMA, or another validated mapping technique appropriate to the spatial scale.

Record:

- calibration/reference material IDs;
- detection/quantification limits;
- measurement locations and coordinate frame;
- raw spectra/data files;
- software and analysis version;
- uncertainty and any matrix-effect corrections.

### 4.2 Metallography and microstructure

Prepare specimens using the current laboratory-controlled procedure; ASTM **E3-26** is the current ASTM guide for metallographic specimen preparation. If chemical etching is used, control it under an applicable procedure such as ASTM **E407-23** and preserve safety documentation.

At minimum characterize:

- porosity/voids and lack-of-fusion or cracking indications;
- grain morphology and build-direction effects;
- second phases/precipitates at the resolution supported by the instrument;
- intended zone boundaries;
- unexpected segregation or reaction products.

Use optical microscopy/SEM as appropriate. Add XRD, EBSD, TEM, CT, or other methods only where they answer a preregistered question; their absence must not be hidden by an unsupported phase claim.

### 4.3 Microhardness / local property mapping

Where local hardness gradients are an endpoint, use a calibrated method consistent with ASTM **E384-22** or a later applicable revision. Avoid interpreting a single indent as a bulk property. Report load, dwell, indent location, spacing, rejected indents, mean, standard deviation, and map coordinates.

### 4.4 Tensile behavior

Use an applicable current metallic-material tension method such as ASTM **E8/E8M-25**, with specimen geometry, orientation, strain measurement, test rate, temperature, and fracture location recorded. Report at minimum:

- yield strength where valid;
- ultimate tensile strength;
- elongation;
- reduction of area where applicable;
- complete stress–strain data rather than only summary values.

The protocol does not prescribe a target strength until the candidate baseline and intended use case are frozen.

## 5. Required provenance

Each specimen receives a unique immutable ID linking:

`feedstock lot -> build -> coordinates/orientation -> extraction -> preparation -> instrument -> calibration -> raw data -> analysis -> result`

ECHO/PVK evidence must retain:

- raw-data SHA-256 digests;
- instrument and calibration IDs;
- environment where material to the measurement;
- operator/laboratory;
- analysis script/version;
- excluded/rejected results with reasons;
- photographs or microscopy acquisition metadata where applicable.

## 6. Primary scientific success criteria

The campaign may advance from `CONCEPT/LITERATURE_SUPPORTED` toward `INTERNAL_TEST` only when all of the following are demonstrated:

1. the intended candidate state is analytically distinguishable from the declared baseline or neighboring zone **above combined measurement uncertainty**;
2. the effect repeats across at least three independent builds, not merely repeated readings of one coupon;
3. a preregistered property/microstructure endpoint changes in the predicted direction or the null result is explicitly recorded;
4. defect level and sampling/orientation effects are quantified sufficiently to prevent them from masquerading as a candidate-material effect;
5. raw data, calibrations, exclusions, and analysis are recoverable from the evidence package;
6. the result survives a blinded/re-coded reanalysis or independent internal reviewer where practical.

Failure of any criterion is a useful negative result and does not permit maturity elevation.

## 7. Simulation-to-test correlation

If a CALPHAD, thermal, solidification, phase-field, finite-element, or surrogate model is used, freeze its inputs and predicted observables before comparing with the experiment. Report:

- predicted vs measured chemistry/phase/microstructure/property observable;
- uncertainty in both model and measurement;
- residual/error distribution;
- which parameters were fitted after seeing the data;
- whether a holdout build was used.

A calibrated model is not independent validation if the same data used for fitting are then used as the only validation evidence.

## 8. Advancement ladder

- **P0:** protocol and baseline frozen.
- **P1:** one manufacturing campaign completed; evidence intact.
- **P2:** repeatability across independent builds established.
- **P3:** simulation-to-test correlation established on holdout material.
- **P4:** independent laboratory reproduces key chemistry/microstructure/property result.
- **P5:** application-specific fatigue/corrosion/environmental/structural qualification campaign begins.

Only P4 or stronger may support wording such as “independently reproduced.” Aerospace qualification/certification is outside this protocol.

## 9. External-safe statement until P2 closes

> WS-AlTi is an IP-stage additive-manufacturing materials platform under coupon-level validation. Relevant strengthening and additive-manufacturing mechanisms are supported by external literature, but Worldshepherd-specific composition, zoning, and mechanical-property performance remain under laboratory validation.

## 10. Standards/evidence anchors

- ASTM E8/E8M-25 — tension testing of metallic materials.
- ASTM E384-22 — microindentation hardness.
- ASTM E1251-25 — aluminum/alloy spark atomic-emission analysis where applicable.
- ASTM E3-26 — metallographic specimen preparation.
- ASTM E407-23 — microetching metals/alloys where applicable.

The laboratory must verify that the selected edition and method are applicable to the exact specimen, equipment, material condition, and contractual context before claiming conformity.
