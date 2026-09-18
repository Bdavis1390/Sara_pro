# WS-SARA G9D — REMOTE REGISTRY WITNESS SERVICE

Status: **IMPLEMENTED ON STACKED BRANCH / PENDING G8 + G9A-C + EXACT-HEAD QUALIFICATION**

## Purpose

G9D moves the G9C monotonic witness protocol across a separately callable service boundary and makes the software deployable as a durable standalone witness process.

It does not promote deployment-independence claims merely because another process or container exists.

## Remote witness service

The service provides a durable SQLite monotonic ledger for one configured:

- witness ID;
- namespace;
- Ed25519 signing key ID;
- signing-key fingerprint.

The ledger verifies its stored receipt chain and head/history consistency at initialization and exposes authenticated endpoints for:

- public witness-key record;
- current head;
- witness advancement;
- integrity status.

Lower generations and same-generation conflicting coordinates fail closed.

## Client trust configuration

The SARA-side runtime requires:

- HTTPS witness URL;
- bearer token from an absolute, non-symlink, service-UID-owned file;
- local witness public-key record from an absolute, non-symlink file;
- independently configured expected SHA-256 fingerprint for that witness key;
- optional private-CA bundle from a securely opened, absolute, non-symlink file.

When a private CA is configured, its validated bytes are loaded directly into the SSL context rather than reopening the path after validation.

Hostname verification and certificate verification remain enabled.

## G9D HTTPS qualification

The dedicated qualification creates:

1. an ephemeral CI root CA;
2. a server certificate signed by that CA;
3. SANs for `DNS:localhost` and `IP:127.0.0.1`;
4. a separate witness Ed25519 key;
5. an independent witness bearer token;
6. a persistent witness database directory.

The CA private key is deleted immediately after issuing the server certificate and is never included in the witness-container mount.

All HTTP client operations use the CA certificate with ordinary certificate/hostname verification.

The Python client uses:

`ssl.create_default_context(cafile=...)`

or the equivalent secure runtime `cadata` path, with hostname checking enabled.

Qualification exercises:

- generic unit tests;
- standalone witness image build;
- CA-chain verification;
- SAN/hostname verification;
- bearer-authenticated public-key retrieval;
- signed witness advancement;
- local pinned-key signature verification;
- durable head recovery after container restart;
- ledger integrity after restart;
- lower-generation rejection after restart.

## Explicit non-claims

The CI qualification records:

- `external_witnessed=false`;
- `independence_verified=false`.

A separate process/container on one GitHub runner does not establish:

- separate administration;
- separate cloud account or security boundary;
- separate backup/rollback domain;
- WORM retention;
- production availability;
- HSM/KMS custody of the witness key;
- FIPS validation;
- external timestamp authority;
- independent third-party operation.

## Promotion requirement

To promote beyond internally verified remote-protocol software evidence, deploy the witness in a genuinely separate administrative and persistence domain, pin its identity from SARA-side configuration, demonstrate independent backup/rollback controls, and repeat the G8 coherent-rollback campaign against that deployment.

Only then may `external_witnessed` or `independence_verified` be reconsidered.
