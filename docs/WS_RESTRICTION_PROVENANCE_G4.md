# WS-RESTRICTION-PROVENANCE G4 — AUTHORITY BINDING

Status: **IMPLEMENTED IN SOFTWARE ON STACKED BRANCH / PENDING G3 + INTERNAL VALIDATION**

## Objective

G4 binds restriction evidence to the Worldshepherd policy authority that is permitted to emit governed restriction events.

Before G4, `queue_restriction_event()` defaulted the audit actor to `PRIME_SENTINEL`, but callers could override that argument. G2 validated the restriction payload but did not require the outer audit actor to be PRIME. That left an avoidable provenance ambiguity.

G4 removes the override and introduces a versioned authority-bound evidence envelope.

## V2 provenance schema

New restriction captures use:

```text
schema    = WS-RESTRICTION-PROVENANCE-V2
authority = PRIME_SENTINEL
```

`authority` is not a caller parameter. `capture_restriction()` sets it from the system constant and includes it in the canonical identity document before `restriction_id` is calculated.

Consequently:

```text
authority -> canonical evidence identity -> restriction_id -> SARA outbox event ID
```

Changing authority semantics cannot silently reuse the same V2 restriction identity.

## Queue authority

`queue_restriction_event()` no longer exposes an `actor` keyword. It writes the SARA outbox actor from `evidence.authority`, which for V2 evidence is `PRIME_SENTINEL`.

A caller cannot request a restriction event with another audit actor through the governed queue helper.

## Observability enforcement

G4 hardens the G2 restriction projection:

- every restriction-shaped audit record, including historical V1, must have outer audit actor `PRIME_SENTINEL`;
- V2 additionally requires payload `authority=PRIME_SENTINEL`;
- V2 records missing or changing the payload authority are malformed;
- V1 records containing a V2-style authority field are malformed rather than silently treated as legacy.

The strict projection adds only structural fields:

- `provenance_schema`;
- `authority`;
- `authority_bound_in_payload`.

No additional content is exposed.

## V1 migration path

Historical G1/G2/G3 evidence may use:

```text
WS-RESTRICTION-PROVENANCE-V1
```

V1 did not contain an authority field inside the hashed payload. G4 preserves a bounded legacy-read path so historical records are not rewritten or invalidated solely by the schema migration.

A V1 record is accepted only when:

- its outer audit actor is `PRIME_SENTINEL`;
- it does not contain the V2-only `authority` field;
- all existing G2 structural validation succeeds.

G2/G4 observability reports:

```text
authority = PRIME_SENTINEL
authority_bound_in_payload = false
```

for such records. This makes the weaker legacy assurance visible instead of pretending V1 and V2 have the same binding strength.

## V2 downgrade resistance

A V2 record cannot be made to pass as V2 after removing or altering its authority field. It fails V2 validation.

A record explicitly relabeled as V1 must satisfy the V1 field contract, which rejects the V2-only authority field. Historical V1 acceptance therefore has a distinct schema and field shape rather than an optional-V2 authority switch.

This is structural downgrade resistance inside the SARA evidence contract. It is not a cryptographic signature scheme.

## Acceptance tests

The G4 regression suite verifies:

1. new captures use provenance schema V2;
2. `PRIME_SENTINEL` is inserted into the V2 semantic document;
3. the queue emits the same governed authority as the outer audit actor;
4. the queue helper has no supported actor override;
5. valid V2 records project with `authority_bound_in_payload=true`;
6. a non-PRIME outer audit actor is rejected;
7. a missing V2 payload authority is rejected;
8. an altered V2 payload authority is rejected;
9. authority tampering makes the bounded observability status unhealthy;
10. historical V1 records with PRIME outer actor remain readable;
11. historical V1 projections explicitly report `authority_bound_in_payload=false`;
12. V1 records cannot carry the V2-only authority field;
13. the required build executes G1, G2, G3, and G4 restriction suites together.

## Claims boundary

G4 is **application-level authority binding**, not independent signer authentication.

The literal `PRIME_SENTINEL` identifier is bound into V2 evidence identity and cross-checked against the SARA audit actor, but G4 does not prove that a hardware key, external signer, HSM, TPM, remote attestation system, or independent witness produced the event.

ECHO semantic hashing and stable event IDs provide replay/conflict evidence within the existing software architecture; they do not transform the authority string into a digital signature.

A later gate should add non-secret fingerprint-key epoch identifiers and, separately, independently verifiable signing/witness evidence where justified.

Until G3 is merged and G4 is reconciled onto that protected head, then passes exact-head required CI, broader Verified Local validation, and protected merge, classify G4 as **IMPLEMENTED IN SOFTWARE ON STACKED BRANCH / PENDING INTERNAL VALIDATION**.
