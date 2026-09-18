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

## 4. Important cross-project finding: canonical schema gap and corrective implementation

G4A exposed a concrete G1-to-G4 integration gap: directly converting CCSDS data into
the original state-vector-only `SdaObservation` would lose or invent semantics.

The missing semantics are:

1. **object identity** — OPM carries OBJECT_ID/OBJECT_NAME;
2. **center identity** — OPM carries CENTER_NAME;
3. **time-system semantics** — CCSDS supports multiple time systems and ordinal
   forms;
4. **covariance provenance** — a state estimate must not fabricate a 6x6 covariance;
5. **measurement class** — TDM RANGE is a measurement observable, not a Cartesian
   state vector.

The stacked branch now implements the corrective candidate in
`worldshepherd_sara/sda_canonical.py` as
`WS-SDA-CANONICAL-ENVELOPE-V2`.

The envelope:

- retains OBJECT_ID, OBJECT_NAME and CENTER_NAME for OPM state-vector evidence;
- preserves the original CCSDS time string and time-system label;
- normalizes only qualified calendar-form UTC, leaving other time values raw rather
  than guessing;
- permits covariance to remain absent instead of inventing one and requires an
  explicit provenance reference when covariance is supplied;
- represents RANGE as a typed measurement payload with participants, path, mode and
  units rather than coercing it into state-vector fields;
- binds the result to the interface-contract digest, raw-source digest, source
  standard and parser profile.

The original V1 record remains intact for its tested scope. V2 is a non-lossy
heterogeneous evidence envelope candidate and does not silently upgrade V1 data or
full CCSDS conformance.

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
2. add G4A parser and canonical-envelope tests to exact-head CI;
3. add OPM covariance-block parsing and provenance without inventing covariance;
4. add qualified CCSDS time-system handling beyond bounded calendar UTC;
5. expand TDM observables one type at a time with authoritative fixtures;
6. test XML only against the applicable CCSDS 505.0 navigation-message XML
   specification and SANA schemas;
7. seek independent/partner interoperability validation before any full-conformance
   claim.
