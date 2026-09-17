# WS-RESTRICTION-PROVENANCE G4 — AUTHORITY BINDING

Status: **IMPLEMENTED IN SOFTWARE ON CURRENT-MAIN BRANCH / PENDING INTERNAL VALIDATION**

## Objective

G4 binds restriction evidence to the Worldshepherd policy authority that is permitted to emit governed restriction events.

Before G4, `queue_restriction_event()` defaulted the audit actor to `PRIME_SENTINEL`, but callers could override that argument. G2 validated the restriction payload but did not require the outer audit actor to be PRIME. That left an avoidable provenance ambiguity.

G4 removes the override and introduces a versioned authority-bound evidence envelope.

## V2 provenance schema

At the G4 stage, new restriction captures used:

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
- V1 records containing a V2-style authority field are malformed rather than silently treated as legacy;
- for both V1 and V2, observability reconstructs the canonical safe identity document and requires the stored `restriction_id` to equal its SHA-256-derived identity.

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
- its `restriction_id` matches the recomputed V1 safe-envelope identity;
- all existing G2 structural validation succeeds.

G2/G4 observability reports:

```text
authority = PRIME_SENTINEL
authority_bound_in_payload = false
```

for such records. This makes the weaker legacy assurance visible instead of pretending V1 and V2 have the same binding strength.

## V2 downgrade resistance

A V2 record cannot be made to pass as V2 after removing or altering its authority field. It fails V2 validation.

If a V2 record is relabeled as V1 and the V2 authority field is removed, the V1 canonical identity changes. Reusing the original V2 `restriction_id` therefore fails semantic-identity verification.

A V1 record that retains the V2-only authority field also fails the V1 field contract.

This provides structural and semantic downgrade detection inside the SARA evidence contract. It is not a cryptographic signature scheme: a malicious party able to rewrite the full record could also calculate a new unkeyed restriction ID.

## Acceptance tests

The G4 regression suite verifies:

1. new captures use provenance schema V2;
2. `PRIME_SENTINEL` is inserted into the V2 semantic document;
3. valid V2 restriction IDs match recomputation from the safe identity document;
4. the queue emits the same governed authority as the outer audit actor;
5. the queue helper has no supported actor override;
6. valid V2 records project with `authority_bound_in_payload=true`;
7. a non-PRIME outer audit actor is rejected;
8. a missing V2 payload authority is rejected;
9. an altered V2 payload authority is rejected;
10. semantic V2 tampering without a matching restriction ID is rejected;
11. authority tampering makes the bounded observability status unhealthy;
12. historical V1 records with correctly derived V1 restriction IDs and PRIME outer actor remain readable;
13. historical V1 projections explicitly report `authority_bound_in_payload=false`;
14. stripping V2 authority, relabeling as V1, and retaining the V2 ID is rejected;
15. V1 records cannot carry the V2-only authority field;
16. the required build executes G1, G2, G3, and G4 restriction suites together.

## Claims boundary

G4 is **application-level authority binding**, not independent signer authentication.

The literal `PRIME_SENTINEL` identifier is bound into V2 evidence identity and cross-checked against the SARA audit actor, but G4 does not prove that a hardware key, external signer, HSM, TPM, remote attestation system, or independent witness produced the event.

The recomputed `restriction_id` detects inconsistent/tampered safe envelopes when the ID is not rewritten with them, but it is an unkeyed digest of already-safe evidence fields and is not an authenticity proof against a party able to rewrite the entire record.

ECHO semantic hashing and stable event IDs provide replay/conflict evidence within the existing software architecture; they do not transform the authority string or restriction ID into a digital signature.

A later gate should add non-secret fingerprint-key epoch identifiers and, separately, independently verifiable signing/witness evidence where justified.

G3 is merged and proven internally for its tested positive-schema invariants. G4 is merged on protected main and established the authority-binding baseline used by G5. G5 advances new captures to V3 by adding fingerprint-key epoch provenance while preserving V1/V2 legacy-read semantics. The separate G4 10x scorecard remains the retained evidence for the five declared G3-start residual attack classes.
