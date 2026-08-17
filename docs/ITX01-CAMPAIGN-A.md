# ITX01-CAMPAIGN-A — Integrated Evidence Campaign

Status: DRAFT BASELINE

## Objective

Exercise the smallest physical system slice that touches Worldshepherd metrology, propulsion, FIELD-SKIN sensing, power isolation, environmental sensing, solver correlation, Glob/DOE ordering, and SARA evidence provenance.

## Test article

- Reference structure: conventional rigid carrier first.
- Propulsion article: validated-force EHD/EAD reference module.
- FIELD-SKIN role: FS-1 sensing first. FS-2/FS-3 are separate gates.
- Materials: WS-AlTi coupons may be mounted as non-critical specimens until measured properties justify structural or active roles.
- Metrology: WS-UPB force-balance family with calibration records and an explicit uncertainty budget.

## Required measurements

Minimum synchronized channels:

- force/moment channel(s) required by the selected balance;
- propulsion voltage and current;
- logic/sensor-domain power;
- temperature at propulsion article and selected structure locations;
- ambient pressure and humidity;
- local magnetic field;
- vibration/acceleration;
- FIELD-SKIN sensor outputs used by the campaign.

Each sensor must carry identity, units, sample rate, calibration identity, location/orientation, and uncertainty provenance.

## Test sequence

1. configuration freeze and digest generation;
2. pre-calibration;
3. zero and drift characterization;
4. unpowered baseline;
5. powered null article;
6. reference EHD/EAD active run;
7. polarity/orientation reversal when physically meaningful;
8. FIELD-SKIN FS-1 concurrent sensing run;
9. deterministic PA/PB/PC ordering blocks;
10. bounded sensor/actuator fault injection;
11. one withheld solver prediction;
12. post-calibration;
13. SARA experiment/claim ingestion;
14. discrepancy classification and campaign review.

## Momentum/force accounting

A reported force shall be decomposed, where relevant, into intended mechanism, aerodynamic/EHD, electrostatic, Lorentz, thermal, vibration/mechanical, cable, and residual terms. A residual is not automatically a new-physics claim.

## Energy accounting

Record source energy and measured allocations to propulsion, RF/field actuation where used, computation, thermal load, storage/change in stored energy, and known loss channels. Unclosed energy is a measurement/model discrepancy until demonstrated otherwise.

## Glob/DOE use

PA, PB, and PC may determine admissible test ordering and withheld-condition selection. The same physical condition should be reproducible independent of the ordering trajectory. Order-sensitive effects trigger investigation of hysteresis, drift, charging history, aging, thermal history, or operator/system bias.

## Acceptance outcomes

Use WS-R0 through WS-R4 result classes. Conventional model agreement within declared uncertainty is a successful WS-R2 outcome. WS-R3/WS-R4 are reserved for significant unexplained discrepancies and independent reproduction, respectively.

## Exit criteria

Campaign A exits when at least one physical propulsion run has traceable calibration, raw-data digest, uncertainty, synchronized power/environment channels, a matching solver prediction, a powered-null comparison, SARA ingestion, and a reproducible evidence export.

## Claim boundary

This document defines the campaign. It does not assert that EHD performance, FIELD-SKIN propulsion contribution, WS-AlTi properties, or anomalous propulsion have been physically validated.
