# WS ECHO Domain Evidence Bridge v0.1

**Status:** DRAFT / IMPLEMENTED IN SOFTWARE / VALIDATION PENDING / BLOCK MERGE  
**Date:** 2026-09-12  
**Claims boundary:** Evidence/provenance transport only. This bridge does not validate domain capability, authorize execution, or elevate maturity.

## Purpose

Worldshepherd already has an ECHO event-store, checkpoint, persistence, and evidence-artifact stack. New domain demonstrators must feed that existing custody path rather than inventing parallel audit ledgers.

This bounded bridge provides a domain-neutral contract from a source evidence object to the existing `AuditRecord` / `EchoEventStore` interface.

It is intentionally independent of the unmerged Army Decision Program and NP004 APNT feature branches. Those branches can later supply compatible envelopes after their own incorporation gates clear.

## Contract

`DomainEvidenceEnvelope` carries:

- `domain`;
- `source_kind`;
- stable `source_id`;
- upstream `source_sha256`;
- exact `claim_state`;
- exact source `claims_boundary`;
- bounded strict-JSON payload;
- optional parent provenance references;
- `human_signoff` state; and
- `execution_attempted`, which must always be `false` for this bridge.

The bridge adds only transport metadata:

- schema `WS-ECHO-DOMAIN-EVIDENCE-BRIDGE-V1`;
- bridge-level claims boundary;
- semantic bridge-payload SHA-256;
- stable `_outbox_event_id`; and
- `_delivery_semantics=AT_LEAST_ONCE`.

## Identity and conflict behavior

The stable ECHO event ID is derived only from:

`domain + source_kind + source_id`

It is **not** derived from mutable evidence content.

The complete semantic payload is separately hashed. This intentionally produces the following behavior through the existing ECHO event store:

1. same source identity + same semantic evidence -> `DEDUPLICATED`;
2. same source identity + changed semantic evidence -> `EchoEventConflict`;
3. new source identity -> new ECHO event.

This prevents a changed claim, recommendation, parent reference, or evidence payload from replacing prior content under the same source identity.

## Claims custody

The bridge preserves `claim_state` and `claims_boundary` exactly as supplied by the domain evidence object. It does not translate `SIMULATED_ONLY` into `PROVEN INTERNALLY`, and it does not infer customer, government, operational, compliance, or production validation.

The bridge-level boundary is:

> Evidence/provenance transport only; the bridge preserves the source claim boundary and does not validate domain capability, authorize execution, or elevate maturity.

## Execution boundary

An envelope with `execution_attempted=true` is rejected during model validation.

The bridge has no external-action adapter, actuator interface, procurement function, navigation command, hardware control path, or autonomous authorization path.

## Existing Worldshepherd components reused

The implementation reuses:

- `models.AuditRecord`;
- `echo_event_store.EchoEventStore`;
- `echo_event_store.semantic_sha256`;
- `evidence_artifacts.ArtifactEvidence`;
- `evidence_artifacts.artifact_from_bytes`; and
- existing JSON resource limits.

No second provenance database is introduced.

## Compatibility fixtures

The focused tests use domain-neutral fixture objects shaped like:

- an Army Decision Package; and
- an NP004 APNT replay result.

These are compatibility fixtures only. The bridge does not import the unmerged feature-branch modules and does not claim those modules have been incorporated into `main`.

## Verification targets

The focused regression suite requires:

- exact claim-boundary preservation;
- no execution-bearing envelopes;
- stable source-derived event identity;
- deterministic semantic payload hashes;
- ECHO `STORED -> DEDUPLICATED` behavior for identical replay;
- ECHO conflict on changed semantics under the same source identity;
- strict rejection of NaN/Infinity in nested payloads;
- unique parent provenance references; and
- compatibility with the existing `ArtifactEvidence` contract.

## Claims state

Before successful exact-head CI and review:

**IMPLEMENTED IN SOFTWARE / VALIDATION PENDING**

Maximum claim after successful focused CI and clean review:

**PROVEN INTERNALLY FOR THE V0.1 DOMAIN-EVIDENCE TRANSPORT/CUSTODY SCOPE**

This does not establish:

- domain engineering validity;
- Army or Navy acceptance;
- APNT performance;
- acquisition authority;
- operational execution;
- complete enterprise provenance;
- exactly-once delivery;
- external validation; or
- certification/compliance.

## Incorporation gate

Keep the PR draft and block merge until exact-head focused CI is green, review is clean, existing ECHO behavior remains compatible, and CRE1AWS explicitly authorizes incorporation.
