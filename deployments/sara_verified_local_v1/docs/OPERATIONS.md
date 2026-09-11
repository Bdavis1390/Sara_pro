# SARA Verified Local v1 — Operations & Incident Runbook

## Scope
This runbook applies to the localhost-only `sara_verified_local_v1` deployment and synthetic/public/releasable data. It does **not** authorize CUI, classified, export-controlled, partner-proprietary, or operational mission data and does not establish CMMC, NIST SP 800-171 compliance, RMF/ATO, or customer operational approval.

## Supported operating state
- Service must remain bound to loopback on the host unless a separately reviewed production profile is approved.
- The application container runs non-root, read-only root filesystem, dropped Linux capabilities, and `no-new-privileges`.
- Persistent application state resides in the named `sara_data` volume.
- Relay and admin credentials are separate; relay credentials must not authorize admin endpoints.
- `/livez` establishes process liveness. `/readyz` establishes application/storage readiness. `/health` is compatibility/status information, not an authorization decision.

## Operational checks
At start of shift or after deployment/recovery:
1. Run `docker compose config --quiet`.
2. Run `scripts/verify_deployment.sh`.
3. Confirm `/livez` and `/readyz` are healthy.
4. Confirm relay token remains blocked from admin endpoints.
5. Confirm audit append/self-test succeeds.
6. Capture `scripts/ops_snapshot.sh` output and retain with the relevant release/incident record.

## PRIME SENTINEL optional signer profile

The default SARA deployment does not start the signing service. Enable the signer only after provisioning its two host-side secret files outside the repository:

- `/var/lib/worldshepherd/prime-sentinel/ed25519-private.pem`
- `/var/lib/worldshepherd/prime-sentinel/service-token`

The reference signer container runs as UID `10001`. Each file must be owned by that UID and grant no group/other permissions. The private key must be an unencrypted Ed25519 PEM key. The bearer-token file must contain one independent token of at least 32 characters. Do not reuse the SARA relay or administrator bearer values.

One controlled provisioning pattern is to generate material in a root-only temporary directory, install it to the paths above with owner/group `10001:10001` and mode `0600`, then securely remove the temporary copies. Do not place private key or bearer-token contents in shell history, `.env`, Git, issue text, logs, CI artifacts, or release evidence.

Set `PRIME_SENTINEL_SIGNING_KEY_ID` only in the signer launch environment, then start the opt-in profile with `docker compose --profile prime-sentinel up -d prime-sentinel`. Retrieve `/v1/public-key`, independently confirm its fingerprint against the intended key, and configure only that public key in SARA through `PRIME_SENTINEL_PUBLIC_KEYS_JSON`. Recreate/restart SARA after changing trusted public keys.

The reference host binding remains loopback-only. Do not expose port 9540 publicly. Key rotation requires introducing the new public key into SARA, validating issuance/verification, moving issuance to the new key ID, revoking the prior key ID in SARA, and retaining the rotation evidence. Suspected signer-key or signer-token compromise is SEV-1 and requires immediate signer shutdown, credential/key replacement, revocation of the compromised key ID, preservation of evidence, and explicit human reauthorization before resuming release issuance.

`VERIFY_PRIME_SENTINEL_INTEGRATION=1 scripts/verify_deployment.sh` enables the same two-container signer→SARA lifecycle gate used by protected CI. GitHub Actions runs that integration automatically. The test uses ephemeral secrets and proves software separation, signature verification, replay rejection, and one-time authorization consumption; it does not validate production/HSM custody.

## Incident classes
- **SEV-1:** suspected credential compromise, unauthorized admin action, integrity/custody failure, prohibited-data exposure, or inability to trust audit/configuration state.
- **SEV-2:** service unavailable, readiness failure, persistent-data corruption, repeated authorization failures, or recovery failure without evidence of compromise.
- **SEV-3:** degraded/non-critical function, performance regression, warning-level dependency/runtime issue, or documentation/configuration drift.

## Fail-closed response
For SEV-1:
1. Stop consequential automation and do not approve new external actions.
2. Preserve logs/evidence before destructive remediation when safe.
3. Rotate affected credentials outside version control.
4. Isolate the localhost deployment from any external integration path.
5. Record incident UTC start, operator, Git commit, configuration digest, evidence digests, observed symptoms, containment action, and recovery decision.
6. Restore only from an approved evidence-backed state; do not silently repair an untrusted history.
7. Require explicit human closure/re-authorization before resuming consequential workflows.

For SEV-2:
1. Capture operations snapshot and container logs.
2. Run readiness/self-test.
3. If persistent state is suspect, run the recovery procedure against a verified backup artifact.
4. Verify exact evidence/data inventory after restore.
5. Record discrepancy and root cause before returning to normal operation.

For SEV-3:
1. Record the regression/warning and affected version.
2. Open a tracked corrective issue.
3. Do not promote evidence maturity merely because the service remains available.

## Evidence retention baseline
The public CI evidence retention period is a convenience baseline, not a federal records schedule. For this local profile:
- Qualification and recovery artifacts should be retained for at least 90 days when CI storage permits.
- Release acceptance records should retain commit SHA, artifact SHA-256, workflow/run identity, and claims boundary even after ephemeral artifacts expire.
- Incidents remain open until evidence identifies containment, restoration state, residual risk, and authorized closure.
- Deletion or retention changes involving regulated/customer records require separate legal/contract review.

## Recovery
`scripts/recovery_exercise.sh` proves a destructive named-volume backup/restore loop for synthetic/public local data. It does **not** prove replacement-host recovery, off-host independent retention, disaster recovery across regions, or controlled-data restoration.

## Rollback
A rollback is authorized only to a specifically identified prior release whose code/evidence state is known. Rollback must preserve an immutable record of:
- source release commit;
- target prior commit/image;
- data/schema compatibility decision;
- pre-rollback backup digest;
- post-rollback readiness and smoke-test results;
- operator approval.

Until a CI rollback drill against a frozen prior release is green, full deployment rollback remains an open production-readiness gate.

## Escalation / claims rule
When uncertainty exists, classify the state as `UNVERIFIED` or the applicable `REQUIRES_*` category and escalate. No operational procedure may convert internal evidence into external certification, physical validation, government acceptance, or legal eligibility.

## Research intake governance reference
Worldshepherd Research Intake Wave 3 is governed by the repository-level intake record, claims matrix, machine-readable ledger, and execution queue under `../../../docs/WS_RESEARCH_INGEST_WAVE3_*`. These records are evidence-governance inputs only; they do not authorize external network activity, controlled-data handling, physical capability claims, partner validation, or operational use.
