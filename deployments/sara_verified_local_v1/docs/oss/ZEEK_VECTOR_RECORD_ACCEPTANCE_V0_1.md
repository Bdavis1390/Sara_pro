# Zeek `vector of record` acceptance oracle v0.1

Status: **RESEARCH / NO UPSTREAM PATCH CLAIMED**

This document defines the Worldshepherd acceptance boundary for the Zeek logging-framework research path associated with Zeek issue #5076. The issue remains open and asks for native JSON serialization of `vector of record` values as arrays of objects rather than escaped JSON strings. The upstream discussion also identifies an unresolved compatibility question for non-JSON writers such as TSV.

This oracle is intentionally stricter than "the JSON looks right." A candidate implementation must preserve type semantics, writer behavior, evidence integrity, and existing logging behavior before Worldshepherd will treat it as patch-ready.

## Required JSON behavior

For a logged `vector of record`, the JSON writer must emit a native JSON array whose elements are native JSON objects. It must not emit a quoted string containing escaped JSON. Field ordering may follow the writer's existing deterministic rules; semantic ordering of vector elements must be preserved.

The minimum regression matrix is:

| Case | Required result |
| --- | --- |
| one record | one-element JSON array of one object |
| multiple records | JSON array preserves vector element order |
| empty vector | empty JSON array when the field is present |
| optional field absent | field remains absent according to existing Zeek optional-field semantics |
| nested scalar fields | string/count/bool/time/address-like values retain their JSON types |
| nested optional fields | omitted/null behavior matches Zeek's existing record semantics; no synthetic value is invented |
| special characters | writer performs one correct JSON escaping pass, never double-encoding |

## Writer compatibility gate

Issue #5076's upstream discussion notes that JSON has a natural representation for arrays of records while TSV does not. Therefore a patch must not silently impose JSON semantics on every writer.

Before upstreaming, the implementation must demonstrate one of the following explicitly documented behaviors for writers that cannot represent the type natively: capability rejection with a clear diagnostic, an upstream-approved serialization rule, or another behavior accepted by Zeek maintainers. Silent conversion to a string is not an acceptable Worldshepherd pass condition because it recreates the schema mismatch the issue is trying to remove.

## Serialization and threading gate

The value must survive Zeek's logging pipeline without loss of record boundaries, field types, vector order, or optional-field state. Tests must cover the boundary between script-level values, logging serialization, writer dispatch, and final writer output. A JSON-only unit test that bypasses the logging pipeline is insufficient.

## Backward-regression gate

Existing scalar, record, vector-of-scalar, set, table, and ordinary log-writer behavior must remain unchanged unless an upstream design explicitly requires otherwise. Existing Zeek logging tests must pass. The new tests should be additive and narrowly scoped.

## OCSF interoperability gate

The motivating OCSF use case is an `array[record]` field such as DNS answers. Patch acceptance therefore requires a fixture where Zeek emits a native JSON array of answer objects that can be consumed as an array-of-records without an intermediate "parse this JSON string" transformation.

Worldshepherd's OCSF/Gemara corpus remains a separate governance/evidence oracle. A future Zeek-derived OCSF projection must preserve the Worldshepherd correlation grains and evidence binding; Zeek serialization success does not upgrade any OCSF/Gemara conformance claim.

## Claims boundary

Passing this oracle would establish only that the candidate implementation meets the stated internal technical acceptance criteria. It would not imply Zeek upstream acceptance, OCSF certification, Gemara certification, partner validation, government acceptance, or production readiness.

No upstream PR should be opened from Worldshepherd until the candidate change is built and tested against the relevant Zeek test suite and the writer compatibility decision is reconciled with upstream maintainer guidance.
