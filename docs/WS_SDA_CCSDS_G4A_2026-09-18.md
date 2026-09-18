# WS-SDA G4A — CCSDS Authoritative Interoperability Baseline

Status: **IMPLEMENTED IN SOFTWARE ON STACKED BRANCH — CI NOT YET EXECUTED**
Date: 2026-09-18
Branch: `feature/ws-sda-ccsds-g4a-20260918`
Parent gate: WS-SDA G1/G2 PR #447

## 1. Authoritative sources

G4A is pinned to the active CCSDS navigation-message standards, not third-party
examples:

- **CCSDS 502.0-B-3 — Orbit Data Messages, Issue 3, May 2023**
  - official publication: https://ccsds.org/Pubs/502x0b3e1.pdf
  - active-publication record: https://ccsds.org/publications/allpubs/entry/3073/
- **CCSDS 503.0-B-2 — Tracking Data Message, Issue 2, June 2020**
  - official publication with current corrigendum: https://ccsds.org/Pubs/503x0b2c1.pdf
  - active-publication record: https://ccsds.org/publications/allpubs/entry/3061/

The ODM standard identifies OPM/OMM/OEM/OCM version 3.0 as the current Blue Book
message versions. The TDM standard uses `CCSDS_TDM_VERS = 2.0`.

## 2. Implemented G4A profiles

`worldshepherd_sara/sda_ccsds.py` provides two deliberately bounded KVN profiles:

### OPM v3 Cartesian state-vector extraction

`WS-CCSDS-OPM-V3-KVN-SUBSET-V1` requires and preserves:

- `CCSDS_OPM_VERS = 3.0`;
- creation date and originator;
- optional message ID;
- object name and international/object ID;
- center name;
- reference frame;
- time system;
- epoch;
- X/Y/Z explicitly in km;
- X_DOT/Y_DOT/Z_DOT explicitly in km/s.

Unmodeled assignment keywords are retained as `extra_keywords`; they are not
silently interpreted.

### TDM v2 RANGE extraction

`WS-CCSDS-TDM-V2-KVN-RANGE-SUBSET-V1` requires:

- `CCSDS_TDM_VERS = 2.0`;
- exactly one metadata block and one data block;
- time system;
- participants 1 and 2;
- mode;
- path;
- explicit `RANGE_UNITS` in km, s, or RU;
- one or more RANGE observations.

The Worldshepherd profile deliberately requires explicit RANGE_UNITS even though
the CCSDS TDM standard defines km as the default if omitted. This removes unit
ambiguity at the Worldshepherd ingestion boundary without claiming that a
standards-valid defaulted message is invalid CCSDS.

## 3. Negative behavior

The executable test plan rejects:

- legacy/wrong message versions;
- duplicate required fields;
- missing or wrong state-vector units;
- non-finite numeric values;
- malformed or reordered TDM block markers;
- unsupported TDM observables in the RANGE-only profile;
- invalid RANGE_UNITS;
- ordinal CCSDS time strings at the bounded UTC conversion boundary.

The final item is intentional. CCSDS supports more time representations and time
systems than Python calendar-form UTC. G4A refuses to silently reinterpret those
values until a dedicated time-scale adapter is qualified.

## 4. Important cross-project finding: canonical schema gap

G4A exposed a concrete G1-to-G4 integration gap that must be closed before a CCSDS
OPM is converted into the canonical `SdaObservation`:

1. **object identity** — OPM carries OBJECT_ID/OBJECT_NAME, while the current
   canonical observation identifies the observation and source but does not yet
   have a first-class target/object identity field;
2. **center identity** — OPM carries CENTER_NAME; dropping it would make a state
   vector semantically incomplete;
3. **time-system semantics** — CCSDS supports multiple time systems and ordinal
   forms; converting every epoch to UTC by assumption would be wrong;
4. **covariance provenance** — the canonical SDA record requires a 6x6 covariance,
   while a valid OPM may require separate parsing of its covariance block or an
   explicit qualified upstream covariance source;
5. **measurement class** — TDM RANGE is a measurement observable, not a Cartesian
   state vector, so it must not be coerced into the current state-vector record.

Therefore G4A **does not** add a lossy `OPM -> SdaObservation` shortcut. The correct
next schema step is an SDA canonical envelope that retains object/center identity
and supports typed measurement payloads or a qualified transformation into a state
estimate.

This is a strengthening of the architecture, not a parser limitation to hide.

## 5. Claims boundary

A passing G4A test suite will establish:

- authoritative-version-pinned KVN parsing for the two declared Worldshepherd
  profiles;
- deterministic profile rendering/round-trip semantics;
- fail-closed behavior for the declared negative cases.

It will **not** establish:

- full CCSDS 502.0-B-3 or 503.0-B-2 conformance;
- XML Navigation Data Message conformance;
- OMM/OEM/OCM support;
- every OPM optional field or covariance representation;
- every TDM observable or multi-segment message;
- SANA-registry completeness;
- partner, vendor, Space Force, SDA, NASA, or government acceptance.

## 6. Next gates

1. pass the G1/G2 parent gate and protected merge;
2. add G4A tests to exact-head CI;
3. introduce the canonical SDA object/center/measurement envelope without breaking
   G1 provenance and identity invariants;
4. add OPM covariance parsing and provenance;
5. add qualified CCSDS time-system handling;
6. expand TDM observables one type at a time with authoritative fixtures;
7. test XML only against the applicable CCSDS 505.0 navigation-message XML
   specification and SANA schemas;
8. seek independent/partner interoperability validation before any full-conformance
   claim.
