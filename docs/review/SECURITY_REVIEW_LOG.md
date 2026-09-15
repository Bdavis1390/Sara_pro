# Pre-outreach hostile review log

Date: 2026-09-14

Scope: `deployments/sara_verified_local_v1` and the external-review packet prepared for independent systems criticism.

This is an engineering review log, not a certification report.

## Findings resolved in this review

### WS-REV-001 — recorded authorization could outlive replacement key material behind the same key ID

**Severity:** security-significant fail-closed ambiguity

**Observed behavior:** a PRIME SENTINEL authorization record persisted the SHA-256 fingerprint of the public key that originally verified the assertion. Later usability checks confirmed that the recorded key ID was still configured and not revoked, but did not compare the recorded fingerprint with the currently configured public key bytes.

If an operator incorrectly replaced public-key material while reusing the same `key_id`, an authorization verified under the previous key could remain usable until expiration because the identity continuity check stopped at the key ID.

**Resolution:**

- added `PrimeSentinelVerifier.key_fingerprint_sha256()`;
- recorded-authorization usability now compares the stored public-key fingerprint with the currently configured key fingerprint using a constant-time comparison;
- fingerprint mismatch fails closed;
- added a regression test that replaces the public key behind `PS-K1` and requires rejection;
- documented that key IDs identify specific key material and should not be reused during rotation.

**Related observation:** the PRIME SENTINEL signing service already binds each signing key ID to its public-key fingerprint in the issuance SQLite ledger and refuses startup/configuration when the same ID is associated with different key material. The verifier-side change aligns SARA with that existing signer invariant.

Status: **FIXED ON REVIEW BRANCH; CI VERIFICATION REQUIRED.**

## Boundaries made explicit in this review

### WS-REV-002 — local SARA JSON persistence is single-process transactional, not distributed storage

`DurableStore` protects registry transactions with an in-process re-entrant lock and atomic file replacement. That is sufficient for the supported single SARA service process, but it is not a cross-process or distributed locking protocol.

The security policy now states the supported topology explicitly: **one SARA writer process per writable SARA data volume**. Scaling multiple SARA writer processes against the same `SARA_DATA_DIR` is outside the qualified boundary and requires a storage backend with cross-process transaction semantics plus requalification.

Status: **DOCUMENTED SUPPORTED-TOPOLOGY LIMIT.**

### WS-REV-003 — request-size enforcement does not depend only on Content-Length

The ASGI request-size middleware rejects a declared body larger than the configured limit, but also wraps the ASGI `receive` function and counts actual body bytes. This means a caller cannot bypass the application limit merely by omitting or understating `Content-Length` when the downstream endpoint consumes the body.

Residual reviewer target: exercise chunked/streamed bodies and any future streaming endpoints so response-start ordering cannot create an ambiguous late rejection.

Status: **CONTROL PRESENT; NEGATIVE TESTING REMAINS VALUABLE.**

### WS-REV-004 — signer idempotency and key identity are durably ledgered

The PRIME SENTINEL issuance path uses a SQLite ledger with `BEGIN IMMEDIATE`, request-ID binding, unique authorization IDs/nonces, durable PREPARED/SIGNED state, and a hash-linked issuance-event chain. The signer also binds a `key_id` to a specific public-key fingerprint in metadata.

This improves issuance durability and retry semantics but does not make the database externally immutable. A sufficiently privileged host actor remains outside the assurance boundary.

Status: **IMPLEMENTED; NOT EXTERNAL ATTESTATION.**

## Known limits intentionally not hidden

- local audit records are application-appended and host-writable;
- ECHO-style local content addressing is not WORM storage or a legal chain-of-custody system;
- local SARA storage is supported as a single-writer topology;
- production HSM/KMS custody is not established;
- no CMMC, FedRAMP, RMF/ATO, FIPS, government interoperability, or partner validation is implied by CI;
- repository-wide open-source licensing has not been selected;
- broader physical/research claims in the repository are not upgraded by the existence of working SARA software.

## Release gate for the outreach packet

Do not call this packet externally ready until all of the following are true:

- [x] reviewer-first root README exists;
- [x] narrow review target is identified;
- [x] architecture/threat model exists;
- [x] reproducibility procedure exists;
- [x] claims boundary exists;
- [x] licensing ambiguity is explicit rather than silently assumed;
- [x] outreach asks for criticism, not endorsement;
- [x] key-continuity gap is patched and regression-tested in source;
- [x] single-writer storage assumption is documented;
- [ ] external-review CI passes on the final head commit;
- [ ] existing repository-required checks pass on the final head commit;

When the final two boxes are green, the repository is suitable for a one-time technical-review request. That still does not imply the recipient will respond or that a partnership exists.
