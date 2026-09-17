# Verified Local Full-Stack Deployment

Status: **DEPLOYMENT CANDIDATE / REQUIRES EXACT-HEAD CI BEFORE PROTECTED-MAIN PROMOTION**

## Scope

This procedure deploys the localhost-only Worldshepherd software baseline:

- SARA / SSPADAWANZZ administration service;
- PRIME SENTINEL authorization signer;
- ECHO SENTINEL LINK persistence and signed-checkpoint service.

All three host ports remain bound to `127.0.0.1`.

This profile is for synthetic, public, or otherwise explicitly authorized local data. It does not authorize public-network exposure, CUI/classified processing, export-controlled data, customer production data, or regulated clinical use.

## Host prerequisites

Required:

- Git checkout of the exact release commit;
- Docker Engine with Docker Compose v2;
- Python 3;
- OpenSSL;
- curl;
- root privileges or `sudo` for provisioning service-owned secret files.

The reference containers run as UID `10001`.

## One-command deployment

From the repository root:

```bash
bash scripts/sara.sh deploy-full
```

The command:

1. refuses a dirty tracked deployment subtree;
2. resolves the exact 40-character Git commit;
3. provisions independent SARA admin/relay bearer tokens;
4. provisions PRIME and ECHO secret files outside Git under `/var/lib/worldshepherd` by default;
5. sets secret ownership to UID `10001` and mode `0600`;
6. generates Ed25519 PRIME and ECHO keys when missing;
7. starts PRIME first and obtains its public key;
8. binds that public key into SARA's verification-only trust configuration;
9. runs the fail-closed host/config preflight;
10. starts SARA + PRIME + ECHO;
11. waits for all readiness endpoints;
12. executes the full runtime acceptance verifier.

Override the secret root only when needed:

```bash
WS_DEPLOY_SECRET_ROOT=/approved/absolute/path bash scripts/sara.sh deploy-full
```

Override the release identifier only with an evidence-backed release label:

```bash
WS_DEPLOY_RELEASE_ID=ws-local-approved-001 bash scripts/sara.sh deploy-full
```

## Verification

Run at any time:

```bash
bash scripts/sara.sh verify-full
```

A PASS requires all of the following:

- deployment preflight passes;
- `SARA_BUILD_COMMIT` equals checked-out Git HEAD;
- release identity is not `UNKNOWN`, `UNVERIFIED`, or `UNCONFIGURED`;
- SARA, PRIME, and ECHO readiness pass;
- SARA administrator self-test passes;
- relay credentials are denied administrator access;
- SARA trusts the exact PRIME public key exposed by the deployed signer;
- PRIME performs a live signing transaction and SARA verifies that assertion using public-key material only;
- ECHO ingests a deployment probe;
- ECHO creates a signed checkpoint;
- the deployed ECHO image independently verifies that checkpoint against the separately obtained checkpoint-key fingerprint;
- all three containers run non-root;
- all three containers use read-only root filesystems;
- all capabilities are dropped;
- `no-new-privileges` is active;
- every published port is bound to `127.0.0.1`;
- OCI image revision/version labels match the exact commit/release;
- retained deployment evidence contains no raw `docker inspect` payloads.

The receipt is written under:

```text
deployments/sara_verified_local_v1/.deployment-evidence/full-stack/<UTC timestamp>/receipt.json
```

The receipt is claims-bounded and does not contain SARA bearer-token values.

## Stop

```bash
bash scripts/sara.sh down-full
```

This stops SARA, PRIME, and ECHO but does **not** delete named Docker volumes.

Do not add `-v` unless destruction of retained local state/evidence is explicitly intended and approved.

## Secret custody

Default host files:

```text
/var/lib/worldshepherd/prime-sentinel/ed25519-private.pem
/var/lib/worldshepherd/prime-sentinel/service-token
/var/lib/worldshepherd/echo/ingest-token
/var/lib/worldshepherd/echo/checkpoint-ed25519-private.pem
```

These files are not committed to Git and must remain service-UID-owned with no group/other permissions.

The deployable baseline uses:

```text
ECHO_CHECKPOINT_SIGNER_MODE=LOCAL_PEM
```

The ECHO external-signer interface and AWS KMS Ed25519 adapter are separate software capabilities. They do not convert this local profile into an HSM/KMS-custody claim. `EXTERNAL` mode fails closed until a deployment integration injects an actual approved signer.

## Evidence confidentiality

Deployment evidence may contain:

- public keys/fingerprints;
- signed assertions;
- event/checkpoint IDs and digests;
- image/container IDs;
- release/commit identity;
- sanitized security configuration.

It must not contain:

- SARA bearer-token values;
- PRIME service-token values;
- ECHO ingest-token values;
- private signing-key bytes;
- raw container inspection documents containing environment secrets.

The CI deployment gate explicitly scans retained evidence for SARA bearer-token leakage.

## Production boundary

A successful full-stack PASS establishes an internally verified **localhost software deployment baseline** at the named commit.

It does not establish:

- public-network production authorization;
- TLS edge/reverse-proxy authorization;
- identity-provider integration;
- CMMC certification;
- NIST SP 800-171 organizational conformity;
- RMF/ATO;
- HSM/KMS/FIPS key custody;
- immutable/WORM retention;
- controlled-data approval;
- customer/government acceptance;
- physical/clinical validation;
- independent external reproduction.

Those are separate evidence gates.
