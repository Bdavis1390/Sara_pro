# Worldshepherd Identity Security G1

## Purpose

G1 converts the IDScan/Nexus incident lessons into an executable, claims-controlled defensive identity-policy gate inside the governed SARA package.

The gate is deliberately narrow. It implements software controls for:

- tenant isolation;
- tenant-scoped key-reference enforcement;
- default denial of raw identity-document reads;
- bounded raw-document retention with purge identification;
- selective disclosure through boolean derived assertions;
- hardware-backed privileged-authentication policy;
- per-request and rolling-window assertion-export limits;
- fail-closed handling of unsupported derived claims; and
- SHA-256 chained audit-event digests plus deterministic report verification.

No real identity document or personal identity data is used by the benchmark.

## Data-minimization model

The preferred path is:

`temporary identity evidence -> verification -> minimum derived claims -> signed/digested assertion evidence -> raw evidence deletion`

The G1 demonstration exposes only boolean derived claims such as `identity_verified` and `age_over_21`. It intentionally does not include a driver's-license number, image, address, birth date, barcode payload, or other reusable identity artifact in the generated assertion.

## Deterministic adversarial cases

The G1 benchmark executes and requires correct handling of:

1. legitimate same-tenant verification with privileged authentication;
2. selective assertion issuance;
3. oversized bulk export;
4. rolling-window export-volume exceedance;
5. cross-tenant raw-document access;
6. expired raw-document access;
7. weak privileged authentication; and
8. tenant-key scope mismatch.

The acceptance report also verifies that expired raw records are identified for purge and that the chained audit sequence is internally consistent.

## Claims boundary

G1 is `IMPLEMENTED_IN_SOFTWARE`.

That means the policy evaluator, deterministic cases, evidence digesting, assertion minimization, and test harness exist in the repository and can be executed.

G1 does **not** establish:

- production encryption or HSM/KMS-backed tenant isolation;
- actual WebAuthn/FIDO/hardware-token integration;
- an external append-only/WORM audit store;
- scanner, DMV, wallet, identity-provider, or KYC-provider integration;
- production-scale anomaly detection;
- independent penetration testing;
- production deployment;
- NIST conformity or certification; or
- prevention of any specific real-world breach.

## Standards alignment target

NIST SP 800-63-4 and SP 800-63A-4 are treated as architecture and test-design alignment targets for digital identity and identity proofing. This document does not claim formal conformance.

A later gate must map concrete deployed controls, authenticators, proofing methods, retention behavior, fraud controls, and evidence to applicable normative requirements before any conformity statement is considered.

## Next gates

### G2 — cryptographic and authenticator integration

- real KMS/HSM-backed per-tenant keys;
- envelope encryption and independent tenant-key rotation;
- WebAuthn/FIDO2 or equivalent hardware-backed privileged authentication;
- signed assertion envelopes with expiration and revocation state;
- append-only external audit sink; and
- replay/revocation tests.

### G3 — service/API integration

- SARA/PRIME authorization hooks;
- ECHO provenance ingestion;
- OVERWATCH export/anomaly telemetry;
- explicit deletion/retention job;
- load and concurrency tests; and
- negative testing for tenant-boundary confusion and privilege escalation.

### G4 — external validation

- independent security review;
- controlled penetration testing;
- privacy/legal review;
- identity-provider interoperability testing; and
- evidence-based standards assessment.

No later-gate result may be inferred from a G1 pass.
