# Worldshepherd Wave 1 External Laboratory Execution Handoff

**Status:** execution-preparation package; not experimental evidence.  
**Source PVK candidate:** `9165fcae4b82277e050b76f606687f1179c31021`  
**Campaigns:** `SV-WSALTI-001-P1`, `SV-META-001-P1`  
**Machine-readable plan:** `fixtures/lab_execution_campaigns_wave1_v1.json`

## 1. Purpose

This handoff converts the existing Worldshepherd scientific-validation protocols into a form that an external laboratory can scope, quote, execute, and return with an evidence chain suitable for SARA/ECHO/PVK ingestion.

It does **not** disclose protected composition, proprietary process settings, or unvalidated performance claims. Those values are supplied only after the appropriate confidentiality/IP path is in place and before preregistration is frozen.

A quote, purchase order, laboratory report, or structural evidence-package acceptance does not by itself promote scientific maturity.

## 2. Common laboratory requirements

Before work starts, Worldshepherd and the laboratory should freeze:

- campaign and artifact IDs;
- sample/device IDs;
- exact methods and current revisions the laboratory intends to use;
- instrument identities and calibration state;
- sample/device custody process;
- measurement geometry/reference frame;
- requested native/raw-data formats;
- primary endpoints and exclusion/failure rules;
- uncertainty/measurement-limitation reporting;
- allowed method deviations and how they will be documented;
- delivery package structure and retention period.

The laboratory should identify any requested method that is technically inappropriate for the submitted article before execution rather than silently substituting a different method.

## 3. Evidence-return contract

The preferred evidence bundle is one directory/package per campaign containing:

1. a laboratory report or signed result summary;
2. raw/native instrument data;
3. calibration/reference-material records or identifiers;
4. instrument make/model/asset-or-serial identity and software/firmware version where available;
5. sample/device custody and preparation history;
6. method/procedure identity and deviations;
7. uncertainty statement or documented measurement limitations;
8. analysis scripts or analysis-version identity where laboratory policy permits;
9. processed/derived data separately from raw data;
10. a result-to-source-file map.

Worldshepherd will compute SHA-256 identities for received files and wrap the bundle using `ws-lab-evidence-package-1`. Laboratory evidence remains at its declared independence level and does not automatically become `independently_replicated` evidence.

## 4. Campaign A — WS-AlTi coupon validation

### Governing question

Can the frozen candidate material/process state produce an intended material state or zoning pattern that is measurable above uncertainty, repeatable across independently manufactured builds, and associated with a reproducible microstructure/property response relative to a declared baseline?

### Minimum manufacturing/sample structure

The source protocol calls for at least three independently manufactured builds for each baseline/candidate condition. When material volume permits, each build contributes three tensile specimens in the preregistered selected orientation plus chemistry/metallography and local-property material.

The machine-readable execution manifest defines:

- baseline builds `WSALTI-BASE-B01` through `B03`;
- candidate builds `WSALTI-CAND-B01` through `B03`;
- specimen roles `MET-CHEM`, `HARD-MAP`, and `TEN`;
- thirty minimum expected specimen IDs if all planned tensile material is available.

These IDs are custody/provenance identifiers, not statements that the samples already exist.

### Requested measurement classes

The lab should scope an appropriate subset/combination of:

- bulk chemistry where technically applicable;
- spatial/local chemistry mapping at preregistered locations;
- metallography/microstructure;
- microhardness/local property mapping;
- metallic-material tensile testing;
- defect/porosity characterization sufficient to bound defects as a confounder.

Method anchors from the governing protocol include ASTM E8/E8M-25, E384-22, E1251-25 where applicable, E3-26, and E407-23 where etching is used. The laboratory remains responsible for confirming the selected method/revision is applicable to the exact material condition, geometry, equipment, and contractual context.

### Minimum raw evidence requested

- native chemistry spectra/mapping files;
- microscopy acquisition data or highest-fidelity native exports available;
- complete stress-strain data rather than summary-only strength values;
- indent-level hardness data with position/load/dwell and rejected-indents rationale;
- measurement-coordinate/extraction map;
- instrument/calibration/reference-material identity;
- processing/analysis version;
- method deviations and uncertainty/limitations.

### Advancement rule

No WS-AlTi record advances toward `INTERNAL_TEST` unless the candidate/baseline distinction survives combined uncertainty, repeats across independent builds, the preregistered endpoint is retained whether positive or null, relevant defect/sampling effects are bounded, and the raw evidence chain is recoverable.

The campaign does not establish aerospace qualification, fatigue life, corrosion resistance, or general superiority.

## 5. Campaign B — adaptive metasurface validation

### Governing question

Do frozen command states produce repeatable electromagnetic phase/amplitude response and corresponding bounded array-level field redistribution consistent with the preregistered electromagnetic model within uncertainty?

### Required preregistration before fabrication/test

Freeze one operating band, polarization/incidence set, geometry revision, material stack, tuning mechanism, command-state set, predicted per-state response, array/aperture geometry, primary beam/scattering endpoint, thermal/power envelope, and pass/fail rules.

The first campaign deliberately does **not** treat a large optical/RF research span as one validation claim.

### Planned devices

- `META-REF-01` — reference coupon;
- `META-UC-01` — unit-cell or small periodic coupon;
- `META-ACT-01`, `META-ACT-02`, `META-ACT-03` — independent active coupon/small-array replicas.

The exact fabrication architecture and command values remain to be frozen before test.

### Calibrated measurement request

For RF/microwave work, request calibrated complex `S11` and applicable `S21` across the frozen band, including calibration method/reference plane, VNA identity, source power, IF bandwidth/averaging/sweep settings, cable/fixture configuration, temperature, and native Touchstone or equivalent complex raw data.

For each state/device, the protocol requires reference measurement, target-state measurement, return-to-reference, at least three complete state cycles, temperature logging, full power-cycle repeat, and fixture reversal/rotation where practical.

The array-level campaign requires at least a reference state and a preregistered steering/null state plus raw angular pattern/scattering data. IEEE 149-2021 principles are an anchor where antenna/radiation-pattern measurement is applicable; the laboratory must determine near-/far-field suitability for the actual aperture and frequency.

### Advancement rule

No metasurface record advances toward `INTERNAL_TEST` unless commanded phase/amplitude changes exceed measurement uncertainty, the preregistered state relation is retained, the effect repeats, the frozen model has a reported simulation-to-test error, the bounded beam/null endpoint is observed in the preregistered region where applicable, and thermal/fixture/cable/background explanations are insufficient.

A reduction at one angle is not evidence of “stealth” or “cloaking.” Those terms remain blocked absent later application-specific scattering validation across the relevant frequency, angle, polarization, power, and environment.

## 6. Quote/scoping questions for any candidate facility

Ask the facility to answer, in writing where practical:

- Which requested measurement classes are within current capability?
- Which methods/revisions would they actually use?
- What sample dimensions/quantity/preparation are required?
- Can they retain native/raw data and provide copies to the client?
- What calibration/traceability records accompany the work?
- Can they provide measurement uncertainty or a documented limitations statement?
- How are samples/devices labeled and custody tracked?
- What is the expected turnaround and cost structure?
- What IP/confidentiality or user agreement is required before protected details are shared?
- Are any proposed steps research-service measurements rather than accredited/standards-conforming tests, and how will that distinction be stated?

## 7. Intake into SARA/ECHO

Upon return, do not manually summarize the report and discard the raw files. Instead:

1. preserve the original package read-only;
2. compute file SHA-256 values;
3. populate `ws-lab-evidence-package-1` with sample/device, instrument, calibration, method, custody, file, and result references;
4. submit the package to the SARA lab-package structural validator;
5. resolve any structural blockers;
6. create/update the corresponding PVK scientific record only after human scientific review;
7. retain negative/null results;
8. require separate replication evidence before changing the independence/replication state.

## 8. Current safe external wording

**WS-AlTi:**

> WS-AlTi is an IP-stage additive-manufacturing materials platform under coupon-level validation. Relevant strengthening and additive-manufacturing mechanisms are supported by external literature, but Worldshepherd-specific composition, zoning, and mechanical-property performance remain under laboratory validation.

**Adaptive metasurface:**

> Worldshepherd is developing a reconfigurable metasurface architecture based on established electromagnetic and tunable-material principles. Worldshepherd-specific phase/amplitude, beam-steering, nulling, or scattering performance remains under calibrated coupon/array validation.
