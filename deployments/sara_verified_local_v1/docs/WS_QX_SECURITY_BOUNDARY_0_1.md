# WS-QX 0.1 Evidence Integrity / Security Boundary

WS-QX evidence is only useful if custody is distinguishable from truth.

A SHA-256 digest can demonstrate that recorded bytes have not changed relative to a known digest; it does not prove that a sensor was calibrated, an operator was authorized, a measurement was physically observed, or an external laboratory was independent.

Accordingly WS-QX separates:

1. integrity: digests and immutable references;
2. identity: hardware/operator/model/configuration identifiers;
3. authorization: PRIME-governed permission records;
4. provenance: ECHO evidence lineage;
5. measurement validity: calibration, uncertainty, test controls;
6. qualification: profile-specific pass/fail dimensions;
7. replication: separately sourced external evidence.

Threats to address in later versions include evidence substitution, replay, stale calibration, configuration drift, forged hardware identity, timestamp manipulation, selective omission, test-manifest substitution, unauthorized claim promotion, and circular/self-attested external validation.

WS-QX 0.1 does not claim cryptographic attestation, TPM/TEE binding, production PKI, CUI authorization, or certification. Those remain separate implementation and validation tasks.
