# Sentinel Custody Isolation Design

Status: DESIGN / NOT IMPLEMENTED
Claims state: INTERNAL_SYNTHETIC_SOFTWARE_EVIDENCE only
Parent blocker: issue #124
Parent remediation lineage: PR #122 / PR #97

## 1. Objective

Replace same-interpreter authoritative custody with a separately isolated authority component so caller code cannot directly read or mutate authoritative package custody, one-shot registration state, resolution provenance, or signing material.

The client library remains responsible for local data-model convenience, request construction, detached audit rendering, and fail-closed handling. It must not be the authoritative security boundary.

## 2. Threat boundary

The isolation boundary is intended to withstand arbitrary Python-level introspection and mutation inside the client interpreter, including access to module globals, function `__globals__`, closures, defaults, import hooks, `sys.modules`, monkeypatching, direct source loaders, and caller-owned object mutation.

This design does not claim protection against an adversary with equivalent privilege over the isolated authority process, its OS account, host kernel, HSM/keyring administration, or deployment/runtime configuration. Those are separate controls and require their own validation.

## 3. Required architecture

### Client

The `worldshepherd_sara` package becomes a client/validator. It may hold:
- immutable request payloads;
- detached snapshots returned by the authority service;
- non-authoritative local convenience objects;
- endpoint/configuration identifiers that contain no signing secret.

It must not hold:
- authoritative custody dictionaries;
- one-shot registration authority;
- mutable authoritative evidence or issue ledgers;
- resolution signing keys;
- generic signing functions;
- service-side authorization secrets.

### Authority service

A separately isolated service/process owns:
- package identity registration and one-shot lifecycle state;
- authoritative evidence ledger and evidence-chain state;
- open/resolved issue custody;
- package closed/open lifecycle state;
- resolution provenance chain;
- signing keys or handles to OS/HSM-backed signing keys;
- authorization verification required for privileged transitions.

The service exposes only narrow transition operations. Proposed minimum API:
- `register_package`
- `ingest_evidence`
- `resolve_issue`
- `close_package`
- `get_snapshot`
- `health`

No generic `sign(payload)` operation is permitted.

## 4. Service invariants

1. Package registration is one-shot for a package instance/authority identity unless an explicit governed replacement workflow is used.
2. The service, not the client, determines whether a package is closed.
3. Evidence ingestion is rejected after authoritative closure.
4. Resolution creation requires service-side authorization verification and an open matching issue.
5. Resolution records are append-only and integrity-bound.
6. Closing validates required evidence, authoritative evidence integrity, unresolved issues, and resolution-chain integrity from service-owned state.
7. Returned snapshots are detached/read-only representations; mutating them has no effect on service state.
8. Secrets never cross the service boundary.
9. Service requests are authenticated and replay-resistant at the transport/session layer.
10. Every accepted/rejected transition produces an auditable event with deterministic identifiers suitable for ECHO SENTINEL LINK provenance.

## 5. Legacy-source disposition

`infrastructure_assurance_legacy.py` must not remain executable vulnerable source on the production runtime import path. Historical preservation options:
- move the exact source to a documentation/test fixture directory and store it as non-importable text/data;
- or fully harden the implementation so loading it directly cannot recreate vulnerable state transitions.

The preferred path is non-executable historical preservation plus a clean client implementation.

## 6. Client API rules

- Remove or deprecate `_custody(state)` as an authoritative object-returning API.
- Replace it with detached snapshot access where compatibility requires observability.
- Local `PackageState` fields are mirrors only and must never be treated as authoritative for privileged transition decisions.
- Client functions must fail closed if the authority service is unavailable, unauthenticated, returns an invalid response, or detects version/schema mismatch.
- No client fallback may silently revert to same-process custody.

## 7. Isolation candidates

Preferred evaluation order:

1. Local Unix-domain-socket service under a distinct service account, with strict filesystem/socket ACLs and service-owned key material.
2. Same service with OS keyring/TPM/HSM-backed signing for stronger key custody.
3. Remote mutually authenticated service for distributed deployments where local isolation is insufficient.

A plain child process that shares caller-owned authentication material or exposes a generic signer is not sufficient by itself.

## 8. Authorization model

Privileged transitions must be authorized using material or identity that the arbitrary client interpreter cannot forge merely by reading Python objects. Candidate mechanisms include:
- mutually authenticated service identity plus externally provisioned operator/service credentials;
- OS-mediated peer identity combined with a separate authorization policy engine;
- hardware/OS-backed signing identities;
- PRIME SENTINEL as the policy-decision boundary, with the custody service independently validating signed authorization artifacts.

The exact mechanism remains REQUIRES IMPLEMENTATION VALIDATION. No current clearance, government authorization, or certification is implied.

## 9. Adversarial acceptance tests

The implementation is not ready for blocker closure until exact-head tests demonstrate at least:

1. Direct source-loader execution cannot restore a vulnerable runtime API.
2. Alternate-name loading of historical source cannot create an authoritative runtime implementation.
3. Deleting/rebinding all client registries cannot reset service registration.
4. Mutating any client snapshot cannot reopen a package or modify authoritative evidence/issues.
5. Introspecting client module globals/closures/defaults cannot recover signing material.
6. The client cannot obtain a generic signing oracle.
7. Forged resolution provenance is rejected without a valid service-authorized transition.
8. Post-closure ingest remains rejected even after arbitrary client-side lifecycle mutation.
9. Service restart/recovery preserves or deliberately fail-closes authoritative lifecycle according to documented persistence policy.
10. Loss of authority-service connectivity fails closed and cannot fall back to legacy local custody.
11. Replayed privileged requests are rejected or idempotently bound to their original transition identity.
12. Version/schema mismatch is rejected.

## 10. Evidence gates

G0 — architecture and threat model accepted internally.
G1 — isolated authority prototype with no secrets or authoritative mutable custody in the client interpreter.
G2 — adversarial regression suite passes on exact head.
G3 — restart/recovery, transport authentication, replay resistance, and audit provenance pass.
G4 — fresh independent code/security review finds no unresolved P1 at the stated threat boundary.
G5 — separate CRE1AWS incorporation authorization.

Passing these gates remains software evidence only. External Sentinel fitness, USACE/Air Force acceptance, CMMC/NIST conformity, clearance, supplier status, certification, deployment authority, and operational effectiveness require separate evidence and authorization.

## 11. Current disposition

Issue #124 remains OPEN.
PR #122 remains DRAFT / BLOCK MERGE.
PR #97 remains authoritative blocked integration lineage.
This design does not authorize merge, deployment, government outreach, supplier submission, or external operational-readiness claims.
