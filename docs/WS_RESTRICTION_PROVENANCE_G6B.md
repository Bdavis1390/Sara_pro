# WS-RESTRICTION-PROVENANCE G6B — PRIME-SIGNED V4 EVIDENCE

Status: **IMPLEMENTED IN SOFTWARE ON CURRENT-MAIN CANDIDATE / PENDING EXACT-HEAD QUALIFICATION**

## Relationship to G6A

Protected main already contains G6A: signed ECHO witness verification.

G6A proves exact semantic restriction-event inclusion in an Ed25519-signed ECHO checkpoint under a separately trusted checkpoint-key fingerprint.

G6B is complementary. It requires an externally produced PRIME Ed25519 signature before a new restriction event may enter SARA and re-verifies that PRIME signature from persisted evidence during observability.

The two controls address different trust boundaries and are required together by the combined candidate workflow.

## G6B enforcement

- PRIME private signing material is not generated or stored by this restriction path.
- The existing PRIME public-key verifier is reused for detached signatures.
- The external signer signs the complete already-safe V3 semantic restriction document plus expected signing key ID under a domain-separated protocol.
- SARA constructs V4 only after successful signature verification.
- The unsigned new-event queue helper fails closed.
- New events use signed-only V4 queueing.
- OVERWATCH re-verifies persisted V4 signatures against the current configured public-key and revocation state.
- Unknown, revoked, malformed, or tampered signatures are not counted as currently verified evidence.
- Administrator projections omit the signature value and arbitrary safe-summary/metadata content.

## Combined 10x security metrics

### Application/provenance path metric

G3-start cumulative residual classes now include:

1. caller-selected audit actor;
2. authority absent from semantic identity;
3. outer actor mismatch accepted;
4. semantic mutation accepted with stale identity;
5. schema downgrade accepted with stale stronger identity;
6. fingerprint-key epoch ambiguity;
7. unsigned new restriction emission.

Baseline: **7**.

10x threshold: **<=0.7**.

Integral practical pass: **0/7 open**.

### Signed ECHO witness authenticity metric

G6A separately freezes four authenticity residual classes.

Baseline: **4**.

10x threshold: **<=0.4**.

Integral practical pass: **0/4 open**.

Both gates must pass; neither gate can compensate for failure in the other.

## Claims boundary

These are software assurance metrics, not universal security multipliers.

The combined G6 candidate does not prove:

- HSM/TPM/KMS private-key custody;
- hardware-enforced non-exportability;
- signer non-compromise;
- independent third-party witnessing;
- immutable external WORM retention;
- FIPS certification;
- secure transient-memory erasure;
- real-world incident probability reduction by a factor of ten.

Those require separate evidence.

Until exact-head required CI, the full Verified Local deployment/recovery/evidence gate, and protected merge succeed on the combined candidate, classify G6B as **IMPLEMENTED IN SOFTWARE / PENDING INTERNAL VALIDATION**.
